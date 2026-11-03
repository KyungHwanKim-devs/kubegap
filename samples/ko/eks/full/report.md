# my-cluster — full 점검, 2026-11-03 11:17 KST

이 클러스터는 us-east-1 리전의 EKS `my-cluster` 이고, kube 컨텍스트는 `my-cluster` 예요. Kubernetes 1.32.13 에 노드 8대, 파드 145개가 돌고, prod 네임스페이스 8개와 dev 네임스페이스 4개가 같은 노드를 나눠 써요. 수집 시점에 급한 장애는 없습니다. 지난 full 점검 뒤 새로 생긴 일은 `prod-app-q/app-q-ai` 가 2026-11-02 18:38 KST 에 메모리 제한에 걸려 죽은 것이고, 노드 `ip-10-0-1-139` 의 Failed 파드 12개는 정리됐어요.

## 지금 손봐야 할 문제 5개

### 1. prod 데이터베이스 7개에 백업이 하나도 없고, PVC 를 지우면 디스크도 그 자리에서 지워집니다
**문제.** prod 데이터베이스 StatefulSet 7개에 어떤 백업도 없어요. `prod-app-q/app-q-backend-postgresql`, `prod-app-m/app-m-backend-mysql`, `prod-app-o/app-o-backend-mysql`, `prod-app-l-backend/app-l-neo4j`, `prod-app-p/app-p-postgresql`, `prod-app-n/app-n-backend-prod-mysql`, `app-s-prod/app-s-backend-postgresql` 이에요. 일곱 개의 PV 가 모두 reclaimPolicy Delete 라서, 네임스페이스를 지우거나 Argo CD prune 이 PVC 를 지우면 EBS 볼륨도 바로 지워지고 되돌릴 방법이 없어요. 2026-10-26 리포트부터 매번 들어 있던 문제이고 아직 손대지 않았어요.

**근거.** DLM 수명 주기 정책이 0개예요. 출처는 aws/dlm-lifecycle-policies.json 이에요. AWS Backup 백업 계획도 0개예요. 출처는 aws/backup-plans.json 이에요. 최근 30일 EBS 스냅샷 12개는 전부 설명이 "pre-delete backup of orphan PVC" 로, 사람이 PVC 를 지우기 전에 손으로 뜬 거예요. 출처는 aws/ec2-snapshots-30d.json 이에요. VolumeSnapshot CRD 가 없어 EBS CSI 컨트롤러가 24시간에 1,500줄의 오류를 남겼어요. 출처는 summary.json logs 예요. EBS 볼륨 17개, 280 GB 가 전부 암호화되지 않았어요. 출처는 aws/ec2-volumes.json 이에요.

**원인.** 추정입니다. 클러스터를 만들 때 백업 도구를 넣지 않았고, PVC 정리는 지우기 전에 손으로 스냅샷을 뜨는 절차로 대신해 왔어요. StorageClass `gp3` 는 기본값인 Delete 와 암호화 없음을 그대로 써요.

**조치.** ① 일곱 볼륨에 `backup=prod-db` 태그를 붙이고 DLM 으로 매일 스냅샷을 7개씩 남겨요. 1시간 걸려요.
```bash
aws dlm create-lifecycle-policy --region us-east-1 --state ENABLED \
  --description "prod db daily" \
  --execution-role-arn arn:aws:iam::<account>:role/AWSDataLifecycleManagerDefaultRole \
  --policy-details '{"ResourceTypes":["VOLUME"],"TargetTags":[{"Key":"backup","Value":"prod-db"}],
    "Schedules":[{"Name":"daily","CreateRule":{"Interval":24,"IntervalUnit":"HOURS","Times":["18:00"]},
    "RetainRule":{"Count":7},"CopyTags":true}]}'
```
② 일곱 PV 를 Retain 으로 바꿔요. PVC 를 실수로 지워도 볼륨이 남아요. 15분 걸려요. `kubectl patch pv <pv 이름> -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'`. ③ 데이터베이스마다 mysqldump, pg_dump, neo4j-admin dump 를 S3 로 올리는 CronJob 을 두고 한 번은 복원까지 해 봐요. 스냅샷은 볼륨 단위라 테이블 하나를 되살릴 때는 덤프가 빨라요. 반나절 걸려요. ④ 계정의 EBS 기본 암호화를 켜고 `encrypted: "true"`, `reclaimPolicy: Retain` 인 새 StorageClass 를 만들어요. 기존 볼륨은 스냅샷에서 암호화 볼륨으로 복원해야 해서 점검 시간이 필요해요. 며칠 걸려요.

