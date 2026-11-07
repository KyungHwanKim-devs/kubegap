"""lib/foundations/versions reads version strings for the modules that parsed a Kubernetes minor, major or semver triple themselves (#144, the rest in #150): the seven parsers it replaced must not come back."""

from __future__ import annotations

import re
from pathlib import Path

from lib.foundations import versions

ROOT = Path(__file__).resolve().parent.parent


def test_major_minor_reads_every_spelling_the_clusters_and_tools_use():
    assert versions.major_minor("v1.33.5+k3s1") == (1, 33)
    assert versions.major_minor("v1.32.13-eks-577a51e") == (1, 32)
    assert versions.major_minor("1.30.9-eksbuild.3") == (1, 30)
    assert versions.major_minor("2.49.1") == (2, 49)
    assert versions.major_minor("1.30") == (1, 30)
    assert versions.major_minor("") is None and versions.major_minor(None) is None and versions.major_minor("garbage") is None
    assert versions.minor("v1.33.5+k3s1") == 33 and versions.major("v3.7.3") == 3 and versions.major("x") is None
    assert versions.minor_text("v1.32.13-eks") == "1.32" and versions.next_minor_text("v1.32.13-eks") == "1.33" and versions.next_minor_text(None) is None
    assert versions.triple("v1.18.1-eksbuild.1") == (1, 18, 1) and versions.triple("1.11") is None
    assert versions.minor_gap("v1.18.1-eksbuild.1", "v1.19.0-eksbuild.1") == 1 and versions.minor_gap("v1.30.0", "v2.1.0") == 71 and versions.minor_gap("garbage", "v1.19.0") == 0


def test_no_other_module_parses_a_version_with_its_own_regular_expression():
    """hygiene, scaling, collect, kubeproxy, evaluate (twice), vpccni and traffic each had one before #144; the image-tag readers of the *ctl modules are #150."""
    pat = re.compile(r"v\?\(\\d\+\)\\\.\(\\d\+\)|v\?\\d\+\\\.\(\\d\+\)|v\?\(\\d\+\\\.\\d\+\)")
    offenders = [f.name for f in (ROOT / "lib").rglob("*.py") if f.name != "versions.py" and pat.search(f.read_text(encoding="utf-8"))]
    assert offenders == [], offenders


def test_image_version_reads_the_semver_triple_of_an_image_tag():
    assert versions.image_version("quay.io/metallb/speaker:v0.16.2") == "0.16.2"
    assert versions.image_version("602401143452.dkr.ecr.us-east-1.amazonaws.com/eks/coredns:v1.11.3-eksbuild.1") == "1.11.3"
    assert versions.image_version("registry.k8s.io/kube-proxy:v1.31.0@sha256:abcd") == "1.31.0"
    assert versions.image_version("grafana/grafana:latest") is None and versions.image_version("redis@sha256:abcd") is None
    assert versions.image_version("nginx") is None and versions.image_version(None) is None and versions.image_version("x:1.2") is None
