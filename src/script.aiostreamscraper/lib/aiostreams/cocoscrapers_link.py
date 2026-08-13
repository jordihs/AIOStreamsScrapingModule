"""
Copies our CocoScrapers-compatible adapter into an already-installed CocoScrapers
addon's own scraper folder, so it shows up alongside CocoScrapers' bundled
scrapers without any manual file management. Front-end addons that already
support "CocoScrapers Module" as an external provider (Umbrella, FenLightAM,
etc.) then pick it up automatically, with no extra integration on their side.

Everything below was confirmed by downloading and reading CocoScrapers' actual
source (script.module.cocoscrapers, from its own repository zip) and by
reading Kodi's own log with debug logging on, rather than guessing, since none
of this is officially documented:

- Folder: lib/cocoscrapers/sources_cocoscrapers/torrents/, alongside bundled
  scrapers like bitlord.py and comet.py.
- Enablement: lib/cocoscrapers/__init__.py's enabledCheck() only calls a
  provider's sources() if CocoScrapers' own addon setting
  "provider.<module_name>" (module_name = filename without .py) is the
  string 'true'. Just being present in the folder is not enough.
- Addon.setSetting() on a key that ISN'T declared in that addon's own
  resources/settings.xml is a silent no-op, confirmed via Kodi's log:
  "requested setting (provider.aiostreamsscraper_jordihs) was not found."
  CocoScrapers' settings.xml only declares provider.* for its 20 bundled
  providers, so setSetting() alone can never enable ours - enabledCheck()
  always reads it back as unset. The fix is to add a real <setting> entry
  to CocoScrapers' settings.xml (as a sibling of the existing provider.*
  entries under section > category id="torrents" > the group that holds
  them), defaulted to enabled, rather than relying on setSetting() at all.
  This also has the side benefit of making it a real, visible, toggleable
  entry in CocoScrapers' own settings screen, same as its own providers.
"""
import os
import xml.etree.ElementTree as ET

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
LINKED_SETTING_ID = f'provider.{LINKED_MODULE_NAME}'

# Filenames used by earlier beta versions, before the rename above - cleaned
# up on every link so devices that ran an older beta don't keep a stale copy.
LEGACY_FILENAMES = ['aiostreams.py']

SCRAPERS_RELATIVE_PATH = ('lib', 'cocoscrapers', 'sources_cocoscrapers', 'torrents')
SETTINGS_XML_RELATIVE_PATH = ('resources', 'settings.xml')
LANGUAGE_STRINGS_RELATIVE_PATH = ('resources', 'language', 'resource.language.en_gb', 'strings.po')

# CocoScrapers' settings GUI resolves a setting's label by numeric string id
# only - a literal label like "AIOStreams" is silently not rendered (visible
# toggle, no text next to it). Picked well above CocoScrapers' own highest
# used id (32574 as of the version this was checked against) to avoid
# colliding with whatever it adds in future updates.
LINKED_LABEL_STRING_ID = '32990'
LINKED_LABEL_TEXT = 'AIOStreams'


def _own_adapter_path():
    own_addon = xbmcaddon.Addon(OWN_ADDON_ID)
    own_path = xbmcvfs.translatePath(own_addon.getAddonInfo('path'))
    return os.path.join(own_path, *ADAPTER_RELATIVE_PATH)


def _cocoscrapers_addon_path():
    path = xbmcvfs.translatePath(f"special://home/addons/{COCOSCRAPERS_ADDON_ID}/")
    return path if xbmcvfs.exists(path) else None


def _cocoscrapers_scrapers_dir(coco_addon_path):
    target_dir = os.path.join(coco_addon_path, *SCRAPERS_RELATIVE_PATH)
    if not xbmcvfs.exists(target_dir + os.sep):
        xbmc.log(
            f"[script.aiostreamscraper] CocoScrapers is installed but "
            f"{target_dir} was not found; its internal layout may have changed.",
            xbmc.LOGWARNING,
        )
        return None
    return target_dir


def _provider_module_names(target_dir):
    """Mirrors CocoScrapers' own torrents/__init__.py scan, so this list always
    matches whatever providers are actually installed on this device."""
    _dirs, files = xbmcvfs.listdir(target_dir)
    return [f[:-3] for f in files if f.endswith('.py') and not f.startswith('__')]


