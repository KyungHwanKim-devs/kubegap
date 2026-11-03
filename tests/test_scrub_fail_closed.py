"""kubectl output is scrubbed before it reaches disk, and a scrub failure writes nothing (#84).

A fake kubectl on PATH prints a List with a ConfigMap whose value is a canary; the tests assert the canary is never on disk,
and that when the scrubber raises, no file exists and the step, kind or inventory entry records "scrub failed".
"""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from lib import collect, discover, scrub, shell, summarize, yamlite
from lib.config import Config
from lib.runlog import RunLog, read_runlog

CANARY = "CANARY-9f3a"
LIST = {"kind": "List", "apiVersion": "v1", "items": [{"kind": "ConfigMap", "apiVersion": "v1", "metadata": {"name": "c", "namespace": "n"}, "data": {"PASSWORD": CANARY}}]}


@pytest.fixture
def fake_kubectl(tmp_path, monkeypatch):
    """A kubectl that prints LIST for `get`, a one-line table for `api-resources`, and the List again for `version`."""
    d = tmp_path / "bin"
    d.mkdir()
    script = d / "kubectl"
    # kubectl api-resources -o wide is parsed by column start positions, so header and row must line up
    table = "".join(c.ljust(13) for c in ("NAME", "SHORTNAMES", "APIVERSION", "NAMESPACED", "KIND")).rstrip() + "\\n" + "".join(c.ljust(13) for c in ("configmaps", "cm", "v1", "true", "ConfigMap")).rstrip() + "\\n"
    script.write_text('#!/bin/sh\ncase "$*" in\n  *api-resources*) printf "' + table + "\";;\n  *) cat <<'EOF'\n" + json.dumps(LIST) + "\nEOF\n;;\nesac\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{d}{os.pathsep}{os.environ['PATH']}")
    return script


def _ctx(tmp_path, inv=None):
    log = RunLog(tmp_path / "run.log")
    return collect.StepContext(name="core", folder=tmp_path, context=None, cfg=Config(), inv=inv or {}, snap=tmp_path, log=log, kubeconfig=None, prom=None, stores=None, node_access=None, echo=None, state=collect.CollectState())


def _canary_on_disk(root: Path) -> list[str]:
    """Files under root that still carry the canary; the fake kubectl under bin/ carries it by design and is skipped."""
    return [str(p) for p in root.rglob("*") if p.is_file() and "bin" not in p.relative_to(root).parts and CANARY in p.read_text(encoding="utf-8", errors="replace")]


# ---------- shell.run transform ----------


def test_shell_run_writes_only_what_the_transform_returns(tmp_path):
    out = tmp_path / "x.json"
    r = shell.run([sys.executable, "-c", f"print({json.dumps(json.dumps(LIST))})"], out_path=out, transform=lambda t: t.replace(CANARY, "<gone>"))
    assert r.ok and out.is_file()
    assert CANARY not in out.read_text() and "<gone>" in out.read_text()


def test_shell_run_writes_nothing_and_fails_when_the_transform_raises(tmp_path):
    out = tmp_path / "x.json"
    log = RunLog(tmp_path / "run.log")

    def boom(t):
        raise scrub.ScrubFailed("scrub failed: RuntimeError: boom")

    r = shell.run([sys.executable, "-c", "print('{}')"], out_path=out, transform=boom, id="t", log=log)
    assert r.ok is False and r.code == 0
    assert r.error == "scrub failed: RuntimeError: boom"
    assert not out.exists() and [p.name for p in tmp_path.iterdir()] == ["run.log"]
    rec = next(x for x in read_runlog(tmp_path / "run.log") if x.get("kind") == "command")
    assert rec["error"] == "scrub failed: RuntimeError: boom" and rec["out"] is None


def test_shell_run_without_transform_is_unchanged(tmp_path):
    out = tmp_path / "x.txt"
    r = shell.run([sys.executable, "-c", "print('hi')"], out_path=out)
    assert r.ok and out.read_text() == "hi\n"


# ---------- _step_kubectl ----------


