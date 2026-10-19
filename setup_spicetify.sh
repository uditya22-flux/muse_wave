#!/usr/bin/env bash
set -e

PROJECT_DIR="/home/uditya/uditya windows/project/musewave/spotify__"
APP_DIR="$PROJECT_DIR/.spotify_spicetify"
SPICETIFY_CFG="/home/uditya/.config/spicetify"
SPICETIFY_BIN="/home/uditya/.spicetify/spicetify"

if ! [ -x "$SPICETIFY_BIN" ]; then
    SPICETIFY_BIN="$(which spicetify 2>/dev/null || true)"
fi

# 1. Ensure writable Spotify directory exists
mkdir -p "$APP_DIR/Apps"
for item in /usr/share/spotify/*; do
    base=$(basename "$item")
    if [ "$base" = "Apps" ]; then
        if [ ! -f "$APP_DIR/Apps/xpui.spa" ] && [ ! -d "$APP_DIR/Apps/xpui" ]; then
            cp -f /usr/share/spotify/Apps/* "$APP_DIR/Apps/"
            chmod -R u+w "$APP_DIR/Apps"
        fi
    elif [ "$base" = "spotify" ]; then
        if [ ! -f "$APP_DIR/spotify" ]; then
            cp -f /usr/share/spotify/spotify "$APP_DIR/spotify"
            chmod u+rwx "$APP_DIR/spotify"
        fi
    else
        ln -sfn "$item" "$APP_DIR/$base"
    fi
done

# 2. Install Musewave Spicetify Extension
mkdir -p "$SPICETIFY_CFG/Extensions"
cp -f "$PROJECT_DIR/spicetify_extension/musewave.js" "$SPICETIFY_CFG/Extensions/musewave.js"

# 3. Point Spicetify config-xpui.ini to writable Spotify dir & enable musewave.js
if [ -f "$SPICETIFY_CFG/config-xpui.ini" ]; then
    "$PROJECT_DIR/venv/bin/python" -c '
import configparser, pathlib
p = pathlib.Path("/home/uditya/.config/spicetify/config-xpui.ini")
text = p.read_text()
lines = []
for line in text.splitlines():
    if line.strip().startswith("spotify_path"):
        lines.append("spotify_path           = /home/uditya/uditya windows/project/musewave/spotify__/.spotify_spicetify")
    elif line.strip().startswith("extensions"):
        if "musewave.js" not in line:
            val = line.split("=", 1)[1].strip()
            new_val = f"{val}|musewave.js" if val else "musewave.js"
            lines.append(f"extensions            = {new_val}")
        else:
            lines.append(line)
    else:
        lines.append(line)
p.write_text("\n".join(lines) + "\n")
'
fi

# 4. Apply Spicetify (backup if needed, then apply)
if [ -n "$SPICETIFY_BIN" ] && [ -x "$SPICETIFY_BIN" ]; then
    "$SPICETIFY_BIN" apply || "$SPICETIFY_BIN" backup apply
    echo "Spicetify + Musewave extension applied successfully!"
else
    echo "Warning: spicetify binary not found at $SPICETIFY_BIN"
fi
