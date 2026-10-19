#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  MUSEWAVE v2.0.0 :: UBUNTU / DEBIAN LINUX INSTALLER"
echo "============================================================"

# 1. Install system dependencies
echo "[1/4] Installing system dependencies (playerctl, alsa-utils, libnotify-bin, python3-venv)..."
sudo apt-get update -qq
sudo apt-get install -y playerctl alsa-utils libnotify-bin python3-venv python3-pip

# 2. Setup virtual environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[2/4] Setting up Python virtual environment..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q

# 3. Make scripts executable
echo "[3/4] Configuring launcher scripts..."
chmod +x launch_with_spotify.sh setup_spicetify.sh

# 4. Install desktop entry
echo "[4/4] Creating desktop application shortcut..."
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/musewave.desktop" <<EOF
[Desktop Entry]
Version=2.0.0
Name=Musewave
Comment=Multimodal Voice & Gesture Media Controller
Exec="$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/main.py"
Path=$SCRIPT_DIR
Terminal=true
Type=Application
Categories=AudioVideo;Audio;Utility;
EOF

echo "============================================================"
echo "  INSTALLATION COMPLETE!"
echo "  Run with: ./venv/bin/python main.py"
echo "  Train custom gestures: ./venv/bin/python gesture_trainer.py"
echo "============================================================"
