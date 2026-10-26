"""Discovery (discover).

From Pods, DaemonSets, Deployments, StatefulSets, CRDs, Namespaces, StorageClasses, Nodes and `aws eks describe-cluster` (on EKS),
work out what the cluster is and what is installed, and write `inventory.json`. Prometheus/Loki retention, SSM-registered nodes,
profile guess and node access method are decided here too. Raw objects are saved to `objects/<kind>.json` so that collect
does not fetch them again.

k3s detection rule: `+k3s` in the node kubelet version, StorageClass `local-path`, `local-path-provisioner` in kube-system.
When detected: profile guess `k3s`, node access `ssh`, EKS platform collector disabled.

Adding a platform (e.g. GKE or AKS)
-----------------------------------
`detect_platform` already names "gke" and "aks" from the node providerID. Everything else keys off that string, so a new
platform is wired in at these points and nowhere else:
1. `detect_platform` (this module): add or sharpen the evidence rule; `setup.py` shows the same result, so no change there.
2. `collectors/<platform>-platform/` (detect, collect.yaml, checks.yaml, signatures.yaml): `_collectors_enabled` turns it on
   by folder name alone. `PLATFORM_COLLECTOR_ALIASES` maps a platform onto another folder when they share one (rke2 -> k3s-platform).
3. `_node_access` (this module): choose the node command backend; today gke/aks get "none" and the DaemonSet backend
   (config `node_access: daemonset`, deploy/node-access/daemonset.yaml) is the way to read nodes on them.
4. `collect.py` `CLOUD_STEP_TYPES` / `_cloud_available`: register cloud-API step types and the inventory block they need
   (the counterpart of `cluster.eks`, which `_eks_facts` fills here).
5. `components.py`: rules with `"platform": "<name>"` for the platform's add-ons (see its module docstring).
6. `kube.context_info`: kubeconfig evidence (today only EKS: server suffix, ARN cluster name, `aws eks get-token`).
7. Summary modules that branch on `inventory.cluster.platform`: `controlplane.py` (control plane log source), `security.py`
   (`_aws`, IRSA/pod identity), `cost.py` (pricing and spot facts), `observability.py` (`_failure_modes` applicability),
   `resilience.py` (spot/AZ expectations), plus `storage.py`, `kubeproxy.py`, `hygiene.py` and `k3s.py` which read it.
8. `rubric/profiles/<name>.yaml` + `_profile` here: a profile with the platform's expected families and disabled checks.
"""

from __future__ import annotations

import datetime as _dt
import fnmatch
import json
import re
from pathlib import Path

from . import __version__, aws, kube, monitoring, paths
from . import rubric as _rubric
from .components import COMPONENTS
from .config import Config
from .runlog import RunLog
from .snapshot import items

OBJECT_KINDS = {  # the minimum set of kinds inventory needs. collect fetches more kinds beyond these.
    "nodes": ["get", "nodes"],
    "namespaces": ["get", "namespaces"],
    "storageclasses": ["get", "storageclasses"],
    "customresourcedefinitions": ["get", "crds"],
    "daemonsets": ["get", "daemonsets", "-A"],
    "deployments": ["get", "deployments", "-A"],
    "statefulsets": ["get", "statefulsets", "-A"],
    "services": ["get", "services", "-A"],
    "pods": ["get", "pods", "-A"],
    "configmaps": ["get", "configmaps", "-A"],  # configuration only visible in config bodies (e.g. the fluent-bit kubernetes_events input)
}


def _match_name(pattern: str, ns: str, name: str) -> bool:
    pns, _, pname = pattern.partition("/")
    return fnmatch.fnmatchcase(ns, pns) and fnmatch.fnmatchcase(name, pname)


