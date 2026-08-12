import json
import sys
import urllib.request
import urllib.error
import xbmcvfs
import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon('script.aiostreamscraper')

# Add local lib directory dynamically to avoid schema conflicts in addon.xml
addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
lib_path = xbmcvfs.translatePath(f"{addon_path}lib")
if lib_path not in sys.path:
    sys.path.append(lib_path)

from aiostreams.core import AIOStreamsEngine

def run_test_search():
    manifest_url = addon.getSetting('manifest_url').strip()
    timeout_val = addon.getSetting('timeout')
    timeout = int(timeout_val) if timeout_val else 10

    dialog = xbmcgui.Dialog()

    if not manifest_url:
        dialog.ok("AIOStreams Test", "Please configure your Manifest URL first.")
        return

    user_input = dialog.input(
        "Enter IMDb ID (e.g. tt0087363) or movie title:",
        defaultt="tt0087363"
    )

    if not user_input:
        return

    query = user_input.strip()
    
    if not query.startswith("tt"):
        if "gremlin" in query.lower():
            imdb_id = "tt0087363"
        else:
            imdb_id = query
    else:
        imdb_id = query

    base_url = manifest_url.replace('/manifest.json', '')
    endpoint = f"{base_url}/stream/movie/{imdb_id}.json"

    try:
        req = urllib.request.Request(endpoint, headers={'User-Agent': 'Kodi/AIOStreamsScraper'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode('utf-8')
            data = json.loads(body)
            streams = data.get('streams', [])
            
            if streams:
                engine = AIOStreamsEngine(manifest_url=manifest_url, timeout=timeout)
                first = engine._normalize_stream(streams[0])
                
                msg = (
                    f"Status: Success (HTTP 200)\n"
                    f"Total Streams Found: {len(streams)}\n\n"
                    f"--- First Result Details ---\n"
                    f"Title: {first.get('raw_title', 'N/A')}\n"
                    f"Quality: {first.get('quality', 'N/A')}\n"
                    f"Size: {first.get('size_formatted', 'N/A')}\n"
                    f"Source: {first.get('source_name', 'N/A')}"
                )
                dialog.ok("Test Search Success", msg)
            else:
                dialog.ok("Test Search Success", "HTTP 200 OK received, but 0 streams were returned for this query.")

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')[:250] if e.fp else "No response body"
        msg = (
            f"HTTP Error Code: {e.code}\n\n"
            f"Response Message:\n{error_body}"
        )
        dialog.ok("Test Search Error", msg)

    except Exception as e:
        dialog.ok("Connection Error", f"Failed to connect to server:\n{str(e)}")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        run_test_search()
    else:
        addon.openSettings()
