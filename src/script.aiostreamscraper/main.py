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
from aiostreams.cocoscrapers_link import link_to_cocoscrapers, disable_other_cocoscrapers_providers
from aiostreams.manifest_store import get_manifest_url, set_manifest_url


def run_set_manifest_url():
    dialog = xbmcgui.Dialog()
    current = get_manifest_url()

    user_input = dialog.input("Enter AIOStreams Manifest URL:", defaultt=current)
    if not user_input:
        # xbmcgui.Dialog().input() returns '' both on Cancel and on OK with
        # an empty field - either way, leave the stored value untouched
        # rather than risk silently wiping out a working URL.
        return

    set_manifest_url(user_input)
    dialog.ok("Manifest URL", "Manifest URL saved.")


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
            "This result is a magnet link with no resolved direct URL, so it can't "
            "be played here without a debrid service or torrent resolver."
        )
        return

    list_item = xbmcgui.ListItem(label=stream.get('raw_title', 'AIOStreams Test'))
    xbmc.Player().play(url, list_item)


def run_link_cocoscrapers():
    dialog = xbmcgui.Dialog()
    result = link_to_cocoscrapers()

    if not result['cocoscrapers_installed']:
        dialog.ok("CocoScrapers Link", "CocoScrapers is not installed. Install it first, then try again.")
        return

    if result['linked'] and result['enabled']:
        msg = "Linked and enabled in CocoScrapers successfully."
    elif result['linked']:
        msg = "Linked, but could not enable it in CocoScrapers' settings."
    else:
        msg = "Could not link: expected scraper folder not found."
    dialog.ok("CocoScrapers Link", msg)


def run_cocoscrapers_only():
    dialog = xbmcgui.Dialog()

    confirmed = dialog.yesno(
        "Make AIOStreams the Only CocoScrapers Source",
        "This will disable every other CocoScrapers torrent provider by "
        "overwriting your current enable/disable choices in CocoScrapers' "
        "own settings.\n\n"
        "This cannot be undone - there is no automatic way to restore your "
        "previous provider selection afterwards.\n\n"
        "Continue?",
        yeslabel="Disable Others",
        nolabel="Cancel"
    )

    if not confirmed:
        return

    link_result = link_to_cocoscrapers()
    if not link_result['cocoscrapers_installed']:
        dialog.ok("CocoScrapers", "CocoScrapers is not installed.")
        return

    disable_result = disable_other_cocoscrapers_providers()
    dialog.ok(
        "CocoScrapers",
        f"Disabled {len(disable_result['disabled_providers'])} other provider(s). "
        f"AIOStreams is now the only enabled source."
    )


def run_main_menu():
    # Redundant fallback for running the addon directly (e.g. from the addon
    # browser) - every option here is also reachable from the settings
    # dialog itself via type="action" settings. None of those close the
    # settings dialog (deliberately, per user request) - only `timeout` is a
    # native Kodi-persisted field left exposed there, and Kodi doesn't flush
    # a field's edit to disk until you leave the dialog, so editing timeout
    # and immediately running an action from the same still-open dialog can
    # read the previous value once. Not worth engineering around: it's a
    # one-shot staleness on a rarely-changed numeric field, not the
    # data-loss-causing race the old manifest_url text field had (see
    # aiostreams.manifest_store).
    options = [
        "Open Settings",
        "Run Test Search",
        "Link to CocoScrapers Now",
        "Make AIOStreams the Only CocoScrapers Source",
        "Set Manifest URL",
    ]
    choice = xbmcgui.Dialog().select("AIOStreams Scraper", options)

    if choice == 0:
        addon.openSettings()
    elif choice == 1:
        run_test_search()
    elif choice == 2:
        run_link_cocoscrapers()
    elif choice == 3:
        run_cocoscrapers_only()
    elif choice == 4:
        run_set_manifest_url()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        run_test_search()
    elif len(sys.argv) > 1 and sys.argv[1] == 'link_cocoscrapers':
        run_link_cocoscrapers()
    elif len(sys.argv) > 1 and sys.argv[1] == 'cocoscrapers_only':
        run_cocoscrapers_only()
    elif len(sys.argv) > 1 and sys.argv[1] == 'set_manifest_url':
        run_set_manifest_url()
    else:
        run_main_menu()
