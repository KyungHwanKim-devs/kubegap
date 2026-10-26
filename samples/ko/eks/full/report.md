# my-cluster — full 점검, 2026-10-26 16:47 KST

이 클러스터는 EKS `my-cluster` 예요. kube 컨텍스트 `my-cluster`, Kubernetes 1.32.13, 리전 us-east-1, 프로필 prod, 노드 8대, 네임스페이스 25개, 파드 157개, prod 네임스페이스 8개에 app-r, app-q, app-m, app-o, app-l, app-p, app-n, app-s 여덟 서비스가 돌고 dev 네임스페이스는 4개예요. 수집 시점에 급한 장애는 없습니다. 16:27 full 점검 뒤 19분 동안 스팟 회수도, 노드 변경도, 배포도 없었고, 그래서 아래 다섯 문제는 14:52, 16:27 리포트와 같은 다섯이고 조치는 아직 하나도 시작되지 않았어요. 새로 보인 건 `prod-app-p` 의 PostgreSQL 이 수집 시각에 CPU 제한으로 42% 멈춰 있던 것 하나인데, 7일 사용은 제한의 1% 도 안 돼 짧은 몰아 쓰기로 봤어요. 이번 수집은 직전 수집 19분 뒤에 시작돼 apiserver 숫자에는 kubegap 자신의 부하가 섞여 있고 세지 않았어요.

## 지금 손봐야 할 문제 5개

### 1. prod 파드 42개 중 28개가 여전히 만료된 스팟 노드 한 대에 있고, AWS 는 2분 예고로 그 노드를 가져갈 수 있으며, 지난 네 번의 회수마다 prod 서비스 하나가 멈췄습니다
**문제.** 애플리케이션 파드는 `workload-type=app` 레이블이 있는 노드에만 올라갈 수 있고, 지금 그 노드는 한 가용 영역의 스팟 노드 두 대예요. `ip-10-0-1-139` r8gd.xlarge 가 prod 파드 42개 중 28개, 워크로드 22개를 들고 있고, `ip-10-0-1-62` r8gd.large 는 prod 파드 5개를 들어요. 두 번째 노드는 오늘 14:17 KST 에 앞 노드가 회수되면서 생겼어요. AWS 는 26시간 동안 두 번째 앱 노드를 네 번 회수했어요. 그때마다 그 노드의 파드 여섯 개가 쫓겨나 Karpenter 가 새 노드를 띄울 때까지 80초쯤 기다렸는데, 큰 노드에 CPU request 여유가 없어서였어요. 레플리카 1개에 Recreate 전략인 `prod-app-p/app-p-backend` 는 그 시간 내내 접속이 안 됐어요. 레플리카 2개짜리 prod Deployment 다섯 개는 두 레플리카가 모두 큰 노드에 있어서, 그 노드가 가면 app-r, app-o-ai, app-o-backend, app-l-backend, app-l-frontend 가 같이 가고 클러스터는 메모리 때문에 그 손실을 받아내지 못해요. 큰 노드는 Karpenter 만료에서 55시간 지났고 `prod-app-m/app-m-admin` 의 `karpenter.sh/do-not-disrupt` 애노테이션 하나가 붙잡고 있어요.

**근거.** prod 파드 28개가 `ip-10-0-1-139` 에, 5개가 `ip-10-0-1-62` 에 있고 둘 다 us-east-1 예요. 출처는 summary.json resilience.placement 예요. `ip-10-0-1-139` 의 CPU requests 는 allocatable 의 99.5% 인데 7일 p95 사용은 5.6% 예요. 출처는 metrics/node_cpu_request_ratio.json 과 metrics/node_cpu_usage_ratio_p95_7d.json 이에요. 그 노드를 빼면 allocatable 메모리 46.0 GB 에 requests 47.5 GB 예요. 출처는 summary.json resilience.n_plus_one 이에요. 컨트롤 플레인 로그에 24시간 동안 "no fit" 스케줄러 줄이 113개 있고 app-m-backend, app-p-backend, app-l-embedding-server 가 각 23개, app-m-api 가 19개예요. 출처는 summary.json controlplane.scheduler 예요. Karpenter 는 2026-10-25T20:09:52Z, 2026-10-26T03:33:23Z, 05:17:28Z 에 "initiating delete from interruption message" 를 남겼어요. 출처는 logs/pods/karpenter/karpenter_karpenter.log 예요. do-not-disrupt 파드가 2026-10-06 이후 이 노드의 교체를 14,171번 막았어요. 출처는 events.json 이에요. app-p-backend 는 아직 replicas 1, Recreate, generation 5 예요. 출처는 objects/deployments.json 이에요.

**원인.** prod 가 Karpenter `default` 풀의 스팟 노드 두 대에서 분산 규칙 없이 돌아서, 파드는 자리가 있는 쪽 노드에 몰려요. 실제 사용의 18배인 requests 때문에 스케줄러는 큰 노드를 꽉 찬 것으로 보고, 쫓겨난 파드는 몇 초 안에 재배치되지 못하고 새 노드를 기다려요. Karpenter 는 기다리는 파드 여섯 개 크기로만 대체 노드를 만들어서 새 노드는 작고 값싼 스팟이라 또 회수돼요. 온디맨드를 받을 수 있는 `app-amd64-fallback` 풀은 노드 0대에 10% 예산이 83,953번 막혔어요. 추정입니다. app-m-admin 의 do-not-disrupt 애노테이션은 한 번 세션을 지키려 붙였다가 떼지 않은 것으로 보여요.

