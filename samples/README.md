# Sample reports

Eight real reports: a daily and a full audit of an EKS cluster and of a two-node k3s cluster, each written once in English and once in Korean. They were made on 2026-11-15 by typing `/kubegap daily` or `/kubegap full` into an agent session that knew nothing about the clusters, and are published as the run wrote them, with names replaced.

| Cluster | Mode | English | Korean |
|---|---|---|---|
| k3s: 2 nodes, embedded etcd, MetalLB, local-path-provisioner, run at small scale | daily | [report](en/k3s/daily/report.md) | [리포트](ko/k3s/daily/report.md) |
| k3s, the same | full | [report](en/k3s/full/report.md) · [details](en/k3s/full/report-details.md) | [리포트](ko/k3s/full/report.md) · [세부](ko/k3s/full/report-details.md) |
| EKS: 9 nodes (Karpenter plus a managed node group), run at medium scale | daily | [report](en/eks/daily/report.md) | [리포트](ko/eks/daily/report.md) |
| EKS, the same | full | [report](en/eks/full/report.md) · [details](en/eks/full/report-details.md) | [리포트](ko/eks/full/report.md) · [세부](ko/eks/full/report-details.md) |

What to know when reading them:

- **A daily report is one or two screens.** What is broken now, what happened, the three things that matter most, and at the end what the run did not look at. A daily audit writes one file.
- **A full report is long.** Up to five problems, each explained in six sections, around 500 lines. `report-details.md` next to it holds every verdict and every table and is assembled by code.
- **The English and the Korean report of one cluster are two separate runs**, minutes apart, by two sessions. They agree on the facts and do not always choose the same five problems or order them alike: choosing is the agent's judgement, within what the assembly check requires (every critical finding and every high failure has to be placed).
- **The k3s full reports did not read the nodes.** Node access was skipped in those runs, and the reports say so under the limits of the run. The EKS full reports read seven of nine nodes; two are not registered with SSM.
- **Names are placeholders.** Account ids, private IPs, load balancer addresses, cluster and node names, namespaces, workload names, repositories and domains were replaced with names such as `node-a`, `app-c` or `lab-k`. Numbers and findings are untouched and the wording is unchanged apart from those names. How a sample is made is in [`docs/SAMPLES.md`](../docs/SAMPLES.md).
