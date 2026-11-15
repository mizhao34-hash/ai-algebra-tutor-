import pytest
from sympy import Eq, solve

from app.courses import CONCEPTS, COURSES, course_of
from app.grader import X, parse_math
from app.recommend import is_unlocked, recommend
from app.skills import SKILLS, topological_order


def value(line: str):
    """A worked-example line as something comparable: the solution set of an
    equation (or of several joined by "or"), or the expression itself."""
    if "=" in line:
        sols = set()
        for eq in line.split(" or "):
            lhs, rhs = eq.split("=")
            sols |= set(solve(Eq(parse_math(lhs), parse_math(rhs)), X))
        return ("eq", frozenset(sols))
    return ("expr", parse_math(line).expand())


@pytest.mark.parametrize("skill", SKILLS)
def test_worked_example_every_line_is_equivalent(skill):
    lines = CONCEPTS[skill].example
    assert len(lines) >= 3
    first = value(lines[0])
    for line in lines[1:]:
        assert value(line) == first, (skill, line)


@pytest.mark.parametrize("skill", SKILLS)
def test_worked_example_ends_in_simplest_answer(skill):
    last = CONCEPTS[skill].example[-1].replace(" ", "")
    if "=" in CONCEPTS[skill].example[0]:
        for part in last.split("or"):  # "x=7orx=-7" for two solutions
            assert part.startswith("x=") and parse_math(part[2:]).is_number, skill
    else:
        from app.grader import is_simplest_linear
        assert is_simplest_linear(last), skill


def test_courses_cover_every_skill_once_in_teaching_order():
    order = topological_order()
    for course in COURSES.values():
        skills = course.skills
        # Within a course, prerequisites that are in the same course come first.
        for i, s in enumerate(skills):
            for p in SKILLS[s].prerequisites:
                if p in skills:
                    assert skills.index(p) < i, (course.id, s, p)
        assert all(s in order for s in skills)
    assert course_of("two_step") == "algebra_1" and course_of("distributive") == "pre_algebra"


def test_course_gating_ignores_prerequisites_in_other_courses():
    zero = {s: 0.0 for s in SKILLS}
    alg1 = COURSES["algebra_1"].skills
    # Globally, one_step_add is locked behind integer_ops (Pre-Algebra)...
    assert not is_unlocked("one_step_add", zero)
    # ...but inside Algebra 1 it is a starting point.
    assert is_unlocked("one_step_add", zero, alg1)
    assert not is_unlocked("two_step", zero, alg1)
    assert recommend(zero, alg1) == "one_step_add"
    assert recommend(zero, COURSES["pre_algebra"].skills) == "integer_ops"