**조치.** ① 공유 prod 차트에서 CPU requests 를 7일 p95 로 내려요. app-l-backend 500 m → 150 m, app-l-embedding-server 500 m → 160 m, app-p-backend 500 m → 150 m, app-l-neo4j 500 m → 50 m, neo4j 메모리 4 Gi → 1 Gi. 이렇게 하면 `ip-10-0-1-139` 의 요청률이 60% 쯤으로 내려가고 쫓겨난 파드가 몇 초 안에 재배치되며 N+1 메모리 부족이 사라져요. 1시간 걸려요. ② app-p-backend 를 replicas 2, RollingUpdate maxSurge 1 maxUnavailable 0, preStop 5초로 바꿔요. 20분 걸려요. ③ 공유 prod 차트에 hostname 과 zone 기준 topologySpreadConstraints 를 넣고 app-o-ai 와 app-o-backend 에 minAvailable 1 PDB 를 만들어요. Argo CD 동기화까지 2~3시간 걸려요. ④ app-m-admin 템플릿에서 `karpenter.sh/do-not-disrupt` 를 떼요. 10분 걸려요. 그러면 Karpenter 가 만료 노드를 교체하고 문제 2 도 같이 풀려요. ①~③ 을 ④ 보다 먼저 해야 해요. 안 그러면 파드가 대체 노드에 다시 몰려요. ⑤ `app-amd64-fallback` 풀에 쓸 수 있는 예산과 온디맨드 capacity-type 요구를 주고 `karpenter.sh/capacity-type` 기준 분산을 넣어 prod 가 스팟에만 있지 않게 해요. 반나절 걸려요.
```yaml
# 공유 prod 차트 values -> Deployment template.spec
replicas: 2
strategy: { type: RollingUpdate, rollingUpdate: { maxSurge: 1, maxUnavailable: 0 } }
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: kubernetes.io/hostname
  whenUnsatisfiable: DoNotSchedule
  labelSelector: { matchLabels: { app.kubernetes.io/name: "{{ .name }}" } }
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
  labelSelector: { matchLabels: { app.kubernetes.io/name: "{{ .name }}" } }
containers:
- resources: { requests: { cpu: 150m } }
  lifecycle: { preStop: { exec: { command: ["sleep", "5"] } } }
```

**왜 이런 일이 생기나.**
- 원리: 스팟 중단은 2분 예고로 와요. Karpenter 는 바로 노드를 비우고 대기 중인 파드 크기에 맞춰 대체 노드를 만들기 때문에, 남은 노드에 request 여유가 없으면 사용자가 보는 공백은 노드 기동 시간과 파드 시작 시간을 더한 만큼이에요. 스케줄러는 사용량이 아니라 requests 로 자리를 정하니 실제보다 훨씬 큰 requests 는 놀고 있는 노드를 꽉 찬 노드로 만들고, 분산 제약이 없으면 스케줄러와 Karpenter 통합이 레플리카를 같은 노드에 모아요.
- 사례: 이 체크에 기록된 공개 사례는 없어요. 체크 정의에 자체 측정이 적혀 있어요. 첫 실제 실행에서 스팟 회수 한 번이 prod 파드 27개를 든 노드를 가져가 prod 서비스 하나가 2분 7초 멈췄어요.
- 더 알아보기: "Kubernetes docs: Pod Topology Spread Constraints", "Karpenter docs: Disruption (expiration, consolidation, interruption)", "AWS docs: EC2 Spot Instance interruption notices".

근거 체크: `resilience.prod-concentration.node-1-139`, `resilience.n-plus-one.cluster`, `resilience.replicas-same-node.prod-app-r/deployment/app-r`, `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai`, `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend`, `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-backend`, `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend`, `resilience.replicas-same-zone.*` ×4, `resilience.single-replica-in-prod.prod-app-p/app-p-backend`, `resilience.recreate-strategy-serving.prod-app-p/deployment/app-p-backend`, `resilience.no-pdb.prod-app-o/app-o-ai`, `resilience.no-pdb.prod-app-o/app-o-backend`, `controlplane.scheduler-unschedulable.prod-app-m/app-m-api`, `controlplane.scheduler-unschedulable.prod-app-m/app-m-backend`, `controlplane.scheduler-unschedulable.prod-app-l-backend/app-l-embedding-server`, `controlplane.scheduler-unschedulable.prod-app-p/app-p-backend`, `resources.node-request-usage-gap.node-1-139`, `resources.cpu-request-overprovisioned.*` (39), `resources.krr-recommendation.*` (31), `scaling.karpenter-expired-not-replaced.default-n44bh`, `karpenter.spot-to-spot-consolidation-off.cluster`, `resilience.priority-inversion.cluster`, `observability.failure-mode-uncovered.Scheduling failure`

### 2. 노드 `ip-10-0-1-139` 의 디스크가 87% 찼고, 이미지 정리가 2026-10-23 부터 906번 실패했으며, 디스크 압박으로 쫓겨난 파드 12개가 남아 알림 12개를 계속 울리고 있습니다
**문제.** prod 파드 28개를 든 노드의 루트 디스크가 50 GB 중 6.8 GB 남았어요. 파드를 돌리는 노드 에이전트인 kubelet 은 남은 공간이 10% 아래로 가면 파드를 쫓아내는데, 이미 12번 그랬고 그중 11개가 prod 파드예요. 노드의 모든 이미지가 사용 중이라 이미지 정리는 도움이 안 돼요. 쫓겨난 파드 12개는 Failed 상태로 남아 있고 가장 오래된 건 2026-09-24 부터예요. 각각이 Slack 에 `KubePodNotReady` 알림을 하나씩 울리고 있어서 지금 울리는 알림 18개 중 12개가 이거예요. 진짜 파드 장애가 나도 이미 무시되는 목록에 한 줄 더해질 뿐이에요. 16:27 점검 이후 바뀐 건 정리 실패 4번이 더 쌓인 것뿐이에요.

