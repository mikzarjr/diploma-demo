# База данных — структура и связи

## Таблицы

| Таблица | Назначение |
|---|---|
| `users` | Пользователи системы (менеджер, руководитель, администратор) |
| `calls` | Звонки: аудио, транскрипт, summary, статус обработки |
| `speaker_turns` | Реплики звонка с таймкодами и ролью говорящего |
| `checks` | Настраиваемые проверки (rule-based или LLM-based) |
| `check_results` | Результаты применения проверки к звонку или реплике |

---

## Связи

```
users
 └──< calls                (manager_id → users.id)
       ├──< speaker_turns  (call_id → calls.id)
       └──< check_results  (call_id → calls.id)
                ├──> checks          (check_id → checks.id)
                └──> speaker_turns   (speaker_turn_id → speaker_turns.id, nullable)
```

---

## Ключевые моменты

**`check_results.speaker_turn_id` — nullable.**
- Если `check.scope = "call"` → поле пустое, результат относится ко всему звонку.
- Если `check.scope = "segment"` → поле заполнено, результат привязан к конкретной реплике.

**`checks` не связан с `calls` напрямую** — одна проверка применяется к множеству звонков через `check_results`.

**`calls.status`** отражает этап обработки: `new → transcribed → analyzed → error`.
