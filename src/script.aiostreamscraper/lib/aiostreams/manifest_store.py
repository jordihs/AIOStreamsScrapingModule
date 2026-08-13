"""
Stores the AIOStreams manifest URL as a plain file in the addon's profile
data folder, instead of through Kodi's addon-settings API
(xbmcaddon.Addon.getSetting/setSetting).

Why: the manifest URL used to be a native settings.xml type="text" field.
That was the only mechanism found to reliably PERSIST an externally-set
value (see the settings-redesign saga in project memory) - but it was an
unusable focus trap in the settings dialog itself: the value is a long URL,
and pressing left/right on a controller while the row is focused moves the
in-row text caret instead of leaving the field, making every other setting
above it nearly unreachable. Earlier attempts at a popup-button workaround
(RunScript + xbmcaddon.Addon().setSetting()) reliably lost data whenever the
native settings dialog was left open while the external write happened,
seemingly racing the dialog's own in-memory model - and the dialog is
supposed to stay open now (see main.py), so that workaround is a dead end
here regardless of the data-loss issue.

Storing the value in our own file sidesteps both problems at once: nothing
about it is rendered as a settings-dialog row (no caret trap), and nothing
about it goes through xbmcaddon.Addon().setSetting() (no dialog-model race),
no matter whether the settings dialog is open, closed, or was never opened
this session.
"""
import xbmcaddon
import xbmcvfs

ADDON_ID = 'script.aiostreamscraper'
_FILENAME = 'manifest_url.txt'


def _profile_dir():
    addon = xbmcaddon.Addon(ADDON_ID)
    path = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    if not xbmcvfs.exists(path):
        xbmcvfs.mkdirs(path)
    return path


def _store_path():
    return _profile_dir() + _FILENAME


def get_manifest_url():
    path = _store_path()
    if xbmcvfs.exists(path):
        f = xbmcvfs.File(path)
        try:
            value = f.read().strip()
        finally:
            f.close()
        if value:
            return value

    # One-time migration: earlier betas stored the URL in the native
    # `manifest_url` settings.xml field (kept declared, but hidden, purely
    # so this still resolves) - pick it up once so upgrading doesn't lose an
    # already-configured URL, then never touch that field again.
    addon = xbmcaddon.Addon(ADDON_ID)
    legacy_value = addon.getSetting('manifest_url').strip()
    if legacy_value:
        set_manifest_url(legacy_value)
        return legacy_value

    return ''


def set_manifest_url(value):
    value = (value or '').strip()
    f = xbmcvfs.File(_store_path(), 'w')
    try:
        f.write(value)
    finally:
        f.close()
    return value
