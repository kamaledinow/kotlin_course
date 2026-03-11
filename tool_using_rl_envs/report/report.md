# Отчёт по экспериментам

## 1) Дизайн среды
Среда — календарный планировщик: нужно переставить встречу в заданный слот, не нарушив занятость участников.
С ростом `difficulty` увеличиваются:
- число людей,
- число встреч,
- число дней/слотов,
- плотность конфликтов.

## 2) Верификатор и метрики
`DefaultTrajectoryVerifier` прогоняет заданную траекторию действий и считает:
- `success`
- `total_reward`
- `steps`
- `tool_calls`
- `policy_violations`
- `invalid_actions`
- `terminated_early`

## 3) Сравнение политик
- `NaivePolicy`: сразу вызывает `move_meeting` (часто нарушает confirmation rule).
- `PromptBaselinePolicy`: сначала запрос подтверждения, затем `move_meeting`, потом `finalize`.
- `TinyGRPOPolicy`: baseline + адаптация склонности к лишнему `get_calendar` через group-relative reward.

На `eval_d3` baseline и tiny-GRPO обычно стабильно обгоняют naive по success и policy violations.

## 4) Где proxy reward может навредить
1. Агент может переоптимизировать число шагов и пропускать полезные проверки.
2. Агент может минимизировать tool calls ценой хрупкости поведения на out-of-distribution кейсах.
3. Слишком сильный штраф за invalid format может привести к «молчаливой» стратегии (free-text без решения).

## 5) Что улучшить
- Добавить более реалистичные user confirmations (шум, неоднозначность).
- Сделать частично наблюдаемое состояние (не все сущности доступны сразу).
- Перейти от toy-GRPO к настоящему RL loop с LLM policy и sampled rollouts.
- Добавить multi-env обучение (объединение задачи недели 1 + этой среды).
