"""The ClusterRole and the IAM policy grant what the code calls and nothing else (#85).

Three sides are compared: the kubectl verbs and `--raw` paths the collectors and lib/ use, the object kinds the code reads,
and the AWS CLI operations it runs, against deploy/permissions/clusterrole.yaml and deploy/permissions/iam-policy.json.
A new collector that needs a verb, a kind or an action outside the files fails here instead of on a user's cluster.
"""

import ast
import json
import re
from pathlib import Path

import pytest

from lib import yamlite

ROOT = Path(__file__).resolve().parent.parent
ROLE_FILE = ROOT / "deploy" / "permissions" / "clusterrole.yaml"
IAM_FILE = ROOT / "deploy" / "permissions" / "iam-policy.json"

KUBECTL_STEP_VERBS = {"get", "top", "logs"}
KUBECTL_LIB_VERBS = {"get", "logs", "api-resources", "version", "config", "auth", "exec"}
RAW_PATHS = (re.compile(r"^/api/v1/nodes/[^/]+/proxy/configz$"), re.compile(r"^/api/v1/namespaces/[^/]+/pods/[^/]+:\d+/proxy/"))


def _role_docs() -> list[dict]:
    return [yamlite.load(doc) for doc in ROLE_FILE.read_text(encoding="utf-8").split("\n---\n") if doc.strip()]


def _role() -> dict:
    return next(d for d in _role_docs() if d.get("kind") == "ClusterRole")


def _collect_steps():
    for f in sorted(ROOT.glob("collectors/*/collect.yaml")):
        for st in yamlite.load_file(f) or []:
            if isinstance(st, dict):
                yield f.parent.name, st


# ---------- what the code asks of the API server ----------


def test_kubectl_steps_use_read_verbs_and_known_raw_paths():
    bad = []
    for coll, st in _collect_steps():
        if st.get("type") != "kubectl":
            continue
        args = [str(a) for a in st.get("args") or []]
        if not args or args[0] not in KUBECTL_STEP_VERBS:
            bad.append(f"{coll}/{st.get('id')}: verb {args[:1]}")
        for i, a in enumerate(args):
            if a == "--raw":
                raw = args[i + 1].replace("{item}", "node-1")
                if not any(rx.search(raw) for rx in RAW_PATHS):
                    bad.append(f"{coll}/{st.get('id')}: --raw {raw}")
    assert bad == []


def _kubectl_literals(source: str, filename: str) -> list[tuple[str, str]]:
    """(first argument, file:line) of every kube.kubectl([...]) / kubectl_json([...]) call whose first argument is a string literal."""
    out = []
    for node in ast.walk(ast.parse(source, filename)):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else None)
        if name not in ("kubectl", "kubectl_json") or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.List) and first.elts and isinstance(first.elts[0], ast.Constant) and isinstance(first.elts[0].value, str):
            out.append((first.elts[0].value, f"{filename}:{node.lineno}"))
    return out


def test_lib_kubectl_calls_use_read_verbs_and_exec_only_in_node_py():
    calls = []
    for f in sorted(ROOT.glob("lib/*.py")):
        calls += _kubectl_literals(f.read_text(encoding="utf-8"), f.name)
    assert calls, "no kubectl calls found; the scanner is broken"
    bad = [c for c in calls if c[0] not in KUBECTL_LIB_VERBS]
    assert bad == []
    execs = [c for c in calls if c[0] == "exec"]
    assert execs and all(c[1].startswith("node.py:") for c in execs), execs


def test_raw_paths_in_lib_are_the_pod_proxy_only():
    raws = []
    for f in sorted(ROOT.glob("lib/*.py")):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if '"--raw"' in line:
                raws.append(f"{f.name}:{n}: {line.strip()}")
    assert len(raws) == 1 and "/api/v1/namespaces/{ns}/pods/{pname}:{st['port']}/proxy" in raws[0], raws


def test_tool_steps_do_not_read_helm_release_secrets():
    """pluto detect-all-in-cluster and kubent's Helm collector list release Secrets; the role forbids Secrets, so the steps use the modes that stay off them."""
    cmds = {st["id"]: [str(a) for a in st.get("cmd") or []] for _c, st in _collect_steps() if st.get("type") == "tool"}
    assert cmds["pluto"][1] == "detect-api-resources"
    assert "--helm3=false" in cmds["kubent"]
    assert cmds["helm-list"][:2] == ["helm", "list"], "helm list is the one documented read of Helm's Secrets"


