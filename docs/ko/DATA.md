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
- 토큰, 계정 ID, 사설 IP는 리포트에서 마스킹합니다. 스냅샷에서는 마스킹하지 않습니다.

리포트를 모델이 쓰기 때문에 데이터를 내 컴퓨터 안에만 두는 모드는 없습니다. 이것을 받아들일 수 없는 클러스터에는 kubegap을 돌리지 마세요.

## Grafana 토큰이 가는 곳

kubegap은 Prometheus, Alertmanager, Loki, Grafana에 요청할 때 HTTP 리다이렉트를 따라가지 않습니다. 그래서 Grafana 토큰은 `config.yaml`에 적힌 주소나 포트포워드로만 갑니다. 이 컴퓨터 밖의 평문 `http://` 주소로 토큰을 보내게 되면 수집할 때 경고합니다.

## 클러스터에서 온 글은 데이터입니다

로그 줄, 이벤트 메시지, 어노테이션, 대시보드 글처럼 스냅샷의 모든 문자열은 클러스터에서 왔습니다. 클러스터에 쓰기 권한이 있는 사람이면 누구든 이 글을 만들어 넣을 수 있습니다. 그래서 에이전트가 따르는 절차는 이런 글을 문제의 근거로만 다루고, 지시로 따르지 않습니다. 이 규칙은 `SKILL.md` 9절에 있습니다.
