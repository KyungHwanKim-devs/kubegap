---
name: kubegap
description: Kubernetes cluster operations gap audit — /kubegap [daily|full|focus <area>|explain <finding-id>] [--context <name>] [--profile <name>] [--namespace <ns>] [--snapshot <date>] [--compare <A> <B>]. Collects, summarizes and first-pass evaluates the cluster of the current kube context, then the LLM analyzes the result and writes a Markdown report. daily (default) is a short run compared with the previous daily run; full collects everything and writes the full report. Also use this skill for "audit my cluster", "operations audit", "what changed since last run", "explain this finding". EKS is the baseline; a small k3s cluster is a variant.
compatibility: "Tested with Claude Code and Codex; usable in any Agent Skills host with a shell tool. Requires kubectl and python3 (3.11+). Optional: aws (EKS), ssh (k3s nodes), krr, polaris, pluto. Uses read-only cluster access (no command that changes the cluster, no Secret values read); node access via SSM or SSH. Snapshots are stored under ~/.kubegap/"
metadata:
  version: "0.1.0"
  author: KyungHwanKim-devs
  rubric_version: "0.1.51"
---

# /kubegap — cluster operations gap audit

This document is the procedure the LLM (this session) follows. It is deliberately not thin. Collection, summary and first-pass evaluation are done by a deterministic script (`scripts/kubegap`); **judgment and the report are done here**. The script only emits a first-pass status (pass/warn/fail); the final severity, priority, conflict resolution and comparison narrative belong to this procedure.

## 0. What to know before starting

- **Language.** The repository, CLI output, check definitions and templates are English. Before anything else, decide the report language: if `~/.kubegap/config.yaml` has `language: en` or `language: ko`, use it without asking. Otherwise ask the user once: "Which language do you want for the briefing and the report? English / 한국어" and remember the answer for this run (suggest adding `language:` to the config to skip the question next time). If Korean is chosen, write ALL messages to the user and both report files in Korean, translating the template headings and the check names, evidence, why and suggest text while writing (check definitions stay English in the repository); keep check ids, file paths, commands, metric names and resource names untouched. If English is chosen, write everything in English.
- **Six principles.** Read-only (never run a command that changes the cluster). Secret values are never read by any path. The baseline environment is EKS; k3s is a variant. Code gives the first-pass status, the LLM gives the final judgment. Read the summary first and open raw files directly from the snapshot folder. There is no score, only counts per severity.
- **Finding the skill folder.** Resolve the repository path with the command below; every later command is called as `$KUBEGAP/scripts/kubegap …` (it points at the real folder even when installed through a symlink). It looks in the usual skill directories of Claude Code and other Agent Skills hosts; if your host unpacked the skill elsewhere, set `KUBEGAP` to that folder by hand. The command stops with a message instead of silently falling back to the current directory.
  ```bash
  KUBEGAP="$(python3 -c 'import os,sys; print(os.path.dirname(os.path.realpath(sys.argv[1])))' "$(ls -d ~/.claude/skills/kubegap/SKILL.md .claude/skills/kubegap/SKILL.md .agents/skills/kubegap/SKILL.md ~/.agents/skills/kubegap/SKILL.md .github/skills/kubegap/SKILL.md ~/.copilot/skills/kubegap/SKILL.md ~/.cursor/skills/kubegap/SKILL.md 2>/dev/null | head -1)")"
  test -x "$KUBEGAP/scripts/kubegap" || { echo "kubegap: skill folder not found (install it as a folder named kubegap, see README)"; false; }
  ```
