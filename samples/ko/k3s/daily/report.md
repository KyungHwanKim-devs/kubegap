# default — daily 점검, 2026-11-05 17:01

지금 급한 일: 있음 — app-c-prod의 TURN 서버 app-c-coturn이 시작 옵션 오류로 최소 12일째 뜨지 못하고 있어요.

오늘 할 일 3개: ① app-c-coturn 시작 옵션 고치기 ② node-b의 DB 덤프와 etcd 스냅샷을 노드 밖으로 복사하기 ③ 모니터링 저장소를 PVC로 바꾸기(지금 지표는 지워짐)

지난 점검 이후:

- 지난 리포트: 2026-10-27 점검에는 리포트가 없었어요. 그래서 권한 조치를 했는지는 비교하지 못했어요.
- 새로 생김 5개: 전체 CPU 요청 합이 5.99코어에서 6.17코어로 늘어 node-a의 6.0코어를 넘었어요. 나머지는 keda-operator 재시작 10번, cert-manager ACME challenge 실패 10번, elasticsearch-0 CPUThrottlingHigh 3.1일째, CoreDNS 업스트림 헬스 체크 실패 1시간에 1번이에요.
- 사라짐 9개: CPU 스로틀링 경고 3개, 메모리 limit 근접 2개, arc-actions-runner-controller 재시작, app-f-app-w HPA 흔들림, argocd-repo-server 준비 안 됨, apiserver watch 수 과다가 사라졌어요. 로그 경고 몇 개는 클러스터가 아니라 점검 기준이 바뀌어서 이름이 바뀌거나 안 잡혀요.

## 클러스터 한눈에

| 항목 | 값 |
|---|---|
| 노드 | 2대 중 Ready 2대 |
| 파드 | 실행 96, 대기 0, 실패 4 |
| 네임스페이스 | 26개, 프로덕션 7개 |
| 컴포넌트 | 23: actions-runner-controller, alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, flannel, fluent-bit, fluent-bit-events, grafana, ingress-nginx, k3s, keda, kube-proxy, kube-state-metrics, local-path-provisioner, metallb, metrics-server, node-exporter, prometheus, prometheus-operator, reloader |
| 메트릭·로그 저장소 | prometheus 3.7.3 / 없음 |
| Kubernetes | v1.33.5+k3s1 (k3s) |

## 다가오는 일

| 언제 | 무엇 | 출처 |
|---|---|---|
| 2026-11-06 | app-g-prod/app-g-prod-tls의 자동 갱신 예정 시각이에요. 만료는 2026-12-06이에요. 클러스터에서 가장 먼저 만료되는 인증서예요. | summary.json |
| 이미 지남 (2026-06-28) | 쿠버네티스 v1.33 upstream 지원이 끝났어요. 보안 패치가 더 나오지 않아요. | findings-draft.json |
| 매일 03:00 UTC | kube-system/containerd-cleanup-node-a, containerd-cleanup-node-b가 돌아요. 이름으로 보면 노드의 containerd 정리 작업이에요. 무엇을 지우는지는 안 읽었어요. | summary.json |
| 매일 04:00 UTC, 04:30 UTC | registry/registry-gc와 registry/registry-tag-cleanup이 node-b의 레지스트리에서 이미지를 정리해요. | summary.json |
| 매일 04:20 UTC | logging/es-index-retention이 오래된 Elasticsearch 인덱스를 정리해요. | summary.json |
| 지금 | app-i-prod 쿼터의 PVC 개수가 2/2로 꽉 찼어요. | summary.json |

## 1. 시작 옵션 오류로 계속 죽는 app-c-coturn

**상황.** app-c-coturn 파드는 뜨자마자 exit 255로 끝나고 CrashLoopBackOff 상태예요. 2026-10-24 점검 때 이미 재시작이 7418번이었으니 최소 12일째예요. 2026-11-05 17:01 수집 기준으로 지난 24시간 동안 Ready였던 시간은 0분이에요.

- 영향 있음: app-c-prod/app-c-coturn. 파드는 ready false이고 Deployment는 Available=False예요. 로그에 `unrecognized option '--no-dtls'`가 찍혀 있어요.
- 확인했고 멀쩡: app-c-signaling, app-c-web, app-c-postgres-0은 Running이고 Ready예요.
- 다른 이유로 바뀜: 없음
- 안 봄: 실제 사용자 통화가 실패했는지는 못 봤어요. 볼 메트릭이 없어요. app-c-web과 app-c-signaling이 TURN 주소와 비밀번호를 어디서 읽는지, 3478과 49152~49252 포트가 인터넷에서 닿는지도 안 봤어요.

