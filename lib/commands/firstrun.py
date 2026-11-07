"""The questions a first run asks, and the answers it remembers.

A first-time user should not have to read a setup chapter. `kubegap setup` already knows what this cluster and this machine lack; this module
turns each gap into one question with a short explanation, what answering it adds to the report, two or three choices, and always a way to skip.
SKILL.md shows them in the host's choice window and runs the command of the chosen option. Nothing here acts: an option names the command, the
agent runs it only after the user picked it.

Rules:
- A question appears only for something that is missing. A cluster where everything was found gets none.
- The explanation, the gain and the option texts are produced here, from the setup result and the check catalog, so the agent never has to make
  up how many checks an answer adds.
- An answer is remembered per context in `<context folder>/answers.json` and the question is not asked again. `questions --all` lists every
  question again (the `/kubegap setup` mode).
- Two or three options per question and at most MAX_PER_WINDOW questions per window: the smaller of the limits of the two hosts read
  (Claude Code AskUserQuestion: 4 questions, 2-4 options; Codex request_user_input: 3 questions, 2-3 options,
  openai/codex codex-rs/core/src/tools/handlers/request_user_input_spec.rs:35,72@rust-v0.164.0). Both add a free-text entry themselves,
  which is where a value such as an address is typed (`typed` below).

The policies that already exist in config.yaml answer a question for good: `install_tools: never|always`, `ssm_document: never|always`,
`node_access: none`, a `<store>_url`, `grafana_api_token`.

Texts come in two languages, English and Korean, each written from the question's purpose (`language=` of `questions`); the agent copies the
block as printed and never translates it (#173). Loki is left out of the stores question when the log shipper's configuration says the logs
go elsewhere (lib/collection/logsinks.py, #174), and the Grafana token is asked for only when Grafana holds dashboards that are not in ConfigMaps
(`grafana_without_token`; the provisioned ones are read without a token).
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from ..collection.discover import SSH_PLATFORMS
from ..foundations import paths, rubric
from ..foundations.config import Config
from ..foundations.snapshot import load_json, write_private
from . import tools

MAX_PER_WINDOW = 3
ANSWERS_FILE = "answers.json"
NODE_ACCESS_FILE = "node-access.json"
STORES = ("prometheus", "alertmanager", "loki", "grafana")
SKIP = "skip"
PARTIAL = "partial"  # node-ssh: go on with the nodes that answer


# ---------- counts taken from the check catalog ----------


def _checks() -> tuple[dict, ...]:
    return rubric.catalog()


def node_script_checks() -> int:
    """Checks that read the node scripts or the kubelet configuration: the `node.*` checks a daily run does not collect. The `node.*` metric
    checks read Prometheus and run without node access. This is the catalog's count; a profile can switch a few of them off (two are for
    the lab profile only), so the texts say "up to"."""
    return sum(1 for c in _checks() if c["id"].startswith("node.") and c.get("modes") == ["full"])


# ---------- remembered answers ----------


def _load(ctx_dir: Path | None, name: str) -> dict:
    """A JSON object kept in the context folder, or {} when it is absent or unreadable."""
    d = load_json(ctx_dir / name) if ctx_dir else None
    return d if isinstance(d, dict) else {}


def load_answers(ctx_dir: Path | None) -> dict:
    return _load(ctx_dir, ANSWERS_FILE)


def record_answer(ctx_dir: Path, item: str, choice: str, detail: dict | None = None) -> dict:
    answers = load_answers(ctx_dir)
    answers[item] = {"choice": choice, "at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"), **({"detail": detail} if detail else {})}
    write_private(ctx_dir / ANSWERS_FILE, json.dumps(answers, ensure_ascii=False, indent=1))
    return answers


def forget_answers(ctx_dir: Path, items: list[str] | None = None) -> list[str]:
    answers = load_answers(ctx_dir)
    gone = [k for k in answers if items is None or k in items]
    for k in gone:
        del answers[k]
    if gone:
        write_private(ctx_dir / ANSWERS_FILE, json.dumps(answers, ensure_ascii=False, indent=1))
    return gone


def ssh_decision(ctx_dir: Path | None, cfg: Config) -> str:
    """Whether the user has decided about reading nodes over SSH: "yes", "skipped" or "open". Collection connects to a node over SSH only on
    "yes" (lib/collection/discover._node_access): nothing is contacted because of a question that was never answered.
    yes = config.yaml names SSH (`node_access: ssh` or an `ssh:` block), or the user ran the probe (`kubegap nodes` saved an SSH result), or
    chose to go on with the nodes that answer."""
    if cfg.get("node_access") == "ssh" or cfg.get("ssh"):
        return "yes"
    choice = (load_answers(ctx_dir).get("node-ssh") or {}).get("choice")
    if choice == SKIP:
        return "skipped"
    if choice == PARTIAL or _load(ctx_dir, NODE_ACCESS_FILE).get("method") == "ssh":
        return "yes"
    return "open"


# ---------- the questions ----------


def _opt(id: str, label: str, description: str, run: list[str] | None = None, *, remember: bool = True, show: list[str] | None = None, config: list[str] | None = None) -> dict:
    """`run`: kubegap arguments the agent runs after this choice (it adds --context). `show`: lines the agent prints for the user, who acts on
    them. `config`: a [key, value] the choice puts into config.yaml, which the agent writes only after showing the dry run and a second
    choice. `remember`: record the choice so the question is not asked again; false when the action itself removes the gap or the user said
    "later", and then an earlier remembered answer is forgotten instead."""
    return {"id": id, "label": label, "description": description, "run": run, "show": show, "config": config, "remember": remember}


LANGUAGES = ("en", "ko")
_AGAIN = {"en": " Not asked again; `/kubegap setup` brings the question back.", "ko": " 다시 묻지 않아요. `/kubegap setup`으로 다시 불러올 수 있어요."}


def _skip(L: str, lost: str) -> dict:
    return _opt(SKIP, {"en": "Skip", "ko": "건너뛰기"}[L], lost + _AGAIN[L])


def _n(L: str, n: int, en_one: str, en_many: str, ko: str) -> str:
    """A count with its noun: English needs the plural, Korean does not."""
    return f"{n} {en_one if n == 1 else en_many}" if L == "en" else f"{ko} {n}개"


# Every question is written twice, in English and in Korean, from what the question is for. The Korean is not a translation of the English:
# the person reading the window is deciding what kubegap may touch, and a sentence they have to decode is a wrong choice waiting to happen
# (#173). tests/test_firstrun.py checks the Korean against the translation-pattern list the writing guides use.


def _q_home_mode(setup: dict, cfg: Config, L: str) -> dict | None:
    dirs = (setup.get("machine") or {}).get("open_dirs") or []
    if not dirs:
        return None
    top = dirs[0]
    n = len(dirs)
    if L == "ko":
        q = {
            "header": "폴더 권한",
            "question": f"{top['path']} 폴더를 나만 읽을 수 있게 바꿀까요? 지금은 이 컴퓨터의 다른 사용자도 읽을 수 있어요(권한 {top['mode']}).",
            "explain": "이 폴더에 점검 결과가 쌓여요. 클러스터에서 읽어 온 오브젝트, 이벤트, 로그 줄이 전부 여기 있어요. kubegap은 이 폴더를 0700으로 만드는데, 이 폴더는 옛 버전이 만들었거나 나중에 권한이 넓어졌어요.",
            "gain": ["리포트는 달라지지 않아요. 점검 결과를 내 계정만 읽을 수 있게 돼요"],
            "fix": ("지금 고치기", f"{top['path']} 아래 폴더 {n}개에 chmod 700을 해요. 다른 건 건드리지 않아요."),
            "leave": ("그대로 두기", "폴더는 지금 그대로예요." + _AGAIN["ko"]),
        }
    else:
        q = {
            "header": "Permissions",
            "question": f"Make {top['path']} readable by you only? Other users of this machine can read it now (mode {top['mode']}).",
            "explain": "That folder holds the snapshots: every object, event and log line kubegap read from the cluster. kubegap creates it with mode 0700; this one was created by an older kubegap or widened by hand.",
            "gain": ["nothing in the report; the snapshots are readable by your user only"],
            "fix": ("Fix now", f"Runs chmod 700 on {n} folder{'s' if n > 1 else ''} under {top['path']}. Nothing else changes."),
            "leave": ("Leave it", "The folders stay as they are." + _AGAIN["en"]),
        }
    return {
        "id": "home-mode",
        "header": q["header"],
        "question": q["question"],
        "explain": q["explain"],
        "gain": q["gain"],
        "options": [_opt("fix", *q["fix"], run=["protect-home"], remember=False), _opt("leave", *q["leave"])],
        "typed": None,
        "state": {"missing": [d["path"] for d in dirs]},
    }


def _q_tools(setup: dict, cfg: Config, L: str) -> dict | None:
    missing = [t for t in setup.get("tools") or [] if not t["present"] and not t["required"] and t.get("installable")]
    # ssh and aws are not offered on a platform that does not use them
    platform = (setup.get("cluster") or {}).get("platform")
    missing = [t for t in missing if not (t["name"] == "aws" and platform != "eks") and not (t["name"] == "ssh" and platform == "eks")]
    if not missing or cfg.install_policy != "ask":
        return None
    names = [t["name"] for t in missing]
    if L == "ko":
        lines = [f"{t['name']}: {t['role']} — {t.get('checks_text') or ', '.join(t['checks'])} 항목에 쓰여요. 설치 방법: {tools.install_plan(tools.by_name(t['name']))}" for t in missing]
        q = {
            "header": "도구",
            "question": f"이 컴퓨터에 없는 선택 도구가 {len(names)}개 있어요: {', '.join(names)}. 설치할까요?",
            "explain": "도구마다 kubegap이 직접 계산하지 않는 걸 대신 계산해요. 설치는 이 컴퓨터에만 하고, 클러스터에는 아무것도 설치하지 않아요.",
            "install": ("전부 설치", f"{', '.join(names)}를 설치해요. Homebrew가 있으면 그걸로, 없으면 sha256을 확인한 고정 버전으로요."),
            "skip": "이 도구들이 맡은 항목은 '도구 없음'으로 적히거나 입력이 없어 건너뛰어요. 나머지는 전부 돌아가요.",
            "typed": "일부만 설치하려면 도구 이름을 쉼표로 적어 주세요. 그 이름으로 `setup --install-only <이름>`을 돌리고, 나머지는 `skip`으로 기록해요",
        }
    else:
        lines = [f"{t['name']}: {t['role']} — feeds {t.get('checks_text') or ', '.join(t['checks'])}; install: {tools.install_plan(tools.by_name(t['name']))}" for t in missing]
        q = {
            "header": "Tools",
            "question": f"{len(names)} optional tool{'s are' if len(names) > 1 else ' is'} not installed on this machine: {', '.join(names)}. Install?",
            "explain": "Each tool computes something kubegap does not compute itself. They are installed on this machine only; nothing is installed in the cluster.",
            "install": ("Install all", f"Installs {', '.join(names)} (Homebrew, or a pinned release whose sha256 is checked)."),
            "skip": "The checks of these tools are reported as 'tool missing' or skip because their input is not read; everything else runs.",
            "typed": "tool names separated by commas, to install only those: run `setup --install-only <names>`, then record `skip` for the rest",
        }
    return {
        "id": "tools",
        "header": q["header"],
        "question": q["question"],
        "explain": q["explain"],
        "gain": lines,
        "options": [_opt("install", *q["install"], ["setup", "--install-only", ",".join(names)], remember=False), _skip(L, q["skip"])],
        "typed": q["typed"],
        "state": {"missing": names},
    }


def _q_ssm_document(setup: dict, cfg: Config, L: str) -> dict | None:
    doc = ((setup.get("aws") or {}).get("ssm_document")) or {}
    if not (setup.get("cluster") or {}).get("is_eks") or cfg.ssm_document_policy != "ask" or cfg.get("node_access") == "none":
        return None
    if doc.get("present") is None or doc.get("current"):  # unreadable (not offered, the reason is in the setup output) or already there
        return None
    e = (setup.get("cluster") or {}).get("eks") or {}
    new = doc.get("present") is False
    n = node_script_checks()
    if L == "ko":
        q = {
            "header": "노드 점검",
            "question": f"노드 안쪽(디스크, 커널 로그, kubelet 설정)을 읽을까요? AWS 계정 {e.get('account')}, 리전 {e.get('region')}에 문서 하나를 {'올려야' if new else '새 버전으로 바꿔야'} 해요.",
            "explain": "EKS 노드는 SSM으로 읽어요. 노드에서 돌릴 명령은 SSM 문서 kubegap-node-read(deploy/permissions/ssm-document.yaml) 하나에 고정돼 있어요. 그래서 점검용 키로는 그 읽기 명령만 돌릴 수 있고 다른 건 못 해요. 올리는 건 지금 자격 증명으로 호출 한 번이고 ssm:CreateDocument 권한이 필요해요.",
            "gain": [f"full 점검에서 노드 점검 항목이 최대 {n}개 늘어요. Prometheus가 긁지 않는 컴포넌트 메트릭도 노드 쪽에서 읽어요"],
            "upload": ("올리기" if new else "새 버전으로 바꾸기", f"문서 kubegap-node-read를 {'올려요' if new else '새 버전으로 바꿔요'}. 노드에서는 아무것도 바뀌지 않아요."),
            "skip": "노드 점검 항목은 '노드 접근 없음'으로 적혀요.",
        }
    else:
        verb = "upload" if new else "update"
        q = {
            "header": "Node checks",
            "question": f"Read inside the nodes (disk, kernel log, kubelet settings)? It needs one document {verb}ed to AWS account {e.get('account')}, region {e.get('region')}.",
            "explain": "EKS nodes are read through SSM. The commands are fixed in one SSM document, kubegap-node-read (deploy/permissions/ssm-document.yaml), so the audit key can run those read commands and nothing else. The upload is one call with your current credentials and needs ssm:CreateDocument.",
            "gain": [f"up to {n} node checks in a full run, and the node-side read of component metrics that Prometheus does not scrape"],
            "upload": (verb.capitalize(), f"{verb.capitalize()}s the document kubegap-node-read. Nothing on the nodes changes."),
            "skip": "The node checks are reported as 'no node access'.",
        }
    return {
        "id": "ssm-document",
        "header": q["header"],
        "question": q["question"],
        "explain": q["explain"],
        "gain": q["gain"],
        "options": [_opt("upload", *q["upload"], ["setup", "--install-ssm-document"], remember=False), _skip(L, q["skip"])],
        "typed": None,
    }


def _q_node_ssh(setup: dict, cfg: Config, node_access: dict, L: str, *, again: bool = False) -> dict | None:
    c = setup.get("cluster") or {}
    if c.get("platform") not in SSH_PLATFORMS or cfg.get("node_access") not in (None, "", "ssh"):
        return None  # another platform, or a backend named in the config
    probed = (node_access.get("probe") or {}) if node_access.get("method") == "ssh" else {}
    failed = {n: r for n, r in probed.items() if not r.get("ok")}
    n_checks = node_script_checks()
    nodes = c.get("node_count")
    ko = L == "ko"
    gain = (
        [f"full 점검에서 노드 점검 항목이 최대 {n_checks}개 늘어요. Prometheus가 긁지 않는 컴포넌트 메트릭도 노드 쪽에서 읽어요"]
        if ko
        else [f"up to {n_checks} node checks in a full run, and the node-side read of component metrics that Prometheus does not scrape"]
    )
    header = "노드 점검" if ko else "Node checks"
    if not probed and (cfg.get("ssh") or cfg.get("node_access") == "ssh"):
        return None  # the user already wrote how to reach the nodes; nothing to decide
    if not probed or (again and not failed):  # asking again when every node answers: the first form, so the user can still turn it off
        if ko:
            question = f"노드 {nodes}대 안쪽(디스크, 커널 로그, kubelet 설정)을 SSH로 읽을까요?"
            explain = "이 클러스터의 노드는 SSH로 읽어요. 내가 `ssh`를 칠 때 쓰는 사용자와 키를 그대로 써요. '지금 SSH 확인'을 고르면 노드마다 한 번 접속해서 `uname`과 `hostname`만 돌려요. 노드에 아무것도 쓰지 않아요. 고르기 전에는 SSH 접속을 하지 않아요."
            check = ("지금 SSH 확인", "노드마다 한 번 접속해서 어느 노드가 답하는지 알려 줘요. 그다음 점검부터 노드를 SSH로 읽어요.")
            skip = "SSH 접속을 하지 않아요. 노드 점검 항목은 '노드 접근 없음'으로 적혀요."
        else:
            question = f"Read inside the {nodes} node{'s' if nodes != 1 else ''} over SSH (disk, kernel log, kubelet settings)?"
            explain = "On this cluster nodes are read over SSH, with the user and key your own `ssh` would use. Choosing the check connects to each node once and runs `uname` and `hostname`; nothing is written on a node. Until you choose, kubegap makes no SSH connection."
            check = ("Check SSH now", "Connects to every node once and reports which ones answer. Later runs then read the nodes over SSH.")
            skip = "No SSH connection is made. The node checks are reported as 'no node access'."
        return {"id": "node-ssh", "header": header, "question": question, "explain": explain, "gain": gain, "options": [_opt("check", *check, ["nodes"], remember=False), _skip(L, skip)], "typed": None}
    if not failed:
        return None
    kinds = sorted({r.get("kind") or "other" for r in failed.values()})
    opts = []
    if "host-key" in kinds and not (cfg.get("ssh") or {}).get("accept_new_hosts"):
        if ko:
            opts.append(
                _opt(
                    "accept-keys",
                    "호스트 키 받아들이기",
                    "설정 파일에 `ssh.accept_new_hosts: true`를 더해요. 그러면 ssh가 처음 보는 노드의 키를 저장해요. 저장한 키가 나중에 바뀌면 그때는 거부해요.",
                    ["nodes"],
                    remember=False,
                    config=["ssh.accept_new_hosts", "true"],
                )
            )
        else:
            opts.append(
                _opt(
                    "accept-keys",
                    "Accept host keys",
                    "Adds `ssh.accept_new_hosts: true` to the config file, so ssh stores the key of a node it sees for the first time. A stored key that later changes is still refused.",
                    ["nodes"],
                    remember=False,
                    config=["ssh.accept_new_hosts", "true"],
                )
            )
    elif ko:
        opts.append(_opt("check", "다시 확인", "직접 뭔가 고친 뒤에 골라요. 한 번 손으로 로그인했거나 키를 더했을 때요.", ["nodes"], remember=False))
    else:
        opts.append(_opt("check", "Check again", "For after you fixed something yourself (logged in once by hand, added a key).", ["nodes"], remember=False))
    rest = len(probed) - len(failed)
    if rest:
        if ko:
            opts.append(_opt(PARTIAL, "답한 노드만 쓰기", f"답한 노드 {rest}대로 계속해요. {', '.join(sorted(failed))}의 노드 점검 항목은 '노드 접근 없음'으로 적혀요."))
        else:
            opts.append(_opt(PARTIAL, "Use the rest", f"Goes on with the {rest} node{'s' if rest != 1 else ''} that answered. The node checks are 'no node access' for {', '.join(sorted(failed))}."))
    opts.append(_skip(L, "어느 노드에도 SSH 접속을 하지 않아요. 노드 점검 항목은 '노드 접근 없음'으로 적혀요." if ko else "No SSH connection is made to any node. The node checks are reported as 'no node access'."))
    what = "; ".join(f"{n} ({r.get('host')}): {r.get('why')}" for n, r in sorted(failed.items()))
    if ko:
        question = f"노드 {len(probed)}대 중 {len(failed)}대에 SSH가 닿지 않았어요. 어떻게 할까요?"
        explain = "노드별로 안 된 이유예요: " + what
        typed = "나만 아는 값을 항목마다 하나씩 적어 주세요. `<노드>=<주소>`(이 컴퓨터에서 닿는 주소, 예를 들어 Tailscale IP. 로그인 이름이 다르면 `사용자@주소`), `user=<로그인 이름>`, `key=<개인 키 파일 경로>`. 각각 설정 값 `ssh.hosts.<노드>`, `ssh.user`, `ssh.key`로 들어가요. 적고 나면 `nodes`를 다시 돌려요"
    else:
        question = f"SSH did not reach {len(failed)} of {len(probed)} nodes. How do you want to go on?"
        explain = "What failed, per node: " + what
        typed = "values only you know, one per item: `<node>=<address>` (an address this machine can reach, e.g. a Tailscale IP; `user@address` when the login differs), `user=<login>`, `key=<path of the private key>`. Each one is a config value: `ssh.hosts.<node>`, `ssh.user` or `ssh.key`. After they are written, run `nodes` again"
    return {"id": "node-ssh", "header": header, "question": question, "explain": explain, "gain": gain, "options": opts, "typed": typed}


def grafana_without_token(setup: dict) -> dict | None:
    """What a run reads from Grafana without a token: the dashboards and datasources Helm put into ConfigMaps (`setup` counts them,
    `monitoring.grafana.provisioned`). None when nothing is provisioned that way. `unlisted` is how many dashboards exist in Grafana beyond
    the provisioned ones, from Grafana's own metric; None when that metric was not readable."""
    g = (setup.get("monitoring") or {}).get("grafana") or {}
    p = g.get("provisioned") or {}
    dashboards, datasources, total = p.get("dashboards") or 0, p.get("datasources") or 0, p.get("total_dashboards")
    if not dashboards and not datasources:
        return None
    unlisted = max(total - dashboards, 0) if isinstance(total, int) else None
    return {"dashboards": dashboards, "datasources": datasources, "total": total, "unlisted": unlisted}


