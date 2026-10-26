"""ECR summary (collector collectors/ecr).

Inputs: aws/ecr-repositories.json (discovery), aws/ecr-registry.json (replication rules), aws/ecr-scanning-configuration.json (scan type and rules), aws/ecr-pull-through-cache-rules.json,
aws/ecr-images/<repo>.json (describe-images: size, push/last pull time, tags, scan status, vulnerability summary), aws/ecr-lifecycle/<repo>.json (only repositories that have one), objects/pods.json (images the cluster uses), events.json (ErrImagePull, BackOff).
What we look at: per repository scanOnPush, tag mutability, encryption, lifecycle policy presence, image count, GiB, untagged images (attestation manifests counted separately), last push, last pull, scan summary; total GiB and monthly cost (0.10 USD/GB-month); repositories not pulled for over 90 days and their GiB;
repositories the cluster does not use, registry distribution of cluster images (docker.io dependence, pull-through cache presence), digest-pinned count, pull failure events. Registry policies, repository policies and credentials are not read.
Result: the `ecr` section of summary.json. Shape is described in SKILL.md.
"""

from __future__ import annotations

import datetime as _dt
import json
from collections import Counter
from pathlib import Path

from .snapshot import load_json, objects

ECR_STORAGE_USD_PER_GB_MONTH = 0.10  # same list price in every region (as of 2026-10)
STALE_PULL_DAYS = 90


def _ts(s):
    try:
        return _dt.datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return None


def _registry_of(image: str) -> str:
    first = image.split("/")[0]
    return first if ("." in first or ":" in first) and "/" in image else "docker.io"


