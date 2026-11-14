# app-u-cluster-eks — full 점검, 2026-11-15 01:51

지금 깨져 있는 것: 없음

가장 큰 문제 5개: ① 운영 데이터베이스 일곱 개의 백업이 없음 ② 인터넷에 열린 Kafka 포트와 데이터베이스 포트 ③ 인터넷 전체에 열린 클러스터 API 엔드포인트 ④ 매니페스트에 평문으로 적힌 Neo4j 인증 값 ⑤ 지원이 끝난 Kubernetes 1.32와 따라가지 못한 Karpenter

이미 일어난 일: Prometheus가 메모리 한도를 넘어 재시작됨 · 운영 파드 스케줄링이 하루 동안 91번 실패함

운영 규모: 중형

## 클러스터 한눈에

| 항목 | 값 |
|---|---|
| 노드 | 9대 중 Ready 9대 |
| 파드 | 실행 131, 대기 0, 실패 0 |
| 네임스페이스 | 21개, 프로덕션 8개 |
| 컴포넌트 | 23: actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| 메트릭·로그 저장소 | prometheus 2.49.1 / loki 2.6.1 |
| Kubernetes | v1.32.13-eks-577a51e (eks) |

## 이미 일어난 일

비교할 이전 점검이 없어서 이번 점검이 수집한 것만 봤습니다.

### Prometheus가 메모리 한도를 넘어 재시작됨

2026-11-14 14:34 UTC에 `monitoring` 네임스페이스의 `prometheus-kube-prometheus-stack-prometheus-0` 파드에서 `prometheus` 컨테이너가 OOMKilled(exit code 137)로 끝났습니다. 컨테이너가 메모리 limit을 넘어서 커널이 그 컨테이너만 죽인 것입니다. 이 파드는 2026-09-08에 만들어진 뒤로 이 컨테이너가 세 번 재시작됐고, 지난 7일 동안 OOM으로 끝난 것은 이번 한 번입니다. 지금은 다시 떠 있으니 끝난 일입니다. 다만 재시작하는 동안에는 메트릭 수집과 알림 규칙 평가가 멈췄습니다.

왜 메모리가 모자랐는지는 이번 점검으로 단정할 수 없습니다. 이 파드가 도는 노드는 SSM에 등록되지 않아 커널 로그를 읽지 못했고, Prometheus 메트릭으로 OOM 사실만 확인했습니다. Prometheus의 메모리 사용은 시계열 수에 따라 늘어나는데, 지금 활성 시계열은 178,024개이고 메모리가 한도에 가깝다는 경고도 따로 나왔습니다. 메모리 limit이 지금 시계열 수에 비해 작은 것으로 추정합니다.

이 일로 그다음으로 큰 문제에 적은 'OOMKill을 알리는 알림 규칙이 없음'과 'CPU 스로틀링에 걸린 Prometheus'가 드러났습니다. 컨테이너가 OOM으로 죽어도 이 클러스터에는 그것을 알리는 규칙이 없어서, 이번 재시작도 알림으로 전해지지 않았을 것으로 봅니다.

### 운영 파드 스케줄링이 하루 동안 91번 실패함

지난 24시간 동안 컨트롤 플레인 로그에 "Unable to schedule pod; no fit"이 91번 남았습니다. 워크로드별로는 `prod-app-x/app-x-api`가 39번, `prod-app-z-backend/app-z-backend`와 `prod-app-z-backend/app-z-embedding-server`가 각각 26번입니다. 파드가 결국 노드를 얻었는지, 얼마나 기다렸는지는 이 로그만으로는 알 수 없습니다. 지금 Pending인 파드가 남아 있다는 근거는 찾지 못했으니 이어지고 있는지는 알 수 없는 상태로 둡니다.

실패 이유를 샘플 15건으로 보면 거의 모두에 CPU 부족과 node affinity/selector 불일치가 함께 나오고, 5건에는 메모리 부족도 나옵니다. 그와 함께 `karpenter.sh/disruption: disrupting`, `node.kubernetes.io/not-ready`, `node.cloudprovider.kubernetes.io/uninitialized` taint가 붙은 노드가 있었습니다. Karpenter가 노드를 정리하거나 스팟 노드가 회수되는 동안 남은 노드에 CPU 여유가 없었고, 새 노드가 준비되기 전에 파드가 스케줄링을 기다린 것으로 추정합니다. 로그 서명에도 스팟 회수가 잡혔습니다. Karpenter 0.37.0이 이 클러스터의 Kubernetes 버전을 지원하지 않는다는 점이 이 지연에 얼마나 작용했는지는 알 수 없습니다.

이 일로 5번 문제(지원이 끝난 Kubernetes 1.32와 따라가지 못한 Karpenter)가 드러났습니다. 새 노드를 만드는 Karpenter가 지원 범위 밖에서 돌고 있어서, 노드가 빨리 채워져야 하는 순간에 무엇이 어긋나도 이상하지 않은 상태입니다.

## 1. 운영 데이터베이스 일곱 개의 백업이 없음

**고른 이유.** PVC를 실수로 지우거나 데이터가 깨지거나 누군가 볼륨을 지우면 운영 데이터베이스 일곱 개의 데이터를 되살릴 방법이 없습니다.

### 무슨 일인가

이 클러스터에는 PVC를 쓰는 데이터베이스 StatefulSet이 여덟 개 있고, 그중 일곱 개가 운영 네임스페이스에 있습니다. `prod-app-t/app-t-backend-postgresql`, `prod-app-x/app-x-postgresql`, `prod-app-s/app-s-backend-mysql`, `prod-app-y/app-y-backend-mysql`, `prod-app-z-backend/app-z-neo4j`, `prod-app-r/app-r-postgresql`, `prod-app-v/app-v-backend-prod-mysql`입니다. 이 일곱 개 모두에 백업을 만드는 수단을 찾지 못했습니다.

클러스터 안에는 Velero 같은 백업 도구가 없고, 지난 7일 동안 돈 백업 CronJob도 0개이며, VolumeSnapshot은 CRD조차 설치돼 있지 않습니다. AWS 계정 쪽도 같습니다. EBS 스냅샷을 자동으로 만드는 Data Lifecycle Manager 정책이 0개이고 AWS Backup 계획도 0개입니다. 지난 30일 동안 만들어진 EBS 스냅샷은 2개인데, 설명이 "pre-delete backup of dev-app-v/…", "pre-delete backup of dev-app-y/…"인 개발 환경 볼륨을 지우기 전에 손으로 뜬 것입니다. 운영 볼륨의 스냅샷은 없습니다.

여기에 한 가지가 더 겹칩니다. 운영 데이터베이스 PVC 일곱 개가 모두 기본 StorageClass `gp3`를 쓰고, 이 StorageClass의 reclaimPolicy가 `Delete`입니다. PVC를 지우면 그 뒤의 EBS 볼륨도 함께 지워진다는 뜻입니다.

이 판단은 클러스터와 AWS 계정 안에서 본 것에 한정됩니다. 데이터베이스 안의 기능이나 클러스터 밖의 서버가 덤프를 받아 가고 있는지는 이번 점검으로는 알 수 없습니다.

### 왜 생기나

이 클러스터의 데이터베이스는 전부 Helm 차트로 올린 StatefulSet이고 데이터는 EBS 볼륨에 있습니다. EBS 볼륨은 노드가 아니라 가용 영역의 스토리지에 있어서 노드가 죽어도 남습니다. 그래서 따로 챙기지 않아도 안전하다고 느끼기 쉽고, 차트도 기본으로는 백업을 만들지 않습니다. 이 클러스터에서 백업이 빠진 이유가 그것인지는 클러스터에 남아 있지 않아 알 수 없습니다. 개발 볼륨을 지우기 전에는 손으로 스냅샷을 떴으니, 스냅샷을 뜨는 방법 자체는 알고 있다고 봅니다.

백업이 무엇을 막아 주는지는 사본이 어디에 있는지가 정합니다. 원본과 같은 디스크에 있는 사본은 실수로 지운 데이터만 되살려 주고, 디스크가 고장 나면 함께 사라집니다. 같은 클러스터의 다른 노드에 있는 사본은 노드 고장까지는 견딥니다. 하지만 클러스터 전체에 닿는 일은 견디지 못합니다. 클러스터 권한을 가진 공격자나 잘못된 스크립트가 볼륨을 지우는 경우, 네임스페이스가 안의 것과 함께 통째로 지워지는 경우가 그렇습니다. 이런 일에는 사본도 원본과 함께 사라집니다. 이 클러스터는 그 첫 단계인 사본조차 없습니다. EBS 볼륨이 노드 고장을 견디는 것은 사본이 있어서가 아니라 스토리지가 노드와 떨어져 있어서이고, 지우는 일이나 데이터가 깨지는 일에는 아무것도 남지 않습니다.

그래서 오래 쓰여 온 기준이 3-2-1입니다. 중요한 데이터는 원본과 백업 둘을 합해 사본 세 개를 두고, 서로 다른 두 종류의 저장소에 나눠 두고, 그중 하나는 다른 장소에 둡니다. Kubernetes 자체는 이 바깥 사본을 만들어 주지 않습니다. VolumeSnapshot은 CSI 드라이버가 스토리지에 뜨는 특정 시점의 사본인데, 삭제 정책이 Delete이면 VolumeSnapshot 오브젝트를 지울 때 실제 스냅샷도 함께 지워집니다. 그러니 스냅샷을 뜨는 것과 별개로 그것을 어디에 얼마나 남길지도 정해야 합니다.

