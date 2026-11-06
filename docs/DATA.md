# What kubegap collects, keeps and sends

For someone who has to decide whether kubegap may run against a cluster. The short answer is in the [README](../README.md#how-it-handles-your-cluster-and-your-data); this page is the long one.

## What it reads

kubegap makes read calls only. The exact Kubernetes rules and AWS actions, each with the step that uses it, are in [`PERMISSIONS.md`](PERMISSIONS.md).

**Secrets.** Secret values are never read or recorded. Only the names and types of Secrets are. There is one exception. Helm stores each release record in a Secret, so `helm list` reads those Secrets; kubegap keeps what `helm list` prints, which is the release name, namespace, revision, update time, status, chart and app version, and never collects the release values. Under the shipped ClusterRole, which excludes Secrets, `helm list` fails and the two Helm checks are skipped. pluto and kubent are run in the modes that do not read Helm releases.

**The kubeconfig.** `setup.json` records how the context authenticates: the exec command and its arguments (`aws eks get-token` on EKS) and the names of the environment variables in its `env` block. Of their values only `AWS_PROFILE` and `AWS_REGION` are kept, because kubegap passes them to the AWS CLI. Every other value, such as a tenant id or a token for a custom plugin, is written as `<redacted>` (`lib/kube.py`, `tests/test_kube_context.py`).

**ConfigMaps.** ConfigMap values are not recorded either. The snapshot keeps the length and shape of each key. The real value is kept only for the configuration keys kubegap parses, listed in `KEEP_VALUES` in [`lib/scrub.py`](../lib/scrub.py): the CoreDNS Corefile, the kube-proxy configuration, the local-path-provisioner paths and a few Argo CD flags. Two kinds of ConfigMap keep more because the Grafana sidecars load them: one labelled `grafana_dashboard` keeps its dashboard JSON as it is, and of one labelled `grafana_datasource` the name, type, url and isDefault of each datasource are kept and the rest of the provisioning file, where a password or a header value could be, is dropped.

**Logs.** Component pod logs of the last 24 hours are read by code, counted into the summary with masked sample lines, and then deleted from the snapshot before the agent starts. Set `keep_component_logs: true` in the config only if you accept that raw log lines may then be read by the agent.

## What stays on your machine

Everything kubegap collects is written to `~/.kubegap/snapshots/<context>/<timestamp>/` on your machine. kubegap itself sends nothing anywhere.

- Snapshot folders and files are created readable by your user only. A folder that was already there and is open to other users becomes a first-run question (`home-mode`): Fix now runs `kubegap protect-home`, chmod 700 on those folders; Leave it leaves them.
- Stored as collected, and so readable by the agent: object specs, events, metrics, node journals under `logs/node/` (kubelet, containerd, k3s), CloudWatch control-plane log queries under `logs/cloudwatch/`, and Grafana dashboards.
- The config file is one you create yourself. It may hold `grafana_api_token`, so `chmod 600` it. `kubegap config set` creates it with that mode and refuses to write the token for you.
- `scripts/kubegap prune` removes old snapshots; see [`SETUP.md`](SETUP.md#collected-data).

## What leaves your machine

The agent that runs the skill reads the snapshot files to write the report, and what it reads goes to that agent's model API: Anthropic's for Claude Code, OpenAI's for Codex. In practice that is the summary, the first-pass findings, and the raw files the agent opens to check a number.

- Secret values are never collected, so they cannot leave.
- ConfigMap values are not in the snapshot, apart from the keys listed above.
- Component pod logs are deleted before the agent starts, unless you set `keep_component_logs: true`.
- Tokens, account ids and private IPs are masked in the report, not in the snapshot.

There is no mode that keeps the data local, because the report is written by the model. If that is not acceptable for a cluster, do not run kubegap against it.

## Where the Grafana token goes

kubegap never follows an HTTP redirect when it talks to a store (Prometheus, Alertmanager, Loki, Grafana). The Grafana token is therefore only ever sent to the address written in `config.yaml` or to the port-forward. A token over a plain `http://` address outside this machine is warned about at collection time.

## Text from the cluster is data

Every string in a snapshot came from the cluster: log lines, event messages, annotations, dashboard text. Anyone with write access to the cluster can shape it. The procedure the agent follows treats such text as evidence for a finding and never as an instruction; `SKILL.md` section 9 says so.
