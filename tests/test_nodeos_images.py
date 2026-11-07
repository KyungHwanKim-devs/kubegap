"""Image sizes from the node script's images_top section (crictl images) — crictl prints go-units HumanSize, so kB/MB/GB/TB are decimal and KiB/MiB/GiB/TiB are binary."""

from __future__ import annotations

from lib.summaries import nodeos

CRI_LINES = [
    "cmd=crictl",
    "version=RuntimeName: containerd RuntimeVersion: 1.7.27",
    "images=4",
    "images_top:",
    "3.5GiB\tghcr.io/acme/ml:1",
    "3GB\tghcr.io/acme/edge:1",
    "1.23GB\tdocker.io/library/app:1",
    "990kB\tdocker.io/library/tiny:1",
    "imagefs=",
]


def test_images_top_decimal_and_binary_units():
    cri = nodeos._parse_cri(CRI_LINES)
    sizes = {i["image"]: i["size_mb"] for i in cri["images_top"]}
    assert sizes["ghcr.io/acme/ml:1"] == 3584  # 3.5 GiB binary
    assert sizes["ghcr.io/acme/edge:1"] == 2861  # 3 GB decimal, not 3072
    assert sizes["docker.io/library/app:1"] == 1173  # 1.23 GB decimal, not 1260
    assert cri["largest_image_mb"] == 3584


def test_images_top_keeps_lowercase_kb():
    cri = nodeos._parse_cri(CRI_LINES)
    sizes = {i["image"]: i["size_mb"] for i in cri["images_top"]}
    assert sizes["docker.io/library/tiny:1"] == 1


def test_images_over_3gb_uses_converted_size():
    cri = nodeos._parse_cri(CRI_LINES)
    assert cri["images_over_3gb"] == ["ghcr.io/acme/ml:1"]
