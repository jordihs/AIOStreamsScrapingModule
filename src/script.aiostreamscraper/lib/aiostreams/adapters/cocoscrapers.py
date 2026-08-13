"""
CocoScrapers-compatible torrent provider. This file is copied verbatim into an
installed CocoScrapers addon by aiostreams.cocoscrapers_link - see that module
for where and why.

This runs inside CocoScrapers' own Python process, not our addon's. Our own
main.py/service.py add our addon's lib/ folder to sys.path at their own
startup, but that never happens for CocoScrapers' process - so importing
aiostreams here would raise ModuleNotFoundError unless we bootstrap the path
ourselves first. This matters more than it might elsewhere: CocoScrapers'
loader (sources_cocoscrapers/__init__.py) silently swallows ANY exception
while loading a provider module (only logs if CocoScrapers' own debug
setting is on), so a missing import here doesn't fail loudly - it just
looks like "no results" with no attempted network call at all. That's why
this file logs heavily at every stage (module import, class construction,
each interface method) rather than relying on CocoScrapers' own logging.

The classic Exodus/Placenta-lineage scraper interface (confirmed against the
open-source sibling project a4k-openproject/script.module.openscrapers, since
CocoScrapers itself is closed-source) calls movie()/tvshow()/episode() to
build an opaque url-encoded token, then passes that token plus hostDict/
hostprDict into sources(), and later calls resolve() on whichever source the
user picked.

Umbrella (confirmed by reading its actual source, plugin.video.umbrella
6.7.81, resources/lib/modules/sources.py) does NOT follow this convention:
it never calls movie()/tvshow()/episode() at all (grepped, zero matches), and
calls sources() with only 2 positional args - a raw metadata dict it builds
itself (not a url-encoded token) and hostprDict alone, e.g.
`call().sources(data, self.hostprDict)`. sources() below accepts either
shape: a dict (Umbrella's convention) used as-is, or a string (classic
convention) parsed via parse_qsl. Extra positional/keyword args from either
caller are accepted and ignored via *args/**kwargs since we never need
hostDict/hostprDict (no per-hoster filtering here).
"""
import sys
import time
import traceback
from urllib.parse import urlencode, parse_qsl

import xbmc
import xbmcaddon
import xbmcvfs

LOG_PREFIX = '[aiostreamsscraper_jordihs]'
_OWN_ADDON_ID = 'script.aiostreamscraper'
_PROVIDER_NAME = 'aiostreamsscraper_jordihs'

try:
    _own_addon = xbmcaddon.Addon(_OWN_ADDON_ID)
    _addon_path = xbmcvfs.translatePath(_own_addon.getAddonInfo('path'))
    _lib_path = xbmcvfs.translatePath(f"{_addon_path}lib")
    if _lib_path not in sys.path:
        sys.path.append(_lib_path)

    from aiostreams.config import get_engine  # noqa: E402 (must follow the sys.path bootstrap above)

    xbmc.log(f"{LOG_PREFIX} module imported OK, lib_path={_lib_path}", xbmc.LOGINFO)
except Exception as exc:
    # CocoScrapers' loader swallows this exception silently (only logs if ITS
    # own debug setting is on) - log it ourselves before it propagates, since
    # this is otherwise a completely invisible failure mode.
    xbmc.log(f"{LOG_PREFIX} MODULE IMPORT FAILED: {exc!r}\n{traceback.format_exc()}", xbmc.LOGERROR)
    raise


