# Connections and settings

You do not need this page to start. The basic audit runs when `kubectl get nodes` works, and the first run asks about the things beyond it ([README](../README.md#the-first-run)). This page is for when you want to know how kubegap reaches each thing, change a setting, check a connection by hand, or run with the least access.

kubegap has no credential store. It uses what is already on your machine: the kubeconfig, the AWS CLI, your SSH setup.

## What kubegap connects to

| Connection | Where kubegap takes it from | You have to do something when |
|---|---|---|
| Kubernetes API | the kubeconfig's current context, or `--context <name>` | never, if `kubectl get nodes` works |
| AWS, on EKS only | `aws_profile` and `aws_region` in the config, else the `AWS_PROFILE` of the kubeconfig's `exec` block, else the AWS CLI default | the profile kubectl uses is not the one you want the audit to use |
| Prometheus, Alertmanager, Loki, Grafana | found as Services in the cluster and reached through a port-forward | one of them runs outside the cluster: the first run asks for its address |
| apiserver metrics | the `job` label of the apiserver scrape, detected from `apiserver_request_total` | your scrape config uses a job name kubegap does not recognize: set `apiserver_job` |
| Grafana datasource and dashboard lists | the ConfigMaps the Grafana sidecars load (labels `grafana_dashboard`, `grafana_datasource`), no token needed; `grafana_api_token` in the config for the dashboards made in Grafana itself | Grafana counts more dashboards than the ConfigMaps hold: the first run says how many and shows how to make a token |
| Inside the nodes, EKS | SSM `send-command` with the document `kubegap-node-read` | once per account: the first run offers to upload the document |
| Inside the nodes, k3s and bare metal | SSH to each node's InternalIP with the user and key of your `~/.ssh/config` | a node is not reachable that way: the first run asks for the address |
| Inside the nodes, GKE, AKS and other managed nodes | `kubectl exec` into a DaemonSet you apply | you want node checks there: the first run shows the commands |
| Optional tools | your `PATH` | a tool is missing: the first run offers to install it |

Without a connection, only the checks that need it are left out, and the report says so. Nothing else stops.

## The first-run questions

`kubegap setup` looks at the cluster and the machine and lists what is missing as questions. `/kubegap` runs it for you and shows each question as a choice. Every question explains what it is for, says what it adds, and can be skipped.

| Question | Asked when | Choices |
|---|---|---|
| `home-mode` | a folder under `~/.kubegap` is readable by other users of the machine (created by an older kubegap or widened by hand) | Fix now (`kubegap protect-home`, chmod 700) · Leave it |
| `tools` | optional tools are not installed | Install all · Skip · or type the names to install only those |
| `ssm-document` | EKS, and the SSM document is missing or older than the one shipped with kubegap | Upload · Skip |
| `node-ssh` | k3s, RKE2 or an unrecognized platform, the config names no node access (`ssh:` block or `node_access`), and the node DaemonSet is not running | Check SSH now · Skip. If nodes do not answer: Accept host keys or Check again · Use the rest · Skip · or type an address per node |
| `node-daemonset` | GKE or AKS, and the node DaemonSet is not running | Show the commands · Skip |
| `grafana-token` | Grafana was found, no token is set, and either no dashboard or datasource ConfigMap exists for the sidecars or Grafana counts more dashboards than those ConfigMaps hold | Show how · Skip |
| `stores` | Prometheus, Alertmanager, Loki or Grafana has no Service in the cluster. Loki is left out when the log shipper's configuration (fluent-bit, fluentd, promtail) says the logs go elsewhere; the report then says where | Not installed · Ask next time · or type the address |

An answer is remembered per cluster in `~/.kubegap/snapshots/<context>/answers.json`. A skipped question is not asked again, and the report names what was skipped. `/kubegap setup` asks everything again.

By hand, the same thing:

```bash
scripts/kubegap setup --context <name>               # the check, then the open questions
scripts/kubegap questions --context <name> --all     # every question, including the answered ones
scripts/kubegap answer --context <name> node-ssh skip
scripts/kubegap answer --context <name> --forget     # forget every answer of this cluster
```

## Inside the nodes

Disk, inodes, the kernel log, the kubelet configuration and the container runtime are not visible through the Kubernetes API. kubegap reads them on the node with a fixed list of read commands, [`deploy/node-access/COMMANDS.md`](../deploy/node-access/COMMANDS.md). This is the only part that may need something prepared outside your machine. A full run uses it for the node checks. A daily run uses it only to read the `/metrics` of a component that Prometheus does not scrape and the API server proxy cannot reach.

**EKS.** Nodes are read through SSM. The commands are fixed in one SSM document, [`deploy/permissions/ssm-document.yaml`](../deploy/permissions/ssm-document.yaml), which has to exist in the account. The first run offers to upload it. That one call uses your current credentials and needs `ssm:CreateDocument`, `ssm:UpdateDocument`, `ssm:UpdateDocumentDefaultVersion` and `ssm:ListDocumentVersions`; the audit itself does not need them. The node IAM role must include `AmazonSSMManagedInstanceCore`. The EKS-optimized AMI already runs the SSM agent.

**k3s, RKE2, bare metal, kubeadm.** Nodes are read over SSH, and only after you decided so: you chose "Check SSH now" at the first-run question, or ran `scripts/kubegap nodes` yourself, or the config has an `ssh:` block or `node_access: ssh`. Until then kubegap makes no SSH connection. kubegap connects to each node's InternalIP with the user and key from your `~/.ssh/config`, without a password prompt, and only to nodes whose host key is already in your `~/.ssh/known_hosts`. When that does not work the first run tells you why per node and takes the fix as an answer:

- the node's InternalIP is not reachable from your machine, for example on an overlay network such as Tailscale: give an address that is, as `ssh.hosts.<node>`;
- the host key is not known yet: log in once by hand, or let ssh store first-seen keys with `ssh.accept_new_hosts: true`;
- the login is refused: set `ssh.user` and `ssh.key`.

Some reads need more than a plain login. The user needs the log-reading groups, and an optional sudoers file unlocks the remaining root-only reads: [`deploy/node-access/README.md`](../deploy/node-access/README.md). kubegap does not change anything on a node; you add those yourself.

**GKE, AKS, managed nodes with neither SSM nor SSH.** Apply [`deploy/node-access/daemonset.yaml`](../deploy/node-access/daemonset.yaml), whose image is pinned by digest, and [`deploy/permissions/role-daemonset-exec.yaml`](../deploy/permissions/role-daemonset-exec.yaml). kubegap finds the pods on the next run and reads each node through `kubectl exec`. The pod runs privileged; delete the namespace `kubegap` after the audit if you do not want it to stay. kubegap never applies it for you.

Check node access at any time, also before the first collection:

```bash
scripts/kubegap nodes --context <name>
```

It reads the node list from the cluster, sends `uname` and `hostname` to every node, and prints per node whether it answered and, over SSH, which privileged reads are allowed.

## Optional tools

helm, krr, polaris, pluto and kubent are looked up on your `PATH`. On EKS so is aws, on SSH platforms ssh. `kubegap setup` lists the missing ones with the checks each one feeds, and the first-run question offers to install them; `install_tools: never` in the config skips that question and installs nothing. The table says what each tool feeds, in which mode its step runs, where an install lands and what the report says without it. It is generated by `scripts/kubegap tools --markdown` from `lib/tools.py` and the check catalog, and a test keeps it current.

<!-- tools-table:begin -->
| Tool | What it does | Checks that need it | Mode | Install method and location | Without it |
|---|---|---|---|---|---|
| aws | EKS, EC2, SSM and CloudWatch queries (needed only for the EKS profile) | eks.* (11), ecr.* (8), cost.idle-compute-high, cost.request-waste, cost.on-demand-in-spot-pool, cost.unused-eip, cost.idle-load-balancer, cost.idle-node, controlplane.scheduler-unschedulable, controlplane.webhook-call-failures, controlplane.controller-error-repeat, controlplane.apiserver-slow-traces, controlplane.authenticator-failures, controlplane.etcd-slow, node.* (26, full mode) | daily and full; ECR, the control-plane logs, the nodes and the pricing and cost data in full only | Homebrew `awscli` → on failure: the pinned release 2.39.3 from awscli.amazonaws.com, sha256 + OpenPGP signature checked, into `.tools/bin/`, linux only | the EKS, ECR and cost checks are not collected; the control-plane log checks and the node checks say so in the report |
| helm | Helm release status and age (reads release records, which Helm stores in Secrets) | hygiene.helm-release-not-deployed, hygiene.helm-release-stale | full | Homebrew `helm` → on failure: the pinned release v4.3.1 from get.helm.sh, sha256 checked, into `.tools/bin/` | those checks are reported as tool missing |
| krr | Resource request recommendations (Robusta KRR, Prometheus-based) | resources.krr-recommendation | full | a Python virtualenv of its own, `.tools/krr-venv/`, from `deploy/krr-requirements.txt` (a sha256 per file) → on failure: Homebrew `robusta-dev/krr/krr` (third-party tap) | those checks are reported as tool missing |
| polaris | Static manifest audit and lightweight security checks | hygiene.polaris-reliability-danger, security.polaris-security-danger | full | the pinned release v10.2.6 from FairwindsOps/polaris, sha256 checked, into `.tools/bin/` → on failure: Homebrew `FairwindsOps/tap/polaris` (third-party tap) | those checks are reported as tool missing |
| pluto | Deprecated API detection | hygiene.deprecated-api | full | the pinned release v5.24.5 from FairwindsOps/pluto, sha256 checked, into `.tools/bin/` → on failure: Homebrew `FairwindsOps/tap/pluto` (third-party tap) | those checks skip because their input is not read (never a pass) |
| kubent | Deprecated API detection (complements Pluto) | hygiene.deprecated-api | full | Homebrew `kubent` → on failure: the pinned release 0.7.3 from doitintl/kube-no-trouble, sha256 checked, into `.tools/bin/` | those checks skip because their input is not read (never a pass) |
| ssh | Small k3s cluster node access (small k3s cluster profile) | node.* (26, full mode) | full | Included by default on macOS and most Linux. Minimal images (slim containers) may lack it: distro package openssh-client | the node checks are reported as not collected (no node access) |
<!-- tools-table:end -->

An install goes through Homebrew when it is there. Otherwise kubegap downloads the release binary of a version pinned in `lib/tools.py`, compares it with the sha256 pinned next to it, and puts it in `.tools/bin/` inside the kubegap folder only when the digest matches. polaris and pluto come from a third-party tap, so for those two the pinned download goes first. krr is installed into its own Python virtualenv from `deploy/krr-requirements.txt`, which pins every package it needs with a sha256 per file (`pip install --require-hashes`); that virtualenv goes before the third-party tap formula. On Linux the aws CLI zip is also checked against the AWS CLI Team's OpenPGP signature when `gpg` is installed (the key is `deploy/aws-cli-public-key.asc`); without gpg the sha256 pin alone decides and the install says so. Nothing asks a publisher what is newest during an install; `scripts/kubegap setup --check-tool-updates` does that and prints the material of the next pin.

## The config file

`~/.kubegap/config.yaml` is optional. Without it kubegap uses the current kube context and finds everything else. Every key is listed with a comment in [`config.example.yaml`](../config.example.yaml).

You do not have to open the file for the common keys:

```bash
scripts/kubegap config set language ko --dry-run     # prints the lines that would change, writes nothing
scripts/kubegap config set language ko
scripts/kubegap config set ssh.hosts.node-1 100.64.0.11
scripts/kubegap config set prometheus_url http://prometheus.example.internal:9090
```

It keeps your comments, the order of the file and its line ends, writes through a link if the file is one, creates the file readable by you only, and refuses a value of the wrong shape. Keys it sets: `language`, `mode`, `node_access`, `install_tools`, `ssm_document`, `confirm_context`, the four `<store>_url` keys, `ssh.user`, `ssh.key`, `ssh.port`, `ssh.accept_new_hosts` and `ssh.hosts.<node>`. It refuses `grafana_api_token` on purpose: a token on a command line an agent runs has already left your machine, so add that one line in your own editor and `chmod 600` the file.

The keys that answer a first-run question for good:

| Key | Effect |
|---|---|
| `language: en` or `ko` | the report language is not asked |
| `context: <name>` with `confirm_context: false` | the cluster is not asked |
| `install_tools: always` or `never` | tools are installed, or left out, without asking |
| `ssm_document: always` or `never` | the SSM document is uploaded, or left out, without asking |
| `node_access: none` | no node is contacted and no node question is asked |
| `prometheus_url`, `alertmanager_url`, `loki_url`, `grafana_url` | that store is read from the address |
| `grafana_api_token` | the Grafana lists are read |

**What is read without a token.** The Grafana chart's sidecars load dashboards and datasources from ConfigMaps labelled `grafana_dashboard` and `grafana_datasource`; kube-prometheus-stack ships its dashboards that way. kubegap keeps those ConfigMaps in the snapshot (the dashboard JSON as is; of a datasource file only name, type, url and isDefault per entry, never a password or a header) and takes the two lists and the alert-metric-without-dashboard comparison from them. Grafana's own metric `grafana_stat_totals_dashboard`, read from its `/metrics` endpoint through the same port-forward (no login needed) or from a Prometheus that scrapes Grafana, says how many dashboards exist in all; when that is more than the ConfigMaps hold, the difference was made in Grafana itself and the first-run question asks for a token with those numbers. kubegap never reads the Grafana admin password.

Other things the file holds: `mode: full` to make full the default, `profile` and `namespace_profiles` to change what kubegap expects of a cluster or a namespace, `suppress` and `overrides` to silence a check or change a threshold, `retention` and `snapshots_root` for the collected data, `keep_component_logs`, `apiserver_job`.

## Collected data

Every run writes one folder, `~/.kubegap/snapshots/<context>/<timestamp>/`, with the collected files and the two report files, and compares itself with the previous run of the same mode. Folders and files are created readable by your user only. A full snapshot is about 40 MB.

```bash
scripts/kubegap prune --context <name> --keep-daily 14 --keep-full 4 --dry-run
```

`prune` removes older snapshots and deletes without asking, so look at `--dry-run` first. With `retention` set in the config a bare `prune` already removes folders. The latest daily and the latest full always stay.

## Run with the least access

For a first run before security approval, or on a cluster where you may read only what you can justify line by line:

```yaml
# ~/.kubegap/config.yaml
mode: daily          # no node scripts, no CloudWatch logs, no cost data, no external tools
node_access: none    # no SSM send-command, no SSH, no DaemonSet exec
install_tools: never # nothing is installed on this machine
# no grafana_api_token: the Grafana datasource and dashboard lists are not read
```

Give the kubeconfig a dedicated user bound to the shipped ClusterRole, [`deploy/permissions/clusterrole.yaml`](../deploy/permissions/clusterrole.yaml), which is `get` and `list` plus `create` on `pods/portforward`, and excludes Secrets. On EKS attach the IAM policy without its two `ssm:SendCommand` statements. kubegap prints it with your account and cluster filled in:

```bash
scripts/kubegap iam-policy --context <name> --without-node-access   # prints the policy; sends nothing to AWS
scripts/kubegap iam-policy --context <name>                         # the full policy, node reads included
```

If the four stores are reachable by URL, set the four `<store>_url` keys and drop the `pods/portforward` rule as well.

What a run sees with cluster access and no IAM permission at all, measured per mode on an EKS cluster: [the section "Without any IAM permission" of `docs/PERMISSIONS.md`](PERMISSIONS.md#without-any-iam-permission-22).

What that run cannot see, each reported as "not collected" or "skipped" and never as a pass:

- the 26 `node.*` checks that read the node scripts and the kubelet configuration. The 10 that read Prometheus node metrics keep running;
- the two Helm checks, `hygiene.helm-release-not-deployed` and `hygiene.helm-release-stale`;
- the six control-plane log checks on EKS: `controlplane.scheduler-unschedulable`, `webhook-call-failures`, `controller-error-repeat`, `apiserver-slow-traces`, `authenticator-failures`, `etcd-slow`;
- the checks that read cost data, ECR, service quotas and EBS metrics;
- the krr, polaris, pluto and kubent results;
- the node-side read of `/metrics` for components Prometheus does not scrape. Their `*.metrics-unreadable` check warns when the API server proxy is blocked as well.

The Grafana datasource and dashboard lists read "no auth"; the `grafana.*` checks judge from Grafana's own metrics and keep running. What each single permission costs when removed is in [`PERMISSIONS.md`](PERMISSIONS.md).
