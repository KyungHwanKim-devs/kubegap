# Contributing

## Making changes

- To add or modify a check, follow the procedure in `references/development.md`. A check is one entry in `collectors/<collector>/checks.yaml` and must have `test.cases`.
- When the rubric changes, bump `rubric/version` in the same pull request and regenerate the catalog: `scripts/kubegap checks --markdown > docs/CHECKS.md` (a test checks that it is current). When signatures change, bump the version in `signatures/catalog.yaml`.
- `checks.yaml` expressions are Python evaluated by `lib/evaluate.py`. They are code: review them like code.
- Unit tests live in `tests/` (pytest; the YAML parser, rubric resolution, snapshot diff, platform detection and the evaluate helpers); add a test when you touch `lib/`.
- Open a pull request against `main` from a branch; one topic per pull request, with a short description of what changed and why. Everything below must pass before you submit.
- When a parser needs the value of a ConfigMap key, add that key to `KEEP_VALUES` in `lib/scrub.py`. Every other ConfigMap value is replaced by its length and shape before the snapshot is written, so the parser would otherwise see a dict.
- When a node command changes (`collectors/*/collect.yaml` `type: node` or `type: pod-metrics` steps, the scripts they name, the probes in `lib/nodecommands.py`), regenerate the two files a test compares against: `scripts/kubegap node-commands --markdown > deploy/node-access/COMMANDS.md` and `scripts/kubegap node-commands --ssm-document > deploy/permissions/ssm-document.yaml`.

```bash
uvx ruff check . && uvx ruff format --check .   # line length is 240 on purpose (one dict per line in summary modules)
uvx pytest -q                                          # unit tests in tests/ (no cluster needed)
scripts/kubegap selftest                                   # embedded test cases of every check: 0 failures
scripts/kubegap selftest --snapshot <snapshot path>        # optional, with a real snapshot: also 0 key mismatches
uvx --from skills-ref agentskills validate "$PWD"      # run from the parent directory if your folder is not named kubegap
```

## Working on an issue

- Pick an open issue and say so in a comment, so two people do not start the same one. Issues labelled `good first issue` need no cluster.
- Branch name `fix/<issue number>-<a few words>`; the last line of the pull request body is `Closes #<number>`, which closes the issue when the pull request is merged.
- Write what you found before what you changed: which file and line, what the issue got right or wrong, and what you verified. If you ran it against a real cluster, say which kind and what you saw. The body can be in English or in Korean and English.
- Add one line to the `Unreleased` section of `CHANGELOG.md` under Added, Changed or Fixed, with the issue number. The release notes are built from it and name the contributors.
- The first pull request from a fork does not run CI by itself: GitHub waits for a maintainer to approve the workflow run. Run the commands above locally; the maintainer approves and runs CI before merging.
- Pull requests are merged with a merge commit, so your commits stay as you wrote them. The maintainer may push a small follow-up commit onto your branch before merging.

## Rules

- kubegap is read-only. Do not add commands that change the cluster (apply, delete, scale, patch, exec).
- Secret values are never read or recorded anywhere. Names, types and key names only. ConfigMap values are not recorded either, apart from the keys in `KEEP_VALUES`, and raw component logs are deleted once `summarize` has aggregated them (`lib/scrub.py`, `lib/summarize.py`).
- Raw cluster data (snapshots), personal configuration (`config.yaml`) and tool binaries (`.tools/`) are not committed (`.gitignore`).
- README.md and README.ko.md do not use parentheses for asides. Write a second sentence instead. The same rule applies to the reports (`references/report-writing.md`).
- Commit messages: at least one line in English saying what changed and why.
- The code and documentation here were written with coding agents. What to collect, what counts as a problem, and which verdicts were wrong on real clusters were decided by the author. Contributions made the same way are welcome; the review bar is the same either way.