class source:
    # These must be CLASS attributes, not just set in __init__: Umbrella reads
    # them off the class object itself, before ever instantiating a provider
    # (e.g. sources.py: "sourceDict = [... for i in sourceDict if i[1].hasMovies]",
    # where i[1] is the class, not an instance). Missing hasMovies specifically
    # raised an uncaught AttributeError inside a bare list comprehension with
    # no per-item error handling, which aborted Umbrella's entire provider
    # list for that content type - not just skipped our own entry, but broke
    # every other enabled provider too. Confirmed against every bundled
    # CocoScrapers torrent provider, which all declare this same set.
    priority = 1
    pack_capable = False
    hasMovies = True
    hasEpisodes = True

    def __init__(self):
        xbmc.log(f"{LOG_PREFIX} source() constructed", xbmc.LOGINFO)
        self.language = ['en']

    def movie(self, imdb, title, localtitle, aliases, year):
        try:
            token = urlencode({'imdb': imdb})
            xbmc.log(f"{LOG_PREFIX} movie() imdb={imdb!r} title={title!r} -> token={token!r}", xbmc.LOGINFO)
            return token
        except Exception as exc:
            xbmc.log(f"{LOG_PREFIX} movie() FAILED: {exc!r}\n{traceback.format_exc()}", xbmc.LOGERROR)
            return

    def tvshow(self, imdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            token = urlencode({'imdb': imdb})
            xbmc.log(f"{LOG_PREFIX} tvshow() imdb={imdb!r} tvshowtitle={tvshowtitle!r} -> token={token!r}", xbmc.LOGINFO)
            return token
        except Exception as exc:
            xbmc.log(f"{LOG_PREFIX} tvshow() FAILED: {exc!r}\n{traceback.format_exc()}", xbmc.LOGERROR)
            return

    def episode(self, url, imdb, tvdb, title, premiered, season, episode):
        try:
            xbmc.log(f"{LOG_PREFIX} episode() url={url!r} season={season!r} episode={episode!r}", xbmc.LOGINFO)
            if url is None:
                return
            data = dict(parse_qsl(url))
            data['season'] = season
            data['episode'] = episode
            token = urlencode(data)
            xbmc.log(f"{LOG_PREFIX} episode() -> token={token!r}", xbmc.LOGINFO)
            return token
        except Exception as exc:
            xbmc.log(f"{LOG_PREFIX} episode() FAILED: {exc!r}\n{traceback.format_exc()}", xbmc.LOGERROR)
            return

    def sources(self, data, *args, **kwargs):
        sources = []
        start = time.monotonic()
        try:
            xbmc.log(f"{LOG_PREFIX} sources() CALLED with data={data!r} args={args!r}", xbmc.LOGINFO)

            if data is None:
                xbmc.log(f"{LOG_PREFIX} sources() aborting: data is None", xbmc.LOGWARNING)
                return sources

            # Umbrella passes a raw dict; classic Exodus-style callers pass a
            # url-encoded token string built by movie()/episode() above.
            parsed = dict(parse_qsl(data)) if isinstance(data, str) else data
            imdb = parsed.get('imdb')
            if not imdb:
                xbmc.log(f"{LOG_PREFIX} sources() aborting: no imdb id in data (parsed={parsed!r})", xbmc.LOGWARNING)
                return sources

            season = parsed.get('season')
            episode = parsed.get('episode')
            media_type = "series" if season and episode else "movie"

            xbmc.log(f"{LOG_PREFIX} sources() calling get_engine()...", xbmc.LOGINFO)
            engine = get_engine()
            if not engine.base_url:
                xbmc.log(f"{LOG_PREFIX} sources() aborting: no manifest_url configured", xbmc.LOGWARNING)
                return sources

            xbmc.log(
                f"{LOG_PREFIX} sources() calling engine.get_streams(imdb={imdb!r}, "
                f"media_type={media_type!r}, season={season!r}, episode={episode!r})...",
                xbmc.LOGINFO,
            )
            streams = engine.get_streams(
                imdb_id=imdb,
                media_type=media_type,
                season=season,
                episode=episode
            )
            elapsed = time.monotonic() - start
            xbmc.log(
                f"{LOG_PREFIX} sources() get_streams returned {len(streams)} stream(s) in {elapsed:.2f}s",
                xbmc.LOGINFO,
            )

            for item in streams:
                entry = {
                    'source': item['source_name'],
                    'provider': _PROVIDER_NAME,
                    'quality': item['quality'],
                    'language': 'en',
                    'url': item['url'],
                    'name': item['raw_title'],
                    'info': f"{item['quality']} | {item['size_formatted']}",
                    'direct': item['is_direct'],
                    'debridonly': not item['is_direct'],
                    # Umbrella/CocoScrapers expect a raw numeric GB value here
                    # (they do float(i['size']) internally, e.g. providerscache.py
                    # and sourcesFilter()'s size-range filter) - NOT the
                    # human-readable "X.XX GB" string, which belongs in 'info'
                    # only. Confirmed against real CocoScrapers providers, whose
                    # source_utils._size() returns (float_gb, "X.XX GB" string)
                    # as two separate values for exactly this reason.
                    'size': item['size_gb']
                }
                if item.get('info_hash'):
                    entry['hash'] = item['info_hash']
                if item['is_direct']:
                    # Umbrella's sourcesFilter() drops every 'direct': True result
                    # unless 'provider' is one of its own 9 hardcoded built-in
                    # cloud-scraper names (rd_cloud, pm_cloud, ...) - a third-party
                    # CocoScrapers provider can never match those, so an
                    # already-resolved URL (e.g. AIOStreams handing back a
                    # usenet-cached direct link) would otherwise be silently
                    # discarded before Umbrella ever attempts to play it.
                    # 'local' is Umbrella's one documented escape hatch from that
                    # gate ("for library and videoscraper, skips cache check" -
                    # confirmed via source read to have no other special meaning
                    # anywhere else in the addon). Only used for already-direct
                    # entries: magnet/hash-based entries must still go through
                    # Umbrella's normal debrid cache-check flow, which is what
                    # attaches the 'debrid' key sourcesResolve() requires.
                    entry['local'] = True
                sources.append(entry)

            elapsed = time.monotonic() - start
            xbmc.log(f"{LOG_PREFIX} sources() RETURNING {len(sources)} entries after {elapsed:.2f}s total", xbmc.LOGINFO)
            return sources
        except Exception as exc:
            elapsed = time.monotonic() - start
            xbmc.log(
                f"{LOG_PREFIX} sources() FAILED after {elapsed:.2f}s: {exc!r}\n{traceback.format_exc()}",
                xbmc.LOGERROR,
            )
            return sources

    def resolve(self, url):
        xbmc.log(f"{LOG_PREFIX} resolve() url={url!r}", xbmc.LOGINFO)
        return url
