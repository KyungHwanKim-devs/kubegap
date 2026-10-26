"""Log signature catalog loader.

Merges signatures/catalog.yaml (the shared set) with collectors/<collector>/signatures.yaml (per-collector additions, may be empty) into one list.
Entry fields are documented in the header comment of catalog.yaml. Regexes are compiled here; broken entries are recorded in errors and skipped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import paths, yamlite

SEVERITIES = ("critical", "high", "medium", "low")


@dataclass
class Signature:
    id: str
    name: str
    component: str
    area: str
    severity: str
    sources: list[str]
    regex: re.Pattern
    pattern: str
    meaning: str = ""
    cause: str = ""
    verify: str = ""
    warn_at: int = 1
    fail_at: int = 10
    origin: str = ""
    extra: dict = field(default_factory=dict)

    def applies_to(self, rel_path: str) -> bool:
        from fnmatch import fnmatchcase

        return any(fnmatchcase(rel_path, g) for g in self.sources)

    def public(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "component": self.component,
            "area": self.area,
            "severity": self.severity,
            "sources": self.sources,
            "pattern": self.pattern,
            "meaning": self.meaning,
            "cause": self.cause,
            "verify": self.verify,
            "warn_at": self.warn_at,
            "fail_at": self.fail_at,
        }


def load(collectors: list[str] | None = None) -> tuple[list[Signature], list[str]]:
    files = [paths.SIGNATURES_DIR / "catalog.yaml"]
    for name in collectors or []:
        p = paths.COLLECTORS_DIR / name / "signatures.yaml"
        if p.is_file():
            files.append(p)
    sigs: list[Signature] = []
    errors: list[str] = []
    seen: set[str] = set()
    for f in files:
        try:
            items = yamlite.load_file(f) or []
        except Exception as e:
            errors.append(f"{f.name}: {type(e).__name__}: {e}")
            continue
        if not isinstance(items, list):
            errors.append(f"{f.name}: not a list")
            continue
        for it in items:
            try:
                sid = str(it["id"])
                if sid in seen:
                    errors.append(f"{f.name}: duplicate {sid}")
                    continue
                sev = str(it.get("severity", "medium")).lower()
                if sev not in SEVERITIES:
                    errors.append(f"{f.name}: {sid} severity {sev} must be one of {SEVERITIES}")
                    sev = "medium"
                sigs.append(
                    Signature(
                        id=sid,
                        name=str(it.get("name") or sid),
                        component=str(it.get("component") or "any"),
                        area=str(it.get("area") or "observability"),
                        severity=sev,
                        sources=[str(s) for s in (it.get("sources") or [])],
                        regex=re.compile(str(it["pattern"])),
                        pattern=str(it["pattern"]),
                        meaning=str(it.get("meaning") or ""),
                        cause=str(it.get("cause") or ""),
                        verify=str(it.get("verify") or ""),
                        warn_at=int(it.get("warn_at", 1)),
                        fail_at=int(it.get("fail_at", 10)),
                        origin=f.name,
                    )
                )
                seen.add(sid)
            except (KeyError, re.error, ValueError, TypeError) as e:
                errors.append(f"{f.name}: {it.get('id') if isinstance(it, dict) else it}: {type(e).__name__}: {e}")
    return sigs, errors
