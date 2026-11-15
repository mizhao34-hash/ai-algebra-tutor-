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

from sympy import Add, Integer, Mul, Pow, Rel, Symbol, expand, nan, nsimplify, oo, solve_univariate_inequality, sqrt, zoo
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
_INEQUALITY = re.compile(r"(<=|>=|<|>)")
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
    text = text.translate(table).replace("≤", "<=").replace("≥", ">=")
    # "√49" -> "sqrt(49)", "√(x)" -> "sqrt(x)"
    text = re.sub(r"√\s*(\d+)", r"sqrt(\1)", text).replace("√", "sqrt")
    return text.strip()


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
    # The only word allowed is the square-root function, and only as "sqrt(".
    bare = text.replace("sqrt(", "(") if text else text
    if not text or len(text) > MAX_INPUT_LEN or not _ALLOWED.match(bare) or "=" in text:
        raise InvalidInput("Use only numbers, x, + - * / ^, sqrt( ) and parentheses.")
    if not _safe_powers(text):
        raise InvalidInput(f"Powers must be a whole number up to {MAX_EXPONENT}, like x^2.")
    try:
        expr = parse_expr(text, local_dict={"x": X, "sqrt": sqrt}, transformations=_TRANSFORMS, evaluate=evaluate)
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


def _x_power(f) -> int | None:
    """x -> 1, x^2 -> 2 (whole-number powers of x), anything else -> None."""
    if f == X:
        return 1
    if isinstance(f, Pow) and f.base == X and isinstance(f.exp, Integer) and f.exp >= 2:
        return int(f.exp)
    return None


def _is_simple_term(term) -> tuple[bool, int]:
    """Return (is_simple, degree) for one unevaluated term.

    Simple terms: 5, -5, 3/4, x, -3x, (3/4)x, x^2, -2x^2. At most one numerator
    integer, one integer denominator, one power of x, plus an optional leading -1.
    """
    if _x_power(term):
        return True, _x_power(term)
    if isinstance(term, Integer):
        return True, 0
    if not isinstance(term, Mul):
        return False, 0
    factors = _flat_factors(term)
    if Integer(-1) in factors:  # "-12" in "3x - 12" parses as Mul(-1, 12)
        factors.remove(Integer(-1))
    xs = [f for f in factors if _x_power(f)]
    nums = [f for f in factors if isinstance(f, Integer)]
    dens = [f for f in factors if isinstance(f, Pow) and isinstance(f.base, Integer) and f.exp == -1]
    if len(xs) + len(nums) + len(dens) != len(factors):  # something else, e.g. a nested sum
        return False, 0
    if len(xs) > 1 or len(nums) > 1 or len(dens) > 1:
        return False, 0
    if nums and nums[0] == 0:
        return False, 0
    if dens:
        num = abs(int(nums[0])) if nums else 1
        den = int(dens[0].base)
        if den <= 1 or gcd(num, den) != 1:  # 8/2 and 4/1 are not simplest form
            return False, 0
    return True, (_x_power(xs[0]) if xs else 0)


def is_simplest_polynomial(text: str) -> bool:
    """True if text is a sum of simple terms with at most one term per power
    of x: "2x + 7" and "x^2 + 5x + 6" yes; "x + x + 7", "3(x - 4)" no."""
    expr = parse_math(text, evaluate=False)
    degrees = []
    for term in Add.make_args(expr):
        ok, degree = _is_simple_term(term)
        if not ok:
            return False
        degrees.append(degree)
    return len(degrees) == len(set(degrees))


def _is_simplest_number(text: str) -> bool:
    return is_simplest_polynomial(text) and not parse_math(text).has(X)


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
    if not is_simplest_polynomial(text):
        return GradeResult("not_simplified", "Equivalent, but not fully simplified yet.")
    return GradeResult("correct", "Correct!")


# ---------- inequalities ----------

def parse_inequality(text: str):
    """"2x + 1 > 5" -> (lhs, ">", rhs). Raises InvalidInput."""
    parts = [p.strip() for p in _INEQUALITY.split(text)]
    if len(parts) != 3:
        raise InvalidInput("Write an inequality with one of <, >, <= or >=.")
    lhs, op, rhs = parts
    return parse_math(lhs), op, parse_math(rhs)


def inequality_solutions(lhs, op, rhs):
    """The set of x that satisfy it, e.g. Interval.open(3, oo) for x > 3."""
    return solve_univariate_inequality(Rel(lhs, rhs, op), X, relational=False)


def _grade_inequality(problem: Problem, text: str) -> GradeResult:
    if "=" in text.replace("<=", "").replace(">=", ""):
        return GradeResult("invalid", "Use <, >, <= or >=, like x > 3.")
    lhs, op, rhs = parse_inequality(text)
    given = inequality_solutions(lhs, op, rhs)
    expected = inequality_solutions(*parse_inequality(problem.answer))
    if given != expected:
        if {given.inf, given.sup} - {oo, -oo} == {expected.inf, expected.sup} - {oo, -oo}:
            if (given.sup == oo) == (expected.sup == oo):
                # Same boundary and direction: only < vs <= (or > vs >=) differs.
                return GradeResult("incorrect", "Right boundary and direction, but check whether the boundary "
                                                "itself is included (< or <=).")
            # Same boundary, wrong direction: the classic "forgot to flip the sign" mistake.
            return GradeResult("incorrect", "Right boundary, but check the direction of the inequality sign. "
                                            "Did you multiply or divide by a negative number?")
        return GradeResult("incorrect", "Not quite. Check your steps and try again.")
    left, right = [p.strip() for p in _INEQUALITY.split(text)[::2]]
    number = right if left == "x" else left if right == "x" else None
    if number is None or not _is_simplest_number(number):
        return GradeResult("not_simplified", "Right, but write it with x alone on one side, like x > 3.")
    return GradeResult("correct", "Correct!")


def grade(problem: Problem, student_input: str) -> GradeResult:
    text = normalize(student_input)
    try:
        if problem.kind == "simplify":
            return _grade_expression(problem, text)
        if problem.kind == "inequality":
            return _grade_inequality(problem, text)
        return _grade_value(problem, text)
    except InvalidInput as e:
        return GradeResult("invalid", str(e))