**이유.** 지금 받은 coturn 이미지가 `--no-dtls`를 모르는 옵션으로 보고 거부해요. 확인됨.

Deployment가 `coturn/coturn:latest`를 imagePullPolicy Always로 받아요. 그사이 새 이미지가 들어오면서 깨진 것으로 보여요. 그 이미지가 언제 들어왔는지는 몰라요.

**권하는 조치.**

① 죽기 직전 로그로 원인이 같은지 확인하세요.

```
kubectl -n app-c-prod logs deploy/app-c-coturn --previous --tail=5
```

아무것도 바뀌지 않아요.

확인: 출력에 `unrecognized option '--no-dtls'`가 있으면 원인이 같아요. ②로 가세요.

② app-c-web과 app-c-signaling이 TURN 비밀번호를 어디서 읽는지 먼저 찾으세요.

③에서 TURN 비밀번호를 바꿔요. 클라이언트에 내려 주는 값도 같이 바꾸지 않으면 TURN이 떠도 인증에 실패해요.

이 위치는 점검에서 아무도 확인하지 않았어요.

확인: 위치를 찾았으면 ③으로 가세요. 못 찾았으면 ③은 미루세요.

③ ①에서 같은 줄이 나왔고 ②에서 위치를 찾았을 때만 하세요. manifests 저장소 prod/app-c에 있는 app-c-coturn Deployment를 커밋 하나로 고치세요. 이 커밋에 아래를 다 넣어요.

- args에서 `--no-dtls`와 `--no-cli`를 빼요.
- 이미지를 지금 digest로 고정하고 imagePullPolicy를 IfNotPresent로 바꿔요.
- 배포 전략을 Recreate로 바꿔요.
- `--user=<사용자>:<비밀번호>`를 긴 무작위 비밀번호로 바꿔요. 비밀번호는 Git에 평문으로 두지 말고 Secret app-c-coturn-auth에 두세요. Secret은 kubectl로 직접 만들거나 External Secrets로 만들면 돼요.
- 파드·서비스 대역과 노드 LAN 대역으로 가는 릴레이를 막아요. 클라이언트가 LAN 주소로 붙어야 하는지 아무도 확인하지 않았다면 막는 게 기본이에요.
- app-c-web이나 app-c-signaling 쪽의 TURN 비밀번호도 같이 바꿔요.

```yaml
spec:
  strategy:
    type: Recreate
  template:
    spec:
      containers:
        - name: coturn
          image: coturn/coturn@sha256:bbefd3e1fdfdc0d58770fe01b581fd8b00d9f3a5580d00acb77cf719a6bc78e3
          imagePullPolicy: IfNotPresent
          env:
            - name: TURN_PASSWORD
              valueFrom:
                secretKeyRef: {name: app-c-coturn-auth, key: password}
          # args에서 "--no-dtls", "--no-cli", "--user=<사용자>:<비밀번호>"를 지우고 아래를 더해요
          #   - "--user=<사용자>:$(TURN_PASSWORD)"
          #   - "--denied-peer-ip=<ip>-<ip>"
          #   - "--denied-peer-ip=<ip>-<ip>"
          #   - "--no-multicast-peers"
# Secret app-c-coturn-auth는 kubectl로 직접 만들거나 External Secrets로 만들어요. 클라이언트(app-c-web, app-c-signaling)에 넣는 TURN 비밀번호도 같이 바꿔야 해요.
```

Argo CD 앱 app-c이 커밋을 바로 적용해요. Recreate라서 죽어 있는 파드를 먼저 지우고 node-a에 새 파드를 띄워요.

두 옵션을 빼도 동작은 같아요. 이 이미지는 DTLS와 CLI가 기본으로 꺼져 있어요.

레플리카가 1개라 교체하는 동안 TURN이 없어요. 지금도 Ready 파드가 0개라 더 멈추는 건 없어요. kubectl로 직접 고치면 selfHeal이 Git 상태로 되돌려요.

