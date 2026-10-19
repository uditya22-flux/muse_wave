#!/usr/bin/env bash
# Launches Spotify (unless --watch-only is passed) and automatically keeps
# the Musewave Voice + Gesture controller running while Spotify is open,
# and stops it as soon as Spotify closes.

PROJECT_DIR="/home/uditya/uditya windows/project/musewave/spotify__"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
MAIN_PY="$PROJECT_DIR/main.py"

if [ "$1" != "--watch-only" ]; then
    /usr/bin/spotify "$@" >/dev/null 2>&1 &
    sleep 2
fi

# Wait while Spotify is open, then stop Musewave when Spotify closes
while pgrep -x spotify > /dev/null; do
    # Only start main.py if neither main.py nor gesture_trainer.py is running
    if ! pgrep -f "$MAIN_PY" > /dev/null && ! pgrep -f "gesture_trainer.py" > /dev/null; then
        "$PYTHON_BIN" "$MAIN_PY" >> "$PROJECT_DIR/gesture_app.log" 2>&1 &
    fi
    sleep 2
done

pkill -f "$MAIN_PY" 2>/dev/null || true
