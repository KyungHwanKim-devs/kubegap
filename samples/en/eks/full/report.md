# app-u-cluster-eks — full audit, 2026-11-15 02:09

Broken now: none

The 5 largest problems: ① The production databases have no backup ② Kafka accepts connections from the whole internet ③ The production Neo4j password is written into its manifest ④ Kubernetes 1.32 is past support and Karpenter 0.37 does not support it ⑤ Four production load balancer health checks filter nothing

What already happened: Prometheus was killed for running out of memory · Production pods could not be scheduled 91 times in one day

Scale: medium

## The cluster at a glance

| What | Value |
|---|---|
| Nodes | 9 of 9 Ready |
| Pods | 131 running, 0 pending, 0 failed |
| Namespaces | 21, 8 production |
| Components | 23: actions-runner-controller, alb-controller, alertmanager, argocd, coredns, ebs-csi, ecr, eks-managed-addons, external-dns, external-secrets, grafana, karpenter, keda, kube-proxy, kube-state-metrics, loki, metrics-server, node-exporter, prometheus, prometheus-operator, promtail, victoria-metrics, vpc-cni |
| Metrics and log stores | prometheus 2.49.1 / loki 2.6.1 |
| Kubernetes | v1.32.13-eks-577a51e (eks) |

## What already happened

There is no earlier run to compare with, so this covers only what this run collected.

### Prometheus was killed for running out of memory

At 14:34:30 UTC on 2026-11-14, about two and a half hours before this audit, the `prometheus` container of `monitoring/prometheus-kube-prometheus-stack-prometheus-0` was ended by the kernel for exceeding its memory limit of 1536Mi, and it restarted. That was its only restart in the last seven days; the pod has restarted 3 times over its whole life. It is running now, so the event itself is over, but the conditions that led to it are still there: its working set is at 73% of the limit, it holds 177,943 active series, and 34% of its CPU periods were throttled over the last 24 hours, so it runs short of CPU through the day as well. Loki in the same namespace was restarted twice in seven days, once for memory.

While Prometheus restarts, no rule is evaluated and no alert can fire. Why memory ran out at that moment is not known. A burst of new series, a heavy query or compaction are all possible, and the audit has no per-query record; the kernel log of its node `node-1-117` could not be read because that node is not registered with SSM.

This exposed a weakness listed among the next largest problems, that no alert covers a container killed for memory: the cluster's own monitoring was killed and no rule exists that would have told anyone.

### Production pods could not be scheduled 91 times in one day

In the 24 hours before this audit the scheduler logged "Unable to schedule pod; no fit" 91 times into the control plane log, all of them for three production workloads: `prod-app-x/app-x-api` 39 times, `prod-app-z-backend/app-z-backend` 26 times and `prod-app-z-backend/app-z-embedding-server` 26 times. No pod is pending now, so each of these pods was placed in the end; how many separate pods waited, and for how long, cannot be told from the log lines, since one waiting pod is logged on every retry.

The reasons the scheduler gave name nodes tainted `karpenter.sh/disruption: disrupting`, nodes still `not-ready` or `uninitialized`, and too little free CPU or memory on the rest. That is the shape of node replacement: Karpenter consolidated or replaced a node, the pods on it were evicted, and they waited until a new node had started, which takes Karpenter about 61 seconds here. This is inferred from the reasons, not from a record of each eviction.

It touches problem 4, Kubernetes 1.32 is past support and Karpenter 0.37 does not support it: these three workloads depend on Karpenter producing a node quickly every time, and that is what the version mismatch puts at risk.

## 1. The production databases have no backup

**Why this one.** When a volume is deleted or its data is corrupted, the data of seven production services is gone for good, because there is nothing to restore it from.

### What is the matter

Eight databases run inside this cluster as StatefulSets with their own volume, seven of them in production: `prod-app-t/app-t-backend-postgresql`, `prod-app-x/app-x-postgresql`, `prod-app-s/app-s-backend-mysql`, `prod-app-y/app-y-backend-mysql`, `prod-app-z-backend/app-z-neo4j`, `prod-app-r/app-r-postgresql` and `prod-app-v/app-v-backend-prod-mysql`, plus `dev-app-s/app-s-backend-mysql`. Not one of them has a backup CronJob, and the cluster has no backup tool such as Velero, no VolumeSnapshot and not even the VolumeSnapshot API.

On the AWS side the account has no Data Lifecycle Manager policy and no AWS Backup plan. In the last 30 days exactly two EBS snapshots were taken, and both are described as "pre-delete backup" of development volumes in `dev-app-v` and `dev-app-y`; by their description they were taken before those volumes were deleted. Nothing copies the production volumes.

The volumes themselves add to the risk. All seven production database volumes are `gp3` EBS volumes whose PersistentVolume has the reclaim policy `Delete`, so deleting the PersistentVolumeClaim, or the namespace that holds it, deletes the EBS volume with it. The StatefulSets keep their claims when the StatefulSet itself is deleted, but deleting a claim or the namespace still deletes the volume.

What the audit found sound: every one of these volumes is bound, none is filling, and EBS keeps them independent of the nodes, so a node failure or a spot interruption does not lose them. What it cannot see is whether an application team dumps its database somewhere outside Kubernetes, for example from a laptop or a CI job. Nothing in the cluster points at such a copy.

### Why it comes about

How this cluster came to have no backup cannot be told from its state. The databases were installed from Helm charts, which create the StatefulSet and its volume but no backup, and a cluster grows one service at a time without anyone owning "the backups" as a whole. The two pre-delete snapshots of development volumes show the idea of a copy exists in the team; it has not been turned into something that runs by itself. This is an inference from what is and is not present.

What a backup protects against depends on where the copy lives. A copy on the same disk as the data only brings back rows deleted by mistake; the disk fails with both. A copy elsewhere in the same cluster survives a node failure but not what reaches the whole cluster: a script or a person with cluster rights deleting volumes, a namespace removed with everything in it, or a mistake in a GitOps tool that prunes a whole environment. In this cluster there is not even the first kind of copy. The EBS volume is the data and the only instance of it.

That is why the usual rule is three copies on two kinds of media with one off site. Kubernetes does not make any of these copies. A VolumeSnapshot is a point-in-time copy on the storage system and exists only through a CSI driver with the snapshot API installed; with the deletion policy `Delete`, removing the VolumeSnapshot object also removes the snapshot. On EKS, the copy can come from AWS instead: a Data Lifecycle Manager policy or an AWS Backup plan takes EBS snapshots on a schedule by tag, outside the cluster's reach.