def _q_grafana_token(setup: dict, cfg: Config, L: str) -> dict | None:
    g = (setup.get("monitoring") or {}).get("grafana") or {}
    if not g.get("ok") or cfg.get("grafana_api_token"):
        return None
    prov = grafana_without_token(setup)
    if prov and not prov["unlisted"]:
        return None  # every dashboard Grafana counts comes from a ConfigMap, which is read without a token; or the count is unreadable and nothing says otherwise
    cfg_path = cfg.path or paths.DEFAULT_CONFIG
    if L == "ko":
        q = {
            "header": "Grafana",
            "question": (
                f"Grafana에 대시보드가 {prov['total']}개 있는데 ConfigMap에서 읽을 수 있는 건 {prov['dashboards']}개예요. 나머지 {prov['unlisted']}개는 Grafana 화면에서 만든 거라 토큰이 있어야 목록에 나와요. 토큰을 넣을까요?"
                if prov
                else "Grafana의 데이터소스 목록과 대시보드 목록도 읽을까요? 읽기 전용 토큰이 하나 필요해요."
            ),
            "explain": "Grafana는 로그인한 쪽에만 이 목록을 보여 줘요. kubegap은 관리자 비밀번호를 읽지 않으니(Secret이에요) 토큰은 직접 만들어 설정 파일에 넣어 주세요. 이 대화에 토큰을 붙여 넣지는 마세요."
            + (" Helm이 ConfigMap으로 넣은 대시보드와 데이터소스는 토큰 없이도 읽어요." if prov else ""),
            "gain": [
                f"Grafana 화면에서 만든 대시보드 {prov['unlisted']}개가 목록과 알림 대조에 들어가요" if prov else "리포트에 데이터소스 목록과 대시보드 목록이 들어가요. grafana.* 점검 항목은 토큰이 없어도 Grafana 자체 메트릭으로 돌아가요"
            ],
            "show": ("방법 보기", "세 단계를 보여 줘요. Grafana와 내 편집기에서 직접 해요."),
            "show_lines": [
                "1. Grafana에 관리자로 들어가서 Viewer 역할의 서비스 계정을 만들고 토큰을 하나 더해요",
                f"2. 내 편집기로 {cfg_path}에 이 줄을 더해요:  grafana_api_token: <토큰>",
                f"3. chmod 600 {cfg_path}",
            ],
            "skip": f"화면에서 만든 대시보드 {prov['unlisted']}개는 목록에 없고, 리포트에 그렇게 적혀요." if prov else "두 목록은 리포트에 '인증 없음'으로 적혀요.",
        }
    else:
        q = {
            "header": "Grafana",
            "question": (
                f"Grafana has {prov['total']} dashboards and {prov['dashboards']} of them can be read from ConfigMaps. The other {prov['unlisted']} were made in Grafana itself and need a token to be listed. Add one?"
                if prov
                else "Read the Grafana datasource and dashboard lists too? It needs one read-only token."
            ),
            "explain": "Grafana answers those lists only to a logged-in caller. kubegap does not read the admin password (it is a Secret), so the token is yours to create and to put in the config file. Do not paste it into this chat."
            + (" The dashboards and datasources Helm put into ConfigMaps are read without one." if prov else ""),
            "gain": [
                f"the {prov['unlisted']} dashboards made in Grafana itself join the list and the alert comparison"
                if prov
                else "the datasource list and the dashboard list in the report; the grafana.* checks run from Grafana's own metrics either way"
            ],
            "show": ("Show how", "Prints the three steps. You do them in Grafana and in your own editor."),
            "show_lines": [
                "1. In Grafana, as an admin, create a service account with the role Viewer and add a token to it",
                f"2. Add this line to {cfg_path} in your own editor:  grafana_api_token: <the token>",
                f"3. chmod 600 {cfg_path}",
            ],
            "skip": f"The {prov['unlisted']} dashboards made in Grafana stay unlisted, and the report says so." if prov else "The two lists read 'no auth' in the report.",
        }
    return {"id": "grafana-token", "header": q["header"], "question": q["question"], "explain": q["explain"], "gain": q["gain"], "options": [_opt("show", *q["show"], show=q["show_lines"]), _skip(L, q["skip"])], "typed": None}


