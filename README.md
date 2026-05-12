[README.md](https://github.com/user-attachments/files/27616171/README.1.md)

<div align="center">

```
███╗   ███╗██╗   ██╗███████╗███████╗██╗    ██╗ █████╗ ██╗   ██╗███████╗
████╗ ████║██║   ██║██╔════╝██╔════╝██║    ██║██╔══██╗██║   ██║██╔════╝
██╔████╔██║██║   ██║███████╗█████╗  ██║ █╗ ██║███████║██║   ██║█████╗  
██║╚██╔╝██║██║   ██║╚════██║██╔══╝  ██║███╗██║██╔══██║╚██╗ ██╔╝██╔══╝  
██║ ╚═╝ ██║╚██████╔╝███████║███████╗╚███╔███╔╝██║  ██║ ╚████╔╝ ███████╗
╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝  ╚═══╝  ╚══════╝
```

**Control your music with your hands. No API keys. No mouse. Just vibes.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-00C7B7?style=flat-square&logo=google&logoColor=white)](https://mediapipe.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org)
[![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=flat-square&logo=windows&logoColor=white)](https://microsoft.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-ff69b4?style=flat-square)]()

</div>

---

```
> initialising gesture engine...
> loading mediapipe hand model... ✓
> webcam feed active... ✓
> cosine similarity matcher ready... ✓
> awaiting gesture input_
```

---

## ❯ What Is This?

**Musewave** is a real-time hand gesture controller for music. Point your webcam at yourself, show a trained gesture, and it fires an OS-level media key — pause, skip, like, volume. Works with **Spotify, YouTube, VLC, or literally anything**.

No Spotify API. No Premium required. No cloud. Runs entirely on your CPU.

---

## ❯ How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                         PIPELINE                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [WEBCAM]  ──▶  [MEDIAPIPE]  ──▶  [NORMALISE]  ──▶  [MATCH]   │
│                                                                 │
│   30fps         21 landmarks      wrist=origin    cosine sim   │
│   BGR           x, y, z each      scale-free      vs stored    │
│   frame         = 63 floats       63-d vector     samples      │
│                                                                 │
│                                       ▼                         │
│                              score > 0.82?                      │
│                                 │       │                       │
│                                YES      NO                      │
│                                 │       │                       │
│                                 ▼       ▼                       │
│                           [MEDIA KEY]  wait                     │
│                          (OS-level)                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Stage 1 — MediaPipe Hand Detection
Google's on-device model finds your hand and outputs **21 3D landmark points** per frame (~30fps on any CPU).

### Stage 2 — Cosine Similarity Matching
Each gesture you train is stored as normalised 63-dimensional vectors. Your live pose is compared against every sample. Top-3 scores are averaged to reduce outlier noise. No neural net. No GPU. Pure geometry.

---

## ❯ Gestures

| Gesture | Shape | Default Action |
|---------|-------|---------------|
| ✊ Fist | All fingers curled | Play / Pause |
| ✌️ Peace | Index + middle up | Next Track |
| ☝️ Point | Index finger only | Previous Track |
| 🖐 Open | All 5 fingers spread | Volume Up |
| 🤌 Pinch | Thumb + index touch | Volume Down |

> These are just suggestions. You train your own. Any shape. Any action.

---

## ❯ Project Structure

```
musewave/
│
├── 📄 gesture_trainer.py     # webcam UI to record + name gestures
├── 📄 gesture_detector.py    # landmark extraction + cosine matching
├── 📄 spotify_controller.py  # wraps `keyboard` lib → media keys
├── 📄 main.py                # webcam loop, UI overlay, state machine
│
├── 📋 gesture_config.json    # your saved gestures (auto-generated)
├── 📋 gesture_app.log        # runtime log (auto-generated)
└── 📖 README.md
```

---

## ❯ Requirements

```
OS       Windows 10 / 11
Python   3.10+
Camera   Any USB or built-in webcam
Perms    Administrator (keyboard lib needs it for key injection)
```

```bash
pip install opencv-python mediapipe numpy keyboard
```

---

## ❯ Quickstart

```bash
# 1. clone
git clone https://github.com/yourusername/musewave.git
cd musewave

# 2. install deps
pip install opencv-python mediapipe numpy keyboard

# 3. train your gestures (run as admin)
python gesture_trainer.py

# 4. launch
python main.py
```

> **Note:** Right-click your terminal → *Run as Administrator* before step 3.  
> The `keyboard` library needs elevated privileges to inject OS-level key events.

---

## ❯ Training Your Gestures

```bash
python gesture_trainer.py
```

A webcam window opens. **Click on it first** — OpenCV only reads keys when its window has focus.

```
╔══════════════════════════════════════╗
║     GESTURE TRAINER  v1.0            ║
║                                      ║
║  [N]  New gesture                    ║
║  [T]  Test mode                      ║
║  [L]  List saved gestures            ║
║  [D]  Delete last gesture            ║
║  [Q]  Quit                           ║
╚══════════════════════════════════════╝
```

### Step-by-step

**① Name it**
```
Press N → type a name → Enter
e.g. "Fist", "Peace", "OK"
```

**② Pick an action**
```
W / S to move cursor, Enter to confirm

  > Play / Pause
    Next Track
    Previous Track
    Like / Save Song
    Volume Up
    Volume Down
```

**③ Record it**
```
Get hand in frame → green skeleton visible?
Press R → hold still 2.5 seconds → ring fills
Press A → record again from a different angle
Repeat until you have 30+ samples
Press F → saved ✓
```

**④ Test it**
```
Press T from menu
Show gesture → watch the score

  Match : Peace → Next Track
  Score : 0.94  ← excellent
```

### Score Guide

```
0.90 – 1.00  ████████████  excellent — fires every time
0.82 – 0.89  ██████████░░  good — consistent
0.70 – 0.81  ██████░░░░░░  weak — add more samples
< 0.70       ███░░░░░░░░░  no match — re-record
```

---

## ❯ Runtime Controls

```
gesture_trainer.py
──────────────────
N          New gesture
T          Test mode
L          List gestures
D          Delete last
Q / ESC    Quit

During recording:
R          Record (hold 2.5s)
A          Add more samples
F          Finish + save
ESC        Cancel / back

main.py
───────
Q / ESC    Quit
[gesture]  Fires mapped action
```

---

## ❯ Configuration

All gestures live in `gesture_config.json` — plain JSON, version-control friendly.

```json
{
  "gestures": [
    {
      "name": "Fist",
      "action": "Play / Pause",
      "samples": [
        [0.0, 0.0, 0.0, 0.12, -0.34, 0.05, ...],
        ...
      ]
    }
  ]
}
```

Back it up. Share it. Commit it. It's just data.

### Tunable Constants

```python
# gesture_detector.py
MATCH_THRESHOLD  = 0.82   # ↑ = fewer false positives, stricter
STABLE_FRAMES    = 6      # frames gesture must hold before firing

# gesture_trainer.py  
RECORD_DURATION  = 2.5    # seconds per recording pass
SAMPLES_PER_PASS = 30     # samples collected per pass

# main.py
COOLDOWN         = 5.0    # seconds before same gesture fires again
```

---

## ❯ Under The Hood

### Normalisation
```python
def extract_vector(hand_landmarks):
    pts = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])
    pts -= pts[0]                                    # wrist → origin
    span = np.linalg.norm(pts[9] - pts[0]) + 1e-6   # scale by hand size
    pts /= span
    return pts.flatten()                             # 63-d, position/scale free
```

### Matching
```python
sims  = sorted([cosine_sim(live_vec, s) for s in gesture["samples"]], reverse=True)
score = np.mean(sims[:3])   # top-3 average, not single best
```

### Noise Augmentation
```python
# Each recorded sample gets slight noise → synthetic variety
self.samples.append(vec + np.random.normal(0, 0.007, vec.shape))
```
This makes recognition robust to slight hand angle variation without extra recording rounds.

### Stability Buffer
```python
# 6 consecutive frames must agree before action fires (~200ms at 30fps)
# Prevents single-frame false positives
```

---

## ❯ Troubleshooting

```
PROBLEM                          FIX
───────────────────────────────────────────────────────────────────
Keys do nothing                  Click the webcam window first
                                 OpenCV only reads keys with focus

????? in menu text               Update to latest gesture_trainer.py
                                 Uses ASCII-only + FONT_HERSHEY_SIMPLEX

Wrong gestures firing            Raise MATCH_THRESHOLD to 0.88
                                 Re-record conflicting gestures
                                 Make shapes more visually distinct

Gestures not detecting           Lower MATCH_THRESHOLD to 0.78
                                 Add more samples (30+ per gesture)
                                 Improve lighting

No hand detected during record   Ensure green skeleton is visible first
                                 Better lighting. Whole hand in frame.

Media keys not working           Run terminal as Administrator
                                 Open Spotify and play something first
                                 Click Spotify → then back to gesture window

ModuleNotFoundError              pip install opencv-python mediapipe numpy keyboard
```

---

## ❯ Architecture Notes

**Why media keys instead of Spotify API?**  
Spotify removed playback control from free accounts in mid-2024. OS media keys work with Spotify Free, YouTube, VLC — anything.

**Why cosine similarity, not a neural net?**  
For a small fixed gesture set, cosine similarity on normalised vectors is:
- Microseconds per frame (vs milliseconds)  
- Interpretable — the score tells you exactly what's happening  
- Requires zero training data beyond what the user provides  
- Matches a neural net in accuracy for this task

**Why MediaPipe?**  
Runs real-time on CPU. No setup. Handles varying skin tones, partial occlusion, different hand sizes. Battle-tested at scale.

---

## ❯ Known Limitations

```
⚠  Windows only          keyboard lib media injection is Windows-specific
⚠  One hand at a time    gesture matcher uses first detected hand only  
⚠  Static gestures       hand poses only — no motion path gestures yet
⚠  Lighting sensitive    MediaPipe degrades in dark / backlit environments
⚠  No now-playing info   media key approach = no track name readback
```

---

## ❯ Roadmap

```
[ ] macOS + Linux support (platform key injection)
[ ] Dynamic gesture support (temporal landmark sequences)
[ ] Low-light adaptation
[ ] Multi-hand gesture combos
[ ] Optional Spotify API for now-playing display (Premium)
[ ] GUI installer / setup wizard
```

---

## ❯ License

```
MIT License — do whatever you want, just keep the attribution.
```

---

<div align="center">

```
built with mediapipe + opencv + too much caffeine
```

**[⭐ star this repo](https://github.com/yourusername/musewave)** if it saved you from touching your keyboard

</div>
