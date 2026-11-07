# Contributing

## Making changes

- To add or modify a check, follow the procedure in `references/development.md`. A check is one entry in `collectors/<collector>/checks.yaml` and must have `test.cases`.
- When the rubric changes, bump `rubric/version` and the `rubric_version` line in the `SKILL.md` frontmatter in the same pull request and regenerate the catalog: `scripts/kubegap checks --markdown > docs/CHECKS.md` (a test checks that the catalog and the frontmatter are current). When signatures change, bump the version in `signatures/catalog.yaml`.
- `checks.yaml` expressions are Python evaluated by `lib/evaluate.py`. They are code: review them like code.
- The YAML files here are read by `lib/yamlite.py`, which supports only a subset of YAML; the subset is listed at the top of [`lib/yamlite.py`](lib/yamlite.py). Anchors, aliases, tags and plain strings continued on the next line raise an error with the line number. Keep a plain string on one line, or use a `>` block or quotes for long text.
- Unit tests live in `tests/` (pytest; the YAML parser, rubric resolution, snapshot diff, platform detection and the evaluate helpers); add a test when you touch `lib/`.
- `tests/test_regress.py` runs summarize, evaluate and render on the committed snapshots in `tests/fixtures/snapshot-*/` and compares the result with `tests/fixtures/expected/`. When your change is meant to alter a summary, a verdict or the report, run `scripts/kubegap regress --update` and commit the new expectation in the same pull request; the diff shows the reviewer what moved. The procedure, the fixture builder and the degraded variant are described in `references/development.md`.
- Open a pull request against `main` from a branch; one topic per pull request, with a short description of what changed and why. Everything below must pass before you submit.
- When a parser needs the value of a ConfigMap key, add that key to `KEEP_VALUES` in `lib/scrub.py`. Every other ConfigMap value is replaced by its length and shape before the snapshot is written, so the parser would otherwise see a dict. The same happens to the two annotations that carry a copy of the object, `kubectl.kubernetes.io/last-applied-configuration` and `objectset.rio.cattle.io/applied`.
- When a tool of `lib/tools.py` changes (a tool added or removed, its `checks`, `modes`, install method or pin), regenerate the table a test compares against: `scripts/kubegap tools --markdown` and `scripts/kubegap tools --markdown --language ko`, pasted between the `tools-table` markers of `docs/SETUP.md` and `docs/ko/SETUP.md`. Every entry of `checks` must be a check id of the catalog, `<area>.*`, `<area>.*@full` (the full-mode-only checks of that area) or `*`.
- When a node command changes (`collectors/*/collect.yaml` `type: node` or `type: pod-metrics` steps, the scripts they name, the probes in `lib/nodecommands.py`), regenerate the two files a test compares against: `scripts/kubegap node-commands --markdown > deploy/node-access/COMMANDS.md` and `scripts/kubegap node-commands --ssm-document > deploy/permissions/ssm-document.yaml`.

```bash
uvx ruff check . && uvx ruff format --check .   # line length is 240 on purpose (one dict per line in summary modules)
uvx pytest -q                                          # unit tests in tests/ (no cluster needed)
scripts/kubegap selftest                                   # embedded test cases of every check: 0 failures
scripts/kubegap regress                                    # the committed snapshots give the committed summaries, findings and report details
scripts/kubegap selftest --snapshot <snapshot path>        # optional, with a real snapshot: also 0 key mismatches
uvx --from skills-ref agentskills validate "$PWD"      # run from the parent directory if your folder is not named kubegap
```

## Working on an issue

- Pick an open issue and say so in a comment, so two people do not start the same one. Issues labelled `good first issue` need no cluster.
- Branch name `fix/<issue number>-<a few words>`; the last line of the pull request body is `Closes #<number>`, which closes the issue when the pull request is merged.
- Write what you found before what you changed: which file and line, what the issue got right or wrong, and what you verified. If you ran it against a real cluster, say which kind and what you saw. The body can be in English or in Korean and English.
- Add one line to the `Unreleased` section of `CHANGELOG.md` under Added, Changed or Fixed, with the issue number. The release notes are built from it and name the contributors.
- The first pull request from a fork does not run CI by itself: GitHub waits for a maintainer to approve the workflow run. Run the commands above locally; the maintainer approves and runs CI before merging.
- Pull requests are squash-merged: `main` gets one commit per pull request, titled after it. Inside the pull request, split your commits by topic anyway, such as code, documentation and CHANGELOG; it makes the review easier and the history stays on the pull request page. The maintainer may push a small follow-up commit onto your branch before merging.

## Rules

- kubegap is read-only. Do not add commands that change the cluster (apply, delete, scale, patch, exec).
- Secret values are never read or recorded anywhere. Names, types and key names only. The one exception is `helm list`, which reads Helm's own release records stored in Secrets; only release metadata is kept, and `helm get values` is never run. ConfigMap values are not recorded either, apart from the keys in `KEEP_VALUES`, and raw component logs are deleted once `summarize` has aggregated them (`lib/scrub.py`, `lib/summarize.py`).
- Raw cluster data (snapshots), personal configuration (`config.yaml`) and tool binaries (`.tools/`) are not committed (`.gitignore`).
- README.md and README.ko.md do not use parentheses for asides. Write a second sentence instead. The same rule applies to the reports (`references/report-writing.md`).
- Commit messages: at least one line in English saying what changed and why.
- The code and documentation here were written with coding agents. What to collect, what counts as a problem, and which verdicts were wrong on real clusters were decided by the author. Contributions made the same way are welcome; the review bar is the same either way.