_STORE_GAIN = {
    "en": {
        "prometheus": "every check and figure fed by PromQL: usage against requests over 7 days, restarts, throttling, the control-plane and component metrics",
        "alertmanager": "the alert routing and silence checks",
        "loki": "the log checks that search Loki",
        "grafana": "the Grafana health checks",
    },
    "ko": {
        "prometheus": "PromQL로 보는 점검 항목과 숫자 전부예요. 7일 사용량과 requests 비교, 재시작, 스로틀링, 컨트롤플레인과 컴포넌트 메트릭",
        "alertmanager": "알림 라우팅과 silence 점검 항목",
        "loki": "Loki를 검색하는 로그 점검 항목",
        "grafana": "Grafana 상태 점검 항목",
    },
}


def loki_not_asked(setup: dict, language: str = "en") -> str | None:
    """Why Loki is left out of the stores question: the shipper's configuration says the logs go somewhere else (lib/collection/logsinks.py, #174).
    None when Loki could still be the answer: no shipper was read, or an output points at a Loki."""
    sinks = setup.get("log_sinks") or {}
    goes = sinks.get("logs_go_to") or []
    if not goes or "loki" in goes or sinks.get("loki_outside"):
        return None
    from ..collection import logsinks

    return logsinks.explain(sinks, language)