def analyze(snap: Path, inv: dict | None) -> dict:
    inv = inv or {}
    repos_doc = load_json(snap / "aws" / "ecr-repositories.json")
    if repos_doc is None:
        return {"present": False, "reason": "aws/ecr-repositories.json missing (not EKS, or ecr:DescribeRepositories failed)"}
    now = _ts(inv.get("taken_at")) or _dt.datetime.now(_dt.UTC)
    prod = set((inv.get("namespaces") or {}).get("prod_like") or [])
    account = ((inv.get("eks") or {}).get("account")) or (repos_doc.get("repositories") or [{}])[0].get("registryId")
    registry = load_json(snap / "aws" / "ecr-registry.json") or {}
    scanning = (load_json(snap / "aws" / "ecr-scanning-configuration.json") or {}).get("scanningConfiguration") or {}
    ptc = (load_json(snap / "aws" / "ecr-pull-through-cache-rules.json") or {}).get("pullThroughCacheRules") or []
    # --- images the cluster uses
    in_use: Counter = Counter()
    by_registry: Counter = Counter()
    digest_pinned = 0
    dockerhub_images: set = set()
    used_repos: dict[str, set] = {}
    for p in objects(snap, "pods"):
        ns = p["metadata"]["namespace"]
        for c in (p.get("spec") or {}).get("containers", []) + (p.get("spec") or {}).get("initContainers", []):
            im = c.get("image") or ""
            in_use[im] += 1
            reg = _registry_of(im)
            by_registry[reg] += 1
            if "@sha256:" in im:
                digest_pinned += 1
            if reg == "docker.io":
                dockerhub_images.add(im)
            if account and reg.startswith(f"{account}.dkr.ecr."):
                repo = im.split("/", 1)[1].split("@")[0].rsplit(":", 1)[0]
                used_repos.setdefault(repo, set()).add(ns)
    # --- repositories
    rows = []
    for r in repos_doc.get("repositories") or []:
        name = r["repositoryName"]
        safe = name.replace("/", "__")
        ims = (load_json(snap / "aws" / "ecr-images" / f"{safe}.json") or {}).get("imageDetails") or []
        lifecycle = load_json(snap / "aws" / "ecr-lifecycle" / f"{safe}.json")
        attest = [i for i in ims if "attestation" in str(i.get("artifactMediaType") or "") or i.get("subjectManifestDigest")]
        real = [i for i in ims if i not in attest]
        untagged = [i for i in real if not i.get("imageTags")]
        size_b = sum(i.get("imageSizeInBytes") or 0 for i in ims)
        last_push = max((_ts(i.get("imagePushedAt")) for i in ims if i.get("imagePushedAt")), default=None)
        last_pull = max((_ts(i.get("lastRecordedPullTime")) for i in ims if i.get("lastRecordedPullTime")), default=None)
        scan_status = Counter((i.get("imageScanStatus") or {}).get("status", "none") for i in real)
        sev: Counter = Counter()
        for i in real:
            for k, v in ((i.get("imageScanFindingsSummary") or {}).get("findingSeverityCounts") or {}).items():
                sev[k] += v
        rules = (json.loads(lifecycle["lifecyclePolicyText"]) if lifecycle and lifecycle.get("lifecyclePolicyText") else {}).get("rules") or []
        used_ns = used_repos.get(name) or set()
        rows.append(
            {
                "name": name,
                "target": f"ecr/repository/{name}",
                "created": (r.get("createdAt") or "")[:10],
                "tag_mutability": r.get("imageTagMutability"),
                "scan_on_push": bool((r.get("imageScanningConfiguration") or {}).get("scanOnPush")),
                "encryption": (r.get("encryptionConfiguration") or {}).get("encryptionType"),
                "lifecycle": lifecycle is not None,
                "lifecycle_rules": len(rules),
                "lifecycle_summary": [f"{x.get('selection', {}).get('tagStatus')}:{x.get('selection', {}).get('countType')}={x.get('selection', {}).get('countNumber')}" for x in rules][:4],
                "images": len(real),
                "attestations": len(attest),
                "untagged": len(untagged),
                "gib": round(size_b / 1024**3, 2),
                "last_push": last_push.isoformat()[:10] if last_push else None,
                "last_pull": last_pull.isoformat()[:10] if last_pull else None,
                "days_since_pull": round((now - last_pull).total_seconds() / 86400) if last_pull else None,
                "days_since_push": round((now - last_push).total_seconds() / 86400) if last_push else None,
                "scan_status": dict(scan_status),
                "scanned": scan_status.get("COMPLETE", 0),
                "findings": dict(sev),
                "critical_high": sev.get("CRITICAL", 0) + sev.get("HIGH", 0),
                "used_by_cluster": bool(used_ns),
                "used_in_prod": any(ns in prod for ns in used_ns),
                "used_namespaces": sorted(used_ns),
                "has_latest_tag": any("latest" in (i.get("imageTags") or []) for i in real),
            }
        )
    total_gib = round(sum(x["gib"] for x in rows), 1)
    stale = [x for x in rows if x["images"] and (x["days_since_pull"] is None or x["days_since_pull"] > STALE_PULL_DAYS)]
    unused = [x for x in rows if not x["used_by_cluster"]]
    prod_rows = [x for x in rows if x["used_in_prod"]]
    # --- pull failure events
    ev = load_json(snap / "events.json") or {}
    ev_items = ev.get("items") if isinstance(ev, dict) else ev
    pull_fail = [e for e in (ev_items or []) if e.get("reason") in ("Failed", "BackOff", "ErrImagePull", "ImagePullBackOff") and "pull" in str(e.get("message") or "").lower()]
    pull_fail_rows = Counter(f"{(e.get('involvedObject') or {}).get('namespace')}/{(e.get('involvedObject') or {}).get('name')}" for e in pull_fail)
    scan_type = scanning.get("scanType")
    scan_rules = scanning.get("rules") or []
    summary = {
        "present": True,
        "account": account,
        "repositories": len(rows),
        "images": sum(x["images"] for x in rows),
        "attestations": sum(x["attestations"] for x in rows),
        "untagged": sum(x["untagged"] for x in rows),
        "total_gib": total_gib,
        "monthly_usd": round(total_gib * 1.073741824 * ECR_STORAGE_USD_PER_GB_MONTH, 1),
        "largest": [(x["name"], x["gib"]) for x in sorted(rows, key=lambda x: -x["gib"])[:5]],
        "scan_type": scan_type,
        "scan_rules": len(scan_rules),
        "registry_scan_on_push": any(any(ru.get("scanFrequency") in ("SCAN_ON_PUSH", "CONTINUOUS_SCAN") for ru in [rule]) for rule in scan_rules),
        "repos_scan_off": [x["name"] for x in rows if not x["scan_on_push"]],
        "repos_scan_off_prod": [x["name"] for x in prod_rows if not x["scan_on_push"]],
        "images_scanned": sum(x["scanned"] for x in rows),
        "critical_high_findings": sum(x["critical_high"] for x in rows),
        "repos_with_critical_high": [x["name"] for x in rows if x["critical_high"]],
        "repos_mutable": [x["name"] for x in rows if x["tag_mutability"] == "MUTABLE"],
        "repos_mutable_prod": [x["name"] for x in prod_rows if x["tag_mutability"] == "MUTABLE"],
        "repos_no_lifecycle": [x["name"] for x in rows if not x["lifecycle"]],
        "repos_no_lifecycle_gib": round(sum(x["gib"] for x in rows if not x["lifecycle"]), 1),
        "repos_stale_pull": [(x["name"], x["gib"], x["days_since_pull"]) for x in stale],
        "stale_pull_gib": round(sum(x["gib"] for x in stale), 1),
        "stale_pull_days": STALE_PULL_DAYS,
        "repos_unused_by_cluster": [x["name"] for x in unused],
        "unused_gib": round(sum(x["gib"] for x in unused), 1),
        "repos_empty": [x["name"] for x in rows if not x["images"]],
        "repos_with_latest_tag": [x["name"] for x in rows if x["has_latest_tag"]],
        "encryption": dict(Counter(x["encryption"] for x in rows)),
        "replication_rules": len((registry.get("replicationConfiguration") or {}).get("rules") or []),
        "pull_through_cache_rules": [r.get("ecrRepositoryPrefix") for r in ptc],
        "images_in_use": len(in_use),
        "images_by_registry": dict(by_registry.most_common()),
        "dockerhub_images": len(dockerhub_images),
        "dockerhub_sample": sorted(dockerhub_images)[:6],
        "digest_pinned": digest_pinned,
        "pull_failure_events": sum(pull_fail_rows.values()),
        "pull_failure_targets": [k for k, _ in pull_fail_rows.most_common(5)],
    }
    return {
        "present": True,
        "summary": summary,
        "repositories": rows,
        "registry": {"replication_rules": summary["replication_rules"], "scan_type": scan_type, "scan_rules": scan_rules, "pull_through_cache": ptc},
        "note": f"Cost is {ECR_STORAGE_USD_PER_GB_MONTH} USD/GB-month list price × stored GiB. Attestation manifests (BuildKit provenance, 1-2 KB) are not counted as untagged images. Last pull is ECR's lastRecordedPullTime (recorded at 24-hour granularity). Repository and registry policies are not read",
    }
