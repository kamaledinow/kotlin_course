from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from tool_using_rl_envs.base.data import Data


class TrajectoryVerifier(ABC):
    """Verifier that evaluates a given action trajectory in a multi-step ToolEnv."""

    @abstractmethod
    def verify_trajectory(
        self,
        env,
        data: Data,
        actions: List[str],
        max_steps: Optional[int] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class DefaultTrajectoryVerifier(TrajectoryVerifier):
    def verify_trajectory(
        self,
        env,
        data: Data,
        actions: List[str],
        max_steps: Optional[int] = None,
    ) -> Dict[str, Any]:
        env.reset(data)
        total_reward = 0.0
        tool_calls = 0
        policy_violations = 0
        invalid_actions = 0
        info_trace: List[dict] = []
        done = False

        step_budget = max_steps if max_steps is not None else len(actions)
        for i, action in enumerate(actions[:step_budget], start=1):
            if action.startswith("TOOL_CALL "):
                tool_calls += 1
            _, reward, done, info = env.step(action)
            total_reward += reward
            policy_violations += int(info.get("policy_violations", 0))
            invalid_actions += int(info.get("invalid_actions", 0))
            info_trace.append(info)
            if done:
                break

        success = bool(getattr(env, "state", {}).get("success", False))
        terminated_early = not done and len(actions) >= step_budget
        return {
            "success": success,
            "total_reward": total_reward,
            "steps": min(len(actions), step_budget),
            "tool_calls": tool_calls,
            "policy_violations": policy_violations,
            "terminated_early": terminated_early,
            "invalid_actions": invalid_actions,
            "info_trace": info_trace,
        }
