"""
Copies our CocoScrapers-compatible adapter into an already-installed CocoScrapers
addon's own scraper folder, so it shows up alongside CocoScrapers' bundled
scrapers without any manual file management. Front-end addons that already
support "CocoScrapers Module" as an external provider (Umbrella, FenLightAM,
etc.) then pick it up automatically, with no extra integration on their side.

The target folder and the enable mechanism below were both confirmed by
downloading and reading CocoScrapers' actual source
(script.module.cocoscrapers, from its own repository zip) rather than
guessing, since it isn't officially documented:

- Folder: lib/cocoscrapers/sources_cocoscrapers/torrents/, alongside
  bundled scrapers like bitlord.py and comet.py.
- Enablement: lib/cocoscrapers/__init__.py's enabledCheck() only calls a
  provider's sources() if CocoScrapers' own addon setting
  "provider.<module_name>" (module_name = filename without .py) is the
  string 'true'. New files just being present in the folder is not
  enough - CocoScrapers' settings.xml only declares GUI toggles for its
  20 bundled providers, so an unlisted provider's setting key doesn't
  exist until something writes it. Kodi allows any addon to read/write
  another addon's settings by id even when undeclared in that addon's
  settings.xml, so we set it directly via the settings API instead of
  trying to edit CocoScrapers' settings.xml.
"""
import os

import xbmc
import xbmcaddon
import xbmcvfs

OWN_ADDON_ID = 'script.aiostreamscraper'
COCOSCRAPERS_ADDON_ID = 'script.module.cocoscrapers'
ADAPTER_RELATIVE_PATH = ('lib', 'aiostreams', 'adapters', 'cocoscrapers.py')

# Deliberately not "aiostreams.py": if CocoScrapers' own maintainers ever add
# native AIOStreams support, that's the name they would most likely use, and
# we don't want to collide with (or silently shadow) their file.
LINKED_MODULE_NAME = 'aiostreamsscraper_jordihs'
LINKED_FILENAME = f'{LINKED_MODULE_NAME}.py'

# Filenames used by earlier beta versions, before the rename above - cleaned
# up on every link so devices that ran an older beta don't keep a stale copy.
LEGACY_FILENAMES = ['aiostreams.py']

SCRAPERS_RELATIVE_PATH = ('lib', 'cocoscrapers', 'sources_cocoscrapers', 'torrents')


def _own_adapter_path():
    own_addon = xbmcaddon.Addon(OWN_ADDON_ID)
    own_path = xbmcvfs.translatePath(own_addon.getAddonInfo('path'))
    return os.path.join(own_path, *ADAPTER_RELATIVE_PATH)


def _cocoscrapers_scrapers_dir():
    """Returns (installed, target_dir_or_None)."""
    coco_addon_path = xbmcvfs.translatePath(f"special://home/addons/{COCOSCRAPERS_ADDON_ID}/")
    if not xbmcvfs.exists(coco_addon_path):
        return False, None

    target_dir = os.path.join(coco_addon_path, *SCRAPERS_RELATIVE_PATH)
    if not xbmcvfs.exists(target_dir + os.sep):
        xbmc.log(
            f"[script.aiostreamscraper] CocoScrapers is installed but "
            f"{target_dir} was not found; its internal layout may have changed.",
            xbmc.LOGWARNING,
        )
        return True, None

    return True, target_dir


def _provider_module_names(target_dir):
    """Mirrors CocoScrapers' own torrents/__init__.py scan, so this list always
    matches whatever providers are actually installed on this device."""
    _dirs, files = xbmcvfs.listdir(target_dir)
    return [f[:-3] for f in files if f.endswith('.py') and not f.startswith('__')]


def link_to_cocoscrapers():
    """
    Returns a dict describing what happened:
    {
        'cocoscrapers_installed': bool,
        'linked': bool,
        'enabled': bool,
    }
    """
    result = {'cocoscrapers_installed': False, 'linked': False, 'enabled': False}

    installed, target_dir = _cocoscrapers_scrapers_dir()
    result['cocoscrapers_installed'] = installed
    if not target_dir:
        return result

    for legacy_name in LEGACY_FILENAMES:
        legacy_path = os.path.join(target_dir, legacy_name)
        if xbmcvfs.exists(legacy_path):
            xbmcvfs.delete(legacy_path)

    dest = os.path.join(target_dir, LINKED_FILENAME)
    result['linked'] = xbmcvfs.copy(_own_adapter_path(), dest)

    if result['linked']:
        coco_addon = xbmcaddon.Addon(COCOSCRAPERS_ADDON_ID)
        coco_addon.setSetting(f'provider.{LINKED_MODULE_NAME}', 'true')
        result['enabled'] = True

    return result


def disable_other_cocoscrapers_providers():
    """
    Disables every other CocoScrapers torrent provider (by writing
    provider.<name>=false via the settings API, same mechanism as
    link_to_cocoscrapers' enablement), so AIOStreams becomes the sole
    source CocoScrapers searches. Destructive and has no undo - callers
    must confirm with the user before calling this.

    Returns a dict:
    {
        'cocoscrapers_installed': bool,
        'disabled_providers': [str, ...],
    }
    """
    result = {'cocoscrapers_installed': False, 'disabled_providers': []}

    installed, target_dir = _cocoscrapers_scrapers_dir()
    result['cocoscrapers_installed'] = installed
    if not target_dir:
        return result

    coco_addon = xbmcaddon.Addon(COCOSCRAPERS_ADDON_ID)
    disabled = []
    for module_name in _provider_module_names(target_dir):
        if module_name == LINKED_MODULE_NAME:
            continue
        coco_addon.setSetting(f'provider.{module_name}', 'false')
        disabled.append(module_name)

    result['disabled_providers'] = disabled
    return result
