#!/usr/bin/env python3
"""Turn a real snapshot into a committed test fixture (tests/fixtures/snapshot-<name>/, #145).

Usage: scripts/make-fixture.py <snapshot folder> <destination folder> [--map ~/.kubegap/scrub-map.yaml]

What it does, in this order:
1. Copies the collected inputs and leaves out what summarize, evaluate and render produce (summary.json, findings-draft.json, report.md,
   report-details.md, diff.json, llm/, earlier-reports/, extra/, INCOMPLETE), so the fixture is an input, never an expectation.
2. Trims what no reader uses, mechanically (no reader-specific key lists, so a new reader finds the fields a real snapshot has):
   JSON is written compact; `metadata.managedFields` goes except on ConfigMaps (lib/summaries/hygiene.py reads their change times); CRD
   `spec.versions[].schema` and `additionalPrinterColumns` go (readers take name, group and scope); a string over --max-string
   characters that is a PEM block or has no whitespace (certificates, CSRs, base64 blobs; never a config document, which readers parse)
   becomes `<n chars>`; Polaris results that passed go (lib/summaries/hygiene.py reads failures); each entry of `droppedTargets` in
   prometheus/targets.json becomes `{}` (lib/summaries/observability.py counts them, the count stays); KRR scan `labels` and `annotations` go
   (lib/summaries/resources.py reads object, recommended and warnings); with --log-lines, log files keep only that many lines (the default keeps
   them whole: a cut changes what the signature scan counts).
3. Masks and renames: lib/foundations/mask.mask_text (tokens, keys, account ids; not IP addresses, which readers parse, so the map rewrites them
   to other private addresses), then the name map of scripts/scrub-sample.py when --map is given (the map is yours and stays out of
   the repository), applied to file contents and to paths (a node's log folder carries its name), then the machine's home directory
   and the snapshots root. A JSON file is parsed again after the text pass, so a replacement can never leave an unreadable file.
4. Verifies, unless --no-verify: runs lib/commands/regress on a copy of the source and on the fixture and prints every check whose status differs
   and every finding whose verdict differs per target. A trim that changes a verdict is a trim too far.
5. Prints the size on disk and gzip-compressed (about what git stores). Keep a fixture under 2 MB compressed.
"""

from __future__ import annotations

import argparse
import gzip
import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import importlib

from lib.foundations import mask, yamlite

_scrub_sample = importlib.import_module("scrub-sample")

DERIVED = {"summary.json", "findings-draft.json", "report.md", "report-details.md", "diff.json", "llm", "earlier-reports", "extra", "INCOMPLETE"}
TEXT_SUFFIXES = {".log", ".txt", ".prom", ".csv", ".md", ".yaml", ".yml"}
HOME_RE = re.compile(r"/Users/[A-Za-z0-9._-]+|" + re.escape(str(pathlib.Path.home())))  # the machine's home directory in run.log command lines; not every /home/<x>, which is a container path


def trim_json(rel: str, doc, max_string: int):
    """The mechanical trims of step 2. `rel` is the path inside the snapshot."""

    def blob(v) -> bool:
        return isinstance(v, str) and len(v) > max_string and (v.startswith("-----BEGIN") or not re.search(r"\s", v))

    def shorten(o):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if blob(v):
                    o[k] = f"<{len(v)} chars>"
                else:
                    shorten(v)
        elif isinstance(o, list):
            for v in o:
                shorten(v)

    if rel.startswith("objects/") and isinstance(doc, dict):
        for it in doc.get("items") or []:
            md = it.get("metadata") or {}
            if it.get("kind") != "ConfigMap":
                md.pop("managedFields", None)
            if it.get("kind") == "CustomResourceDefinition":
                for v in (it.get("spec") or {}).get("versions") or []:
                    v.pop("schema", None)
                    v.pop("additionalPrinterColumns", None)
    if rel == "tools/polaris.json" and isinstance(doc, dict):

        def failures_only(results):
            for k in list(results or {}):
                if (results[k] or {}).get("Success"):
                    del results[k]

        for r in doc.get("Results") or []:
            failures_only(r.get("Results"))
            pr = r.get("PodResult")
            if pr:
                failures_only(pr.get("Results"))
                for c in pr.get("ContainerResults") or []:
                    failures_only(c.get("Results"))
    if rel == "prometheus/targets.json" and isinstance(doc, dict) and isinstance(doc.get("data"), dict):
        doc["data"]["droppedTargets"] = [{} for _ in doc["data"].get("droppedTargets") or []]  # lib/summaries/observability.py counts them; the count stays, the labels go
    if rel == "tools/krr.json" and isinstance(doc, dict):
        for s in doc.get("scans") or []:
            o = s.get("object") or {}
            for k in ("labels", "annotations"):  # `warnings` stays: lib/summaries/resources.py keeps them per row and counts the unknown reasons
                o.pop(k, None)
    shorten(doc)
    return doc


