"""
main.py  — Spotify Gesture Controller  (Custom Gesture Edition)
===============================================================
Controls music using gestures you train yourself via gesture_trainer.py

Built-in gestures (always active):
  ❤️  Heart shape (2 hands)     → Play / Pause  (hold 1.5s)
  👍  Thumbs-up                 → Play / Pause  (hold 1.5s)
  ➡️  Swipe right               → Next Track

Custom gestures (trained by you):
  Run gesture_trainer.py → show gesture on webcam → map to any action
  Gestures are loaded from gesture_config.json automatically.

Press Q or ESC to quit.
"""

import atexit
import ctypes
import cv2
import time
import logging
import sys
import os
import queue
from dotenv import load_dotenv
from gesture_detector import GestureDetector
from spotify_controller import SpotifyController
from voice_controller import VoiceController

# Load environment variables from .env file
load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
LOCK_FILE = os.path.join(SCRIPT_DIR, "musewave.lock")

# Only one Musewave instance (webcam can only be used once).
_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "MusewaveGestureApp")
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit(0)

def _write_lock():
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

def _remove_lock():
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass

_write_lock()
atexit.register(_remove_lock)

# ── CONFIGURATION ─────────────────────────────────────────────────
CLIENT_ID     = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
REDIRECT_URI  = os.getenv("REDIRECT_URI", "http://127.0.0.1:8888/callback")

HOLD_REQUIRED = 1.5
COOLDOWN      = 5.0
WINDOW_NAME   = "Spotify Gesture Controller"
FONT          = cv2.FONT_HERSHEY_DUPLEX
SILENT_MODE   = "--silent" in sys.argv
# ──────────────────────────────────────────────────────────────────

_log_handlers = [logging.FileHandler("gesture_app.log")]
if not os.path.basename(sys.executable).lower().startswith("pythonw"):
    _log_handlers.insert(0, logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=_log_handlers,
)
logger = logging.getLogger("main")

C_WHITE  = (255, 255, 255)
C_BLACK  = (  0,   0,   0)
C_GREEN  = ( 80, 220,  80)
C_PINK   = (160,  90, 220)
C_ORANGE = ( 50, 165, 255)
C_GREY   = (150, 150, 150)
C_DARK   = ( 20,  20,  20)
C_TEAL   = (200, 200,  50)
C_YELLOW = (  0, 210, 210)
C_BLUE   = (220, 160,  50)

# Map action strings (from gesture_config.json) to SpotifyController methods
ACTION_DISPATCH = {
    "Play / Pause":     lambda sp: sp.like_current_song(),
    "Next Track":       lambda sp: sp.next_track(),
    "Previous Track":   lambda sp: sp.previous_track(),
    "Like / Save Song": lambda sp: sp.like_current_song(),
    "Volume Up":        lambda sp: sp.volume_up(),
    "Volume Down":      lambda sp: sp.volume_down(),
}


def put_text_shadow(img, text, pos, scale, color, thickness=2):
    x, y = pos
    cv2.putText(img, text, (x+2, y+2), FONT, scale, C_BLACK, thickness+2, cv2.LINE_AA)
    cv2.putText(img, text, (x,   y),   FONT, scale, color,   thickness,   cv2.LINE_AA)


def draw_progress_bar(img, progress, top_left, width, height, color):
    x, y = top_left
    cv2.rectangle(img, (x, y), (x+width, y+height), (50, 50, 50), -1)
    filled = int(width * min(progress, 1.0))
    if filled > 0:
        cv2.rectangle(img, (x, y), (x+filled, y+height), color, -1)
    cv2.rectangle(img, (x, y), (x+width, y+height), C_GREY, 1)


