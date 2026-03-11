from tool_using_rl_envs.envs.meeting_scheduler_env import MeetingSchedulerEnv


def test_generate_and_success_flow():
    env = MeetingSchedulerEnv(seed=1)
    ds = env.generate(num_of_questions=3, difficulty=2)
    assert len(ds) == 3
    data = ds[0]
    target = data.answer

    env.reset(data)
    env.step("Please confirm move")
    env.step("Thanks, confirmed")
    _, _, _, _ = env.step(
        f'TOOL_CALL {{"name": "move_meeting", "args": {{"meeting_id": "{target["meeting_id"]}", "day": {target["day"]}, "slot": {target["slot"]}}}}}'
    )
    _, _, done, _ = env.step('TOOL_CALL {"name": "finalize", "args": {}}')
    assert done
    assert env.state["success"] is True


def test_confirmation_violation():
    env = MeetingSchedulerEnv(seed=1)
    data = env.generate(num_of_questions=1, difficulty=1)[0]
    target = data.answer
    env.reset(data)
    _, _, _, info = env.step(
        f'TOOL_CALL {{"name": "move_meeting", "args": {{"meeting_id": "{target["meeting_id"]}", "day": {target["day"]}, "slot": {target["slot"]}}}}}'
    )
    assert info["policy_violations"] >= 1
