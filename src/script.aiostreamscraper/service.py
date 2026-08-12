import sys

import xbmc
import xbmcaddon
import xbmcvfs

addon = xbmcaddon.Addon('script.aiostreamscraper')

addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
lib_path = xbmcvfs.translatePath(f"{addon_path}lib")
if lib_path not in sys.path:
    sys.path.append(lib_path)

from aiostreams.cocoscrapers_link import link_to_cocoscrapers

if __name__ == '__main__':
    if addon.getSettingBool('link_cocoscrapers_service'):
        result = link_to_cocoscrapers()
        if result['cocoscrapers_installed']:
            xbmc.log(
                f"[script.aiostreamscraper] Startup CocoScrapers link: "
                f"linked={result['linked']} enabled={result['enabled']}",
                xbmc.LOGINFO,
            )
