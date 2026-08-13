"""
Strategy pattern for turning a raw AIOStreams stream object into the
display fields the CocoScrapers adapter needs (quality + a one-line "info"
summary for Umbrella's source picker).

- FilenameHeuristicParser (default, always used unless opted out of): the
  original behavior - guesses quality from keyword substrings in the
  release filename. Works against any AIOStreams instance regardless of
  its configuration, since it never looks at that instance's own
  name/description template output.

- EmojiDescriptionParser (opt-in, via the "Use Emoji-Based Metadata
  Parsing" setting): AIOStreams renders a `description` (or, on older
  instances, `title`) field per-stream from a user-configurable template
  that tags each piece of info with a fixed emoji marker and separates
  multi-value fields with " | " - e.g. "📺 DV 🎧 Atmos | TrueHD 🔊 7.1".
  Reverse-engineered against one specific AIOStreams instance's actual
  Name/Description templates (kept outside the addon, at
  ./tmp/formatting_templates.txt in this repo - not user-agnostic, since
  AIOStreams lets each instance customize both the emojis used and the
  template shape). This is why it's opt-in rather than the default: a user
  whose instance uses different emojis, or omits/reorders template blocks,
  will get partial or empty results, not a crash (every field is optional
  and simply omitted if its marker isn't found), but also not necessarily
  useful ones - the default FilenameHeuristicParser remains the safe
  choice for anyone not on a matching template.
"""
import re

import xbmc

LOG_PREFIX = '[script.aiostreamscraper]'

# Broad emoji/pictograph/symbol Unicode ranges, plus variation selector and
# ZWJ. Deliberately more generous than just the markers _EMOJI_FIELDS below
# looks for: strip_emojis() is also used as a blanket safety net on every
# string field normalize_stream() returns (raw_title, source_name, ...),
# regardless of which parser strategy is active - Kodi on at least the
# Shield renders emoji as a missing-glyph box rather than the character
# itself, and AIOStreams' Name template (not just Description) can inject
# emoji into fields we display no matter which strategy parses metadata.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002300-\U000023FF"
    "\U00002100-\U0000214F"
    "\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF"
    "\U0000FE0F"
    "\U0000200D"
    "]+"
)


def strip_emojis(text):
    if not text:
        return text
    return re.sub(r'\s{2,}', ' ', _EMOJI_RE.sub('', text)).strip()


class MetadataParser:
    """parse() returns {'quality': str, 'display_info': str}. An empty
    display_info means "nothing extra beyond quality/size" - callers fall
    back to their own quality-and-size-only summary in that case."""

    def __init__(self, debug_logging=False):
        self.debug_logging = debug_logging

    def _debug(self, msg):
        if self.debug_logging:
            xbmc.log(f"{LOG_PREFIX} metadata[{type(self).__name__}]: {msg}", xbmc.LOGINFO)

    def parse(self, stream, raw_title):
        raise NotImplementedError


class FilenameHeuristicParser(MetadataParser):
    def parse(self, stream, raw_title):
        quality = self._detect_quality(raw_title)
        self._debug(f"raw_title={raw_title!r} -> quality={quality!r}")
        return {'quality': quality, 'display_info': ''}

    @staticmethod
    def _detect_quality(title):
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


