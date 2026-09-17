# Test Results

## Test approach

The prototype was tested against independently defined expected commitments.

For each controlled recording, the expected result was written before evaluating the system output.

The evaluation focuses on:

1. Inclusion — all final agreed commitments and unresolved items should appear.
2. Exclusion — superseded, cancelled, rejected, or merely conditional information should not appear as active final commitments.
3. Evidence quality — each final item should include a supporting quote and a matching timestamp.
4. State tracking — corrected agreements should replace earlier states.
5. Ambiguity handling — tentative language must not be promoted into a commitment.

---

# Test 1 — Original conversation

## Purpose

Verify that the system can distinguish between:

- an accepted task;
- an assigned owner;
- an initially agreed deadline;
- a corrected deadline;
- a rejected proposal;
- a cancelled task;
- a task with no owner;
- a relative date with insufficient calendar context.

---

## Expected result

### Accepted task

**Task:** Optimize images  
**Owner:** Oksana  
**Final deadline:** Monday

The earlier Friday deadline must not remain as the final deadline.

### Cancelled task

**Task:** CRM integration

CRM integration must not appear as an active commitment.

### Rejected proposal

**Proposal:** Add a customer reviews block

The proposal must not appear as an accepted task.

### Unresolved item

**Task:** Fix homepage text

Missing:

- owner;
- deadline.

The system must not invent either value.

### Unresolved dependency

**Item:** Mobile design

**Relative timing:** "на следующей неделе"

Missing:

- owner;
- date context.

The system must preserve the relative wording instead of converting it to a calendar date without sufficient context.

---

## Actual result

### Accepted task

**Task:** Оптимизация изображений  
**Owner:** Оксана  
**Final deadline:** понедельник

Supporting quote:

> "Хорошо, тогда понедельник, новый дедлайн."

Timestamp:

**84.44s - 94.19s**

Result: PASS

---

### Cancelled task

**Task:** Интеграция с CRM

Supporting quote:

> "я говорила с клиентом, он сказал, что это пока не нужно, можно убрать из плана."

Timestamp:

**59.06s - 67.48s**

Result: PASS

---

### Rejected proposal

**Proposal:** Добавление блока с отзывами

Supporting quote:

> "Давай не будем сейчас это делать, отложим на потом."

Timestamp:

**46.52s - 53.56s**

Result: PASS

---

### Unresolved item

**Task:** Поправка текстов на главной странице

Missing:

- owner;
- deadline.

Supporting quote:

> "там пара неточностей."

Timestamp:

**84.44s - 94.19s**

Result: PASS

---

### Unresolved dependency

**Item:** Дизайн для мобильной версии

**Relative timing:** "на следующей неделе"

Missing:

- owner;
- date context.

Supporting quote:

> "дизайн для мобильной версии обещали прислать на следующей неделе."

Timestamp:

**101.73s - 106.67s**

Result: PASS

---

## Inclusion check

Expected final items: **5**

Correctly included: **5 / 5**

- accepted image optimization task;
- cancelled CRM integration;
- rejected reviews proposal;
- unresolved homepage text work;
- unresolved mobile design dependency.

**Inclusion result: 100%**

---

## Exclusion check

The following obsolete or invalid states were correctly excluded from active final commitments:

- Friday was not kept as the final image-optimization deadline.
- CRM integration was not presented as an active task.
- The reviews block was not presented as an accepted task.
- No owner was invented for homepage text fixes.
- No deadline was invented for homepage text fixes.
- No absolute calendar date was invented for "на следующей неделе".

**Exclusion checks passed: 6 / 6**

---

# Test 2 — Changed agreement

## Purpose

Verify that the system responds to a changed agreement instead of reproducing the result from the first recording.

Only one important agreement was changed:

**The final image-optimization deadline was changed to Wednesday.**

---

## Expected result

### Accepted task

**Task:** Optimize images  
**Owner:** Oksana  
**Final deadline:** Wednesday

The earlier Friday deadline must not remain as the final deadline.

All other final states should remain equivalent to Test 1.

### Cancelled task

**Task:** CRM integration

### Rejected proposal

**Proposal:** Add a customer reviews block

### Unresolved item

**Task:** Fix homepage text

Missing:

- owner;
- deadline.

### Unresolved dependency

**Item:** Mobile design

**Relative timing:** "на следующей неделе"

Missing:

- owner;
- date context.

---

## Actual result

### Accepted task

**Task:** Оптимизация изображений  
**Owner:** Оксана  
**Final deadline:** среда

Supporting quote:

> "Хорошо, тогда среда, новый дедлайн."

Timestamp:

**85.38s - 94.02s**

Result: PASS

---

### Cancelled task

**Task:** Интеграция с CRM

Supporting quote:

> "я говорила с клиентом, он сказал, что это пока не нужно, можно убрать из плана."

Timestamp:

**59.84s - 68.26s**

Result: PASS

---

### Rejected proposal

**Proposal:** Добавление блока с отзывами

Supporting quote:

> "Хм, идея неплохая, но у нас и так тесно по срокам. Давай не будем сейчас это делать, отложим на потом."

Timestamp:

**47.08s - 54.10s**

Result: PASS

---

### Unresolved item

**Task:** Поправка текстов на главной странице

Missing:

- owner;
- deadline.

Supporting quote:

> "там пара неточностей."

Timestamp:

**85.38s - 94.02s**

Result: PASS

---

### Unresolved dependency

**Item:** Дизайн для мобильной версии

**Relative timing:** "на следующей неделе"

Missing:

- owner;
- date context.

Supporting quote:

> "дизайн для мобильной версии обещали прислать на следующей неделе."

Timestamp:

**101.60s - 106.62s**

Result: PASS

---

## Inclusion check

Expected final items: **5**

Correctly included: **5 / 5**

**Inclusion result: 100%**

---

## Exclusion check

The changed recording correctly replaced the earlier deadline state:

- Friday was not retained as the final deadline.
- Wednesday became the final deadline.
- CRM integration was not presented as active.
- The reviews proposal was not presented as accepted.
- No owner or deadline was invented for homepage text fixes.
- The relative mobile-design date was preserved without inventing an absolute date.

**Exclusion checks passed: 6 / 6**

---

# Cross-version change check

| Field | Test 1 | Test 2 |
|---|---|---|
| Task | Optimize images | Optimize images |
| Owner | Oksana | Oksana |
| Initial deadline | Friday | Friday |
| Final deadline | Monday | Wednesday |
| Correct final state | PASS | PASS |

The prototype correctly changed the final deadline from **Monday in Test 1** to **Wednesday in Test 2** based on the changed recording.

This demonstrates that the output is derived from the current conversation rather than copied from a previous result.

---

# Test 3 — Ambiguous / conditional commitment

## Purpose

Verify that tentative, conditional, or explicitly unconfirmed language is not converted into a false accepted commitment.

This test contains:

- one valid accepted task as a control;
- one ambiguous task with tentative language;
- a direct statement that the tentative task should not yet be assigned;
- a later statement that the team will return to the topic once ownership is clear.

---

## Expected result

### Accepted task

**Task:** Check the feedback form  
**Owner:** Oksana  
**Deadline:** Friday

### Unresolved task

**Task:** Update the pricing block on the landing page

Missing:

- owner;
- deadline.

Reason:

- Oksana said she might look at it;
- her statement was conditional on finishing current work;
- Artem explicitly said not to assign the task to her yet;
- the team agreed to return to the topic later.

### Cancelled

None.

### Rejected

None.

---

## Critical PASS criterion

The system must **not** produce the following accepted commitment:

**Update pricing block → Oksana → tomorrow**

The phrases:

- "возможно";
- "если закончу текущие задачи";
- "пока не фиксируем это за тобой";
- "посмотрим по загрузке";
- "вернёмся позже";

must not be interpreted as a firm commitment.

---

## First full pipeline result

The first Test 3 pipeline run correctly avoided the false commitment, but exposed a topic-merging problem.

Observed issues:

- the accepted feedback-form task lost its Friday deadline in the final result;
- semantically identical feedback-form topics were split;
- the pricing-block topic was duplicated because speech recognition produced variants such as "причин-блок" / "причинг-блок".

Critical false-commitment check:

**PASS**

Overall first Test 3 result:

**FAIL**

Reason:

- accepted feedback-form task lost Friday deadline;
- semantically identical topics were split into duplicate unresolved items.

---

## Resolver fix

The deterministic resolver was updated to normalize and merge topic variants.

Examples:

### Feedback form

These variants are now merged:

- "проверка формы обратной связи до пятницы"
- "проверка формы обратной связи"

Canonical topic:

**проверка формы обратной связи**

### Pricing block

Speech-recognition variants such as:

- pricing-блок;
- прайсинг-блок;
- причинг-блок;
- причин-блок;

are normalized to:

**обновление pricing-блока на лендинге**

This allows owner and deadline events to be merged into the same final state while avoiding duplicate unresolved items.

---

## Final Test 3 actual result

### Accepted task

**Task:** Проверка формы обратной связи  
**Owner:** Оксана  
**Deadline:** пятница

Supporting quote:

> "Сделаю до пятницы."

Timestamp:

**39.19s - 42.33s**

Result: PASS

---

### Unresolved task

**Task:** Обновление pricing-блока на лендинге

Missing:

- owner;
- deadline.

Supporting quote:

> "По причинг-блоку тогда вернемся позже, когда будет понятно, кто сможет заняться."

Timestamp:

**44.11s - 54.95s**

Result: PASS

---

### Cancelled

None.

### Rejected