살아나면 hostNetwork로 node-a의 모든 인터페이스에서 3478 UDP/TCP를 듣고, 49152~49252 포트로 릴레이해요. 공인 주소를 알리지만, 라우터가 그 포트를 열어 뒀는지는 확인되지 않았어요.

밖에서 닿는데 사용자명과 같은 비밀번호를 그대로 두면 누구나 비밀번호를 짐작해서 릴레이를 쓸 수 있어요. LAN 대역을 막지 않으면 그 릴레이로 노드 <ip>과 <ip>의 포트에 닿아요.

coturn은 첫 옵션 오류에서 멈춰요. 그래서 다른 옵션이 또 걸리는지는 적용한 뒤에야 알 수 있어요. node-a에서 3478 포트를 다른 프로세스가 쓰고 있는지도 몰라요.

확인: `kubectl -n app-c-prod get pods -l app=app-c-coturn`이 1/1 Running이고 RESTARTS가 더 늘지 않아요. `kubectl -n app-c-prod logs deploy/app-c-coturn --tail=20`에 unrecognized option 줄이 없으면 끝이에요.

**되돌리기.** 그 커밋을 git revert 하면 Argo CD가 원래 매니페스트로 되돌려요. 계속 죽던 상태로 돌아갈 뿐이고, 데이터를 가진 워크로드가 아니라 잃는 건 없어요.

**왜 이런 일이 생기나.**

- 원리: `:latest` 태그 이미지는 재시작이나 노드 교체 때 다른 바이너리로 뜰 수 있어요. 어떤 버전이었는지 기록이 남지 않아서 되돌리기도 어려워요. 그래서 버전이나 digest로 고정하고 IfNotPresent를 쓰는 게 기본이에요.
- 읽을 것: Kubernetes 문서 Images의 Image pull policy, coturn turnserver 도움말

**근거.**

| 항목 | 값 | 출처 |
|---|---|---|
| 죽기 직전 로그 첫 줄 | `turnserver: unrecognized option '--no-dtls'` | extra/coturn-previous-head.txt |
| 도움말의 DTLS 설명 | `--dtls`만 있음, 기본으로 꺼짐 | extra/coturn-help-full.txt |
| 이미지와 받는 방식 | coturn/coturn:latest, Always | objects/deployments.json |
| 재시작, 파드 생성 2026-03-20 이후 누적 | 10710번 | summary.json |
| 재시작, 최근 7일 | 1963번 | metrics/restarts_7d.json |
| Ready가 아니었던 시간, 24시간 | 1440분 | summary.json |

## 2. node-b 디스크 한 곳에 같이 있는 DB 원본과 백업

**상황.** prod DB는 nodeSelector와 local-path 볼륨 때문에 전부 node-b 디스크에 있어요. DB 백업 CronJob 7개는 오늘도 성공했지만, 덤프를 노드 안 PVC에만 써요. 그중 5개는 원본과 같은 node-b에 써요.

k3s etcd 스냅샷도 전부 node-b 로컬 파일이에요. 지금 깨진 건 없어요. 다만 node-b 디스크가 망가지면 DB와 덤프와 클러스터 상태를 한꺼번에 잃어요.

- 영향 있음:
  - 원본과 덤프가 둘 다 node-b에 있어요. app-d-postgres, app-d-postgres-vn, app-f-mysql, app-g-postgres, app-e-postgres가 그래요.
  - app-a-postgres, app-d-postgres-mx는 원본이 node-b, 덤프가 node-a에 있어요. 노드 밖 사본은 없어요.
  - app-c-prod/app-c-postgres는 백업 CronJob이 없어요.
  - app-e-api/app-e-minio 데이터는 백업이 전혀 없어요. app-e-postgres-backup은 Postgres만 덤프해요.
  - etcd 스냅샷 5개가 전부 node-b 로컬 파일이에요.
  - node-b를 잃으면 node-b에 묶인 파드 19개는 node-a에서 뜰 수 없어요.
- 확인했고 멀쩡: 백업 CronJob 7개가 모두 있어요. etcd 스냅샷도 12시간마다 만들어지고 있어요.
- 다른 이유로 바뀜: CPU 요청 합이 5.99코어에서 6.17코어로 늘어난 0.18코어 중 0.13코어만 app-f-prod HPA가 파드를 늘린 몫이에요. node-a로 옮길 수 있는 파드 29개는 node-a에 다 들어가요. 그래서 요청을 줄여도 이 문제는 안 풀려요.
- 안 봄: 덤프 크기와 복원 가능 여부, node-b 디스크 상태는 안 봤어요. 다른 PC가 덤프를 가져가는 경로가 있는지도 안 봤어요. registry, app-f-qdrant, elasticsearch, Redis 데이터의 백업도 안 봤어요.

