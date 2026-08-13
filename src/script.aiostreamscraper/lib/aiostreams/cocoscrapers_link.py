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
import json
import os
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcvfs

OWN_ADDON_ID = 'script.aiostreamscraper'
COCOSCRAPERS_ADDON_ID = 'script.module.cocoscrapers'
ADAPTER_RELATIVE_PATH = ('lib', 'aiostreams', 'adapters', 'cocoscrapers.py')

# This name is not just cosmetic: CocoScrapers uses the module's filename
# (module_name = filename minus .py) verbatim, uppercased, as the
# user-visible identifier in two places outside our control - Umbrella's
# "Remaining providers: ..." scrape-progress display and each result's
# scraper-thread name - so whatever this is set to is what the user sees
# during every search, not just in our own settings screen. Was
# "aiostreamsscraper_jordihs" through beta6 (deliberately not "aiostreams.py",
# to avoid colliding with whatever name CocoScrapers' own maintainers would
# use if they ever added native AIOStreams support) - shortened to "aios" to
# fix exactly that display, matching adapters/cocoscrapers.py's
# _PROVIDER_NAME (a separate, unrelated identifier - see that file's comment
# for why they must NOT be the same underlying constant even though they
# now happen to share a value).
LINKED_MODULE_NAME = 'aios'
LINKED_FILENAME = f'{LINKED_MODULE_NAME}.py'
LINKED_SETTING_ID = f'provider.{LINKED_MODULE_NAME}'