**왜 이런 일이 생기나.**
- 원리: EBS 볼륨은 노드가 죽어도 남지만, PVC 가 지워지면 reclaimPolicy Delete 가 볼륨까지 지워요. 같은 계정, 같은 볼륨에만 있는 데이터는 실수 한 번, 손상 한 번으로 끝나요. 백업은 원본과 떨어진 곳에 복사본이 있고 복원해 본 적이 있을 때만 백업이에요.
- 사례: InfluxData 가 2023년에 운영 환경을 지운 뒤 복구한 과정을 공개했고, 이 점검 항목의 사례로 기록돼 있어요. https://www.influxdata.com/blog/deleting-production-steps-how-fix-it/
- 이 점검 항목을 만들 때 측정한 값: 실제 EKS 클러스터에서 "pre-delete backup of orphan PVC" 스냅샷이 열 개 남짓 있었어요. 누군가 PVC 를 지우기 전에 손으로 스냅샷을 뜨고 있었다는 뜻이고, Retain 이 그 절차를 대신해요.
- 더 알아보기: Kubernetes 문서의 Persistent Volumes 중 Reclaiming 절, AWS 문서의 Amazon Data Lifecycle Manager, Google 이 낸 『Site Reliability Engineering』 26장 Data Integrity 를 보세요.

근거 체크: `resilience.no-backup.cluster` `eks.no-backup-policy.cluster` `storage.prod-db-reclaim-delete.cluster` `resilience.prod-db-without-backup-cronjob.cluster` `storage.csi-snapshot-unavailable.cluster` `logs.signatures.ebs-csi.snapshot-crd-missing` `storage.ebs-unencrypted.cluster` `ebscsi.storageclass-unencrypted.cluster`

### 2. prod 파드 42개 중 33개가 같은 영역의 스팟 노드 두 대에 있고, 큰 노드는 만료 241시간이 지나도 파드 하나 때문에 교체되지 않습니다
**문제.** 앱 파드는 `workload-type=app` 레이블이 있는 노드에만 올라가요. 지금 그런 노드는 `ip-10-0-1-139` r8gd.xlarge 와 `ip-10-0-1-62` r8gd.large 두 대이고, 둘 다 us-east-1 의 스팟이에요. 큰 노드 하나에 prod 파드 20개가 있고, `prod-app-r/app-r`, `prod-app-o/app-o-ai`, `prod-app-o/app-o-backend`, `prod-app-l-backend/app-l-frontend` 는 레플리카 전부가 이 노드에 있어요. AWS 가 이 노드를 2분 예고로 회수하면 네 서비스가 새 노드가 뜰 때까지 같이 멈춰요. 레플리카 1개에 Recreate 전략인 `prod-app-p/app-p-backend` 는 어느 노드가 가도 멈춰요.

**근거.** Running prod 파드 42개 중 20개가 `ip-10-0-1-139`, 13개가 `ip-10-0-1-62` 에 있어요. 출처는 objects/pods.json 이에요. `ip-10-0-1-139` 의 NodeClaim `default-n44bh` 는 만료 720시간을 241.8시간 넘겼고, `prod-app-m/app-m-admin` 의 `karpenter.sh/do-not-disrupt` 가 교체를 19,728번 막았어요. 출처는 summary.json scaling.karpenter, events.json DisruptionBlocked 예요. 큰 노드의 CPU requests 는 3.92코어 중 89.3% 인 3.50코어이고, 다른 앱 노드에 남은 CPU 는 0.16코어예요. 출처는 metrics/node_cpu_request_ratio.json 이에요. 24시간 동안 스팟 회수는 없었고 Karpenter 정리는 빈 노드 9대와 consolidation 3대였어요. 출처는 summary.json scaling.karpenter.disruptions_24h 예요.

**원인.** NodePool `default` 에는 영역 조건이 없는데 두 노드가 우연히 같은 2a 에 떴어요. Deployment 에 분산 선언이 없어서 스케줄러와 Karpenter consolidation 이 파드를 빈자리가 있는 큰 노드로 모았어요. `app-m-admin` pod template 의 do-not-disrupt 때문에 만료된 노드가 교체되지 않고, 그 노드에 파드와 디스크 사용이 계속 쌓여 루트 디스크가 82% 예요.

