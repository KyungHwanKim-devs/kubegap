# my-cluster — full 점검, 2026-11-05 17:18

지금 급한 일: 없음

오늘 할 일 5개: ① 운영 DB 7개에 백업이 없음 ② 스팟 노드 한 대에 몰린 prod 파드와 막힌 만료 교체 ③ 인터넷 전체에 열린 Kafka 외부 리스너 ④ prod 대상 그룹 4개의 ALB 헬스 체크 실패 ⑤ 지원 범위를 벗어난 EKS 1.32, Karpenter 0.37, AL2

지난 점검 이후:

- 지시한 일을 했는지: 2026-11-03 점검에는 리포트가 없어서 확인할 수 없어요.
- 새로 생긴 것 7개: build-arm64 스팟 노드 node-2-158이 새로 떴어요. node-1-62 디스크가 79%예요. app-o-frontend 스로틀링, app-l 워커의 요청 과다, app-m-frontend 5xx 0.14%, Grafana p95 2.8초, API 서버 503이 새로 보여요.
- 사라진 것 5개: node-2-144 노드가 떠났어요. Promtail 메모리 문제, kafka-exporter Not Ready, 노드 두 대의 네트워크 오류, 10-06 Prometheus OOM 기록이 없어졌어요.

## 클러스터 한눈에

| 항목 | 값 |
|---|---|
| 노드 | 8대 중 Ready 8대 |
| 파드 | 실행 139, 대기 0, 실패 0 |
| 네임스페이스 | 25개, 프로덕션 8개 |
| 컴포넌트 | 23: actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| 메트릭·로그 저장소 | prometheus 2.49.1 / loki 2.6.1 |
| Kubernetes | v1.32.13-eks-577a51e (eks) |

## 다가오는 일

| 언제 | 무엇 | 출처 |
|---|---|---|
| 2026-11-07 21:31 KST | system-ondemand 풀 노드 node-1-241(NodeClaim system-ondemand-mxf5q)이 expireAfter 720h에 닿아 교체돼요. prod-app-p/app-p-postgresql-0(레플리카 1, us-east-1a 볼륨)이 다른 노드로 옮겨지는 동안 멈춰요. emptyDir에 있는 loki-stack-0의 로그도 사라져요. | summary.json |
| 2026-11-07 21:32 KST | 노드 node-2-218(NodeClaim system-ondemand-jvbnl)이 만료돼 교체돼요. prod-app-q/app-q-backend-postgresql-0(레플리카 1, us-east-1c 볼륨)과 emptyDir을 쓰는 Alertmanager가 옮겨져요. 풀 예산이 10%라 앞의 노드와 한 대씩 차례로 교체돼요. | summary.json |
| 2026-11-08 15:28 KST | 노드 node-2-135(NodeClaim system-ondemand-db9bj)가 만료돼 교체돼요. middleware/kafka-controller-0(브로커 1대)과 prod-app-l-backend/app-l-neo4j-0이 옮겨지는 동안 멈춰요. | summary.json |
| 2026-11-07 | 지난달 지운 고아 PVC를 지우기 전에 떠 둔 EBS 스냅샷 12개에 delete-after 2026-11-07 태그가 붙어 있어요. 자동으로 지우는 정책은 없지만, 이 날짜에 누가 지우면 그 데이터의 마지막 사본이 없어져요. | aws/ec2-snapshots-30d.json |
| 2026-12-03 | 쓰이지 않는 ACM 인증서 acmeai.kr이 만료돼요. 갱신 대상이 아니에요. | aws/acm-certificates.json |
| 2027-03-23 | EKS 1.32의 확장 지원이 끝나요. 표준 지원은 2026-03-23에 이미 끝나서 지금은 확장 지원 요금을 내고 있어요. | aws/describe-cluster-versions.json |

## 1. 운영 DB 7개에 백업이 없음

**상황.** prod DB는 7개예요. MySQL 3개, PostgreSQL 3개, Neo4j 1개예요. 모두 레플리카 1개이고, 데이터는 EBS 볼륨 한 개에만 있어요. 2026-11-05 17:18 KST에 수집한 결과, 계정에도 클러스터에도 백업 장치가 하나도 없어요. 볼륨이 망가지거나 지워지면 되돌릴 사본이 없어요.

- 영향 있음: 아래 7개 DB예요. 모두 reclaimPolicy Delete라서 PVC가 지워지면 볼륨도 바로 지워져요.
  - prod-app-p/app-p-postgresql: vol-0123456789abcdef0, 10Gi, us-east-1a 존. 노드 node-1-241이 2026-11-07 21:31 KST에 만료돼요.
  - prod-app-q/app-q-backend-postgresql: vol-0123456789abcdef0, 10Gi, us-east-1c 존. 노드 node-2-218이 2026-11-07 21:32 KST에 만료돼요.
  - prod-app-l-backend/app-l-neo4j: vol-0123456789abcdef0, 20Gi, us-east-1c 존. 노드 node-2-135가 2026-11-08 15:28 KST에 만료돼요.
  - prod-app-o/app-o-backend-mysql: vol-0123456789abcdef0, 50Gi, us-east-1a 존, 노드 node-1-117
  - app-s-prod/app-s-backend-postgresql: vol-0123456789abcdef0, 10Gi, us-east-1a 존, 노드 node-1-117
  - prod-app-m/app-m-backend-mysql: vol-0123456789abcdef0, 8Gi, us-east-1c 존, 노드 node-2-60
  - prod-app-n/app-n-backend-prod-mysql: vol-0123456789abcdef0, 8Gi, us-east-1c 존, 노드 node-2-60
- 확인했고 멀쩡: EBS 볼륨은 노드와 따로 있어요. 노드가 만료돼 교체돼도 데이터는 남아요.
- 다른 이유로 바뀜: 위의 노드 세 대가 Karpenter 만료 교체로 11-07 밤과 11-08 오후에 바뀌어요. 그때 DB 파드 3개가 다른 노드로 옮겨져요. node-1-241에 있는 monitoring/loki-stack-0은 영구 볼륨이 없어서, 그동안 쌓인 로그가 사라질 수 있어요.
- 안 봄: 클러스터 밖에서 도는 덤프가 있는지, 각 DB의 데이터 크기와 쓰기량, 복원해 본 적이 있는지

**이유.** 백업을 만드는 장치가 하나도 없어요. 볼륨은 동적 프로비저닝 기본값인 reclaimPolicy Delete로 만들어졌어요. 확인됨.

**권하는 조치.**

① 백업이 정말 없는지 다시 확인하세요.

```
aws dlm get-lifecycle-policies --profile acme --region us-east-1
```

```
aws backup list-backup-plans --profile acme --region us-east-1
```

읽기만 해요.

확인: 두 결과가 모두 빈 목록이면 백업이 없는 거예요. 다른 계정이나 다른 리전의 백업, 클러스터 밖의 덤프 스크립트는 이 명령으로 보이지 않아요.