**이유.** 백업 CronJob이 덤프를 노드의 local-path PVC에만 쓰고, 노드 밖으로 보내는 단계가 없어요. 추정.

노드 밖 전송 흔적은 명령, 인자, 환경 변수 문자열에서만 찾았어요. 그래서 이미지 안의 스크립트가 따로 올리고 있을 가능성은 남아 있어요.

**권하는 조치.**

① 백업 PVC가 어느 노드의 어느 디렉터리에 있는지 확인하세요.

```
kubectl get pv -o custom-columns=PV:.metadata.name,NS:.spec.claimRef.namespace,CLAIM:.spec.claimRef.name,SC:.spec.storageClassName,PATH:.spec.hostPath.path,LOCAL:.spec.local.path,NODE:.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0] | grep -i backup
```

아무것도 바뀌지 않아요. 이 명령으로는 클러스터 밖에 이미 사본이 있는지는 못 봐요.

확인: backup이 들어간 PVC 7개의 경로와 노드가 나오면 돼요. ②부터 이 경로를 써요.

② ①에서 경로가 나왔다면, 시간부터 보세요. 백업 CronJob과 containerd-cleanup이 도는 02:40~04:30 UTC를 피해야 해요. 한국 시간으로는 11:40~13:30이에요. 그 시간을 피해서 받을 폴더를 만드세요.

```
D=~/node-b-backup/$(date +%F); mkdir -p $D
```

이 PC에 폴더가 하나 생겨요. ③~⑤는 이 터미널에서 이어서 돌려야 $D가 남아 있어요.

확인: 폴더가 생겼으면 돼요.

③ node-b에서 etcd 스냅샷과 서버 토큰을 받으세요.

```
ssh <사용자>@<ip> 'sudo tar -C /var/lib/rancher/k3s/server -czf - db/snapshots token' > $D/etcd-snapshots-and-token.tgz
```

node-b 디스크를 읽어서 이 PC에 압축 파일을 만들어요. 클러스터는 바뀌지 않아요. 복원에 토큰이 필요한지는 검증하지 않았지만 같이 받아 두세요.

스냅샷과 토큰이 같이 있으면 클러스터의 모든 Secret을 풀 수 있어요. 받은 파일은 암호화된 디스크에 두고, 공유 폴더에는 두지 마세요.

node-b에는 최신 스냅샷 5개, 약 2.5일치만 남아요. containerd-cleanup-node-b가 매일 나머지를 지워요.

ssh 사용자는 확인되지 않았어요. sudo가 비밀번호를 물으면 명령이 멈춰요.

확인: `tar -tzf $D/etcd-snapshots-and-token.tgz`에 db/snapshots/etcd-snapshot-node-b-* 파일과 token이 보여요.

④ node-b에 있는 덤프 PVC 5개를 하나씩 받으세요. ①에서 나온 경로와 PVC 이름을 넣으면 돼요.

```
ssh <사용자>@<ip> 'sudo tar -C <node-b 덤프 경로> -czf - .' > $D/<pvc 이름>.tgz
```

덤프에는 고객 데이터가 그대로 들어 있어요. ③과 똑같이 다루세요.

복사하는 동안 node-b 디스크 읽기가 늘어요. 덤프 크기를 몰라서, 이 PC에 자리가 충분한지도 몰라요.

확인: 압축 파일 5개가 생기고 모두 크기가 0보다 커요.

⑤ node-a에 있는 덤프 PVC 2개를 받으세요. app-a-postgres-backup-pvc와 app-d-postgres-mx-backup-pvc예요.

```
ssh <사용자>@<ip> 'sudo tar -C <node-a 덤프 경로> -czf - .' > $D/<pvc 이름>.tgz
```

위험은 ④와 같고, 이번에는 node-a 디스크 읽기가 늘어요.

확인: 덤프 압축 파일이 모두 7개이고, 7개 다 크기가 0보다 크면 끝이에요.

이건 오늘 한 번 사본을 만들어 두는 거예요. 노드 밖으로 계속 보내는 방법은 따로 정해야 해요. app-e-minio 데이터는 이번 복사에 들어가지 않아요.