**조치.** ① `prod-app-m/app-m-admin` 의 pod template 에서 `karpenter.sh/do-not-disrupt` 를 빼요. 그 뒤 Karpenter 가 예산 10% 안에서 `ip-10-0-1-139` 를 새 노드로 바꾸고 디스크도 새로 시작해요. 교체 때 파드가 옮겨지니 한산한 시간에 해요. 10분 걸려요. ② 레플리카 2개 이상인 prod Deployment 9개에 노드와 영역 분산을 넣어요. 노드는 반드시 나누고 영역은 가능하면 나눠요. 1시간 걸려요.
```yaml
spec:
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector: {matchLabels: {app.kubernetes.io/name: <앱>}}
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector: {matchLabels: {app.kubernetes.io/name: <앱>}}
```
③ `prod-app-p/app-p-backend` 를 RollingUpdate 에 레플리카 2개로 바꿔요. 볼륨이 emptyDir `tmp` 하나뿐이라 Recreate 일 이유가 없어요. 15분 걸려요. ④ `prod-app-o/app-o-ai` 와 `app-o-backend` 에 `maxUnavailable: 1` PDB 를 붙여요. 10분 걸려요. 이렇게 하면 노드 하나가 회수돼도 서비스마다 레플리카 하나는 남아요.

**왜 이런 일이 생기나.**
- 원리: 레플리카 2개의 의미는 하나가 죽어도 버티는 것인데, 둘이 같은 노드에 있으면 그 노드와 함께 같이 사라져요. 스케줄러는 분산 선언이 없으면 자리가 있는 노드에 채우고, Karpenter consolidation 은 비용을 줄이려고 파드를 적은 노드로 적극적으로 모아요. 스팟은 2분 예고 뒤 회수돼요.
- 사례: Moonlight 가 2019년에 낸 장애 사후 분석이 이 점검 항목의 사례예요. https://updates.moonlightwork.com/outage-post-mortem-87370
- 이 점검 항목을 만들 때 측정한 값: 첫 실측에서 스팟 회수 한 번에 prod 서비스 하나가 2분 7초 멈췄어요. 그 노드는 prod 파드 27개, 64% 를 들고 있었어요.
- 더 알아보기: Kubernetes 문서의 Pod Topology Spread Constraints, Karpenter 문서의 Disruption 중 expireAfter 와 do-not-disrupt 절, AWS EC2 문서의 Spot Instance interruptions 를 보세요.

근거 체크: `resilience.prod-concentration.node-1-139` `resilience.replicas-same-node.prod-app-r/deployment/app-r` `resilience.replicas-same-node.prod-app-o/deployment/app-o-ai` `resilience.replicas-same-node.prod-app-o/deployment/app-o-backend` `resilience.replicas-same-node.prod-app-l-backend/deployment/app-l-frontend` `resilience.replicas-same-zone.prod-app-m/deployment/app-m-api` `resilience.replicas-same-zone.prod-app-m/deployment/app-m-backend` `resilience.replicas-same-zone.prod-app-m/deployment/app-m-frontend` `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-backend` `resilience.replicas-same-zone.prod-app-l-backend/deployment/app-l-embedding-server` `scaling.karpenter-expired-not-replaced.default-n44bh` `resilience.single-replica-in-prod.prod-app-p/app-p-backend` `resilience.recreate-strategy-serving.prod-app-p/deployment/app-p-backend` `resilience.no-pdb.prod-app-o/app-o-ai` `resilience.no-pdb.prod-app-o/app-o-backend` `node.disk-usage.<ip>:9100:/`

### 3. app-q-ai 가 어제 메모리 제한에 걸려 죽었는데 아무 알림도 울리지 않았고, prod 헬스체크 넷은 아무것도 거르지 못합니다
**문제.** `prod-app-q/app-q-ai` 는 레플리카 1개인데, 2026-11-02 18:38 KST 에 768Mi 메모리 제한을 넘어 OOMKilled 됐어요. 새 파드가 뜬 지 44분 만이었고, 재시작하는 동안 `app-q-ai.my-cluster` 뒤에는 파드가 없었어요. 이 일을 알려 줄 규칙이 없어요. 알림 규칙 157개 중 5xx 나 응답 시간처럼 사용자가 겪는 증상을 보는 규칙은 하나도 없고, OOMKill 을 보는 규칙도 없어요. prod ALB 타깃 그룹 네 개는 타깃이 전부 unhealthy 라서 ALB 가 모든 타깃에 그대로 보내고, 파드가 응답하지 않아도 걸러내지 못해요.

