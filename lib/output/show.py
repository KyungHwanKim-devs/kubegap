"""`kubegap show`: what an agent reads a snapshot through.

The files of a snapshot are megabytes of JSON. An agent that opens them by hand reads a part and cannot know what the part left out; a
report once said 11 workloads where there were 15 that way. These views print a bounded amount and always say the whole first: how many
there are, how many are shown, and how to see the rest. Nothing is cut silently.

    kubegap show findings [--severity S] [--status fail|warn] [--area A] [--check ID]
    kubegap show finding <id | check id | prefix*>
    kubegap show tables
    kubegap show table <dotted path into the summary> [--where key=value] [--field name] [--offset N] [--limit N] [--all]
    kubegap show object <kind> <namespace/name | name>
    kubegap show learn <topic | check id>

Every function returns text. Same snapshot, same arguments, same text.
"""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path

from ..foundations import rubric
from ..foundations.snapshot import load_json

ROWS = 20  # rows of a table shown without --all
INLINE = 5  # items of a list inside a row shown before "and N more"
SEVERITIES = ("critical", "high", "medium", "low", "info")


class ShowError(Exception):
    pass


def _findings(snap: Path) -> tuple[dict, list[dict]]:
    fd = load_json(snap / "findings-draft.json")
    if not fd:
        raise ShowError(f"{snap / 'findings-draft.json'} does not exist; run `kubegap evaluate` first")
    return fd, [f for f in fd.get("findings") or [] if f.get("status") in ("fail", "warn")]


def _counts(found: list[dict]) -> str:
    parts = []
    for st in ("fail", "warn"):
        by = {s: sum(1 for f in found if f["status"] == st and f["severity_default"] == s) for s in SEVERITIES}
        parts.append(f"{st} {sum(by.values())} (" + ", ".join(f"{s} {n}" for s, n in by.items() if n) + ")")
    return ", ".join(parts).replace(" ()", "")


def brief(value, n: int = INLINE) -> str:
    """A value on one line. A list longer than `n` shows its first `n` and how many more there are; nothing is cut without saying so."""
    if isinstance(value, list):
        head = json.dumps(value[:n], ensure_ascii=False, default=str)
        return head if len(value) <= n else f"{len(value)} items: {head[:-1]}, … and {len(value) - n} more]"
    if isinstance(value, dict):
        keys = list(value)
        inner = ", ".join(f"{k}: {brief(value[k], 3)}" for k in keys[:n])
        return "{" + inner + (f", … and {len(keys) - n} more keys" if len(keys) > n else "") + "}"
    return json.dumps(value, ensure_ascii=False, default=str)


def findings(snap: Path, *, severity: str | None = None, status: str | None = None, area: str | None = None, check: str | None = None) -> str:
    """The findings grouped by check, the most severe first. Each group says how many targets it has and names a few of them."""
    fd, found = _findings(snap)
    out = [f"findings of {snap.name} (scale {(fd.get('scale') or {}).get('name')}): {_counts(found)}"]
    keep = [f for f in found if (not severity or f["severity_default"] == severity) and (not status or f["status"] == status) and (not area or f.get("area") == area) and (not check or f.get("check") == check)]
    said = [f"{k} {v}" for k, v in (("severity", severity), ("status", status), ("area", area), ("check", check)) if v]
    if said:
        out.append(f"filter: {', '.join(said)} → {len(keep)} of {len(found)}")
    groups: dict[str, list[dict]] = {}
    for f in keep:
        groups.setdefault(f["check"], []).append(f)
    order = sorted(groups.items(), key=lambda kv: (min(SEVERITIES.index(f["severity_default"]) for f in kv[1]), 0 if any(f["status"] == "fail" for f in kv[1]) else 1, -len(kv[1]), kv[0]))
    out.append(f"{len(order)} checks. One line each: check, severity, fail/warn counts, nature, name; then the targets.")
    for cid, fs in order:
        sev = min((f["severity_default"] for f in fs), key=SEVERITIES.index)
        n_fail, n_warn = sum(1 for f in fs if f["status"] == "fail"), sum(1 for f in fs if f["status"] == "warn")
        extra = " overdue" if any(f.get("overdue") for f in fs) else ""
        out.append(f"\n{cid}  [{sev}] fail {n_fail} warn {n_warn}  {fs[0].get('nature', 'state')}{extra}  — {fs[0].get('name')}")
        targets = [f"{f['target']}({f['status']})" for f in sorted(fs, key=lambda f: (f["status"] != "fail", str(f["target"])))]
        out.append("  targets " + (", ".join(targets) if len(targets) <= INLINE else f"{len(targets)}: " + ", ".join(targets[:INLINE]) + f", … and {len(targets) - INLINE} more (kubegap show finding '{cid}.*')"))
    out.append("\nOne finding with its evidence, the rows it was judged from and where the raw object is: kubegap show finding <check>.<target>")
    return "\n".join(out)


