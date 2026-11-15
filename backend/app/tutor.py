"""AI tutor chat with SymPy-verified, animated worked examples.

A student can ask a free-form question, ask about highlighted text, or ask for
a whole unit to be explained. The LLM answers with:
  - message:      a short explanation in words
  - walkthrough:  optionally, a worked example as a list of steps
                  (operation label + resulting expression/equation)

The frontend animates the walkthrough step by step, so a wrong step would be
taught very convincingly. Therefore, like hints, every step is checked before
it is shown (check_reply):
  1. each line parses with the grader's safe parser;
  2. each line is mathematically equivalent to the example's first line
     (same solution set for equations / inequalities, same value for expressions);
  3. if the student is in the middle of a practice problem, the reply must not
     give away its answer: the message is leak-checked, and the walkthrough
     must use a DIFFERENT problem (we suggest a similar one from the generator).
Rejected replies are retried with the reasons (at most MAX_ATTEMPTS). If the
math can't be verified in the end, the text is still shown if it doesn't leak,
but without the walkthrough.
"""

import os
import random
import threading
from dataclasses import dataclass, field
from typing import Protocol

import anthropic
from pydantic import BaseModel, Field
from sympy import Eq, Rel, expand, simplify, solve

from .courses import CONCEPTS, COURSES, UNITS
from .grader import X, InvalidInput, inequality_solutions, parse_inequality, parse_math
from .hints import DEFAULT_MODEL, HintConfigError, HintLLMError, leaks_answer
from .problems import Problem, generate_problem
from .skills import SKILLS

MAX_ATTEMPTS = 3
MAX_STEPS = 8


# ---------- the reply format the LLM must produce ----------

class Step(BaseModel):
    operation: str = Field(description='What this step does, short, e.g. "Subtract 5 from both sides".')
    result: str = Field(description='The full expression/equation/inequality after this step, e.g. "3x = 12".')


class Walkthrough(BaseModel):
    problem: str = Field(description='The starting expression/equation/inequality, e.g. "3x + 5 = 17". "" if no example.')
    steps: list[Step] = Field(description="The solution, one small step at a time. Empty if no example.")


class TutorReply(BaseModel):
    message: str = Field(description="Your explanation to the student, 1-6 short sentences, friendly and clear.")
    walkthrough: Walkthrough


@dataclass
class TutorContext:
    """Where the student is when they ask (all optional)."""
    mode: str = "chat"                 # "chat" | "selection" | "explain_unit"
    course: str | None = None
    unit: str | None = None
    problem: Problem | None = None     # the practice problem on screen, if any
    selection: str | None = None       # highlighted text, for mode "selection"
    mastery: dict[str, float] = field(default_factory=dict)


@dataclass
class TutorResult:
    message: str
    walkthrough: Walkthrough | None    # None if there is none or it failed verification
    verified: bool                     # walkthrough passed every check
    attempts: int
    source: str                        # "llm" | "fallback"
    rejections: list[str] = field(default_factory=list)


class TutorLLM(Protocol):
    def reply(self, system: str, messages: list[dict], rejections: list[str]) -> TutorReply: ...


# ---------- verification ----------

def math_signature(line: str):
    """Something two equivalent lines have in common:
    - inequality  -> its solution set
    - equation(s) -> solution set (lines like "x - 2 = 0 or x + 3 = 0" are unions)
    - expression  -> its expanded form
    Raises InvalidInput if the line can't be parsed safely."""
    line = line.strip()
    if any(op in line for op in "<>"):
        return ("ineq", inequality_solutions(*parse_inequality(line)))
    if "=" in line:
        sols = set()
        for part in line.split(" or "):
            sides = part.split("=")
            if len(sides) != 2:
                raise InvalidInput("expected one '=' per equation")
            sols |= set(solve(Eq(parse_math(sides[0].strip()), parse_math(sides[1].strip())), X))
        return ("eq", frozenset(sols))
    return ("expr", expand(parse_math(line)))


def is_check_step(line: str) -> bool:
    """A step with no x, like "-7(8) + 4 = -52": substituting the answer back in
    to check it. Not equivalent to the original equation, but valid teaching."""
    return "x" not in line and any(op in line for op in "=<>")


def check_step_is_true(line: str) -> bool:
    """True if a check step is a true statement ("-52 = -52" yes, "-50 = -52" no)."""
    line = line.strip()
    if any(op in line for op in "<>"):
        lhs, op, rhs = parse_inequality(line)
        return bool(Rel(lhs, rhs, op))
    sides = line.split("=")
    if len(sides) != 2:
        raise InvalidInput("expected one '='")
    return simplify(parse_math(sides[0].strip()) - parse_math(sides[1].strip())) == 0


