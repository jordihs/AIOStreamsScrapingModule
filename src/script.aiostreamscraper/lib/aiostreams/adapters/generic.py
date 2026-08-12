import xbmcaddon
from aiostreams.core import AIOStreamsEngine

ADDON = xbmcaddon.Addon('script.aiostreamscraper')

def fetch_links(imdb_id, media_type="movie", season=None, episode=None):
    manifest_url = ADDON.getSetting('manifest_url')
    timeout_val = ADDON.getSetting('timeout')
    timeout = int(timeout_val) if timeout_val else 10
    
    engine = AIOStreamsEngine(manifest_url=manifest_url, timeout=timeout)
    return engine.get_streams(imdb_id=imdb_id, media_type=media_type, season=season, episode=episode)
