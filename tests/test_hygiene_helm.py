"""The Helm section of the hygiene summary: release metadata only, and an absent helm-list.json explained by its real cause (no secrets permission, tool missing, daily mode)."""

from __future__ import annotations

import datetime as _dt
import json

from lib import hygiene


def _write(tmp_path, steps):
    (tmp_path / "collect-result.json").write_text(json.dumps({"core": {"collector": "core", "steps": {"helm-list": steps}}}), encoding="utf-8")


def test_missing_note_distinguishes_permission_tool_and_mode(tmp_path):
    _write(tmp_path, {"ok": False, "error": 'Error: list: failed to list: secrets is forbidden: User "kubegap" cannot list resource "secrets" in API group "" at the cluster scope'})
    n = hygiene._helm_missing_note(tmp_path)
    assert "Secrets" in n and "permission" in n and "ClusterRole" in n
    _write(tmp_path, {"ok": False, "skipped": "tool helm missing", "tool_missing": "helm"})
    assert "not installed" in hygiene._helm_missing_note(tmp_path)
    _write(tmp_path, {"ok": True, "skipped": "not collected in daily mode", "mode_skipped": True})
    assert "daily" in hygiene._helm_missing_note(tmp_path)
    _write(tmp_path, {"ok": False, "error": "context deadline exceeded"})
    assert "context deadline exceeded" in hygiene._helm_missing_note(tmp_path)
    (tmp_path / "collect-result.json").unlink()
    assert "missing" in hygiene._helm_missing_note(tmp_path)


def test_helm_section_has_metadata_only(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "helm-list.json").write_text(
        json.dumps([{"namespace": "prod", "name": "redis", "status": "deployed", "revision": 3, "chart": "redis-20.1.0", "app_version": "7.4", "updated": "2026-01-01 10:00:00.000000 +0000 UTC"}]), encoding="utf-8"
    )
    (tmp_path / "objects").mkdir()
    cx = hygiene._Ctx(tmp_path, {"namespaces": {"prod_like": ["prod"]}})
    h = hygiene._helm(cx, _dt.datetime(2026, 10, 27, tzinfo=_dt.UTC))
    assert h["present"] and h["count"] == 1
    r = h["releases"][0]
    assert r["chart_name"] == "redis" and r["chart_version"] == "20.1.0" and r["prod"] is True
    for k in ("user_values_keys", "user_values_count", "pure_defaults"):
        assert k not in r
    for k in ("values_read", "pure_defaults", "pure_defaults_prod"):
        assert k not in h
    assert h["stale_365d"] == [] and h["not_deployed"] == []
