"""Security (lightweight) area summary.

Inputs: objects/clusterroles, clusterrolebindings, roles, rolebindings, serviceaccounts, pods, deployments, statefulsets, daemonsets, cronjobs, namespaces, networkpolicies, policyendpoints (networking.k8s.aws), externalsecrets, ec2nodeclasses,
tools/polaris.json (Security category), aws/describe-cluster.json (Secret KMS encryption, OIDC), ec2-instances-imds.json, pod-identity-associations.json, summary.k3s (network policy disabled flag).

Output is the `security` section of summary.json: rbac (cluster-admin bindings, wildcard ClusterRoles, secrets read access), service_accounts (token auto-mount without RBAC), pod_security (privileged, host*, hostPath, root, capabilities, PSA labels),
secrets (plaintext env candidates, variable names only; ExternalSecrets not synced; KMS encryption), networkpolicy (enforcement, default-deny), aws (IRSA, Pod Identity, IMDS), polaris_security. Secret values are never recorded anywhere.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from . import scrub
from .snapshot import load_json, objects

SECRET_ENV_RE, ENV_SKIP_RE = scrub.SECRET_ENV_RE, scrub.ENV_SKIP_RE  # shared with the collection-time ConfigMap scan
DANGEROUS_CAPS = {"SYS_ADMIN", "NET_ADMIN", "SYS_PTRACE", "SYS_MODULE", "ALL", "NET_RAW", "SYS_RAWIO", "DAC_READ_SEARCH"}
SYSTEM_NS_PREFIX = ("kube-", "karpenter", "monitoring", "cert-manager", "external-secrets", "ingress-nginx", "metallb-system", "keda", "argocd", "arc-system", "arc-systems", "logging", "reloader")
SYSTEM_SUBJECTS = {("Group", "system:masters"), ("User", "eks:addon-manager"), ("Group", "system:nodes"), ("User", "system:kube-controller-manager"), ("User", "system:kube-scheduler")}


def _wl(kind: str, o: dict) -> str:
    return f"{o['metadata']['namespace']}/{kind.lower()}/{o['metadata']['name']}"


def _tpl(kind: str, o: dict) -> dict:
    if kind == "CronJob":
        return ((((o.get("spec") or {}).get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec") or {}
    return ((o.get("spec") or {}).get("template") or {}).get("spec") or {}


def _rbac(snap: Path, prod: set) -> dict:
    crs = {c["metadata"]["name"]: c for c in objects(snap, "clusterroles.rbac.authorization.k8s.io")}
    crbs = objects(snap, "clusterrolebindings.rbac.authorization.k8s.io")
    rbs = objects(snap, "rolebindings.rbac.authorization.k8s.io")
    roles = {(r["metadata"]["namespace"], r["metadata"]["name"]): r for r in objects(snap, "roles.rbac.authorization.k8s.io")}

    def subjects(b):
        return [{"kind": s.get("kind"), "namespace": s.get("namespace"), "name": s.get("name")} for s in b.get("subjects") or []]

    def is_system(s):
        return (s["kind"], s["name"]) in SYSTEM_SUBJECTS or str(s["name"]).startswith("system:") or str(s["name"]).startswith("eks:")

    admin = []
    for b in crbs:
        if (b.get("roleRef") or {}).get("name") == "cluster-admin":
            subs = subjects(b)
            admin.append({"binding": b["metadata"]["name"], "subjects": subs, "non_system": [s for s in subs if not is_system(s)]})
    admin_ns = [{"binding": f"{b['metadata']['namespace']}/{b['metadata']['name']}", "subjects": subjects(b)} for b in rbs if (b.get("roleRef") or {}).get("kind") == "ClusterRole" and (b.get("roleRef") or {}).get("name") == "cluster-admin"]

    def wildcard(rules):
        return any(("*" in (r.get("verbs") or [])) and ("*" in (r.get("resources") or []) or "*" in (r.get("apiGroups") or [])) for r in rules or [])

    def reads_secrets(rules):
        return any(("secrets" in (r.get("resources") or []) or "*" in (r.get("resources") or [])) and any(v in (r.get("verbs") or []) for v in ("list", "get", "*", "watch")) for r in rules or [])

    bound_cr: dict[str, list] = defaultdict(list)
    for b in crbs:
        rr = b.get("roleRef") or {}
        if rr.get("kind") == "ClusterRole":
            bound_cr[rr["name"]] += subjects(b)
    for b in rbs:
        rr = b.get("roleRef") or {}
        if rr.get("kind") == "ClusterRole":
            bound_cr[rr["name"]] += [{**s, "via_rolebinding": b["metadata"]["namespace"]} for s in subjects(b)]
    wild = []
    secret_readers = []
    for name, c in crs.items():
        if name == "cluster-admin" or name.startswith("system:"):
            continue
        subs = bound_cr.get(name, [])
        if wildcard(c.get("rules")):
            wild.append({"clusterrole": name, "role": None, "bound_subjects": subs[:8], "bound": bool(subs), "prod": False})
        elif reads_secrets(c.get("rules")) and subs and not any(k.get("via_rolebinding") for k in subs):
            user_subs = [s for s in subs if not is_system(s) and not str(s.get("namespace") or "").startswith(SYSTEM_NS_PREFIX)]  # operators (argocd, ESO, cert-manager, KEDA, monitoring) read secrets by design
            if user_subs:
                secret_readers.append({"clusterrole": name, "bound_subjects": user_subs[:8]})
    for (ns, name), r in roles.items():
        if wildcard(r.get("rules")):
            subs = [subjects(b) for b in rbs if b["metadata"]["namespace"] == ns and (b.get("roleRef") or {}).get("kind") == "Role" and (b.get("roleRef") or {}).get("name") == name]
            wild.append({"clusterrole": None, "role": f"{ns}/{name}", "bound_subjects": [s for ss in subs for s in ss][:8], "bound": bool(subs), "prod": ns in prod})
    bound_sa = {(s["namespace"], s["name"]) for subs in bound_cr.values() for s in subs if s.get("kind") == "ServiceAccount"}
    for b in rbs:
        for s in subjects(b):
            if s.get("kind") == "ServiceAccount":
                bound_sa.add((s.get("namespace") or b["metadata"]["namespace"], s.get("name")))
    return {
        "clusterrolebindings": len(crbs),
        "rolebindings": len(rbs),
        "clusterroles": len(crs),
        "cluster_admin_bindings": admin,
        "cluster_admin_non_system": [a for a in admin if a["non_system"]],
        "cluster_admin_namespace_bindings": admin_ns,
        "wildcard_roles": wild,
        "secret_readers": [s for s in secret_readers if s["bound_subjects"]],
        "bound_service_accounts": sorted(f"{ns}/{n}" for ns, n in bound_sa),
    }


def _service_accounts(snap: Path, prod: set, bound_sa: set) -> dict:
    sas = {(s["metadata"]["namespace"], s["metadata"]["name"]): s for s in objects(snap, "serviceaccounts")}
    rows = []
    seen = set()
    for p in objects(snap, "pods"):
        if p["status"].get("phase") != "Running":
            continue
        ns = p["metadata"]["namespace"]
        sp = p.get("spec") or {}
        sa_name = sp.get("serviceAccountName") or "default"
        sa = sas.get((ns, sa_name)) or {}
        mount = sp.get("automountServiceAccountToken")
        if mount is None:
            mount = sa.get("automountServiceAccountToken", True)
        own = next((x for x in p["metadata"].get("ownerReferences") or []), {})
        kind_l = "deployment" if own.get("kind") == "ReplicaSet" else (own.get("kind") or "pod").lower()
        wl = f"{ns}/{kind_l}/{own.get('name', '').rsplit('-', 1)[0] if own.get('kind') == 'ReplicaSet' else own.get('name', p['metadata']['name'])}"
        if wl in seen:
            continue
        seen.add(wl)
        rows.append(
            {
                "workload": wl,
                "namespace": ns,
                "prod": ns in prod,
                "service_account": sa_name,
                "token_mounted": bool(mount) is not False and mount is not False,
                "sa_has_rbac": f"{ns}/{sa_name}" in bound_sa,
                "irsa": bool(((sa.get("metadata") or {}).get("annotations") or {}).get("eks.amazonaws.com/role-arn")),
            }
        )
    unused = [r for r in rows if r["token_mounted"] and not r["sa_has_rbac"]]
    return {
        "service_accounts": len(sas),
        "automount_false_sa": sum(1 for s in sas.values() if s.get("automountServiceAccountToken") is False),
        "workloads": len(rows),
        "token_mounted": sum(1 for r in rows if r["token_mounted"]),
        "token_mounted_without_rbac": unused,
        "token_mounted_without_rbac_prod": [r["workload"] for r in unused if r["prod"]],
        "irsa_service_accounts": sorted(f"{ns}/{n}" for (ns, n), s in sas.items() if ((s.get("metadata") or {}).get("annotations") or {}).get("eks.amazonaws.com/role-arn")),
    }


def _pod_security(snap: Path, prod: set) -> dict:
    rows = []
    workloads = []
    for stem, kind in (("deployments", "Deployment"), ("statefulsets", "StatefulSet"), ("daemonsets", "DaemonSet"), ("cronjobs.batch", "CronJob")):
        for o in objects(snap, stem):
            workloads.append((kind, o))
    for kind, o in workloads:
        ns = o["metadata"]["namespace"]
        tpl = _tpl(kind, o)
        psc = tpl.get("securityContext") or {}
        flags = []
        if tpl.get("hostNetwork"):
            flags.append("hostNetwork")
        if tpl.get("hostPID"):
            flags.append("hostPID")
        if tpl.get("hostIPC"):
            flags.append("hostIPC")
        hp = [v["name"] for v in tpl.get("volumes") or [] if "hostPath" in v]
        if hp:
            flags.append(f"hostPath {hp}")
        root_ok = []
        caps = []
        for c in (tpl.get("containers") or []) + (tpl.get("initContainers") or []):
            sc = c.get("securityContext") or {}
            if sc.get("privileged"):
                flags.append(f"privileged:{c['name']}")
            add = set((sc.get("capabilities") or {}).get("add") or [])
            bad = add & DANGEROUS_CAPS
            if bad:
                caps.append(f"{c['name']}:{sorted(bad)}")
            run_non_root = sc.get("runAsNonRoot") if sc.get("runAsNonRoot") is not None else psc.get("runAsNonRoot")
            run_as_user = sc.get("runAsUser") if sc.get("runAsUser") is not None else psc.get("runAsUser")
            if not run_non_root and (run_as_user in (None, 0)):
                root_ok.append(c["name"])
        if caps:
            flags.append(f"capabilities {caps}")
        system = ns.startswith(SYSTEM_NS_PREFIX) or (kind == "DaemonSet" and ns.startswith("kube-"))
        severe = any(f.startswith(("privileged", "hostPID", "hostIPC")) for f in flags) or bool(caps)
        if flags or root_ok:
            rows.append(
                {
                    "workload": _wl(kind, o),
                    "kind": kind,
                    "namespace": ns,
                    "prod": ns in prod,
                    "system": system,
                    "flags": flags,
                    "root_allowed_containers": root_ok,
                    "severe": severe,
                    "host_access": any(f.startswith(("hostNetwork", "hostPath")) for f in flags),
                }
            )
    psa = {}
    for n in objects(snap, "namespaces"):
        labels = n["metadata"].get("labels") or {}
        psa[n["metadata"]["name"]] = {"enforce": labels.get("pod-security.kubernetes.io/enforce"), "warn": labels.get("pod-security.kubernetes.io/warn"), "audit": labels.get("pod-security.kubernetes.io/audit")}
    total = len(workloads)
    return {
        "workloads": total,
        "rows": rows,
        "severe": [r["workload"] for r in rows if r["severe"] and not r["system"]],
        "severe_system": [r["workload"] for r in rows if r["severe"] and r["system"]],
        "host_access_non_system": [r["workload"] for r in rows if r["host_access"] and not r["system"]],
        "root_allowed_prod": [r["workload"] for r in rows if r["root_allowed_containers"] and r["prod"]],
        "root_allowed_ratio": round(sum(1 for r in rows if r["root_allowed_containers"]) / total, 2) if total else None,
        "psa": psa,
        "psa_enforced_namespaces": sorted(k for k, v in psa.items() if v["enforce"]),
        "prod_without_psa": sorted(n for n in prod if not (psa.get(n) or {}).get("enforce")),
    }


def _secrets(snap: Path, prod: set, platform: str | None) -> dict:
    plain = []
    for stem, kind in (("deployments", "Deployment"), ("statefulsets", "StatefulSet"), ("daemonsets", "DaemonSet"), ("cronjobs.batch", "CronJob")):
        for o in objects(snap, stem):
            ns = o["metadata"]["namespace"]
            for c in _tpl(kind, o).get("containers") or []:

                def suspicious(e):
                    v = str(e.get("value"))
                    if not v or v == "None" or v.startswith("/") or v.isdigit() or v.lower() in ("true", "false", "yes", "no", "on", "off") or len(v) < 8:
                        return False  # numeric limits (TOKEN_CAP), flags (ALLOW_EMPTY_PASSWORD=yes) and short values are not secrets
                    if e["name"].startswith("STAKATER_"):
                        return False  # the "Secret name to watch" variable injected by Reloader
                    return bool(SECRET_ENV_RE.search(e["name"])) and not ENV_SKIP_RE.search(e["name"])

                names = [e["name"] for e in c.get("env") or [] if "value" in e and suspicious(e)]
                if names:
                    plain.append({"workload": _wl(kind, o), "namespace": ns, "prod": ns in prod, "container": c["name"], "env_names": names[:8]})  # values are not recorded
    # A ConfigMap key is a candidate when its name looks secret-like and its value looks like a secret (key name only is recorded, never the value; e.g. fluent-bit HTTP_Passwd)
    cm_rows = []
    cm_used: dict[tuple, set] = {}
    for stem, kind in (("deployments", "Deployment"), ("statefulsets", "StatefulSet"), ("daemonsets", "DaemonSet"), ("cronjobs.batch", "CronJob")):
        for o in objects(snap, stem):
            ns = o["metadata"]["namespace"]
            tpl = _tpl(kind, o)
            for v in tpl.get("volumes") or []:
                if v.get("configMap"):
                    cm_used.setdefault((ns, v["configMap"].get("name")), set()).add(_wl(kind, o))
            for c in tpl.get("containers") or []:
                for ef in c.get("envFrom") or []:
                    if ef.get("configMapRef"):
                        cm_used.setdefault((ns, ef["configMapRef"].get("name")), set()).add(_wl(kind, o))
                for e in c.get("env") or []:
                    ref = (e.get("valueFrom") or {}).get("configMapKeyRef")
                    if ref:
                        cm_used.setdefault((ns, ref.get("name")), set()).add(_wl(kind, o))
    for cm in objects(snap, "configmaps"):
        ns, name = cm["metadata"]["namespace"], cm["metadata"]["name"]
        if ns.startswith(SYSTEM_NS_PREFIX) or name.startswith("kube-root-ca") or ((cm["metadata"].get("annotations") or {}).get("meta.helm.sh/release-name") and name.endswith(("-dashboard", "-dashboards"))):
            continue
        # The detection ran at collection time, before the values were dropped from the snapshot (lib/scrub.py); only key names are recorded.
        keys = scrub.configmap_secret_like_keys(cm)
        if keys:
            cm_rows.append({"namespace": ns, "name": name, "target": f"{ns}/configmap/{name}", "prod": ns in prod, "keys": keys[:8], "mounted_by": sorted(cm_used.get((ns, name), set()))[:6]})
    es_bad = []
    es_total = 0
    for es in objects(snap, "externalsecrets.external-secrets.io"):
        es_total += 1
        conds = {c.get("type"): c for c in (es.get("status") or {}).get("conditions") or []}
        r = conds.get("Ready") or {}
        if r.get("status") != "True":
            es_bad.append({"namespace": es["metadata"]["namespace"], "name": es["metadata"]["name"], "reason": r.get("reason"), "message": (r.get("message") or "")[:160], "prod": es["metadata"]["namespace"] in prod})
    types = Counter()
    m = load_json(snap / "metrics" / "secret_types.json")
    for s in (m or {}).get("result") or []:
        types[(s.get("metric") or {}).get("type")] += 1
    kms = None
    dc = load_json(snap / "aws" / "describe-cluster.json")
    if dc:
        enc = (dc.get("cluster") or {}).get("encryptionConfig") or []
        kms = {"enabled": bool(enc), "resources": [r for e in enc for r in (e.get("resources") or [])], "key": ((enc[0].get("provider") or {}).get("keyArn") if enc else None)}
    return {
        "plaintext_env": plain,
        "plaintext_env_prod": [p["workload"] + ":" + p["container"] for p in plain if p["prod"]],
        "plaintext_configmap": cm_rows,
        "plaintext_configmap_prod": [r["target"] for r in cm_rows if r["prod"]],
        "externalsecrets": es_total,
        "externalsecrets_not_ready": es_bad,
        "secret_types": dict(types),
        "kms_encryption": kms,
        "platform": platform,
    }


def _networkpolicy(snap: Path, prod: set, platform: str | None, k3s: dict | None) -> dict:
    nps = objects(snap, "networkpolicies.networking.k8s.io")
    by_ns: dict[str, list] = defaultdict(list)
    default_deny = set()
    for n in nps:
        ns = n["metadata"]["namespace"]
        sp = n.get("spec") or {}
        by_ns[ns].append(n["metadata"]["name"])
        if not (sp.get("podSelector") or {}).get("matchLabels") and not (sp.get("podSelector") or {}).get("matchExpressions") and "Ingress" in (sp.get("policyTypes") or ["Ingress"]) and not sp.get("ingress"):
            default_deny.add(ns)
    enforced, how = None, None
    if platform == "eks":
        enforced = False
        how = "aws-eks-nodeagent in the aws-node DaemonSet has no --enable-network-policy argument"
        for d in objects(snap, "daemonsets"):
            if d["metadata"]["name"] == "aws-node":
                for c in d["spec"]["template"]["spec"].get("containers") or []:
                    for a in c.get("args") or []:
                        if a.startswith("--enable-network-policy="):
                            enforced = a.endswith("true")
                            how = f"aws-eks-nodeagent {a}"
                    for e in c.get("env") or []:
                        if e.get("name") == "ENABLE_NETWORK_POLICY":
                            enforced = str(e.get("value")).lower() == "true"
                            how = f"aws-node ENABLE_NETWORK_POLICY={e.get('value')}"
        pe = len(objects(snap, "policyendpoints.networking.k8s.aws"))
        how += f", {pe} PolicyEndpoints"
        if nps and pe == 0 and enforced:
            how += " (policies exist but 0 PolicyEndpoints; the controller may not be running)"
    elif platform == "k3s":
        args = []
        for n in (k3s or {}).get("nodes") or []:
            args += n.get("args") or []
        enforced = "--disable-network-policy" not in args
        how = "k3s built-in kube-router network policy controller" + (" (disabled via --disable-network-policy)" if not enforced else "")
    else:
        how = "verify that the CNI implements NetworkPolicy (Calico and Cilium do; plain flannel does not)"
    return {
        "policies": len(nps),
        "namespaces_with_policy": sorted(by_ns),
        "default_deny_ingress_namespaces": sorted(default_deny),
        "prod_without_default_deny": sorted(n for n in prod if n not in default_deny),
        "enforced": enforced,
        "enforcement": how,
        "policies_but_not_enforced": bool(nps) and enforced is False,
    }


def _aws(snap: Path, inv: dict, sa_info: dict) -> dict:
    if (inv.get("cluster") or {}).get("platform") != "eks":
        return {"applicable": False}
    inst = load_json(snap / "aws" / "ec2-instances-imds.json")
    rows = [i for i in (inst or []) if isinstance(i, dict)]
    pia = (load_json(snap / "aws" / "pod-identity-associations.json") or {}).get("associations") or []
    nodeclass = [{"name": n["metadata"]["name"], "metadataOptions": (n.get("spec") or {}).get("metadataOptions")} for n in objects(snap, "ec2nodeclasses.karpenter.k8s.aws")]
    dc = load_json(snap / "aws" / "describe-cluster.json") or {}
    oidc = (((dc.get("cluster") or {}).get("identity") or {}).get("oidc") or {}).get("issuer")
    return {
        "applicable": True,
        "instances": len(rows),
        "imds_hop_limit_gt1": [{"id": i.get("id"), "type": i.get("type"), "name": i.get("name"), "hop_limit": i.get("hop_limit"), "tokens": i.get("tokens")} for i in rows if (i.get("hop_limit") or 0) > 1 or i.get("tokens") != "required"],
        "imds_by_setting": dict(Counter(f"hop={i.get('hop_limit')} tokens={i.get('tokens')}" for i in rows)),
        "ec2nodeclass_metadata": nodeclass,
        "irsa_service_accounts": sa_info.get("irsa_service_accounts") or [],
        "pod_identity_associations": len(pia),
        "oidc_provider": bool(oidc),
        "instances_source": "aws/ec2-instances-imds.json" if inst is not None else None,
    }


def analyze(snap: Path, inv: dict | None, k3s_summary: dict | None = None) -> dict:
    inv = inv or {}
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    platform = (inv.get("cluster") or {}).get("platform")
    rbac = _rbac(snap, prod)
    sa = _service_accounts(snap, prod, set(rbac["bound_service_accounts"]))
    try:
        from .hygiene import _Ctx as _HCtx
        from .hygiene import _polaris

        pol = _polaris(_HCtx(snap, inv))
        polaris = {
            "present": pol.get("present"),
            "score": pol.get("score"),
            "security_checks": [c for c in pol.get("checks") or [] if c.get("category") == "Security"],
            "workloads": [
                {"target": r["target"], "namespace": r["namespace"], "prod": r["prod"], "security_danger": r["security_danger"], "security_warning": r["security_warning"][:6]}
                for r in pol.get("workloads") or []
                if r.get("security_danger") or r.get("security_warning")
            ],
            "danger_workloads_prod": [r["target"] for r in pol.get("workloads") or [] if r.get("security_danger") and r.get("prod")],
            "danger_workloads": [r["target"] for r in pol.get("workloads") or [] if r.get("security_danger")],
            "danger_check_counts": dict(Counter(c for r in pol.get("workloads") or [] for c in (r.get("security_danger") or []))),
        }
    except Exception as e:
        polaris = {"present": False, "error": f"{type(e).__name__}: {e}"}
    return {
        "rbac": rbac,
        "service_accounts": sa,
        "pod_security": _pod_security(snap, prod),
        "secrets": _secrets(snap, prod, platform),
        "networkpolicy": _networkpolicy(snap, prod, platform, k3s_summary),
        "aws": _aws(snap, inv, sa),
        "polaris": polaris,
    }
