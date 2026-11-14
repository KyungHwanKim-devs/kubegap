"""The daily report: one or two screens that say what matters now.

A daily run exists for three reasons: a full run takes too long, a full run reads more than a cautious user wants on their disk or in a
model, and a full report holds too many kinds of information for someone new to see what matters today. So the daily report is not a short
full report. It answers three questions: is something broken now, what happened since the last run, and which three things matter most.
Each of the three is told in three short parts (what it is, why it matters, what to do) with one page to read.

No separate agent writes it. The session that analysed the run writes `report/daily.json` in the daily shape (references/daily-<language>.md),
reading the summary and the findings only: the raw objects are already deleted (lib/output/slim.py). `check` refuses what a reader should not
get (a number the summary does not hold, an address no learn topic carries, a made-up term, the conversational sentence ending, a part that
runs long), and `assemble` prints the report from the facts with everything countable written by code.

The facts of a daily run (schema 2):

    {"broken_now": [{"title": "", "what": "", "finding_ids": []}],
     "happened": {"incidents": [{"id": "A", "title": "", "what": "", "state": "ended|ongoing|unknown", "finding_ids": [], "facts": []}]},
     "top": [{"id": "1", "title": "", "loss": "irreversible|outage|partial|degraded", "what": "", "why": "", "do": "",
              "read": {"title": "", "url": ""}, "finding_ids": [], "facts": []}],
     "rest": [{"title": "", "finding_ids": []}],
     "since_last": {"appeared": [""], "gone": [""]},
     "severity_changes": []}
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..foundations import paths
from ..foundations import rubric as _rubric
from ..foundations import units as _units
from ..foundations.snapshot import load_json
from . import glossary as _glossary
from . import outline as _facts
from . import parts as _writer
from . import sections as _sections
from .report import HAEYO

TOP = 3
STATES = ("ended", "ongoing", "unknown")
# How long each part may run, in sentences. A daily report is read in a minute; the long explanation is the full report's.
SENTENCES = {"what": 4, "why": 3, "do": 4, "incident": 4, "broken": 3}
_SENTENCE_END = re.compile(r"[.?!](?=\s|$)")

TEXT = {
    "ko": {
        "title": "# {cluster} — daily 점검, {when}",
        "verdict": "지금 깨져 있는 것 {broken}개 · 지난 점검 이후 일어난 일 {happened}건 · 지금 가장 중요한 것 {top}개",
        "first_broken": "지금 깨져 있는 것",
        "first_happened": "지난 점검 이후 일어난 일",
        "first_top": "지금 가장 중요한 것",
        "first_scale": "운영 규모",
        "none": "없음",
        "broken": "지금 깨져 있는 것",
        "happened": "지난 점검 이후 일어난 일",
        "happened_none": "새로 일어난 일을 찾지 못했습니다.",
        "top": "지금 가장 중요한 것",
        "top_none": "심각도가 높은 문제를 찾지 못했습니다.",
        "what": "무슨 일인가",
        "why": "왜 중요한가",
        "do": "무엇을 하면 되나",
        "read": "더 읽기",
        "since_new": "이번 점검에서 처음 나왔습니다.",
        "since_old": "{when} 점검부터 그대로입니다. 이번이 {n}번째 점검입니다.",
        "ongoing": "지금도 계속되고 있습니다.",
        "ended": "지금은 끝난 일입니다.",
        "rest": "그 밖에 열려 있는 것",
        "since": "지난 점검 이후 달라진 것",
        "period": "{start} 점검과 비교했습니다.",
        "no_previous": "이번이 이 클러스터의 첫 daily 점검이라 비교할 이전 점검이 없습니다. 수집한 기간 안에 일어난 일을 적었습니다.",
        "appeared": "새로 생긴 것",
        "gone": "없어진 것",
        "objects": "오브젝트는 {added}개가 추가되고 {removed}개가 없어지고 {changed}개가 바뀌었습니다.",
        "unseen": "이번 점검이 보지 않은 것",
        "unseen_intro": "daily 점검은 가볍게 보는 점검입니다. Kubernetes API와 메트릭·로그 저장소만 읽었습니다.",
        "unseen_secrets": "Secret 값은 어느 점검에서도 읽지 않습니다.",
        "unseen_at_limit": "수집이 자체 제한에 걸려 일부만 읽은 것이 있습니다: {names}. 여기에서 센 숫자는 실제보다 적을 수 있습니다.",
        "unseen_checks": "그래서 점검 항목 {total}개 가운데 {unseen}개는 이번에 보지 못했습니다. 노드 안쪽, 비용, 없어질 API 같은 항목이고, 문제로도 통과로도 세지 않았습니다.",
        "unseen_serious": "특히 아래와 같은 문제는 심각할 수 있는데도 노드 안쪽이나 클라우드 계정, 애플리케이션 설정을 읽어야 보여서 daily 점검으로는 알 수 없습니다. 이 리포트에 없다고 해서 문제가 없다는 뜻이 아닙니다.",
        "unseen_full": "이것들을 확인하고, 원인을 원본까지 열어 따지고, 문제마다 원리와 점검 방법과 규모별 해결 방안을 길게 설명하는 것은 `/kubegap full`입니다.",
        "first_unseen": "daily 점검이 볼 수 없는 심각한 문제가 {n}가지 있습니다. 목록은 맨 아래에 있고, 확인하려면 `/kubegap full`을 돌립니다.",
        "ids": "점검 항목 id (`/kubegap explain <id>`)",
        "tail": "kubegap {version}, rubric {rubric} · 스냅샷 `{snap}`",
    },
    "en": {
        "title": "# {cluster} — daily audit, {when}",
        "verdict": "Broken now: {broken} · Happened since the last audit: {happened} · Matter most now: {top}",
        "first_broken": "Broken now",
        "first_happened": "Happened since the last audit",
        "first_top": "What matters most now",
        "first_scale": "Scale",
        "none": "nothing",
        "broken": "Broken now",
        "happened": "What happened since the last audit",
        "happened_none": "Nothing new was found to have happened.",
        "top": "What matters most now",
        "top_none": "No problem of high severity was found.",
        "what": "What it is",
        "why": "Why it matters",
        "do": "What to do",
        "read": "Further reading",
        "since_new": "It appeared in this audit for the first time.",
        "since_old": "It has stood since the audit of {when}. This is audit number {n} to see it.",
        "ongoing": "It is still going on.",
        "ended": "It is over now.",
        "rest": "What else is open",
        "since": "What changed since the last audit",
        "period": "Compared with the audit of {start}.",
        "no_previous": "This is the first daily audit of this cluster, so there is no earlier one to compare with. What is listed happened within the period this audit collected.",
        "appeared": "Appeared",
        "gone": "Went away",
        "objects": "{added} objects were added, {removed} were removed and {changed} changed.",
        "unseen": "What this audit did not look at",
        "unseen_intro": "A daily audit is the light one. It read the Kubernetes API and the metric and log stores only.",
        "unseen_secrets": "Secret values are not read by any audit.",
        "unseen_at_limit": "The collection stopped at one of its own limits and read only part of: {names}. A number counted from these may be lower than the real one.",
        "unseen_checks": "So {unseen} of the {total} checks were not looked at this time: the inside of the nodes, cost, APIs about to be removed and the like. They are counted neither as a problem nor as a pass.",
        "unseen_serious": "In particular, the problems below can be serious and still cannot be seen by a daily audit, because they show only in the inside of a node, in the cloud account or in how applications are configured. That they are not in this report does not mean they are not there.",
        "unseen_full": "To check these, to follow a cause down to the raw material, and to have each problem explained with its principle, how to watch it and how it is solved at each scale, run `/kubegap full`.",
        "first_unseen": "There are {n} kinds of serious problem a daily audit cannot see. They are listed at the end; to check them, run `/kubegap full`.",
        "ids": "Check ids (`/kubegap explain <id>`)",
        "tail": "kubegap {version}, rubric {rubric} · snapshot `{snap}`",
    },
}


# What a daily run cannot find, said in the reader's words: one phrase per check that is critical or high at some scale and judged only by a
# full run, because it needs the inside of a node or the cloud account. The report lists the ones that apply to the cluster, so that a reader
# does not take their absence for a pass. tests/test_daily_report.py fails when such a check has no phrase here.
UNSEEN = {
    "ko": {
        "node.kernel-oom-node-level": "노드 전체의 메모리가 모자라 커널이 프로세스를 끝낸 일",
        "node.kernel-lockup": "커널이 멈추는 오류",
        "node.kernel-io-fs-errors": "디스크 I/O 오류와 파일시스템 오류",
        "node.conntrack-table-full": "conntrack 테이블이 가득 차 패킷이 버려지는 것",
        "node.cri-not-ready": "컨테이너 런타임 이상",
        "node.clock-unsynced-os": "노드 시계가 맞지 않는 것",
        "traffic.flannel-sysctl-off": "노드의 네트워크 커널 설정이 꺼져 있는 것",
        "platform.k3s-etcd-snapshot-stale": "etcd 스냅샷이 없거나 오래된 것",
        "platform.k3s-certificate-expiring": "k3s 내부 인증서의 만료",
        "platform.k3s-datastore-slow": "k3s 데이터스토어(etcd)가 느린 것",
        "platform.k3s-datastore-large": "k3s 데이터스토어가 한도에 가까운 것",
        "storage.local-path-over-capacity": "local-path 볼륨이 요청한 용량을 넘은 것",
        "storage.local-path-fs-near-full": "노드 디스크가 차는 것",
        "controlplane.webhook-call-failures": "API 서버의 웹훅 호출 실패",
        "controlplane.scheduler-unschedulable": "스케줄러가 파드를 배치하지 못한 기록",
        "hygiene.deprecated-api": "다음 Kubernetes 버전에서 없어지는 API를 쓰는 것",
        "resilience.backup-same-node": "백업이 원본 데이터베이스와 같은 노드에만 있는 것",
        "resilience.prod-db-without-backup-cronjob": "백업 작업이 없는 운영 데이터베이스",
        "security.plaintext-configmap-secret": "ConfigMap에 적힌 비밀 값",
        "security.eks-secrets-encryption-off": "EKS의 Secret 암호화 설정",
        "security.imds-hop-limit": "파드가 노드의 IAM 자격 증명에 닿을 수 있는 설정",
        "traffic.alb-unhealthy-targets": "로드밸런서 뒤의 비정상 대상",
        "eks.public-endpoint-open": "클러스터 엔드포인트가 인터넷 전체에 열려 있는 것",
        "eks.no-backup-policy": "EBS 스냅샷과 백업 정책이 없는 것",
        "eks.acm-certificate-expiring": "ACM 인증서의 만료",
        "eks.service-quota-near-limit": "AWS 서비스 한도에 가까운 것",
        "eks.security-group-open-to-world": "보안 그룹이 인터넷 전체에 열려 있는 것",
        "vpccni.node-ip-exhaustion": "파드에 줄 IP가 모자란 것",
        "vpccni.no-available-ip": "파드에 줄 IP가 모자란 것",
        "vpccni.subnet-ips-low": "파드에 줄 IP가 모자란 것",
    }
}


def serious_full_only(platform: str | None, collectors: list[str] | None) -> list[dict]:
    """The checks a daily run cannot judge although their finding would be serious: they need a collection unit the daily run leaves out
    (collectors/units.yaml), are critical or high at some scale, and belong to this cluster (its platform, and a collector that ran)."""
    out = []
    for c in _rubric.catalog():
        sev = c["severity_default"]
        if not _units.missing(c.get("needs"), "daily") or not any(v in ("critical", "high") for v in (sev.values() if isinstance(sev, dict) else [sev])):
            continue
        if _rubric.applies(c, platform, "large") or (collectors is not None and c.get("collector") not in collectors):
            continue
        out.append(c)
    return out


def _prose(facts: dict):
    """(label, part, text) for every sentence an agent wrote: what `check` reads for length, sentence ending and terms."""
    for b in facts.get("broken_now") or []:
        yield f"broken_now {b.get('title')!r}", "broken", str(b.get("what") or "")
    for i in (facts.get("happened") or {}).get("incidents") or []:
        yield f"incident {i.get('id')}", "incident", str(i.get("what") or "")
    for t in facts.get("top") or []:
        for part in ("what", "why", "do"):
            yield f"top {t.get('id')} {part}", part, str(t.get(part) or "")
    for kind in ("appeared", "gone"):
        for line in (facts.get("since_last") or {}).get(kind) or []:
            yield f"since_last.{kind}", "", str(line)


def learn_urls(fd: dict) -> set[str]:
    """Every address a learn topic of this run carries: the only pages a daily report may point to, because someone opened them."""
    out: set[str] = set()
    for t in fd.get("learn") or []:
        for key in ("sources", "reading", "cases"):
            out |= {str(x.get("url")) for x in t.get(key) or [] if isinstance(x, dict) and x.get("url")}
    return out


def _resolve(doc, path: str):
    """The value at `a.b[0].c`. Raises KeyError or IndexError or TypeError when the path does not exist."""
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        doc = doc[int(part[1:-1])] if part.startswith("[") else doc[part]
    return doc


def _numbered(facts: dict):
    """(label, number) for every number an entry of the daily file carries with its source."""
    for kind, entries in (("broken_now", facts.get("broken_now") or []), ("incident", (facts.get("happened") or {}).get("incidents") or []), ("top", facts.get("top") or [])):
        for e in entries:
            for n in (e.get("facts") or []) if isinstance(e, dict) else []:
                if isinstance(n, dict):
                    yield f"{kind} {e.get('id') or e.get('title')}: {n.get('what')}", n


def verify_numbers(snap: Path, facts: dict) -> list[str]:
    """Numbers whose source does not say what the facts say. A path with `*` or `...` is too."""
    out: list[str] = []
    docs: dict[str, object] = {}
    for label, n in _numbered(facts):
        src, path = n.get("source_file"), str(n.get("json_path") or "")
        if n.get("derived"):
            continue
        f = snap / str(src or "")
        if not src or not f.is_file():
            out.append(f"{label}: source file {src} does not exist")
            continue
        if not path or "*" in path or "..." in path or not src.endswith(".json"):
            continue
        try:
            doc = docs.setdefault(src, json.loads(f.read_text(encoding="utf-8")))
            found = _resolve(doc, path)
        except (KeyError, IndexError, TypeError, ValueError):
            out.append(f"{label}: {path} is not in {src}")
            continue
        value = n.get("value")
        wanted = [str(v) for v in value] if isinstance(value, list) else [str(value)]
        if not all(w in json.dumps(found, ensure_ascii=False, default=str) for w in wanted):
            out.append(f"{label}: facts say {value}, {src} {path} says {str(found)[:120]}")
    return out


def check(facts: dict, snap: Path, language: str = "ko") -> list[str]:
    """Every rule the daily facts break, one line each, worded for the session that has to fix it."""
    out: list[str] = []
    if facts.get("problems") or facts.get("next"):
        out.append("a daily run writes `top` (three at most) and `rest`, not `problems` and `next`: those are the full report's (references/daily-<language>.md)")
    fd = load_json(snap / "findings-draft.json") or {}
    findings = [f for f in fd.get("findings") or [] if f.get("status") in ("fail", "warn")]
    known = {f["id"] for f in findings}
    final = _facts.final_severities(facts, findings)
    top = [t for t in facts.get("top") or [] if isinstance(t, dict)]
    rest = [r for r in facts.get("rest") or [] if isinstance(r, dict)]
    incidents = [i for i in (facts.get("happened") or {}).get("incidents") or [] if isinstance(i, dict)]
    broken = [b for b in facts.get("broken_now") or [] if isinstance(b, dict)]

    for kind, entries in (("top", top), ("rest", rest), ("incident", incidents), ("broken_now", broken)):
        for e in entries:
            label = f"{kind} {e.get('id') or e.get('title')!r}"
            if not e.get("title"):
                out.append(f"{label}: no title")
            if not _facts._ids(e):
                out.append(f"{label}: no finding_ids; every entry names the findings it stands for")
            for pat in _facts._ids(e):
                if not any(_facts._matches([pat], k) for k in known):
                    out.append(f"{label}: finding id {pat} is not in findings-draft.json")
    for e in incidents + broken:
        if not e.get("what"):
            out.append(f"{e.get('title')!r}: `what` is empty; say what happened in two or three sentences")
    for i in incidents:
        if i.get("state") not in STATES:
            out.append(f"incident {i.get('id')}: state must be one of {', '.join(STATES)} (unknown when the summary does not say whether it still goes on)")

    if len(top) > TOP:
        out.append(f"{len(top)} entries in top; a daily report tells {TOP} and lists the others in rest")
    allowed = learn_urls(fd)
    rank: list[tuple[int, int]] = []
    for t in top:
        tid = t.get("id")
        for part in ("what", "why", "do"):
            if not t.get(part):
                out.append(f"top {tid}: `{part}` is empty")
        if t.get("loss") not in _facts.LOSSES:
            out.append(f"top {tid}: loss must be one of {', '.join(_facts.LOSSES)}")
        read = t.get("read")
        if read is not None and (not isinstance(read, dict) or not read.get("title") or read.get("url") not in allowed):
            out.append(f"top {tid}: read must be {{title, url}} with an address from `learn` in findings-draft.json (pages someone opened), or null when no topic covers it")
        sev = _facts.problem_severity(t, final)
        if sev and t.get("loss") in _facts.LOSSES:
            late = any(f.get("overdue") and f["status"] == "fail" and _facts._matches(_facts._ids(t), f["id"]) for f in findings)
            rank.append((_facts.SEVERITIES.index(sev), max(_facts.LOSSES.index(t["loss"]) - (1 if late else 0), 0)))
    if rank != sorted(rank):
        out.append("top is not in order: severity first (scale already applied), then what is lost (irreversible, outage, partial, degraded; an `overdue` failure counts one step higher)")

    placed = [pat for e in top + rest + incidents + broken for pat in _facts._ids(e)]
    lost = sorted(f["id"] for f in findings if _facts.must_be_placed(f, final[f["id"]]) and not _facts._matches(placed, f["id"]))
    if lost:
        out.append(f"{len(lost)} critical or high failures or critical warnings are in no list (top, rest, happened, broken_now): {', '.join(lost[:12])}{' …' if len(lost) > 12 else ''}")
    if top and rest:
        worst_rest = _facts._worst([s for r in rest for s in [_facts.problem_severity(r, final)] if s])
        last = _facts.problem_severity(top[-1], final)
        if worst_rest and last and _facts.SEVERITIES.index(worst_rest) < _facts.SEVERITIES.index(last):
            out.append(f"rest holds a {worst_rest} entry while top {top[-1].get('id')} is {last}; the more severe one belongs in top")

    terms = _glossary.load(language)
    for label, part, text in _prose(facts):
        if "```" in text:
            out.append(f"{label}: no code block in a daily report; name the setting in a sentence")
        n = len(_SENTENCE_END.findall(text))
        if part and n > SENTENCES[part]:
            out.append(f"{label}: {n} sentences; this part takes {SENTENCES[part]} at most (the long explanation is the full report's)")
        if language == "ko" and HAEYO.search(text):
            out.append(f"{label}: ends a sentence in 해요체 ({HAEYO.search(text).group(0)}); the report is written in 합니다체")
        out += [f"{label}: {hit}" for hit in _glossary.find(text, terms)]

    # a number is what the file it names says it is; a `derived` mark is not accepted in a daily report, where nothing checks it afterwards
    for _label, n in _numbered(facts):
        if n.get("derived"):
            out.append(f"{_label}: `derived` is not accepted in a daily report; give the file and the path the number is at, or leave the number out")
    out += verify_numbers(snap, facts)
    for label, n in _numbered(facts):
        if n.get("source_file") and not _facts._inside(snap, str(n["source_file"])):
            out.append(f"{label}: source {n['source_file']} is outside the snapshot")
    return out


def first_seen(snap: Path, entry: dict, limit: int = 30) -> tuple[str, int] | None:
    """(when, runs) for an entry that the earlier daily runs of this cluster already had, without a gap: the day of the first of them and how
    many runs it has stood, this one included. None when the run before this one did not have it."""
    pats = _facts._ids(entry)
    earlier = sorted((p for p in snap.parent.iterdir() if p.is_dir() and paths.is_snapshot_name(p.name) and p.name < snap.name and paths.snapshot_mode(p) == "daily"), reverse=True)
    since, runs = None, 1
    for s in earlier[:limit]:
        fd = load_json(s / "findings-draft.json") or {}
        if not any(_facts._matches(pats, f.get("id", "")) for f in fd.get("findings") or [] if f.get("status") in ("fail", "warn")):
            break
        since, runs = s, runs + 1
    if since is None:
        return None
    return _writer._when((load_json(since / "inventory.json") or {}).get("taken_at")) or since.name, runs  # with the time: two runs may share a day


def _unseen(snap: Path, t: dict, language: str) -> str:
    inv, fd = load_json(snap / "inventory.json") or {}, load_json(snap / "findings-draft.json") or {}
    by = (fd.get("checks") or {}).get("by_status") or {}
    # one line per collection unit this run left out, in the words the unit itself carries (collectors/units.yaml): the list cannot drift from what was read
    left = _units.left_out(paths.snapshot_mode(snap), (inv.get("cluster") or {}).get("platform"))
    lines = [t["unseen_intro"], "", *(f"- {u['unseen'][language]}" for u in left), f"- {t['unseen_secrets']}"]
    at_limit = ((load_json(snap / "summary.json") or {}).get("collection") or {}).get("at_limit") or {}
    if at_limit:
        lines.append("- " + t["unseen_at_limit"].format(names="; ".join(f"`{step}` ({', '.join(map(str, what)) if isinstance(what, list) else what})" for step, what in sorted(at_limit.items()))))
    lines.append("")
    lines += [t["unseen_checks"].format(total=(fd.get("checks") or {}).get("total", 0), unseen=by.get("not-collected", 0)), ""]
    serious = unseen_phrases(snap, language)
    if serious:
        lines += [t["unseen_serious"], "", *(f"- {p}" for p in serious), ""]
    lines.append(t["unseen_full"])
    return f"## {t['unseen']}\n\n" + "\n".join(lines)


def unseen_phrases(snap: Path, language: str) -> list[str]:
    """The serious things this daily run could not find, in the reader's words, without repeats."""
    inv = load_json(snap / "inventory.json") or {}
    checks = serious_full_only((inv.get("cluster") or {}).get("platform"), inv.get("collectors_enabled"))
    if language not in UNSEEN:  # the check's own name is its English phrase; the Korean ones are written out above
        return list(dict.fromkeys(str(c["name"]) for c in checks))
    return list(dict.fromkeys(UNSEEN[language][c["id"]] for c in checks if c["id"] in UNSEEN[language]))


