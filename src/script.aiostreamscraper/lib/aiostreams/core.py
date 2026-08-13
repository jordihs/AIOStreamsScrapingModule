import json
import time
import traceback
from urllib.parse import unquote, urlparse
import urllib.request
import urllib.error

import xbmc

MANIFEST_SUFFIX = '/manifest.json'
LOG_PREFIX = '[script.aiostreamscraper]'


class AIOStreamsEngine:
    def __init__(self, manifest_url, timeout=10):
        self.manifest_url = manifest_url.strip() if manifest_url else ""
        self.timeout = timeout
        self.base_url = (
            self.manifest_url[:-len(MANIFEST_SUFFIX)]
            if self.manifest_url.endswith(MANIFEST_SUFFIX)
            else self.manifest_url
        )

    def get_streams(self, imdb_id, media_type="movie", season=None, episode=None):
        xbmc.log(
            f"{LOG_PREFIX} get_streams start imdb_id={imdb_id!r} media_type={media_type!r} "
            f"season={season!r} episode={episode!r} base_url_set={bool(self.base_url)}",
            xbmc.LOGINFO,
        )

        if not self.base_url or not imdb_id:
            xbmc.log(f"{LOG_PREFIX} get_streams aborting: no base_url or imdb_id", xbmc.LOGWARNING)
            return []

        start = time.monotonic()
        try:
            data = self.fetch_raw(imdb_id, media_type=media_type, season=season, episode=episode)
        except Exception as exc:
            elapsed = time.monotonic() - start
            xbmc.log(
                f"{LOG_PREFIX} get_streams: fetch_raw failed after {elapsed:.2f}s: {exc!r}\n{traceback.format_exc()}",
                xbmc.LOGERROR,
            )
            return []

        raw_streams = data.get('streams', [])
        parsed_streams = []
        for stream in raw_streams:
            parsed = self.normalize_stream(stream)
            if parsed:
                parsed_streams.append(parsed)

        elapsed = time.monotonic() - start
        xbmc.log(
            f"{LOG_PREFIX} get_streams done in {elapsed:.2f}s: "
            f"{len(raw_streams)} raw -> {len(parsed_streams)} parsed",
            xbmc.LOGINFO,
        )

        return parsed_streams

    def fetch_raw(self, imdb_id, media_type="movie", season=None, episode=None):
        """Fetch and JSON-decode the raw AIOStreams response. Raises on network/HTTP errors."""
        endpoint = self._build_endpoint(imdb_id, media_type, season, episode)
        host = urlparse(endpoint).hostname  # never log the full endpoint - AIOStreams manifest
        # URLs commonly embed API keys/config in the path.
        xbmc.log(f"{LOG_PREFIX} fetch_raw: GET host={host} timeout={self.timeout}s", xbmc.LOGINFO)

        start = time.monotonic()
        req = urllib.request.Request(endpoint, headers={'User-Agent': 'Kodi/AIOStreamsScraper'})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            body = response.read().decode('utf-8')
            elapsed = time.monotonic() - start
            xbmc.log(
                f"{LOG_PREFIX} fetch_raw: response in {elapsed:.2f}s, status={response.status}, "
                f"{len(body)} bytes",
                xbmc.LOGINFO,
            )
            return json.loads(body)

    def _build_endpoint(self, imdb_id, media_type, season, episode):
        query_id = f"{imdb_id}:{season}:{episode}" if media_type == "series" and season and episode else imdb_id
        return f"{self.base_url}/stream/{media_type}/{query_id}.json"

    def normalize_stream(self, stream):
        behavior = stream.get('behaviorHints', {})
        size_bytes = behavior.get('videoSize') or behavior.get('folderSize') or 0
        size_gb = round(size_bytes / (1024 ** 3), 2) if size_bytes else 0

        raw_title = behavior.get('filename')
        if not raw_title and stream.get('url'):
            parsed_url = urlparse(stream['url'])
            raw_title = unquote(parsed_url.path.split('/')[-1])

        if not raw_title:
            raw_title = stream.get('name', 'AIOStreams Release')

        is_direct = bool(stream.get('url'))
        info_hash = stream.get('infoHash')
        url = stream.get('url')
        if not url and info_hash:
            url = f"magnet:?xt=urn:btih:{info_hash}"

        if not url:
            return None

        return {
            'raw_title': raw_title,
            'quality': self._detect_quality(raw_title),
            'size_bytes': size_bytes,
            'size_gb': size_gb,
            'size_formatted': f"{size_gb} GB" if size_gb else "N/A",
            'url': url,
            'info_hash': info_hash,
            'is_direct': is_direct,
            'source_name': stream.get('name', 'AIOStreams')
        }

    def _detect_quality(self, title):
        title_upper = title.upper()
        if any(q in title_upper for q in ['2160P', '4K', 'UHD']):
            return '4K'
        if '1080P' in title_upper:
            return '1080p'
        if '720P' in title_upper:
            return '720p'
        if any(q in title_upper for q in ['DVD', 'DVDRIP', 'XVID', 'SD', 'CAM']):
            return 'SD'
        return '1080p'
