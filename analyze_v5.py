import json
import re
import time
from pathlib import Path

import requests


MODEL = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/chat"

BASE_DIR = Path(__file__).parent
TRANSCRIPT_FILE = BASE_DIR / "transcript.txt"

EVENTS_FILE = BASE_DIR / "events_v5.json"
RESULT_FILE = BASE_DIR / "commitments_v5.json"
TEXT_FILE = BASE_DIR / "commitments_v5.txt"


def ask_ollama(system_prompt, user_prompt):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_ctx": 8192
            },
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        },
        timeout=600
    )

    response.raise_for_status()

    content = response.json()["message"]["content"]
    return json.loads(content)


def normalize_text(text):
    if not text:
        return ""

    text = text.lower()
    text = text.replace("ё", "е")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def quote_exists(quote, transcript):
    if not quote:
        return False

    return normalize_text(quote) in normalize_text(transcript)


def extract_events(transcript):
    system_prompt = """
Ты анализируешь проектный разговор.

Твоя единственная задача — построить хронологический журнал событий.
НЕ формируй финальный список задач.

Каждое событие должно отражать одно изменение состояния.

Типы:

task_accepted
task_mentioned
owner_assigned
deadline_assigned
deadline_changed
task_cancelled
proposal
proposal_rejected
unresolved_dependency

ОЧЕНЬ ВАЖНО:

1. Если меняется дедлайн существующей задачи, topic ДОЛЖЕН быть названием
   той же задачи, а не "перенос дедлайна".

ПЛОХО:
topic = "Перенос дедлайна на понедельник"

ХОРОШО:
topic = "Оптимизация изображений"

2. Если дедлайн явно назван, записывай его в поле deadline.

3. Если владелец явно назван, записывай owner.

4. Не выдумывай owner или deadline.

5. Не переноси данные между разными задачами.

6. Если идея отклонена, это proposal_rejected.

7. Если задача отменена, это task_cancelled.

8. supporting_quote должна быть дословной и короткой.

9. Если один факт подтверждается соседними репликами,
   выбери цитату, которая лучше всего подтверждает изменение.

Верни только JSON:

{
  "speakers": {
    "A": "имя или null",
    "B": "имя или null"
  },
  "events": [
    {
      "sequence": 1,
      "topic": "название конкретной задачи или темы",
      "event_type": "...",
      "owner": null,
      "deadline": null,
      "timestamp": "...",
      "supporting_quote": "...",
      "meaning": "..."
    }
  ]
}
"""

    return ask_ollama(system_prompt, transcript)


def canonical_topic(topic):
    """
    Лёгкая нормализация названий тем.
    Никакой AI здесь нет.
    """

    if not topic:
        return ""

    t = normalize_text(topic)

    replacements = {
        "оптимизация изображений на главной странице": "оптимизация изображений",
        "оптимизация изображений": "оптимизация изображений",

        "добавление блока с отзывами клиентов": "добавление блока с отзывами",
        "добавление блока с отзывами": "добавление блока с отзывами",

        "отмена интеграции с crm": "интеграция с crm",
        "интеграция с crm": "интеграция с crm",

        "поправка текстов на главной странице": "поправка текстов на главной странице",
        "правки текстов на главной странице": "поправка текстов на главной странице",

        "дизайн для мобильной версии": "дизайн для мобильной версии"
    }

    return replacements.get(t, t)


