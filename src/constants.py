from pathlib import Path

SAMPLE_RATE = 48000

MODEL_DIR = Path("models")
DATA_DIR = Path("data")
TEMP_DIR = Path("tmp")

SILERO_SPEAKERS = ["aidar", "baya", "kseniya", "xenia", "eugene"]
TERA_SPEAKERS = ["natasha-g2p-vits"]
VOSK_SPEAKERS = [str(i) for i in range(5)]