def test_step_kubectl_scrubs_before_the_file_exists(tmp_path, fake_kubectl, monkeypatch):
    writes = []
    real = shell.write_private
    monkeypatch.setattr(shell, "write_private", lambda path, text, **kw: (writes.append((path, text)), real(path, text, **kw)))
    ctx = _ctx(tmp_path)
    res = collect._step_kubectl(ctx, {"id": "events", "type": "kubectl", "args": ["get", "events", "-A", "-o", "json"], "out": "events.json"})
    assert res == {"ok": True, "items": 1, "error": None}
    assert len(writes) == 1 and CANARY not in writes[0][1], "exactly one write, and it is the scrubbed text"
    doc = json.loads((tmp_path / "events.json").read_text())
    assert doc["items"][0]["data"]["PASSWORD"] == {"len": len(CANARY), "shape": scrub.shape(CANARY)}
    assert _canary_on_disk(tmp_path) == []


def test_step_kubectl_writes_nothing_when_scrubbing_raises(tmp_path, fake_kubectl, monkeypatch):
    def boom(obj):
        raise RuntimeError("boom")

    monkeypatch.setattr(scrub, "scrub_objects", boom)
    ctx = _ctx(tmp_path)
    res = collect._step_kubectl(ctx, {"id": "events", "type": "kubectl", "args": ["get", "events", "-A", "-o", "json"], "out": "events.json"})
    assert res["ok"] is False and res["items"] is None
    assert res["error"] == "scrub failed: RuntimeError: boom"
    assert not (tmp_path / "events.json").exists() and _canary_on_disk(tmp_path) == []
    rec = next(x for x in read_runlog(tmp_path / "run.log") if x.get("kind") == "command")
    assert rec["id"] == "core.events" and rec["error"].startswith("scrub failed") and rec["out"] is None
    assert [x["id"] for x in summarize.summarize_run(tmp_path)["failed"]] == ["core.events"]  # report section 7-1 counts it among the failed commands


def test_step_kubectl_per_node_json_is_scrubbed_too(tmp_path, fake_kubectl):
    ctx = _ctx(tmp_path, inv={"nodes": {"nodes": [{"name": "n1"}]}})
    res = collect._step_kubectl(ctx, {"id": "kubelet-configz", "type": "kubectl", "for_each": "nodes", "args": ["get", "--raw", "/api/v1/nodes/{item}/proxy/configz"], "out": "logs/node/{item}/kubelet-configz.json"})
    assert res["ok"] and res["nodes"]["n1"]["out"] == "logs/node/n1/kubelet-configz.json"
    assert _canary_on_disk(tmp_path) == []


def test_step_kubectl_text_output_is_written_as_is(tmp_path, fake_kubectl):
    ctx = _ctx(tmp_path)
    res = collect._step_kubectl(ctx, {"id": "top.nodes", "type": "kubectl", "args": ["top", "nodes"], "out": "metrics/top-nodes.txt"})
    assert res["ok"] and res["items"] is None
    assert CANARY in (tmp_path / "metrics" / "top-nodes.txt").read_text()  # not JSON-scrubbed: a text table carries no Secret the scrubber knows


# ---------- json_scrubber and the metrics filter ----------


def test_json_scrubber_wraps_any_parse_failure_as_scrub_failed(monkeypatch):
    fn, _ = scrub.json_scrubber()

    def boom(text):
        raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setattr(scrub.json, "loads", boom)
    with pytest.raises(scrub.ScrubFailed, match=r"^scrub failed: RecursionError: maximum recursion depth exceeded$"):
        fn("{}")


def test_shell_run_names_the_type_of_an_unnamed_exception(tmp_path):
    def boom(t):
        raise ValueError("odd")

    r = shell.run([sys.executable, "-c", "print('{}')"], out_path=tmp_path / "x", transform=boom)
    assert r.ok is False and r.error == "ValueError: odd" and not (tmp_path / "x").exists()


