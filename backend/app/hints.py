"""LLM step hints, verified with SymPy before the student sees them.

Pipeline for one hint request:
  1. Ask the LLM for ONE next step as JSON: {"hint": words, "next_step": math}.
  2. check_hint() verifies it with SymPy (equivalent, makes progress, parses)
     and checks it doesn't leak the final answer.
  3. If rejected, ask again with the rejection reasons (at most MAX_ATTEMPTS).
  4. If every attempt fails, return a fixed, safe hint for the skill.

With verify=False the first LLM output is returned unchecked. That mode exists
only for experiment 2 (hint error/leak rate with vs without the SymPy check).

Prompt-injection note: everything sent to the LLM is either server-generated
(the problem) or has passed the grader's strict math whitelist (`current`),
so students can't put free text into the prompt.
"""

import os
import re
import threading
from dataclasses import dataclass, field
from typing import Protocol

import anthropic
from pydantic import BaseModel, Field
from sympy import Eq, expand, solve

from .grader import (
    X,
    InvalidInput,
    answer_values,
    inequality_solutions,
    is_simplest_polynomial,
    parse_inequality,
    parse_math,
)
from .problems import Problem
from .skills import SKILLS

MAX_ATTEMPTS = 3
DEFAULT_MODEL = "claude-opus-5-5"


class HintProposal(BaseModel):
    """The JSON shape the LLM must return (enforced by structured outputs)."""

    hint: str = Field(description="One or two sentences telling the student the next operation and why.")
    next_step: str = Field(
        description='The expression or equation after doing that ONE step, e.g. "3x = 12". '
        "Empty string if writing it would reveal the final answer."
    )


@dataclass
class HintResult:
    hint: str
    next_step: str          # "" when not shown
    verified: bool          # passed check_hint (always False for fallbacks and verify=False)
    attempts: int           # LLM calls made
    source: str             # "llm" or "fallback"
    rejections: list[str] = field(default_factory=list)  # why earlier attempts failed


class HintLLM(Protocol):
    def propose(self, problem: Problem, current: str, rejections: list[str]) -> HintProposal: ...


class HintIssue(str):
    """A rejection reason: reads like a plain message (it is a str, sent back to
    the LLM) but also carries a short machine-readable `code` for experiments."""

    def __new__(cls, code: str, message: str):
        obj = super().__new__(cls, message)
        obj.code = code
        return obj


class HintLLMError(RuntimeError):
    """The LLM call failed or refused; counts as a failed attempt."""


class HintConfigError(RuntimeError):
    """Hints can't work at all (e.g. missing/invalid API key). Not retried."""


# ---------- SymPy verification ----------

def _split_equation(text: str):
    parts = text.split("=")
    if len(parts) != 2:
        raise InvalidInput("expected exactly one '='")
    return parse_math(parts[0].strip()), parse_math(parts[1].strip())


def _solutions(lhs, rhs) -> set:
    return set(solve(Eq(lhs, rhs), X))


def _answers(problem: Problem) -> set:
    """The problem's solution set ({4}, or {-3, 2} for a quadratic)."""
    return set(answer_values(problem))


def _same_text(a: str, b: str) -> bool:
    return a.replace(" ", "") == b.replace(" ", "")


def leaks_answer(problem: Problem, text: str) -> bool:
    """Does free text state the final answer? Deliberately strict: a false
    alarm only costs a retry, a miss gives the answer away."""
    raw = text.replace("−", "-").replace("≤", "<=").replace("≥", ">=").lower()
    if problem.kind == "simplify":
        return problem.answer.replace(" ", "").lower() in raw.replace(" ", "")
    if problem.kind == "inequality":
        # "x >= -2" or the same thing written backwards, "-2 <= x".
        t = re.sub(r"\s*(<=|>=|<|>)\s*", r"\1", raw)
        _, op, value = problem.answer.split()
        flipped = {"<": ">", ">": "<", "<=": ">=", ">=": "<="}[op]
        v = re.escape(value)
        return bool(re.search(rf"(?<![\w)])x{re.escape(op)}{v}(?!\d|[/.]\d)", t)
                    or re.search(rf"(?<![\d.]){v}{re.escape(flipped)}x(?![\w(])", t))
    # Remove spaces only around "=", keeping word boundaries, so "so x = 4" -> "so x=4"
    # while "8x = 0" -> "8x=0" still shows the 8 in front of x.
    t = re.sub(r"\s*=\s*", "=", raw)
    end = r"(?!\d|[/.]\d)"  # not followed by more digits, "/2" or ".5" ("x = 4." still counts)
    alone = r"(?<![\w)])"    # x is a bare variable, not "8x" or "(x"
    # Quadratics have two answers ("-3, 2"); stating EITHER one is a leak.
    for ans in problem.answer.replace(" ", "").lower().split(","):
        a = re.escape(ans)
        patterns = [rf"{alone}x=+{a}{end}", rf"(?<![\d.]){a}=x(?![\w(])", rf"{alone}x\s+is\s+{a}{end}"]
        if problem.kind == "evaluate":
            patterns += [rf"(=|\bis\s+){a}{end}"]
        if any(re.search(p, t) for p in patterns):
            return True
    return False


