# AIOStreams Scraper for Kodi

> **Beta software.** This addon is under active development, offered with no guarantees, and may change or break between versions. Use at your own risk.

A Kodi addon that connects a Kodi scraper front end (e.g. [CocoScrapers](https://github.com/CocoScrapers/cocoscrapers)) to a self-hosted [AIOStreams](https://github.com/Viren070/AIOStreams) instance. It queries your AIOStreams manifest URL for a given IMDb ID and returns the results as playable sources, so any addon that already knows how to consume a CocoScrapers-style provider can use AIOStreams as a search backend without a dedicated integration.

## What's in this repo

- **`script.aiostreamscraper`** — the actual addon: talks to your AIOStreams instance, normalizes results (title, quality, size, source), and exposes them to adapters.
  - `lib/aiostreams/adapters/cocoscrapers.py` — a CocoScrapers-compatible `source` provider.
  - `lib/aiostreams/adapters/generic.py` — a plain `fetch_links()` function for other consumers.
  - A settings screen with a manifest URL, a timeout, and a **Run Test Search** button that can play back the first result to confirm everything works end to end.
- **`repository.aiostreamscraper`** — a Kodi repository addon. Installing it gives you the scraper addon plus automatic updates whenever a new version is published here.

## Installation

### Recommended: via the repository (gets future updates automatically)

1. In Kodi, enable installs from unknown sources: **Settings → System → Add-ons → Unknown sources**.
2. **Settings → File manager → Add source**, enter:

   ```
   https://jordihs.github.io/AIOStreamsScrapingModule/
   ```

   and give it any name (e.g. `AIOStreams Repo`).
3. **Add-ons → Install from zip file** → pick that source → `repository.aiostreamscraper` → `repository.aiostreamscraper-0.1.0~beta1.zip`.
4. **Add-ons → Install from repository → AIOStreams Scraper Repository → AIOStreams Scraper**.

From then on, Kodi will offer updates automatically as new versions are published to this repository.

### Manual install (no auto-updates)

Download the addon zip from the [latest release](https://github.com/jordihs/AIOStreamsScrapingModule/releases) and install it directly via **Install from zip file**.

## Configuration

Open the addon's settings (or **Add-ons → My add-ons → AIOStreams Scraper → Configure**) and set:

- **Full AIOStreams Manifest URL** — the `manifest.json` URL of your AIOStreams instance.
- **Search Timeout (seconds)** — request timeout, defaults to 10.
- **Run Test Search** — looks up an IMDb ID against your instance and, on success, offers to play the first result so you can confirm the whole path (manifest → search → stream URL → playback) actually works.

## Building from source

```
python build.py
```

This produces:

- `dist/` — standalone zips for manual "install from zip file" testing (not committed).
- `docs/` — the full Kodi repository (`addons.xml`, checksum, per-addon zips, and browsable index pages), served via GitHub Pages at the URL above.

## Status

This is an early beta (`0.1.0~beta1`). Expect rough edges, and please report issues via [GitHub Issues](https://github.com/jordihs/AIOStreamsScrapingModule/issues).