def _match(found: list[dict], ident: str) -> list[dict]:
    exact = [f for f in found if f["id"] == ident]
    if exact:
        return exact
    if ident.endswith("*"):
        return [f for f in found if fnmatch.fnmatchcase(f["id"], ident)]
    return [f for f in found if f.get("check") == ident]


def finding(snap: Path, ident: str, *, limit: int = 5, all_: bool = False) -> str:
    """One finding in full: what was judged, the evidence, the whole material the rule saw (`details`), why it matters, and where to look
    further. A check id or a prefix ending in `*` gives the findings it matches: how many, and the first few in full."""
    fd, found = _findings(snap)
    hits = _match(found, ident)
    if not hits:
        near = sorted({f["check"] for f in found if ident.split(".")[0] in f["check"]})
        raise ShowError(f"no finding matches {ident!r}. " + (f"Checks of that area with findings: {brief(near, 12)}" if near else "See `kubegap show findings`."))
    shown_ = hits if all_ else hits[:limit]
    out = [f"{len(hits)} finding{'s' if len(hits) != 1 else ''} match {ident!r}" + (f"; showing the first {len(shown_)} (--all for every one). All ids: {brief([f['id'] for f in hits], 12)}" if len(shown_) < len(hits) else "")]
    topics = {t["topic"]: t for t in fd.get("learn") or []}
    for f in shown_:
        out += ["", f"== {f['id']}", f"status {f['status']}, severity {f['severity_default']}, {f.get('nature', 'state')}" + (", overdue" if f.get("overdue") else "") + f"; check: {f.get('name')}"]
        out.append(f"evidence: {f.get('evidence')}")
        if f.get("thresholds"):
            out.append(f"thresholds in force: {json.dumps(f['thresholds'], ensure_ascii=False)}")
        if f.get("details") is not None:
            out.append("judged from (everything the rule saw):")
            out.append(json.dumps(f["details"], ensure_ascii=False, indent=1, default=str))
        for key in ("why", "suggest", "measured"):
            if f.get(key):
                out.append(f"{key}: {' '.join(str(f[key]).split())}")
        if f.get("source"):
            out.append(f"source: {f['source']}" + (f"  (kubegap show table {str(f['source']).split(':', 1)[1]})" if str(f["source"]).startswith("summary.json:") else ""))
        mine = [name for name, t in topics.items() if f.get("check") in (t.get("checks") or [])]
        if mine:
            out.append(f"learn topic: {', '.join(mine)}  (kubegap show learn {mine[0]})")
    return "\n".join(out)


def _resolve(doc, path: str):
    cur = doc
    for part in [p for p in path.split(".") if p]:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            where = list(cur) if isinstance(cur, dict) else f"a list of {len(cur)}" if isinstance(cur, list) else type(cur).__name__
            raise ShowError(f"{part!r} is not in {path!r}. There: {brief(where, 30) if isinstance(where, list) else where}")
    return cur


def _size(v) -> str:
    if isinstance(v, list):
        return f"list of {len(v)}" + (" rows" if v and isinstance(v[0], dict) else "")
    if isinstance(v, dict):
        return f"{len(v)} keys"
    return brief(v)


def tables(snap: Path) -> str:
    """The sections of the summary and what each holds, two levels deep, with sizes."""
    summary = load_json(snap / "summary.json")
    if not summary:
        raise ShowError(f"{snap / 'summary.json'} does not exist; run `kubegap summarize` first")
    out = ["summary of " + snap.name + ": section, then its keys with their size. A list of rows is a table: kubegap show table <section>.<key>"]
    for sec, body in summary.items():
        if not isinstance(body, dict):
            continue
        out.append(f"\n{sec}")
        for k, v in body.items():
            out.append(f"  {sec}.{k}: {_size(v)}")
            if isinstance(v, dict):
                rows = [(k2, v2) for k2, v2 in v.items() if isinstance(v2, list) and v2 and isinstance(v2[0], dict)]
                out += [f"    {sec}.{k}.{k2}: {_size(v2)}" for k2, v2 in rows]
    return "\n".join(out)


