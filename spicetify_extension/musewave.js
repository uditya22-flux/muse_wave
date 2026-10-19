// NAME: Musewave Gesture Bridge
// AUTHOR: Musewave
// DESCRIPTION: Connects webcam hand gestures to Spicetify (Liked Songs, Playback, Volume & In-App Toasts)

(function MusewaveExtension() {
    if (!Spicetify?.Player || !Spicetify?.showNotification) {
        setTimeout(MusewaveExtension, 300);
        return;
    }

    const BRIDGE_URL = "http://127.0.0.1:19745";
    let connected = false;

    async function likeCurrentTrack() {
        try {
            const data = Spicetify.Player.data || Spicetify.Queue?.track;
            const item = data?.item || data?.track;
            const title = item?.name || item?.metadata?.title || "Current Track";
            const artist = item?.artists?.[0]?.name || item?.metadata?.artist_name || "";
            const uri = item?.uri;

            if (typeof Spicetify.Player.getHeart === "function") {
                if (!Spicetify.Player.getHeart()) {
                    Spicetify.Player.toggleHeart();
                }
            } else if (Spicetify.Platform?.LibraryAPI && uri) {
                await Spicetify.Platform.LibraryAPI.add({ uris: [uri] });
            } else if (typeof Spicetify.Player.toggleHeart === "function") {
                Spicetify.Player.toggleHeart();
            }

            const label = artist ? `${title} — ${artist}` : title;
            Spicetify.showNotification(`❤️ Musewave: Saved "${label}" to Liked Songs`);
        } catch (err) {
            console.error("[Musewave] Error liking track:", err);
            if (typeof Spicetify.Player.toggleHeart === "function") {
                Spicetify.Player.toggleHeart();
            }
            Spicetify.showNotification("❤️ Musewave: Saved to Liked Songs");
        }
    }

    async function handleEvent(evt) {
        if (!evt || !evt.type) return;
        switch (evt.type) {
            case "like_song":
                await likeCurrentTrack();
                break;
            case "vol_up":
                if (typeof Spicetify.Player.increaseVolume === "function") {
                    try { Spicetify.Player.increaseVolume(); } catch (_) {}
                }
                Spicetify.showNotification("🔊 Musewave: Volume Up");
                break;
            case "vol_down":
                if (typeof Spicetify.Player.decreaseVolume === "function") {
                    try { Spicetify.Player.decreaseVolume(); } catch (_) {}
                }
                Spicetify.showNotification("🔉 Musewave: Volume Down");
                break;
            case "notify":
                if (evt.message) {
                    Spicetify.showNotification(evt.message);
                }
                break;
        }
    }

    async function pollBridge() {
        try {
            const trackItem = Spicetify.Player.data?.item;
            const title = trackItem?.name || trackItem?.metadata?.title || "";
            const artist = trackItem?.artists?.[0]?.name || trackItem?.metadata?.artist_name || "";
            const liked = typeof Spicetify.Player.getHeart === "function" ? !!Spicetify.Player.getHeart() : false;

            const q = new URLSearchParams({ title, artist, liked: liked ? "1" : "0" });
            const res = await fetch(`${BRIDGE_URL}/poll?${q.toString()}`, {
                method: "GET",
                cache: "no-store",
            });
            if (res.ok) {
                if (!connected) {
                    connected = true;
                    Spicetify.showNotification("👋 Musewave Gesture Control Connected");
                }
                const data = await res.json();
                if (Array.isArray(data.events)) {
                    for (const evt of data.events) {
                        await handleEvent(evt);
                    }
                }
            }
        } catch (_) {
            connected = false;
        } finally {
            setTimeout(pollBridge, 250);
        }
    }

    try {
        if (Spicetify.Topbar?.Button) {
            new Spicetify.Topbar.Button(
                "Musewave Hand Gestures",
                `<svg role="img" height="16" width="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a1 1 0 0 1 1 1v4.5h1V2.5a1 1 0 1 1 2 0v4h1V4a1 1 0 1 1 2 0v6.5a4.5 4.5 0 0 1-4.5 4.5h-3A4.5 4.5 0 0 1 3 10.5V7a1 1 0 0 1 2 0v2h1V2.5a1 1 0 0 1 2 0V6.5h0V2a1 1 0 0 1 1-1z"/></svg>`,
                () => {
                    Spicetify.showNotification(
                        connected
                            ? "👋 Musewave Active: Fist=Play/Pause | 2F Right/Left=Next/Prev | Palm=Vol+ | Index=Vol- | Thumb/Heart=Like"
                            : "⚠️ Musewave Python controller not detected on port 19745"
                    );
                }
            );
        }
    } catch (_) {}

    pollBridge();
})();
