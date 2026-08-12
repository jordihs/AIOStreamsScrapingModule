import sys
import urllib.error
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon('script.aiostreamscraper')

# Add local lib directory dynamically to avoid schema conflicts in addon.xml
addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
lib_path = xbmcvfs.translatePath(f"{addon_path}lib")
if lib_path not in sys.path:
    sys.path.append(lib_path)

from aiostreams.config import get_engine


def run_test_search():
    engine = get_engine()
    dialog = xbmcgui.Dialog()

    if not engine.base_url:
        dialog.ok("AIOStreams Test", "Please configure your Manifest URL first.")
        return

    user_input = dialog.input(
        "Enter IMDb ID (e.g. tt0087363):",
        defaultt="tt0087363"
    )

    if not user_input:
        return

    imdb_id = user_input.strip()

    try:
        data = engine.fetch_raw(imdb_id, media_type="movie")
        streams = data.get('streams', [])

        if streams:
            first = engine.normalize_stream(streams[0])

            msg = (
                f"Status: Success (HTTP 200)\n"
                f"Total Streams Found: {len(streams)}\n\n"
                f"--- First Result Details ---\n"
                f"Title: {first.get('raw_title', 'N/A')}\n"
                f"Quality: {first.get('quality', 'N/A')}\n"
                f"Size: {first.get('size_formatted', 'N/A')}\n"
                f"Source: {first.get('source_name', 'N/A')}"
            )

            if dialog.yesno("Test Search Success", msg, yeslabel="Play", nolabel="Close"):
                play_stream(first, dialog)
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


def play_stream(stream, dialog):
    url = stream.get('url', '')

    if not url.startswith(('http://', 'https://')):
        dialog.ok(
            "Playback Unavailable",
            "This result is a torrent hash with no direct URL, so it can't be "
            "played without a debrid service or torrent resolver."
        )
        return

    list_item = xbmcgui.ListItem(label=stream.get('raw_title', 'AIOStreams Test'))
    xbmc.Player().play(url, list_item)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        run_test_search()
    else:
        addon.openSettings()
