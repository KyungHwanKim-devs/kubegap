"""End-to-end regression against committed snapshot fixtures (#145): summarize → evaluate → render on `tests/fixtures/snapshot-<name>/`,
compared with the expectation in `tests/fixtures/expected/<variant>/`. `tests/test_regress.py` runs it in CI; `scripts/kubegap regress`
runs it by hand and `--update` rewrites the expectation, which is the only way it changes, so a pull request shows the difference.

A fixture is an input folder made by scripts/make-fixture.py from a real `full` run. The pipeline writes into the snapshot (summary.json,
findings-draft.json, run.log notes, the removal of logs/pods/*.log) and into the context folder next to it (events-history.json, history.csv),
so every run works on a copy placed as <tmp>/<context>/<snapshot>, and the expectation is the first run on a context folder with no history.

Compared: summary.json whole, the check results and findings of findings-draft.json (check, target, status, severity, evidence; `details` and
`rule_hash` are the report's business and the rubric's), and report-details.md in both languages. Normalised before the comparison: the snapshot
path, `generated_at`, and the kubegap version string. The rubric version is not normalised: a rubric change is expected to change the expectation,
in the same pull request. Nothing else is: the expectation written on one Python of the CI matrix must hold on the others, which is why
`summarize_metrics` adds samples with `math.fsum` (3.12 changed how `sum()` adds floats).

A variant is a fixture plus a mutation applied to the copy before the run. `<name>-degraded` takes inputs away from the fixture the way a run loses them
(a forbidden List, no Prometheus, no node access, an object kind the account may not list) and records the loss as collect would. The test checks that
every check whose status changes is skipped with a reason and that the loss reaches summary.json and report section 7-1 (#98). A check that keeps
judging on the emptied summary section and passes is the empty-result policy of #141, measured by comparing the two expectations, not hidden here."""

from __future__ import annotations

import difflib
import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path

from .. import __version__
from ..collection import collect
from ..foundations import paths
from ..foundations.config import Config
from ..foundations.snapshot import check_schema, load_json, write_private
from ..judgement import evaluate
from ..output import render
from ..summaries import summarize

FIXTURES = paths.ROOT / "tests" / "fixtures"
EXPECTED = FIXTURES / "expected"
OUTPUTS = ("summary.json", "findings.json", "report-details.en.md", "report-details.ko.md")
FORBIDDEN = 'Error from server (Forbidden): events is forbidden: User "kubegap" cannot list resource "events" in API group "" at the cluster scope'
GONE_STORES = ("prometheus", "alertmanager")
AWS_STEP_TYPES = ("aws", "cwlogs", "cw-metrics", "alb-metrics")
AWS_DENIED = "An error occurred (AccessDeniedException) when calling the operation: User is not authorized to perform it (the degraded fixture: no IAM policy)"
DENIED_STEM = "networkpolicies.networking.k8s.io"  # the kind the degraded variant takes away: judged by an object-type check (security.networkpolicy-coverage), so the skip reason shows


def fixtures() -> list[Path]:
    return sorted(p for p in FIXTURES.glob("snapshot-*") if p.is_dir())