def check_reply(reply: TutorReply, ctx: TutorContext) -> list[str]:
    """Reasons the reply can't be shown as-is ([] = fine)."""
    issues: list[str] = []
    w = reply.walkthrough
    if not reply.message.strip():
        issues.append("The message is empty.")
    if ctx.problem and leaks_answer(ctx.problem, reply.message):
        issues.append("The message reveals the answer to the student's current practice problem.")
    if w.problem.strip() or w.steps:
        if not w.problem.strip() or not w.steps:
            issues.append("A walkthrough needs both a starting problem and at least one step.")
            return issues
        if len(w.steps) > MAX_STEPS:
            issues.append(f"Use at most {MAX_STEPS} steps.")
        try:
            start = math_signature(w.problem)
        except InvalidInput as e:
            issues.append(f"The walkthrough problem '{w.problem}' can't be parsed ({e}).")
            return issues
        if ctx.problem:
            try:
                # Same solution set = same final answer on screen, even if the
                # example looks different, so that would give the answer away too.
                if start == math_signature(ctx.problem.expression):
                    issues.append("The walkthrough has the same answer as the student's current problem; "
                                  "use a DIFFERENT example (the suggested similar problem).")
            except InvalidInput:
                pass
            if leaks_answer(ctx.problem, " ".join(s.operation for s in w.steps)):
                issues.append("A step label reveals the answer to the student's current problem.")
        previous = w.problem
        for i, step in enumerate(w.steps, 1):
            try:
                if is_check_step(step.result):
                    if not check_step_is_true(step.result):
                        issues.append(f"Step {i} ('{step.result}') is a check that isn't true.")
                        break
                    continue
                if math_signature(step.result) != start:
                    issues.append(f"Step {i} ('{previous}' -> '{step.result}') is not mathematically valid.")
                    break
            except InvalidInput as e:
                issues.append(f"Step {i} result '{step.result}' can't be parsed ({e}). Use only numbers, x, "
                              "+ - * / ^ ( ), sqrt( ), =, <, >, <=, >= and 'or'.")
                break
            previous = step.result
    return issues


# ---------- prompt ----------

SYSTEM_PROMPT = """You are a warm, patient algebra tutor inside a learning website for grades 6-11.
Explain ideas simply, in short sentences. Ask a guiding question when it helps.

Your reply has two parts:
- "message": your explanation in words (1-6 short sentences). Write math inline like 3x + 5 = 17.
- "walkthrough": a worked example shown to the student as a step-by-step animation.
  Include one when a worked example would help (it usually does). Otherwise use problem "" and no steps.
  Each step has a short "operation" (e.g. "Subtract 5 from both sides", "Divide by -2: flip the sign!")
  and the FULL "result" after that step. Make steps small: one operation each. At most 8 steps.
  Write math with numbers, x, + - * / ^ ( ), sqrt(49), =, <, >, <=, >=. Use implicit multiplication like 3x.
  For two solutions write one line like "x - 2 = 0 or x + 3 = 0".
  Every step is checked by a computer algebra system; invalid steps are rejected.

Rules:
- If the student is working on a practice problem, NEVER give its answer or solve it for them,
  in the message or the walkthrough. Guide them, and use the similar example provided instead.
- Stay on algebra and on this website's topics. If asked about something unrelated, gently steer back.
"""


def _context_text(ctx: TutorContext) -> str:
    lines = []
    if ctx.course in COURSES:
        lines.append(f"Course: {COURSES[ctx.course].name}")
    unit = UNITS[ctx.unit][1] if ctx.unit in UNITS else None
    if unit:
        lines.append(f"Unit: {unit.name}")
    skills = list(unit.skills) if unit else (COURSES[ctx.course].skills if ctx.course in COURSES else [])
    if skills:
        lines.append("Topics in scope (lesson summaries):")
        lines += [f"- {SKILLS[s].name}: {CONCEPTS[s].summary}" for s in skills]
        known = [s for s in skills if s in ctx.mastery]
        if known:
            lines.append("The student's mastery (0-100%, 70% = mastered): "
                         + ", ".join(f"{SKILLS[s].name} {round(ctx.mastery[s] * 100)}%" for s in known))
    if ctx.problem:
        p = ctx.problem
        lines.append(f"The student is currently working on this practice problem: {p.prompt} {p.expression}")
        lines.append("Do NOT solve it or give its answer.")
        similar = similar_problem(p)
        lines.append(f"If you show a worked example, use this similar problem instead: {similar.expression}")
    if ctx.mode == "explain_unit" and skills:
        example = generate_problem(skills[0], random.randrange(10**9))
        lines.append(f"The student asked you to explain this unit. Teach its main idea, then work through "
                     f"this example: {example.expression}")
    if ctx.mode == "selection" and ctx.selection:
        lines.append(f'The student highlighted this text and wants it explained: "{ctx.selection}"')
    return "\n".join(lines)


