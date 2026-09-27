"""
voice_controller.py
-------------------
Listens for voice commands in a background thread.
Uses Google Speech Recognition (needs internet).
Uses sounddevice instead of pyaudio — works on Python 3.14+

Supported commands:
  "next"         → Next Track
  "previous"     → Previous Track  
  "like"         → Like / Save Song
  "volume up"    → Volume Up
  "volume down"  → Volume Down

Usage:
  vc = VoiceController(callback=my_function)
  vc.start()   # starts listening in background
  vc.stop()    # stops listening
"""

import threading
import queue
import logging
import numpy as np
import sounddevice as sd
import speech_recognition as sr

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────
SAMPLE_RATE   = 16000
CHANNELS      = 1
CHUNK_SECONDS = 3       # listen in 3-second chunks
LANGUAGE      = "en-IN" # Indian English — change to "en-US" if needed

# Keywords to listen for → action string
COMMANDS = {
    "next"        : "Next Track",
    "skip"        : "Next Track",
    "previous"    : "Previous Track",
    "back"        : "Previous Track",
    "like"        : "Like / Save Song",
    "save"        : "Like / Save Song",
    "heart"       : "Like / Save Song",
    "volume up"   : "Volume Up",
    "louder"      : "Volume Up",
    "volume down" : "Volume Down",
    "quieter"     : "Volume Down",
    "pause"       : "Play / Pause",
}
# ─────────────────────────────────────────────────────────────────


class VoiceController:
    def __init__(self, callback):
        """
        callback: function(action_string) called when a command is recognised
        e.g. callback("Next Track")
        """
        self.callback   = callback
        self._running   = False
        self._thread    = None
        self._recogniser = sr.Recognizer()
        self._recogniser.energy_threshold = 300
        self._recogniser.dynamic_energy_threshold = True

    def start(self):
        """Start listening in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Voice controller started — listening for commands")

    def stop(self):
        """Stop listening."""
        self._running = False
        logger.info("Voice controller stopped")

    def _record_chunk(self) -> np.ndarray:
        """Record one chunk of audio from the microphone."""
        frames = int(SAMPLE_RATE * CHUNK_SECONDS)
        audio  = sd.rec(frames, samplerate=SAMPLE_RATE,
                        channels=CHANNELS, dtype='int16')
        sd.wait()
        return audio.flatten()

    def _numpy_to_audio_data(self, audio_np: np.ndarray) -> sr.AudioData:
        """Convert numpy array to SpeechRecognition AudioData."""
        raw_bytes = audio_np.tobytes()
        return sr.AudioData(raw_bytes, SAMPLE_RATE, 2)  # 2 bytes per sample (int16)

    def _parse_command(self, text: str):
        """Check if recognised text contains a known command."""
        text = text.lower().strip()
        logger.info("Heard: '%s'", text)

        for keyword, action in COMMANDS.items():
            if keyword in text:
                return action
        return None

    def _listen_loop(self):
        """Main listening loop — runs in background thread."""
        logger.info("Microphone listening started")
        while self._running:
            try:
                audio_np   = self._record_chunk()
                audio_data = self._numpy_to_audio_data(audio_np)

                text = self._recogniser.recognize_google(
                    audio_data,
                    language=LANGUAGE
                )

                action = self._parse_command(text)
                if action:
                    logger.info("Voice command recognised: %s -> %s", text, action)
                    self.callback(action)

            except sr.UnknownValueError:
                pass   # silence or unclear audio — ignore
            except sr.RequestError as e:
                logger.error("Google Speech API error: %s", e)
            except Exception as e:
                logger.error("Voice controller error: %s", e)
