# kubegap이 쓰는 권한

이 문서는 권한마다 어디에 왜 필요한지와 없으면 무엇이 빠지는지를 설명하며, 권한 한 줄 한 줄의 완전한 목록은 [영어 원본](../PERMISSIONS.md)이 정본입니다.

## 요약

kubegap은 클러스터를 바꾸지 않습니다. 읽기 호출만 하고, 내 kubeconfig, AWS 프로파일, SSH가 이미 가진 접근 권한을 그대로 씁니다. 점검 전용 신원을 따로 만든다면 아래 항목이 필요합니다.

**클러스터.** [`deploy/permissions/clusterrole.yaml`](../../deploy/permissions/clusterrole.yaml)을 쓰세요. 코어 리소스와 kubegap이 읽는 API 그룹에 `get`과 `list`를 주고, Secret은 제외합니다. 여기에 세 가지가 더 있습니다.

- `nodes/proxy`: kubelet 설정을 읽습니다.
- `pods/proxy`: API 서버를 거쳐 컴포넌트 파드의 `/metrics`를 읽습니다.
- `pods/portforward`의 `create`: `kubectl port-forward`로 Prometheus, Alertmanager, Loki, Grafana에 연결할 때 인가를 받는 권한입니다. 클러스터에는 아무것도 만들지 않습니다.

역할에 있는 권한은 전부 코드가 실제로 호출하는 것이고, 테스트로 이 상태를 유지합니다. 역할에 없는 API 그룹의 리소스 종류는 실패가 아니라 권한 없음으로 기록합니다. 그 종류를 읽는 점검 항목은 없습니다.

**AWS, EKS일 때.** [`deploy/permissions/iam-policy.json`](../../deploy/permissions/iam-policy.json)을 쓰세요. Describe, List, Get 액션과 CloudWatch `GetMetricData`, 그리고 두 가지로 제한한 SSM `SendCommand`가 들어 있습니다.

- 실행할 수 있는 SSM 문서는 `kubegap-node-read` 하나뿐입니다. 이 SSM 문서는 읽기 명령을 담고 있고, 자유로운 명령 문자열을 받지 않습니다.
- `kubernetes.io/cluster/<CLUSTER_NAME>=owned` 태그가 있는 인스턴스에서만 실행할 수 있습니다. 관리형 노드 그룹과 Karpenter가 모든 노드에 이미 붙이는 태그입니다.

SSM 문서 ARN에 계정 ID가 들어 있어서, 다른 계정이 공유한 같은 이름의 SSM 문서는 일치하지 않습니다.

`scripts/kubegap iam-policy --context <name>`을 실행하면 kubeconfig에서 읽은 값으로 `<ACCOUNT_ID>`와 `<CLUSTER_NAME>`을 채운 정책을 출력합니다. 출력만 하고 AWS에는 아무것도 보내지 않습니다. `SendCommand` 구문 두 개를 뺀 정책을 보려면 `--without-node-access`를 붙이세요.

**노드에 닿는 명령.** 노드 접속 방식과 상관없이 모든 명령이 [`deploy/node-access/COMMANDS.md`](../../deploy/node-access/COMMANDS.md)에 있습니다. 이 파일은 수집기 정의인 `collectors/*/collect.yaml`에서 생성되고, 테스트가 최신 상태를 확인합니다.

**k3s와 베어메탈의 SSH 노드.** [`deploy/node-access/README.md`](../../deploy/node-access/README.md)를 따르세요. 로그를 읽는 그룹에 사용자를 넣는 한 줄이 있고, 필요하면 읽기 전용 명령을 허용하는 sudoers 파일을 추가합니다.

**SSM도 SSH도 없는 노드, GKE, AKS와 그 밖의 관리형 노드.** 읽지 않습니다. 노드 점검 항목은 미수집으로 적힙니다.

SSM 문서를 한 번 올리는 일은 점검 정책에 들어 있지 않습니다. 내 자격 증명으로 실행하며, `ssm:CreateDocument`, `ssm:UpdateDocument`, `ssm:UpdateDocumentDefaultVersion`, `ssm:ListDocumentVersions`가 필요합니다.