**근거.** 마지막 종료는 OOMKilled, 종료 코드 137 이고 memory request 256Mi, limit 768Mi 예요. 출처는 objects/pods.json 이에요. KRR 이 권하는 메모리 request 는 607 MB 예요. 출처는 summary.json resources.krr 예요. `app-q-ai.my-cluster` 은 24시간 130건에 p95 평균 14.09초, 시간당 최대 35.56초였어요. 출처는 summary.json traffic.ingresses 예요. 사용자 증상 규칙은 157개 중 0개예요. 출처는 summary.json observability 예요. 건강한 타깃이 0개인 prod 타깃 그룹은 `app-q-backend` 404, `app-o-frontend` 307, `app-l-backend` 404 두 개, `app-n-frontend` 307 이에요. 출처는 summary.json traffic.alb 예요.

**원인.** 추정입니다. app-q-ai 의 메모리 request 와 limit 이 요청을 처리할 때의 최대 사용량보다 낮게 잡혀 있어요. 컨테이너 로그는 kubegap 수집 범위 밖이라 무엇이 메모리를 썼는지는 몰라요. 알림은 kube-prometheus-stack 기본 규칙만 있고 증상 규칙은 따로 만들지 않았어요. 헬스체크는 ingress 에 경로 annotation 이 없어 기본값 `/` 를 쓰는데, 앱이 `/` 에서 404 나 로그인 리다이렉트 307 을 돌려줘요.

**조치.** ① app-q-ai 의 메모리를 request 640Mi, limit 1Gi 로 올리고 CPU limit 은 빼요. 10분 걸려요. 레플리카 2개는 문제 2 의 조치와 같이 해요.
```yaml
resources:
  requests: {cpu: 100m, memory: 640Mi}
  limits:   {memory: 1Gi}
```
② prod 네임스페이스의 OOMKill 알림을 PrometheusRule 로 넣어요. 30분 걸려요. `increase(container_oom_events_total{namespace=~"prod-.*|app-s-prod"}[10m]) > 0`. ③ ALB 메트릭은 Prometheus 가 아니라 CloudWatch 에 있으니, prod 타깃 그룹마다 5xx 수와 응답 시간 p95 에 CloudWatch 알람을 걸고 SNS 로 Slack 에 보내요. 2시간 걸려요.
```bash
aws cloudwatch put-metric-alarm --alarm-name app-q-ai-p95 --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime --extended-statistic p95 --period 300 --evaluation-periods 3 \
  --threshold 5 --comparison-operator GreaterThanThreshold \
  --dimensions Name=LoadBalancer,Value=app/k8s-acmeprodlb-b18a4555d7/<id> Name=TargetGroup,Value=targetgroup/k8s-app-svc-fc2d368787/<id> \
  --alarm-actions arn:aws:sns:us-east-1:<account>:<topic>
```
④ 네 ingress 에 앱이 200 을 돌려주는 경로를 적어요. app-q-ai 는 이미 `/health` 를 쓰고 app-r 은 `/livez` 를 써요. 30분 걸려요. `alb.ingress.kubernetes.io/healthcheck-path: /health`. ⑤ EKS 에서 항상 울리는 KubeControllerManagerDown 과 KubeSchedulerDown 을 kube-prometheus-stack values `kubeControllerManager.enabled: false`, `kubeScheduler.enabled: false` 로 꺼요. 10분 걸려요. 이렇게 하면 다음 OOM 과 느려짐은 사람이 보기 전에 알림으로 오고, 헬스체크가 응답하지 않는 파드를 실제로 빼게 돼요.

**왜 이런 일이 생기나.**
- 원리: 컨테이너가 memory limit 을 넘으면 cgroup OOM killer 가 그 컨테이너만 죽여요. 레플리카가 하나면 그동안 서비스가 없어요. 알림은 원인보다 증상에 걸어야 해요. "CPU 80%" 는 사용자가 모르는 원인이고 "5분 동안 5xx 1% 초과" 가 증상이에요. ALB 는 타깃이 전부 unhealthy 면 장애를 내지 않고 모두에게 보내는데, 그러면 헬스체크가 하는 일이 없어져요.
- 사례: Zalando 가 2019년 1월 DNS 장애 사후 분석을 공개했고, OOMKill 점검 항목의 사례로 기록돼 있어요. https://github.com/zalando-incubator/kubernetes-on-aws/blob/dev/docs/postmortems/jan-2019-dns-outage.md
- 이 점검 항목을 만들 때 측정한 값: 실제 EKS 클러스터에서 타깃이 전부 unhealthy 인 프론트엔드가 그래도 요청 17,213건을 받았어요. 같은 클러스터의 타깃 그룹 6개가 헬스체크 경로에서 404 나 307 을 받고 있었어요.
- 더 알아보기: Google 이 낸 『Site Reliability Engineering』 6장 Monitoring Distributed Systems, AWS Elastic Load Balancing 문서의 Health checks for your target groups, Kubernetes 문서의 Resource Management for Pods and Containers 를 보세요.

