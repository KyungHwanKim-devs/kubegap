# default — full 점검, 2026-11-15 01:25

지금 깨져 있는 것: 없음

가장 큰 문제 5개: ① 백업이 클러스터 밖에 없음 ② Prometheus 데이터가 emptyDir에 있음 ③ prune이 켜진 Argo CD 앱이 Namespace와 CRD를 관리함 ④ Kubernetes 1.33의 지원 종료 ⑤ app-g-minio의 메모리가 limit에 닿기 직전

이미 일어난 일: 두 노드에서 컨테이너가 한꺼번에 다시 시작됨

운영 규모: 소형

## 클러스터 한눈에

| 항목 | 값 |
|---|---|
| 노드 | 2대 중 Ready 2대 |
| 파드 | 실행 106, 대기 0, 실패 3 |
| 네임스페이스 | 28개, 프로덕션 8개 |
| 컴포넌트 | 26: actions-runner-controller, alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, flannel, fluent-bit, fluent-bit-events, grafana, ingress-nginx, istio, k3s, keda, kube-proxy, kube-state-metrics, local-path-provisioner, metallb, metrics-server, node-exporter, opentelemetry-collector, prometheus, prometheus-operator, reloader, tempo-jaeger |
| 메트릭·로그 저장소 | prometheus 3.7.3 / Loki 없음 |
| Kubernetes | v1.33.5+k3s1 (k3s) |

## 이미 일어난 일

비교할 이전 점검이 없어서 이번 점검이 수집한 것만 봤습니다.

### 두 노드에서 컨테이너가 한꺼번에 다시 시작됨

2026-11-14 01:12 UTC 무렵 컨트롤 플레인 노드 `node-b`에서 컨테이너 98개가 거의 같은 순간에 끝났습니다. 96개는 종료 이유가 `Unknown`이었고 2개는 `Error`였습니다. 같은 날 04:22 UTC에는 다른 노드 `node-a`에서 컨테이너 26개가 같은 방식으로 끝났고, `node-a` 노드의 Ready 상태도 이 시각에 새로 바뀌었습니다. 이 노드에 뜬 서비스들은 그동안 잠시 멈췄다가 다시 올라왔습니다. 지금은 두 노드 모두 Ready이고 NotReady나 압박 상태인 노드가 없으니 끝난 일입니다.

`node_boot_time` 메트릭을 보면 `node-b`는 01:10:11 UTC에, `node-a`는 04:20:35 UTC에 부팅했습니다. 두 번 모두 노드가 재부팅된 직후에 컨테이너가 한꺼번에 끝난 것입니다. 이 재시작 때문에 `prometheus-kube-prometheus-stack-prometheus-0`가 다시 뜨면서 01:14:32 UTC에 WAL을 읽다가 오류를 만나 복구를 시작했습니다. 로그에 "Encountered WAL read error, attempting repair"와 "Starting corruption repair"가 남아 있습니다. Prometheus는 지금 계속 돌고 있지만 복구가 끝났다는 줄은 수집한 로그에 없고, 복구는 손상된 지점 뒤의 기록을 잘라 내는 방식이라 그 무렵의 메트릭 일부가 빠졌을 수 있습니다. `tempo-0`도 같은 01:12 UTC에 종료 코드 255로 끝났다가 다시 올라왔습니다.

두 노드가 재부팅된 것은 부팅 시각 메트릭으로 확인했습니다. 하지만 누가 왜 재부팅했는지(OS 업데이트, 사람, 전원 문제)는 이번 점검으로는 알 수 없습니다. 노드에 접속하지 않기로 해서 노드의 journal을 읽지 못했습니다. 그 시각의 `journalctl -b -1`을 보면 알 수 있습니다.

이 일로 2번 문제(Prometheus 데이터가 emptyDir에 있음)가 드러났습니다. 이번에는 컨테이너만 다시 시작하고 파드는 그대로여서 데이터가 남았지만, 파드가 지워지고 다시 만들어졌다면 30일 치 메트릭이 전부 사라졌을 것입니다.

## 1. 백업이 클러스터 밖에 없음

**고른 이유.** 노드 두 대가 함께 망가지거나 클러스터 권한으로 볼륨이 지워지면 데이터베이스 일곱 개(운영 여섯 개 포함)와 etcd를 한꺼번에 잃고 되살릴 방법이 없습니다.

### 무슨 일인가

이 클러스터에는 Velero 같은 백업 도구가 없고 VolumeSnapshot도 0개입니다. 그 대신 백업 CronJob 여덟 개가 지난 7일 안에 돌았습니다. 데이터베이스 덤프를 만드는 일곱 개(`app-a-postgres-backup`, `app-f-postgres-backup`, `app-f-postgres-mx-backup`, `app-f-postgres-vn-backup`, `app-g-postgres-backup`, `app-h-mysql-backup`, `app-i-postgres-backup`)와 etcd 스냅샷을 복사하는 `kube-system/etcd-snapshot-backup`입니다. k3s가 스스로 만드는 etcd 스냅샷도 5개 있습니다.

여덟 개 모두 덤프를 `node-a` 노드의 local-path 볼륨에 씁니다. 원본 데이터베이스는 `node-b` 노드에 있으니, 노드 한 대가 고장 나는 경우에는 다른 노드의 사본으로 되살릴 수 있습니다. 하지만 여덟 개 가운데 어느 것도 S3나 rclone, restic 같은 클러스터 밖 저장소로 보내는 흔적이 없습니다. 두 노드를 함께 잃는 일에는 남는 사본이 없습니다. 덤프를 실제로 복원해 본 적이 있는지는 이번 점검으로는 알 수 없습니다.

하나 더 있습니다. 백업 덤프를 담은 PersistentVolume 여섯 개는 reclaimPolicy가 `Delete`입니다. 원본 데이터베이스 볼륨 대부분이 `Retain`인 것과 반대라서, 네임스페이스나 PVC가 지워지면 원본 볼륨은 남아도 덤프는 함께 지워집니다. 이 점은 3번 문제(prune이 켜진 Argo CD 앱이 Namespace와 CRD를 관리함)와 겹칩니다.

### 왜 생기나

백업 CronJob들이 덤프를 원본과 다른 노드에 두도록 짜여 있어서 노드 한 대의 고장에는 대비가 돼 있습니다. 그다음 단계인 클러스터 밖 사본만 아직 만들어지지 않은 상태입니다. CronJob의 볼륨과 명령, 환경 변수에서 밖으로 보내는 흔적을 찾지 못했다는 것은 문자열을 맞춰 본 결과라서, 다른 방식으로 밖으로 보내고 있다면 그 사실은 여기에 잡히지 않습니다.

백업이 무엇을 막아 주는지는 사본이 어디에 있는지가 정합니다. 원본과 같은 디스크에 있는 사본은 실수로 지운 데이터만 되살려 주고, 디스크가 고장 나면 둘 다 잃습니다. 같은 클러스터의 다른 노드에 있는 사본은 노드 고장까지 막아 줍니다. 하지만 클러스터 전체에 닿는 일은 막지 못합니다. 노드가 있는 장소의 화재나 도난, 클러스터 권한을 얻은 공격자나 스크립트가 볼륨을 지우는 경우, 네임스페이스가 통째로 지워지는 경우가 그렇습니다. 이때는 사본도 원본과 함께 사라집니다.

그래서 백업에서 오래 쓰여 온 기준이 3-2-1입니다. 중요한 데이터는 원본 하나와 백업 사본 둘을 두고, 두 종류의 저장 매체에 나눠 두고, 그중 사본 하나는 다른 장소에 둡니다. 덤프를 같은 클러스터의 PersistentVolume에 쌓는 클러스터는 원본과 사본 하나를 한 장소, 한 종류의 매체에 둔 셈입니다.

쿠버네티스는 클러스터 밖 사본을 대신 만들어 주지 않습니다. VolumeSnapshot은 CSI 드라이버가 있어야 쓸 수 있는데, local-path 볼륨은 한 노드의 디렉터리일 뿐이라 뒤에서 스냅샷을 따로 보관해 줄 스토리지가 없습니다. 볼륨에 적힌 용량도 지켜지지 않고, 볼륨을 지우면 내용도 지워집니다. 그러니 내보내는 단계는 직접 만들어야 합니다.