One more thing holds for every backup. A backup that has never been restored is not known to work: a file that appears every night says the job ran, not that the database comes back from it.

[GitLab](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/) lost production data in 2017 when an engineer removed the data directory of the production database by mistake. The nightly `pg_dump` backups had been failing because of a version mismatch, the mails that reported it were rejected and the S3 bucket was empty; the data came back only from a snapshot someone had taken by hand six hours earlier. What saved them was a copy nobody had planned as the backup, and this cluster has not even that for its production data.

At [InfluxData](https://www.influxdata.com/blog/deleting-production-steps-how-fix-it/) a name collision in the Argo CD configuration made Argo CD delete a whole production environment. The volumes had the reclaim policy `Retain`, so the data stayed and the objects were rebuilt by hand. This cluster is managed by Argo CD too, and its database volumes have `Delete`, so the same mistake here would take the data with the objects.

### How to watch it

There is nothing to watch yet, because no backup job exists. Once one does, two things are worth a rule. The age of the last successful backup, from kube-state-metrics, catches a job that stopped running. The rule has to be made; this cluster has no rule on CronJob success.

```yaml
- alert: BackupCronJobStale
  expr: time() - kube_cronjob_status_last_successful_time{cronjob=~".*backup.*"} > 86400 * 1.5
  for: 30m
```

When the copy is made by AWS instead, AWS Backup reports failed jobs itself; the job status, not a Kubernetes metric, is what to watch.

Whether a copy restores is not visible in any metric. The way to see it is to restore one dump or snapshot into an empty database on a schedule and compare a few row counts.

### How it is solved

At the scale this cluster is run at, with real users depending on these services, the fit is Velero together with snapshots made by AWS. Velero, on a Schedule, backs up the Kubernetes objects of each production namespace and the volumes, and writes the objects to an S3 bucket in another account or region. Next to it, an AWS Backup plan or a Data Lifecycle Manager policy snapshots the EBS volumes daily, selected by the tag `kubernetes.io/created-for/pvc/name` that the EBS CSI driver puts on every volume it creates, and copies those snapshots to a second region. With both in place the objects and the data come back together, and the restore is a procedure someone has practised in a scratch cluster. The cost is one more component to run and upgrade, storage for the snapshots, and a few hours on the calendar for restore tests. A Velero restore skips objects that already exist unless told otherwise, and Velero backups expire after 30 days unless a TTL is set.

For the databases that matter most, a logical dump made by the database's own tool on a CronJob, uploaded to the same bucket, adds a second kind of copy next to the volume snapshot.

Alongside, change the reclaim policy of the production database volumes to `Retain`, so that deleting a claim by mistake leaves the EBS volume in place.

The shape of a DLM policy selecting the volumes of one namespace by the tag the CSI driver sets, one such target per production namespace, as an example and not as something to apply as it stands:

```yaml
PolicyDetails:
  ResourceTypes: [VOLUME]
  TargetTags:
    - Key: kubernetes.io/created-for/pvc/namespace
      Value: prod-app-x
  Schedules:
    - Name: daily
      CreateRule: { Interval: 24, IntervalUnit: HOURS, Times: ["18:00"] }
      RetainRule: { Count: 7 }
      CrossRegionCopyRules:
        - TargetRegion: ap-northeast-1
          Encrypted: true
          RetainRule: { Interval: 7, IntervalUnit: DAYS }
```

Where to change it: the backup itself is new and lives in the AWS account and in a new Velero release. The databases are part of the Argo CD applications of each product, for example `app-x-prod`, `app-t-prod`, `app-y-prod`, `app-v-prod` and `app-z-backend-prod`, all from the repository `https://github.com/example-org/iac` under `apps/prod/<product>`, with selfHeal on. A change made by hand to the StatefulSets in the cluster is reverted, and a dump CronJob added outside the repository is not tracked by anything; add both in that repository. The reclaim policy is a field of the PersistentVolume, which Argo CD does not manage, so it can be patched on each volume directly.

What to be careful of when applying it: taking a snapshot does not stop a database, and changing a PersistentVolume's reclaim policy does not touch the pod. Each of these databases runs a single replica, so a dump CronJob that locks tables runs against the only instance serving users; schedule it outside busy hours. Restore tests belong in a scratch cluster, so that a test never runs against the production namespaces.

At a larger scale, the databases move out of the cluster into a managed service such as RDS with point-in-time recovery, the backup account is separate and write-once, and a restore is rehearsed every quarter with a recorded recovery time.

### Evidence

| What | Value | Source |
|---|---|---|
| Databases with their own volume | 8, of them 7 in production | `resilience.backup.databases` |
| Backup CronJobs for those databases | 0 | `resilience.backup.databases` |
| Backup tool, etcd snapshots, VolumeSnapshots | none, 0, 0 | `resilience.no-backup` finding |
| VolumeSnapshot API installed | no | `storage.snapshots.volumesnapshot_crd` |
| DLM policies, AWS Backup plans | 0, 0 | `eks.no-backup-policy` finding |
| EBS snapshots in 30 days | 2, both pre-delete copies of dev volumes | `storage.snapshots.ebs_snapshot_descriptions` |
| Production database volumes with reclaim policy Delete | 7 | `storage.pvcs.prod_db_delete_reclaim` |
| Storage class of those volumes | gp3 | `storage.pvcs.rows` |
| Claims kept when the StatefulSet is deleted | yes (`whenDeleted: Retain`) | objects `statefulsets prod-app-z-backend/app-z-neo4j`, `prod-app-x/app-x-postgresql` |

### Further reading

- [GitLab: Postmortem of database outage of January 31](https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/): how believing a backup exists differs from restoring one.
- [Velero: How Velero Works](https://velero.io/docs/main/how-velero-works/): what a backup, a schedule and a restore do, and what a restore leaves alone.
- [restic: Preparing a new repository](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html): the storage back ends restic writes to and how the repository password works, for the dump CronJobs.
- [k3s: etcd-snapshot](https://docs.k3s.io/cli/etcd-snapshot): the S3 options and the restore procedure; useful as a model of a snapshot that leaves the cluster by itself.

## 2. Kafka accepts connections from the whole internet

**Why this one.** If the broker's authentication is weak or misconfigured, anyone on the internet can read or write the messages that flow between this cluster's services, and data read by a stranger cannot be taken back.

### What is the matter

The Service `middleware/kafka-controller-0-external` is of type LoadBalancer and carries the annotation `service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing`, so the AWS Load Balancer Controller built a public Network Load Balancer for it. It forwards ports 9094 and 443 to the external listener of the only Kafka broker, `kafka-controller-0`, and external-dns publishes it under the name `broker.lab-k.example`. The security group of that load balancer allows port 9094 from `0.0.0.0/0`. The Service sets no `loadBalancerSourceRanges`, so nothing narrows who may connect.

Kafka here is a single broker running Kafka 3.6.1 from the Helm chart `kafka-26.8.1`, with a replication factor of 1. It is the message bus of the cluster: the alert rules `DmmConsumerLagHigh`, `IlBridgeLagHigh`, `IlEditBridgeLagHigh` and `OnPremiseConsumerLagHigh` watch consumers of it, and the last of them suggests that a consumer outside the cluster is why the listener is public. That is inferred from the rule name.

What the audit found sound: the broker has SCRAM users configured (`KAFKA_CLIENT_USERS`, with the passwords taken from the Secret `kafka-user-passwords`), so clients are expected to authenticate. What it could not see is the protocol of the external listener itself, which decides whether a client on port 9094 must authenticate and whether the traffic is encrypted; that setting is not in any object this audit reads. Whether anyone outside has actually connected is not known either.

The databases are exposed in a milder way. The Network Load Balancer `app-u-db-shared`, created outside Kubernetes, puts MySQL, PostgreSQL, Redis and Neo4j ports of production databases on an internet-facing address, but its security group allows at most four single addresses per port. That is an allow-list, not an open door, and it holds as long as the list stays correct.

### Why it comes about

Why the listener was made public cannot be confirmed. A consumer outside the VPC, such as an on-premise system, needs a route to the broker, and an internet-facing load balancer is the quickest one to build. This is inferred from the rule names and the published host name.

A Service of type LoadBalancer puts a port outside the cluster, and who can reach it is decided outside Kubernetes. With the AWS Load Balancer Controller the scheme is internal unless the annotation says `internet-facing`, which this Service does. The allowed sources come from `spec.loadBalancerSourceRanges`, and when that field is empty the controller uses `0.0.0.0/0` and writes a security group that allows the whole internet.

For an HTTP service that is the intended state. For Kafka, PostgreSQL, MySQL or Redis it means the listener of the data store is on the internet, and the only thing between a stranger and the data is the store's own authentication. Nothing in the cluster reports it: the Service is healthy and every consumer works.

An allow-list, as on `app-u-db-shared`, is better and still not private. The address is reachable from everywhere, and only the list decides who gets through, so every edit to that list has to be right.

### How to watch it

The state is a property of the objects and the security group, not a time series, so it is seen in the inventory: a LoadBalancer Service with the internet-facing scheme and no source ranges.

```bash
kubectl get svc -A -o json | jq -r '.items[] | select(.spec.type=="LoadBalancer") | [.metadata.namespace, .metadata.name, (.metadata.annotations["service.beta.kubernetes.io/aws-load-balancer-scheme"] // "internal"), ((.spec.loadBalancerSourceRanges // []) | join(","))] | @tsv'
```

Who knocks on the port shows in two places once a security group narrows it. The CloudWatch metric `SecurityGroupBlockedFlowCount_Inbound` of the Network Load Balancer counts the flows its security group turned away, and VPC flow logs on the load balancer's network interfaces list the source addresses that connected to port 9094.

### How it is solved

At the scale this cluster is run at, the broker should not have an address on the internet at all. Make the load balancer internal by setting the scheme annotation to `internal`, and give the outside consumer a path into the VPC instead: a site-to-site VPN, a peered network, or the Tailscale network this cluster already uses for `app-ad`. If an internet-facing address has to stay for a while, list the consumer's addresses in `spec.loadBalancerSourceRanges`, so that the security group allows only them, and make sure the external listener requires SASL with TLS. In return, nothing listens for strangers, and the allow-list becomes a second layer instead of the only one. The cost is that every outside client needs a network path into the VPC, which is work on the client's side.

The shape of the change, as an example in the chart's values and not as something to apply as it stands:

```yaml
externalAccess:
  enabled: true
  controller:
    service:
      type: LoadBalancer
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-scheme: "internal"
      loadBalancerSourceRanges:
        - <ip>/16
```

Where to change it: the Service carries the Helm marks of the release `kafka` in the namespace `middleware` (chart `kafka-26.8.1`, revision 7). Nothing in the cluster marks it as managed by Argo CD, so change it in the values that release was installed from and upgrade the release; a change made to the Service by hand is overwritten at the next upgrade. The load balancer `app-u-db-shared` was created outside Kubernetes and is changed where it was made, in the AWS account.

What to be careful of when applying it: this stops the message bus for a while. The broker has a start-up container, `auto-discovery`, that reads the load balancer's address when the pod starts, so after the address changes the broker has to be restarted to hand clients the new one, and with a single broker and a replication factor of 1 that restart stops every producer and consumer until it is back. Plan for the load balancer to get a new, internal address. Every client that connects through `broker.lab-k.example` loses its connection until external-dns has published that address and the client can reach it, and a consumer outside the VPC cannot reconnect at all until its network path exists. The broker's external listener settings in the release values name how clients reach it, so read them together with this change. The example shows only the annotation that changes; the Service also carries the external-dns host name, the load balancer type and the target type, and those have to stay. Do it after the outside consumer has a working path, at a quiet hour. The data volume of the broker is not touched by the restart.

At a larger scale, Kafka is reached only over private networking such as PrivateLink, clients authenticate with mutual TLS, and the network rules live in code with review, so no single edit opens a port.

### Evidence

| What | Value | Source |
|---|---|---|
| Service type and scheme | LoadBalancer, internet-facing | object `services middleware/kafka-controller-0-external` |
| Ports forwarded | 9094, 443 | `traffic.db_exposed` |
| Sources allowed on 9094 | 0.0.0.0/0 | `traffic.db_exposed` |
| `loadBalancerSourceRanges` | not set | `traffic.db_exposed` |
| Published host name | broker.lab-k.example | object `services middleware/kafka-controller-0-external` |
| Brokers, replication factor | 1, 1 | object `statefulsets middleware/kafka-controller` |
| Helm release | kafka in middleware, chart kafka-26.8.1, revision 7 | `hygiene.helm.releases` |
| `app-u-db-shared` ports on an internet-facing address | 8 | `traffic.db_exposed` |
| `app-u-db-shared` sources allowed per port | at most 4, each a /32 | `traffic.db_exposed` |

### Further reading

- [AWS Load Balancer Controller: Service annotations](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/service/annotations/): the defaults for scheme, source ranges and security groups that decide who can connect to a Network Load Balancer.
- [Kubernetes: Service](https://kubernetes.io/docs/concepts/services-networking/service/): what a LoadBalancer Service really opens and how the internal load balancer annotation of each cloud works.
- [Elastic Load Balancing: Update the security groups for your Network Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-security-groups.html): what an NLB without a security group lets through, and the metric and logs that show blocked traffic.

## 3. The production Neo4j password is written into its manifest

**Why this one.** Everyone who can read the manifest repository, the Argo CD UI or the StatefulSet can read the password of a production graph database whose port is on an internet-facing address, and a password once read cannot be made secret again.

### What is the matter

The `neo4j` container of the StatefulSet `prod-app-z-backend/app-z-neo4j` sets the environment variable `NEO4J_AUTH` as a literal value of 26 characters, not as a reference to a Secret. By its name and its length, the value is the user and password of the database; that is inferred from the name, since the value is not read. The audit records only the name and the length, never the value.

The same container already reads the password the right way under another name: `GRAPH_DB_PASSWORD` comes from the key `NEO4J_PASSWORD` of the Secret `app-z-backend-secret`. So a database password already lives in a Secret, and a credential for the same database is written out in plain text next to it; whether the two values are the same cannot be told, because neither is read.

How far it reaches: the StatefulSet is managed by the Argo CD application `app-z-backend-prod` from the repository `https://github.com/example-org/iac`, path `apps/prod/app-z-backend`, so the value is in that Git repository and its whole history, in the Argo CD UI and in the output of `kubectl get statefulset -o yaml` for anyone with read access to workloads in the namespace. The Neo4j Bolt port 7687 of this database is also bound to the internet-facing load balancer `app-u-db-shared`, limited to four addresses by its security group.

What the audit found sound: the rest of the cluster keeps its credentials properly. 36 ExternalSecrets pull values from AWS Secrets Manager through the ClusterSecretStore `aws-secrets-manager`, all of them ready, and no ConfigMap holds a value that looks like a password. A second hit of the same kind, `TS_KUBE_SECRET` in `app-ad`, was looked at and is the name of a Secret, not a credential. Whether this password has been changed since it was first written into the repository cannot be told.

### Why it comes about

The likely history is that the StatefulSet was written first with the password inline and the Secret came later for the application's own use. That is inferred from the two variables side by side; the repository history would tell.

Kubernetes has two objects that look alike. A ConfigMap is for data that is not confidential. A Secret is meant for confidential data, which lets the cluster treat it differently: reading Secrets is granted separately in RBAC, and encryption at rest is configured for them. A password written as a literal `env` value in a StatefulSet gets none of that. It is part of an object that everyone who can read workloads can see, and it travels wherever the manifest goes: the Git repository, `kubectl describe`, the Argo CD UI.

A Secret is not safe by itself either. Its value is only base64 encoded, so a Secret manifest committed to Git is as readable as the plain value. Inside the cluster, list and watch on Secrets reveal the content just as get does, and anyone who may create a pod in a namespace can mount any Secret of that namespace. That is why the usual practice is to keep the value in a store outside the cluster and let only a reference live in Git, which is what this cluster already does for 36 other values.

On EKS the storage side is covered: this cluster has envelope encryption of Secrets turned on. That protects the copy in etcd, not a value written in a manifest.

### How to watch it

A literal value that looks like a credential is found in the manifest before it is merged. kube-linter runs the check `env-var-secret` by default, and running it in the pipeline of the IAC repository catches the next one.

```yaml
# .kube-linter.yaml in the IAC repository
checks:
  include:
    - env-var-secret
```

For who reads Secrets in the cluster, the API server audit log at the Metadata level records each read of a Secret with the user. On EKS that is the `audit` log type of the control plane logging, which is not among the four types this cluster sends to CloudWatch (api, authenticator, controllerManager, scheduler); it would have to be turned on.

### How it is solved

At the scale this cluster is run at, the fit is the pattern the cluster already uses. Put the Neo4j credential in AWS Secrets Manager, let an ExternalSecret in `prod-app-z-backend` create a Secret from it through `aws-secrets-manager`, and set `NEO4J_AUTH` from that Secret with `valueFrom.secretKeyRef`. Then change the password, because the old one has been readable in the repository and must be treated as known. The value then has one home outside the cluster, it can be rotated without touching a manifest, and Git holds only a reference. The cost is nothing new: the operator and the store are already running.

The shape of the reference, as an example and not as something to apply as it stands:

```yaml
env:
  - name: NEO4J_AUTH
    valueFrom:
      secretKeyRef:
        name: app-z-neo4j-auth
        key: NEO4J_AUTH
```

Where to change it: the StatefulSet is managed by the Argo CD application `app-z-backend-prod`, repository `https://github.com/example-org/iac`, path `apps/prod/app-z-backend`, revision `main`, with selfHeal on. A change made to the StatefulSet in the cluster is reverted, so make it in the repository. Removing the line from the current files does not remove it from the Git history; changing the password is what makes the old value useless.

What to be careful of when applying it: create the ExternalSecret and check that the Secret exists before the StatefulSet refers to it, because a pod that references a missing Secret does not start and this database has no second replica. Changing the environment of the StatefulSet restarts its pod, and `app-z-neo4j` runs a single replica, so the database is unavailable to `app-z-backend` while the pod restarts. The data volume `data-app-z-neo4j-0` is kept across the restart. Moving the value into a Secret does not by itself change the password stored in the existing database on `data-app-z-neo4j-0`; whether Neo4j reads `NEO4J_AUTH` again on a volume that already holds data is not something this audit can tell, so change the password inside Neo4j itself, and update `app-z-backend-secret` in the same change window, or `app-z-backend` cannot log in.

At a larger scale, each workload's access to its Secrets is narrowed in RBAC, reads of Secrets are audited and alerted on, and credentials are short-lived and issued per client rather than one shared password.

### Evidence

| What | Value | Source |
|---|---|---|
| Variable set as a literal | `NEO4J_AUTH`, 26 characters | object `statefulsets prod-app-z-backend/app-z-neo4j` |
| Database password read from a Secret | `GRAPH_DB_PASSWORD` from `app-z-backend-secret` key `NEO4J_PASSWORD` | object `statefulsets prod-app-z-backend/app-z-neo4j` |
| Replicas of `app-z-neo4j` | 1 | object `statefulsets prod-app-z-backend/app-z-neo4j` |
| Managed by | Argo CD `app-z-backend-prod`, `apps/prod/app-z-backend`, selfHeal on | `security.plaintext-secret-env` finding |
| ExternalSecrets in the cluster, not ready | 36, 0 | `security.secrets` |
| ConfigMaps with password-like values | 0 | `security.secrets.plaintext_configmap` |
| Envelope encryption of Secrets | on | `inventory.eks.secrets_encryption` |
| Sources allowed on port 7687 of `app-u-db-shared` | 4 | `traffic.db_exposed` |

### Further reading

- [Kubernetes: Good practices for Kubernetes Secrets](https://kubernetes.io/docs/concepts/security/secrets-good-practices/): what administrators and developers each have to do so that a Secret is more than a renamed ConfigMap.
- [External Secrets Operator: overview](https://external-secrets.io/latest/introduction/overview/): how Secrets are synchronised from an external store and who owns which resource.
- [kube-linter: checks](https://raw.githubusercontent.com/stackrox/kube-linter/main/docs/generated/checks.md): the manifest checks for secrets in environment variables and which of them run by default.
- [EKS: Default envelope encryption for all Kubernetes API Data](https://docs.aws.amazon.com/eks/latest/userguide/envelope-encryption.html): what EKS encrypts by default and what happens when a customer key is disabled or deleted.

## 4. Kubernetes 1.32 is past support and Karpenter 0.37 does not support it

**Why this one.** Seven of the nine nodes of this cluster come from Karpenter, and the next control plane upgrade, whether planned or done by EKS at the end of extended support, leaves Karpenter unable to launch nodes, so pods that lose their node have nowhere to go.

### What is the matter

The control plane runs Kubernetes 1.32 (`v1.32.13-eks-577a51e`) and the nodes run `v1.32.9`. EKS standard support for 1.32 ended on 2026-03-23, 237 days ago, and the cluster has been in extended support since then, which AWS bills per cluster hour; extended support ends on 2027-03-23. The Kubernetes project itself stopped patching 1.32 on 2026-02-28.

Karpenter, which launches seven of the nine nodes through two of its four NodePools (the other two nodes belong to an EKS managed node group), is at version 0.37.0 from the Helm release `karpenter`. Its compatibility table covers Kubernetes 1.23 to 1.30, so the cluster is already two minors outside what this Karpenter supports, and Karpenter said so in its own log at 08:53 UTC on 2026-11-14. It still works today: by its log it launched 7 nodes in the last 24 hours, in about 61 seconds each at the median and 67 seconds at most, with no launch failure.

The one EC2NodeClass, `default`, uses `amiFamily: AL2` with no AMI selector, so new nodes boot the latest Amazon Linux 2 image for the cluster's version. Seven nodes that could be read run Amazon Linux 2 with cgroup v1. EKS's own upgrade insight for 1.33 reports an error for this: AWS stopped publishing EKS-optimised AL2 images on 2025-11-26, and there is none for 1.33.

What the audit found sound: no manifest or Helm release uses an API version that 1.33 removes (Pluto found 0; kubent found 0 but could not read 13 of its lists), and the only deprecated call the API server saw was 2 requests for `componentstatuses`. The rest of the upgrade is therefore mostly about the add-ons and the nodes, not the workloads.

### Why it comes about

The likely history is that the control plane was upgraded to 1.32 when the cluster was built or soon after, and Karpenter, which EKS does not upgrade, stayed at the version it was installed with. The EC2NodeClass still uses the `karpenter.k8s.aws/v1beta1` API of the 0.x line, which fits that picture. This is inferred from the versions; the release history would tell.

A Kubernetes minor is patched for about fourteen months upstream. EKS keeps it in standard support for fourteen months from its own release, then in extended support for twelve more at an extra cost, and at the end of extended support it upgrades the control plane by itself, at any time after the date and without asking. It upgrades only the control plane; nodes and add-ons such as Karpenter stay where they were. And the API server never skips a minor, so a cluster that waits has to cross each minor in turn.

Karpenter is installed and upgraded by the owner of the cluster, separately from the control plane. Each release supports a range of Kubernetes minors; 1.32 needs Karpenter 1.2 or later. Outside its range, Karpenter reports that it is not compatible, and a control plane upgraded further past that range leaves the autoscaler unable to prepare new nodes. Catching up is not one step: the CRDs are tied to the Karpenter version and Helm installs CRDs only on the first install, and some releases can only be reached through an intermediate one.

The AMI family is the other half. An EC2NodeClass names the image family new nodes boot from. 1.32 is the last minor for which EKS released AL2 images, so the day the cluster moves to 1.33 there is no image for `AL2` and no new node can start, whatever the Karpenter version. Until then, new nodes boot an image that no longer gets updates; Amazon Linux 2 itself ended support on 2026-06-30. Without a pinned version, every new image would make Karpenter replace all nodes through drift, by default 10% of the nodes at a time.

[ZenML](https://status.zenml.io/incidents/bnrlb8tck3v0) ran its production EKS cluster on an outdated Kubernetes version and AMI type. When the upgrade finally came it bundled several changes in one night, one of them removed IAM permissions from the worker nodes, and the workspaces were down for about eight hours until the node group was rebuilt. This cluster is in the same position: a version, an autoscaler and an image family that all have to move, and the longer they wait the more of them move at once.

### How to watch it

The mismatch is two version strings and one field, so it is read from the objects before an upgrade rather than alerted on after it. The symptom it would cause can be alerted on: pods pending while Karpenter creates no node.

```promql
sum(kube_pod_status_phase{phase="Pending"}) > 0
  and sum(increase(karpenter_nodeclaims_created_total[15m])) == 0
```

This cluster runs Loki with promtail, so where Karpenter's log reaches Loki the controller's own complaint can be alerted on too. Neither rule exists here; both have to be made.

```logql
count_over_time({namespace="karpenter"} |= "is not compatible with" [24h]) > 0
```

For the version itself, the Upgrade insights tab of the cluster in the EKS console and the AWS Health Dashboard list what blocks the next upgrade; the AL2 error above came from there.

### How it is solved

At the scale this cluster is run at, the upgrade becomes a written procedure, done in this order. First Karpenter, because it must support the version the cluster is on before anything else: move it from 0.37 to 1.x one minor at a time through the releases the upgrade guide requires, with the CRDs managed by the `karpenter-crd` chart so they move with each step, and the NodePools and the EC2NodeClass converted to the `v1` API on the way. Then the node image: change `default` to AL2023 with a pinned alias, and give the NodePools a disruption budget that allows no drift replacement in busy hours, so the switch replaces nodes when the team chose it. Then the control plane, one minor at a time from 1.32 to the version you want, each followed by the managed add-ons and the nodes. In return, nodes keep launching after each upgrade, they run a supported image, patches arrive again and extended support billing stops. The cost is engineer time for each step and a non-production cluster to rehearse on, if one exists.

The shape of the node class and the budget, as an example and not as something to apply as it stands:

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiSelectorTerms:
    - alias: al2023@v<a release that includes 1.32 images>
---
apiVersion: karpenter.sh/v1
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

Where to change it: Karpenter is the Helm release `karpenter` in the namespace `karpenter`. Nothing in the cluster marks the EC2NodeClass `default` as managed by Argo CD or Helm; it carries the annotation of `kubectl apply`, so change it where it is declared, in the manifest it was applied from. The cluster version is changed in the AWS account.

What to be careful of when applying it: the example shows only the fields that change, and the existing `role`, subnet and security group selectors stay; the budget goes into each of the four NodePools. The pinned version has to be a release that has images for the cluster's current minor, or no node can launch. Switching the node class replaces every node Karpenter launched, and fourteen production workloads run a single replica, so each of them stops while its pod moves; four production Deployments also keep all their replicas on one node. The NodePools allow 10% of nodes to be disrupted at a time, so nodes are replaced a few at a time, not all at once. AL2023 uses cgroup v2, so anything that reads cgroup v1 files, old Java 8 builds among them, needs a look before the switch. The Kafka broker and the eight databases run as single-replica StatefulSets on EBS volumes that live in one zone each, so each is down while its pod moves and needs a node in that zone.

At a larger scale, upgrades happen three times a year as routine: release notes reviewed, insights cleared, removed APIs scanned in CI, a non-production cluster upgraded first, and the image pin promoted from a lower environment. When several minors must be crossed at once, building a new cluster on the target version and moving the workloads is weighed against a chain of in-place upgrades.

### Evidence

| What | Value | Source |
|---|---|---|
| Control plane version | v1.32.13-eks-577a51e | `platform.k8s-version-eol` finding |
| End of EKS standard support | 2026-03-23, 237 days ago | `platform.k8s-version-eol` finding |
| Upstream end of life | 2026-02-28 | `platform.k8s-version-eol` finding |
| Support type, end of extended support | EXTENDED, 2027-03-23 | `eks.extended-support` finding |
| Karpenter version, supported range | 0.37.0, 1.23 to 1.30 | `scaling.karpenter` |
| Karpenter incompatibility in its log | 1 line, 2026-11-14 08:53 UTC | `logs.signatures` finding |
| Nodes launched in 24 h, median and longest time | 7, 61 s, 67 s | `scaling.karpenter.latency_24h` |
| EC2NodeClass AMI family, pinned | AL2, no | `karpenter.ec2nodeclass-al2` finding |
| Nodes on Amazon Linux 2 with cgroup v1 | 7 | `node.cgroup-v1` findings |
| Manifests using APIs removed in 1.33 | 0 (kubent could not read 13 lists) | `hygiene.deprecated` |
| Deprecated API calls seen | componentstatuses v1, 2 | `metrics.apiserver_requested_deprecated_apis` |
| NodePool disruption budget | 10% of nodes, all four NodePools | `scaling.karpenter.nodepools` |

### Further reading

- [Karpenter: Compatibility](https://karpenter.sh/docs/upgrading/compatibility/): the matrix of Kubernetes minors and the Karpenter release each one needs.
- [Karpenter: Upgrade Guide](https://karpenter.sh/docs/upgrading/upgrade-guide/): the per-release notes, including the releases that must be passed through on the way from 0.37.
- [Amazon EKS: Understand the Kubernetes version lifecycle on EKS](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html): the EKS calendar, what extended support includes and what the automatic upgrade does and does not touch.
- [Amazon EKS: Guide to EKS AL2 and AL2-Accelerated AMIs transition features](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html): the AL2 end dates and what changes for workloads on AL2023, cgroup v2 above all.
- [Karpenter: Disruption](https://karpenter.sh/docs/concepts/disruption/): how drift is detected and how budgets limit when and how many nodes are replaced.
- [Amazon EKS best practices: Cluster Upgrades](https://docs.aws.amazon.com/eks/latest/best-practices/cluster-upgrades.html): the order of an in-place upgrade and the tools that find removed APIs before it.

## 5. Four production load balancer health checks filter nothing

**Why this one.** When a pod of these four services breaks, the load balancer keeps sending users to it, because its health check already marks every target as failed and has stopped telling good from bad.

### What is the matter

Four target groups of the shared production ALB `k8s-lb-b18a4555d7` have no healthy target at all. The ALB checks each target on the path `/` and expects the code 200, and each answers something else.

- `prod-app-t/app-t-backend`, port 3000: the one target answers 404. It served 6,089 requests in the last 24 hours.
- `prod-app-z-backend/app-z-backend`, port 8000: both targets answer 404. It served 6 requests.
- `prod-app-y/app-y-frontend`, port 3003: the one target answers 307, a redirect. It served 820 requests.
- `prod-app-v/app-v-frontend`, port 3000: the one target answers 307. It served 9,936 requests, 30 of them with a 5xx from the target.

Over the last 24 hours the lowest healthy count of each group was 0 and the highest unhealthy count equalled all its targets. The services work for users only because of how an ALB behaves when every target of a group is unhealthy: it fails open and routes to all of them. So these services are up, but their health check does nothing.

The two backends already have a health endpoint: both declare `readinessProbe` and `livenessProbe` on `/health`. The ALB simply asks for `/` instead. The two frontends declare no probe at all, and their `/` answers with a redirect.

How far the effect reaches: three of the four run a single replica, so for them a filtering health check would not keep users away from a broken pod anyway, because there is no other pod to send them to. It matters most for `app-z-backend` with two replicas, and for every service once it is scaled out. What the audit cannot tell is whether any user request actually reached a broken pod through this path.

### Why it comes about

The target groups carry the AWS Load Balancer Controller's default health check of `/` with success code 200, which means the Ingresses set no health check path of their own. The applications answer `/` with 404 or a redirect, so the defaults and the applications never matched. That is confirmed by the target group settings and the reason codes the ALB reports.

The controller turns each Ingress into an ALB, a target group per Service, and listener rules. Here the target type is `ip`, so the ALB sends traffic straight to the pod addresses. The ALB health check is its own, separate from Kubernetes readiness: Kubernetes asks the pod on `/health` and finds it Ready, the ALB asks `/`, gets 404, and after two failures every 15 seconds marks the target unhealthy. A pod can be Ready to Kubernetes and failed to the ALB at the same time, which is the state of all four.

The ALB routes only to healthy targets. When some are unhealthy, the load moves to the rest; when all are unhealthy, it fails open and routes to all of them. That rule keeps a service up when its health check is wrong, and it also hides that the check is wrong: nothing breaks, and the target group shows red in the console where nobody looks. The day one pod of `app-z-backend` truly fails, the ALB cannot tell it from the healthy one and keeps sending it half of the traffic.

### How to watch it

The CloudWatch metric `UnHealthyHostCount` of each target group shows the state, and AWS recommends an alarm on its Minimum statistic above zero for more than one data point, because the Minimum is above zero only when every node of the load balancer sees the target as unhealthy. `HealthyHostCount` shows how many targets carry the load, and `UnhealthyRoutingRequestCount` counts the requests sent through the fail-open path, which on these four groups is all of them. Whether such alarms exist in this account was not checked.

```text
AWS/ApplicationELB UnHealthyHostCount, statistic Minimum,
dimensions LoadBalancer + TargetGroup, threshold > 0 for 2 data points
```

For one target group, the reason code per target says why:

```bash
aws elbv2 describe-target-health --target-group-arn <arn>
```

### How it is solved

At the scale this cluster is run at, give every Ingress a health check the application answers. For the two backends that is their existing `/health` endpoint; for the two frontends it is a path that returns 200 without a redirect, which may need a small route in the application. Then add one CloudWatch alarm on `UnHealthyHostCount` per target group, so a wrong health check shows the day it appears. In return, the ALB stops sending requests to a broken pod as soon as there are two of them, and a broken check becomes visible. The cost is a few annotations per Ingress and, for the frontends, a route in the code.

Since the target type is already `ip`, the namespaces can also be labelled for the pod readiness gate, so a rollout waits until the new pod is healthy in the target group before the old one goes. That only helps once the health check passes.

The shape of the annotations on an Ingress, as an example and not as something to apply as it stands:

```yaml
metadata:
  annotations:
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/success-codes: '200'
```

Where to change it: each service is managed by its own Argo CD application from the repository `https://github.com/example-org/iac`, revision `main`, with selfHeal on: `app-t-prod` at `apps/prod/app-t`, `app-z-backend-prod` at `apps/prod/app-z-backend`, `app-y-prod` at `apps/prod/app-y` and `app-v-prod` at `apps/prod/app-v`. A change made to the Ingress in the cluster is reverted, so make it in the repository.

What to be careful of when applying it: changing the health check path does not restart any pod. But the moment the check starts to work, the fail-open state ends, and a target that really fails the new check is taken out of rotation. For the three single-replica services a wrong new path changes nothing, because their one target fails and the ALB stays open to it. For `app-z-backend` with two targets it matters: if one pod passes the new check and the other does not, all traffic goes to the one that passes. The two frontends have no `/health` route today, so the path in the example does not fit them until such a route exists. The target groups keep a deregistration delay of 300 seconds, so a target removed while serving drains slowly.

At a larger scale, the readiness gate is on in every application namespace, the controller runs with a PodDisruptionBudget and its own metrics scraped, and health checks are part of the service template, so no Ingress is created without one.

### Evidence

| What | Value | Source |
|---|---|---|
| Target groups with no healthy target | 4 | `traffic.alb.unhealthy_target_groups` |
| Health check path and expected code | `/`, 200 | `traffic.alb.target_groups` |
| `app-t-backend` answer, targets, requests 24 h | 404, 0 of 1 healthy, 6,089 | `traffic.alb.target_groups` |
| `app-z-backend` answer, targets, requests 24 h | 404, 0 of 2 healthy, 6 | `traffic.alb.target_groups` |
| `app-y-frontend` answer, targets, requests 24 h | 307, 0 of 1 healthy, 820 | `traffic.alb.target_groups` |
| `app-v-frontend` answer, targets, requests 24 h, target 5xx | 307, 0 of 1 healthy, 9,936, 30 | `traffic.alb.target_groups` |
| Lowest healthy count and highest unhealthy count over 24 h | 0, equal to all targets in each group | `traffic.alb.unhealthy_target_groups` |
| Probe path of the two backends | `/health` | objects `deployments prod-app-t/app-t-backend`, `prod-app-z-backend/app-z-backend` |
| Replicas | 1, 2, 1, 1 | the same deployments |
| Target type, deregistration delay | ip, 300 s | `traffic.alb.target_groups` |

### Further reading

- [Elastic Load Balancing: Health checks for Application Load Balancer target groups](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html): the health check settings, the fail-open rule and the reason codes a target reports.
- [Elastic Load Balancing: CloudWatch metrics for your Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html): which statistic of `UnHealthyHostCount` to alarm on and what the target group health metrics count.
- [AWS Load Balancer Controller: Pod readiness gate](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/deploy/pod_readiness_gate/): why a small rolling update can empty a target group, and the conditions under which the gate is injected.

## The next largest problems

- **The cluster API endpoint is open to the whole internet.** The public endpoint of `app-u-cluster-eks` allows `0.0.0.0/0`, so the API server answers anyone; only IAM authentication stands between a leaked credential and the cluster. Severity: high.
- **NetworkPolicies are stored but not enforced.** Three NetworkPolicies exist in `prod-app-t`, `prod-app-x` and `prod-app-r`, but the VPC CNI node agent runs with `--enable-network-policy=false` and no PolicyEndpoint exists, so all traffic passes as if they were not there. Severity: high.
- **The app-ad VPN container can administer the node network.** The `tailscale` container of `prod-app-z-backend/app-ad` has `NET_ADMIN`, mounts `/dev/net/tun` from the host and may run as root, so whoever takes over that container can change networking on its node. Severity: high.
- **Alertmanager and Loki keep their data on emptyDir.** Both run one replica and store their data in an emptyDir volume, so a restart loses Alertmanager's silences and notification state and all logs Loki holds. Severity: high.
- **No alert covers a container killed for memory.** Of 157 alert rules none fires on an OOM kill, so no rule would have fired for the Prometheus restart of 2026-11-14. Severity: high.
- **A system node has already run out of pod IP addresses once.** On `node-1-116`, a `t8i.small` with three of three network interfaces attached, the VPC CNI answered "no available IP" once since it started; it now uses 6 of 9 pod addresses. Severity: high.

## Since the previous report

There is no earlier run to compare with, so this covers only what this run collected.

## Each area in one line

| Area | What |
|---|---|
| resources | Prometheus uses 73% of its 1536Mi memory limit and had 34% of its CPU periods throttled over the day; most other containers request far more CPU than they use. |
| scaling | Karpenter launches nodes in about a minute, but the scheduler logged 91 placement failures for production pods in a day while nodes were being replaced, and 20 serving Deployments have no HPA. |
| observability | 157 alert rules exist but none watches a user symptom, no rule covers OOM kills, and Alertmanager and Loki lose their data on restart. |
| traffic | Kafka is reachable from the internet without a source limit, and four production target groups have no healthy target because the ALB checks / and the applications answer it with 404 or a redirect. |
| resilience | No backup tool, snapshot policy or backup CronJob exists; 14 production workloads run one replica and 10 keep all replicas in one zone. |
| hygiene | Several images use mutable tags such as latest, and one EKS upgrade insight is open. |
| storage | Every production database volume uses the reclaim policy Delete with no snapshot, and the CSI snapshot API is not installed. |
| security | The API endpoint is open to 0.0.0.0/0, NetworkPolicies are not enforced, a Neo4j password is written in plain text and one VPN container has NET_ADMIN. |
| cost | Extended support for 1.32 is being billed, and requested capacity is well above what is used. |
| tenancy | Five production namespaces lack a boundary such as a quota or a NetworkPolicy, and development workloads share nodes with production. |
| node OS | Seven nodes run cgroup v1 on Amazon Linux 2, and two nodes could not be read because they are not registered with SSM. |
| platform | Kubernetes 1.32 is 237 days past EKS standard support, Karpenter 0.37 supports only up to 1.30, and the node class still uses AL2. |

## Limits of this run

**Not judged because the cluster does not hold the data**

- Two nodes, node-1-117 and node-2-60, are not registered with SSM, so their operating system and kernel log were not read.
  - Weaker for it: Whether the kernel itself killed processes on the node that runs Prometheus cannot be told.
  - To see it: Attach AmazonSSMManagedInstanceCore to the node IAM role used by those nodes.
- The configuration of the external Kafka listener (protocol and authentication) is not in any object this audit reads.
  - Weaker for it: Problem 2 cannot say whether a stranger reaching port 9094 must authenticate.
  - To see it: Read the listener settings in the values of the Helm release kafka in middleware.

**Not read by kubegap yet**

- 8 components were read only through their objects and metrics; kubegap has no checks of their own for them: actions-runner-controller, external-dns, kube-state-metrics, metrics-server, node-exporter, prometheus-operator, promtail, victoria-metrics.
  - Weaker for it: a fault inside one of these components is not in this report.
- The collection stopped at one of its own limits and read only part of: `core.component-logs` (argocd: argocd/argocd-application-controller, argocd: argocd/argocd-applicationset-controller, argocd: argocd/argocd-notifications-controller, argocd: argocd/argocd-repo-server, ebs-csi: kube-system/ebs-csi-controller, external-dns: kube-system/external-dns, external-secrets: external-secrets/external-secrets, external-secrets: external-secrets/external-secrets-cert-controller, loki: monitoring/loki-stack).
  - Weaker for it: a number counted from these is a lower bound, and the oldest lines of the day or the rest of a list are not in this report.

**What you answered not to read at the first-run questions**

- none

## Numbers

Severity is for a cluster run at scale medium.

1 findings whose severity the analysis changed are counted at the changed level.

No earlier full run to compare with.

| Severity | fail | warn |
|---|---|---|
| critical | 1 | 0 |
| high | 22 | 27 |
| medium | 105 | 153 |
| low | 15 | 126 |

Checks behind each entry:

- Prometheus was killed for running out of memory: `resources.oomkilled.*`, `resources.oomkilled-repeated.*`, `resources.cpu-throttling.*`, `prometheus.memory-pressure.*`
- Production pods could not be scheduled 91 times in one day: `controlplane.scheduler-unschedulable.*`
- The production databases have no backup: `resilience.no-backup.*`, `eks.no-backup-policy.*`
- Kafka accepts connections from the whole internet: `traffic.db-exposed.*`
- The production Neo4j password is written into its manifest: `security.plaintext-secret-env.prod-app-z-backend/statefulset/app-z-neo4j:neo4j`
- Kubernetes 1.32 is past support and Karpenter 0.37 does not support it: `platform.k8s-version-eol.*`, `platform.karpenter-version-compat.*`, `karpenter.ec2nodeclass-al2.*`, `logs.signatures.karpenter.version-unsupported`, `eks.extended-support.*`, `hygiene.eks-upgrade-insight.*`, `node.cgroup-v1.*`
- Four production load balancer health checks filter nothing: `traffic.alb-unhealthy-targets.*`

Details and every table: [`report-details.md`](report-details.md) · kubegap 0.2.0, rubric 0.1.94 · snapshot `~/.kubegap/snapshots/<context>/2026-11-15T02-09-39`
