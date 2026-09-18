from flask import Flask, render_template_string, request, jsonify, send_file
from pathlib import Path
from werkzeug.utils import secure_filename
import subprocess
import shutil
import threading
import time
import json
import uuid
import sys
import re
import imageio_ffmpeg


app = Flask(__name__)

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

for stale_upload in UPLOAD_DIR.iterdir():
    if stale_upload.is_file():
        try:
            stale_upload.unlink()
        except OSError:
            pass

TRANSCRIBE_SCRIPT = BASE_DIR / "transcribe.py"
ANALYZE_SCRIPT = BASE_DIR / "analyze_v5.py"
RESOLVE_SCRIPT = BASE_DIR / "resolve_v5_evidence.py"

WORKING_AUDIO = BASE_DIR / "working_audio.mp3"
TRANSCRIPT_FILE = BASE_DIR / "transcript.txt"
EVENTS_FILE = BASE_DIR / "events_v5.json"
COMMITMENTS_FILE = BASE_DIR / "commitments_v5_evidence.json"

MAX_AUDIO_SECONDS = 180


def get_audio_duration_seconds(audio_path: Path) -> float:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    result = subprocess.run(
        [
            ffmpeg_exe,
            "-hide_banner",
            "-i",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    ffmpeg_output = (
        result.stderr
        or result.stdout
        or ""
    )

    match = re.search(
        r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
        ffmpeg_output,
    )

    if not match:
        raise RuntimeError(
            "FFmpeg did not return audio duration."
        )

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))

    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


jobs = {}
jobs_lock = threading.Lock()
pipeline_lock = threading.Lock()