② 내일 2026-11-07이 되기 전에, 2026-10-06에 뜬 스냅샷 12개를 아무도 지우지 않게 팀에 알려 두세요.

이 스냅샷 12개에는 모두 delete-after 2026-11-07 태그가 붙어 있어요. 자동으로 지우는 정책은 없지만, 태그를 보고 누가 손으로 지울 수 있어요.

그중에는 이미 지운 prod 볼륨의 유일한 사본이 있어요. 해당하는 볼륨은 prod-app-m의 admin, frontend, api, backend-prod mysql, prod-app-o의 backend-prod, frontend-prod mysql, app-s-prod의 backend-prod, frontend-prod mysql이에요. 한 번 지우면 되돌릴 수 없어요.

확인: 11-07이 지난 뒤에도 스냅샷 12개가 남아 있으면 돼요.

③ 2026-11-07 21:31 KST에 노드가 만료되기 전에, prod DB 볼륨 7개의 스냅샷을 지금 떠 두세요.

```
for v in vol-0123456789abcdef0 vol-0123456789abcdef0 vol-0123456789abcdef0 vol-0123456789abcdef0 vol-0123456789abcdef0 vol-0123456789abcdef0 vol-0123456789abcdef0; do aws ec2 create-snapshot --profile acme --region us-east-1 --volume-id "$v" --description "manual prod db backup 2026-11-06" --tag-specifications 'ResourceType=snapshot,Tags=[{Key=purpose,Value=manual-prod-db-backup}]'; done
```

EBS 스냅샷 7개가 생겨요. 파드와 볼륨은 그대로이고, 재시작도 없어요. 스냅샷 저장 요금이 붙어요.

DB를 멈추지 않고 뜨기 때문에, 전원이 갑자기 꺼진 순간의 디스크 상태 그대로 찍혀요. MySQL과 PostgreSQL은 보통 시작할 때 복구 과정을 거쳐 열려요. 하지만 Neo4j community가 이런 스냅샷으로 열리는지는 검증되지 않았어요.

볼륨이 암호화돼 있지 않아서 스냅샷도 암호화되지 않아요. 이 스냅샷으로 복원해 본 적은 없어요. Kafka 데이터 볼륨 data-kafka-controller-0은 20Gi, Delete인데 이 7개에 들어 있지 않아요.

확인: 아래 명령 결과에서 7줄이 모두 completed면 끝이에요.

```
aws ec2 describe-snapshots --profile acme --region us-east-1 --owner-ids self --filters Name=tag:purpose,Values=manual-prod-db-backup --query 'Snapshots[].[VolumeId,State]' --output table
```

④ prod DB PV 7개의 reclaimPolicy를 Retain으로 바꾸세요.

```
for pv in pvc-1a304f49-fa2e-43ed-a996-df104613c88c pvc-5cccf1df-7624-45a2-833d-2191c5490713 pvc-8d1f15c7-e0e6-4410-bd40-64d7332aef0d pvc-9f1aab56-d94c-499d-8df6-2def93e79427 pvc-a50dcc70-b062-457a-b0e3-07a3e6da2ec6 pvc-ebc5618b-a1af-40d3-b15d-4969ed13487e pvc-f226562f-a020-4027-a0d4-1494585c8b6f; do kubectl --context my-cluster patch pv "$pv" -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'; done
```

PV 스펙 한 줄만 바뀌고, 파드 재시작은 없어요. 이제 PVC가 지워져도 EBS 볼륨은 남아요.

PV에는 Argo CD 추적 라벨이 없어서, selfHeal이 이 변경을 되돌리지 않아요. 대신 PVC를 지운 뒤 남은 볼륨은 손으로 지울 때까지 요금이 계속 나와요.

확인: 아래 명령 결과에서 7개가 모두 Retain이면 돼요.

```
kubectl --context my-cluster get pv -o custom-columns=NAME:.metadata.name,CLAIM:.spec.claimRef.name,POLICY:.spec.persistentVolumeReclaimPolicy
```

⑤ 매일 자동으로 도는 백업을 계획하세요.

- DLM 정책이나 AWS Backup 계획을 만들어요. 태그가 KubernetesCluster=my-cluster인 볼륨을 매일 스냅샷하고 7~14일 보관해요.
- DB마다 mysqldump, pg_dump, neo4j-admin 덤프를 S3로 보내는 CronJob을 만들어요.
- 스냅샷 하나를 새 볼륨으로 복원해서 DB가 열리는지 시험해요.

덤프를 DB와 같은 노드 디스크에만 저장하면, 노드가 사라질 때 덤프도 같이 사라져요. Neo4j community는 온라인 백업이 없어서, 덤프하려면 DB를 멈춰야 할 수 있어요. 이건 검증되지 않았어요.

태그로 볼륨을 고르면 Prometheus, vm-single 같은 다른 볼륨도 함께 찍혀서 요금이 늘어요.

확인: `aws dlm get-lifecycle-policies` 결과에 ENABLED 정책이 하나 있고, 다음 날 스냅샷이 7개 이상 생기면 돼요.

**되돌리기.** 스냅샷은 `aws ec2 delete-snapshot --profile acme --region us-east-1 --snapshot-id <snapshot-id>`로 지우면 돼요. reclaimPolicy는 ④ 명령에서 Retain을 Delete로 바꿔 다시 실행하면 원래대로 돌아가요. ⑤에서 만든 DLM 정책이나 AWS Backup 계획은 DISABLED로 바꾸거나 지우면 돼요. 어느 조치도 데이터를 지우지 않아요.

**왜 이런 일이 생기나.**

- 원리: 볼륨은 노드가 죽어도 남아요. 하지만 잘못 지우거나 망가지면 복구할 수단은 스냅샷뿐이에요. reclaimPolicy가 Delete면 네임스페이스 삭제나 Argo CD prune 한 번에 볼륨이 바로 사라져요.
- 사례: 2023년 InfluxData에서 자동화가 Argo CD Application 이름을 잘못 만들어 운영 환경 하나가 통째로 지워졌어요. 볼륨이 Retain이었고 백업도 있어서 데이터를 잃지 않았어요. 이 클러스터의 prod 앱 8개도 Argo CD가 prune, selfHeal로 관리해요. 그런데 DB 볼륨은 Delete이고 백업도 없어요.
- 읽을 것: Amazon Data Lifecycle Manager 사용 설명서, Kubernetes 문서의 Persistent Volumes Reclaim Policy

**근거.**

| 항목 | 값 | 출처 |
|---|---|---|
| DLM 수명 주기 정책 | 0개 | aws/dlm-lifecycle-policies.json |
| AWS Backup 계획 | 0개 | aws/backup-plans.json |
| 클러스터 안 백업 CronJob, 최근 7일 | 0개 | summary.json resilience.backup.count |
| 백업 CronJob이 없는 prod DB | 7개 | summary.json resilience.backup |
| prod DB PV reclaimPolicy | 7개 모두 Delete | objects/persistentvolumes.json |
| 10-06 스냅샷, delete-after 2026-11-07 | 12개 | aws/ec2-snapshots-30d.json |

