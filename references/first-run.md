# First-run questions — how to ask and what to do with each answer

This file is the detail of `SKILL.md` section 2. Read it when the `setup` output has a `== questions for the user (N)` block with N above 0, when a required tool is missing, or when the user ran `/kubegap setup`. A run whose block says 0 does not need it.

The aim: a person who has never read the documentation can run `/kubegap`, read one short explanation per missing thing, pick, and get a report. Nobody should have to open a config file or a setup chapter to get started.

## 1. Every question is a choice the user picks

Ask through the host's choice window, the tool that shows options the user selects with the arrow keys:

| Host | Tool | Limits |
|---|---|---|
| Claude Code | `AskUserQuestion` | up to 4 questions per window, 2–4 options each |
| Codex | `request_user_input` | up to 3 questions per window, 2–3 options each. Listed in Plan mode; in Default mode only when the user enabled `default_mode_request_user_input` (`openai/codex` `codex-rs/protocol/src/config_types.rs:700-702@rust-v0.164.0`, `codex-rs/features/src/lib.rs:1868-1871@rust-v0.164.0`) |

Both add a free-text entry to every question by themselves, and the user types into it inside the same window. Do not add an "Other" option of your own.

- **At most 3 questions per window**, in the order the block lists them. More than 3: a second window after the first is answered.
- **Never write a question as a chat message that the user answers by typing**, as long as the choice tool is listed among your tools. The user asked to pick, not to type.
- If the host has no choice tool in this session (Codex in Default mode without the feature, another host), write the same questions once as a numbered list, each with its lettered options, and tell the user the one line that turns the window on for next time when you know it (Codex: `codex --enable default_mode_request_user_input`, `codex-rs/cli/src/main.rs:965-966@rust-v0.164.0`).
- Translate the texts when the report language is Korean. Keep ids, commands, paths and node names as they are.

## 2. From the block to the window

`setup` prints one entry per open question:

```
[node-ssh] Node checks
  question: Read inside the 2 nodes over SSH (disk, kernel log, kubelet settings)?
  explain:  On this cluster nodes are read over SSH, with the user and key your own `ssh` would use. …
  adds:     up to 26 node checks in a full run, and the node-side read of component metrics that Prometheus does not scrape
  option check: Check SSH now — Connects to every node once and reports which ones answer.
      run:  $KUBEGAP/scripts/kubegap nodes --context default
  option skip: Skip — No SSH connection is made. The node checks are reported as 'no node access'. …
      then: $KUBEGAP/scripts/kubegap answer --context default node-ssh skip
  typed answer: …
```

| Block line | Where it goes |
|---|---|
| `[id] header` | the short header of the question |
| `question` | the question text. Add the `explain` sentence and the `adds` lines to it, so the user reads what the thing is and what answering adds before picking. Do not shorten the numbers and do not add any of your own |
| `option <id>: <label> — <description>` | one option: label and description as printed |
| `config:`, `run:`, `show:`, `then:` under an option | what to do after the user picked that option (section 3). They are not shown in the window |
| `typed answer` | what the free-text entry means for this question. Mention it in the question text in a few words ("or type the addresses") |

Every explanation, count and option comes from the block. Do not invent a question, an option or a number of checks; if something you would like to ask is not in the block, it is not asked. The only questions outside the block are the two this file names: Write / Don't write before a config value is written (section 3) and Install / Stop for a missing required tool (section 5).

## 3. After the user picks

For each answered question, in order:

1. **`config:` under the chosen option** — the choice puts that key and value into the config file. Write it the way step 5 says: dry run, show the lines, Write / Don't write. If the user picks Don't write, stop here for this question and leave it open.
2. **`run:` under the chosen option** — run that command. Together with a `config:` line it is the only thing the choice authorizes.
3. **`show:` lines** — print them for the user exactly as given. The user acts on them (applies a manifest, creates a token); you do not.
4. **`then:`** — run it, always. For most options it remembers the choice so the question does not come back. For an option that acts (`answer … --forget`) it drops a choice remembered earlier, so a "skip" from last time does not outlive "check now".
5. **A typed answer** — follow the `typed answer` line of that question. It names the config keys the typed values belong to. Every value that goes into the config file is written with `config set`, in two steps:
   ```bash
   $KUBEGAP/scripts/kubegap config set <key> <value> --dry-run   # prints the lines that would change
   ```
   Show the printed lines and ask in the choice window: "Write this to `<path>`?" with the options Write / Don't write. Only after Write:
   ```bash
   $KUBEGAP/scripts/kubegap config set <key> <value>
   ```
   Several values from one answer: one dry run each, shown together, one Write / Don't write question for all of them. Never edit the config file with the file tools, and never put `grafana_api_token` on a command line (the command refuses it; the user adds that line by hand).
