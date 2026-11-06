# default — daily audit, 2026-11-05 17:01

Urgent now: yes. app-c-prod's TURN server app-c-coturn has failed to start for at least 12 days because of a start option error.

Today's problems: ① app-c-coturn down on a removed option ② DBs and their backups on one disk ③ Monitoring data held in emptyDir

Coming up: app-g-prod/app-g-prod-tls auto-renews on 2026-11-06 and expires on 2026-12-06, the first certificate in the cluster to expire, which matters after today's 10 ACME challenge failures. Daily jobs run at 03:00 UTC (containerd-cleanup-node-a and containerd-cleanup-node-b), at 04:00 and 04:30 UTC (registry-gc and registry-tag-cleanup) and at 04:20 UTC (es-index-retention).

Since the last run:

- Earlier work: the 2026-10-27 daily run had no report, so there was no earlier work to check.
- Appeared: total CPU requests went from 5.99 to 6.17 cores, above the 6.0 cores node-a has alone. keda-operator restarted 10 times and is Running now. There were 10 ACME challenge failures, and all 122 Orders are valid. elasticsearch-0 CPUThrottlingHigh has fired for 3.1 days. There was 1 CoreDNS upstream health check failure an hour, with 0 SERVFAIL.
- Went away: 3 CPU throttling warnings, 2 memory-near-limit warnings, and 4 other warnings:
  - arc-actions-runner-controller restarts
  - app-f-app-w HPA flapping
  - argocd-repo-server not ready
  - apiserver watch count
- Check changes: the node-b-loss capacity check moved from high to critical severity, a new ingress-nginx end-of-support check was added, and the MetalLB speaker log signature was renamed. The grafana and keda log warnings went away because the log signatures changed, not because the cluster changed.

## The cluster at a glance

| What | Value |
|---|---|
| Nodes | 2 of 2 Ready |
| Pods | 96 running, 0 pending, 4 failed |
| Namespaces | 26, 7 production |
| Components | 23: actions-runner-controller, alertmanager, argocd, cert-manager, coredns, elasticsearch-opensearch, external-secrets, flannel, fluent-bit, fluent-bit-events, grafana, ingress-nginx, k3s, keda, kube-proxy, kube-state-metrics, local-path-provisioner, metallb, metrics-server, node-exporter, prometheus, prometheus-operator, reloader |
| Metrics and log stores | prometheus 3.7.3 / none |
| Kubernetes | v1.33.5+k3s1 (k3s) |

## Coming up

| When | What | Source |
|---|---|---|
| 2026-11-06 | app-g-prod/app-g-prod-tls의 자동 갱신 예정 시각이에요. 만료는 2026-12-06이에요. 클러스터에서 가장 먼저 만료되는 인증서예요. | summary.json |
| 이미 지남 (2026-06-28) | 쿠버네티스 v1.33 upstream 지원이 끝났어요. 보안 패치가 더 나오지 않아요. | findings-draft.json |
| 매일 03:00 UTC | kube-system/containerd-cleanup-node-a, containerd-cleanup-node-b가 돌아요. 이름으로 보면 노드의 containerd 정리 작업이에요. 무엇을 지우는지는 안 읽었어요. | summary.json |
| 매일 04:00 UTC, 04:30 UTC | registry/registry-gc와 registry/registry-tag-cleanup이 node-b의 레지스트리에서 이미지를 정리해요. | summary.json |
| 매일 04:20 UTC | logging/es-index-retention이 오래된 Elasticsearch 인덱스를 정리해요. | summary.json |
| 지금 | app-i-prod 쿼터의 PVC 개수가 2/2로 꽉 찼어요. | summary.json |

## 1. app-c-coturn down on a removed option

**What is happening.** app-c-coturn exits with code 255 right after it starts, and it is in CrashLoopBackOff. The first line of its last log is `turnserver: unrecognized option '--no-dtls'`. It had 7418 restarts at the 2026-10-24 run, so it has been down for at least 12 days. It was Ready for 0 of the last 1440 minutes. KubePodCrashLooping fired within the last 15 days, and its default receiver is discord.