근거 체크: `resources.oomkilled.prod-app-q/deploy/app-q-ai:ai` `resources.oomkilled-repeated.prod-app-q/deploy/app-q-ai:ai` `resources.krr-recommendation.prod-app-q/deployment/app-q-ai:ai` `traffic.ingress-p95-latency.prod-app-q/app-q-ai` `observability.failure-mode-uncovered.OOMKill` `observability.no-symptom-alerts.cluster` `observability.no-slo.cluster` `traffic.alb-unhealthy-targets.prod-app-q/app-q-backend` `traffic.alb-unhealthy-targets.prod-app-o/app-o-frontend` `traffic.alb-unhealthy-targets.prod-app-l-backend/app-l-backend` `traffic.alb-unhealthy-targets.prod-app-n/app-n-frontend` `observability.alert-firing-stale.KubeControllerManagerDown` `observability.alert-firing-stale.KubeSchedulerDown`

### 4. Kafka 브로커 포트가 인터넷 전체에 열려 있고, 배포 도구 Argo CD 는 SSO 없이 admin 계정 하나로 인터넷에서 닿습니다
**문제.** `middleware/kafka-controller-0-external` 은 인터넷 쪽 NLB 이고, 보안 그룹이 9094 와 443 을 모든 주소 0.0.0.0/0 에 열어 두었어요. `broker.my-cluster` 으로 이름도 붙어 있고 하루 2.85 GB 가 오가서 바깥 클라이언트가 실제로 써요. LB 는 TLS 를 끝내지 않고, 브로커가 어떤 인증을 요구하는지는 설정값이 수집되지 않아 확인하지 못했어요. Argo CD `deploy.my-cluster` 은 SSO 없이 admin 계정이 켜져 있고, 앱 12개가 저장소와 대상이 전부 `*` 인 default 프로젝트에 있어요. admin 비밀번호 하나로 어떤 저장소의 매니페스트든 어느 네임스페이스에든 배포할 수 있어요. 반면 DB 포트를 연 NLB `acme-db-shared` 는 보안 그룹이 /32 주소 4개 이하만 허용해서 이번에 medium 으로 내렸어요.

**근거.** Kafka NLB 보안 그룹 `k8s-middlewa-kafkacon` 의 인바운드는 9094 와 443 둘 다 0.0.0.0/0 이에요. 출처는 extra/lb-security-group-rules.txt 이고 스냅샷 밖에서 읽기 전용 명령으로 읽었어요. 이 NLB 는 24시간 2,845,864,092 바이트를 처리했고 동시 연결이 최대 441개였어요. 출처는 aws/alb-metrics.json 이에요. Argo CD 는 admin.enabled True, SSO False, RBAC policy.default 가 비어 있어요. 출처는 summary.json argocdctl 이에요. default 프로젝트에 앱 12개 중 12개, 그중 prod 8개가 묶여 있어요. EKS API 엔드포인트도 0.0.0.0/0 에 공개예요. 출처는 aws/describe-cluster.json 이에요.

**원인.** 추정입니다. 클러스터 밖 Kafka 클라이언트를 붙이려고 Bitnami 차트의 external 리스너를 internet-facing LB 로 열면서 허용 주소를 정하지 않았어요. Argo CD 는 설치 기본값을 그대로 쓰고 있어요.

**조치.** ① Kafka Service 에 클라이언트 주소만 허용해요. 클라이언트 IP 목록을 확인하는 시간까지 30분 걸려요. 이렇게 하면 9094 와 443 이 목록에 있는 주소에서만 닿아요.
```yaml
# middleware/kafka-controller-0-external, Helm values externalAccess.service.loadBalancerSourceRanges 로도 같아요
spec:
  loadBalancerSourceRanges:
    - <클라이언트 IP>/32
```
② 다음으로 Kafka 외부 리스너를 SASL_SSL 로 바꿔요. 클라이언트 설정도 바뀌어서 하루 걸려요. ③ Argo CD 에 OIDC SSO 를 붙이고 `admin.enabled: "false"` 로 바꾼 뒤, 서비스마다 sourceRepos 와 destinations 를 좁힌 AppProject 를 만들어요. 반나절 걸려요. ④ EKS API 공개 접근을 사무실이나 VPN 주소로 좁혀요. 30분 걸려요. `aws eks update-cluster-config --name my-cluster --resources-vpc-config endpointPrivateAccess=true,publicAccessCidrs=<사무실 IP>/32`. ⑤ VPC CNI 애드온 설정에서 `enableNetworkPolicy: "true"` 를 켜서 `prod-app-q`, `prod-app-p`, `app-s-prod` 에 이미 있는 NetworkPolicy 3개가 실제로 적용되게 해요. 먼저 dev 에서 확인해야 해서 1시간 걸려요.