def _q_stores(setup: dict, cfg: Config, L: str) -> dict | None:
    mon = setup.get("monitoring") or {}
    # only a store with no Service in the cluster. One that was found but did not answer is a failure the setup output shows, not a question
    missing = [k for k in STORES if k in mon and not (mon[k] or {}).get("ok") and (mon[k] or {}).get("access") is None and not cfg.url(k)]
    if "loki" in missing and loki_not_asked(setup, L):
        missing.remove("loki")
    if not missing or mon.get("error") or not (setup.get("cluster") or {}).get("reachable"):
        return None
    outside = (setup.get("log_sinks") or {}).get("loki_outside") if "loki" in missing else None
    if L == "ko":
        q = {
            "header": "모니터링 도구",
            "question": f"클러스터 안에서 {', '.join(missing)}{'을' if len(missing) == 1 else '를'} 찾지 못했어요. 다른 곳에 설치돼 있나요?",
            "explain": "kubegap은 이 도구들을 클러스터 안의 Service로 찾아서 포트포워딩으로 읽어요. 다른 클러스터, 관리형 서비스, VM처럼 밖에서 돌고 있으면 주소를 적어 주면 그 주소로 읽어요."
            + (f" 로그 수집기 설정에 Loki 주소가 적혀 있어요: {outside}. 그 주소가 맞으면 아래에 `loki={outside}`라고 적어 주세요." if outside else ""),
            "gain": [f"{k}: {_STORE_GAIN['ko'][k]}" for k in missing],
            "absent": ("설치 안 함", "그 도구가 필요한 점검 항목은 건너뛰고, 리포트에 그렇게 적어요."),
            "later": ("다음에 다시 묻기", "아무것도 기억하지 않아요."),
            "typed": f"주소를 도구마다 한 줄씩 적어 주세요. `<도구>=<http 주소>` 형식이에요. 예: `{'loki=' + outside if outside else 'prometheus=http://prometheus.example.internal:9090'}`. 각각 설정 값 `<도구>_url`로 들어가요. 적고 나면 `setup`을 다시 돌려요",
        }
    else:
        q = {
            "header": "Stores",
            "question": f"Not found in the cluster: {', '.join(missing)}. {'Is it' if len(missing) == 1 else 'Are they'} installed somewhere else?",
            "explain": "kubegap looks for these as Services in the cluster and port-forwards to them. One that runs elsewhere (another cluster, a managed service, a VM) is read from its address instead."
            + (f" The log shipper's configuration names a Loki at {outside}; if that is the one, type `loki={outside}`." if outside else ""),
            "gain": [f"{k}: {_STORE_GAIN['en'][k]}" for k in missing],
            "absent": ("Not installed", "The checks that need them are skipped and the report says so."),
            "later": ("Ask next time", "Nothing is remembered."),
            "typed": f"the addresses, one per store: `<store>=<http address>`, e.g. `{'loki=' + outside if outside else 'prometheus=http://prometheus.example.internal:9090'}`. Each one is a config value, `<store>_url`. After they are written, run `setup` again",
        }
    return {
        "id": "stores",
        "header": q["header"],
        "question": q["question"],
        "explain": q["explain"],
        "gain": q["gain"],
        "options": [_opt("absent", *q["absent"]), _opt("later", *q["later"], remember=False)],
        "typed": q["typed"],
        "state": {"missing": missing},
    }