# Filenames AND provider.<name> setting ids used by earlier beta versions,
# before the renames above - cleaned up on every link so devices that ran an
# older beta don't keep a stale copy alongside the new one (a leftover file
# would still get loaded and scraped by CocoScrapers under its old identity;
# a leftover setting id would show as an orphaned, permanently-disabled-
# looking toggle with no provider behind it).
LEGACY_FILENAMES = ['aiostreams.py', 'aiostreamsscraper_jordihs.py']
LEGACY_SETTING_IDS = ['provider.aiostreamsscraper_jordihs']

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
    visible label in CocoScrapers' settings screen. Returns (ok, changed):
    ok is True if the string is present after this call (already there, or
    just added); changed is True only if this call actually wrote to disk.
    """
    po_path = os.path.join(coco_addon_path, *LANGUAGE_STRINGS_RELATIVE_PATH)
    if not xbmcvfs.exists(po_path):
        return False, False

    marker = f'msgctxt "#{LINKED_LABEL_STRING_ID}"'

    try:
        with open(po_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as exc:
        xbmc.log(f"[script.aiostreamscraper] Could not read {po_path}: {exc}", xbmc.LOGWARNING)
        return False, False

    if marker in text:
        return True, False

    addition = f'\n{marker}\nmsgid "{LINKED_LABEL_TEXT}"\nmsgstr ""\n'

    try:
        with open(po_path, 'a', encoding='utf-8') as f:
            f.write(addition)
    except Exception as exc:
        xbmc.log(f"[script.aiostreamscraper] Could not write {po_path}: {exc}", xbmc.LOGWARNING)
        return False, False

    return True, True


def _declare_provider_setting(coco_addon_path):
    """
    Ensures LINKED_SETTING_ID exists as a real, declared setting (defaulted
    to enabled) in CocoScrapers' own resources/settings.xml. See module
    docstring for why this is required instead of just calling setSetting().
    Returns (ok, changed): ok is True if the setting is present after this
    call (already there, or just added), False if settings.xml couldn't be
    found/parsed/patched; changed is True if this call (or the label-string
    call it makes) wrote anything to disk.
    """
    settings_xml_path = os.path.join(coco_addon_path, *SETTINGS_XML_RELATIVE_PATH)
    if not xbmcvfs.exists(settings_xml_path):
        return False, False

    try:
        tree = ET.parse(settings_xml_path)
    except Exception as exc:
        xbmc.log(f"[script.aiostreamscraper] Could not parse {settings_xml_path}: {exc}", xbmc.LOGWARNING)
        return False, False

    root = tree.getroot()
    label_ok, label_changed = _declare_provider_label_string(coco_addon_path)
    label = LINKED_LABEL_STRING_ID if label_ok else LINKED_LABEL_TEXT
    changed = label_changed

    # Drop any setting entry left behind by an older beta's module name -
    # its backing .py file is gone (removed via LEGACY_FILENAMES cleanup in
    # link_to_cocoscrapers()), so left alone this would show as a permanent
    # orphaned toggle for a provider that no longer exists.
    for group in root.iter('group'):
        for legacy_setting in list(group.findall('setting')):
            if legacy_setting.get('id') in LEGACY_SETTING_IDS:
                group.remove(legacy_setting)
                changed = True

    existing = root.find(f".//setting[@id='{LINKED_SETTING_ID}']")
    if existing is not None:
        if existing.get('label') == label:
            return True, changed
        # Self-heals an entry created by an older version of this function
        # (e.g. one that used a literal label before it was known that
        # CocoScrapers' settings GUI only renders numeric-id labels).
        existing.set('label', label)
        changed = True
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
            return False, changed

        new_setting = ET.SubElement(target_group, 'setting')
        new_setting.set('id', LINKED_SETTING_ID)
        new_setting.set('type', 'boolean')
        new_setting.set('label', label)
        new_setting.set('help', '')
        ET.SubElement(new_setting, 'level').text = '0'
        ET.SubElement(new_setting, 'default').text = 'true'
        ET.SubElement(new_setting, 'control').set('type', 'toggle')
        changed = True

    try:
        tree.write(settings_xml_path, encoding='UTF-8', xml_declaration=True)
    except Exception as exc:
        xbmc.log(f"[script.aiostreamscraper] Could not write {settings_xml_path}: {exc}", xbmc.LOGWARNING)
        return False, changed

    return True, changed


def _reload_cocoscrapers_addon():
    """
    Best-effort fix for an unconfirmed bug: our provider's toggle has
    repeatedly shown up in CocoScrapers' settings screen with no visible
    label (blank text next to the toggle) even though the underlying
    settings.xml/strings.po patch was independently confirmed correct on
    disk - never root-caused further than "Kodi is caching the parsed
    settings/strings somewhere a plain file edit doesn't invalidate".
    Confirmed on a real device (beta6) that SetAddonEnabled(false)+(true)
    ALONE did not fix it, so this now also fires Kodi's `UpdateLocalAddons`
    builtin first - the actual documented mechanism for "an installed
    addon's files changed on disk outside of Kodi's own install/update
    flow, make Kodi notice without a restart", which SetAddonEnabled may
    not trigger by itself (it might only flip a database flag rather than
    re-scanning the addon's files). Kept the enable/disable toggle too as a
    cheap second attempt. Only called when _declare_provider_setting
    actually changed something on disk, so this doesn't run on every
    ordinary startup once things are stable. If the label is STILL blank
    after this, the bug is very likely not a caching/reload problem at all
    (e.g. a real Kodi restart may be needed to prove the mechanism works
    under any condition, or the numeric string id itself may be wrong for
    some reason not yet identified) - see project memory before attempting
    a third reload variant blind.
    """
    try:
        xbmc.executebuiltin('UpdateLocalAddons')
    except Exception as exc:
        xbmc.log(
            f"[script.aiostreamscraper] _reload_cocoscrapers_addon: "
            f"UpdateLocalAddons failed: {exc}",
            xbmc.LOGWARNING,
        )

    for enabled in (False, True):
        try:
            xbmc.executeJSONRPC(json.dumps({
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'Addons.SetAddonEnabled',
                'params': {'addonid': COCOSCRAPERS_ADDON_ID, 'enabled': enabled},
            }))
        except Exception as exc:
            xbmc.log(
                f"[script.aiostreamscraper] _reload_cocoscrapers_addon: "
                f"SetAddonEnabled({enabled}) failed: {exc}",
                xbmc.LOGWARNING,
            )
            return


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
        result['enabled'], changed = _declare_provider_setting(coco_addon_path)
        if changed:
            _reload_cocoscrapers_addon()

        # Declaring the setting in CocoScrapers' SCHEMA (resources/settings.xml,
        # above) only controls what its settings GUI displays and what default
        # value Kodi would offer there - it does NOT, on its own, get written
        # into the separate per-profile VALUES file CocoScrapers actually reads
        # enablement from at runtime (special://profile/addon_data/
        # script.module.cocoscrapers/settings.xml, parsed directly by
        # control.py's make_settings_dict() - confirmed by reading that
        # function: it builds its enabled-providers dict purely from whatever
        # <setting> elements literally exist in that file, with no fallback to
        # the schema's declared default for a key that's simply absent).
        # Nothing else ever populates that file for a newly-added setting
        # unless the user happens to open CocoScrapers' own settings screen -
        # confirmed via live testing (beta8-10) that without this, our
        # provider is silently never enabled and sources() is never called at
        # all, no matter how many real searches run. Force it explicitly every
        # time instead. This also fires CocoScrapers' own registered
        # onSettingsChanged callback (its "Settings Monitor Service", visible
        # in kodi.log), which should refresh its cached enabled-providers dict
        # immediately - no separate reload needed for this specific value,
        # unlike the still-unconfirmed settings-GUI label bug _reload_
        # cocoscrapers_addon() targets. If Kodi hasn't picked up a
        # brand-new setting id in its own addon-schema cache yet this session
        # (same class of lag as that label bug), this call may silently no-op
        # - harmless, since this whole function reruns every Kodi startup
        # (while link_cocoscrapers_service stays on) and will retry.
        xbmcaddon.Addon(COCOSCRAPERS_ADDON_ID).setSetting(LINKED_SETTING_ID, 'true')

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
