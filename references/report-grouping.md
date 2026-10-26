# Report grouping rules — findings with the same cause become one item (detail for SKILL.md section 7, item 12-1)

When writing the report, each group below is written as **one item**, not as dozens of findings. Give the count, totals and top 5, and leave the full list to appendix 7-5.

When `resources.cpu-request-overprovisioned`, `memory-request-overprovisioned`, `krr-recommendation` and `large-request-binpacking` hit the same container, write one row of a "resource adjustment table" (current request → recommended, p95 evidence, related finding ids). `besteffort-in-prod` and `no-memory-limit` on the same pod are one item; `oomkilled`, `oomkilled-repeated` and `memory-limit-near-p95` for the same incident are one item. For a check with dozens of warns (over-allocation types) write count, totals and top 5 only, and leave the full list to appendix 7-5. `scaling.hpa-cpu-only-prod`, `hpa-no-behavior-prod` and `hpa-never-scaled` on the same HPA are one row of an "HPA settings table" (metric, target, min/max, behavior, 15-day movement); when the cause of `hpa-never-scaled` is an oversized request, point to that container in the resource adjustment table. When `scaling.no-hpa-serving-prod` and `resilience.single-replica` hit the same Deployment, attach "no HPA either" to the single resilience item.

**Observability.** When one Loki OOM incident triggers `observability.loki-oomkilled`, `loki.memory-pressure`, `logs.signatures(promtail.send-failed)`, `grafana.datasource-errors(429)` and `resources.oomkilled*` together, that is one "Loki memory" item. The observability stack on emptyDir is one "observability stack storage" item made of `observability.stack-storage-emptydir`, `prometheus.storage-risk` and `alertmanager.single-instance`. Always-firing alerts: `alert-firing-stale` and `alerts-always-firing` as one line per alert name (on EKS, KubeControllerManagerDown and KubeSchedulerDown are false positives from the managed control plane; the rules should be disabled). A gap in ingress backend metrics is one `ingress-controller-metrics-missing` item with only the `golden-signals-missing` count attached.

**Traffic.** `traffic.alb-deregistration-vs-grace` fires on dozens of target groups because of the same default (300 seconds), so it is one "ALB controller default deregistration delay" item with the count and the top 5 prod backends. On a small k3s cluster, a NodePort in `traffic.db-exposed` is LAN exposure and goes to medium under severity rule ④ (profile context).

**Resilience.** Group `resilience.single-eligible-node` by constraint (label, taint), one line each ("role NotIn <label> → N workloads"); `replicas-same-node`, `single-replica-in-prod`, `no-pdb` and `no-readiness-probe` become one row per workload in a "resilience table". `db-probe-timeout` and `exec-probe` on the same container are one item (Bitnami chart defaults).

**Hygiene.** `mutable-image-tag`, `always-pull-with-tag` and `polaris-reliability-danger(tagNotSpecified)` are one line per workload.

**Storage.** `storage.csi-snapshot-unavailable` and `logs.signatures(ebs-csi.snapshot-crd-missing)` are one item.

**Security.** When one ExternalSecret that has failed to sync for months triggers `security.externalsecret-not-ready`, `eso.provider-api-errors`, `operators.unhealthy-condition` and `logs.signatures(external-secrets.provider-error)` together, that is one item. The IMDS parts of `security.imds-hop-limit` and `karpenter.ec2nodeclass-hardening` are one item.

**Tenancy.** `tenancy.prod-boundary-missing`, `prod-without-quota`, `tenant-without-limitrange`, `security.psa-not-enforced`, `networkpolicy-coverage` and `no-default-deny` become one "tenant boundary table" per namespace (four columns: quota, LimitRange, NetworkPolicy, PSA).

**Cost.** `cost.request-waste` and `cost.idle-compute-high` are the money view of the resource adjustment table, so they go as one line under that table.

**Node.** When every node has the same value, as with `node.cgroup-v1`, write one cluster-level line without the node list. Node disk: `events.tracked-warning-reasons(FreeDiskSpaceFailed)`, `node.disk-usage` and `logs.signatures(kubelet.image-gc-failed, containerd.shim-error)` become one "node disk full" item; the Prometheus emptyDir in `node.pod-dir-large` attaches to the observability stack storage item.

**Platform.** AL2 end of life: `hygiene.eks-upgrade-insight(AL2)`, `karpenter.ec2nodeclass-al2`, `eks.node-os-skew`, `node.cgroup-v1` and `eks.nodegroup-ami-old` become one "AL2 → AL2023 migration" item. Nodes not registered in SSM: `eks.ssm-unregistered`, `node.os-not-collected` and `vpccni.metrics-unreadable` are one item. `platform.karpenter-version-compat` with `logs.signatures(karpenter.version-unsupported)`, and `platform.k3s-datastore-slow` with `controlplane.etcd-slow`, are one item each.
