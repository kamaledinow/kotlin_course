from __future__ import annotations

from tool_using_rl_envs.envs.meeting_scheduler_env import MeetingSchedulerEnv
from tool_using_rl_envs.agents.policies import TinyGRPOPolicy


def main() -> None:
    env = MeetingSchedulerEnv(seed=7)
    train = env.generate(num_of_questions=40, difficulty=4)
    policy = TinyGRPOPolicy(ask_calendar_prob=0.9)

    grouped_rewards = []
    for i in range(0, len(train), 10):
        batch = train[i : i + 10]
        rewards = []
        for data in batch:
            env.reset(data)
            target = data.answer
            actions = [
                f"Please confirm: move {target['meeting_id']} to d{target['day']}:{target['slot']}",
                "Confirmed",
            ]
            if policy.ask_calendar_prob > 0.5:
                actions.append('TOOL_CALL {"name": "get_calendar", "args": {"person": "P1", "range": [0, 3]}}')
            actions.extend(
                [
                    f'TOOL_CALL {{"name": "move_meeting", "args": {{"meeting_id": "{target["meeting_id"]}", "day": {target["day"]}, "slot": {target["slot"]}}}}}',
                    'TOOL_CALL {"name": "finalize", "args": {}}',
                ]
            )
            r = 0.0
            for a in actions:
                _, rr, done, _ = env.step(a)
                r += rr
                if done:
                    break
            rewards.append(r)
        grouped_rewards.append(rewards)

    policy.train_from_groups(grouped_rewards)
    print(f"trained ask_calendar_prob={policy.ask_calendar_prob:.3f}")


if __name__ == "__main__":
    main()
