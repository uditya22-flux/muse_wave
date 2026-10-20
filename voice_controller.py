"""
voice_controller.py — Real-Time Voice Command Controller (English + Malayalam)
==============================================================================
Listens for voice commands in English, Malayalam (മലയാളം), and Manglish
using ALSA/PipeWire (`arecord`) + SpeechRecognition (`en-IN` and `ml-IN`)
so the webcam stays completely OFF by default for hardware privacy and safety.

Supported Voice Commands (English & Malayalam):
  - Play / Pause:
      "play", "pause", "stop", "resume"
      "പാട്ട് വെക്കൂ" (pattu vekku), "പാടൂ" (padu), "നിർത്തൂ" (nirthu), "മതി" (mathi)
  - Next Track:
      "next", "skip", "next song", "forward"
      "അടുത്തത്" (aduthathu), "അടുത്ത പാട്ട്" (adutha pattu), "മാറ്റൂ" (maattu), "വേറെ പാട്ട്" (vere pattu)
  - Previous Track:
      "previous", "back", "go back", "last song"
      "മുമ്പത്തെ പാട്ട്" (mumbathe pattu), "കഴിഞ്ഞ പാട്ട്" (kazhinja pattu), "പിന്നോട്ട്" (pinnottu)
  - Volume Up:
      "volume up", "louder", "increase volume"
      "ശബ്ദം കൂട്ടൂ" (shabdham koottu), "സൗണ്ട് കൂട്ടൂ" (sound koottu), "കൂട്ടൂ" (koottu), "ഒച്ച കൂട്ടൂ" (ocha koottu)
  - Volume Down:
      "volume down", "quieter", "lower volume"
      "ശബ്ദം കുറയ്ക്കൂ" (shabdham kurakku), "സൗണ്ട് കുറയ്ക്കൂ" (sound kurakku), "കുറയ്ക്കൂ" (kurakku), "പതുക്കെ" (pathukke)
  - Like / Save Song:
      "save", "like", "save song", "like song"
      "ഇഷ്ടമായി" (ishtamayi), "ഇഷ്ടപ്പെട്ടു" (ishtapettu), "സേവ് ചെയ്യൂ" (save cheyyu), "നല്ല പാട്ട്" (nalla pattu), "പൊളി പാട്ട്" (poli pattu)
  - Camera ON / OFF:
      "camera on", "gestures on", "ക്യാമറ ഓൺ", "ക്യാമറ തുറക്കൂ" (camera thurakku)
      "camera off", "gestures off", "ക്യാമറ ഓഫ്", "ക്യാമറ നിർത്തൂ" (camera nirthu)
"""

import subprocess
import threading
import time
import logging
import numpy as np

logger = logging.getLogger("voice_controller")

try:
    import speech_recognition as sr
    SR_OK = True
except ImportError:
    SR_OK = False
    logger.error("SpeechRecognition not found. Run: pip install SpeechRecognition")

SAMPLE_RATE = 16000
CHUNK_SEC   = 0.10
CHUNK_BYTES = int(SAMPLE_RATE * CHUNK_SEC * 2)  # 16-bit mono = 2 bytes/sample


def _pick_capture_device() -> str:
    """Find a working ALSA/PipeWire capture device for arecord."""
    candidates = ["default", "plughw:0,7", "plughw:0,6", "plughw:0,0"]
    for dev in candidates:
        try:
            p = subprocess.run(
                [
                    "arecord", "-D", dev,
                    "-f", "S16_LE", "-r", str(SAMPLE_RATE),
                    "-c", "1", "-d", "1", "-t", "raw", "-q", "-"
                ],
                capture_output=True,
                timeout=2.5,
            )
            if p.returncode == 0 and len(p.stdout) >= SAMPLE_RATE:
                arr = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(arr ** 2)))
                if rms > 1.0:
                    logger.info("VoiceController using microphone device '%s' (ambient rms=%.1f)", dev, rms)
                    return dev
        except Exception:
            continue
    return "default"