가장 좁은 권한으로 돌리는 방법과 그때 보지 못하는 것은 [SETUP.md](SETUP.md#가장-좁은-권한으로-돌리기)에 있습니다. 무엇을 모으고, 남기고, 보내는지는 [DATA.md](DATA.md)에 있습니다.

## 권한을 빼면 어떻게 되나

kubegap은 `collectors/*/collect.yaml`에 정의한 수집 단계를 돌려 데이터를 모읍니다. 권한을 하나 빼면 그 권한이 맡은 만큼만 빠집니다. 무엇이 빠지는지는 아래에 권한별로 적었고, 어떤 권한이든 공통으로 이렇게 동작합니다.

- 거부당한 수집 단계는 실패로 기록하고 `report-details.md`의 7-1절에 나열합니다.
- `objects/<kind>.json`이나 `metrics/<id>.json` 파일이 없으면 그 파일을 읽는 점검 항목은 `skip`이 됩니다. `skip`은 판정하지 못하고 건너뛰었다는 뜻이고, 통과로 세지 않습니다.
- 요약 데이터나 자원 목록으로 판정하는 점검 항목은 규칙의 `rule.needs`에 적힌 입력이 없으면 `skip`이 됩니다. `done`으로 끝날 때는 판정하지 못한 대상을 7-5절에 적습니다.
- 입력이 비어 있다는 이유로 통과시키지 않습니다. 배경은 [#114](https://github.com/KyungHwanKim-devs/kubegap/issues/114)에 있습니다.

영어 원본의 표는 `tests/test_permissions.py`가 검사합니다. Kubernetes 표는 ClusterRole의 그룹, 리소스, verb와 정확히 같아야 하고, AWS 표는 정책의 액션과 정확히 같아야 합니다. 표에 적은 수집 단계는 `collectors/*/collect.yaml`에 있어야 하고, 모드 칸은 그 단계의 `modes:`와 맞아야 합니다. 점검 항목 칸은 각 종류가 어느 요약 섹션에 들어가는지 보고 사람이 썼습니다. 같은 테스트는 코드가 역할에 없는 것을 읽지 않는지와, 역할에 코드가 읽지 않는 것이 없는지도 확인합니다.

이 문서에서 자주 나오는 이름은 이런 뜻입니다.

| 이름 | 뜻 |
|---|---|
| `core/objects.dump-all` | `collectors/core/collect.yaml`의 수집 단계 `objects.dump-all`입니다. ClusterRole이 허용하는 리소스 종류를 한 번씩 나열해 `objects/<kind>.json`에 저장합니다. Kubernetes 권한 대부분이 이 단계에서 쓰입니다 |
| `lib/collection/discover.py` | 수집 전에 몇 가지 종류를 읽어 클러스터의 플랫폼과 컴포넌트를 판단합니다 |
| daily, full | daily 점검과 full 점검입니다. 따로 적지 않은 권한은 둘 다 씁니다. full이라고 적은 것은 full 점검에서만 씁니다 |

## 점검 종류별로 쓰는 권한

**daily 점검.**

- ClusterRole에 있는 리소스의 Kubernetes `get`과 `list`
- 컴포넌트 로그를 읽는 `pods/log`
- Prometheus, Alertmanager, Loki, Grafana 포트포워드
- `grafana_api_token`이 설정되어 있을 때 Grafana API
- AWS API는 부르지 않고 노드에도 접속하지 않습니다. 남는 AWS 호출은 EKS 클러스터의 kubeconfig가 스스로 하는 `aws eks get-token` 하나입니다.

**full 점검.** daily 점검이 쓰는 것 전부에 아래를 더합니다.

- EKS에서 탐지와 setup에 쓰는 AWS Describe, List 호출: `eks`, `ecr:DescribeRepositories`, `ssm:DescribeInstanceInformation`, `ssm:DescribeDocument`, `sts`, `logs:DescribeLogGroups`
- EKS의 AWS 수집 단계 전부. 이 가운데 `alb-metrics`는 `elasticloadbalancing:Describe*`, `ec2:DescribeSecurityGroups`, `cloudwatch:GetMetricData`를 씁니다.
- 파드 메트릭을 노드 안에서 curl로 대신 읽는 동작. EKS에서는 고정된 문서의 SSM `send-command`와, 그 출력을 읽는 `ssm:GetCommandInvocation`을 씁니다.
- 노드 스크립트: SSM 또는 SSH로 실행합니다.
- kubelet 설정을 읽는 `nodes/proxy`
- CloudWatch Logs Insights: `logs:StartQuery`, `GetQueryResults`, `StopQuery`
- 쿼터와 EBS의 `GetMetricData` 쿼리
- `helm list`: Helm의 릴리스 Secret을 읽고 메타데이터만 남깁니다.
- 비용과 가격, ECR, 서비스 쿼터
- 외부 도구 krr, polaris, pluto, kubent

## Kubernetes 권한

모든 규칙은 `get`과 `list`입니다. 예외는 `pods/portforward`의 `create`입니다. API 서버가 스트림을 여는 동작을 이렇게 부르기 때문이고, 클러스터에 만들어지는 것은 없습니다.

### 없으면 점검이 돌지 않는 권한

**`pods`.** 거의 모든 요약이 파드를 바탕으로 만들어집니다. 노드, 복원력, 위생, 보안, 플랫폼, 멀티테넌시, 스토리지, 스케일링, 비용과 모든 컴포넌트 영역이 파드를 쓰고, 점검 항목 407개 중 230개가 여기에 기댑니다. 이 권한이 없으면 `setup`이 "no permission to list pods"라고 알리고 수집을 시작하지 않습니다.

**`nodes`.** 플랫폼, 버전, 존, 용량 유형을 판단할 때 읽습니다. 복원력, 스토리지, 플랫폼, coredns, 관측성, 트래픽, 오퍼레이터, `node.*`에 걸쳐 82개 항목이 씁니다. 없으면 `setup`이 클러스터에 닿을 수 없다고 알리고 아무것도 돌지 않습니다.

**`apps` 그룹.** 컴포넌트 탐지에 `deployments`와 `daemonsets`를 읽고, 복원력, 트래픽, 스케일링, 플랫폼, 모든 컴포넌트 영역의 205개 항목이 씁니다. 없으면 컴포넌트 탐지의 Deployment, DaemonSet, StatefulSet 규칙이 실패합니다. `lib/foundations/components.py`의 CRD 규칙과 이미지 규칙은 그대로 동작합니다. 워크로드 섹션이 전부 비어서 점검 항목 대부분이 `skip`이 됩니다.

**API 디스커버리 URL.** `/api`, `/api/*`, `/apis`, `/apis/*`의 `get`입니다. 모든 `kubectl` 호출이 리소스 이름을 찾을 때 쓰고, `core/objects.dump-all`도 `kubectl api-resources --verbs=list`로 씁니다. 없으면 kubectl이 리소스 이름을 전혀 찾지 못합니다.

**`/version`.** `kubectl version`으로 서버 버전과, pluto와 kubent에 넘길 다음 마이너 버전을 알아냅니다. 없으면 서버 버전을 알 수 없고 `platform.k8s-version-eol`이 `skip`이 됩니다.

이 URL들은 기본 `system:discovery` 바인딩이 모든 인증 사용자에게 이미 허용합니다. 역할 파일만 읽어도 필요한 권한이 다 보이도록 역할에 넣어 두었습니다.

### 로그와 메트릭을 읽는 권한

**`pods/log`.** 수집 단계 `core/component-logs`가 컴포넌트 파드의 최근 24시간 로그를 `kubectl logs`로 읽습니다. 요약 단계인 `summarize`가 끝나면 원본을 지우고, `keep_component_logs`를 설정하면 남깁니다. `logs.signatures`, `observability.unclassified-errors`, 그리고 `lib/summaries/scaling.py`가 `logs/pods/karpenter/`에서 읽는 Karpenter 로그 정보가 이 로그를 씁니다.

없으면 `logs.signatures`는 일치하는 로그가 없다고 보고, `observability.unclassified-errors`는 분류할 로그가 없습니다. 이 둘은 로그 파일이 없는 경우와 로그가 빈 경우를 구분하지 못해서, `skip` 없이 조용히 넘어갑니다. `observability.*`의 Loki와 로그 에이전트 점검 항목 9개는 Loki와 Prometheus를 읽으므로 영향이 없습니다.

**`pods/proxy`.** `type: pod-metrics` 수집 단계 11개가 API 서버를 거쳐 컴포넌트 파드의 `/metrics`를 읽습니다. 경로는 `/api/v1/namespaces/<ns>/pods/<pod>:<port>/proxy/metrics`이고, 대상은 AWS Load Balancer Controller, Argo CD 세 곳, cert-manager, External Secrets, Grafana, Karpenter, KEDA 두 곳, MetalLB speaker입니다.

각 컴포넌트의 `*.metrics-unreadable`, `traffic.metallb-speaker-not-ready`, 그리고 이 메트릭으로 판정하는 `albctl.reconcile-errors`, `albctl.aws-api-churn`, `argocd.*` 컨트롤러 점검 항목, `certmanager.controller-errors`, `eso.provider-api-errors`, `karpenter.consistency-errors`, `keda.*`가 씁니다.

없으면 이 단계들이 실패합니다. 노드 접속 방법이 있으면 노드 안에서 같은 URL을 curl로 읽습니다. 접속 방법이 없으면 `metrics-unreadable` 항목이 warn을 내고 메트릭으로 판정하는 항목은 `skip`이 됩니다.

**`nodes/proxy`.** full 점검에서 `core/kubelet-configz` 단계 하나만 씁니다. `/api/v1/nodes/<node>/proxy/configz`로 kubelet 설정을 읽고, `node.kubelet-reserved-missing`, `node.kubelet-eviction-memory-missing`, `node.kubelet-api-qps-low` 세 항목이 그 결과를 봅니다.

역할에 이 권한을 남겨 둔 이유는 같은 정보를 얻을 다른 방법이 노드의 kubelet 설정 파일뿐이기 때문입니다. 그 파일을 읽으려면 노드 접속이 필요한데, GKE와 AKS 사용자에게는 접속 방법이 없습니다.

빼면 정확히 이 세 항목만 "kubelet not read"로 `skip`이 되고 다른 것은 바뀌지 않습니다. 단계는 노드마다 실패해서 7-1절에 나타나고, 노드 리포트에는 `kubelet configz (node proxy permission or kubelet not responding)`가 적힙니다.

**`pods/portforward`.** `lib/collection/portfwd.py`가 `kubectl port-forward svc/<store>`로 Prometheus, Alertmanager, Loki, Grafana에 연결합니다. 설정 파일에 `prometheus_url`, `alertmanager_url`, `loki_url`, `grafana_url`을 넣으면 쓰지 않습니다.

PromQL로 판정하는 모든 항목이 이 연결에 기댑니다. `type: metric` 항목 33개, Prometheus로 만드는 요약 섹션인 coredns, kube-proxy, 리소스, 스택 상태, daily의 `node.*` 메트릭, 그리고 prometheus, alertmanager, loki, grafana 영역입니다.

없으면 네 도구에 연결하지 못합니다. metric 항목은 "no Prometheus"로 `skip`이 되고 PromQL로 만드는 섹션은 비어 있습니다. 이 권한을 주는 대신 URL 네 개를 설정해도 됩니다.

**`metrics.k8s.io` 그룹.** `core/top.nodes`와 `core/top.pods`가 `kubectl top`으로 읽습니다. `summary.json`의 `metrics` 아래 `top-nodes`와 `top-pods`에 들어가는 CPU, 메모리 상위 30개 표에만 쓰입니다. 리소스 점검 항목은 Prometheus를 읽습니다. 없으면 두 단계가 실패하고 표가 비지만, 어떤 점검 항목의 결과도 바뀌지 않습니다.

### 코어 리소스

| 리소스 | 어디에 쓰나 | 없으면 |
|---|---|---|
| `services` | `lib/collection/monitoring.py`가 `get svc -A`로 네 모니터링 도구를 찾습니다. 트래픽, 복원력, 플랫폼, albctl, kubeproxy, 오퍼레이터의 80개 항목이 씁니다 | 설정에 URL이 없으면 모니터링 도구를 찾지 못합니다. `traffic.*`의 서비스 항목은 `skip`이 됩니다 |
| `endpoints` | `traffic.endpoint-zero`, `operators.webhook-no-endpoints` | 둘 다 `skip`이 됩니다. 이때 `summary.webhooks.no_endpoints`는 `None`입니다 |
| `namespaces` | 네임스페이스 수와 prod로 보이는 네임스페이스를 판단합니다. 복원력의 네임스페이스별 항목, `security.psa-not-enforced`, 멀티테넌시의 25개 항목이 씁니다 | 네임스페이스를 운영과 개발로 나눈 분류가 비어 있습니다 |
| `persistentvolumes` | 스토리지 18개, 복원력, ebscsi, k3s local-path 플랫폼 항목까지 64개 항목이 씁니다 | 스토리지 항목 `skip` |
| `persistentvolumeclaims` | 스토리지, 복원력의 36개 항목이 씁니다 | 스토리지 항목 `skip` |
| `resourcequotas`, `limitranges` | `tenancy.*` 12개 | 멀티테넌시 항목 `skip` |
| `serviceaccounts` | `security.sa-token-mounted-without-rbac`, albctl, karpenter, ebscsi, eso의 `no-dedicated-role` 항목 | 이 항목들 `skip` |

**`events`.** `core/events`가 `kubectl get events -A`로 읽습니다. `events.tracked-warning-reasons`, Warning 사유 기록, `recent_changes`, 리포트의 모든 문제에 붙는 이벤트 근거에 쓰입니다. `ecr.pull-failures`, `storage.volume-attach-errors`, `resilience.priority-inversion`, `traffic.pod-not-ready`, `ebscsi.node-ops-errors`, `vpccni.node-ip-exhaustion`의 이벤트 규칙도 이 데이터를 봅니다.

없으면 단계가 실패하고 `report-details.md`의 3절에 이벤트 변화가 나오지 않습니다. `ecr.pull-failures`는 `skip`이 됩니다. `events.tracked-warning-reasons`와 나머지 다섯 규칙의 이벤트 분기는 이벤트가 0건인 것으로 보고 조용히 넘어갑니다. 다른 분기는 그대로 판정합니다.

**`configmaps`.** `core/objects.dump-all`이 읽되, 값은 수집할 때 버립니다. `lib/foundations/scrub.py`의 `KEEP_VALUES`에 있는 키만 값을 남기고 나머지는 길이와 형태로 저장합니다. `argocd.*` 13개, `coredns.*` 10개, `kubeproxy.*` 8개, local-path의 `storage.*` 6개, `security.plaintext-configmap-secret`까지 38개 항목이 씁니다. 없으면 이 항목들이 `skip`이 되고, CoreDNS Corefile, kube-proxy 모드, Argo CD 설정을 알 수 없습니다.

### 표준 API 그룹

아래 그룹은 모두 전체 리소스에 `get`과 `list`를 줍니다. `core/objects.dump-all`이 읽고, 없으면 표의 항목이 `skip`이 됩니다. 다르게 동작하는 그룹은 표 아래에 적었습니다.

| 그룹 | 읽는 것 | 쓰는 점검 항목 |
|---|---|---|
| `batch` | CronJob과 Job. 컴포넌트 탐지에도 씁니다. descheduler 차트가 CronJob을 설치하기 때문입니다 | 복원력의 Job 항목, 위생, 멀티테넌시 |
| `autoscaling` | HorizontalPodAutoscaler | `scaling.*` 13개, coredns 오토스케일링, `platform.*` |
| `policy` | PodDisruptionBudget | 복원력의 PDB 항목, coredns, albctl, karpenter, keda의 가용성 항목 |
| `networking.k8s.io` | Ingress와 NetworkPolicy | `traffic.*` 19개, `security.networkpolicy-not-enforced`, `security.no-default-deny`, argocd, 모니터링 도구 Ingress를 보는 관측성 항목, certmanager, 스택 상태의 노출 항목 |
| `storage.k8s.io` | StorageClass | `storage.*` 18개, ebscsi, 복원력 |
| `rbac.authorization.k8s.io` | Role과 바인딩 | `security.cluster-admin-bindings`, `security.rbac-wildcard`, `security.secrets-read-permission`, `security.sa-token-mounted-without-rbac`, 멀티테넌시 |
| `admissionregistration.k8s.io` | 웹훅 설정 | `operators.webhook-no-endpoints`, `operators.webhook-self-lock`, `albctl.webhook-fail-policy-pods`, `keda.webhook-fail-policy`, `traffic.ingress-nginx-vulnerable-version`, certmanager, eso, metallb 요약의 웹훅 행 |
| `apiextensions.k8s.io` | CustomResourceDefinition. 컴포넌트 탐지에도 씁니다 | `hygiene.unused-crds`, `storage.csi-snapshot-unavailable`, 컴포넌트 탐지의 CRD 규칙 |
| `discovery.k8s.io` | EndpointSlice | 트래픽, kubeproxy, albctl. `albctl.webhook-fail-policy-pods`가 여기에 기댑니다 |
| `scheduling.k8s.io` | PriorityClass | 복원력의 우선순위 항목 |
| `apiregistration.k8s.io` | APIService | `scaling.*`의 외부 메트릭 항목, `keda.*`, `platform.*` |

- `admissionregistration.k8s.io`가 없으면 항목이 `skip`이 되거나 웹훅 행이 빠집니다. `traffic.ingress-nginx-vulnerable-version`은 admission 웹훅 포트가 NetworkPolicy로 막혀 있는지 볼 때 이 그룹을 씁니다.
- `apiextensions.k8s.io`가 없으면 `lib/foundations/components.py`의 CRD 규칙이 아무것도 찾지 못합니다. Deployment, DaemonSet, StatefulSet, 이미지 규칙은 그대로 동작합니다. `hygiene.unused-crds`와 CRD로만 찾는 컴포넌트는 `skip`이 됩니다.

### CRD 그룹

역할에는 CRD 그룹 16개가 있습니다. 모두 `core/objects.dump-all`이 읽습니다.

| 그룹 | 읽는 것 | 쓰는 점검 항목 |
|---|---|---|
| `monitoring.coreos.com` | PrometheusRule | `observability.*` 알림 규칙 항목 13개 |
| `karpenter.sh` | NodePool, NodeClaim | `karpenter.*` 9개, `scaling.*`, `cost.*` |
| `karpenter.k8s.aws` | EC2NodeClass | `karpenter.ec2nodeclass-al2`, `karpenter.ec2nodeclass-hardening`, `security.imds-hop-limit`의 근거 |
| `keda.sh` | ScaledObject, ScaledJob, TriggerAuthentication | `keda.*` 8개, `scaling.*` |
| `external-secrets.io` | ExternalSecret, PushSecret | `eso.*` 8개, `security.externalsecret-not-ready` |
| `argoproj.io` | Application, ApplicationSet, AppProject | `argocd.*` 13개 |
| `cert-manager.io` | Certificate, CertificateRequest, Issuer, ClusterIssuer | `certmanager.*` 9개 |
| `acme.cert-manager.io` | Order, Challenge | `certmanager.acme-challenge-failing` |
| `metallb.io` | IPAddressPool, L2Advertisement, BGPAdvertisement, BGPPeer, ServiceL2Status, ServiceBGPStatus, ConfigurationState | `traffic.metallb-pool-near-full`, `traffic.metallb-l2-leader-concentration`, `traffic.metallb-config-stale`, `traffic.metallb-single-lb-service`, `traffic.metallb-version-old`, `traffic.metallb-speaker-not-ready`, `traffic.metallb-service-ip-not-announced`, `traffic.metallb-bgp-session-down` |
| `frrk8s.metallb.io` | BGPSessionState (MetalLB 0.15.2 이상의 frr-k8s 모드가 노드·피어마다 씀) | `traffic.metallb-bgp-session-down` (frr-k8s 모드) |
| `elbv2.k8s.aws` | TargetGroupBinding, IngressClassParams | `albctl.tgb-stale-or-orphan`, `traffic.*`의 ALB 행 |
| `networking.k8s.aws` | PolicyEndpoint | VPC CNI 네트워크 정책을 보는 `security.networkpolicy-not-enforced` |
| `crd.k8s.amazonaws.com` | ENIConfig | `vpccni.*`의 커스텀 네트워킹 행 |
| `snapshot.storage.k8s.io` | VolumeSnapshot, VolumeSnapshotClass | `storage.csi-snapshot-unavailable` |

이 13개 그룹은 없으면 표의 항목이 `skip`이 됩니다. 나머지 세 그룹은 동작이 다릅니다.

- `k3s.cattle.io`: `etcdsnapshotfiles`를 읽습니다. 최근 k3s etcd 스냅샷이 있으면 `resilience.no-backup`이 warn으로 내려가고, `eks.no-backup-policy`의 근거에도 들어갑니다. `platform.k3s-etcd-snapshot-*` 항목은 노드 스크립트를 읽습니다. 백업을 etcd 스냅샷으로 하는 k3s 클러스터에서 이 그룹이 없으면 `resilience.no-backup`이 warn 대신 fail이 됩니다.
- `actions.github.com`: `autoscalingrunnersets`를 읽습니다. 멀티테넌시에서 러너 워크로드를 구분할 뿐 판정하지는 않습니다. 없으면 러너 워크로드를 일반 워크로드로 셉니다.
- `actions.summerwind.dev`: `runnerdeployments`를 읽고, 쓰임과 없을 때의 동작은 `actions.github.com`과 같습니다.

이 역할로 돌리면 16개 밖의 CRD는 읽을 수 없습니다. `objects.dump-all`은 API 서버가 제공하는 종류 중 하나로 그 CRD를 나열하지만, LIST가 거부되어 `not_permitted`에 기록합니다. `report-details.md`의 7-1절에는 "Kinds the ClusterRole does not grant"로 나옵니다. 이런 종류를 읽는 점검 항목은 없으므로 빠지는 점검도 없습니다. 관리자 kubeconfig로 돌리면 나열할 수 있는 종류를 전부 저장합니다.

이 역할을 전용 사용자에 묶어 돌리는 방법은 [SETUP.md](SETUP.md#가장-좁은-권한으로-돌리기)에 있습니다.

### 읽지 않는 것

**Secret.** 역할에 `secrets` 항목이 없고, `objects.dump-all`도 이 종류를 제외하고, 코드의 어떤 `kubectl` 호출도 Secret을 요청하지 않습니다. `tests/test_permissions.py`가 모든 호출을 검사합니다. 이름과 종류는 kube-state-metrics의 `kube_secret_info` 메트릭에서 얻습니다.

예외는 Helm 하나입니다. full 점검의 `core/helm-list` 단계에서 `helm list`가 Helm이 Secret에 저장한 릴리스 기록을 읽고, kubegap은 이름, 네임스페이스, 상태, 리비전, 차트, 앱 버전을 남깁니다. 이 역할로는 `helm list`가 실패하고 Helm 점검 항목 2개가 `skip`이 됩니다. 이 두 항목이 필요할 때만 `secrets` 읽기 권한을 주세요.

**ConfigMap 값.** `lib/foundations/scrub.py`가 수집할 때 값을 모두 버리고 길이와 형태를 저장합니다. 예외는 `KEEP_VALUES`의 키로, CoreDNS Corefile과 kube-proxy 설정 같은 컴포넌트 설정입니다.

**쓰기 verb가 있는 것.** 역할에는 `get`, `list`와 `pods/portforward`의 `create` 하나만 있습니다. IAM 정책에는 Describe, List, Get 액션과 문서 하나로 제한한 `ssm:SendCommand`만 있습니다. `tests/test_permissions.py`가 코드의 모든 `kubectl`, `aws` 호출에서 verb를 검사합니다.

## AWS 권한

EKS에서만 씁니다. 정책의 와일드카드와 코드가 실제로 부르는 호출이 서로 맞는지는 `tests/test_permissions.py`가 양방향으로 확인합니다.

### 클러스터 정보

**`sts:GetCallerIdentity`.** `lib/commands/setup.py`가 AWS CLI를 쓸 수 있는지, 어느 계정인지 확인합니다. 결과는 `setup`에만 나옵니다. 없으면 `setup`이 AWS를 쓸 수 없다고 알립니다. 수집은 kubeconfig의 `cluster.eks`로 판단하므로 AWS 수집 단계는 그대로 돌고, 단계마다 자기 액션 권한에 따라 성공하거나 실패합니다.

**`eks:Describe*`.** 클러스터, 노드 그룹, 애드온 정보를 읽습니다. 코드가 부르는 호출은 `describe-cluster`, `describe-nodegroup`, `describe-addon`, `describe-addon-versions`, `describe-cluster-versions`이고, 뒤의 두 호출은 full에서만 씁니다. `eks.audit-log-off`, `eks.public-endpoint-open`, `eks.extended-support`, `eks.addon-outdated`, `eks.nodegroup-ami-old`, `security.eks-secrets-encryption-off`, 애드온 설정을 보는 `vpccni.*`가 이 정보를 씁니다.

없으면 `inventory.json`의 EKS 정보에 `error`만 남고, `eks.*` 인벤토리 항목이 "EKS facts not read"로 `skip`이 됩니다. `security.eks-secrets-encryption-off`는 `kms_encryption`이 없어 조용히 넘어갑니다. 플랫폼 판단은 kubeconfig로 하므로 그대로 됩니다.

**`eks:List*`.** `list-addons`, `list-nodegroups`, `list-insights`, `list-pod-identity-associations`를 부릅니다. 뒤의 두 호출은 full에서만 씁니다. `eks.addon-outdated`, `eks.nodegroup-ami-old`, `platform.*`의 인사이트 행, `security.*`의 pod identity 행이 씁니다. 없으면 앞의 두 항목이 `skip`이 되고 인사이트와 pod identity 행이 비어 있습니다.

**`ec2:Describe*`.** 코드가 부르는 호출은 `describe-subnets`, `describe-security-groups`, `describe-volumes`, `describe-addresses`, `describe-nat-gateways`, `describe-instance-types`, `describe-route-tables`, `describe-snapshots`, `describe-instances`, `describe-spot-price-history`입니다. 수집 단계 가운데 `ec2-root-volumes`, `route-tables`, `ec2-snapshots-30d`, `ec2-instances-imds`, `ec2-spot-prices`는 full에서만 돌아갑니다.

쓰는 항목은 `eks.security-group-open-to-world`, `vpccni.subnet-ips-low`, `vpccni.external-snat-off-with-private-routes`, `vpccni.max-pods-exceeds-ip-capacity`, `storage.ebs-unattached`, `storage.ebs-gp2-volumes`, `storage.ebs-unencrypted`와 이 세 항목의 30일 스냅샷 근거, `cost.unused-eip`, `cost.on-demand-in-spot-pool`, `security.imds-hop-limit`, 로드밸런서 보안 그룹을 보는 `traffic.db-exposed`입니다.

없으면 `vpccni.*`, `cost.*`, `traffic.db-exposed`는 `skip`이 되거나 보안 그룹을 읽지 못했다고 적습니다. `eks.security-group-open-to-world`, `storage.ebs-*`, `security.imds-hop-limit`는 `skip`이 됩니다.

### 트래픽과 메트릭

**`elasticloadbalancing:Describe*`.** `eks-platform/alb-metrics`가 `lib/collection/albmetrics.py`로 로드밸런서, 속성, 리스너, 타깃 그룹과 그 속성, 타깃 상태를 읽습니다. 호출은 `describe-load-balancers`, `describe-load-balancer-attributes`, `describe-listeners`, `describe-target-groups`, `describe-target-group-attributes`, `describe-target-health`입니다. `traffic.db-exposed`, `traffic.ingress-*`의 ALB 행, `cost.idle-load-balancer`, `albctl.*`의 타깃 그룹 행이 쓰고, 없으면 이 항목들이 `skip`이 됩니다.

**`cloudwatch:GetMetricData`.** `eks-platform/alb-metrics`가 ALB 요청, 5xx, 지연 메트릭을 읽고, full에서는 `eks-platform/quota-usage`와 `eks-platform/ebs-volume-metrics`도 씁니다. 없으면 `traffic.ingress-5xx-ratio`와 `traffic.ingress-p95-latency`의 ALB 행, `eks.service-quota-near-limit`, `storage.ebs-volume-io-saturated`가 `skip`이 됩니다.

### 컨트롤플레인 로그

**`logs:DescribeLogGroups`.** `lib/commands/setup.py`가 컨트롤플레인 로그 그룹이 있는지 확인합니다. 결과는 `setup`에만 나옵니다. 없으면 `setup`에 이 확인이 실패했다고 나올 뿐 다른 것은 바뀌지 않습니다.

**`logs:StartQuery`, `logs:GetQueryResults`.** full 점검에서 `eks-platform/controlplane-logs`가 `lib/collection/cwlogs.py`로 최근 24시간을 Logs Insights로 조회하고 결과를 읽습니다. `controlplane.scheduler-unschedulable`, `controlplane.webhook-call-failures`, `controlplane.controller-error-repeat`, `controlplane.apiserver-slow-traces`, `controlplane.authenticator-failures`, `controlplane.etcd-slow` 여섯 항목이 씁니다. 둘 중 하나라도 없으면 EKS에서 이 여섯 항목이 `skip`이 됩니다. k3s에서는 이 항목들이 노드 접속으로 저널을 읽습니다.

**`logs:StopQuery`.** 시간 초과로 쿼리를 포기할 때 부릅니다. 없으면 포기한 쿼리가 자체 시간 제한까지 AWS 쪽에서 계속 돌아갑니다.

### 노드 명령

이 네 권한은 EKS에서 노드에 명령을 보낼 때 씁니다.

**`ssm:DescribeInstanceInformation`.** `lib/commands/setup.py`와 `lib/collection/discover.py`가 어떤 노드가 SSM에 등록되어 있는지 확인해 `ssm_unregistered` 목록을 만듭니다. `eks-platform/ssm-instances`도 씁니다. `eks.ssm-unregistered`가 직접 쓰고, 등록되지 않은 노드에는 명령이 가지 않으므로 `node.*` 전체가 간접적으로 기댑니다. 없으면 `discover`가 오류를 기록하고 노드 접속 방식을 `none`으로 정해서 `send-command`를 보내지 않습니다. 노드 스크립트 항목 21개가 모든 노드를 "node not read"로 건너뛰고, 등록 목록이 `None`이므로 `eks.ssm-unregistered`는 `skip`이 됩니다.

**`ssm:DescribeDocument`.** `lib/commands/setup.py`와 `lib/collection/nodecommands.py`가 `kubegap-node-read`가 계정에 있고 최신인지 확인합니다. 쓰는 항목은 `ssm:SendCommand`와 같습니다. 없으면 kubegap이 SSM 문서가 저장소의 것과 같은지 확인할 수 없어서 노드 명령을 보내지 않습니다.

**`ssm:SendCommand`.** `lib/collection/node.py`가 `type: node` 수집 단계와, API 서버 프록시가 막혔을 때 파드 메트릭을 대신 읽는 동작에 씁니다. 수집 단계는 full 전용이고, 메트릭을 대신 읽는 curl은 daily와 full 모두에서 돌아갑니다.

노드 스크립트와 kubelet configz를 읽는 `node.*` 항목 26개, `vpccni.*`의 ipamd 행, `vpc-cni.*` 로그 시그니처 셋(ipamd.log), `kubeproxy.*`의 모드 행, `*.metrics-unreadable`의 대체 경로가 씁니다. `node.*`의 나머지 10개는 Prometheus를 읽습니다. 없으면 이 노드 항목들은 daily에서 수집되지 않고, full에서는 읽지 못한 노드마다 `skip`이 됩니다. 파드 메트릭을 대신 읽을 수도 없어서 `metrics-unreadable`이 warn을 냅니다.

**`ssm:GetCommandInvocation`.** `lib/collection/node.py`가 모든 SSM 명령의 결과를 읽습니다. 쓰는 항목은 `ssm:SendCommand`와 같습니다. 없으면 명령은 가지만 출력을 읽지 못해서 노드 단계가 실패합니다.

### 수집 단계 하나만 쓰는 권한

아래 권한은 수집 단계 하나만 쓰고, 없으면 표의 항목이 `skip`이 됩니다. `acm:ListCertificates`는 daily와 full 모두에서 쓰고, 나머지는 full 전용입니다.

| 권한 | 수집 단계 | 쓰는 점검 항목 |
|---|---|---|
| `acm:ListCertificates` | `eks-platform/acm-certificates` | `eks.acm-certificate-expiring`. 없으면 "acm not available"로 `skip`이 됩니다 |
| `servicequotas:ListServiceQuotas` | `eks-platform/service-quotas` | `eks.service-quota-near-limit`. 없으면 "quotas not available"로 `skip`이 됩니다 |
| `dlm:GetLifecyclePolicies` | `eks-platform/dlm-policies` | `eks.no-backup-policy`. 두 목록이 다 있어야 합니다 |
| `backup:ListBackupPlans` | `eks-platform/backup-plans` | `eks.no-backup-policy`. 두 목록이 다 있어야 합니다 |
| `ecr:DescribeImages` | `ecr/images` | `ecr.untagged-images`, `ecr.tag-mutable-prod`, `ecr.scan-disabled`의 이미지 행 |
| `ecr:DescribeRegistry` | `ecr/registry` | `ecr.no-replication` |
| `ecr:DescribePullThroughCacheRules` | `ecr/pull-through-cache` | `ecr.dockerhub-dependency` |
| `ecr:GetLifecyclePolicy` | `ecr/lifecycle-policy` | `ecr.no-lifecycle-policy`, `ecr.untagged-images` |
| `ecr:GetRegistryScanningConfiguration` | `ecr/scanning-configuration` | `ecr.scan-disabled` |
| `ce:GetCostAndUsage` | `eks-platform/ce-cost-30d` | `cost.*` 7개 |
| `pricing:GetProducts` | `eks-platform/pricing-ondemand` | `cost.idle-compute-high`, `cost.request-waste`, `cost.on-demand-in-spot-pool`, `cost.idle-node` |

**`ecr:DescribeRepositories`.** daily와 full 모두에서 `lib/collection/discover.py`가 저장소 이름을 읽고, ECR 수집기는 이 목록의 저장소마다 돌아갑니다. `ecr.*` 8개가 기대는 권한입니다. 없으면 ECR 수집기가 살펴볼 저장소가 없어서 ECR 항목이 `skip`이 됩니다.

## IAM 권한이 하나도 없을 때 (#22)

보안팀이 IAM 정책을 승인하기 전에 EKS 점검을 먼저 돌려 보고 싶은 경우가 많습니다. 다만 "AWS 자격 증명 없이" 돌리는 경우는 없습니다. EKS 클러스터의 kubeconfig는 `aws eks get-token`으로 인증하기 때문에 AWS 신원이 항상 하나는 있습니다. 실제로 있는 경우는 클러스터는 읽을 수 있지만(액세스 엔트리나 `aws-auth` 매핑으로 `deploy/permissions/clusterrole.yaml`에 묶인 신원) IAM 정책은 하나도 없는 신원입니다. 2026-11-06에 관리자의 클러스터(EKS 1.32, 노드 8대, `prod` 프로파일)에서 딱 그 권한만 있는 IAM 역할로 재 봤습니다. `sts get-caller-identity`를 뺀 모든 AWS 호출이 `AccessDenied`로 거부되고, `kubegap setup`은 AWS 절에 거부된 호출을 적고, 수집·요약·판정은 끝까지 돌아갑니다.

| 모드 | 점검 항목 | 판정함 | IAM 권한이 없어서 건너뜀 | 다른 이유로 건너뜀 | 이 모드에서 수집하지 않음 |
|---|---|---|---|---|---|
| daily | — | — | 0 | — | — |
| full | 365 | 295 | 57 | 6 (같은 4개에 Helm 점검 항목 2개가 더해집니다. 기본 ClusterRole이 Secret을 막아서 `helm list`가 돌지 못합니다) | 0 |

daily 줄은 daily 점검이 AWS를 부르던 때에 잰 값이었습니다. 지금 daily 점검은 Kubernetes API와 저장소만 읽고 AWS를 부르지 않으므로, IAM 정책이 없어도 달라지는 것이 없습니다. AWS가 필요한 점검 항목은 "이 모드에서 수집하지 않음"으로 적힙니다.

각 줄에서 남는 4개는 이 플랫폼에서 돌지 않는 2개와 LLM 점검 항목 2개입니다. 시험한 컴퓨터에 없던 도구(krr, polaris)의 항목은 뺐습니다.

없는 권한 때문에 못 보는 것은 아래와 같습니다. 하나하나 이유를 붙여 건너뜀으로 적히고, 통과로 세지 않습니다.

- 노드 스크립트와 kubelet 설정을 읽는 `node.*` 점검 항목 23개(SSM `send-command`가 거부됩니다. Prometheus를 읽는 노드 점검 항목 10개는 그대로 돌아갑니다)와 `eks.ssm-unregistered`
- `describe-cluster`와 거기서 이어지는 호출을 읽는 EKS 점검 항목 11개: `eks.audit-log-off`, `eks.public-endpoint-open`, `eks.node-os-skew`, `eks.extended-support`, `eks.no-backup-policy`, `eks.addon-outdated`, `eks.nodegroup-ami-old`, `eks.security-group-open-to-world`, `eks.acm-certificate-expiring`, `eks.service-quota-near-limit`, `vpccni.external-snat-off-with-private-routes`
- `ecr.*` 점검 항목 8개와 `storage.ebs-*` 점검 항목 4개
- API 서버 프록시가 막혀 있을 때 노드를 거쳐 읽는 파드 `/metrics`. 이 클러스터에서는 `albctl.aws-api-churn`, `albctl.reconcile-errors`, `argocd.backend-errors`, `eso.provider-api-errors`, `karpenter.consistency-errors`, `karpenter.nodepool-usage-near-limit`, `keda.external-metrics-api-errors`, `vpccni.ec2-api-errors`, `grafana.alerting-failures`, `grafana.datasource-errors`가 이 경로로 읽습니다. 대신 `*.metrics-unreadable`이 warn을 냅니다.
- full 모드에서는 컨트롤플레인 로그 점검 항목 뒤의 Logs Insights 질의와 `cost.*` 점검 항목 7개의 AWS 입력도 못 봅니다. 컨트롤플레인 로그 점검 항목 6개 중 `controlplane.etcd-slow`는 `prod`에서 꺼져 있고, `controlplane.scheduler-unschedulable`, `controlplane.webhook-call-failures`, `controlplane.controller-error-repeat`는 빈 개수로 판정되고, 2개는 빈 결과로 통과합니다(다음 문단).

이런 리포트를 읽을 때 알아 둘 것이 둘 있습니다. 첫째, `describe-cluster`는 discover가 그 위에 쌓는 호출입니다. 거부되면 인벤토리에 클러스터 이름, 리전, 계정만 남고, 거기서 VPC id, 서브넷 id, 노드 그룹, 애드온을 가져가는 단계(`subnets`, `cluster-security-groups`, `route-tables`, `cluster-versions`, `nodegroup`, `addon-versions`, `ecr/images`, `ecr/lifecycle-policy`)는 거부가 아니라 빈 입력("목록이 비어 있음", "플레이스홀더에 값이 없음")으로 적힙니다. 거부 자체는 `run.log`와 `setup` 출력에 있습니다. 둘째, AWS 입력이 거부돼도 판정까지 가서 빈 결과로 통과하는 점검 항목이 8개 있습니다. `cost.idle-compute-high`, `cost.request-waste`, `cost.on-demand-in-spot-pool`, `cost.unused-eip`, `cost.idle-load-balancer`, `security.imds-hop-limit`, `controlplane.apiserver-slow-traces`, `controlplane.authenticator-failures`입니다. 이 항목들에는 "needs" 조건이 없습니다. [#141](https://github.com/KyungHwanKim-devs/kubegap/issues/141)에서 고칠 예정이고, 그전까지는 이런 실행에서 이 항목들이 통과했다는 것은 아무것도 읽지 못했다는 뜻입니다.

## 노드에 닿는 명령

EKS에서는 `ssm:SendCommand`로 노드에 들어갑니다. k3s와 베어메탈에서는 같은 스크립트를 SSH로 보내고, 두 방법 다 없으면 노드를 읽지 않습니다. 필요한 준비는 [`deploy/node-access/README.md`](../../deploy/node-access/README.md)에 있습니다.

`type: node` 수집 단계는 모두 full 전용입니다.

| 플랫폼 | 수집 단계 |
|---|---|
| 모든 플랫폼 | `core/node-os`, `kube-proxy/proxy-mode` |
| EKS | `eks-platform/kubelet-journal`, `eks-platform/containerd-journal`, `vpc-cni/ipamd-metrics`, `vpc-cni/ipamd-log` |
| k3s | `k3s-platform/k3s-journal-errors`, `k3s-platform/k3s-journal-stats`, `k3s-platform/k3s-scheduler-unschedulable`, `k3s-platform/k3s-webhook-failures`, `k3s-platform/k3s-etcd-slow`, `k3s-platform/kubelet-pleg`, `k3s-platform/k3s-node`, `k3s-platform/containerd-log` |

파드 메트릭을 대신 읽는 curl은 daily와 full 모두에서 돌아갑니다. 접속 방식별 명령 전문은 [`deploy/node-access/COMMANDS.md`](../../deploy/node-access/COMMANDS.md)에 있습니다.

## `ssm:SendCommand`를 제한하는 방법

정책에는 `ssm:SendCommand`가 두 번 나오고, 명령이 실행되려면 두 구문이 모두 맞아야 합니다.

- SSM 문서: `arn:aws:ssm:*:<ACCOUNT_ID>:document/kubegap-node-read`만 허용합니다.
- 인스턴스: `kubernetes.io/cluster/<CLUSTER_NAME>=owned` 태그가 있는 것만 허용합니다.

그래서 이 정책을 가진 키로는 그 SSM 문서 하나를, 그 클러스터의 노드에서만 실행할 수 있습니다. 다른 것은 실행할 수 없습니다.

SSM 문서는 [`deploy/permissions/ssm-document.yaml`](../../deploy/permissions/ssm-document.yaml)입니다. 매개변수 `step`은 고정된 읽기 명령 목록에서 하나를 고릅니다. 다른 매개변수는 둘뿐입니다. `podIp`는 `allowedPattern`으로 IPv4 주소만 받고, `executionTimeout`은 숫자만 받습니다.

명령은 접속 방식별로 [`deploy/node-access/COMMANDS.md`](../../deploy/node-access/COMMANDS.md)에 있습니다. 이 파일과 SSM 문서는 수집기 정의에서 생성하고, 둘 중 하나라도 최신이 아니면 테스트가 실패합니다.

명령을 보내기 전에 `lib/collection/node.py`가 로컬 SSM 문서와 계정에 있는 SSM 문서의 sha256을 비교하고, 다르면 보내지 않습니다.

SSM 문서를 올릴 때는 `ssm:CreateDocument`, `ssm:UpdateDocument`, `ssm:UpdateDocumentDefaultVersion`, `ssm:ListDocumentVersions`가 내 자격 증명에 한 번 필요합니다. `kubegap setup --install-ssm-document`로 올리고, 이 권한들은 점검 정책에 들어 있지 않습니다.