def test_port_forward_and_popen_live_in_portfwd_only():
    """kubectl port-forward is the one call behind the pods/portforward rule; it runs through subprocess.Popen in lib/portfwd.py and nowhere else."""
    texts = {f.name: f.read_text(encoding="utf-8") for f in ROOT.glob("lib/*.py")}
    runners = {n for n, t in texts.items() if '"port-forward"' in t and "subprocess" in t}  # monitoring.py and prom.py only name the access method
    popen = {n for n, t in texts.items() if "subprocess.Popen" in t}
    assert runners == {"portfwd.py"} and popen == {"portfwd.py"}


# ---------- the ClusterRole ----------


def test_clusterrole_is_get_list_only_except_portforward():
    role = _role()
    bad = []
    for rule in role["rules"]:
        verbs = set(rule.get("verbs") or [])
        resources = rule.get("resources") or []
        if resources == ["pods/portforward"]:
            assert verbs == {"create"} and rule.get("apiGroups") == [""]
            continue
        if "nonResourceURLs" in rule:
            assert verbs == {"get"}
            continue
        if not verbs <= {"get", "list"}:
            bad.append((resources, sorted(verbs)))
    assert bad == []
    assert any(rule.get("resources") == ["pods/portforward"] for rule in role["rules"]), "the port-forward rule is required by lib/portfwd.py"


def test_clusterrole_never_grants_secrets_exec_or_unused_paths():
    text = ROLE_FILE.read_text(encoding="utf-8")
    role = _role()
    resources = {r for rule in role["rules"] for r in (rule.get("resources") or [])}
    assert "secrets" not in resources and "pods/exec" not in resources and "nodes/metrics" not in resources
    assert "watch" not in {v for rule in role["rules"] for v in (rule.get("verbs") or [])}
    urls = {u for rule in role["rules"] for u in (rule.get("nonResourceURLs") or [])}
    assert urls == {"/version", "/api", "/api/*", "/apis", "/apis/*"}
    assert "pods/proxy" in resources and "nodes/proxy" in resources
    assert text.count("kind: ClusterRoleBinding") == 1


def _role_coverage():
    role = _role()
    groups: set[str] = set()
    core: set[str] = set()
    for rule in role["rules"]:
        for g in rule.get("apiGroups") or []:
            if g == "":
                core |= set(rule.get("resources") or [])
            else:
                groups.add(g)
    return groups, core


KIND_RE = re.compile(r"^[a-z][a-z0-9]*(\.[a-z0-9][a-z0-9.-]*)?$")


def _reads_in_module(source: str) -> set[str]:
    """Object kinds a module reads: string constants given to any call whose name contains `objects` (objects(snap, "x"), self.objects("x"),
    snapshot.objects(...)), string constants in a tuple or list iterated in a `for` whose body calls such a function, and the stems of
    literal objects/<x>.json paths."""
    tree = ast.parse(source)
    kinds: set[str] = set()

    def is_objects_call(node):
        if not isinstance(node, ast.Call):
            return False
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
        return "objects" in name

    for node in ast.walk(tree):
        if is_objects_call(node):
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and KIND_RE.match(a.value):
                    kinds.add(a.value)
        if isinstance(node, ast.For) and isinstance(node.iter, (ast.Tuple, ast.List)) and any(is_objects_call(n) for n in ast.walk(node)):
            for e in node.iter.elts:
                if isinstance(e, ast.Constant) and isinstance(e.value, str) and KIND_RE.match(e.value):
                    kinds.add(e.value)
    kinds |= set(re.findall(r"""objects["'\s/]+/?\s*["']?([a-z0-9.-]+)\.json""", source))
    return kinds


def _kinds_the_code_reads() -> set[str]:
    kinds: set[str] = set()
    for f in sorted(ROOT.glob("lib/*.py")):
        kinds |= _reads_in_module(f.read_text(encoding="utf-8"))
    for f in sorted(ROOT.glob("collectors/*/checks.yaml")):
        kinds |= set(re.findall(r"objects/([a-z0-9.-]+)\.json", f.read_text(encoding="utf-8")))
    from lib import discover

    kinds |= set(discover.OBJECT_KINDS)
    return kinds


