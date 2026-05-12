"""
gesture_trainer.py  — Webcam Gesture Training System
=====================================================
Show your hand gesture to the webcam → it records → maps to a Spotify action.

Supported actions:
  - Play / Pause
  - Next Track
  - Previous Track
  - Like / Save Song
  - Volume Up
  - Volume Down

Usage:
  python gesture_trainer.py

Controls:
  [N] = Add a new gesture (type name → pick action → record)
  [T] = Test all saved gestures live
  [D] = Delete last saved gesture
  [L] = List all saved gestures
  [Q] = Quit

While recording:
  [R] = Hold to capture samples (keep your hand steady for ~2.5s)
  [S] = Save the gesture after recording
  [ESC] = Go back / cancel

Gestures are saved to: gesture_config.json
The main.py file reads gesture_config.json automatically.
"""

import cv2
import json
import time
import numpy as np
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gesture_trainer")

try:
    import mediapipe as mp
    MP_OK = True
except ImportError:
    MP_OK = False
    logger.error("mediapipe not found. Run: pip install mediapipe")

GESTURE_CONFIG_FILE = "gesture_config.json"
SAMPLES_PER_GESTURE = 30
RECORD_DURATION     = 2.5       # seconds
MATCH_THRESHOLD     = 0.82

FONT = cv2.FONT_HERSHEY_DUPLEX

C_WHITE  = (255, 255, 255)
C_BLACK  = (  0,   0,   0)
C_GREEN  = ( 60, 220,  60)
C_RED    = ( 50,  50, 220)
C_ORANGE = ( 50, 165, 255)
C_PINK   = (200, 100, 220)
C_TEAL   = (200, 200,  50)
C_GREY   = (140, 140, 140)
C_DARK   = ( 15,  15,  15)
C_YELLOW = (  0, 210, 210)
C_BLUE   = (220, 160,  50)

ACTIONS = [
    "Play / Pause",
    "Next Track",
    "Previous Track",
    "Like / Save Song",
    "Volume Up",
    "Volume Down",
]


# ════════════════════════════════════════════════════════════════════
# Landmark helpers
# ════════════════════════════════════════════════════════════════════

def extract_vector(hand_landmarks) -> np.ndarray:
    """21 landmarks × [x,y,z] = 63-d vector, normalised for position & scale."""
    pts = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])
    pts -= pts[0]                                # centre on wrist
    span = np.linalg.norm(pts[9] - pts[0]) + 1e-6
    pts /= span
    return pts.flatten()


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def recognise(vector: np.ndarray, config: dict):
    """Returns (name, action, score) or (None, None, best_score)."""
    best_name, best_action, best_score = None, None, 0.0
    for g in config["gestures"]:
        sims = sorted([cosine_sim(vector, s) for s in g["samples"]], reverse=True)
        score = float(np.mean(sims[:3])) if sims else 0.0
        if score > best_score:
            best_score  = score
            best_name   = g["name"]
            best_action = g["action"]
    if best_score >= MATCH_THRESHOLD:
        return best_name, best_action, best_score
    return None, None, best_score


# ════════════════════════════════════════════════════════════════════
# Config I/O
# ════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    if Path(GESTURE_CONFIG_FILE).exists():
        with open(GESTURE_CONFIG_FILE) as f:
            raw = json.load(f)
        for g in raw.get("gestures", []):
            g["samples"] = [np.array(s) for s in g["samples"]]
        return raw
    return {"gestures": []}


def save_config(config: dict):
    raw = {"gestures": [
        {"name": g["name"], "action": g["action"],
         "samples": [s.tolist() for s in g["samples"]]}
        for g in config["gestures"]
    ]}
    with open(GESTURE_CONFIG_FILE, "w") as f:
        json.dump(raw, f, indent=2)
    logger.info("Saved -> %s", GESTURE_CONFIG_FILE)


# ════════════════════════════════════════════════════════════════════
# UI helpers
# ════════════════════════════════════════════════════════════════════

def shadow(img, text, pos, scale, color, thick=1):
    x, y = pos
    cv2.putText(img, text, (x+2, y+2), FONT, scale, C_BLACK, thick+2, cv2.LINE_AA)
    cv2.putText(img, text, pos,        FONT, scale, color,   thick,   cv2.LINE_AA)


def panel(img, lines, top_left, lh=30, pad=14, bg=C_DARK, alpha=0.82):
    x, y = top_left
    h_box = len(lines) * lh + pad * 2
    w_box = max((len(l) for l in lines), default=10) * 11 + pad * 2
    ov = img.copy()
    cv2.rectangle(ov, (x, y), (x + w_box, y + h_box), bg, -1)
    cv2.addWeighted(ov, alpha, img, 1 - alpha, 0, img)
    for i, line in enumerate(lines):
        is_sel = line.startswith(">>")
        col    = C_GREEN if is_sel else C_WHITE
        txt    = line.lstrip("> ").lstrip()
        shadow(img, txt, (x + pad, y + pad + (i + 1) * lh - 6), 0.50, col, 1)