def questions(setup: dict, cfg: Config, ctx_dir: Path | None, *, all_: bool = False, language: str = "en") -> list[dict]:
    """The open questions for this context, in the order they are asked, with their texts in `language`. `setup` is the dict `run_setup`
    wrote to setup.json."""
    if not (setup.get("cluster") or {}).get("reachable"):
        return []
    L = language if language in LANGUAGES else "en"
    answers = {} if all_ else load_answers(ctx_dir)
    node_access = _load(ctx_dir, NODE_ACCESS_FILE)
    out = []
    builders = (
        _q_home_mode(setup, cfg, L),
        _q_tools(setup, cfg, L),
        _q_ssm_document(setup, cfg, L),
        _q_node_ssh(setup, cfg, node_access, L, again=all_),
        _q_grafana_token(setup, cfg, L),
        _q_stores(setup, cfg, L),
    )
    for q in builders:
        if q is None:
            continue
        a = answers.get(q["id"])
        if a:
            # a remembered answer closes the question, unless what is missing has grown since (a tool or store that was not missing then)
            now = set((q.get("state") or {}).get("missing") or [])
            then = set((a.get("detail") or {}).get("missing") or [])
            if not now - then:
                continue
        out.append(q)
    return out


def skipped(setup: dict, cfg: Config, ctx_dir: Path | None, *, language: str = "en") -> list[dict]:
    """Questions answered with "skip" whose gap is still there: the report names them in "what this run could not see"."""
    answers = load_answers(ctx_dir)
    return [{"id": q["id"], "header": q["header"], "gain": q["gain"], "at": answers[q["id"]].get("at")} for q in questions(setup, cfg, ctx_dir, all_=True, language=language) if (answers.get(q["id"]) or {}).get("choice") == SKIP]