클러스터 상태도 같습니다. k3s는 기본으로 하루 두 번 etcd 스냅샷을 만들고 서버 노드에 다섯 개를 남깁니다. 이 스냅샷에는 데이터스토어 전체와 클러스터 CA 키가 들어 있고, 서버 토큰에서 만든 키로 암호화됩니다. 그래서 새 호스트에서 복원하려면 그 토큰이 있어야 하고, 토큰이 없는 스냅샷으로는 아무것도 되살리지 못합니다. 마지막으로, 복원해 보지 않은 백업은 된다고 말할 수 없습니다. 매일 밤 덤프 파일이 생긴다는 것은 Job이 돌았다는 뜻이지 그 파일로 데이터베이스가 살아난다는 뜻이 아닙니다.

[GitLab](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/)은 2017년에 엔지니어가 운영 데이터베이스의 데이터 디렉터리를 실수로 지웠습니다. 매일 돌던 `pg_dump` 백업은 버전이 맞지 않아 계속 실패하고 있었고, 실패를 알리는 메일은 거부되고 있었으며, S3 버킷은 비어 있었습니다. 결국 여섯 시간 전에 손으로 떠 둔 LVM 스냅샷으로 복구했습니다. 백업이 있다고 모두 믿었지만 만들어지지 않는다는 것을 알려 주는 장치가 없었고 복원해 본 사람도 없었습니다. 이 클러스터도 덤프는 매일 쌓이지만 복원해 본 기록은 클러스터에 남아 있지 않습니다.

