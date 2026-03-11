from __future__ import annotations

import json
import random
import re
from copy import deepcopy
from typing import Any, Dict, Optional, Tuple

from tool_using_rl_envs.base.data import Data
from tool_using_rl_envs.envs.tool_env import ToolEnv


class MeetingSchedulerEnv(ToolEnv):
    """World: move one meeting to a free slot with confirmation-first policy."""

    TOOL_PREFIX = "TOOL_CALL "

    def __init__(self, seed: int = 42):
        super().__init__(name="meeting_scheduler")
        self.seed = seed
        self.rng = random.Random(seed)
        self.state: Dict[str, Any] = {}
        self.done = False
        self.confirmed = False
        self.observation_history: list[str] = []
        self.last_tool_output_entities: set[str] = set()
        self.used_actions: set[str] = set()

    def reset(self, data: Data) -> str:
        self.state = deepcopy(data.initial_state)
        self.state["target"] = data.answer
        self.state["success"] = False
        self.done = False
        self.confirmed = False
        self.observation_history = []
        self.last_tool_output_entities = set(self.state["persons"] + [m["id"] for m in self.state["meetings"]])
        self.used_actions = set()
        meetings_str = ", ".join([f"{m['id']}@d{m['day']}:{m['slot']}" for m in self.state["meetings"]])
        obs = (
            f"Task: {data.question}\n"
            f"People: {', '.join(self.state['persons'])}\n"
            f"Meetings: {meetings_str}\n"
            "Available tools: get_calendar(person, range), get_meeting(meeting_id), move_meeting(meeting_id, day, slot), finalize()"
        )
        self.observation_history.append(obs)
        return obs

    def _parse_action(self, action: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        if action.startswith(self.TOOL_PREFIX):
            try:
                payload = json.loads(action[len(self.TOOL_PREFIX) :])
                return "tool", payload
            except json.JSONDecodeError:
                return "invalid", None
        return "text", None

    def _check_hallucination(self, action: str) -> bool:
        tokens = set(re.findall(r"[A-Z]\d+", action))
        allowed = self.last_tool_output_entities.union(set(self.state["persons"])).union(
            {m["id"] for m in self.state["meetings"]}
        )
        return not tokens.issubset(allowed)

    def _meeting_by_id(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        for meeting in self.state["meetings"]:
            if meeting["id"] == meeting_id:
                return meeting
        return None

    def _slot_free(self, participants: list[str], day: int, slot: int, ignored_meeting: str) -> bool:
        for m in self.state["meetings"]:
            if m["id"] == ignored_meeting:
                continue
            if m["day"] == day and m["slot"] == slot and any(p in m["participants"] for p in participants):
                return False
        return True

    def step(self, action: str) -> Tuple[str, float, bool, Dict[str, Any]]:
        if self.done:
            return "Episode already finished.", 0.0, True, {"policy_violations": 0}

        reward = -0.01
        policy_violations = 0
        invalid_actions = 0

        if action in self.used_actions:
            reward -= 0.05
        self.used_actions.add(action)

        if self._check_hallucination(action):
            policy_violations += 1
            reward -= 0.2

        action_type, payload = self._parse_action(action)
        if action_type == "invalid":
            invalid_actions += 1
            reward -= 0.15
            obs = "Invalid TOOL_CALL format. Use: TOOL_CALL {\"name\": ..., \"args\": {...}}"
            self.observation_history.append(obs)
            return obs, reward, False, {"policy_violations": policy_violations, "invalid_actions": invalid_actions}

        if action_type == "text":
            if "confirm" in action.lower() or "подтверж" in action.lower():
                self.confirmed = True
                reward += 0.05
                obs = "Confirmation received. You may now apply state-changing tool calls."
            else:
                obs = "Noted. Continue."
            self.observation_history.append(obs)
            return obs, reward, False, {"policy_violations": policy_violations, "invalid_actions": invalid_actions}

        tool_name = payload.get("name")
        args = payload.get("args", {})

        if tool_name == "get_calendar":
            person = args.get("person")
            day_range = args.get("range", [0, 1])
            meetings = [
                {"id": m["id"], "day": m["day"], "slot": m["slot"]}
                for m in self.state["meetings"]
                if person in m["participants"] and day_range[0] <= m["day"] <= day_range[1]
            ]
            self.last_tool_output_entities.add(person)
            for m in meetings:
                self.last_tool_output_entities.add(m["id"])
            obs = json.dumps({"person": person, "meetings": meetings})
            reward -= 0.02
        elif tool_name == "get_meeting":
            meeting = self._meeting_by_id(args.get("meeting_id", ""))
            if not meeting:
                obs = "Meeting not found"
                reward -= 0.1
            else:
                for p in meeting["participants"]:
                    self.last_tool_output_entities.add(p)
                self.last_tool_output_entities.add(meeting["id"])
                obs = json.dumps(meeting)
                reward -= 0.02
        elif tool_name == "move_meeting":
            if not self.confirmed:
                policy_violations += 1
                reward -= 0.3
                obs = "Policy violation: move_meeting requires explicit user confirmation first."
            else:
                mid = args.get("meeting_id")
                day = int(args.get("day", -1))
                slot = int(args.get("slot", -1))
                meeting = self._meeting_by_id(mid)
                if not meeting:
                    obs = "Meeting not found"
                    reward -= 0.1
                elif day not in self.state["days"] or slot not in self.state["slots"]:
                    obs = "Invalid day or slot"
                    reward -= 0.1
                elif not self._slot_free(meeting["participants"], day, slot, mid):
                    obs = "Slot conflict"
                    reward -= 0.08
                else:
                    meeting["day"] = day
                    meeting["slot"] = slot
                    obs = f"Moved {mid} to d{day}:{slot}"
                    reward += 0.2
        elif tool_name == "finalize":
            target = self.state["target"]
            meeting = self._meeting_by_id(target["meeting_id"])
            ok = bool(meeting and meeting["day"] == target["day"] and meeting["slot"] == target["slot"])
            self.state["success"] = ok
            self.done = True
            reward += 1.0 if ok else -1.0
            obs = "SUCCESS" if ok else "FAIL"
        else:
            invalid_actions += 1
            reward -= 0.15
            obs = "Unknown tool"

        self.observation_history.append(obs)
        return obs, reward, self.done, {"policy_violations": policy_violations, "invalid_actions": invalid_actions}

    def generate(
        self,
        num_of_questions: int = 100,
        max_attempts: int = 100,
        difficulty: Optional[int] = 1,
        **kwargs,
    ) -> list[Data]:
        d = max(1, min(10, int(difficulty or 1)))
        persons_n = kwargs.get("persons", min(4 + d // 2, 9))
        meetings_n = kwargs.get("meetings", min(4 + d, 12))
        days_n = kwargs.get("days", 2 + d // 3)
        slots_n = kwargs.get("slots", 4 + d // 2)

        episodes: list[Data] = []
        attempts = 0
        while len(episodes) < num_of_questions and attempts < num_of_questions * max_attempts:
            attempts += 1
            rng = random.Random(self.seed + attempts + d * 1000)
            persons = [f"P{i}" for i in range(1, persons_n + 1)]
            days = list(range(days_n))
            slots = list(range(slots_n))

            meetings = []
            for i in range(1, meetings_n + 1):
                participants = rng.sample(persons, k=min(2 + d // 4, len(persons)))
                meetings.append(
                    {
                        "id": f"M{i}",
                        "participants": participants,
                        "day": rng.choice(days),
                        "slot": rng.choice(slots),
                    }
                )

            target_meeting = rng.choice(meetings)
            # find one feasible new slot
            candidates = [(day, slot) for day in days for slot in slots if (day, slot) != (target_meeting["day"], target_meeting["slot"])]
            rng.shuffle(candidates)
            feasible = None
            for day, slot in candidates:
                if self._slot_free_static(meetings, target_meeting["id"], target_meeting["participants"], day, slot):
                    feasible = (day, slot)
                    break
            if not feasible:
                continue

            question = (
                f"Move meeting {target_meeting['id']} to day {feasible[0]} slot {feasible[1]} without creating conflicts. "
                "You must ask for explicit confirmation before any state-changing action."
            )
            answer = {"meeting_id": target_meeting["id"], "day": feasible[0], "slot": feasible[1]}
            data = Data(
                question=question,
                answer=json.dumps(answer),
                difficulty=d,
                initial_state={"persons": persons, "days": days, "slots": slots, "meetings": meetings},
                metadata={"seed": self.seed + attempts, "difficulty": d},
            )
            episodes.append(data)

        for ep in episodes:
            ep.answer = json.loads(ep.answer)
        return episodes

    @staticmethod
    def _slot_free_static(meetings: list[Dict[str, Any]], ignored_meeting: str, participants: list[str], day: int, slot: int) -> bool:
        for m in meetings:
            if m["id"] == ignored_meeting:
                continue
            if m["day"] == day and m["slot"] == slot and any(p in m["participants"] for p in participants):
                return False
        return True
