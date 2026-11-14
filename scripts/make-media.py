#!/usr/bin/env python3
"""Make the pictures README shows from the committed sample reports: a still of the top of a full report and a scroll through a daily report.

Usage: uvx --with playwright --with markdown python scripts/make-media.py [--chromium <path to a Chromium binary>]

    docs/media/report-full.png, report-full.ko.png     the first screen and the first problem of samples/<lang>/eks/full/report.md
    docs/media/report-daily.gif, report-daily.ko.gif   samples/<lang>/k3s/daily/report.md, scrolled from top to bottom

The reports are rendered from Markdown with the style below (GitHub's look, so the picture shows what a reader sees on the repository page).
Needs ffmpeg on PATH for the GIFs. Without --chromium the newest Chromium in Playwright's cache is used (`playwright install chromium` puts one there).
"""

import argparse
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MEDIA = ROOT / "docs" / "media"
CSS = """
body{margin:0;background:#f6f8fa;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;color:#1f2328}
.wrap{max-width:900px;margin:32px auto;background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:40px 48px;font-size:16px;line-height:1.6}
h1{font-size:28px;border-bottom:1px solid #d8dee4;padding-bottom:8px;margin-top:0}
h2{font-size:23px;border-bottom:1px solid #d8dee4;padding-bottom:6px;margin-top:36px}
h3{font-size:19px;margin-top:28px}
code{background:#f6f8fa;padding:2px 6px;border-radius:6px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:85%}
pre{background:#f6f8fa;padding:14px;border-radius:6px;overflow:hidden;font-size:85%}
pre code{background:none;padding:0}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}
th,td{border:1px solid #d0d7de;padding:6px 12px;text-align:left;vertical-align:top}
th{background:#f6f8fa}
ul{padding-left:24px}
strong{font-weight:600}
a{color:#0969da;text-decoration:none}
"""


def html_of(md_path: pathlib.Path, *, until_heading: str | None = None) -> str:
    import markdown

    text = md_path.read_text(encoding="utf-8")
    if until_heading:  # keep the report up to the line that starts the named section of its first problem
        lines, out, seen = text.splitlines(), [], 0
        for ln in lines:
            if ln.startswith("### ") and ln[4:].strip() == until_heading:
                seen += 1
                if seen == 1:
                    break
            out.append(ln)
        text = "\n".join(out)
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='wrap'>{body}</div></body></html>"


def chromium_path(given: str | None) -> str | None:
    if given:
        return given
    cache = pathlib.Path.home() / "Library" / "Caches" / "ms-playwright"
    if not cache.is_dir():
        cache = pathlib.Path.home() / ".cache" / "ms-playwright"
    found = sorted(cache.glob("chromium_headless_shell-*/*/chrome-headless-shell")) + sorted(cache.glob("chromium-*/*/chrome"))
    return str(found[-1]) if found else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chromium", help="path to a Chromium or chrome-headless-shell binary")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright

    exe = chromium_path(a.chromium)
    stills = [("en", "report-full.png", "Why it comes about"), ("ko", "report-full.ko.png", "왜 생기나")]
    scrolls = [("en", "report-daily.gif"), ("ko", "report-daily.ko.gif")]
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        for lang, name, until in stills:
            page = browser.new_page(viewport={"width": 1000, "height": 900}, device_scale_factor=1.5)
            page.set_content(html_of(ROOT / "samples" / lang / "eks" / "full" / "report.md", until_heading=until))
            page.locator(".wrap").screenshot(path=str(MEDIA / name))
            page.close()
            print(MEDIA / name)
        for lang, name in scrolls:
            page = browser.new_page(viewport={"width": 1000, "height": 720}, device_scale_factor=1)
            page.set_content(html_of(ROOT / "samples" / lang / "k3s" / "daily" / "report.md"))
            height = page.evaluate("document.documentElement.scrollHeight")
            with tempfile.TemporaryDirectory() as tmp:
                step, y, n = 90, 0, 0
                while True:
                    page.evaluate(f"window.scrollTo(0, {y})")
                    for _ in range(10 if y == 0 else 2):  # hold the first screen a little longer; two frames a step keep the text readable while it moves
                        page.screenshot(path=f"{tmp}/f{n:04d}.png")
                        n += 1
                    if y + 720 >= height:
                        break
                    y += step
                for _ in range(12):  # and the last
                    page.screenshot(path=f"{tmp}/f{n:04d}.png")
                    n += 1
                flt = "fps=6,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=24[p];[s1][p]paletteuse=dither=none"
                r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "6", "-i", f"{tmp}/f%04d.png", "-vf", flt, str(MEDIA / name)], check=False, capture_output=True, text=True)
                if r.returncode:
                    sys.exit(f"ffmpeg failed: {r.stderr[-300:]}")
            page.close()
            print(MEDIA / name, f"({n} frames)")
        browser.close()


if __name__ == "__main__":
    main()
