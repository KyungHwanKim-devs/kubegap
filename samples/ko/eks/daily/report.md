# app-u-cluster-eks — daily 점검, 2026-11-15 01:40

지금 깨져 있는 것 1개 · 지난 점검 이후 일어난 일 1건 · 지금 가장 중요한 것 3개

지금 깨져 있는 것: NetworkPolicy가 적용되지 않음

지난 점검 이후 일어난 일: Prometheus가 OOM으로 재시작함

지금 가장 중요한 것: ① 클러스터 백업이 없음 ② 쿠버네티스 `1.32` 지원 종료 ③ Karpenter 버전과 AMI가 클러스터 버전을 따라가지 못함

운영 규모: 중형

daily 점검이 볼 수 없는 심각한 문제가 20가지 있습니다. 목록은 맨 아래에 있고, 확인하려면 `/kubegap full`을 돌립니다.

## 클러스터 한눈에

| 항목 | 값 |
|---|---|
| 노드 | 9대 중 Ready 9대 |
| 파드 | 실행 131, 대기 0, 실패 0 |
| 네임스페이스 | 21개, 프로덕션 8개 |
| 컴포넌트 | 22개 |
| 메트릭·로그 저장소 | prometheus 2.49.1 / loki 2.6.1 |
| Kubernetes | v1.32.13-eks-577a51e (eks) |

## 지금 깨져 있는 것

### NetworkPolicy가 적용되지 않음

`prod-app-t`, `prod-app-x`, `prod-app-r` 세 네임스페이스에 NetworkPolicy가 있지만 지금 아무 트래픽도 막지 않습니다. NetworkPolicy는 파드끼리 주고받을 수 있는 트래픽을 정하는 규칙이고, CNI가 실제로 집행해야 효력이 있습니다. 이 클러스터의 `aws-eks-nodeagent`는 `--enable-network-policy=false`로 떠 있고 PolicyEndpoint도 하나도 없습니다.

## 지난 점검 이후 일어난 일

이번이 이 클러스터의 첫 daily 점검이라 비교할 이전 점검이 없습니다. 수집한 기간 안에 일어난 일을 적었습니다.

### Prometheus가 OOM으로 재시작함

`monitoring`의 `prometheus-kube-prometheus-stack-prometheus-0` 컨테이너가 2026-11-14T14:34:30Z에 메모리 한도 1536Mi를 넘어 OOMKilled로 끝났습니다. OOMKilled는 컨테이너가 메모리 한도를 넘어 커널이 그 컨테이너를 끝낸 것을 말합니다. 지금은 다시 떠 있지만 사용량이 한도의 0.934까지 차 있어 같은 일이 다시 일어날 수 있습니다. 재시작 동안 알림 평가가 멈췄는지는 이번 점검으로 알 수 없습니다. 지금도 계속되고 있습니다.

## 지금 가장 중요한 것

### 1. 클러스터 백업이 없음

**무슨 일인가.** 이 클러스터에는 백업 도구가 설치되어 있지 않습니다. etcd 스냅샷, 최근에 돈 백업용 CronJob, VolumeSnapshot도 하나도 보이지 않습니다. 쿠버네티스 오브젝트와 PersistentVolume의 데이터 어느 쪽도 클러스터 밖에 사본이 없다는 뜻입니다.

**왜 중요한가.** 네임스페이스를 실수로 지우거나 EBS 볼륨이 망가지면 `app-u-cluster`의 서비스 설정과 데이터를 되살릴 방법이 없습니다. `prod-app-z-backend`의 `app-z-neo4j`처럼 데이터를 가진 워크로드가 그대로 잃게 됩니다.

**무엇을 하면 되나.** Velero를 설치해 오브젝트와 볼륨을 Schedule로 함께 백업하고, 백업은 다른 계정이나 리전의 S3에 두기를 권합니다. EBS 볼륨에는 AWS Backup 플랜이나 Data Lifecycle Manager 정책을 더해 스냅샷을 다른 리전으로 복사하는 편이 좋습니다. 백업을 만든 뒤에는 정해 둔 날에 별도 클러스터로 복원해 실제로 되살아나는지 확인합니다.

더 읽기: [GitLab: Postmortem of database outage of January 31](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/)

### 2. 쿠버네티스 `1.32` 지원 종료