def noted(setup: dict, cfg: Config, ctx_dir: Path | None, *, language: str = "en") -> list[str]:
    """Things decided without a question, for the report's "what this run could not see": today, Loki left out because the logs go elsewhere."""
    out = []
    why = loki_not_asked(setup, language)
    if why and not cfg.url("loki") and not ((setup.get("monitoring") or {}).get("loki") or {}).get("ok"):
        out.append(f"loki: 묻지 않았어요. {why}. Loki는 읽지 않아요" if language == "ko" else f"loki: not asked. {why}; Loki is not read")
    prov = grafana_without_token(setup)
    if prov and not prov["unlisted"] and not cfg.get("grafana_api_token") and ((setup.get("monitoring") or {}).get("grafana") or {}).get("ok"):
        if language == "ko":
            tail = f"Grafana가 세는 대시보드도 {prov['total']}개라 빠진 게 없어요" if isinstance(prov["total"], int) else "Grafana 전체 개수는 메트릭을 못 읽어 모르고, 화면에서 만든 대시보드가 있으면 목록에 없어요"
            out.append(f"grafana: 토큰 없이 ConfigMap에서 대시보드 {prov['dashboards']}개와 데이터소스 {prov['datasources']}개를 읽어요. {tail}")
        else:
            tail = f"Grafana counts {prov['total']} dashboards too, so none is missing" if isinstance(prov["total"], int) else "the total in Grafana could not be read from its metric, so a dashboard made in Grafana itself would be unlisted"
            out.append(f"grafana: no token needed; {prov['dashboards']} dashboards and {prov['datasources']} datasources are read from ConfigMaps. {tail}")
    return out


