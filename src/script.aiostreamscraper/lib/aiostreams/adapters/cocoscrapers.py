import xbmcaddon
from aiostreams.core import AIOStreamsEngine

ADDON = xbmcaddon.Addon('script.aiostreamscraper')

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']

    def sources(self, data, hostpr):
        sources = []
        manifest_url = ADDON.getSetting('manifest_url')
        timeout_val = ADDON.getSetting('timeout')
        timeout = int(timeout_val) if timeout_val else 10
        
        if not manifest_url:
            return sources

        engine = AIOStreamsEngine(manifest_url=manifest_url, timeout=timeout)
        media_type = "series" if "season" in data else "movie"

        streams = engine.get_streams(
            imdb_id=data.get('imdb'),
            media_type=media_type,
            season=data.get('season'),
            episode=data.get('episode')
        )

        for item in streams:
            sources.append({
                'source': item['source_name'],
                'quality': item['quality'],
                'language': 'en',
                'url': item['url'],
                'info': item['raw_title'],
                'direct': True,
                'debridonly': False,
                'size': item['size_formatted']
            })

        return sources