def _match_voice_command(text: str):
    """
    Map recognized speech text (English, Malayalam script, or Manglish) to an action:
      'camera_on', 'camera_off', 'Play / Pause', 'Next Track',
      'Previous Track', 'Volume Up', 'Volume Down', 'Like / Save Song', or None.
    """
    t = text.lower().strip()
    if not t:
        return None
    words = t.split()

    # ── 1. Camera / Gesture toggle commands (English + Malayalam) ────
    cam_on_phrases = (
        "camera on", "turn on camera", "start camera", "enable camera", "gestures on", "gesture on",
        "ക്യാമറ ഓൺ", "ക്യാമറ തുറക്ക", "ക്യാമറ വെക്ക", "camera thurakk", "camera vekk",
    )
    if any(p in t for p in cam_on_phrases):
        return "camera_on"

    cam_off_phrases = (
        "camera off", "turn off camera", "stop camera", "disable camera", "gestures off", "gesture off",
        "ക്യാമറ ഓഫ്", "ക്യാമറ നിർത്ത", "ക്യാമറ അടക്ക", "camera nirth", "camera adakk",
    )
    if any(p in t for p in cam_off_phrases):
        return "camera_off"

    # ── 2. Like / Save song (English + Malayalam) ────────────────────
    save_phrases = (
        "save song", "like song", "save this", "like this", "add to liked", "favorite", "favourite",
        "ഇഷ്ടമായി", "ഇഷ്ടപ്പെട്ടു", "സേവ്", "ലൈക്ക്", "സൂക്ഷിക്ക", "നല്ല പാട്ട്", "പൊളി പാട്ട്", "സൂപ്പർ പാട്ട്",
        "ishtamayi", "ishtapettu", "ishtaayi", "save cheyy", "like cheyy", "nalla pattu", "nalla paattu",
        "poli pattu", "poli paattu", "super pattu",
    )
    if any(p in t for p in save_phrases) or t in ("save", "like", "heart", "ishtam", "ഇഷ്ടം"):
        return "Like / Save Song"

    # ── 3. Next track (English + Malayalam) ──────────────────────────
    next_phrases = (
        "next song", "next track", "skip song", "skip track", "play next",
        "അടുത്ത", "വേറെ പാട്ട്", "പാട്ട് മാറ്റ", "മാറ്റുക", "മാറ്റു", "മാറ്റൂ", "മുന്നോട്ട്", "നെക്സ്റ്റ്", "സ്കിപ്പ്",
        "adutha", "aduthathu", "aduthath", "vere pattu", "vere paattu",
        "pattu matt", "paattu maatt", "maattu", "mattu", "maatuka", "munnottu",
    )
    if any(p in t for p in next_phrases) or any(w in words for w in ("next", "skip", "forward")):
        return "Next Track"

    # ── 4. Previous track (English + Malayalam) ──────────────────────
    prev_phrases = (
        "previous song", "previous track", "last song", "go back", "play previous",
        "മുമ്പത്തെ", "മുൻപത്തെ", "കഴിഞ്ഞ പാട്ട്", "പിന്നോട്ട്", "പഴയ പാട്ട്", "ആദ്യത്തെ പാട്ട്", "തിരിച്ചു", "തിരിച്ച്", "പ്രീവിയസ്", "ബാക്ക്",
        "mumbathe", "munpathe", "kazhinja pattu", "kazhinja paattu", "pinnottu", "pazhaya pattu", "thirichu",
    )
    if any(p in t for p in prev_phrases) or any(w in words for w in ("previous", "prev", "back", "replay")):
        return "Previous Track"

    # ── 5. Volume Up (English + Malayalam) ───────────────────────────
    vol_up_phrases = (
        "volume up", "turn it up", "increase volume", "sound up", "louder", "volume high", "volume higher",
        "ശബ്ദം കൂട്ട", "സൗണ്ട് കൂട്ട", "ഒച്ച കൂട്ട", "വോളിയം കൂട്ട", "വോളിയം അപ്പ്", "കൂട്ടുക", "കൂട്ടു", "കൂട്ടൂ",
        "shabdham koott", "shabdam koot", "sound koott", "sound koot", "ocha koott", "ocha koot",
        "volume koott", "volume koot", "koottu", "kootu", "koottuka", "kootuka",
    )
    if any(p in t for p in vol_up_phrases) or t in ("up", "higher"):
        return "Volume Up"

    # 6. Volume Down (English + Malayalam)
    vol_down_phrases = (
        "volume down", "turn it down", "decrease volume", "lower volume", "sound down", "quieter", "softer", "volume low", "volume lower",
        "ശബ്ദം കുറ", "സൗണ്ട് കുറ", "ഒച്ച കുറ", "വോളിയം കുറ", "വോളിയം ഡൗൺ", "കുറയ്ക്ക", "കുറച്ചു", "കുറച്ച്", "പതുക്കെ",
        "shabdham kurakk", "shabdam kurakk", "sound kurakk", "ocha kurakk", "volume kurakk",
        "kurakku", "kurakkuka", "kurachu", "pathukke",
    )
    if any(p in t for p in vol_down_phrases) or t in ("down", "lower"):
        return "Volume Down"

    # ── 7. Play / Pause (English + Malayalam) ────────────────────────
    play_pause_phrases = (
        "play pause", "pause music", "play music", "stop music", "resume music", "pause song", "play song",
        "നിർത്തുക", "നിർത്തു", "നിർത്തൂ", "നില്ല്", "മതി",
        "പാടുക", "പാടു", "പാടൂ", "പാട്ട് വെക്ക", "പാട്ട് ഇട", "തുടങ്ങുക", "തുടങ്ങൂ", "പ്ലേ", "പോസ്", "സ്റ്റോപ്പ്",
        "nirthu", "nirthuka", "nillu", "mathi", "padu", "paadu", "paduka",
        "pattu vekk", "paattu vekk", "pattu idu", "paattu idu", "thudangu", "thudanguka",
    )
    if any(p in t for p in play_pause_phrases) or any(w in words for w in ("play", "pause", "stop", "resume")):
        return "Play / Pause"

    return None


