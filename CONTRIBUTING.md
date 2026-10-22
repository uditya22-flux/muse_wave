# Contributing to Musewave

Thank you for your interest in contributing to **Musewave** (`uditya22-flux/muse_wave`). This document outlines the architecture guidelines, development workflow, and pull request requirements.

---

## 1. Local Development Setup

### Linux (Ubuntu / Debian)
```bash
git clone https://github.com/uditya22-flux/muse_wave.git
cd muse_wave
chmod +x install.sh
./install.sh
```

### Windows 10 / 11
```powershell
git clone https://github.com/uditya22-flux/muse_wave.git
cd muse_wave
.\install_windows.bat
```

---

## 2. Repository Structure & Branching Strategy

| Branch | Purpose |
| :--- | :--- |
| `main` | Full multimodal daemon (Voice + Hand Gestures + Spicetify Bridge + MPRIS2/Win32) |
| `gesture` | Hand-gesture classifier & computer vision pipeline |
| `voice` | Bilingual ASR (`en-IN` + `ml-IN`) & audio stream pipeline |

### Core Modules
- `main.py` — Daemon entry point, camera lifecycle state machine, and HUD compositor.
- `voice_controller.py` — Low-latency 16 kHz PCM capture (`arecord` on Linux, `sounddevice` on Windows) + parallel speech recognition.
- `gesture_detector.py` — 21-landmark MediaPipe Hand Landmarker + rotation-invariant k-NN geometric classifier.
- `gesture_trainer.py` — Interactive sample capture and vector normalization utility for `gesture_config.json`.
- `spotify_controller.py` — Cross-platform media dispatch (MPRIS2 D-Bus, PipeWire/ALSA, Win32 Virtual-Key codes, and local Spicetify HTTP bridge on `127.0.0.1:19745`).

---

## 3. How to Contribute

1. **Fork the repository** and create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Follow Privacy & Security Rules**:
   - Never commit `.env` files, API keys, local logs (`*.log`), or personal playlists (`liked_songs.txt`).
   - Keep the webcam hardware OFF by default (`Voice-First Mode`) unless explicitly toggled by the user.
   - Ensure any changes in `spotify_controller.py` or `voice_controller.py` degrade gracefully across both Linux and Windows (`sys.platform == "win32"`).
3. **Verify Syntax & Imports**:
   ```bash
   python3 -m py_compile main.py voice_controller.py gesture_detector.py gesture_trainer.py spotify_controller.py
   ```
4. **Open a Pull Request** against `main` with a clear description of the changes and platform tested.

---

## 4. Adding New Voice Languages or Commands

To add new voice commands or regional languages:
1. Edit `_VOICE_PATTERNS` in `voice_controller.py`.
2. Add the target BCP-47 language code to `_transcribe_async()` in `voice_controller.py`.
3. Document the new phrase mappings in `README.md`.

## 5. License

By contributing to Musewave, you agree that your contributions will be licensed under the [MIT License](LICENSE).
