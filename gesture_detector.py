"""
gesture_detector.py  — Custom Gesture Detector
================================================
Loads trained gestures from gesture_config.json (created by gesture_trainer.py).
Keeps ALL original methods intact (stable_heart, stable_thumbsup, detect_right_swipe,
draw_landmarks, has_hands) so main.py works without any changes.

NEW: recognise_custom(result) → returns (gesture_name, action) or (None, None)
     This is called by main.py after the built-in gesture checks.

Gesture matching:
  - Cosine similarity on normalised 63-d landmark vectors
  - Top-3 sample average per gesture
  - Threshold: 0.82 (tunable via MATCH_THRESHOLD)
  - Stability buffer: must match same gesture for STABLE_FRAMES consecutive frames
"""

import json
import time
import collections
import numpy as np
from pathlib import Path

try:
    import mediapipe as mp
    MP_OK = True
except ImportError:
    MP_OK = False

GESTURE_CONFIG_FILE = "gesture_config.json"
MATCH_THRESHOLD     = 0.82
STABLE_FRAMES       = 6           # frames in a row before declaring a stable custom gesture
SWIPE_BUFFER        = 12          # frames of wrist-x history for swipe detection
SWIPE_THRESHOLD     = 0.18        # normalised-x distance for a swipe


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════

def _load_config() -> dict:
    if Path(GESTURE_CONFIG_FILE).exists():
        with open(GESTURE_CONFIG_FILE) as f:
            raw = json.load(f)
        for g in raw.get("gestures", []):
            g["samples"] = [np.array(s) for s in g["samples"]]
        return raw
    return {"gestures": []}


def _extract_vector(hand_landmarks) -> np.ndarray:
    pts = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])
    pts -= pts[0]
    span = np.linalg.norm(pts[9] - pts[0]) + 1e-6
    pts /= span
    return pts.flatten()


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _recognise(vector: np.ndarray, config: dict):
    best_name, best_action, best_score = None, None, 0.0
    for g in config["gestures"]:
        sims  = sorted([_cosine_sim(vector, s) for s in g["samples"]], reverse=True)
        score = float(np.mean(sims[:3])) if sims else 0.0
        if score > best_score:
            best_score  = score
            best_name   = g["name"]
            best_action = g["action"]
    if best_score >= MATCH_THRESHOLD:
        return best_name, best_action, best_score
    return None, None, best_score


# ════════════════════════════════════════════════════════════════════
# GestureDetector
# ════════════════════════════════════════════════════════════════════