## 2. 스팟 노드 한 대에 몰린 prod 파드와 막힌 만료 교체

**상황.** 스팟 노드 node-1-139에 prod 파드 42개 중 20개가 있어요. 2026-11-05 17:18 KST 수집 기준이고, 노드는 r8gd.xlarge, us-east-1a 존이에요. 이 노드는 만료 시점을 301.9시간 넘겼어요. 그런데 app-m-admin 파드의 do-not-disrupt 어노테이션 때문에 Karpenter가 교체하지 못하고 있어요.

스팟 회수가 한 번만 일어나도 아래 서비스들이 한꺼번에 멈춰요. 이 노드는 ENI 4개를 다 써서 'no available IP'도 4번 났어요.

- 영향 있음: 레플리카가 전부 이 노드에 있는 워크로드
  - prod-app-o/app-o-ai: 3개 모두 여기 있어요. topologySpread, PDB, readiness probe가 모두 없어요.
  - prod-app-o/app-o-backend: 2개 모두 여기 있어요. PDB와 readiness probe가 없어요.
  - prod-app-r/app-r: 2개 모두 여기 있어요. PDB는 minAvailable 1이에요.
  - prod-app-l-backend/app-l-frontend: 2개 모두 여기 있어요. preferred podAntiAffinity가 있지만 지켜지지 않았어요.
  - 레플리카 1개인 prod 워크로드 6개: app-m-admin, app-o-admin, app-o-frontend, app-p-backend, app-n-admin-frontend, app-s-backend
- 확인했고 멀쩡: prod-app-m의 api, backend, frontend는 node-1-139와 node-1-62에 나뉘어 있어요. 다만 두 노드 모두 us-east-1a 존이에요. Karpenter 컨트롤러 2개는 두 노드에 나뉘어 있고 PDB도 있어요. 수집 시점의 Pending 파드는 0개예요.
- 다른 이유로 바뀜: 지난 24시간 동안 노드 41대가 떠났어요. Karpenter가 app-l 워커용 노드를 비었을 때 지우거나 통합하면서 정리한 거예요.
- 안 봄: 이 노드가 지난 42일 동안 스팟 회수 경고를 받은 적이 있는지, 레플리카 1개인 서비스들의 실제 사용자 트래픽

**이유.** app-m-admin 파드 템플릿에 `karpenter.sh/do-not-disrupt: "true"`가 있어서 Karpenter가 이 노드를 비우지 못해요. 또 prod Deployment에 topologySpreadConstraints가 없어서, 스케줄러가 남은 자리가 큰 이 노드에 파드를 계속 모았어요. 확인됨. 어노테이션을 왜 넣었는지는 몰라요.

**권하는 조치.**

① 이 노드에 무엇이 있고, 왜 교체가 막혔는지 확인하세요.

```
kubectl --context my-cluster get pods -A -o wide --field-selector spec.nodeName=node-1-139
```

```
kubectl --context my-cluster get events -A --field-selector involvedObject.name=default-n44bh
```

읽기만 해요.

확인: 파드가 38개 나오고, DisruptionBlocked 이벤트에 app-m-admin이 나오면 돼요.

② IAC 저장소에서 네 워크로드를 분산하세요. app-o-ai, app-o-backend, app-r, app-l-frontend에 hostname 기준 topologySpreadConstraints를 넣어요. app-o-ai와 app-o-backend에는 PDB도 더해요.

```yaml
# Deployment spec.template.spec 에 추가 (app-o-ai 예시, 나머지는 matchLabels만 바꿔요)
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app.kubernetes.io/instance: app-o-prod
        app.kubernetes.io/name: ai
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-o-ai
  namespace: prod-app-o
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/instance: app-o-prod
      app.kubernetes.io/name: ai
```

Argo CD가 동기화하면 네 Deployment가 롤링 업데이트돼요. 새 파드는 node-1-62나 Karpenter가 새로 띄운 app 노드로 가요.

selfHeal이 켜져 있어서 kubectl로 바꾸면 되돌아가요. 그래서 저장소에서 바꿔야 해요. 차트의 값 이름이 이 스니펫과 같은지는 검증되지 않았어요.

app-o 워크로드는 readiness probe가 없어요. 그래서 새 파드가 뜨자마자 Ready로 세어지고, 앱이 준비되기 전에 들어온 요청은 실패할 수 있어요.

app-o-ai는 파드당 메모리 2Gi를 요청하는데, node-1-62에 남은 CPU는 0.26코어예요. 그래서 새 노드가 필요할 수 있어요. maxUnavailable이 0이라 새 파드가 뜰 때까지 옛 파드가 남아 있어요.

확인: `kubectl --context my-cluster -n prod-app-o get pods -o wide`에서 ai와 backend 파드가 두 노드 이상에 나뉘어 있으면 돼요. `kubectl --context my-cluster -n prod-app-o get pdb`에 app-o-ai와 app-o-backend가 보여야 해요.

③ ②가 끝나면, 트래픽이 적은 시간에 app-m-admin의 do-not-disrupt 어노테이션을 지우세요. 그 전에 어노테이션을 넣은 사람에게 이유를 먼저 물어보세요. 바꿀 곳은 IAC 저장소 apps/prod/app-m예요.

```yaml
# app-m-admin 파드 템플릿 어노테이션에서 이 줄을 지워요 (값 파일의 키 이름은 미검증)
karpenter.sh/do-not-disrupt: "true"
```

app-m-admin이 롤링 업데이트돼요. 그러면 Karpenter가 node-1-139를 교체해요. 새 노드를 먼저 띄우고, PDB를 지키면서 파드 38개를 내보내요. 한 번에 한 대씩 교체돼요.

레플리카 1개인 prod 워크로드 6개는 새 파드가 Ready가 될 때까지 멈춰요. 그중 app-o-admin, app-o-frontend, app-n-admin-frontend, app-s-backend는 readiness probe가 없어요.

external-secrets 컨트롤러와 dev 파드 12개도 함께 옮겨져요. external-secrets 컨트롤러는 레플리카가 1개예요. 새 노드도 스팟일 수 있어요. 어노테이션이 긴 관리 작업을 지키려고 넣은 것이었다면, 그 작업이 끊겨요.

확인: `kubectl --context my-cluster get nodeclaims`에서 default-n44bh가 사라지고, ①의 첫 명령 결과가 빈 목록이면 끝이에요.

④ 같은 일이 반복되지 않게 계획하세요.

- prod 앱 차트 공통값에 hostname과 zone 기준 topologySpreadConstraints를 기본으로 넣어요.
- NodePool default의 인스턴스 크기를 제한하거나, prod용 on-demand 풀을 따로 둬요.
- VPC CNI prefix delegation을 켜서 ENI 한도에 덜 걸리게 해요.