**되돌리기.** 클러스터를 바꾸지 않아서 되돌릴 게 없어요. 받은 압축 파일만 지우면 돼요.

**왜 이런 일이 생기나.**

- 원리: 백업은 노드 디스크가 죽어도 복구하려고 해요. 덤프 PVC가 원본 DB와 같은 노드의 local-path면, 디스크 하나만 고장 나도 원본과 백업을 같이 잃어요. 한 번도 복원해 보지 않은 덤프는 막상 쓰려 할 때 안 될 수 있어요.
- 읽을 것: k3s 문서 etcd-snapshot의 S3 설정, rclone 문서 rclone copy

**근거.**

| 항목 | 값 | 출처 |
|---|---|---|
| DB 백업 CronJob, 그중 원본과 같은 노드 | 7개, 5개 | summary.json |
| 노드 밖 전송 흔적 | 7개 모두 없음 | summary.json |
| etcd 스냅샷, 2026-11-03~11-05 | 5개, 모두 node-b 로컬 | objects/etcdsnapshotfiles.k3s.cattle.io.json |
| node-b를 잃으면 다른 노드에서 못 뜨는 파드 | 19개 | summary.json |
| 전체 CPU 요청 합, node-a 하나의 CPU | 6.17코어, 6.0코어 | summary.json |
| 옮길 파드 29개에 필요한 CPU, node-a 여유 | 2.3코어, 3.45코어 | summary.json |

## 3. emptyDir에 있는 Prometheus·Alertmanager·Grafana 데이터

**상황.** Prometheus의 30.8일치 지표 21.3GiB가 emptyDir에 있어요. Alertmanager의 사일런스와 알림 기록, Grafana 내부 DB도 마찬가지예요. 컨테이너가 재시작될 때는 남아요. 하지만 차트 값이 바뀌어 파드가 새로 만들어지거나, 노드를 비우거나, 파드가 퇴거되면 0부터 다시 쌓여요.

Prometheus 파드는 2025-11-30부터 같은 파드라 아직 잃은 적은 없어요.

- 영향 있음:
  - Prometheus: 데이터 볼륨이 emptyDir이고 PVC가 없어요. 보존은 30d, 크기 상한은 0B예요.
  - Alertmanager: 데이터 볼륨이 emptyDir이고 레플리카는 1개예요.
  - Grafana: storage 볼륨이 emptyDir이고 레플리카는 1개예요.
- 확인했고 멀쩡: Prometheus 컴팩션 실패와 WAL 손상은 0번이에요. 활성 사일런스도 0개라 지금 잃을 사일런스는 없어요.
- 다른 이유로 바뀜: 없음
- 안 봄: manifests 저장소의 kube-prometheus-stack-values.yaml 내용은 안 읽었어요. Grafana에 UI로 만든 사용자나 대시보드가 있는지도 몰라요.

**이유.** kube-prometheus-stack 차트에 저장소 설정을 안 넣으면 Prometheus Operator가 emptyDir를 써요. 확인됨.

**권하는 조치.**

① Prometheus와 Alertmanager에 저장소 설정이 없는지 확인하세요.

```
kubectl -n monitoring get prometheus,alertmanager -o custom-columns=NAME:.metadata.name,STORAGE:.spec.storage
```

아무것도 바뀌지 않아요.

확인: STORAGE 칸이 `<none>`이면 emptyDir를 쓰고 있어요. ②로 가세요.

② 커밋하기 전에 두 가지를 먼저 보세요. 첫째, values 파일에 다른 저장소 설정이 이미 있는지예요. 둘째, Grafana에 UI로 만든 대시보드나 사용자가 있는지예요.

③의 키 이름을 차트가 그대로 받는지는 values 파일을 안 열어 봐서 검증하지 않았어요.

UI로 만든 건 ③에서 사라져요. 남기려면 미리 내보내 두세요.

확인: 겹치는 설정이 없고, Grafana에서 잃어도 되는지 판단이 섰으면 ③으로 가세요.

③ ①에서 저장소 설정이 없었다면, 지난 30일 지표를 잃어도 되는 시간을 고르세요. 그때 manifests 저장소의 monitoring/kube-prometheus-stack-values.yaml에 PVC 설정을 더하고 커밋하세요.