class GestureDetector:
    """
    Drop-in replacement for the original GestureDetector.
    All original methods kept + recognise_custom() added.
    """

    def __init__(self):
        if not MP_OK:
            raise ImportError("mediapipe not found. Run: pip install mediapipe")

        self.mp_hands = mp.solutions.hands
        self.hands    = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.55,
        )
        self.mp_draw  = mp.solutions.drawing_utils
        self.mp_style = mp.solutions.drawing_styles

        # Custom gesture state
        self._config        = _load_config()
        self._stable_buf    = collections.deque(maxlen=STABLE_FRAMES)
        self._last_reload   = time.time()

        # Swipe detection state
        self._wrist_history = collections.deque(maxlen=SWIPE_BUFFER)
        self._swipe_fired   = False

        # Heart / thumbs-up stability state (kept from original)
        self._heart_buf     = collections.deque(maxlen=8)
        self._thumbsup_buf  = collections.deque(maxlen=8)

    # ── Config hot-reload (every 5s) ─────────────────────────────────

    def _maybe_reload(self):
        now = time.time()
        if now - self._last_reload > 5.0:
            self._config      = _load_config()
            self._last_reload = now

    # ── Mediapipe ────────────────────────────────────────────────────

    def process(self, rgb):
        """Run mediapipe hand detection. Pass RGB frame."""
        return self.hands.process(rgb)

    def draw_landmarks(self, frame, result):
        """Draw hand skeleton on frame (BGR)."""
        if result.multi_hand_landmarks:
            for hlm in result.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame, hlm,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_style.get_default_hand_landmarks_style(),
                    self.mp_style.get_default_hand_connections_style(),
                )

    def has_hands(self, result) -> int:
        """Return number of hands detected."""
        if result.multi_hand_landmarks:
            return len(result.multi_hand_landmarks)
        return 0

    # ── Original gesture detectors (kept for backwards compat) ───────

    def stable_heart(self, result) -> bool:
        """
        Detects a two-hand heart shape.
        Original heuristic: index + thumb tips of both hands form a rough diamond.
        """
        detected = self._detect_heart_raw(result)
        self._heart_buf.append(detected)
        return sum(self._heart_buf) >= 5

    def stable_thumbsup(self, result) -> bool:
        """
        Detects a thumbs-up gesture (thumb extended, other fingers curled).
        """
        detected = self._detect_thumbsup_raw(result)
        self._thumbsup_buf.append(detected)
        return sum(self._thumbsup_buf) >= 5

    def detect_right_swipe(self, result) -> bool:
        """
        Detects a rightward wrist swipe.
        Returns True once per swipe (resets after hand leaves or reverses).
        """
        if not result.multi_hand_landmarks:
            self._wrist_history.clear()
            self._swipe_fired = False
            return False

        wrist_x = result.multi_hand_landmarks[0].landmark[0].x
        self._wrist_history.append(wrist_x)

        if len(self._wrist_history) < SWIPE_BUFFER:
            return False

        delta = self._wrist_history[-1] - self._wrist_history[0]
        # NOTE: frame is flipped so positive delta = left in camera = right for user
        if delta < -SWIPE_THRESHOLD and not self._swipe_fired:
            self._swipe_fired = True
            return True
        if abs(delta) < 0.05:
            self._swipe_fired = False
        return False

    # ── NEW: Custom gesture recognition ──────────────────────────────

    def recognise_custom(self, result):
        """
        Matches the current hand pose against all trained gestures.
        Returns (gesture_name, action_string) when a stable match is found,
        or (None, None) otherwise.

        Call this in main.py's frame loop alongside stable_heart / stable_thumbsup.
        """
        self._maybe_reload()

        if not self._config["gestures"]:
            return None, None

        if not result.multi_hand_landmarks:
            self._stable_buf.clear()
            return None, None

        hand  = result.multi_hand_landmarks[0]
        vec   = _extract_vector(hand)
        name, action, _ = _recognise(vec, self._config)
        self._stable_buf.append(name)

        # Require STABLE_FRAMES consistent frames
        if (len(self._stable_buf) == STABLE_FRAMES
                and len(set(self._stable_buf)) == 1
                and name is not None):
            return name, action

        return None, None

    # ── Internal raw detectors ────────────────────────────────────────

    def _detect_heart_raw(self, result) -> bool:
        """
        Two-hand heart: tips of index fingers and thumbs are close together
        and form a roughly diamond shape.
        """
        if not result.multi_hand_landmarks or len(result.multi_hand_landmarks) < 2:
            return False
        try:
            h1, h2 = result.multi_hand_landmarks[0], result.multi_hand_landmarks[1]
            # Landmark 4 = thumb tip, 8 = index tip
            def pt(hlm, idx): return np.array([hlm.landmark[idx].x, hlm.landmark[idx].y])
            t1, t2 = pt(h1, 4), pt(h2, 4)   # thumb tips
            i1, i2 = pt(h1, 8), pt(h2, 8)   # index tips
            thumb_dist = np.linalg.norm(t1 - t2)
            index_dist = np.linalg.norm(i1 - i2)
            # Thumbs close, indexes close
            return thumb_dist < 0.12 and index_dist < 0.12
        except Exception:
            return False

    def _detect_thumbsup_raw(self, result) -> bool:
        """
        Thumbs-up: thumb tip significantly above thumb base,
        all other finger tips below their PIP joints.
        """
        if not result.multi_hand_landmarks:
            return False
        try:
            lm = result.multi_hand_landmarks[0].landmark
            # Thumb extended upward: tip (4) y < ip (3) y  (smaller y = higher in frame)
            thumb_up = lm[4].y < lm[3].y < lm[2].y
            # Other fingers curled: tip y > pip y for fingers 2-5
            fingers_curled = all(lm[tip].y > lm[pip].y
                                  for tip, pip in [(8,6),(12,10),(16,14),(20,18)])
            return thumb_up and fingers_curled
        except Exception:
            return False