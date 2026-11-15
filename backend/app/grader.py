"""SymPy grader for student answers.

Grading has two checks:
  1. Equivalence: is the answer mathematically equal to the canonical answer?
  2. Form: is it written in simplest form? ("x = 8/2" has the right value but
     isn't finished.) Form is judged on the UNEVALUATED parse, because SymPy
     normally rewrites 3(x - 4) to 3x - 12 and that would hide the difference.

Security: SymPy's parse_expr calls eval(), so student text must never reach it
unchecked. We allow only digits, x, + - * / ^ ( ) = . and spaces, and cap the
length. Powers are needed for quadratics but are dangerous (9^9^9 would hang
the server), so every ^ must be followed by a whole number <= MAX_EXPONENT and
powers can't be chained.
"""

import re
from dataclasses import dataclass
from math import gcd
from tokenize import TokenError  # raised for unbalanced parentheses like "3(x"

from sympy import Add, Integer, Mul, Pow, Symbol, expand, nan, nsimplify, oo, zoo
from sympy.core.sympify import SympifyError
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from .problems import Problem

X = Symbol("x")
MAX_INPUT_LEN = 60
MAX_EXPONENT = 4
_ALLOWED = re.compile(r"^[0-9x+\-*/^().=\s]+$")
_POWER = re.compile(r"\^\s*(\d+)")
# implicit multiplication lets students type "3x" and "2(x+1)"; convert_xor reads ^ as a power.
_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)


class InvalidInput(ValueError):
    pass


@dataclass(frozen=True)
class GradeResult:
    status: str   # "correct" | "not_simplified" | "incorrect" | "invalid"
    message: str

    @property
    def correct(self) -> bool:
        return self.status == "correct"


def normalize(text: str) -> str:
    """Map look-alike characters students paste (−, ×, ·, ÷, X) to ASCII."""
    table = str.maketrans({"−": "-", "–": "-", "×": "*", "·": "*", "÷": "/", "X": "x", "²": "^2"})
    return text.translate(table).strip()


def _safe_powers(text: str) -> bool:
    """Every power is ^ followed by a small whole number, and not chained (a^2^2)."""
    t = text.replace("**", "^")
    matches = list(_POWER.finditer(t))
    if t.count("^") != len(matches):  # some ^ isn't followed by a number, e.g. 2^x or 2^(3)
        return False
    for m in matches:
        rest = t[m.end():].lstrip()
        if int(m.group(1)) > MAX_EXPONENT or rest.startswith(("^", ".")):
            return False
    return True


def parse_math(text: str, evaluate: bool = True):
    """Parse one side of an equation (no '='). Raises InvalidInput."""
    if not text or len(text) > MAX_INPUT_LEN or not _ALLOWED.match(text) or "=" in text:
        raise InvalidInput("Use only numbers, x, + - * / ^ and parentheses.")
    if not _safe_powers(text):
        raise InvalidInput(f"Powers must be a whole number up to {MAX_EXPONENT}, like x^2.")
    try:
        expr = parse_expr(text, local_dict={"x": X}, transformations=_TRANSFORMS, evaluate=evaluate)
    except (SyntaxError, TypeError, SympifyError, TokenError):
        raise InvalidInput("That expression couldn't be read.")
    if expr.has(zoo, oo, nan):  # e.g. division by zero
        raise InvalidInput("That expression divides by zero.")
    return expr


# ---------- simplest-form check ----------

def _flat_factors(term) -> list:
    """Unevaluated '-3x' is Mul(-1, Mul(3, x)); flatten to [-1, 3, x]."""
    out = []
    for f in Mul.make_args(term):
        out.extend(_flat_factors(f) if isinstance(f, Mul) else [f])
    return out


def _is_simple_term(term) -> tuple[bool, bool]:
    """Return (is_simple, has_x) for one unevaluated term.

    Simple terms: 5, -5, 3/4, x, -x, 3x, -3x, (3/4)x. At most one numerator
    integer, one integer denominator, one x, plus an optional leading -1.
    """
    if term == X:
        return True, True
    if isinstance(term, Integer):
        return True, False
    if not isinstance(term, Mul):
        return False, False
    factors = _flat_factors(term)
    if Integer(-1) in factors:  # "-12" in "3x - 12" parses as Mul(-1, 12)
        factors.remove(Integer(-1))
    xs = [f for f in factors if f == X]
    nums = [f for f in factors if isinstance(f, Integer)]
    dens = [f for f in factors if isinstance(f, Pow) and isinstance(f.base, Integer) and f.exp == -1]
    if len(xs) + len(nums) + len(dens) != len(factors):  # something else, e.g. a nested sum
        return False, False
    if len(xs) > 1 or len(nums) > 1 or len(dens) > 1:
        return False, False
    if nums and nums[0] == 0:
        return False, False
    if dens:
        num = abs(int(nums[0])) if nums else 1
        den = int(dens[0].base)
        if den <= 1 or gcd(num, den) != 1:  # 8/2 and 4/1 are not simplest form
            return False, False
    return True, bool(xs)