**근거.** 루트 디스크 87% 사용, 50 GB 중 6.8 GB 남음. 출처는 summary.json nodeos.nodes[].disk 예요. containerd 가 이미지 45개로 38.9 GB, 파드 로그 294 MB, emptyDir 1.3 GB 를 써요. 출처는 summary.json nodeos.nodes[].cri 와 .disk 예요. `FreeDiskSpaceFailed` 가 2026-10-23T01:20Z 이후 906번, "attempted to free 3,424,603,340 bytes, found 0 bytes eligible" 이에요. 출처는 events.json 이에요. Evicted 사유의 Failed 파드 12개: prod-app-l-backend 7, prod-app-r 2, app-s-prod 2, dev-app-o 1. 출처는 objects/pods.json 이에요. KubePodNotReady 가 12개 울리고 있고 가장 긴 건 17.4일이에요. 출처는 metrics/alerts_firing_stale_days.json 이에요.

**원인.** prod 의 3분의 2를 든 노드에서 이미지, 로그, emptyDir 이 50 GB 루트 볼륨 하나를 같이 쓰고, 가장 큰 이미지는 app-l backend 1.9 GB 급이에요. kubelet 의 이미지 가비지 컬렉션은 안 쓰는 이미지만 지우는데 여기서는 모든 이미지가 돌아가는 파드 것이에요. 쫓겨난 파드는 아무것도 치우지 않아서 알림이 남아요.

**조치.** ① 문제 1 의 ④ 가 노드를 교체하면서 디스크를 한 번에 비워요. ② EC2NodeClass `default` 의 루트 볼륨을 50Gi → 100Gi 로, `encrypted: true`, `instanceStorePolicy: RAID0` 으로 바꿔 r8gd 인스턴스의 로컬 NVMe 에 이미지와 emptyDir 이 놓이게 해요. 30분 걸리고 다음 노드부터 적용돼요. 문제 5 와 같은 변경이에요. ③ 문제 1 ① 과 같은 차트 변경에서 prod 컨테이너에 `ephemeral-storage` requests 1Gi, limits 4Gi 를 넣고 embedding 서버의 모델 캐시 emptyDir 에 `sizeLimit: 4Gi` 를 넣어요. ④ Failed 파드 12개를 지워요. 5분 걸리고 클러스터를 바꾸는 일이라 제안만 해요. `kubectl delete pod -A --field-selector=status.phase=Failed`. 이러면 알림 12개가 바로 사라져요.
```yaml
# EC2NodeClass default
spec:
  blockDeviceMappings:
  - deviceName: /dev/xvda
    ebs: { volumeSize: 100Gi, volumeType: gp3, encrypted: true }
  instanceStorePolicy: RAID0
```

**왜 이런 일이 생기나.**
- 원리: kubelet 은 이미지 파일시스템을 보다가 `nodefs.available` 이 10% 아래로 가면 파드를 쫓아내요. 이미지 가비지 컬렉션은 85% 와 80% 임계값 사이에서 돌지만 어떤 컨테이너도 쓰지 않는 이미지만 지울 수 있어서, 모든 이미지가 사용 중인 노드는 사람이 공간을 더 주거나 파드를 옮길 때까지 계속 쫓아내요. 쫓겨난 파드는 누가 지우기 전까지 Failed 오브젝트로 남고, `kube_pod_status_phase` 위에 만든 Prometheus 규칙은 그걸 영원히 not ready 로 봐요.
- 사례: 이 체크에 기록된 공개 사례는 없어요.
- 더 알아보기: "Kubernetes docs: Node-pressure Eviction", "Kubernetes docs: Garbage Collection of unused containers and images", "Karpenter docs: EC2NodeClass blockDeviceMappings and instanceStorePolicy".

근거 체크: `node.disk-usage.<ip>:9100:/`, `events.tracked-warning-reasons.FreeDiskSpaceFailed`, `logs.signatures.kubelet.image-gc-failed`, `logs.signatures.containerd.shim-error`, `observability.alerts-always-firing.KubePodNotReady`, `observability.alert-firing-stale.KubePodNotReady/*` ×4, `scaling.karpenter-expired-not-replaced.default-n44bh`, `karpenter.ec2nodeclass-hardening.cluster`

### 3. prod 데이터베이스 7개에 어떤 백업도 없고, EBS 볼륨은 전부 암호화되지 않았으며, 스냅샷 경로는 끊어져 있습니다
**문제.** prod 데이터베이스 일곱 개, app-m, app-o, app-n 의 MySQL, app-q, app-p, app-s 의 PostgreSQL, app-l 의 Neo4j 가 reclaim 정책이 Delete 인 EBS 볼륨에 데이터를 둬요. 네임스페이스나 PVC 를 실수로 지우면 데이터가 같이 사라지고 되돌릴 길이 없어요. 백업 도구도, 백업 CronJob 도, AWS 의 태그 기반 EBS 스냅샷 스케줄러인 DLM 정책도, AWS Backup 플랜도 없고, VolumeSnapshot CRD 가 없어서 EBS CSI 드라이버의 스냅샷 사이드카가 오류를 계속 남겨요. 볼륨 17개와 StorageClass 넷이 전부 암호화되지 않았고 확장도 허용하지 않아서, 90% 찬 dev MySQL 볼륨 하나는 제자리에서 키울 수 없어요. 존재하는 스냅샷은 PVC 를 지우기 전에 손으로 뜬 것뿐이에요.

