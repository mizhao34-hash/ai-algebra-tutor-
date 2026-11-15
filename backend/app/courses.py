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
            "Work with negative numbers, exponents and roots, and simplify algebraic expressions.",
            (
                Unit("integers", "Integers", ("integer_ops",)),
                Unit("exponents_roots", "Exponents and square roots", ("exponents", "square_roots")),
                Unit("expressions", "Algebraic expressions", ("combine_like_terms", "distributive")),
            ),
        ),
        Course(
            "algebra_1",
            "Algebra 1",
            "Grades 8–9",
            "Solve linear equations and inequalities, from one step to many.",
            (
                Unit("one_step", "One-step equations", ("one_step_add", "one_step_mul")),
                Unit("multi_step_eq", "Multi-step equations",
                     ("two_step", "vars_both_sides", "parentheses", "multi_step")),
                Unit("inequalities", "Linear inequalities", ("one_step_ineq", "two_step_ineq")),
            ),
        ),
        Course(
            "algebra_2",
            "Algebra 2",
            "Grades 10–11",
            "Multiply polynomials, then solve quadratic equations, which usually have two solutions.",
            (
                Unit("polynomials", "Polynomials", ("multiply_binomials", "square_binomial")),
                Unit("quadratics", "Quadratic equations", ("quad_square_root", "quad_factored", "quad_factor_solve")),
            ),
        ),
    ]
}


# Unit ids are unique across courses, so /next?unit=... is unambiguous.
UNITS: dict[str, tuple[str, Unit]] = {u.id: (c.id, u) for c in COURSES.values() for u in c.units}
assert len(UNITS) == sum(len(c.units) for c in COURSES.values()), "duplicate unit id"


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
    "exponents": Concept(
        "An exponent says how many times to multiply a number by itself: 3^4 = 3 × 3 × 3 × 3. "
        "Exponents come before multiplication, division, addition and subtraction.",
        (
            "Work out each power first: multiply the base by itself as many times as the exponent says.",
            "A negative base in parentheses is part of the power: (-3)^2 = (-3)(-3) = 9.",
            "Without parentheses the minus sign comes after the power: -3^2 = -(3 × 3) = -9.",
            "Then add or subtract the results.",
        ),
        ("-3^2 + 6", "-9 + 6", "-3"),
        "Treating -3^2 like (-3)^2. Only the 3 is squared, so -3^2 = -9; (-3)^2 = 9.",
    ),
    "square_roots": Concept(
        "The square root of a number is the value that, multiplied by itself, gives that number: "
        "√49 = 7 because 7 × 7 = 49.",
        (
            "Find each square root by asking which number times itself gives the number under the root.",
            "A number in front of the root multiplies it: 3√25 = 3 × 5.",
            "Then add, subtract or multiply the results as usual.",
        ),
        ("sqrt(49) + sqrt(16)", "7 + 4", "11"),
        "Adding under the root: √49 + √16 is 7 + 4 = 11, not √65.",
    ),
    "one_step_ineq": Concept(
        "Solve an inequality like an equation, with one extra rule: multiplying or dividing both sides "
        "by a negative number flips the inequality sign.",
        (
            "Undo the operation on x by doing the opposite to both sides.",
            "If you multiply or divide by a negative number, flip the sign (< becomes >, <= becomes >=).",
            "Write the answer with x alone, like x > 3.",
        ),
        ("-3x < 12", "-3x / (-3) > 12 / (-3)", "x > -4"),
        "Forgetting to flip the sign: -3x < 12 gives x > -4, not x < -4. Check with x = 0: -3(0) < 12 is true, "
        "and 0 > -4.",
    ),
    "two_step_ineq": Concept(
        "Undo the constant term first, then divide by the coefficient of x, flipping the sign if it is negative.",
        (
            "Add or subtract to move the constant term to the other side.",
            "Divide both sides by the coefficient of x.",
            "If that coefficient is negative, flip the inequality sign.",
        ),
        ("-2x + 3 <= 7", "-2x <= 4", "x >= -2"),
        "Flipping the sign when you add or subtract. Only multiplying or dividing by a negative flips it.",
    ),
    "multiply_binomials": Concept(
        "To multiply (x + a)(x + b), multiply every term of the first by every term of the second "
        "(First, Outer, Inner, Last), then combine like terms.",
        (
            "Multiply the first terms: x · x = x^2.",
            "Multiply the outer and inner terms: x · b and a · x.",
            "Multiply the last terms: a · b.",
            "Combine the two x terms.",
        ),
        ("(x + 2)(x + 3)", "x^2 + 3x + 2x + 6", "x^2 + 5x + 6"),
        "Multiplying only the first and last terms: (x + 2)(x + 3) is not x^2 + 6. "
        "The middle terms 3x + 2x are needed.",
    ),
    "square_binomial": Concept(
        "(x + a)^2 means (x + a)(x + a). Multiply it out: (x + a)^2 = x^2 + 2ax + a^2.",
        (
            "Write the square as a product: (x + a)(x + a).",
            "Multiply every term by every term.",
            "Combine the two middle terms, which are equal: ax + ax = 2ax.",
        ),
        ("(x - 3)^2", "(x - 3)(x - 3)", "x^2 - 3x - 3x + 9", "x^2 - 6x + 9"),
        "Squaring each term separately: (x - 3)^2 is not x^2 + 9. The middle term -6x is missing, "
        "and the last term is (-3)^2 = +9.",
    ),
    "quad_square_root": Concept(
        "When the equation is just x² equal to a number, take the square root of both sides. "
        "Remember there are two solutions: a positive one and a negative one.",
        (
            "Get x² by itself on one side (move constants, divide by the coefficient).",
            "Take the square root of both sides.",
            "Write both solutions: x = √k and x = -√k.",
        ),
        ("x^2 - 49 = 0", "x^2 = 49", "x = 7 or x = -7"),
        "Giving only the positive solution. (-7)² = 49 too, so x = -7 is also a solution.",
    ),
    "quad_factored": Concept(
        "Zero-product property: if two factors multiply to 0, at least one of them must be 0. "
        "So set each factor equal to 0 and solve each one.",
        (
            "Check that one side is a product of factors and the other side is 0.",
            "Set each factor equal to 0.",
            "Solve each small equation; each gives one solution.",
        ),
        ("(x - 2)(x + 3) = 0", "x - 2 = 0 or x + 3 = 0", "x = 2 or x = -3"),
        "Getting the signs backwards: (x + 3) = 0 gives x = -3, not x = 3.",
    ),
    "quad_factor_solve": Concept(
        "To solve x² + bx + c = 0, factor it as (x + m)(x + n) where m × n = c and m + n = b, "
        "then use the zero-product property.",
        (
            "Make sure one side is 0.",
            "Find two numbers that multiply to c and add to b.",
            "Write the factored form (x + m)(x + n) = 0.",
            "Set each factor to 0 and solve.",
        ),
        ("x^2 + x - 6 = 0", "(x + 3)(x - 2) = 0", "x + 3 = 0 or x - 2 = 0", "x = -3 or x = 2"),
        "Choosing numbers that multiply to c but don't add to b: for x² + x - 6, 6 and -1 multiply "
        "to -6 but add to 5, not 1. Use 3 and -2.",
    ),
}

assert set(CONCEPTS) == set(SKILLS), "every skill needs a concept lesson"
assert sorted(s for c in COURSES.values() for s in c.skills) == sorted(SKILLS), "each skill in exactly one course"
