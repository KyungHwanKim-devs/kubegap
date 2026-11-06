# default — full audit, 2026-11-05 17:25

Urgent now: yes. app-c-coturn, the TURN relay of app-c-prod, has been down for at least 38 days and crash-loops on every start.

Today's problems: ① app-c-coturn crash-looping for 38 days ② No backup copy leaves the nodes ③ Stale alerts, no user-symptom alerts ④ Kubernetes 1.33 past end of life ⑤ Four Postgres DBs open on NodePorts

Since the last run:

- The previous run listed no problems, so there is no earlier work to mark done or not done.
- Appeared: 3.
  - apiserver 503s at 0.004 per second, measured while collection ran.
  - One failed CoreDNS health check of 1.1.1.1 and 8.8.8.8 in the last hour, with no SERVFAIL answers.
  - An info-level CPUThrottlingHigh on logging/elasticsearch-0, firing for 3.1 days.
  - 4 log findings are also new, but only because the log rules changed. The cluster did not cause them.
- Went away: none.

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
| 2026-06-28, already 130 days past | Upstream end of life of Kubernetes 1.33, the version both nodes run | findings-draft.json |
| 2026-11-06 | cert-manager is due to renew app-g-prod-tls, which expires on 2026-12-06 | summary.json |
| 2026-11-07 | cert-manager is due to renew app-e-api-tls, which expires on 2026-12-07 | summary.json |
| every day at 03:00 UTC | containerd-cleanup-node-b prunes unused images and deletes all but the 5 newest etcd snapshots on node-b | objects/cronjobs.json |
| every day at 03:30 UTC | app-d-postgres-backup deletes dumps older than 3 days; the app-f-mysql and app-g dumps do the same, the app-a dumps after 5 days and the app-e dumps after 7 | objects/cronjobs.json |
| every day at 04:20 UTC | es-index-retention deletes Elasticsearch k3s-* indices older than 14 days | objects/cronjobs.json |
| every day at 04:30 UTC | registry-tag-cleanup deletes all but the last 5 commit-hash tags per repository in the in-cluster registry | objects/cronjobs.json |
| now | app-i-prod uses 2 of the 2 PVCs its quota allows; a third PVC is refused | summary.json |

## 1. app-c-coturn crash-looping for 38 days

**What is happening.** The only app-c-coturn pod exits with code 255 right after each start. It has been in CrashLoopBackOff for at least 38 days, and the Deployment has 0 of 1 replicas available. WebRTC clients of app-c.acme.com and example-h.space that need a TURN relay get none.

- Affected: app-c-prod/app-c-coturn, in CrashLoopBackOff with 10,715 restarts. The last exit was code 255 at 2026-11-05 08:24 UTC, and the Deployment shows Available=False.
- Checked and healthy: app-c-signaling and app-c-web are Running and Ready on node-a. app-c-postgres-0 is Running and Ready on node-b.
- Changed for another reason: node-a rebooted around 2026-10-28 22:06 UTC. The BackOff events on record start then.
- Not checked: whether any call actually failed, because there are no TURN, WebRTC or ingress request metrics. Also not checked: which clients need the relay and how many there are.

**Why.** The container runs coturn/coturn:latest with imagePullPolicy Always. The image it now pulls rejects the argument --no-dtls. Confirmed. The previous container log begins with `turnserver: unrecognized option '--no-dtls'`. When the tag moved is not known.

**Suggested fix.**

① See the rejected option for yourself.

```
kubectl -n app-c-prod logs deploy/app-c-coturn --previous | head -3
```

This only reads.

Check: the first line reads `turnserver: unrecognized option '--no-dtls'`. It names only the first option this build rejects, and it does not say why the tag changed.

② If ① shows that line, confirm that the pinned build accepts the peer options.

```
docker run --rm coturn/coturn@sha256:bbefd3e1fdfdc0d58770fe01b581fd8b00d9f3a5580d00acb77cf719a6bc78e3 --help 2>&1 | grep -E 'denied-peer-ip|no-loopback-peers'
```

This only reads.

Check: the output lists --denied-peer-ip. If it does not, do not bring the relay back yet.

③ If ② lists --denied-peer-ip, change the app-c-coturn Deployment in Git, all in one commit. The repository is acme/acme-k8s-manifests, path prod/app-c. Make these changes:

- Delete the lines `- --no-dtls` and `- --no-cli`.
- Pin the image to the digest that runs today, and set imagePullPolicy to IfNotPresent.
- Set the update strategy to Recreate.
- Replace the --user credential with one that is not guessable. Today's value is guessable.
- Add these arguments in range form, because it is unverified whether this build accepts CIDR:
  - `--denied-peer-ip=<ip>-<ip>`
  - `--denied-peer-ip=<ip>-<ip>`
  - `--denied-peer-ip=<ip>-<ip>`
  - `--denied-peer-ip=<ip>-<ip>`
  - `--denied-peer-ip=169.254.0.0-169.254.255.255`

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
        # args: the same list as today without '- --no-dtls' and '- --no-cli'