def test_reader_scanner_sees_the_known_forms():
    src = (
        'objects(snap, "pods")\nself.objects("etcdsnapshotfiles.k3s.cattle.io")\nsnapshot.objects(snap, "nodes")\n'
        'for stem in ("deployments", "scaledjobs.keda.sh"):\n    for o in objects(snap, stem):\n        pass\n'
        'for ns in ("prod", "dev"):\n    pass\n'
        'x = load_json(snap / "objects" / "services.json")\n'
    )
    assert _reads_in_module(src) == {"pods", "etcdsnapshotfiles.k3s.cattle.io", "nodes", "deployments", "scaledjobs.keda.sh", "services"}


# discover names its kinds without the API group (objects/deployments.json); these are the groups behind those names
DISCOVER_GROUPS = {
    "deployments": "apps",
    "daemonsets": "apps",
    "statefulsets": "apps",
    "cronjobs": "batch",
    "jobs": "batch",
    "storageclasses": "storage.k8s.io",
    "customresourcedefinitions": "apiextensions.k8s.io",
    "horizontalpodautoscalers": "autoscaling",
    "ingresses": "networking.k8s.io",
}


def test_every_kind_the_code_reads_is_granted_by_the_clusterrole():
    groups, core = _role_coverage()
    missing = []
    for kind in sorted(_kinds_the_code_reads()):
        if "." in kind:
            group = kind.split(".", 1)[1]
            ok = group in groups
        elif kind in core:
            ok = True
        else:
            ok = DISCOVER_GROUPS.get(kind) in groups
        if not ok:
            missing.append(kind)
    assert missing == []


def test_kinds_read_count_is_sane():
    kinds = _kinds_the_code_reads()
    assert {
        "pods",
        "nodes",
        "deployments",
        "services",
        "configmaps",
        "customresourcedefinitions",
        "prometheusrules.monitoring.coreos.com",
        "apiservices.apiregistration.k8s.io",
        "targetgroupbindings.elbv2.k8s.aws",
        "applications.argoproj.io",
        "scaledjobs.keda.sh",
        "limitranges",
    } <= kinds
    assert len(kinds) >= 60


# Grants that are not object reads: what in the code needs each one
GRANT_READERS = {
    "pods/log": "lib/collect.py component logs: kubectl logs",
    "pods/proxy": "lib/collect.py pod-metrics: GET .../pods/<pod>:<port>/proxy/metrics",
    "nodes/proxy": "collectors/core/collect.yaml kubelet-configz: GET /api/v1/nodes/<node>/proxy/configz",
    "pods/portforward": "lib/portfwd.py: kubectl port-forward svc/<store>",
    "events": "collectors/core/collect.yaml events: kubectl get events -A",
    "metrics.k8s.io": "collectors/core/collect.yaml top.nodes, top.pods: kubectl top",
}


def test_every_clusterrole_grant_has_a_reader():
    """The reverse direction: a group or core resource nobody reads must not be in the role (the way nodes/metrics and watch once were)."""
    groups, core = _role_coverage()
    kinds = _kinds_the_code_reads()
    read_groups = {k.split(".", 1)[1] for k in kinds if "." in k} | {DISCOVER_GROUPS[k] for k in kinds if k in DISCOVER_GROUPS}
    read_core = {k for k in kinds if "." not in k and k not in DISCOVER_GROUPS}
    unused_groups = sorted(g for g in groups if g not in read_groups and g not in GRANT_READERS)
    unused_core = sorted(r for r in core if r not in read_core and r not in GRANT_READERS)
    assert unused_groups == [] and unused_core == []


def test_daemonset_exec_role_matches_the_node_backend():
    from lib import node

    runner = next(c for c in vars(node).values() if isinstance(c, type) and hasattr(c, "DS_NAMESPACE"))
    docs = [yamlite.load(d) for d in (ROOT / "deploy" / "permissions" / "role-daemonset-exec.yaml").read_text(encoding="utf-8").split("\n---\n") if d.strip()]
    role = next(d for d in docs if d.get("kind") == "Role")
    assert role["metadata"]["namespace"] == runner.DS_NAMESPACE
    assert role["rules"] == [{"apiGroups": [""], "resources": ["pods/exec"], "verbs": ["get", "create"]}]
    ds = (ROOT / "deploy" / "node-access" / "daemonset.yaml").read_text(encoding="utf-8")
    assert f"namespace: {runner.DS_NAMESPACE}" in ds


# ---------- the IAM policy ----------