- Affected: app-c-prod/app-c-coturn.
  - It is in CrashLoopBackOff and not ready.
  - It has 10710 restarts since the pod was created on 2026-03-20, and 1963 in the last 7 days.
  - The Deployment has been Available=False with MinimumReplicasUnavailable since 2026-11-05T06:50:54Z.
- Checked and healthy:
  - app-c-signaling and app-c-web are Running and Ready, with 5 restarts each.
  - app-c-postgres-0 is Running and Ready on node-b.
- Changed for another reason: none
- Not checked:
  - How app-c-web and app-c-signaling use the TURN address.
  - Whether user calls or connections actually fail.
  - Whether port 3478 is reachable from the internet.

**Why.** The coturn image that is pulled now rejects `--no-dtls` as an unknown option. Confirmed.

The help text of that image has no `--no-dtls`. It has only `--dtls`, and DTLS is off by default. `--no-cli` is also missing, and the CLI is off by default.

The Deployment pulls `coturn/coturn:latest` with imagePullPolicy Always. The args have not changed since 2026-03-20, so a newer latest image broke it. When that image arrived is unknown.

**Suggested fix.**

① First, confirm the cause is the same in the last log.

```
kubectl -n app-c-prod logs deploy/app-c-coturn --previous --tail=5
```

Nothing changes in the cluster.

Check: if the output has `unrecognized option '--no-dtls'`, the cause is the same.

② Do this only if step ① showed the same line and the same commit also makes two security changes. The first change blocks relay to the nodes with `--denied-peer-ip=<ip>-<ip>`. The second replaces `--user=app-c:app-c` with a hard-to-guess credential.

Make the change in the manifests repo, in prod/app-c:

- In the app-c-coturn Deployment, remove `--no-dtls` and `--no-cli`.
- Pin the image to its current digest.
- Switch the strategy to Recreate.
- Deny relay to the pod and service ranges.

Read the new credential from a Secret. Change app-c-web and app-c-signaling to the new credential at the same time.

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
          # args에서 "--no-dtls"와 "--no-cli" 두 줄을 지우고, 아래 두 줄을 더해요
          #   - "--denied-peer-ip=<ip>-<ip>"
          #   - "--denied-peer-ip=<ip>-<ip>"
          # "--user=app-c:app-c"는 Secret에서 읽는 새 자격 증명으로 바꿔요
