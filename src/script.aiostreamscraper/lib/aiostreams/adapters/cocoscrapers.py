"""
CocoScrapers-compatible torrent provider. This file is copied verbatim into an
installed CocoScrapers addon by aiostreams.cocoscrapers_link - see that module
for where and why.

CocoScrapers calls movie()/tvshow()/episode() to build an opaque token, then
passes that token into sources(), and later calls resolve() on whichever
source the user picked. This is the classic Exodus/Placenta-lineage scraper
interface (confirmed against the open-source sibling project
a4k-openproject/script.module.openscrapers, since CocoScrapers itself is
closed-source).
"""
from urllib.parse import urlencode, parse_qsl

from aiostreams.config import get_engine


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            return urlencode({'imdb': imdb})
        except Exception:
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            return urlencode({'imdb': imdb})
        except Exception:
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            if url is None:
                return
            data = dict(parse_qsl(url))
            data['season'] = season
            data['episode'] = episode
            return urlencode(data)
        except Exception:
            return

    def sources(self, url, hostDict, hostprDict):
        sources = []
        try:
            if url is None:
                return sources

            data = dict(parse_qsl(url))
            imdb = data.get('imdb')
            if not imdb:
                return sources

            season = data.get('season')
            episode = data.get('episode')
            media_type = "series" if season and episode else "movie"

            engine = get_engine()
            if not engine.base_url:
                return sources

            streams = engine.get_streams(
                imdb_id=imdb,
                media_type=media_type,
                season=season,
                episode=episode
            )

            for item in streams:
                sources.append({
                    'source': item['source_name'],
                    'quality': item['quality'],
                    'language': 'en',
                    'url': item['url'],
                    'info': item['raw_title'],
                    'direct': item['is_direct'],
                    'debridonly': not item['is_direct'],
                    'size': item['size_formatted']
                })

            return sources
        except Exception:
            return sources

    def resolve(self, url):
        return url
