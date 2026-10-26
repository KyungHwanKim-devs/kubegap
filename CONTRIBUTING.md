# Contributing

## Making changes

- To add or modify a check, follow the procedure in `references/development.md`. A check is one entry in `collectors/<collector>/checks.yaml` and must have `test.cases`.
- When the rubric changes, bump `rubric/version` in the same pull request and regenerate the catalog: `scripts/kubegap checks --markdown > docs/CHECKS.md` (a test checks that it is current). When signatures change, bump the version in `signatures/catalog.yaml`.
- `checks.yaml` expressions are Python evaluated by `lib/evaluate.py`. They are code: review them like code.
- Unit tests live in `tests/` (pytest; the YAML parser, rubric resolution, snapshot diff, platform detection and the evaluate helpers); add a test when you touch `lib/`.
- Open a pull request against `main` from a branch; one topic per pull request, with a short description of what changed and why. Everything below must pass before you submit.

```bash
uvx ruff check . && uvx ruff format --check .   # line length is 240 on purpose (one dict per line in summary modules)
uvx pytest -q                                          # unit tests in tests/ (no cluster needed)
scripts/kubegap selftest                                   # embedded test cases of every check: 0 failures
scripts/kubegap selftest --snapshot <snapshot path>        # optional, with a real snapshot: also 0 key mismatches
uvx --from skills-ref agentskills validate "$PWD"      # run from the parent directory if your folder is not named kubegap
```

## Rules

- kubegap is read-only. Do not add commands that change the cluster (apply, delete, scale, patch, exec).
- Secret values are never read or recorded anywhere. Names, types and key names only.
- Raw cluster data (snapshots), personal configuration (`config.yaml`) and tool binaries (`.tools/`) are not committed (`.gitignore`).
- Commit messages: at least one line in English saying what changed and why. Do not add co-author trailers for code-generation tools.
