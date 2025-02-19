import os
import json
import tempfile
import gradio as gr
import warnings

from playsound3 import playsound
from constants import SAMPLE_RATE, MODEL_DIR, DATA_DIR, TEMP_DIR, SILERO_SPEAKERS, TERA_SPEAKERS, VOSK_SPEAKERS
from torch_setup import torch_init
from tts_models import silero_init, tera_init, vosk_init
from utils import create_dir_if_not_exists

create_dir_if_not_exists(MODEL_DIR)
create_dir_if_not_exists(DATA_DIR)
create_dir_if_not_exists(TEMP_DIR)

torch_init()

warnings.filterwarnings('ignore')
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

silero_model = silero_init()
tera_model = tera_init()
vosk_synth = vosk_init()

def tera_tts(phrase: str, speaker: str=""):
    if len(phrase.strip()) == 0:
        raise gr.Error("Пустая строка")
    with tempfile.NamedTemporaryFile(dir=TEMP_DIR, prefix="tera_tts", suffix=".wav", delete=False) as temp_file:
        audio = tera_model(phrase, lenght_scale=1.1)
        tera_model.save_wav(audio, temp_file.name)
        playsound(temp_file.name)

def silero(phrase: str, speaker: str="baya"):
    if len(phrase.strip()) == 0:
        raise gr.Error("Пустая строка")
    with tempfile.NamedTemporaryFile(dir=TEMP_DIR, prefix="silero", suffix=".wav", delete=False) as temp_file:
        audio_path = silero_model.save_wav(text=phrase,
                                                audio_path=str(temp_file.name),
                                                speaker=speaker,
                                                sample_rate=SAMPLE_RATE)
        playsound(audio_path)

def vosk_tts(phrase: str, speaker: str="0"):
    if len(phrase.strip()) == 0:
        raise gr.Error("Пустая строка")
    with tempfile.NamedTemporaryFile(dir=TEMP_DIR, prefix="vosk_tts", suffix=".wav", delete=False) as temp_file:
        vosk_synth.synth(phrase, temp_file.name, speaker_id=speaker)
        playsound(temp_file.name)


def gr_load_json(file):
    try:
        with open(file.name, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise gr.Error("JSON должен быть списком словарей")
        
        for item in data:
            if not isinstance(item, dict):
                raise gr.Error("Все элементы списка должны быть словарями")
            if not all(key in item for key in ["origin", "transcription", "type"]):
                raise gr.Error("Каждая запись должна содержать поля origin, transcription и type")
                
        first_entry = data[0]
        return (
            data, 
            0, 
            first_entry["origin"], 
            first_entry["transcription"], 
            first_entry["type"], 
            f"1/{len(data)}"
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
    
    next_entry = data[new_index]
    return (
        data, 
        new_index, 
        next_entry["origin"], 
        next_entry["transcription"], 
        next_entry["type"], 
        f"{new_index+1}/{len(data)}"
    )


def gr_save_json(data):
    if not data:
        raise gr.Error("Нет данных для сохранения")
    
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as file_wrapper:
        with open(file_wrapper.name, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return file_wrapper.name


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
            gr.Markdown("""1. Загрузите JSON-файл с аббревиатурами
                        2. Для каждой записи (Origin) введите правильное произношение (Transcription) и класс (Type)
                        3. Проверьте правильность произношения в TTS-системах
                        4. Сохраните готовый файл""")
        with gr.Accordion("Примечания", open=False):
            gr.Markdown("""- Аббревиатуры читаются отдельно по буквам: ВВП (вэ вэ пэ), НЛО (эн эл о), СССР (эс эс эс эр)
                        - Акронимы читаются одним словом: ВУЗ (вуз), ЗОЖ (зож), НАТО (н+ато)
                        - В раздел 'Другое' распределяется всё остальное: фамилии, географические названия и т.д.
                        - Для обозначения ударения используйте символ '+'. Например: 'св+ёкла'
                        - Для достижения правильного произношения можно экспериментировать с написанием: менять регистр букв, разделять слова на части и т.д.""")
    
    data_state = gr.State()
    index_state = gr.State()
    
    with gr.Row():
        upload_btn = gr.UploadButton("Загрузить JSON файл", file_types=[".json"])
        
    
    index_display = gr.Textbox(label="Текущая запись", interactive=False)
    
    with gr.Row():
        prev_btn = gr.Button("← Назад")
        next_btn = gr.Button("Вперед →")
    
    origin_display = gr.Textbox(label="Origin", interactive=False)
    transcription_input = gr.Textbox(label="Transcription")
    type_radio = gr.Radio(
        ["Аббревиатура", "Акроним", "Другое"], 
        label="Type", 
        value="Аббревиатура"
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

    
    save_btn = gr.Button("Сохранить изменения")
    
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
        outputs=[data_state, index_state, origin_display, transcription_input, type_radio, index_display]
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
        inputs=[data_state],
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