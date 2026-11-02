"""`cases` on a check: the public incident write-ups the report may cite. Shape only; reachability is checked by the person who adds a case.

`measured` holds what was measured on the clusters the check was written on; it stays out of `why` and `notes` so a report never cites it as a case."""

from __future__ import annotations

import re
from pathlib import Path

from lib import evaluate, paths, rubric, selftest

# "Company YEAR" inside prose: one to three capitalised words followed by a year. Words that are not a company are excluded.
NAME_YEAR_IN_WHY = re.compile(r"\b([A-Z][A-Za-z0-9.&'-]+(?: [A-Z][A-Za-z0-9.&'-]+){0,2}),? \(?((?:19|20)\d\d)\)?")
NOT_A_COMPANY = {
    "Kubernetes",
    "EKS",
    "GKE",
    "AKS",
    "KubeCon",
    "CVE",
    "SRE",
    "Since",
    "In",
    "On",
    "At",
    "From",
    "After",
    "Before",
    "Until",
    "By",
    "The",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Sept",
    "Oct",
    "Nov",
    "Dec",
    "Linux",
    "Ubuntu",
    "AWS",
    "Amazon",
    "Google",
    "Azure",
    "Karpenter",
    "Helm",
    "Istio",
    "Argo",
    "Argo CD",
    "Docker Hub",
}

# A measurement on the clusters the check was written on, written into prose: "Measured on a real EKS cluster: …", "(seen on a first real run)".
MEASUREMENT_IN_PROSE = re.compile(r"\bmeasured\b|\b(?:observed|seen) on\b|\bfirst real run|\bon (?:a )?real (?:EKS |k3s )?clusters?\b|\bk3s k3s\b", re.IGNORECASE)


def _checks():
    checks, errors = rubric.load_checks([p.name for p in sorted(paths.COLLECTORS_DIR.iterdir()) if (p / "checks.yaml").is_file()])
    assert not errors, errors
    return checks


def test_cases_have_who_and_https_url_and_no_duplicates():
    for c in _checks():
        cases = c.get("cases") or []
        assert isinstance(cases, list), c["id"]
        urls = [x["url"] for x in cases]
        assert len(urls) == len(set(urls)), f"{c['id']}: duplicate case url"
        for x in cases:
            assert set(x) >= {"who", "url"}, f"{c['id']}: case needs who and url: {x}"
            assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .&'()/-]+ (19|20)\d\d", x["who"]), f"{c['id']}: who is 'Company YEAR': {x['who']!r}"
            assert x["url"].startswith("https://") and " " not in x["url"], f"{c['id']}: url: {x['url']!r}"


def test_no_name_only_citation_outside_cases():
    """A company and year named in `why` or `notes` must have its write-up under `cases`; a name without a link cannot be checked by the reader."""
    for c in _checks():
        who = " ".join(x["who"] for x in c.get("cases") or [])
        for k in ("why", "notes"):
            for m in NAME_YEAR_IN_WHY.finditer(str(c.get(k) or "")):
                name = m.group(1)
                if name in NOT_A_COMPANY or name.split()[0] in NOT_A_COMPANY:
                    continue
                assert name.split()[-1] in who or name in who, f"{c['id']}: {k} names {m.group(0)!r} but cases has no entry for it"


def test_measurements_live_in_measured_not_in_why_or_notes():
    """The report takes cases from `cases` only and labels `measured` separately; a measurement left in `why` or `notes` reads as a case."""
    for c in _checks():
        for k in ("why", "notes"):
            m = MEASUREMENT_IN_PROSE.search(str(c.get(k) or ""))
            assert not m, f"{c['id']}: {k} carries a measurement ({m.group(0)!r}); move it to measured"


def test_measured_reaches_the_findings(tmp_path):
    c = next(c for c in _checks() if c["id"] == "resilience.prod-concentration")
    selftest._build_snapshot(tmp_path, c, c["test"]["cases"][0], "prod")
    out = evaluate.evaluate(tmp_path, {}, echo=None)
    f = next(f for f in out["findings"] if f["check"] == c["id"])
    assert f["measured"] == c["measured"] and f["cases"] == c["cases"]


def test_catalog_counts_cases():
    text = (Path(paths.ROOT) / "docs" / "CHECKS.md").read_text(encoding="utf-8")
    n = sum(1 for c in _checks() if c.get("cases"))
    assert f"{n} checks carry a public case" in text, "run `scripts/kubegap checks --markdown > docs/CHECKS.md`"
