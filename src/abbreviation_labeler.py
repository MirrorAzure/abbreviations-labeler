import os
import re
import json
import glob
#import tempfile
import gradio as gr
import warnings

from datetime import datetime
from pathlib import Path
from playsound3 import playsound
from constants import SAMPLE_RATE, MODEL_DIR, DATA_DIR, TEMP_DIR, SILERO_SPEAKERS, TERA_SPEAKERS, VOSK_SPEAKERS
from torch_setup import torch_init
from tts_models import silero_init, tera_init, vosk_init
from utils import create_dir_if_not_exists
from alphabets import alphabets

create_dir_if_not_exists(MODEL_DIR)
create_dir_if_not_exists(DATA_DIR)
create_dir_if_not_exists(TEMP_DIR)

torch_init()

warnings.filterwarnings('ignore')
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

silero_model = silero_init()
tera_model = tera_init()
vosk_synth = vosk_init()

abbreviation_types = ["Буквенная аббревиатура", "Звуковая аббревиатура", "Буквенно-звуковая аббревиатура", "Другое", "Пропуск"]

sound_abbreviation_pattern = re.compile(r"[бвгджзйклмнпрстфхцчшщ][аеёиоуыэюя][бвгджзйклмнпрстфхцчшщ]")
file_name_pattern = re.compile(r"(?P<original_name>.+?)(?:_(?:\d+-)+\d+)?\.json")

def tera_tts(phrase: str, speaker: str=""):
    if len(phrase.strip()) == 0:
        raise gr.Error("Пустая строка")
    audio_file_name = TEMP_DIR / "tera_tts.wav"
    audio = tera_model(phrase, lenght_scale=1.1)
    tera_model.save_wav(audio, str(audio_file_name))
    playsound(audio_file_name.absolute())

def silero(phrase: str, speaker: str="baya"):
    if len(phrase.strip()) == 0:
        raise gr.Error("Пустая строка")
    audio_file_name = TEMP_DIR / "silero.wav"
    silero_model.save_wav(text=phrase,
                            audio_path=str(audio_file_name),
                            speaker=speaker,
                            sample_rate=SAMPLE_RATE)
    playsound(audio_file_name.absolute())

def vosk_tts(phrase: str, speaker: str="0"):
    if len(phrase.strip()) == 0:
        raise gr.Error("Пустая строка")
    audio_file_name = TEMP_DIR / "vosk_tts.wav"
    #with tempfile.NamedTemporaryFile(dir=TEMP_DIR, prefix="vosk_tts", suffix=".wav", delete=False) as temp_file:
    vosk_synth.synth(phrase, str(audio_file_name), speaker_id=speaker)
    playsound(audio_file_name.absolute())

def get_transcription(text: str, type: str="Буквенная аббревиатура") -> str:
    if len(text.strip()) == 0:
        raise gr.Error("Пустая строка")
    if type == "Буквенная аббревиатура":
        transcription = ' '.join([alphabets.get(symbol, "") for symbol in text.upper()])
        gr.Info(f"Для буквенной аббревиатуры была определена транскрипция: {transcription}")
    elif type == "Звуковая аббревиатура":
        transcription = text.lower()
        gr.Info(f"Для звуковой аббревиатуры была определена транскрипция: {transcription}")
    else:
        transcription = text
        gr.Info("Тип аббревиатуры не был определён. Транскрипция задана по умолчанию.")
    return transcription

def check_for_sound_abbreviation(text: str) -> bool:
    if len(text.strip()) == 0:
        raise gr.Error("Пустая строка")
    is_sound = bool(sound_abbreviation_pattern.findall(text.lower()))
    return is_sound


