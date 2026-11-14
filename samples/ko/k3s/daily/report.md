# default — daily 점검, 2026-11-15 01:20

지금 깨져 있는 것 0개 · 지난 점검 이후 일어난 일 2건 · 지금 가장 중요한 것 3개

지금 깨져 있는 것: 없음

지난 점검 이후 일어난 일: Alertmanager의 Slack 알림 일부가 전달되지 않음 · tempo가 OOM으로 끝나고 여러 번 재시작함

지금 가장 중요한 것: ① DB 백업이 클러스터 밖으로 나가는지 확인되지 않음 ② Prometheus 데이터가 emptyDir에 있고 WAL 손상이 기록됨 ③ Kubernetes `1.33` 지원이 끝남

운영 규모: 소형

daily 점검이 볼 수 없는 심각한 문제가 17가지 있습니다. 목록은 맨 아래에 있고, 확인하려면 `/kubegap full`을 돌립니다.

## 클러스터 한눈에

| 항목 | 값 |
|---|---|
| 노드 | 2대 중 Ready 2대 |
| 파드 | 실행 106, 대기 0, 실패 3 |
| 네임스페이스 | 28개, 프로덕션 8개 |
| 컴포넌트 | 26개 |
| 메트릭·로그 저장소 | prometheus 3.7.3 / Loki 없음 |
| Kubernetes | v1.33.5+k3s1 (k3s) |

## 지난 점검 이후 일어난 일

이번이 이 클러스터의 첫 daily 점검이라 비교할 이전 점검이 없습니다. 수집한 기간 안에 일어난 일을 적었습니다.

### Alertmanager의 Slack 알림 일부가 전달되지 않음

지난 24시간 동안 Alertmanager가 `slack` integration으로 보낸 알림 60건 가운데 8건이 실패했고 52건은 전달됐습니다. Alertmanager는 Prometheus가 울린 알림을 채널로 보내는 구성 요소입니다. 실패한 이유는 이번 점검으로 알 수 없습니다.

### tempo가 OOM으로 끝나고 여러 번 재시작함

`monitoring`의 `tempo`는 지난 7일 동안 파드 하나가 OOM으로 끝나 교체됐고, 그 파드들에서 재시작이 163번 있었습니다. OOM은 컨테이너가 메모리 한도를 넘어 커널이 끝내는 것을 말합니다. 지금 떠 있는 `tempo-0`도 2026-11-14T01:12:30Z에 exit code `255`로 한 번 끝났습니다. `app-ac-prod`의 `app-ac-ai`도 7일 안에 OOM으로 한 번 끝났습니다.

## 지금 가장 중요한 것

### 1. DB 백업이 클러스터 밖으로 나가는지 확인되지 않음

**무슨 일인가.** 클러스터에 백업 전용 도구가 없습니다. 대신 지난 7일 안에 돈 백업 CronJob(`app-f-postgres-backup`, `app-h-mysql-backup`, `etcd-snapshot-backup` 등)과 etcd 스냅샷 5개가 있습니다. 다만 이 백업 파일이 노드 디스크에만 남는지, 클러스터 밖 저장소로 복사되는지는 이번 점검으로 확인할 수 없습니다.

**왜 중요한가.** 백업이 같은 노드에만 있으면 노드 디스크가 망가질 때 `app-f-postgres`, `app-h-mysql` 같은 DB와 백업이 함께 사라집니다. 이 손실은 되돌릴 수 없습니다.

**무엇을 하면 되나.** 각 백업 CronJob이 결과 파일을 S3 호환 저장소처럼 클러스터 밖 한 곳에 복사하도록 두는 편이 좋습니다. 작은 클러스터라면 restic 같은 도구로 DB 덤프와 etcd 스냅샷을 외부 저장소에 올리는 것으로 충분합니다. 한 번은 실제로 복원해 보아 백업이 쓸 수 있는지 확인하기를 권합니다.

