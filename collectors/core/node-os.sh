#!/bin/sh
# kubegap node OS read-only inspection. Writes nothing to the node.
# On EKS it runs via SSM (root); over SSH it runs as the login user and only the read-only commands allowed by deploy/node-access/kubegap-sudoers via sudo -n.
# Output is a sequence of sections split by "### <section>" and is parsed by lib/nodeos.py. SSM truncates stdout at 24,000 characters, so every section caps its line count.
S() { echo "### $1"; }
if [ "$(id -u)" = 0 ]; then SUDO=""; else SUDO="sudo -n"; fi
K3S=/usr/local/bin/k3s

S meta
echo "uid=$(id -u)"
echo "hostname=$(hostname 2>/dev/null)"
echo "kernel=$(uname -r)"
echo "os=$(. /etc/os-release 2>/dev/null; echo "$PRETTY_NAME")"
echo "uptime_s=$(cut -d' ' -f1 /proc/uptime)"
echo "loadavg=$(cut -d' ' -f1-3 /proc/loadavg)"
echo "nproc=$(nproc 2>/dev/null)"
echo "mem_total_kb=$(awk '/MemTotal/{print $2}' /proc/meminfo)"
echo "containerd=$(containerd --version 2>/dev/null)"
echo "k3s=$([ -x $K3S ] && $K3S --version 2>/dev/null | head -1)"
echo "dmesg_restrict=$(cat /proc/sys/kernel/dmesg_restrict 2>/dev/null)"
echo "zombies=$(ps -eo stat= 2>/dev/null | grep -c '^Z')"
echo "kubelet_rss_kb=$(ps -o rss= -C kubelet 2>/dev/null | head -1 | tr -d ' ')"
echo "containerd_rss_kb=$(ps -o rss= -C containerd 2>/dev/null | head -1 | tr -d ' ')"
echo "k3s_rss_kb=$(ps -o rss= -C k3s-server,k3s-agent,k3s 2>/dev/null | head -1 | tr -d ' ')"

S kernel
# Kernel log for 24h. If journalctl -k is empty (non-persistent journald, permissions) fall back to dmesg -T (everything since boot) and record it in source.
KSRC=journalctl
# If the boot was within 24h, skip the first 300s after boot (SATA scans and link-down lines from the boot sequence) — otherwise a reboot shows up as a NIC-event fail
KSINCE="-24h"; BOOT_S=$(date -d "$(uptime -s 2>/dev/null)" +%s 2>/dev/null); NOW_S=$(date +%s)
if [ -n "$BOOT_S" ] && [ $((NOW_S - BOOT_S)) -lt 86400 ]; then KSINCE=$(date -d "@$((BOOT_S + 300))" '+%Y-%m-%d %H:%M:%S'); echo "boot_window_excluded=$KSINCE"; fi
KLOG=$(journalctl -k --since "$KSINCE" -o short-iso --no-pager -q 2>/dev/null)
if [ -z "$KLOG" ]; then
  KSRC=dmesg
  KLOG=$(dmesg -T 2>/dev/null || $SUDO /usr/bin/dmesg -T 2>/dev/null)
  [ -z "$KLOG" ] && KSRC=none