None.

---

## Test 3 inclusion check

Expected final items: **2**

Correctly included: **2 / 2**

- accepted feedback-form task;
- unresolved pricing-block task.

**Inclusion result: 100%**

---

## Test 3 exclusion check

The system correctly excluded the following false state:

- pricing block was not assigned to Oksana;
- "tomorrow" was not used as an accepted deadline;
- conditional wording was not treated as a commitment;
- no duplicate pricing-block unresolved items remained after topic normalization;
- no duplicate feedback-form unresolved item remained after topic normalization.

**Exclusion checks passed: 5 / 5**

---

## Test 3 overall result

**PASS**

The system successfully distinguished between:

- a real accepted commitment;
- tentative intention;
- conditional language;
- an explicitly unconfirmed assignment;
- a task that should remain unresolved.

This is the main ambiguity / clarification safety check for the prototype.

---

# Processing time

## Test 1

Measured full processing time:

**346.80 seconds**

Approximately:

**5 minutes 47 seconds**

A previous successful pipeline run was also measured at approximately:

**344 seconds**

---

## Test 2

Measured full processing time:

**393.44 seconds**

Approximately:

**6 minutes 33 seconds**

---

## Test 3

Measured full processing time:

**193.53 seconds**

Approximately:

**3 minutes 14 seconds**

---

## Resolver timing

The deterministic Python resolver runs in milliseconds.

Measured examples:

- 0.0016 s
- 0.0019 s
- 0.0025 s
- 0.0029 s
- 0.0035 s

---

# Performance observation

Speech transcription typically completes in roughly **10–11 seconds** on the first two controlled recordings.

The main latency comes from local LLM reasoning with:

**Ollama + qwen2.5:7b**

The deterministic Python resolver is comparatively negligible.

The architecture separates:

1. speech recognition;
2. AI event extraction;
3. deterministic final-state resolution.

This separation was introduced after earlier experiments showed that a second LLM pass could forget or overwrite corrected state such as a changed deadline.

---

# Failure cases discovered during development

The controlled tests exposed several concrete failure modes.

## 1. Corrected deadline regression

Earlier LLM-only versions sometimes retained the original Friday deadline instead of the corrected Monday deadline.

Fix:

- extract chronological events once;
- resolve final state deterministically in Python.

---

## 2. Weak supporting evidence

An early result used:

> "Кей, согласен, не в этот раз."

as evidence for rejecting the reviews block.

A stronger supporting quote was selected instead:

> "Давай не будем сейчас это делать, отложим на потом."

---

## 3. Quote / timestamp mismatch

Some results initially contained a correct quote but a timestamp from a different utterance.

Fix:

- supporting quotes are aligned back to the transcript;
- the timestamp is taken from the transcript line that actually contains the quote.

---

## 4. Relative date normalization

The second test initially changed:

> "на следующей неделе"

into a less faithful normalized form.

Fix:

- preserve the relative wording from the supporting quote;
- mark missing `date_context`.

---

## 5. Topic fragmentation

Test 3 exposed semantically identical topics with different names.

Examples:

- feedback-form topic with and without deadline in the topic string;
- pricing / причинг / причин speech-recognition variants.

Fix:

- deterministic canonical topic normalization;
- merge owner / deadline events into the same task state.

---

# Evidence playback

The browser prototype allows the user to click:

**▶ Прослушать**

for each result.

The player:

- seeks to the supporting timestamp;
- plays only the supporting audio segment;
- stops automatically at the end of the segment.

This makes each extracted commitment auditable against the original recording.

---

# Final controlled test summary

| Test | Main purpose | Result |
|---|---|---|
| Test 1 | Corrected deadline, cancellation, rejection, unresolved fields | PASS |
| Test 2 | Changed agreement in a second recording | PASS |
| Test 3 | Ambiguous / conditional commitment safety | PASS |

---

# Aggregate controlled results

## Expected final items

Test 1:

**5 / 5**

Test 2:

**5 / 5**

Test 3:

**2 / 2**

Total:

**12 / 12**

### Controlled inclusion accuracy

**100%**

---

## Exclusion checks

Test 1:

**6 / 6**

Test 2:

**6 / 6**

Test 3:

**5 / 5**

Total:

**17 / 17**

### Controlled exclusion checks passed

**100%**

---

# Overall result

Across the three controlled recordings, the prototype correctly handled:

- accepted commitments;
- ownership;
- initial deadlines;
- corrected deadlines;
- changed agreements across recordings;
- cancellation;
- proposal rejection;
- missing owner;
- missing deadline;
- relative-date ambiguity;
- conditional language;
- tentative intent;
- explicit non-assignment;
- topic normalization;
- supporting quotes;
- supporting timestamps;
- evidence playback;
- deterministic final-state resolution.

The three controlled scenarios all reached the expected final state after the documented resolver fixes.