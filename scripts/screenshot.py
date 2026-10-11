#!/usr/bin/env python3
"""Screenshot an itinerary page at phone width with whatever headless browser exists.

Usage: python3 screenshot.py out/index.html shots/ [--dark]

Looks for Chrome, Chromium or Edge (macOS, Linux, Windows paths and $PATH).
Writes shots/page.png, plus shots/part-1.png, part-2.png ... (2400 px slices)
when Pillow is installed, so each slice is small enough to view.
Exits with code 2 and a message if no browser is found: skip the visual
check and tell the user.
"""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge"]


def find_browser():
    for p in CANDIDATES:
        if Path(p).exists():
            return p
    for n in NAMES:
        w = shutil.which(n)
        if w:
            return w
    # Playwright's bundled Chromium, if installed
    for root in [Path.home() / ".cache/ms-playwright", Path.home() / "Library/Caches/ms-playwright"]:
        for exe in list(root.glob("chromium-*/chrome-linux/chrome")) + list(root.glob("chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium")):
            return str(exe)
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    page, outdir = Path(args[0]).resolve(), Path(args[1])
    outdir.mkdir(parents=True, exist_ok=True)
    browser = find_browser()
    if not browser:
        print("No headless browser found (Chrome/Chromium/Edge/Playwright). Skip the visual check and say so.")
        sys.exit(2)
    src = page
    if "--dark" in sys.argv or "--light" in sys.argv:
        theme = "dark" if "--dark" in sys.argv else "light"
        tmp = Path(tempfile.mkdtemp()) / page.name
        tmp.write_text(page.read_text().replace('<html lang="en">', f'<html lang="en" data-theme="{theme}">', 1))
        src = tmp
    shot = outdir / "page.png"
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
           "--window-size=500,9000", "--virtual-time-budget=12000", f"--screenshot={shot}", src.as_uri()]
    subprocess.run(cmd, capture_output=True, timeout=120)
    if not shot.exists():
        print("Browser ran but produced no screenshot. Skip the visual check and say so.")
        sys.exit(2)
    try:
        from PIL import Image
        im = Image.open(shot)
        w, h = im.size
        px = im.load()
        bg = px[w - 2, h - 2]
        last = h - 1
        while last > 0 and all(px[x, last] == bg for x in range(0, w, 25)):
            last -= 1
        n = 0
        for top in range(0, last + 1, 2400):
            n += 1
            im.crop((0, top, w, min(top + 2400, last + 20))).save(outdir / f"part-{n}.png")
        print(f"Wrote {shot} and {n} slices (part-1.png ... part-{n}.png)")
    except ImportError:
        print(f"Wrote {shot} (install Pillow to get viewable slices)")


if __name__ == "__main__":
    main()
