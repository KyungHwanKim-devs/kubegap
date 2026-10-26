# collectors/

One collector = one folder. Each folder has these files (the first four always, the rest when the collector needs them).

| File | Role |
|---|---|
| `detect` | Rule that decides whether the component is installed. If false, the collector is skipped; if the profile expects the component, this becomes an absence finding |
| `collect.yaml` | List of steps to run (kubectl, PromQL, AWS CLI, CloudWatch, node commands, external tools). Each step has an id, timeout, failure handling and output path |
| `checks.yaml` | List of check definitions, each with embedded `test.cases` |
| `signatures.yaml` | Log signatures for this component |
| `metrics.yaml`, `cwlogs.yaml` | PromQL and CloudWatch Logs Insights queries referenced by `collect.yaml` (where used) |
| `node-os.sh`, `k3s-node.sh` | Scripts run on nodes through SSM, SSH or the DaemonSet backend (`core/`, `k3s-platform/`) |

A collector that produces its own summary section registers it in `COMPONENT_SECTIONS` in `lib/summarize.py` (summary key, `lib/<module>.py` exposing `analyze(snap, inv, …)`, the collector folder names that enable it); when none of those collectors is in `inventory.collectors_enabled` the section is written as `{"present": false}`. Component detection rules live in `lib/components.py`. See `references/development.md`.

- `core/` always runs (resources, scaling, events, CRD conditions, resilience, structure and hygiene, security, storage basics).
- `eks-platform/` always runs under the `eks` profile. On k3s (`k3s`) it is turned off by detection.
- Every other folder is enabled by its `detect` result (the names match the component names in components.py). EKS side: `vpc-cni/`, `coredns/`, `kube-proxy/`, `ebs-csi/`, `alb-controller/`, `karpenter/`, `keda/`, `external-secrets/`, `argocd/`, `prometheus/`, `alertmanager/`, `grafana/`, `loki/`, `ecr/`. Small k3s cluster side (counterparts of the EKS ones): `flannel/` (VPC CNI), `local-path-provisioner/` (EBS CSI), `metallb/` (ALB), `cert-manager/` (ACM). The node script in `k3s-platform/` (k3s-node.sh) also reads the flannel and local-path sections, and those collectors reuse its output (no second SSH round trip).
- No collector may have an empty `collect`: even an objects-only collector has at least one metrics (promql) or pod-metrics step.

To support a new component, add one folder here plus its summary module in `lib/` (see above). That is the contribution point after release.
