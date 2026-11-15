"""Courses (Pre-Algebra, Algebra 1), their units, and the concept lessons.

A course groups skills from skills.py into ordered units. The Concept tab shows
each skill's lesson; the Practice tab only practices that course's skills.

Concept examples are worked solutions, one line per step. Every line is
written in the grader's math syntax, and tests/test_courses.py verifies with
SymPy that each line is equivalent to the first and the last is the answer,
so a typo in a lesson fails the tests instead of teaching something wrong.
"""

from dataclasses import dataclass

from .skills import SKILLS


@dataclass(frozen=True)
class Concept:
    summary: str
    steps: tuple[str, ...]
    example: tuple[str, ...]  # worked example, first line = problem, last line = answer
    mistake: str              # a common mistake and why it's wrong


@dataclass(frozen=True)
class Unit:
    id: str
    name: str
    skills: tuple[str, ...]  # in teaching order


@dataclass(frozen=True)
class Course:
    id: str
    name: str
    grades: str
    description: str
    units: tuple[Unit, ...]

    @property
    def skills(self) -> list[str]:
        return [s for u in self.units for s in u.skills]


COURSES: dict[str, Course] = {
    c.id: c
    for c in [
        Course(
            "pre_algebra",
            "Pre-Algebra",
            "Grades 6–8",
            "Work with negative numbers and simplify algebraic expressions.",
            (
                Unit("integers", "Integers", ("integer_ops",)),
                Unit("expressions", "Algebraic expressions", ("combine_like_terms", "distributive")),
            ),
        ),
        Course(
            "algebra_1",
            "Algebra 1",
            "Grades 8–9",
            "Solve linear equations, from one step to many.",
            (
                Unit("one_step", "One-step equations", ("one_step_add", "one_step_mul")),
                Unit("multi_step", "Multi-step equations",
                     ("two_step", "vars_both_sides", "parentheses", "multi_step")),
            ),
        ),
    ]
}


def course_of(skill: str) -> str:
    return next(c.id for c in COURSES.values() if skill in c.skills)


CONCEPTS: dict[str, Concept] = {
    "integer_ops": Concept(
        "Add, subtract, multiply and divide positive and negative numbers. "
        "Multiplication and division come before addition and subtraction.",
        (
            "Do multiplication and division first, from left to right.",
            "Subtracting a negative is the same as adding a positive: 5 - (-3) = 5 + 3.",
            "Same signs multiply to a positive; different signs multiply to a negative.",
            "To add numbers with different signs, subtract their sizes and keep the sign of the larger one.",
        ),
        ("-7 + 3(-2)", "-7 + (-6)", "-13"),
        "Adding before multiplying: -7 + 3(-2) is not (-7 + 3)(-2) = 8. "
        "Multiply first: 3(-2) = -6, then -7 + (-6) = -13.",
    ),
    "combine_like_terms": Concept(
        "Like terms have the same variable part, like 3x and -x, or 5 and 2. "
        "Combine them by adding their coefficients.",
        (
            "Find the x terms and the number terms, keeping each term's sign with it.",
            "Add the coefficients of the x terms (x by itself means 1x).",
            "Add the number terms.",
            "Write the result as one x term and one number.",
        ),
        ("3x + 5 - x + 2", "3x - x + 5 + 2", "2x + 7"),
        "Losing the sign in front of a term: in 3x + 5 - x + 2 the second x term is -x, "
        "so 3x - x = 2x, not 4x.",
    ),
    "distributive": Concept(
        "a(b + c) = ab + ac: the number outside the parentheses multiplies every term inside.",
        (
            "Multiply the outside number by the first term inside.",
            "Multiply it by the second term inside, including that term's sign.",
            "Write the two products as one expression.",
        ),
        ("-3(x - 4)", "-3x - 3(-4)", "-3x + 12"),
        "Multiplying only the first term: -3(x - 4) is not -3x - 4. "
        "The -3 multiplies the -4 too, and (-3)(-4) = +12.",
    ),
    "one_step_add": Concept(
        "To undo adding or subtracting a number, do the opposite operation to both sides of the equation.",
        (
            "Find the number added to or subtracted from x.",
            "Do the opposite to both sides: subtract it if it was added, add it if it was subtracted.",
            "Simplify both sides so x is alone.",
        ),
        ("x - 7 = -13", "x - 7 + 7 = -13 + 7", "x = -6"),
        "Changing only one side. Whatever you do to one side you must do to the other, "
        "or the equation is no longer balanced.",
    ),
    "one_step_mul": Concept(
        "To undo multiplying or dividing x by a number, divide or multiply both sides by that number.",
        (
            "If x is multiplied by a number, divide both sides by that number.",
            "If x is divided by a number, multiply both sides by that number.",
            "Keep track of negative signs.",
        ),
        ("-7x = 42", "-7x / (-7) = 42 / (-7)", "x = -6"),
        "Dividing by the wrong sign: in -7x = 42 you divide by -7, not 7, so x = -6, not 6.",
    ),
    "two_step": Concept(
        "Undo the operations in reverse order: first move the constant term, "
        "then divide by the coefficient of x.",
        (
            "Add or subtract to move the constant term to the other side.",
            "Divide both sides by the coefficient of x.",
            "Check your answer by putting it back into the original equation.",
        ),
        ("3x + 5 = 17", "3x + 5 - 5 = 17 - 5", "3x = 12", "x = 4"),
        "Dividing only the x term: dividing 3x + 5 = 17 by 3 must divide every term. "
        "Moving the 5 first avoids the fractions.",
    ),
    "vars_both_sides": Concept(
        "When x is on both sides, move all x terms to one side and all numbers to the other, then solve.",
        (
            "Add or subtract an x term on both sides so x appears on only one side.",
            "Move the constant terms to the other side.",
            "Divide by the coefficient of x.",
        ),
        ("5x + 3 = 2x + 15", "5x - 2x + 3 = 2x - 2x + 15", "3x + 3 = 15", "3x = 12", "x = 4"),
        "Moving a term without doing it to both sides: subtract 2x from BOTH sides, "
        "so the left becomes 5x - 2x = 3x and the right loses its x term.",
    ),
    "parentheses": Concept(
        "Remove the parentheses first, by distributing (or by dividing both sides by the number outside), "
        "then solve the two-step equation that is left.",
        (
            "Distribute the number outside the parentheses to each term inside.",
            "Move the constant term to the other side.",
            "Divide by the coefficient of x, and check the answer in the original equation.",
        ),
        ("-4(x - 3) = 40", "-4x + 12 = 40", "-4x = 28", "x = -7"),
        "Distributing to only the first term: -4(x - 3) is -4x + 12, not -4x - 3.",
    ),
    "multi_step": Concept(
        "Put the earlier skills together: distribute, combine like terms on each side, "
        "collect the x terms on one side, then solve.",
        (
            "Distribute to remove the parentheses.",
            "Combine like terms on each side separately.",
            "Move the x terms to one side and the numbers to the other.",
            "Divide by the coefficient of x.",
        ),
        ("2(x + 3) + 4x = x + 21", "2x + 6 + 4x = x + 21", "6x + 6 = x + 21", "5x + 6 = 21", "5x = 15", "x = 3"),
        "Combining terms that are on opposite sides of the = sign. A term can only move across "
        "the = sign by doing the same operation to both sides.",
    ),
}

assert set(CONCEPTS) == set(SKILLS), "every skill needs a concept lesson"
assert sorted(s for c in COURSES.values() for s in c.skills) == sorted(SKILLS), "each skill in exactly one course"
