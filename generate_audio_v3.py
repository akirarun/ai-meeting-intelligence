"""Генерирует диалог v3 и таймлайн; ожидания ниже относятся к анализатору.

ACCEPTED: Проверка формы обратной связи; Owner: Оксана; Deadline: пятница.
UNRESOLVED: Обновление pricing-блока; Owner: missing; Deadline: missing.
Критический PASS: в accepted не должно быть
«Обновление pricing-блока → Оксана → завтра».
"""

import asyncio
import subprocess
import tempfile
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "dialogue_v3.mp3"
TIMELINE_FILE = BASE_DIR / "timeline_v3.txt"

VOICE_ARTEM = "ru-RU-DmitryNeural"
VOICE_OKSANA = "ru-RU-SvetlanaNeural"
SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2
PAUSE_MS = 500

DIALOGUE = [
    ("Артём", VOICE_ARTEM,
     "Привет, это Артём. Давай быстро пройдёмся по оставшимся задачам лендинга."),
    ("Оксана", VOICE_OKSANA,
     "Привет, Артём, это Оксана. Да, давай."),
    ("Артём", VOICE_ARTEM,
     "Нам ещё нужно обновить pricing-блок на лендинге. Кто сможет это взять?"),
    ("Оксана", VOICE_OKSANA,
     "Я, возможно, посмотрю завтра, если закончу текущие задачи."),
    ("Артём", VOICE_ARTEM,
     "Хорошо. Тогда пока не фиксируем это за тобой."),
    ("Оксана", VOICE_OKSANA,
     "Да, посмотрим по загрузке."),
    ("Артём", VOICE_ARTEM,
     "А форму обратной связи нужно проверить до пятницы."),
    ("Оксана", VOICE_OKSANA,
     "Это я беру. Сделаю до пятницы."),
    ("Артём", VOICE_ARTEM,
     "Отлично, тогда проверка формы обратной связи за тобой, дедлайн пятница."),
    ("Артём", VOICE_ARTEM,
     "По pricing-блоку тогда вернёмся позже, когда будет понятно, кто сможет заняться."),
    ("Оксана", VOICE_OKSANA, "Хорошо."),
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
        raise RuntimeError(f"Ошибка FFmpeg:\n{result.stderr or result.stdout}")


async def main() -> None:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    pause_frames = SAMPLE_RATE * PAUSE_MS // 1000
    silence = b"\x00" * pause_frames * CHANNELS * SAMPLE_WIDTH
    timeline = []
    current_frame = 0

    with tempfile.TemporaryDirectory(prefix="ugc_audio_v3_") as temp_dir:
        temp_path = Path(temp_dir)
        combined_wav = temp_path / "dialogue_v3.wav"
        with wave.open(str(combined_wav), "wb") as output:
            output.setnchannels(CHANNELS)
            output.setsampwidth(SAMPLE_WIDTH)
            output.setframerate(SAMPLE_RATE)

            for index, (speaker, voice, text) in enumerate(DIALOGUE):
                print(f"{index + 1:02d}/{len(DIALOGUE)} — {speaker}", flush=True)
                mp3_path = temp_path / f"line_{index:02d}.mp3"
                wav_path = temp_path / f"line_{index:02d}.wav"
                await edge_tts.Communicate(text=text, voice=voice).save(str(mp3_path))
                run_ffmpeg(
                    ffmpeg_exe, "-i", str(mp3_path),
                    "-ac", str(CHANNELS), "-ar", str(SAMPLE_RATE),
                    "-c:a", "pcm_s16le", str(wav_path),
                )
                with wave.open(str(wav_path), "rb") as source:
                    if (source.getnchannels(), source.getsampwidth(),
                            source.getframerate()) != (CHANNELS, SAMPLE_WIDTH, SAMPLE_RATE):
                        raise RuntimeError(f"Неверный формат WAV: {wav_path.name}")
                    frame_count = source.getnframes()
                    frames = source.readframes(frame_count)
                if not frame_count or len(frames) != frame_count * CHANNELS * SAMPLE_WIDTH:
                    raise RuntimeError(f"Пустая или неполная реплика: {index + 1}")

                start_sec = current_frame / SAMPLE_RATE
                output.writeframes(frames)
                current_frame += frame_count
                end_sec = current_frame / SAMPLE_RATE
                timeline.append(
                    f"[{start_sec:>6.3f}s - {end_sec:>6.3f}s] {speaker}: {text}"
                )
                if index < len(DIALOGUE) - 1:
                    output.writeframes(silence)
                    current_frame += pause_frames

        run_ffmpeg(
            ffmpeg_exe, "-i", str(combined_wav),
            "-codec:a", "libmp3lame", "-b:a", "128k", str(OUTPUT_FILE),
        )
        TIMELINE_FILE.write_text("\n".join(timeline) + "\n", encoding="utf-8")

    print(f"Аудио: {OUTPUT_FILE}")
    print(f"Таймлайн: {TIMELINE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
