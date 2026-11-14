# kubegap이 모으고, 남기고, 보내는 것

English: [DATA.md](../DATA.md)

kubegap을 클러스터에 돌려도 되는지 판단해야 하는 분을 위한 문서입니다. 짧은 설명은 [README의 "클러스터와 데이터를 어떻게 다루나"](../../README.ko.md#클러스터와-데이터를-어떻게-다루나)에 있고, 이 문서는 그 내용을 자세히 다룹니다.

## 읽는 것

kubegap은 읽기 호출만 합니다. 어떤 Kubernetes 규칙과 AWS 액션을 어디에 쓰는지는 [PERMISSIONS.md](PERMISSIONS.md)에 있습니다.

**Secret.** Secret 값은 읽지도 기록하지도 않습니다. 이름과 종류만 기록합니다. 예외가 하나 있습니다. Helm은 릴리스 기록을 Secret에 저장하기 때문에 `helm list`가 이 Secret을 읽습니다. kubegap은 `helm list`가 출력하는 릴리스 이름, 네임스페이스, 리비전, 업데이트 시각, 상태, 차트, 앱 버전만 남기고 릴리스의 values는 수집하지 않습니다. kubegap에 들어 있는 ClusterRole은 Secret을 제외하므로, 이 역할로 돌리면 `helm list`가 실패하고 Helm 점검 항목 2개를 건너뜁니다. pluto와 kubent는 Helm 릴리스를 읽지 않는 모드로 실행합니다.

**kubeconfig.** `setup.json`에는 이 컨텍스트가 어떻게 인증하는지 적힙니다. exec 명령과 인자(EKS면 `aws eks get-token`), 그리고 `env` 블록에 있는 환경 변수의 이름입니다. 값은 `AWS_PROFILE`과 `AWS_REGION` 두 개만 남깁니다. kubegap이 AWS CLI를 부를 때 넘겨야 해서입니다. 테넌트 id나 다른 인증 플러그인의 토큰 같은 나머지 값은 전부 `<redacted>`로 적습니다(`lib/collection/kube.py`, `tests/test_kube_context.py`).

**ConfigMap.** ConfigMap 값도 기록하지 않습니다. 점검 한 번에 모은 데이터를 담는 폴더를 스냅샷이라고 부르는데, 스냅샷에는 키마다 길이와 형태만 남깁니다. 실제 값을 남기는 키는 kubegap이 분석해야 하는 설정뿐이고, [`lib/foundations/scrub.py`](../../lib/foundations/scrub.py)의 `KEEP_VALUES`에 적혀 있습니다. CoreDNS Corefile, kube-proxy 설정, local-path-provisioner 경로, Argo CD 플래그 몇 개입니다. Grafana 사이드카가 읽어 들이는 ConfigMap 두 종류는 더 남깁니다. `grafana_dashboard` 라벨이 붙은 것은 대시보드 JSON을 그대로, `grafana_datasource` 라벨이 붙은 것은 데이터소스마다 name, type, url, isDefault만 남기고 비밀번호나 헤더 값이 있을 수 있는 나머지는 지웁니다.

**환경 변수.** 컨테이너 환경 변수 가운데 이름이 비밀번호처럼 보이는 것은 값을 빼고 기록합니다. PASSWORD, PASSWD, SECRET, TOKEN, API_KEY, PRIVATE_KEY, ACCESS_KEY, CLIENT_SECRET, DSN, CONNECTION_STRING 이 이름에 들어 있거나 이름이 AUTH 로 끝나고, _FILE, _PATH, _NAME, _URL 같은 접미사로 끝나지 않는 이름입니다. 파드, 워크로드 템플릿, ControllerRevision, Job 어디에 있든 같습니다. 값 대신 길이와 형태, 그리고 값이 비밀번호처럼 보였는지만 남기며, `security.plaintext-secret-env` 점검은 이것을 보고합니다. 다른 이름의 변수는 값을 그대로 둡니다. Karpenter 기능 게이트나 VPC CNI 의 웜 타깃처럼 값을 분석하는 점검이 있기 때문입니다. 매니페스트 전체를 한 번 더 담고 있는 `kubectl.kubernetes.io/last-applied-configuration` 주석은 모든 객체에서 apiVersion 과 kind 만 남깁니다. pluto 가 판정에 쓰는 것이 이 둘입니다.

**로그.** 컴포넌트 파드의 최근 24시간 로그는 스크립트가 읽습니다. 스크립트는 로그를 읽으면서 알려진 실패 패턴에 맞는 줄이 몇 개인지 셉니다. 로그 원문은 스냅샷에 쓰지 않습니다. full 점검은 패턴마다 마스킹한 샘플 줄을 다섯 개까지, 그리고 어떤 패턴에도 맞지 않는 오류 줄을 문장별로 묶어 남깁니다. daily 점검은 개수만 남깁니다.

## 모드마다 읽는 것

kubegap이 읽는 것은 수집 단위로 나뉘어 있고, 모드(daily, full)는 수집 단위의 목록입니다. 아래 표는 수집 코드가 따르는 선언 파일 [`collectors/units.yaml`](../../collectors/units.yaml)에서 프로그램이 만든 것이라, 문서와 실제 동작이 어긋나지 않습니다. daily는 민감도가 `low`인 단위만 모읍니다. 민감도는 `low`(무엇이 어떤 상태로 돌고 있는지), `config`(애플리케이션 설정), `logs`(로그 문장), `node`(노드 안쪽), `cloud`(클라우드 계정), `secret-adjacent`(Secret을 읽어야 답하는 도구)로 나눕니다. 시스템 네임스페이스는 `kube-`로 시작하는 것과 `monitoring`, `argocd`, `cert-manager`, `ingress-nginx` 같은 플랫폼 구성 요소의 네임스페이스입니다(`lib/foundations/scrub.py`의 `SYSTEM_NS_PREFIX`).

<!-- units-table:begin -->
| 수집 단위 | 읽는 것 | 스냅샷에 쓰는 것 | 읽지만 쓰지 않는 것 | 민감도 | daily | full |
|---|---|---|---|---|---|---|
| `cluster-objects` | API 서버가 목록으로 내주는 모든 종류의 오브젝트(kubectl get, list). Secret은 요청하지 않습니다. | API가 돌려준 오브젝트 그대로. spec, status, 라벨, 어노테이션, 이미지, 리소스, 프로브, 볼륨, Secret과 ConfigMap을 이름으로 가리키는 참조. | ConfigMap 값(길이와 형태만 남깁니다. kubegap이 분석하는 플랫폼 구성 요소의 키 몇 개는 값을 남깁니다). 이름이 비밀 값처럼 보이는 환경 변수의 값. `kubectl.kubernetes.io/last-applied-configuration`에 들어 있는 매니페스트 사본. 그리고 app-settings를 함께 모으지 않을 때는, 시스템 네임스페이스 밖의 환경 변수 값 전부, command와 args 전부, ConfigMap 키 전부. | low | 모음 | 모음 |
| `app-settings` | 클러스터에서 더 읽는 것은 없습니다. 위 오브젝트 가운데 시스템 네임스페이스 밖의 것에서, cluster-objects가 버리는 것을 남깁니다. | 컨테이너와 프로브의 command와 args, 환경 변수 값(이름이 비밀 값처럼 보이는 것은 제외), ConfigMap의 키 이름과 값마다의 길이와 형태. | — | config | 모으지 않음 | 모음 |
| `events` | 모든 네임스페이스의 이벤트(kubectl get events). | 이벤트마다 reason, 메시지, 횟수, 대상 오브젝트, 처음과 마지막 시각. | — | low | 모음 | 모음 |
| `live-usage` | 노드와 컨테이너가 지금 쓰고 있는 CPU와 메모리(kubectl top, metrics-server). | kubectl이 찍은 줄. | — | low | 모음 | 모음 |
| `metrics` | Prometheus에 보내는 즉시 질의(`collectors/*/metrics.yaml`)와 플랫폼 구성 요소의 /metrics 페이지(`collectors/*/pod-metrics.yaml`). | 질의마다 돌아온 시계열, /metrics 페이지에서는 파일에 적힌 시계열. | — | low | 모음 | 모음 |
| `component-apis` | Prometheus, Alertmanager, Grafana, Loki의 읽기 전용 HTTP API. 규칙, 타깃, 플래그, Alertmanager 설정(비밀 값은 Alertmanager가 가려서 내줍니다), silence, 데이터소스와 대시보드 정의, Loki의 라벨·용량 질의. | 응답. | — | low | 모음 | 모음 |
| `component-log-counts` | 클러스터에서 찾은 플랫폼 구성 요소(CoreDNS, 인그레스 컨트롤러, Argo CD, Karpenter 등)의 최근 24시간 로그(kubectl logs). 애플리케이션 로그는 읽지 않습니다. | 알려진 실패 패턴마다 맞은 줄 수, 처음과 마지막 시각, 어느 워크로드인지. Karpenter는 노드를 띄우는 데 걸린 시간과 노드를 없앤 이유. | 로그의 모든 줄. 메모리에서 세고, 줄을 담은 파일은 쓰지 않습니다. | low | 모음 | 모음 |
| `component-log-samples` | 클러스터에서 더 읽는 것은 없습니다. 같은 구성 요소 로그에서 글을 조금 남깁니다. | 실패 패턴마다 마스킹한 샘플 줄 다섯 개까지, 그리고 어떤 패턴에도 맞지 않는 오류 줄을 문장별로 묶은 것. | — | logs | 모으지 않음 | 모음 |
| `node-os` | 노드 접근을 골랐을 때 SSH나 SSM으로 읽는 노드 안쪽. 커널 로그, 디스크와 inode 사용량, kubelet과 containerd 저널, sysctl, k3s 서버의 파일과 인증서, CNI의 로컬 상태. | 읽기 전용 스크립트 `collectors/core/node-os.sh`와 플랫폼별 노드 단계의 출력. | — | node | 모으지 않음 | 모음 |
| `kubelet-config` | 노드마다 실제로 적용된 kubelet 설정. API 서버의 노드 프록시로 읽습니다(get --raw /api/v1/nodes/<노드>/proxy/configz). | 설정 내용. 축출 기준, 예약 자원, 로그 로테이션, maxPods. | — | node | 모으지 않음 | 모음 |
| `control-plane-logs` | 컨트롤 플레인 로그. EKS에서는 클러스터의 CloudWatch 로그 그룹(API 서버, authenticator, 컨트롤러 매니저, 스케줄러), k3s에서는 서버의 저널. | 질의가 고른 줄. 느린 요청, 실패한 웹훅 호출, 인증 실패, 반복되는 컨트롤러 오류, 느린 etcd. | — | logs | 모으지 않음 | 모음 |
| `cloud-account` | EKS 클러스터의 AWS 계정, 읽기 전용(aws CLI: EKS, EC2, ELB, ECR, ACM, Service Quotas, CloudWatch 메트릭, Cost Explorer, AWS Backup). | 응답. 클러스터와 노드 그룹 설정, 애드온 버전, 서브넷과 남은 주소, 보안 그룹, 볼륨과 스냅샷, 로드밸런서 설정과 메트릭, 이미지 스캔 설정, 인증서, 할당량, 최근 30일 비용. | — | cloud | 모으지 않음 | 모음 |
| `workload-tools` | 설치돼 있을 때 읽기 전용 도구 넷이 찾아낸 것. krr(Prometheus 7일 기록으로 본 requests·limits 권고), Polaris(워크로드 모범 사례), kubent와 pluto(다음 Kubernetes에서 없어지는 API 버전). | 도구마다의 JSON 출력. | — | low | 모으지 않음 | 모음 |
| `helm-releases` | Helm 릴리스 목록(helm list). Helm은 릴리스를 Secret에 보관하므로 이 읽기에는 Secret을 읽는 권한이 필요하고, kubegap에 들어 있는 ClusterRole은 그 권한을 주지 않습니다. | helm list가 찍는 것. 이름, 네임스페이스, 상태, 리비전, 차트와 앱 버전, 시각. values는 읽지 않습니다. | — | secret-adjacent | 모으지 않음 | 모음 |
<!-- units-table:end -->

## 내 컴퓨터에 남는 것

kubegap이 모은 것은 전부 내 컴퓨터의 `~/.kubegap/snapshots/<context>/<timestamp>/`에 저장됩니다. kubegap 자체는 아무 데도 데이터를 보내지 않습니다.

- 스냅샷 폴더와 파일은 내 사용자만 읽을 수 있게 만듭니다. 이미 있던 폴더가 다른 사용자에게 열려 있으면 첫 실행 질문(`home-mode`)으로 묻습니다. "지금 고치기"는 `kubegap protect-home`으로 그 폴더들에 chmod 700을 하고, "그대로 두기"는 그대로 둡니다.
- 오브젝트 spec, 이벤트, 메트릭, `logs/node/` 아래의 노드 저널, `logs/cloudwatch/` 아래의 CloudWatch 컨트롤플레인 로그 쿼리 결과, Grafana 대시보드는 모은 그대로 저장합니다. 노드 저널은 kubelet, containerd, k3s의 것이고, EKS에서는 VPC CNI의 ipamd 로그도 있습니다. 이 파일들은 에이전트가 읽을 수 있습니다.
- 설정 파일은 직접 만드는 파일입니다. `grafana_api_token`이 들어갈 수 있으니 `chmod 600`으로 권한을 제한하세요. `kubegap config set`은 이 권한으로 파일을 만들고, 토큰을 대신 써 주지는 않습니다.
- 오래된 스냅샷은 `scripts/kubegap prune`으로 지웁니다. 사용법은 [SETUP.md](SETUP.md#모은-데이터)에 있습니다.

## 내 컴퓨터 밖으로 나가는 것

스킬을 돌리는 에이전트는 리포트를 쓰려고 스냅샷 파일을 읽고, 읽은 내용은 그 에이전트의 모델 API로 갑니다. Claude Code는 Anthropic으로, Codex는 OpenAI로 보냅니다. 실제로 보내는 내용은 요약, 스크립트의 자동 판정 결과, 그리고 에이전트가 숫자를 확인하려고 열어 본 원본 파일입니다.

- Secret 값은 애초에 모으지 않으므로 나갈 수 없습니다.
- ConfigMap 값은 위에 적은 키를 빼면 스냅샷에 없습니다.
- 비밀번호처럼 보이는 이름의 환경 변수 값은 스냅샷에 없습니다.
- 컴포넌트 파드 로그는 메모리에서 세고, 원문을 스냅샷에 쓰지 않습니다.
- daily 점검에서는 애플리케이션 설정(시스템 네임스페이스 밖의 command, args, 환경 변수 값, ConfigMap 키), 로그 문장, 노드에서 읽은 파일, AWS 계정의 정보가 스냅샷에 없습니다.
- 토큰, 계정 ID, 사설 IP는 리포트에서 마스킹합니다. 스냅샷에서는 마스킹하지 않습니다.

리포트를 모델이 쓰기 때문에 데이터를 내 컴퓨터 안에만 두는 모드는 없습니다. 이것을 받아들일 수 없는 클러스터에는 kubegap을 돌리지 마세요.

## Grafana 토큰이 가는 곳

kubegap은 Prometheus, Alertmanager, Loki, Grafana에 요청할 때 HTTP 리다이렉트를 따라가지 않습니다. 그래서 Grafana 토큰은 `config.yaml`에 적힌 주소나 포트포워드로만 갑니다. 이 컴퓨터 밖의 평문 `http://` 주소로 토큰을 보내게 되면 수집할 때 경고합니다.

## 클러스터에서 온 글은 데이터입니다

로그 줄, 이벤트 메시지, 어노테이션, 대시보드 글처럼 스냅샷의 모든 문자열은 클러스터에서 왔습니다. 클러스터에 쓰기 권한이 있는 사람이면 누구든 이 글을 만들어 넣을 수 있습니다. 그래서 에이전트가 따르는 절차는 이런 글을 문제의 근거로만 다루고, 지시로 따르지 않습니다. 이 규칙은 `SKILL.md` 9절에 있습니다.