def assemble(snap: Path, facts: dict, language: str, rubric: str, version: str) -> str:
    """The daily report from the facts. Code writes the title, the first screen, the cluster at a glance, how long each thing has stood, what
    changed in numbers, what the run did not read and the ids; the agent's sentences are printed as they were checked."""
    t = TEXT[language]
    h = _writer.HEADINGS[language]
    inv, fd = load_json(snap / "inventory.json") or {}, load_json(snap / "findings-draft.json") or {}
    broken = [b for b in facts.get("broken_now") or [] if isinstance(b, dict)]
    incidents = [i for i in (facts.get("happened") or {}).get("incidents") or [] if isinstance(i, dict)]
    top = [x for x in facts.get("top") or [] if isinstance(x, dict)][:TOP]
    rest = [r for r in facts.get("rest") or [] if isinstance(r, dict)]
    scale = (fd.get("scale") or {}).get("name")
    out = [t["title"].format(cluster=(inv.get("cluster") or {}).get("cluster_name") or inv.get("context") or snap.parent.name, when=_writer._when(inv.get("taken_at")))]
    first = [
        t["verdict"].format(broken=len(broken), happened=len(incidents), top=len(top)),
        "",
        f"{t['first_broken']}: " + (" · ".join(str(b.get("title")) for b in broken) or t["none"]),
        "",
        f"{t['first_happened']}: " + (" · ".join(str(i.get("title")) for i in incidents) or t["none"]),
        "",
        f"{t['first_top']}: " + (" ".join(f"{_writer.CIRCLED[n]} {x.get('title')}" for n, x in enumerate(top)) or t["none"]),
    ]
    if scale:
        first += ["", f"{t['first_scale']}: {_sections.SCALE_WORD[language].get(scale, scale)}"]
    n_unseen = len(unseen_phrases(snap, language))
    if n_unseen:
        first += ["", t["first_unseen"].format(n=n_unseen)]
    out += ["\n".join(first), _writer.glance(snap, h, names=False)]
    if broken:
        out.append(f"## {t['broken']}\n\n" + "\n\n".join(f"### {b.get('title')}\n\n{str(b.get('what') or '').strip()}" for b in broken))
    prev = paths.previous_snapshot(snap)
    period = t["period"].format(start=_writer._when((load_json(prev / "inventory.json") or {}).get("taken_at"))) if prev else t["no_previous"]
    happened = "\n\n".join(f"### {i.get('title')}\n\n{str(i.get('what') or '').strip()} {t.get(str(i.get('state')), '')}".rstrip() for i in incidents)
    out.append(f"## {t['happened']}\n\n{period}\n\n{happened or t['happened_none']}")
    blocks = []
    for n, x in enumerate(top, 1):
        seen = first_seen(snap, x)
        lines = [f"### {n}. {x.get('title')}", ""]
        if prev:  # on the first run everything is new, and saying so under each title says nothing
            lines += [t["since_old"].format(when=seen[0], n=seen[1]) if seen else t["since_new"], ""]
        for part in ("what", "why", "do"):
            lines += [f"**{t[part]}.** {str(x.get(part) or '').strip()}", ""]
        read = x.get("read") or {}
        if read.get("url"):
            lines += [f"{t['read']}: [{read.get('title')}]({read['url']})", ""]
        blocks.append("\n".join(lines).rstrip())
    out.append(f"## {t['top']}\n\n" + ("\n\n".join(blocks) or t["top_none"]))
    if rest:
        out.append(f"## {t['rest']}\n\n" + "\n".join(f"- {r.get('title')}" for r in rest))
    since = [period, ""]
    if prev:
        sl = facts.get("since_last") or {}
        for key in ("appeared", "gone"):
            since += [f"**{t[key]}**", "", *([f"- {x}" for x in sl.get(key) or []] or [f"- {t['none']}"]), ""]
        osum = ((load_json(snap / "diff.json") or {}).get("objects") or {}).get("summary") or {}
        if osum:
            since += [t["objects"].format(added=osum.get("added", 0), removed=osum.get("removed", 0), changed=osum.get("changed", 0)), ""]
        since += _writer.criteria_changes(snap, h)
    if prev:
        out.append(f"## {t['since']}\n\n" + "\n".join(since).rstrip())
    out.append(_unseen(snap, t, language))
    ids = [f"- {x.get('title')}: " + ", ".join(f"`{i}`" for i in _facts._ids(x)) for x in broken + incidents + top if _facts._ids(x)]
    tail = t["tail"].format(version=version, rubric=rubric, snap=snap)
    return _writer.space_blocks("\n\n".join(out)) + "\n\n" + (f"{t['ids']}:\n\n" + "\n".join(ids) + "\n\n" if ids else "") + tail + "\n"
