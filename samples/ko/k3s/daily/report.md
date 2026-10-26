# default (k3s, 노드 node-a·node-b) — daily 점검, 2026-10-26 16:46 KST

이 클러스터는 `default` 컨텍스트로 접속하는 2노드 k3s 예요. 서버 버전은 v1.33.5+k3s1, 프로필은 lab, 네임스페이스 26개 중 프로덕션이 7개예요. 급한 장애는 없습니다. 16:18 KST daily 점검 이후 바뀐 것은 하나예요. `app-f-prod/app-f-api-server` 의 HPA 가 16:27:56 KST 에 레플리카를 5 에서 3 으로 줄였고, 그 덕에 16:18 리포트의 CPU 스로틀링과 N+1 부족이 1차 결과에서 사라졌어요. 고친 것은 없고 500m CPU 제한은 그대로라, 다음 CPU 순간 상승 때 같은 일이 다시 생겨요. 마지막 full 점검은 오늘 16:27 KST 라 full 점검은 아직 필요 없어요.

## 지금 손봐야 할 문제 3개

### 1. `app-f-prod/app-f-api-server` 는 HPA 가 줄여서 조용해졌을 뿐이고, 500m CPU 제한은 오늘 세 번째로 같은 일을 만들었어요
**문제.** `app-f-prod` 의 `app-f-api-server` Deployment 는 `app-f-api-prod.acme.com`, `example-k.kr`, `www.example-k.kr` 뒤의 API 예요. 오늘 HPA 가 13:35, 16:11, 16:14 KST 에 늘리고 16:27:56 KST 에 5 에서 3 으로 줄였어요. 늘어날 때마다 새 파드가 `node-a` 한 노드에만 올라가고, 500m CPU 제한 때문에 시작 중에 CPU 주기의 절반 이상이 멈춰서 Ready 까지 91초가 걸려요. 늘어난 동안에는 CPU requests 합계가 `node-b` 를 잃었을 때 남는 용량을 넘어서 N+1 이 깨져요. 지금은 3 레플리카라 지표가 전부 내려왔지만, 바뀐 설정은 없어요.

**근거.** 16:27:56 KST 에 SuccessfulRescale "New size: 3; reason: All metrics below target" 이 찍혔고 오늘 누적 13건이에요. 출처는 `events.json` 이에요. 남은 새 파드 `app-f-api-server-5d6b56f78b-vh2ct` 의 5분 스로틀링 비율은 46.1% 에서 8.7% 로 내려왔어요. 출처는 `metrics/cpu_throttle_ratio_5m.json` 이에요. 이 파드는 16:11:55 KST 에 만들어져 16:13:26 KST 에 Ready 가 됐어요. 출처는 `objects/pods.json` 이에요. CPU requests 합계는 6.31코어에서 6.06코어로 내려왔고, `node-b` 없이 쓸 수 있는 CPU 는 6.0코어예요. 출처는 `summary.json resilience.n_plus_one` 이에요. 컨테이너 `app` 은 requests cpu 100m, limits cpu 500m 그대로예요. 출처는 `objects/deployments.json` 이에요. HPA 는 min 2, max 5, 현재 3, CPU 사용률 13%, 목표 60% 예요. 출처는 `objects/horizontalpodautoscalers.autoscaling.json` 이에요.

**원인.** 메커니즘은 확인됐어요. HPA 가 CPU 사용량을 100m request 로 나누기 때문에 파드당 60m 만 넘어도 늘리고, 새 파드가 시작하며 쓰는 CPU 를 500m 제한이 막아서 1분 반 동안 Ready 가 안 돼요. 순간 상승이 지나면 300초 안정화 창 뒤에 다시 줄여요. N+1 판정은 지금 6.06코어 대 6.0코어로 2% 허용 오차 안에서 통과한 것이라 여유가 사실상 없어요. 이 서비스에는 요청·오류·지연 메트릭이 없어서 사용자가 느꼈는지는 클러스터에서 읽을 수 없어요.