def text_pass(text: str, rules: list[tuple[str, str]], roots: list[str]) -> str:
    for r in roots:  # before the name map, which would rewrite the names inside the path and hide it from this replacement
        text = text.replace(r, "<snapshots>")
    text = HOME_RE.sub("/home/user", text)
    text = mask.mask_text(text).text
    return _scrub_sample.scrub(text, rules)


def build(src: pathlib.Path, dst: pathlib.Path, rules: list[tuple[str, str]], *, max_string: int, log_lines: int) -> tuple[int, int]:
    if dst.exists():
        shutil.rmtree(dst)
    roots = [str(src.resolve().parent.parent), str(src.resolve().parent)]
    raw = gz = 0
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src).as_posix()
        if not p.is_file() or rel.split("/")[0] in DERIVED:
            continue
        out = dst / _scrub_sample.scrub(rel, rules)
        out.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".json" or p.name == "run.log":
            if p.suffix == ".json":
                doc = trim_json(rel, json.loads(p.read_text(encoding="utf-8")), max_string)
                text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
                text = text_pass(text, rules, roots)
                json.loads(text)  # a replacement that broke the file is an error here, not in the test
            else:
                lines = p.read_text(encoding="utf-8").splitlines()
                text = text_pass("\n".join(lines), rules, roots) + "\n"
                for ln in text.splitlines():
                    json.loads(ln)
        elif p.suffix in TEXT_SUFFIXES or p.name == "MODE":
            text = p.read_text(encoding="utf-8", errors="replace")
            if p.suffix == ".log" and log_lines:
                text = "\n".join(text.splitlines()[:log_lines]) + ("\n" if text else "")
            text = text_pass(text, rules, roots)
        else:
            raise SystemExit(f"make-fixture: {rel}: no rule for this file type")
        data = text.encode("utf-8")
        out.write_bytes(data)
        raw += len(data)
        gz += len(gzip.compress(data, 6))
    return raw, gz


def verify(src: pathlib.Path, dst: pathlib.Path, rules: list[tuple[str, str]]) -> list[str]:
    """Check statuses of the source snapshot against the fixture, and every finding's verdict per target (targets of the source renamed through
    the same map first), both run through lib/commands/regress on a copy."""
    import tempfile
    from collections import Counter

    from lib.commands import regress

    def verdicts(folder: pathlib.Path, rename):
        with tempfile.TemporaryDirectory() as td:
            fd = json.loads(regress.run(regress.stage(folder, pathlib.Path(td)))["findings.json"])
        return {r["id"]: r["status"] for r in fd["check_results"]}, Counter((f["check"], rename(f["target"] or ""), f["status"]) for f in fd["findings"])

    a, fa = verdicts(src, lambda t: _scrub_sample.scrub(t, rules))
    b, fb = verdicts(dst, lambda t: t)
    out = [f"verify: {cid} {a[cid]} in the source, {b.get(cid)} in the fixture" for cid in a if a[cid] != b.get(cid)]
    out += [f"verify: {check} {target} {status}: {fa[k]} in the source, {fb[k]} in the fixture" for k in sorted(set(fa) | set(fb)) if fa[k] != fb[k] for check, target, status in [k]]
    return out or ["verify: every check has the same status, and every finding the same verdict per target, on the source and on the fixture"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--map", help="name map (format: scripts/scrub-sample.py header); without it names stay")
    ap.add_argument("--max-string", type=int, default=2000, help="strings longer than this become `<n chars>` (default 2000)")
    ap.add_argument("--log-lines", type=int, default=0, help="lines kept per .log file (default: all)")
    ap.add_argument("--no-verify", action="store_true", help="skip the comparison of check statuses between the source and the fixture")
    a = ap.parse_args()
    spec = yamlite.load(pathlib.Path(a.map).read_text(encoding="utf-8")) or {} if a.map else {}
    src, dst = pathlib.Path(a.src), pathlib.Path(a.dst)
    rules = _scrub_sample.build(spec)
    raw, gz = build(src, dst, rules, max_string=a.max_string, log_lines=a.log_lines)
    if not a.no_verify:
        for line in verify(src, dst, rules):
            print(line)
    print(f"{dst}: {raw / 1e6:.1f} MB on disk, {gz / 1e6:.2f} MB gzip-compressed" + (" (over the 2 MB fixture budget)" if gz > 2_000_000 else ""))


if __name__ == "__main__":
    main()