def degrade(snap: Path) -> None:
    """Take away what a degraded run does not have, and record it the way collect records it (lib/collection/collect: a forbidden List is a failed
    step; a promql step without Prometheus is `error: no Prometheus connection`; an http step without its store is `skipped: no <store> connection`;
    an AWS call refused is a failed step with the AccessDenied text; a node step without a backend is `skipped: no node command backend`; a kind the
    account may not list is `not_permitted` of the dump-all record)."""
    cr = load_json(snap / "collect-result.json")
    inv = load_json(snap / "inventory.json")
    # 1. a forbidden List: the step fails, its file is not written
    (snap / "events.json").unlink()
    cr["core"]["steps"]["events"] = {"ok": False, "items": None, "error": FORBIDDEN}
    # 2. no Prometheus and no Alertmanager: every promql step and every http step of those stores, with its output
    for collector, st in paths.collect_steps():
        rec = (cr.get(collector) or {}).get("steps") or {}
        if st["id"] not in rec:
            continue
        if st["type"] == "promql":
            rec[st["id"]] = {"ok": False, "error": "no Prometheus connection"}
        elif st["type"] == "http" and st.get("store") in GONE_STORES:
            rec[st["id"]] = {"ok": False, "skipped": f"no {st['store']} connection"}
            (snap / st["out"]).unlink(missing_ok=True)
        elif st["type"] == "node":
            rec[st["id"]] = {"ok": False, "skipped": "no node command backend"}
    for f in (snap / "metrics").glob("*.json"):  # the promql outputs; kubectl top and the pod scrapes stay
        f.unlink()
    for k in GONE_STORES:
        inv["stores"].pop(k, None)
    # 3. every AWS call refused (the identity reads the cluster and holds no IAM policy, docs/PERMISSIONS.md): the aws, cwlogs, cw-metrics and alb-metrics steps fail
    #    the way lib/collection/collect/cloud_steps.py run_aws_step records a refusal, and their outputs are gone; discovery's describe-cluster is left as read, so the EKS facts stay
    for collector, st in paths.collect_steps():
        rec = (cr.get(collector) or {}).get("steps") or {}
        if st["id"] in rec and st["type"] in AWS_STEP_TYPES:
            rec[st["id"]] = {"ok": False, "out": None, "error": AWS_DENIED}
    shutil.rmtree(snap / "aws", ignore_errors=True)
    shutil.rmtree(snap / "logs" / "cloudwatch", ignore_errors=True)
    # 4. no node access
    shutil.rmtree(snap / "logs" / "node", ignore_errors=True)
    inv["node_access"] = {
        "method": "none",
        "source": "detected",
        "reasons": ["degraded fixture: no node access"],
        "ssm_registered": [],
        "ssm_unregistered": None,
        "ssm_error": "AccessDeniedException: ssm:DescribeInstanceInformation",
    }  # the list is None when it was not read (lib/collection/discover.py), so eks.ssm-unregistered skips
    # 5. an object kind the account may not list: dump-all records it as not permitted and writes no file
    rec = cr["core"]["steps"]["objects.dump-all"]
    (snap / "objects" / f"{DENIED_STEM}.json").unlink()
    rec["written"] = [s for s in rec["written"] if s != DENIED_STEM]
    rec["fetched_by_discovery"] = [s for s in rec["fetched_by_discovery"] if s != DENIED_STEM]
    rec["not_permitted"] = sorted(set(rec["not_permitted"]) | {DENIED_STEM})
    cr["_summary"] = collect.step_summary(cr, cr["_summary"]["mode"], cr["_summary"]["seconds_total"])
    write_private(snap / "collect-result.json", json.dumps(cr, ensure_ascii=False, indent=1))
    write_private(snap / "inventory.json", json.dumps(inv, ensure_ascii=False, indent=1))


VARIANTS: dict[str, Callable[[Path], None] | None] = {"": None, "-degraded": degrade}


def variants() -> list[tuple[str, Path, Callable[[Path], None] | None]]:
    """(variant name, fixture folder, mutation) for every fixture and every variant."""
    return [(f.name.removeprefix("snapshot-") + suffix, f, mut) for f in fixtures() for suffix, mut in VARIANTS.items()]


def stage(fixture: Path, workdir: Path, mutate: Callable[[Path], None] | None = None) -> Path:
    """Copy the fixture to <workdir>/<context>/<snapshot> and apply the mutation. The context folder is where summarize keeps cross-run state."""
    snap = workdir / "context" / "snapshot"
    shutil.copytree(fixture, snap)
    check_schema(snap)  # a fixture is a snapshot of the current format version, as the CLI would demand (#97)
    if mutate:
        mutate(snap)
    return snap


def run(snap: Path) -> dict[str, str]:
    """summarize → evaluate → render (en, ko) on `snap`; the four outputs as text, normalised."""
    quiet = lambda *a, **k: None  # noqa: E731
    summarize.summarize(snap, echo=quiet)
    evaluate.evaluate(snap, Config(), echo=quiet)
    out: dict[str, str] = {}
    for lang in ("en", "ko"):
        p = render.render_details(snap, language=lang)
        out[f"report-details.{lang}.md"] = p.read_text(encoding="utf-8")
    out["summary.json"] = (snap / "summary.json").read_text(encoding="utf-8")
    fd = load_json(snap / "findings-draft.json")
    kept = {
        "platform": fd.get("platform"),
        "scale": fd.get("scale"),
        "rubric_version": fd.get("rubric_version"),
        "check_results": [{k: r.get(k) for k in ("id", "status", "reason", "counts", "skipped_reason") if k in r} for r in fd.get("check_results") or []],
        "findings": [{k: f.get(k) for k in ("check", "target", "status", "severity_default", "evidence", "source") if k in f} for f in fd.get("findings") or []],
    }
    out["findings.json"] = json.dumps(kept, ensure_ascii=False, indent=1) + "\n"
    return {k: normalise(v, snap) for k, v in out.items()}


