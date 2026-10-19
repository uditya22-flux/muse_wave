import subprocess
import logging
import time
import json
import threading
import collections
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path

logger = logging.getLogger(__name__)

PLAYER      = "spotify,%any"
COOLDOWN    = 0.5
BRIDGE_PORT = 19745
_last_sent  = {}

# Spicetify bridge state
_spicetify_events    = collections.deque(maxlen=30)
_spicetify_lock      = threading.Lock()
_spicetify_last_seen = 0.0
_spicetify_track     = {"title": "", "artist": "", "liked": False}


def _push_spicetify_event(evt_type: str, message: str = ""):
    with _spicetify_lock:
        _spicetify_events.append({"type": evt_type, "message": message, "ts": time.time()})


class _SpicetifyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # keep logs quiet

    def _send_cors(self, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_OPTIONS(self):
        self._send_cors(200)

    def do_GET(self):
        global _spicetify_last_seen
        parsed = urlparse(self.path)
        if parsed.path == "/poll":
            _spicetify_last_seen = time.time()
            qs = parse_qs(parsed.query)
            title  = (qs.get("title") or [""])[0]
            artist = (qs.get("artist") or [""])[0]
            liked  = (qs.get("liked") or ["0"])[0] == "1"
            if title:
                _spicetify_track["title"]  = title
                _spicetify_track["artist"] = artist
                _spicetify_track["liked"]  = liked

            with _spicetify_lock:
                # Only deliver recent events (within last 5 seconds)
                now = time.time()
                evts = [e for e in _spicetify_events if now - e.get("ts", 0) < 5.0]
                _spicetify_events.clear()

            self._send_cors(200)
            self.wfile.write(json.dumps({"ok": True, "events": evts}).encode("utf-8"))
        else:
            self._send_cors(200)
            self.wfile.write(json.dumps({"ok": True, "service": "musewave-spicetify-bridge"}).encode("utf-8"))


def _start_spicetify_bridge():
    def _serve():
        try:
            HTTPServer.allow_reuse_address = True
            srv = HTTPServer(("127.0.0.1", BRIDGE_PORT), _SpicetifyHandler)
            logger.info("Spicetify bridge listening on http://127.0.0.1:%d", BRIDGE_PORT)
            srv.serve_forever()
        except Exception as e:
            logger.debug("Spicetify bridge port %d already in use or unavailable: %s", BRIDGE_PORT, e)

    t = threading.Thread(target=_serve, daemon=True)
    t.start()


def _run(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if result.returncode != 0:
            err = (result.stderr or "").strip()
            if err:
                logger.warning("Command %s returned %d: %s", cmd, result.returncode, err)
            return None
        return result.stdout.strip()
    except Exception as e:
        logger.error("Command failed: %s - %s", cmd, e)
        return None

def _get_target_player() -> str:
    """
    Prioritize:
      1. 'spotify' if it is currently Playing
      2. Any other MPRIS player (e.g. YouTube in browser) that is currently Playing
      3. 'spotify' if it is running (Paused)
      4. Any Paused MPRIS player
    """
    players_out = _run(["playerctl", "-l"])
    if not players_out:
        return PLAYER
    players = [p.strip() for p in players_out.splitlines() if p.strip()]
    statuses = {p: _run(["playerctl", f"--player={p}", "status"]) for p in players}

    for p in players:
        if (p == "spotify" or p.startswith("spotify.")) and statuses.get(p) == "Playing":
            return p
    for p in players:
        if statuses.get(p) == "Playing":
            return p
    for p in players:
        if p == "spotify" or p.startswith("spotify."):
            return p
    for p in players:
        if statuses.get(p) == "Paused":
            return p
    return players[0] if players else PLAYER

def _playerctl(*args):
    target = _get_target_player()
    return _run(["playerctl", f"--player={target}"] + list(args))

def _change_volume(direction: str) -> bool:
    """
    direction: 'up' or 'down'
    Uses wpctl (PipeWire), amixer (ALSA), playerctl, and Spicetify bridge so volume always changes on Linux.
    """
    pctl_arg   = "0.1+" if direction == "up" else "0.1-"
    wpctl_arg  = "10%+" if direction == "up" else "10%-"
    amixer_arg = "10%+" if direction == "up" else "10%-"

    ok = False
    # 1. PipeWire / WirePlumber (Ubuntu 24.04 default)
    if _run(["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", wpctl_arg]) is not None:
        ok = True
    # 2. ALSA fallback
    elif _run(["amixer", "-q", "sset", "Master", amixer_arg]) is not None:
        ok = True
    # 3. Also adjust playerctl player volume if supported
    if _playerctl("volume", pctl_arg) is not None:
        ok = True
    # 4. Notify Spicetify extension
    _push_spicetify_event("vol_up" if direction == "up" else "vol_down")
    return ok

def _send(action_fn, label):
    now = time.time()
    if now - _last_sent.get(label, 0.0) < COOLDOWN:
        return f"{label} (too soon)"
    _last_sent[label] = now
    try:
        ok = action_fn()
        if ok is False or ok is None:
            logger.warning("Action had no active player: %s", label)
            return "No active Spotify player found"
        logger.info("Action: %s", label)
        return label
    except Exception as e:
        return f"Failed: {e}"

def _dbus_mpris(method: str) -> bool:
    """Direct D-Bus MPRIS call to Spotify in case playerctl blocks on CanGoNext/CanGoPrevious."""
    cmd = [
        "dbus-send", "--print-reply",
        "--dest=org.mpris.MediaPlayer2.spotify",
        "/org/mpris/MediaPlayer2",
        f"org.mpris.MediaPlayer2.Player.{method}",
    ]
    return _run(cmd) is not None

class SpotifyController:
    def __init__(self, auto_open=True, *args, **kwargs):
        self._connected  = bool(_run(["which", "playerctl"]))
        self._is_premium = False
        _start_spicetify_bridge()
        if auto_open and _run(["pgrep", "-x", "spotify"]) is None:
            try:
                spicetify_bin = Path(__file__).resolve().parent / ".spotify_spicetify" / "spotify"
                target_bin = str(spicetify_bin) if spicetify_bin.exists() else "spotify"
                subprocess.Popen(
                    [target_bin],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                logger.info("Launched Spotify desktop app (%s).", target_bin)
            except Exception as e:
                logger.warning("Could not auto-launch Spotify: %s", e)
        logger.info("SpotifyController ready (playerctl + Spicetify mode)")

    @property
    def is_connected(self):
        return self._connected

    @property
    def is_premium(self):
        return self._is_premium or (time.time() - _spicetify_last_seen < 5.0)

    def like_current_song(self):
        def _pp():
            ok = _playerctl("play-pause") is not None or _dbus_mpris("PlayPause")
            _push_spicetify_event("notify", "⏯️ Musewave: Play / Pause")
            return ok
        return _send(_pp, "Play/Pause toggled")

    def next_track(self):
        def _next():
            ok = _playerctl("next") is not None or _dbus_mpris("Next")
            _push_spicetify_event("notify", "⏭️ Musewave: Next Track")
            return ok
        return _send(_next, "Next track")

    def previous_track(self):
        def _prev():
            # In Spotify, sending 'previous' once after 3s only rewinds to 0:00.
            # Sending 'previous' twice skips back to the actual previous song!
            ok = _playerctl("previous") is not None or _dbus_mpris("Previous")
            time.sleep(0.15)
            _playerctl("previous") or _dbus_mpris("Previous")
            _push_spicetify_event("notify", "⏮️ Musewave: Previous Track")
            return ok
        return _send(_prev, "Previous track")

    def volume_up(self):
        return _send(lambda: _change_volume("up"), "Volume up")

    def volume_down(self):
        return _send(lambda: _change_volume("down"), "Volume down")

    def save_current_song(self):
        def _save():
            # 1. Trigger Spicetify in-app Like / Save to Spotify Liked Songs
            _push_spicetify_event("like_song")
            # 2. Also log locally to liked_songs.txt & desktop notification
            label = self.get_now_playing_label() or "Current track"
            liked_file = Path(__file__).resolve().parent / "liked_songs.txt"
            with open(liked_file, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  |  {label}\n")
            _run(["notify-send", "-a", "Musewave", "Saved to Spotify Liked Songs ❤️", label])
            return True
        return _send(_save, "Song saved")

    def get_now_playing_label(self):
        try:
            title  = _playerctl("metadata", "title") or _spicetify_track.get("title", "")
            artist = _playerctl("metadata", "artist") or _spicetify_track.get("artist", "")
            if title:
                return f"{title}  -  {artist}" if artist else title
        except Exception:
            pass
        return ""

