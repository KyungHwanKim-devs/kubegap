"""#22: a step that writes its output file with only errors (every AWS call refused) is not a read, so the summary says not available and the check skips instead of passing on nothing. Measured on the EKS cluster with a principal that has cluster access and no IAM policy."""

import json

from lib.summaries import eksplatform


def _w(p, name, doc):
    (p / "aws").mkdir(exist_ok=True)
    (p / "aws" / name).write_text(json.dumps(doc))


def test_quota_usage_with_only_errors_is_not_available(tmp_path):
    _w(tmp_path, "cw-quota-usage.json", {"mode": "quotas", "items": {}, "meta": {}, "queries": 0, "errors": ["aws/service-quotas-ec2.json missing (earlier step failed?)"]})
    out = eksplatform._quotas(tmp_path)
    assert out["available"] is False and "service-quotas-ec2" in out["error"]


def test_ebs_metrics_with_only_errors_is_not_available(tmp_path):
    _w(tmp_path, "cw-ebs-volumes.json", {"mode": "static", "items": {}, "meta": {}, "queries": 0, "errors": ["aws/ec2-volumes.json missing (earlier step failed?)"]})
    out = eksplatform._ebs(tmp_path, {})
    assert out["available"] is False and "ec2-volumes" in out["error"]


def test_empty_but_clean_results_stay_available(tmp_path):
    _w(tmp_path, "cw-quota-usage.json", {"mode": "quotas", "items": {}, "meta": {}, "queries": 0, "errors": []})
    assert eksplatform._quotas(tmp_path)["available"] is True