def build_final_state(events):
    """
    Главная часть v5.

    Финальное состояние строит Python,
    а не второй запрос к модели.
    """

    states = {}

    last_active_task = None

    for event in events:
        topic = canonical_topic(event.get("topic"))
        event_type = event.get("event_type")
        owner = event.get("owner")
        deadline = event.get("deadline")
        quote = event.get("supporting_quote")
        timestamp = event.get("timestamp")
        sequence = event.get("sequence")

        if not topic:
            continue

        if topic not in states:
            states[topic] = {
                "topic": topic,
                "status": None,
                "owner": None,
                "deadline": None,
                "supporting_quote": None,
                "timestamp": None,
                "sequence": sequence,
                "history": []
            }

        state = states[topic]

        state["history"].append(event)

        if event_type == "task_accepted":
            state["status"] = "active"

            if owner:
                state["owner"] = owner

            if deadline:
                state["deadline"] = deadline

            state["supporting_quote"] = quote
            state["timestamp"] = timestamp

            last_active_task = topic

        elif event_type == "task_mentioned":
            if state["status"] is None:
                state["status"] = "mentioned"

            if owner:
                state["owner"] = owner

            if deadline:
                state["deadline"] = deadline

            state["supporting_quote"] = quote
            state["timestamp"] = timestamp

        elif event_type == "owner_assigned":
            state["owner"] = owner
            state["supporting_quote"] = quote
            state["timestamp"] = timestamp

            if state["status"] is None:
                state["status"] = "active"

            last_active_task = topic

        elif event_type == "deadline_assigned":
            state["deadline"] = deadline
            state["supporting_quote"] = quote
            state["timestamp"] = timestamp

            if state["status"] is None:
                state["status"] = "active"

            last_active_task = topic

        elif event_type == "deadline_changed":
            target_topic = topic

            # Защита от старого формата,
            # если модель снова назовёт тему "перенос дедлайна..."
            if (
                "перенос дедлайна" in topic
                or "дедлайн" in topic
                and topic not in states
            ):
                if last_active_task:
                    target_topic = last_active_task

            if target_topic not in states:
                states[target_topic] = {
                    "topic": target_topic,
                    "status": "active",
                    "owner": None,
                    "deadline": None,
                    "supporting_quote": None,
                    "timestamp": None,
                    "sequence": sequence,
                    "history": []
                }

            target_state = states[target_topic]

            target_state["deadline"] = deadline
            target_state["supporting_quote"] = quote
            target_state["timestamp"] = timestamp

            if target_state["status"] is None:
                target_state["status"] = "active"

            target_state["history"].append(event)

            last_active_task = target_topic

        elif event_type == "task_cancelled":
            state["status"] = "cancelled"
            state["supporting_quote"] = quote
            state["timestamp"] = timestamp

            if last_active_task == topic:
                last_active_task = None

        elif event_type == "proposal":
            if state["status"] is None:
                state["status"] = "proposal"

            state["supporting_quote"] = quote
            state["timestamp"] = timestamp

        elif event_type == "proposal_rejected":
            state["status"] = "rejected"
            state["supporting_quote"] = quote
            state["timestamp"] = timestamp

        elif event_type == "unresolved_dependency":
            state["status"] = "unresolved"

            if deadline:
                state["deadline"] = deadline

            state["supporting_quote"] = quote
            state["timestamp"] = timestamp

    return states


def infer_relative_deadline_from_quote(state):
    """
    Если модель не положила относительный срок в deadline,
    но он явно есть в цитате — забираем его обычными правилами.
    """

    if state.get("deadline"):
        return

    quote = normalize_text(state.get("supporting_quote"))

    patterns = [
        ("на следующей неделе", "на следующей неделе"),
        ("к понедельнику", "к понедельнику"),
        ("на понедельник", "понедельник"),
        ("к пятнице", "к пятнице"),
        ("в пятницу", "пятница"),
        ("завтра", "завтра"),
        ("послезавтра", "послезавтра")
    ]

    for marker, value in patterns:
        if marker in quote:
            state["deadline"] = value
            return


def states_to_result(states, transcript):
    result = {
        "accepted_tasks": [],
        "cancelled_tasks": [],
        "rejected_proposals": [],
        "unresolved_questions": []
    }

    for topic, state in states.items():
        infer_relative_deadline_from_quote(state)

        status = state.get("status")
        owner = state.get("owner")
        deadline = state.get("deadline")
        quote = state.get("supporting_quote")
        timestamp = state.get("timestamp")

        quote_verified = quote_exists(quote, transcript)

        if status == "active":
            if owner:
                result["accepted_tasks"].append({
                    "task": topic,
                    "owner": owner,
                    "deadline": deadline,
                    "timestamp": timestamp,
                    "supporting_quote": quote,
                    "quote_verified": quote_verified
                })
            else:
                missing = ["owner"]

                if not deadline:
                    missing.append("deadline")

                result["unresolved_questions"].append({
                    "question": topic,
                    "missing": missing,
                    "deadline": deadline,
                    "timestamp": timestamp,
                    "supporting_quote": quote,
                    "quote_verified": quote_verified
                })

        elif status == "mentioned":
            missing = ["owner"]

            if not deadline:
                missing.append("deadline")

            result["unresolved_questions"].append({
                "question": topic,
                "missing": missing,
                "deadline": deadline,
                "timestamp": timestamp,
                "supporting_quote": quote,
                "quote_verified": quote_verified
            })

        elif status == "cancelled":
            result["cancelled_tasks"].append({
                "task": topic,
                "timestamp": timestamp,
                "supporting_quote": quote,
                "quote_verified": quote_verified
            })

        elif status == "rejected":
            result["rejected_proposals"].append({
                "proposal": topic,
                "timestamp": timestamp,
                "supporting_quote": quote,
                "quote_verified": quote_verified
            })

        elif status == "unresolved":
            missing = ["owner"]

            if deadline:
                missing.append("date_context")
            else:
                missing.append("deadline")

            result["unresolved_questions"].append({
                "question": topic,
                "missing": missing,
                "deadline": deadline,
                "timestamp": timestamp,
                "supporting_quote": quote,
                "quote_verified": quote_verified
            })

    return result