def check_hint(problem: Problem, current: str, proposal: HintProposal) -> list[HintIssue]:
    """Return the reasons a hint is unacceptable ([] means it passed).
    Codes: empty_hint, leak_text, leak_step, not_equivalent, no_progress, unparseable."""
    errors: list[HintIssue] = []
    step = proposal.next_step.strip()

    if not proposal.hint.strip():
        errors.append(HintIssue("empty_hint", "The hint text is empty."))
    if leaks_answer(problem, proposal.hint):
        errors.append(HintIssue("leak_text", "The hint text reveals the final answer."))
    if not step:
        return errors  # describing the operation without writing the step is allowed

    try:
        if problem.kind == "inequality":
            lhs, op, rhs = parse_inequality(step)
            if inequality_solutions(lhs, op, rhs) != inequality_solutions(*parse_inequality(problem.answer)):
                errors.append(HintIssue("not_equivalent", f"'{step}' is not equivalent to the original inequality."))
            elif _same_text(step, current):
                errors.append(HintIssue("no_progress", f"'{step}' doesn't change anything; it should make one step of progress."))
            elif (lhs == X and not rhs.has(X)) or (rhs == X and not lhs.has(X)):
                errors.append(HintIssue("leak_step", "The next step reveals the final answer; leave next_step empty instead."))
        elif problem.kind == "solve":
            lhs, rhs = _split_equation(step)
            cur_l, cur_r = _split_equation(current)
            if _solutions(lhs, rhs) != _answers(problem):
                errors.append(HintIssue("not_equivalent", f"'{step}' is not equivalent to the original equation."))
            # Compare the WRITTEN form, not the value: distributing or combining like
            # terms never changes a side's value, but it is real progress.
            elif _same_text(step, current):
                errors.append(HintIssue("no_progress", f"'{step}' doesn't change anything; it should make one step of progress."))
            # "x = 4" or "4 = x" (any arrangement where one side is just x) is the answer itself.
            elif (lhs == X and not rhs.has(X)) or (rhs == X and not lhs.has(X)):
                errors.append(HintIssue("leak_step", "The next step reveals the final answer; leave next_step empty instead."))
        else:
            expr, cur = parse_math(step), parse_math(current)
            if expand(expr - answer_values(problem)[0]) != 0:
                errors.append(HintIssue("not_equivalent", f"'{step}' is not equivalent to the original expression."))
            elif _same_text(step, current):
                errors.append(HintIssue("no_progress", f"'{step}' doesn't change anything; it should make one step of progress."))
            elif is_simplest_polynomial(step):
                errors.append(HintIssue("leak_step", "The next step is the final answer; leave next_step empty instead."))
    except InvalidInput as e:
        errors.append(HintIssue("unparseable", f"next_step '{step}' couldn't be parsed ({e}). Write ONE equation or "
                                               "expression using only numbers, x, + - * / ^ ( ) and =."))
    return errors


def validate_current(problem: Problem, current: str) -> None:
    """The student's current step must be valid math equivalent to the problem.
    Raises InvalidInput otherwise (the API turns that into a 400)."""
    if problem.kind == "inequality":
        if inequality_solutions(*parse_inequality(current)) != inequality_solutions(*parse_inequality(problem.answer)):
            raise InvalidInput("current step is not equivalent to the problem")
    elif problem.kind == "solve":
        if _solutions(*_split_equation(current)) != _answers(problem):
            raise InvalidInput("current step is not equivalent to the problem")
    elif expand(parse_math(current) - answer_values(problem)[0]) != 0:
        raise InvalidInput("current step is not equivalent to the problem")


# ---------- fallback ----------

FALLBACK_HINTS = {
    "integer_ops": "Do multiplication first, then addition and subtraction. Watch the signs.",
    "combine_like_terms": "Group the x terms together and the plain numbers together, then add each group.",
    "distributive": "Multiply the number outside the parentheses by EACH term inside, keeping the signs.",
    "one_step_add": "Undo the number added to x by doing the opposite operation to both sides.",
    "one_step_mul": "Undo the multiplication or division on x by doing the opposite to both sides.",
    "two_step": "First move the constant term to the other side, then divide by the coefficient of x.",
    "vars_both_sides": "Move all x terms to one side and all numbers to the other, then simplify.",
    "parentheses": "Start by distributing (or divide both sides by the number outside the parentheses).",
    "multi_step": "Distribute first, combine like terms on each side, then collect x terms on one side.",
    "exponents": "Work out each power first. A minus sign outside parentheses is applied after the power.",
    "square_roots": "Ask which number multiplied by itself gives the number under the root.",
    "one_step_ineq": "Undo the operation on x. If you multiply or divide by a negative number, flip the sign.",
    "two_step_ineq": "Move the constant term first, then divide by the coefficient of x, flipping the sign if it is negative.",
    "multiply_binomials": "Multiply every term in the first parentheses by every term in the second, then combine like terms.",
    "square_binomial": "Write the square as the binomial times itself, multiply out, and combine the two middle terms.",
    "quad_square_root": "Get x squared by itself, then take the square root of both sides. Remember the negative root.",
    "quad_factored": "If a product is zero, one of the factors must be zero. Set each factor equal to zero.",
    "quad_factor_solve": "Look for two numbers that multiply to the constant term and add to the x coefficient.",
}


