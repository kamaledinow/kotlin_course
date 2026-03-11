from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List


@dataclass
class EpisodeContext:
    question: str
    target_meeting: str
    target_day: int
    target_slot: int


class PromptBaselinePolicy:
    """Simple scripted prompting baseline."""

    def act(self, observation: str, step_idx: int, ctx: EpisodeContext) -> str:
        if step_idx == 0:
            return f"I can do that. Please confirm moving {ctx.target_meeting} to day {ctx.target_day}, slot {ctx.target_slot}."
        if step_idx == 1:
            return "Thanks for confirmation."
        if step_idx == 2:
            return f'TOOL_CALL {{"name": "get_meeting", "args": {{"meeting_id": "{ctx.target_meeting}"}}}}'
        if step_idx == 3:
            return (
                'TOOL_CALL {"name": "move_meeting", "args": '
                + json.dumps({"meeting_id": ctx.target_meeting, "day": ctx.target_day, "slot": ctx.target_slot})
                + "}"
            )
        return 'TOOL_CALL {"name": "finalize", "args": {}}'


class NaivePolicy:
    """Worse policy for comparison: skips confirmation rule."""

    def act(self, observation: str, step_idx: int, ctx: EpisodeContext) -> str:
        if step_idx == 0:
            return (
                'TOOL_CALL {"name": "move_meeting", "args": '
                + json.dumps({"meeting_id": ctx.target_meeting, "day": ctx.target_day, "slot": ctx.target_slot})
                + "}"
            )
        return 'TOOL_CALL {"name": "finalize", "args": {}}'


class TinyGRPOPolicy(PromptBaselinePolicy):
    """Tiny GRPO-style policy: learns whether to query calendar first."""

    def __init__(self, ask_calendar_prob: float = 0.5):
        self.ask_calendar_prob = ask_calendar_prob

    def act(self, observation: str, step_idx: int, ctx: EpisodeContext) -> str:
        if step_idx == 0:
            return f"Please confirm: move {ctx.target_meeting} to d{ctx.target_day}:{ctx.target_slot}."
        if step_idx == 1:
            return "Confirmed, proceeding."
        if step_idx == 2 and self.ask_calendar_prob > 0.5:
            person = re.findall(r"P\d+", observation)
            p = person[0] if person else "P1"
            return f'TOOL_CALL {{"name": "get_calendar", "args": {{"person": "{p}", "range": [0, 3]}}}}'
        if step_idx in (2, 3):
            return (
                'TOOL_CALL {"name": "move_meeting", "args": '
                + json.dumps({"meeting_id": ctx.target_meeting, "day": ctx.target_day, "slot": ctx.target_slot})
                + "}"
            )
        return 'TOOL_CALL {"name": "finalize", "args": {}}'

    def train_from_groups(self, grouped_rewards: List[List[float]]) -> None:
        """Relative update: if shorter trajectories perform better, reduce extra tool usage."""
        means = [sum(g) / len(g) for g in grouped_rewards if g]
        if not means:
            return
        delta = (means[-1] - means[0]) * 0.1
        self.ask_calendar_prob = min(1.0, max(0.0, self.ask_calendar_prob - delta))
