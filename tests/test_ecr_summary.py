"""The ECR summary carries its units in the key names: `largest_repos` and `repos_stale_pull` are labeled rows with a `gib` key, not bare tuples (issue #10, a repository total once read as a 96 GB image)."""

from __future__ import annotations

import json

from lib.summaries import ecr


def _write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _snapshot(tmp_path):
    _write(
        tmp_path / "aws" / "ecr-repositories.json",
        {
            "repositories": [
                {"repositoryName": "app-a", "registryId": "123456789012", "createdAt": "2024-01-01T00:00:00+00:00"},
                {"repositoryName": "app-b", "registryId": "123456789012", "createdAt": "2024-01-01T00:00:00+00:00"},
            ]
        },
    )
    _write(
        tmp_path / "aws" / "ecr-images" / "app-a.json",
        {"imageDetails": [{"imageSizeInBytes": 8 * 1024**3, "imageTags": ["v1"], "imagePushedAt": "2026-04-01T00:00:00+00:00", "lastRecordedPullTime": "2026-05-01T00:00:00+00:00"}]},
    )
    _write(
        tmp_path / "aws" / "ecr-images" / "app-b.json",
        {"imageDetails": [{"imageSizeInBytes": 2 * 1024**3, "imageTags": ["v2"], "imagePushedAt": "2026-10-01T00:00:00+00:00", "lastRecordedPullTime": "2026-10-31T00:00:00+00:00"}]},
    )
    _write(tmp_path / "objects" / "pods.json", {"items": []})
    return tmp_path


def test_largest_repos_are_labeled_rows_with_gib(tmp_path):
    out = ecr.analyze(_snapshot(tmp_path), {"taken_at": "2026-11-01T00:00:00+00:00", "eks": {"account": "123456789012"}})
    assert out["summary"]["largest_repos"] == [{"name": "app-a", "gib": 8.0}, {"name": "app-b", "gib": 2.0}]


def test_repos_stale_pull_are_labeled_rows_with_gib_and_days(tmp_path):
    out = ecr.analyze(_snapshot(tmp_path), {"taken_at": "2026-11-01T00:00:00+00:00", "eks": {"account": "123456789012"}})
    assert out["summary"]["repos_stale_pull"] == [{"name": "app-a", "gib": 8.0, "days_since_pull": 184}]