class _Facts:
    """Index extracted from the objects, used to match detection rules."""

    def __init__(self, objs: dict, aws_addons: list | None):
        self.workloads: dict[str, list[tuple[str, str]]] = {}
        self.images: set[str] = set()
        for kind in ("daemonsets", "deployments", "statefulsets"):
            lst = []
            for o in items(objs.get(kind)):
                m = o["metadata"]
                lst.append((m["namespace"], m["name"]))
                for c in o.get("spec", {}).get("template", {}).get("spec", {}).get("containers", []) or []:
                    if c.get("image"):
                        self.images.add(c["image"])
            self.workloads[kind[:-1]] = lst
        self.crds = {o["metadata"]["name"] for o in items(objs.get("customresourcedefinitions"))}
        self.namespaces = {o["metadata"]["name"] for o in items(objs.get("namespaces"))}
        self.provisioners = {o.get("provisioner") for o in items(objs.get("storageclasses"))}
        self.node_annotations: set[str] = set()
        self.node_versions: set[str] = set()
        for n in items(objs.get("nodes")):
            self.node_annotations |= set((n["metadata"].get("annotations") or {}).keys())
            self.node_versions.add((n.get("status", {}).get("nodeInfo") or {}).get("kubeletVersion", ""))
        self.aws_addons = aws_addons or []
        self.configmap_texts: list[tuple[str, str, str]] = []  # (ns, name, full data body)
        for cm in items(objs.get("configmaps")):
            data = cm.get("data") or {}
            if data:
                self.configmap_texts.append((cm["metadata"]["namespace"], cm["metadata"]["name"], "\n".join(str(v) for v in data.values())))

    def evidence(self, rule: dict) -> str | None:
        for key, val in rule.items():
            if key in ("daemonset", "deployment", "statefulset"):
                for ns, name in self.workloads.get(key, []):
                    if _match_name(val, ns, name):
                        return f"{key} {ns}/{name}"
            elif key == "crd" and val in self.crds:
                return f"crd {val}"
            elif key == "namespace" and val in self.namespaces:
                return f"namespace {val}"
            elif key == "storageclass_provisioner" and val in self.provisioners:
                return f"storageclass provisioner {val}"
            elif key == "node_annotation" and any(a.startswith(val) for a in self.node_annotations):
                return f"node annotation {val}*"
            elif key == "node_version_contains" and any(val in v for v in self.node_versions):
                return f"node version contains {val}"
            elif key == "image":
                hit = next((i for i in self.images if val in i), None)
                if hit:
                    return f"image {hit.split('@')[0]}"
            elif key == "configmap_data_regex":
                rx = re.compile(val, re.MULTILINE)
                for ns, name, text in self.configmap_texts:
                    if rx.search(text):
                        return f"configmap {ns}/{name} data matches {val!r}"
            elif key == "aws_addons" and self.aws_addons:
                return "aws eks list-addons: " + ", ".join(self.aws_addons)
        return None


def detect_components(objs: dict, aws_addons: list | None) -> dict:
    facts = _Facts(objs, aws_addons)
    out = {}
    for comp in COMPONENTS:
        ev = next((e for r in comp["any"] if (e := facts.evidence(r))), None)
        out[comp["name"]] = {"present": ev is not None, "family": comp["family"], "evidence": ev, "platform": comp.get("platform")}
    return out


def _node_summary(nodes: list) -> dict:
    def lbl(n, *keys):
        labels = n["metadata"].get("labels") or {}
        return next((labels[k] for k in keys if k in labels), None)

    rows = []
    for n in nodes:
        info = n.get("status", {}).get("nodeInfo") or {}
        conds = {c["type"]: c["status"] for c in (n.get("status", {}).get("conditions") or [])}
        rows.append(
            {
                "name": n["metadata"]["name"],
                "ready": conds.get("Ready") == "True",
                "roles": sorted(k.split("/", 1)[1] for k in (n["metadata"].get("labels") or {}) if k.startswith("node-role.kubernetes.io/")),
                "kubelet": info.get("kubeletVersion"),
                "os_image": info.get("osImage"),
                "kernel": info.get("kernelVersion"),
                "runtime": info.get("containerRuntimeVersion"),
                "arch": info.get("architecture"),
                "instance_type": lbl(n, "node.kubernetes.io/instance-type", "beta.kubernetes.io/instance-type"),
                "zone": lbl(n, "topology.kubernetes.io/zone", "failure-domain.beta.kubernetes.io/zone"),
                "capacity_type": lbl(n, "karpenter.sh/capacity-type", "eks.amazonaws.com/capacityType"),
                "nodegroup": lbl(n, "eks.amazonaws.com/nodegroup"),
                "nodepool": lbl(n, "karpenter.sh/nodepool"),
                "provider_id": (n.get("spec") or {}).get("providerID"),
                "internal_ip": next((a.get("address") for a in (n.get("status", {}).get("addresses") or []) if a.get("type") == "InternalIP"), None),
                "external_ip": next((a.get("address") for a in (n.get("status", {}).get("addresses") or []) if a.get("type") == "ExternalIP"), None),
                "unschedulable": bool((n.get("spec") or {}).get("unschedulable")),
                "taints": [f"{t.get('key')}={t.get('value', '')}:{t.get('effect')}" for t in ((n.get("spec") or {}).get("taints") or [])],
                "allocatable": (n.get("status", {}).get("allocatable") or {}),
                "capacity": (n.get("status", {}).get("capacity") or {}),
            }
        )

    def distinct(key):
        return sorted({str(r[key]) for r in rows if r.get(key) is not None})

    return {
        "count": len(rows),
        "ready": sum(1 for r in rows if r["ready"]),
        "kubelet_versions": distinct("kubelet"),
        "os_images": distinct("os_image"),
        "kernels": distinct("kernel"),
        "runtimes": distinct("runtime"),
        "architectures": distinct("arch"),
        "instance_types": distinct("instance_type"),
        "zones": distinct("zone"),
        "capacity_types": distinct("capacity_type"),
        "nodegroups": distinct("nodegroup"),
        "nodepools": distinct("nodepool"),
        "nodes": rows,
    }


