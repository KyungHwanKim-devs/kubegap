"""A daily run is the light one: it reads the Kubernetes API and the stores only, keeps no literal environment value of an application, keeps no
log text, and asks only what it needs. These tests hold each of those promises where the code makes it (README, docs/DATA.md state them)."""

from __future__ import annotations

import json

from lib.collection import discover
from lib.commands import firstrun
from lib.foundations import paths, scrub
from lib.foundations.config import Config


def _pod(ns: str) -> dict:
    env = [{"name": "FEATURE_GATES", "value": "SpotToSpotConsolidation=true"}, {"name": "DB_PASSWORD", "value": "hunter2hunter2"}, {"name": "FROM_REF", "valueFrom": {"secretKeyRef": {"name": "s", "key": "k"}}}]
    return {"kind": "Pod", "metadata": {"namespace": ns, "name": "p"}, "spec": {"containers": [{"name": "c", "env": json.loads(json.dumps(env))}]}}


def test_a_daily_run_keeps_no_literal_environment_value_outside_the_system_namespaces():
    full = scrub.scrub_objects({"kind": "List", "items": [_pod("shop")]})["items"][0]["spec"]["containers"][0]["env"]
    assert full[0]["value"] == "SpotToSpotConsolidation=true" and "value" not in full[1]  # a full run drops the credential-like name only
    light = scrub.scrub_objects({"kind": "List", "items": [_pod("shop"), _pod("kube-system"), _pod("karpenter")]}, light=True)["items"]
    app, system, karpenter = (p["spec"]["containers"][0]["env"] for p in light)
    assert all("value" not in e for e in app) and app[0][scrub.MARK]["len"] == 28 and app[2]["valueFrom"]  # the name, the length and the reference stay
    assert system[0]["value"] == karpenter[0]["value"] == "SpotToSpotConsolidation=true"  # a component's setting is what the checks read
    assert "value" not in system[1]  # and a credential-like name loses its value everywhere, as before


def test_a_daily_run_asks_only_the_scale_and_the_folder_permissions(tmp_path):
    setup = {
        "cluster": {"reachable": True, "platform": "eks", "is_eks": True, "nodes": 3},
        "tools": [{"name": "krr", "present": False, "required": False}],
        "machine": {"open_dirs": [{"path": "/x", "mode": "0755"}]},
        "aws": {"ssm_document": {"present": False}},
    }
    daily = [q["id"] for q in firstrun.questions(setup, Config(), tmp_path, language="ko", mode="daily")]
    assert set(daily) <= set(firstrun.DAILY_QUESTIONS) and "scale" in daily
    assert len(firstrun.questions(setup, Config(), tmp_path, language="ko", mode="full")) > len(daily)  # the rest waits for the first full run


def test_the_aws_steps_and_the_node_steps_do_not_run_in_a_daily_run():
    for collector, st in paths.collect_steps():
        if st["type"] in ("aws", "alb-metrics", "cw-metrics", "cwlogs", "node", "tool"):
            assert st.get("modes") == ["full"], f"{collector}/{st['id']} ({st['type']}) would run in a daily run"
    assert "no AWS API call" in discover.DAILY_NO_AWS and "no node" in discover.DAILY_NO_NODES


def _snap(root, name, mode, objs):
    s = root / "c" / name
    (s / "objects").mkdir(parents=True)
    (s / "logs").mkdir()
    (s / "MODE").write_text(mode + "\n")
    (s / "events.json").write_text("{}")
    for kind, its in objs.items():
        (s / "objects" / f"{kind}.json").write_text(json.dumps({"kind": "List", "items": its}))
    return s


def _deploy(name, replicas, image="app:1"):
    return {"kind": "Deployment", "metadata": {"namespace": "shop", "name": name, "generation": replicas}, "spec": {"replicas": replicas, "template": {"spec": {"containers": [{"name": "c", "image": image}]}}}}


def test_a_daily_snapshot_keeps_a_digest_in_place_of_its_objects_and_the_next_run_still_sees_what_changed(tmp_path):
    from lib.output import diff, slim

    a = _snap(tmp_path, "2026-11-13T09-00-00", "daily", {"deployments.apps": [_deploy("web", 2), _deploy("old", 1)], "pods": [{"kind": "Pod", "metadata": {"namespace": "shop", "name": "p1"}}]})
    b = _snap(tmp_path, "2026-11-14T09-00-00", "daily", {"deployments.apps": [_deploy("web", 3), _deploy("new", 1)], "pods": []})
    before = diff.diff_objects(a, b)
    assert slim.slim(a) == ["objects/", "events.json", "logs/"] and not (a / "objects").exists() and (a / diff.DIGEST_FILE).is_file()
    assert "app:1" not in (a / diff.DIGEST_FILE).read_text()  # hashes, no value
    after = diff.diff_objects(a, b)  # the earlier run has only its digest, the new one still has its objects
    assert after == before
    assert after["added"] == [{"kind": "deployments.apps", "name": "shop/new"}] and after["removed"] == [{"kind": "deployments.apps", "name": "shop/old"}]
    assert after["changed"] == [{"kind": "deployments.apps", "name": "shop/web", "generation": [2, 3], "changed_fields": ["spec.replicas"]}]
    assert after["count_only"] == {"pods": {"before": 1, "after": 0, "delta": -1}}
    full = _snap(tmp_path, "2026-11-14T10-00-00", "full", {"pods": []})
    assert slim.slim(full) == [] and (full / "objects").is_dir()  # a full run keeps everything