def recording_ring(img, progress, cx, cy, r=80):
    angle = int(360 * min(progress, 1.0))
    col   = C_GREEN if progress < 0.85 else C_PINK
    cv2.ellipse(img, (cx, cy), (r, r), -90, 0, angle, col, 6, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), r - 3, (40, 40, 40), 2)


# ════════════════════════════════════════════════════════════════════
# Trainer class
# ════════════════════════════════════════════════════════════════════

class GestureTrainer:

    def __init__(self):
        if not MP_OK:
            sys.exit(1)
        self.mp_hands = mp.solutions.hands
        self.hands    = self.mp_hands.Hands(
            static_image_mode=False, max_num_hands=2,
            min_detection_confidence=0.6, min_tracking_confidence=0.55,
        )
        self.mp_draw  = mp.solutions.drawing_utils
        self.mp_style = mp.solutions.drawing_styles

        self.config       = load_config()
        self.mode         = "menu"
        self.new_name     = ""
        self.new_action   = None
        self.action_idx   = 0
        self.samples      = []
        self.record_start = None
        self.flash_msg    = ""
        self.flash_color  = C_WHITE
        self.flash_until  = 0.0
        self.test_result  = ""
        self.test_score   = 0.0

    # ── Mediapipe ────────────────────────────────────────────────────

    def first_hand(self, result):
        if result.multi_hand_landmarks:
            return result.multi_hand_landmarks[0]
        return None

    def draw_lm(self, frame, result):
        if result.multi_hand_landmarks:
            for hlm in result.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame, hlm,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_style.get_default_hand_landmarks_style(),
                    self.mp_style.get_default_hand_connections_style(),
                )

    # ── HUD ──────────────────────────────────────────────────────────

    def hud(self, frame, result, now):
        h, w = frame.shape[:2]

        # top bar
        ov = frame.copy()
        cv2.rectangle(ov, (0, 0), (w, 60), C_DARK, -1)
        cv2.addWeighted(ov, 0.80, frame, 0.20, 0, frame)
        shadow(frame, "GESTURE TRAINER", (12, 38), 0.75, C_TEAL, 2)
        n = len(self.config["gestures"])
        shadow(frame, f"{n} gesture{'s' if n!=1 else ''} saved",
               (w - 230, 36), 0.50, C_YELLOW, 1)

        dispatch = {
            "menu":          self._hud_menu,
            "name_input":    self._hud_name,
            "action_select": self._hud_action,
            "recording":     self._hud_record,
            "test":          self._hud_test,
        }
        dispatch.get(self.mode, lambda *a: None)(frame, result, now)

        # flash message
        if now < self.flash_until:
            fw = len(self.flash_msg) * 10
            shadow(frame, self.flash_msg,
                   (w // 2 - fw // 2, h - 120), 0.72, self.flash_color, 2)

        cv2.putText(frame, "Q = quit", (w - 90, h - 8),
                    FONT, 0.38, C_GREY, 1, cv2.LINE_AA)

    def _hud_menu(self, frame, result, now):
        lines = [
            "--- MENU ---",
            "[N] Add new gesture",
            "[T] Test gestures",
            "[D] Delete last gesture",
            "[L] List all gestures",
        ]
        if self.config["gestures"]:
            names = "  ".join(g["name"] for g in self.config["gestures"])
            lines += ["", f"Saved: {names}"]
        panel(frame, lines, (12, 75))

    def _hud_name(self, frame, result, now):
        panel(frame, [
            "TYPE gesture name  then press ENTER",
            f">> {self.new_name}_",
            "",
            "[ENTER] confirm   [ESC] back",
        ], (12, 75))

    def _hud_action(self, frame, result, now):
        lines = ["SELECT ACTION   UP/DOWN or W/S   ENTER", ""]
        for i, a in enumerate(ACTIONS):
            lines.append((">> " if i == self.action_idx else "   ") + a)
        lines += ["", "[ESC] back"]
        panel(frame, lines, (12, 75))

    def _hud_record(self, frame, result, now):
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2

        if self.record_start is not None:
            elapsed  = now - self.record_start
            progress = elapsed / RECORD_DURATION
            recording_ring(frame, progress, cx, cy - 50)
            shadow(frame,
                   f"Hold still... {len(self.samples)}/{SAMPLES_PER_GESTURE}",
                   (cx - 150, cy + 60), 0.70, C_GREEN, 2)
        else:
            panel(frame, [
                f"Gesture : {self.new_name}",
                f"Action  : {self.new_action}",
                "",
                "[R] Hold to record  (keep hand steady ~2.5s)",
                "[S] Save gesture when satisfied",
                "[ESC] Cancel",
            ], (12, 75))
            shadow(frame, f"Samples captured: {len(self.samples)}",
                   (12, h - 30), 0.60, C_TEAL, 1)

    def _hud_test(self, frame, result, now):
        lines = ["--- TEST MODE --- show a gesture", ""]
        if self.test_result:
            lines += [f">> {self.test_result}", f"   Score: {self.test_score:.2f}"]
        else:
            lines += ["(no match yet)"]
        lines += ["", "[ESC] back to menu"]
        panel(frame, lines, (12, 75))

    # ── Flash ─────────────────────────────────────────────────────────

    def flash(self, msg, color=C_GREEN, dur=2.0):
        self.flash_msg   = msg
        self.flash_color = color
        self.flash_until = time.time() + dur

    # ── Key handler ───────────────────────────────────────────────────

    def handle_key(self, key, result, now) -> bool:
        if key == 255:   # no key
            return True
        if key in (ord('q'), 27) and self.mode == "menu":
            return False

        if self.mode == "menu":
            if key == ord('n'):
                self.new_name  = ""
                self.samples   = []
                self.mode      = "name_input"
            elif key == ord('t'):
                self.test_result = ""
                self.mode        = "test"
            elif key == ord('d'):
                if self.config["gestures"]:
                    r = self.config["gestures"].pop()
                    save_config(self.config)
                    self.flash(f"Deleted: {r['name']}", C_RED)
                else:
                    self.flash("Nothing to delete", C_GREY)
            elif key == ord('l'):
                if self.config["gestures"]:
                    self.flash("  |  ".join(g["name"] for g in self.config["gestures"]),
                               C_TEAL, 3.5)
                else:
                    self.flash("No gestures saved yet", C_GREY)

        elif self.mode == "name_input":
            if key == 27:
                self.mode = "menu"
            elif key == 13:
                if self.new_name.strip():
                    self.action_idx = 0
                    self.mode       = "action_select"
                else:
                    self.flash("Name cannot be empty!", C_RED)
            elif key == 8:
                self.new_name = self.new_name[:-1]
            elif 32 <= key <= 126:
                self.new_name += chr(key)

        elif self.mode == "action_select":
            if key == 27:
                self.mode = "name_input"
            elif key in (82, 119, ord('w')):   # UP arrow / w
                self.action_idx = (self.action_idx - 1) % len(ACTIONS)
            elif key in (84, 115, ord('s')):   # DOWN arrow / s
                self.action_idx = (self.action_idx + 1) % len(ACTIONS)
            elif key == 13:
                self.new_action = ACTIONS[self.action_idx]
                self.samples    = []
                self.mode       = "recording"

        elif self.mode == "recording":
            if key == 27:
                self.mode = "menu"
            elif key == ord('r'):
                hand = self.first_hand(result)
                if hand:
                    self.record_start = now
                    self.samples      = []
                else:
                    self.flash("No hand in view! Try again.", C_RED)
            elif key == ord('s'):
                if len(self.samples) >= 5:
                    self.config["gestures"].append({
                        "name":    self.new_name,
                        "action":  self.new_action,
                        "samples": self.samples,
                    })
                    save_config(self.config)
                    self.flash(f"Saved '{self.new_name}' -> {self.new_action}", C_GREEN, 2.5)
                    self.mode = "menu"
                else:
                    self.flash(f"Need 5+ samples (have {len(self.samples)}). Press [R] again.", C_RED)

        elif self.mode == "test":
            if key == 27:
                self.mode = "menu"

        return True

    # ── Recording update ──────────────────────────────────────────────

    def update_record(self, result, now):
        if self.mode != "recording" or self.record_start is None:
            return
        hand = self.first_hand(result)
        if hand is None:
            self.record_start = None
            self.flash("Hand lost! Press [R] to retry.", C_RED)
            return
        elapsed      = now - self.record_start
        target_count = int((elapsed / RECORD_DURATION) * SAMPLES_PER_GESTURE)
        while len(self.samples) < target_count:
            vec   = extract_vector(hand)
            noise = np.random.normal(0, 0.008, vec.shape)
            self.samples.append(vec + noise)
        if elapsed >= RECORD_DURATION:
            self.record_start = None
            self.flash(f"{len(self.samples)} samples ready! Press [S] to save.", C_GREEN, 3.0)

    # ── Test update ───────────────────────────────────────────────────

    def update_test(self, result, now):
        if self.mode != "test":
            return
        hand = self.first_hand(result)
        if hand:
            vec = extract_vector(hand)
            name, action, score = recognise(vec, self.config)
            self.test_result = f"{name}  ->  {action}" if name else "(no match)"
            self.test_score  = score

    # ── Main loop ─────────────────────────────────────────────────────

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Cannot open webcam.")
            sys.exit(1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        logger.info("Trainer running. Press [N] to add your first gesture.")

        while True:
            ok, frame = cap.read()
            if not ok:
                continue
            frame  = cv2.flip(frame, 1)
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.hands.process(rgb)
            now    = time.time()

            self.draw_lm(frame, result)
            self.update_record(result, now)
            self.update_test(result, now)
            self.hud(frame, result, now)

            cv2.imshow("Gesture Trainer", frame)
            key = cv2.waitKey(1) & 0xFF

            if not self.handle_key(key, result, now):
                break

        cap.release()
        cv2.destroyAllWindows()
        logger.info("Done. Gestures saved to %s", GESTURE_CONFIG_FILE)


if __name__ == "__main__":
    GestureTrainer().run()