def gr_load_json(file):
    original_name = Path(file.name).absolute()
    try:
        with open(file.name, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise gr.Error("JSON должен быть списком словарей")
        
        first_index = 0
        index_changed = False
        
        for idx, item in enumerate(data):
            transcription = item.get("transcription", "")
            if len(transcription) == 0 and not index_changed:
                index_changed = True
                first_index = idx
                gr.Info("Открыт первый неразмеченный элемент")
            if not isinstance(item, dict):
                raise gr.Error("Все элементы списка должны быть словарями")
            if not all(key in item for key in ["origin", "transcription", "type"]):
                raise gr.Error("Каждая запись должна содержать поля origin, transcription и type")
        
        if not index_changed:
            gr.Info("Все элементы размечены. Открыт первый элемент")
        
        if check_for_sound_abbreviation(data[first_index]["origin"]):
            data[first_index]["type"] = "Звуковая аббревиатура"
        
        if data[first_index]["type"] not in abbreviation_types:
            data[first_index]["type"] = abbreviation_types[0]    
        
        if len(data[first_index]["transcription"]) == 0:
            data[first_index]["transcription"] = get_transcription(data[first_index]["origin"], type=data[first_index]["type"])
        
        first_entry = data[first_index]
        
        return (
            data, 
            first_index, 
            first_entry["origin"], 
            first_entry["transcription"], 
            first_entry["type"], 
            f"{first_index+1}/{len(data)}",
            original_name
        )
    except Exception as e:
        raise gr.Error(f"Ошибка загрузки файла: {str(e)}")

def gr_navigate(direction, data, index, curr_origin, curr_transcription, curr_type):
    if data is None or index is None:
        return data, index, "", "", "", "0/0"
    
    data[index] = {
        "origin": curr_origin,
        "transcription": curr_transcription,
        "type": curr_type
    }
    
    new_index = index + direction
    if new_index < 0 or new_index >= len(data):
        return data, index, curr_origin, curr_transcription, curr_type, f"{index+1}/{len(data)}"
    
    if check_for_sound_abbreviation(data[new_index]["origin"]):
        data[new_index]["type"] = "Звуковая аббревиатура"
        
    if data[new_index]["type"] not in abbreviation_types:
        data[new_index]["type"] = abbreviation_types[0]

    if len(data[new_index]["transcription"]) == 0:
        data[new_index]["transcription"] = get_transcription(data[new_index]["origin"], type=data[new_index]["type"])
    
    next_entry = data[new_index]
    return (
        data, 
        new_index, 
        next_entry["origin"], 
        next_entry["transcription"], 
        next_entry["type"], 
        f"{new_index+1}/{len(data)}"
    )


def gr_save_json(data, original_file: Path):
    if not data:
        raise gr.Error("Нет данных для сохранения")
    
    files = glob.glob(str(TEMP_DIR / "*.json"))
    for file in files:
        os.remove(file)
    
    base_name = file_name_pattern.search(original_file.name).group("original_name")
    curr_time = datetime.now().strftime(format="%d-%m-%Y-%H-%M-%S")
    save_name = f"{base_name}_{curr_time}.json"
    save_path = TEMP_DIR / save_name
    
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(save_path.absolute())


def gr_update_data(data, index, transcription, type_val):
    if data is not None and index is not None and 0 <= index < len(data):
        data[index] = {
            "origin": data[index]["origin"],
            "transcription": transcription,
            "type": type_val
        }
    return data

with gr.Blocks(title="Audio Labeler") as demo:
    # with gr.Row():
    gr.Markdown("## Разметчик сокращений")
    with gr.Column():
        with gr.Accordion("Инструкция", open=False):
            gr.Markdown("""
                        1. Загрузите JSON-файл с аббревиатурами
                        2. Для каждой записи (Origin) введите правильное произношение (Transcription) и класс (Type)
                        3. Проверьте правильность произношения в TTS-системах
                        4. Сохраните готовый файл
                        """)
        with gr.Accordion("Примечания", open=False):
            gr.Markdown("""
                        - Для обозначения ударения используйте символ '+'. Например: св+ёкла
                        - Для достижения правильного произношения можно экспериментировать с написанием: менять регистр букв, разделять слова на части, добавлять дефисы '-' и т.д.
                        - Буквенные аббревиатуры читаются отдельно по буквам: ВВП (вэ вэ пэ), НЛО (эн эл о), СССР (эс эс эс эр)
                        - Звуковые аббревиатуры читаются так же, как пишутся: ВУЗ (вуз), ЗОЖ (зож), НАТО (н+ато)
                        - Буквенно-звуковые аббревиатуры содержат и буквенные, и звуковые части: ГИБДД (ги бэ дэ дэ)
                        - В раздел 'Другое' распределяется всё остальное: фамилии, географические названия и т.д.
                        """)
    
    data_state = gr.State()
    index_state = gr.State()
    file_state = gr.State(value=Path("tmp.json"))
    
    with gr.Row():
        upload_btn = gr.UploadButton("Загрузить JSON файл", file_types=[".json"])

    
    origin_display = gr.Textbox(label="Origin", interactive=False)
    transcription_input = gr.Textbox(label="Transcription")
    type_radio = gr.Radio(
        abbreviation_types, 
        label="Type", 
        value=abbreviation_types[0]
    )
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Silero TTS")
            silero_speaker_select = gr.Dropdown(
                choices=SILERO_SPEAKERS,
                label="Голос",
                value=SILERO_SPEAKERS[0]
            )
            silero_play_btn = gr.Button("Воспроизвести")
        with gr.Column():
            gr.Markdown("### Tera TTS")
            tera_speaker_select = gr.Dropdown(
                choices=TERA_SPEAKERS,
                label="Голос",
                value=TERA_SPEAKERS[0]
            )
            tera_play_btn = gr.Button("Воспроизвести")
        with gr.Column():
            gr.Markdown("### Vosk TTS")
            vosk_speaker_select = gr.Dropdown(
                choices=VOSK_SPEAKERS,
                label="Голос",
                value=VOSK_SPEAKERS[0]
            )
            vosk_play_btn = gr.Button("Воспроизвести")

    index_display = gr.Textbox(label="Текущая запись", interactive=False)
    
    with gr.Row():
        prev_btn = gr.Button("← Назад")
        next_btn = gr.Button("Вперед →")

    
    save_btn = gr.Button("Записать в файл")
    
    download = gr.File(label="Скачать измененный файл")

    silero_play_btn.click(
        silero,
        inputs=[transcription_input, silero_speaker_select],
        outputs=[]
    )
    
    tera_play_btn.click(
        tera_tts,
        inputs=[transcription_input, tera_speaker_select],
        outputs=[]
    )

    vosk_play_btn.click(
        vosk_tts,
        inputs=[transcription_input, vosk_speaker_select],
        outputs=[]
    )

    upload_btn.upload(
        gr_load_json,
        inputs=[upload_btn],
        outputs=[data_state, index_state, origin_display, transcription_input, type_radio, index_display, file_state]
    )
    
    prev_btn.click(
        gr_navigate,
        inputs=[
            gr.State(-1), 
            data_state, 
            index_state, 
            origin_display, 
            transcription_input, 
            type_radio
        ],
        outputs=[
            data_state, 
            index_state, 
            origin_display, 
            transcription_input, 
            type_radio, 
            index_display
        ]
    )
    
    next_btn.click(
        gr_navigate,
        inputs=[
            gr.State(1), 
            data_state, 
            index_state, 
            origin_display, 
            transcription_input, 
            type_radio
        ],
        outputs=[
            data_state, 
            index_state, 
            origin_display, 
            transcription_input, 
            type_radio, 
            index_display
        ]
    )
    
    save_btn.click(
        gr_save_json,
        inputs=[data_state, file_state],
        outputs=[download]
    )
    
    transcription_input.change(
        gr_update_data,
        inputs=[data_state, index_state, transcription_input, type_radio],
        outputs=[data_state]
    )
    
    type_radio.change(
        gr_update_data,
        inputs=[data_state, index_state, transcription_input, type_radio],
        outputs=[data_state]
    )

demo.launch(inbrowser=True)