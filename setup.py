from setuptools import setup

setup(
    name="musewave",
    version="2.0.0",
    py_modules=[
        "main",
        "voice_controller",
        "gesture_detector",
        "gesture_trainer",
        "spotify_controller",
    ],
    data_files=[
        ("musewave", ["gesture_config.json"]),
        ("musewave/spicetify_extension", ["spicetify_extension/musewave.js"]),
    ],
)