```yaml
prometheus:
  prometheusSpec:
    retentionSize: 32GB
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: local-path
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 40Gi
alertmanager:
  alertmanagerSpec:
    storage:
      volumeClaimTemplate:
        spec:
          storageClassName: local-path
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 1Gi
grafana:
  persistence:
    enabled: true
    storageClassName: local-path
    size: 2Gi
```

Argo CD 앱 monitoring이 차트 79.5.0에 새 값을 적용해요. Prometheus Operator가 Prometheus와 Alertmanager StatefulSet을 다시 만들어요. 파드는 PVC를 달고 node-b에 새로 떠요. Grafana도 PVC를 달고 다시 떠요.

지금 있는 21.3GiB, 30.8일치 지표는 파드가 바뀌는 순간 지워지고 되살릴 수 없어요. 교체하는 동안 Prometheus와 Alertmanager가 멈춰서 알림 평가와 발송이 끊겨요.

Grafana는 UI로 만든 것만 사라져요. 사이드카가 읽는 대시보드와 데이터소스는 다시 들어와요.

Grafana가 RollingUpdate면 새 파드와 옛 파드가 같은 RWO PVC를 원해요. 둘 다 node-b에 뜨면 같이 붙을 수 있다고 보지만, 검증하지 않았어요.

local-path는 요청 크기를 강제하지 않아요. 그래서 실제 상한은 retentionSize 32GB예요.

node-b 디스크는 지금 50%를 쓰고 있어요. emptyDir도 같은 디스크라 늘어나는 양은 거의 없어요. 데이터가 여전히 node-b에만 있어서, node-b를 잃는 경우는 이걸로 못 막아요. 그건 2번 문제예요.

확인: `kubectl -n monitoring get pvc`에 prometheus, alertmanager, grafana PVC가 Bound로 보여요. `kubectl -n monitoring get sts prometheus-kube-prometheus-stack-prometheus -o jsonpath='{.spec.volumeClaimTemplates[*].metadata.name}'` 결과가 비어 있지 않으면 끝이에요.

**되돌리기.** 그 커밋을 git revert 하면 emptyDir로 돌아가요. 그사이 PVC에 쌓인 지표는 버려지고, reclaimPolicy가 Delete라 PVC를 지우면 데이터도 지워져요. ③에서 지워진 지난 30일 지표는 되돌릴 수 없어요.

**왜 이런 일이 생기나.**

- 원리: emptyDir는 컨테이너가 죽어도 남지만, 파드가 노드에서 지워지면 같이 지워져요. 그래서 파드가 다시 만들어지면 지표, 사일런스, 대시보드가 0부터 시작해요. kube-prometheus-stack은 storageSpec을 안 주면 이렇게 동작해요.
- 읽을 것: Prometheus Operator 문서 Storage, Kubernetes 문서 Volumes의 emptyDir

**근거.**

| 항목 | 값 | 출처 |
|---|---|---|
| Prometheus 데이터 볼륨 | emptyDir, volumeClaimTemplates 없음 | objects/statefulsets.json |
| TSDB 크기 | 22888066609 bytes, 21.3GiB | summary.json |
| 가장 오래된 샘플 | 30.8일 | summary.json |
| node-b 루트 파일시스템 사용률 | 50% | metrics/disk_usage_ratio.json |

## 지난 daily 점검 이후

2026-10-27T15-58-38 daily 점검 (2026-10-27 15:58 KST). 그 점검에는 리포트가 없어서 지난번에 권한 조치와는 비교하지 못했어요.

지난 리포트가 시킨 일: 없음

**새로 생긴 것.**

- node-b를 잃었을 때 남는 node-a의 CPU 6.0코어보다 전체 CPU 요청 합이 커졌어요. 지난번 5.99코어, 이번 6.17코어예요. app-f-prod HPA가 app-f-admin과 app-f-api-server를 각각 2개에서 3개로 늘린 몫이 0.13코어예요.
- keda/keda-operator가 10번 재시작했어요. 마지막 종료는 2026-10-28T19:25:01Z이고 지금은 Running이에요.
- cert-manager 로그에 ACME challenge 실패가 10번 있었어요(2026-11-05 02:31~03:35 UTC). 지금 Order 122개는 전부 valid이고 인증서 31개는 전부 Ready예요.
- logging/elasticsearch-0의 CPUThrottlingHigh 알림이 3.1일째 울리고 있어요. severity가 info라 null 수신자로 가요.
- CoreDNS 업스트림 헬스 체크 실패가 1시간에 1번 있었어요. SERVFAIL은 0이에요.

