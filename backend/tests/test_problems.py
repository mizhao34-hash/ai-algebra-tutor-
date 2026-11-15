import re

import pytest
from sympy import Eq, solve

from app.grader import X, answer_values, grade, is_simplest_linear, parse_math
from app.problems import generate_problem, problem_from_id
from app.skills import SKILLS

SEEDS = range(300)


@pytest.mark.parametrize("skill", SKILLS)
def test_deterministic(skill):
    assert generate_problem(skill, 7) == generate_problem(skill, 7)


@pytest.mark.parametrize("skill", SKILLS)
def test_round_trip_id(skill):
    p = generate_problem(skill, 42)
    assert problem_from_id(p.id) == p


@pytest.mark.parametrize("skill", SKILLS)
def test_not_all_the_same(skill):
    assert len({generate_problem(skill, s).expression for s in range(50)}) > 20


@pytest.mark.parametrize("skill", SKILLS)
def test_answer_is_mathematically_right(skill):
    """Parse each problem with the grader's parser and check the stored answer."""
    for seed in SEEDS:
        p = generate_problem(skill, seed)
        if p.kind == "solve":
            lhs, rhs = p.expression.split("=")
            sols = solve(Eq(parse_math(lhs), parse_math(rhs)), X)
            assert sorted(sols) == sorted(answer_values(p)), p
        else:
            assert (parse_math(p.expression) - parse_math(p.answer)).expand() == 0, p


@pytest.mark.parametrize("skill", SKILLS)
def test_canonical_answer_grades_correct(skill):
    for seed in SEEDS:
        p = generate_problem(skill, seed)
        assert grade(p, p.answer).correct, p
        assert all(is_simplest_linear(a.strip()) for a in p.answer.split(",")), p


@pytest.mark.parametrize("skill", ["two_step", "vars_both_sides", "parentheses", "multi_step"])
def test_equations_need_work(skill):
    """The prompt must not already show the answer, e.g. '1x + 0 = 4'."""
    for seed in SEEDS:
        p = generate_problem(skill, seed)
        assert not re.search(r"(?<!\d)1x", p.expression), p  # "1x" should be shown as "x"
        assert not re.search(r"[+-] 0(?!\d)", p.expression), p  # no "+ 0" terms


def test_unknown_skill_and_bad_id():
    with pytest.raises(ValueError):
        generate_problem("calculus", 1)
    with pytest.raises(ValueError):
        problem_from_id("two_step:abc")
