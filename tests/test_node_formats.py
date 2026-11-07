"""Node command output formats (#127): the kernel-message classes of collectors/core/node-os.sh matched against lines built from the kernel's
format strings, and the parsers of lib/summaries/nodeos.py and lib/summaries/k3s.py against the text the tools print at the versions references/sources.md cites."""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from pathlib import Path

import pytest

from lib.summaries import k3s, nodeos

NOW = dt.datetime(2026, 11, 5, 17, 25, 17, tzinfo=dt.UTC)  # the etcd snapshot and certificate ages are measured from the snapshot time, not the wall clock (#165)

ROOT = Path(__file__).resolve().parent.parent
NODE_OS = (ROOT / "collectors" / "core" / "node-os.sh").read_text(encoding="utf-8")
K3S_NODE = (ROOT / "collectors" / "k3s-platform" / "k3s-node.sh").read_text(encoding="utf-8")
PATTERNS = dict(re.findall(r"^(P_[A-Z_]+)='(.*)'$", NODE_OS, re.MULTILINE))
# which class each `C <class> "$P_X" ["$P_EXCLUDE"]` line counts, and what it excludes
CLASSES = {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(r'^C (\w+) "\$(P_[A-Z_]+)"(?: "\$(P_[A-Z_]+)")?$', NODE_OS, re.MULTILINE)}


def classes_of(line: str) -> set[str]:
    """The classes `C` counts the line under, through `grep -E` exactly as the script runs it."""
    out = set()
    for cls, (pat, excl) in CLASSES.items():
        hit = subprocess.run(["grep", "-E", PATTERNS[pat]], input=line, capture_output=True, text=True, check=False).returncode == 0
        if hit and excl:
            hit = subprocess.run(["grep", "-E", PATTERNS[excl]], input=line, capture_output=True, text=True, check=False).returncode != 0
        if hit:
            out.add(cls)
    return out


P = "2026-11-02T08:34:08+0000 ip-10-0-9-9.internal kernel: "


