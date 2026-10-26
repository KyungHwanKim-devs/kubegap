"""Dependency tool list and installation. Used by `kubegap setup`.

Supported environments: macOS (Apple Silicon and Intel), Linux (amd64 and arm64), Windows via WSL2 (= Linux).
Native Windows is not supported.

Install methods are tried per tool in this order. None of them needs sudo.
1. brew      - only when Homebrew is present (mostly macOS). Third-party taps are declared first with `brew trust --formula` (Homebrew 7).
2. download  - prebuilt binaries from the official distribution point (GitHub releases, dl.k8s.io, get.helm.sh, awscli.amazonaws.com)
               into `.tools/bin/`. The default path on Linux, and the fallback on macOS when brew insists on a source build.
3. venv      - tools that support only specific Python versions go into a dedicated virtualenv at `.tools/<name>-venv/`.
4. pip       - `--user` install with the system pip.

Without a required=True tool, collection cannot run at all. For the others, only the checks that tool owns are marked
"tool missing" and everything else proceeds. `checks` names the check areas the tool owns.
"""

from __future__ import annotations

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

from . import shell


@dataclass
class Tool:
    name: str  # executable name
    role: str  # human-readable role
    required: bool = False
    brew: str | None = None  # Homebrew formula (may include a tap)
    download: dict | None = None
    #   official binary download. Keys:
    #   "repo": GitHub repo -> read the latest release tag and fetch the asset named by "asset"
    #   "url": direct URL template. Version comes from "version_url" (one line of text) or "version_repo" (latest GitHub tag)
    #   "bin": executable (basename) to extract from the archive. If not an archive, the downloaded file itself
    #   "strip_tag": prefix to strip from the tag (default "v")
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
        download={"url": "https://dl.k8s.io/release/{tag}/bin/{os}/{arch}/kubectl", "version_url": "https://dl.k8s.io/release/stable.txt", "bin": "kubectl"},
        version_args=["version", "--client", "-o", "json"],
        checks=["*"],
    ),
    Tool("jq", "JSON processing", required=True, brew="jq", download={"repo": "jqlang/jq", "asset": "jq-{jq_os}-{arch}", "bin": "jq", "strip_tag": "jq-"}, checks=["*"]),
    Tool("python3", "Runs the collect, summarize and evaluate scripts", required=True, brew="python", checks=["*"], note="This script itself runs on Python, so it cannot be missing"),
    Tool(
        "aws",
        "EKS, EC2, SSM and CloudWatch queries (needed only for the EKS profile)",
        brew="awscli",
        download={"url": "https://awscli.amazonaws.com/awscli-exe-linux-{arch_x}.zip", "only_os": ["linux"], "bin": "aws", "post": "aws-install"},
        checks=["eks-platform", "controlplane-logs", "node-os(ssm)", "cost"],
        note="On macOS without brew, install https://awscli.amazonaws.com/AWSCLIV2.pkg directly",
    ),
    Tool(
        "helm",
        "Release status and values drift",
        brew="helm",
        download={"url": "https://get.helm.sh/helm-{tag}-{os}-{arch}.tar.gz", "version_repo": "helm/helm", "bin": "helm"},
        version_args=["version", "--short"],
        checks=["hygiene.helm-release"],
    ),
    Tool(
        "argocd",
        "Argo CD application status and diff (login required)",
        brew="argocd",
        download={"repo": "argoproj/argo-cd", "asset": "argocd-{os}-{arch}", "bin": "argocd"},
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
        download={"repo": "FairwindsOps/polaris", "asset": "polaris_{version}_{os}_{arch}.tar.gz", "bin": "polaris"},
        version_args=["version"],
        checks=["hygiene.polaris", "security.polaris"],
    ),
    Tool(
        "pluto", "Deprecated API detection", brew="FairwindsOps/tap/pluto", download={"repo": "FairwindsOps/pluto", "asset": "pluto_{version}_{os}_{arch}.tar.gz", "bin": "pluto"}, version_args=["version"], checks=["hygiene.deprecated-api"]
    ),
    Tool("kubent", "Deprecated API detection (complements Pluto)", brew="kubent", download={"repo": "doitintl/kube-no-trouble", "asset": "kubent-{version}-{os}-{arch}.tar.gz", "bin": "kubent"}, checks=["hygiene.deprecated-api"]),
    Tool("promtool", "PrometheusRule syntax validation (optional)", brew="prometheus", download={"repo": "prometheus/prometheus", "asset": "prometheus-{version}.{os}-{arch}.tar.gz", "bin": "promtool"}, checks=["observability.rule-syntax"]),
    Tool(
        "amtool",
        "Alertmanager routes and silences (optional)",
        brew=None,
        download={"repo": "prometheus/alertmanager", "asset": "alertmanager-{version}.{os}-{arch}.tar.gz", "bin": "amtool"},
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


def _get(url: str, timeout: float = 60) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=timeout) as resp:
        return resp.read()


def _latest_tag(repo: str) -> str:
    meta = json.loads(_get(f"https://api.github.com/repos/{repo}/releases/latest", 30).decode())
    return meta.get("tag_name") or ""