더 읽기: [k3s 문서: etcd-snapshot](https://docs.k3s.io/cli/etcd-snapshot)

### 2. Prometheus 데이터가 emptyDir에 있고 WAL 손상이 기록됨

**무슨 일인가.** Prometheus가 22.3GiB의 데이터를 PVC가 아닌 emptyDir에 두고 있습니다. emptyDir는 파드가 다른 노드로 옮겨지거나 지워지면 함께 사라지는 임시 볼륨입니다. 2026-11-14T01:14:32Z에 WAL 손상이 기록됐고, 시작할 때의 손상도 1번 있었습니다. WAL은 Prometheus가 디스크에 쓰기 전에 받아 둔 데이터를 적는 로그입니다.

**왜 중요한가.** Prometheus 파드가 다시 만들어지면 30d 보관하도록 둔 지표가 모두 사라지고, 그동안 알림의 근거도 없어집니다. 장애를 되짚을 기록이 남지 않습니다.

**무엇을 하면 되나.** kube-prometheus-stack의 Prometheus에 `storageSpec`으로 PVC를 붙이는 편이 좋습니다. 이 클러스터의 `local-path` StorageClass로도 충분합니다. 볼륨을 바꾸면 파드가 다시 만들어지고 지금 emptyDir의 데이터는 사라집니다. WAL 손상의 원인은 `/kubegap full`에서 볼 수 있습니다.

더 읽기: [Prometheus 문서: Storage](https://prometheus.io/docs/prometheus/latest/storage/)

### 3. Kubernetes `1.33` 지원이 끝남

**무슨 일인가.** 이 클러스터는 k3s `v1.33.5+k3s1`로 돌고 있습니다. upstream 지원은 2026-06-28에 끝났고 지금 140일이 지났습니다. 지원이 끝난 버전에는 보안 패치가 더 나오지 않습니다.

**왜 중요한가.** 노드 2대 모두 같은 버전이라 새 취약점이 알려져도 클러스터 전체가 패치 없이 남습니다. 오래 미룰수록 한 번에 건너야 할 버전이 늘어 업그레이드가 어려워집니다.

**무엇을 하면 되나.** k3s는 minor 버전을 하나씩 올리는 편이 좋습니다. 작은 클러스터라면 server 노드부터 수동으로 올리고, 각 노드를 drain한 뒤 올리는 방식으로 충분합니다. 올리기 전에 etcd 스냅샷을 클러스터 밖에 하나 받아 두고, 없어진 API를 쓰는 매니페스트가 있는지 먼저 확인하기를 권합니다.

더 읽기: [k3s 문서: 수동 업그레이드](https://docs.k3s.io/upgrades/manual)

## 그 밖에 열려 있는 것

- CPU throttling이 높은 컨테이너 8개
- prune이 켜진 Argo CD 애플리케이션이 Namespace나 CRD를 관리함
- `app-g-minio` 메모리 사용이 한도에 가까움

## 이번 점검이 보지 않은 것

daily 점검은 가볍게 보는 점검입니다. Kubernetes API와 메트릭·로그 저장소만 읽었습니다.

- 애플리케이션이 어떻게 시작되고 설정되는지(command, args, 환경 변수 값, ConfigMap 키)를 남기지 않았습니다. 그래서 데이터베이스에 백업 작업이 있는지, ConfigMap에 비밀 값이 적혀 있는지, JVM 힙이 메모리 제한보다 큰지는 알 수 없습니다.
- 플랫폼 구성 요소의 로그는 알려진 실패 패턴에 맞는 줄이 몇 개인지만 셌고, 로그 문장은 남기지 않았습니다. 그래서 알려진 패턴에 맞지 않는 오류는 이 리포트에 나오지 않습니다.
- 노드에 접속하지 않았습니다. 그래서 노드 디스크가 차는 것, 커널이 메모리가 모자라 프로세스를 끝낸 일, k3s 서버 인증서의 만료, k3s의 etcd 스냅샷, kubelet과 컨테이너 런타임의 오류는 알 수 없습니다.
- kubelet 설정(파드를 내보내는 기준, 예약 자원, maxPods)을 읽지 않았습니다.
- 컨트롤 플레인 로그를 읽지 않았습니다. 그래서 느린 API 요청, 실패하는 어드미션 웹훅, 인증 실패, 느린 etcd는 알 수 없습니다.
- 몇 분씩 걸리는 추가 도구를 돌리지 않았습니다. 그래서 일주일 사용량으로 본 requests·limits 권고와, 다음 Kubernetes 버전에서 없어지는 API 버전 목록이 없습니다.
- Helm 릴리스를 읽지 않았습니다. 그래서 실패했거나 설치 도중에 멈춘 릴리스는 이 리포트에 나오지 않습니다.
- Secret 값은 어느 점검에서도 읽지 않습니다.
- 수집이 자체 제한에 걸려 일부만 읽은 것이 있습니다: `core.component-logs` (argocd: argocd/argocd-application-controller, argocd: argocd/argocd-applicationset-controller, argocd: argocd/argocd-notifications-controller, argocd: argocd/argocd-repo-server, coredns: kube-system/coredns, external-secrets: external-secrets/external-secrets, fluent-bit: logging/fluent-bit, ingress-nginx: ingress-nginx/nginx-ingress-ingress-nginx-controller, istio: istio-system/istiod, metallb: metallb-system/speaker, tempo-jaeger: monitoring/tempo). 여기에서 센 숫자는 실제보다 적을 수 있습니다.

그래서 점검 항목 349개 가운데 62개는 이번에 보지 못했습니다. 노드 안쪽, 비용, 없어질 API 같은 항목이고, 문제로도 통과로도 세지 않았습니다.

특히 아래와 같은 문제는 심각할 수 있는데도 노드 안쪽이나 클라우드 계정, 애플리케이션 설정을 읽어야 보여서 daily 점검으로는 알 수 없습니다. 이 리포트에 없다고 해서 문제가 없다는 뜻이 아닙니다.

- 스케줄러가 파드를 배치하지 못한 기록
- 노드 전체의 메모리가 모자라 커널이 프로세스를 끝낸 일
- 커널이 멈추는 오류
- 디스크 I/O 오류와 파일시스템 오류
- conntrack 테이블이 가득 차 패킷이 버려지는 것
- 컨테이너 런타임 이상
- 노드 시계가 맞지 않는 것
- 다음 Kubernetes 버전에서 없어지는 API를 쓰는 것
- 백업이 원본 데이터베이스와 같은 노드에만 있는 것
- ConfigMap에 적힌 비밀 값
- 노드의 네트워크 커널 설정이 꺼져 있는 것
- etcd 스냅샷이 없거나 오래된 것
- k3s 내부 인증서의 만료
- k3s 데이터스토어(etcd)가 느린 것
- k3s 데이터스토어가 한도에 가까운 것
- local-path 볼륨이 요청한 용량을 넘은 것
- 노드 디스크가 차는 것

이것들을 확인하고, 원인을 원본까지 열어 따지고, 문제마다 원리와 점검 방법과 규모별 해결 방안을 길게 설명하는 것은 `/kubegap full`입니다.

점검 항목 id (`/kubegap explain <id>`):

- Alertmanager의 Slack 알림 일부가 전달되지 않음: `observability.alertmanager-notification-failed.slack`
- tempo가 OOM으로 끝나고 여러 번 재시작함: `resources.oomkilled-repeated.*`
- DB 백업이 클러스터 밖으로 나가는지 확인되지 않음: `resilience.no-backup.cluster`
- Prometheus 데이터가 emptyDir에 있고 WAL 손상이 기록됨: `logs.signatures.prometheus.wal-corrupt`, `prometheus.storage-risk.*`
- Kubernetes `1.33` 지원이 끝남: `platform.k8s-version-eol.cluster`

kubegap 0.2.0, rubric 0.1.94 · 스냅샷 `~/.kubegap/snapshots/<context>/2026-11-15T01-20-18`