def test_every_keep_pattern_in_the_collectors_compiles():
    import re

    bad = []
    for f in sorted(Path(collect.__file__).resolve().parent.parent.glob("collectors/*/collect.yaml")):
        for st in yamlite.load_file(f) or []:
            if isinstance(st, dict) and st.get("keep"):
                try:
                    re.compile(st["keep"])
                except re.error as e:
                    bad.append(f"{f.parent.name}/{st.get('id')}: {e}")
    assert bad == []


def test_json_scrubber_leaves_non_json_text_alone():
    fn, info = scrub.json_scrubber()
    assert fn("not json") == "not json" and info["items"] is None


def test_json_scrubber_counts_items_and_scrubs():
    fn, info = scrub.json_scrubber()
    out = fn(json.dumps(LIST))
    assert info["items"] == 1 and CANARY not in out


def test_metrics_filter_drops_comments_buckets_and_keeps_matches():
    text = '# HELP x\nfoo_total 1\nfoo_bucket{le="1"} 2\nbar_total 3\n'
    assert collect._metrics_filter(None)(text) == "foo_total 1\nbar_total 3\n"
    assert collect._metrics_filter("^bar")(text) == "bar_total 3\n"
    assert collect._metrics_filter("(")(text) == "foo_total 1\nbar_total 3\n"  # invalid regex: keep every non-comment line
    assert collect._metrics_filter(None)("# only\n") == ""


# ---------- dump_all ----------


def test_dump_all_scrubs_in_memory(tmp_path, fake_kubectl):
    log = RunLog(tmp_path / "run.log")
    (tmp_path / "objects").mkdir()
    s = collect.dump_all(None, None, tmp_path, [], 10, log, "core")
    assert s["kinds"] == 1 and s["failed"] == {}
    assert (tmp_path / "objects" / "configmaps.json").is_file() and _canary_on_disk(tmp_path) == []


def test_dump_all_records_a_scrub_failure_and_writes_nothing(tmp_path, fake_kubectl, monkeypatch):
    def boom(obj):
        raise RuntimeError("boom")

    monkeypatch.setattr(scrub, "scrub_objects", boom)
    log = RunLog(tmp_path / "run.log")
    (tmp_path / "objects").mkdir()
    s = collect.dump_all(None, None, tmp_path, [], 10, log, "core")
    assert s["kinds"] == 0 and s["failed"] == {"configmaps": "scrub failed: RuntimeError: boom"} and s["ok"] is False
    assert list((tmp_path / "objects").iterdir()) == [] and _canary_on_disk(tmp_path) == []
    assert [x["id"] for x in summarize.summarize_run(tmp_path)["failed"]] == ["core.scrub-configmaps"]


# ---------- discover.write_objects ----------


def test_discover_records_a_scrub_failure_per_kind_and_writes_the_others(tmp_path, monkeypatch):
    """Drive discover's write_objects shape directly (discover() needs a cluster): one kind fails to scrub, the other is written, inventory names the failure.
    The path from `failures` to inventory.json `fetch_failures` is covered by the source assertion below, not by running discover()."""
    objs = {"configmaps": json.loads(json.dumps(LIST)), "nodes": {"kind": "List", "items": []}}
    failures: dict = {}

    def scrub_objects(obj):
        if obj is objs["configmaps"]:
            raise RuntimeError("boom")
        return obj

    monkeypatch.setattr(scrub, "scrub_objects", scrub_objects)
    for kind, data in objs.items():
        err = scrub.scrub_or_error(data)
        if err:
            failures[kind] = err
            continue
        discover.write_private(tmp_path / "objects" / f"{kind}.json", json.dumps(data))
    assert failures == {"configmaps": "scrub failed: RuntimeError: boom"}
    assert sorted(p.name for p in (tmp_path / "objects").iterdir()) == ["nodes.json"]
    assert _canary_on_disk(tmp_path) == []


def test_discover_source_uses_scrub_or_error_before_every_object_write():
    src = (Path(discover.__file__)).read_text(encoding="utf-8")
    body = src[src.index("def write_objects()") : src.index("ctx_info = kube.context_info")]
    assert "scrub.scrub_or_error(data)" in body and "failures[kind] = err" in body and "scrub_objects(" not in body