HTML = r"""
<!doctype html>
<html lang="ru">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width,initial-scale=1"
>

<title>Final Commitments</title>

<style>

:root {
    --ink: #19191b;
    --muted: #6e6e73;
    --blue: #0a84ff;
    --green: #34c759;
    --red: #ff453a;
    --orange: #ff9f0a;
    --purple: #bf5af2;
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;
    min-height: 100vh;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "SF Pro Display",
        "Segoe UI",
        sans-serif;

    color: var(--ink);

    background:
        radial-gradient(
            circle at 10% 15%,
            rgba(89, 139, 255, .34),
            transparent 28%
        ),
        radial-gradient(
            circle at 88% 14%,
            rgba(255, 170, 218, .28),
            transparent 26%
        ),
        radial-gradient(
            circle at 70% 86%,
            rgba(100, 210, 255, .22),
            transparent 30%
        ),
        linear-gradient(
            145deg,
            #eef2ff,
            #faf8fd
        );

    background-attachment: fixed;
}


.shell {
    width: min(
        1180px,
        calc(100% - 28px)
    );

    margin: 28px auto 60px;
}


.glass {
    background:
        rgba(255,255,255,.56);

    border:
        1px solid
        rgba(255,255,255,.76);

    box-shadow:
        0 18px 60px
        rgba(56,66,98,.14);

    backdrop-filter:
        blur(28px)
        saturate(155%);

    -webkit-backdrop-filter:
        blur(28px)
        saturate(155%);
}


.hero {
    border-radius: 30px;
    padding: 28px;
}


.eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;

    padding: 7px 11px;

    border-radius: 999px;

    background:
        rgba(255,255,255,.70);

    font-size: 12px;
    font-weight: 700;
}


.dot {
    width: 8px;
    height: 8px;

    border-radius: 50%;

    background: var(--blue);

    box-shadow:
        0 0 0 5px
        rgba(10,132,255,.12);
}


h1 {
    margin: 16px 0 10px;

    max-width: 760px;

    font-size:
        clamp(
            34px,
            5vw,
            58px
        );

    line-height: 1;

    letter-spacing:
        -.05em;
}


.subtitle {
    max-width: 780px;

    color: var(--muted);

    font-size: 16px;

    line-height: 1.55;
}


.upload-card {
    margin-top: 24px;

    padding: 16px;

    border-radius: 22px;

    background:
        rgba(255,255,255,.44);

    border:
        1px solid
        rgba(255,255,255,.75);
}


.dropzone {
    padding: 18px;

    border-radius: 16px;

    border:
        1px dashed
        rgba(60,60,67,.24);

    background:
        rgba(255,255,255,.42);
}


.file-row {
    display: flex;
    align-items: center;
    gap: 12px;
}


.file-icon {
    width: 38px;
    height: 38px;

    display: grid;
    place-items: center;

    border-radius: 12px;

    background: white;

    box-shadow:
        0 8px 20px
        rgba(35,45,75,.08);
}


input[type=file] {
    width: 100%;

    margin-top: 10px;

    color: var(--muted);
}


input[type=file]::file-selector-button {
    border: 0;

    padding: 9px 13px;

    margin-right: 10px;

    border-radius: 10px;

    background: white;

    font-weight: 700;

    cursor: pointer;

    box-shadow:
        0 4px 14px
        rgba(0,0,0,.07);
}


.actions {
    display: grid;

    grid-template-columns:
        1fr auto;

    gap: 10px;

    margin-top: 12px;
}


button {
    border: 0;

    border-radius: 14px;

    padding: 13px 16px;

    font-size: 14px;

    font-weight: 720;

    cursor: pointer;

    transition:
        transform .18s ease,
        opacity .18s ease,
        background .18s ease;
}


button:hover:not(:disabled) {
    transform:
        translateY(-1px);
}


button:disabled {
    opacity: .48;

    cursor: not-allowed;
}


.primary {
    background:
        linear-gradient(
            180deg,
            #202023,
            #0c0c0d
        );

    color: white;

    box-shadow:
        0 10px 24px
        rgba(0,0,0,.16);
}


.dev-button {
    background:
        rgba(255,255,255,.70);

    color: #4b4b50;

    border:
        1px solid
        rgba(255,255,255,.90);
}


.dev-note {
    margin-top: 8px;

    color: #929297;

    font-size: 11px;
}


#progressPanel {
    display: none;

    margin-top: 14px;

    padding: 14px;

    border-radius: 16px;

    background:
        rgba(255,255,255,.46);

    border:
        1px solid
        rgba(255,255,255,.76);
}


.progress-head {
    display: flex;

    justify-content:
        space-between;

    font-weight: 700;
}


.progress-track {
    height: 8px;

    margin-top: 10px;

    border-radius: 999px;

    overflow: hidden;

    background:
        rgba(120,120,128,.15);
}


#progressBar {
    width: 0;

    height: 100%;

    background:
        linear-gradient(
            90deg,
            #0a84ff,
            #64d2ff
        );

    transition:
        width .4s ease;
}


#stageText {
    margin-top: 8px;

    color: #5d5d62;

    font-size: 13px;
}


#errorBox,
#successBox {
    display: none;

    margin-top: 14px;

    padding: 13px 15px;

    border-radius: 16px;
}


#errorBox {
    background:
        rgba(255,69,58,.09);

    border:
        1px solid
        rgba(255,69,58,.18);

    color: #8a1d19;

    white-space: pre-wrap;
}


#successBox {
    background:
        rgba(52,199,89,.09);

    border:
        1px solid
        rgba(52,199,89,.18);

    color: #17602f;
}


#results {
    display: none;

    margin-top: 18px;
}


.status-strip {
    display: flex;

    justify-content:
        space-between;

    align-items: center;

    gap: 12px;

    margin-bottom: 16px;

    padding: 14px 16px;

    border-radius: 18px;
}


.status-strip strong {
    font-size: 14px;
}


.status-strip span {
    font-size: 12px;

    color: var(--muted);
}


.grid {
    display: grid;

    grid-template-columns:
        1fr 1fr;

    gap: 16px;
}


.panel {
    padding: 18px;

    border-radius: 22px;

    background:
        rgba(255,255,255,.54);

    border:
        1px solid
        rgba(255,255,255,.78);

    box-shadow:
        0 12px 30px
        rgba(54,65,90,.08);

    backdrop-filter:
        blur(22px);

    -webkit-backdrop-filter:
        blur(22px);
}


.panel-head {
    display: flex;

    align-items: center;

    justify-content:
        space-between;

    gap: 10px;
}


.panel h2 {
    margin: 0;

    font-size: 18px;

    letter-spacing:
        -.02em;
}


.badge {
    min-width: 26px;
    height: 26px;

    display: grid;

    place-items: center;

    border-radius: 999px;

    color: white;

    font-size: 12px;

    font-weight: 800;
}


.accepted {
    background: var(--green);
}


.cancelled {
    background: var(--red);
}


.rejected {
    background: var(--orange);
}


.unresolved {
    background: var(--purple);
}


.item {
    margin-top: 10px;

    padding: 14px;

    border-radius: 17px;

    background:
        rgba(255,255,255,.68);

    border:
        1px solid
        rgba(255,255,255,.90);
}


.item-title {
    font-size: 15px;

    font-weight: 760;
}


.meta {
    margin-top: 6px;

    color: #5e5e63;

    font-size: 13px;

    line-height: 1.5;
}


.quote {
    margin-top: 10px;

    padding: 11px 12px;

    border-radius: 13px;

    background:
        rgba(255,255,255,.74);

    font-size: 13px;

    line-height: 1.45;
}


.audio-row {
    display: flex;

    align-items: center;

    justify-content:
        space-between;

    gap: 10px;

    margin-top: 10px;
}


.timecode {
    font-size: 12px;

    color: #8a8a90;
}


.listen-button {
    padding: 8px 10px;

    border-radius: 11px;

    color: var(--blue);

    background:
        rgba(10,132,255,.10);

    border:
        1px solid
        rgba(10,132,255,.14);
}


.listen-button.playing {
    color: white;

    background: var(--blue);
}


.empty {
    margin-top: 10px;

    padding: 12px;

    border-radius: 13px;

    color: #8a8a90;

    background:
        rgba(255,255,255,.48);
}


.transcript-wrap {
    margin-top: 16px;

    border-radius: 22px;

    overflow: hidden;
}


.transcript-toggle {
    width: 100%;

    display: flex;

    justify-content:
        space-between;

    align-items: center;

    background:
        rgba(28,28,30,.88);

    color: white;

    border-radius: 0;

    padding: 16px 18px;

    text-align: left;
}


.transcript-toggle span:last-child {
    color: #a1a1a6;
}


.transcript {
    display: none;

    padding: 18px;

    background:
        rgba(28,28,30,.90);

    color: #f5f5f7;
}


.transcript.open {
    display: block;
}


pre {
    margin: 0;

    white-space: pre-wrap;

    overflow-wrap: anywhere;

    font:
        12px/1.58
        ui-monospace,
        SFMono-Regular,
        Menlo,
        Consolas,
        monospace;

    color: #d1d1d6;
}


@media(max-width:820px) {

    .grid {
        grid-template-columns:
            1fr;
    }

    .actions {
        grid-template-columns:
            1fr;
    }

    .dev-button {
        width: 100%;
    }
}


@media(max-width:560px) {

    .shell {
        width:
            min(
                100% - 18px,
                1180px
            );

        margin:
            12px auto 34px;
    }

    .hero {
        padding: 20px;

        border-radius: 24px;
    }

    h1 {
        font-size: 40px;
    }

    .status-strip {
        align-items:
            flex-start;

        flex-direction:
            column;
    }
}

</style>

</head>

<body>


<div class="shell">


<section class="hero glass">


<div class="eyebrow">

<span class="dot"></span>

AI meeting intelligence

</div>


<h1>

Conversation → final commitments

</h1>


<div class="subtitle">

Загрузите запись разговора.
Система распознает спикеров,
отслеживает изменения договорённостей
и показывает финальное состояние:
задачи, ответственных, сроки
и нерешённые вопросы.

</div>


<form
    id="uploadForm"
    class="upload-card"
>


<div class="dropzone">


<div class="file-row">


<div class="file-icon">

🎙️

</div>


<div>

<strong>

Аудиозапись встречи

</strong>

<div
    style="
        font-size:12px;
        color:#8e8e93;
        margin-top:2px
    "
>

MP3, до 3 минут
для тестового сценария

</div>

</div>


</div>


<input
    id="audioInput"
    type="file"
    name="audio"
    accept=".mp3"
>


</div>


<div class="actions">


<button
    id="processButton"
    class="primary"
    type="submit"
>

Обработать запись

</button>


<button
    id="devButton"
    class="dev-button"
    type="button"
>

Последний результат

</button>


</div>


<div class="dev-note">

Техническая кнопка для разработки:
открывает последний сохранённый
результат без повторного запуска AI.

</div>


<div id="progressPanel">


<div class="progress-head">

<span>

Обработка записи

</span>

<span id="progressPercent">

0%

</span>

</div>


<div class="progress-track">

<div id="progressBar"></div>

</div>


<div id="stageText">

Подготовка...

</div>


</div>


<div id="errorBox"></div>

<div id="successBox"></div>


</form>


</section>


<div id="results">


<div
    id="statusStrip"
    class="status-strip glass"
>


<div>


<strong id="statusTitle">

Результат готов

</strong>

<br>

<span id="statusSubtitle"></span>


</div>


<span id="timingText"></span>


</div>


<div class="grid">


<section class="panel">


<div class="panel-head">


<h2>

Принятые задачи

</h2>


<span
    id="acceptedCount"
    class="badge accepted"
>

0

</span>


</div>


<div id="acceptedTasks"></div>


</section>


<section class="panel">


<div class="panel-head">


<h2>

Отменённые задачи

</h2>


<span
    id="cancelledCount"
    class="badge cancelled"
>

0

</span>


</div>


<div id="cancelledTasks"></div>


</section>


<section class="panel">


<div class="panel-head">


<h2>

Отклонённые предложения

</h2>


<span
    id="rejectedCount"
    class="badge rejected"
>

0

</span>


</div>


<div id="rejectedProposals"></div>


</section>


<section class="panel">


<div class="panel-head">


<h2>

Нерешённые вопросы

</h2>


<span
    id="unresolvedCount"
    class="badge unresolved"
>

0

</span>


</div>


<div id="unresolvedQuestions"></div>


</section>


</div>


<div class="transcript-wrap glass">


<button
    id="transcriptToggle"
    class="transcript-toggle"
    type="button"
>


<span>

Transcript

</span>


<span id="transcriptState">

Показать

</span>


</button>


<div
    id="transcriptBox"
    class="transcript"
>


<pre id="transcriptText"></pre>


</div>


</div>


</div>


</div>


<script>


const $ =
    id =>
        document.getElementById(
            id
        );


const form =
    $("uploadForm");


const audioInput =
    $("audioInput");


const processButton =
    $("processButton");


const devButton =
    $("devButton");


const progressPanel =
    $("progressPanel");


const progressBar =
    $("progressBar");


const progressPercent =
    $("progressPercent");


const stageText =
    $("stageText");


const errorBox =
    $("errorBox");


const successBox =
    $("successBox");


const results =
    $("results");


let currentJobId = null;

let audioPlayer = null;

let activeButton = null;

let stopTimer = null;


function esc(value) {

    if (
        value === null
        ||
        value === undefined
    ) {

        return "";
    }

    return String(value)
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        );
}


function prettyTitle(text) {

    const value =
        String(
            text || ""
        ).trim();

    if (!value) {

        return "";
    }

    return (
        value.charAt(0)
        .toUpperCase()
        +
        value.slice(1)
        .replace(
            /\bcrm\b/gi,
            "CRM"
        )
    );
}


const labelMap = {

    owner:
        "ответственный",

    deadline:
        "срок",

    date_context:
        "контекст даты"
};


function humanMissing(value) {

    const items =
        Array.isArray(
            value
        )
        ?
        value
        :
        [value];

    return items
        .filter(Boolean)
        .map(
            item =>
                labelMap[item]
                || item
        )
        .join(", ");
}


function updateProgress(
    percent,
    stage
) {

    progressBar.style.width =
        percent + "%";

    progressPercent.textContent =
        percent + "%";

    if (stage) {

        stageText.textContent =
            stage;
    }
}


function parseTimestamp(
    timestamp
) {

    if (!timestamp) {

        return null;
    }

    const match =
        String(
            timestamp
        ).match(
            /([0-9.]+)s\s*-\s*([0-9.]+)s/
        );

    if (!match) {

        return null;
    }

    return {

        start:
            parseFloat(
                match[1]
            ),

        end:
            parseFloat(
                match[2]
            )
    };
}


function stopCurrentAudio() {

    if (stopTimer) {

        clearTimeout(
            stopTimer
        );

        stopTimer = null;
    }

    if (audioPlayer) {

        audioPlayer.pause();
    }

    if (activeButton) {

        activeButton.textContent =
            "▶ Прослушать";

        activeButton.classList.remove(
            "playing"
        );
    }

    activeButton = null;
}


function playSegment(
    timestamp,
    button
) {

    const range =
        parseTimestamp(
            timestamp
        );

    if (
        !range
        ||
        !currentJobId
    ) {

        alert(
            "Не удалось определить аудиофрагмент."
        );

        return;
    }

    if (
        activeButton === button
        &&
        audioPlayer
        &&
        !audioPlayer.paused
    ) {

        stopCurrentAudio();

        return;
    }

    stopCurrentAudio();

    audioPlayer =
        new Audio(
            "/audio/"
            + currentJobId
        );

    activeButton =
        button;

    button.textContent =
        "■ Остановить";

    button.classList.add(
        "playing"
    );

    audioPlayer.addEventListener(
        "loadedmetadata",

        async () => {

            try {

                audioPlayer.currentTime =
                    range.start;

                await audioPlayer.play();

                const duration =
                    Math.max(
                        .2,
                        range.end
                        -
                        range.start
                    );

                stopTimer =
                    setTimeout(
                        stopCurrentAudio,
                        duration * 1000
                    );

            } catch (error) {

                stopCurrentAudio();

                alert(
                    "Ошибка воспроизведения: "
                    + error.message
                );
            }
        },

        {
            once: true
        }
    );

    audioPlayer.load();
}


function makeItem(
    title,
    meta,
    quote,
    timestamp
) {

    return `
        <div class="item">

            <div class="item-title">

                ${esc(
                    prettyTitle(
                        title
                    )
                )}

            </div>

            <div class="meta">

                ${meta}

            </div>

            <div class="quote">

                “${esc(
                    quote
                )}”

            </div>

            <div class="audio-row">

                <span class="timecode">

                    ${esc(
                        timestamp
                    )}

                </span>

                <button
                    class="listen-button"
                    data-timestamp="${esc(timestamp)}"
                    type="button"
                >

                    ▶ Прослушать

                </button>

            </div>

        </div>
    `;
}


function bindListenButtons() {

    document
        .querySelectorAll(
            ".listen-button"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",

                    () => {

                        playSegment(
                            button.dataset.timestamp,
                            button
                        );
                    }
                );
            }
        );
}


function renderEmpty(
    element
) {

    element.innerHTML =
        `
            <div class="empty">

                Нет

            </div>
        `;
}


function renderResults(
    data
) {

    currentJobId =
        data.job_id;

    const commitments =
        data.commitments
        || {};

    const timings =
        data.timings
        || {};

    successBox.style.display =
        "none";

    $("statusTitle").textContent =
        "Результат готов";

    $("statusSubtitle").textContent =
        "Файл: "
        +
        (
            data.filename
            || "dialogue.mp3"
        );

    $("timingText").textContent =
        data.dev_mode
        ?
        "Dev-режим"
        :
        `Всего ${timings.total} сек.`;


    const acceptedItems =
        commitments.accepted_tasks
        || [];

    const cancelledItems =
        commitments.cancelled_tasks
        || [];

    const rejectedItems =
        commitments.rejected_proposals
        || [];

    const unresolvedItems =
        commitments.unresolved_questions
        || [];


    $("acceptedCount").textContent =
        acceptedItems.length;

    $("cancelledCount").textContent =
        cancelledItems.length;

    $("rejectedCount").textContent =
        rejectedItems.length;

    $("unresolvedCount").textContent =
        unresolvedItems.length;


    const accepted =
        $("acceptedTasks");

    accepted.innerHTML =
        "";

    if (
        acceptedItems.length
    ) {

        acceptedItems.forEach(
            item => {

                accepted.innerHTML +=
                    makeItem(

                        item.task,

                        `
                            Ответственный:
                            ${esc(item.owner)}
                            <br>

                            Дедлайн:
                            ${esc(
                                item.deadline
                                ?? "не указан"
                            )}
                        `,

                        item.supporting_quote,

                        item.timestamp
                    );
            }
        );

    } else {

        renderEmpty(
            accepted
        );
    }


    const cancelled =
        $("cancelledTasks");

    cancelled.innerHTML =
        "";

    if (
        cancelledItems.length
    ) {

        cancelledItems.forEach(
            item => {

                cancelled.innerHTML +=
                    makeItem(

                        item.task,

                        "Статус: отменено",

                        item.supporting_quote,

                        item.timestamp
                    );
            }
        );

    } else {

        renderEmpty(
            cancelled
        );
    }


    const rejected =
        $("rejectedProposals");

    rejected.innerHTML =
        "";

    if (
        rejectedItems.length
    ) {

        rejectedItems.forEach(
            item => {

                rejected.innerHTML +=
                    makeItem(

                        item.proposal,

                        "Статус: отклонено",

                        item.supporting_quote,

                        item.timestamp
                    );
            }
        );

    } else {

        renderEmpty(
            rejected
        );
    }


    const unresolved =
        $("unresolvedQuestions");

    unresolved.innerHTML =
        "";

    if (
        unresolvedItems.length
    ) {

        unresolvedItems.forEach(
            item => {

                unresolved.innerHTML +=
                    makeItem(

                        item.question,

                        `
                            Не хватает:
                            ${esc(
                                humanMissing(
                                    item.missing
                                )
                            )}
                            <br>

                            Срок:
                            ${esc(
                                item.deadline
                                ?? "не указан"
                            )}
                        `,

                        item.supporting_quote,

                        item.timestamp
                    );
            }
        );

    } else {

        renderEmpty(
            unresolved
        );
    }


    $("transcriptText").textContent =
        data.transcript
        || "";

    results.style.display =
        "block";

    bindListenButtons();

    setTimeout(
        () => {

            results.scrollIntoView(
                {
                    behavior:
                        "smooth",

                    block:
                        "start"
                }
            );
        },

        80
    );
}


async function pollJob(
    jobId
) {

    const response =
        await fetch(
            "/status/"
            + jobId,

            {
                cache:
                    "no-store"
            }
        );

    const data =
        await response.json();

    if (!response.ok) {

        throw new Error(
            data.error
            ||
            "Ошибка получения статуса."
        );
    }

    updateProgress(
        data.progress
        || 0,

        data.stage
        || "Обработка..."
    );

    if (
        data.status
        === "done"
    ) {

        updateProgress(
            100,
            "Готово"
        );

        renderResults(
            data
        );

        processButton.disabled =
            false;

        devButton.disabled =
            false;

        processButton.textContent =
            "Обработать новую запись";

        return true;
    }

    if (
        data.status
        === "error"
    ) {

        errorBox.style.display =
            "block";

        errorBox.textContent =
            data.error
            ||
            "Неизвестная ошибка.";

        processButton.disabled =
            false;

        devButton.disabled =
            false;

        return true;
    }

    return false;
}


form.addEventListener(
    "submit",

    async event => {

        event.preventDefault();

        stopCurrentAudio();

        if (
            !audioInput.files.length
        ) {

            alert(
                "Выберите MP3-файл."
            );

            return;
        }

        errorBox.style.display =
            "none";

        results.style.display =
            "none";

        progressPanel.style.display =
            "block";

        processButton.disabled =
            true;

        devButton.disabled =
            true;

        processButton.textContent =
            "Обработка...";

        updateProgress(
            3,
            "Загрузка файла..."
        );

        const formData =
            new FormData();

        formData.append(
            "audio",
            audioInput.files[0]
        );

        try {

            const response =
                await fetch(
                    "/start",

                    {
                        method:
                            "POST",

                        body:
                            formData
                    }
                );

            const data =
                await response.json();

            if (!response.ok) {

                throw new Error(
                    data.error
                    ||
                    "Не удалось запустить обработку."
                );
            }

            currentJobId =
                data.job_id;

            const timer =
                setInterval(
                    async () => {

                        try {

                            const finished =
                                await pollJob(
                                    currentJobId
                                );

                            if (
                                finished
                            ) {

                                clearInterval(
                                    timer
                                );
                            }

                        } catch (
                            error
                        ) {

                            clearInterval(
                                timer
                            );

                            errorBox.style.display =
                                "block";

                            errorBox.textContent =
                                error.message;

                            processButton.disabled =
                                false;

                            devButton.disabled =
                                false;
                        }
                    },

                    1000
                );

        } catch (
            error
        ) {

            errorBox.style.display =
                "block";

            errorBox.textContent =
                error.message;

            processButton.disabled =
                false;

            devButton.disabled =
                false;
        }
    }
);


devButton.addEventListener(
    "click",

    async () => {

        stopCurrentAudio();

        errorBox.style.display =
            "none";

        results.style.display =
            "none";

        progressPanel.style.display =
            "block";

        processButton.disabled =
            true;

        devButton.disabled =
            true;

        updateProgress(
            50,
            "Открываю последний результат..."
        );

        try {

            const response =
                await fetch(
                    "/dev-result",

                    {
                        cache:
                            "no-store"
                    }
                );

            const data =
                await response.json();

            if (
                !response.ok
            ) {

                throw new Error(
                    data.error
                    ||
                    "Не удалось открыть dev-результат."
                );
            }

            updateProgress(
                100,
                "Готово"
            );

            renderResults(
                data
            );

        } catch (
            error
        ) {

            errorBox.style.display =
                "block";

            errorBox.textContent =
                error.message;
        }

        processButton.disabled =
            false;

        devButton.disabled =
            false;
    }
);


$("transcriptToggle")
.addEventListener(
    "click",

    () => {

        const box =
            $("transcriptBox");

        const open =
            box.classList.toggle(
                "open"
            );

        $("transcriptState")
        .textContent =
            open
            ?
            "Скрыть"
            :
            "Показать";
    }
);

</script>


</body>

</html>
"""