- **Argument parsing.** Read the arguments the user typed after the skill name (Claude Code exposes them as `$ARGUMENTS`; other hosts pass them as plain text) as follows. Mode: `daily` (default) collects with `--mode daily` (no node scripts, CloudWatch, cost, ECR or slow tools; roughly half the time), compares with the previous **daily** snapshot and writes the one-file daily report; `full` collects everything, compares with the previous **full** snapshot and writes the full report plus the short version. Scope within a mode: `focus <area>` (one of the 12 areas, in depth) / `explain <finding-id>` (read one finding down to the raw files and explain it). Remember the mode as `$MODE` and pass it to every command below. Options: `--context <name>` (default: current context), `--profile` (override the detected profile), `--namespace <ns>` (narrows **analysis and report scope only**; collection is always cluster-wide), `--snapshot <date|latest>` (analyze that snapshot instead of collecting anew; useful when repeating `explain`), `--compare <A> <B>` (the comparison section covers these two dates instead of the immediately preceding snapshot).
- **The user is asked at only three points (language above, step 1, step 2).** After that, proceed to saving the report without intermediate confirmations. If the user turns a question off in the config, skip it too.
- **Snapshot location.** Default `~/.kubegap/snapshots/<context>/<YYYY-MM-DDTHH-MM-SS>/` (outside the skill folder, so cluster data never accumulates in the skill repository; override with the `$KUBEGAP_SNAPSHOTS` environment variable, `snapshots_root` in config, or `--snapshots-root`). The context folder holds `setup.json` and `history.csv`. An `INCOMPLETE` file in a snapshot folder means collect did not finish: that snapshot is automatically excluded from `latest` and from comparison baselines, and if you analyze it anyway, write "collection incomplete" in report section 7-1. `_summary{collectors[], steps, failed[], skipped[], seconds_total}` in `collect-result.json` is the top-level summary of collection success (per-collector detail is under the keys below it).

## 1. Context confirmation (question 1)

If `--context` was given explicitly, or `~/.kubegap/config.yaml` (falling back to `$KUBEGAP/config.yaml`) has `confirm_context: false`, skip this. Otherwise:

```bash
$KUBEGAP/scripts/kubegap contexts
```

Show the user the current context marked with `*` and the cluster it points to (for EKS: cluster name, region, AWS profile; otherwise the server address) and ask **once**: "Audit the current context `<name>` (<cluster description>)?" If yes, continue. If no, show the context list as-is, say "pick one with `/kubegap --context <name>`" and **stop**.

Add `--context <name>` to every later `scripts/kubegap` command. Always state which context and cluster were audited in the report header and in the first line of the conversation. This guards against auditing a company cluster when the small k3s cluster was intended.

## 2. Dependency check and install consent (question 2)

```bash
$KUBEGAP/scripts/kubegap setup --context <name>
```

Check only (no install). Read the result and:

- **If a required tool (kubectl, jq, python3) is missing**, ask "The audit cannot run without this tool. Install it?" and stop if the user declines.
- **If optional tools are missing**, show the "missing tools" block of the output as a table: tool, role, checks that are skipped without it, install method and location (brew, a GitHub release binary downloaded into `.tools/bin/` inside the repository, or a dedicated Python virtualenv). Then ask **once**: "Install them? (all / choose / none)". All: `setup --install`; choose: `setup --install-only a,b`; none: continue as-is. Remember the checks owned by declined or failed tools and list them in report section 6 "tool missing".
- If `install_tools` in `config.yaml` is `always`, run `setup --install` without asking; if `never`, skip without asking.
- If `setup` reports "not ready: cluster access failed", show the reason to the user and stop. If the fourth block (AWS permissions) fails, do not stop; note that "EKS platform, control-plane log and SSM checks will not run" and continue.
- **EKS only: the SSM document.** Node OS commands run through the SSM document `kubegap-node-read` (deploy/permissions/ssm-document.yaml), which must exist in the account. If the fourth block shows it as MISSING or OUTDATED, ask **once**: "kubegap reads EKS nodes through an SSM document that pins its read-only commands. Upload (or update) `kubegap-node-read` in account <account>, region <region>? This one call needs `ssm:CreateDocument` on your current credentials." Yes: `setup --install-ssm-document`. No: continue; node OS checks (`node.*`) will be reported as "no node access" with the reason. If `ssm_document` in `config.yaml` is `always`, upload without asking; if `never`, skip without asking.

Supported environments are macOS (Apple Silicon and Intel), Linux (amd64, arm64) and Windows inside WSL2. On native Windows `scripts/kubegap` refuses to run by itself.

## 3. Detection and collection

If `--snapshot` was given, skip this section and use that snapshot (`$KUBEGAP/scripts/kubegap snapshots --context <name>` lists them). Otherwise:

```bash
$KUBEGAP/scripts/kubegap collect --context <name> --mode "$MODE" [--profile <p>]
```

Detection (`inventory.json`) and collection (`objects/`, `events.json`, `metrics/`, `aws/`) land in one snapshot folder. The last output line "saved: <path>" is this run's snapshot `$SNAP`. Measured on real clusters: a daily run takes about 135 seconds on an 8-node EKS cluster and about 120 seconds on a 2-node small k3s cluster (collectors run four at a time); a full run adds the steps marked `modes: [full]` in collect.yaml (node scripts, CloudWatch, cost, ECR, krr and the other tools) and took 730–820 seconds on EKS before collectors ran in parallel. A full EKS run may still exceed the foreground time limit most agent shells impose (600 seconds in Claude Code), so start `collect` detached (in Claude Code: the Bash tool with `run_in_background`; elsewhere `nohup … &`) (it refuses if another collection is in progress for the same context — wait for it or use `--force`) and wait until the `INCOMPLETE` file disappears (the wait itself is a background `until` loop). While collecting, only wait. If the output contains "failed", remember which command failed and why for report section 7-1. Do not abort.

## 4. Summary and first-pass evaluation

```bash
$KUBEGAP/scripts/kubegap summarize --context <name> --snapshot "$SNAP"
$KUBEGAP/scripts/kubegap evaluate  --context <name> --snapshot "$SNAP" [--profile <p>]
$KUBEGAP/scripts/kubegap diff      --context <name> --mode "$MODE"      # no positional arguments = compare the latest snapshot of this mode with the previous one of the same mode (daily with daily, full with full). If there is none, it says so and only history.csv is updated: the report then states "No earlier <mode> snapshot to compare with." — nothing more
```

Caution: if `diff` gets a single positional argument, it is read as A (the earlier snapshot) and B becomes latest, which fails with "A and B are the same snapshot" (this has actually happened). When analyzing an older snapshot via `--snapshot`, pass both, as in `diff --context <name> <the snapshot before> <that snapshot>`. If `--compare A B` was given, run `diff --context <name> <A> <B>`. If the `evaluate` output shows "errors N" with N not 0, list the checks with `status: error` in `findings-draft.json` `check_results` and their reasons in report section 7-2.

## 5. Analysis — reading order

From here on it is **reading and judgment**, not Bash. Everything is a file under `$SNAP/`. **Read `references/analysis-procedure.md` now and follow it fully** before opening any snapshot file — it is mandatory, not optional. It holds the reading order (`inventory.json` → `findings-draft.json` → `summary.json` → the previous snapshot and report → `diff.json`), the list of summary.json sections and the pointers to the file-shape references (`references/snapshot-files.md`, `references/summary-shape.md`). Extract only the needed parts of JSON with `python3 -I - <<'EOF' … EOF` (the files are several MB).

Scope follows the arguments from section 0: `--namespace <ns>` narrows steps 2, 3 and 5 of the reading order to that namespace plus cluster-level items; `quick` to `recent_changes` of `summary.json` cross-checked against `diff.json`; `focus <area>` to that area's checks and related summary; `explain <finding-id>` reads one finding to the end and writes only the explanation (not a full report). The exact definitions are in the reference.

## 6. Analysis — review

Continue with the "Review" part of `references/analysis-procedure.md` (steps 6–10: open the raw file for every fail and warn, compare anomalies against the check definitions, `type: llm` checks and correlation, reconcile conflicting findings, apply the severity rules ①–⑤ including `symptom_linked` and `rename_suspects`), then its "Read-only commands outside the snapshot", "Severity guidance" and "Values that collection itself disturbed" paragraphs. Do not start writing until every fail and warn has been reviewed.

**A finding that disappears after a rubric version change is not a defect.** If a finding from the previous report is missing now and `rubric_version` went up, first read that check's `why` (it may carry a verdict-change note). If the change is intended there, do not record it as a "defect" in the tool notes (7-6); classify it under section 3 as a "criteria change".

**Read-only commands outside the snapshot** are allowed only under the three conditions in the reference: read only (section 9 applies unchanged), output saved as `$SNAP/extra/<name>.txt` and recorded in appendix 7-4, port-forwarding via `lib/portfwd.PortForward` without a foreground `sleep` loop.