**무슨 일인가.** 클러스터가 쿠버네티스 `v1.32.13`으로 돌고 있습니다. 이 마이너 버전은 업스트림 지원이 2026-02-28에 끝났고 지금은 260일이 지났습니다. 지원이 끝난 버전은 보안 패치를 더 받지 못하고, EKS에서는 extended support 요금이 붙습니다.

**왜 중요한가.** `app-u-cluster`에 새 취약점이 나와도 패치가 나오지 않습니다. 또 마이너 버전은 하나씩만 올릴 수 있어서 미룰수록 거쳐야 할 업그레이드가 늘어납니다.

**무엇을 하면 되나.** 업그레이드를 문서로 정한 절차로 만드는 편이 좋습니다. 릴리스 노트와 EKS upgrade insights를 확인하고, Pluto나 kubent로 다음 버전에서 사라지는 API를 찾은 뒤 운영이 아닌 클러스터에서 먼저 올립니다. 그다음 컨트롤 플레인, 애드온, 노드 순서로 올리고, 노드를 바꾸기 전에 PodDisruptionBudget을 갖춰 둡니다. 아래 Karpenter 문제를 먼저 풀어야 노드 교체가 됩니다.

더 읽기: [Amazon EKS best practices: Cluster Upgrades](https://docs.aws.amazon.com/eks/latest/best-practices/cluster-upgrades.html)

### 3. Karpenter 버전과 AMI가 클러스터 버전을 따라가지 못함

**무슨 일인가.** Karpenter는 수요에 맞춰 EC2 노드를 띄우고 내리는 오토스케일러입니다. 설치된 Karpenter `0.37.0`은 쿠버네티스 `1.30`까지만 지원하는데 클러스터는 `1.32`입니다. 또 EC2NodeClass `default`가 Amazon Linux 2 AMI를 쓰고 있는데, AL2 AMI는 쿠버네티스 `1.33`부터 나오지 않습니다.

**왜 중요한가.** 지원 범위 밖에서는 Karpenter가 AMI를 찾지 못해 새 노드가 뜨지 않거나 옛 AMI로만 뜰 수 있습니다. 그러면 트래픽이 늘거나 spot 노드가 회수될 때 `app-u-cluster`의 파드가 자리를 얻지 못하고, 클러스터 업그레이드도 막힙니다.

**무엇을 하면 되나.** Karpenter를 호환성 표에 맞는 릴리스까지 한 마이너씩 올리고, CRD는 별도 차트로 함께 올리기를 권합니다. 그 뒤 EC2NodeClass를 AL2023으로 바꾸고 AMI 버전을 alias로 고정해 Git에 둡니다. 이 변경은 drift로 노드를 차례로 교체하므로, 먼저 NodePool에 업무 시간에는 교체하지 않는 disruption budget을 두는 편이 좋습니다.

더 읽기: [Karpenter: Compatibility](https://karpenter.sh/docs/upgrading/compatibility/)

## 그 밖에 열려 있는 것

- OOM을 잡는 알림 규칙이 없음
- Alertmanager와 Loki의 저장소가 emptyDir임
- `prod-app-z-backend`의 비밀값이 평문 환경 변수로 들어 있음
- `app-ad`가 NET_ADMIN 권한과 호스트 경로를 씀

## 이번 점검이 보지 않은 것

daily 점검은 가볍게 보는 점검입니다. Kubernetes API와 메트릭·로그 저장소만 읽었습니다.

- 애플리케이션이 어떻게 시작되고 설정되는지(command, args, 환경 변수 값, ConfigMap 키)를 남기지 않았습니다. 그래서 데이터베이스에 백업 작업이 있는지, ConfigMap에 비밀 값이 적혀 있는지, JVM 힙이 메모리 제한보다 큰지는 알 수 없습니다.
- 플랫폼 구성 요소의 로그는 알려진 실패 패턴에 맞는 줄이 몇 개인지만 셌고, 로그 문장은 남기지 않았습니다. 그래서 알려진 패턴에 맞지 않는 오류는 이 리포트에 나오지 않습니다.
- 노드에 접속하지 않았습니다. 그래서 노드 디스크가 차는 것, 커널이 메모리가 모자라 프로세스를 끝낸 일, k3s 서버 인증서의 만료, k3s의 etcd 스냅샷, kubelet과 컨테이너 런타임의 오류는 알 수 없습니다.
- kubelet 설정(파드를 내보내는 기준, 예약 자원, maxPods)을 읽지 않았습니다.
- 컨트롤 플레인 로그를 읽지 않았습니다. 그래서 느린 API 요청, 실패하는 어드미션 웹훅, 인증 실패, 느린 etcd는 알 수 없습니다.
- AWS API를 부르지 않았습니다. 그래서 백업이 있는지(AWS Backup, 스냅샷), 서브넷의 주소가 모자란지, 클러스터 엔드포인트나 보안 그룹이 인터넷 전체에 열려 있는지, 로드밸런서의 설정과 오류, 비용은 알 수 없습니다.
- 몇 분씩 걸리는 추가 도구를 돌리지 않았습니다. 그래서 일주일 사용량으로 본 requests·limits 권고와, 다음 Kubernetes 버전에서 없어지는 API 버전 목록이 없습니다.
- Helm 릴리스를 읽지 않았습니다. 그래서 실패했거나 설치 도중에 멈춘 릴리스는 이 리포트에 나오지 않습니다.
- Secret 값은 어느 점검에서도 읽지 않습니다.
- 수집이 자체 제한에 걸려 일부만 읽은 것이 있습니다: `core.component-logs` (argocd: argocd/argocd-application-controller, argocd: argocd/argocd-applicationset-controller, argocd: argocd/argocd-notifications-controller, argocd: argocd/argocd-repo-server, ebs-csi: kube-system/ebs-csi-controller, external-dns: kube-system/external-dns, external-secrets: external-secrets/external-secrets, external-secrets: external-secrets/external-secrets-cert-controller, loki: monitoring/loki-stack). 여기에서 센 숫자는 실제보다 적을 수 있습니다.

그래서 점검 항목 367개 가운데 86개는 이번에 보지 못했습니다. 노드 안쪽, 비용, 없어질 API 같은 항목이고, 문제로도 통과로도 세지 않았습니다.

특히 아래와 같은 문제는 심각할 수 있는데도 노드 안쪽이나 클라우드 계정, 애플리케이션 설정을 읽어야 보여서 daily 점검으로는 알 수 없습니다. 이 리포트에 없다고 해서 문제가 없다는 뜻이 아닙니다.

- 스케줄러가 파드를 배치하지 못한 기록
- API 서버의 웹훅 호출 실패
- 노드 전체의 메모리가 모자라 커널이 프로세스를 끝낸 일
- 커널이 멈추는 오류
- 디스크 I/O 오류와 파일시스템 오류
- conntrack 테이블이 가득 차 패킷이 버려지는 것
- 컨테이너 런타임 이상
- 노드 시계가 맞지 않는 것
- EKS의 Secret 암호화 설정
- 파드가 노드의 IAM 자격 증명에 닿을 수 있는 설정
- 다음 Kubernetes 버전에서 없어지는 API를 쓰는 것
- 로드밸런서 뒤의 비정상 대상
- 백업이 원본 데이터베이스와 같은 노드에만 있는 것
- ConfigMap에 적힌 비밀 값
- 클러스터 엔드포인트가 인터넷 전체에 열려 있는 것
- EBS 스냅샷과 백업 정책이 없는 것
- ACM 인증서의 만료
- AWS 서비스 한도에 가까운 것
- 보안 그룹이 인터넷 전체에 열려 있는 것
- 파드에 줄 IP가 모자란 것

이것들을 확인하고, 원인을 원본까지 열어 따지고, 문제마다 원리와 점검 방법과 규모별 해결 방안을 길게 설명하는 것은 `/kubegap full`입니다.

점검 항목 id (`/kubegap explain <id>`):

- NetworkPolicy가 적용되지 않음: `security.networkpolicy-not-enforced.cluster`
- Prometheus가 OOM으로 재시작함: `resources.oomkilled.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus`, `prometheus.memory-pressure.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus`, `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus`, `resources.oomkilled-repeated.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus`
- 클러스터 백업이 없음: `resilience.no-backup.cluster`
- 쿠버네티스 `1.32` 지원 종료: `platform.k8s-version-eol.cluster`
- Karpenter 버전과 AMI가 클러스터 버전을 따라가지 못함: `platform.karpenter-version-compat.cluster`, `karpenter.ec2nodeclass-al2.cluster`

kubegap 0.2.0, rubric 0.1.94 · 스냅샷 `~/.kubegap/snapshots/<context>/2026-11-15T01-40-53`