def detect_platform(ctx_info: dict, nodes: dict, comps: dict | None = None, objs: dict | None = None) -> tuple[str, list[str]]:
    """Name the platform ("eks", "k3s", "gke", "aks", "rke2", "unknown") and list the evidence.

    `ctx_info` is `kube.context_info`, `nodes` is `_node_summary`, `comps` is `detect_components` (k3s/rke2/local-path markers)
    and `objs` holds the raw kubectl documents (StorageClass names). The last two may be empty: `setup` calls this with only the
    nodes, which still yields EKS (kubeconfig/providerID), k3s/rke2 (kubelet version) and GKE/AKS (providerID) correctly."""
    comps, objs = comps or {}, objs or {}
    reasons = []
    if ctx_info.get("is_eks"):
        reasons.append("kubeconfig points at EKS (server *.eks.amazonaws.com or aws eks get-token)")
    pids = [r.get("provider_id") or "" for r in nodes["nodes"]]
    if any(p.startswith("aws://") for p in pids):
        reasons.append("node providerID is aws://")
    if ctx_info.get("is_eks") or (pids and all(p.startswith("aws://") for p in pids) and any("eks" in v for v in nodes["kubelet_versions"])):
        return "eks", reasons
    if comps.get("k3s", {}).get("present"):
        reasons.append("+k3s in node kubelet version")
    if "local-path" in {o["metadata"]["name"] for o in items(objs.get("storageclasses"))}:
        reasons.append("StorageClass local-path")
    if comps.get("local-path-provisioner", {}).get("present"):
        reasons.append("local-path-provisioner in kube-system")
    if comps.get("k3s", {}).get("present") or len(reasons) >= 2:
        return "k3s", reasons
    if any(p.startswith("gce://") for p in pids):
        return "gke", ["node providerID is gce://"]
    if any(p.startswith("azure://") for p in pids):
        return "aks", ["node providerID is azure://"]
    if comps.get("rke2", {}).get("present"):
        return "rke2", ["+rke2 in node kubelet version"]
    return "unknown", reasons or ["no evidence for EKS, k3s, GKE or AKS (kubeadm etc.)"]


def _profile(platform: str, nodes: dict, cfg: Config, override: str | None) -> dict:
    if override:
        return {"name": override, "source": "cli --profile", "reasons": []}
    if cfg.get("profile"):
        return {"name": str(cfg["profile"]), "source": "config.yaml", "reasons": []}
    if platform == "eks":
        return {"name": "prod", "source": "detected", "reasons": ["platform eks"]}
    if platform in ("k3s", "rke2") or nodes["count"] <= 3:
        return {"name": "lab", "source": "detected", "reasons": [f"platform {platform}", f"{nodes['count']} nodes (3 or fewer)"] if nodes["count"] <= 3 else [f"platform {platform}"]}
    # 1.0 has only the eks and small k3s cluster profiles. Anything else uses the eks baseline and records the reasoning.
    zones = [z for z in (nodes.get("zones") or []) if z]
    if nodes["count"] > 20 or len(zones) >= 3:
        return {"name": "multi-az-prod", "source": "detected", "reasons": [f"platform {platform}", f"{nodes['count']} nodes, {len(zones)} AZs"]}
    return {"name": "small-prod", "source": "detected", "reasons": [f"platform {platform} (not EKS or k3s)", f"{nodes['count']} nodes (4-20), {len(zones)} AZs — inherits the checks of the base profile eks, quota and cost checks disabled"]}


