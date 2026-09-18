"""Генерирует Test 1: диалог и таймлайн.

Ожидаемые ключевые состояния:
- ACCEPTED: оптимизация изображений; owner: Оксана; final deadline: понедельник.
- REJECTED: блок с отзывами.
- CANCELLED: интеграция с CRM.
- UNRESOLVED: тексты на главной — owner/deadline missing.
- UNRESOLVED: мобильный дизайн — owner missing, относительный срок
  «на следующей неделе» без достаточного date context.
"""

import asyncio
import subprocess
import tempfile
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "dialogue.mp3"
TIMELINE_FILE = BASE_DIR / "timeline.txt"

VOICE_ARTEM = "ru-RU-DmitryNeural"
VOICE_OKSANA = "ru-RU-SvetlanaNeural"

SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2
PAUSE_MS = 500


DIALOGUE = [
    (
        "Артём",
        VOICE_ARTEM,
        "Привет! Это Артём, у нас сегодня созвон по лендингу.",
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Привет, Артём, это Оксана. Давай пробежимся по статусу.",
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Смотри, по картинкам на главной — они сейчас весят слишком много, страница долго грузится.",
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Да, вижу. Я возьму это на себя, сделаю оптимизацию изображений.",
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Отлично. Когда сможешь закончить?",
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Думаю, к пятнице управлюсь.",
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Хорошо, ставим пятницу как дедлайн.",
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Слушай, а что если добавить блок с отзывами клиентов прямо под первым экраном?",
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Хм, идея неплохая, но у нас и так тесно по срокам. Давай не будем сейчас это делать, отложим на потом.",
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Ок, согласен, не в этот раз.",
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Кстати, по поводу интеграции с CRM, которую мы обсуждали на прошлой неделе — я говорила с клиентом, он сказал, что это пока не нужно, можно убрать из плана.",
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Понял, значит интеграцию отменяем полностью.",
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Да. Слушай, а по пятнице — я подумала, не успею, там ещё правки от дизайнера придут. Давай перенесём на понедельник?",
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Хорошо, тогда понедельник — новый дедлайн.",
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Ещё момент — тексты на главной странице тоже надо поправить, там пара неточностей.",
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Да, точно, надо поправить.",
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Угу.",
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Ладно, и последнее — дизайн для мобильной версии обещали прислать на следующей неделе.",
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Хорошо, тогда ждём.",
    ),
]


def run_ffmpeg(ffmpeg_exe: str, *args: str) -> None:
    result = subprocess.run(
        [ffmpeg_exe, "-y", "-loglevel", "error", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Ошибка FFmpeg:\n"
            + (result.stderr or result.stdout)
        )


async def main() -> None:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    if not Path(ffmpeg_exe).exists():
        raise RuntimeError(
            f"FFmpeg не найден: {ffmpeg_exe}"
        )

    pause_frames = SAMPLE_RATE * PAUSE_MS // 1000
    silence = (
        b"\x00"
        * pause_frames
        * CHANNELS
        * SAMPLE_WIDTH
    )

    timeline = []
    current_frame = 0

    with tempfile.TemporaryDirectory(
        prefix="ugc_audio_test1_"
    ) as temp_dir:
        temp_path = Path(temp_dir)
        combined_wav = temp_path / "dialogue.wav"

        with wave.open(
            str(combined_wav),
            "wb",
        ) as output:
            output.setnchannels(CHANNELS)
            output.setsampwidth(SAMPLE_WIDTH)
            output.setframerate(SAMPLE_RATE)

            for index, (
                speaker,
                voice,
                text,
            ) in enumerate(DIALOGUE):
                print(
                    f"{index + 1:02d}/{len(DIALOGUE)} — {speaker}",
                    flush=True,
                )

                mp3_path = (
                    temp_path
                    / f"line_{index:02d}.mp3"
                )

                wav_path = (
                    temp_path
                    / f"line_{index:02d}.wav"
                )

                await edge_tts.Communicate(
                    text=text,
                    voice=voice,
                ).save(str(mp3_path))

                run_ffmpeg(
                    ffmpeg_exe,
                    "-i",
                    str(mp3_path),
                    "-ac",
                    str(CHANNELS),
                    "-ar",
                    str(SAMPLE_RATE),
                    "-c:a",
                    "pcm_s16le",
                    str(wav_path),
                )

                with wave.open(
                    str(wav_path),
                    "rb",
                ) as source:
                    actual_format = (
                        source.getnchannels(),
                        source.getsampwidth(),
                        source.getframerate(),
                    )

                    expected_format = (
                        CHANNELS,
                        SAMPLE_WIDTH,
                        SAMPLE_RATE,
                    )

                    if actual_format != expected_format:
                        raise RuntimeError(
                            f"Неверный формат WAV: {wav_path.name}"
                        )

                    frame_count = source.getnframes()
                    frames = source.readframes(
                        frame_count
                    )

                expected_bytes = (
                    frame_count
                    * CHANNELS
                    * SAMPLE_WIDTH
                )

                if (
                    not frame_count
                    or len(frames) != expected_bytes
                ):
                    raise RuntimeError(
                        "Пустая или неполная реплика: "
                        f"{index + 1}"
                    )

                start_sec = (
                    current_frame
                    / SAMPLE_RATE
                )

                output.writeframes(frames)
                current_frame += frame_count

                end_sec = (
                    current_frame
                    / SAMPLE_RATE
                )

                timeline.append(
                    (
                        speaker,
                        text,
                        start_sec,
                        end_sec,
                    )
                )

                if index < len(DIALOGUE) - 1:
                    output.writeframes(silence)
                    current_frame += pause_frames

        run_ffmpeg(
            ffmpeg_exe,
            "-i",
            str(combined_wav),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(OUTPUT_FILE),
        )

    TIMELINE_FILE.write_text(
        "\n".join(
            f"[{start:>6.2f}s - {end:>6.2f}s] "
            f"{speaker}: {text}"
            for (
                speaker,
                text,
                start,
                end,
            ) in timeline
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(f"Аудио: {OUTPUT_FILE}")
    print(f"Таймлайн: {TIMELINE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())