# ---------- the loop ----------

def generate_hint(
    problem: Problem,
    current: str,
    llm: HintLLM,
    verify: bool = True,
    max_attempts: int = MAX_ATTEMPTS,
) -> HintResult:
    rejections: list[str] = []
    for attempt in range(1, max_attempts + 1):
        try:
            proposal = llm.propose(problem, current, rejections)
        except HintLLMError as e:
            rejections.append(f"attempt {attempt}: LLM error: {e}")
            continue
        if not verify:
            return HintResult(proposal.hint, proposal.next_step.strip(), False, attempt, "llm", rejections)
        errors = check_hint(problem, current, proposal)
        if not errors:
            return HintResult(proposal.hint, proposal.next_step.strip(), True, attempt, "llm", rejections)
        rejections.extend(f"attempt {attempt}: {e}" for e in errors)
    return HintResult(FALLBACK_HINTS[problem.skill], "", False, max_attempts, "fallback", rejections)


# ---------- Claude implementation ----------

SYSTEM_PROMPT = """You are a patient algebra tutor helping a middle-school student with linear equations.
Give exactly ONE small next step, never the whole solution.

Rules:
- "hint": one or two short sentences naming the operation to do next and why.
- "next_step": the expression or equation after applying ONLY that one step, written with
  numbers, x, + - * / ( ) and = (e.g. "3x = 12" or "2x + 7"). Use implicit multiplication like 3x.
- Never state the final answer anywhere. If the next step would produce the final answer
  (for example "x = 4", a fully simplified expression, or the final number), set "next_step"
  to "" and only describe the operation in "hint".
- "next_step" must be ONE equation or expression, never two joined by "or". Write powers as x^2.
- Quadratic equations have two solutions; never state either of them.
- For an inequality, "next_step" is ONE inequality using <, >, <= or >=. Remember that multiplying or
  dividing by a negative number flips the sign.
- Write square roots as sqrt(49)."""


def _user_prompt(problem: Problem, current: str, rejections: list[str]) -> str:
    lines = [
        f"Skill: {SKILLS[problem.skill].name}",
        f"Task: {problem.prompt} {problem.expression}",
        f"The student's current step: {current}",
        "Give the single next step from the current step.",
    ]
    if rejections:
        lines.append("\nYour earlier hints were rejected by an automatic checker:")
        lines += [f"- {r}" for r in rejections]
        lines.append("Fix these problems.")
    return "\n".join(lines)


class ClaudeHintLLM:
    def __init__(self, model: str | None = None, client: anthropic.Anthropic | None = None):
        # Credentials come from ANTHROPIC_API_KEY (in .env, never committed).
        # A short timeout because a student is waiting on this request.
        self.client = client or anthropic.Anthropic(timeout=60.0, max_retries=2)
        self.model = model or os.environ.get("HINT_MODEL", DEFAULT_MODEL)
        # Running token totals (for cost reporting in experiments); the lock makes
        # the counter safe when an experiment calls propose() from several threads.
        self.usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
        self._lock = threading.Lock()

    def propose(self, problem: Problem, current: str, rejections: list[str]) -> HintProposal:
        try:
            msg = self.client.beta.messages.parse(
                model=self.model,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _user_prompt(problem, current, rejections)}],
                output_format=HintProposal,  # structured outputs: response is valid JSON for this schema
                output_config={"effort": "low"},  # a one-step hint needs little reasoning; keeps latency down
                # If a safety classifier declines, the API retries on a fallback model in the same call.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            raise HintConfigError("Claude API key is invalid; check ANTHROPIC_API_KEY in .env") from e
        except TypeError as e:
            # The SDK raises TypeError("Could not resolve authentication method...")
            # when no credentials are configured at all. Not worth retrying.
            raise HintConfigError("No Claude API key configured; set ANTHROPIC_API_KEY in .env") from e
        except anthropic.BadRequestError as e:
            # 400s come from the request or the account (e.g. "credit balance is too low"),
            # not from bad luck, so retrying can't help. Surface them instead of hiding
            # them behind the fallback hint.
            raise HintConfigError(f"Claude API rejected the request: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise HintLLMError(f"connection error: {e}") from e
        except anthropic.APIStatusError as e:  # rate limits, 5xx, bad requests
            raise HintLLMError(f"API error {e.status_code}: {e.message}") from e
        with self._lock:
            self.usage["input_tokens"] += msg.usage.input_tokens
            self.usage["output_tokens"] += msg.usage.output_tokens  # includes thinking tokens
            self.usage["calls"] += 1
        if msg.stop_reason == "refusal":
            raise HintLLMError("model declined to answer")
        if msg.stop_reason == "max_tokens" or msg.parsed_output is None:
            raise HintLLMError(f"no usable output (stop_reason={msg.stop_reason})")
        return msg.parsed_output