**근거.** prod 데이터베이스 PVC 일곱 개: app-o MySQL 48.9 GB, app-l Neo4j 19.5 GB, PostgreSQL 셋 각 9.7 GB, MySQL 둘 각 7.8 GB. 출처는 summary.json storage.pvcs 예요. EBS 볼륨 17개 280 GB 전부 gp3, 전부 암호화 안 됨. 출처는 findings-draft.json storage.ebs-unencrypted 예요. DLM 정책 0, AWS Backup 플랜 0, VolumeSnapshot 0, etcd 스냅샷 0, 백업 CronJob 0. 출처는 findings-draft.json eks.no-backup-policy 와 resilience.no-backup 이에요. 30일 안의 EBS 스냅샷 12개는 전부 "pre-delete backup of orphan PVC" 이름이에요. 출처는 findings-draft.json storage.csi-snapshot-unavailable 이에요. `dev-app-t/data-app-t-mysql-0` 은 9.7 GB 의 90.2% 고 `allowVolumeExpansion: false` 예요. 출처는 findings-draft.json storage.pvc-usage-high 예요.

**원인.** 데이터베이스를 기본 gp3 클래스로 클러스터에 옮겨 왔고 백업 층을 아무도 더하지 않았어요. EBS CSI 애드온은 스냅샷 사이드카를 싣고 오지만 CRD 를 주는 `snapshot-controller` 애드온은 설치된 적이 없어요.

**조치.** ① DLM 정책 하나를 만들어요. `kubernetes.io/created-for/pvc/namespace` 태그가 `prod-*` 또는 `app-s-prod` 인 볼륨, 매일, 14일 보존. 1시간 걸리고 오늘로 "복구 경로 없음" 이 끝나요. ② prod PV 일곱 개를 `persistentVolumeReclaimPolicy: Retain` 으로 패치하고 아래의 암호화 클래스를 `allowVolumeExpansion: true` 로 기본 클래스로 만들어요. 10분 걸려요. ③ `snapshot-controller` EKS 애드온과 VolumeSnapshotClass 를 설치해요. 30분 걸리고 사이드카 오류가 멈추며 CSI 스냅샷이 가능해져요. ④ 계정 수준 EBS 기본 암호화를 켜고 볼륨 17개를 스냅샷, 암호화 복사, 교체로 옮기면서 복구 리허설을 같이 해요. 하루 걸려요. ⑤ 네임스페이스 단위 복구를 위해 EBS CSI 스냅샷 기반 Velero 를 넣어요. 하루 걸려요.
```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3-encrypted
  annotations: { storageclass.kubernetes.io/is-default-class: "true" }
provisioner: ebs.csi.aws.com
parameters: { type: gp3, encrypted: "true" }
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
```

**왜 이런 일이 생기나.**
- 원리: reclaim 정책이 Delete 인 PersistentVolume 은 PVC 와 함께 지워지고, 네임스페이스 삭제는 그 안의 모든 PVC 를 지워요. 클러스터 밖의 스케줄로 뜬 스냅샷만이 잘못된 `kubectl delete` 와 노드 손실 둘 다에서 살아남는 유일한 사본이에요. EBS 의 저장 시 암호화는 볼륨을 만들 때 정하는 속성이라 기존 볼륨은 바꿀 수 없고 옮겨야만 해요.
- 사례: 이 체크에 기록된 공개 사례는 없어요.
- 더 알아보기: "AWS docs: Amazon Data Lifecycle Manager", "Kubernetes docs: Volume Snapshots and the snapshot controller", "Kubernetes docs: PersistentVolume reclaim policy".

근거 체크: `resilience.no-backup.cluster`, `eks.no-backup-policy.cluster`, `storage.csi-snapshot-unavailable.cluster`, `logs.signatures.ebs-csi.snapshot-crd-missing`, `storage.ebs-unencrypted.cluster`, `ebscsi.storageclass-unencrypted.cluster`, `storage.no-volume-expansion.gp3`, `storage.no-volume-expansion.gp3-2a`, `storage.no-volume-expansion.gp3-2c`, `storage.pvc-usage-high.dev-app-t/data-app-t-mysql-0`, `ecr.scan-disabled.ecr/registry/<account>`

### 4. 사용자가 보는 것을 지켜보는 알림이 없습니다. 오늘의 회수와 `api.example-b.ai` 의 0.6% 오류율은 아무도 호출하지 않았고, prod 헬스체크 넷은 아무것도 거르지 못하며, 프론트엔드 셋은 200 m CPU 제한에 막혀 있습니다
**문제.** 알림 규칙 157개가 전부 원인이나 애플리케이션 카운터를 보고, 공개 호스트의 오류 비율이나 지연 같은 사용자 증상을 보는 규칙은 0개예요. 무엇이 정상인지 말해 주는 가용성·지연 목표인 SLO 도 없어요. 오늘 네 번의 스팟 회수와 app-p 장애는 알림을 하나도 만들지 않았는데, EKS 에서는 참일 수 없는 `KubeControllerManagerDown` 과 `KubeSchedulerDown` 은 47.8일째 Slack 에 떠 있어요. 공개 API `api.example-b.ai` 는 24시간 동안 5xx 를 723번 돌려줬어요. 로드밸런서는 prod 서비스 넷의 모든 타깃을 unhealthy 로 표시해요. 헬스체크가 `/` 를 찔러 404 나 307 을 받기 때문이고, 그래서 파드가 진짜 고장 나도 아무것도 달라지지 않아요. app-m, app-o, app-n 의 Next.js 프론트엔드는 request 10 m, limit 200 m 템플릿을 같이 쓰고, app-m 프론트엔드는 지금 CPU 주기의 24% 를 멈춰 있어요. 16:27 의 27% 에서 조금 내려왔을 뿐이에요.

