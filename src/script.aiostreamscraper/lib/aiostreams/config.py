from urllib.parse import urlparse

import xbmc
import xbmcaddon

from .core import AIOStreamsEngine

ADDON_ID = 'script.aiostreamscraper'


def get_engine():
    addon = xbmcaddon.Addon(ADDON_ID)
    manifest_url = addon.getSetting('manifest_url').strip()
    timeout_val = addon.getSetting('timeout')
    timeout = int(timeout_val) if timeout_val else 10

    # Never log the full manifest_url - AIOStreams manifest URLs commonly
    # embed API keys/config in the path.
    host = urlparse(manifest_url).hostname if manifest_url else None
    xbmc.log(
        f"[script.aiostreamscraper] get_engine: manifest_url_set={bool(manifest_url)} "
        f"host={host} timeout={timeout}s",
        xbmc.LOGINFO,
    )

    return AIOStreamsEngine(manifest_url=manifest_url, timeout=timeout)
