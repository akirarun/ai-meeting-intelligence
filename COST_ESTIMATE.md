# Оценка стоимости обработки



## Общая схема



Текущий pipeline состоит из четырёх основных частей:



1. AssemblyAI — распознавание речи, speaker diarization и timestamps.

2. Ollama + qwen2.5:7b — локальный анализ транскрипта.

3. Python resolver — локальное определение финального состояния договорённостей.

4. Flask — локальный браузерный интерфейс.



В текущей архитектуре переменная внешняя API-стоимость на одну минуту аудио возникает в первую очередь на этапе AssemblyAI.



---



# AssemblyAI



Для pre-recorded audio AssemblyAI публикует следующие pay-as-you-go тарифы:



Universal-2: $0.15 / audio hour



Universal-3.5 Pro: $0.21 / audio hour



Standard speaker diarization: +$0.02 / audio hour



AssemblyAI указывает, что pre-recorded audio тарифицируется по фактической длительности аудио.



---



# Вариант с Universal-2



Speech-to-text:



$0.15 / hour



Speaker diarization:



+$0.02 / hour



Итого:



$0.17 / audio hour



Стоимость одной минуты:



$0.17 / 60 ≈ $0.00283 / audio minute



То есть примерно:



$0.0028 за минуту аудио



Для трёхминутной записи:



$0.00283 × 3 ≈ $0.0085



То есть примерно:



$0.0085 за 3 минуты аудио



---



# Вариант с Universal-3.5 Pro



Speech-to-text:



$0.21 / hour



Speaker diarization:



+$0.02 / hour



Итого:



$0.23 / audio hour



Стоимость одной минуты:



$0.23 / 60 ≈ $0.00383 / audio minute



То есть примерно:



$0.0038 за минуту аудио



Для трёхминутной записи:



$0.00383 × 3 ≈ $0.0115



То есть примерно:



$0.0115 за 3 минуты аудио



---



# Ollama / qwen2.5:7b



Анализ транскрипта выполняется локально через:



Ollama



qwen2.5:7b



Отдельной usage-based API-стоимости у локального Ollama нет:



External API cost: $0



При этом локальное выполнение не является буквально бесплатным с инфраструктурной точки зрения.



Оно использует:



- CPU или GPU;

- оперативную память;

- электроэнергию;

- ресурсы локального компьютера.



В рамках этого прототипа стоимость локального compute отдельно не измерялась, поэтому она не включена в стоимость API на минуту аудио.



---



# Python resolver



Финальное состояние договорённостей определяется локальным Python-кодом.



Внешняя API-стоимость:



$0



Измеренное время работы resolver на контролируемых тестах составляло примерно:



0.0016–0.0035 секунды



По сравнению с распознаванием речи и локальным LLM-анализом эта стадия практически не влияет на общую задержку.



---



# Flask UI



Flask-приложение работает локально.



Для текущего demo:



External API cost: $0



Production hosting в этот расчёт не включён.



---



# Генерация тестовых аудиозаписей



Для создания синтетических тестовых записей использовались:



edge-tts



imageio-ffmpeg



edge-tts используется только для подготовки синтетических тестовых данных. imageio-ffmpeg также используется в runtime для проверки длительности загружаемой записи.



Проверка длительности через imageio-ffmpeg выполняется локально и не создаёт отдельного внешнего API cost, поэтому она не включается в variable operating cost per audio minute.



---



# Итоговая оценка



Если используется:



AssemblyAI Universal-2



\+ standard speaker diarization



\+ local Ollama qwen2.5:7b



\+ local Python resolver



оценочная переменная API-стоимость составляет:



≈ $0.0028 / audio minute



Для трёхминутной встречи:



≈ $0.0085



Если используется:



AssemblyAI Universal-3.5 Pro



\+ standard speaker diarization



\+ local Ollama qwen2.5:7b



\+ local Python resolver



оценочная переменная API-стоимость составляет:



≈ $0.0038 / audio minute



Для трёхминутной встречи:



≈ $0.0115



---



# Что включено в расчёт



В расчёт включены:



- Speech-to-text

- Speaker diarization

- Local LLM reasoning

- Deterministic state resolution



При этом локальный LLM и resolver имеют:



External API cost: $0



---



# Что не включено



В расчёт не включены:



- стоимость компьютера;

- электричество;

- GPU или CPU infrastructure;

- production hosting;

- storage;

- network traffic;

- будущие платные LLM API;

- calendar integrations;

- task-management integrations;

- стоимость разработки и поддержки.



---



# Processing time



Измеренные полные времена обработки:



Test 1: 346.80 секунд



Test 2: 393.44 секунд



Test 3: 193.53 секунды



Основной bottleneck в текущей версии:



Ollama + qwen2.5:7b



на локальном CPU.



Сам deterministic resolver работает за миллисекунды.



---



# Cost / performance trade-off



Текущая архитектура сознательно оптимизирована прежде всего под корректность финального состояния, а не под realtime latency.



Возможные способы ускорения production-версии:



- GPU inference;

- меньшая локальная модель;

- hosted LLM;

- prompt optimization;

- structured generation;

- уменьшение размера контекста;

- более специализированная extraction model.



Это может изменить стоимость обработки, но уменьшить latency.



---



# Важное замечание



Точная стоимость зависит от того, какая именно AssemblyAI speech model фактически используется в transcribe.py.



Если в проекте используется Universal-2, основной estimate:



≈ $0.0028 / audio minute



Если используется Universal-3.5 Pro:



≈ $0.0038 / audio minute



В текущем transcribe.py параметр speech_model явно не задан, поэтому документ оставляет conditional estimate для двух возможных AssemblyAI speech models. Перед production deployment модель следует зафиксировать явно.



---



# Краткий итог



Universal-2 + diarization:



≈ $0.0028 / audio minute



≈ $0.0085 / 3-minute meeting



Universal-3.5 Pro + diarization:



≈ $0.0038 / audio minute



≈ $0.0115 / 3-minute meeting



Local Ollama qwen2.5:7b:



$0 external API cost



Python resolver:



$0 external API cost



Тарифы AssemblyAI проверены по публичной информации, актуальной на сентябрь 2026.