**근거.** 알림 규칙 157개, 증상 0, 원인 138, 앱 메트릭 19. 규칙이 없는 장애 유형 셋: OOMKill, 스케줄링 실패, VPC CNI IP 고갈. 출처는 summary.json observability.rules 와 failure_modes 예요. 120,706건 중 5xx 723건, 시간당 최대 116건, 시간당 p95 최대 5.57초. 출처는 aws/alb-metrics.json 타깃 그룹 k8s-app-svc-d65740e6d5 예요. healthy 타깃 0인 prod 타깃 그룹 넷: app-q-backend 404, app-l-backend 두 타깃 모두 404, app-o-frontend 307, app-n-frontend 307. 출처는 aws/alb-metrics.json HealthyHostCount_Minimum 이에요. 스로틀링 비율 app-m-frontend 0.24 와 0.23, Prometheus 0.28, app-p-postgresql 0.42, app-o-frontend 0.08. 출처는 metrics/cpu_throttle_ratio_5m.json 이에요. 울리는 알림 18개: KubePodNotReady 12, KubeControllerManagerDown 과 KubeSchedulerDown 47.8일, CPUThrottlingHigh 1, InfoInhibitor 2, Watchdog. 출처는 summary.json observability.alerts.firing_now 예요. `api.v1.example-b.ai` 는 86건 요청에 p95 평균 10.92초, 최대 35.36초인데 체크의 요청 수 하한 아래예요. 출처는 summary.json traffic.ingresses 예요.

**원인.** kube-prometheus-stack 기본값을 설치하고 다듬지 않았어요. 컨트롤 플레인 규칙은 직접 운영하는 컴포넌트를 전제하고, 이미 비용을 내는 ALB 메트릭 위에는 규칙을 하나도 쓰지 않았어요. 헬스체크 경로는 리다이렉트하거나 404 를 주는 앱에서 `/` 로 남았어요. 프론트엔드 템플릿은 놀고 있는 Node.js 프로세스에는 맞지만 렌더링 몰림에는 안 맞는 200 m 제한을 복사했어요. 추정입니다. app-m-backend 의 5xx 가 몰린 시간은 같은 시간에 p95 도 5초를 넘은 걸로 보아 업스트림 타임아웃으로 보여요.

**조치.** ① ALB 타깃 그룹용 YACE CloudWatch 익스포터를 넣고 공개 호스트마다 규칙 두 개를 만들어요. 5xx 비율 1% 초과 5분, p95 2초 초과 10분, `slack-sre` 로 보내요. 반나절 걸려요. 그 전까지는 `k8s-app-svc-d65740e6d5` 의 `HTTPCode_Target_5XX_Count` 에 CloudWatch 알람을 거는 데 10분 걸려요. ② 차트 values 에 `kubeControllerManager.enabled: false`, `kubeScheduler.enabled: false`, `kubeEtcd.enabled: false` 를 넣어 `KubeControllerManagerDown` 과 `KubeSchedulerDown` 을 끄고 문제 2 의 Failed 파드 12개를 지워요. 10분 걸리고 채널에 붙박이로 있던 알림 14개가 사라져요. ③ prod 인그레스 넷의 `alb.ingress.kubernetes.io/healthcheck-path` 를 실제 헬스 경로로 바꾸거나 리다이렉트하는 앱에는 `success-codes: 200-399` 를 넣어요. 20분 걸려요. ④ 공유 프론트엔드 템플릿에서 CPU limit 을 빼고 request 를 100 m 로 올리고 Prometheus 의 CPU limit 을 1 로 올려요. 20분 걸려요. app-p PostgreSQL 은 다음 점검에서 42% 가 다시 보이면 같이 해요. ⑤ 공개 호스트마다 SLO 를 하나씩 써요. 30일 동안 요청의 99.5% 가 5xx 아니고 2초 안, 그리고 번 레이트로 알림. 하루 걸려요.
```yaml
# 공유 프론트엔드 차트
resources:
  requests: { cpu: 100m, memory: 256Mi }
  limits: { memory: 384Mi }
# 인그레스 애노테이션
alb.ingress.kubernetes.io/healthcheck-path: /api/health
alb.ingress.kubernetes.io/success-codes: "200-399"
```

**왜 이런 일이 생기나.**
- 원리: 증상으로 호출하고 원인은 대시보드에 둬요. 사용자는 5xx 나 느린 응답을 느끼지 CPU 퍼센트를 느끼지 않으니, 사용자 증상으로 이어지지 않는 알림은 아무도 깨우지 않거나 모두를 헛되이 깨워요. CPU limit 은 100 ms CFS 주기마다 적용돼요. 컨테이너가 할당량을 다 쓰면 주기의 나머지를 기다리고 이건 CPU 사용량이 아니라 지연으로 나타나요. HPA 는 limit 이 아니라 request 기준으로 늘려요.
- 사례: Buffer 2020 과 Omio 2020 사례에서는 평균 CPU 는 낮은데 스로틀링이 높던 서비스에서 CPU limit 을 빼자 지연이 떨어졌어요. `resources.cpu-throttling` 체크 정의에 기록돼 있어요. 알림 체크들에는 기록된 공개 사례가 없어요.
- 더 알아보기: "Google SRE Book ch. 6, Monitoring Distributed Systems, Symptoms Versus Causes", "Google SRE Workbook ch. 5, Alerting on SLOs", "CFS bandwidth control (kernel sched-bwc)", "AWS docs: Health checks for Application Load Balancer target groups".