fi
echo "source=$KSRC"
echo "lines=$(printf '%s\n' "$KLOG" | grep -c .)"
C() { echo "c:$1=$(printf '%s\n' "$KLOG" | grep -cE "$2")"; }
# Classification patterns (case sensitive). Match the exact message shape so boot messages like nvme_core.io_timeout on the kernel command line are not caught.
P_OOM_NODE='Out of memory: Kill'
P_OOM_CG='Memory cgroup out of memory'
P_OOM_SYS='Out of memory: Kill(ed)? process [0-9]+ \((kubelet|containerd|k3s|dockerd|systemd|sshd|containerd-shim)'
P_LOCKUP='soft lockup|hard LOCKUP|hung_task|blocked for more than|rcu_sched detected|rcu_preempt detected|rcu: INFO'
P_IO='I/O error|Buffer I/O error|blk_update_request: I/O error|nvme nvme[0-9]+: .*(timeout|reset|Abort|abort)|critical medium error|print_req_error'
P_FS='EXT4-fs error|EXT4-fs warning|XFS \([a-z0-9]+\): .*(error|Corruption|Metadata)|Remounting filesystem read-only|BTRFS error|Read-only file system'
P_NIC='ena [0-9a-f:.]+ (eth|ens)[0-9]+: .*(reset|timeout|hang|keep alive)|Link is Down|link down|Tx timeout|Unit Hang|NETDEV WATCHDOG|(eth|ens|enp)[0-9a-z]+: .*(reset|went down)'
P_CT='nf_conntrack: .*table full'
P_NET='TCP: out of memory|neighbou?r.*table overflow|SYN flooding|TCP: too many orphaned|dropping packet'
P_MEM='page allocation failure|Out of socket memory|Out of memory and no killable'
P_BUG='BUG: |Oops: |Call Trace:|general protection fault'
P_SEG='segfault at'
P_CLK='clocksource.*unstable|TSC.*unstable|Clocksource .* unstable'
C oom_node "$P_OOM_NODE"
C oom_cgroup "$P_OOM_CG"
C oom_system_victim "$P_OOM_SYS"
C lockup "$P_LOCKUP"
C io_error "$P_IO"
C fs_error "$P_FS"
C nic "$P_NIC"
C conntrack_full "$P_CT"
C net_pressure "$P_NET"
C mem_pressure "$P_MEM"
C bug "$P_BUG"
C segfault "$P_SEG"
C clock "$P_CLK"
echo "samples:"
printf '%s\n' "$KLOG" | grep -E "$P_OOM_NODE|$P_OOM_CG|$P_LOCKUP|$P_IO|$P_FS|$P_NIC|$P_CT|$P_NET|$P_MEM|$P_BUG|$P_SEG|$P_CLK" \
  | grep -v '^$' | cut -c1-200 | tail -n 40

S sysctl
P() { v=$(cat "/proc/sys/$2" 2>/dev/null | tr '\t' ' '); echo "$1=${v:-absent}"; }
P net.netfilter.nf_conntrack_max net/netfilter/nf_conntrack_max
P net.netfilter.nf_conntrack_count net/netfilter/nf_conntrack_count
P net.netfilter.nf_conntrack_tcp_timeout_established net/netfilter/nf_conntrack_tcp_timeout_established
P fs.inotify.max_user_watches fs/inotify/max_user_watches
P fs.inotify.max_user_instances fs/inotify/max_user_instances
P fs.file-max fs/file-max
P fs.file-nr fs/file-nr
P fs.aio-max-nr fs/aio-max-nr
P net.core.somaxconn net/core/somaxconn
P net.core.netdev_max_backlog net/core/netdev_max_backlog
P net.ipv4.ip_local_port_range net/ipv4/ip_local_port_range
P net.ipv4.tcp_max_syn_backlog net/ipv4/tcp_max_syn_backlog
P net.ipv4.tcp_tw_reuse net/ipv4/tcp_tw_reuse
P net.ipv4.ip_forward net/ipv4/ip_forward
P net.bridge.bridge-nf-call-iptables net/bridge/bridge-nf-call-iptables
P net.ipv4.neigh.default.gc_thresh3 net/ipv4/neigh/default/gc_thresh3
P vm.max_map_count vm/max_map_count
P vm.swappiness vm/swappiness
P vm.overcommit_memory vm/overcommit_memory
P vm.panic_on_oom vm/panic_on_oom
P kernel.panic kernel/panic
P kernel.panic_on_oops kernel/panic_on_oops
P kernel.pid_max kernel/pid_max
P kernel.threads-max kernel/threads-max
P kernel.dmesg_restrict kernel/dmesg_restrict

