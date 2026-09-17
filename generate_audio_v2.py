import asyncio
import shutil
import subprocess
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg


BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "audio_v2_parts"
OUTPUT_FILE = BASE_DIR / "dialogue_v2.mp3"
TIMELINE_FILE = BASE_DIR / "timeline_v2.txt"

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
        "Привет. Это Артём, у нас сегодня созвон по лендингу."
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Привет, Артём, это Оксана. Давай пробежимся по статусу."
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Смотри, по картинкам на главной. Они сейчас весят слишком много, страница долго грузится."
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Да, вижу. Я возьму это на себя, сделаю оптимизацию изображений."
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Отлично. Когда сможешь закончить?"
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Думаю, к пятнице управлюсь."
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Хорошо, ставим пятницу как дедлайн. Слушай, а что если добавить блок с отзывами клиентов прямо под первым экраном?"
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Хм, идея неплохая, но у нас и так тесно по срокам. Давай не будем сейчас это делать, отложим на потом."
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Окей, согласен, не в этот раз."
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Кстати, по поводу интеграции с CRM, которую мы обсуждали на прошлой неделе, я говорила с клиентом, он сказал, что это пока не нужно, можно убрать из плана."
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Понял, значит интеграцию отменяем полностью?"
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Да. Слушай, а по пятнице, я подумала, не успею, там ещё правки от дизайнера придут. Давай перенесём на среду?"
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Хорошо, тогда среда — новый дедлайн. Ещё момент, тексты на главной странице тоже надо поправить, там пара неточностей."
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Да, точно, надо поправить."
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Угу."
    ),
    (
        "Оксана",
        VOICE_OKSANA,
        "Ладно, и последнее, дизайн для мобильной версии обещали прислать на следующей неделе."
    ),
    (
        "Артём",
        VOICE_ARTEM,
        "Хорошо, тогда ждём."
    ),
]


async def generate_mp3(
    text: str,
    voice: str,
    output_path: Path
) -> None:

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice
    )

    await communicate.save(
        str(output_path)
    )


def convert_mp3_to_wav(
    ffmpeg_exe: str,
    source: Path,
    target: Path
) -> None:

    command = [
        ffmpeg_exe,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-ac",
        str(CHANNELS),
        "-ar",
        str(SAMPLE_RATE),
        "-sample_fmt",
        "s16",
        str(target),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"Не удалось преобразовать {source.name} в WAV:\n"
            f"{result.stderr or result.stdout}"
        )


def read_wav_frames(
    path: Path
) -> tuple[bytes, int]:

    with wave.open(
        str(path),
        "rb"
    ) as wav_file:

        if (
            wav_file.getnchannels()
            != CHANNELS
        ):
            raise RuntimeError(
                f"Неверное число каналов в {path.name}"
            )

        if (
            wav_file.getsampwidth()
            != SAMPLE_WIDTH
        ):
            raise RuntimeError(
                f"Неверная глубина сэмпла в {path.name}"
            )

        if (
            wav_file.getframerate()
            != SAMPLE_RATE
        ):
            raise RuntimeError(
                f"Неверная частота дискретизации в {path.name}"
            )

        frame_count = (
            wav_file.getnframes()
        )

        frames = (
            wav_file.readframes(
                frame_count
            )
        )

    return frames, frame_count


def write_combined_wav(
    wav_paths: list[Path],
    dialogue: list[tuple[str, str, str]],
    output_path: Path,
) -> list[tuple[str, str, float, float]]:

    pause_frames_count = int(
        SAMPLE_RATE
        * PAUSE_MS
        / 1000
    )

    silence = (
        b"\x00"
        * pause_frames_count
        * CHANNELS
        * SAMPLE_WIDTH
    )

    timeline = []

    current_frame = 0

    with wave.open(
        str(output_path),
        "wb"
    ) as output:

        output.setnchannels(
            CHANNELS
        )

        output.setsampwidth(
            SAMPLE_WIDTH
        )

        output.setframerate(
            SAMPLE_RATE
        )

        for index, wav_path in enumerate(
            wav_paths
        ):

            speaker, _, text = (
                dialogue[index]
            )

            frames, frame_count = (
                read_wav_frames(
                    wav_path
                )
            )

            start_sec = (
                current_frame
                / SAMPLE_RATE
            )

            output.writeframes(
                frames
            )

            current_frame += (
                frame_count
            )

            end_sec = (
                current_frame
                / SAMPLE_RATE
            )

            timeline.append(
                (
                    speaker,
                    text,
                    round(
                        start_sec,
                        2
                    ),
                    round(
                        end_sec,
                        2
                    ),
                )
            )

            if (
                index
                < len(wav_paths) - 1
            ):

                output.writeframes(
                    silence
                )

                current_frame += (
                    pause_frames_count
                )

    return timeline


def encode_final_mp3(
    ffmpeg_exe: str,
    wav_path: Path,
    mp3_path: Path
) -> None:

    command = [
        ffmpeg_exe,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "128k",
        str(mp3_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:

        raise RuntimeError(
            "Не удалось создать итоговый MP3:\n"
            + (
                result.stderr
                or result.stdout
            )
        )


async def main() -> None:

    ffmpeg_exe = (
        imageio_ffmpeg
        .get_ffmpeg_exe()
    )

    if not Path(
        ffmpeg_exe
    ).exists():

        raise RuntimeError(
            f"FFmpeg не найден: {ffmpeg_exe}"
        )

    if TEMP_DIR.exists():

        shutil.rmtree(
            TEMP_DIR
        )

    TEMP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        f"FFmpeg: {ffmpeg_exe}"
    )

    print(
        "Генерирую dialogue_v2.mp3..."
    )

    print(
        "Контрольное изменение: "
        "финальный дедлайн — среда."
    )

    print()

    wav_paths = []

    for index, (
        speaker,
        voice,
        text
    ) in enumerate(
        DIALOGUE,
        start=1
    ):

        mp3_path = (
            TEMP_DIR
            / f"line_{index:02d}.mp3"
        )

        wav_path = (
            TEMP_DIR
            / f"line_{index:02d}.wav"
        )

        print(
            f"{index:02d}/{len(DIALOGUE)} — {speaker}"
        )

        await generate_mp3(
            text=text,
            voice=voice,
            output_path=mp3_path,
        )

        convert_mp3_to_wav(
            ffmpeg_exe=ffmpeg_exe,
            source=mp3_path,
            target=wav_path,
        )

        wav_paths.append(
            wav_path
        )

    combined_wav = (
        TEMP_DIR
        / "dialogue_v2.wav"
    )

    timeline = write_combined_wav(
        wav_paths=wav_paths,
        dialogue=DIALOGUE,
        output_path=combined_wav,
    )

    encode_final_mp3(
        ffmpeg_exe=ffmpeg_exe,
        wav_path=combined_wav,
        mp3_path=OUTPUT_FILE,
    )

    TIMELINE_FILE.write_text(
        "\n".join(
            f"[{start:>6.2f}s - {end:>6.2f}s] "
            f"{speaker}: {text}"
            for (
                speaker,
                text,
                start,
                end
            ) in timeline
        ),
        encoding="utf-8",
    )

    print()
    print("Готово.")

    print(
        f"Аудио: {OUTPUT_FILE}"
    )

    print(
        f"Таймлайн: {TIMELINE_FILE}"
    )

    print()

    print(
        "Ожидаемый финальный результат:"
    )

    print(
        "Оптимизация изображений "
        "→ Оксана → среда."
    )

    print(
        "Пятница не должна остаться "
        "финальным дедлайном."
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )