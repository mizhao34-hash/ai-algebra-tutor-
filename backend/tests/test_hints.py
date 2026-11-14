"""Hint verification and retry loop, with fake LLMs (no API calls)."""

from types import SimpleNamespace

import pytest

from app.grader import InvalidInput
from app.hints import (
    FALLBACK_HINTS,
    ClaudeHintLLM,
    HintConfigError,
    HintLLMError,
    HintProposal,
    _user_prompt,
    check_hint,
    generate_hint,
    leaks_answer,
    validate_current,
)
from app.problems import Problem

SOLVE = Problem("two_step:1", "two_step", "solve", "Solve for x:", "3x + 5 = 17", "4")
NEG = Problem("two_step:2", "two_step", "solve", "Solve for x:", "2x + 9 = 3", "-3")
SIMPLIFY = Problem("combine_like_terms:1", "combine_like_terms", "simplify", "Simplify:", "3x + 5 - x + 2", "2x + 7")
EVAL = Problem("integer_ops:1", "integer_ops", "evaluate", "Evaluate:", "-7 + 3(-2)", "-13")


def P(hint="Subtract 5 from both sides.", next_step="3x = 12"):
    return HintProposal(hint=hint, next_step=next_step)


# ---------- check_hint ----------

def test_good_step_passes():
    assert check_hint(SOLVE, SOLVE.expression, P()) == []


def test_describing_without_a_step_is_allowed():
    assert check_hint(SOLVE, "3x = 12", P("Divide both sides by 3.", "")) == []


@pytest.mark.parametrize("step", ["3x = 13", "3x + 5 = 18", "x + 5 = 17"])
def test_wrong_math_rejected(step):
    assert any("not equivalent" in e for e in check_hint(SOLVE, SOLVE.expression, P(next_step=step)))


@pytest.mark.parametrize(
    "problem_expr,step",
    [("3(x - 2) = 21", "3x - 6 = 21"), ("3x + 5 - x = 17", "2x + 5 = 17"), ("-4(x - 4) + 6x = 5x - 5", "-4x + 16 + 6x = 5x - 5")],
)
def test_rewriting_one_side_is_progress(problem_expr, step):
    """Regression: distributing/combining doesn't change a side's VALUE but is a real step."""
    from sympy import Eq, solve

    from app.grader import X, parse_math

    lhs, rhs = problem_expr.split("=")
    ans = str(solve(Eq(parse_math(lhs), parse_math(rhs)), X)[0])
    p = Problem("t:9", "multi_step", "solve", "Solve for x:", problem_expr, ans)
    assert check_hint(p, problem_expr, P("Distribute / combine.", step)) == []


def test_no_progress_rejected():
    assert any("doesn't change" in e for e in check_hint(SOLVE, SOLVE.expression, P(next_step="3x+5=17")))


@pytest.mark.parametrize("step", ["x = 4", "4 = x", "x = 8/2"])
def test_final_answer_step_rejected(step):
    assert any("reveals the final answer" in e for e in check_hint(SOLVE, "3x = 12", P(next_step=step)))


@pytest.mark.parametrize("text", ["Divide by 3 to get x = 4.", "So x=4", "That gives 4 = x", "x is 4"])
def test_answer_in_hint_text_rejected(text):
    assert any("hint text reveals" in e for e in check_hint(SOLVE, "3x = 12", P(text, "")))


@pytest.mark.parametrize("text", ["x = 40 would be wrong", "Subtract 4 from both sides", "x = -4 is a common mistake"])
def test_leak_check_avoids_obvious_false_alarms(text):
    assert not leaks_answer(SOLVE, text)


def test_coefficient_times_x_is_not_a_leak_when_answer_is_zero():
    """Regression: '8x = 0' contains the characters 'x = 0' but doesn't reveal x."""
    zero = Problem("t:0", "two_step", "solve", "Solve for x:", "8x + 3 = 3", "0")
    assert not leaks_answer(zero, "Your equation 8x = 0 is correct so far.")
    assert not leaks_answer(zero, "Now 0 = 2x, so divide.")
    assert leaks_answer(zero, "So x = 0.")
    assert leaks_answer(zero, "That means 0 = x")


def test_negative_answers_and_other_kinds():
    assert leaks_answer(NEG, "so x = -3")
    assert leaks_answer(SIMPLIFY, "The answer is 2x + 7.")
    assert leaks_answer(EVAL, "which is -13")
    assert check_hint(SIMPLIFY, SIMPLIFY.expression, P("Combine the x terms.", "2x + 5 + 2")) == []
    assert any("final answer" in e for e in check_hint(SIMPLIFY, SIMPLIFY.expression, P("Combine.", "2x + 7")))
    assert check_hint(EVAL, EVAL.expression, P("Multiply first.", "-7 + -6")) == []
    assert any("final answer" in e for e in check_hint(EVAL, EVAL.expression, P("Add.", "-13")))