마지막으로 모든 백업에 해당하는 것이 하나 있습니다. 복원해 보지 않은 백업은 있다고 볼 수 없습니다. 매일 밤 덤프 파일이 생긴다는 것은 작업이 돌았다는 뜻이지, 그 파일로 데이터베이스가 살아난다는 뜻이 아닙니다.

[GitLab](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/)은 2017년에 엔지니어가 운영 데이터베이스의 데이터 디렉터리를 실수로 지웠습니다. 매일 밤 돌던 `pg_dump` 백업은 버전이 맞지 않아 계속 실패하고 있었고, 실패를 알리는 메일은 거부되고 있었으며, S3 버킷은 비어 있었습니다. 결국 여섯 시간 전에 손으로 떠 둔 LVM 스냅샷으로 복구했습니다. 백업이 있다고 믿었지만 아무도 그것을 확인하지 않았다는 점이 이 클러스터와 같습니다. 이 클러스터는 거기서 한 걸음 더 나가 손으로 뜬 운영 스냅샷도 없습니다.

[InfluxData](https://www.influxdata.com/blog/deleting-production-steps-how-fix-it/)에서는 Argo CD 설정의 이름 충돌 때문에 Argo CD가 운영 환경 하나를 통째로 지웠습니다. 볼륨의 reclaimPolicy가 `Retain`이어서 데이터는 남았고, Kubernetes 오브젝트는 손으로 다시 만들었습니다. 이 클러스터도 운영 애플리케이션을 Argo CD가 selfHeal을 켠 채로 관리하는데, 데이터베이스 PVC의 reclaimPolicy는 `Delete`입니다. 같은 일이 생기면 볼륨까지 함께 사라집니다.

### 추천 점검 방법

백업은 "만들어졌는가", "클러스터 밖으로 나갔는가", "되살아나는가"를 따로 봐야 합니다.

만들어졌는지는 백업 작업의 마지막 성공 시각으로 봅니다. 백업을 CronJob으로 만든다면 kube-state-metrics가 내보내는 `kube_cronjob_status_last_successful_time`으로, 정한 주기보다 오래 성공하지 못한 백업을 알리는 규칙을 둘 수 있습니다. 지금 이 클러스터에는 백업 작업이 없으니 이런 규칙도 백업을 만들면서 함께 만들어야 합니다.

```yaml
- alert: BackupCronJobStale
  expr: time() - kube_cronjob_status_last_successful_time{cronjob=~".*backup.*"} > 86400 * 1.5
  for: 30m
```

클러스터 밖으로 나갔는지는 내보내는 쪽이 남기는 결과로 봅니다. Velero를 쓰면 백업 하나하나가 오브젝트로 남고, AWS Backup이나 Data Lifecycle Manager를 쓰면 볼륨별 최신 스냅샷 시각을 AWS 쪽에서 볼 수 있습니다.

되살아나는지는 메트릭으로는 알 수 없습니다. 정해진 주기로 백업 하나를 빈 데이터베이스나 별도 클러스터에 복원해 보고 몇몇 테이블의 행 수를 비교하는 수밖에 없습니다.

### 추천 해결 방안

이 클러스터는 운영 담당자가 있고 실제 사용자가 쓰는 서비스가 올라가 있는 중형 규모로 봤습니다. 이 규모에서는 Kubernetes 오브젝트와 볼륨을 함께 백업하는 Velero를 Schedule로 돌리고, 백업을 다른 계정이나 다른 리전의 오브젝트 스토리지에 두는 방법을 권합니다. 여기에 EBS 볼륨용으로 AWS Backup 계획이나 Data Lifecycle Manager 정책을 하나 더하고, 스냅샷을 다른 리전으로 복사합니다. Data Lifecycle Manager는 태그를 기준으로 EBS 스냅샷을 정해진 주기로 뜨고 보존 기간이 지나면 지워 주는 AWS 기능이고, AWS Backup은 그것을 포함하는 더 넓은 서비스입니다.

이렇게 하면 오브젝트와 데이터를 함께 되살릴 수 있고, 복원이 연습해 둔 절차가 됩니다. 치르는 것도 있습니다. Velero는 돌리고 업그레이드해야 하는 구성 요소가 하나 늘어나는 것이고, 복원할 때 이미 있는 리소스는 따로 지시하지 않으면 건너뛰며, TTL을 정하지 않으면 백업이 30일 뒤에 만료됩니다. 스냅샷은 보존하는 만큼 저장 비용이 듭니다.

볼륨 스냅샷은 데이터베이스가 쓰는 중간에 뜨는 것이라, 데이터베이스가 정상적으로 다시 올라오긴 하지만 마지막 몇 개의 트랜잭션이 어떤 상태로 남을지는 데이터베이스에 달려 있습니다. 그래서 MySQL과 PostgreSQL은 스냅샷과 함께 `mysqldump`나 `pg_dump`로 논리 덤프를 하루 한 번 떠서 같은 오브젝트 스토리지로 보내는 편이 좋습니다. Neo4j도 자체 덤프 명령이 있습니다.

```yaml
# 모양을 보여 주는 예시입니다. 일정과 보존 기간, 대상 네임스페이스는 환경에 맞게 정합니다.
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: prod-daily
  namespace: velero
spec:
  schedule: "0 18 * * *"
  template:
    includedNamespaces: ["prod-*"]
    snapshotVolumes: true
    ttl: 720h
```

적용할 때 조심할 것이 셋 있습니다. 첫째, StorageClass `gp3`의 reclaimPolicy를 `Retain`으로 바꾸고 싶어도 StorageClass의 이 값은 이미 만들어진 PV에 적용되지 않습니다. 운영 PV 일곱 개는 PV 자체의 `persistentVolumeReclaimPolicy`를 따로 바꿔야 합니다. 둘째, 스냅샷을 뜨는 것 자체는 서비스를 멈추지 않지만 복원 연습을 운영 네임스페이스에 하면 지금 데이터를 덮어쓸 수 있으니 반드시 다른 네임스페이스나 다른 클러스터에서 합니다. 셋째, 데이터베이스 StatefulSet은 레플리카가 1개라서, 덤프를 뜨는 동안의 부하가 그대로 서비스에 걸립니다. 사용자가 적은 시간대로 일정을 정하는 편이 좋습니다.

백업 정책은 AWS 계정의 리소스라 클러스터 매니페스트에 들어가지 않습니다. 계정의 리소스를 관리하는 곳(Terraform 같은 IaC)에서 만드세요. Velero를 클러스터에 설치하는 것은 운영 애플리케이션을 관리하는 Argo CD 저장소 `https://github.com/example-org/iac`에 Application으로 더하면 다른 애플리케이션과 같은 방식으로 관리됩니다.

규모가 커지면 백업 저장소를 별도 AWS 계정에 두고 운영 계정의 권한으로는 지울 수 없게 막아 두는 편이 좋습니다. 클러스터 권한을 얻은 공격자가 백업까지 지우는 일을 막기 위해서입니다. 복원 연습도 분기마다 정기 일정으로 둡니다.

### 근거

| 항목 | 값 | 출처 |
|---|---|---|
| PVC를 쓰는 데이터베이스 StatefulSet | 8개, 그중 운영 7개 | resilience.backup.databases |
| 백업 CronJob | 0개 | resilience.backup |
| VolumeSnapshot, VolumeSnapshot CRD | 0개, CRD 없음 | storage.snapshots |
| Data Lifecycle Manager 정책, AWS Backup 계획 | 0개, 0개 | aws (eks.no-backup-policy) |
| 지난 30일 EBS 스냅샷 | 2개, 모두 개발 볼륨 삭제 전 수동 | storage.ebs.snapshot_descriptions |
| reclaimPolicy가 Delete인 운영 데이터베이스 PVC | 7개 | storage.pvcs.prod_db_delete_reclaim |
| 기본 StorageClass | `gp3`, reclaimPolicy Delete | storage.classes |

### 더 읽을 것

- [GitLab: Postmortem of database outage of January 31](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/): 백업이 있다고 믿는 것과 복원되는 것이 어떻게 다른지 보여 주는 기록입니다.
- [Velero: How Velero Works](https://velero.io/docs/main/how-velero-works/): 백업, Schedule, 복원이 각각 무엇을 하고 복원이 무엇을 건드리지 않는지 설명합니다.
- [restic: Preparing a new repository](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html): 덤프를 오브젝트 스토리지로 보낼 때 쓸 수 있는 저장소 종류와 비밀번호가 어떻게 쓰이는지 나옵니다.
- [k3s: etcd-snapshot](https://docs.k3s.io/cli/etcd-snapshot): k3s의 클러스터 상태 백업 방법입니다. 이 클러스터는 EKS라 직접 해당하지 않지만, 클러스터 상태를 복원하는 데 무엇이 필요한지 보여 줍니다.

## 2. 인터넷에 열린 Kafka 포트와 데이터베이스 포트

**고른 이유.** Kafka 브로커가 누구에게나 열려 있고 인증이 켜져 있는지는 알 수 없어서, 인증이 약하거나 꺼져 있으면 메시지를 읽고 쓰는 일이 인터넷 어디에서나 가능합니다.

### 무슨 일인가

두 곳에서 데이터를 다루는 포트가 인터넷 쪽 주소에 있습니다.

첫째는 `middleware` 네임스페이스의 Service `kafka-controller-0-external`입니다. type LoadBalancer이고 `aws-load-balancer-scheme: internet-facing` 어노테이션으로 인터넷용 NLB를 만들었습니다. 포트는 9094와 443이고, 로드밸런서의 보안 그룹이 9094 포트를 0.0.0.0/0에 열어 둡니다. `spec.loadBalancerSourceRanges`가 비어 있어서 컨트롤러가 기본값인 0.0.0.0/0을 쓴 것입니다. external-dns 어노테이션으로 `broker.lab-k.example`이라는 이름도 붙어 있습니다. 2025-12-17에 만들어졌습니다.

둘째는 Kubernetes 밖에서 만든 NLB `app-u-db-shared`입니다. 이 NLB도 internet-facing이고 3307, 3308, 3309, 3311, 5432, 5433, 6379, 7687 포트를 받습니다. TargetGroupBinding 일곱 개가 이 NLB를 `prod-app-t/app-t-backend-postgresql`, `prod-app-s/app-s-backend-mysql`, `prod-app-y/app-y-backend-mysql`, `prod-app-z-backend/app-z-neo4j`, `prod-app-z-backend/app-z-pg-proxy`, `dev-app-s/app-s-backend-mysql`과 그 밖의 Service 하나에 연결합니다. 대부분 데이터베이스 Service입니다. 이쪽은 보안 그룹이 포트마다 최대 네 개의 /32 주소만 허용하고, 6379 포트는 하나만 허용합니다. 그래서 누구에게나 열린 것은 아니지만 MySQL, PostgreSQL, Redis, Neo4j가 인터넷에서 닿는 주소 뒤에 있다는 점은 같습니다.

실제로 바깥에서 누가 연결을 시도했는지, Kafka 쪽에 SASL 같은 인증이 켜져 있는지는 이번 점검으로는 알 수 없습니다. 인증이 켜져 있다면 남은 방어는 그 인증 하나이고, 꺼져 있다면 지금도 인터넷에서 메시지를 읽고 쓸 수 있습니다.

### 왜 생기나

Kafka Service는 Helm 차트 `kafka-26.8.1`의 외부 접속 기능으로 만들어진 것으로 보입니다. Service에 `meta.helm.sh/release-name: kafka` 어노테이션이 있습니다. 클러스터 밖의 클라이언트가 브로커에 붙어야 해서 인터넷용으로 열었다고 추정하지만, 그 클라이언트가 어디에 있는지는 클러스터에 남아 있지 않습니다. `app-u-db-shared`는 개발자나 외부 도구가 데이터베이스에 직접 붙으려고 손으로 만든 것으로 보이고, 그래서 주소 목록으로 좁혀 둔 것입니다.

Service를 클러스터 밖에 여는 방법은 두 가지이고, 둘 다 이름보다 많은 것을 엽니다. type NodePort는 30000-32767 범위에서 포트를 하나 받고, 그 Service의 파드가 있든 없든 모든 노드가 그 포트를 Service로 넘깁니다. type LoadBalancer는 보통 NodePort Service로 시작하고, 클라우드 컨트롤러가 그 위에 외부 로드밸런서를 만들어 붙입니다.

누가 연결할 수 있는지는 Kubernetes 밖에서 정해집니다. AWS Load Balancer Controller는 어노테이션에 internet-facing이라고 쓰지 않으면 internal로 만듭니다. 허용하는 출처는 `spec.loadBalancerSourceRanges`이고, 아무것도 적지 않으면 0.0.0.0/0을 씁니다. 컨트롤러는 이 범위를 허용하는 보안 그룹을 로드밸런서에 만들어 붙입니다. 보안 그룹 없이 만든 NLB는 모든 클라이언트 트래픽을 리스너로 넘기고, 나중에 보안 그룹을 붙일 수도 없습니다.

HTTP 서비스라면 이것이 원래 의도한 상태입니다. 하지만 PostgreSQL, MySQL, Redis, Kafka라면 데이터베이스의 리스너가 인터넷에 있고, 낯선 사람과 데이터 사이에 남은 것은 데이터베이스 자체의 인증뿐이라는 뜻입니다. 클러스터 안에서는 이 상태가 아무 데서도 드러나지 않습니다. Service는 정상이고 애플리케이션도 잘 동작합니다. 주소 목록으로 좁혀 둔 `app-u-db-shared`는 그보다 낫지만 내부망에 있는 것과는 다릅니다. 인터넷에서 닿는 주소 앞에 데이터베이스를 둔다는 것은 목록을 고칠 때마다 그 목록이 틀리지 않아야 한다는 뜻입니다.

### 추천 점검 방법

로드밸런서의 보안 그룹이 무엇을 막았는지는 CloudWatch의 `SecurityGroupBlockedFlowCount_Inbound` 메트릭으로 볼 수 있습니다. 보안 그룹이 막은 흐름의 수라서, 막힌 트래픽이 나오는 유일한 곳입니다. Kafka를 주소 목록으로 좁힌 뒤에는 이 값으로 낯선 주소가 얼마나 두드리는지 보입니다.

```text
CloudWatch SecurityGroupBlockedFlowCount_Inbound (Network Load Balancer), statistic Sum
```

누가 실제로 붙었는지는 VPC 흐름 로그를 로드밸런서의 ENI와 목적지 포트로 걸러서 봅니다. 출처 주소가 나오므로 9094나 5432에 허용 목록 밖의 주소가 붙었는지 알 수 있습니다.

노출 자체는 시계열이 아니라 오브젝트의 성질이라, 새로 생기는 것은 목록으로 확인합니다.

```bash
kubectl get svc -A -o wide | grep LoadBalancer
```

### 추천 해결 방안

이 규모에서는 데이터베이스와 Kafka 앞의 로드밸런서를 internal로 만들고, 바깥에서 붙어야 하는 사람과 시스템은 VPN이나 피어링한 네트워크로 들어오게 하는 방법을 권합니다. 매니페스트에는 기본값에 기대지 말고 scheme을 명시하고, 허용할 클라이언트 범위를 `spec.loadBalancerSourceRanges`에 적습니다. NLB는 처음부터 보안 그룹을 붙여 만들고, 위의 막힌 흐름 메트릭과 흐름 로그를 봅니다.

이렇게 하면 주소 자체가 인터넷에서 라우팅되지 않고, 주소 목록은 유일한 방어가 아니라 두 번째 방어가 됩니다. 치르는 것은 모든 클라이언트에게 VPC로 들어오는 길이 필요하다는 점이고, 보안 그룹 없이 만든 NLB는 다시 만들어야 보안 그룹을 붙일 수 있다는 점입니다.

```yaml
# 모양을 보여 주는 예시입니다. 허용 범위는 실제 클라이언트 범위로 정합니다.
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internal"
spec:
  type: LoadBalancer
  loadBalancerSourceRanges:
    - <ip>/8
```

Kafka 브로커를 바로 internal로 바꾸기 어렵다면 그 전에 `loadBalancerSourceRanges`에 실제 클라이언트 주소만 적어서 0.0.0.0/0을 닫는 것이 먼저입니다.

적용할 때 조심할 것이 있습니다. NLB의 scheme은 바꿀 수 없어서, internal로 바꾸면 컨트롤러가 기존 NLB를 지우고 새로 만듭니다. 주소가 바뀌므로 `broker.lab-k.example`을 쓰는 클라이언트는 external-dns가 레코드를 바꿀 때까지 연결이 끊기고, Kafka 클라이언트는 브로커가 알려 주는 advertised listener 주소로 다시 붙으므로 그 설정도 새 주소에 맞아야 합니다. 바깥 클라이언트가 VPN으로 들어올 길을 먼저 만든 뒤에 바꾸세요. 이 Service는 443 포트도 9094와 같은 대상으로 넘기므로, 출처 범위를 좁히면 443을 쓰는 클라이언트도 막힙니다. 그리고 `kafka-controller`는 레플리카가 1개라서 Helm 값을 바꿔 파드가 다시 뜨는 동안 브로커가 멈춥니다. `app-u-db-shared`는 개발 데이터베이스 하나를 포함해 일곱 개의 Service가 걸려 있어서, 누가 실제로 쓰는지 흐름 로그로 먼저 확인하는 편이 좋습니다.

`kafka-controller-0-external`은 Service에 Helm 릴리스 `kafka`의 어노테이션이 있으니 그 릴리스의 values에서 외부 접속 설정을 바꾸세요. 이 Service가 Argo CD Application에 들어 있다는 표시는 클러스터에 없습니다. `app-u-db-shared`는 Kubernetes 밖에서 만든 NLB라서 클러스터에 선언한 곳이 없습니다. 이 NLB를 만든 곳(콘솔이나 IaC)에서 바꾸세요.

규모가 커지면 데이터베이스에 붙는 길을 하나로 모으는 편이 좋습니다. 개인이 데이터베이스에 직접 붙지 않고 Session Manager나 접근 프록시를 거치게 하면, 누가 언제 붙었는지 기록이 남고 주소 목록을 손으로 고칠 일도 없어집니다.

### 근거

| 항목 | 값 | 출처 |
|---|---|---|
| `kafka-controller-0-external` 포트 | 9094, 443 | traffic.db_exposed |
| 9094 포트의 보안 그룹 허용 | 0.0.0.0/0 | traffic.db_exposed |
| `kafka-controller-0-external` scheme | internet-facing | objects/services.json |
| `app-u-db-shared` 포트 | 3307, 3308, 3309, 3311, 5432, 5433, 6379, 7687 | traffic.db_exposed |
| `app-u-db-shared` 허용 출처 | 포트마다 최대 4개, 가장 넓은 것 /32, 6379는 1개 | traffic.db_exposed |
| `app-u-db-shared`를 데이터베이스에 연결하는 TargetGroupBinding | 7개 | traffic.db_exposed |

### 더 읽을 것

- [Kubernetes: Service](https://kubernetes.io/docs/concepts/services-networking/service/): NodePort와 LoadBalancer가 실제로 어느 노드 주소에 무엇을 여는지, 클라우드마다 내부 로드밸런서 어노테이션이 무엇인지 나옵니다.
- [AWS Load Balancer Controller: Service annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/): NLB에 누가 붙을 수 있는지 정하는 scheme, 출처 범위, 보안 그룹의 기본값이 정리돼 있습니다.
- [Elastic Load Balancing: Update the security groups for your Network Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-security-groups.html): 보안 그룹 없는 NLB가 무엇을 통과시키는지와 막힌 트래픽을 보는 메트릭과 로그를 설명합니다.

## 3. 인터넷 전체에 열린 클러스터 API 엔드포인트

**고른 이유.** 자격 증명 하나가 새거나 RBAC 설정 하나가 잘못되면 인터넷 어디에서든 클러스터 전체를 읽고 바꿀 수 있습니다.

### 무슨 일인가

EKS 클러스터 `app-u-cluster-eks`의 API 서버 엔드포인트가 public과 private 둘 다 켜져 있고, public 쪽에 접근을 허용하는 CIDR이 `0.0.0.0/0` 하나입니다. 인터넷의 어떤 주소에서든 API 서버에 요청을 보낼 수 있다는 뜻입니다. private 엔드포인트가 켜져 있으니 노드는 VPC 안에서 API 서버에 닿고, 엔드포인트를 좁혀도 노드 쪽은 영향을 받지 않습니다.

지난 1시간 동안 API 서버가 401로 답한 요청은 메트릭에 나오지 않았습니다. 지금 낯선 곳에서 인증을 시도하는 흔적은 이 메트릭으로는 보이지 않는다는 뜻입니다. 다만 이 클러스터는 컨트롤 플레인 로그 가운데 `audit`을 끄고 있어서, 누가 어디에서 무엇을 했는지는 기록으로 남지 않습니다.

### 왜 생기나

새 EKS 클러스터는 public 엔드포인트를 켜고 시작합니다. 그래서 따로 바꾸지 않으면 이 상태로 남습니다. 이 클러스터는 private 엔드포인트를 켰지만 public CIDR 목록은 기본값 그대로입니다. 운영자와 CI가 바깥에서 `kubectl`을 쓰기 위해 열어 둔 것으로 보이지만, 이 점검을 실행한 자격 증명도 `ci-user` 사용자였으니 CI가 어디에서 도는지에 따라 좁힐 범위가 달라집니다. 이유는 클러스터에 남아 있지 않습니다.

EKS 클러스터에는 문이 둘 있고 각각 자물쇠가 따로 있습니다. 첫째 문이 API 서버 엔드포인트입니다. public 엔드포인트가 켜져 있으면 API 서버가 인터넷에서 닿습니다. 접근은 IAM 인증과 Kubernetes RBAC로 지켜지기 때문에 AWS는 이 기본값도 안전하다고 봅니다. 열린 엔드포인트가 없애는 것은 두 번째 방어선입니다. 새어 나간 자격 증명이 어디에서든 통하고, 인증의 결함이나 너무 넓은 RoleBinding 하나도 어디에서든 쓸 수 있게 됩니다.

이 문의 자물쇠가 public 접근 CIDR 목록입니다. public 엔드포인트에 닿을 수 있는 주소를 제한하고, private 엔드포인트에는 영향을 주지 않습니다. private 엔드포인트를 함께 켜 두면 노드의 트래픽은 VPC 안에 머무르므로, CIDR을 좁혀도 노드 주소를 목록에 넣을 필요가 없습니다. 이 클러스터가 지금 그 상태입니다. public 접근을 아예 끄면 모든 `kubectl` 명령이 VPC 안이나 연결된 네트워크에서 와야 합니다.

둘째 문은 클러스터 보안 그룹입니다. EKS가 클러스터와 함께 만들어 컨트롤 플레인과 관리형 노드 그룹의 네트워크 인터페이스에 붙이는 보안 그룹이고, 기본으로는 같은 그룹 안의 트래픽만 받습니다. 여기에 0.0.0.0/0 규칙이 더해지면 kubelet의 10250 포트, NodePort 범위, SSH 22 포트가 인터넷에 열립니다. 이번 점검에서는 이 보안 그룹의 규칙을 문제로 잡지 않았습니다.

[Aqua Nautilus](https://www.aquasec.com/blog/leveraging-kubernetes-rbac-to-backdoor-clusters/)가 보고한 공격에서는, 공격자들이 인터넷에서 닿고 익명 요청에 권한을 준 API 서버를 찾아 관리자 수준의 ClusterRole과 ServiceAccount, ClusterRoleBinding을 만들어 계속 드나들 길을 만들었습니다. 그리고 Monero를 채굴하는 DaemonSet을 올렸습니다. 연구자들은 공격받은 클러스터를 적어도 60개, 같은 공격자의 흔적이 있는 노출된 클러스터를 60개 더 찾았습니다. 이 클러스터는 익명 접근을 허용한다는 근거는 없지만, 인증이나 RBAC의 실수 하나가 누구나 찾아 쓸 수 있는 것이 된다는 점은 같습니다. 엔드포인트를 알려진 주소로 좁혀 두면 같은 실수가 있어도 바깥에서 닿지 않습니다.

### 추천 점검 방법

엔드포인트가 다시 열리는 것은 AWS Config 관리형 규칙으로 알립니다. `eks-endpoint-no-public-access`는 public 엔드포인트가 켜져 있으면 언제나 NON_COMPLIANT로 보고하는데, CIDR 목록은 보지 않으므로 private 전용으로 운영하는 클러스터에 맞습니다. 클러스터 보안 그룹에 세상 전체에 열린 규칙이 생기는 것은 `vpc-sg-open-only-to-authorized-ports`가 잡습니다. 이 계정에 두 규칙이 켜져 있는지는 이번 점검으로 확인하지 않았습니다.

```text
EKS_ENDPOINT_NO_PUBLIC_ACCESS
VPC_SG_OPEN_ONLY_TO_AUTHORIZED_PORTS (authorizedTcpPorts = 443)
```

API 서버가 401로 답한 요청은 `apiserver_request_total`의 응답 코드로 볼 수 있습니다. 엔드포인트가 열려 있는 동안 이 값이 늘면 낯선 곳의 요청이 섞여 있을 수 있습니다.

```promql
sum(rate(apiserver_request_total{code="401"}[1h]))
```

지금 설정은 아래처럼 확인합니다.

```bash
aws eks describe-cluster --name app-u-cluster-eks --query cluster.resourcesVpcConfig
```

### 추천 해결 방안

이 규모에서는 public 엔드포인트를 끄고, 연결된 네트워크나 VPC 안의 bastion, CloudShell로 API 서버에 닿게 하는 방법을 권합니다. 클러스터 보안 그룹에는 그 네트워크에서 오는 443만 허용합니다. 그리고 위의 AWS Config 규칙 두 개를 켜서, 엔드포인트가 다시 열리거나 세상에 열린 규칙이 생기면 감사 때가 아니라 그 자리에서 알게 합니다.

얻는 것은 API 서버가 인터넷에 드러난 면이 없어지는 것입니다. 치르는 것은 API와 이야기하는 모든 사람, CI 작업, 도구가 VPC로 들어오는 길을 가져야 한다는 점입니다. 그 길도 새로 만들고 지켜야 하는 인프라이고, 잘못되면 운영자가 클러스터에 들어가지 못하는 새 원인이 됩니다.

그 길을 당장 만들기 어렵다면 public 엔드포인트는 두고 public 접근 CIDR을 사무실, VPN 출구, CI가 나가는 주소로 좁히는 것이 먼저입니다. private 엔드포인트가 이미 켜져 있으니 노드는 이 변경에 영향을 받지 않습니다. 운영자의 주소가 바뀌면 AWS API로 목록을 고쳐야 `kubectl`이 다시 동작한다는 불편이 생깁니다. 그와 함께 컨트롤 플레인 로그의 `audit`을 켜 두면 누가 어디에서 무엇을 했는지 남습니다.

```text
# 모양을 보여 주는 예시입니다. CIDR은 실제로 운영하는 주소로 정합니다.
aws eks update-cluster-config --name app-u-cluster-eks \
  --resources-vpc-config endpointPublicAccess=true,publicAccessCidrs="203.0.113.10/32"
```

적용할 때 조심할 것이 있습니다. 이 점검을 실행한 `ci-user`처럼 바깥에서 API를 부르는 자격 증명이 있으면, 목록을 좁히는 순간 그 작업이 끊깁니다. 그 작업이 어느 주소에서 나가는지 먼저 확인하고 목록에 넣으세요. Argo CD는 클러스터 안에서 돌기 때문에 영향을 받지 않습니다.

엔드포인트 설정은 EKS 클러스터 리소스의 속성이라 클러스터 안에 선언한 곳이 없습니다. 클러스터를 만든 곳(Terraform 같은 IaC)에서 바꾸세요. 콘솔이나 CLI로만 바꾸면 다음에 그 IaC를 적용할 때 되돌아갈 수 있습니다.

### 근거

| 항목 | 값 | 출처 |
|---|---|---|
| public 엔드포인트, private 엔드포인트 | 둘 다 켜짐 | inventory.json (eks) |
| public 접근 CIDR | `0.0.0.0/0` | inventory.eks.public_access_cidrs |
| 꺼져 있는 컨트롤 플레인 로그 | `audit` | inventory.eks.control_plane_logging_off |
| 지난 1시간 401 응답 | 시계열 0개 | metrics.apiserver_401_rate_1h |
| 점검에 쓴 AWS 자격 증명 | `ci-user` 사용자 | setup.json |

### 더 읽을 것

- [EKS: Cluster API server endpoint](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html): 엔드포인트의 세 가지 조합을 한 표로 보여 주고, private 전용 API 서버에 닿는 방법을 설명합니다.
- [EKS: Security group requirements for clusters](https://docs.aws.amazon.com/eks/latest/userguide/sec-group-reqs.html): 클러스터 보안 그룹이 어디에 붙는지, 기본 규칙과 좁힐 때 남겨야 하는 최소 규칙이 나옵니다.
- [AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html): 들어오는 포트나 bastion, SSH 키 없이 노드에 셸을 여는 방법입니다.
- [AWS Config: vpc-sg-open-only-to-authorized-ports](https://docs.aws.amazon.com/config/latest/developerguide/vpc-sg-open-only-to-authorized-ports.html): 세상에 열린 포트를 보고하는 관리형 규칙과 그 매개변수입니다.

## 4. 매니페스트에 평문으로 적힌 Neo4j 인증 값

**고른 이유.** Git 저장소나 Argo CD 화면을 읽을 수 있는 사람이면 운영 Neo4j의 인증 값을 그대로 볼 수 있고, 그 데이터베이스는 인터넷에서 닿는 NLB 뒤에 있습니다.

### 무슨 일인가

`prod-app-z-backend` 네임스페이스의 StatefulSet `app-z-neo4j`에서 `neo4j` 컨테이너의 환경 변수 `NEO4J_AUTH`가 Secret 참조가 아니라 26자짜리 문자열 값으로 직접 적혀 있습니다. 이 점검은 값을 기록하지 않았고 길이와 모양만 봤습니다. 변수 이름과 길이로 보아 실제 인증 값일 가능성이 높다고 봅니다.

같은 컨테이너의 다른 변수 `GRAPH_DB_PASSWORD`는 Secret `app-z-backend-secret`의 키 `NEO4J_PASSWORD`를 `secretKeyRef`로 읽습니다. 비밀번호를 Secret으로 다루는 길은 이미 있는데, `NEO4J_AUTH` 하나만 그 길을 타지 않은 것입니다. 이 네임스페이스에는 External Secrets Operator의 ExternalSecret도 네 개 있습니다. `app-z-backend-secret`이 그중 하나로 만들어지는지는 이번에 확인하지 않았습니다.

이 StatefulSet은 Argo CD Application `app-z-backend-prod`가 저장소 `https://github.com/example-org/iac`의 `apps/prod/app-z-backend` 경로에서 관리합니다. 그래서 이 값은 그 저장소의 이력에도 남아 있을 것으로 봅니다. 그리고 2번 문제(인터넷에 열린 Kafka 포트와 데이터베이스 포트)에서 본 것처럼 `app-z-neo4j`의 7687 포트는 인터넷용 NLB `app-u-db-shared`에 연결돼 있고, 보안 그룹이 주소 네 개만 허용합니다.

같은 이름 규칙으로 `prod-app-z-backend/app-ad`의 `TS_KUBE_SECRET`도 걸렸지만, 변수 이름으로 보아 비밀 값이 아니라 Secret 오브젝트의 이름을 받는 자리로 보여서 이 문제에 넣지 않았습니다. 값을 보지 않았으니 확인은 매니페스트에서 하세요.

### 왜 생기나

데이터베이스를 처음 띄울 때 인증 값을 그대로 적고, 나중에 애플리케이션 쪽 비밀번호만 Secret으로 옮긴 것으로 보입니다. 애플리케이션이 쓰는 `GRAPH_DB_PASSWORD`만 Secret을 읽고 있다는 점에서 그렇게 추정합니다. 정확한 경위는 클러스터에 남아 있지 않습니다.

Kubernetes에는 겉보기에 비슷한 오브젝트가 둘 있습니다. ConfigMap은 비밀이 아닌 키-값 데이터를 위한 것이고, Secret은 비슷하지만 비밀 데이터를 위한 것입니다. 그 차이 덕분에 클러스터가 Secret을 다르게 다룰 수 있습니다. RBAC에서 접근 권한을 따로 주고, 저장할 때 암호화를 설정할 수 있습니다.

Deployment나 StatefulSet에 환경 변수 값으로 적은 비밀번호는 그 어느 것도 받지 못합니다. 워크로드를 읽을 수 있는 사람이면 누구나 보는 오브젝트의 일부가 되고, 매니페스트가 가는 곳마다 따라갑니다. Git 저장소, `kubectl describe`의 출력, Argo CD 화면이 그렇습니다. Git에 한 번 들어간 값은 커밋을 고쳐도 이력에 남습니다.

Secret이라고 그 자체로 안전한 것도 아닙니다. 값은 base64로 인코딩될 뿐이고 base64는 암호화가 아닙니다. Secret 매니페스트를 저장소에 넣으면 저장소를 읽는 사람은 모두 값을 읽습니다. 클러스터 안에서도 Secret에 대한 list와 watch 권한은 get과 똑같이 내용을 보여 주고, 한 네임스페이스에 파드를 만들 수 있는 사람은 그 네임스페이스의 Secret을 마운트해서 읽을 수 있습니다. EKS는 1.28부터 Kubernetes API 데이터 전체를 AWS가 소유한 키로 봉투 암호화합니다. 이 클러스터도 Secret 암호화가 켜져 있습니다. 하지만 이것은 etcd에 저장된 값을 지키는 것이지, 매니페스트에 적힌 값을 지키지는 않습니다.

### 추천 점검 방법

매니페스트에 비밀 값이 들어가는 것은 합치기 전에 잡는 편이 좋습니다. kube-linter는 `env-var-secret` 검사를 기본으로 켜고 있어서, 비밀번호처럼 보이는 이름의 환경 변수에 값이 직접 적히면 알려 줍니다. `https://github.com/example-org/iac` 저장소의 CI에 넣으면 이번 같은 값이 저장소에 들어가기 전에 멈춥니다.

```text
kube-linter lint apps/ --include env-var-secret
```

누가 Secret을 읽는지는 API 서버 감사 로그로 봅니다. Kubernetes의 권장 사항은 한 사용자가 Secret을 한꺼번에 많이 읽는 것 같은 일에 알림을 거는 것입니다. 이 클러스터는 컨트롤 플레인 로그 가운데 `audit`이 꺼져 있어서 지금은 이 기록이 남지 않습니다.

```yaml
- level: Metadata
  resources:
    - group: ""
      resources: ["secrets", "configmaps"]
```

### 추천 해결 방안

이 규모에서는 비밀 값을 클러스터 밖의 저장소에 두고 External Secrets Operator가 거기서 Kubernetes Secret을 만들게 하는 방법을 권합니다. 이 클러스터에는 이미 External Secrets Operator가 있고, ClusterSecretStore가 하나, ExternalSecret이 36개 있습니다. `app-z-backend-secret`이 이미 그 길로 만들어진 것이라면, `NEO4J_AUTH`의 값을 그 저장소에 키 하나로 더하고 StatefulSet에서는 `secretKeyRef`로 읽기만 하면 됩니다. 그러면 값을 바꾸는 일이 한 곳에서 끝나고 Git에는 참조만 남습니다.

옮긴 뒤에는 값을 바꿔야 합니다. 지금 값은 이미 매니페스트와 저장소 이력에서 읽을 수 있었기 때문입니다. 함께 Secret에 대한 get, list, watch 권한을 그것이 필요한 구성 요소로 좁히고, 컨트롤 플레인 로그의 `audit`을 켜는 편이 좋습니다.

```yaml
# 모양을 보여 주는 예시입니다. Secret 이름과 키는 실제 것으로 정합니다.
env:
  - name: NEO4J_AUTH
    valueFrom:
      secretKeyRef:
        name: app-z-backend-secret
        key: NEO4J_AUTH
```

적용할 때 조심할 것이 셋 있습니다. 먼저, 예시처럼 `app-z-backend-secret`에서 `NEO4J_AUTH` 키를 읽게 바꾸기 전에 그 키가 Secret에 실제로 있어야 합니다. 이 Secret은 ExternalSecret이 만드는 것이라 바깥 저장소에 키를 먼저 더하고 동기화된 것을 확인하세요. 키가 없으면 파드가 뜨지 못해 Neo4j가 멈춘 채로 남습니다. 그다음으로, `app-z-neo4j`는 레플리카가 1개인 StatefulSet이고 업데이트 전략이 RollingUpdate라서, 환경 변수를 바꾸면 파드가 다시 뜨는 동안 Neo4j가 멈춥니다. 둘째, 이 값을 바꿨을 때 이미 데이터가 있는 Neo4j의 비밀번호도 함께 바뀌는지는 Neo4j 이미지의 동작에 달려 있으니 Neo4j 문서에서 먼저 확인하세요. 데이터베이스의 비밀번호와 `GRAPH_DB_PASSWORD`가 읽는 Secret의 값이 어긋나면 `app-z-backend`가 데이터베이스에 붙지 못합니다. 셋째, 이 StatefulSet은 selfHeal이 켜진 Argo CD Application `app-z-backend-prod`가 관리하므로 클러스터에서 직접 고치면 되돌아갑니다. 저장소 `https://github.com/example-org/iac`의 `apps/prod/app-z-backend` 경로에서 바꾸세요.

규모가 커지면 비밀 값의 회전을 저장소 쪽에서 정기적으로 하고, External Secrets Operator가 그 값을 따라가게 해서 사람이 값을 손으로 옮기는 일을 없애는 편이 좋습니다. 고객 관리형 KMS 키는 키를 직접 통제해야 할 때만 쓰고, 그 키가 꺼지면 클러스터 전체가 Secret을 읽지 못한다는 점을 함께 대비해야 합니다.

### 근거

| 항목 | 값 | 출처 |
|---|---|---|
| 평문 값으로 적힌 변수 | `NEO4J_AUTH`, 26자 | objects/statefulsets.json (prod-app-z-backend/app-z-neo4j) |
| 같은 컨테이너의 Secret 참조 | `GRAPH_DB_PASSWORD` → `app-z-backend-secret` | objects/statefulsets.json |
| `app-z-neo4j` 레플리카 | 1 | objects/statefulsets.json |
| 관리하는 곳 | Argo CD `app-z-backend-prod`, selfHeal 켜짐 | security.plaintext-secret-env |
| ExternalSecret, ClusterSecretStore | 36개, 1개 | objects/externalsecrets.external-secrets.io.json |
| 꺼져 있는 컨트롤 플레인 로그 | `audit` | inventory.eks.control_plane_logging_off |

### 더 읽을 것

- [Kubernetes: Good practices for Kubernetes Secrets](https://kubernetes.io/docs/concepts/security/secrets-good-practices/): Secret이 이름만 바꾼 ConfigMap이 되지 않으려면 관리자와 개발자가 각각 무엇을 해야 하는지 정리돼 있습니다.
- [EKS: Default envelope encryption for all Kubernetes API Data](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html): EKS가 1.28부터 기본으로 무엇을 암호화하는지, 고객 키가 꺼지거나 지워지면 무슨 일이 생기는지 나옵니다.
- [External Secrets Operator: overview](https://external-secrets.io/latest/introduction/overview/): 바깥 저장소에서 Secret을 동기화하는 방식과 어느 리소스를 누가 소유하는지 설명합니다.
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets): Secret을 암호화한 채로 Git에 두는 다른 방법과, 봉인 키를 백업해야 하는 이유가 있습니다.
- [kube-linter: checks](https://raw.githubusercontent.com/stackrox/kube-linter/main/docs/generated/checks.md): 환경 변수의 비밀 값을 잡는 검사와 그 검사가 기본으로 켜져 있는지 나옵니다.

## 5. 지원이 끝난 Kubernetes 1.32와 따라가지 못한 Karpenter

**고른 이유.** 보안 패치가 나오지 않는 버전에서 돌고 있고, 업그레이드를 미룰수록 한 번에 넘어야 할 변경이 쌓여서 그 업그레이드 날 노드가 뜨지 않으면 서비스 일부가 멈춥니다.

### 무슨 일인가

이 클러스터의 컨트롤 플레인은 `v1.32.13-eks-577a51e`이고 노드 아홉 대는 `v1.32.9`입니다. Kubernetes 프로젝트가 1.32의 패치를 멈춘 날은 2026-02-28이고, EKS의 표준 지원이 끝난 날은 2026-03-23입니다. 점검한 날 기준으로 EKS 표준 지원이 끝난 지 237일이 지났고, 클러스터의 지원 유형은 `EXTENDED`입니다. 연장 지원 기간이라 EKS가 보안 패치를 대 주고 있지만, 그 대가로 클러스터 시간당 추가 요금이 붙습니다.

노드를 만드는 쪽은 더 뒤처져 있습니다. Karpenter가 `0.37.0`인데, 이 버전이 지원하는 Kubernetes는 1.23부터 1.30까지입니다. 클러스터는 1.32라서 지원 범위를 두 마이너 벗어났습니다. Karpenter 로그에도 2026-11-14 08:53 UTC에 버전을 지원하지 않는다는 오류가 한 줄 남았습니다. 그래도 지난 24시간 동안 Karpenter는 노드를 7개 띄웠으니, 지금 노드를 만드는 일 자체는 하고 있습니다.

그리고 EC2NodeClass `default`가 `amiFamily: AL2`이고 AMI 버전을 고정하지 않았습니다. Amazon Linux 2용 EKS AMI는 1.32가 마지막이라, 이 설정 그대로 1.33으로 올리면 새 노드가 부팅할 이미지가 없습니다.

API 서버 메트릭에는 폐기 예정 API 호출이 하나 잡혔습니다. `componentstatuses` v1이고, 어느 릴리스에서 없어지는지는 메트릭에 적혀 있지 않습니다.

### 왜 생기나

EKS는 연장 지원이 기본으로 켜져 있어서, 표준 지원이 끝나도 클러스터가 멈추거나 저절로 올라가지 않습니다. 그래서 업그레이드가 급한 일로 느껴지지 않고 뒤로 밀리기 쉽습니다. Karpenter는 컨트롤 플레인과 별개로 클러스터 주인이 설치하고 올리는 것이라, 컨트롤 플레인만 1.32로 올리고 Karpenter는 0.37에 남은 것으로 보입니다. 클러스터에 그 결정의 이유는 남아 있지 않습니다.

Kubernetes 프로젝트는 가장 최근 세 마이너의 릴리스 브랜치를 관리합니다. 한 마이너는 열네 달 정도 패치를 받는데, 열두 달은 표준 지원이고 나머지 두 달은 CVE가 붙은 취약점과 심각한 문제만 고치는 유지 기간입니다. 그 뒤로는 아무것도 고쳐지지 않고, 옛 버전에만 있는 취약점은 보고조차 되지 않을 수 있습니다.

EKS는 자기 날짜가 따로 있습니다. EKS가 그 버전을 내놓은 날부터 14개월이 표준 지원이고, 그 뒤 12개월이 추가 요금이 붙는 연장 지원입니다. 연장 지원이 끝나면 EKS가 공지 없이 아무 때나 컨트롤 플레인을 올립니다. 이때 올라가는 것은 컨트롤 플레인뿐이고 노드와 애드온은 그대로 남습니다.

기다리는 비용은 한 가지 규칙에서 나옵니다. API 서버는 업그레이드할 때 마이너를 건너뛸 수 없습니다. 세 마이너 뒤처진 클러스터는 업그레이드를 세 번 연달아 해야 하고, 그때마다 없어지는 API와 애드온 호환성을 따로 확인해야 합니다. kubelet은 API 서버보다 세 마이너까지 오래돼도 되니 노드는 조금 늦어도 되지만, 끝없이 늦을 수는 없습니다.

Karpenter와 AMI는 아직 없는 노드의 문제입니다. 지금 도는 노드는 멀쩡하고, 깨진 것은 다음 노드를 띄울 설정이라서 클러스터가 늘어나거나 노드를 바꿔야 할 때만 드러납니다. Karpenter는 릴리스마다 지원하는 Kubernetes 범위가 있고, 범위 밖이면 오류를 냅니다. 1.32에는 Karpenter 1.2 이상이, 1.33에는 1.5 이상이 필요합니다. 따라잡는 것도 한 번에 되지 않습니다. CRD는 Karpenter 버전과 함께 움직여야 하는데 Helm은 첫 설치 때만 CRD를 설치하고, 어떤 릴리스는 중간 릴리스를 거쳐야만 닿을 수 있으며, 옛 패치로 되돌리면 클러스터의 모든 노드가 drift로 잡힐 수 있습니다.

EKS는 1.32를 마지막으로 Amazon Linux 2 AMI를 내지 않았고, 2025-11-26에는 AL2 AMI 배포를 완전히 멈췄습니다. Amazon Linux 2 자체의 지원도 2026-06-30에 끝났습니다. 그러니 지금 노드는 패치가 오지 않는 이미지로 돌고 있습니다. AMI 버전을 `latest`로 두면 새 AMI가 나올 때마다 Karpenter가 노드를 drift로 보고 바꾸는데, Karpenter 문서는 이것을 운영 환경에 권하지 않습니다. 버전을 고정하면 고정 값을 바꿀 때만 노드가 바뀝니다.

[ZenML](https://status.zenml.io/incidents/bnrlb8tck3v0)은 운영 EKS 클러스터가 오래된 Kubernetes 버전과 AMI 종류로 돌고 있었습니다. 업그레이드하면서 VPC와 EKS Terraform 모듈을 함께 바꿨고, Terraform으로 KMS Secret 암호화를 켜는 변경이 워커 노드의 IAM 권한까지 지웠습니다. 노드 그룹을 다시 만들 때까지 여덟 시간 정도 서비스가 멈췄습니다. 미뤄 둔 업그레이드가 하룻밤에 여러 변경으로 한꺼번에 왔고 그중 하나가 노드를 망가뜨렸다는 점이, Kubernetes와 Karpenter와 AMI를 함께 넘어야 하는 이 클러스터와 같습니다.

### 추천 점검 방법

지원 종료일은 메트릭이 아니라 달력의 사실이라, EKS가 알려 주는 곳을 봅니다. EKS 콘솔의 Upgrade insights 탭은 업그레이드를 막는 문제를 24시간마다 다시 확인하고, AWS Health는 표준 지원이 끝나기 적어도 60일 전에 공지를 보냅니다.

```bash
aws eks list-insights --cluster-name app-u-cluster-eks
aws eks describe-cluster-versions
```

다음 마이너에서 없어지는 API를 누가 부르는지는 API 서버의 `apiserver_requested_deprecated_apis`로 봅니다. 이 조건에 걸리는 시계열이 있으면 업그레이드 전에 고쳐야 할 호출이 있다는 뜻입니다. 지금 잡힌 `componentstatuses` 호출에는 없어지는 릴리스가 적혀 있지 않습니다.

```promql
apiserver_requested_deprecated_apis{removed_release!=""}
```

Karpenter가 노드를 제대로 만드는지는, 기다리는 파드가 있는데 노드 생성 카운터가 움직이지 않는 것으로 봅니다. 버전 불일치 자체는 메트릭에 없어서, 업그레이드 전에 오브젝트로 읽어야 합니다. Karpenter 로그를 Loki로 보내고 있으니 오류 줄로 알림을 걸 수도 있습니다.

```promql
sum(kube_pod_status_phase{phase="Pending"}) > 0 and sum(increase(karpenter_nodeclaims_created_total[15m])) == 0
```

```logql
count_over_time({namespace="karpenter"} |= "is not compatible with" [24h]) > 0
```

### 추천 해결 방안

이 규모에서는 업그레이드를 글로 적고 연습한 절차로 만드는 방법을 권합니다. 릴리스 노트를 읽고, Upgrade insights를 비우고, CI에서 매니페스트의 없어질 API를 검사하고, 운영이 아닌 클러스터를 먼저 올린 뒤, 컨트롤 플레인, 애드온, 노드 순서로 올립니다. 노드를 바꾸기 전에는 PodDisruptionBudget과 topology spread를 갖춰 둡니다. 이렇게 하면 업그레이드가 사건이 아니라 일정이 됩니다. 치르는 것은 운영이 아닌 클러스터 하나와, 한 해 세 번의 엔지니어 시간입니다.

이 클러스터는 순서가 정해져 있습니다. Karpenter를 먼저 올려야 합니다. 0.37에서 1.x로 가는 길에는 CRD 이전이 들어 있고, 거쳐야 하는 중간 릴리스가 있으니 Karpenter 업그레이드 안내서를 릴리스마다 따라갑니다. Karpenter CRD는 별도 차트로 관리해서 Karpenter를 올릴 때마다 함께 움직이게 합니다. 그다음 EC2NodeClass를 AL2023으로 바꾸고 AMI 버전을 고정합니다. 그 뒤에야 Kubernetes 1.33으로 올릴 수 있습니다.

```yaml
# 모양을 보여 주는 예시입니다. 고정할 AMI 버전은 실제로 시험한 것으로 정합니다.
kind: EC2NodeClass
spec:
  amiSelectorTerms:
    - alias: al2023@v20240807
---
kind: NodePool
spec:
  disruption:
    budgets:
      - nodes: "10%"
      - nodes: "0"
        reasons: [Drifted]
        schedule: "0 0 * * 1-5"
        duration: 10h
```

적용할 때 조심할 것이 있습니다. 위 예시는 Karpenter 1.x의 API 모양이라 지금의 0.37에는 맞지 않고, Karpenter를 1.x로 올린 뒤에 씁니다. 1.x로 옮기는 과정에서도 노드가 drift로 잡힐 수 있습니다. 그리고 NodePool 네 개 모두 `expireAfter`가 720h라서 위 budget과 상관없이 노드가 30일마다 교체되고, 그때마다 레플리카가 1개인 데이터베이스가 다시 뜹니다. EC2NodeClass를 바꾸면 그것을 쓰는 NodePool의 노드가 모두 drift로 잡혀 교체됩니다. NodePool 네 개 모두 budget이 `nodes: "10%"` 하나뿐이라 업무 시간에도 교체가 일어날 수 있으니, 위 예시처럼 시간대를 막는 budget을 먼저 넣는 편이 좋습니다. 운영 데이터베이스 StatefulSet이 모두 레플리카 1개이고, 1번 문제에서 본 것처럼 백업이 없으니 노드 교체 전에 백업을 먼저 갖추세요. AL2023은 cgroup v2를 쓰므로 Java 8의 옛 빌드처럼 cgroup v1 파일을 읽는 것은 바꾸기 전에 확인해야 합니다. 1.33으로 올리기 전에 Pluto나 Upgrade insights로 없어지는 API를 다시 확인하세요.

EC2NodeClass와 Karpenter 설치는 Argo CD나 Helm이 관리한다는 표시를 이번 점검에서 찾지 못했습니다. 선언한 곳(매니페스트나 Helm 값)에서 바꾸세요. EKS 버전은 클러스터를 만든 IaC에서 바꿉니다.

규모가 커지면 여러 마이너를 한 번에 넘어야 할 때 제자리 업그레이드를 연달아 하는 대신, 목표 버전의 새 클러스터를 만들고 워크로드를 옮기는 방법을 함께 따져 봅니다. 여러 버전을 한 번에 넘고 되돌릴 수 있지만, 두 클러스터를 나란히 돌려야 하고 API 엔드포인트와 OIDC 발급자 주소가 바뀝니다.

### 근거

| 항목 | 값 | 출처 |
|---|---|---|
| 컨트롤 플레인 버전 | `v1.32.13-eks-577a51e` | inventory.json |
| 노드 버전 | `v1.32.9`, 9대 | setup.json |
| EKS 표준 지원 종료 | 2026-03-23, 237일 지남 | platform.k8s-version-eol |
| upstream 지원 종료 | 2026-02-28 | platform.k8s-version-eol |
| 지원 유형 | `EXTENDED` | inventory.eks |
| Karpenter 버전, 지원 범위 | `0.37.0`, 1.23~1.30 | scaling.karpenter |
| Karpenter 버전 오류 로그 | 1번, 2026-11-14 08:53 UTC | logs.signatures |
| 지난 24시간 Karpenter가 띄운 노드 | 7개 | scaling.karpenter |
| EC2NodeClass `default` | `amiFamily: AL2`, AMI 고정 안 함 | karpenterctl.summary |
| NodePool disruption budget | 4개 모두 `nodes: "10%"` 하나 | scaling.karpenter.nodepools |
| 폐기 예정 API 호출 시계열 | 1개, `componentstatuses` v1 | metrics.apiserver_requested_deprecated_apis |

### 더 읽을 것

- [Kubernetes: Patch Releases](https://kubernetes.io/releases/patch-releases/): 마이너의 지원 기간, 유지 기간에 고치는 것, 릴리스별 지원 종료일이 있습니다.
- [Amazon EKS: Understand the Kubernetes version lifecycle on EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html): EKS의 달력, 연장 지원에 들어가는 것, 자동 업그레이드가 건드리는 것과 건드리지 않는 것을 설명합니다.
- [Amazon EKS best practices: Cluster Upgrades](https://docs.aws.amazon.com/eks/latest/best-practices/cluster-upgrades.html): 제자리 업그레이드의 순서와 그 전에 없어진 API를 찾는 도구가 나옵니다.
- [Karpenter: Compatibility](https://karpenter.sh/docs/upgrading/compatibility/): Kubernetes 마이너마다 필요한 Karpenter 릴리스가 표로 있습니다.
- [Karpenter: Upgrade Guide](https://karpenter.sh/docs/upgrading/upgrade-guide/): 반드시 거쳐야 하는 릴리스와 되돌릴 때 생기는 일을 포함한 릴리스별 안내입니다.
- [Karpenter: NodeClasses](https://karpenter.sh/docs/concepts/nodeclasses/): alias로 AMI를 고르고 고정하는 방법과 `latest`가 도는 노드에 무엇을 뜻하는지 나옵니다.
- [Amazon EKS: Guide to EKS AL2 and AL2-Accelerated AMIs transition features](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html): AL2 종료일과 AL2023에서 워크로드에 달라지는 것, 특히 cgroup v2를 설명합니다.
- [Karpenter: Disruption](https://karpenter.sh/docs/concepts/disruption/): drift를 어떻게 알아내는지, budget이 언제 몇 대까지 교체를 허용하는지 나옵니다.

## 그다음으로 큰 문제

- **ALB 헬스 체크를 통과하지 못하는 운영 서비스 네 개.** `app-t-backend`, `app-y-frontend`, `app-z-backend`, `app-v-frontend`의 타깃 그룹에서 정상 타깃이 0개입니다. 헬스 체크 경로 `/`가 404나 307을 돌려주기 때문이고, 모든 타깃이 비정상이면 ALB가 fail open으로 전부에 트래픽을 보내므로 지금 요청은 처리되지만 헬스 체크가 아무것도 걸러 내지 못합니다. 심각도는 high입니다.
- **적용되지 않는 NetworkPolicy.** `prod-app-t`, `prod-app-x`, `prod-app-r`에 NetworkPolicy가 세 개 있지만 VPC CNI의 network policy 기능이 꺼져 있어 저장만 돼 있습니다. 세 정책은 5432 포트를 출처 제한 없이 열어 두는 차트 기본값이라 켜도 막는 것은 적습니다. 심각도는 high입니다.
- **노드 권한을 가진 app-ad 컨테이너.** `prod-app-z-backend/app-ad`의 `tailscale` 컨테이너가 `NET_ADMIN` capability와 `/dev/net/tun` hostPath를 쓰고, 두 컨테이너 모두 root로 돌 수 있습니다. 이 컨테이너가 뚫리면 노드까지 닿을 수 있습니다. 심각도는 high입니다.
- **emptyDir에 저장되는 Alertmanager와 Loki.** 두 StatefulSet 모두 레플리카 1개이고 데이터를 emptyDir에 둡니다. 파드가 다른 노드로 옮겨 가면 silence와 로그가 처음부터 시작합니다. 심각도는 high입니다.
- **OOMKill을 알리는 알림 규칙이 없음.** 알림 규칙 157개 가운데 컨테이너 OOMKill을 다루는 것이 없습니다. 이번 Prometheus 재시작도 그래서 조용히 지나갔을 것으로 봅니다. 심각도는 high입니다.
- **CPU 스로틀링에 걸린 Prometheus.** `prometheus` 컨테이너의 스로틀링 비율이 수집 시점에 0.61, 24시간 기준으로 0.33입니다. 하루 중 세 번에 한 번꼴로 CPU를 기다렸다는 뜻이고, 쿼리와 규칙 평가가 늦어집니다. 심각도는 high입니다.
- **파드 IP를 내주지 못한 시스템 노드.** `node-1-116`(t8i.small)에서 ipamd가 "no available IP"를 한 번 돌려줬습니다. 지금 IP 사용은 9개 중 6개이고 max-pods는 11이라, 몰릴 때 파드가 ContainerCreating에서 멈출 수 있습니다. 심각도는 high입니다.

## 지난 리포트 이후

비교할 이전 점검이 없어서 이번 점검이 수집한 것만 봤습니다.

## 영역별 한 줄

| 영역 | 무엇 |
|---|---|
| 리소스 | Prometheus가 7일 안에 OOMKilled로 한 번 재시작됐고 24시간 동안 CPU 스로틀링 비율이 0.33이었습니다. |
| 스케일링 | Karpenter 0.37.0이 클러스터의 Kubernetes 1.32를 지원하지 않고, 24시간 동안 운영 파드의 스케줄링 실패가 91번 기록됐습니다. |
| 모니터링 | Alertmanager와 Loki가 emptyDir을 쓰고, OOMKill을 알리는 규칙과 증상 기반 알림 규칙이 없습니다. |
| 트래픽 | Kafka 9094 포트가 인터넷 전체에 열려 있고, 운영 서비스 네 개의 ALB 헬스 체크가 404나 307로 실패합니다. |
| 가용성 | 운영 데이터베이스 일곱 개에 백업 수단이 없고, Deployment 네 개의 파드가 모두 가용 영역 하나(`ap-northeast-2a`)에 있습니다. |
| 설정 관리 | 이번 점검에서 critical이나 high 문제를 찾지 못했습니다. |
| 스토리지 | EBS 볼륨 13개 모두 스냅샷 정책이 없고, 운영 데이터베이스 PVC 일곱 개의 reclaimPolicy가 Delete입니다. |
| 보안 | API 엔드포인트가 0.0.0.0/0에 열려 있고, Neo4j 인증 값이 평문 환경 변수이며, NetworkPolicy가 적용되지 않습니다. |
| 비용 | 이번 점검에서 critical이나 high 문제를 찾지 못했습니다. |
| 멀티테넌시 | 이번 점검에서 critical이나 high 문제를 찾지 못했습니다. |
| 노드 OS | 노드 두 대가 SSM에 등록되지 않아 그 노드의 OS 로그는 읽지 못했습니다. |
| 플랫폼 | Kubernetes 1.32의 EKS 표준 지원이 2026-03-23에 끝나 연장 지원으로 돌고 있고, EC2NodeClass가 AL2 AMI를 씁니다. |

## 이번 점검의 한계

**클러스터에 데이터가 없어서 판단하지 못한 것**

- 노드 `node-1-117`과 `node-2-60`이 SSM에 등록되지 않아 두 노드의 커널 로그와 OS 정보를 읽지 못했습니다.
  - 약해지는 결론: Prometheus가 도는 노드의 커널 로그를 읽지 못해 OOM이 컨테이너 한도 때문인지 노드 메모리 부족 때문인지는 Prometheus 메트릭으로만 판단했습니다.
  - 보려면: 두 노드의 IAM 역할에 AmazonSSMManagedInstanceCore 정책이 붙어 있는지 확인하면 다음 점검에서 읽을 수 있습니다.
- 데이터베이스 덤프나 백업이 클러스터 밖, 예를 들어 데이터베이스 안의 기능이나 외부 서버에서 만들어지는지는 클러스터 자료로 알 수 없습니다.
  - 약해지는 결론: 1번 문제의 '백업이 없음'은 클러스터와 AWS 계정 안에서 본 것에 한정됩니다.
  - 보려면: 각 데이터베이스 담당자에게 클러스터 밖 백업 작업이 있는지 확인하면 됩니다.

**kubegap이 아직 읽지 못하는 것**

- 컴포넌트 8개는 오브젝트와 메트릭으로만 읽었습니다. kubegap에 전용 점검 항목이 없습니다: actions-runner-controller, external-dns, kube-state-metrics, metrics-server, node-exporter, prometheus-operator, promtail, victoria-metrics.
  - 약해지는 결론: 이 컴포넌트 안에서 생긴 이상은 이 리포트에 나오지 않습니다.
- 수집이 자체 제한에 걸려 일부만 읽은 것이 있습니다: `core.component-logs` (argocd: argocd/argocd-application-controller, argocd: argocd/argocd-applicationset-controller, argocd: argocd/argocd-notifications-controller, argocd: argocd/argocd-repo-server, ebs-csi: kube-system/ebs-csi-controller, external-dns: kube-system/external-dns, external-secrets: external-secrets/external-secrets, external-secrets: external-secrets/external-secrets-cert-controller, loki: monitoring/loki-stack).
  - 약해지는 결론: 여기에서 센 숫자는 실제보다 적을 수 있고, 하루 가운데 앞쪽 로그나 목록의 나머지는 이 리포트에 없습니다.

**첫 실행 질문에서 읽지 않기로 답하신 것**

- 없음

## 숫자

심각도는 운영 규모 중형 기준입니다.

분석에서 심각도를 조정한 1건은 조정한 값으로 셌습니다.

비교할 이전 full 점검이 없습니다.

| 심각도 | fail | warn |
|---|---|---|
| critical | 1 | 0 |
| high | 22 | 27 |
| medium | 105 | 152 |
| low | 15 | 127 |

항목별 체크:

- Prometheus가 메모리 한도를 넘어 재시작됨: `resources.oomkilled.monitoring*`, `resources.oomkilled-repeated.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus`
- 운영 파드 스케줄링이 하루 동안 91번 실패함: `controlplane.scheduler-unschedulable.*`
- 운영 데이터베이스 일곱 개의 백업이 없음: `resilience.no-backup.cluster`, `eks.no-backup-policy.cluster`
- 인터넷에 열린 Kafka 포트와 데이터베이스 포트: `traffic.db-exposed.*`
- 인터넷 전체에 열린 클러스터 API 엔드포인트: `eks.public-endpoint-open.cluster`
- 매니페스트에 평문으로 적힌 Neo4j 인증 값: `security.plaintext-secret-env.prod-app-z-backend/statefulset/app-z-neo4j:neo4j`
- 지원이 끝난 Kubernetes 1.32와 따라가지 못한 Karpenter: `platform.k8s-version-eol.cluster`, `platform.karpenter-version-compat.cluster`, `karpenter.ec2nodeclass-al2.cluster`, `logs.signatures.karpenter.version-unsupported`

자세한 내용과 모든 표: [`report-details.md`](report-details.md) · kubegap 0.2.0, rubric 0.1.94 · 수집 자료 `~/.kubegap/snapshots/<context>/2026-11-15T01-51-00`
