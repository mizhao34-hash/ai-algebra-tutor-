import pytest

from app.grader import InvalidInput, grade, is_simplest_linear, parse_math
from app.problems import Problem

SOLVE = Problem("t:1", "two_step", "solve", "Solve for x:", "3x + 5 = 17", "4")
NEG = Problem("t:2", "two_step", "solve", "Solve for x:", "2x + 9 = 3", "-3")
SIMPLIFY = Problem("t:3", "combine_like_terms", "simplify", "Simplify:", "3x + 5 - x + 2", "2x + 7")
EXPAND = Problem("t:4", "distributive", "simplify", "Expand:", "-3(x - 4)", "-3x + 12")
EVAL = Problem("t:5", "integer_ops", "evaluate", "Evaluate:", "-7 + 3(-2)", "-13")


@pytest.mark.parametrize("answer", ["4", "x = 4", "x=4", " 4 = x ", "X = 4"])
def test_solve_correct_forms(answer):
    assert grade(SOLVE, answer).status == "correct"


@pytest.mark.parametrize("answer", ["-3", "x = -3", "x = −3", "-(3)"])
def test_negative_answers(answer):
    assert grade(NEG, answer).status == "correct"


@pytest.mark.parametrize("answer", ["5", "x = 3", "-4"])
def test_solve_incorrect(answer):
    assert grade(SOLVE, answer).status == "incorrect"


@pytest.mark.parametrize("answer", ["8/2", "x = 2 + 2", "x = 2*2", "4.0"])
def test_solve_not_simplified(answer):
    assert grade(SOLVE, answer).status == "not_simplified"


@pytest.mark.parametrize("answer", ["x", "x = x", "3x + 5 = 17", "y = 4", "x = 4 = 4", ""])
def test_solve_invalid(answer):
    assert grade(SOLVE, answer).status == "invalid"


@pytest.mark.parametrize("answer", ["2x + 7", "7 + 2x", "2*x+7", "2x+7"])
def test_simplify_correct(answer):
    assert grade(SIMPLIFY, answer).status == "correct"


@pytest.mark.parametrize("answer", ["3x + 5 - x + 2", "x + x + 7", "2x + 3 + 4", "2(x + 3.5)"])
def test_simplify_equivalent_but_unfinished(answer):
    assert grade(SIMPLIFY, answer).status == "not_simplified"


def test_simplify_incorrect_and_equation():
    assert grade(SIMPLIFY, "2x + 8").status == "incorrect"
    assert grade(SIMPLIFY, "y = 2x + 7").status == "invalid"


def test_expand():
    assert grade(EXPAND, "-3x + 12").correct
    assert grade(EXPAND, "12 - 3x").correct
    assert grade(EXPAND, "-3(x - 4)").status == "not_simplified"
    assert grade(EXPAND, "-3x - 12").status == "incorrect"


def test_evaluate():
    assert grade(EVAL, "-13").correct
    assert grade(EVAL, "-7 - 6").status == "not_simplified"
    assert grade(EVAL, "13").status == "incorrect"


@pytest.mark.parametrize(
    "evil",
    [
        "__import__('os').system('ls')",
        "9**9**9",
        "2^100",
        "x" * 100,
        "lambda: 1",
        "1/0",
        "3(x",
    ],
)
def test_rejects_unsafe_or_broken_input(evil):
    with pytest.raises(InvalidInput):
        parse_math(evil)
    assert grade(SOLVE, evil).status == "invalid"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3x - 12", True), ("-x", True), ("5", True), ("3/4", True), ("-3/4x", True),
        ("6/4", False), ("8/2", False), ("2*3x", False), ("4 - -2", False),
        ("3(x - 4)", False), ("0x + 5", False), ("x + 1 + 1", False),
    ],
)
def test_is_simplest_linear(text, expected):
    assert is_simplest_linear(text) is expected
