"""ConfigMaps changed after the pods that use them started (hygiene.config_changes): reference modes, the managedFields change time, immutable ConfigMaps, and the section being absent when no change times were collected."""

from __future__ import annotations

import json

from lib.summaries import hygiene


def _write(tmp_path, stem, items):
    (tmp_path / "objects").mkdir(exist_ok=True)
    (tmp_path / "objects" / f"{stem}.json").write_text(json.dumps({"items": items}), encoding="utf-8")


def _cm(ns, name, times=(), immutable=False, manager="kubectl-client-side-apply"):
    md = {"namespace": ns, "name": name}
    if times:
        md["managedFields"] = [{"manager": manager, "operation": "Update", "time": t, "fieldsV1": {"f:data": {"f:k": {}}}} for t in times]
    cm = {"metadata": md, "data": {"k": {"len": 3, "shape": "word"}}}
    if immutable:
        cm["immutable"] = True
    return cm


def _pod(ns, name, started, spec):
    return {"metadata": {"namespace": ns, "name": name}, "spec": spec, "status": {"phase": "Running", "startTime": started}}


ENV_SPEC = {"containers": [{"name": "app", "env": [{"name": "X", "valueFrom": {"configMapKeyRef": {"name": "app-cfg", "key": "k"}}}]}]}
FILE_SPEC = {"volumes": [{"name": "cfg", "configMap": {"name": "app-cfg"}}], "containers": [{"name": "app", "volumeMounts": [{"name": "cfg", "mountPath": "/etc/app"}]}]}
SUBPATH_SPEC = {"volumes": [{"name": "cfg", "configMap": {"name": "app-cfg"}}], "containers": [{"name": "app", "volumeMounts": [{"name": "cfg", "mountPath": "/etc/app/app.yaml", "subPath": "app.yaml"}]}]}
ENVFROM_PROJECTED_SPEC = {
    "volumes": [{"name": "all", "projected": {"sources": [{"configMap": {"name": "shared"}}]}}],
    "containers": [{"name": "app", "envFrom": [{"configMapRef": {"name": "app-cfg"}}], "volumeMounts": [{"name": "all", "mountPath": "/all"}]}],
}


def _modes(spec):
    return {k: v["modes"] for k, v in hygiene._cm_refs(spec).items()}


def test_ref_modes():
    assert _modes(ENV_SPEC) == {"app-cfg": {"env"}}
    assert _modes(FILE_SPEC) == {"app-cfg": {"file"}}
    assert _modes(SUBPATH_SPEC) == {"app-cfg": {"subpath"}}
    assert _modes(ENVFROM_PROJECTED_SPEC) == {"app-cfg": {"env"}, "shared": {"file"}}
    assert _modes({"volumes": [{"name": "cfg", "configMap": {"name": "unmounted"}}], "containers": [{"name": "a"}]}) == {"unmounted": {"file"}}
    expr = {"volumes": [{"name": "cfg", "configMap": {"name": "app-cfg"}}], "containers": [{"name": "app", "volumeMounts": [{"name": "cfg", "mountPath": "/etc/app/x", "subPathExpr": "$(POD_NAME)"}]}]}
    assert _modes(expr) == {"app-cfg": {"subpath"}}
    two = {"volumes": [{"name": "all", "projected": {"sources": [{"configMap": {"name": "a"}}, {"configMap": {"name": "b"}}]}}], "containers": [{"name": "app", "volumeMounts": [{"name": "all", "mountPath": "/all/x", "subPath": "x"}]}]}
    assert _modes(two) == {"a": {"subpath"}, "b": {"subpath"}}
    assert hygiene._cm_refs(ENV_SPEC)["app-cfg"]["containers"] == {"app"}


def test_section_absent_without_change_times(tmp_path):
    _write(tmp_path, "configmaps", [_cm("prod", "app-cfg")])
    _write(tmp_path, "pods", [_pod("prod", "app-1", "2026-10-01T00:00:00Z", ENV_SPEC)])
    assert hygiene._config_changes(hygiene._Ctx(tmp_path, {})) is None


