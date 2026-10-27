# Node preparation (environments reached over SSH: k3s, bare metal, kubeadm)

kubegap **never changes a node**. To read the node operating-system layer (kernel log, k3s server log, datastore size, containerd state),
you prepare each node once. Anything not prepared is reported as "no node access" and only those checks are skipped.
EKS needs no preparation on the node (SSM `send-command` runs as root); it needs the SSM document `kubegap-node-read` in the account, which `kubegap setup` uploads with your consent (see the main README). The complete list of commands that reach a node on any backend is [`COMMANDS.md`](COMMANDS.md).

## Step 1 — log-reading groups (recommended, one line)

Add the SSH user to the `systemd-journal` (journalctl) and `adm` (/var/log) groups. This grants read access only.

```bash
sudo usermod -aG systemd-journal,adm <user>
```

Then, in a new SSH session, `journalctl -u k3s -n 1` should work without a password. This enables: k3s server and agent logs (in place of control-plane logs), the kernel log (`/var/log/kern.log`), containerd logs.

## Step 2 — sudo for read-only commands (optional)

Some reads still need root: `dmesg` (Ubuntu sets `kernel.dmesg_restrict=1`), `k3s secrets-encrypt status`, `k3s etcd-snapshot ls`,
the size of `/var/lib/rancher/k3s/server/db`, `crictl` (the config file of the crictl bundled with k3s is root-only), pod log and emptyDir directory sizes (`du -d` for per-directory totals only; file contents are not read), `ss -ltnp` (process name per port). Also used: `k3s certificate check` (certificate expiry), local-path volume directory sizes (`du /var/lib/rancher/k3s/storage`), containerd log `tail`, reading `registries.yaml` and the containerd `config.toml` (password lines are filtered out by the script).
These commands power the node OS checks (`node.*`: exited container count, image size, pod log and emptyDir size). With step 1 alone, the kernel log, sysctl, time sync, disk usage, systemd restart and OS update checks work; the rest is "no node access". Install `kubegap-sudoers` from this folder with the username replaced. Every command is read-only; there are no write commands.

```bash
sed 's/<USER>/<user>/' kubegap-sudoers | sudo tee /etc/sudoers.d/kubegap >/dev/null
sudo chmod 440 /etc/sudoers.d/kubegap && sudo visudo -c
```

## Verify

```bash
scripts/kubegap nodes --context <name>            # per node: reachable or not, and which privileged reads are allowed (journal, kern.log, dmesg, k3s-db, crictl, sudo list)
```

## When the address or username differs per node

Put `node-name: user@address` under `ssh.hosts` in `config.yaml` (for example an overlay-network address). Password login is not supported. To install your key on a node:
`ssh-copy-id <user>@<address>` (while password login is temporarily enabled) or add one line with the public key to `~/.ssh/authorized_keys` from the console.
