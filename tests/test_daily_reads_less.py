"""A daily run is the light one: it reads the Kubernetes API and the stores only, keeps no literal environment value of an application, keeps no
log text, and asks only what it needs. These tests hold each of those promises where the code makes it (README, docs/DATA.md state them)."""

from __future__ import annotations

import json

from lib.commands import firstrun
from lib.foundations import paths, scrub, units
from lib.foundations.config import Config


def _pod(ns: str) -> dict:
    env = [{"name": "FEATURE_GATES", "value": "SpotToSpotConsolidation=true"}, {"name": "DB_PASSWORD", "value": "hunter2hunter2"}, {"name": "FROM_REF", "valueFrom": {"secretKeyRef": {"name": "s", "key": "k"}}}]
    c = {
        "name": "c",
        "image": "app:1",
        "command": ["sh", "-c"],
        "args": ["mysqldump -h db -psecretsecret > /dump/a.sql"],
        "env": json.loads(json.dumps(env)),
        "livenessProbe": {"exec": {"command": ["redis-cli", "-a", "secretsecret", "ping"]}},
    }
    return {"kind": "Pod", "metadata": {"namespace": ns, "name": "p"}, "spec": {"containers": [c]}}


def _cm(ns: str) -> dict:
    managed = [{"manager": "argocd-controller", "operation": "Apply", "time": "2026-11-01T00:00:00Z", "fieldsV1": {"f:data": {"f:DB_HOST": {}, "f:app.ini": {}}, "f:metadata": {"f:labels": {"f:app": {}}}}}]
    return {"kind": "ConfigMap", "metadata": {"namespace": ns, "name": "settings", "labels": {"app": "x"}, "managedFields": managed}, "data": {"DB_HOST": "db.internal", "app.ini": "password = secretsecret\n"}}


def test_a_daily_run_keeps_no_literal_environment_value_outside_the_system_namespaces():
    full = scrub.scrub_objects({"kind": "List", "items": [_pod("shop")]})["items"][0]["spec"]["containers"][0]["env"]
    assert full[0]["value"] == "SpotToSpotConsolidation=true" and "value" not in full[1]  # a full run drops the credential-like name only
    light = scrub.scrub_objects({"kind": "List", "items": [_pod("shop"), _pod("kube-system"), _pod("karpenter")]}, app_settings=False)["items"]
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


def test_a_daily_run_keeps_no_command_no_args_and_no_configmap_key_of_an_application():
    """What an application is started and configured with can hold a credential (a password on a command line, in a probe, as a key's value), and
    a daily run is for the user who does not want that on disk: it is dropped before a file exists, and the system namespaces keep theirs."""
    app, system = scrub.scrub_objects({"kind": "List", "items": [_pod("shop"), _pod("kube-system")]}, app_settings=False)["items"]
    c = app["spec"]["containers"][0]
    assert "command" not in c and "args" not in c and c[scrub.MARK]["items_dropped"] == {"command": 2, "args": 1}  # "has a command" stays readable
    assert "command" not in c["livenessProbe"]["exec"] and c["image"] == "app:1"
    assert "secretsecret" not in json.dumps(app)
    assert system["spec"]["containers"][0]["args"] and system["spec"]["containers"][0]["livenessProbe"]["exec"]["command"]
    cm_app, cm_sys = scrub.scrub_objects({"kind": "List", "items": [_cm("shop"), _cm("kube-system")]}, app_settings=False)["items"]
    assert "data" not in cm_app and cm_app[scrub.MARK]["keys_dropped"] == 2 and cm_app[scrub.MARK]["data_chars"] > 0 and cm_app["metadata"]["labels"] == {"app": "x"}
    assert "DB_HOST" not in json.dumps(cm_app) and "app.ini" not in json.dumps(cm_app)  # not in managedFields either, which name every key a manager wrote
    assert cm_app["metadata"]["managedFields"][0] == {"manager": "argocd-controller", "operation": "Apply", "time": "2026-11-01T00:00:00Z", "fieldsV1": {"f:data": {}, "f:metadata": {}}}  # who wrote data, and when, stays
    assert set(cm_sys["data"]) == {"DB_HOST", "app.ini"} and "secretsecret" not in json.dumps(cm_sys)  # keys with length and shape, as in a full run
    full = scrub.scrub_objects({"kind": "List", "items": [_pod("shop"), _cm("shop")]})["items"]
    assert full[0]["spec"]["containers"][0]["command"] == ["sh", "-c"] and set(full[1]["data"]) == {"DB_HOST", "app.ini"}  # a full run collects app-settings


def test_the_aws_steps_and_the_node_steps_do_not_run_in_a_daily_run():
    daily = units.of_mode("daily")
    for collector, st in paths.collect_steps():
        if st["type"] in ("aws", "alb-metrics", "cw-metrics", "cwlogs", "node", "tool"):
            assert st["unit"] not in daily, f"{collector}/{st['id']} ({st['type']}) would run in a daily run"


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