_RENDER = {
    "en": {
        "title": "== questions for the user ({n})",
        "none": "  none: nothing is missing, or every question was answered before",
        "config": "   (dry run, show the lines, write only after the user picks Write)",
        "typed": "  typed answer: ",
        "skipped": "skipped earlier",
        "tail": "  -> name these in the report under what this run could not see, with: `/kubegap setup` asks again",
        "note": "note",
        "note_tail": "  -> name these in the report under what this run could not see",
    },
    "ko": {
        "title": "== questions for the user ({n})",
        "none": "  none: 빠진 게 없거나, 질문마다 답이 이미 있어요",
        "config": "   (dry run으로 바뀔 줄을 먼저 보여 주고, 사용자가 '쓰기'를 고른 뒤에만 써요)",
        "typed": "  typed answer: ",
        "skipped": "skipped earlier",
        "tail": "  -> 리포트의 '이번에 못 본 것'에 이 항목을 적고, `/kubegap setup`으로 다시 물을 수 있다고 써요",
        "note": "note",
        "note_tail": "  -> 리포트의 '이번에 못 본 것'에 이 항목을 적어요",
    },
}


def render(qs: list[dict], context: str | None, skipped_items: list[dict] | None = None, notes: list[str] | None = None, *, language: str = "en") -> str:
    """The text block `kubegap setup` and `kubegap questions` print, in the report language. SKILL.md puts it into the choice window as
    printed and never translates it (references/first-run.md says what each line means). The line labels (question, explain, adds,
    option, run, then) stay English in both languages: they are the block's structure, read by the agent, not by the user."""
    cmd = "$KUBEGAP/scripts/kubegap"
    ctx = f" --context {context}" if context else ""
    R = _RENDER[language if language in LANGUAGES else "en"]
    L = [R["title"].format(n=len(qs))]
    if not qs:
        L.append(R["none"])
    for q in qs:
        L.append(f"[{q['id']}] {q['header']}")
        L.append(f"  question: {q['question']}")
        L.append(f"  explain:  {q['explain']}")
        for g in q["gain"]:
            L.append(f"  adds:     {g}")
        for o in q["options"]:
            L.append(f"  option {o['id']}: {o['label']} — {o['description']}")
            if o["config"]:
                L.append(f"      config: {o['config'][0]} {o['config'][1]}{R['config']}")
            if o["run"]:
                L.append(f"      run:  {cmd} {o['run'][0]}{ctx} {' '.join(o['run'][1:])}".rstrip())
            for s in o["show"] or []:
                L.append(f"      show: {s}")
            # a choice that is not remembered also drops an earlier remembered one, so "skip" from last time does not outlive "check now"
            L.append(f"      then: {cmd} answer{ctx} {q['id']} {o['id']}" if o["remember"] else f"      then: {cmd} answer{ctx} {q['id']} --forget")
        if q.get("typed"):
            L.append(f"{R['typed']}{q['typed']}")
    for s in skipped_items or []:
        L.append(f"{R['skipped']} [{s['id']}] {s['header']}: {'; '.join(s['gain'])}")
    if skipped_items:
        L.append(R["tail"])
    for n in notes or []:
        L.append(f"{R['note']} {n}")
    if notes:
        L.append(R["note_tail"])
    return "\n".join(L)
