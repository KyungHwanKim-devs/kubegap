"""The full report: assembled from what the agent that analysed the run wrote, with the parts only code can vouch for added.

The agent writes three kinds of file under `<snapshot>/report/`:

    outline.json     what goes where and which findings stand behind each entry (lib/output/outline.py)
    overview.md      the sections it writes in prose, each under its `## ` heading: what is broken now (only when something is), what
                     already happened, the next largest problems, since the previous report
    problem-N.md     one file per problem of the outline, starting with `## N. <title>` and holding the six sections

One agent writes all of it, with everything it read still in its context, so the same thing is not counted two ways in two places. No
other agent is started from here: where an independent reading is wanted, the session asks its own host for a subagent
(references/full-<language>.md).

`problems_with` names what is wrong with those files; `assemble` builds report.md. The titles of the first screen, of the headings and of
the list of ids at the end all come from the outline, and a file whose heading differs from the outline is refused, so a title cannot
say one thing on the first screen and another above its section. Code writes: the first screen, the cluster at a glance, the period, the
advice table, what changed because kubegap's criteria changed, findings the user decided not to fix, what is coming up, each area in one
line, the limits of the run, the numbers, the ids.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..foundations import paths
from ..foundations.snapshot import load_json
from . import glossary as _glossary
from . import outline as _outline
from . import parts as _parts
from . import sections as _sections
from .render import table

DIR = "report"
# a sentence that ends in "~요" (사라져요, 있어요, 이에요); "~세요", "~까요" and "~나요" are requests and questions and stay
HAEYO = re.compile(r"[가-힣]*[가-힣](?<![세까나])요(?=[.!]|\s*$)", re.MULTILINE)
_H2 = re.compile(r"^## (.+?)\s*$", re.MULTILINE)


class ReportError(Exception):
    pass


def _read(snap: Path, name: str) -> str | None:
    p = snap / DIR / name
    return p.read_text(encoding="utf-8") if p.is_file() else None


def split_sections(text: str) -> dict[str, str]:
    """`## heading` -> the text under it, for the headings outside code blocks."""
    bare = _parts._FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    marks = [(m.start(), m.end(), m.group(1)) for m in _H2.finditer(bare)]
    return {name: text[end : (marks[i + 1][0] if i + 1 < len(marks) else len(text))].strip() for i, (_start, end, name) in enumerate(marks)}


def allowed_urls(snap: Path) -> set[str]:
    """Every address a report of this run may carry: those of the learn topics of its findings and the public cases of its checks, which someone
    opened, and the repositories this cluster's Argo CD applications point at, which the snapshot holds. Any other was written from memory."""
    fd = load_json(snap / "findings-draft.json") or {}
    out: set[str] = set()
    for t in fd.get("learn") or []:
        for key in ("sources", "reading", "cases"):
            out |= {str(x.get("url")).rstrip("/") for x in t.get(key) or [] if isinstance(x, dict) and x.get("url")}
    for f in fd.get("findings") or []:
        out |= {str(c.get("url")).rstrip("/") for c in f.get("cases") or [] if isinstance(c, dict) and c.get("url")}
    # The repository an Argo CD application points at is this cluster's own data, read from the snapshot: the guide tells the writer to name it
    # where a change has to be made (`declared in`), and the first English full report was refused for doing so.
    apps = (((load_json(snap / "summary.json") or {}).get("argocdctl") or {}).get("applications") or {}).get("rows") or []
    for a in apps:
        u = str(a.get("repo_url") or "").rstrip("/") if isinstance(a, dict) else ""
        if u:
            out |= {u, u.removesuffix(".git")}
    return out


def _h3_titles(text: str) -> list[str]:
    return _parts._H3.findall(_parts._FENCE.sub("", text or ""))


