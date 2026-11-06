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
"""

from __future__ import annotations

import datetime as _dt
import json
from functools import lru_cache
from pathlib import Path

from . import paths, rubric, tools
from .config import Config
from .snapshot import load_json, write_private

MAX_PER_WINDOW = 3
ANSWERS_FILE = "answers.json"
NODE_ACCESS_FILE = "node-access.json"
STORES = ("prometheus", "alertmanager", "loki", "grafana")
SSH_PLATFORMS = ("k3s", "rke2", "unknown")  # the platforms read over SSH; lib/discover._node_access uses this tuple
DAEMONSET_PLATFORMS = ("gke", "aks")  # no SSM, no SSH: the DaemonSet backend is the way in
SKIP = "skip"
PARTIAL = "partial"  # node-ssh: go on with the nodes that answer


# ---------- counts taken from the check catalog ----------


@lru_cache(maxsize=1)
def _checks() -> tuple[dict, ...]:
    cols = sorted(p.name for p in paths.COLLECTORS_DIR.iterdir() if p.is_dir())
    return tuple(rubric.load_checks(cols)[0])


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
    "yes" (lib/discover._node_access): nothing is contacted because of a question that was never answered.
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


def _skip(lost: str) -> dict:
    return _opt(SKIP, "Skip", f"{lost} Not asked again; `/kubegap setup` brings the question back.")


def _q_home_mode(setup: dict, cfg: Config) -> dict | None:
    dirs = (setup.get("machine") or {}).get("open_dirs") or []
    if not dirs:
        return None
    top = dirs[0]
    return {
        "id": "home-mode",
        "header": "Folder permissions",
        "question": f"Make {top['path']} readable by you only? Other users of this machine can read it now (mode {top['mode']}).",
        "explain": "That folder holds the snapshots: every object, event and log line kubegap read from the cluster. kubegap creates it with mode 0700; this one was created by an older kubegap or widened by hand.",
        "gain": ["nothing in the report; the snapshots are readable by your user only"],
        "options": [
            _opt("fix", "Fix now", f"Runs chmod 700 on {len(dirs)} folder{'s' if len(dirs) > 1 else ''} under {top['path']}. Nothing else changes.", run=["protect-home"], remember=False),
            _opt("leave", "Leave it", "The folders stay as they are. Not asked again; `/kubegap setup` brings the question back."),
        ],
        "typed": None,
        "state": {"missing": [d["path"] for d in dirs]},
    }


def _q_tools(setup: dict, cfg: Config) -> dict | None:
    missing = [t for t in setup.get("tools") or [] if not t["present"] and not t["required"] and t.get("installable")]
    # ssh and aws are not offered on a platform that does not use them
    platform = (setup.get("cluster") or {}).get("platform")
    missing = [t for t in missing if not (t["name"] == "aws" and platform != "eks") and not (t["name"] == "ssh" and platform == "eks")]
    if not missing or cfg.install_policy != "ask":
        return None
    names = [t["name"] for t in missing]
    lines = [f"{t['name']}: {t['role']} — feeds {', '.join(t['checks'])}; install: {tools.install_plan(tools.by_name(t['name']))}" for t in missing]
    return {
        "id": "tools",
        "header": "Tools",
        "question": f"{len(names)} optional tool{'s are' if len(names) > 1 else ' is'} not installed on this machine: {', '.join(names)}. Install?",
        "explain": "Each tool computes something kubegap does not compute itself. They are installed on this machine only; nothing is installed in the cluster.",
        "gain": lines,
        "options": [
            _opt("install", "Install all", f"Installs {', '.join(names)} (Homebrew, or a pinned release whose sha256 is checked).", ["setup", "--install-only", ",".join(names)], remember=False),
            _skip("The checks of these tools are reported as 'tool missing'; everything else runs."),
        ],
        "typed": "tool names separated by commas, to install only those: run `setup --install-only <names>`, then record `skip` for the rest",
        "state": {"missing": names},
    }


def _q_ssm_document(setup: dict, cfg: Config) -> dict | None:
    doc = ((setup.get("aws") or {}).get("ssm_document")) or {}
    if not (setup.get("cluster") or {}).get("is_eks") or cfg.ssm_document_policy != "ask" or cfg.get("node_access") == "none":
        return None
    if doc.get("present") is None or doc.get("current"):  # unreadable (not offered, the reason is in the setup output) or already there
        return None
    e = (setup.get("cluster") or {}).get("eks") or {}
    verb = "upload" if doc.get("present") is False else "update"
    return {
        "id": "ssm-document",
        "header": "Node checks",
        "question": f"Read inside the nodes (disk, kernel log, kubelet settings)? It needs one document {verb}ed to AWS account {e.get('account')}, region {e.get('region')}.",
        "explain": "EKS nodes are read through SSM. The commands are fixed in one SSM document, kubegap-node-read (deploy/permissions/ssm-document.yaml), so the audit key can run those read commands and nothing else. The upload is one call with your current credentials and needs ssm:CreateDocument.",
        "gain": [f"up to {node_script_checks()} node checks in a full run, and the node-side read of component metrics that Prometheus does not scrape"],
        "options": [
            _opt("upload", verb.capitalize(), f"{verb.capitalize()}s the document kubegap-node-read. Nothing on the nodes changes.", ["setup", "--install-ssm-document"], remember=False),
            _skip("The node checks are reported as 'no node access'."),
        ],
        "typed": None,
    }


def _q_node_ssh(setup: dict, cfg: Config, node_access: dict, *, again: bool = False) -> dict | None:
    c = setup.get("cluster") or {}
    if c.get("platform") not in SSH_PLATFORMS or cfg.get("node_access") not in (None, "", "ssh") or c.get("node_reader_pods"):
        return None  # another platform, a backend named in the config, or the node DaemonSet is already running and is what gets used
    probed = (node_access.get("probe") or {}) if node_access.get("method") == "ssh" else {}
    failed = {n: r for n, r in probed.items() if not r.get("ok")}
    n_checks = node_script_checks()
    gain = [f"up to {n_checks} node checks in a full run, and the node-side read of component metrics that Prometheus does not scrape"]
    if not probed and (cfg.get("ssh") or cfg.get("node_access") == "ssh"):
        return None  # the user already wrote how to reach the nodes; nothing to decide
    if not probed or (again and not failed):  # asking again when every node answers: the first form, so the user can still turn it off
        return {
            "id": "node-ssh",
            "header": "Node checks",
            "question": f"Read inside the {c.get('node_count')} node{'s' if c.get('node_count') != 1 else ''} over SSH (disk, kernel log, kubelet settings)?",
            "explain": "On this cluster nodes are read over SSH, with the user and key your own `ssh` would use. Choosing the check connects to each node once and runs `uname` and `hostname`; nothing is written on a node. Until you choose, kubegap makes no SSH connection.",
            "gain": gain,
            "options": [
                _opt("check", "Check SSH now", "Connects to every node once and reports which ones answer. Later runs then read the nodes over SSH.", ["nodes"], remember=False),
                _skip("No SSH connection is made. The node checks are reported as 'no node access'."),
            ],
            "typed": None,
        }
    if not failed:
        return None
    kinds = sorted({r.get("kind") or "other" for r in failed.values()})
    opts = []
    if "host-key" in kinds and not (cfg.get("ssh") or {}).get("accept_new_hosts"):
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
    else:
        opts.append(_opt("check", "Check again", "For after you fixed something yourself (logged in once by hand, added a key).", ["nodes"], remember=False))
    if len(failed) < len(probed):
        opts.append(_opt(PARTIAL, "Use the rest", f"Goes on with the {len(probed) - len(failed)} node{'s' if len(probed) - len(failed) != 1 else ''} that answered. The node checks are 'no node access' for {', '.join(sorted(failed))}."))
    opts.append(_skip("No SSH connection is made to any node. The node checks are reported as 'no node access'."))
    return {
        "id": "node-ssh",
        "header": "Node checks",
        "question": f"SSH did not reach {len(failed)} of {len(probed)} nodes. How do you want to go on?",
        "explain": "What failed, per node: " + "; ".join(f"{n} ({r.get('host')}): {r.get('why')}" for n, r in sorted(failed.items())),
        "gain": gain,
        "options": opts,
        "typed": "values only you know, one per item: `<node>=<address>` (an address this machine can reach, e.g. a Tailscale IP; `user@address` when the login differs), `user=<login>`, `key=<path of the private key>`. Each one is a config value: `ssh.hosts.<node>`, `ssh.user` or `ssh.key`. After they are written, run `nodes` again",
    }


def _q_node_daemonset(setup: dict, cfg: Config) -> dict | None:
    c = setup.get("cluster") or {}
    if c.get("platform") not in DAEMONSET_PLATFORMS or cfg.get("node_access") or c.get("node_reader_pods"):
        return None  # already applied: the pods are found and used, nothing to ask
    return {
        "id": "node-daemonset",
        "header": "Node checks",
        "question": "Read inside the nodes (disk, kernel log, kubelet settings)? On this platform it needs a small DaemonSet that you apply yourself.",
        "explain": "kubegap never writes to a cluster, so it will not apply this for you. The DaemonSet runs one privileged pod per node; once its pods run, kubegap reads each node through `kubectl exec`. You can delete it after the audit.",
        "gain": [f"up to {node_script_checks()} node checks in a full run"],
        "options": [
            _opt(
                "show",
                "Show the commands",
                "Prints the two commands to apply and the one to remove it. The next run finds the pods by itself.",
                show=[
                    f"kubectl apply -f {paths.ROOT / 'deploy/node-access/daemonset.yaml'}",
                    f"kubectl apply -f {paths.ROOT / 'deploy/permissions/role-daemonset-exec.yaml'}",
                    "# to remove it afterwards: kubectl delete namespace kubegap",
                ],
            ),
            _skip("Nothing is applied, so no node is read. The node checks are reported as 'no node access'."),
        ],
        "typed": None,
    }


def _q_grafana_token(setup: dict, cfg: Config) -> dict | None:
    g = (setup.get("monitoring") or {}).get("grafana") or {}
    if not g.get("ok") or cfg.get("grafana_api_token"):
        return None
    cfg_path = cfg.path or paths.DEFAULT_CONFIG
    return {
        "id": "grafana-token",
        "header": "Grafana",
        "question": "Read the Grafana datasource and dashboard lists? It needs a read-only Grafana token that you create.",
        "explain": "Grafana answers those two lists only to a logged-in caller. kubegap does not read the admin password (it is a Secret), so the token is yours to create and to put in the config file. Do not paste it into this chat.",
        "gain": ["the datasource list and the dashboard list in the report; the grafana.* checks run from Grafana's own metrics either way"],
        "options": [
            _opt(
                "show",
                "Show how",
                "Prints the three steps. You do them in Grafana and in your own editor.",
                show=[
                    "1. In Grafana, as an admin, create a service account with the role Viewer and add a token to it",
                    f"2. Add this line to {cfg_path} in your own editor:  grafana_api_token: <the token>",
                    f"3. chmod 600 {cfg_path}",
                ],
            ),
            _skip("The two lists read 'no auth' in the report."),
        ],
        "typed": None,
    }


_STORE_GAIN = {
    "prometheus": "every check and figure fed by PromQL: usage against requests over 7 days, restarts, throttling, the control-plane and component metrics",
    "alertmanager": "the alert routing and silence checks",
    "loki": "the log checks that search Loki",
    "grafana": "the Grafana health checks",
}


def _q_stores(setup: dict, cfg: Config) -> dict | None:
    mon = setup.get("monitoring") or {}
    # only a store with no Service in the cluster. One that was found but did not answer is a failure the setup output shows, not a question
    missing = [k for k in STORES if k in mon and not (mon[k] or {}).get("ok") and (mon[k] or {}).get("access") is None and not cfg.url(k)]
    if not missing or mon.get("error") or not (setup.get("cluster") or {}).get("reachable"):
        return None
    return {
        "id": "stores",
        "header": "Stores",
        "question": f"Not found in the cluster: {', '.join(missing)}. {'Is it' if len(missing) == 1 else 'Are they'} installed somewhere else?",
        "explain": "kubegap looks for these as Services in the cluster and port-forwards to them. One that runs elsewhere (another cluster, a managed service, a VM) is read from its address instead.",
        "gain": [f"{k}: {_STORE_GAIN[k]}" for k in missing],
        "options": [
            _opt("absent", "Not installed", "The checks that need them are skipped and the report says so."),
            _opt("later", "Ask next time", "Nothing is remembered.", remember=False),
        ],
        "typed": "the addresses, one per store: `<store>=<http address>`, e.g. `prometheus=http://prometheus.example.internal:9090`. Each one is a config value, `<store>_url`. After they are written, run `setup` again",
        "state": {"missing": missing},
    }


def questions(setup: dict, cfg: Config, ctx_dir: Path | None, *, all_: bool = False) -> list[dict]:
    """The open questions for this context, in the order they are asked. `setup` is the dict `run_setup` wrote to setup.json."""
    if not (setup.get("cluster") or {}).get("reachable"):
        return []
    answers = {} if all_ else load_answers(ctx_dir)
    node_access = _load(ctx_dir, NODE_ACCESS_FILE)
    out = []
    for q in (_q_home_mode(setup, cfg), _q_tools(setup, cfg), _q_ssm_document(setup, cfg), _q_node_ssh(setup, cfg, node_access, again=all_), _q_node_daemonset(setup, cfg), _q_grafana_token(setup, cfg), _q_stores(setup, cfg)):
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


def skipped(setup: dict, cfg: Config, ctx_dir: Path | None) -> list[dict]:
    """Questions answered with "skip" whose gap is still there: the report names them in "what this run could not see"."""
    answers = load_answers(ctx_dir)
    return [{"id": q["id"], "header": q["header"], "gain": q["gain"], "at": answers[q["id"]].get("at")} for q in questions(setup, cfg, ctx_dir, all_=True) if (answers.get(q["id"]) or {}).get("choice") == SKIP]


def render(qs: list[dict], context: str | None, skipped_items: list[dict] | None = None) -> str:
    """The text block `kubegap setup` and `kubegap questions` print. SKILL.md reads it to fill the choice window
    (references/first-run.md says what each line means)."""
    cmd = "$KUBEGAP/scripts/kubegap"
    ctx = f" --context {context}" if context else ""
    L = [f"== questions for the user ({len(qs)})"]
    if not qs:
        L.append("  none: nothing is missing, or every question was answered before")
    for q in qs:
        L.append(f"[{q['id']}] {q['header']}")
        L.append(f"  question: {q['question']}")
        L.append(f"  explain:  {q['explain']}")
        for g in q["gain"]:
            L.append(f"  adds:     {g}")
        for o in q["options"]:
            L.append(f"  option {o['id']}: {o['label']} — {o['description']}")
            if o["config"]:
                L.append(f"      config: {o['config'][0]} {o['config'][1]}   (dry run, show the lines, write only after the user picks Write)")
            if o["run"]:
                L.append(f"      run:  {cmd} {o['run'][0]}{ctx} {' '.join(o['run'][1:])}".rstrip())
            for s in o["show"] or []:
                L.append(f"      show: {s}")
            # a choice that is not remembered also drops an earlier remembered one, so "skip" from last time does not outlive "check now"
            L.append(f"      then: {cmd} answer{ctx} {q['id']} {o['id']}" if o["remember"] else f"      then: {cmd} answer{ctx} {q['id']} --forget")
        if q.get("typed"):
            L.append(f"  typed answer: {q['typed']}")
    for s in skipped_items or []:
        L.append(f"skipped earlier [{s['id']}] {s['header']}: {'; '.join(s['gain'])}")
    if skipped_items:
        L.append("  -> name these in the report under what this run could not see, with: `/kubegap setup` asks again")
    return "\n".join(L)
