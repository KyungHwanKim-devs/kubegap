# Test fixtures

`snapshot-<name>/` is one `full` snapshot of a reference cluster, committed as an input for `tests/test_regress.py` (#145): summarize, evaluate and
render run on a copy of it and the result is compared with `expected/<variant>/`. Each was made from a real run by `scripts/make-fixture.py`, which
leaves out what the pipeline produces, trims the fields no reader uses, replaces names through a private map, and verifies against the source run
that no check changed its status or finding count. The procedure and the degraded variant are described in `references/development.md`.

| Fixture | Cluster | Collected | Profile | Nodes | Namespaces | Node access | Stores | Size |
|---|---|---|---|---|---|---|---|---|
| `snapshot-k3s` | k3s v1.33.5+k3s1, two nodes | 2026-11-07T10:22:59+09:00 | lab | 2 | 26 | ssh | prometheus, alertmanager, grafana, loki (loki not reachable) | 18.8 MB, 1.55 MB compressed |
| `snapshot-eks` | EKS v1.32.13, Karpenter | 2026-11-07T10:33:37+09:00 | prod | 9 | 26 | ssm | prometheus, alertmanager, grafana, loki | 17.8 MB, 1.45 MB compressed |

Both inventories carry `schema: 1` (the snapshot format version of #97, written by discovery since 0.1.5); it was added to these two by hand when the key was introduced, as a collection of this version would write it.

`expected/<name>/` and `expected/<name>-degraded/` hold `summary.json`, `findings.json` (check results and findings without `details`), and
`report-details.en.md` / `report-details.ko.md`. They change only through `scripts/kubegap regress --update`.

`api-resources/` is the list of kinds each reference cluster serves (`tests/test_object_files.py`, #160). `loki-config-3.7.9.yaml` is a Loki
configuration dump written from the Loki source for a version no cluster at hand runs (`tests/test_monitoring_loki.py`).