```

The Argo CD app app-c applies the commit. It has auto sync, prune and selfHeal turned on.

Recreate removes the dead pod first and starts a new one on node-a. The new pod listens on 3478 UDP/TCP through hostNetwork and relays on ports 49152–49252.

There is one replica, so TURN is gone during the swap. No pod is Ready now, so nothing more stops.

If you change it by hand with kubectl, selfHeal puts the Git state back.

Once it is up, it listens on 3478 on every node-a interface. relay-ip is the node's LAN address, <ip>, so it relays to any LAN address that is not denied.

This step blocks the two nodes, which covers kubelet 10250, the node-b API on 6443 and the NodePorts. The rest of <ip>/24 stays open.

The name and the password in app-c:app-c are the same. If you leave it as is, anyone can use the relay.

Whether 3478 is reachable from outside is not checked. If it is reachable, do not bring the server up without the two changes above.

coturn stops reading options at the first error. You only know whether it starts after you apply the change.

Check: `kubectl -n app-c-prod get pods -l app=app-c-coturn` shows 1/1 Running, and RESTARTS stops going up. `kubectl -n app-c-prod logs deploy/app-c-coturn --tail=20` has no unrecognized option line.

**Rollback.** Run git revert on that commit. Argo CD returns app-c-coturn to the old manifest, which keeps crashing. It holds no data, so nothing is lost.

**Why this happens.**

- Principle: an image with the `:latest` tag can start as a different binary on a restart or a node change. Nothing records which version ran, so you cannot go back to it. Pinning a version or digest with imagePullPolicy IfNotPresent is the safe default.
- Read: Kubernetes documentation, Images — Image pull policy. Also the coturn turnserver help text.

**Evidence.**

| What | Value | Source |
|---|---|---|
| Restarts since the pod was created on 2026-03-20 | 10710 | summary.json |
| Restarts, 7 days | 1963 | metrics/restarts_7d.json |
| Minutes not Ready, 24 hours | 1440 | summary.json |
| BackOff events, 2026-10-28 to 2026-11-05 | 48970 | summary.json |
| Last log line | `turnserver: unrecognized option '--no-dtls'` | extra/coturn-previous-head.txt |
| Image and pull policy | coturn/coturn:latest, Always | objects/deployments.json |

## 2. DBs and their backups on one disk

**What is happening.** nodeSelector and local-path volumes pin the prod DBs below to the node-b disk. There are 7 DB backup CronJobs, and 5 of them write their dumps to node-b too. All 5 k3s etcd snapshots are also local files on node-b. No backup shows any sign of a copy off the node. If the node-b disk fails, the data, the dumps and the cluster state go together. Then 19 pods tied to node-b cannot start on node-a. Nothing is broken now.

- Affected:
  - app-d-prod/app-d-postgres and app-d-postgres-vn use nodeSelector storage=node-b. Their backups write to a PVC on node-b.
  - app-f-prod/app-f-mysql is pinned to node-b. app-f-mysql-backup writes to the PVC mysql-backup-app-f-mysql-0 on node-b.
  - app-g-prod/app-g-postgres is on storage=node-b. Its backup writes to a PVC on node-b.
  - app-e-api/app-e-postgres is on storage=node-b. Its backup writes to a PVC on node-b.
  - app-e-api/app-e-minio has its data PVC on node-b. No CronJob backs it up.
  - app-a-prod/app-a-postgres and app-d-prod/app-d-postgres-mx are on node-b, and their dumps go to node-a. They have no copy off the node.
  - app-c-prod/app-c-postgres is pinned to node-b. app-c-prod has no backup CronJob.
  - app-i-prod/app-i-postgres and app-h/app-h-postgres are only on node-a's local disk. They have no backup CronJob.
  - default/data-app-z-db-0 is a Bound PVC on node-b. No workload uses it, and it has no backup.
- Checked and healthy: all 7 backup CronJobs last succeeded on 2026-11-05 between 02:50 and 03:50 UTC. No Job failed.
- Changed for another reason:
  - The HPA scaled app-f-prod/app-f-admin and app-f-api-server to 3 replicas, at 2026-11-05T03:59:32Z and 04:17:35Z. This explains 0.13 of the 0.18-core rise to 6.17 cores, and the other 0.05 cores were not traced.
  - The 29 pods that can move still fit on node-a: they need 2.3 cores, and node-a has 3.45 free.
  - The 19 pods tied to node-b cannot move because of nodeSelector and local-path, not CPU.
- Not checked:
  - Dump sizes, and whether the dumps restore.
  - node-b disk health (SMART).
  - A user crontab on node-b, or another machine that pulls the dumps.
  - The data backups of registry/registry and app-f-prod/app-f-qdrant.
  - Whether app-i-postgres and app-h-postgres are backed up from outside the cluster.

**Why.** The backup CronJobs write dumps only to local-path PVCs on cluster nodes and have no step that sends them off the node. Likely.

Evidence: none of the 7 has s3, rclone or restic in its command, args or env. A script inside an image could still be uploading. The etcd snapshots point to file:// on node-b.

**Suggested fix.**

① Find which directory on which node holds each backup PVC.

```
kubectl get pv -o custom-columns=PV:.metadata.name,NS:.spec.claimRef.namespace,CLAIM:.spec.claimRef.name,SC:.spec.storageClassName,PATH:.spec.hostPath.path,LOCAL:.spec.local.path,NODE:.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0] | grep -i backup
```

Nothing changes in the cluster.

Check: the paths and nodes of the 7 backup PVCs appear. This does not show whether a copy already exists outside the cluster.

② If step ① showed the paths, copy today's dumps and etcd snapshots once to a PC outside node-b. Do it outside 02:50–04:00 UTC, when the backups and containerd-cleanup run.

```
mkdir -p ~/node-b-backup/$(date +%F) && ssh node-b@<node-b 주소> 'sudo tar -C /var/lib/rancher/k3s/server/db/snapshots -czf - .' > ~/node-b-backup/$(date +%F)/etcd-snapshots.tgz
```

This reads the node-b disk and writes an archive on this PC. No cluster object changes.

For each dump PVC, ssh to the node that step ① showed and pull it with `sudo tar -C <경로> -czf - .`:

- Paths on node-b, <ip>: use node-b.
- Paths on node-a, <ip>: use node-a. These are app-d-postgres-mx-backup-pvc and app-a-postgres-backup-pvc.

The etcd snapshots hold every Secret in the cluster, and the dumps hold customer data. Keep the files on an encrypted disk and never in a shared folder.

The copy adds disk reads on the node. The dump size is unknown, so free space on this PC is unknown too.

If sudo asks for a password over ssh, the command stops. The `node-b@` user name is not confirmed.

The node keeps only the latest 5 snapshots, because containerd-cleanup-node-b deletes older ones.

Check: `tar -tzf ~/node-b-backup/$(date +%F)/etcd-snapshots.tgz | head` shows snapshot file names, and every dump archive is larger than 0.

③ Next, plan a lasting off-node copy. Make the changes in the manifests repo and the k3s config file:

1. Add a step to each of the 7 backup CronJobs that sends the dump to a NAS or object storage, with rclone or restic.
2. Create backup CronJobs for app-c-prod/app-c-postgres, app-i-postgres and app-h-postgres.
3. Change the k3s config so etcd snapshots also go to S3-compatible storage.
4. Once a month, restore one dump somewhere else.

After this, every backup Job leaves a copy off the node each day.

The destination credentials have to be a Secret. Longer dumps can hit activeDeadlineSeconds, which is 1800 seconds for app-a.

The k3s config change needs a k3s server restart. node-b is the only control-plane and etcd node, so the API server stops during the restart.

While it is stopped, deploys, scheduling, Argo CD sync and the HPA all stop.

Check: the next day, the destination has dated dumps, and there is a record of a restore drill.

**Rollback.** Step ② does not change the cluster. To undo it, delete the archives. To undo step ③, revert its Git commits.

**Why this happens.**

- Principle: a backup exists so you can recover after a node disk dies. If the dump PVC is local-path on the same node as the DB, one failed disk takes both. A dump that has never been restored may not work.
- Read: k3s documentation, etcd-snapshot, S3 settings. Also the rclone documentation, rclone copy.

**Evidence.**

| What | Value | Source |
|---|---|---|
| Backup CronJobs / with a sign of an off-node copy | 7 / 0 | summary.json |
| Dumps on the same node as their DB | 5 | summary.json |
| etcd snapshots, all local on node-b | 5 | objects/etcdsnapshotfiles.k3s.cattle.io.json |
| Pods that cannot start elsewhere if node-b is lost | 19 | summary.json |
| Total CPU requests vs node-a alone | 6.17 vs 6.0 cores | summary.json |
| node-b root filesystem use | 50% | metrics/disk_usage_ratio.json |

## 3. Monitoring data held in emptyDir

**What is happening.** All of these sit in emptyDir:

- Prometheus's 21.3GiB of metrics, which covers 30.8 days.
- Alertmanager's silences and notification log.
- Grafana's internal DB.

They survive a container restart, but they are deleted when the pod leaves the node. That happens when a chart value change recreates the pod, when you drain the node, or when the pod is evicted. The Prometheus pod has been the same pod since 2025-11-30, so nothing has been lost yet.

- Affected:
  - Prometheus: its volume prometheus-kube-prometheus-stack-prometheus-db is emptyDir with no PVC. TSDB is 21.3GiB, retention is 30d and the size cap is 0B.
  - Alertmanager: its volume alertmanager-kube-prometheus-stack-alertmanager-db is emptyDir. It has 1 replica.
  - Grafana: its volume storage is emptyDir. It has 1 replica.
- Checked and healthy: Prometheus has 0 compaction failures and 0 WAL corruptions. Alertmanager has 0 active silences, so there are no silences to lose now.
- Changed for another reason: none
- Not checked:
  - The contents of monitoring/kube-prometheus-stack-values.yaml in the manifests repo.
  - Whether Grafana has users or dashboards made in its UI.

**Why.** kube-prometheus-stack without a storage setting makes Prometheus Operator use emptyDir. Confirmed. The Prometheus and Alertmanager StatefulSets here have no volumeClaimTemplates.

**Suggested fix.**

① Confirm that Prometheus and Alertmanager have no storage setting.

```
kubectl -n monitoring get prometheus,alertmanager -o custom-columns=NAME:.metadata.name,STORAGE:.spec.storage
```

Nothing changes in the cluster.

Check: if STORAGE shows <none>, they use emptyDir.

② If step ① showed no storage, add PVC settings to monitoring/kube-prometheus-stack-values.yaml in the manifests repo and commit. Pick a time when losing the last 30 days of metrics is acceptable.

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

The Argo CD app monitoring applies the new values to chart 79.5.0. It has auto sync, prune and selfHeal turned on.

Prometheus Operator recreates the Prometheus and Alertmanager StatefulSets. Their pods come back on node-b with PVCs, and Grafana does the same.

The current 21.3GiB of metrics, 30.8 days, are deleted the moment the pods are replaced. They cannot be brought back.

During the swap, Prometheus and Alertmanager stop, so alert evaluation and sending stop.

Anything made in the Grafana UI is lost. The dashboards and datasources that the sidecar reads come back.

If Grafana uses RollingUpdate, the new and old pods want the same RWO PVC. If both are on node-b, both may attach to it. This is not verified.

local-path does not enforce the requested size, so retentionSize is the real cap.

node-b's disk is 50% used. The emptyDir data already sits on that disk, so usage grows very little.

The data still lives only on node-b, so this does not cover losing node-b, which is problem 2.

The values file was not opened, so whether the chart takes these key names is not verified.

Check: `kubectl -n monitoring get pvc` shows the prometheus, alertmanager and grafana PVCs as Bound. `kubectl -n monitoring get sts prometheus-kube-prometheus-stack-prometheus -o jsonpath='{.spec.volumeClaimTemplates[*].metadata.name}'` is not empty.

**Rollback.** Run git revert on the commit to go back to emptyDir. The metrics stored in the PVCs are dropped. reclaimPolicy is Delete, so deleting a PVC deletes its data. The 30 days removed in step ② cannot be restored.

**Why this happens.**

- Principle: when Prometheus, Alertmanager and Grafana keep data in emptyDir, a pod that moves or is recreated starts from zero. That covers stored metrics, alert silences and dashboards. kube-prometheus-stack behaves this way when storageSpec is not set.
- Read: Prometheus Operator documentation, Storage. Also the Kubernetes documentation, Volumes — emptyDir.

**Evidence.**

| What | Value | Source |
|---|---|---|
| Prometheus TSDB size | 22888066609 bytes | summary.json |
| Oldest sample | 30.8 days | summary.json |
| Prometheus data volume | emptyDir | objects/statefulsets.json |
| node-b root filesystem use | 50% | metrics/disk_usage_ratio.json |

## Since the previous daily run

2026-10-27T15-58-38 daily 점검 (2026-10-27 15:58 KST). 그 점검에는 리포트가 없어서 지난번에 권한 조치와는 비교하지 못했어요.

Work the previous report asked for: none

**Appeared.**

- node-b를 잃었을 때 남는 node-a의 CPU 6.0코어보다 전체 CPU 요청 합이 커졌어요. 지난번 5.99코어, 이번 6.17코어예요. app-f-prod HPA가 app-f-admin과 app-f-api-server를 각각 2개에서 3개로 늘린 몫이 0.13코어예요.
- keda/keda-operator가 10번 재시작했어요. 마지막 종료는 2026-10-28T19:25:01Z이고 지금은 Running이에요.
- cert-manager 로그에 ACME challenge 실패가 10번 있었어요(2026-11-05 02:31~03:35 UTC). 지금 Order 122개는 전부 valid이고 인증서 31개는 전부 Ready예요.
- logging/elasticsearch-0의 CPUThrottlingHigh 알림이 3.1일째 울리고 있어요. severity가 info라 null 수신자로 가요.
- CoreDNS 업스트림 헬스 체크 실패가 1시간에 1번 있었어요. SERVFAIL은 0이에요.

**Went away.**

- CPU 스로틀링 경고가 3개 사라졌어요: app-d-prod/app-d-postgres, app-f-prod/app-f-api-server, app-i-prod/app-i-web.
- 메모리 limit 근접 경고가 2개 사라졌어요: app-a-prod/app-a-umami, app-a-prod/app-a-postgres.
- arc-systems/arc-actions-runner-controller 재시작 경고가 사라졌어요. 재시작 수는 61에서 70이 됐지만 지금 Running이에요.
- app-f-prod/app-f-app-w HPA 흔들림과 argocd/argocd-repo-server 준비 안 됨 경고가 사라졌어요.
- apiserver watch 수 과다 경고가 사라졌어요.

**Changed because the checks changed, not the cluster.**

- ingress-nginx 지원 종료를 보는 체크가 새로 생겼어요. ingress-nginx 1.14.0은 2026-03-24에 저장소가 보관 처리됐다고 나와요. 클러스터가 바뀐 게 아니에요.
- node-b를 잃었을 때 자리가 모자라는지 보는 체크의 기본 심각도가 high에서 critical로 바뀌었어요. 실패로 바뀐 것 자체는 CPU 요청이 늘어난 클러스터 변화예요.
- MetalLB speaker 오류가 다른 로그 시그니처 이름으로 잡혀요. 지난번 speaker-error 496번, 이번 speaker-peer-unreachable 482번이고 둘 다 memberlist 연결 실패예요. 로그 시그니처 버전이 1.0.15에서 1.1.0으로 바뀌었어요.
- grafana db-locked, grafana provisioning-error, keda scaler-error 로그 경고가 사라졌어요. 지난번 근거 줄이 INFO 수준 로그였어서, 시그니처가 바뀌어 안 잡히는 것으로 보여요.

**Checks that did not run last time, so these findings are new to the audit, not to the cluster.**

- `traffic.ingress-nginx-retired.cluster` (warn/medium)

## Serious, not today

- Upstream support for Kubernetes v1.33.5+k3s1 ended on 2026-06-28. An upgrade needs a plan, so it is not on today's list.
- There are no SLOs, and 0 of 161 alert rules watch user symptoms. No rule alerts on OOMKill. Alert design is not a one-day job, so it waits.
- app-d-prod/app-d, app-f-prod/app-f-admin, app-f-prod/app-f-api-server and app-f-prod/app-f-app-x-client have every replica on node-a. A role NotIn rule lets most app Deployments run only on node-a. Both ingress-nginx controllers are on node-b.
- kube-system CoreDNS has 1 replica and no PDB, and it runs only on node-b.
- app-e-api/app-e-minio's 7-day memory p95 is 98% of its 512Mi limit. There was no OOM in 7 days.
- There may be plaintext credentials:
  - Python scripts in the app-a-prod/app-v-scripts and app-d-prod/app-d-app-v-scripts ConfigMaps contain names like TOKEN and OPENAI_API_KEY.
  - Values were not collected, so it is unknown whether these are real values or env var names.
  - default/app-y-backend-config holds keys like JWT_SECRET as they are.
- In logging, elasticsearch, kibana and es-index-retention take passwords as literal env values, not secretKeyRef.
- The app-i-prod quota for PVC count is full at 2/2, so new PVCs are refused. app-a-prod, app-b-prod and app-i-prod have quotas but no LimitRange.
- Some Argo CD apps with prune on manage a Namespace or CRD as a resource. If one drops out of the manifests, the whole namespace can be deleted.
- Four monitoring, logging and DB containers were CPU-throttled at the moment of collection. The values were prometheus 0.56, app-e-postgres 0.46, elasticsearch 0.43 and fluent-bit 0.29. There are no 24-hour values. fluent-bit memory is at 84% of its limit.
- app-c-prod/app-c-coturn uses hostNetwork and does not block running as root. Look at it after problem 1 is fixed.
- On both node-a and node-b, GitHub Actions runners run on the same nodes as prod pods.
- node-a's root filesystem is 77% used.
- cert-manager controller and cainjector restarted 12 and 14 times. Their last exit was at 2026-10-28T19:25:01Z, the same moment as keda-operator. They are Running now.

## What this run could not see

- There is no Loki in the cluster, so the Loki log search did not run, and logs were read only from pods. To see it: if Loki runs elsewhere, set loki_url in the audit config. If it does not exist, answer "not installed" in `/kubegap setup`.
- Grafana datasources and dashboards could not be read without a token. To see them: create a Viewer service account token in Grafana and set it as grafana_api_token.
- Daily mode does not collect the items below, so 55 items were not judged. To see them: run `/kubegap full`.
  - node OS
  - k3s journal
  - kubelet config
  - krr, polaris, pluto, kubent
  - helm list
- There are no ingress-nginx metrics, so 5xx and latency per site are unseen. How the app-c-coturn outage looked to users is unknown too. To see it: turn on the ingress-nginx controller metrics and attach a ServiceMonitor.
- The dump file sizes on the node-b disk, whether they restore, and any other path that moves dumps off the node are unseen. To see them: run the command in step ① of problem 2, then check node-b's user crontab and systemd timers.
- Whether the manifests repo acme/acme-k8s-manifests is public is unknown. To see it: check the repo's visibility on GitHub.

## Numbers

| Severity | fail | warn | vs. previous daily run |
|---|---|---|---|
| critical | 3 | 1 | fail +1, warn 0 |
| high | 20 | 66 | fail -6, warn +1 |
| medium | 59 | 104 | fail +2, warn -4 |
| low | 9 | 97 | fail 0, warn +1 |

Checks behind each problem:

- problem 1: `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn`, `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn`, `traffic.pod-not-ready.app-c-prod/app-c-coturn`, `hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn`, `events.tracked-warning-reasons.BackOff`
- problem 2: `resilience.no-backup.cluster`, `resilience.n-plus-one.cluster`, `resilience.backup-same-node.app-d-prod/app-d-postgres-backup`, `resilience.backup-same-node.app-d-prod/app-d-postgres-vn-backup`, `resilience.backup-same-node.app-f-prod/app-f-mysql-backup`, `resilience.backup-same-node.app-g-prod/app-g-postgres-backup`, `resilience.backup-same-node.app-e-api/app-e-postgres-backup`, `resilience.backup-same-node.app-a-prod/app-a-postgres-backup`, `resilience.backup-same-node.app-d-prod/app-d-postgres-mx-backup`
- problem 3: `observability.stack-storage-emptydir.monitoring/prometheus-kube-prometheus-stack-prometheus`, `observability.stack-storage-emptydir.monitoring/alertmanager-kube-prometheus-stack-alertmanager`, `observability.stack-storage-emptydir.monitoring/kube-prometheus-stack-grafana`, `prometheus.storage-risk.monitoring/statefulset/prometheus-kube-prometheus-stack-prometheus`

Details and every table: [`report-details.md`](report-details.md) · kubegap 0.1.2, rubric 0.1.80 · snapshot `~/.kubegap/snapshots/my-cluster/2026-11-05T17-00-00`