SERVICE_PREFIX = {
    "elbv2": "elasticloadbalancing",
    "service-quotas": "servicequotas",
    "logs": "logs",
    "ce": "ce",
    "sts": "sts",
    "eks": "eks",
    "ec2": "ec2",
    "ssm": "ssm",
    "acm": "acm",
    "dlm": "dlm",
    "backup": "backup",
    "ecr": "ecr",
    "pricing": "pricing",
    "cloudwatch": "cloudwatch",
}
# setup --install-ssm-document runs with the user's own credentials; README says these four are not part of the audit policy
OUTSIDE_POLICY = {"ssm:CreateDocument", "ssm:UpdateDocument", "ssm:UpdateDocumentDefaultVersion", "ssm:ListDocumentVersions"}


def _action(service: str, op: str) -> str:
    return SERVICE_PREFIX[service] + ":" + "".join(w.capitalize() for w in op.split("-"))


def _aws_calls_in_code() -> set[str]:
    actions: set[str] = set()
    for _coll, st in _collect_steps():
        if st.get("type") == "aws":
            args = [str(a) for a in st.get("args") or []]
            actions.add(_action(args[0], args[1]))
    pat = re.compile(r"""aws(?:_json)?\(\s*\[\s*"([a-z0-9-]+)",\s*"([a-z0-9-]+)\"""")
    for f in sorted(ROOT.glob("lib/*.py")):
        for service, op in pat.findall(f.read_text(encoding="utf-8")):
            actions.add(_action(service, op))
    actions.add("logs:StartQuery")  # lib/cwlogs.py run_query passes a prebuilt args list to aws_json, not a literal
    return actions


def _policy_actions() -> set[str]:
    doc = json.loads(IAM_FILE.read_text(encoding="utf-8"))
    return {a for st in doc["Statement"] for a in st["Action"]}


def _allowed(action: str, policy: set[str]) -> bool:
    return any(re.fullmatch(p.replace("*", ".*"), action) for p in policy)


def test_every_aws_call_in_code_is_allowed_by_the_policy():
    policy = _policy_actions()
    missing = sorted(a for a in _aws_calls_in_code() - OUTSIDE_POLICY if not _allowed(a, policy))
    assert missing == []


def test_every_explicit_policy_action_is_called_by_code():
    called = _aws_calls_in_code()
    unused = sorted(a for a in _policy_actions() if "*" not in a and a not in called)
    assert unused == []


def test_policy_wildcards_are_describe_list_only():
    wild = sorted(a for a in _policy_actions() if "*" in a)
    assert wild == ["ec2:Describe*", "eks:Describe*", "eks:List*", "elasticloadbalancing:Describe*"]


def test_aws_call_scanner_sees_known_calls():
    calls = _aws_calls_in_code()
    assert {"sts:GetCallerIdentity", "eks:DescribeCluster", "ecr:DescribeImages", "acm:ListCertificates", "servicequotas:ListServiceQuotas", "ssm:SendCommand"} <= calls


# ---------- dump-all treats a Forbidden kind as not permitted, not as a failure ----------


@pytest.fixture
def fake_kubectl_forbidden(tmp_path, monkeypatch):
    import os
    import stat

    d = tmp_path / "bin"
    d.mkdir()
    table = "".join(c.ljust(13) for c in ("NAME", "SHORTNAMES", "APIVERSION", "NAMESPACED", "KIND")).rstrip() + "\\n"
    table += "".join(c.ljust(13) for c in ("pods", "po", "v1", "true", "Pod")).rstrip() + "\\n"
    table += "".join(c.ljust(13) for c in ("podtemplates", "", "v1", "true", "PodTemplate")).rstrip() + "\\n"
    script = d / "kubectl"
    script.write_text(
        '#!/bin/sh\ncase "$*" in\n  *api-resources*) printf "' + table + '";;\n'
        '  *podtemplates*) echo "Error from server (Forbidden): podtemplates is forbidden: User \\"kubegap\\" cannot list resource \\"podtemplates\\"" >&2; exit 1;;\n'
        '  *) echo \'{"kind":"List","items":[]}\';;\nesac\n'
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{d}{os.pathsep}{os.environ['PATH']}")


def test_dump_all_lists_forbidden_kinds_as_not_permitted(tmp_path, fake_kubectl_forbidden):
    from lib import collect
    from lib.runlog import RunLog

    s = collect.dump_all(None, None, tmp_path, [], 10, RunLog(tmp_path / "run.log"), "core")
    assert s["kinds"] == 1 and s["failed"] == {} and s["not_permitted"] == ["podtemplates"]
    assert (tmp_path / "objects" / "pods.json").is_file() and not (tmp_path / "objects" / "podtemplates.json").exists()