def normalise(text: str, snap: Path) -> str:
    """The snapshot path, `generated_at` and the kubegap version, each where it is written (never as a bare substring: `0.1.4` is also inside `10.0.1.42`). The header row is matched under its label in every
    report language (lib/output/render.LABELS): the Korean row kept the version and the first release after the expectation was written failed the comparison."""
    from ..output.render import LABELS  # render imports nothing from here

    text = text.replace(str(snap), "<snapshot>")
    text = re.sub(r'"generated_at": "[^"]*"', '"generated_at": "<generated_at>"', text)
    text = re.sub(r'"kubegap": "[^"]*"', '"kubegap": "<kubegap>"', text)
    key = "kubegap / rubric / signatures"
    labels = "|".join(re.escape(LABELS[lang].get(key, key)) for lang in LABELS)
    return re.sub(r"(\| (?:" + labels + r") \| )" + re.escape(__version__) + " /", r"\1<kubegap> /", text)


def compare(variant: str, outputs: dict[str, str]) -> list[str]:
    """Human-readable differences against tests/fixtures/expected/<variant>/; empty when they match."""
    exp_dir = EXPECTED / variant
    diffs: list[str] = []
    for name in OUTPUTS:
        p = exp_dir / name
        if not p.is_file():
            diffs.append(f"{variant}/{name}: no expectation (run `scripts/kubegap regress --update`)")
            continue
        want = p.read_text(encoding="utf-8")
        if want != outputs[name]:
            d = list(difflib.unified_diff(want.splitlines(), outputs[name].splitlines(), f"expected/{variant}/{name}", f"this run/{name}", lineterm="", n=1))
            diffs.append("\n".join(d[:200]) + (f"\n… {len(d) - 200} more lines" if len(d) > 200 else ""))
    return diffs


def update(variant: str, outputs: dict[str, str]) -> Path:
    exp_dir = EXPECTED / variant
    for name in OUTPUTS:
        write_private(exp_dir / name, outputs[name], mode=0o644)  # a committed file, readable like the rest of the repository
    return exp_dir


# ---------- references/summary-shape.md ----------

SHAPE_DOC = paths.ROOT / "references" / "summary-shape.md"
_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")


def documented_shape(doc: Path = SHAPE_DOC) -> dict[str, set[str]]:
    """{section: first-level keys} from the `## section` headings and the first backticked `section{…}` fragment under each."""
    out: dict[str, set[str]] = {}
    section = None
    for line in doc.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            out[section] = set()
            continue
        if section is None or not line.startswith("`") or not line[1:].startswith(section + "{"):
            continue
        body = line[len(section) + 2 :]
        depth, key, keys = 0, "", []
        for ch in body:
            if ch in "{[(":
                if depth == 0 and key.strip():
                    keys.append(key.strip())
                    key = ""
                depth += 1
            elif ch in "}])":
                depth -= 1
                if depth == 0:
                    key = ""
                if depth < 0:
                    break
            elif ch == "," and depth == 0:
                if key.strip():
                    keys.append(key.strip())
                key = ""
            elif depth == 0:
                key += ch
        if key.strip():
            keys.append(key.strip())
        out[section] = {k.split(" ")[0] for k in keys if _IDENT.match(k.split(" ")[0])}
        section = None  # only the first shape line of a section
    return out


def shape_mismatches(summaries: list[dict], doc: Path = SHAPE_DOC) -> list[str]:
    """Headings that no summary has as a key, summary keys without a heading, and documented first-level keys that no summary's section carries
    (a key one platform writes and another does not, such as the EKS part of `controlplane`, is present in the EKS fixture's summary)."""
    shape = documented_shape(doc)
    out = [f"documented section `{s}` is not a key of any summary.json" for s in shape if not any(s in summ for summ in summaries)]
    out += sorted({f"summary.json key `{k}` has no `## {k}` heading in {doc.name}" for summ in summaries for k in summ if k not in shape})
    for s, keys in shape.items():
        seen: set[str] = set()
        for summ in summaries:
            sec = summ.get(s)
            if isinstance(sec, dict):
                seen |= set(sec)
        out += [f"`{s}.{k}` is documented but no summary has such a key" for k in sorted(keys) if k not in seen]
    return out
