"""The versions kubegap's facts were read at (#146): references/verified-versions.yaml is the one source; this module renders README's "Verified against"
table in both languages (`scripts/kubegap verified --markdown`), says for a running component whether its version is inside the range read
(`range_note`, the report header), and lists the citations that name a tag the file does not know (`uncited_tags`, tests/test_verified_doc.py)."""

from __future__ import annotations

import functools
import re

from ..foundations import paths, yamlite

FILE = paths.ROOT / "references" / "verified-versions.yaml"
# One citation: `owner/repo path:line@tag` (also `path:12-14,20@tag`, `go.mod:12@tag`, a tag with `/` such as `api/v1.8.0`). The repository is not
# preceded by `/`, `.` or a word character (so `/metrics/cadvisor` in a URL path is not one).
CITATION = re.compile(r"(?<![\w./])([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s+[A-Za-z0-9_./-]+(?::[\d,-]+)?@([\w.+-]+(?:/[\w.+-]+)*)")
# A later citation of the same file or repository on the same line: `, :41@tag`, `` `pkg/x.go:12@tag` ``. It belongs to the last repository named on the line.
CONTINUATION = re.compile(r"(?<![\w@])(?:[A-Za-z0-9_./-]+)?:[\d,-]+@([\w.+-]+(?:/[\w.+-]+)*)")
# Where citations live: the check and query data, the signatures, the summary modules and their helpers, the node scripts, the rubric data, the deployed
# documents and the sources register. Not scanned: tests, docs/, CHANGELOG, README (they repeat citations made elsewhere).
CITED_IN = ("collectors/*/*.yaml", "collectors/*/*.sh", "signatures/*.yaml", "lib/**/*.py", "rubric/*.yaml", "deploy/**/*", "references/sources.md", "SKILL.md")
LABELS = {
    "en": {
        "component": "Component",
        "read": "Versions read in source",
        "clusters": "Reference clusters (EKS / k3s)",
        "assumes": "Assumed installation, and what happens outside it",
        "none": "—",
        "to": " to ",
        "newest": "newest",
        "inside": "verified",
        "outside": "outside the verified range",
        "observed": "{n} facts in references/sources.md are marked unverified: observed on the reference clusters, not read in source.",
    },
    "ko": {
        "component": "구성 요소",
        "read": "소스로 읽은 버전",
        "clusters": "기준 클러스터 (EKS / k3s)",
        "assumes": "가정한 설치 방식과 그 밖에서 일어나는 일 (영문)",
        "none": "—",
        "to": " ~ ",
        "newest": "최신",
        "inside": "검증 범위 안",
        "outside": "검증 범위 밖",
        "observed": "references/sources.md 의 사실 {n}개는 unverified 로 표시되어 있습니다. 기준 클러스터에서 관찰했을 뿐 소스로 읽지 않은 것입니다.",
    },
}


@functools.cache
def load() -> dict:
    return yamlite.load_file(FILE) or {}


def components() -> list[dict]:
    return list(load().get("components") or [])


def libraries() -> set[str]:
    return set(load().get("libraries") or [])


def _ver_key(tag: str) -> tuple:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", tag)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)) if m else (0, 0, 0)


def version_range(component: dict) -> tuple[str, str] | None:
    """(lowest, highest) of the tags in `read` that citations attribute to the component's first repository, the one the component is named after (the
    others are its libraries and sub-projects, whose numbering is their own), limited to `tag_prefix` when the repository holds several tag families
    (`kube-prometheus-stack-`, `controller-v`); None when no tag carries a dotted version (a commit hash, a branch)."""
    primary = (component.get("repos") or [None])[0]
    prefix = component.get("tag_prefix") or ""
    read = set(component.get("read") or [])
    full = full_citations()
    elsewhere = {t for repo, tags in full.items() if repo != primary for t in tags}  # a continuation tag another repository cites in full was most likely its
    tags = [t for t in cited_tags().get(primary, set()) if t in read and t.startswith(prefix) and re.search(r"\d+\.\d+", t) and (t in full.get(primary, set()) or t not in elsewhere)]
    if not tags:
        return None
    tags.sort(key=_ver_key)
    return tags[0], tags[-1]


def _minor_text(tag: str) -> str:
    k = _ver_key(tag)
    return f"{k[0]}.{k[1]}"


def range_note(component_name: str, version: str | None, language: str = "en") -> str | None:
    """For the report header: `3.7.3 (verified 2.49 to 3.15)` or `1.8 (outside the verified range 2.6 to 3.7)`; None without a version or a range."""
    comp = next((c for c in components() if c["name"].split(" (")[0].lower().startswith(component_name.lower())), None)
    rng = version_range(comp) if comp else None
    if not version or not rng:
        return None
    lab = LABELS.get(language) or LABELS["en"]
    lo, hi = rng
    inside = _ver_key(lo)[:2] <= _ver_key(version)[:2] <= _ver_key(hi)[:2]
    return f"{version} ({lab['inside'] if inside else lab['outside']} {_minor_text(lo)}{lab['to']}{_minor_text(hi)})"


