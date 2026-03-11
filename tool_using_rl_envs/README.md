# Tool-Using RL Envs: Meeting Scheduler

Мини-проект для ДЗ недели 4: многошаговый LLM-агент с tool-calls, процедурной генерацией и траекторным верификатором.

## Идея среды
Агент должен перенести встречу `M*` в целевой слот без конфликтов.

Типы действий:
1. Free-text сообщение (например запрос подтверждения).
2. Структурированный вызов инструмента в формате:
   `TOOL_CALL {"name": "...", "args": {...}}`

Инструменты:
- `get_calendar(person, range)`
- `get_meeting(meeting_id)`
- `move_meeting(meeting_id, day, slot)`
- `finalize()`

## Policy rules
1. **Confirmation rule**: state-changing `move_meeting` разрешён только после явного подтверждения в free-text.
2. **No hallucinated entities**: нельзя использовать сущности, которых не было в наблюдении/выводах тулов/initial_state.

## Reward
- Outcome-centric: `+1` за успешный `finalize`, `-1` за провал.
- Shaping: штрафы за лишние шаги, лишние tool calls, policy violations, invalid format, повторяющиеся действия.

## Структура
- `base/data.py` — контейнер эпизода.
- `envs/tool_env.py` — интерфейс `ToolEnv`.
- `envs/meeting_scheduler_env.py` — реализация среды.
- `verifier/trajectory_verifier.py` — `verify_trajectory(...)`.
- `agents/policies.py` — наивная, baseline и tiny-GRPO policy.
- `scripts/generate_eval.py` — генерация `eval_d1..eval_d5`.
- `scripts/run_eval.py` — сравнение двух политик + tiny-GRPO.
- `scripts/train_tiny_grpo.py` — простая GRPO-подобная подстройка.
- `report/report.md` — анализ результатов и ограничений proxy-reward.

## Запуск
```bash
cd tool_using_rl_envs
python3 scripts/generate_eval.py
python3 scripts/train_tiny_grpo.py
python3 scripts/run_eval.py
```

## Фиксированный eval
Генерируются файлы:
- `data/eval_d1.jsonl`
- ...
- `data/eval_d5.jsonl`
по 100 эпизодов в каждом.
