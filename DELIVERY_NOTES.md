\# Delivery Notes



\## Проект



AI Meeting Intelligence



Браузерный прототип, который принимает запись разговора и извлекает не обычное резюме встречи, а финальное состояние договорённостей:



\- принятые задачи;

\- ответственных;

\- финальные дедлайны;

\- отменённые задачи;

\- отклонённые предложения;

\- нерешённые вопросы;

\- отсутствующие owner / deadline;

\- supporting quote;

\- supporting timestamp;

\- возможность прослушать соответствующий фрагмент исходного аудио.



\---



\# Что ожидалось от решения



Основная задача прототипа — корректно определить финальные договорённости после разговора, включая случаи, когда состояние задачи меняется по ходу встречи.



Необходимо было обработать как минимум следующие ситуации:



\- предложение задачи;

\- подтверждённая задача;

\- назначение ответственного;

\- назначение дедлайна;

\- изменение дедлайна;

\- отмена задачи;

\- отклонение предложения;

\- задача без назначенного owner;

\- задача без дедлайна;

\- относительная дата без достаточного calendar context;

\- неоднозначная или условная формулировка, которая не должна становиться твёрдым commitment.



Также требовалось предоставить evidence для результата:



\- supporting quote;

\- timestamp;

\- возможность прослушать соответствующий участок аудио.



\---



\# Что реализовано



Прототип реализует полный pipeline:



1\. Пользователь загружает MP3 через браузер.

2\. AssemblyAI выполняет speech-to-text.

3\. AssemblyAI определяет speaker labels и timestamps.

4\. Ollama + qwen2.5:7b анализирует transcript.

5\. LLM извлекает хронологические события.

6\. Deterministic Python resolver определяет финальное состояние.

7\. Flask UI показывает результат.

8\. Для каждого элемента отображаются supporting quote и timestamp.

9\. Пользователь может прослушать evidence segment прямо из браузера.



\---



\# Архитектура



Pipeline:



Audio



↓



AssemblyAI



Speech-to-text + speaker diarization + timestamps



↓



Ollama / qwen2.5:7b



Chronological event extraction



↓



Python deterministic resolver



Final-state resolution + evidence alignment



↓



Flask browser UI



Final commitments + supporting audio playback



\---



\# Использованные AI-инструменты и модели



\## Speech recognition



AssemblyAI



Используется для:



\- speech-to-text;

\- speaker labels;

\- timestamps.



В текущем `transcribe.py` указаны:



speaker\_labels=True



language\_code="ru"



Конкретная speech model явно не зафиксирована в коде, поэтому используется конфигурация AssemblyAI по умолчанию.



\---



\## LLM reasoning



Ollama



Модель:



qwen2.5:7b



Используется локально.



Основная задача модели:



\- прочитать transcript;

\- извлечь хронологический список событий;

\- определить тип каждого события;

\- извлечь owner;

\- извлечь deadline;

\- извлечь supporting quote;

\- сохранить смысл изменения договорённости.



LLM не формирует финальное состояние напрямую.



\---



\# Почему используется deterministic resolver



На ранних версиях pipeline финальное состояние формировалось дополнительным LLM-проходом.



Это оказалось нестабильно.



Пример:



первоначальный дедлайн:



Friday



позже изменён на:



Monday



После дополнительного LLM-прохода модель иногда снова возвращала старое состояние:



Friday



Поэтому финальная архитектура была изменена.



Теперь:



LLM отвечает за понимание текста и извлечение событий.



Python отвечает за состояние и применение изменений.



Это позволило сделать final-state logic более предсказуемой и тестируемой.



\---



\# Основные файлы



app.py



Flask application и browser UI.



transcribe.py



AssemblyAI transcription, speaker labels и timestamps.



analyze\_v5.py



Ollama / qwen2.5:7b event extraction.



resolve\_v5\_evidence.py



Deterministic final-state resolver.



TEST\_RESULTS.md



Подробные Expected / Actual результаты тестирования.



COST\_ESTIMATE.md



Оценка переменной стоимости обработки аудио.



README.md



Описание проекта, архитектуры, установки и запуска.



\---



\# Test recordings



Для воспроизводимого тестирования были подготовлены синтетические записи:



dialogue.mp3



dialogue\_v2.mp3



dialogue\_v3.mp3



Также сохранены соответствующие timeline-файлы:



timeline.txt



timeline\_v2.txt



timeline\_v3.txt



\---



\# Test 1



\## Цель



Проверить:



\- accepted task;

\- owner;

\- initial deadline;

\- corrected deadline;

\- rejected proposal;

\- cancelled task;

\- unresolved owner;

\- unresolved deadline;

\- relative date without calendar context.



\## Expected



Accepted:



Оптимизация изображений



Owner:



Оксана



Final deadline:



понедельник



Cancelled:



интеграция с CRM



Rejected:



добавление блока с отзывами



Unresolved:



поправка текстов на главной странице



Missing:



owner



deadline



Unresolved:



дизайн для мобильной версии



Deadline:



на следующей неделе



Missing:



owner



date\_context



\## Actual



Все 5 ожидаемых финальных элементов были получены.



Inclusion:



5 / 5



Exclusion checks:



6 / 6



Result:



PASS



\---



\# Test 2



\## Цель



Проверить, что система действительно анализирует новую запись, а не повторяет предыдущий результат.



Во второй версии разговора изменён финальный дедлайн.



Test 1:



Monday



Test 2:



Wednesday



\## Expected



Accepted:



Оптимизация изображений



Owner:



Оксана



Final deadline:



среда



Остальные состояния должны остаться эквивалентными Test 1.



\## Actual



Система корректно изменила финальный дедлайн на:



среда



Старый Friday не остался финальным состоянием.



Inclusion:



5 / 5



Exclusion checks:



6 / 6



Result:



PASS



\---



\# Test 3



\## Цель



Проверить неоднозначную и условную формулировку.



Ключевая реплика:



"Я, возможно, посмотрю завтра, если закончу текущие задачи."



Позже говорится:



"Тогда пока не фиксируем это за тобой."



И финально:



"По pricing-блоку тогда вернемся позже, когда будет понятно, кто сможет заняться."



\## Critical expected behavior



Система не должна создать:



Обновление pricing-блока → Оксана → завтра



\## Expected



Accepted:



Проверка формы обратной связи



Owner:



Оксана



Deadline:



пятница



Unresolved:



Обновление pricing-блока на лендинге



Missing:



owner



deadline



\## Первый результат



Critical false-commitment check:



PASS



Но обнаружились две проблемы:



\- accepted feedback-form task потерял Friday deadline;

\- одна и та же тема была разделена на несколько похожих topics.



Причиной стали различия topic names и ASR-искажения слова pricing.



Примеры:



pricing



причин



причинг



Также feedback-form task появился как:



проверка формы обратной связи



и:



проверка формы обратной связи до пятницы



\## Исправление



В deterministic resolver была добавлена canonical topic normalization.



После исправления:



Accepted:



Проверка формы обратной связи



Owner:



Оксана



Deadline:



пятница



Unresolved:



Обновление pricing-блока на лендинге



Missing:



owner



deadline



Inclusion:



2 / 2



Exclusion checks:



5 / 5



Final result:



PASS



\---



\# Итог контролируемых тестов



Test 1:



PASS



Test 2:



PASS



Test 3:



PASS



Expected final items:



Test 1:



5 / 5



Test 2:



5 / 5



Test 3:



2 / 2



Total:



12 / 12



Controlled exclusion checks:



Test 1:



6 / 6



Test 2:



6 / 6



Test 3:



5 / 5



Total:



17 / 17



Эти результаты относятся только к подготовленным контролируемым synthetic tests.



Они не означают 100% точность на любых реальных встречах.



\---



\# Output check



Для проверки качества результата использовался отдельный output check.



Для каждого final item проверялось:



\- соответствует ли task ожидаемой;

\- соответствует ли owner ожидаемому;

\- соответствует ли final deadline ожидаемому;

\- отсутствуют ли superseded deadlines;

\- отсутствуют ли cancelled tasks среди active commitments;

\- отсутствуют ли rejected proposals среди active commitments;

\- не придуман ли owner;

\- не придуман ли deadline;

\- сохранена ли relative date;

\- соответствует ли supporting quote исходному transcript;

\- совпадает ли timestamp с utterance, содержащим supporting quote.



Дополнительно в Test 3 отдельно проверялся критический false positive:



pricing block → Oksana → tomorrow



Он не был создан.



\---



\# Evidence verification



Supporting quote проверяется против transcript.



Если цитата найдена, результат содержит:



Цитата найдена: ✓



Timestamp привязывается к transcript utterance, содержащему соответствующую quote.



В browser UI пользователь может нажать:



▶ Прослушать



После этого воспроизводится соответствующий участок исходного аудио.



\---



\# Обнаруженные failure cases



\## 1. Corrected deadline regression



Проблема:



LLM-only final pass мог вернуть старый дедлайн после его изменения.



Исправление:



deterministic state resolution.



\---



\## 2. Weak supporting quote



Проблема:



ранняя версия могла выбрать слабую или косвенную цитату.



Исправление:



поиск более сильного supporting evidence в соседних utterances.



\---



\## 3. Quote / timestamp mismatch



Проблема:



правильная цитата могла получить timestamp другой реплики.



Исправление:



цитата повторно ищется в transcript, после чего timestamp берётся именно из соответствующей transcript record.



\---



\## 4. Relative date normalization



Проблема:



относительная дата могла потерять исходную формулировку.



Исправление:



literal relative wording имеет приоритет.



Пример:



на следующей неделе



сохраняется без преобразования в придуманную calendar date.



\---



\## 5. Topic fragmentation



Проблема:



одна задача могла иметь несколько похожих названий.



Исправление:



canonical topic normalization в deterministic resolver.



\---



\## 6. ASR distortion



Проблема:



AssemblyAI может искажать английские или технические слова.



Пример:



pricing



могло распознаваться как:



причин



или:



причинг



В controlled scenario эти варианты были нормализованы.



\---



\# Измеренное время обработки



\## Test 1



Full pipeline:



346.80 секунд



Примерно:



5 минут 47 секунд



Также один из предыдущих успешных запусков занял:



344.39 секунды



\---



\## Test 2



Full pipeline:



393.44 секунды



Примерно:



6 минут 33 секунды



\---



\## Test 3



Full pipeline:



193.53 секунды



Примерно:



3 минуты 14 секунд



\---



\# Resolver performance



Deterministic Python resolver работает за миллисекунды.



Зафиксированные значения:



0.0016 s



0.0019 s



0.0025 s



0.0029 s



0.0035 s



Основной latency bottleneck — локальный qwen2.5:7b.



\---



\# Cost estimate



Подробный расчёт находится в:



COST\_ESTIMATE.md



Так как конкретная AssemblyAI speech model явно не закреплена в `transcribe.py`, cost estimate содержит диапазон для актуальных вариантов модели.



Universal-2 + standard diarization:



примерно $0.0028 / audio minute



Universal-3.5 Pro + standard diarization:



примерно $0.0038 / audio minute



Local Ollama qwen2.5:7b:



$0 external API usage cost



Python resolver:



$0 external API usage cost



Локальный compute, электричество и production hosting отдельно не измерялись.



\---



\# Точное время разработки



Точное суммарное время разработки проекта не фиксировалось таймером.



Поэтому в delivery notes не указывается придуманное количество часов.



Измеренное время выполнения pipeline и отдельных стадий указано отдельно выше.



\---



\# Что сработало хорошо



\- speaker-aware transcript;

\- chronological event extraction;

\- deterministic final-state resolution;

\- corrected deadline handling;

\- cancellation handling;

\- rejected proposal handling;

\- unresolved owner handling;

\- unresolved deadline handling;

\- relative date preservation;

\- ambiguity handling;

\- quote verification;

\- timestamp alignment;

\- evidence audio playback;

\- changed-recording test;

\- controlled false-positive test.



\---



\# Текущие ограничения



Прототип не является production meeting platform.



Ограничения:



\- в основном протестирован на controlled Russian conversations;

\- основной сценарий — короткие записи;

\- qwen2.5:7b на CPU работает медленно;

\- качество diarization зависит от исходного аудио;

\- ASR может ошибаться на английских и технических словах;

\- topic normalization частично rule-based;

\- supporting timestamp относится к utterance, а не к точной word-level границе цитаты;

\- relative dates не переводятся в абсолютные даты без calendar context;

\- нет authentication;

\- нет multi-user storage;

\- нет production database;

\- нет production hosting;

\- нет calendar integration;

\- нет Jira / Trello / Notion integration.



\---



\# Что намеренно оставлено вне scope



Не реализованы:



\- Google Calendar integration;

\- Jira integration;

\- Trello integration;

\- Notion integration;

\- automatic task sending;

\- production authentication;

\- meeting history;

\- cloud storage.



Главный фокус прототипа — корректное извлечение финального состояния договорённостей.



\---



\# Product decision



Ключевое архитектурное решение проекта:



AI используется для понимания естественного языка.



Финальное состояние определяется deterministic logic.



Evidence показывается пользователю.



Кратко:



Understand with AI.



Resolve state deterministically.



Show evidence.



\---



\# Финальный статус



Browser UI:



WORKING



MP3 upload:



WORKING



AssemblyAI transcription:



WORKING



Speaker diarization:



WORKING



Timestamp extraction:



WORKING



Ollama qwen2.5:7b event extraction:



WORKING



Deterministic resolver:



WORKING



Accepted tasks:



WORKING



Corrected deadline:



WORKING



Cancelled tasks:



WORKING



Rejected proposals:



WORKING



Unresolved questions:



WORKING



Relative dates:



WORKING



Ambiguous commitment handling:



WORKING



Supporting quote:



WORKING



Supporting timestamp:



WORKING



Evidence audio playback:



WORKING



Test 1:



PASS



Test 2:



PASS



Test 3:



PASS



\---



\# Итог



Прототип успешно демонстрирует полный browser-based workflow:



MP3 meeting recording



→ transcription



→ speaker-aware transcript



→ AI event extraction



→ deterministic state resolution



→ final commitments



→ supporting quote



→ supporting timestamp



→ playable audio evidence



На трёх контролируемых сценариях система достигла ожидаемого финального состояния после документированных исправлений.

