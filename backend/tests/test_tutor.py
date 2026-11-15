"""AI tutor chat: walkthrough verification, leak guard, retry loop, API (fake LLMs only)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.grader import InvalidInput
from app.hints import HintConfigError, HintLLMError
from app.main import create_app
from app.problems import Problem, generate_problem
from app.tutor import (
    FALLBACK,
    MAX_STEPS,
    ClaudeTutorLLM,
    Step,
    TutorContext,
    TutorReply,
    Walkthrough,
    ask_tutor,
    build_system,
    check_reply,
    math_signature,
    similar_problem,
)

ACTIVE = Problem("two_step:1", "two_step", "solve", "Solve for x:", "3x + 5 = 17", "4")


def R(message="Undo the +5 first, then divide by 3.", problem="2x + 1 = 9", steps=(("Subtract 1", "2x = 8"), ("Divide by 2", "x = 4"))):
    return TutorReply(message=message, walkthrough=Walkthrough(problem=problem, steps=[Step(operation=o, result=r) for o, r in steps]))


NO_EXAMPLE = dict(problem="", steps=())


# ---------- math_signature ----------

@pytest.mark.parametrize(
    "a,b",
    [
        ("3x + 5 = 17", "x = 4"),
        ("x^2 + x - 6 = 0", "x - 2 = 0 or x + 3 = 0"),
        ("-2x + 3 <= 7", "x >= -2"),
        ("(x + 2)(x + 3)", "x^2 + 5x + 6"),
        ("sqrt(49) + sqrt(16)", "11"),
    ],
)
def test_equivalent_lines_share_a_signature(a, b):
    assert math_signature(a) == math_signature(b)


def test_different_lines_differ_and_bad_input_raises():
    assert math_signature("-2x <= 4") != math_signature("x <= -2")  # forgot to flip
    with pytest.raises(InvalidInput):
        math_signature("import os")


# ---------- check_reply ----------

def test_valid_reply_passes():
    assert check_reply(R(), TutorContext()) == []
    assert check_reply(R(**NO_EXAMPLE), TutorContext()) == []  # text-only is fine


def test_invalid_step_is_rejected_with_its_number():
    bad = R(steps=(("Subtract 1", "2x = 8"), ("Divide by 2", "x = 5")))
    assert any("Step 2" in i and "not mathematically valid" in i for i in check_reply(bad, TutorContext()))


def test_unparseable_and_too_long_walkthroughs():
    assert any("can't be parsed" in i for i in check_reply(R(steps=(("Hmm", "x equals four"),)), TutorContext()))
    long = R(steps=tuple(("Same", "2x + 1 = 9") for _ in range(MAX_STEPS + 1)))
    assert any("at most" in i for i in check_reply(long, TutorContext()))
    assert any("both a starting problem" in i for i in check_reply(R(problem="", steps=(("x", "x = 4"),)), TutorContext()))


def test_active_problem_is_protected():
    ctx = TutorContext(problem=ACTIVE)
    # Saying the answer in words
    assert any("reveals the answer" in i for i in check_reply(R(message="So x = 4.", **NO_EXAMPLE), ctx))
    # Working the student's own problem
    own = R(problem="3x + 5 = 17", steps=(("Subtract 5", "3x = 12"), ("Divide by 3", "x = 4")))
    assert any("DIFFERENT example" in i for i in check_reply(own, ctx))
    # A different problem that happens to have the same answer would still show "x = 4".
    assert any("same answer" in i for i in check_reply(R(), ctx))
    # A different problem with a different answer is fine.
    other = R(problem="2x + 1 = 11", steps=(("Subtract 1", "2x = 10"), ("Divide by 2", "x = 5")))
    assert check_reply(other, ctx) == []


def test_similar_problem_is_same_skill_but_different():
    q = similar_problem(ACTIVE)
    assert q.skill == ACTIVE.skill and q.expression != ACTIVE.expression and q.answer != ACTIVE.answer


def test_system_prompt_has_context_but_not_the_answer():
    p = generate_problem("two_step", 5)
    system = build_system(TutorContext(course="algebra_1", unit="multi_step_eq", problem=p, mastery={"two_step": 0.42}))
    assert "Multi-step equations" in system and "Two-step equations 42%" in system
    assert p.expression in system and "Do NOT solve it" in system
    assert f"x = {p.answer}" not in system
    explain = build_system(TutorContext(mode="explain_unit", unit="inequalities"))
    assert "explain this unit" in explain and "Linear inequalities" in explain
    sel = build_system(TutorContext(mode="selection", selection="flip the sign"))
    assert '"flip the sign"' in sel


# ---------- ask_tutor loop ----------

class Scripted:
    def __init__(self, *items):
        self.items, self.calls = list(items), []

    def reply(self, system, messages, rejections):
        self.calls.append(list(rejections))
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


MSGS = [{"role": "user", "content": "How do I start?"}]


def test_verified_on_first_try():
    r = ask_tutor(MSGS, TutorContext(), Scripted(R()))
    assert r.verified and r.walkthrough and r.attempts == 1 and r.source == "llm"


def test_retries_with_feedback_then_succeeds():
    bad = R(steps=(("Divide by 2", "x = 5"),))
    llm = Scripted(bad, R())
    r = ask_tutor(MSGS, TutorContext(), llm)
    assert r.verified and r.attempts == 2 and llm.calls[1] and "Step 1" in llm.calls[1][0]


def test_unverifiable_math_falls_back_to_text_only():
    bad = R(steps=(("Divide by 2", "x = 5"),))
    r = ask_tutor(MSGS, TutorContext(), Scripted(bad, bad, HintLLMError("timeout")))
    assert r.walkthrough is None and not r.verified and r.message == bad.message and r.source == "llm"


def test_leaking_every_time_gives_the_safe_fallback():
    leak = R(message="The answer is x = 4.", **NO_EXAMPLE)
    r = ask_tutor(MSGS, TutorContext(problem=ACTIVE), Scripted(leak, leak, leak))
    assert r.message == FALLBACK and r.source == "fallback"


def test_config_error_propagates():
    with pytest.raises(HintConfigError):
        ask_tutor(MSGS, TutorContext(), Scripted(HintConfigError("no key")))


def test_claude_request_includes_rejections_as_feedback():
    seen = {}

    def parse(**kw):
        seen.update(kw)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=R(), usage=SimpleNamespace(input_tokens=1, output_tokens=1))

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse)))
    ClaudeTutorLLM(client=client).reply("sys", MSGS, ["attempt 1: Step 2 is wrong"])
    assert seen["output_format"] is TutorReply and seen["system"] == "sys"
    assert seen["messages"][0] == MSGS[0] and "Step 2 is wrong" in seen["messages"][-1]["content"]


# ---------- API ----------

class FakeMastery:
    def mastery(self, history):
        return {s: 0.5 for s, _ in history}


class AlwaysValid:
    def __init__(self):
        self.systems = []

    def reply(self, system, messages, rejections):
        self.systems.append(system)
        return R()


@pytest.fixture
def tutor_client(tmp_path):
    llm = AlwaysValid()
    app = create_app(db_path=str(tmp_path / "t.db"), mastery_model=FakeMastery(), tutor_llm=llm)
    with TestClient(app) as c:
        c.llm = llm
        yield c


def test_tutor_endpoint(tutor_client):
    r = tutor_client.post("/users/t1/tutor", json={"messages": MSGS, "course": "algebra_1", "unit": "multi_step_eq"})
    body = r.json()
    assert r.status_code == 200 and body["verified"] and body["walkthrough"]["steps"][0]["result"] == "2x = 8"
    assert set(body) == {"message", "walkthrough", "verified", "source"}  # no rejections leak to the browser


def test_explain_unit_needs_no_typed_question(tutor_client):
    r = tutor_client.post("/users/t2/tutor", json={"mode": "explain_unit", "unit": "inequalities"})
    assert r.status_code == 200
    assert "explain this unit" in tutor_client.llm.systems[-1]


def test_problem_context_reaches_the_prompt(tutor_client):
    p = tutor_client.get("/users/t3/next", params={"skill": "two_step"}).json()
    tutor_client.post("/users/t3/tutor", json={"messages": MSGS, "problem_id": p["id"]})
    assert p["expression"] in tutor_client.llm.systems[-1]


def test_bad_requests(tutor_client):
    assert tutor_client.post("/users/t4/tutor", json={"messages": []}).status_code == 400
    assert tutor_client.post("/users/t4/tutor", json={"messages": [{"role": "user", "content": "x" * 600}]}).status_code == 400
    assert tutor_client.post("/users/t4/tutor", json={"messages": MSGS, "unit": "nope"}).status_code == 404
    assert tutor_client.post("/users/t4/tutor", json={"messages": MSGS, "problem_id": "bad"}).status_code == 404
    too_long = {"messages": MSGS, "selection": "y" * 301}
    assert tutor_client.post("/users/t4/tutor", json=too_long).status_code == 422


def test_rate_limit(tutor_client, monkeypatch):
    monkeypatch.setattr(main, "TUTOR_PER_USER_PER_HOUR", 2)
    for _ in range(2):
        assert tutor_client.post("/users/t5/tutor", json={"messages": MSGS}).status_code == 200
    assert tutor_client.post("/users/t5/tutor", json={"messages": MSGS}).status_code == 429
    assert tutor_client.post("/users/t6/tutor", json={"messages": MSGS}).status_code == 200  # per user


def test_substitute_back_check_steps():
    """Regression: 'check your answer' steps have no x; they are fine if true."""
    good = R(problem="-7x + 4 = -52", steps=(("Subtract 4", "-7x = -56"), ("Divide by -7", "x = 8"),
                                              ("Check: substitute x = 8", "-7(8) + 4 = -52"), ("Simplify", "-52 = -52")))
    assert check_reply(good, TutorContext()) == []
    wrong = R(problem="-7x + 4 = -52", steps=(("Divide", "x = 8"), ("Check", "-7(9) + 4 = -52")))
    assert any("isn't true" in i for i in check_reply(wrong, TutorContext()))
    ineq = R(problem="-3x < 12", steps=(("Divide by -3, flip", "x > -4"), ("Check with x = 0", "-3(0) < 12")))
    assert check_reply(ineq, TutorContext()) == []
