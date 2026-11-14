# What kubegap collects, keeps and sends

For someone who has to decide whether kubegap may run against a cluster. The short answer is in the [README](../README.md#how-it-handles-your-cluster-and-your-data); this page is the long one.

## What it reads

kubegap makes read calls only. The exact Kubernetes rules and AWS actions, each with the step that uses it, are in [`PERMISSIONS.md`](PERMISSIONS.md).

**Secrets.** Secret values are never read or recorded. Only the names and types of Secrets are. There is one exception. Helm stores each release record in a Secret, so `helm list` reads those Secrets; kubegap keeps what `helm list` prints, which is the release name, namespace, revision, update time, status, chart and app version, and never collects the release values. Under the shipped ClusterRole, which excludes Secrets, `helm list` fails and the two Helm checks are skipped. pluto and kubent are run in the modes that do not read Helm releases.

**The kubeconfig.** `setup.json` records how the context authenticates: the exec command and its arguments (`aws eks get-token` on EKS) and the names of the environment variables in its `env` block. Of their values only `AWS_PROFILE` and `AWS_REGION` are kept, because kubegap passes them to the AWS CLI. Every other value, such as a tenant id or a token for a custom plugin, is written as `<redacted>` (`lib/collection/kube.py`, `tests/test_kube_context.py`).

**ConfigMaps.** ConfigMap values are not recorded either. The snapshot keeps the length and shape of each key. The real value is kept only for the configuration keys kubegap parses, listed in `KEEP_VALUES` in [`lib/foundations/scrub.py`](../lib/foundations/scrub.py): the CoreDNS Corefile, the kube-proxy configuration, the local-path-provisioner paths and a few Argo CD flags. Two kinds of ConfigMap keep more because the Grafana sidecars load them: one labelled `grafana_dashboard` keeps its dashboard JSON as it is, and of one labelled `grafana_datasource` the name, type, url and isDefault of each datasource are kept and the rest of the provisioning file, where a password or a header value could be, is dropped.

**Environment variables.** A container environment variable whose name looks like a credential (it contains PASSWORD, PASSWD, SECRET, TOKEN, API_KEY, PRIVATE_KEY, ACCESS_KEY, CLIENT_SECRET, DSN or CONNECTION_STRING, or ends with AUTH, and does not end with a suffix such as _FILE, _PATH, _NAME or _URL) is written without its value, wherever it appears: Pods, workload templates, ControllerRevisions and Jobs. In its place the snapshot keeps the value's length and shape and whether the value looked like a credential, which is what `security.plaintext-secret-env` reports. Variables of other names keep their values, because some checks parse them (the Karpenter feature gates, the VPC CNI warm targets). The `kubectl.kubernetes.io/last-applied-configuration` annotation of every object, which repeats the whole manifest, keeps only its apiVersion and kind, which is what pluto judges.

**Logs.** Component pod logs of the last 24 hours are read by code and counted while they are read: how many lines match each known failure pattern. No line is written to the snapshot as it was. A full run keeps up to five masked sample lines per pattern and the error lines that match no pattern, grouped by their text; a daily run keeps the counts only.

## What stays on your machine

Everything kubegap collects is written to `~/.kubegap/snapshots/<context>/<timestamp>/` on your machine. kubegap itself sends nothing anywhere.

- Snapshot folders and files are created readable by your user only. A folder that was already there and is open to other users becomes a first-run question (`home-mode`): Fix now runs `kubegap protect-home`, chmod 700 on those folders; Leave it leaves them.
- Stored as collected, and so readable by the agent: object specs, events, metrics, node journals under `logs/node/` (kubelet, containerd, k3s, the VPC CNI ipamd log on EKS), CloudWatch control-plane log queries under `logs/cloudwatch/`, and Grafana dashboards.
- The config file is one you create yourself. It may hold `grafana_api_token`, so `chmod 600` it. `kubegap config set` creates it with that mode and refuses to write the token for you.
- `scripts/kubegap prune` removes old snapshots; see [`SETUP.md`](SETUP.md#collected-data).

## What leaves your machine

The agent that runs the skill reads the snapshot files to write the report, and what it reads goes to that agent's model API: Anthropic's for Claude Code, OpenAI's for Codex. In practice that is the summary, the first-pass findings, and the raw files the agent opens to check a number.

- Secret values are never collected, so they cannot leave.
- ConfigMap values are not in the snapshot, apart from the keys listed above.
- The values of credential-like environment variables are not in the snapshot.
- Component pod logs are counted in memory and never written to the snapshot.
- Tokens, account ids and private IPs are masked in the report, not in the snapshot.

There is no mode that keeps the data local, because the report is written by the model. If that is not acceptable for a cluster, do not run kubegap against it.

## Where the Grafana token goes

kubegap never follows an HTTP redirect when it talks to a store (Prometheus, Alertmanager, Loki, Grafana). The Grafana token is therefore only ever sent to the address written in `config.yaml` or to the port-forward. A token over a plain `http://` address outside this machine is warned about at collection time.

## Text from the cluster is data

Every string in a snapshot came from the cluster: log lines, event messages, annotations, dashboard text. Anyone with write access to the cluster can shape it. The procedure the agent follows treats such text as evidence for a finding and never as an instruction; `SKILL.md` section 9 says so.