def problems_with(snap: Path, language: str) -> list[str]:
    """Everything that keeps the report from being assembled or that a reader should not get, one line each, worded for the agent that
    wrote the files: the outline's promises, a missing file or section, a heading that differs from the outline, an address nobody opened,
    the conversational sentence ending, a term the glossary avoids."""
    h = _parts.HEADINGS[language]
    out_ = _outline.load(snap)
    if not out_:
        return [f"{snap / _outline.PATH} does not exist; write the outline first (references/full-{language}.md)"]
    out = _outline.check(out_, snap)
    overview = _read(snap, "overview.md")
    if overview is None:
        return [*out, f"{DIR}/overview.md does not exist"]
    secs = split_sections(overview)
    for name in (h["happened"], h["next"]):
        if name not in secs:
            out.append(f"{DIR}/overview.md: no `## {name}` section")
    for key, heading in (("broken_now", h["broken"]), ("happened", h["happened"])):
        want = [str(e.get("title")) for e in out_.get(key) or [] if isinstance(e, dict)]
        got = _h3_titles(secs.get(heading, ""))
        if want and heading not in secs:
            out.append(f"{DIR}/overview.md: the outline has {key} entries but there is no `## {heading}` section")
        elif sorted(want) != sorted(got):
            out.append(f"{DIR}/overview.md `## {heading}`: its `### ` headings must be the outline's {key} titles, one each. Outline: {want}; headings: {got}")
    texts = [("overview.md", overview)]
    for n, p in enumerate(out_.get("problems") or [], 1):
        text = _read(snap, f"problem-{n}.md")
        if text is None:
            out.append(f"{DIR}/problem-{n}.md does not exist (the outline has {len(out_.get('problems') or [])} problems)")
            continue
        first = text.lstrip().splitlines()[0] if text.strip() else ""
        if first.strip() != f"## {n}. {p.get('title')}":
            out.append(f"{DIR}/problem-{n}.md must start with `## {n}. {p.get('title')}` (the outline's title); it starts with {first.strip()!r}. Change whichever is wrong, so both say the same")
        found = [x for x in _h3_titles(text) if x in h["sections"]]
        if found != h["sections"]:
            out.append(f"{DIR}/problem-{n}.md needs these `### ` sections in this order: {', '.join(h['sections'])} (found: {', '.join(found) or 'none'})")
        texts.append((f"problem-{n}.md", text))
    extra = sorted(p.name for p in (snap / DIR).glob("problem-*.md") if p.name not in {f"problem-{n}.md" for n in range(1, len(out_.get("problems") or []) + 1)})
    if extra:
        out.append(f"{DIR}/: {', '.join(extra)} has no problem in the outline; remove the file or add the problem")
    allowed = allowed_urls(snap)
    terms = _glossary.load(language)
    for name, text in texts:
        prose = _parts._FENCE.sub("", text)
        for u in sorted(_parts._urls(prose)):
            if u.rstrip("/") not in allowed:
                out.append(f"{DIR}/{name}: the address {u} is not in a learn topic or a case of this run's findings (kubegap show learn <topic>); an address is not written from memory")
        if language == "ko":
            for m in HAEYO.finditer(re.sub(r"`[^`]*`", "", prose)):
                out.append(f"{DIR}/{name}: a sentence ends in 해요체 ({m.group(0)}); the report is written in 합니다체")
        out += [f"{DIR}/{name}: {hit}" for hit in _glossary.find(text, terms)]
    return out


def first_screen(out_: dict, snap: Path, language: str) -> str:
    """The lines a reader sees first, from the outline's titles (the same titles the headings must carry)."""
    h = _parts.HEADINGS[language]
    titles = {k: [str(e.get("title")) for e in out_.get(k) or [] if isinstance(e, dict) and e.get("title")] for k in ("broken_now", "happened", "problems")}
    lines = [
        f"{h['first_broken']}: " + (" · ".join(titles["broken_now"]) or h["none"]),
        f"{h['first_problems'].format(n=len(titles['problems']))}: " + " ".join(f"{_parts.CIRCLED[i]} {t}" for i, t in enumerate(titles["problems"][: len(_parts.CIRCLED)])),
        f"{h['first_happened']}: " + (" · ".join(titles["happened"]) or h["none"]),
    ]
    scale = (load_json(snap / "findings-draft.json") or {}).get("scale") or {}
    if scale.get("name"):
        lines.append(f"{h['first_scale']}: {_sections.SCALE_WORD[language].get(scale['name'], scale['name'])}")
    return "\n\n".join(lines)


