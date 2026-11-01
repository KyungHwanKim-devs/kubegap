"""`cases` on a check: the public incident write-ups the report may cite. Shape only; reachability is checked by the person who adds a case."""

from __future__ import annotations

import re
from pathlib import Path

from lib import paths, rubric

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


def test_catalog_counts_cases():
    text = (Path(paths.ROOT) / "docs" / "CHECKS.md").read_text(encoding="utf-8")
    n = sum(1 for c in _checks() if c.get("cases"))
    assert f"{n} checks carry a public case" in text, "run `scripts/kubegap checks --markdown > docs/CHECKS.md`"