def test_env_reference_changed_after_start_needs_restart(tmp_path):
    _write(tmp_path, "configmaps", [_cm("prod", "app-cfg", ["2026-09-01T00:00:00Z", "2026-10-05T12:00:00Z"], manager="argocd-controller")])
    _write(tmp_path, "pods", [_pod("prod", "app-6d7ff4dcdb-aaaaa", "2026-10-01T00:00:00Z", ENV_SPEC), _pod("prod", "app-6d7ff4dcdb-bbbbb", "2026-10-06T00:00:00Z", ENV_SPEC)])
    out = hygiene._config_changes(hygiene._Ctx(tmp_path, {"namespaces": {"prod_like": ["prod"]}}))
    assert out["configmaps_with_time"] == 1 and out["pods_checked"] == 2
    assert len(out["restart_needed"]) == 1 and out["refresh_only"] == []
    r = out["restart_needed"][0]
    assert r["configmap"] == "app-cfg" and r["pods"] == ["app-6d7ff4dcdb-aaaaa"] and r["workloads"] == ["prod/app"]
    assert r["changed_by"] == "argocd-controller" and r["changed_at"].startswith("2026-10-05T12:00:00") and r["prod"] is True
    assert r["ref_modes"] == ["env"] and r["restart_needed_pods"] == 1 and r["stale_hours"] == 108.0


def test_file_mount_is_refresh_only_and_subpath_is_not(tmp_path):
    _write(tmp_path, "configmaps", [_cm("prod", "app-cfg", ["2026-10-05T00:00:00Z"])])
    _write(tmp_path, "pods", [_pod("prod", "file-1", "2026-10-01T00:00:00Z", FILE_SPEC), _pod("prod", "sub-1", "2026-10-01T00:00:00Z", SUBPATH_SPEC)])
    out = hygiene._config_changes(hygiene._Ctx(tmp_path, {}))
    r = out["stale"][0]
    assert r["restart_needed_pods"] == 1 and r["refresh_only_pods"] == 1 and sorted(r["ref_modes"]) == ["file", "subpath"]
    assert out["restart_needed"] and not out["refresh_only"]


def test_unchanged_and_not_running_are_ignored_and_a_recreated_immutable_counts(tmp_path):
    # an immutable ConfigMap cannot be edited: one that exists since before the pod started is not a change, one created after it (deleted and recreated) is
    old_imm = _cm("prod", "imm-old", ["2026-09-01T00:00:00Z"], immutable=True)
    old_imm["metadata"]["creationTimestamp"] = "2026-09-01T00:00:00Z"
    new_imm = _cm("prod", "app-cfg", ["2026-10-05T00:00:00Z"], immutable=True)
    new_imm["metadata"]["creationTimestamp"] = "2026-10-05T00:00:00Z"
    _write(tmp_path, "configmaps", [new_imm, old_imm, _cm("prod", "old-cfg", ["2026-09-01T00:00:00Z"])])
    pending = _pod("prod", "p-1", "2026-10-01T00:00:00Z", ENV_SPEC)
    pending["status"]["phase"] = "Pending"
    old_spec = {"containers": [{"name": "app", "envFrom": [{"configMapRef": {"name": "old-cfg"}}]}]}
    imm_spec = {"containers": [{"name": "app", "envFrom": [{"configMapRef": {"name": "imm-old"}}]}]}
    _write(tmp_path, "pods", [pending, _pod("prod", "app-1", "2026-10-01T00:00:00Z", ENV_SPEC), _pod("prod", "old-1", "2026-10-01T00:00:00Z", old_spec), _pod("prod", "imm-1", "2026-10-01T00:00:00Z", imm_spec)])
    out = hygiene._config_changes(hygiene._Ctx(tmp_path, {}))
    assert out["pods_checked"] == 3
    assert [(r["configmap"], r["changed_at"][:10]) for r in out["stale"]] == [("app-cfg", "2026-10-05")]  # the recreation time is the change time