def _node_access(platform: str, nodes: dict, cfg: Config, eks: dict | None, log: RunLog) -> dict:
    forced = cfg.get("node_access")
    out: dict = {"method": None, "source": "detected", "reasons": [], "ssm_registered": [], "ssm_unregistered": []}
    if forced in ("ssm", "ssh", "none"):
        out["method"], out["source"] = forced, "config.yaml"
    elif platform == "eks":
        out["method"], out["reasons"] = "ssm", ["EKS: SSM send-command"]
    elif platform in ("k3s", "rke2", "unknown"):
        out["method"], out["reasons"] = "ssh", [f"{platform}: SSH"]
    else:  # gke, aks: no native backend yet (no cluster to test one on); the platform-independent DaemonSet backend is the available option
        out["method"], out["reasons"] = (
            "none",
            [f"{platform}: node access for this platform is not implemented yet (node-exporter metrics only). Apply deploy/node-access/daemonset.yaml and set config.yaml node_access: daemonset to read nodes via kubectl exec"],
        )
    # If the user has applied deploy/node-access/daemonset.yaml (environments where neither SSM nor SSH works), nodes are read via kubectl exec — the third backend.
    # (A regression on 2026-10-26 attached the `else` above to this `if`, which turned EKS node access off; keep this block separate from the chain.)
    if cfg.get("node_access") in (None, "", "daemonset") and (platform != "eks" or cfg.get("node_access") == "daemonset"):
        ds_pods, _ = kube.kubectl_json(["get", "pods", "-n", "kubegap", "-l", "app.kubernetes.io/name=kubegap-node-reader", "-o", "json"], context=cfg.get("context"), timeout=20)
        running = [p_["spec"].get("nodeName") for p_ in ((ds_pods or {}).get("items") or []) if (p_.get("status") or {}).get("phase") == "Running"]
        if running:
            out["method"], out["reasons"] = "daemonset", [f"kubegap-node-reader DaemonSet: {len(running)} pods Running (namespace kubegap) — nodes are read via kubectl exec"]
            out["daemonset_nodes"] = running
    if out["method"] == "ssm" and eks is not None:
        prof = cfg.get("aws_profile") or eks.get("profile")
        region = cfg.get("aws_region") or eks.get("region")
        d, r = aws.aws_json(["ssm", "describe-instance-information", "--max-results", "50"], profile=prof, region=region, id="discover.ssm-instances", log=log)
        if d is None:
            out["ssm_error"] = r.error or r.stderr.strip()[-200:]
        else:
            online = {i["InstanceId"]: i.get("PingStatus") for i in d.get("InstanceInformationList", [])}
            for n in nodes["nodes"]:
                m = re.search(r"(i-[0-9a-f]+)$", n.get("provider_id") or "")
                iid = m.group(1) if m else None
                (out["ssm_registered"] if iid in online and online[iid] == "Online" else out["ssm_unregistered"]).append({"node": n["name"], "instance_id": iid})
    if out["method"] == "ssh":
        ssh_cfg = cfg.get("ssh") or {}
        out["ssh"] = {"user": ssh_cfg.get("user"), "key": ssh_cfg.get("key"), "port": ssh_cfg.get("port", 22), "note": "If empty, the host settings from ~/.ssh/config are used. Connects by node name or InternalIP"}
    return out


