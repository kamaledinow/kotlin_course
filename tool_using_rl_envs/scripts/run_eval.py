from __future__ import annotations

import json
from pathlib import Path

from tool_using_rl_envs.agents.policies import EpisodeContext, NaivePolicy, PromptBaselinePolicy, TinyGRPOPolicy
from tool_using_rl_envs.base.data import Data
from tool_using_rl_envs.envs.meeting_scheduler_env import MeetingSchedulerEnv
from tool_using_rl_envs.verifier.trajectory_verifier import DefaultTrajectoryVerifier


def rollout(policy, env: MeetingSchedulerEnv, data: Data, max_steps: int = 8):
    obs = env.reset(data)
    actions = []
    target = data.answer if isinstance(data.answer, dict) else json.loads(data.answer)
    ctx = EpisodeContext(
        question=data.question,
        target_meeting=target["meeting_id"],
        target_day=target["day"],
        target_slot=target["slot"],
    )
    for i in range(max_steps):
        action = policy.act(obs, i, ctx)
        actions.append(action)
        obs, _, done, _ = env.step(action)
        if done:
            break
    return actions


def evaluate(policy, dataset: list[Data]) -> dict:
    verifier = DefaultTrajectoryVerifier()
    env = MeetingSchedulerEnv(seed=99)
    metrics = []
    for d in dataset:
        actions = rollout(policy, env, d)
        metrics.append(verifier.verify_trajectory(env, d, actions, max_steps=8))

    return {
        "success_rate": sum(int(m["success"]) for m in metrics) / len(metrics),
        "avg_reward": sum(m["total_reward"] for m in metrics) / len(metrics),
        "avg_steps": sum(m["steps"] for m in metrics) / len(metrics),
        "avg_policy_violations": sum(m["policy_violations"] for m in metrics) / len(metrics),
    }


def load_eval(path: Path) -> list[Data]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            rows.append(Data.from_dict(json.loads(line)))
    return rows


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    eval_path = root / "data" / "eval_d3.jsonl"
    dataset = load_eval(eval_path)

    naive = evaluate(NaivePolicy(), dataset)
    baseline = evaluate(PromptBaselinePolicy(), dataset)
    grpo = evaluate(TinyGRPOPolicy(ask_calendar_prob=0.2), dataset)

    print("Naive:", naive)
    print("Baseline:", baseline)
    print("Tiny-GRPO:", grpo)


if __name__ == "__main__":
    main()