근거 체크: `observability.no-symptom-alerts.cluster`, `observability.no-slo.cluster`, `observability.failure-mode-uncovered.OOMKill`, `observability.failure-mode-uncovered.Scheduling failure`, `observability.failure-mode-uncovered.VPC CNI IP exhaustion`, `observability.alerts-always-firing.KubeControllerManagerDown`, `observability.alerts-always-firing.KubeSchedulerDown`, `observability.alert-firing-stale.KubeControllerManagerDown`, `observability.alert-firing-stale.KubeSchedulerDown`, `traffic.ingress-5xx-ratio.prod-app-m/app-m-backend`, `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend`, `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend`, `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend`, `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend`, `resources.cpu-throttling.prod-app-m/deploy/app-m-frontend:frontend`, `resources.cpu-throttling.prod-app-p/sts/app-p-postgresql:postgresql`, `resources.cpu-throttling.monitoring/sts/prometheus-kube-prometheus-stack-prometheus:prometheus`, `observability.stack-storage-emptydir.monitoring/loki-stack`, `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager`, `observability.loki-oomkilled.cluster`, `observability.no-event-retention.cluster`

### 5. Kubernetes 1.32 는 표준 지원이 끝난 지 217일이고, AL2 노드 이미지는 더 이상 나오지 않으며, Karpenter 0.37 은 이 버전을 지원하지 않고, 배포 도구와 데이터베이스 넷이 인터넷에서 닿습니다
**문제.** 클러스터는 Kubernetes 1.32 예요. 표준 지원은 2026-03-23 에 끝났고 연장 지원은 2027-03-23 에 끝나요. 1.33 으로의 업그레이드는 두 군데서 막혀요. Amazon 은 2025-11-26 에 Amazon Linux 2 노드 이미지 발행을 멈췄는데 Karpenter EC2NodeClass 는 아직 AL2 를 요구해서, 업그레이드 뒤에는 새 앱 노드가 뜰 수 없어요. 그리고 Karpenter 0.37.0 은 Kubernetes 1.30 까지만 지원해서 모든 스팟 회수를 처리하는 오토스케일러가 이미 지원 범위를 두 버전 벗어나 있어요. 관리형 애드온 넷이 뒤처져 있고 EBS CSI 드라이버는 마이너 30개 차이예요. 인스턴스 8대 전부 IMDS 홉 제한 2 라 파드가 노드 자격 증명에 닿아요. 배포 도구 Argo CD 는 `deploy.my-cluster` 으로 인터넷에 있고 admin 계정 하나에 SSO 없이 모든 애플리케이션이 와일드카드 프로젝트에 있어요. 클러스터 밖에서 만든 NLB 가 MySQL, PostgreSQL, Redis, Neo4j 포트를 인터넷에 열고 Kafka 외부 리스너도 열려 있어요.

**근거.** 서버 v1.32.13, 표준 지원 종료 2026-03-23 로 217일 전, 지원 유형 EXTENDED. 출처는 inventory.json cluster.eks 와 findings-draft.json platform.k8s-version-eol 이에요. EKS 업그레이드 인사이트 "Amazon Linux 2 compatibility" 가 1.33 에 ERROR. 출처는 findings-draft.json hygiene.eks-upgrade-insight 예요. EC2NodeClass `default` 는 amiFamily AL2, AMI 고정 없음, 루트 50 GB 암호화 안 됨, IMDS 홉 2. 출처는 findings-draft.json karpenter.ec2nodeclass-al2 와 karpenter.ec2nodeclass-hardening 이에요. Karpenter 0.37.0 대 Kubernetes 1.32, "version unsupported" 로그 1줄. 출처는 logs/pods/karpenter/karpenter_karpenter.log 예요. 애드온: EBS CSI v1.37.0 대 v1.67.2, VPC CNI v1.19.0 대 v1.23.2, CoreDNS v1.11.3 대 v1.11.4, kube-proxy v1.32.0 대 v1.32.13. 출처는 inventory.json cluster.eks.addons 예요. NLB `acme-db-shared` 포트 3306, 5432, 6379, 7687 이 소스 제한 없이 인터넷에, `middleware/kafka-controller-0-external` 포트 9094 도 인터넷에. 출처는 findings-draft.json traffic.db-exposed 예요. Argo CD admin 켜짐, SSO 없음, RBAC 정책 비어 있음, 애플리케이션 12개 중 12개가 소스와 목적지 `*` 인 `default` 프로젝트. 출처는 summary.json argocdctl.config 예요. API 엔드포인트가 0.0.0.0/0 에 공개. 출처는 inventory.json cluster.eks.public_access_cidrs 예요.

**원인.** 클러스터는 2025년 말 당시 기본값으로 만들어졌고 플랫폼 층은 그 뒤 손대지 않았어요. Karpenter, 노드 이미지 계열, 애드온이 설치 시점에 고정됐어요. 공유 데이터베이스 NLB 와 Argo CD 노출은 작은 팀의 편의였고 한 번도 좁혀지지 않았어요.