**조치.** ① 컨테이너 `app` 의 CPU 제한을 빼고 100m request 는 유지해요. 이렇게 하면 늘어날 때 스로틀링이 없어지고 시작이 빨라지며, requests 가 그대로라 스케줄링은 안 바뀌어요. Git 과 Argo CD 로 10분 걸려요. ② readiness·liveness 프로브의 `timeoutSeconds` 를 1 에서 3 으로 올리고, liveness 에는 `/healthcheck` 와 다른 경로를 줘요. 느린 시작을 죽은 프로세스로 오인하지 않게 돼요. 20분 걸려요. ③ 일주일치 데이터로 HPA 목표를 정해요. 늘었다 줄었다가 하루 세 번씩 이어지면 CPU 목표를 80% 로 올리거나 request 를 200m 으로 올려서, 짧은 순간 상승이 파드 세 개와 N+1 여유 300m 을 먹지 않게 해요. 읽는 데 30분 걸려요.
```yaml
# app-f-prod/deployment/app-f-api-server, container app
resources:
  requests: {cpu: 100m, memory: 1088Mi}
  limits: {memory: 2720Mi}   # cpu limit removed
```

**왜 이런 일이 생기나.**
- 원리: 커널은 CPU 제한을 100ms CFS 주기마다 쓸 수 있는 할당량으로 적용해요. 주기 초반에 할당량을 다 쓴 프로세스는 남은 시간 동안 멈추기 때문에 평균 CPU 는 낮아 보이고 시작과 응답만 느려져요. HPA 는 제한이 아니라 request 대비 사용률로 늘리므로, 작은 request 와 낮은 제한을 같이 두면 스로틀링과 스케일아웃이 동시에 일어나고 늘어난 파드마다 request 만큼 N+1 여유를 먹어요.
- 사례: Buffer 2020 과 Omio 2020 사례가 cpu-throttling 체크 정의에 있어요. 두 곳 모두 평균 CPU 가 낮은 서비스에서 스로틀링으로 인한 지연을 찾아 CPU 제한을 뺐어요.
- 더 알아보기: "CFS bandwidth control (kernel sched-bwc)", "Kubernetes docs: HorizontalPodAutoscaler algorithm details", "Kubernetes docs: Resource Management for Pods and Containers".

근거 체크: `resilience.replicas-same-node.app-f-prod/deployment/app-f-api-server`, `resilience.single-eligible-node.app-f-prod/deployment/app-f-api-server`, `traffic.pod-not-ready.app-f-prod/app-f-api-server` (pass 로 판단, 시작 시간), `resilience.liveness-dependency-path.app-f-prod/deployment/app-f-api-server:app`, `resources.cpu-request-overprovisioned.app-f-prod/deploy/app-f-api-server:app`, `observability.golden-signals-missing.app-f-prod/app-f-api-server-ingress`, 그리고 이번에 resolved 된 `resources.cpu-throttling.app-f-prod/deploy/app-f-api-server:app` 과 `resilience.n-plus-one.cluster`

### 2. `app-c-prod/app-c-coturn` 이 7,899번 재시작했고, 아직 아무도 원인을 읽지 않았어요
**문제.** app-c 앱의 TURN 서버가 노드 `node-a` 에서 CrashLoopBackOff 상태예요. TURN 서버는 WebRTC 통화가 NAT 를 넘도록 중계하는 서버예요. Deployment 의 available 이 0 이라 중계가 필요한 app-c 통화는 실패해요. 2026-10-25 이후 모든 리포트에서 1번 또는 2번 문제였고 조치는 아직 손대지 않았어요.

**근거.** 재시작 7,899회, 16:18 KST 이후 5회 늘었어요. 출처는 `objects/pods.json` 이에요. BackOff 경고 이벤트가 7,371건에서 7,509건으로 29분에 138건 늘었고 전부 이 파드 하나예요. 출처는 `diff.json events.changed` 예요. 마지막 종료는 16:42:01 KST, 종료 코드 255, 시작과 종료가 같은 초예요. 출처는 `objects/pods.json` lastState 예요. Deployment `app-c-coturn` 은 desired 1, available 0 이에요. 출처는 `summary.json objects.deployments.unavailable` 이에요. 이미지는 `coturn/coturn:latest`, CPU 제한 200m, 메모리 제한 128Mi, 프로브 없음이에요. 출처는 `objects/deployments.json` 이에요.

