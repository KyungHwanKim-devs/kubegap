"""The glossary of a report language (references/glossary-<language>.yaml): the spelling the report uses for a term and the spellings it does not.

A writer that is told to "use plain words" invents them ("the moment a pod is put down" for scheduling). The glossary names the invented
forms that have actually appeared, the writer gets the list, and `find` reads the finished text for any that came back so one more
replacement pass can fix those sentences. Code blocks and code spans are not read: a command or a field name is data.
"""

from __future__ import annotations

import re

from ..foundations import paths, yamlite

_FENCE = re.compile(r"^```.*?^```[ \t]*$", re.DOTALL | re.MULTILINE)
_SPAN = re.compile(r"`[^`\n]*`")


def load(language: str) -> list[dict]:
    p = paths.ROOT / "references" / f"glossary-{language}.yaml"
    if not p.is_file():
        return []
    return [t for t in (yamlite.load_file(p) or {}).get("terms") or [] if isinstance(t, dict) and t.get("use") and t.get("avoid")]


def as_text(terms: list[dict]) -> str:
    """The list as the writer reads it: one line per term."""
    return "\n".join(f"- {t['use']} ← {', '.join(repr(a) for a in t['avoid'])}" for t in terms)


def find(text: str, terms: list[dict]) -> list[str]:
    """One line per sentence that uses a spelling the glossary avoids: the line, the spelling, and what to write."""
    prose = _SPAN.sub("", _FENCE.sub("", text))
    out = []
    for ln in prose.splitlines():
        for t in terms:
            hit = next((a for a in t["avoid"] if a in ln), None)
            if hit:
                out.append(f'- quote: "{ln.strip()[:200]}"\n  term: {hit!r} is not used; write {t["use"]}')
    return out