def _place_binary(blob: bytes, filename: str, bin_name: str, target: Path) -> str | None:
    """If it is an archive, extract the bin_name executable; otherwise use the file as-is. Returns the failure reason as a string, or None on success."""
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
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    target.write_bytes(data)
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return None


def _aws_install(blob: bytes, log=None) -> dict:
    """The aws CLI v2 Linux zip ships an install script. `-i` (install dir) and `-b` (binary link dir) install it without sudo."""
    work = shell.TOOLS_DIR / "aws-cli-src"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(work)
    installer = work / "aws" / "install"
    installer.chmod(0o755)
    for f in (work / "aws" / "dist").rglob("*"):
        if f.is_file():
            f.chmod(f.stat().st_mode | stat.S_IXUSR)
    dest = shell.TOOLS_DIR / "aws-cli"
    shell.TOOLS_BIN.mkdir(parents=True, exist_ok=True)
    r = shell.run([str(installer), "-i", str(dest), "-b", str(shell.TOOLS_BIN), "--update"], timeout=300, id="install.aws.installer", log=log)
    shutil.rmtree(work, ignore_errors=True)
    if not r.ok:
        return {"ok": False, "error": f"aws install script failed: {(r.error or r.stderr.strip())[-300:]}"}
    return {"ok": True}


def install_download(tool: Tool, log=None) -> dict:
    d = tool.download or {}
    method = "download"
    try:
        v = platform_vars()
        if d.get("repo"):
            tag = _latest_tag(d["repo"])
            method = f"download github {d['repo']} {tag}"
            version = tag[len(d["strip_tag"]) :] if d.get("strip_tag") and tag.startswith(d["strip_tag"]) else tag.lstrip("v")
            want = d["asset"].format(**v, tag=tag, version=version)
            meta = json.loads(_get(f"https://api.github.com/repos/{d['repo']}/releases/tags/{tag}", 30).decode())
            asset = next((a for a in meta.get("assets", []) if a.get("name") == want), None)
            if asset is None:
                names = ", ".join(a.get("name", "") for a in meta.get("assets", []) if not a.get("name", "").endswith((".sha256", ".asc", ".sig", ".json", ".pem")))[:400]
                return {"name": tool.name, "method": method, "ok": False, "error": f"asset {want} for this platform ({v['os']}/{v['arch']}) is not in release {tag}. Available: {names}"}
            url, filename = asset["browser_download_url"], want
        else:
            if d.get("version_url"):
                tag = _get(d["version_url"], 30).decode().strip()
            elif d.get("version_repo"):
                tag = _latest_tag(d["version_repo"])
            else:
                tag = ""
            version = tag.lstrip("v")
            url = d["url"].format(**v, tag=tag, version=version)
            filename = url.rsplit("/", 1)[-1]
            method = f"download {url}"
        blob = _get(url, 600)
        if d.get("post") == "aws-install":
            res = _aws_install(blob, log=log)
            if not res["ok"]:
                return {"name": tool.name, "method": method, "ok": False, "error": res["error"]}
            target = shell.TOOLS_BIN / d["bin"]
        else:
            target = shell.TOOLS_BIN / d["bin"]
            err = _place_binary(blob, filename, d["bin"], target)
            if err:
                return {"name": tool.name, "method": method, "ok": False, "error": err}
        if log is not None:
            log.command(id=f"install.{tool.name}", cmd=[method], code=0, seconds=0.0, out_path=str(target))
        return {"name": tool.name, "method": method, "ok": True, "error": None, "path": str(target), "version": tag}
    except Exception as e:  # any network or archive failure is reported only as an install failure
        return {"name": tool.name, "method": method, "ok": False, "error": f"{type(e).__name__}: {e}"}


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
    shell.TOOLS_BIN.mkdir(parents=True, exist_ok=True)
    target = shell.TOOLS_BIN / v["bin"]
    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(real)
    return {"name": tool.name, "method": method, "ok": True, "error": None, "path": str(target), "python": py}


def install_tool(tool: Tool, log=None) -> dict:
    """Try brew -> download -> venv -> pip in order. Never raises. If everything fails, the collected reasons are returned."""
    errors: list[str] = []
    if tool.brew and shell.which("brew"):
        if "/" in tool.brew:
            shell.run(["brew", "trust", "--formula", tool.brew], timeout=120, id=f"trust.{tool.name}", log=log)
        r = shell.run(["brew", "install", tool.brew], timeout=900, id=f"install.{tool.name}", log=log)
        if r.ok:
            return {"name": tool.name, "method": f"brew install {tool.brew}", "ok": True, "error": None}
        err = r.error or r.stderr.strip()
        if "Command Line Tools" in err:
            err = "brew requires a Command Line Tools update (sudo) for a source build"
        errors.append(f"brew: {err[-300:]}")
    if _download_applicable(tool):
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
    if tool.brew and shell.which("brew"):
        steps.append(f"brew install {tool.brew}" + (" (third-party tap: brew trust first)" if "/" in tool.brew else ""))
    if _download_applicable(tool):
        d = tool.download
        src = f"GitHub release {d['repo']}" if d.get("repo") else d["url"].split("/")[2]
        steps.append(f"official binary from {src} -> {shell.TOOLS_BIN}/")
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