Drift가 켜져 있어서 NodePool 요구 조건을 바꾸면 default 풀 노드가 한 대씩 교체돼요. on-demand로 바꾸면 비용이 늘어요. prefix delegation은 노드를 새로 띄워야 적용돼요.

확인: 다음 점검에서 한 노드에 몰린 prod 파드 비율이 0.3 아래로 내려가면 돼요.

**되돌리기.** IAC 저장소에서 커밋을 되돌리면 Argo CD가 원래대로 돌려요. 이미 교체된 노드는 되돌릴 수 없지만, 되돌릴 필요도 없어요.

**왜 이런 일이 생기나.**

- 원리: 레플리카를 2개 두는 건 하나가 죽어도 버티기 위해서예요. 그런데 둘이 같은 노드에 있으면 노드와 함께 사라져요. 분산을 선언하지 않으면 스케줄러와 Karpenter 통합이 파드를 한 노드로 모아요.
- 사례: Moonlight에서 웹사이트 파드 3개가 같은 노드에 몰렸어요. 그 노드가 커널 패닉을 일으켰고, 1월 18일부터 22일까지 서비스가 끊겼다 이어지기를 반복했어요. anti-affinity로 고쳤어요. 여기서도 app-o-ai, app-o-backend, app-r, app-l-frontend가 스팟 노드 한 대에 모여 있어요.
- 읽을 것: Kubernetes 문서의 Pod Topology Spread Constraints, Karpenter 문서의 Disruption

**근거.**

| 항목 | 값 | 출처 |
|---|---|---|
| node-1-139의 prod 파드 | 20개 | summary.json resilience.placement |
| 전체 prod 파드 42개 중 비중 | 0.48 | summary.json resilience.placement |
| 만료를 넘긴 시간 | 301.9시간 | summary.json scaling.karpenter.nodeclaims[1] |
| do-not-disrupt로 교체가 막힌 횟수, 누적 | 21337회 | summary.json scaling.karpenter.nodeclaims[1] |
| 스팟 회수로 지운 NodeClaim, 2026-08-28 이후 | 261개 | summary.json karpenterctl.metrics |
| node-1-62에 남은 CPU | 0.26코어 | summary.json resilience.n_plus_one |

## 3. 인터넷 전체에 열린 Kafka 외부 리스너

**상황.** middleware/kafka-controller-0-external Service가 인터넷용 NLB를 만들었어요. 보안 그룹은 9094와 443 포트를 0.0.0.0/0에 열어 뒀어요. 클라이언트 인증 사용자인 SASL은 설정돼 있지만, 외부 리스너가 TLS를 쓰는지는 몰라요.

NLB는 24시간 동안 약 2.87GB를 처리했고, 동시 연결이 최대 146개였어요. 실제로 쓰이는 연결이에요.

- 영향 있음: middleware/kafka-controller, 브로커 1대. NLB의 프런트 SG sg-0123456789abcdef0가 두 포트를 0.0.0.0/0에 열고 있어요.
- 확인했고 멀쩡: 공용 DB NLB acme-db-shared는 포트마다 /32 주소 4개 이하로만 열려 있어요. middleware에는 Argo 앱이 없어서, 변경을 되돌리는 건 Helm뿐이에요.
- 다른 이유로 바뀜: 아직 없어요. 다만 2026-11-08 15:28 KST에 node-2-135가 만료되면, 조치와 상관없이 브로커가 다시 떠요. 그때 새 노드에서 docker.io/bitnamilegacy 이미지를 다시 받아야 하고, Kafka 지연을 보는 app-o-ai의 KEDA도 영향을 받아요.
- 안 봄: 어떤 외부 주소가 붙는지, TLS를 쓰는지, 브로커 로그의 인증 실패 기록, 지금 Helm values에 이미지 덮어쓰기가 들어 있는지

**이유.** Helm 릴리스 kafka의 외부 접근 설정이 출발 주소를 제한하지 않은 채 인터넷용 NLB를 만들었어요. 그래서 AWS Load Balancer Controller가 보안 그룹을 0.0.0.0/0으로 열었어요. 이 릴리스는 bitnami kafka 26.8.1이에요. 확인됨.

**권하는 조치.**

① 외부 리스너가 어떤 프로토콜을 쓰는지 리스너 줄만 읽어 보세요.

```
kubectl --context my-cluster -n middleware get configmap kafka-controller-configuration -o jsonpath='{.data.server\.properties}' | grep -E '^(listeners|advertised\.listeners|listener\.security\.protocol\.map)='
```

읽기만 해요. 출력은 이 세 줄뿐이에요.

확인: listener.security.protocol.map에서 EXTERNAL이 SASL_SSL이면 암호화돼 있어요. SASL_PLAINTEXT나 PLAINTEXT면 비밀번호와 데이터가 암호화되지 않은 채 인터넷을 지나가요.

② 외부에서 붙는 클라이언트를 찾으세요. 먼저 Kafka 담당자에게 물어보세요. 답이 없으면 NLB 서브넷에 VPC Flow Logs를 하루 켜서 9094, 443으로 들어오는 출발 주소를 모으면 돼요.

흐름 로그 저장 요금이 붙어요. 다 모은 뒤에는 꼭 끄세요.

확인: 출발 주소 목록이 나오면 돼요.

③ 외부 클라이언트 주소를 모두 알아낸 뒤에, 외부 Service의 loadBalancerSourceRanges를 그 주소들로 좁히세요.

먼저 지금 값을 받아요.

```
helm --kube-context my-cluster -n middleware get values kafka -o yaml > kafka-values-current.yaml
```

받은 파일에 아래 내용을 더해요. 키 이름은 검증되지 않았어요.

```yaml
externalAccess:
  controller:
    service:
      loadBalancerSourceRanges:
        - <client-ip>/32
```

바꾸기 전과 바꾼 뒤의 매니페스트를 만들어 비교해요.

```
helm --kube-context my-cluster -n middleware get manifest kafka > kafka-manifest-before.yaml
```

```
helm --kube-context my-cluster -n middleware template kafka <차트 위치>/kafka --version 26.8.1 -f kafka-values-current.yaml > kafka-manifest-after.yaml
```

```
diff kafka-manifest-before.yaml kafka-manifest-after.yaml   # Service kafka-controller-0-external 의 loadBalancerSourceRanges 말고 차이가 없어야 해요
```

차이가 그것뿐일 때만 적용해요.

```
helm --kube-context my-cluster -n middleware upgrade kafka <차트 위치>/kafka --version 26.8.1 -f kafka-values-current.yaml
```

NLB 보안 그룹의 0.0.0.0/0 규칙이 받은 주소들로 바뀌어요. 목록에 없는 곳에서 오는 연결은 끊겨요.

지금 values는 이미지를 docker.io/bitnamilegacy로 덮어쓰고 있어요. 이 값이 빠진 채 upgrade하면 하나뿐인 브로커가 재시작돼요. 기본 이미지를 받지 못하면 Kafka 전체가 멈춘 채로 남아요. 그래서 diff를 꼭 봐야 해요.