**원인.** 추정입니다. 1초 안에 255 로 끝나는 프로세스는 시작 단계에서 실패하는 것이고, 대개 설정 오류나 포트 바인딩 실패예요. 컨테이너 로그는 kubegap 수집 범위 밖이라 정확한 메시지는 몰라요. `:latest` 태그라 2026-10-25 노드 재부팅 때 매니페스트 변경 없이 바이너리가 바뀌었을 수 있어요.

**조치.** ① 마지막 크래시 메시지를 읽어요. 10분 걸려요.
```bash
kubectl -n app-c-prod logs app-c-coturn-549854dfcb-jgp4h -c coturn --previous | tail -50
```
② 포트 충돌이면 `node-a` 에서 `ss -lunp | grep 3478` 로 3478 을 쓰는 프로세스를 찾아요. 5분 걸려요. ③ 인자를 고치고 이미지 태그를 다이제스트나 버전으로 고정하고 3478 에 tcpSocket 프로브를 붙여요. 30분 걸려요. 이렇게 하면 app-c 통화가 복구되고 시간당 약 280건의 BackOff 이벤트가 멈추며, 늘 울리는 알림 KubePodCrashLooping 과 KubeDeploymentReplicasMismatch 가 조용해져요. ④ 오늘 못 고치면 Deployment 를 0 으로 줄여 이벤트 소음을 멈출 수 있어요. 그 결정은 운영자 몫이에요.

**왜 이런 일이 생기나.**
- 원리: 재시작의 원인은 OOMKilled, liveness 프로브 실패, 애플리케이션 자체 종료 셋 중 하나예요. 프로브가 없는데 1초 안에 255 로 끝나면 세 번째라서, 다음 단계는 이전 컨테이너의 로그뿐이에요. 제한을 올리거나 프로브를 바꿔도 여기서는 도움이 안 돼요.
- 사례: 이 체크 정의에 기록된 공개 사례는 없어요.
- 더 알아보기: "Kubernetes docs: Debug Running Pods, kubectl logs --previous", "CrashLoopBackOff backoff timing (kubelet)", "Kubernetes docs: Images, image tags versus digests".

근거 체크: `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn`, `events.tracked-warning-reasons.BackOff`, `traffic.pod-not-ready.app-c-prod/app-c-coturn`, `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn`, `hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn`, `observability.alerts-always-firing.KubePodCrashLooping`, `observability.alerts-always-firing.KubeDeploymentReplicasMismatch`, `resilience.single-replica-in-prod.app-c-prod/app-c-coturn`

### 3. `app-i-prod/app-i-web` 와 Postgres 세 개의 CPU 스로틀링이 점검마다 10% 를 넘나들고, 원인인 낮은 CPU 제한은 그대로예요
**문제.** `example-i.dev` 를 서빙하는 `app-i-prod/app-i-web` 이 이번에 다시 warn 으로 올라왔어요. 레플리카 1개에 CPU 제한 300m 이고, liveness 와 readiness 가 같은 경로 `/` 를 timeout 1초로 봐요. 스로틀링이 심해지는 순간에 프로브가 늦으면 하나뿐인 파드가 트래픽에서 빠지거나 재시작돼요. `app-d-prod/app-d-postgres`, `app-d-prod/app-d-postgres-mx`, `app-g-prod/app-g-postgres` 세 StatefulSet 도 150m 제한에서 같은 식으로 경계선을 오가요. 네 건 모두 14:43 이후 리포트마다 resolved 와 new 를 번갈아 찍고 있어요.

**근거.** `app-i-web-7545d66987-mzgxd` 의 5분 스로틀링 비율은 11.7% 예요. 15:30 에 10.5%, 16:18 에 7.9% 였어요. 출처는 `metrics/cpu_throttle_ratio_5m.json` 이에요. 이 파드의 7일 CPU p95 는 0.007코어예요. 출처는 `metrics/cpu_p95_7d_cores.json` 이에요. 컨테이너 `web` 은 requests cpu 50m, limits cpu 300m 이에요. 출처는 `objects/deployments.json` 이에요. 같은 파일에서 `app-d-postgres-mx-0` 은 12.2%, `app-d-postgres-0` 은 10.0%, `app-g-postgres-0` 은 7.1% 예요. 세 StatefulSet 의 CPU 제한은 150m 이에요. 출처는 `objects/statefulsets.json` 이에요. `app-i-web` 은 HPA 없이 레플리카 1개예요. 출처는 `summary.json scaling` 이에요.