S cri
# Container runtime: use crictl directly if it works (EKS root), otherwise the k3s built-in crictl through the sudoers allowance.
if crictl info >/dev/null 2>&1; then CRI="crictl"
elif [ -x $K3S ] && $SUDO $K3S crictl info >/dev/null 2>&1; then CRI="$SUDO $K3S crictl"
else CRI=""; fi
echo "cmd=${CRI:-none}"
if [ -n "$CRI" ]; then
  echo "version=$($CRI version 2>/dev/null | tr '\n' ' ' | tr -s ' ')"
  PS=$($CRI ps -a 2>/dev/null)
  for st in Running Exited Created Unknown; do echo "state:$st=$(printf '%s\n' "$PS" | tail -n +2 | grep -cw "$st")"; done
  echo "images=$($CRI images 2>/dev/null | tail -n +2 | grep -c .)"
  # Top 15 images by size. Table columns: IMAGE TAG IMAGE_ID SIZE — SIZE is a human unit like "1.23GB", hence sort -h
  echo "images_top:"
  $CRI images 2>/dev/null | tail -n +2 | awk 'NF>=4 {print $4 "\t" $1 ":" $2}' | sort -h -r | head -15
  echo "imagefs=$($CRI imagefsinfo 2>/dev/null | tr -d ' \n' | cut -c1-400)"
  INFO=$($CRI info 2>/dev/null | tr -d ' \n')
  echo "conditions=$(printf '%s' "$INFO" | grep -oE '"type":"[A-Za-z]+","status":(true|false)|"status":(true|false),"type":"[A-Za-z]+"' | tr '\n' ' ')"
  echo "systemd_cgroup=$(printf '%s' "$INFO" | grep -oE '"SystemdCgroup":(true|false)' | head -1 | cut -d: -f2)"
  echo "snapshotter=$(printf '%s' "$INFO" | grep -oE '"snapshotter":"[a-z0-9]+"' | head -1 | cut -d: -f2 | tr -d '"')"
  echo "sandbox_image=$(printf '%s' "$INFO" | grep -oE '"sandboxImage":"[^"]+"' | head -1 | cut -d: -f2- | tr -d '"')"
  echo "cni_error=$(printf '%s' "$INFO" | grep -oE '"lastCNILoadStatus(\.default)?":"[^"]{1,160}"' | head -1 | cut -d: -f2- | tr -d '"')"
  # Top 10 containers by writable layer (DISK column) — on a node whose disk is filling up this pins down "which container writes to the node disk".
  # Table output (crictl stats -a / ps -a) is cut by header column positions (JSON would exceed the 24,000-character SSM cap). Without `crictl stats -a` in sudoers this shows as permission.
  # crictl stats prefixes its first line with clear-screen escapes (ESC[2J ESC[H) — that shifts the header positions by 7, so strip everything before CONTAINER.
  if STATS=$($CRI stats -a 2>/dev/null | sed '1s/^.*CONTAINER /CONTAINER /') && [ -n "$STATS" ]; then
    echo "writable_layers:"
    PSA=$($CRI ps -a 2>/dev/null | sed '1s/^.*CONTAINER /CONTAINER /')
    printf '%s\n' "$STATS" | awk -v ps="$PSA" '
      function tok(s) { sub(/^ +/, "", s); split(s, t, " "); return t[1] }
      function mb(v) { u=v; gsub(/[0-9.]/, "", u); n=v+0; if (u=="kB"||u=="KB"||u=="KiB") return n/1024; if (u=="MB"||u=="MiB") return n; if (u=="GB"||u=="GiB") return n*1024; if (u=="TB"||u=="TiB") return n*1048576; return n/1048576 }
      BEGIN { n=split(ps, L, "\n"); h=L[1]; hn=index(h,"NAME"); hpi=index(h,"POD ID"); rest=substr(h,hpi+6); hp=hpi+5+index(rest,"POD"); hns=index(h,"NAMESPACE");
              for (i=2;i<=n;i++) { id=substr(L[i],1,13); if (id=="") continue; CN[id]=tok(substr(L[i],hn)); PD[id]=tok(substr(L[i],hp)); NS[id]=(hns>0)?tok(substr(L[i],hns)):"?" } }
      NR==1 { hd=index($0,"DISK"); next }
      { id=substr($0,1,13); d=tok(substr($0,hd)); if (d=="" || !(id in PD)) next; printf "%d\t%s/%s/%s\n", mb(d), NS[id], PD[id], CN[id] }' | sort -rn | head -10
  else
    echo "writable_layers_error=$($CRI stats -a 2>&1 | head -1 | cut -c1-120)"
  fi
fi

S cgroup
echo "fs=$(stat -fc %T /sys/fs/cgroup/ 2>/dev/null)"
echo "controllers=$(cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null)"

S time
timedatectl status 2>/dev/null | sed 's/^ *//' | grep -iE 'synchronized|NTP|Time zone' | head -4
echo "chrony=$(chronyc tracking 2>/dev/null | grep -E 'Stratum|System time|Leap' | tr -s ' ' | tr '\n' ';')"

S disk
# Filesystem usage per path (capacity and inodes). The parser merges paths on the same filesystem.
for p in / /var/lib/containerd /var/lib/rancher /var/lib/kubelet /var/log /run /tmp; do
  [ -d "$p" ] || continue
  df -P -k "$p" 2>/dev/null | tail -1 | awk -v p="$p" '{print "fs:" p " dev=" $1 " size_kb=" $2 " used_kb=" $3 " avail_kb=" $4 " use=" $5 " mount=" $6}'
  df -P -i "$p" 2>/dev/null | tail -1 | awk -v p="$p" '{print "inode:" p " inodes=" $2 " iused=" $3 " iuse=" $5}'
done
echo "pod_logs_mb:"
$SUDO /usr/bin/du -m -d 1 /var/log/pods 2>/dev/null | sort -rn | head -12
echo "emptydir_mb:"
# Only /var/lib/kubelet/pods/<uid>/volumes/kubernetes.io~empty-dir. ~csi and ~local-volume are PV bind mounts, not node disk usage.
$SUDO /usr/bin/du -m -d 3 /var/lib/kubelet/pods 2>/dev/null | grep -E 'kubernetes\.io~empty-dir$' | sort -rn | head -10
# No directory existence test ([ -d ]): it is false for a normal user when the parent is root-only (0700), so just try du.
if systemctl is-active docker >/dev/null 2>&1; then
  DM=$($SUDO /usr/bin/du -sm /var/lib/docker 2>/dev/null | cut -f1); echo "docker_mb=${DM:-?}"
fi
echo "containerd_mb=$( ( $SUDO /usr/bin/du -sm /var/lib/containerd 2>/dev/null; $SUDO /usr/bin/du -sm /var/lib/rancher/k3s/agent/containerd 2>/dev/null ) | cut -f1 | head -1)"

S services
for u in kubelet containerd k3s k3s-agent docker crio; do
  a=$(systemctl is-active "$u" 2>/dev/null)
  case "$a" in ""|unknown|inactive) [ "$u" = kubelet ] || [ "$u" = containerd ] || continue;; esac
  n=$(systemctl show -p NRestarts "$u" 2>/dev/null | cut -d= -f2)
  s=$(systemctl show -p ActiveEnterTimestamp "$u" 2>/dev/null | cut -d= -f2-)
  echo "$u active=$a restarts=${n:-?} since=$s"
done

S updates
echo "reboot_required=$([ -e /var/run/reboot-required ] && echo yes || echo no)"
echo "ubuntu_updates=$(grep -hoE '[0-9]+ (updates? can be applied|of these updates (are|is) (a )?standard security)' /var/lib/update-notifier/updates-available 2>/dev/null | tr '\n' ';')"
if command -v needs-restarting >/dev/null 2>&1; then
  needs-restarting -r >/dev/null 2>&1; rc=$?
  echo "needs_restarting_rc=$rc"
fi
echo "ami_release=$(cat /etc/eks/release 2>/dev/null | grep -E 'BASE_AMI_ID|BUILD_TIME|RELEASE_VERSION' | tr '\n' ';')"

S end