def similar_problem(p: Problem) -> Problem:
    """Same skill, different numbers (a different seed), and not the same problem."""
    seed = int(p.id.split(":")[1])
    for k in range(1, 20):
        q = generate_problem(p.skill, seed + 7919 * k)
        if q.expression != p.expression and q.answer != p.answer:
            return q
    return q


def build_system(ctx: TutorContext) -> str:
    context = _context_text(ctx)
    return SYSTEM_PROMPT + ("\nContext:\n" + context if context else "")


# ---------- the loop ----------

FALLBACK = ("Sorry, I couldn't put together an explanation I could double-check just now. "
            "Try asking in a different way, or open the lesson for this topic.")


def ask_tutor(messages: list[dict], ctx: TutorContext, llm: TutorLLM) -> TutorResult:
    system = build_system(ctx)
    rejections: list[str] = []
    last_ok_text: str | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            reply = llm.reply(system, messages, rejections)
        except HintLLMError as e:
            rejections.append(f"attempt {attempt}: LLM error: {e}")
            continue
        issues = check_reply(reply, ctx)
        if not issues:
            has_w = bool(reply.walkthrough.steps)
            return TutorResult(reply.message, reply.walkthrough if has_w else None, has_w, attempt, "llm", rejections)
        # Remember a text-only answer that is safe, in case the math never verifies.
        if not (ctx.problem and leaks_answer(ctx.problem, reply.message)) and reply.message.strip():
            last_ok_text = reply.message
        rejections += [f"attempt {attempt}: {i}" for i in issues]
    if last_ok_text:
        return TutorResult(last_ok_text, None, False, MAX_ATTEMPTS, "llm", rejections)
    return TutorResult(FALLBACK, None, False, MAX_ATTEMPTS, "fallback", rejections)


# ---------- Claude implementation ----------

class ClaudeTutorLLM:
    def __init__(self, model: str | None = None, client: anthropic.Anthropic | None = None):
        self.client = client or anthropic.Anthropic(timeout=90.0, max_retries=2)
        self.model = model or os.environ.get("TUTOR_MODEL", os.environ.get("HINT_MODEL", DEFAULT_MODEL))
        self.usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
        self._lock = threading.Lock()

    def reply(self, system: str, messages: list[dict], rejections: list[str]) -> TutorReply:
        msgs = list(messages)
        if rejections:
            # Feedback from the checker goes in as an extra user turn.
            msgs = msgs + [{"role": "user", "content": "Your previous reply was rejected by an automatic checker:\n"
                            + "\n".join(f"- {r}" for r in rejections) + "\nPlease answer again, fixing these."}]
        try:
            msg = self.client.beta.messages.parse(
                model=self.model,
                max_tokens=6000,
                system=system,
                messages=msgs,
                output_format=TutorReply,
                output_config={"effort": "low"},  # chat needs to feel fast
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            raise HintConfigError("Claude API key is invalid; check ANTHROPIC_API_KEY in .env") from e
        except TypeError as e:
            raise HintConfigError("No Claude API key configured; set ANTHROPIC_API_KEY in .env") from e
        except anthropic.BadRequestError as e:
            raise HintConfigError(f"Claude API rejected the request: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise HintLLMError(f"connection error: {e}") from e
        except anthropic.APIStatusError as e:
            raise HintLLMError(f"API error {e.status_code}: {e.message}") from e
        with self._lock:
            self.usage["input_tokens"] += msg.usage.input_tokens
            self.usage["output_tokens"] += msg.usage.output_tokens
            self.usage["calls"] += 1
        if msg.stop_reason == "refusal":
            raise HintLLMError("model declined to answer")
        if msg.stop_reason == "max_tokens" or msg.parsed_output is None:
            raise HintLLMError(f"no usable output (stop_reason={msg.stop_reason})")
        return msg.parsed_output