def test_unparseable_step_rejected():
    assert any("couldn't be parsed" in e for e in check_hint(SOLVE, SOLVE.expression, P(next_step="3x equals 12")))


def test_issues_carry_codes():
    issues = check_hint(SOLVE, "3x = 12", P("so x = 4", "x = 4"))
    assert [i.code for i in issues] == ["leak_text", "leak_step"]


def test_validate_current():
    validate_current(SOLVE, "3x = 12")
    for bad in ["3x = 13", "hello", "3x + 5"]:
        with pytest.raises(InvalidInput):
            validate_current(SOLVE, bad)


# ---------- generate_hint loop ----------

class ScriptedLLM:
    """Returns (or raises) the given items in order and records each call."""

    def __init__(self, *items):
        self.items, self.calls = list(items), []

    def propose(self, problem, current, rejections):
        self.calls.append(list(rejections))
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_first_good_answer_is_used():
    r = generate_hint(SOLVE, SOLVE.expression, ScriptedLLM(P()))
    assert (r.verified, r.attempts, r.source, r.next_step) == (True, 1, "llm", "3x = 12")


def test_retries_with_feedback_then_succeeds():
    llm = ScriptedLLM(P(next_step="3x = 13"), P(next_step="x = 4"), P())
    r = generate_hint(SOLVE, SOLVE.expression, llm)
    assert r.verified and r.attempts == 3 and len(r.rejections) == 2
    assert llm.calls[0] == [] and len(llm.calls[2]) == 2  # later calls see why earlier ones failed


def test_falls_back_after_three_failures():
    llm = ScriptedLLM(P(next_step="3x = 13"), HintLLMError("timeout"), P("x = 4", ""))
    r = generate_hint(SOLVE, SOLVE.expression, llm)
    assert r.source == "fallback" and not r.verified and r.hint == FALLBACK_HINTS["two_step"]
    assert r.next_step == "" and r.attempts == 3


def test_unverified_mode_returns_first_output_as_is():
    r = generate_hint(SOLVE, SOLVE.expression, ScriptedLLM(P("x = 4", "x = 4")), verify=False)
    assert (r.hint, r.next_step, r.verified, r.attempts) == ("x = 4", "x = 4", False, 1)


def test_config_error_is_not_retried():
    llm = ScriptedLLM(HintConfigError("no key"), P())
    with pytest.raises(HintConfigError):
        generate_hint(SOLVE, SOLVE.expression, llm)
    assert len(llm.calls) == 1


def test_every_skill_has_a_safe_fallback():
    for skill, text in FALLBACK_HINTS.items():
        assert text and not any(ch.isdigit() for ch in text), skill


def test_prompt_includes_rejections():
    assert "rejected" not in _user_prompt(SOLVE, SOLVE.expression, [])
    assert "- attempt 1: bad" in _user_prompt(SOLVE, SOLVE.expression, ["attempt 1: bad"])


# ---------- ClaudeHintLLM with a fake SDK client ----------

class FakeClient:
    def __init__(self, response):
        self.response, self.kwargs = response, None
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse))

    def _parse(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def test_claude_request_shape_and_parsing():
    usage = SimpleNamespace(input_tokens=100, output_tokens=20)
    client = FakeClient(SimpleNamespace(stop_reason="end_turn", parsed_output=P(), usage=usage))
    out = ClaudeHintLLM(model="claude-opus-5-5", client=client).propose(SOLVE, SOLVE.expression, [])
    assert out == P()
    kw = client.kwargs
    assert kw["model"] == "claude-opus-5-5" and kw["output_format"] is HintProposal
    assert kw["fallbacks"] == "default" and "3x + 5 = 17" in kw["messages"][0]["content"]


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_claude_refusal_or_truncation_is_a_failed_attempt(stop):
    client = FakeClient(SimpleNamespace(stop_reason=stop, parsed_output=None, usage=SimpleNamespace(input_tokens=1, output_tokens=1)))
    with pytest.raises(HintLLMError):
        ClaudeHintLLM(client=client).propose(SOLVE, SOLVE.expression, [])


def test_claude_400_is_a_config_error_not_retried():
    import anthropic
    import httpx

    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    err = anthropic.BadRequestError("credit balance is too low", response=httpx.Response(400, request=req), body=None)

    class Raising(FakeClient):
        def _parse(self, **kwargs):
            raise err

    with pytest.raises(HintConfigError, match="credit balance"):
        ClaudeHintLLM(client=Raising(None)).propose(SOLVE, SOLVE.expression, [])