def update_job(
    job_id,
    **changes
):
    with jobs_lock:

        if job_id in jobs:

            jobs[job_id].update(
                changes
            )


def run_process_with_progress(
    command,
    cwd,
    job_id,
    start_progress,
    max_progress,
    stage
):
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    update_job(
        job_id,
        progress=start_progress,
        stage=stage
    )

    started = time.perf_counter()

    current_progress = start_progress

    while process.poll() is None:

        time.sleep(1)

        elapsed = (
            time.perf_counter()
            - started
        )

        target_progress = min(
            max_progress,
            start_progress
            + int(
                elapsed / 8
            )
        )

        if (
            target_progress
            > current_progress
        ):
            current_progress = (
                target_progress
            )

            update_job(
                job_id,
                progress=current_progress,
                stage=stage
            )

    stdout, stderr = (
        process.communicate()
    )

    if process.returncode != 0:

        raise RuntimeError(
            stderr
            or stdout
            or
            "Процесс завершился с ошибкой."
        )

    return stdout


def process_job_inner(
    job_id,
    uploaded_path,
    original_filename
):
    try:

        total_start = (
            time.perf_counter()
        )

        update_job(
            job_id,
            status="processing",
            progress=8,
            stage="Подготовка аудио..."
        )

        shutil.copyfile(
            uploaded_path,
            WORKING_AUDIO
        )

        for file_path in (
            TRANSCRIPT_FILE,
            EVENTS_FILE,
            COMMITMENTS_FILE
        ):

            if file_path.exists():

                file_path.unlink()


        transcription_start = (
            time.perf_counter()
        )

        run_process_with_progress(
            [
                sys.executable,
                str(
                    TRANSCRIBE_SCRIPT
                )
            ],

            BASE_DIR,
            job_id,
            10,
            24,

            "Распознавание речи и спикеров..."
        )

        transcription_time = (
            time.perf_counter()
            - transcription_start
        )

        if (
            not TRANSCRIPT_FILE.exists()
        ):

            raise RuntimeError(
                "После транскрибации "
                "не найден transcript.txt"
            )

        transcript = (
            TRANSCRIPT_FILE
            .read_text(
                encoding="utf-8"
            )
        )

        update_job(
            job_id,
            progress=27,
            stage="Транскрипт готов."
        )


        analysis_start = (
            time.perf_counter()
        )

        run_process_with_progress(
            [
                sys.executable,
                str(
                    ANALYZE_SCRIPT
                )
            ],

            BASE_DIR,
            job_id,
            30,
            88,

            "AI-анализ договорённостей..."
        )

        analysis_time = (
            time.perf_counter()
            - analysis_start
        )

        if (
            not EVENTS_FILE.exists()
        ):

            raise RuntimeError(
                "После AI-анализа "
                "не найден events_v5.json"
            )


        update_job(
            job_id,
            progress=93,
            stage="Собираю финальное состояние..."
        )

        resolution_start = (
            time.perf_counter()
        )

        resolver = subprocess.run(
            [
                sys.executable,
                str(
                    RESOLVE_SCRIPT
                )
            ],

            cwd=BASE_DIR,

            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        resolution_time = (
            time.perf_counter()
            - resolution_start
        )

        if (
            resolver.returncode
            != 0
        ):

            raise RuntimeError(
                resolver.stderr
                or resolver.stdout
                or
                "Resolver завершился с ошибкой."
            )

        if (
            not COMMITMENTS_FILE.exists()
        ):

            raise RuntimeError(
                "После resolver не найден "
                "commitments_v5_evidence.json"
            )

        commitments = json.loads(
            COMMITMENTS_FILE
            .read_text(
                encoding="utf-8"
            )
        )

        total_time = (
            time.perf_counter()
            - total_start
        )

        timings = {

            "transcription":
                round(
                    transcription_time,
                    2
                ),

            "analysis":
                round(
                    analysis_time,
                    2
                ),

            "resolution":
                round(
                    resolution_time,
                    4
                ),

            "total":
                round(
                    total_time,
                    2
                )
        }

        update_job(
            job_id,

            status="done",

            progress=100,

            stage="Готово",

            filename=
                original_filename,

            transcript=
                transcript,

            commitments=
                commitments,

            timings=
                timings,

            audio_path=
                str(
                    uploaded_path
                ),

            dev_mode=
                False
        )

    except Exception as exc:

        update_job(
            job_id,

            status="error",

            stage="Ошибка",

            error=str(
                exc
            )
        )



def process_job(
    job_id,
    uploaded_path,
    original_filename
):
    with pipeline_lock:
        process_job_inner(
            job_id,
            uploaded_path,
            original_filename
        )


@app.route("/")
def index():

    return render_template_string(
        HTML
    )


@app.route(
    "/start",
    methods=["POST"]
)
def start_job():

    audio = request.files.get(
        "audio"
    )

    if (
        not audio
        or
        not audio.filename
    ):

        return jsonify(
            {
                "error":
                    "Аудиофайл не выбран."
            }
        ), 400

    filename = (
        secure_filename(
            audio.filename
        )
        or
        "uploaded_audio.mp3"
    )

    if (
        Path(filename)
        .suffix
        .lower()
        != ".mp3"
    ):

        return jsonify(
            {
                "error":
                    "Сейчас прототип "
                    "принимает только MP3."
            }
        ), 400

    job_id = (
        uuid.uuid4().hex
    )

    uploaded_path = (
        UPLOAD_DIR
        /
        f"{job_id}_{filename}"
    )

    audio.save(
        uploaded_path
    )

    try:
        duration_seconds = get_audio_duration_seconds(
            uploaded_path
        )
    except Exception:
        uploaded_path.unlink(
            missing_ok=True
        )

        return jsonify(
            {
                "error":
                    "Не удалось определить "
                    "длительность MP3."
            }
        ), 400

    if duration_seconds > MAX_AUDIO_SECONDS:
        uploaded_path.unlink(
            missing_ok=True
        )

        return jsonify(
            {
                "error":
                    "Аудиозапись должна быть "
                    "не длиннее 3 минут."
            }
        ), 400

    with jobs_lock:

        jobs[job_id] = {

            "status":
                "queued",

            "progress":
                5,

            "stage":
                "Файл загружен.",

            "filename":
                filename,

            "audio_path":
                str(
                    uploaded_path
                ),

            "error":
                None
        }

    thread = (
        threading.Thread(
            target=
                process_job,

            args=(
                job_id,
                uploaded_path,
                filename
            ),

            daemon=True
        )
    )

    thread.start()

    return jsonify(
        {
            "job_id":
                job_id
        }
    )


@app.route(
    "/status/<job_id>"
)
def job_status(
    job_id
):

    with jobs_lock:

        job = jobs.get(
            job_id
        )

        if not job:

            return jsonify(
                {
                    "error":
                        "Задача не найдена."
                }
            ), 404

        data = dict(
            job
        )

    data["job_id"] = (
        job_id
    )

    return jsonify(
        data
    )


@app.route(
    "/dev-result"
)
def dev_result():

    if (
        not TRANSCRIPT_FILE.exists()
    ):

        return jsonify(
            {
                "error":
                    "Не найден transcript.txt"
            }
        ), 404

    if (
        not COMMITMENTS_FILE.exists()
    ):

        return jsonify(
            {
                "error":
                    "Не найден "
                    "commitments_v5_evidence.json"
            }
        ), 404

    if (
        not WORKING_AUDIO.exists()
    ):

        return jsonify(
            {
                "error":
                    "Не найден working_audio.mp3"
            }
        ), 404

    try:

        transcript = (
            TRANSCRIPT_FILE
            .read_text(
                encoding="utf-8"
            )
        )

        commitments = json.loads(
            COMMITMENTS_FILE
            .read_text(
                encoding="utf-8"
            )
        )

    except Exception as exc:

        return jsonify(
            {
                "error":
                    str(
                        exc
                    )
            }
        ), 500

    data = {

        "job_id":
            "dev",

        "status":
            "done",

        "progress":
            100,

        "stage":
            "Готово",

        "filename":
            WORKING_AUDIO.name,

        "audio_path":
            str(
                WORKING_AUDIO
            ),

        "transcript":
            transcript,

        "commitments":
            commitments,

        "timings":
            {},

        "dev_mode":
            True,

        "error":
            None
    }

    with jobs_lock:

        jobs["dev"] = dict(
            data
        )

    return jsonify(
        data
    )


@app.route(
    "/audio/<job_id>"
)
def job_audio(
    job_id
):

    with jobs_lock:

        job = jobs.get(
            job_id
        )

        if not job:

            return jsonify(
                {
                    "error":
                        "Задача не найдена."
                }
            ), 404

        audio_path = job.get(
            "audio_path"
        )

    if not audio_path:

        return jsonify(
            {
                "error":
                    "Аудиофайл не найден."
            }
        ), 404

    path = Path(
        audio_path
    )

    if not path.exists():

        return jsonify(
            {
                "error":
                    "Аудиофайл больше недоступен."
            }
        ), 404

    return send_file(
        path,
        mimetype="audio/mpeg",
        conditional=True
    )


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )