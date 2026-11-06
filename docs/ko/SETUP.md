# 연결과 설정

English: [SETUP.md](../SETUP.md)

이 문서를 읽지 않아도 kubegap을 시작할 수 있습니다. `kubectl get nodes`가 되면 기본 점검이 돌아가고, 그 이상은 처음 실행할 때 물어봅니다. 이때 무엇을 읽고 무엇을 고르는지는 [README의 "처음 돌릴 때"](../../README.ko.md#처음-돌릴-때)에 있습니다.

이 문서는 kubegap이 각 대상에 어떻게 연결하는지 알고 싶을 때, 설정을 바꿀 때, 연결을 직접 확인할 때, 가장 좁은 권한으로 돌릴 때 읽으세요.

kubegap은 자격 증명을 따로 저장하지 않습니다. kubeconfig, AWS CLI, SSH 설정처럼 내 컴퓨터에 이미 있는 것을 그대로 씁니다.

## kubegap이 연결하는 곳

| 연결 대상 | 연결 정보를 가져오는 곳 | 직접 할 일이 생기는 경우 |
|---|---|---|
| Kubernetes API | kubeconfig의 현재 컨텍스트 또는 `--context <name>` | `kubectl get nodes`가 되면 없습니다 |
| AWS, EKS일 때만 | 설정 파일의 `aws_profile`과 `aws_region`. 없으면 kubeconfig `exec` 블록의 `AWS_PROFILE`, 그것도 없으면 AWS CLI 기본 설정 | kubectl이 쓰는 프로파일과 다른 프로파일로 점검하고 싶을 때 |
| Prometheus, Alertmanager, Loki, Grafana | 클러스터의 Service를 찾아 포트포워드로 연결합니다 | 클러스터 밖에서 돌고 있을 때. 첫 실행에서 주소를 묻습니다 |
| apiserver 메트릭 | `apiserver_request_total`에서 찾아낸, apiserver를 수집하는 job의 `job` 레이블 | 수집 설정의 job 이름을 kubegap이 알아보지 못할 때. `apiserver_job`을 지정하세요 |
| Grafana 데이터소스와 대시보드 목록 | Grafana 사이드카가 읽는 ConfigMap(라벨 `grafana_dashboard`, `grafana_datasource`). 토큰이 필요 없습니다. Grafana 화면에서 만든 대시보드까지 보려면 설정 파일의 `grafana_api_token` | Grafana가 세는 대시보드가 ConfigMap보다 많을 때. 첫 실행에서 몇 개인지와 토큰 만드는 법을 알려 줍니다 |
| 노드 안쪽, EKS | SSM `send-command`와 SSM 문서 `kubegap-node-read` | AWS 계정마다 한 번. 첫 실행에서 SSM 문서를 올릴지 묻습니다 |
| 노드 안쪽, k3s와 베어메탈 | `~/.ssh/config`의 사용자와 키로 각 노드의 InternalIP에 SSH 접속 | 그렇게 닿지 않는 노드가 있을 때. 첫 실행에서 주소를 묻습니다 |
| 노드 안쪽, GKE, AKS와 그 밖의 관리형 노드 | 직접 적용한 DaemonSet에 `kubectl exec` | 이 환경에서 노드 점검을 하고 싶을 때. 첫 실행에서 명령을 보여 줍니다 |
| 추가 도구 | `PATH` | 도구가 없을 때. 첫 실행에서 설치할지 묻습니다 |

연결이 없으면 그 연결이 필요한 점검 항목만 빠지고, 빠졌다는 사실을 리포트에 적습니다. 다른 점검은 멈추지 않습니다.

## 첫 실행 질문

`kubegap setup`은 클러스터와 내 컴퓨터를 살펴보고 빠진 것을 질문으로 정리합니다. `/kubegap`을 치면 이 명령이 먼저 돌고, 질문마다 선택지가 뜹니다. 질문에는 무엇을 위한 것인지와 고르면 무엇이 늘어나는지가 같이 나오고, 모두 건너뛸 수 있습니다.

| 질문 | 묻는 때 | 선택지 |
|---|---|---|
| `home-mode` | `~/.kubegap` 아래 폴더를 이 컴퓨터의 다른 사용자가 읽을 수 있을 때 (옛 kubegap이 만들었거나 직접 권한을 넓힌 경우) | 지금 고치기 (`kubegap protect-home`, chmod 700) · 그대로 두기 |
| `tools` | 추가 도구가 설치되어 있지 않을 때 | 전부 설치 · 건너뛰기 · 도구 이름을 적어 그 도구만 설치 |
| `ssm-document` | EKS에서 SSM 문서가 없거나 kubegap에 들어 있는 SSM 문서보다 오래됐을 때 | 올리기 · 건너뛰기 |
| `node-ssh` | k3s, RKE2 또는 kubegap이 알아보지 못한 플랫폼이고, 설정 파일에 노드 접속(`ssh:` 블록이나 `node_access`)이 없고, DaemonSet 파드도 없을 때 | 지금 SSH 확인 · 건너뛰기. 응답하지 않는 노드가 있으면 호스트 키 받기 또는 다시 확인 · 응답한 노드만 쓰기 · 건너뛰기 · 노드별 주소 입력 |
| `node-daemonset` | GKE나 AKS에서 노드 DaemonSet이 돌고 있지 않을 때 | 명령 보기 · 건너뛰기 |
| `grafana-token` | Grafana를 찾았고 토큰이 없는데, 사이드카용 대시보드·데이터소스 ConfigMap이 하나도 없거나 Grafana가 세는 대시보드가 그 ConfigMap보다 많을 때 | 방법 보기 · 건너뛰기 |
| `stores` | Prometheus, Alertmanager, Loki, Grafana 중 클러스터에 Service가 없는 것이 있을 때. 로그 수집기(fluent-bit, fluentd, promtail) 설정에 로그가 다른 곳으로 간다고 적혀 있으면 Loki는 묻지 않고, 리포트에 어디로 가는지 적습니다 | 설치 안 함 · 다음에 다시 묻기 · 주소 입력 |

답은 클러스터별로 `~/.kubegap/snapshots/<context>/answers.json`에 저장됩니다. 건너뛴 질문은 다시 묻지 않고, 무엇을 건너뛰었는지는 리포트에 적습니다. 전부 다시 고르려면 `/kubegap setup`을 실행하세요.

같은 일을 직접 하려면 이렇게 실행하세요.

```bash
scripts/kubegap setup --context <name>               # 상태를 확인하고 아직 답하지 않은 질문을 보여 줍니다
scripts/kubegap questions --context <name> --all     # 이미 답한 질문까지 전부 보여 줍니다
scripts/kubegap answer --context <name> node-ssh skip
scripts/kubegap answer --context <name> --forget     # 이 클러스터의 답을 전부 지웁니다
```

## 노드 안쪽

디스크, inode, 커널 로그, kubelet 설정, 컨테이너 런타임은 Kubernetes API로 볼 수 없습니다. 그래서 kubegap은 노드에서 정해 둔 읽기 명령만 실행해서 이 정보를 읽습니다. 명령 목록은 [`deploy/node-access/COMMANDS.md`](../../deploy/node-access/COMMANDS.md)에 있습니다.

kubegap을 쓰면서 내 컴퓨터 바깥에 무언가를 준비해야 할 수 있는 곳은 여기뿐입니다. full 점검은 노드 점검 항목을 판정할 때 노드에 접속합니다. daily 점검은 Prometheus가 수집하지 않고 API 서버 프록시로도 닿지 않는 컴포넌트의 `/metrics`를 읽을 때만 접속합니다.

**EKS.** SSM으로 노드를 읽습니다. 실행할 명령은 SSM 문서 [`deploy/permissions/ssm-document.yaml`](../../deploy/permissions/ssm-document.yaml) 하나에 고정되어 있고, 이 SSM 문서가 AWS 계정에 있어야 합니다. 첫 실행에서 올릴지 묻습니다. 올릴 때는 지금 쓰는 자격 증명으로 한 번 호출하고, `ssm:CreateDocument`, `ssm:UpdateDocument`, `ssm:UpdateDocumentDefaultVersion`, `ssm:ListDocumentVersions` 권한이 필요합니다. 점검 자체에는 이 권한이 필요 없습니다. 노드 IAM 역할에는 `AmazonSSMManagedInstanceCore`가 있어야 합니다. EKS 최적화 AMI에서는 SSM 에이전트가 이미 돌고 있습니다.

**k3s, RKE2, 베어메탈, kubeadm.** SSH로 노드를 읽습니다. 다만 사용자가 정한 뒤에만 접속합니다. 첫 실행 질문에서 "지금 SSH 확인"을 골랐거나, `scripts/kubegap nodes`를 직접 실행했거나, 설정 파일에 `ssh:` 블록이나 `node_access: ssh`가 있는 경우입니다. 그 전에는 SSH 연결을 하나도 만들지 않습니다.

접속할 때는 `~/.ssh/config`의 사용자와 키로 각 노드의 InternalIP에 연결합니다. 비밀번호는 묻지 않고, 호스트 키가 `~/.ssh/known_hosts`에 이미 있는 노드에만 접속합니다. 접속이 안 되면 첫 실행 질문이 노드마다 이유를 알려 주고, 아래 해결 방법을 답으로 받습니다.

- 내 컴퓨터에서 노드의 InternalIP에 닿지 않을 때: Tailscale 같은 오버레이 네트워크가 대표적입니다. 닿는 주소를 `ssh.hosts.<node>`에 적으세요.
- 호스트 키가 아직 등록되지 않았을 때: 직접 한 번 로그인하거나, `ssh.accept_new_hosts: true`를 설정해서 처음 보는 키를 ssh가 저장하게 하세요.
- 로그인이 거부될 때: `ssh.user`와 `ssh.key`를 설정하세요.

일부 정보는 로그인만으로 읽히지 않습니다. 사용자가 로그를 읽는 그룹에 들어 있어야 하고, 선택 사항인 sudoers 파일을 넣으면 root만 읽을 수 있는 나머지도 읽힙니다. 방법은 [`deploy/node-access/README.md`](../../deploy/node-access/README.md)에 있습니다. kubegap은 노드에서 아무것도 바꾸지 않으므로 이 설정은 직접 하세요.

**GKE, AKS, SSM도 SSH도 없는 관리형 노드.** [`deploy/node-access/daemonset.yaml`](../../deploy/node-access/daemonset.yaml)과 [`deploy/permissions/role-daemonset-exec.yaml`](../../deploy/permissions/role-daemonset-exec.yaml)을 적용하세요. DaemonSet 이미지는 다이제스트로 고정되어 있습니다. 다음 점검에서 kubegap이 파드를 찾아 `kubectl exec`로 노드를 읽습니다. 이 파드는 privileged로 돌아갑니다. 계속 남겨 두고 싶지 않으면 점검이 끝난 뒤 `kubegap` 네임스페이스를 지우세요. kubegap이 대신 적용하는 일은 없습니다.

노드 접속은 첫 수집 전을 포함해 언제든 확인할 수 있습니다.

```bash
scripts/kubegap nodes --context <name>
```

이 명령은 클러스터에서 노드 목록을 읽어 모든 노드에 `uname`과 `hostname`을 보냅니다. 결과에서 노드마다 응답했는지를 볼 수 있고, SSH라면 어떤 권한 읽기가 허용되는지도 볼 수 있습니다.

## 추가 도구

kubegap은 helm, krr, polaris, pluto, kubent를 `PATH`에서 찾습니다. EKS에서는 aws, SSH를 쓰는 플랫폼에서는 ssh도 찾습니다. `kubegap setup`을 실행하면 없는 도구와 그 도구의 결과를 쓰는 점검 항목이 나오고, 첫 실행 질문이 설치할지 묻습니다. 설정에 `install_tools: never`를 두면 그 질문을 건너뛰고 아무것도 설치하지 않습니다. 아래 표는 도구마다 어느 점검 항목에 쓰이는지, 어느 모드에서 돌아가는지, 설치하면 어디에 들어가는지, 없으면 리포트에 어떻게 적히는지입니다. `scripts/kubegap tools --markdown --language ko`가 `lib/tools.py`와 점검 카탈로그에서 만들고, 테스트가 최신인지 확인합니다.

<!-- tools-table:begin -->
| 도구 | 하는 일 | 쓰는 점검 항목 | 모드 | 설치 방법과 위치 | 없으면 |
|---|---|---|---|---|---|
| aws | EKS, EC2, SSM, CloudWatch 조회(EKS 프로필에서만) | eks.* (11), ecr.* (8), cost.idle-compute-high, cost.request-waste, cost.on-demand-in-spot-pool, cost.unused-eip, cost.idle-load-balancer, cost.idle-node, controlplane.scheduler-unschedulable, controlplane.webhook-call-failures, controlplane.controller-error-repeat, controlplane.apiserver-slow-traces, controlplane.authenticator-failures, controlplane.etcd-slow, node.* (26, full mode) | daily, full(ECR·컨트롤플레인 로그·노드·가격과 비용 데이터는 full에서만) | Homebrew `awscli` → 실패하면 고정 버전 2.39.3을 awscli.amazonaws.com에서 받아 sha256 + OpenPGP 서명 확인 뒤 `.tools/bin/`, linux만 | EKS·ECR·비용 항목은 수집되지 않고, 컨트롤플레인 로그 항목과 노드 항목은 리포트에 그렇게 적힙니다 |
| helm | Helm 릴리스 상태와 나이(Helm이 Secret에 두는 릴리스 기록을 읽음) | hygiene.helm-release-not-deployed, hygiene.helm-release-stale | full | Homebrew `helm` → 실패하면 고정 버전 v4.3.1을 get.helm.sh에서 받아 sha256 확인 뒤 `.tools/bin/` | 그 항목은 '도구 없음'으로 적힙니다 |
| krr | 리소스 requests 추천(Robusta KRR, Prometheus 기반) | resources.krr-recommendation | full | `.tools/krr-venv/` 전용 Python virtualenv, `deploy/krr-requirements.txt`(파일마다 sha256) → 실패하면 Homebrew `robusta-dev/krr/krr` (서드파티 tap) | 그 항목은 '도구 없음'으로 적힙니다 |
| polaris | 매니페스트 정적 점검과 가벼운 보안 점검 | hygiene.polaris-reliability-danger, security.polaris-security-danger | full | 고정 버전 v10.2.6을 FairwindsOps/polaris에서 받아 sha256 확인 뒤 `.tools/bin/` → 실패하면 Homebrew `FairwindsOps/tap/polaris` (서드파티 tap) | 그 항목은 '도구 없음'으로 적힙니다 |
| pluto | 지원이 끝난 API 탐지 | hygiene.deprecated-api | full | 고정 버전 v5.24.5을 FairwindsOps/pluto에서 받아 sha256 확인 뒤 `.tools/bin/` → 실패하면 Homebrew `FairwindsOps/tap/pluto` (서드파티 tap) | 그 항목은 입력을 읽지 못해 건너뜁니다(통과로 세지 않음) |
| kubent | 지원이 끝난 API 탐지(Pluto 보완) | hygiene.deprecated-api | full | Homebrew `kubent` → 실패하면 고정 버전 0.7.3을 doitintl/kube-no-trouble에서 받아 sha256 확인 뒤 `.tools/bin/` | 그 항목은 입력을 읽지 못해 건너뜁니다(통과로 세지 않음) |
| ssh | 작은 k3s 클러스터의 노드 접근(k3s 프로필) | node.* (26, full mode) | full | kubegap이 설치하지 않습니다. macOS와 대부분의 Linux에 기본으로 있고, 슬림 컨테이너 이미지에는 없을 수 있습니다(배포판 패키지 openssh-client) | 노드 항목은 '노드 접근 없음'으로 적힙니다 |
<!-- tools-table:end -->

설치는 이렇게 합니다.

- Homebrew가 있으면 Homebrew로 설치합니다.
- Homebrew가 없으면 `lib/tools.py`에 고정한 버전의 릴리스 바이너리를 내려받습니다. 같은 파일에 고정한 sha256과 비교해서 값이 맞을 때만 kubegap 폴더 안의 `.tools/bin/`에 넣습니다.
- polaris와 pluto는 서드파티 tap에서 받기 때문에 고정 버전 다운로드를 먼저 시도합니다.
- krr는 전용 Python virtualenv에 `deploy/krr-requirements.txt`로 설치합니다. 이 파일은 krr가 쓰는 패키지 전부를 파일마다 sha256으로 고정하고 있어서 `pip install --require-hashes`로 값이 맞는 것만 들어갑니다. 서드파티 tap의 formula보다 이 virtualenv를 먼저 씁니다.
- Linux에서 aws CLI zip은 `gpg`가 있으면 AWS CLI Team의 OpenPGP 서명으로도 확인합니다. 키는 `deploy/aws-cli-public-key.asc`에 있습니다. gpg가 없으면 sha256 고정값만으로 판단하고, 설치 결과에 그렇게 적습니다.

설치하는 동안에는 배포처에 최신 버전을 묻지 않습니다. 최신 버전을 확인하려면 `scripts/kubegap setup --check-tool-updates`를 실행하세요. 다음에 고정할 버전 정보를 출력합니다.

## 설정 파일

`~/.kubegap/config.yaml`은 없어도 됩니다. 없으면 현재 kube 컨텍스트를 쓰고 나머지는 kubegap이 찾습니다. 모든 키와 설명은 [`config.example.yaml`](../../config.example.yaml)에 있습니다.

자주 쓰는 키는 파일을 열지 않고 바꿀 수 있습니다.

```bash
scripts/kubegap config set language ko --dry-run     # 바뀔 줄만 출력하고 아무것도 쓰지 않습니다
scripts/kubegap config set language ko
scripts/kubegap config set ssh.hosts.node-1 100.64.0.11
scripts/kubegap config set prometheus_url http://prometheus.example.internal:9090
```

`config set`은 주석, 파일의 순서, 줄바꿈 형식을 그대로 둡니다. 파일이 링크이면 링크가 가리키는 파일에 씁니다. 새로 만드는 파일은 나만 읽을 수 있게 만들고, 형식이 맞지 않는 값은 거부합니다.

이 명령으로 쓸 수 있는 키는 `language`, `mode`, `node_access`, `install_tools`, `ssm_document`, `confirm_context`, 모니터링 도구 주소 네 개인 `prometheus_url`, `alertmanager_url`, `loki_url`, `grafana_url`, 그리고 `ssh.user`, `ssh.key`, `ssh.port`, `ssh.accept_new_hosts`, `ssh.hosts.<node>`입니다.

`grafana_api_token`은 일부러 거부합니다. 에이전트가 실행하는 명령줄에 토큰을 넣으면 그 토큰은 이미 내 컴퓨터를 떠난 것이기 때문입니다. 이 한 줄은 직접 편집기로 넣고, 파일을 `chmod 600`으로 바꾸세요.

아래 키를 설정하면 첫 실행 질문에 답이 정해져서 다시 묻지 않습니다.

| 키 | 효과 |
|---|---|
| `language: en` 또는 `ko` | 리포트 언어를 묻지 않습니다 |
| `context: <name>`과 `confirm_context: false` | 어느 클러스터를 점검할지 묻지 않습니다 |
| `install_tools: always` 또는 `never` | 묻지 않고 도구를 설치하거나, 묻지 않고 설치 없이 넘어갑니다 |
| `ssm_document: always` 또는 `never` | 묻지 않고 SSM 문서를 올리거나, 묻지 않고 올리지 않습니다 |
| `node_access: none` | 어떤 노드에도 접속하지 않고 노드 질문도 하지 않습니다 |
| `prometheus_url`, `alertmanager_url`, `loki_url`, `grafana_url` | 그 도구를 적어 둔 주소에서 읽습니다 |
| `grafana_api_token` | Grafana 목록을 읽습니다 |

**토큰 없이 읽는 것.** Grafana 차트의 사이드카는 `grafana_dashboard`, `grafana_datasource` 라벨이 붙은 ConfigMap에서 대시보드와 데이터소스를 읽어 들입니다. kube-prometheus-stack의 대시보드가 그렇게 들어 있습니다. kubegap은 이 ConfigMap을 스냅샷에 남기고(대시보드 JSON은 그대로, 데이터소스 파일은 항목마다 name, type, url, isDefault만. 비밀번호나 헤더 값은 남기지 않습니다) 두 목록과 "알림 메트릭이 어느 대시보드에도 없는지" 비교를 거기서 만듭니다. Grafana 자체 메트릭 `grafana_stat_totals_dashboard`를 같은 포트포워드의 `/metrics`에서(로그인 없이), 안 되면 Grafana를 긁는 Prometheus에서 읽어 대시보드 전체 개수를 알고, 그 수가 ConfigMap보다 많으면 그만큼은 Grafana 화면에서 만든 것이라 첫 실행 질문이 그 숫자와 함께 토큰을 묻습니다. kubegap은 Grafana 관리자 비밀번호를 읽지 않습니다.

설정 파일에는 다음 키도 넣을 수 있습니다.

| 키 | 쓰임 |
|---|---|
| `mode: full` | full 점검을 기본값으로 합니다 |
| `profile`, `namespace_profiles` | kubegap이 클러스터나 네임스페이스에 적용하는 기준을 바꿉니다 |
| `suppress`, `overrides` | 점검 항목을 끄거나 기준값을 바꿉니다 |
| `retention`, `snapshots_root` | 모은 데이터를 얼마나 남길지, 어디에 둘지 정합니다 |
| `keep_component_logs` | 컴포넌트 파드 로그의 원본을 남깁니다. 어떤 뜻인지는 [DATA.md](DATA.md#읽는-것)에 있습니다 |
| `apiserver_job` | apiserver를 수집하는 job 이름을 지정합니다 |

## 모은 데이터

점검할 때마다 `~/.kubegap/snapshots/<context>/<timestamp>/` 폴더가 하나 생깁니다. 이 폴더를 스냅샷이라고 부릅니다. 스냅샷에는 모은 파일과 리포트 파일 두 개가 들어 있고, kubegap은 같은 모드의 지난 점검과 이 데이터를 비교합니다. 폴더와 파일은 내 사용자만 읽을 수 있게 만듭니다. full 스냅샷 하나는 40 MB쯤 됩니다.

```bash
scripts/kubegap prune --context <name> --keep-daily 14 --keep-full 4 --dry-run
```

`prune`은 오래된 스냅샷을 묻지 않고 지웁니다. 먼저 `--dry-run`으로 지워질 목록을 확인하세요. 설정 파일에 `retention`이 있으면 옵션 없이 `prune`만 실행해도 폴더가 지워집니다. 가장 최근의 daily 스냅샷과 full 스냅샷은 항상 남습니다.

## 가장 좁은 권한으로 돌리기

보안 승인을 받기 전에 처음 돌려 볼 때나, 권한마다 근거를 대야 하는 클러스터에서는 이렇게 설정하세요.

```yaml
# ~/.kubegap/config.yaml
mode: daily          # 노드 스크립트, CloudWatch 로그, 비용 데이터, 외부 도구를 쓰지 않습니다
node_access: none    # SSM send-command, SSH, DaemonSet exec를 쓰지 않습니다
install_tools: never # 이 컴퓨터에 아무것도 설치하지 않습니다
# grafana_api_token 없음: Grafana 데이터소스와 대시보드 목록을 읽지 않습니다
```

kubeconfig에는 전용 사용자를 만들어 kubegap에 들어 있는 ClusterRole [`deploy/permissions/clusterrole.yaml`](../../deploy/permissions/clusterrole.yaml)에 묶으세요. 이 역할은 `get`과 `list`만 허용하고 Secret은 제외합니다.

EKS에서는 `ssm:SendCommand` 구문 두 개를 뺀 IAM 정책을 붙이세요. 아래 명령을 실행하면 계정과 클러스터가 채워진 정책이 출력됩니다.

```bash
scripts/kubegap iam-policy --context <name> --without-node-access   # 정책을 출력만 하고 AWS에는 아무것도 보내지 않습니다
scripts/kubegap iam-policy --context <name>                         # 노드 읽기까지 포함한 전체 정책입니다
```

모니터링 도구 네 개에 URL로 닿을 수 있다면 `prometheus_url`, `alertmanager_url`, `loki_url`, `grafana_url`을 모두 설정하고 `pods/portforward` 규칙도 빼세요.

클러스터 접근 권한만 있고 IAM 권한이 하나도 없을 때 EKS 점검이 모드별로 무엇을 보는지 실측한 결과는 [`docs/ko/PERMISSIONS.md`의 "IAM 권한이 하나도 없을 때"](PERMISSIONS.md#iam-권한이-하나도-없을-때-22)에 있습니다.

이렇게 돌리면 아래 항목은 볼 수 없습니다. 리포트에는 수집하지 못했거나 건너뛰었다고 적고, 통과로 세지 않습니다.

- 노드 스크립트와 kubelet 설정을 읽는 `node.*` 점검 항목 26개. Prometheus의 노드 메트릭을 읽는 10개는 그대로 돌아갑니다.
- Helm 점검 항목 2개: `hygiene.helm-release-not-deployed`, `hygiene.helm-release-stale`
- EKS의 컨트롤플레인 로그 점검 항목 6개: `controlplane.scheduler-unschedulable`, `webhook-call-failures`, `controller-error-repeat`, `apiserver-slow-traces`, `authenticator-failures`, `etcd-slow`
- 비용 데이터, ECR, 서비스 쿼터, EBS 메트릭을 읽는 점검 항목
- krr, polaris, pluto, kubent의 결과
- Prometheus가 수집하지 않는 컴포넌트의 `/metrics`를 노드에서 읽는 것. API 서버 프록시까지 막혀 있으면 그 컴포넌트의 `*.metrics-unreadable` 점검 항목이 warn을 냅니다.

Grafana 데이터소스와 대시보드 목록은 "no auth"로 표시됩니다. `grafana.*` 점검 항목은 Grafana 자체 메트릭으로 판정하므로 그대로 돌아갑니다. 권한을 하나씩 뺄 때 무엇이 빠지는지는 [PERMISSIONS.md](PERMISSIONS.md)에 있습니다.
