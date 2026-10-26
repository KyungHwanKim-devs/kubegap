#!/bin/sh
# kubegap k3s node platform read-only inspection. Writes nothing to the node.
# Runs as the SSH login user; anything needing root is attempted only through the commands allowed by deploy/node-access/kubegap-sudoers via sudo -n. If that fails the section is empty and the parser records "no node access".
# Output is a sequence of "### <section>" sections parsed by lib/k3s.py. Tokens and secrets are never printed (the --token value in the systemd unit and K10... tokens are removed with sed).
S() { echo "### $1"; }
if [ "$(id -u)" = 0 ]; then SUDO=""; else SUDO="sudo -n"; fi
K3S=/usr/local/bin/k3s
REDACT='s/K10[0-9a-f]\{20,\}::[a-z]*:[0-9a-f]*/<token>/g; s/\(--token[= ]\)[^ ]*/\1<redacted>/g; s/\(K3S_TOKEN=\)[^ ]*/\1<redacted>/g'

S meta
echo "role=$( systemctl is-active k3s >/dev/null 2>&1 && echo server || ( systemctl is-active k3s-agent >/dev/null 2>&1 && echo agent || echo none ) )"
echo "version=$([ -x $K3S ] && $K3S --version 2>/dev/null | head -1)"
echo "config_file=$([ -e /etc/rancher/k3s/config.yaml ] && echo present || echo absent)"
echo "smartctl=$(command -v smartctl >/dev/null 2>&1 && echo yes || echo no)"
echo "sensors=$(command -v sensors >/dev/null 2>&1 && echo yes || echo no)"

S unit
# ExecStart arguments of the systemd unit. Tokens are removed. (The same data is in the node annotation k3s.io/node-args, which the parser prefers)
for u in k3s k3s-agent; do
  systemctl cat "$u" 2>/dev/null | sed -n '/^ExecStart=/,/^$/p' | sed -e "$REDACT" | head -40
done
for u in k3s k3s-agent; do
  systemctl is-active "$u" >/dev/null 2>&1 && echo "unit:$u $(systemctl show -p ActiveEnterTimestamp,NRestarts "$u" 2>/dev/null | tr '\n' ' ')"
done

S check-config
# Kernel config check. Strip color codes; keep only missing entries and the final STATUS.
[ -x $K3S ] && $K3S check-config 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | grep -E 'missing|STATUS' | sed 's/^ *//' | head -20

S ports
# Which addresses 6443 (apiserver), 2379/2380/2381 (etcd), 10250 (kubelet), 9345 (supervisor), 8472 (vxlan; UDP so not in ss -l), 7946 (MetalLB memberlist) and 179 (BGP) listen on. Process names need root.
( $SUDO /usr/bin/ss -ltnp 2>/dev/null || ss -ltn 2>/dev/null ) | awk 'NR>1 {print $4, $6}' | grep -E ':(6443|6444|2379|2380|2381|10250|10257|10259|9345|7946|179|80|443|30[0-9]{3}|31[0-9]{3}|32[0-9]{3}) ' | sed -E 's/users:\(\("([^"]+)".*/\1/' | sort -u | head -40

S flannel
echo "mtu=$(ip -d link show flannel.1 2>/dev/null | grep -oE 'mtu [0-9]+' | head -1 | cut -d' ' -f2)"
echo "vxlan=$(ip -d link show flannel.1 2>/dev/null | grep -oE 'vxlan id [0-9]+ local [0-9.]+ dev [a-z0-9]+' | head -1)"
echo "stats=$(ip -s link show flannel.1 2>/dev/null | awk '/RX:/{getline; rx=$0} /TX:/{getline; tx=$0} END{print "rx:" rx " tx:" tx}' | tr -s ' ')"
echo "underlay_mtu=$(d=$(ip -d link show flannel.1 2>/dev/null | grep -oE 'dev [a-z0-9]+' | head -1 | cut -d' ' -f2); [ -n "$d" ] && ip link show "$d" 2>/dev/null | grep -oE 'mtu [0-9]+' | cut -d' ' -f2)"
echo "addrs=$(ip -o -4 addr show 2>/dev/null | grep -vE ' lo | veth| cni| docker| br-[0-9a-f]' | awk '{print $2 "=" $4}' | tr '\n' ' ')"
echo "ip_forward=$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null)"
echo "br_netfilter=$(cat /proc/sys/net/bridge/bridge-nf-call-iptables 2>/dev/null || echo absent)"