def _eks_facts(eks: dict, cfg: Config, snap: Path, log: RunLog) -> dict:
    prof = cfg.get("aws_profile") or eks.get("profile")
    region = cfg.get("aws_region") or eks.get("region")
    name = eks.get("name")
    out: dict = {"name": name, "region": region, "account": eks.get("account"), "profile": prof}
    kw = {"profile": prof, "region": region, "log": log}
    d, r = aws.aws_json(["eks", "describe-cluster", "--name", name], id="discover.describe-cluster", out_path=snap / "aws" / "describe-cluster.json", **kw)
    if d is None:
        out["error"] = r.error or r.stderr.strip()[-300:]
        return out
    c = d.get("cluster") or {}
    logging_on = []
    for cl in (c.get("logging") or {}).get("clusterLogging") or []:
        if cl.get("enabled"):
            logging_on += cl.get("types") or []
    vpc = c.get("resourcesVpcConfig") or {}
    out.update(
        {
            "version": c.get("version"),
            "platform_version": c.get("platformVersion"),
            "status": c.get("status"),
            "created_at": c.get("createdAt"),
            "control_plane_logging": sorted(logging_on),
            "control_plane_logging_off": sorted({"api", "audit", "authenticator", "controllerManager", "scheduler"} - set(logging_on)),
            "endpoint_public": vpc.get("endpointPublicAccess"),
            "endpoint_private": vpc.get("endpointPrivateAccess"),
            "public_access_cidrs": vpc.get("publicAccessCidrs"),
            "secrets_encryption": bool(c.get("encryptionConfig")),
            "support_type": (c.get("upgradePolicy") or {}).get("supportType"),
            "authentication_mode": (c.get("accessConfig") or {}).get("authenticationMode"),
            "subnet_ids": vpc.get("subnetIds"),
            "security_groups": (vpc.get("securityGroupIds") or []) + ([vpc.get("clusterSecurityGroupId")] if vpc.get("clusterSecurityGroupId") else []),
        }
    )
    d, r = aws.aws_json(["eks", "list-addons", "--cluster-name", name], id="discover.list-addons", out_path=snap / "aws" / "list-addons.json", **kw)
    addons = (d or {}).get("addons") or []
    out["addons"] = {}
    for a in addons:
        dd, _ = aws.aws_json(["eks", "describe-addon", "--cluster-name", name, "--addon-name", a], id=f"discover.describe-addon.{a}", out_path=snap / "aws" / f"describe-addon-{a}.json", **kw)
        ad = (dd or {}).get("addon") or {}
        out["addons"][a] = {"version": ad.get("addonVersion"), "status": ad.get("status"), "health_issues": len((ad.get("health") or {}).get("issues") or [])}
    d, r = aws.aws_json(["eks", "list-nodegroups", "--cluster-name", name], id="discover.list-nodegroups", out_path=snap / "aws" / "list-nodegroups.json", **kw)
    out["nodegroups"] = (d or {}).get("nodegroups") or []
    # ECR: repository name list (for_each input for collectors/ecr). Read-only; repository policies and images are fetched by the collector.
    d, r = aws.aws_json(["ecr", "describe-repositories", "--max-items", "500"], id="discover.ecr-repositories", out_path=snap / "aws" / "ecr-repositories.json", **kw)
    out["ecr_repositories"] = sorted(x.get("repositoryName") for x in ((d or {}).get("repositories") or []) if x.get("repositoryName"))
    return out


