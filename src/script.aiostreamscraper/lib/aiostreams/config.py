import xbmc
import xbmcaddon

from .core import AIOStreamsEngine

ADDON_ID = 'script.aiostreamscraper'

# Kodi's addon settings dialog can trigger a RunScript action (e.g. the "Run
# Test Search" button) before it has finished flushing a just-edited setting
# to settings.xml on disk. Retry briefly rather than reporting "unconfigured".
SETTING_FLUSH_RETRIES = 4
SETTING_FLUSH_RETRY_DELAY_MS = 150


def get_engine():
    manifest_url = xbmcaddon.Addon(ADDON_ID).getSetting('manifest_url').strip()

    attempts = 0
    while not manifest_url and attempts < SETTING_FLUSH_RETRIES:
        xbmc.sleep(SETTING_FLUSH_RETRY_DELAY_MS)
        manifest_url = xbmcaddon.Addon(ADDON_ID).getSetting('manifest_url').strip()
        attempts += 1

    addon = xbmcaddon.Addon(ADDON_ID)
    timeout_val = addon.getSetting('timeout')
    timeout = int(timeout_val) if timeout_val else 10
    return AIOStreamsEngine(manifest_url=manifest_url, timeout=timeout)