def _period(snap: Path, h: dict) -> tuple[str, bool]:
    prev = paths.previous_snapshot(snap)
    if not prev:
        return h["period_none"], False
    start = _parts._when((load_json(prev / "inventory.json") or {}).get("taken_at"))
    end = _parts._when((load_json(snap / "inventory.json") or {}).get("taken_at"))
    return h["period"].format(start=start, end=end), True


def assemble(snap: Path, language: str, rubric: str, version: str, skipped: list[dict] | None = None) -> str:
    """report.md from the agent's files and the snapshot. Call `problems_with` first; this assumes the files are there and consistent."""
    h = _parts.HEADINGS[language]
    out_ = _outline.load(snap)
    inv = load_json(snap / "inventory.json") or {}
    secs = split_sections(_read(snap, "overview.md") or "")
    cluster = inv.get("cluster") or {}
    period, has_base = _period(snap, h)
    parts_: list[str] = [
        f"# {cluster.get('cluster_name') or inv.get('context') or snap.parent.name} — full {h['audit']}, {_parts._when(inv.get('taken_at')) or snap.name}",
        first_screen(out_, snap, language),
        _parts.glance(snap, h),
    ]
    if out_.get("broken_now"):
        parts_.append(f"## {h['broken']}\n\n{secs.get(h['broken'], '')}")
    parts_.append(f"## {h['happened']}\n\n{period}\n\n{secs.get(h['happened']) or h['none']}")
    parts_ += [(_read(snap, f"problem-{n}.md") or "").strip() for n in range(1, len(out_.get("problems") or []) + 1)]
    parts_.append(f"## {h['next']}\n\n{secs.get(h['next']) or h['none']}")
    parts_.append(_sections.declined(snap, language))
    since = [f"## {h['since']}", ""]
    if has_base:
        sl = out_.get("since_last") or {}
        rows = [[r.get("problem"), h["done"], r.get("proof")] for r in sl.get("done") or [] if isinstance(r, dict)] + [[r.get("problem"), h["not_done"], r.get("proof")] for r in sl.get("not_done") or [] if isinstance(r, dict)]
        if rows:
            since += [table([h["prev_work"], h["state"], h["proof"]], rows), ""]
        since += [secs.get(h["since"]) or h["none"], "", *_parts.criteria_changes(snap, h)]
    else:
        since.append(h["period_none"])
    parts_.append("\n".join(since).rstrip())
    up = [[u.get("when"), u.get("what"), u.get("source") or ""] for u in out_.get("upcoming") or [] if isinstance(u, dict) and u.get("what")]
    if up:
        parts_.append(f"## {h['upcoming']}\n\n" + table([h["when"], h["what"], h["source"]], up))
    summary = out_.get("area_summary") or {}
    parts_.append(f"## {h['areas']}\n\n" + table([h["area"], h["what"]], [[_parts.AREA_WORD.get(h["areas"], {}).get(a, a), summary.get(a) or h["none"]] for a in _outline.AREAS]))
    parts_ += [_sections.limits(out_, snap, language, skipped), _sections.numbers(snap, language, out_)]
    ids = [f"- {e.get('title')}: " + ", ".join(f"`{i}`" for i in _outline._ids(e)) for k in ("broken_now", "happened", "problems") for e in out_.get(k) or [] if isinstance(e, dict) and _outline._ids(e)]
    tail = f"{h['details']}: [`report-details.md`](report-details.md) · kubegap {version}, rubric {rubric} · {h['snapshot']} `{snap}`"
    body = _parts.space_blocks("\n\n".join(p for p in parts_ if p))
    return body + "\n\n" + (f"{h['checks']}:\n\n" + "\n".join(ids) + "\n\n" if ids else "") + tail + "\n"