@pytest.mark.parametrize(
    "line,expected",
    [
        # mm/oom_kill.c:891, 1115@v5.10
        (P + "Out of memory: Killed process 4242 (java) total-vm:3400000kB, anon-rss:1800000kB, file-rss:0kB, shmem-rss:0kB, UID:0 pgtables:4000kB oom_score_adj:0", {"oom_node"}),
        (P + "Memory cgroup out of memory: Killed process 4242 (java) total-vm:3400000kB", {"oom_cgroup"}),
        (P + "Out of memory: Killed process 1234 (kubelet) total-vm:1000kB", {"oom_node", "oom_system_victim"}),
        (P + "Out of memory: Kill process 1234 (containerd-shim) score 10 or sacrifice child", {"oom_node", "oom_system_victim"}),
        # kernel/watchdog.c:412@v5.10 says BUG: too, which counts as a lockup only
        (P + "watchdog: BUG: soft lockup - CPU#3 stuck for 22s! [kworker/3:1:12345]", {"lockup"}),
        (P + "NMI watchdog: Watchdog detected hard LOCKUP on cpu 2", {"lockup"}),
        (P + "INFO: task jbd2/nvme0n1p1-8:302 blocked for more than 120 seconds.", {"lockup"}),
        (P + "rcu: INFO: rcu_sched detected stalls on CPUs/tasks:", {"lockup"}),
        (P + "rcu: INFO: rcu_preempt self-detected stall on CPU", {"lockup"}),
        # block/blk-core.c:229@v5.10 and blk-mq.c:779@v6.12
        (P + "blk_update_request: I/O error, dev nvme0n1, sector 2048 op 0x0:(READ) flags 0x0 phys_seg 1 prio class 0", {"io_error"}),
        (P + "I/O error, dev nvme1n1, sector 4096 op 0x1:(WRITE) flags 0x800 phys_seg 1 prio class 2", {"io_error"}),
        (P + "Buffer I/O error on dev dm-0, logical block 1, lost async page write", {"io_error"}),
        (P + "nvme nvme0: I/O 12 QID 3 timeout, reset controller", {"io_error"}),
        (P + "critical medium error, dev sda, sector 123 op 0x0:(READ) flags 0x0 phys_seg 1 prio class 0", {"io_error"}),
        # fs/ext4/super.c, fs/xfs/xfs_message.c, fs/btrfs/messages.c
        (P + "EXT4-fs error (device nvme0n1p1): ext4_find_entry:1535: inode #2: comm ls: reading directory lblock 0", {"fs_error"}),
        (P + "EXT4-fs (nvme0n1p1): Remounting filesystem read-only", {"fs_error"}),
        (P + "XFS (dm-0): Metadata corruption detected at xfs_dir3_block_read_verify+0x1a/0x80, xfs_dir3_block block 0x1234", {"fs_error"}),
        (P + "BTRFS error (device sda1): bad tree block start, want 1 have 0", {"fs_error"}),
        (P + "BTRFS: error (device sda1) in btrfs_run_delayed_refs:2122: errno=-5 IO failure", {"fs_error"}),
        # drivers/net/ethernet/amazon/ena/ena_netdev.c, net/sched/sch_generic.c, drivers/net/phy/phy.c
        (P + "ena 0000:00:05.0 eth0: Keep alive watchdog timeout.", {"nic"}),
        (P + "ena 0000:00:05.0 ens5: Found a Tx that wasn't completed on time, qid 3, index 12.", {"nic"}),
        (P + "ena 0000:00:05.0 enX0: TX hasn't completed, qid 3, index 12. 1500 msecs have passed", {"nic"}),
        (P + "NETDEV WATCHDOG: eth0 (ena): transmit queue 2 timed out", {"nic"}),
        (P + "eth0: Link is Down", {"nic"}),
        # net/netfilter/nf_conntrack_core.c:1488@v5.10: one line, one class, not also net_pressure
        (P + "nf_conntrack: nf_conntrack: table full, dropping packet", {"conntrack_full"}),
        (P + "TCP: out of memory -- consider tuning tcp_mem", {"net_pressure"}),
        (P + "TCP: too many orphaned sockets", {"net_pressure"}),
        (P + "neighbour: arp_cache: neighbor table overflow!", {"net_pressure"}),
        (P + "TCP: request_sock_TCP: Possible SYN flooding on port 443. Sending cookies.", {"net_pressure"}),
        (P + "kworker/u8:2: page allocation failure: order:0, mode:0xa20(GFP_ATOMIC), nodemask=(null)", {"mem_pressure"}),
        # arch/x86/kernel/dumpstack.c:195 and arch/arm64/kernel/stacktrace.c:173 (Graviton nodes)
        (P + "Call Trace:", {"bug"}),
        (P + "Call trace:", {"bug"}),
        (P + "BUG: kernel NULL pointer dereference, address: 0000000000000008", {"bug"}),
        (P + "Oops: 0000 [#1] SMP NOPTI", {"bug"}),
        (P + "general protection fault, probably for non-canonical address 0xdead: 0000 [#1] SMP", {"bug"}),
        (P + "java[4242]: segfault at 0 ip 00007f ... sp 00007f ... error 4 in libjvm.so", {"segfault"}),
        (P + "clocksource: timekeeping watchdog on CPU1: Marking clocksource 'tsc' as unstable because the skew is too large:", {"clock"}),
        (P + "tsc: Marking TSC unstable due to clocksource watchdog", {"clock"}),
        # boot-time noise and a user-space errno text match nothing
        (P + "nvme nvme0: 4/0/0 default/read/poll queues", set()),
        (P + "Read-only file system", set()),
        (P + "systemd[1]: Started Journal Service.", set()),
    ],
)
def test_kernel_line_is_counted_under_its_one_class(line, expected):
    assert classes_of(line) == expected


def test_every_pattern_is_counted_once():
    assert set(PATTERNS) == {pat for pat, _ in CLASSES.values()}, "a P_ pattern that no C line counts, or the reverse"


# ---------- lib/summaries/nodeos.py ----------


