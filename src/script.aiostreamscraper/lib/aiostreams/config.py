from urllib.parse import urlparse

import xbmc
import xbmcaddon

from .core import AIOStreamsEngine
from .manifest_store import get_manifest_url

ADDON_ID = 'script.aiostreamscraper'


def get_engine():
    addon = xbmcaddon.Addon(ADDON_ID)
    manifest_url = get_manifest_url()
    timeout_val = addon.getSetting('timeout')
    timeout = int(timeout_val) if timeout_val else 10
    use_emoji_metadata = addon.getSettingBool('use_emoji_metadata')
    debug_logging = addon.getSettingBool('debug_logging')

    # Never log the full manifest_url - AIOStreams manifest URLs commonly
    # embed API keys/config in the path.
    host = urlparse(manifest_url).hostname if manifest_url else None
    xbmc.log(
        f"[script.aiostreamscraper] get_engine: manifest_url_set={bool(manifest_url)} "
        f"host={host} timeout={timeout}s use_emoji_metadata={use_emoji_metadata} "
        f"debug_logging={debug_logging}",
        xbmc.LOGINFO,
    )

    return AIOStreamsEngine(
        manifest_url=manifest_url,
        timeout=timeout,
        use_emoji_metadata=use_emoji_metadata,
        debug_logging=debug_logging,
    )
