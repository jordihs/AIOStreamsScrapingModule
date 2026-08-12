from aiostreams.config import get_engine


def fetch_links(imdb_id, media_type="movie", season=None, episode=None):
    engine = get_engine()
    return engine.get_streams(imdb_id=imdb_id, media_type=media_type, season=season, episode=episode)