def table(snap: Path, path: str, *, where: list[str] | None = None, field: str | None = None, offset: int = 0, limit: int = ROWS, all_: bool = False) -> str:
    """One value of the summary. A list of rows prints how many rows there are, then `limit` of them from `offset`, one per line, with the
    long lists inside a row shortened and counted. `--where key=value` keeps the rows whose key has that value; `--field name` prints that
    one field of each kept row whole."""
    summary = load_json(snap / "summary.json")
    if not summary:
        raise ShowError(f"{snap / 'summary.json'} does not exist; run `kubegap summarize` first")
    value = _resolve(summary, path)
    if not isinstance(value, list):
        if isinstance(value, dict):
            return f"{path}: {len(value)} keys\n" + "\n".join(f"  {k}: {_size(v) if isinstance(v, (list, dict)) else brief(v)}" for k, v in value.items())
        return f"{path}: {brief(value)}"
    rows = value
    total = len(rows)
    said = [f"{path}: {total} {'rows' if rows and isinstance(rows[0], dict) else 'items'}"]
    for cond in where or []:
        if "=" not in cond:
            raise ShowError(f"--where takes key=value, got {cond!r}")
        k, want = cond.split("=", 1)
        rows = [r for r in rows if isinstance(r, dict) and str(r.get(k)) == want]
        said.append(f"where {k}={want}: {len(rows)} of {total}")
    part = rows if all_ else rows[offset : offset + limit]
    if len(part) < len(rows):
        said.append(f"showing {offset + 1}–{offset + len(part)} of {len(rows)} (--offset {offset + len(part)} for the next, --all for every row)")
    out = ["; ".join(said)]
    for r in part:
        if field is not None:
            if not isinstance(r, dict) or field not in r:
                raise ShowError(f"field {field!r} is not in the rows of {path}. Fields: {brief(sorted(r) if isinstance(r, dict) else [], 30)}")
            v = r[field]
            out.append(f"{field} ({_size(v) if isinstance(v, (list, dict)) else 'value'}): " + json.dumps(v, ensure_ascii=False, default=str))
        elif isinstance(r, dict):
            out.append("- " + ", ".join(f"{k}: {brief(v)}" for k, v in r.items()))
        else:
            out.append("- " + brief(r))
    if field is None and any(isinstance(r, dict) and any(isinstance(v, list) and len(v) > INLINE for v in r.values()) for r in part):
        out.append("\nA list inside a row is shortened above and counted. To see one whole: --where <key>=<value> --field <name>")
    return "\n".join(out)


def object_(snap: Path, kind: str, name: str) -> str:
    """One raw object as collected (Secret and ConfigMap values are never in a snapshot). `name` is `namespace/name`, or the name alone for a
    cluster-scoped kind."""
    folder = snap / "objects"
    if not folder.is_dir():
        raise ShowError(f"{snap.name} holds no raw objects (a daily snapshot keeps the summary and the findings only)")
    stems = sorted(p.stem for p in folder.glob("*.json"))
    match = [s for s in stems if s == kind or s.split(".")[0] == kind or s.split(".")[0] == kind + "s"]
    if not match:
        raise ShowError(f"no object file for kind {kind!r}. Kinds collected: {brief(stems, 200)}")
    ns, _, nm = name.rpartition("/")
    for stem in match:
        for o in (load_json(folder / f"{stem}.json") or {}).get("items") or []:
            md = o.get("metadata") or {}
            if md.get("name") == nm and (md.get("namespace") or "") == ns:
                return f"{stem} {name} ({snap.name}/objects/{stem}.json)\n" + json.dumps(o, ensure_ascii=False, indent=1, default=str)
    names = sorted(((o.get("metadata") or {}).get("namespace") or "") + "/" + (o.get("metadata") or {}).get("name", "") for stem in match for o in (load_json(folder / f"{stem}.json") or {}).get("items") or [])
    raise ShowError(f"{kind} {name!r} is not in the snapshot. {len(names)} objects of that kind: {brief([n.lstrip('/') for n in names], 30)}")


def learn(snap: Path | None, ident: str) -> str:
    """A learn topic whole: how the thing works and where that was read, how it is watched, how it is solved at each scale, cases, reading.
    `ident` is a topic name or the id of a check the topic covers."""
    topics, _errs = rubric.load_learn()
    hit = next((t for t in topics if t["topic"] == ident or ident in (t.get("checks") or [])), None)
    if not hit:
        raise ShowError(f"no learn topic named {ident!r} and none covers a check of that id. Topics: {brief(sorted(t['topic'] for t in topics), 80)}")
    return json.dumps(hit, ensure_ascii=False, indent=1)
