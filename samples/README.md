# Sample reports

Real reports written by `/kubegap` on an EKS cluster and a two-node k3s cluster. Four are in English and two in Korean. Account ids, private IPs, cluster and node names, namespaces, workload names and domains were replaced afterwards with placeholders such as `node-a`, `app-c` or `api.example-b.ai`; numbers and findings are untouched, and wording is unchanged apart from those names. The procedure is in [`docs/SAMPLES.md`](../docs/SAMPLES.md).

Every run writes two files. `report.md` is for people: a first screen (urgent or not, today's problems, since the last run), the cluster at a glance and what is coming up (both from code), the problems (3 in daily mode, 5 in full) each with what is happening, why, a suggested fix, rollback, why this happens (the principle, a public case, what to read next) and the evidence table, then the since-last-run table, every other critical or high item, one line per area in full mode, what the run could not see, a numbers table and the check ids behind each problem. `report-details.md` is for the next run and for digging: every table (counts, critical/high list, changes, absence, suppressed, collectors run, checks evaluated, signature matches, the full first-pass list) assembled by `scripts/kubegap render-details`, plus the analysis record from the facts: severity changes, recounted numbers, why things changed, per-area detail (full mode), files read and tool notes.

| Language | Cluster | Mode | Report | Details |
|---|---|---|---|---|
| English | k3s, 2 Ubuntu nodes, embedded etcd, MetalLB, flannel, local-path-provisioner; profile `lab` | daily | [en/k3s/daily/report.md](en/k3s/daily/report.md) | [en/k3s/daily/report-details.md](en/k3s/daily/report-details.md) |
| English | k3s, same | full | [en/k3s/full/report.md](en/k3s/full/report.md) | [en/k3s/full/report-details.md](en/k3s/full/report-details.md) |
| English | EKS, 8 nodes (Karpenter spot plus a managed node group), 23 components; profile `prod` | daily | [en/eks/daily/report.md](en/eks/daily/report.md) | [en/eks/daily/report-details.md](en/eks/daily/report-details.md) |
| English | EKS, same | full | [en/eks/full/report.md](en/eks/full/report.md) | [en/eks/full/report-details.md](en/eks/full/report-details.md) |
| Korean | EKS, same | full | [ko/eks/full/report.md](ko/eks/full/report.md) | [ko/eks/full/report-details.md](ko/eks/full/report-details.md) |
| Korean | k3s, same | daily | [ko/k3s/daily/report.md](ko/k3s/daily/report.md) | [ko/k3s/daily/report-details.md](ko/k3s/daily/report-details.md) |

Daily snapshots are compared with the previous daily snapshot, full with full, so a report's "since the previous run" section always talks about the same kind of run.