def _declare_provider_label_string(coco_addon_path):
    """
    Adds a strings.po entry for LINKED_LABEL_STRING_ID so the setting has a
    visible label in CocoScrapers' settings screen. Returns True if the
    string is present after this call (already there, or just added).
    """
    po_path = os.path.join(coco_addon_path, *LANGUAGE_STRINGS_RELATIVE_PATH)
    if not xbmcvfs.exists(po_path):
        return False

    marker = f'msgctxt "#{LINKED_LABEL_STRING_ID}"'

    try:
        with open(po_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as exc:
        xbmc.log(f"[script.aiostreamscraper] Could not read {po_path}: {exc}", xbmc.LOGWARNING)
        return False

    if marker in text:
        return True

    addition = f'\n{marker}\nmsgid "{LINKED_LABEL_TEXT}"\nmsgstr ""\n'

    try:
        with open(po_path, 'a', encoding='utf-8') as f:
            f.write(addition)
    except Exception as exc:
        xbmc.log(f"[script.aiostreamscraper] Could not write {po_path}: {exc}", xbmc.LOGWARNING)
        return False

    return True


def _declare_provider_setting(coco_addon_path):
    """
    Ensures LINKED_SETTING_ID exists as a real, declared setting (defaulted
    to enabled) in CocoScrapers' own resources/settings.xml. See module
    docstring for why this is required instead of just calling setSetting().
    Returns True if the setting is present after this call (already there,
    or just added), False if settings.xml couldn't be found/parsed/patched.
    """
    settings_xml_path = os.path.join(coco_addon_path, *SETTINGS_XML_RELATIVE_PATH)
    if not xbmcvfs.exists(settings_xml_path):
        return False

    try:
        tree = ET.parse(settings_xml_path)
    except Exception as exc:
        xbmc.log(f"[script.aiostreamscraper] Could not parse {settings_xml_path}: {exc}", xbmc.LOGWARNING)
        return False

    root = tree.getroot()
    label = LINKED_LABEL_STRING_ID if _declare_provider_label_string(coco_addon_path) else LINKED_LABEL_TEXT

    existing = root.find(f".//setting[@id='{LINKED_SETTING_ID}']")
    if existing is not None:
        if existing.get('label') == label:
            return True
        # Self-heals an entry created by an older version of this function
        # (e.g. one that used a literal label before it was known that
        # CocoScrapers' settings GUI only renders numeric-id labels).
        existing.set('label', label)
    else:
        target_group = None
        for group in root.iter('group'):
            if any(s.get('id', '').startswith('provider.') for s in group.findall('setting')):
                target_group = group
                break

        if target_group is None:
            xbmc.log(
                f"[script.aiostreamscraper] Could not find a provider.* settings group "
                f"in {settings_xml_path}; its schema may have changed.",
                xbmc.LOGWARNING,
            )
            return False

        new_setting = ET.SubElement(target_group, 'setting')
        new_setting.set('id', LINKED_SETTING_ID)
        new_setting.set('type', 'boolean')
        new_setting.set('label', label)
        new_setting.set('help', '')
        ET.SubElement(new_setting, 'level').text = '0'
        ET.SubElement(new_setting, 'default').text = 'true'
        ET.SubElement(new_setting, 'control').set('type', 'toggle')

    try:
        tree.write(settings_xml_path, encoding='UTF-8', xml_declaration=True)
    except Exception as exc:
        xbmc.log(f"[script.aiostreamscraper] Could not write {settings_xml_path}: {exc}", xbmc.LOGWARNING)
        return False

    return True


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

    coco_addon_path = _cocoscrapers_addon_path()
    result['cocoscrapers_installed'] = coco_addon_path is not None
    if not coco_addon_path:
        return result

    target_dir = _cocoscrapers_scrapers_dir(coco_addon_path)
    if not target_dir:
        return result

    for legacy_name in LEGACY_FILENAMES:
        legacy_path = os.path.join(target_dir, legacy_name)
        if xbmcvfs.exists(legacy_path):
            xbmcvfs.delete(legacy_path)

    dest = os.path.join(target_dir, LINKED_FILENAME)
    result['linked'] = xbmcvfs.copy(_own_adapter_path(), dest)

    if result['linked']:
        result['enabled'] = _declare_provider_setting(coco_addon_path)

    return result


def disable_other_cocoscrapers_providers():
    """
    Disables every other CocoScrapers torrent provider (by writing
    provider.<name>=false via the settings API - these ARE declared in
    CocoScrapers' schema already, so setSetting() works fine for them,
    unlike for our own), so AIOStreams becomes the sole source CocoScrapers
    searches. Destructive and has no undo - callers must confirm with the
    user before calling this.

    Returns a dict:
    {
        'cocoscrapers_installed': bool,
        'disabled_providers': [str, ...],
    }
    """
    result = {'cocoscrapers_installed': False, 'disabled_providers': []}

    coco_addon_path = _cocoscrapers_addon_path()
    result['cocoscrapers_installed'] = coco_addon_path is not None
    if not coco_addon_path:
        return result

    target_dir = _cocoscrapers_scrapers_dir(coco_addon_path)
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