```

When you push, Argo CD applies the change through the app-c app, which runs with selfHeal. Recreate removes the crashing pod first and then starts one new pod on node-a from the pinned image.

After the change, DTLS and the CLI stay off. Peers in the private, CGNAT and link-local ranges are refused. Clients get the new credential through app-c-web and app-c-signaling.

Risk to availability:

- The relay is already down, so the rollout costs no availability.
- turnserver stops at the first option it rejects, so the log names only --no-dtls.
- The saved usage text shows --cli but no --no-cli, so --no-cli is removed too.
- Whether this build accepts every other argument is seen only when it starts.

Risk in the rollout:

- The pod uses hostNetwork and hostPort 3478, and it is pinned to node-a. A new pod can start only after the old pod frees the port, and Recreate deletes the old pod first.
- The API may reject the change with 'may not be specified when strategy type is Recreate'. If it does, add `rollingUpdate: null` under strategy. That fix is unverified.
- Argo CD selfHeal reverts a by-hand kubectl edit, so make the change in Git.

Risk once it runs:

- coturn relays for anyone who holds the --user credential, and the web client hands it out.
- Without the denied ranges, the relay can reach LAN and node addresses from node-a, <ip>. That includes the Postgres NodePorts 30432-30435 of problem 5 and the kubelet on 10250. This is why the ranges go in the same commit.
- If <public-ip>:3478 is reachable from outside, anyone can use that path. The router's port forwarding was not checked.

Check: after a few minutes, `kubectl -n app-c-prod get pods -l app=app-c-coturn -o wide` shows 1/1 Running on node-a with RESTARTS 0. Then `kubectl -n app-c-prod logs deploy/app-c-coturn | grep -i listener` shows the 3478 listeners.

④ When the pod is Running, confirm that the Deployment is available and the alerts clear.

```
kubectl -n app-c-prod get deploy app-c-coturn; kubectl -n monitoring port-forward svc/kube-prometheus-stack-alertmanager 9093 & sleep 2; curl -s 'http://localhost:9093/api/v2/alerts?filter=namespace="app-c-prod"' | grep -c alertname
```

This only reads.

Check: the Deployment shows 1/1 available. The query returns 0 once KubePodCrashLooping and KubeDeploymentReplicasMismatch resolve.

Only a TURN allocation test from a client outside the LAN shows that relaying works. You can run one on the Trickle ICE page with turn:app-c.acme.com:3478.

⑤ When the relay works again, keep the image from moving. Bump the digest only when you want a new coturn release. Move the --user credential into a Secret, referenced from the args or a config file.

This makes a new Deployment revision through Git, rolled out the same way as ③.

Risk: an option the new image does not accept brings back the same crash loop. Before every bump, read `kubectl -n app-c-prod exec deploy/app-c-coturn -- turnserver --help`.

Check: the pod stays Running with 0 restarts, and turnserver --help lists every option in the args.

**Rollback.** Run git revert on the commit, and Argo CD restores the previous Deployment. That Deployment crash-loops again. Nothing is deleted.

**Why this happens.**

- Principle: an image tagged :latest can come up as a different program on any restart. There is no record of which version ran before, so you cannot roll back to it. Pinning a digest and pulling IfNotPresent keeps a restart from changing the program. Exit code 255 with no Unhealthy events means the program itself fails at start, and the previous container log holds the reason.
- Read: the Kubernetes documentation on Images, for image pull policy and digests. Also the `turnserver --help` output of the pinned version.

**Evidence.**

| What | Value | Source |
|---|---|---|
| Restarts of the coturn container since 2026-03-20 | 10,715 | summary.json |
| BackOff events, 2026-10-28 to 2026-11-05 | 49,085 | summary.json |
| KubePodCrashLooping firing | 38.1 days | findings-draft.json |
| Ready ratio, last 24 hours | 0.0 | findings-draft.json |
| First log line of the crashed container | unrecognized option '--no-dtls' | extra/coturn-previous-head.txt |
| Image and pull policy | coturn/coturn:latest, Always | objects/deployments.json |

## 2. No backup copy leaves the nodes

**What is happening.** Seven dump CronJobs run every night, and every dump lands on a local-path volume on node-a or node-b. Five of them sit on node-b, the same single SSD as the database they copy. The five etcd snapshots are on node-b only. app-c-postgres and app-i-postgres have no dump at all. If node-b's disk fails, the production databases, five of the seven dumps and all etcd snapshots are lost together.

- Affected:
  - app-d-postgres and app-d-postgres-vn: dump volumes on node-b, the same node as the data.
  - app-f-mysql: dumps go to a volume of the app-f-mysql StatefulSet itself, on node-b.
  - app-g-postgres: dump volume on node-b, the same node as the data.
  - app-e-postgres: dump volume on node-b, the same node as the data.
  - app-c-postgres and app-i-postgres: no dump CronJob in their namespaces.
  - etcd: 5 snapshots on node-b's disk, and k3s runs without --etcd-s3.
- Checked and healthy: the Postgres dump CronJobs succeeded on their last run, 2026-11-05 between 02:50 and 03:50 UTC. The app-a-postgres and app-d-postgres-mx dumps go to node-a, away from their databases.
- Changed for another reason: none.
- Not checked:
  - Whether app-f-mysqldump succeeded. The pipe into gzip has no pipefail, so the Job can report success when mysqldump fails.
  - The content of any dump, and whether one has ever been restored.
  - Whether someone copies the node directories elsewhere from outside the cluster.
  - app-d-redis and app-a-redis persistence.
  - app-h-postgres and app-e-minio, which have no dump.

**Why.** No off-node copy is set up. Confirmed. Every dump ends with gzip into a directory on one node, and k3s runs without --etcd-s3.

**Suggested fix.**

① List the dump files and etcd snapshots on both nodes.

```
ssh node-b 'sudo ls -la --time-style=long-iso /var/lib/rancher/k3s/storage/*backup* /var/lib/rancher/k3s/server/db/snapshots'; ssh node-a 'sudo ls -la --time-style=long-iso /var/lib/rancher/k3s/storage/*backup*'
```

This only reads.

Check: each directory has a file dated 2026-11-05 or later, larger than a few kilobytes.

Look at the app-f-mysql sizes in particular. Its Job status does not prove the dump worked.

This does not show that a dump restores. It also misses node-a directories outside /var/lib/rancher/k3s/storage, if the default class there uses another path.

② Today, before any other change in this report, copy the dumps, the etcd snapshots and the k3s server token to a machine outside the cluster.

```
umask 077; mkdir -p ~/k3s-backup/$(date +%F) && ssh node-b "sudo -n sh -c 'cd /var/lib/rancher/k3s && tar -czf - storage/*backup* server/db/snapshots server/token'" > ~/k3s-backup/$(date +%F)/node-b.tgz && ssh node-a "sudo -n sh -c 'cd /var/lib/rancher/k3s && tar -czf - storage/*backup*'" > ~/k3s-backup/$(date +%F)/node-a.tgz
```

This writes two archives to your machine. The cluster is not changed. The nodes only read their disks.

Risk:

- The archive holds database contents and the k3s server token. umask 077 keeps it readable only by you.
- The glob takes only the dump volumes. It leaves out Elasticsearch, the registry and app-e-minio. The app-a dump directory alone is about 5.9 GB.
- Reading adds I/O on node-b, which already logs slow etcd applies. Run it outside 02:50-04:30 UTC, when the dump jobs run.
- The dump CronJobs delete old dumps every day at 03:30 UTC (app-d, app-f-mysql and app-g after 3 days, app-a after 5, app-e after 7), so today's dumps last only that long on the nodes. Every day es-index-retention also deletes Elasticsearch k3s-* indices older than 14 days at 04:20 UTC, and registry-tag-cleanup keeps only the last 5 commit-hash tags per repository at 04:30 UTC.
- Do not use ssh -t. A terminal corrupts the binary stream.

If sudo needs a password, sudo -n fails and the command stops. In that case:

1. Open an interactive ssh session on the node.
2. Write the archive there with `sudo tar -czf /root/<node>.tgz …`.
3. Run `sudo install -m 600 -o $USER`, then copy the archive with scp.
4. Delete the archive on the node.

The token path is the k3s default. It is unverified on this node.

Check: `tar -tzf ~/k3s-backup/<date>/node-b.tgz | head -20` lists dump files and etcd-snapshot-node-b-* files. `gzip -t` on the archive reports no error.

③ This week, make a copy leave the nodes every night:

- Enable k3s etcd snapshots to S3-compatible storage with --etcd-s3.
- Add an rclone or restic step after each dump that sends the file to the same store.
- Add dump CronJobs for app-c-postgres and app-i-postgres.
- Add `set -o pipefail` to app-f-mysql-backup.

These also have no dump or off-node copy and need one: app-h-postgres, app-e-minio, the orphaned volume data-app-z-db-0 in default, and the registry data. The registry data, 32.7 GB on node-b, is also pruned every night by registry-gc and registry-tag-cleanup.

This adds new k3s flags on node-b, which restarts k3s there. It also changes CronJobs in Git and adds new CronJobs in app-c-prod and app-i-prod.

Risk:

- node-b is the only server, so the API is unavailable while k3s restarts.
- Keep the store credentials in a Secret, not in the CronJob env.
- The app-i-prod quota already holds 2 of 2 PVCs, so a dump PVC there is refused. Send that dump straight to the store, or raise the quota.
- That quota also caps cpu and memory, and no LimitRange fills in defaults. The dump Job's container must state requests and limits, or the pod is refused.
- The app-e-api dump volume and the 5.9 GB app-a dump volume on node-a, which has 24.3 GB free, keep growing with retention.

Check: the bucket has a file with tonight's date for each database. `k3s etcd-snapshot ls` on node-b lists s3 locations.

④ When the first off-node copy exists, restore one dump of each engine into a scratch namespace. Write down how long it took. Use `gunzip -c <file> | psql` for Postgres and `gunzip -c <file> | mysql` for app-f-mysql.

This creates a temporary namespace with a throwaway database pod.

Risk: requests already exceed what one node holds. Run it on node-b outside the dump window, and delete it afterwards. Do not point it at a production Service.

Check: row counts of a few tables match production.

**Rollback.** The copy steps change nothing in the cluster. To undo the k3s change, remove the flags and restart k3s. The CronJob changes are Git commits that git revert undoes.

**Why this happens.**

- Principle: a dump on the same disk as its database dies with it. A backup exists to recover even then, so one copy has to leave the node. A dump that was never restored may not work.
- Case: at InfluxData in 2023, a wrong object name in a pull request made Argo CD replace a production instance. That deleted its StatefulSets and PersistentVolumeClaims. They recovered from Retain volumes, Velero and object-store backups in just under six hours. Here, seven Argo CD apps run with automated prune, volumes use reclaimPolicy Delete, and no copy exists outside the two nodes. The same mistake would leave nothing to restore.
- Read: the K3s documentation on etcd-snapshot, for S3 options and restore. Also the PostgreSQL documentation, Backup and Restore: SQL Dump.

**Evidence.**

| What | Value | Source |
|---|---|---|
| Dump CronJobs whose output stays on a node | 7 | summary.json |
| Dump CronJobs on the same node as their database | 5 | summary.json |
| etcd snapshots kept off node-b | no | summary.json |
| Production databases without a dump | 2 | summary.json |
| app-a dump volume against its 5,120 MB claim | 5,862 MB | summary.json |

## 3. Stale alerts, no user-symptom alerts

**What is happening.** Five warning alerts go to Discord now, and have for days to weeks. They are KubePodCrashLooping and KubeDeploymentReplicasMismatch for app-c-coturn, two KubeJobFailed for app-a-prod, and KubeCPUOvercommit. Alertmanager sent 24 notifications in the last day and none failed, yet the coturn outage went on for 38 days. Of the 161 alert rules, 153 watch causes and 7 watch app metrics, and none was confirmed to check site error ratio or latency.

- Affected:
  - app-c-coturn: KubePodCrashLooping has fired for 38.1 days while the pod stayed down.
  - app-a-sandbox-watchdog: two old failed Jobs from 2026-10-25 and 2026-10-28 keep KubeJobFailed firing. The CronJob succeeds every minute.
  - Cluster CPU: KubeCPUOvercommit fires because 6.17 cores are requested against the 6.0 cores left if node-b is lost.
- Checked and healthy: no notification failures in 24 hours, and no active or forgotten silences.
- Changed for another reason: none.
- Not checked: what the Discord channel shows and who reads it. Also Grafana alerting, which needs a Grafana token.

**Why.** Cause alerts are left firing until they become background noise. Likely. Evidence: the same five warnings repeat every 4 hours to the default Discord receiver, the failed Jobs were never cleaned up, and the overcommit was never decided on.

**Suggested fix.**

① Save the status of the two failed watchdog Jobs, then delete them.

```
kubectl -n app-a-prod get job app-a-sandbox-watchdog-29881700 app-a-sandbox-watchdog-29887083 -o yaml > watchdog-failed-jobs.yaml && kubectl -n app-a-prod delete job app-a-sandbox-watchdog-29881700 app-a-sandbox-watchdog-29887083
```

The two Jobs and any remaining pods are removed, and KubeJobFailed for app-a-prod resolves.

Risk: the saved file is their only record. Argo CD does not track Jobs made by a CronJob, so nothing recreates them. The next run that exceeds its 120-second deadline fires the alert again, which is the alert working.

Check: `kubectl -n app-a-prod get jobs | grep -c Failed` returns 0. KubeJobFailed for app-a-prod leaves Alertmanager within minutes.

② Today, fix app-c-coturn as in problem 1. That clears the two app-c-prod alerts.

Check: Alertmanager shows no app-c-prod alert.

③ This week, decide on KubeCPUOvercommit. You have two options:

- Lower the CPU requests of stateless workloads until the total fits on node-a alone. Never lower them on the databases.
- Accept the risk for a two-node cluster. Route the alert to the null receiver in the kube-prometheus-stack values in Git, with a comment saying why.

Risk: lowering requests restarts those pods, and single-replica Deployments are down while they roll. Routing the alert away hides a real capacity limit. Losing node-b already stops the API, so the alert adds little today. It matters again with a third node.

Check: KubeCPUOvercommit no longer reaches Discord, and the reason sits next to the route.

④ When the noise is gone, add alerts on what users see:

- Enable ingress-nginx controller metrics and a ServiceMonitor.
- Alert on a 5xx ratio above 1% for 5 minutes, and on p99 latency per host.
- Add an alert for OOMKilled containers. No rule covers them today.

First, save the current values.

```
helm -n ingress-nginx get values nginx-ingress -o yaml > nginx-values.yaml
```

Add `controller.metrics.enabled=true` and `controller.metrics.serviceMonitor.enabled=true` to that file. Then upgrade.

```
helm -n ingress-nginx upgrade nginx-ingress ingress-nginx/ingress-nginx --version 4.14.0 -f nginx-values.yaml
```

The two controller pods restart. They carry all public traffic. With 2 replicas, surge 1 and unavailable 0, one pod keeps serving while the new pod schedules and becomes Ready.

Risk: without `-f`, Helm resets the values to chart defaults. That includes the Service type and the MetalLB address <ip>. Without `--version`, Helm also upgrades the controller.

ingress-nginx 1.14.0 is retired upstream, so this is also a good time to plan its replacement.

Check: `kubectl -n monitoring get prometheusrules` shows the new rules. The query nginx_ingress_controller_requests returns series.

**Rollback.** The deleted Jobs are recorded in the saved YAML. Undo the Helm change with `helm rollback nginx-ingress` to the previous revision. The rule and route changes are Git commits that git revert undoes.

**Why this happens.**

- Principle: an alert that has fired for days means nobody is looking, or a false positive was left alone. Real problems get buried in that noise. With alerts only on causes such as CPU or job status, you learn about outages from users.
- Read: the Google SRE book, chapter 6, Monitoring Distributed Systems. Also the kube-prometheus-stack runbooks for KubeJobFailed and KubeCPUOvercommit.

**Evidence.**

| What | Value | Source |
|---|---|---|
| Alerts active on Discord | 5 | summary.json |
| Notifications sent, last 24 hours | 24 | metrics/am_notifications_1d.json |
| Failed notifications, last 24 hours | 0 | metrics/alertmanager_notifications_failed_1d.json |
| Rules on a user symptom, of 161 | 0 | summary.json |
| KubeCPUOvercommit firing | 30.6 days | findings-draft.json |
| Oldest KubeJobFailed for app-a-prod | 11.2 days | findings-draft.json |

## 4. Kubernetes 1.33 past end of life

**What is happening.** Both nodes run k3s v1.33.5+k3s1. Upstream support for 1.33 ended on 2026-06-28, so the cluster has gone 130 days without Kubernetes security patches. 1.34 also left support on 2026-10-27, so reaching a supported version takes two upgrades in a row. Both nodes also have pending OS updates and need a reboot.

- Affected: node-b, the k3s server, needs a reboot and has 7 security updates pending. node-a, the agent, needs a reboot and has 1 pending.
- Checked and healthy: no API objects that 1.34 removes. The k3s certificates have at least 287 days left.
- Changed for another reason: none.
- Not checked: whether any CVE fixed after v1.33.5 applies here. Also manifests in Git or Helm charts that are not applied yet.

**Why.** The cluster has stayed on the version it was installed with, and nothing upgrades k3s automatically. Likely. Evidence: no upgrade controller is present in the cluster.

**Suggested fix.**

① Check for APIs removed up to 1.35.

```
pluto detect-all-in-cluster --target-versions k8s=v1.35.0 -o wide; kubent --target-version 1.35.0
```

This only reads.

Check: both print no objects. They do not see manifests that exist only in Git, Helm hook templates, or resources they may not list.

② Right before the upgrade, and after problem 2's off-node copy exists, take an etcd snapshot and copy it off the node.

```
ssh node-b 'sudo k3s etcd-snapshot save --name pre-upgrade-1.34' && ssh node-b "sudo sh -c 'cat /var/lib/rancher/k3s/server/db/snapshots/pre-upgrade-1.34*'" > ~/k3s-backup/pre-upgrade-1.34.db
```

This adds a snapshot of about 38 MB on node-b and a copy on your machine.

Risk: the nightly cleanup at 03:00 UTC keeps only the 5 newest snapshots, so the copy on the node is gone within about three days. The off-node copy is the one that counts.

The exact file name k3s gives is unverified. If the glob matches more than one file, list the directory and copy the newest.

Check: `ls -l ~/k3s-backup/pre-upgrade-1.34.db` shows about 38 MB.

③ In a maintenance window, upgrade one version at a time, following the k3s manual upgrade guide:

1. Upgrade node-b, the server, to the latest v1.34 k3s release.
2. Upgrade node-a, the agent.
3. Check that every node is Ready and every pod is back.
4. Repeat for v1.35.

Do the OS reboots separately, one node at a time.

k3s restarts on each node with the new version.

Risk while k3s restarts:

- node-b is the only server. While k3s restarts there, the API is down and nothing can be scheduled or changed.
- Whether running containers keep running through the restart is unverified here.

Risk during the reboots:

- A reboot of node-b stops all 48 pods on it, including every production database, until it is back.
- A reboot of node-a stops the app-c, app-f and app-d front ends.

Before you restart k3s on node-b:

- node-b's --server flag points at <ip>, an address no node has. Read the k3s config on node-b first.
- ingress-nginx 1.14.0 and cert-manager 1.14.4 each support a range of Kubernetes versions. Check those ranges against 1.35.

Check: `kubectl get nodes` shows both nodes Ready on the new version. `kubectl get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded` shows only the pods that were failing before.

**Rollback.** The snapshot steps are undone by deleting files. k3s cannot be downgraded a version in place. The way back is restoring the pre-upgrade snapshot from ② on the old binary, with the dumps from problem 2.

**Why this happens.**

- Principle: an unsupported version gets no security patches. On k3s you cannot skip a version, so every month of delay makes the upgrade path longer.
- Case: in 2025, ZenML ran an outdated EKS version and had skipped several upgrades. During the catch-up, a Terraform change removed IAM permissions from the worker nodes, and all workspaces were down for about 8 hours. Here the cluster is also two versions behind, and the catch-up runs on a single server node.
- Read: the K3s documentation, Upgrades: manual upgrades. Also the Kubernetes documentation, Version Skew Policy.

**Evidence.**

| What | Value | Source |
|---|---|---|
| Server version | v1.33.5+k3s1 | inventory.json |
| Days since end of life | 130 | findings-draft.json |
| Objects removed in 1.34 | 0 | summary.json |
| Security updates pending on node-b | 7 | summary.json |
| k3s certificates, days left | 287 | summary.json |

## 5. Four Postgres DBs open on NodePorts

**What is happening.** Four production databases are open on NodePorts 30432 to 30435 on both nodes, without TLS. A probe reached all four ports on both nodes, from the other node over the LAN and from a Mac over Tailscale. Anyone on the LAN or the tailnet can try passwords against them.

- Affected: app-d-postgres on 30433, app-d-postgres-mx on 30435, app-d-postgres-vn on 30434 and app-g-postgres on 30432. All answered over the LAN and over Tailscale.
- Checked and healthy: no other Service is exposed this way besides ingress-nginx on 80 and 443. The MetalLB port 7946 did not answer from the other node.
- Changed for another reason: none.
- Not checked: whether the router forwards these ports from the internet, how each database authenticates remote clients, and who connects through the ports today.

**Why.** The *-external Services were added in Git for access from outside the cluster and left in place. Likely. Evidence: they carry Argo CD tracking for the apps app-d-kr, app-d-mx, app-d-vn and app-g, and they were created between 2025-11-11 and 2026-03-14.

**Suggested fix.**

① Before closing the ports, see whether something still uses them.

```
for t in app-d-prod/app-d-postgres-0 app-d-prod/app-d-postgres-mx-0 app-d-prod/app-d-postgres-vn-0 app-g-prod/app-g-postgres-0; do ns=${t%/*}; pod=${t#*/}; echo "== $t"; kubectl -n $ns exec $pod -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select client_addr, usename, application_name, backend_start from pg_stat_activity where client_addr is not null"'; done
```

This runs four read-only queries.

Risk: none to the data. Through a NodePort, the client address likely shows a node or flannel address, not the real client. It shows that something uses a port, not who. Ask the people who hold the passwords too.

Check: addresses outside <ip>/16, or the 10.42.x.0/1 gateway addresses, mean something still uses the NodePorts. Clients that connect only now and then do not show.

② When nobody needs the ports, or those users have a port-forward instead, delete the four *-external Service manifests in Git. They live in prod/app-d-kr, prod/app-d-mx, prod/app-d-vn and prod/app-g. Argo CD prunes the Services.

For by-hand access, they can use:

```
kubectl -n app-d-prod port-forward svc/app-d-postgres 15432:5432
```

The four NodePort Services disappear. The ClusterIP Services that the apps and dump jobs use stay as they are. The database pods do not restart.

Risk: any outside client on 30432-30435 loses access at once. Argo CD selfHeal recreates a Service you delete by hand, so make the change in Git.

Check: `kubectl get svc -A | grep -c NodePort` returns 0. `nc -vz -w 3 <node address> 30433` from the Mac over Tailscale fails.

**Rollback.** Run git revert on the commit, and Argo CD recreates the four Services with the same ports.

**Why this happens.**

- Principle: a NodePort listens on every node interface, so a database behind it is guarded by one password. Safer options are a ClusterIP Service with port-forward, or an interface reachable only over Tailscale.
- Read: the Kubernetes documentation on Service type NodePort. Also the PostgreSQL documentation, The pg_hba.conf File.

**Evidence.**

| What | Value | Source |
|---|---|---|
| NodePort of app-g-postgres-external | 30432 | summary.json |
| NodePort of app-d-postgres-external | 30433 | summary.json |
| NodePort of app-d-postgres-vn-external | 30434 | summary.json |
| NodePort of app-d-postgres-mx-external | 30435 | summary.json |
| All four ports answered, both nodes | over LAN and Tailscale | extra/node-port-probe.txt, extra/node-port-probe-lan.txt |

## Since the previous full run

2026-11-04T22-29-59 (full)

Work the previous report asked for: none

**Appeared.**

- 503 responses from the apiserver at 0.004 per second, measured while collection ran (controlplane.apiserver-5xx)
- CoreDNS health checks of the upstream resolvers 1.1.1.1 and 8.8.8.8 failed once in the last hour, with no SERVFAIL answers (coredns.forward-upstream-errors)
- CPUThrottlingHigh for logging/elasticsearch-0, severity info and routed to the null receiver, firing for 3.1 days

**Went away.**

- none

**Changed because the checks changed, not the cluster.**

- The log-signature rules changed in this kubegap version, so four log findings are new for that reason: cert-manager 'propagation check failed' (10 lines, 02:31-03:35 UTC), 'too many open files' from containerd on node-b (32 lines, 03:30-04:17 UTC), and two MetalLB speaker signatures

**Checks whose rule changed between the runs.**

- `logs.signatures.cert-manager.challenge-failed` (warn/medium)
- `logs.signatures.common.too-many-open-files` (warn/high)
- `logs.signatures.metallb.speaker-peer-unreachable` (warn/low)
- `logs.signatures.metallb.speaker-error` (warn/medium)

## Serious, not today

- No SLO tool or SLO recording rule exists. This waits until problem 3 gives the sites symptom alerts.
- node-b is the only k3s server and the only node allowed to run the production databases. Without node-b, node-a's 6.0 cores fall short of the 6.17 cores requested, and the API stops anyway. Fixing this needs a third node, which is a hardware decision.
- node-b's single SSD carries etcd, Elasticsearch, Prometheus, the registry and 19 local-path volumes.
  - Elasticsearch uses 103,451 MB on a 20,480 MB claim.
  - Prometheus uses 22,004 MB in emptyDir.
  - The registry uses 32,732 MB.
  - etcd logged 191 slow applies in 24 hours, the slowest 1,160 ms, with no leader change.
  - No user-visible effect was found. Disk latency was not measured.
- Prometheus, with 21.4 GiB and 30 days of history, keeps its data in emptyDir, and so do Alertmanager and Grafana. A pod restart drops that data.
- Seven Argo CD apps with automated prune manage their own Namespace object, and local-path volumes use reclaimPolicy Delete. Removing a Namespace manifest from Git deletes the namespace and its data.
- CoreDNS runs one replica, on node-b, with no PodDisruptionBudget.
- 37 workloads can run on only one node, because of nodeSelector or local volumes. Among them are app-f-api-server with 3 replicas, app-f-admin, app-f-app-x-client and app-d, all pinned to node-a.
- node-b reached its inotify instance limit, fs.inotify.max_user_instances=128. containerd logged 'too many open files' 32 times between 03:30 and 04:17 UTC, while the nightly Jobs ran.
- app-e-api/app-e-minio uses 98% of its memory limit at the 7-day p95. No OOM kill appears in the 7-day metrics.
- Elasticsearch, Kibana and the es-index-retention CronJob in logging set ELASTIC_PASSWORD as a literal env value, not a Secret reference.
- default/app-y-backend-config has keys named JWT_SECRET, JWT_RELAY_SECRET, TWITTER_CLIENT_SECRET and TWITTER_CLIENT_SECRET_RELAY, and nothing mounts it. The values were not read.
- Prometheus, Elasticsearch, app-e-postgres and fluent-bit are CPU-throttled in more than 10% of their periods.
- cert-manager is due to renew app-g-prod-tls on 2026-11-06 and app-e-api-tls on 2026-11-07. They expire on 2026-12-06 and 2026-12-07.

## Each area in one line

| Area | What |
|---|---|
| resources | Requests run ahead of use for CPU and behind for memory; app-e-minio is at 98% of its memory limit. |
| scaling | 11 CPU-only HPAs, 6 never scaled; no node autoscaler, as expected for two machines. |
| observability | 161 cause-only alert rules, 6 always firing; monitoring data on emptyDir; no ingress metrics. |
| traffic | Retired ingress-nginx, four database NodePorts and a down TURN relay. |
| resilience | No off-node backup, one server node holding every production database, many single replicas. |
| hygiene | Mutable image tags, the coturn outage among them; four lingering Failed pods. |
| storage | Local-path claims not enforced: Elasticsearch at 5 times its claim; all volumes reclaim on delete. |
| security | No literal secrets found in the flagged script ConfigMaps; no NetworkPolicy default deny or Pod Security enforcement; plaintext Elasticsearch password in env. |
| cost | 4.9% CPU use of two owned machines; nothing to drop. |
| tenancy | Production, CI and system workloads share both nodes; no saturation in 7 days. |
| node OS | Both nodes need a reboot; node-b hit the inotify limit; no kernel errors. |
| platform | k3s 1.33 past end of life; a single etcd server logging slow applies. |

## What this run could not see

- Loki logs: no Loki Service exists, so nothing was searched there. Run `/kubegap setup` and say where Loki runs, or that it is not installed.
- Grafana datasources, dashboards and alerts: Grafana answers only logged-in callers. Create a Viewer service-account token in Grafana, and add it as grafana_api_token in the kubegap config file in your own editor.
- Request rate, errors and latency of the sites: ingress-nginx exposes no metrics. Enable controller metrics and a ServiceMonitor as in problem 3, step ④.
- Whether the NodePorts and the coturn ports are reachable from the internet: read the router's port-forwarding table, or probe the public address from a network outside the LAN and the tailnet.
- Disk latency and I/O on node-b: query `rate(node_disk_io_time_seconds_total[5m])` for instance <ip>:9100 in Prometheus.

## Numbers

| Severity | fail | warn | vs. previous full run |
|---|---|---|---|
| critical | 2 | 2 | fail 0, warn 0 |
| high | 28 | 68 | fail 0, warn +2 |
| medium | 73 | 135 | fail +2, warn 0 |
| low | 9 | 121 | fail 0, warn +1 |

Checks behind each problem:

- problem 1: `events.tracked-warning-reasons.BackOff`, `resilience.restarts-crashloop.app-c-prod/app-c-coturn-549854dfcb-jgp4h:coturn`, `security.privileged-or-host-access.app-c-prod/deployment/app-c-coturn`, `hygiene.mutable-image-tag.app-c-prod/deployment/app-c-coturn:coturn`, `hygiene.polaris-reliability-danger.app-c-prod/deployment/app-c-coturn`, `observability.alert-firing-stale.KubePodCrashLooping/app-c-prod`, `operators.unhealthy-condition.deployments/app-c-prod/app-c-coturn`, `traffic.pod-not-ready.app-c-prod/app-c-coturn`, `observability.alerts-always-firing.KubePodCrashLooping`
- problem 2: `resilience.no-backup.cluster`, `resilience.backup-same-node.app-d-prod/app-d-postgres-backup`, `resilience.backup-same-node.app-d-prod/app-d-postgres-vn-backup`, `resilience.backup-same-node.app-f-prod/app-f-mysql-backup`, `resilience.backup-same-node.app-g-prod/app-g-postgres-backup`, `storage.local-path-over-capacity.app-a-prod/app-a-postgres-backup-pvc`, `resilience.backup-same-node.app-a-prod/app-a-postgres-backup`, `resilience.backup-same-node.app-d-prod/app-d-postgres-mx-backup`, `resilience.backup-same-node.app-e-api/app-e-postgres-backup`, `platform.k3s-etcd-snapshot-local-only.node-b`, `resilience.cronjob-policy.app-d-prod/app-d-postgres-backup`, `resilience.cronjob-policy.app-d-prod/app-d-postgres-mx-backup`, `resilience.cronjob-policy.app-d-prod/app-d-postgres-vn-backup`, `resilience.cronjob-policy.app-f-prod/app-f-mysql-backup`, `resilience.cronjob-policy.app-g-prod/app-g-postgres-backup`, `resilience.prod-db-without-backup-cronjob.cluster`
- problem 3: `observability.no-symptom-alerts.cluster`, `observability.failure-mode-uncovered.OOMKill`, `observability.alert-firing-stale.CPUThrottlingHigh/monitoring`, `observability.alert-firing-stale.KubeCPUOvercommit`, `observability.alert-firing-stale.KubeJobFailed/app-a-prod`, `observability.alert-firing-stale.KubeQuotaFullyUsed/app-i-prod`, `observability.alerts-always-firing.CPUThrottlingHigh`, `observability.alerts-always-firing.KubeCPUOvercommit`, `observability.alerts-always-firing.KubeDeploymentReplicasMismatch`, `observability.alerts-always-firing.KubeJobFailed`, `observability.alerts-always-firing.KubeQuotaFullyUsed`, `observability.ingress-controller-metrics-missing.ingress-controller`, `observability.alert-firing-stale.CPUThrottlingHigh/logging`, `observability.page-severity-cause-alerts.cluster`, `observability.severity-channels-not-separated.cluster`
- problem 4: `platform.k8s-version-eol.cluster`, `node.os-updates-pending.node-a`, `node.os-updates-pending.node-b`, `node.reboot-required.node-a`, `node.reboot-required.node-b`
- problem 5: `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-external`, `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-mx-external`, `traffic.db-exposed.nodeport/app-d-prod/app-d-postgres-vn-external`, `traffic.db-exposed.nodeport/app-g-prod/app-g-postgres-external`

Details and every table: [`report-details.md`](report-details.md) · kubegap 0.1.2, rubric 0.1.80 · snapshot `~/.kubegap/snapshots/my-cluster/2026-11-05T17-00-00`