def test_containerd_version_from_both_version_line_shapes():
    # the rpm build prints the bare version, a git-describe build (k3s) keeps the v; the CRI version is the fallback
    assert nodeos._parse_cri(["cmd=crictl", "version=Version: 0.1.0 RuntimeName: containerd RuntimeVersion: v2.1.4-k3s1 RuntimeApiVersion: v1"])["version"] == "v2.1.4-k3s1"
    for line, want in (("containerd github.com/containerd/containerd 1.7.29 442cb34", "1.7.29"), ("containerd github.com/containerd/containerd/v2 v2.1.4-k3s1 1c4457e", "2.1.4"), ("containerd containerd.io v2.2.0 1c4457e", "2.2.0")):
        assert (re.search(r"(?<![\w.])v?(\d+\.\d+\.\d+)", line) or [None, None])[1] == want


def test_crictl_binary_version_and_snapshotter_fallback_on_containerd_2():
    lines = [
        "cmd=sudo -n /usr/local/bin/k3s crictl",
        "version=Version: 0.1.0 RuntimeName: containerd RuntimeVersion: v2.1.4-k3s1 RuntimeApiVersion: v1",
        "crictl=crictl version v1.33.0",
        'imagefs={"status":{"containerFilesystems":[],"imageFilesystems":[{"fsId":{"mountpoint":"/var/lib/rancher/k3s/agent/containerd/io.containerd.snapshotter.v1.overlayfs"},"inodesUsed":{"value":"738647"},"timestamp":"1","usedBytes":{"value":"21474836480"}}]}}',
        'conditions="status":true,"type":"RuntimeReady" "status":true,"type":"NetworkReady" "status":false,"type":"ContainerdHasNoDeprecationWarnings"',
        "systemd_cgroup=true",
        "snapshotter=",
        "sandbox_image=",
    ]
    cri = nodeos._parse_cri(lines)
    assert cri["crictl_version"] == "1.33.0"
    assert cri["snapshotter"] == "overlayfs", "containerd 2.x prints no snapshotter in crictl info; the imagefs mount point names it"
    assert cri["sandbox_image"] is None
    assert cri["conditions"] == {"RuntimeReady": True, "NetworkReady": True, "ContainerdHasNoDeprecationWarnings": False} and cri["deprecation_warnings"]
    assert cri["imagefs_used_gb"] == 20.0
    old = nodeos._parse_cri(["cmd=crictl", "version=Version: 0.1.0 RuntimeName: containerd RuntimeVersion: 1.7.29 RuntimeApiVersion: v1", "snapshotter=overlayfs"])
    assert old["snapshotter"] == "overlayfs" and old["crictl_version"] is None


def test_service_lines_from_systemd_219_and_249():
    rows = nodeos._parse_services(["kubelet active=active restarts=? since=Thu 2026-10-08 12:32:23 UTC", "kubelet active=inactive restarts=0 since=n/a", "k3s active=active restarts=5 since=Wed 2026-10-28 19:25:12 UTC"])
    assert rows[0] == {"unit": "kubelet", "active": "active", "restarts": None, "since": "Thu 2026-10-08 12:32:23 UTC"}, "systemd 219 (Amazon Linux 2) has no NRestarts property"
    assert rows[1]["since"] is None and rows[1]["restarts"] == 0
    assert rows[2]["restarts"] == 5


def test_timedatectl_wordings_of_systemd_219_and_239():
    old = nodeos._parse_time(["Time zone: n/a (UTC, +0000)", "NTP enabled: yes", "NTP synchronized: yes"])
    new = nodeos._parse_time(["Time zone: Etc/UTC (UTC, +0000)", "System clock synchronized: no", "NTP service: active"])
    assert (old["synchronized"], old["ntp"]) == (True, "yes") and (new["synchronized"], new["ntp"]) == (False, "active")