**왜 이런 일이 생기나.**
- 원리: 허용 주소가 없는 인터넷 쪽 LB 는 누구나 닿을 수 있고, 그때 남는 방어는 애플리케이션 자신의 인증 하나뿐이에요. 배포 도구는 클러스터 전체에 쓰기 권한을 가진 경우가 많아서, 그 계정 하나가 클러스터 전체의 열쇠가 돼요. Argo CD application-controller 의 ClusterRole 도 verbs 와 resources 가 `*` 예요.
- 사례: Aqua Nautilus 가 2023년에 Kubernetes RBAC 으로 클러스터에 백도어를 심는 공격을 보고했고, 공개 엔드포인트 점검 항목의 사례로 기록돼 있어요. https://www.aquasec.com/blog/leveraging-kubernetes-rbac-to-backdoor-clusters/
- 이 점검 항목을 만들 때 측정한 값: 실제 EKS 클러스터에서 Kubernetes 밖에서 만든 인터넷 쪽 NLB 가 MySQL, Postgres, Redis, Neo4j 포트를 받고 있었고, Kafka 9094 NLB 도 인터넷 쪽이었어요.
- 더 알아보기: Kubernetes 문서의 Create an External Load Balancer 중 loadBalancerSourceRanges 절, Argo CD 문서의 RBAC Configuration 과 SSO 설정, Amazon EKS 문서의 Cluster endpoint access control 을 보세요.

근거 체크: `traffic.db-exposed.loadbalancer/middleware/kafka-controller-0-external` `traffic.db-exposed.nlb/acme-db-shared` `eks.public-endpoint-open.cluster` `argocd.admin-account-no-sso.cluster` `argocd.default-project-wildcard.cluster` `security.rbac-wildcard.argocd-application-controller` `traffic.external-exposure.ingress/argocd/argocd-server` `security.networkpolicy-not-enforced.cluster` `security.networkpolicy-coverage.cluster`

### 5. Kubernetes 1.32 는 표준 지원이 끝난 지 225일이고, 다음 버전으로 가는 길을 AL2 노드 이미지와 Karpenter 0.37 이 막고 있습니다
**문제.** 클러스터는 1.32.13 으로 EKS 연장 지원 기간에 있어요. 1.33 으로 올리려면 먼저 두 가지를 풀어야 해요. Karpenter 가 띄운 노드 6대가 Amazon Linux 2 인데 EKS 는 1.33 부터 AL2 AMI 를 내지 않아요. Karpenter 0.37.0 은 Kubernetes 1.30 까지만 지원해서 지금도 지원 범위 밖에서 돌고 있어요. 이대로 control plane 만 올리면 Karpenter 가 새 노드에 쓸 AMI 를 찾지 못해 노드를 늘리지 못할 수 있어요.

**근거.** API 서버는 v1.32.13-eks-577a51e 이고, 표준 지원 종료 2026-03-23 에서 225일 지났어요. 출처는 inventory.json 과 findings-draft.json 이에요. Karpenter 0.37.0 의 지원 상한은 1.30 이고, Karpenter 로그에 버전 미지원 오류가 2026-11-02 17:46 KST 에 한 줄 남았어요. 출처는 summary.json karpenterctl, logs 예요. EC2NodeClass `default` 는 amiFamily AL2 이고 AMI 를 고정하지 않았어요. EKS 업그레이드 인사이트가 AL2 호환성을 ERROR 로 내고 있어요. 출처는 aws/list-insights.json 이에요. 관리형 노드 그룹 노드 2대는 이미 AL2023 인데 AMI 가 329일 됐어요. 출처는 aws/describe-nodegroup-system_core-20251217040546303900000001.json 이에요.

**원인.** 추정입니다. Karpenter 0.x 에서 1.x 로 가는 이전은 API 가 v1beta1 에서 v1 으로 바뀌는 큰 작업이라 미뤄졌고, 그래서 Kubernetes 업그레이드와 AL2023 이전도 같이 밀렸어요.