def test_oldest_reader_decides_when_only_a_sidecar_restarted(tmp_path):
    _write(tmp_path, "configmaps", [_cm("prod", "app-cfg", ["2026-10-05T00:00:00Z"])])
    spec = {"containers": [{"name": "app", "envFrom": [{"configMapRef": {"name": "app-cfg"}}]}, {"name": "sidecar", "envFrom": [{"configMapRef": {"name": "app-cfg"}}]}]}
    pod = _pod("prod", "app-1", "2026-10-01T00:00:00Z", spec)
    pod["status"]["containerStatuses"] = [
        {"name": "app", "state": {"running": {"startedAt": "2026-10-01T00:00:00Z"}}},
        {"name": "sidecar", "state": {"running": {"startedAt": "2026-10-06T00:00:00Z"}}},
    ]
    _write(tmp_path, "pods", [pod])
    out = hygiene._config_changes(hygiene._Ctx(tmp_path, {}))
    assert [r["configmap"] for r in out["stale"]] == ["app-cfg"]  # the app container still runs on the old value


def test_system_root_ca_configmap_is_ignored(tmp_path):
    _write(tmp_path, "configmaps", [_cm("prod", "kube-root-ca.crt", ["2026-10-05T00:00:00Z"], manager="kube-controller-manager")])
    spec = {
        "volumes": [{"name": "kube-api-access", "projected": {"sources": [{"serviceAccountToken": {"path": "token"}}, {"configMap": {"name": "kube-root-ca.crt"}}]}}],
        "containers": [{"name": "app", "volumeMounts": [{"name": "kube-api-access", "mountPath": "/var/run/secrets/kubernetes.io/serviceaccount"}]}],
    }
    _write(tmp_path, "pods", [_pod("prod", "app-1", "2026-10-01T00:00:00Z", spec)])
    assert hygiene._config_changes(hygiene._Ctx(tmp_path, {})) is None


def test_metadata_only_write_is_not_a_change(tmp_path):
    """A label or annotation write by another manager bumps its managedFields time but did not change the configuration."""
    cm = _cm("prod", "app-cfg", ["2026-09-01T00:00:00Z"])
    cm["metadata"]["managedFields"][0]["fieldsV1"] = {"f:data": {"f:k": {}}}
    cm["metadata"]["managedFields"].append({"manager": "argocd-controller", "operation": "Update", "time": "2026-10-05T00:00:00Z", "fieldsV1": {"f:metadata": {"f:annotations": {"f:argocd.argoproj.io/tracking-id": {}}}}})
    _write(tmp_path, "configmaps", [cm])
    _write(tmp_path, "pods", [_pod("prod", "app-1", "2026-10-01T00:00:00Z", ENV_SPEC)])
    out = hygiene._config_changes(hygiene._Ctx(tmp_path, {}))
    assert out["configmaps_with_time"] == 1 and out["stale"] == []


def test_container_restarted_after_change_holds_new_value(tmp_path):
    _write(tmp_path, "configmaps", [_cm("prod", "app-cfg", ["2026-10-05T00:00:00Z"])])
    restarted = _pod("prod", "app-1", "2026-10-01T00:00:00Z", ENV_SPEC)
    restarted["status"]["containerStatuses"] = [{"name": "app", "state": {"running": {"startedAt": "2026-10-06T00:00:00Z"}}}]
    stale = _pod("prod", "app-2", "2026-10-01T00:00:00Z", ENV_SPEC)
    stale["status"]["containerStatuses"] = [{"name": "app", "state": {"running": {"startedAt": "2026-10-01T00:00:10Z"}}}]
    _write(tmp_path, "pods", [restarted, stale])
    out = hygiene._config_changes(hygiene._Ctx(tmp_path, {}))
    assert [r["pods"] for r in out["restart_needed"]] == [["app-2"]]
