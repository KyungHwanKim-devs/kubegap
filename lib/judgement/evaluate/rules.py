"""How one rule is evaluated and recorded: the restricted eval, the status of a rule, the finding it writes, the keys a summary item was read by, and the Run that holds one check's state.

Part of the evaluator (lib/judgement/evaluate).
"""

from __future__ import annotations

import fnmatch
import inspect
import re
from collections import Counter
from typing import ClassVar

from . import evidence
from .context import Context

SAFE_BUILTINS = {
    "len": len,
    "any": any,
    "all": all,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "round": round,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "sorted": sorted,
    "isinstance": isinstance,
    "True": True,
    "False": False,
    "None": None,
    "re": re,
}


def eval_expr(expr: str, env: dict):
    return eval(expr, {"__builtins__": SAFE_BUILTINS}, env)


def status(rule: dict, env: dict) -> str:
    """A rule without `expr` never fails (warn-only check); without `warn_expr` it never warns."""
    if rule.get("expr") and eval_expr(rule["expr"], env):
        return "fail"
    if rule.get("warn_expr") and eval_expr(rule["warn_expr"], env):
        return "warn"
    return "pass"


def dev_namespace(target: str, env: dict, globs: list[str]) -> bool:
    """Whether the target lives in a namespace config.yaml `dev_namespaces` names. The checks of rubric/scales.yaml `dev_namespace_disabled_checks` emit nothing there."""
    ns = None
    for key in ("ns",):
        if isinstance(env.get(key), str) and env[key]:
            ns = env[key]
    if ns is None:
        lab = env.get("labels")
        if isinstance(lab, dict) and lab.get("namespace"):
            ns = lab["namespace"]
    if ns is None:
        it = env.get("item")
        if isinstance(it, dict) and isinstance(it.get("namespace"), str):
            ns = it["namespace"]
    if ns is None and "/" in (target or ""):
        ns = target.split("/", 1)[0]
    if not ns:
        return False
    return any(fnmatch.fnmatch(ns, pat) for pat in globs)


def excluded(check_id: str, target: str, platform: dict) -> bool:
    pats = (platform.get("exclude") or {}).get(check_id) or []
    return any(fnmatch.fnmatchcase(target, p) for p in pats)


def finding(check: dict, target: str, status: str, evidence, source: str, extra: dict | None = None) -> dict:
    return {
        "id": f"{check['id']}.{target}",
        "check": check["id"],
        "name": check["name"],
        "area": check["area"],
        "type": check["type"],
        "status": status,
        "severity_default": check["severity_default"],
        "symptom_linked": bool(check.get("symptom_linked")),
        "target": target,
        "evidence": evidence,
        "source": source,
        "collector": check.get("collector"),
        **(extra or {}),
    }


KEY_HARD_RE = re.compile(r"""item\[['"]([^'"]+)['"]\]""")  # both quote styles: the expressions use single quotes, the evidence helpers (formatted Python) double


KEY_SOFT_RE = re.compile(r"""item\.get\(['"]([^'"]+)['"]""")


HELPER_CALL_RE = re.compile(r"\b_([a-z0-9_]+_text)\(")


def expression_texts(check: dict) -> str:
    """The rule, target and evidence of a check as one text to scan for the `item` keys they read, with the source of every evidence helper the
    evidence calls (`_n_plus_one_text(item)` reads its keys inside lib/judgement/evaluate/evidence.py) appended, so a key renamed in a summary module is still
    found by selftest's audit against a real snapshot (#24)."""
    rule = check.get("rule") or {}
    texts = " ".join(str(x) for x in (rule.get("expr"), rule.get("warn_expr"), check.get("target"), check.get("evidence")) if x)
    for name in HELPER_CALL_RE.findall(texts):
        fn = getattr(evidence, name, None)
        if fn is not None:
            texts += " " + inspect.getsource(fn)
    return texts


def referenced_keys(check: dict) -> set[str]:
    """The `item` keys a summary check's expressions read: `item['k']` and `item.get('k')` across rule, target and evidence. selftest audits these against a real summary; `details` keeps exactly these."""
    texts = expression_texts(check)
    return set(KEY_HARD_RE.findall(texts)) | set(KEY_SOFT_RE.findall(texts))


class ItemRecorder(dict):
    """A summary or inventory item that remembers which top-level keys the rule, target, evidence and the helpers they call actually read. `details` keeps exactly those keys,
    so a helper such as `_oom_text(item)` that reads `last_kill` leaves `last_kill` in the finding, which a regex over the expression text could never know. Iterating the whole
    item (`str(item)`, `item.items()`) counts as reading every key."""

    def __init__(self, data: dict):
        super().__init__(data)
        self.read: set[str] = set()
        self.read_all = False

    def __getitem__(self, k):
        self.read.add(k)
        return super().__getitem__(k)

    def get(self, k, default=None):
        self.read.add(k)
        return super().get(k, default)

    def __contains__(self, k):
        self.read.add(k)
        return super().__contains__(k)

    def _all(self):
        self.read_all = True

    def items(self):
        self._all()
        return super().items()

    def values(self):
        self._all()
        return super().values()

    def __iter__(self):
        self._all()
        return super().__iter__()

    def __repr__(self):
        self._all()
        return super().__repr__()

    def kept(self) -> dict:
        if self.read_all:
            return dict(self)
        return {k: super(ItemRecorder, self).__getitem__(k) for k in sorted(self.read) if dict.__contains__(self, k)}  # sorted: `read` is a set, and its order would follow the hash seed into findings-draft.json and the report