**조치.** ① Karpenter 를 0.37 의 마지막 패치로 올린 뒤 1.0 으로, 그다음 1.33 을 지원하는 1.x 로 올려요. Karpenter 문서의 v1 이전 순서를 그대로 따라요. 2~3일 걸려요. ② EC2NodeClass 를 AL2023 으로 바꾸고 AMI 를 버전으로 고정해요. cgroup v2 로 바뀌니 JVM 과 모니터링 에이전트를 dev 에서 먼저 확인해요. 하루 걸려요.
```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata: {name: default}
spec:
  amiSelectorTerms:
    - alias: al2023@<버전>
```
③ 애드온 넷을 올려요. aws-ebs-csi-driver v1.37.0, vpc-cni v1.19.0, coredns v1.11.3, kube-proxy v1.32.0 이 밀려 있어요. 2시간 걸려요. ④ 그다음 control plane 을 1.33 으로, 노드를 차례로 올려요. 하루 걸려요. 이렇게 하면 연장 지원에서 빠지고 보안 패치를 다시 받아요.

**왜 이런 일이 생기나.**
- 원리: Kubernetes 는 마이너 버전을 건너뛰어 올릴 수 없어서 미룰수록 거쳐야 할 단계가 늘어요. 노드 이미지와 노드 오토스케일러는 control plane 버전에 맞는 것이 있어야 해서, 셋 중 하나가 뒤처지면 나머지도 묶여요. Karpenter 1.x 는 시작할 때 클러스터 버전을 자기 지원표와 비교하고, 표 밖이면 AMI 를 고르지 못해요.
- 사례: ZenML 이 2025년에 상태 페이지에 공개한 장애 기록이 이 점검 항목의 사례로 올라 있어요. https://status.zenml.io/incidents/bnrlb8tck3v0
- 이 점검 항목을 만들 때 측정한 값: 실제 EKS 클러스터에서 지원 상한 1.30 인 Karpenter 0.37.0 이 1.32 클러스터에서 돌고 있었어요.
- 더 알아보기: Amazon EKS 문서의 Kubernetes version lifecycle 과 AL2 에서 AL2023 으로 옮기기, Karpenter 문서의 Upgrade Guide 중 v1 Migration, Kubernetes 문서의 Version Skew Policy 를 보세요.

근거 체크: `platform.k8s-version-eol.cluster` `eks.extended-support.cluster` `platform.karpenter-version-compat.cluster` `logs.signatures.karpenter.version-unsupported` `karpenter.ec2nodeclass-al2.cluster` `hygiene.eks-upgrade-insight.Amazon Linux 2 compatibility` `eks.node-os-skew.cluster` `eks.nodegroup-ami-old.nodegroups` `eks.addon-outdated.aws-ebs-csi-driver` `eks.addon-outdated.vpc-cni` `eks.addon-outdated.coredns` `eks.addon-outdated.kube-proxy`

번외로 금방 끝나는 것 하나: dev ExternalSecret `database/mysql-app-n-secret` 이 "could not get secret data from provider" 로 실패하고 있고 이벤트 누적은 2,351번이에요. 2026-10-26 리포트는 원인을 Secrets Manager 에 키가 없는 것으로 확인했어요. 키를 만들거나 ExternalSecret 을 지우는 데 5분 걸리고, 발견 사항 다섯 개가 사라져요.

## 지난 full 점검 이후 (2026-10-27 15:30 KST)
직전 full 스냅샷 2026-10-27 15:30 에는 리포트가 없어서, 지난 문제의 진행은 2026-10-26 16:47 full 리포트를 기준으로 적었어요. 6일 20시간 동안 Deployment 16개가 배포됐고 노드는 build-arm64 의 CI 노드 한 대만 바뀌었어요. AWS 는 EKS 플랫폼 버전을 eks.55 에서 eks.58 로 올렸어요. 새로 생긴 사건은 app-q-ai 의 OOMKill 과 Argo CD application-controller 의 OOMKill 한 번이에요. `ip-10-0-1-139` 의 Failed 파드 12개가 정리돼서 오래 울리던 KubePodNotReady 알림 네 개가 사라졌고, 그 노드 디스크는 86.4% 에서 82% 로 내려왔어요. 2026-10-27 의 스케줄 실패 다섯 개는 그날 노드 교체 때 생긴 것이라 이번엔 없고, 이번의 app-l 워커 스케줄 실패는 KEDA 가 0 에서 늘릴 때 노드를 1분쯤 기다린 거예요. Argo CD 발견 사항 여섯 개는 2026-10-27 에 수집이 비어 건너뛰었다가 이번에 처음 평가된 기준 변경이에요. 룰은 0.1.51 에서 0.1.63 으로 올랐어요.

