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

import cv2
import time
import logging
import sys
import os
from dotenv import load_dotenv
from gesture_detector import GestureDetector
from spotify_controller import SpotifyController, _run, _push_spicetify_event
from voice_controller import VoiceController

# Load environment variables from .env file
load_dotenv()

# ── CONFIGURATION ─────────────────────────────────────────────────
CLIENT_ID     = os.getenv("CLIENT_ID", "")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
REDIRECT_URI  = os.getenv("REDIRECT_URI", "http://127.0.0.1:8888/callback")

HOLD_REQUIRED = 1.5
COOLDOWN      = 2.5
WINDOW_NAME   = "Spotify Gesture Controller"
FONT          = cv2.FONT_HERSHEY_DUPLEX
# ──────────────────────────────────────────────────────────────────

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gesture_app.log")
_handlers = [logging.StreamHandler(sys.stdout)]
if sys.stdout.isatty():
    _handlers.append(logging.FileHandler(LOG_FILE))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=_handlers,
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

# Map action strings (from gesture_config.json / voice commands) to SpotifyController methods
ACTION_DISPATCH = {
    "Play / Pause":     lambda sp: sp.like_current_song(),
    "Next Track":       lambda sp: sp.next_track(),
    "Previous Track":   lambda sp: sp.previous_track(),
    "Like / Save Song": lambda sp: sp.save_current_song(),
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
    plan_label = "PREMIUM" if is_premium else "VOICE+CAM"
    plan_color = C_GREEN if is_premium else C_YELLOW
    put_text_shadow(frame, plan_label, (w - 135, 28), 0.50, plan_color, 1)

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
    show_window = "--show" in sys.argv
    # Keep the webcam completely OFF by default unless --camera or --show is passed,
    # or the user says "camera on".
    camera_requested = {"on": ("--camera" in sys.argv) or show_window}

    spotify = SpotifyController()
    logger.info("Media-key controller ready.")

    detector = None
    cap      = None

    state = {
        "status_msg":   "Voice control active ('play', 'pause', 'next', 'prev', 'volume up/down', 'save', 'camera on/off')",
        "status_color": C_WHITE,
    }

    def on_voice_command(action: str, spoken_text: str):
        if action == "camera_on":
            camera_requested["on"] = True
            _run(["notify-send", "-a", "Musewave", "Camera ON 📷", f"Heard '{spoken_text}' — hand gestures enabled"])
            _push_spicetify_event("notify", "📷 Musewave: Camera Gestures ON")
            logger.info("Voice '%s' -> Camera ON requested", spoken_text)
            return

        if action == "camera_off":
            camera_requested["on"] = False
            _run(["notify-send", "-a", "Musewave", "Camera OFF 🔒", f"Heard '{spoken_text}' — voice-only mode"])
            _push_spicetify_event("notify", "🔒 Musewave: Camera OFF (Voice Only)")
            logger.info("Voice '%s' -> Camera OFF requested", spoken_text)
            return

        fn = ACTION_DISPATCH.get(action)
        if fn:
            res = fn(spotify)
            state["status_msg"]   = f"Voice '{spoken_text}' -> {res}"
            state["status_color"] = C_GREEN
            _run(["notify-send", "-a", "Musewave Voice 🎙️", f"{action}", f"Heard: \"{spoken_text}\""])
            logger.info("Voice '%s' -> %s -> %s", spoken_text, action, res)

    voice = VoiceController(on_command=on_voice_command)
    voice.start()

    gesture_start   = None
    cooldown_until  = 0.0
    active_gesture  = None
    now_playing_txt = ""
    np_refresh_at   = 0.0

    logger.info(
        "Running in Voice-First mode (webcam is %s). Say 'camera on' / 'camera off' anytime.",
        "ON" if camera_requested["on"] else "OFF",
    )

    while True:
        # 1. Manage webcam open/close state based on voice toggle
        if camera_requested["on"] and cap is None:
            if detector is None:
                detector = GestureDetector()
                logger.info("Gesture detector initialized.")
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                logger.error("Cannot open webcam; staying in voice-only mode.")
                cap.release()
                cap = None
                camera_requested["on"] = False
            else:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                logger.info("Webcam turned ON.")

        elif not camera_requested["on"] and cap is not None:
            cap.release()
            cap = None
            if show_window:
                cv2.destroyAllWindows()
            logger.info("Webcam turned OFF (hardware camera released).")

        # 2. If webcam is OFF, sleep lightly while VoiceController handles commands
        if cap is None:
            time.sleep(0.15)
            continue

        # 3. Webcam is ON: process gesture frame
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.02)
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

        if show_window:
            detector.draw_landmarks(frame, result)

        heart_ok    = detector.stable_heart(result)
        thumbsup_ok = detector.stable_thumbsup(result)

        # Custom trained gesture check
        custom_name, custom_action = detector.recognise_custom(result)

        detected_builtin = "heart" if heart_ok else ("thumbsup" if thumbsup_ok else None)

        # ── Priority: custom > built-in heart/thumbsup (Save Song) ───

        if custom_name and not in_cooldown:
            fn  = ACTION_DISPATCH.get(custom_action, lambda sp: "Unknown action")
            res = fn(spotify)
            state["status_msg"]   = f"{custom_name}  ->  {res}"
            state["status_color"] = C_BLUE
            step_cooldown  = 0.6 if custom_action in ("Volume Up", "Volume Down") else COOLDOWN
            cooldown_until = now + step_cooldown
            gesture_start  = None
            active_gesture = None
            logger.info("Custom '%s' -> %s -> %s", custom_name, custom_action, res)

        elif detected_builtin and not in_cooldown:
            if active_gesture != detected_builtin:
                gesture_start  = now
                active_gesture = detected_builtin

            hold = now - gesture_start
            if hold >= HOLD_REQUIRED:
                res = spotify.save_current_song()
                state["status_msg"]   = f"Like / Save  ->  {res}"
                state["status_color"] = C_PINK
                cooldown_until = now + COOLDOWN
                gesture_start  = None
                active_gesture = None
                logger.info("Hold '%s' -> %s", detected_builtin, res)
            else:
                icon = "Heart" if detected_builtin == "heart" else "Thumbs-up"
                state["status_msg"]   = f"{icon} - hold {HOLD_REQUIRED - hold:.1f}s more"
                state["status_color"] = C_GREEN

        else:
            gesture_start  = None
            active_gesture = None
            if not in_cooldown and state["status_color"] not in (C_PINK, C_ORANGE, C_BLUE, C_GREEN):
                state["status_msg"]   = "Voice + Gestures active | Say 'camera off' to turn off webcam"
                state["status_color"] = C_WHITE

        if show_window:
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

            draw_ui(
                frame, state["status_msg"], state["status_color"], bar_progress,
                now_playing_txt, cooldown_left, glabel,
                is_premium=spotify.is_premium,
            )

            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), ord('Q'), 27):
                break
        else:
            time.sleep(0.01)

    voice.stop()
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()
    logger.info("Exited.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Stopped by user (Ctrl+C).")