class VoiceController:
    """
    Background voice command listener (English + Malayalam) that triggers
    on_command(action_name, spoken_text) whenever a command is spoken.
    """

    def __init__(self, on_command):
        self.on_command  = on_command
        self._running    = False
        self._thread     = None
        self._recognizer = sr.Recognizer() if SR_OK else None
        self._last_cmd_t = 0.0

    def start(self):
        if not SR_OK:
            logger.error("Cannot start VoiceController: SpeechRecognition missing.")
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("VoiceController started (English + Malayalam; camera OFF by default).")

    def stop(self):
        self._running = False

    def _transcribe_async(self, pcm_bytes: bytes):
        def _worker():
            audio = sr.AudioData(pcm_bytes, SAMPLE_RATE, 2)
            results = {}

            def _rec(lang):
                try:
                    txt = self._recognizer.recognize_google(audio, language=lang)
                    if txt:
                        results[lang] = txt.strip()
                except Exception:
                    pass

            # Run English (India) and Malayalam (India) recognition in parallel
            t_en = threading.Thread(target=_rec, args=("en-IN",), daemon=True)
            t_ml = threading.Thread(target=_rec, args=("ml-IN",), daemon=True)
            t_en.start()
            t_ml.start()
            t_en.join(timeout=4.0)
            t_ml.join(timeout=4.0)

            if not results:
                return

            # Check both transcripts (en-IN and ml-IN) for a matching command
            for lang in ("en-IN", "ml-IN"):
                txt = results.get(lang, "")
                if not txt:
                    continue
                action = _match_voice_command(txt)
                logger.info("Heard voice [%s]: %r -> action=%r", lang, txt, action)
                if action and self.on_command:
                    now = time.time()
                    if now - self._last_cmd_t >= 0.8:
                        self._last_cmd_t = now
                        self.on_command(action, txt)
                    return

        threading.Thread(target=_worker, daemon=True).start()

    def _listen_loop(self):
        import sys
        if sys.platform == "win32":
            self._listen_loop_windows()
            return
        dev = _pick_capture_device()
        while self._running:
            proc = None
            try:
                proc = subprocess.Popen(
                    [
                        "arecord", "-D", dev,
                        "-f", "S16_LE", "-r", str(SAMPLE_RATE),
                        "-c", "1", "-t", "raw", "-q", "-"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )

                noise_rms      = 120.0
                in_speech      = False
                speech_chunks  = []
                silence_chunks = 0
                pre_roll       = []

                while self._running and proc.poll() is None:
                    raw = proc.stdout.read(CHUNK_BYTES)
                    if not raw or len(raw) < CHUNK_BYTES:
                        break

                    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                    rms     = float(np.sqrt(np.mean(samples ** 2)))

                    threshold = max(noise_rms * 2.0, 220.0)

                    if not in_speech:
                        pre_roll.append(raw)
                        if len(pre_roll) > 3:
                            pre_roll.pop(0)

                        if rms > threshold:
                            in_speech      = True
                            speech_chunks  = list(pre_roll)
                            silence_chunks = 0
                        else:
                            noise_rms = 0.95 * noise_rms + 0.05 * rms
                    else:
                        speech_chunks.append(raw)
                        if rms < threshold * 0.75:
                            silence_chunks += 1
                        else:
                            silence_chunks = 0

                        if silence_chunks >= 5 or len(speech_chunks) >= 35:
                            if len(speech_chunks) >= 6:
                                pcm_data = b"".join(speech_chunks)
                                self._transcribe_async(pcm_data)
                            in_speech      = False
                            speech_chunks  = []
                            silence_chunks = 0

            except Exception as e:
                logger.warning("Voice capture loop error: %s", e)
                time.sleep(1.0)
            finally:
                if proc is not None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=1)
                    except Exception:
                        pass
            if self._running:
                time.sleep(0.5)

    def _listen_loop_windows(self):
        try:
            import sounddevice as sd
        except Exception as e:
            logger.error("sounddevice not available on Windows: %s", e)
            return

        frames_per_chunk = int(SAMPLE_RATE * CHUNK_SEC)
        while self._running:
            try:
                noise_rms      = 120.0
                in_speech      = False
                speech_chunks  = []
                silence_chunks = 0
                pre_roll       = []

                with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=frames_per_chunk, channels=1, dtype="int16") as stream:
                    while self._running:
                        data, _ = stream.read(frames_per_chunk)
                        raw = bytes(data)
                        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                        rms     = float(np.sqrt(np.mean(samples ** 2)))
                        threshold = max(noise_rms * 2.0, 220.0)

                        if not in_speech:
                            pre_roll.append(raw)
                            if len(pre_roll) > 3:
                                pre_roll.pop(0)
                            if rms > threshold:
                                in_speech      = True
                                speech_chunks  = list(pre_roll)
                                silence_chunks = 0
                            else:
                                noise_rms = 0.95 * noise_rms + 0.05 * rms
                        else:
                            speech_chunks.append(raw)
                            if rms < threshold * 0.75:
                                silence_chunks += 1
                            else:
                                silence_chunks = 0
                            if silence_chunks >= 5 or len(speech_chunks) >= 35:
                                if len(speech_chunks) >= 6:
                                    self._transcribe_async(b"".join(speech_chunks))
                                in_speech      = False
                                speech_chunks  = []
                                silence_chunks = 0
            except Exception as e:
                logger.warning("Windows voice capture error: %s", e)
                time.sleep(1.0)