def discover(context: str, cfg: Config, snap: Path, *, kubeconfig: str | None = None, log: RunLog | None = None, profile_override: str | None = None, echo=print) -> dict:
    log = log or RunLog(snap / "run.log")
    log.stage("discover", "start", context=context)
    taken = _dt.datetime.now().astimezone()
    objs: dict = {}
    failures: dict = {}
    for kind, args in OBJECT_KINDS.items():
        data, r = kube.kubectl_json(args, context=context, timeout=120, id=f"discover.get-{kind}", log=log, out_path=snap / "objects" / f"{kind}.json", kubeconfig=kubeconfig)
        if data is None:
            failures[kind] = r.error or r.stderr.strip()[-200:]
        objs[kind] = data
        echo(f"  {kind:<28} {len(items(data)) if data is not None else 'failed: ' + failures[kind]}")
    ctx_info = kube.context_info(context, kubeconfig)
    ver, _ = kube.kubectl_json(["version"], context=context, timeout=20, id="discover.version", log=log, kubeconfig=kubeconfig)
    server_version = ((ver or {}).get("serverVersion") or {}).get("gitVersion")

    nodes = _node_summary(items(objs.get("nodes")))
    eks_facts = None
    aws_addons = None
    if ctx_info.get("is_eks"):
        eks_facts = _eks_facts(ctx_info.get("eks") or {}, cfg, snap, log)
        aws_addons = list((eks_facts.get("addons") or {}).keys())
    comps = detect_components(objs, aws_addons)
    platform, platform_reasons = detect_platform(ctx_info, nodes, comps, objs)
    profile = _profile(platform, nodes, cfg, profile_override)
    node_access = _node_access(platform, nodes, cfg, ctx_info.get("eks") if ctx_info.get("is_eks") else None, log)

    # Stores: service discovery + connect and read retention (same code as setup)
    svcs, _err = monitoring.find_services(context, kubeconfig, log=log)
    stores = {}
    for kind in monitoring.TARGETS:
        info = monitoring.connect_and_probe(kind, svcs.get(kind), cfg.url(kind), context, kubeconfig)
        stores[kind] = info
    # Reflect store connection results in the component table (for deployment shapes the image rules missed)
    for kind in ("prometheus", "alertmanager", "loki", "grafana"):
        if stores[kind].get("ok") and not comps[kind]["present"]:
            comps[kind]["present"] = True
            comps[kind]["evidence"] = f"service {stores[kind]['service']['namespace']}/{stores[kind]['service']['name']} connected"

    ns_names = sorted(o["metadata"]["name"] for o in items(objs.get("namespaces")))
    pods = items(objs.get("pods"))
    phase_count: dict[str, int] = {}
    for p in pods:
        ph = (p.get("status") or {}).get("phase") or "Unknown"
        phase_count[ph] = phase_count.get(ph, 0) + 1
    scs = [
        {
            "name": o["metadata"]["name"],
            "provisioner": o.get("provisioner"),
            "default": (o["metadata"].get("annotations") or {}).get("storageclass.kubernetes.io/is-default-class") == "true",
            "reclaim": o.get("reclaimPolicy"),
            "expansion": bool(o.get("allowVolumeExpansion")),
            "binding": o.get("volumeBindingMode"),
            "parameters": o.get("parameters") or {},
        }
        for o in items(objs.get("storageclasses"))
    ]

    present = {k: v for k, v in comps.items() if v["present"]}
    families_present = {v["family"] for v in present.values()}
    # Expected families live in rubric/profiles/<name>.yaml (the same source evaluate.py uses); a profile with a base inherits from it
    prof = _rubric.load_profile(profile["name"])
    expected = prof.get("expected_families")
    if expected is None and prof.get("base"):
        expected = _rubric.load_profile(prof["base"]).get("expected_families")
    expected = expected or []
    missing_families = [f for f in expected if f not in families_present and f != "pod-identity-or-irsa"]

    inv = {
        "kubegap": __version__,
        "rubric_version": paths.rubric_version(),
        "signatures_version": paths.signatures_version(),
        "context": context,
        "taken_at": taken.isoformat(timespec="seconds"),
        "cluster": {"platform": platform, "platform_reasons": platform_reasons, "server_version": server_version, "server": ctx_info.get("server"), "cluster_name": ctx_info.get("cluster_name"), "eks": eks_facts},
        "profile": profile,
        "node_access": node_access,
        "nodes": nodes,
        "namespaces": {"count": len(ns_names), "names": ns_names, "prod_like": [n for n in ns_names if re.search(r"(^|-)prod($|-)|production", n)], "dev_like": [n for n in ns_names if re.search(r"(^|-)(dev|staging|stage|test)($|-)", n)]},
        "pods": {"count": len(pods), "by_phase": phase_count},
        "workloads": {k: len(items(objs.get(k))) for k in ("daemonsets", "deployments", "statefulsets")},
        "storage_classes": scs,
        "crds": {"count": len(items(objs.get("customresourcedefinitions"))), "groups": sorted({o["spec"]["group"] for o in items(objs.get("customresourcedefinitions"))})},
        "components": comps,
        "components_present": sorted(present.keys()),
        "families_present": sorted(families_present),
        "expected_families": expected,
        "missing_families": missing_families,
        "stores": stores,
        "collectors_enabled": _collectors_enabled(platform, profile["name"], present),
        "fetch_failures": failures,
    }
    (snap / "inventory.json").write_text(json.dumps(inv, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    log.stage("discover", "end", platform=platform, profile=profile["name"], components=len(present))
    return inv


# Platforms that share another platform's collector folder. rke2 is close enough to k3s (same binary layout and systemd units) to reuse k3s-platform.
PLATFORM_COLLECTOR_ALIASES: dict[str, str] = {"rke2": "k3s-platform"}


def platform_collector(platform: str) -> str | None:
    """Folder name of the platform collector for `platform`: `collectors/<platform>-platform/` when that folder exists, else an alias, else None.
    Adding `collectors/gke-platform/` is therefore enough to enable it on GKE; nothing is listed by name here."""
    folder = f"{platform}-platform"
    if (paths.COLLECTORS_DIR / folder).is_dir():
        return folder
    alias = PLATFORM_COLLECTOR_ALIASES.get(platform)
    return alias if alias and (paths.COLLECTORS_DIR / alias).is_dir() else None


def _collectors_enabled(platform: str, profile: str, present: dict) -> list[str]:
    """Decide which collector folders to enable. core always, `<platform>-platform` when that folder exists, the rest by installed component name."""
    enabled = ["core"]
    pc = platform_collector(platform)
    if pc:
        enabled.append(pc)
    enabled += sorted(n for n in present if n not in ("k3s", "rke2", "eks-managed-addons"))
    return enabled