6. Then list what is still open, without touching the cluster again:
   ```bash
   $KUBEGAP/scripts/kubegap questions --context <name>
   ```
   A choice can open a follow-up (the SSH check found nodes that do not answer; a tool failed to install). Ask what the new block lists, the same way. When it says 0, go on to collection. If `run:` was a `setup …` command, its own output already ends with the block; use that.

A question the user closes without choosing (escape, an empty answer) counts as "ask next time": run nothing, remember nothing, go on. Nothing is installed, uploaded or contacted for a question that was not answered; on an SSH platform that means no SSH connection, and the report says "no node access".

## 4. What each question does

| id | Asked when | Choices | Skipping costs |
|---|---|---|---|
| `home-mode` | a folder under `~/.kubegap` is readable by other users (setup.json `machine.open_dirs`) | Fix now (`protect-home`, chmod 700 on those folders, not remembered because the gap is gone) · Leave it | nothing in the report; the snapshots stay readable by other users of the machine |
| `tools` | optional tools are not on this machine and `install_tools` is `ask` | Install all (`setup --install-only` with the names listed) · Skip · typed: names to install only those (`setup --install-only a,b`, then `answer tools skip` for the rest) | the checks of those tools are reported as "tool missing" |
| `ssm-document` | EKS, and the SSM document `kubegap-node-read` is missing or older than the local file | Upload or Update (`setup --install-ssm-document`) · Skip | the node checks are "no node access" |
| `node-ssh` | k3s, RKE2 or an unrecognized platform, no `ssh:` block in the config, and the node DaemonSet is not running | Check SSH now (`nodes`) · Skip. After a check with failures: Accept host keys (a config value, then `nodes`) or Check again · Use the rest, when some nodes answered · Skip · typed: `<node>=<address>`, `user=<login>`, `key=<path>` | no SSH connection is made; the node checks are "no node access" |
| `node-daemonset` | GKE or AKS, and the node DaemonSet is not running | Show the commands (the user applies the DaemonSet) · Skip | the node checks are "no node access" |
| `grafana-token` | Grafana was found and the config has no `grafana_api_token` | Show how (the user creates the token and adds the line) · Skip | the datasource and dashboard lists read "no auth" |
| `stores` | Prometheus, Alertmanager, Loki or Grafana has no Service in the cluster and no URL in the config | Not installed · Ask next time · typed: `<store>=<address>` | the checks that need that store are skipped |

`ssm_document: always|never`, `install_tools: always|never`, `node_access: none`, a `<store>_url` and `grafana_api_token` in the config answer the matching question for good, and it is never listed.

## 5. Things that are not optional

- **A required tool (kubectl, jq, python3) is missing.** `setup` ends with "Not ready". Ask in the choice window: "The audit cannot run without `<tool>`. Install it?" with Install (`setup --install-only <tool>`) / Stop. Stop ends the run.
- **"Not ready: cluster access failed".** Show the reason and stop. There is nothing to choose.
- **The SSM document line shows FAIL.** The document could not be read (expired credentials, missing `ssm:DescribeDocument`, wrong region). No question is listed for it; show the reason and go on. Node checks are skipped.
- **The AWS permission block has a FAIL.** Do not stop; note that the EKS platform, control-plane log and SSM checks will not run.

## 6. `/kubegap setup`

The user wants to see the questions again, including the ones answered or skipped before. Run language and context as usual, then:

```bash
$KUBEGAP/scripts/kubegap setup --context <name> --ask-again
```

Keep this first list and work through all of it, three questions per window; act on the answers as above. After an action, `questions` without `--all` shows only follow-ups, so do not replace your list with its output. Stop after the last question with one line per question: what was chosen. Do not collect and do not write a report.

## 7. Nobody to answer (headless)

In a headless run (`claude -p`, `codex exec`, a schedule) there is no window and nobody to pick. Treat every listed question as "ask next time": run nothing, remember nothing, write nothing to the config, go on to collection. If `setup` ends with "Not ready" (a required tool is missing, the cluster is unreachable), stop with that reason. The gap stays visible in the report as "no node access", "tool missing" or "no auth". Only the two questions without which the run cannot be trusted stop a headless run: the report language and the context (SKILL.md section 0).

## 8. In the report

`setup` and `questions` end with `skipped earlier [...]` lines for the questions the user skipped while the gap is still there. Name each of them in "What this run could not see" with what it would add, and end that sentence with: `/kubegap setup` asks again.