def is_simplest_linear(text: str) -> bool:
    """True if text is written as (at most) one x term plus one constant."""
    expr = parse_math(text, evaluate=False)
    x_terms = const_terms = 0
    for term in Add.make_args(expr):
        ok, has_x = _is_simple_term(term)
        if not ok:
            return False
        x_terms += has_x
        const_terms += not has_x
    return x_terms <= 1 and const_terms <= 1


def _is_simplest_number(text: str) -> bool:
    return is_simplest_linear(text) and not parse_math(text).has(X)


# ---------- grading ----------

def _equal(a, b) -> bool:
    return expand(a - b) == 0


def answer_values(problem: Problem) -> list:
    """The problem's answer(s): '4' -> [4]; quadratics store '-3, 2' -> [-3, 2]."""
    return [parse_math(a.strip()) for a in problem.answer.split(",")]


def _number(v):
    # 4.0 and 4 are the same value; nsimplify turns floats into exact rationals.
    return nsimplify(v, rational=True)


def parse_solutions(text: str) -> list[tuple[object, str]]:
    """Read one or more solutions: "x = 4", "4 = x", "x = 2, x = -3",
    "x = 2 or x = -3", "2, -3", "x = ±7". Returns (value, written text) pairs.
    Raises InvalidInput if a part isn't "x = number" or a number."""
    values = []
    for part in re.split(r",|\bor\b|\band\b", text):
        part = part.strip()
        if "=" in part:
            sides = [s.strip() for s in part.split("=")]
            if len(sides) != 2:
                raise InvalidInput("Write your answer as x = a number.")
            # Accept "x = 4" or "4 = x".
            if sides[0] == "x":
                part = sides[1]
            elif sides[1] == "x":
                part = sides[0]
            else:
                raise InvalidInput("Write your answer as x = a number.")
        # "±7", "+-7" or "+/-7" means both 7 and -7 (only at the start of a solution,
        # so "2+-3" elsewhere still means 2 + (-3)).
        signs = [1]
        for prefix in ("±", "+/-", "+-"):
            if part.startswith(prefix):
                signs, part = [1, -1], part[len(prefix):].strip()
                break
        value = parse_math(part)
        if value.has(X):
            raise InvalidInput("Your answer should be a number, without x.")
        values += [(sign * value, part) for sign in signs]
    return values


def _grade_value(problem: Problem, text: str) -> GradeResult:
    """For 'evaluate' and 'solve': the answer is one number, or for some
    equations (quadratics) a set of numbers in any order."""
    if problem.kind == "evaluate":
        if "=" in text:
            return GradeResult("invalid", "Enter just the number.")
        got = [(parse_math(text), text)]
        if got[0][0].has(X):
            return GradeResult("invalid", "Your answer should be a number, without x.")
    else:
        got = parse_solutions(text)
    expected = {_number(v) for v in answer_values(problem)}
    given = {_number(v) for v, _ in got}
    if given != expected:
        if len(expected) > 1 and given and given < expected:
            return GradeResult("incorrect", "That's one solution, but this equation has another one too.")
        return GradeResult("incorrect", "Not quite. Check your steps and try again.")
    if not all(_is_simplest_number(t) for _, t in got):
        return GradeResult("not_simplified", "Right value, but simplify it to a single number.")
    return GradeResult("correct", "Correct!")


def _grade_expression(problem: Problem, text: str) -> GradeResult:
    """For 'simplify': the answer must be an equivalent, fully simplified expression."""
    if "=" in text:
        return GradeResult("invalid", "Enter an expression, not an equation.")
    if not _equal(parse_math(text), parse_math(problem.answer)):
        return GradeResult("incorrect", "Not quite. Check your steps and try again.")
    if not is_simplest_linear(text):
        return GradeResult("not_simplified", "Equivalent, but not fully simplified yet.")
    return GradeResult("correct", "Correct!")


def grade(problem: Problem, student_input: str) -> GradeResult:
    text = normalize(student_input)
    try:
        if problem.kind == "simplify":
            return _grade_expression(problem, text)
        return _grade_value(problem, text)
    except InvalidInput as e:
        return GradeResult("invalid", str(e))
