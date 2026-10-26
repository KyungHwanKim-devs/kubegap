#!/usr/bin/env python3
"""Turn a real report into a publishable sample by replacing names with placeholders.

Usage: scripts/scrub-sample.py --map <map.yaml> <in.md> <out.md>

Run `scripts/kubegap mask --ips <in.md>` first; that removes tokens, account ids and private IPs.
This script then applies the name map, which is yours and stays out of the repository:

    rules:                                   # regular expressions, applied first, in order
      - [ '\\bmy-real-cluster\\b', 'my-cluster' ]
      - [ 'ip-10-0-(\\d+)-(\\d+)\\.[a-z0-9.-]*compute\\.internal', 'node-\\1-\\2' ]
    domains:                                 # base domain -> replacement; subdomains are kept,
      example-corp.com: acme.com             # so api.example-corp.com becomes api.acme.com and
      example-corp.io: acme.io               # two different hosts never collapse into one name
    apps:                                    # each name becomes app-a, app-b, ... in this order;
      - checkout                             # longer names are matched first
      - checkout-worker
    rules_after:                             # applied last, same form as rules
      - [ '\\bsome-leftover\\b', 'placeholder' ]

Numbers, findings and wording are left as they are. See docs/SAMPLES.md.
"""

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from lib import yamlite

LETTERS = "abcdefghijklmnopqrstuvwxyz"


def app_placeholder(i: int) -> str:
    name = LETTERS[i] if i < 26 else LETTERS[i // 26 - 1] + LETTERS[i % 26]
    return f"app-{name}"


def build(spec: dict) -> list[tuple[str, str]]:
    rules: list[tuple[str, str]] = [(p, r) for p, r in spec.get("rules") or []]
    domains = spec.get("domains") or {}
    for d in sorted(domains, key=len, reverse=True):
        rules.append((rf"(?<![A-Za-z0-9-]){re.escape(d)}(?![A-Za-z0-9-])", domains[d]))
    apps = spec.get("apps") or []
    app_map = {a: app_placeholder(i) for i, a in enumerate(apps)}
    for a in sorted(apps, key=len, reverse=True):
        rules.append((rf"(?<![A-Za-z0-9])({re.escape(a)})(?![A-Za-z0-9])", app_map[a]))
        rules.append((rf"(?<![A-Za-z0-9])({re.escape(a)})(?=[-_])", app_map[a]))
    rules += [(p, r) for p, r in spec.get("rules_after") or []]
    return rules


def scrub(text: str, rules: list[tuple[str, str]]) -> str:
    for pat, rep in rules:
        text = re.sub(pat, rep, text, flags=re.MULTILINE)
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--map", required=True, help="YAML file with rules, domains, apps and rules_after")
    ap.add_argument("src")
    ap.add_argument("dst")
    a = ap.parse_args()
    spec = yamlite.load(pathlib.Path(a.map).read_text(encoding="utf-8")) or {}
    src, dst = pathlib.Path(a.src), pathlib.Path(a.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(scrub(src.read_text(encoding="utf-8"), build(spec)), encoding="utf-8")
    print(dst)


if __name__ == "__main__":
    main()
