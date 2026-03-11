from __future__ import annotations

import json
from pathlib import Path

from tool_using_rl_envs.envs.meeting_scheduler_env import MeetingSchedulerEnv


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "data"
    out_dir.mkdir(exist_ok=True)

    env = MeetingSchedulerEnv(seed=123)
    for d in range(1, 6):
        data = env.generate(num_of_questions=100, difficulty=d)
        out_path = out_dir / f"eval_d{d}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for row in data:
                f.write(json.dumps(row.to_dict(), ensure_ascii=False) + "\n")
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