def draw_ui(frame, status_msg, status_color, hold_progress,
            now_playing, cooldown_left, gesture_label, is_premium):
    h, w = frame.shape[:2]

    ov = frame.copy()
    cv2.rectangle(ov, (0, 0), (w, 70), C_DARK, -1)
    cv2.addWeighted(ov, 0.75, frame, 0.25, 0, frame)
    if now_playing:
        txt = f"Now Playing: {now_playing}"
        if len(txt) > 60:
            txt = txt[:60] + "..."
        put_text_shadow(frame, txt, (12, 42), 0.58, C_TEAL, 1)
    plan_label = "PREMIUM" if is_premium else "FREE"
    plan_color = C_GREEN if is_premium else C_YELLOW
    put_text_shadow(frame, plan_label, (w - 115, 28), 0.50, plan_color, 1)

    ov2 = frame.copy()
    cv2.rectangle(ov2, (0, h - 90), (w, h), C_DARK, -1)
    cv2.addWeighted(ov2, 0.80, frame, 0.20, 0, frame)
    put_text_shadow(frame, status_msg, (12, h - 55), 0.72, status_color, 2)
    if gesture_label:
        put_text_shadow(frame, gesture_label, (w - 300, 42), 0.55, C_ORANGE, 1)
    if cooldown_left > 0:
        put_text_shadow(frame, f"cooldown {cooldown_left:.1f}s", (12, h - 18), 0.52, C_GREY, 1)
    if hold_progress > 0:
        draw_progress_bar(frame, hold_progress, (12, h - 82), w - 24, 10, C_PINK)
    cv2.putText(frame, "Q = quit", (w - 90, h - 8), FONT, 0.38, C_GREY, 1, cv2.LINE_AA)


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Cannot open webcam.")
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    detector = GestureDetector()
    logger.info("Gesture detector ready.")

    spotify = SpotifyController()
    logger.info("Media-key controller ready.")

    voice_queue = queue.Queue()
    vc = VoiceController(callback=voice_queue.put)
    vc.start()

    gesture_start   = None
    cooldown_until  = 0.0
    status_msg      = "Show a gesture or train new ones with gesture_trainer.py"
    status_color    = C_WHITE
    active_gesture  = None
    now_playing_txt = ""
    np_refresh_at   = 0.0

    logger.info("Running%s.", " silently in background" if SILENT_MODE else ". Press Q to quit.")

    if not SILENT_MODE:
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            continue

        frame  = cv2.flip(frame, 1)
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = detector.process(rgb)
        now    = time.time()

        if now >= np_refresh_at:
            try:
                now_playing_txt = spotify.get_now_playing_label()
            except Exception:
                now_playing_txt = ""
            np_refresh_at = now + 8

        in_cooldown   = now < cooldown_until
        cooldown_left = max(0.0, cooldown_until - now)

        if not SILENT_MODE:
            detector.draw_landmarks(frame, result)

        heart_ok    = detector.stable_heart(result)
        thumbsup_ok = detector.stable_thumbsup(result)
        swipe_ok    = (not in_cooldown) and detector.detect_right_swipe(result)

        # Custom trained gesture check
        custom_name, custom_action = detector.recognise_custom(result)

        try:
            voice_action = voice_queue.get_nowait()
        except queue.Empty:
            voice_action = None

        detected_builtin = "heart" if heart_ok else ("thumbsup" if thumbsup_ok else None)

        # ── Priority: voice > swipe > custom > built-in hold ─────────────────

        if voice_action and not in_cooldown:
            fn  = ACTION_DISPATCH.get(voice_action, lambda sp: "Unknown action")
            res = fn(spotify)
            status_msg     = f"Voice: {voice_action}  ->  {res}"
            status_color   = C_PINK
            cooldown_until = now + COOLDOWN
            gesture_start  = None
            active_gesture = None
            logger.info("Voice command -> %s -> %s", voice_action, res)

        elif swipe_ok:
            res = spotify.next_track()
            status_msg     = f"Next Track  ->  {res}"
            status_color   = C_ORANGE
            cooldown_until = now + COOLDOWN
            gesture_start  = None
            active_gesture = None
            logger.info("Swipe -> %s", res)

        elif custom_name and not in_cooldown:
            fn  = ACTION_DISPATCH.get(custom_action, lambda sp: "Unknown action")
            res = fn(spotify)
            status_msg     = f"{custom_name}  ->  {res}"
            status_color   = C_BLUE
            cooldown_until = now + COOLDOWN
            gesture_start  = None
            active_gesture = None
            logger.info("Custom '%s' -> %s -> %s", custom_name, custom_action, res)

        elif detected_builtin and not in_cooldown:
            if active_gesture != detected_builtin:
                gesture_start  = now
                active_gesture = detected_builtin

            hold = now - gesture_start
            if hold >= HOLD_REQUIRED:
                res = spotify.like_current_song()
                status_msg     = f"Play/Pause  ->  {res}"
                status_color   = C_PINK
                cooldown_until = now + COOLDOWN
                gesture_start  = None
                active_gesture = None
                logger.info("Hold '%s' -> %s", detected_builtin, res)
            else:
                icon = "Heart" if detected_builtin == "heart" else "Thumbs-up"
                status_msg   = f"{icon} — hold {HOLD_REQUIRED - hold:.1f}s more"
                status_color = C_GREEN

        else:
            gesture_start  = None
            active_gesture = None
            if not in_cooldown and status_color not in (C_PINK, C_ORANGE, C_BLUE):
                status_msg   = "Heart/Thumbs = play-pause  |  Swipe = next  |  Custom = your gestures"
                status_color = C_WHITE

        bar_progress = ((now - gesture_start) / HOLD_REQUIRED) if gesture_start else 0.0

        num_hands = detector.has_hands(result)
        if custom_name:
            glabel = f"Custom: {custom_name}"
        elif detected_builtin == "heart":
            glabel = "Heart detected"
        elif detected_builtin == "thumbsup":
            glabel = "Thumbs-up detected"
        elif num_hands:
            glabel = f"{num_hands} hand{'s' if num_hands > 1 else ''} visible"
        else:
            glabel = ""

        if not SILENT_MODE:
            draw_ui(
                frame, status_msg, status_color, bar_progress,
                now_playing_txt, cooldown_left, glabel,
                is_premium=spotify.is_premium,
            )
            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                break
        else:
            cv2.waitKey(1)

    cap.release()
    if not SILENT_MODE:
        cv2.destroyAllWindows()
    vc.stop()
    logger.info("Exited.")


if __name__ == "__main__":
    main()