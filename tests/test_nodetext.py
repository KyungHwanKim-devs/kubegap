"""lib/foundations/nodetext: the node script's text format and the kernel oom-kill line (#150)."""

from lib.foundations import nodetext

OS_TXT = "### meta\nhostname=n1\nkernel=6.8.0\n### kernel\nsource=journalctl\nlines=3\nc:oom_cgroup=1\nsamples:\n  something\noom_samples:\n2026-11-05T02:00:00+0000 kernel: oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=/,mems_allowed=0,oom_memcg=/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod2a2e36d9_6307_40b4_ab46_f44f16f5327b.slice,task_memcg=/x,task=java,pid=1,uid=0\n"


def test_parse_sections_and_key_values():
    sec = nodetext.parse_sections(OS_TXT)
    assert sorted(sec) == ["kernel", "meta"] and sec["meta"] == ["hostname=n1", "kernel=6.8.0"]
    assert nodetext.key_values(sec["meta"]) == {"hostname": "n1", "kernel": "6.8.0"}
    assert nodetext.parse_sections("no header line")["_head"] == ["no header line"]


def test_parse_kernel_reads_counts_samples_and_oom_kills():
    kern = nodetext.parse_kernel(nodetext.parse_sections(OS_TXT)["kernel"])
    assert kern["source"] == "journalctl" and kern["lines"] == 3 and kern["counts"] == {"oom_cgroup": 1} and kern["oom_section"] is True
    assert kern["samples"] == ["  something"] and len(kern["oom_kills"]) == 1
    assert kern["oom_kills"][0]["pod_uid"] == "2a2e36d9-6307-40b4-ab46-f44f16f5327b" and kern["oom_kills"][0]["node_level"] is False


def test_kernel_oom_kills_reads_only_the_nodes_whose_file_exists(tmp_path):
    (tmp_path / "logs" / "node" / "n1").mkdir(parents=True)
    (tmp_path / "logs" / "node" / "n1" / "os.txt").write_text(OS_TXT)
    out = nodetext.kernel_oom_kills(tmp_path, ["n1", "n2"])
    assert list(out) == ["n1"] and out["n1"]["oom_cgroup_count"] == 1 and len(out["n1"]["kills"]) == 1 and out["n1"]["source"] == "journalctl"
