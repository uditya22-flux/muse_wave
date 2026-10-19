<div align="center">

```text
███╗   ███╗██╗   ██╗███████╗███████╗██╗    ██╗ █████╗ ██╗   ██╗███████╗
████╗ ████║██║   ██║██╔════╝██╔════╝██║    ██║██╔══██╗██║   ██║██╔════╝
██╔████╔██║██║   ██║███████╗█████╗  ██║ █╗ ██║███████║██║   ██║█████╗  
██║╚██╔╝██║██║   ██║╚════██║██╔══╝  ██║███╗██║██╔══██║╚██╗ ██╔╝██╔══╝  
██║ ╚═╝ ██║╚██████╔╝███████║███████╗╚███╔███╔╝██║  ██║ ╚████╔╝ ███████╗
╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝  ╚═══╝  ╚══════╝
                        [ v2.0 // VOICE + GESTURE + SPICETIFY ]
```

**Zero-Touch Media Control for Linux & Desktop — Powered by Bilingual Voice (English + മലയാളം), 3D Hand-Landmark Geometry, and Spicetify.**  
*No Spotify Web API keys. No Premium subscription required. Privacy-first (Webcam OFF by default).*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Linux](https://img.shields.io/badge/Linux-Ubuntu%20%7C%20PipeWire%20%7C%20MPRIS2-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://kernel.org)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Hands%203D-00C7B7?style=for-the-badge&logo=google&logoColor=white)](https://mediapipe.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-Real--Time%20CV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)
[![Spicetify](https://img.shields.io/badge/Spicetify-Native%20Bridge-1DB954?style=for-the-badge&logo=spotify&logoColor=white)](https://spicetify.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

</div>

---

```bash
$ musewave --status
[✓] audio.vad        :: ALSA/PipeWire 16kHz PCM stream active (ambient noise floor calibrated)
[✓] speech.engine    :: Parallel ASR threads ready [en-IN + ml-IN (മലയാളം / Manglish)]
[✓] privacy.guard    :: Webcam hardware RELEASED (LED OFF — say "camera on" to enable CV)
[✓] gesture.engine   :: 90-D curl-weighted cosine matcher + rotation-invariant 2-finger solver
[✓] spicetify.bridge :: HTTP IPC daemon listening on 127.0.0.1:19745
[✓] mpris.router     :: Auto-targeting active player (Spotify / YouTube / Browser / VLC)
> awaiting voice or gesture input_
```

---

## ⚡ Why Musewave?

Spotify locked playback Web APIs behind Premium, and leaving a webcam running 24/7 just to skip a track feels intrusive. **Musewave v2.0** solves both:

1. **🎙️ Privacy-First Bilingual Voice Control (Webcam OFF by Default)**  
   Starts in pure voice mode so your webcam light stays **completely off**. Speak naturally in **English**, **Malayalam (`മലയാളം`)**, or **Manglish** to play, pause, skip, adjust volume, or save tracks.
2. **🖐️ On-Demand 3D Hand Gesture Engine**  
   Say `"camera on"` (or `"ക്യാമറ ഓൺ"`) whenever you want touchless hand gestures, and `"camera off"` (`"ക്യാമറ ഓഫ്"`) to immediately release `/dev/video0` and shut off the camera LED.
3. **💚 Native Spicetify Injection (`musewave.js`)**  
   Includes a custom Spicetify extension that bridges Python directly into Spotify's internal `Spicetify.Player` & `LibraryAPI` — allowing you to **genuinely Heart / Save songs to your Spotify "Liked Songs"** and see live in-app toast notifications without a developer API key.
4. **🌐 Universal MPRIS2 Media Routing**  
   Automatically detects and controls whichever media source is actively playing — **Spotify Desktop**, **YouTube** (Brave / Chrome / Firefox), or **VLC** — via `playerctl`, D-Bus MPRIS2, and PipeWire (`wpctl`).

---

## 🌿 Repository Branches

This repository is organized into three dedicated branches so you can pull the exact stack you want:

| Branch | Focus | Description |
| :--- | :--- | :--- |
| **`main`** *(default)* | **Full Hybrid Stack** | Complete **Voice (English + Malayalam) + Hand Gestures + Spicetify Bridge** with dynamic `"camera on"` / `"camera off"` switching |
| **`voice`** | **Voice-First Stack** | Focused on low-CPU continuous voice activation (`en-IN` + `ml-IN`) with hardware webcam disabled by default |
| **`gesture`** | **Computer Vision Stack** | Focused on MediaPipe 3D hand-landmark recognition, custom gesture training (`gesture_trainer.py`), and `gesture_config.json` profiles |

```bash
# Clone a specific branch:
git clone -b main https://github.com/uditya22-flux/spotify__.git     # Hybrid (Voice + Gesture)
git clone -b voice https://github.com/uditya22-flux/spotify__.git    # Voice-focused
git clone -b gesture https://github.com/uditya22-flux/spotify__.git  # Gesture-focused
```

---

## 🏗️ System Architecture

```text
                    ┌──────────────────────────────────────────────┐
                    │           MUSEWAVE CORE (main.py)            │
                    └───────┬──────────────────────────────┬───────┘
                            │                              │
        [Always Active]     ▼                              ▼    [On-Demand: "camera on"]
┌───────────────────────────────────────┐      ┌───────────────────────────────────────┐
│     VOICE ENGINE (voice_controller)   │      │    VISION ENGINE (gesture_detector)   │
├───────────────────────────────────────┤      ├───────────────────────────────────────┤
│ • PipeWire / ALSA 16kHz PCM Stream    │      │ • MediaPipe 21×3D Hand Landmarks      │
│ • Adaptive RMS Voice Activity (VAD)   │      │ • 63-D Wrist-Centred + Scale Norm     │
│ • Parallel Dual-ASR: en-IN + ml-IN    │      │ • +27-D (2.5×) Finger-Curl Vectors    │
│ • English + മലയാളം + Manglish Lexicon │      │ • Rotation-Invariant Geometric Rules  │
└───────────────────┬───────────────────┘      └───────────────────┬───────────────────┘
                    └──────────────────────┬───────────────────────┘
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │      MEDIA ROUTER (spotify_controller.py)    │
                    └───────┬──────────────────────────────┬───────┘
                            │                              │
                            ▼                              ▼
        ┌──────────────────────────────────────┐ ┌─────────────────────────────────────┐
        │   LINUX MPRIS2 + PIPEWIRE AUDIO      │ │  SPICETIFY IPC BRIDGE (:19745/poll) │
        ├──────────────────────────────────────┤ ├─────────────────────────────────────┤
        │ • playerctl (Spotify / YouTube)      │ │ • musewave.js Extension             │
        │ • Direct D-Bus MPRIS2 Fallback       │ │ • Spicetify.Player.toggleHeart()    │
        │ • wpctl / amixer Audio Sink Control  │ │ • Native In-App Toast Notifications │
        └──────────────────────────────────────┘ └─────────────────────────────────────┘
```

---

## 🎙️ Voice Commands (English + മലയാളം / Manglish)

Both **`en-IN`** and **`ml-IN`** speech recognizers run concurrently on every detected voice segment — mix English and Malayalam seamlessly without changing any settings:

| Action | Malayalam (`മലയാളം`) | Manglish / Phonetic | English Commands |
| :--- | :--- | :--- | :--- |
| **⏯️ Play / Pause** | `"പാട്ട് വെക്കൂ"`, `"പാടൂ"`, `"നിർത്തൂ"`, `"മതി"`, `"നില്ല്"` | `pattu vekku`, `padu`, `nirthu`, `mathi`, `nillu` | `"play"`, `"pause"`, `"stop"`, `"resume"` |
| **⏭️ Next Track** | `"അടുത്ത പാട്ട്"`, `"അടുത്തത്"`, `"മാറ്റൂ"`, `"വേറെ പാട്ട്"` | `adutha pattu`, `aduthathu`, `maattu`, `vere pattu` | `"next"`, `"skip"`, `"next song"`, `"forward"` |
| **⏮️ Previous Track** | `"മുമ്പത്തെ പാട്ട്"`, `"കഴിഞ്ഞ പാട്ട്"`, `"പിന്നോട്ട്"` | `mumbathe pattu`, `kazhinja pattu`, `pinnottu` | `"previous"`, `"back"`, `"go back"`, `"last song"` |
| **🔊 Volume Up** | `"ശബ്ദം കൂട്ടൂ"`, `"സൗണ്ട് കൂട്ടൂ"`, `"കൂട്ടൂ"`, `"ഒച്ച കൂട്ടൂ"` | `shabdham koottu`, `sound koottu`, `koottu` | `"volume up"`, `"louder"`, `"increase volume"` |
| **🔉 Volume Down** | `"ശബ്ദം കുറയ്ക്കൂ"`, `"സൗണ്ട് കുറയ്ക്കൂ"`, `"കുറയ്ക്കൂ"`, `"പതുക്കെ"` | `shabdham kurakku`, `kurakku`, `pathukke` | `"volume down"`, `"quieter"`, `"lower volume"` |
| **❤️ Like / Save** | `"ഇഷ്ടമായി"`, `"ഇഷ്ടപ്പെട്ടു"`, `"നല്ല പാട്ട്"`, `"പൊളി പാട്ട്"` | `ishtamayi`, `ishtapettu`, `nalla pattu`, `poli pattu` | `"save"`, `"like"`, `"save song"`, `"like song"` |
| **📷 Camera ON** | `"ക്യാമറ ഓൺ"`, `"ക്യാമറ തുറക്കൂ"` | `camera on`, `camera thurakku` | `"camera on"`, `"turn on camera"`, `"gestures on"` |
| **🔒 Camera OFF** | `"ക്യാമറ ഓഫ്"`, `"ക്യാമറ നിർത്തൂ"`, `"ക്യാമറ അടക്കൂ"` | `camera off`, `camera nirthu`, `camera adakku` | `"camera off"`, `"turn off camera"`, `"gestures off"` |

---

## 🖐️ Hand Gesture Mappings

When camera mode is enabled (via `"camera on"` or `./venv/bin/python main.py --show`), Musewave recognizes both your custom-trained poses in `gesture_config.json` and rotation-invariant geometric poses:

| Gesture | Hand Pose | Mapped Action | Recognition Method |
| :--- | :--- | :--- | :--- |
| **✊ Fist (`pause`)** | All fingers curled into palm | **Play / Pause** | 90-D Cosine Similarity |
| **✌️ 2 Fingers Right (`next`)** | Index + Middle extended, tilted right | **Next Track** | Rotation-Invariant Vector + Cosine |
| **✌️ 2 Fingers Left (`prev`)** | Index + Middle extended, tilted left | **Previous Track** | Rotation-Invariant Vector + Cosine |
| **🖐️ Back of Palm (`volume up`)** | All 5 fingers open / spread | **Volume Up (`+10%`)** | 90-D Cosine Similarity |
| **☝️ 1 Index Finger (`volume down`)** | Single index finger pointing up | **Volume Down (`-10%`)** | Geometric Curl Rule + Cosine |
| **👍 / 🫰 Thumb Up or Korean Heart** | Thumb extended **or** Thumb+Index crossed | **Like / Save Song** | 90-D Cosine + Built-in Hold Detector |

---

## 🔬 Under The Hood: 90-D Feature Engineering

Standard 63-D MediaPipe landmark vectors struggle when the wrist rotates slightly in 3D space. Musewave enhances raw landmarks with **2.5× weighted finger-curl vectors** (`MCP → TIP` and `PIP → TIP`) plus rotation-invariant vector dot-products:

```python
def _to_feature(vec: np.ndarray) -> np.ndarray:
    """Enhance 63-d wrist-normalised landmarks with 27-d finger-curl vectors (90-d total)."""
    pts = np.asarray(vec, dtype=float).reshape(21, 3)
    fingers = np.concatenate([
        pts[4] - pts[2],   pts[8] - pts[5],   pts[12] - pts[9],  pts[16] - pts[13], pts[20] - pts[17],
        pts[8] - pts[6],   pts[12] - pts[10], pts[16] - pts[14], pts[20] - pts[18],
    ])
    return np.concatenate([pts.flatten(), fingers * 2.5])
```

And for 2-finger directional gestures (`next` vs `prev`), extension is verified independent of camera rotation using collinearity between `MCP → PIP` ($\vec{v}_1$) and `PIP → TIP` ($\vec{v}_2$):

$$\cos\theta = \frac{\vec{v}_1 \cdot \vec{v}_2}{\|\vec{v}_1\| \|\vec{v}_2\|} > 0.50 \quad \land \quad \|\text{TIP} - \text{WRIST}\| > \|\text{PIP} - \text{WRIST}\| + 0.15$$

---

## 🚀 Quickstart

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/uditya22-flux/spotify__.git
cd spotify__

python3 -m venv venv
./venv/bin/pip install opencv-python mediapipe numpy SpeechRecognition python-dotenv
```

### 2. Install System Media Tools (Ubuntu / Debian)
```bash
sudo apt install playerctl alsa-utils libnotify-bin
```

### 3. Run Musewave
```bash
# Default: Voice-First Mode (Webcam OFF — English + Malayalam active)
./venv/bin/python main.py

# Voice + Live Camera HUD Overlay
./venv/bin/python main.py --show

# Train or Customize Hand Gestures
./venv/bin/python gesture_trainer.py
```

### 4. Optional: Enable Spicetify In-App Integration
```bash
bash setup_spicetify.sh
```
This installs [`spicetify_extension/musewave.js`](spicetify_extension/musewave.js) into Spicetify, adding a top-bar status indicator inside Spotify and enabling native one-gesture/one-voice **Liked Songs** saving.

---

## 📂 Project Structure

```text
spotify__/
├── main.py                        # Core event loop (Voice-First + dynamic Webcam state machine)
├── voice_controller.py            # ALSA/PipeWire VAD + parallel en-IN / ml-IN speech engine
├── gesture_detector.py            # 90-D feature extractor, geometric rules & cosine classifier
├── gesture_trainer.py             # Interactive OpenCV HUD for recording custom hand gestures
├── spotify_controller.py          # MPRIS2 (Spotify/YouTube) router, PipeWire volume & Spicetify IPC server
├── gesture_config.json            # Trained 3D hand landmark samples
├── spicetify_extension/
│   └── musewave.js                # Spicetify extension for native Spotify Liked Songs & toasts
├── setup_spicetify.sh             # Zero-sudo Spicetify workspace patcher
├── launch_with_spotify.sh         # Auto-starts Musewave when Spotify opens & stops when it closes
├── spotify.desktop                # Desktop launcher entry for seamless background startup
└── LICENSE                        # MIT License
```

---

## 📜 License

Released under the **[MIT License](LICENSE)** — Copyright © 2026 **Uditya Krishna**.

<div align="center">

**Built with MediaPipe · OpenCV · SpeechRecognition · PipeWire · Spicetify**  
**[⭐ Star this repo on GitHub](https://github.com/uditya22-flux/spotify__)**

</div>