S journald
echo "disk=$(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMG]' | head -1)"
echo "conf=$(grep -hE '^(SystemMaxUse|SystemKeepFree|MaxRetentionSec|Storage|RuntimeMaxUse)=' /etc/systemd/journald.conf /etc/systemd/journald.conf.d/*.conf 2>/dev/null | tr '\n' ';')"
echo "k3s_lines_24h=$(journalctl -u k3s -u k3s-agent --since -24h -q 2>/dev/null | wc -l | tr -d ' ')"

S server
# Only meaningful on server nodes. On agents the command is missing or not permitted, so the section is empty.
if systemctl is-active k3s >/dev/null 2>&1; then
  echo "secrets_encrypt=$($SUDO $K3S secrets-encrypt status 2>/dev/null | grep -E 'Encryption Status' | sed 's/Encryption Status: //')"
  echo "etcd_snapshots:"
  $SUDO $K3S etcd-snapshot ls 2>/dev/null | tail -n +2 | awk '{print $1, $2, $3, $4}' | tail -n 30
  echo "db_mb=$($SUDO /usr/bin/du -sm /var/lib/rancher/k3s/server/db 2>/dev/null | cut -f1)"
  echo "db_ls:"
  $SUDO /usr/bin/ls -la /var/lib/rancher/k3s/server/db 2>/dev/null | tail -n +2 | awk '{print $1, $5, $6, $7, $9}' | head -12
  echo "db_kind=$( $SUDO /usr/bin/ls -la /var/lib/rancher/k3s/server/db 2>/dev/null | grep -q ' etcd$' && echo etcd || ( $SUDO /usr/bin/ls -la /var/lib/rancher/k3s/server/db 2>/dev/null | grep -q state.db && echo sqlite || echo unknown ) )"
  echo "certificates:"
  $SUDO $K3S certificate check 2>&1 | grep -E 'certificate .* expires at|expired|WARN|warning' | sed -E 's/\x1b\[[0-9;]*m//g' | head -60
fi

S registries
$SUDO /usr/bin/cat /etc/rancher/k3s/registries.yaml 2>/dev/null | grep -vE 'password|token|username' | head -30

S containerd
$SUDO /usr/bin/cat /var/lib/rancher/k3s/agent/etc/containerd/config.toml 2>/dev/null | grep -E 'SystemdCgroup|sandbox_image|snapshotter|registry\.(configs|mirrors)|disable_cgroup' | sed 's/^ *//' | head -20

S local-path
# local-path-provisioner volume directories (default /var/lib/rancher/k3s/storage). The PVC name is part of the directory name.
echo "total_mb=$($SUDO /usr/bin/du -sm /var/lib/rancher/k3s/storage 2>/dev/null | cut -f1)"
echo "volumes_mb:"
$SUDO /usr/bin/du -m -d 1 /var/lib/rancher/k3s/storage 2>/dev/null | grep -v 'storage$' | sort -rn | head -30

S disks
lsblk -d -o NAME,TYPE,SIZE,ROTA,MODEL 2>/dev/null | grep -vE 'loop|NAME' | tr -s ' ' | head -8
if command -v smartctl >/dev/null 2>&1; then
  for d in $(lsblk -d -n -o NAME,TYPE 2>/dev/null | awk '$2=="disk"{print "/dev/" $1}'); do
    echo "smart:$d health=$($SUDO /usr/sbin/smartctl -H $d 2>/dev/null | grep -iE 'overall-health|SMART Health Status' | sed 's/.*: *//') attrs=$($SUDO /usr/sbin/smartctl -A $d 2>/dev/null | grep -iE 'Percentage Used|Media and Data Integrity|Reallocated_Sector_Ct|Wear_Leveling|Power_On_Hours|Temperature' | tr -s ' ' | cut -c1-80 | tr '\n' ';')"
  done
fi

S thermal
for z in /sys/class/thermal/thermal_zone*; do [ -e "$z/temp" ] && echo "zone:$(cat $z/type 2>/dev/null)=$(cat $z/temp 2>/dev/null)"; done 2>/dev/null | head -8
command -v sensors >/dev/null 2>&1 && sensors 2>/dev/null | grep -E '^(Package|Core|Tctl|temp1|Composite)' | tr -s ' ' | head -6

S end
