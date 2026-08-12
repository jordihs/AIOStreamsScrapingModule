#!/usr/bin/env python3
"""
Package the Kodi addons in src/ and assemble a Kodi addon repository under docs/.

- dist/<addon-id>-<version>.zip   standalone zips for manual "install from zip file"
                                   testing (not committed, see .gitignore)

- docs/                           a full Kodi repository (addons.xml + addons.xml.md5
                                   + per-addon zip/icon + browsable index.html files),
                                   meant to be committed and pushed, then served via
                                   GitHub Pages (Settings -> Pages -> Deploy from branch
                                   -> main -> /docs). The "docs" folder name is required
                                   by GitHub Pages' branch-folder deploy option.

                                   Two hosts are involved on purpose:
                                   - GitHub Pages serves index.html listings so Kodi's
                                     File Manager source can browse to and install the
                                     repository zip (raw.githubusercontent.com returns
                                     404 for folder paths, it can't do that).
                                   - raw.githubusercontent.com serves the exact files
                                     (addons.xml / checksum / addon zips) that Kodi's
                                     repository engine fetches by constructed URL once
                                     the repository addon is installed - see
                                     src/repository.aiostreamscraper/addon.xml.
"""
import hashlib
import html
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
DIST_DIR = ROOT / "dist"
DOCS_DIR = ROOT / "docs"

ADDON_IDS = ["script.aiostreamscraper", "repository.aiostreamscraper"]

EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDE_DIRS = {"__pycache__"}


def get_version(addon_dir):
    addon_xml = (addon_dir / "addon.xml").read_text(encoding="utf-8")
    match = re.search(r'<addon\b[^>]*\bversion="([^"]+)"', addon_xml)
    if not match:
        raise SystemExit(f"Could not find version= in {addon_dir / 'addon.xml'}")
    return match.group(1)


def iter_files(addon_dir):
    for path in addon_dir.rglob("*"):
        if path.is_dir():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.suffix in EXCLUDE_SUFFIXES:
            continue
        yield path


def zip_addon(addon_id, out_dir):
    addon_dir = SRC_DIR / addon_id
    if not addon_dir.is_dir():
        raise SystemExit(f"Addon source not found at {addon_dir}")

    version = get_version(addon_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{addon_id}-{version}.zip"

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in iter_files(addon_dir):
            arcname = Path(addon_id) / file_path.relative_to(addon_dir)
            zf.write(file_path, arcname)

    return zip_path


def build_standalone_zips():
    for addon_id in ADDON_IDS:
        zip_path = zip_addon(addon_id, DIST_DIR)
        print(f"Built {zip_path.relative_to(ROOT)}")


def write_directory_index(dir_path):
    """
    A minimal directory listing Kodi's HTTP file-source browser can parse: it expects
    an <a href="name">name</a> per entry, with the link text equal to the href.
    """
    entries = sorted(
        p.name + ("/" if p.is_dir() else "")
        for p in dir_path.iterdir()
        if p.name != "index.html"
    )
    items = "\n".join(
        f'    <li><a href="{html.escape(e)}">{html.escape(e)}</a></li>' for e in entries
    )
    page = (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"utf-8\"><title>Index</title></head>\n"
        f"<body>\n<ul>\n{items}\n</ul>\n</body></html>\n"
    )
    (dir_path / "index.html").write_text(page, encoding="utf-8")


def build_repo():
    for old_zip in DOCS_DIR.glob("*/*.zip"):
        old_zip.unlink()

    addons_root = ET.Element("addons")

    for addon_id in ADDON_IDS:
        addon_dir = SRC_DIR / addon_id
        out_dir = DOCS_DIR / addon_id
        zip_addon(addon_id, out_dir)

        icon_src = addon_dir / "icon.png"
        if icon_src.is_file():
            (out_dir / "icon.png").write_bytes(icon_src.read_bytes())

        addons_root.append(ET.parse(addon_dir / "addon.xml").getroot())
        write_directory_index(out_dir)

    DOCS_DIR.mkdir(exist_ok=True)
    ET.indent(addons_root, space="    ")
    addons_xml_bytes = ET.tostring(addons_root, encoding="UTF-8", xml_declaration=True)
    (DOCS_DIR / "addons.xml").write_bytes(addons_xml_bytes)

    checksum = hashlib.md5(addons_xml_bytes).hexdigest()
    (DOCS_DIR / "addons.xml.md5").write_text(checksum, encoding="utf-8")

    write_directory_index(DOCS_DIR)

    print(f"Assembled {DOCS_DIR.relative_to(ROOT)} (addons.xml, addons.xml.md5, per-addon zips, index.html)")


if __name__ == "__main__":
    build_standalone_zips()
    build_repo()
