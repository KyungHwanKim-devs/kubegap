"""scripts/scrub-sample.py replaces names in Korean text too, where a particle sits right after the name."""

from __future__ import annotations

import subprocess
import sys

from lib.foundations import paths


def test_a_word_rule_matches_a_name_with_a_korean_particle(tmp_path):
    (tmp_path / "map.yaml").write_text("rules:\n  - ['\\bprodnode\\b', 'node-a']\n")
    (tmp_path / "in.md").write_text("prodnode가 죽으면 prodnode에 있던 파드가 멈춰요. prodnode2는 그대로예요.\n")
    subprocess.run([sys.executable, str(paths.ROOT / "scripts" / "scrub-sample.py"), "--map", str(tmp_path / "map.yaml"), str(tmp_path / "in.md"), str(tmp_path / "out.md")], check=True, capture_output=True)
    assert (tmp_path / "out.md").read_text() == "node-a가 죽으면 node-a에 있던 파드가 멈춰요. prodnode2는 그대로예요.\n"