**조치.** ① v1 마이그레이션 가이드를 따라 Karpenter 0.37 → 1.x 로 올려요. CRD API 가 v1beta1 에서 v1 로 바뀌어요. dev 애플리케이션에서 드라이런까지 2~3시간 걸려요. ② EC2NodeClass 를 `amiFamily: AL2023` 에 고정된 `amiSelectorTerms` 별칭, `httpPutResponseHopLimit: 1`, 문제 2 의 100Gi 암호화 루트 볼륨, 업무 시간 밖에 노드 1대씩이라는 디스럽션 예산으로 바꿔요. 그러면 Drift 가 AL2 노드 여섯 대를 하나씩 교체해요. 반나절 걸리고, 파드가 옮겨 가며 흩어지도록 문제 1 ①~③ 뒤에 해요. ③ 애드온 넷을 올리고 VPC CNI 에 `ENABLE_PREFIX_DELEGATION=true` 를 주고 관리형 노드 그룹 AMI 를 새로 해요. 2시간 걸려요. ④ EKS 1.32 → 1.33 → 1.34 를 마이너 하나씩, dev 먼저 올려요. 마이너당 하루 걸려요. ⑤ NLB `acme-db-shared` 와 Kafka 리스너를 사무실·VPN CIDR 로 제한하거나 내부로 옮기고, API 엔드포인트 CIDR 을 제한하고, Argo CD 를 팀별 AppProject 와 SSO 뒤에 둬요. 반나절 걸려요.
```yaml
# EC2NodeClass default
spec:
  amiFamily: AL2023
  amiSelectorTerms: [{ alias: al2023@v20251201 }]
  metadataOptions: { httpPutResponseHopLimit: 1, httpTokens: required }
```

**왜 이런 일이 생기나.**
- 원리: Kubernetes 마이너 버전은 업스트림에서 14개월쯤 패치를 받아요. EKS 의 표준 창은 14개월이고 연장 지원이 12개월을 더하며 그 뒤에는 컨트롤 플레인이 강제로 올라가요. 노드 이미지, 오토스케일러, CNI 는 각자 지원 버전표를 내기 때문에 업그레이드는 그 전부가 목표 버전을 이미 지원할 때만 가능해요. 그래서 플랫폼 층은 클러스터보다 한 걸음 뒤가 아니라 한 걸음 앞에 있어야 해요.
- 사례: 이 체크들에 기록된 공개 사례는 없어요.
- 더 알아보기: "AWS docs: Amazon EKS Kubernetes release calendar and extended support", "Karpenter docs: v1 migration", "AWS docs: EKS-optimized Amazon Linux 2023 AMI", "AWS docs: Instance metadata service version 2 and hop limit".

근거 체크: `platform.k8s-version-eol.cluster`, `eks.extended-support.cluster`, `platform.karpenter-version-compat.cluster`, `logs.signatures.karpenter.version-unsupported`, `karpenter.ec2nodeclass-al2.cluster`, `karpenter.ec2nodeclass-hardening.cluster`, `hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility`, `eks.node-os-skew.cluster`, `eks.nodegroup-ami-old.nodegroups`, `eks.addon-outdated.aws-ebs-csi-driver`, `eks.addon-outdated.vpc-cni`, `eks.addon-outdated.coredns`, `eks.addon-outdated.kube-proxy`, `security.imds-hop-limit.cluster`, `eks.public-endpoint-open.cluster`, `traffic.db-exposed.nlb/acme-db-shared`, `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external`, `argocd.admin-account-no-sso.cluster`, `argocd.default-project-wildcard.cluster`, `argocd.components-not-ha.cluster`, `security.networkpolicy-not-enforced.cluster`, `vpccni.prefix-delegation-off.cluster`, `vpccni.node-ip-exhaustion.node-1-139`

번외로 금방 끝나는 것 하나: dev ExternalSecret `database/mysql-app-n-secret` 이 키 `dev/app-n-db` 가 없어서 2025-12-17 부터 1,639번 실패했어요. 키를 만들거나 ExternalSecret 을 지우는 데 5분 걸리고 발견 사항 다섯 개가 사라져요.

## 지난 full 점검 이후 (2026-10-26 16:27 KST)
두 점검 사이의 19분은 조용했어요. 노드가 늘거나 줄지 않았고 스팟 회수도 없었으며 Deployment, StatefulSet, Helm 릴리스 어느 것도 spec 이 바뀌지 않았어요. 멈추지 않는 카운터만 올라갔어요. `ip-10-0-1-139` 의 이미지 정리 실패 902 → 906, dev ExternalSecret 의 동기화 실패 1,638 → 1,639, 만료 노드를 붙잡는 do-not-disrupt 차단 14,163 → 14,171 이에요. 새 발견 사항 둘은 둘 다 측정값이에요. `prod-app-p` 의 PostgreSQL 이 수집 시각에 CPU 제한으로 42% 멈춰 있었는데 7일 사용은 제한의 1% 아래고 알림은 아직 pending 이라 짧은 몰아 쓰기로 보고 warn 으로 뒀고, apiserver LIST p99 0.618초는 두 수집이 19분 간격으로 겹쳐 생긴 값이에요. 16:27 에 같은 이유로 올라갔던 PATCH 지연은 돌아왔고, app-o 프론트엔드의 스로틀링은 14% 에서 8% 로 내려가 사라졌으며, app-m 프론트엔드는 27% 에서 24% 로 내려와 fail 에서 warn 이 됐어요. 셋 다 Deployment 변경 없이 트래픽만 오르내린 거예요. 룰은 0.1.50 그대로고 평가 체크도 같은 356개라 기준 변경은 없어요.

