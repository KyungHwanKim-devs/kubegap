r"""Version strings: the home for reading "v1.33.5+k3s1", "1.30.9-eksbuild.3", "v1.32.13-eks-577a51e" or "2.49.1" into numbers.

Seven private parsers of the Kubernetes minor, major or a semver triple (hygiene, scaling, collect, kubeproxy, evaluate twice, vpccni, traffic) were
replaced by this module in #144, and the `_ver(image)` image-tag reader copied into ten summary modules by `image_version` in #150; a fix in one
never reached the others. tests/test_versions.py and tests/test_helper_homes.py fail when a version regular expression appears elsewhere under lib/.
Two readers stay where they are because they do another job: `podmetrics._vt` compares dotted version texts of any length as tuples, and
`tools._VERSION_RE` finds a version inside a tool's `--version` output.
"""

from __future__ import annotations

import re

_MAJOR_MINOR = re.compile(r"v?(\d+)\.(\d+)")


def major_minor(v) -> tuple[int, int] | None:
    """(major, minor) of a version string with an optional leading v and any suffix; None when the text does not start with two numbers."""
    m = _MAJOR_MINOR.match(str(v or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


_TRIPLE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def triple(v) -> tuple[int, int, int] | None:
    """(major, minor, patch) when the text starts with three numbers ("v1.18.1-eksbuild.1" -> (1, 18, 1)); None otherwise."""
    m = _TRIPLE.match(str(v or ""))
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


_IMAGE_TAG = re.compile(r":v?(\d+\.\d+\.\d+)")


def image_version(image) -> str | None:
    """ "0.16.2" from an image reference whose tag starts with a semver triple ("quay.io/metallb/speaker:v0.16.2", "…:1.2.3-eksbuild.1"); None for a
    digest-only reference, `latest`, or no tag."""
    m = _IMAGE_TAG.search(str(image or ""))
    return m.group(1) if m else None


def minor(v) -> int | None:
    mm = major_minor(v)
    return mm[1] if mm else None


def major(v) -> int | None:
    mm = major_minor(v)
    return mm[0] if mm else None


def minor_text(v) -> str | None:
    """ "1.33" for "v1.33.5+k3s1": the form the compatibility tables and the tool targets use."""
    mm = major_minor(v)
    return f"{mm[0]}.{mm[1]}" if mm else None


def next_minor_text(v) -> str | None:
    """ "1.34" for "v1.33.5": the minor after the given one."""
    mm = major_minor(v)
    return f"{mm[0]}.{mm[1] + 1}" if mm else None


def minor_gap(installed, latest) -> int:
    """How many minors `latest` is ahead of `installed`, majors counted as 100 minors; 0 when either cannot be read."""
    a, b = major_minor(installed), major_minor(latest)
    if not a or not b:
        return 0
    return (b[0] - a[0]) * 100 + (b[1] - a[1])
