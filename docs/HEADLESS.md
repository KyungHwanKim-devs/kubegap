# Headless and scheduled runs

`/kubegap` is written for an interactive session: it asks the report language, confirms the kube context and, on a first run, asks about anything the cluster or the machine is missing, then runs through to the report. Nothing in it needs a person at the keyboard once the language and the context are known. This page shows how to run the same skill without a terminal open, with `claude -p` or `codex exec`, and how to put that on a daily schedule.

Two things stay the same as in an interactive run. kubegap is read-only toward the cluster and never reads Secret values. What the agent reads from the snapshot goes to that agent's model API, as [`DATA.md`](DATA.md) describes.

One thing the skill will not do for you. A session never creates or edits a crontab entry, a systemd timer, a CronJob or a CI job on its own. SKILL.md section 9 says so. You write the schedule, with the lines below as a start.

## 1. Answer the questions in advance

Two questions must be answered or the run stops: the report language and the cluster. The first-run questions about missing things are optional: in a headless run each one is left open and the run goes on without it, so decide them here if you want them. Put the keys in `~/.kubegap/config.yaml`:

```yaml
language: en              # or ko. Otherwise the skill asks
context: prod             # the kube context to audit
confirm_context: false    # do not ask "audit this context?". Passing --context on the command line also skips it
install_tools: never      # or always. ask, the default, leaves missing tools out in a headless run
node_access: ssh          # k3s and other SSH platforms: read the nodes over SSH. Without a decision no node is contacted. none = never
ssm_document: never       # EKS only. never = node OS checks are skipped if the SSM document is missing; always = upload it without asking
```

Pass `--context <name>` on the command line as well, even with `context` in the config. A scheduled job that audits the wrong cluster is the mistake the context question exists to prevent, and the explicit flag is the one place a reader of the crontab sees which cluster the job touches.

If the language or the cluster is still open in a headless run, the skill names the key that would have answered it and stops. The run is then visible in the log as a stop, not as a report that silently guessed. An open first-run question does not stop the run: nothing is installed, uploaded or contacted for it, and the report names what was left out. `scripts/kubegap config set <key> <value>` writes every key above except `context`, which you add to the file yourself.

## 2. The headless commands

Claude Code. `-p` prints the result and exits. The skill needs the shell and file tools, so allow them for the run; this is narrower than `--dangerously-skip-permissions`, which is not needed:

```bash
claude -p "/kubegap daily --context prod" --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch"
```

Codex. `codex exec` runs one prompt and exits. The default sandbox has no network and writes only inside the working directory, but the audit talks to the API server, port-forwards Prometheus and Loki, calls the AWS CLI on EKS and writes the snapshot under `~/.kubegap/`. So the sandbox has to be opened for this process; the sandbox setting is about what the agent may touch on your machine, and the read-only rules toward the cluster apply unchanged:

```bash
codex exec --sandbox danger-full-access --skip-git-repo-check -C ~ \
  -o ~/.kubegap/last-run.md '$kubegap daily --context prod'
```

Single quotes keep the shell from expanding `$kubegap`, which is how a Codex skill is named in a prompt. `-o` saves the agent's final message, the briefing the skill prints after saving the report, to a file you can read or forward.

The report itself is written by further agents that the run starts with the same CLI, one `claude -p` or `codex exec` per step: a step checker that reads the objects, a writer, a fact checker, and a replacer for the sentences the fact checker named. They use the same login, get no shell, and write nothing but their answer. Inside a Codex sandbox that does not allow this, such as `workspace-write`, the skill does those steps itself and says so in its briefing.

Run the command once by hand before scheduling it. The first run installs optional tools, if `install_tools: always`, and on EKS may need the SSM document, and both are easier to watch than to debug from a cron log.

## 3. A cron example

```cron
# crontab -e
# cron does not read your shell profile: give it the directories where claude, kubectl, aws and jq live, and the kubeconfig
PATH=/opt/homebrew/bin:/usr/local/bin:/home/me/.local/bin:/usr/bin:/bin
KUBECONFIG=/home/me/.kube/config

# daily audit on weekdays at 08:30, one at a time
30 8 * * 1-5  flock -n /tmp/kubegap-prod.lock claude -p "/kubegap daily --context prod" --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch" >> /home/me/.kubegap/cron.log 2>&1

# full audit on Sunday night
0 22 * * 0    flock -n /tmp/kubegap-prod.lock claude -p "/kubegap full --context prod" --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch" >> /home/me/.kubegap/cron.log 2>&1

# keep the last 14 daily and 4 full snapshots; a full snapshot is about 40 MB
0 23 * * 0    /home/me/src/kubegap/scripts/kubegap prune --context prod --keep-daily 14 --keep-full 4 >> /home/me/.kubegap/cron.log 2>&1
```

Replace `claude -p …` with the `codex exec …` line above for Codex. Write absolute paths; most cron implementations do not expand `$HOME` or `~` in the environment lines. `flock -n` skips a run while the previous one is still running; on macOS, where `flock` is not installed by default, drop it or use `brew install flock`.

Credentials have to work without a browser. `claude` and `codex` must already be logged in on that machine, or take an API key from the environment. On EKS, an AWS profile whose credentials expire, such as SSO, will fail the first morning after the session ends; use a profile backed by long-lived or instance credentials for the scheduled job.

## 4. Where the report lands

Every run writes one folder, `~/.kubegap/snapshots/<context>/<YYYY-MM-DDTHH-MM-SS>/`, with `report.md`, `report-details.md` and the collected data. The newest report of a context:

```bash
cat "$(ls -dt ~/.kubegap/snapshots/prod/*/ | head -1)report.md"
```

The daily report compares against the previous daily snapshot, so a scheduled daily run gives the "what changed since yesterday" section every morning without further setup. `scripts/kubegap prune` and the `retention` keys in `config.example.yaml` keep the folder from growing without bound.
