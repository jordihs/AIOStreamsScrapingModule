#!/usr/bin/env python3
"""
Package the Kodi addons in src/ and assemble Kodi addon repositories.

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

- local-repo/                     a Kodi repository pointing at itself on local disk,
                                   for fast iteration on the same machine running Kodi
                                   (never committed, see .gitignore). Local folders are
                                   natively browsable by Kodi's file source, so unlike
                                   docs/ this needs no index.html workaround. Its copy
                                   of script.aiostreamscraper always gets a fresh,
                                   timestamp-suffixed version, so every rebuild looks
                                   like a new update to Kodi with no manual version
                                   bump needed. It uses a distinct repository addon id
                                   (repository.aiostreamscraper.local) so it can't
                                   collide with the real repository.aiostreamscraper if
                                   both ever end up installed on the same machine.
"""
import hashlib
import html
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
DIST_DIR = ROOT / "dist"
DOCS_DIR = ROOT / "docs"
LOCAL_REPO_DIR = ROOT / "local-repo"
LOCAL_REPO_HTTP_PORT = 8642

ADDON_IDS = ["script.aiostreamscraper", "repository.aiostreamscraper"]
LOCAL_REPO_ADDON_ID = "repository.aiostreamscraper.local"
# Bump whenever this wrapper's own addon.xml content changes (its <dir> URLs,
# description, etc.) so an already-installed copy on a test machine is
# recognized as updatable rather than silently keeping stale content.
LOCAL_REPO_WRAPPER_VERSION = "1.0.2"

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


def patched_addon_xml(addon_dir, version_override=None):
    """Returns (addon_xml_text, effective_version). If version_override is set
    and differs from the real version in src/, the version= attribute is
    patched in the returned text only - the file on disk is never touched."""
    real_version = get_version(addon_dir)
    text = (addon_dir / "addon.xml").read_text(encoding="utf-8")
    version = version_override or real_version
    if version != real_version:
        text = text.replace(f'version="{real_version}"', f'version="{version}"', 1)
    return text, version


def zip_addon(addon_id, out_dir, version_override=None):
    addon_dir = SRC_DIR / addon_id
    if not addon_dir.is_dir():
        raise SystemExit(f"Addon source not found at {addon_dir}")

    addon_xml_text, version = patched_addon_xml(addon_dir, version_override)

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{addon_id}-{version}.zip"

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in iter_files(addon_dir):
            arcname = Path(addon_id) / file_path.relative_to(addon_dir)
            if file_path.name == "addon.xml":
                zf.writestr(str(arcname), addon_xml_text)
            else:
                zf.write(file_path, arcname)

    return zip_path, addon_xml_text


def build_standalone_zips():
    for addon_id in ADDON_IDS:
        zip_path, _ = zip_addon(addon_id, DIST_DIR)
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
        _zip_path, addon_xml_text = zip_addon(addon_id, out_dir)

        icon_src = addon_dir / "icon.png"
        if icon_src.is_file():
            (out_dir / "icon.png").write_bytes(icon_src.read_bytes())

        addons_root.append(ET.fromstring(addon_xml_text))
        write_directory_index(out_dir)

    DOCS_DIR.mkdir(exist_ok=True)
    ET.indent(addons_root, space="    ")
    addons_xml_bytes = ET.tostring(addons_root, encoding="UTF-8", xml_declaration=True)
    (DOCS_DIR / "addons.xml").write_bytes(addons_xml_bytes)

    checksum = hashlib.md5(addons_xml_bytes).hexdigest()
    (DOCS_DIR / "addons.xml.md5").write_text(checksum, encoding="utf-8")

    write_directory_index(DOCS_DIR)

    print(f"Assembled {DOCS_DIR.relative_to(ROOT)} (addons.xml, addons.xml.md5, per-addon zips, index.html)")


