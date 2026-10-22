## Summary
Briefly describe the changes introduced in this Pull Request.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (new gesture, voice command, or platform capability)
- [ ] Documentation / Packaging update

## Checklist
- [ ] Tested on Linux (`Ubuntu/Debian`) or Windows (`win32`)
- [ ] Webcam remains OFF by default on startup (Voice-First privacy preserved)
- [ ] No secrets, `.env` files, or `.log` files included in the commit
- [ ] `python3 -m py_compile main.py voice_controller.py gesture_detector.py gesture_trainer.py spotify_controller.py` passes cleanly