def test_cgroup_version_from_stat_including_the_unnamed_magic_of_coreutils_822():
    # coreutils/coreutils src/stat.c:270-271, 417-418@v8.22 name cgroupfs and tmpfs only; :288@v8.26 adds cgroup2fs
    assert [nodeos.CGROUP_FS.get(fs, "unknown") for fs in ("cgroup2fs", "tmpfs", "UNKNOWN (0x63677270)", "cgroupfs")] == ["v2", "v1", "v2", "unknown"]


# ---------- lib/summaries/k3s.py ----------

CERT_LINES = [
    'time="2026-11-05T17:25:17Z" level=info msg="/var/lib/rancher/k3s/server/tls/server-ca.crt: certificate k3s-server-ca@1761681912 (CertSign) is ok, expires at 2035-10-26T19:25:12Z"',
    'time="2026-11-05T17:25:17Z" level=warning msg="/var/lib/rancher/k3s/server/tls/client-admin.crt: certificate system:admin (ClientAuth) will expire within 120 days at 2026-12-01T00:00:00Z"',
    'time="2026-11-05T17:25:17Z" level=error msg="/var/lib/rancher/k3s/server/tls/serving-kube-apiserver.crt: certificate kube-apiserver (ServerAuth,ClientAuth) expired at 2026-10-01T00:00:00Z"',
    'time="2026-11-05T17:25:17Z" level=error msg="/var/lib/rancher/k3s/server/tls/x.crt: certificate x (Unknown) is not valid before 2028-01-01T00:00:00Z"',
]


def test_certificate_check_wordings_of_k3s():
    out = k3s._parse_server(["secrets_encrypt=Disabled, no configuration file found", "certificates:", *CERT_LINES], NOW)
    assert [c["status"] for c in out["certificates"]] == ["ok", "expiring", "expired", "not-yet-valid"]
    assert out["certificates"][2]["usage"] == "ServerAuth,ClientAuth"
    assert [c["name"] for c in out["certificates_expiring_90d"]] == ["system:admin", "kube-apiserver"], "the warning wording (120-day window) and the expired one are under 90 days"
    assert out["certificates_min_days_left"] == -36
    assert out["certificates_raw_lines"] == 4 and out["secrets_encryption"] == "Disabled, no configuration file found"


def test_etcd_snapshot_rows_and_journald_sizes():
    out = k3s._parse_server(
        [
            "etcd_snapshots:",
            "etcd-snapshot-kkh2-1793664001 file:///var/lib/rancher/k3s/server/db/snapshots/etcd-snapshot-kkh2-1793664001 39432224 2026-11-03T00:00:01Z",
            "etcd-snapshot-kkh2-1793707204 s3://bucket/etcd-snapshot-kkh2-1793707204 39514144 2026-11-03T12:00:04Z",
            "db_mb=594",
        ],
        NOW,
    )
    assert [s["offsite"] for s in out["etcd_snapshots"]] == [False, True] and out["snapshot_interval_h"] == 12.0 and out["etcd_snapshots"][0]["size_mb"] == 37.6
    rec: dict = {"gaps": [], "role": "server"}
    for disk, mb in (("336.0M", 336), ("1.5G", 1536), ("1.0T", 1048576), ("800B", 0)):
        k3s._node_runtime(rec, {"journald": [f"disk={disk}", "conf=", "k3s_lines_24h=9116"]})
        assert rec["journald"]["disk_mb"] == mb, disk


def test_unit_token_masking_of_k3s_node_sh(tmp_path):
    redact = re.search(r'^REDACT="(.*)"$', K3S_NODE, re.MULTILINE).group(1)
    unit = "ExecStart=/usr/local/bin/k3s \\\n    server \\\n\t'--token' \\\n\t'K10abcdef0123456789abcdef::server:0123456789abcdef' \\\n\t'--agent-token' \\\n\t'plainsecret' \\\n\t'--token=inline' \\\n\t'--disable' \\\n\t'traefik' \\\n"
    out = subprocess.run(["sed", "-e", redact], input=unit, capture_output=True, text=True, check=True).stdout
    assert "K10abc" not in out and "plainsecret" not in out and "inline" not in out
    assert out.count("'<redacted>'") == 2 and "'--token=<redacted>'" in out and "'traefik'" in out, out