sg-0123456789abcdef0는 ALB와 함께 쓰는 백엔드 SG라서 손으로 고치지 마세요. 2026-11-08 15:28 KST 노드 만료와 겹치지 않게 시간을 잡으세요.

확인: 아래 명령 결과에 0.0.0.0/0이 없으면 끝이에요.

```
aws ec2 describe-security-groups --profile acme --region us-east-1 --group-ids sg-0123456789abcdef0 sg-0123456789abcdef0 --query 'SecurityGroups[].IpPermissions[].IpRanges'
```

**되돌리기.** `helm --kube-context my-cluster -n middleware rollback kafka <이전 리비전>`으로 되돌리면 보안 그룹이 다시 열려요. 흐름 로그는 지우면 돼요.

**왜 이런 일이 생기나.**

- 원리: 메시지 큐 포트가 인터넷용 로드밸런서에 열려 있으면, 데이터를 지키는 건 비밀번호 하나뿐이에요. AWS에서는 로드밸런서 보안 그룹이 누가 붙을 수 있는지 정해요. 내부 스킴이나 VPN을 쓰는 편이 더 안전해요.
- 읽을 것: AWS Load Balancer Controller 문서의 Service annotations와 loadBalancerSourceRanges, Apache Kafka 문서의 Security

**근거.**

| 항목 | 값 | 출처 |
|---|---|---|
| 9094 인바운드 규칙 CIDR | 0.0.0.0/0 | summary.json traffic.alb.lbs[0] |
| NLB 처리량, 24시간 | 2868958720바이트 | summary.json traffic.alb.lbs[0] |
| NLB 최대 동시 연결, 24시간 | 146개 | summary.json traffic.alb.lbs[0] |
| 열린 포트 | 9094 | summary.json traffic.db_exposed[0] |

## 4. prod 대상 그룹 4개의 ALB 헬스 체크 실패

**상황.** 공유 ALB acme-prod-lb에 있는 prod 대상 그룹 4개의 대상이 전부 unhealthy예요. 헬스 체크가 기본 경로 /로 가는데, 앱이 200을 돌려주지 않기 때문이에요. 대상이 모두 실패하면 ALB는 모든 대상에 트래픽을 그냥 보내요. 그래서 지금 서비스는 응답하지만, 죽은 파드도 걸러내지 못해요.

- 영향 있음:
  - prod-app-q/app-q-backend: 대상 1개가 /에 404를 돌려줘요. 파드 readiness /health는 통과해요.
  - prod-app-l-backend/app-l-backend: 대상 2개가 /에 404를 돌려줘요. readiness /health는 통과해요.
  - prod-app-o/app-o-frontend: 대상 1개가 307을 돌려줘요. readiness probe가 없어요.
  - prod-app-n/app-n-frontend: 대상 1개가 307을 돌려줘요. readiness probe가 없어요. 24시간 동안 4xx 1482건, 5xx 26건이 났어요.
  - dev 대상 그룹 2곳도 실패하지만 prod는 아니에요.
- 확인했고 멀쩡: 같은 네임스페이스의 app-q-ai, app-q-studio, app-q-web은 healthcheck-path /health를 써요.
- 다른 이유로 바뀜: 없음
- 안 봄: 프론트엔드 두 곳에서 200을 돌려주는 경로, /health가 200을 주는지 3xx를 주는지

**이유.** 네 Ingress에 `alb.ingress.kubernetes.io/healthcheck-path`가 없어서 ALB가 /를 검사해요. 그런데 이 앱들은 /에 404나 307을 돌려줘요. 확인됨.

**권하는 조치.**

① 대상 그룹의 헬스 상태를 AWS에서 직접 보세요.

```
aws elbv2 describe-target-health --profile acme --region us-east-1 --target-group-arn $(aws elbv2 describe-target-groups --profile acme --region us-east-1 --names k8s-app-svc-36f816b829 --query 'TargetGroups[0].TargetGroupArn' --output text)
```

읽기만 해요. 나머지 세 곳은 이름만 바꿔서 실행하면 돼요.

- k8s-app-svc-bb495c72c8
- k8s-app-svc-8c88bb317a
- k8s-app-svc-032c25d752

확인: State가 unhealthy, Reason이 Target.ResponseCodeMismatch로 나와요.

② IAC 저장소에서 app-q-backend와 app-l-backend Ingress에 헬스 체크 경로 /health를 넣으세요.

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/healthcheck-path: /health
```

두 대상 그룹의 헬스 체크 경로만 바뀌고, 파드 재시작은 없어요. 대상이 healthy가 되면 ALB는 healthy 대상에만 트래픽을 보내요.

Ingress 40개가 ALB 그룹 acme-prod-lb 하나를 같이 써요. 한 Ingress의 어노테이션이 잘못되면 그룹 전체 조정이 멈출 수 있어요.

ALB는 200만 성공으로 봐요. /health가 3xx를 주면 여전히 실패해요. /health가 DB까지 확인하는 경로라면, DB가 내려갈 때 대상이 전부 실패해 지금 상태로 돌아가요.

selfHeal 때문에 저장소에서 바꿔야 해요.

확인: ① 명령에서 State가 healthy로 나오면 돼요.

③ 프론트엔드 두 곳에서 200을 돌려주는 경로를 찾으세요.

```
kubectl --context my-cluster -n prod-app-n port-forward deploy/app-n-frontend 3000:3000
```

다른 터미널에서 실행해요.

```
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/
```

로컬 포트 포워딩만 열어요. 클러스터는 바뀌지 않아요. app-o-frontend는 prod-app-o에서 포트 3003으로 같은 방법을 쓰면 돼요.

확인: 200을 돌려주는 경로를 찾으면 돼요.

④ ③에서 200 경로를 찾았다면, 두 프론트엔드에 그 경로를 넣으세요. Ingress에는 healthcheck-path로, Deployment에는 readinessProbe로 넣어요.

```yaml
# Ingress
alb.ingress.kubernetes.io/healthcheck-path: <200-path>
# Deployment containers[0]
readinessProbe:
  httpGet:
    path: <200-path>
    port: http
  periodSeconds: 10
