"""SymPy grader for student answers.

Grading has two checks:
  1. Equivalence: is the answer mathematically equal to the canonical answer?
  2. Form: is it written in simplest form? ("x = 8/2" has the right value but
     isn't finished.) Form is judged on the UNEVALUATED parse, because SymPy
     normally rewrites 3(x - 4) to 3x - 12 and that would hide the difference.

Security: SymPy's parse_expr calls eval(), so student text must never reach it
unchecked. We allow only digits, x, + - * / ( ) = . and spaces, cap the length,
and forbid powers entirely (linear equations need none, and inputs like 9**9**9
would hang the server).
"""

import re
from dataclasses import dataclass
from math import gcd
from tokenize import TokenError  # raised for unbalanced parentheses like "3(x"

from sympy import Add, Integer, Mul, Pow, Symbol, expand, nan, oo, zoo
from sympy.core.sympify import SympifyError
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from .problems import Problem

X = Symbol("x")
MAX_INPUT_LEN = 60
_ALLOWED = re.compile(r"^[0-9x+\-*/().=\s]+$")
# implicit multiplication lets students type "3x" and "2(x+1)".
_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


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
    table = str.maketrans({"−": "-", "–": "-", "×": "*", "·": "*", "÷": "/", "X": "x"})
    return text.translate(table).strip()


def parse_math(text: str, evaluate: bool = True):
    """Parse one side of an equation (no '='). Raises InvalidInput."""
    if not text or len(text) > MAX_INPUT_LEN or not _ALLOWED.match(text) or "**" in text or "=" in text:
        raise InvalidInput("Use only numbers, x, + - * / and parentheses.")
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


def _grade_value(problem: Problem, text: str) -> GradeResult:
    """For 'evaluate' and 'solve': the answer must be a number."""
    if problem.kind == "solve" and "=" in text:
        sides = [s.strip() for s in text.split("=")]
        if len(sides) != 2:
            return GradeResult("invalid", "Write your answer as x = a number.")
        # Accept "x = 4" or "4 = x".
        if parse_math(sides[0]) == X:
            text = sides[1]
        elif parse_math(sides[1]) == X:
            text = sides[0]
        else:
            return GradeResult("invalid", "Write your answer as x = a number.")
    value = parse_math(text)
    if value.has(X):
        return GradeResult("invalid", "Your answer should be a number, without x.")
    if not _equal(value, parse_math(problem.answer)):
        return GradeResult("incorrect", "Not quite. Check your steps and try again.")
    if not _is_simplest_number(text):
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