def unverified_count() -> int:
    """Table rows of references/sources.md marked **unverified** (the legend and prose that mention the marker are not facts)."""
    return sum(1 for line in (paths.ROOT / "references" / "sources.md").read_text(encoding="utf-8").splitlines() if line.startswith("|") and "**unverified" in line)


def render_table(language: str = "en") -> str:
    lab = LABELS.get(language) or LABELS["en"]
    lines = [f"| {lab['component']} | {lab['read']} | {lab['clusters']} | {lab['assumes']} |", "|---|---|---|---|"]
    for c in components():
        rng = version_range(c)
        read = f"{rng[0]}{lab['to']}{rng[1]}" if rng and rng[0] != rng[1] else (rng[0] if rng else "")
        if c.get("newest") and (not rng or _ver_key(c["newest"]) != _ver_key(rng[1])):
            read = f"{read} ({lab['newest']} {c['newest']})" if read else c["newest"]
        clusters = f"{c.get('eks') or lab['none']} / {c.get('k3s') or lab['none']}"
        assumes = " — ".join(x for x in (c.get("assumes"), c.get("outside")) if x) or lab["none"]
        lines.append(f"| {c['name']} | {read} | {clusters} | {assumes} |")
    lines.append("")
    lines.append(lab["observed"].format(n=unverified_count()))
    return "\n".join(lines) + "\n"


def _lines() -> list[str]:
    out = []
    for pattern in CITED_IN:
        for f in sorted(paths.ROOT.glob(pattern)):
            if f.is_file():
                out += f.read_text(encoding="utf-8", errors="replace").splitlines()
    return out


@functools.cache
def full_citations() -> dict[str, set[str]]:
    """repository → the tags named by citations that spell the repository (`owner/repo path:line@tag`): unambiguous."""
    out: dict[str, set[str]] = {}
    for line in _lines():
        for m in CITATION.finditer(line):
            if not re.match(r"v\d", m.group(1).split("/")[1]):  # `storage.k8s.io/v1 …@v1.37.2` is an API group, not a repository
                out.setdefault(m.group(1), set()).add(m.group(2))
    return out


@functools.cache
def cited_tags() -> dict[str, set[str]]:
    """repository → every tag a citation of it names, over CITED_IN. A `:line@tag` or `path:line@tag` without a repository belongs to the repository last
    named on its line, by a citation or by a bare mention of a repository that is cited in full somewhere (`kubernetes/kubernetes go.mod pins: :38@v1.32.13`).
    In prose that attribution can be wrong (a second project's file cited in backticks after the first repository's name), so `uncited_tags` holds a
    continuation tag only to the tags the file knows anywhere, and a full citation to its own component's `read`."""
    lines = _lines()
    out = {repo: set(tags) for repo, tags in full_citations().items()}
    mention = re.compile(r"(?<![\w./-])(" + "|".join(re.escape(r) for r in sorted(out, key=len, reverse=True)) + r")(?![\w./-])") if out else None
    for line in lines:
        repo = None
        pos = 0
        for m in mention.finditer(line) if mention else ():
            if repo:
                for c in CONTINUATION.finditer(line, pos, m.start()):
                    out[repo].add(c.group(1))
            repo = m.group(1)
            pos = m.end()
        if repo:
            for c in CONTINUATION.finditer(line, pos):
                out[repo].add(c.group(1))
    return out


def uncited_tags() -> list[str]:
    """Citations the file does not account for. A citation that spells its repository must name a tag in that component's `read` (or the repository
    is a library, whose tags are not tracked). A `:line@tag` continuation, whose repository is inferred from the line, must name a tag that some
    component's `read` or some library's full citation knows. A repository that is neither a component's nor a library is reported once."""
    by_repo = {r: c for c in components() for r in c.get("repos") or []}
    libs = libraries()
    known = {t for c in components() for t in c.get("read") or []}
    full = full_citations()
    for repo, tags in full.items():
        if repo in libs:
            known |= tags
    out = []
    for repo, tags in sorted(cited_tags().items()):
        if repo in by_repo:
            read = by_repo[repo].get("read") or []
            out += [f"{repo}@{t} is cited but not in `read` of {by_repo[repo]['name']!r}" for t in sorted(full.get(repo, set())) if t not in read]
            out += [f"{repo} :line@{t} (continuation, repository inferred) names a tag no component's `read` and no library citation knows" for t in sorted(tags - full.get(repo, set())) if t not in known]
        elif repo not in libs:
            out.append(f"{repo} is cited ({', '.join(sorted(tags))}) but is neither a component's repository nor a library in references/verified-versions.yaml")
    return out
