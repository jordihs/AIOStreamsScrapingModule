from aiostreams.config import get_engine


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['en']

    def sources(self, data, hostpr):
        sources = []
        engine = get_engine()

        if not engine.base_url:
            return sources

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