# (marker codepoint, field name, 'single' or 'list'). Matched against the
# Description template in tmp/formatting_templates.txt. 'list' fields are
# rendered by that template with "::join(' | ')" - split back out on '|'.
# 📦's value can also carry an appended folderSize/bitrate (that template
# line has no separate emoji per sub-field) - kept as one opaque string
# rather than trying to re-split it further.
_EMOJI_FIELDS = [
    ('\U0001F3A5', 'quality', 'single'),        # 🎥
    ('\U0001F39E', 'encode', 'single'),         # 🎞️
    ('\U0001F3F7', 'release_group', 'single'),  # 🏷️
    ('\U0001F4E1', 'network', 'single'),        # 📡
    ('\U0001F4FA', 'visual_tags', 'list'),      # 📺
    ('\U0001F3A7', 'audio_tags', 'list'),       # 🎧
    ('\U0001F50A', 'audio_channels', 'list'),   # 🔊
    ('\U0001F4E6', 'size_info', 'single'),      # 📦
    ('\U000023F1', 'duration', 'single'),       # ⏱️
    ('\U0001F465', 'seeders', 'single'),        # 👥
    ('\U0001F4C5', 'age', 'single'),            # 📅
    ('\U0001F50D', 'indexer', 'single'),        # 🔍
    ('\U0001F30E', 'languages', 'list'),        # 🌎
    ('\U0001F4DD', 'subtitles', 'list'),        # 📝
    ('\U0001F4C1', 'filename_info', 'single'),  # 📁
    ('\U00002139', 'message', 'single'),        # ℹ️
]
_MARKER_RE = re.compile('|'.join(re.escape(m) for m, _, _ in _EMOJI_FIELDS))
_MARKER_TO_FIELD = {m: (name, kind) for m, name, kind in _EMOJI_FIELDS}


class EmojiDescriptionParser(MetadataParser):
    def parse(self, stream, raw_title):
        text = stream.get('description') or stream.get('title') or ''
        self._debug(f"raw description/title text: {text!r}")

        fields = self._extract(text)
        self._debug(f"extracted fields: {fields!r}")

        if self.debug_logging:
            missing = [name for _, name, _ in _EMOJI_FIELDS if name not in fields]
            if missing:
                self._debug(f"markers NOT found for: {', '.join(missing)}")
            if not fields:
                self._debug(
                    "matched ZERO emoji markers - either 'description'/'title' "
                    "is empty for this stream, or this AIOStreams instance's "
                    "template uses different emojis/shape than "
                    "tmp/formatting_templates.txt (see this module's docstring)"
                )

        if fields.get('quality'):
            quality = fields['quality']
        else:
            quality = FilenameHeuristicParser._detect_quality(raw_title)
            self._debug(
                f"no quality marker (\U0001F3A5) found, fell back to filename "
                f"heuristic on raw_title={raw_title!r} -> quality={quality!r}"
            )

        display_info = self._build_display_info(fields)
        self._debug(f"result: quality={quality!r} display_info={display_info!r}")

        return {'quality': quality, 'display_info': display_info}

    def _extract(self, text):
        if not text:
            return {}

        # Variation selectors (the invisible ️ after e.g. 🎞) are rendered
        # inconsistently across template engines - match on the base
        # codepoint only, so drop them before scanning.
        text = text.replace('\U0000FE0F', '')

        matches = [(m.start(), m.group()) for m in _MARKER_RE.finditer(text)]
        fields = {}
        for i, (pos, marker) in enumerate(matches):
            name, kind = _MARKER_TO_FIELD[marker]
            value_start = pos + len(marker)
            value_end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
            # A marker's value stops at the next marker OR a real line
            # break, whichever comes first (covers the last marker on a
            # line that has no marker on the following line).
            value = text[value_start:value_end].split('\n', 1)[0].strip()
            if not value:
                self._debug(f"marker for {name!r} matched at {pos} but value was empty - skipped")
                continue
            if kind == 'list':
                fields[name] = [v.strip() for v in value.split('|') if v.strip()]
            else:
                fields[name] = value
            self._debug(f"marker for {name!r} matched at {pos}: raw value={value!r} -> {fields[name]!r}")
        return fields

    @staticmethod
    def _build_display_info(fields):
        parts = []
        if fields.get('encode'):
            parts.append(fields['encode'])
        if fields.get('release_group'):
            parts.append(fields['release_group'])
        if fields.get('visual_tags'):
            parts.append('+'.join(fields['visual_tags']))
        if fields.get('audio_tags'):
            parts.append('+'.join(fields['audio_tags']))
        if fields.get('audio_channels'):
            parts.append('+'.join(fields['audio_channels']))
        if fields.get('size_info'):
            parts.append(fields['size_info'])
        if fields.get('seeders'):
            parts.append(f"{fields['seeders']} seeders")
        return strip_emojis(' | '.join(parts))