**사라진 것.**

- CPU 스로틀링 경고가 3개 사라졌어요: app-d-prod/app-d-postgres, app-f-prod/app-f-api-server, app-i-prod/app-i-web.
- 메모리 limit 근접 경고가 2개 사라졌어요: app-a-prod/app-a-umami, app-a-prod/app-a-postgres.
- arc-systems/arc-actions-runner-controller 재시작 경고가 사라졌어요. 재시작 수는 61에서 70이 됐지만 지금 Running이에요.
- app-f-prod/app-f-app-w HPA 흔들림과 argocd/argocd-repo-server 준비 안 됨 경고가 사라졌어요.
- apiserver watch 수 과다 경고가 사라졌어요.

**클러스터가 아니라 점검 기준이 바뀌어서 달라진 것.**

- ingress-nginx 지원 종료를 보는 체크가 새로 생겼어요. ingress-nginx 1.14.0은 2026-03-24에 저장소가 보관 처리됐다고 나와요. 클러스터가 바뀐 게 아니에요.
- node-b를 잃었을 때 자리가 모자라는지 보는 체크의 기본 심각도가 high에서 critical로 바뀌었어요. 실패로 바뀐 것 자체는 CPU 요청이 늘어난 클러스터 변화예요.
- MetalLB speaker 오류가 다른 로그 시그니처 이름으로 잡혀요. 지난번 speaker-error 496번, 이번 speaker-peer-unreachable 482번이고 둘 다 memberlist 연결 실패예요. 로그 시그니처 버전이 1.0.15에서 1.1.0으로 바뀌었어요.
- grafana db-locked, grafana provisioning-error, keda scaler-error 로그 경고가 사라졌어요. 지난번 근거 줄이 INFO 수준 로그였어서, 시그니처가 바뀌어 안 잡히는 것으로 보여요.

**지난번에는 돌지 않은 점검 항목이라 클러스터가 아니라 점검에 새로 보인 것.**

- `traffic.ingress-nginx-retired.cluster` (warn/medium)

## 오늘은 안 하지만 심각한 것

- 쿠버네티스 v1.33.5+k3s1은 upstream 지원이 2026-06-28에 끝났어요. 업그레이드는 계획이 필요해서 오늘 할 일에서 뺐어요.
- SLO가 없어요. 알림 규칙 161개 중 사용자 증상을 보는 규칙은 0개이고, OOMKill을 알리는 규칙도 없어요. 알림 설계는 하루에 끝낼 일이 아니라 뒤로 미뤘어요.
- app-d-prod/app-d, app-f-prod/app-f-admin, app-f-prod/app-f-api-server, app-f-prod/app-f-app-x-client는 레플리카가 전부 node-a에 있어요. 앱 Deployment 대부분은 role NotIn 조건 때문에 node-a에만 뜰 수 있어요. ingress-nginx 컨트롤러 2개는 둘 다 node-b에 있어요.
- kube-system CoreDNS는 레플리카 1개이고, PDB 없이 node-b에만 있어요.
- app-e-api/app-e-minio의 7일 메모리 p95가 limit 512Mi의 98%예요. 7일 동안 OOM 기록은 없어요.
- 평문 자격 증명 후보가 있어요. app-a-prod/app-v-scripts와 app-d-prod/app-d-app-v-scripts ConfigMap의 파이썬 스크립트에 TOKEN, OPENAI_API_KEY 같은 이름이 있어요. 값은 수집하지 않아서 실제 값인지 환경 변수 이름인지는 몰라요. default/app-y-backend-config에는 JWT_SECRET 같은 키가 그대로 있어요.
- logging의 elasticsearch, kibana, es-index-retention은 비밀번호를 secretKeyRef가 아니라 env 리터럴 값으로 받아요.
- app-i-prod 쿼터의 PVC 개수가 2/2로 꽉 차서 새 PVC는 거부돼요. app-a-prod, app-b-prod, app-i-prod는 쿼터는 있는데 LimitRange가 없어요.
- prune이 켜진 Argo CD 앱이 Namespace나 CRD를 리소스로 관리해요. 매니페스트에서 빠지면 네임스페이스째 지워질 수 있어요.
- 모니터링·로깅·DB 컨테이너 4개가 수집 순간에 CPU 스로틀링을 받았어요. prometheus 0.56, app-e-postgres 0.46, elasticsearch 0.43, fluent-bit 0.29예요. 24시간 값은 없어요. fluent-bit 메모리는 limit의 84%예요.
- app-c-prod/app-c-coturn은 hostNetwork를 쓰고 root 실행을 막지 않아요. 1번을 고친 뒤에 보면 돼요.
- node-a와 node-b 모두에서 GitHub Actions 러너가 prod 파드와 같은 노드에서 돌아요.
- node-a 루트 파일시스템 사용률이 77%예요.
- cert-manager controller와 cainjector가 각각 12번, 14번 재시작했어요. 마지막 종료는 2026-10-28T19:25:01Z로 keda-operator와 같은 시각이에요. 지금은 Running이에요.