## 7. Writing the report

**Read `references/report-writing.md` now and follow it fully** before writing the first line of any report file — it is mandatory, not optional. A run writes two files into `$SNAP/` in both modes: `report.md` for people (template `$KUBEGAP/templates/report.md`: an opening paragraph, the Top N problems — 3 in daily, 5 in full — each with Problem, Evidence, Cause, Action, a "Why this happens" block in three bullets (the principle, a public case from the check definition, what to read next) and the evidence check ids; then what changed since the previous run of this mode as prose, what this run could not see, and a numbers table) and `report-details.md` for the next run and for digging, assembled by code from the snapshot plus the small fragments you write into `$SNAP/llm/` (`adjustments.md`, `changes.md`, `areas.md` in full mode, `files-read.md`, `tool-notes.md`). Order: fragments → `report.md` → render → mask.

**Render, then mask (always the last two commands).**
```bash
$KUBEGAP/scripts/kubegap render-details --context <name> --snapshot "$SNAP" --language <en|ko>   # assembles report-details.md in the chosen language; prints fragments you forgot
$KUBEGAP/scripts/kubegap mask "$SNAP/report.md" "$SNAP/report-details.md"
```
If the mask count is not 0, check where `<masked>` remains. If you edit either file afterwards, run `mask` again. Then show the user only what step 18 of the reference lists (the two paths, context and cluster, the numbers table with deltas, Top N titles with a one-line action each, one line on tool notes if any, one line of commands for next time).

## 8. Writing rules

Tone and content rules are the "Writing rules" section of `references/report-writing.md` (report tone rules: conclusion first, one idea per sentence, plain words, polite conversational register, numbers with units; no summarizing, no omissions, no "etc." / "…" / "and N more", context first, no analogies, no invention, "confirmed" only for what was verified). Apply them to both report files and to messages to the user.

**Language (from section 0).** If Korean was chosen, write ALL messages to the user and both report files in Korean, translating the template headings and the check names, evidence, why and suggest text while writing (check definitions stay English in the repository); keep check ids, file paths, commands, metric names and resource names untouched. In Korean, end sentences in the polite conversational (haeyo) style, not the plain declarative (handa) style. If English was chosen, write everything in English, in plain sentences addressed to the reader.

## 9. What not to do

- Commands that change the cluster (`kubectl apply/delete/edit/scale/rollout/drain/cordon`, `aws … update/put/delete`, `helm upgrade/uninstall`, `argocd app sync`). Proposals go into the report as YAML only. Node cleanup such as `crictl rmi --prune` is proposed only.
- Reading Secret values (`kubectl get secret -o yaml/json`, `--decode`). Metadata already comes from the `kube_secret_info` metric.
- HTTP requests to public addresses outside the cluster (Prometheus, Loki and Grafana only via port-forward or the URL in config.yaml).
- Saving an unmasked report; tokens, passwords or a full list of internal IPs in the report body.
- Creating or recommending scheduled or headless runs. The user decides when to run.
- Questions other than steps 1 and 2 (and the language step). When unsure, state the assumption in the report and continue.
- **Changing kubegap's own code (`lib/`, `collectors/`, `templates/`, `scripts/`).** When you find a false positive, a summary defect or a masker false positive, write it with reproduction evidence in report section 7-6 tool notes. Fixing is for a development session. (This rule came from a session that patched `lib/mask.py` in the middle of a report: the fix was right, but the rubric version was not bumped and selftest did not run, so report and code diverged.)
- **Using values that collection itself disturbed.** collect sends about a hundred object LISTs and a hundred PromQL queries over 5–7 minutes. If `controlplane.apiserver-latency` (LIST p99), `apiserver-5xx` or Prometheus throttling overlaps the collection time (including the previous snapshot's `taken_at`), write "measured during collection (likely includes kubegap itself)" and do not count it as user impact.

## 10. Changing checks and the rubric (development note)

A report session does not change code (section 9). The procedure for adding or editing checks, selftest and version bumps is in [references/development.md](references/development.md).