def fix_known_relative_date_context(result):
    """
    Уточняем missing после финальной сборки.
    """

    for item in result["unresolved_questions"]:
        missing = item.get("missing", [])
        deadline = item.get("deadline")

        if deadline:
            d = normalize_text(deadline)

            relative = any(
                marker in d
                for marker in [
                    "следующей неделе",
                    "понедельник",
                    "пятниц",
                    "завтра",
                    "послезавтра"
                ]
            )

            if relative:
                if "date_context" not in missing:
                    missing.append("date_context")

                if "deadline" in missing:
                    missing.remove("deadline")

        item["missing"] = missing


def save_text(result):
    lines = []

    lines.append("=== ПРИНЯТЫЕ ЗАДАЧИ ===")

    if not result["accepted_tasks"]:
        lines.append("  Нет")

    for item in result["accepted_tasks"]:
        lines.append(f"  Задача: {item.get('task')}")
        lines.append(f"  Ответственный: {item.get('owner')}")
        lines.append(f"  Дедлайн: {item.get('deadline')}")
        lines.append(f"  Цитата: \"{item.get('supporting_quote')}\"")
        lines.append(f"  Таймкод: {item.get('timestamp')}")
        lines.append(
            f"  Цитата найдена: "
            f"{'✓' if item.get('quote_verified') else '✗'}"
        )
        lines.append("")

    lines.append("=== ОТМЕНЁННЫЕ ЗАДАЧИ ===")

    if not result["cancelled_tasks"]:
        lines.append("  Нет")

    for item in result["cancelled_tasks"]:
        lines.append(f"  Задача: {item.get('task')}")
        lines.append(f"  Цитата: \"{item.get('supporting_quote')}\"")
        lines.append(f"  Таймкод: {item.get('timestamp')}")
        lines.append(
            f"  Цитата найдена: "
            f"{'✓' if item.get('quote_verified') else '✗'}"
        )
        lines.append("")

    lines.append("=== ОТКЛОНЁННЫЕ ПРЕДЛОЖЕНИЯ ===")

    if not result["rejected_proposals"]:
        lines.append("  Нет")

    for item in result["rejected_proposals"]:
        lines.append(f"  Предложение: {item.get('proposal')}")
        lines.append(f"  Цитата: \"{item.get('supporting_quote')}\"")
        lines.append(f"  Таймкод: {item.get('timestamp')}")
        lines.append(
            f"  Цитата найдена: "
            f"{'✓' if item.get('quote_verified') else '✗'}"
        )
        lines.append("")

    lines.append("=== НЕРЕШЁННЫЕ ВОПРОСЫ ===")

    if not result["unresolved_questions"]:
        lines.append("  Нет")

    for item in result["unresolved_questions"]:
        lines.append(f"  Вопрос: {item.get('question')}")
        lines.append(f"  Не хватает: {item.get('missing')}")
        lines.append(f"  Срок: {item.get('deadline')}")
        lines.append(f"  Цитата: \"{item.get('supporting_quote')}\"")
        lines.append(f"  Таймкод: {item.get('timestamp')}")
        lines.append(
            f"  Цитата найдена: "
            f"{'✓' if item.get('quote_verified') else '✗'}"
        )
        lines.append("")

    TEXT_FILE.write_text("\n".join(lines), encoding="utf-8")


def main():
    if not TRANSCRIPT_FILE.exists():
        raise FileNotFoundError(
            f"Не найден файл {TRANSCRIPT_FILE}"
        )

    transcript = TRANSCRIPT_FILE.read_text(encoding="utf-8")

    print("Шаг 1/2: извлекаю события через Ollama...")
    start = time.perf_counter()

    events_result = extract_events(transcript)

    ai_elapsed = time.perf_counter() - start

    EVENTS_FILE.write_text(
        json.dumps(events_result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"AI-анализ готов за {ai_elapsed:.2f} сек.")

    print("\nШаг 2/2: собираю финальное состояние через Python...")
    python_start = time.perf_counter()

    states = build_final_state(events_result.get("events", []))
    result = states_to_result(states, transcript)
    fix_known_relative_date_context(result)

    python_elapsed = time.perf_counter() - python_start
    total_elapsed = time.perf_counter() - start

    result["timing"] = {
        "ai_event_extraction_seconds": round(ai_elapsed, 2),
        "python_state_resolution_seconds": round(python_elapsed, 4),
        "total_seconds": round(total_elapsed, 2)
    }

    result["model"] = MODEL
    result["architecture"] = "LLM event extraction + deterministic Python state resolution"

    RESULT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    save_text(result)

    print("\nГотово.")
    print(f"События: {EVENTS_FILE}")
    print(f"JSON: {RESULT_FILE}")
    print(f"Текст: {TEXT_FILE}")

    print("\nВремя:")
    print(f"  AI: {ai_elapsed:.2f} сек.")
    print(f"  Python: {python_elapsed:.4f} сек.")
    print(f"  Всего: {total_elapsed:.2f} сек.")


if __name__ == "__main__":
    main()