[InfluxData](https://www.influxdata.com/blog/deleting-production-steps-how-fix-it/)는 Argo CD 설정의 이름 충돌 때문에 운영 환경 하나가 통째로 지워졌습니다. 볼륨의 reclaimPolicy가 `Retain`이어서 데이터는 남았고, 쿠버네티스 오브젝트는 손으로 다시 만들었습니다. 클러스터 권한으로 지우는 일은 클러스터 안의 사본을 원본과 함께 가져가고, 그 손이 닿지 않은 것만 돌아옵니다. 이 클러스터의 덤프 볼륨이 `Delete`라는 점이 여기에 해당합니다.

### 추천 점검 방법

백업은 "만들어졌는가", "밖으로 나갔는가", "되살아나는가" 세 가지를 따로 봐야 합니다.

만들어졌는지는 CronJob의 마지막 성공 시각으로 봅니다. kube-state-metrics가 내보내는 `kube_cronjob_status_last_successful_time`으로 일정보다 오래 성공하지 못한 백업을 알리는 규칙인데, 이 클러스터에는 `BackupCronJobStale`이라는 이름의 알림 규칙이 이미 있습니다. 아래와 같은 모양입니다.

```yaml
- alert: BackupCronJobStale
  expr: time() - kube_cronjob_status_last_successful_time{cronjob=~".*backup.*"} > 86400 * 1.5
  for: 30m
```

밖으로 나갔는지는 내보내는 Job도 CronJob으로 만들면 같은 메트릭으로 볼 수 있습니다. 오브젝트 스토리지 쪽에서는 가장 최근 오브젝트의 시각과 버킷 크기를 봅니다.

```
time() - kube_cronjob_status_last_successful_time{cronjob="offsite-backup"}
```

되살아나는지는 메트릭으로 볼 수 없습니다. 정해진 주기로 덤프 하나를 빈 데이터베이스에 복원해 몇 개 테이블의 행 수를 비교해 보고, k3s 스냅샷은 여분의 호스트에서 서버 토큰과 함께 복원해 보는 수밖에 없습니다.

### 추천 해결 방안

이 규모에서는 이미 만들고 있는 덤프를 그대로 두고, 그것을 클러스터 밖 오브젝트 스토리지로 한 번 더 보내는 단계만 더하는 방법을 권합니다. 덤프 볼륨을 읽기 전용으로 마운트하는 CronJob을 하나 두고 `restic`이나 `rclone`으로 S3 호환 버킷에 올립니다. `restic`은 올리기 전에 암호화하니 저장소 쪽에 내용을 맡기지 않아도 됩니다. 얻는 것은 장소 전체를 잃어도 남는 사본이고, 치르는 것은 매달의 저장 비용과 Secret으로 관리할 자격 증명 하나입니다. `restic` 저장소 비밀번호를 잃으면 백업도 잃는다는 점은 기억해야 합니다. 아래는 모양을 보여 주는 예시이며, 버킷과 Secret 이름은 환경에 맞게 정합니다.

```yaml
containers:
  - name: offsite
    image: restic/restic
    args: ["backup", "/dumps"]
    envFrom:
      - secretRef: { name: offsite-backup }
    volumeMounts:
      - { name: dumps, mountPath: /dumps, readOnly: true }
```

etcd는 k3s의 etcd 스냅샷 S3 옵션을 켜면 스냅샷을 만들 때마다 버킷에도 올라갑니다. 서버 토큰은 클러스터 밖, 비밀번호 관리 도구 같은 곳에 따로 보관해야 그 스냅샷을 쓸 수 있습니다.

적용할 때 조심할 것이 있습니다. 덤프 볼륨은 `node-a` 노드의 local-path라서 내보내는 CronJob도 `node-a`에서 떠야 볼륨을 붙일 수 있습니다. 그리고 파드는 자기 네임스페이스의 PVC만 마운트할 수 있으니, 덤프가 일곱 개 네임스페이스에 흩어져 있는 지금은 네임스페이스마다 내보내는 CronJob을 하나씩 두거나 덤프 위치를 한곳으로 모아야 합니다. 그리고 k3s 설정을 바꾸려면 `node-b`의 k3s를 재시작해야 하는데, 이 클러스터의 컨트롤 플레인 노드는 `node-b` 하나라서 재시작하는 동안 API 서버가 멈춥니다.

이 CronJob들은 Argo CD가 관리합니다. 데이터베이스 백업은 각각의 앱(`app-a-prod`, `app-f-kr`, `app-f-mx`, `app-f-vn`, `app-g-api`, `app-h`, `app-i`)이 `https://github.com/example-org/k8s-manifests` 저장소의 `prod/<앱 이름>` 경로에서, etcd 스냅샷 복사는 앱 `etcd-snapshot-backup`이 같은 저장소의 `infra/etcd-snapshot-backup` 경로에서 관리합니다. 모두 selfHeal이 켜져 있어서 클러스터에서 직접 고치면 되돌아가니, 내보내는 CronJob도 그 저장소에 추가해야 합니다.

규모가 커지면 Velero로 쿠버네티스 오브젝트와 볼륨을 함께 정해진 일정으로 다른 계정이나 리전의 오브젝트 스토리지에 백업하고, 정기적으로 임시 클러스터에 복원해 보는 편이 좋습니다.

### 근거

| 항목 | 값 | 출처 |
|---|---|---|
| 백업 도구 | 없음 | inventory.json |
| VolumeSnapshot | 0개 | inventory.json |
| k3s etcd 스냅샷 | 5개 | inventory.json |
| 지난 7일 안에 돈 백업 CronJob | 8개, 덤프는 모두 `node-a` | summary.json:resilience.backup.rows |
| 원본 데이터베이스 노드 | `node-b` | summary.json:resilience.backup.rows |
| 클러스터 밖 사본 흔적 | 8개 모두 없음 | summary.json:resilience.backup.rows |
| reclaimPolicy가 `Delete`인 백업 덤프 볼륨 | 6개 | objects/persistentvolumes.json |

### 더 읽을 것

- [GitLab: Postmortem of database outage of January 31](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/): 백업이 있다고 믿는 것과 복원되는 것이 어떻게 다른지 보여 주는 기록입니다.
- [k3s: etcd-snapshot](https://docs.k3s.io/cli/etcd-snapshot): S3 옵션과 복원 절차, 복원에 필요한 토큰이 정리돼 있습니다.
- [restic: Preparing a new repository](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html): restic이 쓸 수 있는 저장소와 저장소 비밀번호가 어떻게 동작하는지 설명합니다.
- [Velero: How Velero Works](https://velero.io/docs/main/how-velero-works/): 백업과 일정, 복원이 각각 무엇을 하고 복원이 무엇을 건드리지 않는지 알 수 있습니다.

## 2. Prometheus 데이터가 emptyDir에 있음

**고른 이유.** Prometheus 파드가 지워졌다가 다시 만들어지는 순간 30일 치 메트릭이 전부 사라지고, 그 기간에 무슨 일이 있었는지 되짚을 근거가 없어집니다.

### 무슨 일인가

`monitoring` 네임스페이스의 Prometheus(`prometheus-kube-prometheus-stack-prometheus`)는 데이터 디렉터리를 PersistentVolumeClaim이 아니라 emptyDir에 두고 있습니다. 지금 TSDB 크기는 22.3GiB이고, 보존 기간은 30일, 크기 상한은 `0B`라서 시간으로만 데이터를 지웁니다. 실제로 남아 있는 가장 오래된 샘플은 31.2일 전 것입니다. 레플리카는 하나이고 `nodeSelector`가 `role: observability`로 걸려 있어 지금 `node-b` 노드에서 돌고 있습니다.

이번 기간에 이 위험이 실제로 건드려졌습니다. 이미 일어난 일에 적은 '두 노드에서 컨테이너가 한꺼번에 다시 시작됨' 때 2026-11-14 01:14 UTC에 Prometheus가 WAL 손상을 만나 복구했습니다. 그때는 컨테이너만 다시 시작했고 파드는 그대로였기 때문에 emptyDir의 데이터가 남았습니다. 지난 7일 동안 compaction이 실패한 적은 없습니다.

Prometheus 컨테이너는 CPU limit `300m`, 메모리 limit `1536Mi`로 돌고 있고, head 시계열은 178,571개입니다. 같은 컨테이너가 지난 24시간 동안 CPU 주기의 45%를 스로틀링으로 멈춰 있었다는 점은 그다음으로 큰 문제의 CPU 스로틀링 항목에 함께 적었습니다.

### 왜 생기나

이 Prometheus의 StatefulSet에 `volumeClaimTemplates`가 없고 데이터 볼륨 `prometheus-kube-prometheus-stack-prometheus-db`가 emptyDir인 것을 오브젝트에서 확인했습니다. 차트 값에서 일부러 뺀 것인지 기본값을 그대로 둔 것인지는 클러스터에 남아 있지 않습니다.

Prometheus는 가장 최근 데이터를 메모리에 둡니다. 들어오는 샘플은 두 시간 단위 블록으로 묶이는데, 지금 채우는 블록(head)은 메모리에 있고 디스크에 다 쓰이지 않습니다. 그 대신 디스크의 write-ahead log(WAL)가 128MB 조각으로 이 내용을 기록해 두어, 프로세스가 갑자기 죽어도 다시 시작할 때 WAL을 읽어 head를 되살립니다. 이번 기간의 WAL 복구가 이 과정입니다. 다 찬 블록은 백그라운드에서 compaction으로 더 긴 블록으로 합쳐집니다.

Prometheus의 로컬 저장소는 클러스터링도 복제도 하지 않습니다. 공식 문서도 노드 하나짜리 데이터베이스처럼 다루라고 합니다. 그런데 emptyDir은 파드의 수명을 따르는 볼륨입니다. 컨테이너가 다시 시작할 때는 남지만, 파드가 노드에서 지워지면 내용도 함께 지워집니다. StatefulSet의 롤링 업데이트, 차트 업그레이드로 바뀐 파드 템플릿, 노드 drain, eviction 모두 파드를 지우고 새로 만들기 때문에 그때마다 30일 치 데이터가 사라집니다.

디스크에도 따로 실패하는 방식이 있습니다. 보존 기간은 시간으로 정하고 크기 상한은 기본으로 꺼져 있어서, 시계열이 늘면 블록이 디스크보다 커지는 것을 막는 장치가 없습니다. 디스크가 차면 compaction이 실패하고 결국 쓰기가 멈춥니다. 두 상한을 함께 두면 먼저 닿는 쪽이 쓰이고, 문서는 compaction 전후에 잠깐 상한을 넘을 수 있으니 크기 상한을 디스크의 80~85%로 두라고 권합니다. emptyDir은 노드의 루트 파일시스템을 쓰니, 지금은 Prometheus가 노드 디스크를 다른 파드와 나눠 쓰고 있는 셈입니다.

[UK Ministry of Justice](https://runbooks.cloud-platform.service.justice.gov.uk/incidents/2024-04-15-prometheus.html)는 2024년에 계획된 변경 뒤 Prometheus가 다시 시작했는데, WAL을 다시 읽는 데 startup probe가 허용한 시간보다 오래 걸려서 끝나기 전에 계속 재시작됐습니다. 세 시간 넘게 모니터링이 없었고 startup probe를 늘린 뒤에야 돌아왔습니다. 이 클러스터에서도 다시 시작하는 순간이 가장 위험하다는 점이 같습니다. 이번 WAL 복구는 무사히 끝났지만 재시작 때 무엇이 일어나는지는 데이터 크기에 따라 달라집니다.

[UK Ministry of Justice](https://runbooks.cloud-platform.service.justice.gov.uk/incidents/2023-07-25-prometheus-on-live-cluster-down.html)는 2023년에도 운영 클러스터의 Prometheus가 종료 코드 137로 계속 OOMKilled 되어 두 시간 가까이 모니터링을 잃었습니다. 네임스페이스와 규칙이 늘면서 Prometheus가 필요한 메모리가 인스턴스가 줄 수 있는 양을 넘었고, 결국 더 큰 노드로 옮기고 limit을 올렸습니다. 알림은 클러스터 밖의 Pingdom 점검이 울렸습니다.

[Saifeddine Rajhi](https://seifrajhi.github.io/blog/prometheus-manage-memory-overload/)는 kube-prometheus-stack 차트를 업그레이드하는 동안 Prometheus 파드가 OOMKilled로 Ready가 되지 못한 경험을 적었습니다. 평소에는 약 30Gi로 돌다가 WAL로 복구하는 동안 50Gi 넘게 필요했고, `promtool tsdb analyze`로 시계열이 많은 메트릭을 찾아 줄였습니다. limit 가까이 도는 Prometheus는 다시 시작하지 못할 수 있다는 점이 이 클러스터의 메모리 limit을 정할 때 참고가 됩니다.

### 추천 점검 방법

볼륨이 차는 것과 compaction 실패는 알림으로 봅니다. 이 클러스터에는 `PrometheusTSDBCompactionsFailing` 알림 규칙이 이미 있습니다. 볼륨 사용률 알림은 PVC로 옮긴 뒤에야 의미가 있으니, 옮긴 뒤 아래 모양의 규칙을 더하는 편이 좋습니다. `KubePersistentVolumeFillingUp`도 이미 있어 PVC로 옮기면 함께 걸립니다.

```yaml
- alert: PrometheusVolumeFillingUp
  expr: |
    kubelet_volume_stats_used_bytes{persistentvolumeclaim=~"prometheus-.*"}
      / kubelet_volume_stats_capacity_bytes{persistentvolumeclaim=~"prometheus-.*"} > 0.8
```

메모리는 limit에 대한 사용량을 다시 시작할 여유까지 생각해 낮은 기준으로 지켜봅니다. 아래 같은 규칙은 이 클러스터에서 찾지 못했습니다.

```yaml
- alert: PrometheusMemoryNearLimit
  expr: |
    container_memory_working_set_bytes{container="prometheus"}
      / on (namespace, pod, container) kube_pod_container_resource_limits{resource="memory", container="prometheus"} > 0.75
  for: 30m
```

메모리가 따라가는 것은 head의 시계열 수이므로 `prometheus_tsdb_head_series`가 배포 뒤 계단처럼 오르는지도 함께 봅니다. Prometheus가 죽으면 규칙도 평가되지 않으니, Prometheus 자신의 상태는 클러스터 밖에서 health 엔드포인트를 확인하는 점검으로만 알 수 있습니다.

### 추천 해결 방안

이 규모에서는 Prometheus 하나를 의도한 크기로 두는 방법을 권합니다. kube-prometheus-stack 값에서 `storageSpec`으로 PersistentVolumeClaim을 주고, `retention` 옆에 `retentionSize`를 볼륨의 80~85%로 두고, 메모리 limit은 head 시계열 수와 재시작 여유를 보고 정합니다. 지금 TSDB가 22.3GiB이니 30일을 그대로 두려면 볼륨도 그보다 넉넉해야 하고, 볼륨을 작게 잡으면 크기 상한이 먼저 닿아 오래된 데이터가 30일보다 일찍 지워집니다. 얻는 것은 파드가 다시 만들어져도 남는 데이터와 디스크가 차서 쓰기가 멈추지 않는다는 보장이고, 치르는 것은 레플리카가 하나라서 다시 시작하는 동안 메트릭과 알림 평가에 빈틈이 생긴다는 점입니다. 아래는 모양을 보여 주는 예시이며 숫자는 이 클러스터에 맞게 정해야 합니다.

```yaml
prometheus:
  prometheusSpec:
    retention: 30d
    retentionSize: "40GiB"
    storageSpec:
      volumeClaimTemplate:
        spec:
          resources:
            requests:
              storage: 48Gi
```

적용할 때 조심할 것이 있습니다. `storageSpec`을 넣으면 StatefulSet의 볼륨이 바뀌어 파드가 새로 만들어지고, 그 순간 emptyDir에 있던 30일 치 데이터는 사라집니다. 지금 데이터가 필요하다면 바꾸기 전에 따로 옮겨 둬야 합니다. 이 클러스터의 다른 볼륨처럼 local-path StorageClass를 쓰면 새 PVC는 그 노드의 디렉터리가 되고, 데이터가 그 노드에 고정됩니다. 또 이 Prometheus는 Argo CD 앱 `monitoring`이 Helm 차트 `kube-prometheus-stack`(저장소 `https://prometheus-community.github.io/helm-charts`, 버전 `79.5.0`)으로 관리하고 selfHeal이 켜져 있어서, 클러스터에서 직접 고치면 되돌아갑니다. 값은 그 Argo CD 앱의 Helm 값에서 바꿔야 합니다.

규모가 커지면 시계열이 늘어나는 원인 자체를 다루는 편이 좋습니다. `promtool tsdb analyze`로 시계열이 많은 메트릭을 찾아 줄이고, startup probe를 실제 WAL 재생 시간에 맞추고, 클러스터 밖 health 점검을 둡니다. 더 커지면 같은 설정의 Prometheus 두 개 앞에 Thanos Querier 같은 조회 계층을 두거나 관리형 Prometheus로 저장을 클러스터 밖으로 옮깁니다.

### 근거

| 항목 | 값 | 출처 |
|---|---|---|
| 데이터 볼륨 | emptyDir, PVC 없음 | summary.json:stackhealth.prometheus |
| TSDB 크기 | 22.3GiB | summary.json:stackhealth.prometheus |
| 보존 기간과 크기 상한 | 30d, `0B` | summary.json:stackhealth.prometheus |
| 가장 오래된 샘플 | 31.2일 전 | summary.json:stackhealth.prometheus |
| WAL 손상 복구 | 1번, 2026-11-14 01:14 UTC | logs/pods/prometheus/monitoring_prometheus-kube-prometheus-stack-prometheus.log |
| 7일 동안 실패한 compaction | 0번 | summary.json:stackhealth.prometheus |
| head 시계열 | 178,571개 | metrics `prometheus_tsdb_head_series` |
| 컨테이너 limit | CPU `300m`, 메모리 `1536Mi` | objects/pods.json |
| 레플리카와 노드 | 1개, `nodeSelector` `role: observability` | objects/statefulsets.apps.json |

### 더 읽을 것

- [Prometheus: Storage](https://prometheus.io/docs/prometheus/latest/storage/): 블록, WAL, compaction, 두 가지 보존 상한과 디스크 크기를 정하는 공식이 있습니다.
- [Robust Perception: How much RAM does Prometheus 2.x need for cardinality and ingestion?](https://www.robustperception.io/how-much-ram-does-prometheus-2-x-need-for-cardinality-and-ingestion/): 시계열과 라벨마다 메모리가 얼마나 드는지 보고 head 시계열 수로 limit을 어림할 수 있습니다.
- [Prometheus Operator: Storage](https://prometheus-operator.dev/docs/platform/storage/): Prometheus에 볼륨 클레임을 주는 방법과 크기를 바꿀 때 필요한 일이 있습니다.
- [Prometheus Operator: High Availability](https://prometheus-operator.dev/docs/platform/high-availability/): 레플리카 두 개가 주는 것과 주지 않는 것, 조회 계층이 필요한 이유를 설명합니다.
- [Saifeddine Rajhi: Prometheus memory overload](https://seifrajhi.github.io/blog/prometheus-manage-memory-overload/): 다시 시작하지 못한 Prometheus를 따라가며 원인 메트릭을 찾는 과정을 보여 줍니다.

## 3. prune이 켜진 Argo CD 앱이 Namespace와 CRD를 관리함

**고른 이유.** Git에서 매니페스트 하나가 빠지거나 경로가 바뀌면 Argo CD가 운영 네임스페이스를 그 안의 PVC와 Secret까지 통째로 지우거나, Istio와 Gateway API의 CRD를 지워 그 종류의 오브젝트를 클러스터 전체에서 없앨 수 있습니다.

### 무슨 일인가

운영 Argo CD 앱 11개 가운데 9개가 자동 sync에 `prune: true`를 켠 채 Namespace나 CRD를 관리 대상 리소스로 갖고 있습니다. 8개(`app-a-prod`, `app-b-prod`, `app-d`, `app-g-api`, `app-ac-prod`, `app-k`, `app-n`, `app-l-prod`)는 각자 자기 이름의 Namespace 하나를 관리합니다. `istio` 앱은 Namespace 대신 CRD 23개를 관리합니다. 9개 모두 `selfHeal`이 켜져 있고 `resources-finalizer.argocd.argoproj.io` finalizer가 붙어 있습니다.

이 네임스페이스들에는 운영 데이터베이스와 저장소의 볼륨이 있습니다. 다행히 데이터베이스 원본 볼륨 대부분은 reclaimPolicy가 `Retain`이라서 PVC가 지워져도 PersistentVolume과 노드의 디렉터리는 남습니다. 하지만 `app-g-api`의 `app-g-postgres-backup-node-a-pvc`처럼 `Delete`인 볼륨은 PVC와 함께 내용도 지워집니다. Secret, ConfigMap, Service 같은 오브젝트는 모두 사라지고 손으로 다시 만들어야 합니다. 지금 이 일이 일어나고 있다는 표시는 없습니다.

### 왜 생기나

Namespace를 관리하는 8개 앱 모두 syncOptions에 `CreateNamespace=true`가 있는데도 Namespace를 따로 관리하는 것으로 나옵니다. Git의 매니페스트에 Namespace 오브젝트가 함께 들어 있어서 Argo CD가 그것을 앱의 리소스로 추적하는 것으로 보입니다. 앱의 리소스 목록에서 확인했고, 매니페스트 저장소는 열어 보지 않았습니다. `istio` 앱의 CRD는 Istio와 Gateway API를 설치하면서 함께 들어온 것입니다.

Argo CD의 자동 sync는 기본으로 아무것도 지우지 않습니다. Git에서 사라진 리소스도 클러스터에 남겨 둡니다. 자동 sync 정책에 `prune: true`를 넣으면 이것이 바뀌어, Git에서 렌더링되는 목록에서 빠진 리소스는 다음 sync 때 클러스터에서도 지워집니다.

"Git에서 빠진다"는 일부러 지우는 경우만이 아닙니다. 디렉터리를 옮기거나, 리소스 이름을 바꾸거나, 생성기나 템플릿이 다른 이름을 렌더링하는 경우도 Argo CD에게는 똑같이 옛 오브젝트가 대상 목록에서 사라진 것으로 보입니다. 기본으로 들어 있는 보호 장치는 하나뿐인데, 렌더링 결과가 완전히 비었을 때만 prune을 거부합니다. 다른 리소스는 그대로 렌더링되고 Namespace만 빠진 경우는 이 장치를 통과합니다.

대부분의 종류는 잘못 지워져도 오브젝트 하나로 끝납니다. 하지만 두 종류는 다른 것을 담는 그릇입니다. Namespace를 지우면 그 안의 모든 것이 비동기로 지워지고, 그동안 Namespace는 Terminating 상태로 새 오브젝트를 받지 않습니다. CRD를 지우면 API 서버가 그 엔드포인트를 내리고 저장된 커스텀 오브젝트를 모두 지웁니다. CRD를 다시 만들어도 빈 상태로 시작합니다. 그래서 Namespace나 CRD가 앱의 리소스이면 매니페스트 하나가 빠지는 것만으로 그 네임스페이스의 워크로드와 Secret, PVC 전부, 또는 그 종류의 오브젝트 전부가 지워집니다.

`CreateNamespace=true`로 Argo CD가 만든 Namespace는 보통 추적되지 않으니 prune 되지 않습니다. 앱 자체를 지우는 것도 같은 결과로 가는 두 번째 길입니다. `resources-finalizer.argocd.argoproj.io` finalizer가 붙은 앱을 지우면 컨트롤러가 앱의 리소스를 cascade로 지우는데, 이 클러스터의 9개 앱 모두 이 finalizer가 있습니다.

[InfluxData](https://www.influxdata.com/blog/deleting-production-steps-how-fix-it/)는 이미 있던 이름으로 Argo CD Application과 AppProject를 추가하는 PR을 머지했다가, 새 오브젝트가 기존 앱을 대신하면서 운영 환경 하나가 통째로 지워졌습니다. 모든 API 엔드포인트가 404를 돌려줬습니다. 볼륨이 `Retain`이어서 데이터는 남았고 머지 뒤 여섯 시간이 조금 안 돼 서비스가 돌아왔습니다. 그 뒤 팀은 상태를 가진 리소스와 Argo CD가 관리하는 Namespace에 `Prune=false`를 붙이고 `FailOnSharedResource=true`를 켰습니다. Git의 렌더링 결과가 바뀌는 것만으로 앱이 가진 것이 Namespace까지 지워졌다는 점이 이 클러스터와 같습니다.

[Argo CD issue 28630](https://github.com/argoproj/argo-cd/issues/28630)에는 Argo CD가 관리하던 공유 Namespace가 지워져 약 97개 앱이 Missing이나 OutOfSync로 남았다는 보고가 있습니다. 논의 끝에 원인은 prune이 아니라 force를 켠 수동 sync가 다른 앱을 가리키는 추적 라벨이 붙은 Namespace를 지웠다가 다시 만든 것으로 정리됐고, Namespace의 `Prune=false`는 이를 막지 못했습니다. 이 이슈는 issue 29739의 중복으로 닫혔습니다. `Prune=false` 하나만으로 모든 길이 막히지는 않는다는 점을 보여 줍니다.

### 추천 점검 방법

prune된 리소스를 세는 메트릭은 없습니다. 대신 보호 장치를 걸어 두면 그 결과가 보입니다. Namespace에 `Prune=false`를 붙이면 Argo CD가 그것을 지우려 할 때 앱이 OutOfSync로 남으니, 오래 OutOfSync인 앱을 알리면 사람이 알아챌 수 있습니다. 이런 알림 규칙은 이 클러스터에서 찾지 못했으니 새로 만들어야 합니다.

```yaml
- alert: ArgoAppOutOfSync
  expr: argocd_app_info{sync_status="OutOfSync"} == 1
  for: 30m
```

어느 앱이 Namespace나 CRD를 추적하는지는 아래 명령 모양으로 확인할 수 있습니다.

```bash
kubectl get applications.argoproj.io -A -o json | jq -r '.items[] | select(.spec.syncPolicy.automated.prune==true) | .metadata.name as $n | .status.resources[]? | select(.kind=="Namespace" or .kind=="CustomResourceDefinition") | $n+" "+.kind+"/"+.name'
```

### 추천 해결 방안

이 규모에서는 Namespace 매니페스트를 Git에서 빼고 이미 켜져 있는 `CreateNamespace=true`에 맡기거나, 매니페스트를 남기되 Namespace에 `Prune=false`를 붙이는 방법을 권합니다. 9개 앱이 이미 `CreateNamespace=true`를 쓰고 있으니 앞쪽이 바꿀 것이 적습니다. 다시 만들 수 없는 데이터를 담은 CRD에도 같은 표시를 붙입니다. 얻는 것은 매니페스트가 빠져도 Namespace가 지워지지 않는다는 점이고, 치르는 것은 정말 지우고 싶은 Namespace를 손으로 지워야 하고 `Prune=false`인 동안 앱이 OutOfSync로 보인다는 점입니다. 아래는 모양을 보여 주는 예시입니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: app-g-api
  annotations:
    argocd.argoproj.io/sync-options: Prune=false
```

적용할 때 조심할 것이 있습니다. 매니페스트에서 Namespace를 빼는 순간 prune이 켜진 앱은 그 Namespace를 지우려 합니다. 그러니 먼저 `Prune=false`를 Git에 넣어 sync가 끝난 것을 확인하고, 그다음 커밋에서 Namespace 매니페스트를 빼야 합니다. 그 순서를 거꾸로 하면 바로 이 문제가 일어납니다. `istio` 앱의 CRD에도 같은 순서가 필요한데, 이 CRD들은 저장소의 파일이 아니라 Istio Helm 차트에서 렌더링되므로 위 예시처럼 YAML을 고치는 대신 차트 값이나 렌더링 뒤 단계에서 annotation을 붙여야 합니다.

이 앱들은 `argocd` 네임스페이스의 Application 오브젝트이고, 각 앱의 매니페스트는 `https://github.com/example-org/k8s-manifests` 저장소에 있습니다. selfHeal이 켜져 있으니 클러스터에서 Namespace에 직접 annotation을 붙여도 Git에 없으면 되돌아갈 수 있습니다. 바꾸는 곳은 그 저장소입니다.

규모가 커지면 Namespace와 CRD에 `Prune=confirm`과 `Delete=confirm`을 붙여 사람이 승인하기 전에는 지워지지 않게 하고, 볼륨은 reclaimPolicy `Retain`인 StorageClass에 두고, `FailOnSharedResource=true`로 다른 앱의 오브젝트를 건드리기 전에 sync가 실패하게 합니다.

### 근거

| 항목 | 값 | 출처 |
|---|---|---|
| 운영 Argo CD 앱 | 11개 | summary.json:argocdctl.summary |
| prune이 켜진 채 Namespace나 CRD를 관리하는 앱 | 9개 | summary.json:argocdctl.summary |
| Namespace를 관리하는 앱 | 8개, 각 1개 | objects/applications.argoproj.io.json |
| `istio` 앱이 관리하는 CRD | 23개 | objects/applications.argoproj.io.json |
| `app-g-api`의 reclaimPolicy `Delete` 볼륨 | `app-g-postgres-backup-node-a-pvc` | objects/persistentvolumes.json |

### 더 읽을 것

- [Argo CD: Sync Options](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/): `Prune=false`, `Prune=confirm`, `Delete=confirm`, `CreateNamespace`가 각각 sync 상태에 무엇을 남기는지 정리돼 있습니다.
- [Argo CD: Automated Sync Policy](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/): 자동 sync가 기본으로 무엇을 지우고 prune이 무엇을 더하는지, 빈 앱 보호가 어디까지인지 설명합니다.
- [InfluxData: Deleting Production in a Few Easy Steps](https://www.influxdata.com/blog/deleting-production-steps-how-fix-it/): Argo CD 때문에 운영 환경이 지워진 과정과 그 뒤 팀이 바꾼 것들이 모두 적혀 있습니다.
- [Argo CD: App Deletion](https://argo-cd.readthedocs.io/en/stable/user-guide/app_deletion/): 앱을 지울 때 리소스까지 지워지는 경우와 finalizer가 그것을 정하는 방식을 설명합니다.

## 4. Kubernetes 1.33의 지원 종료

**고른 이유.** 이 클러스터는 보안 패치가 더는 나오지 않는 버전에서 돌고 있어서, 새로 알려진 취약점이 생겨도 고칠 길이 없고 미룰수록 업그레이드가 한꺼번에 몰립니다.

### 무슨 일인가

API 서버와 두 노드 모두 `v1.33.5+k3s1`입니다. Kubernetes 1.33은 upstream 지원이 2026-06-28에 끝났고, 점검한 날 기준으로 140일이 지났습니다. 이 버전에는 더 이상 패치 릴리스가 나오지 않습니다.

업그레이드를 막을 만한 것은 이번 점검에서 찾지 못했습니다. Pluto와 kubent로 매니페스트와 Helm 릴리스를 1.34 기준으로 읽었을 때 다음 버전에서 없어지는 API를 쓰는 곳은 없었습니다. API 서버의 `apiserver_requested_deprecated_apis`에는 `endpoints` `v1` 호출 한 줄이 있지만, 이 시계열에는 없어지는 릴리스가 적혀 있지 않습니다. 업그레이드를 미룬 이유는 클러스터에 남아 있지 않습니다.

### 왜 생기나

k3s는 클라우드가 대신 올려 주는 플랫폼이 아니라서 누군가 정해서 올리지 않으면 버전이 그대로 남습니다. 이 클러스터에는 system-upgrade-controller 같은 자동 업그레이드 장치가 없는 것으로 보입니다. 설치된 구성 요소 목록에서 찾지 못했다는 뜻이고, 노드에서 손으로 올리는 절차가 따로 있는지는 알 수 없습니다.

Kubernetes 프로젝트는 가장 최근 세 개의 마이너 버전만 관리합니다. 한 마이너는 대략 14개월 동안 패치를 받습니다. 12개월은 일반 지원이고, 이어지는 2개월은 유지보수 기간으로 CVE가 붙은 취약점과 의존성 문제, 핵심 구성 요소의 심각한 문제만 고칩니다. 그 뒤로는 아무것도 고치지 않고, 옛 버전에만 있는 취약점은 아예 보고되지 않을 수도 있습니다.

기다리는 비용은 한 가지 규칙에서 나옵니다. API 서버는 업그레이드할 때 마이너 버전을 건너뛸 수 없습니다. 노드가 하나인 클러스터도 같습니다. 세 마이너 뒤처진 클러스터는 세 번을 차례로 올려야 하고, 매번 없어지는 API와 애드온 호환성을 따로 확인해야 합니다. kubelet은 API 서버보다 세 마이너까지 낮아도 되니 노드는 조금 늦어도 되지만 한없이 늦을 수는 없습니다. k3s도 같은 규칙을 따라 중간 마이너를 건너뛰지 않고 서버를 먼저, 에이전트를 나중에 올립니다.

마이너가 바뀔 때마다 예전에 deprecated로 표시된 API 버전도 없어집니다. API 서버에 물어서는 어떤 매니페스트가 그런 버전을 쓰는지 알 수 없습니다. API 서버가 요청한 버전으로 오브젝트를 변환해서 돌려주기 때문입니다. 그래서 Pluto나 kubent 같은 도구는 매니페스트와 Helm 릴리스를 직접 읽습니다.

[ZenML](https://status.zenml.io/incidents/bnrlb8tck3v0)은 2025년에 오래된 Kubernetes 버전과 AMI 이미지 타입으로 돌던 운영 EKS 클러스터를 올리면서 VPC와 EKS Terraform 모듈을 한꺼번에 바꿨습니다. 그 가운데 Terraform으로 KMS Secret 암호화를 켠 변경이 워커 노드의 IAM 권한을 지워 버렸고, 노드 그룹을 다시 만들 때까지 약 여덟 시간 동안 서비스가 멈췄습니다. 미뤄 둔 업그레이드가 하룻밤의 여러 변경으로 한꺼번에 왔다는 점이 이 클러스터가 피해야 할 모습입니다.

### 추천 점검 방법

지원 종료일 자체는 메트릭이 아니라 달력에 있는 사실입니다. 업그레이드 전에 지켜볼 것은 다음 마이너에서 없어지는 API를 아직 부르는 클라이언트가 있는지이고, API 서버의 `apiserver_requested_deprecated_apis`가 그것을 보여 줍니다. 시계열이 있으면 업그레이드 전에 고쳐야 할 클라이언트가 있다는 뜻입니다.

```
apiserver_requested_deprecated_apis{removed_release!=""}
```

이 시계열에 대한 알림 규칙은 이 클러스터에서 찾지 못했습니다. 업그레이드 직전에는 Pluto로 매니페스트와 Helm 릴리스를 다음 마이너 기준으로 한 번 더 읽어 보는 편이 좋습니다.

### 추천 해결 방안

이 규모에서는 날짜를 기다리지 말고 업그레이드를 달력에 넣는 방법을 권합니다. 한 번에 한 마이너씩, k3s가 새 마이너를 내놓고 몇 주 뒤에 올립니다. system-upgrade-controller의 Plan을 두고 릴리스 채널을 따르게 하면 서버를 먼저, 에이전트를 나중에 알아서 올립니다. 각 단계 전에는 Pluto로 다음 마이너에서 없어지는 API를 확인합니다. 얻는 것은 매번 작고 아는 단계로 올라가고 패치가 끊기지 않는다는 점입니다. 치르는 것은 자동 Plan이 묻지 않고 올리고, 그 Job이 노드에서 높은 권한으로 돈다는 점입니다. 컨트롤러는 지원되지 않는 버전 점프를 막아 주지 않으니 채널을 신중히 골라야 합니다. k3s에는 stable과 latest 말고도 Kubernetes 마이너마다 채널이 있습니다. 아래는 서버용 Plan의 모양을 보여 주는 예시입니다.

```yaml
apiVersion: upgrade.cattle.io/v1
kind: Plan
metadata:
  name: server-plan
  namespace: system-upgrade
spec:
  concurrency: 1
  cordon: true
  nodeSelector:
    matchExpressions:
      - { key: node-role.kubernetes.io/control-plane, operator: In, values: ["true"] }
  serviceAccountName: system-upgrade
  upgrade:
    image: rancher/k3s-upgrade
  channel: https://update.k3s.io/v1-release/channels/stable
```

적용할 때 조심할 것이 있습니다. 이 클러스터의 컨트롤 플레인 노드는 `node-b` 하나라서, 서버를 올리는 동안 API 서버와 etcd가 멈춥니다. 그동안 이미 떠 있는 파드는 계속 돌지만 새 배포, 스케일링, 재스케줄링은 되지 않습니다. `cordon: true`는 새 파드가 그 노드에 스케줄링되지 않게 막을 뿐 떠 있는 파드를 내보내지는 않습니다. 하지만 2026-11-14에 `node-b`에서 컨테이너 98개가 한꺼번에 다시 시작한 것처럼, k3s를 다시 시작하면 그 노드의 데이터베이스와 `app-g-minio`, Prometheus가 함께 다시 시작할 수 있습니다. 여기에 drain까지 켜면 `nodeSelector` 때문에 `node-b`에 고정된 이 워크로드들은 갈 곳이 없어 Pending으로 남습니다. 올리기 전에 1번 문제의 etcd 스냅샷이 클러스터 밖에 있는지 먼저 확인하는 편이 좋습니다.

k3s 자체는 Argo CD나 Helm이 관리하는 대상이 아니라 노드에 설치된 바이너리입니다. 버전을 바꾸는 곳은 각 노드의 k3s 설치이거나, system-upgrade-controller를 쓴다면 그 Plan입니다.

규모가 커지면 업그레이드를 적어 두고 연습한 절차로 만드는 편이 좋습니다. 릴리스 노트를 읽고, CI에서 없어지는 API를 찾고, 운영이 아닌 클러스터를 먼저 올린 뒤 컨트롤 플레인, 애드온, 노드 순서로 올립니다. 여러 마이너를 한꺼번에 넘어야 한다면 목표 버전으로 새 클러스터를 만들어 워크로드를 옮기는 방법도 견주어 봅니다.

### 근거

| 항목 | 값 | 출처 |
|---|---|---|
| 서버 버전 | `v1.33.5+k3s1` | inventory.json |
| 노드 버전 | 2대 모두 `v1.33.5+k3s1` | inventory.json |
| upstream 지원 종료일 | 2026-06-28, 140일 지남 | inventory.json |
| 1.34에서 없어지는 API를 쓰는 매니페스트 | 없음 | tools/pluto.json, tools/kubent.json |
| deprecated API 호출 | `endpoints` `v1` 1줄 | metrics/apiserver_requested_deprecated_apis.json |
| 컨트롤 플레인 노드 | `node-b` 1대 | objects/nodes.json |

### 더 읽을 것

- [Kubernetes: Patch Releases](https://kubernetes.io/releases/patch-releases/): 마이너 버전의 지원 기간, 유지보수 기간에 고치는 것, 릴리스마다의 지원 종료일이 있습니다.
- [k3s: Automated Upgrades](https://docs.k3s.io/upgrades/automated): Plan이 k3s 클러스터를 노드마다 어떻게 올리는지, 컨트롤러가 무엇을 막아 주지 않는지 설명합니다.
- [Amazon EKS best practices: Cluster Upgrades](https://docs.aws.amazon.com/eks/latest/best-practices/cluster-upgrades.html): EKS 문서지만 제자리 업그레이드의 순서와 없어지는 API를 미리 찾는 도구는 k3s에도 그대로 쓸 수 있습니다.
- [Amazon EKS: Understand the Kubernetes version lifecycle on EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html): 관리형 플랫폼의 지원 일정이 upstream과 어떻게 다른지 보여 줍니다.

## 5. app-g-minio의 메모리가 limit에 닿기 직전

**고른 이유.** 요청이 조금만 늘어도 커널이 MinIO 프로세스를 OOMKilled로 끝내고, 레플리카가 하나뿐이라 그동안 `app-g-api`의 오브젝트 저장소가 통째로 멈춥니다.

### 무슨 일인가

`app-g-api` 네임스페이스의 StatefulSet `app-g-minio`는 레플리카 하나(`app-g-minio-0`)로 돌고, 컨테이너 `minio`의 메모리 limit은 `512Mi`, request는 `128Mi`입니다. 지난 7일 동안 working set 메모리의 p95가 약 486.8MiB로, limit의 95%였습니다. limit까지 남은 여유가 5%뿐이라 부하가 조금만 늘어도 닿습니다. 다만 지난 7일 안에 이 컨테이너가 OOM으로 죽은 기록은 Prometheus에 없습니다.

KRR이 지난 기록으로 계산한 권장 memory request는 약 582MB입니다. 이 파드는 `node-b` 노드에 `nodeSelector` `storage: node-b` 때문에 그 노드에 고정돼 있고, 데이터는 `app-g-minio-data` 볼륨에 있습니다.

### 왜 생기나

limit이 MinIO가 실제로 쓰는 양보다 낮게 잡혀 있는 것으로 보입니다. 7일 그래프가 계단처럼 오르기만 하는 모양이면 메모리 누수일 수 있는데, 이번 점검에서는 p95 한 값만 봤기 때문에 어느 쪽인지는 알 수 없습니다. `container_memory_working_set_bytes`의 7일 그래프를 보면 구분할 수 있습니다.

메모리 limit은 컨테이너 cgroup의 메모리 한도가 되고 커널이 이를 지킵니다. CPU는 limit을 넘으면 느려질 뿐이지만 메모리는 다릅니다. 컨테이너가 limit보다 많이 할당하려 하면 커널의 out-of-memory 처리가 컨테이너 안의 프로세스 하나를 끝냅니다. 그것이 PID 1이면 kubelet이 컨테이너를 다시 시작합니다. 파드는 남아 있고, 마지막 상태에 `OOMKilled`와 종료 코드 137이 남고, 재시작 횟수가 하나 늘어납니다. 그 프로세스가 처리하던 요청은 사라지고, 컨테이너가 다시 Ready가 될 때까지 레플리카가 하나 줄어듭니다. 레플리카가 하나뿐인 `app-g-minio`에서는 그 시간 동안 서비스가 없습니다.

limit은 모든 레플리카에 같은 값이고, 같은 워크로드의 레플리카는 같은 부하를 받습니다. 한 레플리카를 limit 너머로 미는 부하는 모두를 밀기 때문에 함께 죽고 같은 부하 속으로 다시 올라옵니다. 지난 사용량으로 정한 limit이 부하가 튀는 순간 느려짐이 아니라 중단으로 바뀌는 이유가 이것입니다.

request도 중요합니다. request보다 많이 쓰는 컨테이너는 노드에 메모리 압박이 생기면 eviction 후보가 됩니다. 지금 `app-g-minio`는 request `128Mi`에 실제로는 그 네 배 가까이를 쓰고 있어서, 노드가 압박을 받으면 먼저 내보내질 수 있습니다. 모든 컨테이너의 request와 limit이 같은 파드는 Guaranteed 등급이 되어 가장 나중에 내보내집니다.

[Zalando](https://github.com/zalando-incubator/kubernetes-on-aws/blob/dev/docs/postmortems/jan-2019-dns-outage.md)는 2019년에 하류 서비스의 타임아웃 때문에 클라이언트가 재시도를 쏟아냈고, 그 요청이 DNS 질의로 몰리면서 CoreDNS 파드들이 메모리 limit `100Mi`에 닿아 한꺼번에 OOMKilled 됐습니다. 같은 부하 속에서 계속 죽어 클러스터에 DNS가 아예 없었고, 쇼핑몰은 한 시간 넘게 높은 오류율을 보였습니다. 당직 엔지니어가 request와 limit을 손으로 `2000Mi`로 올려서 끝났습니다. 지난 사용량으로 정한 limit 하나가 부하가 튀는 순간 서비스 전체를 멈췄다는 점이 이 클러스터와 같습니다.

### 추천 점검 방법

죽기 전의 신호는 컨테이너마다 7일 p95 working set을 limit으로 나눈 값입니다. 0.9를 넘으면 다음 부하 증가가 재시작입니다.

```
quantile_over_time(0.95, container_memory_working_set_bytes{container!=""}[7d:15m])
  / on (namespace, pod, container) kube_pod_container_resource_limits{resource="memory"}
```

죽은 뒤의 신호는 최근 한 시간 안에 재시작했고 마지막 종료 이유가 `OOMKilled`인 컨테이너입니다. 이 클러스터에는 `KubePodCrashLooping`은 있지만 OOMKilled만 따로 알리는 규칙은 찾지 못했으니 아래 모양으로 새로 만드는 편이 좋습니다.

```yaml
- alert: ContainerOOMKilled
  expr: |
    increase(kube_pod_container_status_restarts_total[1h]) > 0
    and on (namespace, pod, container)
    kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1
```

### 추천 해결 방안

이 규모에서는 권장값을 읽고 매니페스트에 새 limit을 손으로 적는 방법을 권합니다. KRR은 이미 있는 Prometheus를 내 컴퓨터에서 읽어 권장값을 내는 도구로, 지난 사용량의 최댓값에 여유를 더해 권장값을 냅니다. 이번 점검의 KRR 권장값은 약 582MB이니, limit을 그 위로 올리고 이 저장소가 내보내지면 안 된다면 request도 같은 값으로 올려 Guaranteed로 두는 편이 좋습니다. 얻는 것은 클러스터에 아무것도 설치하지 않고 바로 고친다는 점이고, 치르는 것은 워크로드가 바뀔 때마다 다시 해야 하는 수작업이고 누수가 있다면 그것까지 정상 수요로 잡는다는 점입니다. 아래는 모양을 보여 주는 예시입니다.

```yaml
resources:
  requests:
    memory: 768Mi
  limits:
    memory: 768Mi
```

적용할 때 조심할 것이 있습니다. resources를 바꾸면 StatefulSet의 파드 템플릿이 바뀌어 `app-g-minio-0`이 다시 만들어지고, 레플리카가 하나라서 그동안 MinIO가 멈춥니다. 파드는 `nodeSelector` 때문에 `node-b`로만 갈 수 있으니, request를 올리면 `node-b`에 그만큼 여유가 있어야 스케줄링됩니다. 이 StatefulSet은 Argo CD 앱 `app-g-api`가 `https://github.com/example-org/k8s-manifests` 저장소의 `prod/app-g-api` 경로에서 관리하고 selfHeal이 켜져 있어서, 클러스터에서 직접 고치면 되돌아갑니다. 그 경로에서 바꿔야 합니다.

규모가 커지면 Vertical Pod Autoscaler를 설치해 워크로드마다 `updateMode: "Off"`인 VerticalPodAutoscaler를 두는 편이 좋습니다. 아무것도 바꾸지 않고 권장값만 상태에 계속 갱신해 주니, 누가 도구를 돌리지 않아도 최신 권장값이 있습니다.

### 근거

| 항목 | 값 | 출처 |
|---|---|---|
| 7일 p95 working set / limit | 0.95 | metrics/memory_limit_p95_ratio_7d.json |
| 7일 p95 working set | 약 486.8MiB | metrics/memory_p95_7d_bytes.json |
| 메모리 limit과 request | `512Mi`, `128Mi` | objects/statefulsets.apps.json |
| KRR 권장 memory request | 약 582MB | tools/krr.json |
| 레플리카 | 1개 | objects/statefulsets.apps.json |
| 노드 고정 | `nodeSelector` `storage: node-b` | objects/statefulsets.apps.json |

### 더 읽을 것

- [Kubernetes: Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/): request와 limit이 어떻게 지켜지는지, 메모리 limit에서 끝나는 컨테이너의 예가 있습니다.
- [Zalando: January 2019 cluster DNS outage postmortem](https://github.com/zalando-incubator/kubernetes-on-aws/blob/dev/docs/postmortems/jan-2019-dns-outage.md): `100Mi` limit 하나가 클러스터 전체를 멈춘 과정과 원인이 정리돼 있습니다.
- [Robusta KRR](https://github.com/robusta-dev/krr): 클러스터에 아무것도 두지 않는 권장 도구이고, 기본값이 Vertical Pod Autoscaler와 어떻게 다른지 설명합니다.
- [Kubernetes: Vertical Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/vertical-pod-autoscale/): 구성 요소와 권장값의 근거, 업데이트 모드마다 실행 중인 파드에 무엇을 하는지 설명합니다.

## 그다음으로 큰 문제

- **Alertmanager 알림 일부가 전달되지 않음.** 지난 24시간 동안 보낸 알림 60건 가운데 8건이 수신처에 닿지 못했습니다. 기본 수신처는 `discord`이고 slack 연동 방식으로 보냅니다. 장애가 났을 때 알림이 오지 않을 수 있습니다. 심각도는 high입니다.
- **tempo가 7일 안에 OOM으로 죽음.** `monitoring/tempo`의 파드 하나가 지난 7일 안에 OOMKilled로 끝났고, 그 파드는 이미 교체됐지만 교체 전까지 163번 재시작했습니다. `app-ac-prod/app-ac-ai`도 같은 기간에 OOM으로 한 번 끝났습니다. 심각도는 high입니다.
- **CPU limit 때문에 하루 내내 스로틀링되는 컨테이너.** `prometheus`, `elasticsearch`, `fluent-bit`, `app-g-postgres`, `app-h-api-server` 등 컨테이너 여덟 곳이 지난 24시간 동안 CPU 주기의 4분의 1 넘게 멈춰 있었습니다. 평균 사용량은 낮아 보여도 응답이 늦어집니다. 심각도는 high입니다.

## 지난 리포트 이후

비교할 이전 점검이 없어서 이번 점검이 수집한 것만 봤습니다.

## 다가오는 일

| 언제 | 무엇 | 출처 |
|---|---|---|
| 2026-12-14 무렵 | `node-a` 노드의 루트 파일시스템이 지난 7일 추세대로라면 약 29일 뒤에 가득 찹니다. | storage.local-path-fs-near-full (summary.json) |

## 영역별 한 줄

| 영역 | 무엇 |
|---|---|
| 리소스 | CPU limit에 걸려 하루 내내 스로틀링되는 컨테이너가 여럿이고, `app-g-minio`는 메모리가 limit에 거의 닿아 있습니다. |
| 스케일링 | 15일 대부분을 최소 레플리카에 머문 HPA와 자주 흔들린 HPA가 있습니다. |
| 모니터링 | Prometheus가 emptyDir에 데이터를 두고 있고, Alertmanager 알림 일부가 전달되지 않았습니다. |
| 트래픽 | CoreDNS가 한 노드에만 떠 있고, 데이터베이스나 메시지 큐 포트가 외부 주소에 열려 있다는 지적이 있습니다. |
| 가용성 | 데이터베이스 덤프와 etcd 스냅샷이 모두 클러스터 안의 `node-a` 노드에만 있고, 클러스터 밖 사본이 없습니다. |
| 설정 관리 | prune이 켜진 Argo CD 앱이 Namespace와 CRD를 관리하고 있어서 Git에서 매니페스트가 빠지면 통째로 지워집니다. |
| 스토리지 | `node-a` 노드의 루트 파일시스템 여유가 줄고 있어 약 29일 뒤에 가득 찰 추세입니다. |
| 보안 | NetworkPolicy가 없는 네임스페이스, 권한이 큰 컨테이너, 클러스터 전체 Secret을 읽을 수 있는 서비스 어카운트가 있습니다. |
| 비용 | 이 클러스터는 직접 운영하는 노드라서 비용 점검은 하지 않았습니다. |
| 멀티테넌시 | 운영 네임스페이스에 ResourceQuota가 없어서 한 서비스가 노드 자원을 다 쓸 수 있습니다. |
| 노드 OS | 노드에 접속하지 않기로 해서 노드 안쪽은 읽지 못했고, swap이 켜진 노드가 있다는 것만 메트릭으로 확인했습니다. |
| 플랫폼 | Kubernetes 1.33의 지원이 끝난 지 140일이 지났습니다. |

## 이번 점검의 한계

**클러스터에 데이터가 없어서 판단하지 못한 것**

- 없음

**kubegap이 아직 읽지 못하는 것**

- 컴포넌트 13개는 오브젝트와 메트릭으로만 읽었습니다. kubegap에 전용 점검 항목이 없습니다: actions-runner-controller, elasticsearch-opensearch, fluent-bit, fluent-bit-events, ingress-nginx, istio, kube-state-metrics, metrics-server, node-exporter, opentelemetry-collector, prometheus-operator, reloader, tempo-jaeger.
  - 약해지는 결론: 이 컴포넌트 안에서 생긴 이상은 이 리포트에 나오지 않습니다.
- 수집이 자체 제한에 걸려 일부만 읽은 것이 있습니다: `core.component-logs` (argocd: argocd/argocd-application-controller, argocd: argocd/argocd-applicationset-controller, argocd: argocd/argocd-notifications-controller, argocd: argocd/argocd-repo-server, coredns: kube-system/coredns, external-secrets: external-secrets/external-secrets, fluent-bit: logging/fluent-bit, ingress-nginx: ingress-nginx/nginx-ingress-ingress-nginx-controller, istio: istio-system/istiod, metallb: metallb-system/speaker, tempo-jaeger: monitoring/tempo).
  - 약해지는 결론: 여기에서 센 숫자는 실제보다 적을 수 있고, 하루 가운데 앞쪽 로그나 목록의 나머지는 이 리포트에 없습니다.

**첫 실행 질문에서 읽지 않기로 답하신 것**

- 노드 점검.
  - 답하면 더 보는 것: full 점검에서 노드 점검 항목이 최대 26개 늘어납니다. Prometheus가 긁지 않는 컴포넌트 메트릭도 노드 쪽에서 읽습니다.
  - 보려면: `/kubegap setup`에서 다시 고를 수 있습니다.

## 숫자

심각도는 운영 규모 소형 기준입니다.

비교할 이전 full 점검이 없습니다.

| 심각도 | fail | warn |
|---|---|---|
| critical | 0 | 2 |
| high | 14 | 21 |
| medium | 92 | 173 |
| low | 13 | 115 |

항목별 체크:

- 두 노드에서 컨테이너가 한꺼번에 다시 시작됨: `logs.signatures.prometheus.wal-corrupt`
- 백업이 클러스터 밖에 없음: `resilience.no-backup.cluster`, `resilience.backup-same-node.*`
- Prometheus 데이터가 emptyDir에 있음: `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus`
- prune이 켜진 Argo CD 앱이 Namespace와 CRD를 관리함: `argocd.prune-manages-namespace-or-crd.cluster`
- Kubernetes 1.33의 지원 종료: `platform.k8s-version-eol.cluster`
- app-g-minio의 메모리가 limit에 닿기 직전: `resources.memory-limit-near-p95.app-g-api/sts/app-g-minio:minio`

자세한 내용과 모든 표: [`report-details.md`](report-details.md) · kubegap 0.2.0, rubric 0.1.94 · 수집 자료 `~/.kubegap/snapshots/<context>/2026-11-15T01-25-29`
