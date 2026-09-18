"""
Отправляет dialogue.mp3 в AssemblyAI и получает транскрипт с указанием
кто говорит (Speaker A / Speaker B) и точным временем каждой фразы.
"""

import json
import os
import sys

import assemblyai as aai


API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
AUDIO_FILE = "working_audio.mp3"


if not API_KEY:
    print("Ошибка: не задана переменная окружения ASSEMBLYAI_API_KEY.")
    print("")
    print("PowerShell:")
    print('$env:ASSEMBLYAI_API_KEY="YOUR_API_KEY"')
    sys.exit(1)


if not os.path.exists(AUDIO_FILE):
    print(f"Ошибка: аудиофайл не найден: {AUDIO_FILE}")
    sys.exit(1)


aai.settings.api_key = API_KEY

config = aai.TranscriptionConfig(
    speaker_labels=True,
    language_code="ru",
)

print("Отправляю файл на распознавание...")

transcriber = aai.Transcriber()
transcript = transcriber.transcribe(
    AUDIO_FILE,
    config=config,
)

if transcript.status == "error":
    print(f"Ошибка распознавания: {transcript.error}")
    sys.exit(1)


print("Готово! Сохраняю результаты...")


with open(
    "transcript.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        transcript.json_response,
        f,
        ensure_ascii=False,
        indent=2,
    )


with open(
    "transcript.txt",
    "w",
    encoding="utf-8",
) as f:
    for utterance in transcript.utterances:
        start_sec = utterance.start / 1000
        end_sec = utterance.end / 1000

        f.write(
            f"[{start_sec:>6.2f}s - {end_sec:>6.2f}s] "
            f"Speaker {utterance.speaker}: "
            f"{utterance.text}\n"
        )


print("")
print("Готово:")
print("  transcript.json — полный ответ AssemblyAI")
print("  transcript.txt  — читаемый транскрипт со спикерами и таймкодами")