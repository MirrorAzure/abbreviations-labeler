import os
import torch
import logging
import tempfile
import shutil
from pathlib import Path
from TeraTTS import TTS as TeraTTS
from vosk_tts import Model as VoskModel, Synth

from utils import create_dir_if_not_exists

from constants import MODEL_DIR
from torch_setup import get_device

device = get_device()

def silero_init():
    logging.info("Silero model initialized")
    create_dir_if_not_exists(MODEL_DIR / "silero")

    silero_model_file = "models/silero/silero_tts_v4_ru_model.pt"
    if not os.path.isfile(silero_model_file):
        torch.hub.download_url_to_file("https://models.silero.ai/models/tts/ru/v4_ru.pt",
                                        silero_model_file)

    silero_model = torch.package.PackageImporter(silero_model_file).load_pickle("tts_models", "model")
    silero_model.to(device)
    return silero_model

def tera_init():
    create_dir_if_not_exists(MODEL_DIR / "TeraTTS")

    tera_model = TeraTTS(f"TeraTTS/natasha-g2p-vits", add_time_to_end=1.0, tokenizer_load_dict=True, save_path="./models")
    return tera_model

def vosk_init():
    
    create_dir_if_not_exists(MODEL_DIR / "VoskTTS")

    vosk_model_name = "vosk-model-tts-ru-0.7-multi"
    vosk_full_path = Path(f"models/VoskTTS/{vosk_model_name}")

    if not vosk_full_path.exists():
        vosk_model = VoskModel(model_name=vosk_model_name)
        vosk_model_path = vosk_model.get_model_path(vosk_model_name, "ru")
        destination_path = Path(f"models/VoskTTS")
        shutil.move(vosk_model_path, destination_path)
    vosk_model = VoskModel(model_name=vosk_model_name, model_path=vosk_full_path)
    vosk_synth = Synth(vosk_model)
    return vosk_synth


