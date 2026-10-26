# Sample reports

Real reports written by `/kubegap` on a production EKS cluster and a two-node k3s cluster. Four are in English and two in Korean. Account ids, private IPs, cluster and node names, namespaces, workload names and domains were replaced afterwards with placeholders such as `node-a`, `app-c` or `api.example-b.ai`; numbers, findings and wording are untouched. The procedure is in [`docs/SAMPLES.md`](../docs/SAMPLES.md).

Every run writes two files. `report.md` is for people: an opening paragraph, the Top N problems (3 in daily mode, 5 in full) each with problem, evidence, cause, action, why this happens (the principle, a public case, what to read next) and the evidence check ids, then what changed since the previous run of the same mode, what the run could not see, and a numbers table. `report-details.md` is for the next run and for digging: every table (counts, critical/high list, changes, absence, suppressed, collectors run, checks evaluated, signature matches, the full first-pass list) assembled by `scripts/kubegap render-details`, plus the LLM's adjustments, per-area detail (full mode) and tool notes.

| Language | Cluster | Mode | Report | Details |
|---|---|---|---|---|
| English | k3s, 2 Ubuntu nodes, embedded etcd, MetalLB, flannel, local-path-provisioner; profile `lab` | daily | [en/k3s/daily/report.md](en/k3s/daily/report.md) | [en/k3s/daily/report-details.md](en/k3s/daily/report-details.md) |
| English | k3s, same | full | [en/k3s/full/report.md](en/k3s/full/report.md) | [en/k3s/full/report-details.md](en/k3s/full/report-details.md) |
| English | EKS, 8 nodes (Karpenter spot plus a managed node group), 23 components; profile `prod` | daily | [en/eks/daily/report.md](en/eks/daily/report.md) | [en/eks/daily/report-details.md](en/eks/daily/report-details.md) |
| English | EKS, same | full | [en/eks/full/report.md](en/eks/full/report.md) | [en/eks/full/report-details.md](en/eks/full/report-details.md) |
| Korean | EKS, same | full | [ko/eks/full/report.md](ko/eks/full/report.md) | [ko/eks/full/report-details.md](ko/eks/full/report-details.md) |
| Korean | k3s, same | daily | [ko/k3s/daily/report.md](ko/k3s/daily/report.md) | [ko/k3s/daily/report-details.md](ko/k3s/daily/report-details.md) |

Daily snapshots are compared with the previous daily snapshot, full with full, so a report's "since the previous run" section always talks about the same kind of run.