**원인.** 확인된 것은 평균 사용량이 제한의 2~3% 인데도 CPU 를 순간적으로 몰아 쓰는 구간마다 CFS 주기가 멈춘다는 점이에요. 추정입니다. 제한이 낮을수록 짧은 작업 하나가 한 주기 할당량을 다 쓰기 쉬워서 비율이 10% 근처에서 요동쳐요. 어느 쪽도 오브젝트가 바뀌지 않았으니 값 변화는 측정 시점 차이예요.

**조치.** ① `app-i-web` 컨테이너 `web` 의 CPU 제한을 빼요. 5분 걸려요. ② 같은 방식으로 Postgres StatefulSet 세 개의 150m CPU 제한을 빼요. 각 5분 걸려요. 이렇게 하면 네 건의 플래핑이 끝나고 매 리포트의 new·resolved 소음이 사라져요. ③ `app-i-web` 의 프로브 `timeoutSeconds` 를 3 으로 올리고 레플리카를 2 로 늘려요. 15분 걸려요.
```yaml
# app-i-prod/deployment/app-i-web, container web
resources:
  requests: {cpu: 50m, memory: 128Mi}
  limits: {memory: 512Mi}   # cpu limit removed
```

**왜 이런 일이 생기나.**
- 원리: 스로틀링 비율은 "멈춘 CFS 주기 ÷ 전체 주기" 라서 평균 사용량과 무관하게 짧은 작업의 패턴으로 결정돼요. 5분 창의 값은 측정 시점에 따라 흔들리므로 임계값 근처의 값은 추세로 읽고, 고정된 판단은 7일 p95 와 제한의 비율로 해요.
- 사례: Buffer 2020 과 Omio 2020 사례가 cpu-throttling 체크 정의에 있어요. 두 곳 모두 CPU 제한을 빼서 지연을 줄였어요.
- 더 알아보기: "CFS bandwidth control (kernel sched-bwc)", "Kubernetes docs: Configure Liveness, Readiness and Startup Probes", "container_cpu_cfs_throttled_periods_total".

근거 체크: `resources.cpu-throttling.app-i-prod/deploy/app-i-web:web` (재발), `resources.cpu-throttling.app-d-prod/sts/app-d-postgres-mx:postgres`, `resilience.single-replica-in-prod.app-i-prod/app-i-web`, `resilience.liveness-dependency-path.app-i-prod/deployment/app-i-web:web`, `scaling.no-hpa-serving-prod.app-i-prod/app-i-web`, `observability.golden-signals-missing.app-i-prod/app-i-web`

번외로 금방 끝나는 것 하나: `app-a-prod/app-a-sandbox-watchdog` CronJob 은 매분 돌고 Job 하나가 50초 걸리는데, 그 파드들이 CPU 제한 300m 에서 75%~91% 스로틀링 상태예요. 출처는 `metrics/cpu_throttle_ratio_5m.json` 과 `objects/cronjobs.batch.json` 이에요. Job 파드는 스로틀링 체크에서 원래 건너뛰게 되어 있어서 발견 사항에는 없어요. CPU 제한을 빼면 실행 시간이 줄어 다음 분과 겹칠 위험이 함께 줄어요. 5분 걸려요.