```

Ingress는 대상 그룹 설정만 바뀌어요. readinessProbe를 더하면 롤링 업데이트가 돌고, 새 파드가 먼저 떠요.

경로가 틀리면 새 파드가 Ready가 되지 못해 롤아웃이 멈춰요. 600초 뒤 ProgressDeadlineExceeded만 붙고, 쿠버네티스가 알아서 되돌리지는 않아요. 그동안에는 옛 파드가 계속 응답해요.

확인: `kubectl --context my-cluster -n prod-app-n rollout status deploy/app-n-frontend`가 끝나고, ① 명령에서 healthy가 나오면 돼요.

**되돌리기.** 저장소에서 커밋을 되돌리면 Argo CD가 헬스 체크를 /로 돌려요.

**왜 이런 일이 생기나.**

- 원리: ALB는 unhealthy로 본 대상에는 트래픽을 보내지 않아요. 그런데 대상이 전부 unhealthy면 모두에게 보내요. 그래서 장애처럼 보이지는 않지만, 헬스 체크가 아무것도 걸러내지 못해요. 이건 쿠버네티스 readiness와 별개예요.
- 읽을 것: AWS Load Balancer Controller 문서의 Ingress annotations, Elastic Load Balancing 문서의 Target group health checks

**근거.**

| 항목 | 값 | 출처 |
|---|---|---|
| app-n-frontend 요청, 24시간 | 9938건 | summary.json traffic.alb.target_groups[49] |
| app-n-frontend healthy 대상 | 1개 중 0개 | summary.json traffic.alb.target_groups[49] |
| app-q-backend 요청, 24시간 | 5849건 | summary.json traffic.alb.target_groups[33] |
| app-l-backend healthy 대상 | 2개 중 0개 | summary.json traffic.alb.target_groups[43] |
| app-o-frontend 요청, 24시간 | 1258건 | summary.json traffic.alb.target_groups[39] |

## 5. 지원 범위를 벗어난 EKS 1.32, Karpenter 0.37, AL2

**상황.** EKS 1.32는 2026-03-23에 표준 지원이 끝났어요. 지금은 확장 지원 요금을 내고 있고, 확장 지원도 2027-03-23에 끝나요.

Karpenter 0.37.0은 쿠버네티스 1.30까지만 지원해요. Karpenter 노드를 만드는 EC2NodeClass default는 Amazon Linux 2인데, 1.33부터는 AL2 AMI가 없어요. 셋을 순서대로 풀지 않으면, 다음 업그레이드에서 새 노드가 뜨지 않을 수 있어요.

- 영향 있음: karpenter/karpenter. 2026-11-04 17:48 KST에 'failed validating kubernetes version' 로그가 1건 났어요.
- 확인했고 멀쩡: Karpenter는 지금도 노드를 띄워요. 24시간 동안 노드 41대가 정상적으로 준비됐어요. EKS 애드온 4개는 ACTIVE이고 health issue가 0이에요.
- 다른 이유로 바뀜: 없음
- 안 봄: 워크로드가 AL2023의 cgroup v2에서 문제없이 도는지, 1.33에서 없어지는 API를 쓰는 매니페스트가 있는지

**이유.** EKS를 1.32로 올릴 때 Karpenter와 EC2NodeClass를 함께 올리지 않았어요. 추정이에요. 두 구성 요소가 1.32보다 오래된 지원 범위에 그대로 남아 있어서 그렇게 봐요.

**권하는 조치.**

① EKS 업그레이드 인사이트에서 업그레이드를 막는 항목을 보세요.

```
aws eks list-insights --profile acme --region us-east-1 --cluster-name my-cluster --output table
```

읽기만 해요.

확인: Amazon Linux 2 compatibility가 ERROR로 나와요. 다른 ERROR, WARNING 항목도 함께 적어 두세요.

② AL2를 AL2023으로 옮기는 계획을 세우세요. 먼저 build-arm64 풀용 EC2NodeClass를 AL2023으로 새로 만들어 CI 러너로 시험해요. 문제가 없으면 default 클래스의 amiFamily를 AL2023으로 바꿔요.

Drift가 켜져 있어서 Karpenter 노드 6대가 풀마다 한 대씩 교체돼요. 그때마다 레플리카 1개인 서비스와 DB가 멈춰요.

node-1-139는 do-not-disrupt 때문에 drift 교체도 막혀요. 2번 문제를 먼저 풀어야 해요. AL2023은 cgroup v2라서, 오래된 JVM이나 런타임은 메모리 한도를 다르게 읽을 수 있어요.

확인: `kubectl --context my-cluster get nodes -o wide`의 OS-IMAGE가 모두 Amazon Linux 2023이면 돼요.

③ 아래 두 조건이 모두 끝난 뒤에 Karpenter를 올리세요. 순서는 0.37에서 1.0으로, 이어서 1.32와 1.33을 지원하는 1.x로예요. 공식 업그레이드 가이드의 순서를 따르세요.

- AL2023 이전이 끝나서 모든 Karpenter 노드가 720시간보다 새것이에요.
- 2번 문제를 풀어서 node-1-139가 교체됐어요.

바로 1.0으로 가지 말고, 먼저 0.37 최신 패치로 올리세요. 업그레이드하면 NodePool과 EC2NodeClass가 v1 API로 바뀌어요.

공식 가이드에 따르면 v1부터는 만료 교체가 강제로 일어나서, 대체 노드를 기다리지도 않고 예산도 따르지 않아요. 이 클러스터에서는 검증되지 않았어요. 이때 720시간을 넘긴 노드가 있으면 그 노드의 파드가 한꺼번에 쫓겨나요.

업그레이드 중 컨트롤러가 멈추면, 그동안은 새 노드도 뜨지 않아요.

확인: `kubectl --context my-cluster -n karpenter get deploy karpenter -o jsonpath='{.spec.template.spec.containers[0].image}'`로 버전을 확인하세요. 로그에 'failed validating kubernetes version'이 더 나오지 않으면 돼요.

④ Karpenter가 1.33을 지원하게 되면, 2027-03-23 전에 EKS를 1.33으로 올리세요. 노드 그룹 system_core AMI와 애드온 4개도 함께 올려요.

Terraform 코드에서 cluster_version과 노드 그룹 버전을 바꾸고, plan을 본 뒤 apply해요. CLI나 콘솔로 올리면 다음 apply와 어긋나요.

노드 그룹 노드 2대에 prod MySQL 3개와 app-s PostgreSQL이 있어서, 한 대씩 교체되는 동안 멈춰요. 업그레이드 전에 1번 ③의 스냅샷을 먼저 떠 두세요.

확인: `aws eks describe-cluster --profile acme --region us-east-1 --name my-cluster --query cluster.version`이 1.33이면 끝이에요.

**되돌리기.** EKS 컨트롤플레인 버전은 되돌릴 수 없어요. AMI는 amiFamily를 AL2로 돌리면 drift로 다시 교체돼요. Karpenter도 되돌릴 수 있지만, CRD가 v1로 바뀐 뒤에는 어려워요. 그래서 1번 ③의 스냅샷을 먼저 떠야 해요.

**왜 이런 일이 생기나.**

- 원리: 지원이 끝난 마이너 버전은 보안 패치를 받지 못하고, EKS에서는 확장 지원 요금이 붙어요. Karpenter는 지원 표 밖의 쿠버네티스에서 AMI를 찾지 못해 새 노드를 띄우지 못할 수 있어요.
- 사례: 2025년 ZenML에서 운영 EKS를 업그레이드하던 중 Terraform 변경으로 워커 노드의 IAM 권한이 빠졌어요. 약 8시간 동안 클러스터 밖에서 파드에 닿지 못했어요. 오래된 쿠버네티스 버전과 AMI 종류가 원인 중 하나였어요. 이 클러스터도 밀린 업그레이드를 한꺼번에 해야 해요.
- 읽을 것: Karpenter 문서의 Upgrading to v1.0과 Compatibility, Amazon EKS 문서의 Kubernetes version lifecycle

**근거.**

| 항목 | 값 | 출처 |
|---|---|---|
| EKS 지원 종류 | EXTENDED | inventory.json |
| 확장 지원 종료일 | 2027-03-23 | aws/describe-cluster-versions.json |
| Karpenter 버전 | 0.37.0 | summary.json karpenterctl.summary |
| Karpenter 0.37 최대 지원 버전 | 1.30 | summary.json scaling.karpenter |
| EC2NodeClass default AMI 계열 | AL2 | summary.json karpenterctl.ec2nodeclasses[0] |

## 지난 full 점검 이후

2026-11-03T11-17-15 full 점검이에요. 그 점검에는 리포트가 없어서, 시킨 일을 했는지는 따질 수 없어요.

지난 리포트가 시킨 일: 없음

**새로 생긴 것.**

- 노드 node-2-158(build-arm64 풀, c6gn.xlarge 스팟)이 2026-11-05 15:49 KST에 새로 떴어요. 7일 CPU p95가 0.02라 유휴 노드로 잡혔고, 이 노드에서 EC2 CreateNetworkInterface 실패가 11번 있었어요.
- 노드 node-1-62의 루트 디스크 사용률이 79%가 됐어요.
- prod-app-o/app-o-frontend가 하루 종일 CPU 스로틀링을 받아요. 지금 비율은 0.15예요.
- prod-app-l-backend의 app-l-file-worker는 CPU 요청이 1코어인데 krr 권장값은 0.128코어예요. app-l-graph-worker도 1코어 요청에 권장값 0.542코어예요. keda-hpa-app-l-file-worker는 7일 동안 원하는 레플리카 수가 48번 바뀌었어요.
- prod-app-m/app-m-frontend(www.example-b.ai)에서 24시간 동안 요청 54991건 중 5xx가 80건(0.14%) 났어요.
- Grafana(monitor.my-cluster)의 요청 가중 p95가 2.8초예요.
- API 서버가 초당 0.004건의 503을 냈어요. 수집 중에 잰 값이라 kubegap이 보낸 요청이 섞였을 수 있어요.

**사라진 것.**

- 노드 node-2-144가 클러스터를 떠났어요. 그 노드의 유휴 노드 경고와 cgroup v1 경고도 같이 없어졌어요.
- Promtail의 메모리 사용이 limit에 붙어 있던 문제가 없어졌어요.
- middleware/kafka-exporter의 Not Ready가 없어졌어요. 다만 파드 재시작 수는 5번이에요.
- 노드 <ip>와 <ip>의 네트워크 오류 경고가 없어졌어요.
- Prometheus의 OOM 기록(2026-10-06)이 30일이 지나 집계에서 빠졌어요.

**클러스터가 아니라 점검 기준이 바뀌어서 달라진 것.**

- 노드 하나를 잃었을 때 버티는지(N+1) 경고가 새로 생겼어요. 클러스터가 바뀐 게 아니라, app 노드에만 뜰 수 있는 파드를 그 노드들의 남은 자리로 따로 계산하도록 체크가 바뀐 결과예요(rubric 0.1.65).
- 외부 DB NLB acme-db-shared가 fail에서 warn으로 내려왔어요. 보안 그룹 규칙을 읽어서 /32 주소 목록으로만 열린 걸 보도록 체크가 바뀐 결과예요(rubric 0.1.64).
- prod-app-m/app-m-frontend 스로틀링이 fail에서 warn으로, Prometheus 스로틀링이 warn에서 fail로 바뀌었어요. 5분 비율 대신 24시간 비율로 보도록 체크가 바뀐 결과예요(rubric 0.1.66).
- prod-app-q/app-q-ai의 반복 OOM이 warn에서 fail로 올라갔어요. 살아 있는 파드만 보던 체크가 7일 동안 끝난 파드까지 세도록 바뀐 결과예요(rubric 0.1.66).
- app-q-ai의 p95 지연이 fail에서 warn으로, app-l-frontend의 지연 경고는 없어졌어요. 요청 가중 p95로 보도록 체크가 바뀐 결과예요(rubric 0.1.65).
- arc-runners 러너 파드의 큰 요청 경고는 러너 파드 이름이 바뀐 것이지 새로 생긴 게 아니에요.
- prod 네임스페이스 8개의 쿼터 없음과 prod-app-l-backend의 LimitRange 없음이 warn에서 fail로 바뀌었어요. ResourceQuota와 LimitRange 오브젝트는 두 점검 사이에 바뀌지 않았어요. 체크 기록에는 이 규칙이 바뀌었다는 설명이 없어서, 규칙 변경인지는 확인하지 못했어요.

## 오늘은 안 하지만 심각한 것

- 증상 알림과 SLO가 없어요. 알림 규칙 157개 중 사용자 증상을 보는 규칙은 0개이고, OOM, 스케줄 실패, IP 고갈을 잡는 알림도 없어요. 오늘 문제처럼 당장 데이터를 잃거나 노출되는 일은 아니라서 뒤로 미뤄요.
- EKS API 서버 공개 엔드포인트가 0.0.0.0/0에 열려 있어요. 인증은 IAM이 지키고 있어요. 범위를 좁히려면 CI와 사람의 출발 주소를 먼저 모아야 해서 오늘은 안 해요.
- NetworkPolicy 3개가 아무것도 막지 않아요. 대상은 prod-app-q, prod-app-p, app-s-prod이고, aws-eks-nodeagent가 --enable-network-policy=false라서 그래요. 켜면 정책이 바로 적용돼 트래픽이 끊길 수 있으니 정책을 먼저 검토해야 해요.
- 관측 스택 데이터가 emptyDir에 있어요. Loki 저장소와 Alertmanager 데이터는 파드를 옮기면 사라지고, Loki는 2026-10-25에 OOM으로 한 번 죽었어요. Prometheus는 메모리 limit 1536Mi의 73%를 쓰고 CPU 스로틀링 비율이 0.28이에요. 다가오는 노드 만료 때 Loki 로그가 사라질 수 있어요.
- argocd/argocd-application-controller-0이 42번 재시작했고, 마지막 종료는 2026-10-30의 OOMKilled예요. 모든 prod 앱을 이 컨트롤러가 동기화해요. 메모리 limit을 바꾸는 일이라 따로 해요.
- prod-app-q/app-q-ai가 7일 동안 OOM으로 파드 3개를 잃었어요. 지금 레플리카는 1개예요.
- 쿠버네티스 이벤트를 따로 보관하지 않아서, 1시간쯤 지나면 이벤트가 사라져요.
- 시스템 노드 node-1-241과 node-2-218이 ENI 한도에 닿았어요. 두 노드는 각각 t8i.small, t8i.medium이고, 파드 IP를 각각 6/9, 13/15 쓰고 있어요. prefix delegation은 꺼져 있어요.
- prod-app-l-backend/tts-proxy가 NET_ADMIN 권한, /dev/net/tun hostPath, root 실행으로 떠 있어요. Tailscale 사이드카라서 필요한 권한일 수 있어요.
- 노드 루트 디스크 사용률이 node-1-139 81%, node-1-62 79%예요. node-1-139에서는 kubelet 이미지 GC가 2번 실패했어요. 2번 문제에서 그 노드를 교체하면 같이 풀려요.
- ExternalSecret database/mysql-app-n-secret이 2026-10-08부터 동기화에 실패하고 있어요. UpdateFailed가 2556번 쌓였어요.
- 프론트엔드가 하루 종일 CPU 스로틀링을 받아요. prod-app-m/app-m-frontend가 0.23~0.28, prod-app-o/app-o-frontend가 0.15이고, dev 두 개도 같아요.
- 인스턴스 8대 모두 IMDS hop limit이 2이고, EC2NodeClass default에는 루트 볼륨 암호화가 설정돼 있지 않아요.
- Unhealthy 프로브 이벤트가 115번 있었어요. prod-app-m/app-m-backend 파드와 promtail, app-l-file-worker에서 났어요.

## 영역별 한 줄

| 영역 | 무엇 |
|---|---|
| resources | 요청 과다 컨테이너 34개와 OOM 세 건이 있어요. 프론트엔드는 하루 종일 스로틀링을 받아요. |
| scaling | 만료를 넘긴 노드 하나와 곧 만료되는 노드 세 대가 있어요. HPA 대부분은 늘어난 적이 없어요. |
| observability | 증상 알림과 SLO가 없고, 잘못 잡힌 컨트롤플레인 알림이 57.8일째 울려요. |
| traffic | Kafka가 인터넷에 열려 있고, prod 헬스 체크 4개가 아무것도 걸러내지 못해요. |
| resilience | prod DB 백업이 없고, prod 파드 절반이 스팟 노드 한 대에 있어요. |
| hygiene | 변경과 장애의 시각을 맞출 재료가 없어요. 오래된 ReplicaSet이 353개 남아 있어요. |
| storage | prod DB 볼륨이 reclaimPolicy Delete이고 StorageClass 3개가 암호화되지 않았어요. |
| security | API 엔드포인트가 전체 공개이고 NetworkPolicy가 적용되지 않아요. |
| cost | 노드 비용의 95%가 유휴이고, 요청을 줄이면 월 162.65 USD쯤 줄어요. |
| tenancy | prod 네임스페이스 8개에 쿼터가 없지만, 7일 동안 이웃 영향의 근거는 없어요. |
| node OS | AL2 노드는 cgroup v1이고 노드 그룹 두 대는 읽지 못했어요. |
| platform | EKS, Karpenter, AMI가 모두 지원 범위 밖이거나 끝나 가요. |

## 이번에 못 본 것

- system_core 노드 node-1-117, node-2-60의 디스크, 커널 로그, kubelet·containerd 저널, VPC CNI IPAMD를 못 읽었어요. 이 두 노드에는 argocd-application-controller, prod MySQL 3개, app-s PostgreSQL이 있어요. 노드 그룹 IAM 역할에 AmazonSSMManagedInstanceCore를 붙이고, SSM 에이전트가 온라인인지 확인하세요.
- SSM 문서 kubegap-node-read가 저장소 버전과 달라져서, 다음 점검부터는 노드 안쪽을 못 읽어요. `kubegap setup --context my-cluster --install-ssm-document`로 문서를 갱신하세요.
- Grafana 데이터소스와 대시보드 목록을 못 읽었어요. Grafana에서 Viewer 서비스 계정 토큰을 만들어 config.yaml의 grafana_api_token에 직접 넣으세요.
- EKS 감사 로그가 꺼져 있어서, 누가 언제 무엇을 바꿨는지 볼 수 없어요. EKS 컨트롤플레인 로깅에서 audit을 켜세요.
- Kafka 외부 리스너가 TLS를 쓰는지 몰라요. 3번 ①의 명령으로 리스너 줄만 읽어 보세요.
- Kafka NLB와 DB NLB에 어떤 주소가 붙는지 몰라요. NLB 서브넷에 VPC Flow Logs를 하루 켜서 출발 주소를 모으세요.
- 클러스터 밖에서 도는 DB 덤프가 있는지 몰라요. 개발자 PC나 다른 계정의 작업일 수 있어요. 서비스 담당자마다 덤프 위치와 마지막 복원 시험 날짜를 물어보세요.

## 숫자

| 심각도 | fail | warn | 지난 full 점검 대비 |
|---|---|---|---|
| critical | 1 | 0 | fail 0, warn +1 |
| high | 25 | 24 | fail -1, warn +1 |
| medium | 126 | 166 | fail +9, warn -4 |
| low | 16 | 140 | fail 0, warn +1 |

문제별 체크:

- 문제 1: `resilience.no-backup.cluster`, `eks.no-backup-policy.cluster`, `resilience.prod-db-without-backup-cronjob.cluster`, `storage.prod-db-reclaim-delete.cluster`, `storage.csi-snapshot-unavailable.cluster`, `logs.signatures.ebs-csi.snapshot-crd-missing`
- 문제 2: `resilience.prod-concentration.node-1-139`, `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai`, `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend`, `resilience.replicas-same-node.prod-app-r/deployment/app-r`, `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend`, `resilience.n-plus-one.cluster`, `scaling.karpenter-expired-not-replaced.default-n44bh`, `vpccni.node-ip-exhaustion.node-1-139`, `resilience.no-pdb.prod-app-o/app-o-ai`, `resilience.no-pdb.prod-app-o/app-o-backend`, `resilience.replicas-same-zone.prod-app-m/deployment/app-m-api`, `resilience.replicas-same-zone.prod-app-m/deployment/app-m-backend`, `resilience.replicas-same-zone.prod-app-m/deployment/app-m-frontend`, `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-backend`, `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-embedding-server`
- 문제 3: `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external`, `traffic.db-exposed.nlb/acme-db-shared`
- 문제 4: `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend`, `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend`, `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend`, `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend`, `traffic.alb-unhealthy-targets.dev-app-n/app-n-frontend`, `traffic.alb-unhealthy-targets.dev-app-t/app-t-backend`
- 문제 5: `platform.k8s-version-eol.cluster`, `eks.extended-support.cluster`, `platform.karpenter-version-compat.cluster`, `karpenter.ec2nodeclass-al2.cluster`, `hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility`, `eks.node-os-skew.cluster`, `eks.nodegroup-ami-old.nodegroups`, `logs.signatures.karpenter.version-unsupported`, `node.cgroup-v1.node-2-158`

자세한 내용과 모든 표: [`report-details.md`](report-details.md) · kubegap 0.1.2, rubric 0.1.80 · 수집 자료 `~/.kubegap/snapshots/my-cluster/2026-11-05T17-00-00`
