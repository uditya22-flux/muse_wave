# Security & Privacy Policy

## Supported Versions

| Version | Supported | Platforms |
| :--- | :--- | :--- |
| `2.0.x` | Yes | Ubuntu/Debian Linux, Windows 10/11 |
| `< 2.0` | No | Legacy |

---

## Hardware & Data Privacy Architecture

Musewave is engineered with a strict local-first security and hardware-privacy model:

1. **Zero Unsolicited Camera Access (Voice-First Mode)**:
   - On startup, `cv2.VideoCapture` is not initialized (`cap = None`), ensuring the physical webcam indicator LED remains OFF.
   - The camera device `/dev/video0` (or Windows DirectShow device `0`) is only opened when the user explicitly issues the `"camera on"` voice command, and is immediately released (`cap.release()`) upon `"camera off"`.
2. **No Biometric Image Storage**:
   - Hand-gesture training (`gesture_trainer.py`) stores only 63 normalized floating-point coordinates (21 landmarks $\times$ $(x, y, z)$ relative to the wrist origin) in `gesture_config.json`.
   - Zero raw video frames or images are ever written to disk or transmitted over the network.
3. **Loopback-Only Spicetify Bridge**:
   - The embedded HTTP/WebSocket bridge in `spotify_controller.py` binds strictly to `127.0.0.1:19745` (localhost loopback) and cannot be accessed from external network interfaces.
4. **Zero Stored Credentials**:
   - Media control operates via OS-level MPRIS2 D-Bus (`playerctl`), Win32 Virtual-Key events, and the local Spicetify client—requiring zero Spotify Web API OAuth secrets.

---

## Reporting a Vulnerability

If you discover a security or privacy vulnerability in Musewave:

1. **Do not open a public exploit payload** in a public issue if it puts end users at risk.
2. Open a security advisory on GitHub at:
   `https://github.com/uditya22-flux/muse_wave/security/advisories/new`
   or report it directly via `@uditya22-flux` on GitHub.
3. Include:
   - Operating System (Ubuntu/Debian version or Windows 10/11 build)
   - Steps to reproduce the issue
   - Potential impact and suggested fix (if available)
