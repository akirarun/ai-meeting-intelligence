import json
import re
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

EVENTS_FILE = BASE_DIR / "events_v5.json"
TRANSCRIPT_FILE = BASE_DIR / "transcript.txt"

RESULT_FILE = BASE_DIR / "commitments_v5_evidence.json"
TEXT_FILE = BASE_DIR / "commitments_v5_evidence.txt"


def normalize(text):
    if not text:
        return ""

    text = str(text).lower()
    text = text.replace("ё", "е")

    text = re.sub(
        r"[—–]",
        "-",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def canonical_topic(topic):
    """
    Приводит разные названия одной задачи
    к одному стабильному topic.

    Особенно важно для:
    - deadlines, случайно попавших в название;
    - STT-искажений слова pricing;
    - небольших различий в формулировке.
    """

    t = normalize(topic)

    if not t:
        return ""

    # ---------------------------------
    # 1. ФОРМА ОБРАТНОЙ СВЯЗИ
    # ---------------------------------

    if (
        "форм" in t
        and
        "обратн" in t
        and
        "связ" in t
    ):
        return (
            "проверка формы обратной связи"
        )

    # ---------------------------------
    # 2. PRICING-БЛОК
    # ---------------------------------

    pricing_markers = [
        "pricing",
        "прайсинг",
        "прайсин",
        "причинг",
        "причин",
        "прайс",
    ]

    if (
        "блок" in t
        and
        any(
            marker in t
            for marker in pricing_markers
        )
    ):
        return (
            "обновление pricing-блока "
            "на лендинге"
        )

    # ---------------------------------
    # 3. СТАРЫЕ ИЗВЕСТНЫЕ TOPICS
    # ---------------------------------

    if (
        "оптимизац" in t
        and
        "изображ" in t
    ):
        return (
            "оптимизация изображений"
        )

    if (
        "отзыв" in t
        and
        "блок" in t
    ):
        return (
            "добавление блока с отзывами"
        )

    if (
        "crm" in t
        and
        "интеграц" in t
    ):
        return (
            "интеграция с crm"
        )

    if (
        "текст" in t
        and
        "главн" in t
    ):
        return (
            "поправка текстов "
            "на главной странице"
        )

    if (
        "дизайн" in t
        and
        "мобиль" in t
    ):
        return (
            "дизайн для мобильной версии"
        )

    # ---------------------------------
    # 4. Убираем deadline из topic
    # ---------------------------------

    deadline_suffixes = [
        r"\s+до\s+пятницы$",
        r"\s+к\s+пятнице$",
        r"\s+на\s+пятницу$",
        r"\s+до\s+понедельника$",
        r"\s+к\s+понедельнику$",
        r"\s+на\s+понедельник$",
        r"\s+до\s+среды$",
        r"\s+к\s+среде$",
        r"\s+на\s+среду$",
        r"\s+до\s+завтра$",
        r"\s+на\s+завтра$",
    ]

    for pattern in deadline_suffixes:
        t = re.sub(
            pattern,
            "",
            t
        )

    return t.strip()


def parse_transcript(transcript):
    records = []

    pattern = re.compile(
        r"^\[\s*([0-9.]+)s\s*-\s*"
        r"([0-9.]+)s\]\s*"
        r"([^:]+):\s*(.*)$"
    )

    for line in transcript.splitlines():
        line = line.strip()

        if not line:
            continue

        match = pattern.match(
            line
        )

        if not match:
            continue

        start = float(
            match.group(1)
        )

        end = float(
            match.group(2)
        )

        records.append({
            "start":
                start,

            "end":
                end,

            "timestamp":
                f"{start:.2f}s - {end:.2f}s",

            "speaker":
                match.group(3).strip(),

            "text":
                match.group(4).strip(),
        })

    return records


def quote_exists(
    quote,
    transcript
):
    if not quote:
        return False

    return (
        normalize(quote)
        in
        normalize(transcript)
    )


def find_record_for_quote(
    records,
    quote
):
    q = normalize(
        quote
    )

    if not q:
        return None

    for index, record in enumerate(
        records
    ):
        if (
            q
            in
            normalize(
                record["text"]
            )
        ):
            return (
                index,
                record
            )

    return None


def align_evidence(
    records,
    quote,
    fallback_timestamp
):
    found = find_record_for_quote(
        records,
        quote
    )

    if found:
        _, record = found

        return (
            quote,
            record["timestamp"]
        )

    return (
        quote,
        fallback_timestamp
    )


def split_sentences(text):
    return [
        part.strip()

        for part in re.split(
            r"(?<=[.!?])\s+",
            str(
                text or ""
            ).strip()
        )

        if part.strip()
    ]


def relative_deadline_from_text(
    text
):
    t = normalize(
        text
    )

    patterns = [
        (
            "к концу следующей недели",
            "к концу следующей недели"
        ),
        (
            "в начале следующей недели",
            "в начале следующей недели"
        ),
        (
            "в конце следующей недели",
            "в конце следующей недели"
        ),
        (
            "на следующей неделе",
            "на следующей неделе"
        ),
        (
            "на этой неделе",
            "на этой неделе"
        ),
        (
            "через две недели",
            "через две недели"
        ),
        (
            "через неделю",
            "через неделю"
        ),
        (
            "послезавтра",
            "послезавтра"
        ),
        (
            "завтра",
            "завтра"
        ),
    ]

    for marker, value in patterns:
        if marker in t:
            return value

    return None


def exact_relative_deadline(
    quote,
    deadline
):
    value = (
        relative_deadline_from_text(
            quote
        )
    )

    if value:
        return value

    value = (
        relative_deadline_from_text(
            deadline
        )
    )

    if value:
        return value

    return deadline


def has_relative_date(
    quote,
    deadline
):
    return bool(
        relative_deadline_from_text(
            quote
        )
        or
        relative_deadline_from_text(
            deadline
        )
    )


def is_confirmation(text):
    t = normalize(
        text
    )

    markers = [
        "хорошо",
        "ок",
        "окей",
        "согласен",
        "согласна",
        "договорились",
        "тогда",
        "ставим",
        "новый дедлайн",
        "переносим",
        "дедлайн",
    ]

    return any(
        marker in t
        for marker in markers
    )


def rejection_score(text):
    t = normalize(
        text
    )

    weights = {
        "не будем": 10,
        "отложим": 9,
        "не делаем": 9,
        "не делать": 8,
        "не в этот раз": 4,
        "пока не нужно": 8,
        "не нужно": 6,
    }

    score = 0

    for marker, weight in weights.items():
        if marker in t:
            score += weight

    return score


def best_sentence_in_record(record):
    best_sentence = None
    best_score = 0

    for sentence in split_sentences(
        record["text"]
    ):
        score = rejection_score(
            sentence
        )

        if score > best_score:
            best_sentence = sentence
            best_score = score

    return (
        best_sentence,
        best_score
    )


def find_proposal_rejection_evidence(
    records,
    original_quote
):
    found = find_record_for_quote(
        records,
        original_quote
    )

    if not found:
        return (
            original_quote,
            None
        )

    start_index, original_record = found

    best_quote = original_quote
    best_record = original_record

    best_score = rejection_score(
        original_quote
    )

    for offset in (
        -2,
        -1,
        0
    ):
        index = (
            start_index
            + offset
        )

        if index < 0:
            continue

        record = records[
            index
        ]

        sentence, score = (
            best_sentence_in_record(
                record
            )
        )

        if (
            sentence
            and
            score > best_score
        ):
            best_quote = sentence
            best_record = record
            best_score = score

    return (
        best_quote,
        best_record
    )


def find_deadline_confirmation(
    records,
    original_quote,
    deadline
):
    found = find_record_for_quote(
        records,
        original_quote
    )

    if not found:
        return (
            None,
            None
        )

    start_index, _ = found

    deadline_norm = normalize(
        deadline
    )

    for offset in range(
        1,
        5
    ):
        index = (
            start_index
            + offset
        )

        if index >= len(
            records
        ):
            break

        record = records[
            index
        ]

        for sentence in split_sentences(
            record["text"]
        ):
            sentence_norm = normalize(
                sentence
            )

            if (
                deadline_norm
                and
                deadline_norm
                not in sentence_norm
            ):
                continue

            if is_confirmation(
                sentence
            ):
                return (
                    sentence,
                    record
                )

    return (
        None,
        None
    )


def build_states(
    events,
    transcript
):
    states = {}

    records = parse_transcript(
        transcript
    )

    for event in events:
        topic = canonical_topic(
            event.get(
                "topic"
            )
        )

        event_type = event.get(
            "event_type"
        )

        if not topic:
            continue

        if topic not in states:
            states[topic] = {
                "topic":
                    topic,

                "status":
                    None,

                "owner":
                    None,

                "deadline":
                    None,

                "supporting_quote":
                    None,

                "timestamp":
                    None,

                "history":
                    [],
            }

        state = states[
            topic
        ]

        state[
            "history"
        ].append(
            event
        )

        owner = event.get(
            "owner"
        )

        deadline = event.get(
            "deadline"
        )

        quote = event.get(
            "supporting_quote"
        )

        timestamp = event.get(
            "timestamp"
        )

        quote, timestamp = (
            align_evidence(
                records,
                quote,
                timestamp
            )
        )

        if (
            event_type
            == "task_mentioned"
        ):
            if (
                state["status"]
                is None
            ):
                state[
                    "status"
                ] = "mentioned"

            if owner:
                state[
                    "owner"
                ] = owner

            if deadline:
                state[
                    "deadline"
                ] = deadline

            state[
                "supporting_quote"
            ] = quote

            state[
                "timestamp"
            ] = timestamp


        elif (
            event_type
            == "task_accepted"
        ):
            state[
                "status"
            ] = "active"

            if owner:
                state[
                    "owner"
                ] = owner

            if deadline:
                state[
                    "deadline"
                ] = deadline

            state[
                "supporting_quote"
            ] = quote

            state[
                "timestamp"
            ] = timestamp


        elif (
            event_type
            == "owner_assigned"
        ):
            state[
                "status"
            ] = "active"

            if owner:
                state[
                    "owner"
                ] = owner

            if deadline:
                state[
                    "deadline"
                ] = deadline

            state[
                "supporting_quote"
            ] = quote

            state[
                "timestamp"
            ] = timestamp


        elif (
            event_type
            == "deadline_assigned"
        ):
            if deadline:
                state[
                    "deadline"
                ] = deadline

            if owner:
                state[
                    "owner"
                ] = owner

            if (
                state["status"]
                in (
                    None,
                    "mentioned"
                )
            ):
                state[
                    "status"
                ] = "active"

            state[
                "supporting_quote"
            ] = quote

            state[
                "timestamp"
            ] = timestamp


        elif (
            event_type
            == "deadline_changed"
        ):
            if deadline:
                state[
                    "deadline"
                ] = deadline

            if owner:
                state[
                    "owner"
                ] = owner

            state[
                "status"
            ] = "active"

            confirmation, record = (
                find_deadline_confirmation(
                    records,
                    quote,
                    deadline
                )
            )

            if (
                confirmation
                and
                record
            ):
                state[
                    "supporting_quote"
                ] = confirmation

                state[
                    "timestamp"
                ] = record[
                    "timestamp"
                ]

            else:
                state[
                    "supporting_quote"
                ] = quote

                state[
                    "timestamp"
                ] = timestamp


        elif (
            event_type
            == "task_cancelled"
        ):
            state[
                "status"
            ] = "cancelled"

            state[
                "supporting_quote"
            ] = quote

            state[
                "timestamp"
            ] = timestamp


        elif (
            event_type
            == "proposal"
        ):
            if (
                state["status"]
                is None
            ):
                state[
                    "status"
                ] = "proposal"

            state[
                "supporting_quote"
            ] = quote

            state[
                "timestamp"
            ] = timestamp


        elif (
            event_type
            == "proposal_rejected"
        ):
            state[
                "status"
            ] = "rejected"

            stronger_quote, record = (
                find_proposal_rejection_evidence(
                    records,
                    quote
                )
            )

            state[
                "supporting_quote"
            ] = stronger_quote

            state[
                "timestamp"
            ] = (
                record["timestamp"]
                if record
                else timestamp
            )


        elif (
            event_type
            == "unresolved_dependency"
        ):
            state[
                "status"
            ] = "unresolved"

            if owner:
                state[
                    "owner"
                ] = owner

            if deadline:
                state[
                    "deadline"
                ] = deadline

            state[
                "supporting_quote"
            ] = quote

            state[
                "timestamp"
            ] = timestamp


    for state in states.values():
        state[
            "deadline"
        ] = (
            exact_relative_deadline(
                state.get(
                    "supporting_quote"
                ),
                state.get(
                    "deadline"
                )
            )
        )

    return states


def unresolved_missing(state):
    missing = []

    if not state.get(
        "owner"
    ):
        missing.append(
            "owner"
        )

    deadline = state.get(
        "deadline"
    )

    quote = state.get(
        "supporting_quote"
    )

    if not deadline:
        missing.append(
            "deadline"
        )

    elif has_relative_date(
        quote,
        deadline
    ):
        missing.append(
            "date_context"
        )

    return missing


def build_result(
    states,
    transcript
):
    result = {
        "accepted_tasks": [],
        "cancelled_tasks": [],
        "rejected_proposals": [],
        "unresolved_questions": [],
    }

    for state in states.values():
        topic = state[
            "topic"
        ]

        status = state[
            "status"
        ]

        owner = state[
            "owner"
        ]

        deadline = state[
            "deadline"
        ]

        quote = state[
            "supporting_quote"
        ]

        timestamp = state[
            "timestamp"
        ]

        common = {
            "timestamp":
                timestamp,

            "supporting_quote":
                quote,

            "quote_verified":
                quote_exists(
                    quote,
                    transcript
                ),
        }

        if status == "active":
            if owner:
                result[
                    "accepted_tasks"
                ].append({
                    "task":
                        topic,

                    "owner":
                        owner,

                    "deadline":
                        deadline,

                    **common,
                })

            else:
                result[
                    "unresolved_questions"
                ].append({
                    "question":
                        topic,

                    "missing":
                        unresolved_missing(
                            state
                        ),

                    "deadline":
                        deadline,

                    **common,
                })


        elif status in (
            "mentioned",
            "proposal"
        ):
            result[
                "unresolved_questions"
            ].append({
                "question":
                    topic,

                "missing":
                    unresolved_missing(
                        state
                    ),

                "deadline":
                    deadline,

                **common,
            })


        elif status == "cancelled":
            result[
                "cancelled_tasks"
            ].append({
                "task":
                    topic,

                **common,
            })


        elif status == "rejected":
            result[
                "rejected_proposals"
            ].append({
                "proposal":
                    topic,

                **common,
            })


        elif status == "unresolved":
            result[
                "unresolved_questions"
            ].append({
                "question":
                    topic,

                "missing":
                    unresolved_missing(
                        state
                    ),

                "deadline":
                    deadline,

                **common,
            })

    return result


def save_text(result):
    lines = []

    lines.append(
        "=== ПРИНЯТЫЕ ЗАДАЧИ ==="
    )

    if not result[
        "accepted_tasks"
    ]:
        lines.append(
            "  Нет"
        )

    for item in result[
        "accepted_tasks"
    ]:
        lines.extend([
            f"  Задача: {item['task']}",
            f"  Ответственный: {item['owner']}",
            f"  Дедлайн: {item['deadline']}",
            f'  Цитата: "{item["supporting_quote"]}"',
            f"  Таймкод: {item['timestamp']}",
            "  Цитата найдена: "
            + (
                "✓"
                if item[
                    "quote_verified"
                ]
                else "✗"
            ),
            "",
        ])

    lines.append(
        "=== ОТМЕНЁННЫЕ ЗАДАЧИ ==="
    )

    if not result[
        "cancelled_tasks"
    ]:
        lines.append(
            "  Нет"
        )

    for item in result[
        "cancelled_tasks"
    ]:
        lines.extend([
            f"  Задача: {item['task']}",
            f'  Цитата: "{item["supporting_quote"]}"',
            f"  Таймкод: {item['timestamp']}",
            "  Цитата найдена: "
            + (
                "✓"
                if item[
                    "quote_verified"
                ]
                else "✗"
            ),
            "",
        ])

    lines.append(
        "=== ОТКЛОНЁННЫЕ ПРЕДЛОЖЕНИЯ ==="
    )

    if not result[
        "rejected_proposals"
    ]:
        lines.append(
            "  Нет"
        )

    for item in result[
        "rejected_proposals"
    ]:
        lines.extend([
            f"  Предложение: {item['proposal']}",
            f'  Цитата: "{item["supporting_quote"]}"',
            f"  Таймкод: {item['timestamp']}",
            "  Цитата найдена: "
            + (
                "✓"
                if item[
                    "quote_verified"
                ]
                else "✗"
            ),
            "",
        ])

    lines.append(
        "=== НЕРЕШЁННЫЕ ВОПРОСЫ ==="
    )

    if not result[
        "unresolved_questions"
    ]:
        lines.append(
            "  Нет"
        )

    for item in result[
        "unresolved_questions"
    ]:
        lines.extend([
            f"  Вопрос: {item['question']}",
            f"  Не хватает: {item['missing']}",
            f"  Срок: {item['deadline']}",
            f'  Цитата: "{item["supporting_quote"]}"',
            f"  Таймкод: {item['timestamp']}",
            "  Цитата найдена: "
            + (
                "✓"
                if item[
                    "quote_verified"
                ]
                else "✗"
            ),
            "",
        ])

    TEXT_FILE.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8"
    )


def main():
    start = (
        time.perf_counter()
    )

    events_data = json.loads(
        EVENTS_FILE.read_text(
            encoding="utf-8"
        )
    )

    transcript = (
        TRANSCRIPT_FILE.read_text(
            encoding="utf-8"
        )
    )

    states = build_states(
        events_data.get(
            "events",
            []
        ),
        transcript
    )

    result = build_result(
        states,
        transcript
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    result[
        "python_resolution_seconds"
    ] = round(
        elapsed,
        4
    )

    RESULT_FILE.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    save_text(
        result
    )

    print("Готово.")
    print(
        f"JSON: {RESULT_FILE}"
    )
    print(
        f"Текст: {TEXT_FILE}"
    )
    print(
        f"Python: {elapsed:.4f} сек."
    )


if __name__ == "__main__":
    main()