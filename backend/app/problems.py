"""Template-based problem generator, one template family per skill.

Problems are deterministic in (skill, seed): the same pair always gives the same
problem. The backend can therefore identify a problem by "skill:seed" and
regenerate it for grading instead of storing every problem.

Every equation is built "answer first": we pick the integer solution x, then
compute the right-hand side from it, so solutions are always integers.
"""

import random
from dataclasses import dataclass

from .skills import SKILLS

COEF_RANGE = [n for n in range(-9, 10) if n != 0]
# For a(...) templates: a = ±1 would make the parentheses pointless.
MULT_RANGE = [n for n in COEF_RANGE if abs(n) > 1]
SOLUTION_RANGE = range(-10, 11)


@dataclass(frozen=True)
class Problem:
    id: str          # "skill:seed", enough to regenerate the problem
    skill: str
    kind: str        # "evaluate" (a number), "simplify" (an expression), "solve" (x = ...)
    prompt: str      # instruction shown to the student
    expression: str  # the math itself, in a form the grader's parser accepts
    answer: str      # canonical answer, e.g. "4" or "2x + 7"


# ---------- display helpers ----------

def _term(coef: int, var: str = "x", first: bool = False) -> str:
    """Format one term with its sign: (3,first) -> '3x', (-1) -> ' - x', (5,'') -> ' + 5'."""
    mag = abs(coef)
    body = (var if mag == 1 else f"{mag}{var}") if var else str(mag)
    if first:
        return f"-{body}" if coef < 0 else body
    return f" - {body}" if coef < 0 else f" + {body}"


def _linear(a: int, b: int) -> str:
    """Format a*x + b, skipping zero parts: (3,-4) -> '3x - 4', (0,5) -> '5'."""
    if a == 0:
        return str(b)
    return _term(a, first=True) + (_term(b, var="") if b != 0 else "")


def _paren_num(n: int) -> str:
    """Wrap negatives in parentheses so '3 * -2' is shown as '3(-2)'."""
    return f"({n})" if n < 0 else str(n)


def _times(a: int, inner: str) -> str:
    """a(inner), with a = -1 shown as '-(inner)'."""
    return f"-({inner})" if a == -1 else f"{a}({inner})"


# ---------- one generator per skill ----------

def _integer_ops(r: random.Random):
    a, b, c = r.randint(-12, 12), r.choice(COEF_RANGE), r.choice(COEF_RANGE)
    if r.random() < 0.5:
        # Always parenthesize c: "3(4)" is a product, while "34" would be a different number.
        expr, ans = f"{a} + {b}({c})" if b > 0 else f"{a} - {-b}({c})", a + b * c
    else:
        expr, ans = f"{a} - {_paren_num(b)}", a - b
    return "evaluate", "Evaluate:", expr, str(ans)


def _combine_like_terms(r: random.Random):
    while True:
        a, c = r.choice(COEF_RANGE), r.choice(COEF_RANGE)
        b, d = r.choice(COEF_RANGE), r.choice(COEF_RANGE)
        if a + c != 0:  # keep an x term in the answer
            break
    expr = _term(a, first=True) + _term(b, var="") + _term(c) + _term(d, var="")
    return "simplify", "Simplify:", expr, _linear(a + c, b + d)


def _distributive(r: random.Random):
    a, b = r.choice(MULT_RANGE), r.choice(COEF_RANGE)
    return "simplify", "Expand:", _times(a, _linear(1, b)), _linear(a, a * b)


def _one_step_add(r: random.Random):
    x, b = r.choice(SOLUTION_RANGE), r.choice(COEF_RANGE)
    return "solve", "Solve for x:", f"{_linear(1, b)} = {x + b}", str(x)


def _one_step_mul(r: random.Random):
    x, a = r.choice(SOLUTION_RANGE), r.choice(MULT_RANGE)
    if r.random() < 0.5:
        return "solve", "Solve for x:", f"{a}x = {a * x}", str(x)
    # x/a = q: pick the quotient so x = a*q stays an integer.
    q = r.choice(range(-5, 6))
    return "solve", "Solve for x:", f"x/{_paren_num(a)} = {q}", str(a * q)


def _two_step(r: random.Random):
    x, a, b = r.choice(SOLUTION_RANGE), r.choice(MULT_RANGE), r.choice(COEF_RANGE)
    return "solve", "Solve for x:", f"{_linear(a, b)} = {a * x + b}", str(x)


def _vars_both_sides(r: random.Random):
    while True:
        a, c = r.choice(COEF_RANGE), r.choice(COEF_RANGE)
        if a != c:  # a == c would cancel x entirely
            break
    x, b = r.choice(SOLUTION_RANGE), r.choice(COEF_RANGE)
    d = a * x + b - c * x  # makes ax + b = cx + d true at x
    return "solve", "Solve for x:", f"{_linear(a, b)} = {_linear(c, d)}", str(x)


def _parentheses(r: random.Random):
    x, a, b = r.choice(SOLUTION_RANGE), r.choice(MULT_RANGE), r.choice(COEF_RANGE)
    return "solve", "Solve for x:", f"{_times(a, _linear(1, b))} = {a * (x + b)}", str(x)


def _multi_step(r: random.Random):
    # a(x + b) + cx = dx + e
    while True:
        a, c, d = r.choice(MULT_RANGE), r.choice(COEF_RANGE), r.choice(COEF_RANGE)
        if a + c != d:  # otherwise x cancels
            break
    x, b = r.choice(SOLUTION_RANGE), r.choice(COEF_RANGE)
    e = a * (x + b) + c * x - d * x
    lhs = _times(a, _linear(1, b)) + _term(c)
    return "solve", "Solve for x:", f"{lhs} = {_linear(d, e)}", str(x)


GENERATORS = {
    "integer_ops": _integer_ops,
    "combine_like_terms": _combine_like_terms,
    "distributive": _distributive,
    "one_step_add": _one_step_add,
    "one_step_mul": _one_step_mul,
    "two_step": _two_step,
    "vars_both_sides": _vars_both_sides,
    "parentheses": _parentheses,
    "multi_step": _multi_step,
}
assert set(GENERATORS) == set(SKILLS), "every skill needs exactly one generator"


def generate_problem(skill: str, seed: int) -> Problem:
    if skill not in GENERATORS:
        raise ValueError(f"unknown skill: {skill}")
    kind, prompt, expression, answer = GENERATORS[skill](random.Random(seed))
    return Problem(f"{skill}:{seed}", skill, kind, prompt, expression, answer)


def problem_from_id(problem_id: str) -> Problem:
    """Inverse of Problem.id: 'two_step:17' -> the same problem again."""
    skill, _, seed = problem_id.partition(":")
    if not seed.lstrip("-").isdigit():
        raise ValueError(f"bad problem id: {problem_id}")
    return generate_problem(skill, int(seed))
