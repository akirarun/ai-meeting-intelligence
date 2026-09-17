"""
Генерирует одну аудиозапись разговора двух людей.
Артём говорит мужским голосом, Оксана — женским.
Между репликами добавляется небольшая пауза (для реалистичности и чтобы
таймкоды не съезжали друг на друга).

Запуск:
    python generate_audio.py

Результат: dialogue.mp3 в этой же папке.
"""

import asyncio
import edge_tts
from pydub import AudioSegment
import os

# Голос Артёма и голос Оксаны (готовые голоса Microsoft, бесплатно)
VOICE_ARTEM = "ru-RU-DmitryNeural"
VOICE_OKSANA = "ru-RU-SvetlanaNeural"

# Реплики: (спикер, текст)
DIALOGUE = [
    ("Артём", "Привет! Это Артём, у нас сегодня созвон по лендингу."),
    ("Оксана", "Привет, Артём, это Оксана. Давай пробежимся по статусу."),
    ("Артём", "Смотри, по картинкам на главной — они сейчас весят слишком много, страница долго грузится."),
    ("Оксана", "Да, вижу. Я возьму это на себя, сделаю оптимизацию изображений."),
    ("Артём", "Отлично. Когда сможешь закончить?"),
    ("Оксана", "Думаю, к пятнице управлюсь."),
    ("Артём", "Хорошо, ставим пятницу как дедлайн."),
    ("Артём", "Слушай, а что если добавить блок с отзывами клиентов прямо под первым экраном?"),
    ("Оксана", "Хм, идея неплохая, но у нас и так тесно по срокам. Давай не будем сейчас это делать, отложим на потом."),
    ("Артём", "Ок, согласен, не в этот раз."),
    ("Оксана", "Кстати, по поводу интеграции с CRM, которую мы обсуждали на прошлой неделе — я говорила с клиентом, он сказал, что это пока не нужно, можно убрать из плана."),
    ("Артём", "Понял, значит интеграцию отменяем полностью."),
    ("Оксана", "Да. Слушай, а по пятнице — я подумала, не успею, там ещё правки от дизайнера придут. Давай перенесём на понедельник?"),
    ("Артём", "Хорошо, тогда понедельник — новый дедлайн."),
    ("Артём", "Ещё момент — тексты на главной странице тоже надо поправить, там пара неточностей."),
    ("Оксана", "Да, точно, надо поправить."),
    ("Артём", "Угу."),
    ("Оксана", "Ладно, и последнее — дизайн для мобильной версии обещали прислать на следующей неделе."),
    ("Артём", "Хорошо, тогда ждём."),
]

PAUSE_MS = 500  # пауза между репликами


async def generate_line(text: str, voice: str, out_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


async def main():
    tmp_dir = "tmp_lines"
    os.makedirs(tmp_dir, exist_ok=True)

    combined = AudioSegment.silent(duration=0)
    timeline = []  # для лога таймкодов: (спикер, текст, старт_сек, конец_сек)

    for i, (speaker, text) in enumerate(DIALOGUE):
        voice = VOICE_ARTEM if speaker == "Артём" else VOICE_OKSANA
        line_path = os.path.join(tmp_dir, f"line_{i:02d}.mp3")

        print(f"Генерирую реплику {i+1}/{len(DIALOGUE)} ({speaker})...")
        await generate_line(text, voice, line_path)

        segment = AudioSegment.from_mp3(line_path)
        start_sec = len(combined) / 1000
        combined += segment
        end_sec = len(combined) / 1000
        timeline.append((speaker, text, round(start_sec, 2), round(end_sec, 2)))

        combined += AudioSegment.silent(duration=PAUSE_MS)

    combined.export("dialogue.mp3", format="mp3")
    print("\nГотово! Файл сохранён как dialogue.mp3")

    # Сохраняем таймкоды в отдельный файл — пригодится на шаге проверки
    with open("timeline.txt", "w", encoding="utf-8") as f:
        for speaker, text, start, end in timeline:
            f.write(f"[{start:>6.2f}s - {end:>6.2f}s] {speaker}: {text}\n")
    print("Таймкоды сохранены в timeline.txt (для сверки на следующих шагах)")


if __name__ == "__main__":
    asyncio.run(main())
