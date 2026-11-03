"""Dependency tool list and installation. Used by `kubegap setup`.

Supported environments: macOS (Apple Silicon and Intel), Linux (amd64 and arm64), Windows via WSL2 (= Linux).
Native Windows is not supported.

Install methods are tried per tool in this order. None of them needs sudo.
1. brew      - only when Homebrew is present (mostly macOS). Third-party taps are declared first with `brew trust --formula` (Homebrew 7).
2. download  - prebuilt binaries from the official distribution point (GitHub releases, dl.k8s.io, get.helm.sh, awscli.amazonaws.com)
               into `.tools/bin/`. The default path on Linux, and the fallback on macOS when brew insists on a source build.
               The version is pinned in this file and so is the sha256 of the asset for each platform; the download is compared
               against the pinned digest before anything is written, and install never asks the publisher what is newest.
               `kubegap setup --check-tool-updates` is the one command that does, and it only prints the material of the next pin.
3. venv      - tools that support only specific Python versions go into a dedicated virtualenv at `.tools/<name>-venv/`.
4. pip       - `--user` install with the system pip.

Without a required=True tool, collection cannot run at all. For the others, only the checks that tool owns are marked
"tool missing" and everything else proceeds. `checks` names the check areas the tool owns.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import re
import shutil
import stat
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import paths, shell
from .snapshot import write_private_bytes


@dataclass
class Tool:
    name: str  # executable name
    role: str  # human-readable role
    required: bool = False
    brew: str | None = None  # Homebrew formula (may include a tap)
    download: dict | None = None
    #   official binary download. Keys:
    #   "version": the pinned release tag exactly as the publisher names it (v1.37.2, jq-1.8.2, 0.7.3). Install uses this and nothing newer
    #   "repo" + "asset": GitHub release asset -> https://github.com/<repo>/releases/download/<version>/<asset>
    #   "url": direct URL template for publishers outside GitHub releases (dl.k8s.io, get.helm.sh, awscli.amazonaws.com)
    #   "sha256": {"<os>-<arch>": hex} of the asset per supported platform, taken from the publisher's checksum list when the pin was made
    #             (computed from the asset itself for kubent and aws, which publish none). The download must match it or nothing is written
    #   "checksums": where the publisher's digests are, read only by `setup --check-tool-updates` to print the next pin:
    #             {"asset": "<name in the release>"} or {"url": "<template>"}, with "format": "list" (`<hex>  <file>` lines) or "single" (one hex).
    #             Absent: the command downloads the assets and hashes them
    #   "latest": how `--check-tool-updates` finds the newest version. Default: the latest release of "repo". {"url": ...}: one line of text.
    #             {"repo": ..., "match": regex}: newest release whose tag matches. {"tags": "<owner/repo>"}: first tag of the repo
    #   "bin": executable (basename) to extract from the archive. If not an archive, the downloaded file itself
    #   "strip_tag": prefix to strip from the tag to get the bare version (default "v")
    #   "only_os": try only on these OSes (e.g. aws uses brew on macOS)
    #   "post": special handling such as "aws-install"
    #   template variables: {version} {tag} {os}(darwin|linux) {arch}(arm64|amd64) {arch_x}(aarch64|x86_64) {jq_os}(macos|linux) {krr_os}
    venv: dict | None = None
    #   {"pythons": [candidate interpreters], "brew_python": "python@3.11", "pip": "pip arguments", "bin": "executable", "extra_pip": [...]}
    pip: str | None = None
    version_args: list[str] = field(default_factory=lambda: ["--version"])
    checks: list[str] = field(default_factory=list)
    note: str = ""  # guidance shown when there is no install method


TOOLS: list[Tool] = [
    Tool(
        "kubectl",
        "Core of cluster state and event collection",
        required=True,
        brew="kubectl",
        download={
            "version": "v1.37.2",
            "url": "https://dl.k8s.io/release/{tag}/bin/{os}/{arch}/kubectl",
            "bin": "kubectl",
            "sha256": {
                "darwin-arm64": "55701af0d51815ee335f240e48acf0959c3c23017ed3fa816e880c4a92bae581",
                "darwin-amd64": "88379aff5c8111de6be0a394adffba2819e44cde269f3ab23cef76de1a48eaa8",
                "linux-amd64": "c04487523e7aa7d1493f7808174c899db93d7a9cf57531420cd76b9bd415f8f4",
                "linux-arm64": "fcc16f63186659d9722014b7e02d5fdd2d4e669cb8c0ab66365d7d3b8ba03509",
            },
            "checksums": {"url": "https://dl.k8s.io/release/{tag}/bin/{os}/{arch}/kubectl.sha256", "format": "single"},
            "latest": {"url": "https://dl.k8s.io/release/stable.txt"},
        },
        version_args=["version", "--client", "-o", "json"],
        checks=["*"],
    ),
    Tool(
        "jq",
        "JSON processing",
        required=True,
        brew="jq",
        download={
            "version": "jq-1.8.2",
            "repo": "jqlang/jq",
            "asset": "jq-{jq_os}-{arch}",
            "bin": "jq",
            "strip_tag": "jq-",
            "sha256": {
                "darwin-arm64": "2d75340ba57a4b4b4c8708a21c2dc8e958a48aaa8bba13b27f77f6e4c0eca07e",
                "darwin-amd64": "e94b266e3c26690550006abe63152b782280f4e14374accdf04cbde844f00bc0",
                "linux-amd64": "b1c22172dd303f3be49e935aa56aa48a8b7a46e0bc838b4997d3bb451495870f",
                "linux-arm64": "8b85c817833814ddca00a144c33705546355afccf0cf39b188f3cdb48b852309",
            },
            "checksums": {"asset": "sha256sum.txt", "format": "list"},
        },
        checks=["*"],
    ),
    Tool("python3", "Runs the collect, summarize and evaluate scripts", required=True, brew="python", checks=["*"], note="This script itself runs on Python, so it cannot be missing"),
    Tool(
        "aws",
        "EKS, EC2, SSM and CloudWatch queries (needed only for the EKS profile)",
        brew="awscli",
        download={
            "version": "2.39.3",
            "url": "https://awscli.amazonaws.com/awscli-exe-linux-{arch_x}-{version}.zip",
            "only_os": ["linux"],
            "bin": "aws",
            "post": "aws-install",
            "sha256": {
                "linux-amd64": "14cb35809ad7547dd3c69fa9899a3975fbd850b6a6791f3fe264856490cd9a63",
                "linux-arm64": "f6eb845fbacb11bee87de3f5fbe8043773cbe89d0414607b44b71e216eb9226b",
            },  # AWS publishes a PGP signature, no plain digest: computed from the zip when the pin was made; the signature itself is not verified
            "latest": {"tags": "aws/aws-cli"},
        },
        checks=["eks-platform", "controlplane-logs", "node-os(ssm)", "cost"],
        note="On macOS without brew, install https://awscli.amazonaws.com/AWSCLIV2.pkg directly. The Linux zip's PGP signature is not verified; its pinned sha256 was computed from the zip when the version was pinned (#108)",
    ),
    Tool(
        "helm",
        "Helm release status and age (reads release records, which Helm stores in Secrets)",
        brew="helm",
        download={
            "version": "v4.3.1",  # the collector runs only `helm list -A -o json`, whose shape is the same in Helm 3 and 4; the reports so far were made with Helm 4 from brew
            "url": "https://get.helm.sh/helm-{tag}-{os}-{arch}.tar.gz",
            "bin": "helm",
            "sha256": {
                "darwin-arm64": "6b4e61c8cd27d99e5a801e63ff25dd5c70b36875c2cd659d3e9ce6b76fc23198",
                "darwin-amd64": "34bec4eba761ba5c16d1965ee6b8f5b0abe5993974a802274e2a4f0418893d89",
                "linux-amd64": "0403a88ae20913d11b10a2467b50087721fea7581736da6b9d3992f5357fe54b",
                "linux-arm64": "8cf8f66ecbc252ac8f7f06cca68aba88508ddfde3a6a34feb1678ad1694b4f88",
            },
            "checksums": {"url": "https://get.helm.sh/helm-{tag}-{os}-{arch}.tar.gz.sha256sum", "format": "list"},
            "latest": {"repo": "helm/helm"},
        },
        version_args=["version", "--short"],
        checks=["hygiene.helm-release"],
    ),
    Tool(
        "argocd",
        "Argo CD application status and diff (login required)",
        brew="argocd",
        download={
            "version": "v3.6.0",
            "repo": "argoproj/argo-cd",
            "asset": "argocd-{os}-{arch}",
            "bin": "argocd",
            "sha256": {
                "darwin-arm64": "94c135a62a3478c3df27fcd9224b67d8072f6ba243c0f6cc7e7509782a80a407",
                "darwin-amd64": "87bedcb0756acd3bdf094e4f1b6b689872a085a185c4efcaf4fdbadf7ab1b6b7",
                "linux-amd64": "62f4fe7cf0f97f384993effccbde66a4e541bc9250c6682c75a9f992043263a0",
                "linux-arm64": "45b5c33e4767c80a09c6e824f35bb07fb3f044703e62670b18478e64cbb47fb3",
            },
            "checksums": {"asset": "cli_checksums.txt", "format": "list"},
        },
        version_args=["version", "--client", "--short"],
        checks=["gitops.argocd"],
    ),
    Tool(
        "krr",
        "Resource request recommendations (Robusta KRR, Prometheus-based)",
        brew="robusta-dev/krr/krr",
        venv={
            "pythons": ["python3.11", "python3.10", "python3.12"],
            "brew_python": "python@3.11",
            "pip": "https://github.com/robusta-dev/krr/archive/refs/tags/v1.31.1.tar.gz",
            "bin": "krr",
            "extra_pip": ["cachetools", "typer<0.13", "click<8.2"],
        },
        version_args=["version"],
        checks=["resources.krr-recommendation"],
        note="The macOS release binary crashes on start with a pkg_resources error (packaging defect), and it is not on PyPI. Only Python 3.10-3.12.9 is supported, so the tagged source is installed into a dedicated virtualenv (patching the missing cachetools and the typer 0.13+ incompatibility)",
    ),
    Tool(
        "polaris",
        "Static manifest audit and lightweight security checks",
        brew="FairwindsOps/tap/polaris",
        download={
            "version": "v10.2.6",
            "repo": "FairwindsOps/polaris",
            "asset": "polaris_{version}_{os}_{arch}.tar.gz",
            "bin": "polaris",
            "sha256": {
                "darwin-arm64": "6c92a34f3db0f6a00434c8eb7e7a6e68388f1e6371ce7b12cd8ddac8029ddaaa",
                "darwin-amd64": "e716e37b3a4eaa0af6a76f5f46caf5dc3384094155659c01fa786c1f9f0633ce",
                "linux-amd64": "87856194124409f7f21912775c0d6ac0804061ddaded5b527a1326f1850e9491",
                "linux-arm64": "e1c2774aa8100c6c5c23f2aa49cbf02476fd7b43a226a6372b405b6772acb585",
            },
            "checksums": {"asset": "checksums.txt", "format": "list"},
        },
        version_args=["version"],
        checks=["hygiene.polaris", "security.polaris"],
    ),
    Tool(
        "pluto",
        "Deprecated API detection",
        brew="FairwindsOps/tap/pluto",
        download={
            "version": "v5.24.5",
            "repo": "FairwindsOps/pluto",
            "asset": "pluto_{version}_{os}_{arch}.tar.gz",
            "bin": "pluto",
            "sha256": {
                "darwin-arm64": "61edf3054dc3aa2622fed933067c8dcfb4c6f4e95ed4d9e4fc4a21e68a17fe43",
                "darwin-amd64": "aff97bc8705ec45f14688bf815879019dc15314fe71a8b1988892584e922b663",
                "linux-amd64": "80076e01a320e1f4db30f5dbc927d204e61cd8abed66fa0b4644ca61cd86b39e",
                "linux-arm64": "2b00f52285f0298ae7cec55d34e2387ed725584d072e67c8fa88bee662169f10",
            },
            "checksums": {"asset": "checksums.txt", "format": "list"},
        },
        version_args=["version"],
        checks=["hygiene.deprecated-api"],
    ),
    Tool(
        "kubent",
        "Deprecated API detection (complements Pluto)",
        brew="kubent",
        download={
            "version": "0.7.3",
            "repo": "doitintl/kube-no-trouble",
            "asset": "kubent-{version}-{os}-{arch}.tar.gz",
            "bin": "kubent",
            "strip_tag": "",
            "sha256": {
                "darwin-arm64": "23d5ae5b7ecb46e870be555d87f1a7792a8d170a8fe488da63a5a31fcca5b176",
                "darwin-amd64": "e6682a9595ee2767f0dd633c61006ccc2492e641ed64146d17aca671578e9e48",
                "linux-amd64": "ac96ace138f18a864a6b5bd64643cecbab2887f868da35853812cfdecd307b6d",
                "linux-arm64": "f6f669e19414b6ea3201103791d5c0965ad5c6f20cd6efbd5265d08d7bf6e478",
            },  # the project publishes no checksum file: computed from the assets when the pin was made
        },
        checks=["hygiene.deprecated-api"],
    ),
    Tool(
        "promtool",
        "PrometheusRule syntax validation (optional)",
        brew="prometheus",
        download={
            "version": "v3.15.1",
            "repo": "prometheus/prometheus",
            "asset": "prometheus-{version}.{os}-{arch}.tar.gz",
            "bin": "promtool",
            "sha256": {
                "darwin-arm64": "0d4d3d9837d27e4fcd0bd16d115b1b8d6732a4bf3e69107f1190d9ef653ae471",
                "darwin-amd64": "c89fcb30045d8c394c9d93e96cbbee3aaf2448a48326b417e811eb4e528edf88",
                "linux-amd64": "6a726885328ad9efebbf36e876ce2fb6225468a71fd1e7ce3ba666d5f4d97a84",
                "linux-arm64": "ceb6d21493c37ca0b4513b147642797c68cf39a0f50a444d50e1e80c74f21b26",
            },
            "checksums": {"asset": "sha256sums.txt", "format": "list"},
        },
        checks=["observability.rule-syntax"],
    ),
    Tool(
        "amtool",
        "Alertmanager routes and silences (optional)",
        brew=None,
        download={
            "version": "v0.34.2",
            "repo": "prometheus/alertmanager",
            "asset": "alertmanager-{version}.{os}-{arch}.tar.gz",
            "bin": "amtool",
            "sha256": {
                "darwin-arm64": "dc1fcd4ad3e8bef111683eaf385aa5b2b02493277bca9126c129e0a39fc68a4f",
                "darwin-amd64": "fa5a50303c58771c261fcbed4cf5f9a852cf2c6064942adbd92c6859c65c5f93",
                "linux-amd64": "17ee14acd0f6ba6e25a436ff223d9c17ddd5cf484f543ad12f0932eaa89ba186",
                "linux-arm64": "5aaad82e3d167c30c06ce7d38677d2892a6f66f4c3613ea17af7481750fdd0b0",
            },
            "checksums": {"asset": "sha256sums.txt", "format": "list"},
        },
        checks=["observability.alertmanager"],
        note="No Homebrew formula; the official release binary is downloaded. Without it the same information is read via the Alertmanager HTTP API",
    ),
    Tool(
        "ssh",
        "Small k3s cluster node access (small k3s cluster profile)",
        brew=None,
        version_args=["-V"],
        checks=["node-os(ssh)"],
        note="Included by default on macOS and most Linux. Minimal images (slim containers) may lack it: distro package openssh-client",
    ),
]

_VERSION_RE = re.compile(r"v?(\d+\.\d+(?:\.\d+)?)")
_UA = {"User-Agent": "kubegap", "Accept": "application/vnd.github+json"}


def host_os() -> str:
    return platform.system().lower()  # darwin | linux | windows


SUPPORTED_MACHINES = ("x86_64", "amd64", "arm64", "aarch64")  # platform.machine() values the pins cover; anything else gets no download


def platform_vars() -> dict:
    mach = platform.machine().lower()
    arm = mach in ("arm64", "aarch64")
    return {"os": host_os(), "arch": "arm64" if arm else "amd64", "arch_x": "aarch64" if arm else "x86_64", "jq_os": "macos" if host_os() == "darwin" else "linux", "krr_os": "macos-latest" if host_os() == "darwin" else "ubuntu-latest"}


def supported_host() -> tuple[bool, str]:
    o = host_os()
    if o in ("darwin", "linux"):
        return True, o
    if o == "windows":
        return False, ("Native Windows is not supported. Run inside WSL2 (Ubuntu on Windows), which behaves like Linux")
    return False, f"unsupported OS: {platform.system()}"


def tool_version(tool: Tool) -> str | None:
    r = shell.run([tool.name, *tool.version_args], timeout=15)
    text = (r.stdout or "") + (r.stderr or "")
    if tool.name == "kubectl":
        m = re.search(r'"gitVersion":\s*"([^"]+)"', text)
        return m.group(1) if m else None
    m = _VERSION_RE.search(text)
    return m.group(1) if m else (text.strip().splitlines()[0][:40] if text.strip() else None)


def _download_applicable(tool: Tool) -> bool:
    d = tool.download
    return bool(d) and host_os() in d.get("only_os", ["darwin", "linux"])


def check_tools() -> list[dict]:
    out = []
    for t in TOOLS:
        path = shell.which(t.name)
        installable = bool(t.brew and shell.which("brew")) or _download_applicable(t) or bool(t.venv) or bool(t.pip and (shell.which("pip3") or shell.which("pip")))
        out.append({"name": t.name, "role": t.role, "required": t.required, "present": path is not None, "path": path, "version": tool_version(t) if path else None, "checks": t.checks, "installable": installable, "note": t.note})
    return out


# ---------- install paths ----------

PLATFORMS = ("darwin-arm64", "darwin-amd64", "linux-amd64", "linux-arm64")  # the "<os>-<arch>" keys of download["sha256"]
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def platform_key(v: dict | None = None) -> str:
    v = v or platform_vars()
    return f"{v['os']}-{v['arch']}"


def _get(url: str, timeout: float = 60) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=timeout) as resp:
        return resp.read()


def _latest_tag(repo: str, match: str | None = None) -> str:
    """Newest release tag of a GitHub repo; with `match`, the newest non-prerelease whose tag matches the regex (Helm 3 while 4 is latest). Only `--check-tool-updates` calls this."""
    if not match:
        meta = json.loads(_get(f"https://api.github.com/repos/{repo}/releases/latest", 30).decode())
        return meta.get("tag_name") or ""
    rel = json.loads(_get(f"https://api.github.com/repos/{repo}/releases?per_page=50", 30).decode())
    return next((r.get("tag_name") or "" for r in rel if not r.get("prerelease") and re.match(match, r.get("tag_name") or "")), "")


def latest_version(d: dict) -> str:
    """What the publisher calls newest, found the way download["latest"] says. Network; never called by install."""
    lt = d.get("latest") or {}
    if lt.get("url"):
        return _get(lt["url"], 30).decode().strip()
    if lt.get("tags"):
        tags = json.loads(_get(f"https://api.github.com/repos/{lt['tags']}/tags?per_page=1", 30).decode())
        return (tags[0].get("name") or "") if tags else ""
    return _latest_tag(lt.get("repo") or d["repo"], lt.get("match"))


def _bare_version(d: dict, tag: str) -> str:
    strip = d.get("strip_tag", "v")
    return tag[len(strip) :] if strip and tag.startswith(strip) else tag


def download_url(d: dict, tag: str, v: dict) -> tuple[str, str]:
    """(url, filename) of the asset for version `tag` on platform `v`. GitHub releases have a fixed download URL per tag, so no API call is needed."""
    version = _bare_version(d, tag)
    if d.get("repo"):
        filename = d["asset"].format(**v, tag=tag, version=version)
        return f"https://github.com/{d['repo']}/releases/download/{tag}/{filename}", filename
    url = d["url"].format(**v, tag=tag, version=version)
    return url, url.rsplit("/", 1)[-1]


def sha256_hex(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def parse_checksum_text(text: str, filename: str, fmt: str) -> str | None:
    """The digest of `filename` out of a publisher's checksum file. `list`: lines of `<hex>  <file>` (sha256sum output; a leading `*` on the
    name is the binary-mode marker). `single`: the file holds one hex. Returns None when the file does not name `filename` or the hex is malformed."""
    if fmt == "single":
        parts = text.split()
        return parts[0] if parts and _HEX64.match(parts[0]) else None
    for ln in text.splitlines():
        parts = ln.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == filename and _HEX64.match(parts[0]):
            return parts[0]
    return None


def _place_binary(blob: bytes, filename: str, bin_name: str, target: Path) -> str | None:
    """If it is an archive, extract the bin_name executable; otherwise use the file as-is. The file lands through write_private_bytes: a temporary
    file in `.tools/bin/`, fsync, mode 0700, rename over the target, so an interrupted install never leaves half a binary on PATH.
    Returns the failure reason as a string, or None on success."""
    data: bytes | None
    if filename.endswith((".tar.gz", ".tgz")):
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
            m = next((m for m in tf.getmembers() if m.isfile() and os.path.basename(m.name) == bin_name), None)
            if m is None:
                return f"no {bin_name} executable inside {filename}"
            data = tf.extractfile(m).read()
    elif filename.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            cand = [n for n in zf.namelist() if not n.endswith("/") and os.path.basename(n) == bin_name]
            if not cand:
                return f"no {bin_name} executable inside {filename}"
            data = zf.read(cand[0])
    else:
        data = blob
    write_private_bytes(target, data, mode=0o700)
    return None


def _aws_install(blob: bytes, log=None) -> dict:
    """The aws CLI v2 Linux zip ships an install script. `-i` (install dir) and `-b` (binary link dir) install it without sudo."""
    work = shell.TOOLS_DIR / "aws-cli-src"
    if work.exists():
        shutil.rmtree(work)
    paths.ensure_private_dir(work, base=shell.TOOLS_DIR)
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(work)
    installer = work / "aws" / "install"
    installer.chmod(0o755)
    for f in (work / "aws" / "dist").rglob("*"):
        if f.is_file():
            f.chmod(f.stat().st_mode | stat.S_IXUSR)
    dest = shell.TOOLS_DIR / "aws-cli"
    paths.ensure_private_dir(shell.TOOLS_BIN, base=shell.TOOLS_DIR)
    r = shell.run([str(installer), "-i", str(dest), "-b", str(shell.TOOLS_BIN), "--update"], timeout=300, id="install.aws.installer", log=log)
    shutil.rmtree(work, ignore_errors=True)
    if not r.ok:
        return {"ok": False, "error": f"aws install script failed: {(r.error or r.stderr.strip())[-300:]}"}
    return {"ok": True}


def install_download(tool: Tool, log=None) -> dict:
    """Download the pinned version of `tool` for this platform, compare its sha256 with the pinned digest and only then place it in `.tools/bin/`.
    One network request, to the versioned asset URL; nothing asks the publisher what is newest. A digest mismatch, or a platform without a pinned
    digest, fails the install without writing anything."""
    d = tool.download or {}
    method = "download"
    try:
        mach = platform.machine().lower()
        if mach not in SUPPORTED_MACHINES:
            return {"name": tool.name, "method": method, "ok": False, "error": f"unsupported architecture {mach}; the pinned binaries cover {', '.join(SUPPORTED_MACHINES)}. Nothing downloaded"}
        v = platform_vars()
        key = platform_key(v)
        tag = d["version"]
        expected = (d.get("sha256") or {}).get(key)
        url, filename = download_url(d, tag, v)
        method = f"download {url}"
        if not expected:
            return {"name": tool.name, "method": method, "ok": False, "error": f"no pinned sha256 for {key} in lib/tools.py; nothing downloaded"}
        blob = _get(url, 600)
        actual = sha256_hex(blob)
        if actual != expected:
            return {"name": tool.name, "method": method, "ok": False, "error": f"checksum mismatch for {filename}: pinned sha256 {expected[:12]}…, downloaded {actual[:12]}…; nothing written"}
        paths.ensure_private_dir(shell.TOOLS_BIN, base=shell.TOOLS_DIR)
        target = shell.TOOLS_BIN / d["bin"]
        if d.get("post") == "aws-install":
            res = _aws_install(blob, log=log)
            if not res["ok"]:
                return {"name": tool.name, "method": method, "ok": False, "error": res["error"]}
        else:
            err = _place_binary(blob, filename, d["bin"], target)
            if err:
                return {"name": tool.name, "method": method, "ok": False, "error": err}
        if log is not None:
            log.command(id=f"install.{tool.name}", cmd=[method], code=0, seconds=0.0, out_path=str(target), version=tag, sha256=actual)
        return {"name": tool.name, "method": method, "ok": True, "error": None, "path": str(target), "version": tag, "sha256": actual, "checksum": "verified", "sha256_from": "publisher" if d.get("checksums") else "asset"}
    except Exception as e:  # any network or archive failure is reported only as an install failure
        return {"name": tool.name, "method": method, "ok": False, "error": f"{type(e).__name__}: {e}"}


def pin_material(d: dict, tag: str) -> dict:
    """The `sha256` entry for version `tag`: {"<os>-<arch>": hex} for every platform the tool supports, read from the publisher's checksum
    file when there is one (`checksums`), or computed from the downloaded asset when the project publishes none. Network; `--check-tool-updates` only.
    A platform whose digest cannot be found carries the reason instead of a hex."""
    out: dict = {}
    cs = d.get("checksums") or {}
    for key in PLATFORMS:
        os_, arch = key.split("-")
        if os_ not in d.get("only_os", ["darwin", "linux"]):
            continue
        v = {**platform_vars(), "os": os_, "arch": arch, "arch_x": "aarch64" if arch == "arm64" else "x86_64", "jq_os": "macos" if os_ == "darwin" else "linux"}
        url, filename = download_url(d, tag, v)
        try:
            if cs.get("asset"):
                text = _get(f"https://github.com/{d['repo']}/releases/download/{tag}/{cs['asset']}", 60).decode()
                got = parse_checksum_text(text, filename, cs.get("format", "list"))
                out[key] = got or f"not in {cs['asset']} of {tag}"
            elif cs.get("url"):
                text = _get(cs["url"].format(**v, tag=tag, version=_bare_version(d, tag)), 60).decode()
                got = parse_checksum_text(text, filename, cs.get("format", "single"))
                out[key] = got or f"malformed {cs['url'].rsplit('/', 1)[-1]}"
            else:
                out[key] = sha256_hex(_get(url, 600))
        except Exception as e:
            out[key] = f"{type(e).__name__}: {e}"
    return out


def check_updates(only: list[str] | None = None) -> list[dict]:
    """For every tool with a download entry: the pinned version, what the publisher calls newest, and when they differ, the `sha256` entry of
    the newest version so the pin PR is a copy. Network only; nothing is installed or written. Tools kubent and aws publish no checksum file, so
    their digests are computed from the assets, which downloads them."""
    rows = []
    for name in only or []:
        t = by_name(name)
        if t is None or not t.download:
            rows.append({"name": name, "pinned": "-", "latest": None, "behind": None, "sha256": None, "error": "unknown tool" if t is None else "no download entry (installed through brew or a virtualenv, not pinned here)"})
    for t in TOOLS:
        d = t.download
        if not d or (only and t.name not in only):
            continue
        row: dict = {"name": t.name, "pinned": d["version"], "latest": None, "behind": None, "sha256": None, "error": None}
        try:
            row["latest"] = latest_version(d)
            row["behind"] = bool(row["latest"]) and row["latest"] != d["version"]
            if row["behind"]:
                row["sha256"] = pin_material(d, row["latest"])
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        rows.append(row)
    return rows


def install_in_venv(tool: Tool, log=None) -> dict:
    """Install a tool that supports only specific Python versions into a dedicated virtualenv. If no candidate interpreter exists, fetch Python via brew first (binary bottle, no CLT needed)."""
    v = tool.venv or {}
    method = f"venv({v.get('pip')})"
    py = next((p for p in v.get("pythons", []) if shell.which(p)), None)
    if py is None and v.get("brew_python") and shell.which("brew"):
        r = shell.run(["brew", "install", v["brew_python"]], timeout=900, id=f"install.{tool.name}.python", log=log)
        py = next((p for p in v.get("pythons", []) if shell.which(p)), None)
        if py is None:
            return {"name": tool.name, "method": method, "ok": False, "error": f"{v.get('pythons')} still not found after installing {v['brew_python']}: {(r.error or r.stderr.strip())[-200:]}"}
    if py is None:
        return {"name": tool.name, "method": method, "ok": False, "error": f"no supported Python ({', '.join(v.get('pythons', []))}) found. On Linux install it from the distro first (e.g. apt install python3.11 python3.11-venv)"}
    dest = shell.TOOLS_DIR / f"{tool.name}-venv"
    if dest.exists():
        shutil.rmtree(dest)
    r = shell.run([py, "-m", "venv", str(dest)], timeout=120, id=f"install.{tool.name}.venv", log=log)
    if not r.ok:
        return {"name": tool.name, "method": method, "ok": False, "error": f"venv creation failed: {(r.error or r.stderr.strip())[-300:]}"}
    r = shell.run([str(dest / "bin" / "pip"), "install", "-q", v["pip"], *list(v.get("extra_pip", []))], timeout=900, id=f"install.{tool.name}.pip", log=log)
    if not r.ok:
        return {"name": tool.name, "method": method, "ok": False, "error": f"pip install failed: {(r.error or r.stderr.strip())[-400:]}"}
    real = dest / "bin" / v["bin"]
    if not real.exists():
        return {"name": tool.name, "method": method, "ok": False, "error": f"installed, but {real} does not exist"}
    paths.ensure_private_dir(shell.TOOLS_BIN, base=shell.TOOLS_DIR)
    target = shell.TOOLS_BIN / v["bin"]
    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(real)
    return {"name": tool.name, "method": method, "ok": True, "error": None, "path": str(target), "python": py}


def _tap_first(tool: Tool) -> bool:
    """A formula from a third-party tap (`owner/tap/name`) is whatever the tap's git HEAD holds and is not pinned by anyone we know; when the
    pinned download exists for this host it goes first and brew is the fallback. homebrew-core formulae are verified by brew and stay first."""
    return bool(tool.brew and "/" in tool.brew and _download_applicable(tool))


def install_tool(tool: Tool, log=None) -> dict:
    """Try brew -> download -> venv -> pip in order (download before brew for a third-party tap formula, see _tap_first). Never raises. If everything fails, the collected reasons are returned."""
    errors: list[str] = []
    order = ["download", "brew"] if _tap_first(tool) else ["brew", "download"]
    for step in order:
        if step == "brew" and tool.brew and shell.which("brew"):
            if "/" in tool.brew:
                shell.run(["brew", "trust", "--formula", tool.brew], timeout=120, id=f"trust.{tool.name}", log=log)
            r = shell.run(["brew", "install", tool.brew], timeout=900, id=f"install.{tool.name}", log=log)
            if r.ok:
                return {"name": tool.name, "method": f"brew install {tool.brew}", "ok": True, "error": None, "fallback_from": errors or None}
            err = r.error or r.stderr.strip()
            if "Command Line Tools" in err:
                err = "brew requires a Command Line Tools update (sudo) for a source build"
            errors.append(f"brew: {err[-300:]}")
        if step == "download" and _download_applicable(tool):
            res = install_download(tool, log=log)
            if res["ok"]:
                res["fallback_from"] = errors or None
                return res
            errors.append(res["error"])
    if tool.venv:
        res = install_in_venv(tool, log=log)
        if res["ok"]:
            res["fallback_from"] = errors or None
            return res
        errors.append(res["error"])
    pip = shell.which("pip3") or shell.which("pip")
    if tool.pip and pip:
        r = shell.run([pip, "install", "--user", tool.pip], timeout=900, id=f"install.{tool.name}", log=log)
        if r.ok:
            return {"name": tool.name, "method": f"{pip} install --user {tool.pip}", "ok": True, "error": None}
        errors.append(f"pip: {(r.error or r.stderr.strip())[-300:]}")
    if errors:
        return {"name": tool.name, "method": None, "ok": False, "error": " | ".join(errors), "platform": platform.system()}
    return {"name": tool.name, "method": None, "ok": False, "error": tool.note or "no install method defined", "platform": platform.system()}


def install_plan(tool: Tool) -> str:
    """One human-readable line saying how and where this tool would be installed. Shown when asking for consent."""
    steps = []
    brew_step = (f"brew install {tool.brew}" + (" (third-party tap: brew trust first)" if "/" in tool.brew else "")) if tool.brew and shell.which("brew") else None
    if brew_step and not _tap_first(tool):
        steps.append(brew_step)
    if _download_applicable(tool):
        d = tool.download
        src = f"GitHub release {d['repo']}" if d.get("repo") else d["url"].split("/")[2]
        steps.append(f"official binary {d['version']} from {src}, sha256 pinned in lib/tools.py -> {shell.TOOLS_BIN}/")
    if brew_step and _tap_first(tool):
        steps.append(brew_step)
    if tool.venv:
        v = tool.venv
        steps.append(f"dedicated Python virtualenv {shell.TOOLS_DIR}/{tool.name}-venv/ ({'/'.join(v['pythons'])}, {v['pip']})")
    if tool.pip and (shell.which("pip3") or shell.which("pip")):
        steps.append(f"pip install --user {tool.pip}")
    if not steps:
        return tool.note or "no install method"
    return " -> on failure: ".join(steps)


def by_name(name: str) -> Tool | None:
    return next((t for t in TOOLS if t.name == name), None)
