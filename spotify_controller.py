"""
spotify_controller.py  (Media-Key Edition)
------------------------------------------
DROP-IN replacement for the Spotify-API version.

All public method names and signatures are IDENTICAL to the original,
so main.py needs only two small changes (documented at the bottom of
this file).

How it works
------------
Instead of calling the Spotify Web API (which now requires Premium for
playback endpoints), we send Windows virtual media-key events via the
`keyboard` library.  The OS routes those key-presses to whatever media
app has focus: Spotify Free, YouTube in Chrome, VLC, Windows Media
Player, etc.

Install
-------
    pip install keyboard

Run your app as Administrator if media keys are ignored
(keyboard needs elevated privileges for low-level hooks on some Windows
setups).

Public surface kept from original SpotifyController
-----------------------------------------------------
  .is_connected            -> bool  (True when keyboard lib is available)
  .is_premium              -> bool  (always False; no Spotify account needed)
  .like_current_song()     -> str   (now means Play/Pause toggle)
  .next_track()            -> str   (sends Next Track media key)
  .get_now_playing_label() -> str   (returns empty; no API available)
"""

import time
import logging

logger = logging.getLogger(__name__)

# ── keyboard import ────────────────────────────────────────────────────
try:
    import keyboard as _kb
    _KB_OK = True
except ImportError:
    _KB_OK = False
    logger.warning("keyboard library not found. Run:  pip install keyboard")

# ── Internal cooldown helper ───────────────────────────────────────────
# Extra guard so a single held gesture cannot fire the key twice.
# main.py already has its own COOLDOWN; this is just a safety net.
_INTERNAL_COOLDOWN = 1.0          # seconds
_last_sent: dict = {}

def _send(key: str, label: str) -> str:
    """Send one media key and return a UI-ready display string."""
    now = time.time()
    if now - _last_sent.get(key, 0.0) < _INTERNAL_COOLDOWN:
        return f"{label} (too soon)"
    _last_sent[key] = now

    if not _KB_OK:
        msg = "keyboard lib missing -- pip install keyboard"
        logger.error(msg)
        return msg

    try:
        _kb.send(key)
        logger.info("Media key sent: %s", label)
        return label
    except Exception as exc:
        msg = f"Key send failed: {exc}"
        logger.error(msg)
        return msg


# ══════════════════════════════════════════════════════════════════════
class SpotifyController:
    """
    Mimics the original SpotifyController interface exactly.
    No Spotify credentials, no network calls, no Premium required.
    Works with Spotify Free, YouTube, VLC, or any Windows media app.
    """

    # Original signature: __init__(self, client_id, client_secret, redirect_uri)
    # We accept *args/**kwargs so the existing call in main.py keeps working
    # without any edits.  The arguments are simply ignored.
    def __init__(self, *args, **kwargs):
        self._connected  = _KB_OK
        self._is_premium = False   # always False; main.py uses this for UI text

        if _KB_OK:
            logger.info(
                "SpotifyController ready (media-key mode). "
                "Works with Spotify Free, YouTube, VLC, and any media app."
            )
        else:
            logger.error(
                "SpotifyController: keyboard library missing. "
                "Run:  pip install keyboard  -- then restart."
            )

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        """True when the keyboard library loaded successfully."""
        return self._connected

    @property
    def is_premium(self) -> bool:
        """
        Always False.
        main.py uses this property to choose UI status messages and to
        decide whether to call next_track() or seek-to-end.
        Returning False keeps behaviour consistent and uses the simpler
        code path in main.py.
        """
        return self._is_premium

    # ── Public actions ─────────────────────────────────────────────────

    def like_current_song(self) -> str:
        """
        Original: saved current track to Spotify library (Premium API).
        Now:       toggles Play / Pause on the active media player.

        Triggered by: heart gesture or thumbs-up held for HOLD_REQUIRED s.
        """
        return _send("play/pause media", "Play/Pause toggled")

    def next_track(self) -> str:
        """
        Original: sp.next_track() for Premium, seek-to-end for Free.
        Now:       sends the Next Track media key to the active media app.

        Triggered by: swipe-right gesture.
        """
        return _send("next track", "Next track")

    def previous_track(self) -> str:
        """
        Bonus action (not in original, but available if you add a gesture).
        Sends the Previous Track media key.
        """
        return _send("previous track", "Previous track")

    def volume_up(self) -> str:
        """Bonus: raises system volume by one step."""
        return _send("volume up", "Volume up")

    def volume_down(self) -> str:
        """Bonus: lowers system volume by one step."""
        return _send("volume down", "Volume down")

    def get_now_playing_label(self) -> str:
        """
        Original: polled Spotify API every 8 s for track name + artist.
        Now:       returns empty string so the top bar stays blank.

        main.py calls this on a timer; an empty return hides the bar
        cleanly without any crash or exception.
        """
        return ""