def _local_repo_addon_xml(repo_path):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="{LOCAL_REPO_ADDON_ID}" name="AIOStreams Scraper Repository (Local)" version="{LOCAL_REPO_WRAPPER_VERSION}" provider-name="Jordihs">
    <extension point="xbmc.addon.repository" name="AIOStreams Scraper Repository (Local)">
        <dir>
            <info compressed="false">{repo_path}/addons.xml</info>
            <checksum>{repo_path}/addons.xml.md5</checksum>
            <datadir zip="true">{repo_path}</datadir>
        </dir>
    </extension>
    <extension point="xbmc.addon.metadata">
        <summary lang="en_GB">AIOStreams Scraper Repository (Local)</summary>
        <description lang="en_GB">Local-only repository for rapid development iteration. Not for distribution.</description>
        <platform>all</platform>
        <assets>
            <icon>icon.png</icon>
        </assets>
    </extension>
</addon>
'''


def build_local_repo():
    for old_zip in LOCAL_REPO_DIR.glob("*/*.zip"):
        old_zip.unlink()

    LOCAL_REPO_DIR.mkdir(exist_ok=True)
    repo_path = f"http://127.0.0.1:{LOCAL_REPO_HTTP_PORT}"

    addons_root = ET.Element("addons")

    # script.aiostreamscraper: always a fresh, higher version than last time,
    # so Kodi sees an update available on every rebuild with no manual bump.
    local_version = f"{get_version(SRC_DIR / 'script.aiostreamscraper')}+local{int(time.time())}"
    out_dir = LOCAL_REPO_DIR / "script.aiostreamscraper"
    _zip_path, addon_xml_text = zip_addon("script.aiostreamscraper", out_dir, version_override=local_version)
    icon_src = SRC_DIR / "script.aiostreamscraper" / "icon.png"
    if icon_src.is_file():
        (out_dir / "icon.png").write_bytes(icon_src.read_bytes())
    addons_root.append(ET.fromstring(addon_xml_text))

    # The local repository wrapper itself - not under src/, built directly here.
    repo_xml_text = _local_repo_addon_xml(repo_path)
    repo_out_dir = LOCAL_REPO_DIR / LOCAL_REPO_ADDON_ID
    repo_out_dir.mkdir(parents=True, exist_ok=True)
    repo_zip_path = repo_out_dir / f"{LOCAL_REPO_ADDON_ID}-{LOCAL_REPO_WRAPPER_VERSION}.zip"
    if repo_zip_path.exists():
        repo_zip_path.unlink()
    with zipfile.ZipFile(repo_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{LOCAL_REPO_ADDON_ID}/addon.xml", repo_xml_text)
        repo_icon_src = SRC_DIR / "repository.aiostreamscraper" / "icon.png"
        if repo_icon_src.is_file():
            zf.writestr(f"{LOCAL_REPO_ADDON_ID}/icon.png", repo_icon_src.read_bytes())
    if repo_icon_src.is_file():
        (repo_out_dir / "icon.png").write_bytes(repo_icon_src.read_bytes())
    addons_root.append(ET.fromstring(repo_xml_text))

    ET.indent(addons_root, space="    ")
    addons_xml_bytes = ET.tostring(addons_root, encoding="UTF-8", xml_declaration=True)
    (LOCAL_REPO_DIR / "addons.xml").write_bytes(addons_xml_bytes)
    checksum = hashlib.md5(addons_xml_bytes).hexdigest()
    (LOCAL_REPO_DIR / "addons.xml.md5").write_text(checksum, encoding="utf-8")

    plain_path = str(LOCAL_REPO_DIR.resolve())
    print(f"Assembled {LOCAL_REPO_DIR.relative_to(ROOT)} (script.aiostreamscraper {local_version})")
    print(f"Kodi File Manager source for installing the repo zip (unchanged): {plain_path}")
    print(f"Run 'python serve_local_repo.py' and keep it running for the repository's")
    print(f"internal fetch (Install from repository) to work: {repo_path}")


if __name__ == "__main__":
    build_standalone_zips()
    build_repo()
    build_local_repo()