지난 리포트 문제의 진행: 문제 1 스팟 배치, request 축소, app-p-backend 레플리카 2, 토폴로지 분산, do-not-disrupt 제거, 온디맨드 폴백은 아직 손대지 않음이에요. app-p-backend 는 여전히 replicas 1 에 Recreate, generation 5 고 `ip-10-0-1-139` 는 prod 파드 42개 중 28개를 들고 있으며 `DisruptionBlocked` 는 14,171 이에요. 문제 2 `ip-10-0-1-139` 디스크 87% 와 쫓겨난 파드 12개는 아직 손대지 않음이에요. 디스크 86.4%, Failed 파드 12개, `FreeDiskSpaceFailed` 906. 문제 3 백업 없음, 암호화 안 된 볼륨, 레지스트리 스캔은 아직 손대지 않음이에요. DLM 정책 0, 볼륨 17개 중 17개 암호화 안 됨, 저장소 39개 푸시 시 스캔 꺼짐. 문제 4 증상 알림 없음, prod ALB 헬스체크 넷, emptyDir 위의 Loki 는 아직 손대지 않음이에요. 증상 규칙 0, 같은 prod 타깃 그룹 넷이 전부 unhealthy, Loki 저장소 여전히 emptyDir. 문제 5 표준 지원 끝난 Kubernetes 1.32, AL2 노드, Karpenter 0.37, 열린 Argo CD 는 아직 손대지 않음이에요. 버전 1.32.13, EC2NodeClass 여전히 AL2, Karpenter 0.37.0, SSO 없는 Argo CD admin.

## 이번에 확인 못 한 것
프로필이 기대하는 백업 도구, 이벤트 보존, SLO 정의, 클러스터 안 인증서 관리, 점진적 배포가 하나도 없어요. 세부 리포트 5절에 목록이 있어요. 이 프로필에 해당하는 체크 356개가 전부 평가됐고 EKS 에서 꺼진 체크 2개, fluent-bit 이 없어 건너뛴 체크 1개가 있으며 빠진 도구는 없어요. 실패한 명령 24개는 세부 리포트 7-1 절에 있어요. 19개는 SSM 에 등록되지 않은 관리형 노드 두 대 `ip-10-0-1-117` 과 `ip-10-0-2-60` 에서 돌린 노드 명령과 컨트롤러 메트릭 읽기라, 그 두 대의 OS 상태, kube-proxy 모드, VPC CNI 카운터는 모르고 ALB 컨트롤러, Argo CD, Grafana, Karpenter 의 메트릭은 Prometheus 에서만 왔어요. 1개는 ALB 컨트롤러 파드 프록시 읽기 타임아웃이고 4개는 라이프사이클 정책이 없는 ECR 저장소 조회예요. Grafana 데이터소스와 대시보드는 API 토큰이 없어 건너뛰었고 KEDA 오퍼레이터 메트릭은 Prometheus 엔드포인트가 꺼져 있어 건너뛰었어요. 이번 수집은 16:27 full 수집이 끝나고 19분 뒤에 시작돼서 apiserver 503 초당 0.0037 과 LIST p99 0.618초는 수집 중에 측정된 값이고 kubegap 자신의 요청이 섞였을 가능성이 커요. 둘 다 사용자 영향으로 세지 않았어요. p95 가 10초를 넘는 prod 호스트 둘, 86건 요청의 `api.v1.example-b.ai` 와 7건의 `app-r.my-cluster` 은 지연 체크의 요청 수 하한 아래라 발견 사항이 아니라 이 리포트에만 적혀 있어요. 컨테이너 로그 자체는 수집 범위 밖이라 app-p PostgreSQL 이 수집 시각에 무엇을 하고 있었는지는 몰라요.

## 숫자
| 심각도 | fail | warn | 지난 full 점검 대비 |
|---|---|---|---|
| critical | 2 | 3 | ±0 (같은 다섯: 백업 없음, 네 번의 회수로 올린 prod 집중, 규칙 ③ 으로 올린 N+1, SLO 없음, 증상 알림 없음) |
| high | 38 | 10 | fail −1 (16:27 리포트 39): 새로 뜬 app-p-postgresql 스로틀링을 medium warn 으로 내렸고, app-m-frontend 스로틀링이 fail 에서 warn 으로 내려갔어요. warn ±0: 1차 20 → 10, 16:27 과 같은 11개를 내리고 app-m 5xx 비율을 올렸어요 |
| medium | 105 | 160 | fail ±0 (16:27 105). warn +1 (16:27 159): 1차 171 에 high 에서 내린 6개와 app-p-postgresql 을 더하고 low 나 high 로 옮긴 18개를 뺐어요 |
| low | 18 | 161 | fail ±0 (16:27 18). warn ±0 (16:27 161): 1차 140 에 prod-without-quota 13개, CI 러너, LIST 지연, 새 노드 네트워크 오류, 어드민 5xx 비율, 계정 쿼터, 시스템 노드 IP 2개, 오래된 Prometheus OOM 을 더했어요 |
| info | 3 | 0 | fail ±0 (16:27 3): 감사 로그 꺼짐, 점진적 배포 없음, 삭제된 노드 `ip-10-0-2-149` 의 네트워크 오류 |

최종 critical+high 53개는 1차 61개보다 8개 적어요. `history.csv` 는 1차 기준이에요.

세부, 모든 표와 전체 1차 목록: [`report-details.md`](report-details.md) · kubegap 0.1.0, 룰 0.1.50 · 스냅샷 `~/.kubegap/snapshots/my-cluster/2026-10-26T16-47-02`