## 이번에 못 본 것

- Loki가 클러스터에 없어서 Loki 로그 검색은 못 했어요. 로그는 파드 로그로만 봤어요. Loki가 다른 곳에 있으면 점검 설정의 loki_url에 넣으세요. 없으면 `/kubegap setup`에서 '설치 안 함'으로 답하면 돼요.
- Grafana 데이터소스와 대시보드 목록은 토큰이 없어서 못 읽었어요. Grafana에서 Viewer 서비스 계정 토큰을 만들어 점검 설정의 grafana_api_token에 넣으면 돼요.
- daily 점검이라 노드 OS, k3s 저널, kubelet 설정, krr, polaris, pluto, kubent, helm 목록은 안 모았어요. 이 때문에 판단하지 못한 항목이 55개예요. `/kubegap full`을 돌리면 돼요.
- ingress-nginx 메트릭이 없어서 사이트별 5xx와 지연을 못 봤어요. app-c-coturn 장애가 사용자에게 어떻게 보였는지도 몰라요. ingress-nginx 컨트롤러의 metrics를 켜고 ServiceMonitor를 붙이면 돼요.
- node-b 디스크에 있는 덤프 파일의 크기와 복원 가능 여부는 못 봤어요. 노드 밖으로 덤프를 옮기는 다른 경로가 있는지도 못 봤어요. 2번의 ① 명령을 돌리고, node-b의 사용자 crontab과 systemd 타이머를 확인하면 돼요.
- manifests 저장소 acme/acme-k8s-manifests가 공개 저장소인지 확인하지 않았어요. 공개라면 app-c-coturn 인자의 사용자명과 같은 비밀번호가 밖에 노출된 거예요. GitHub에서 저장소 공개 범위를 확인하면 돼요.

## 숫자

| 심각도 | fail | warn | 지난 daily 점검 대비 |
|---|---|---|---|
| critical | 3 | 1 | fail +1, warn 0 |
| high | 20 | 66 | fail -6, warn +1 |
| medium | 59 | 104 | fail +2, warn -4 |
| low | 9 | 97 | fail 0, warn +1 |

문제별 체크:

- 문제 1: `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn`, `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn`, `traffic.pod-not-ready.app-c-prod/app-c-coturn`, `hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn`, `events.tracked-warning-reasons.BackOff`
- 문제 2: `resilience.no-backup.cluster`, `resilience.n-plus-one.cluster`, `resilience.backup-same-node.app-d-prod/app-d-postgres-backup`, `resilience.backup-same-node.app-d-prod/app-d-postgres-vn-backup`, `resilience.backup-same-node.app-f-prod/app-f-mysql-backup`, `resilience.backup-same-node.app-g-prod/app-g-postgres-backup`, `resilience.backup-same-node.app-e-api/app-e-postgres-backup`, `resilience.backup-same-node.app-a-prod/app-a-postgres-backup`, `resilience.backup-same-node.app-d-prod/app-d-postgres-mx-backup`
- 문제 3: `observability.stack-storage-emptydir.monitoring/prometheus-kube-prometheus-stack-prometheus`, `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager`, `observability.stack-storage-emptydir.monitoring/kube-prometheus-stack-grafana`, `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus`

자세한 내용과 모든 표: [`report-details.md`](report-details.md) · kubegap 0.1.2, rubric 0.1.80 · 수집 자료 `~/.kubegap/snapshots/my-cluster/2026-11-05T17-00-00`
