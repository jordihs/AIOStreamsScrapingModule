import json
import re
from urllib.parse import unquote, urlparse
import urllib.request
import urllib.error

class AIOStreamsEngine:
    def __init__(self, manifest_url, timeout=10):
        self.manifest_url = manifest_url.strip() if manifest_url else ""
        self.timeout = timeout
        self.base_url = self.manifest_url.replace('/manifest.json', '') if self.manifest_url else ""

    def get_streams(self, imdb_id, media_type="movie", season=None, episode=None):
        if not self.base_url or not imdb_id:
            return []

        query_id = f"{imdb_id}:{season}:{episode}" if media_type == "series" and season and episode else imdb_id
        endpoint = f"{self.base_url}/stream/{media_type}/{query_id}.json"

        try:
            req = urllib.request.Request(endpoint, headers={'User-Agent': 'Kodi/AIOStreamsScraper'})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    body = response.read().decode('utf-8')
                    data = json.loads(body)
                    raw_streams = data.get('streams', [])
                    
                    parsed_streams = []
                    for stream in raw_streams:
                        parsed = self._normalize_stream(stream)
                        if parsed:
                            parsed_streams.append(parsed)
                            
                    return parsed_streams
        except Exception:
            return []
        return []

    def _normalize_stream(self, stream):
        behavior = stream.get('behaviorHints', {})
        size_bytes = behavior.get('videoSize') or behavior.get('folderSize') or 0
        size_gb = round(size_bytes / (1024 ** 3), 2) if size_bytes else 0

        raw_title = behavior.get('filename')
        if not raw_title and stream.get('url'):
            parsed_url = urlparse(stream['url'])
            raw_title = unquote(parsed_url.path.split('/')[-1])
            
        if not raw_title:
            raw_title = stream.get('name', 'AIOStreams Release')

        url = stream.get('url') or stream.get('infoHash')
        if not url:
            return None

        return {
            'raw_title': raw_title,
            'quality': self._detect_quality(raw_title),
            'size_bytes': size_bytes,
            'size_formatted': f"{size_gb} GB" if size_gb else "N/A",
            'url': url,
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