지난 리포트 문제의 진행: 문제 1 스팟 노드 집중은 아직 손대지 않음이에요. 큰 노드의 prod 파드가 28개에서 20개로 줄었지만 배포 때 파드가 다른 앱 노드에 놓인 결과이고, do-not-disrupt 차단은 14,171번에서 19,728번으로 늘었으며 `app-p-backend` 는 여전히 레플리카 1개에 Recreate 예요. 문제 2 `ip-10-0-1-139` 디스크와 쫓겨난 파드는 진행 중이에요. Failed 파드는 12개에서 0개가 됐고 디스크는 82% 인데, 이미지 정리는 2026-11-02 에도 3번 실패했어요. 문제 3 백업 없음과 암호화 안 된 볼륨은 아직 손대지 않음이에요. DLM 정책 0개, 볼륨 17개 중 17개 암호화 안 됨이에요. 문제 4 증상 알림과 prod 헬스체크는 아직 손대지 않음이에요. 증상 규칙 0개, 같은 prod 타깃 그룹 넷이 여전히 unhealthy 예요. 문제 5 Kubernetes 1.32, AL2, Karpenter 0.37, 열린 Argo CD 는 아직 손대지 않음이에요. 버전 1.32.13, EC2NodeClass AL2, Karpenter 0.37.0, SSO 없는 admin 그대로예요.

## 이번에 확인 못 한 것
프로필이 기대하는 백업 도구, 이벤트 보존, SLO 정의, 클러스터 안 인증서 관리, 점진적 배포가 하나도 없어요. 점검 항목 365개 중 358개를 평가했어요. 2개는 prod 프로필에서 꺼져 있고, 3개는 fluent-bit 과 ingress-nginx 가 없어 원래 건너뛰게 되어 있으며, 빠진 도구는 없어요. 실패한 명령 24개 중 19개는 SSM 에 등록되지 않은 관리형 노드 `ip-10-0-1-117` 과 `ip-10-0-2-60` 에서 돌린 명령이라, 그 두 대의 OS 상태와 kube-proxy 모드, VPC CNI 카운터, 그 노드에 있는 컨트롤러의 메트릭은 보지 못했어요. 4개는 수명 주기 정책이 없는 ECR 저장소 조회이고, 1개는 ALB 컨트롤러 파드 메트릭 읽기 시간 초과예요. Grafana 데이터소스와 대시보드는 API 토큰이 없어 건너뛰었고, KEDA 오퍼레이터 메트릭은 메트릭 엔드포인트가 꺼져 있어 못 읽었어요. apiserver LIST·PATCH p99 0.7초와 Prometheus 스로틀링 22% 는 수집 중에 측정된 값이라 사용자 영향으로 세지 않았어요. 컨테이너 로그는 수집 범위 밖이라 app-q-ai 가 OOM 직전에 무엇을 하고 있었는지는 몰라요. NLB 보안 그룹은 스냅샷에 없어서 스냅샷 밖에서 따로 읽었어요.

## 숫자
| 심각도 | fail | warn | 지난 full 점검 대비 |
|---|---|---|---|
| critical | 1 | 0 | fail ±0, warn −2. 지난 full 1차 1 / 2. SLO 없음과 증상 알림 없음을 규칙 ③ 대로 high 로 셌어요 |
| high | 23 | 12 | fail −13, warn −11. 지난 full 1차 36 / 23 |
| medium | 118 | 162 | fail +11, warn −8. 지난 full 1차 107 / 170 |
| low | 17 | 158 | fail −1, warn +22. 지난 full 1차 18 / 136 |
| info | 2 | 1 | fail ±0, warn +1. 지난 full 1차 2 / 0 |

지난 full 점검 2026-10-27 15:30 에는 리포트가 없어서 그 1차 숫자와 비교했어요. 이번 최종 critical+high 36개는 이번 1차 60개보다 24개 적어요. 내린 이유는 세부 리포트 1-1 절에 있고, `history.csv` 는 1차 기준이에요.

세부, 모든 표와 전체 1차 목록: [`report-details.md`](report-details.md) · kubegap 0.1.2, 룰 0.1.63 · 스냅샷 `~/.kubegap/snapshots/my-cluster/2026-11-03T11-17-15`