## 지난 daily 점검 이후 (2026-10-26 16:18 KST)
29분 사이 바뀐 오브젝트는 `app-f-prod/app-f-api-server` Deployment 하나예요. HPA 가 16:27:56 KST 에 "All metrics below target" 으로 레플리카를 5 에서 3 으로 줄였고, 그 순간 새 파드 두 개가 지워졌어요. 그래서 16:18 리포트의 새 발견 사항 세 건이 전부 사라졌어요. `app-f-api-server` 의 스로틀링은 남은 새 파드가 8.7% 로 내려가 resolved, N+1 은 requests 6.06코어로 다시 통과, readiness 비율은 fail 에서 warn 으로 내려왔고 저는 시작 시간으로 보고 pass 로 판단했어요. 고쳐서 사라진 것은 하나도 없어요. 컨트롤 플레인의 5xx 와 PATCH 지연 두 건도 resolved 로 찍혔지만 이는 수집 중에 측정된 값이 이번에 안 나온 것이라 클러스터 변화가 아니에요. 새 발견 사항은 `app-i-web` 의 스로틀링 11.7% 하나이고, 오브젝트 변경 없이 10% 경계를 오가는 플래핑이라 재발로 표시했어요. `app-c-coturn` 은 BackOff 138건과 재시작 5회를 더했고, `argocd-repo-server` 의 liveness 프로브는 이번 수집 동안 실패하지 않아 Unhealthy 가 33건 그대로예요. 룰 버전은 0.1.50 그대로라 기준 변경은 없어요. critical·high fail 31건이 그대로 남아 있어요. 세부 2절을 보세요.

지난 리포트 문제의 진행: (1) `app-f-api-server` 의 CPU 제한 제거는 아직 손대지 않음, `objects/deployments.json` 에 limits cpu 500m 그대로. (2) `app-c-coturn` 크래시 로그 읽기는 아직 손대지 않음, 재시작 7,894회에서 7,899회. (3) `argocd-repo-server` 프로브 조정은 아직 손대지 않음, liveness timeoutSeconds 5 그대로이고 메트릭 프록시 502 재발. 목록 밖의 빠른 조치였던 Postgres StatefulSet 세 개의 CPU 제한 제거도 아직 손대지 않음, `objects/statefulsets.json` 에 150m 그대로.

## 이번에 확인 못 한 것
daily 모드라 345개 체크 중 56개는 평가하지 않았어요. 노드 OS, k3s 저널, etcd, 스케줄러, kubelet, helm, krr, polaris, pluto, kubent 가 여기에 들어가요. 마지막 full 점검은 오늘 16:27 KST 예요. Loki 가 설치되어 있지 않아 그 5개 체크는 원래 건너뛰게 되어 있고 로그는 Elasticsearch 와 fluent-bit 에서 와요. 빠진 도구는 없어요. 수집 단계 실패는 없고, 명령 343건 중 2건이 실패했어요. `argocd-repo-server` 의 파드 프록시 메트릭 요청이 502 였고, `node-a` 의 MetalLB speaker 메트릭 첫 시도가 API 서버 프록시에서 타임아웃된 뒤 SSH 로 받았어요. Grafana 데이터소스·대시보드 단계는 `config.yaml` 에 `grafana_api_token` 이 없어 건너뛰었어요. API 서버 LIST p99 0.948초는 kubegap 이 오브젝트 LIST 약 100건을 보내던 16:46:55~16:48:09 KST 에 측정된 값이라 사용자 영향으로 세지 않았어요. 컨테이너 로그는 수집 범위 밖이라 `app-c-coturn` 의 크래시 메시지는 이번에도 읽지 못했어요.

## 숫자
| 심각도 | fail | warn | 지난 daily 대비 |
|---|---|---|---|
| critical | 1 | 2 | fail 0 · warn 0 |
| high | 30 | 59 | fail −2 · warn +1 |
| medium | 55 | 101 | fail 0 · warn 0 |
| low | 9 | 107 | fail 0 · warn 0 |
| info | 0 | 1 | warn −2 |

최종 critical·high 합계 92 는 1차 결과 95 보다 3 적어요. Unhealthy 이벤트 warn 은 새 발생이 없어 medium 으로, cert-manager 재시작 warn 두 건은 런타임 재시작이라 pass 로 판단했어요. `history.csv` 는 1차 결과 숫자를 유지해요.

세부, 모든 표와 1차 결과 전체 목록: [`report-details.md`](report-details.md) · kubegap 0.1.0, 룰 0.1.50 · snapshot `~/.kubegap/snapshots/default/2026-10-26T16-46-55`
