"""
Copies our CocoScrapers-compatible adapter into an already-installed CocoScrapers
addon's own scraper folder, so it shows up alongside CocoScrapers' bundled
scrapers without any manual file management. Front-end addons that already
support "CocoScrapers Module" as an external provider (Umbrella, FenLightAM,
etc.) then pick it up automatically, with no extra integration on their side.

The target folder was confirmed by inspecting a real CocoScrapers install
(lib/cocoscrapers/sources_cocoscrapers/torrents/, alongside scrapers like
bitlord.py and comet.py) - CocoScrapers doesn't officially document this
layout, so if it's ever wrong again this fails loud (logged) rather than
silently.
"""
import os

import xbmc
import xbmcaddon
import xbmcvfs

OWN_ADDON_ID = 'script.aiostreamscraper'
COCOSCRAPERS_ADDON_ID = 'script.module.cocoscrapers'
ADAPTER_RELATIVE_PATH = ('lib', 'aiostreams', 'adapters', 'cocoscrapers.py')
LINKED_FILENAME = 'aiostreams.py'

SCRAPERS_RELATIVE_PATH = ('lib', 'cocoscrapers', 'sources_cocoscrapers', 'torrents')


def _own_adapter_path():
    own_addon = xbmcaddon.Addon(OWN_ADDON_ID)
    own_path = xbmcvfs.translatePath(own_addon.getAddonInfo('path'))
    return os.path.join(own_path, *ADAPTER_RELATIVE_PATH)


def link_to_cocoscrapers():
    """
    Returns a dict describing what happened:
    {
        'cocoscrapers_installed': bool,
        'linked': bool,
    }
    """
    result = {
        'cocoscrapers_installed': False,
        'linked': False,
    }

    coco_addon_path = xbmcvfs.translatePath(f"special://home/addons/{COCOSCRAPERS_ADDON_ID}/")
    if not xbmcvfs.exists(coco_addon_path):
        return result

    result['cocoscrapers_installed'] = True

    target_dir = os.path.join(coco_addon_path, *SCRAPERS_RELATIVE_PATH)
    if not xbmcvfs.exists(target_dir + os.sep):
        xbmc.log(
            f"[script.aiostreamscraper] CocoScrapers is installed but "
            f"{target_dir} was not found; its internal layout may have changed.",
            xbmc.LOGWARNING,
        )
        return result

    dest = os.path.join(target_dir, LINKED_FILENAME)
    result['linked'] = xbmcvfs.copy(_own_adapter_path(), dest)

    return result