def details(check: dict, env: dict) -> dict | None:
    """The material the rule judged, kept whole on the finding (#64). The evidence is one line for a table and may cut a list; `details` is where the rest lives.
    summary and inventory checks: the item's keys that were actually read while judging it (ItemRecorder), never a key the check did not read.
    metric checks: labels and the value, or every joined value. object checks: namespace, name and kind. Checks without an item (absence, cluster-level object checks) carry none."""
    item = env.get("item")
    if isinstance(item, ItemRecorder):
        kept = item.kept()
        return {"key": env.get("key"), "item": kept} if "key" in env else kept
    if isinstance(item, dict):
        keys = referenced_keys(check)
        kept = {k: item[k] for k in keys if k in item} if keys else item
        return {"key": env.get("key"), "item": kept} if "key" in env else kept
    if item is not None and "key" in env:
        return {"key": env.get("key"), "item": item}
    if isinstance(env.get("labels"), dict):
        out: dict = {"labels": env["labels"]}
        if isinstance(env.get("v"), dict):
            out["values"] = env["v"]
        elif "value" in env:
            out["value"] = env["value"]
        return out
    obj = env.get("obj")
    if isinstance(obj, dict):
        return {"namespace": env.get("ns"), "name": env.get("name"), "kind": obj.get("kind")}
    return None


class Run:
    """Mutable state of one check evaluation shared by the type handlers: the check, its thresholds, the collected findings and status counts.

    `emit()` is the single place where a rule is applied to one target, so exclusions (platform `exclude`, dev namespaces) and the merging of
    several instances of one target (Job pods of a CronJob, replicas) behave the same for every check type."""

    _ORDER: ClassVar[dict[str, int]] = {"fail": 0, "warn": 1}

    def __init__(self, check: dict, cx: Context, thresholds: dict):
        self.check, self.cx, self.thresholds = check, cx, thresholds
        self.rule = check.get("rule") or {}
        self.base_env = {**cx.helpers(), **thresholds}
        self.findings: list[dict] = []
        self.counts: Counter = Counter()
        self._by_target: dict[str, dict] = {}
        self.gone_nodes: set[str] = set()
        self.skipped_reasons: Counter = Counter()

    def emit(self, env: dict, default_target: str, source: str) -> None:
        check, cx = self.check, self.cx
        target = str(eval_expr(check["target"], env)) if check.get("target") else default_target
        if excluded(check["id"], target, cx.platform) or (cx.dev_namespaces and check["id"] in cx.dev_disabled and dev_namespace(target, env, cx.dev_namespaces)):
            self.counts["excluded"] += 1
            return
        if self.rule.get("needs") and not eval_expr(self.rule["needs"], env):
            # The rule says what it needs to judge (`needs`); without it the target is not judged, never passed. Counted and named in the result so the report says "N of M not judged: <reason>"
            self.counts["skipped"] += 1
            self.skipped_reasons[self.rule.get("needs_reason") or f"needs {self.rule['needs']}"] += 1
            return
        st = status(self.rule, env)
        self.counts[st] += 1
        if st not in ("fail", "warn"):
            return
        ev = eval_expr(check["evidence"], env) if check.get("evidence") else None
        det = details(check, env)
        if target in self._by_target:
            # When several pods of one workload (Job pods of a CronJob, replicas) map to the same target, merge their evidence into one finding
            f = self._by_target[target]
            f["instances"] = f.get("instances", 1) + 1
            if isinstance(f["evidence"], list):
                f["evidence"].append(ev)
            else:
                f["evidence"] = [f["evidence"], ev]
            if det is not None:
                prev = f.get("details")
                f["details"] = [d for d in ((prev if isinstance(prev, list) else [prev]) + [det]) if d is not None]
            if self._ORDER[st] < self._ORDER[f["status"]]:
                f["status"] = st
            return
        f = finding(check, target, st, ev, source, {"details": det} if det is not None else None)
        self._by_target[target] = f
        self.findings.append(f)

    def gone_node(self, name: str) -> None:
        """A series of a node that is no longer in the cluster: not judged, counted, and named in the check's result so the report can say the node left within the window."""
        self.gone_nodes.add(name)
        self.counts["gone_node"] += 1

    def done(self) -> dict:
        reasons = "; ".join(f"{r} ({n})" if n > 1 else r for r, n in self.skipped_reasons.most_common())
        if self.counts.get("skipped") and not any(self.counts.get(k) for k in ("pass", "fail", "warn", "excluded", "gone_node")):
            return {**self.skip(f"nothing to judge: {reasons}"), "counts": dict(self.counts)}  # every target lacked what the rule needs: the check is skipped, not passed
        out = {"status": "done", "counts": dict(self.counts), "findings": self.findings}
        if self.gone_nodes:
            out["gone_nodes"] = sorted(self.gone_nodes)
        if self.counts.get("skipped"):
            out["skipped_reason"] = reasons  # some targets were judged, these were not; render lists them in section 7-5
        return out

    @staticmethod
    def skip(reason: str) -> dict:
        return {"status": "skip", "reason": reason, "counts": {}, "findings": []}
