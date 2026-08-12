"""
Copies our CocoScrapers-compatible adapter into an already-installed CocoScrapers
addon's own scraper folder, so it shows up alongside CocoScrapers' bundled
scrapers without any manual file management. Front-end addons that already
support "CocoScrapers Module" as an external provider (Umbrella, FenLightAM,
etc.) then pick it up automatically, with no extra integration on their side.

CocoScrapers doesn't officially document this folder layout, so this module
discovers it at runtime instead of hardcoding folder names, and reports back
exactly what it did (or couldn't do) rather than failing silently.
"""
import os

import xbmc
import xbmcaddon
import xbmcvfs

OWN_ADDON_ID = 'script.aiostreamscraper'
COCOSCRAPERS_ADDON_ID = 'script.module.cocoscrapers'
ADAPTER_RELATIVE_PATH = ('lib', 'aiostreams', 'adapters', 'cocoscrapers.py')
LINKED_FILENAME = 'aiostreams.py'

MOVIE_FOLDER_CANDIDATES = ['sources_mv']
EPISODE_FOLDER_CANDIDATES = ['sources_ep', 'sources_tv', 'sources_sh', 'sources_episodes', 'sources_tvshows']


def _own_adapter_path():
    own_addon = xbmcaddon.Addon(OWN_ADDON_ID)
    own_path = xbmcvfs.translatePath(own_addon.getAddonInfo('path'))
    return os.path.join(own_path, *ADAPTER_RELATIVE_PATH)


def _find_existing_folder(base_dir, candidates):
    dirs, _files = xbmcvfs.listdir(base_dir)
    for candidate in candidates:
        if candidate in dirs:
            return candidate
    return None


def link_to_cocoscrapers():
    """
    Returns a dict describing what happened:
    {
        'cocoscrapers_installed': bool,
        'linked_movies': bool,
        'linked_episodes': bool,
        'episode_folder_used': str or None,
    }
    """
    result = {
        'cocoscrapers_installed': False,
        'linked_movies': False,
        'linked_episodes': False,
        'episode_folder_used': None,
    }

    coco_addon_path = xbmcvfs.translatePath(f"special://home/addons/{COCOSCRAPERS_ADDON_ID}/")
    if not xbmcvfs.exists(coco_addon_path):
        return result

    result['cocoscrapers_installed'] = True

    scrapers_base = os.path.join(coco_addon_path, 'lib', 'cocoscrapers')
    if not xbmcvfs.exists(scrapers_base + os.sep):
        xbmc.log(
            f"[script.aiostreamscraper] CocoScrapers is installed but "
            f"{scrapers_base} was not found; its internal layout may have changed.",
            xbmc.LOGWARNING,
        )
        return result

    source_file = _own_adapter_path()

    movie_folder = _find_existing_folder(scrapers_base, MOVIE_FOLDER_CANDIDATES)
    if movie_folder:
        dest = os.path.join(scrapers_base, movie_folder, LINKED_FILENAME)
        result['linked_movies'] = xbmcvfs.copy(source_file, dest)

    episode_folder = _find_existing_folder(scrapers_base, EPISODE_FOLDER_CANDIDATES)
    if episode_folder:
        dest = os.path.join(scrapers_base, episode_folder, LINKED_FILENAME)
        result['linked_episodes'] = xbmcvfs.copy(source_file, dest)
        result['episode_folder_used'] = episode_folder if result['linked_episodes'] else None

    return result
