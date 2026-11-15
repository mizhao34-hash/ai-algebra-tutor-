from app.recommend import is_unlocked, recommend
from app.skills import SKILLS

# These tests are about the original 9-skill linear-equation graph.
NINE = ["integer_ops", "combine_like_terms", "distributive", "one_step_add", "one_step_mul",
        "two_step", "vars_both_sides", "parentheses", "multi_step"]


def mastery(**overrides):
    m = {s: 0.0 for s in SKILLS}
    m.update(overrides)
    return m


def test_new_student_starts_at_root():
    assert recommend(mastery()) == "integer_ops"


def test_locked_skill_is_skipped_even_if_lowest():
    # two_step has the lowest mastery, but one_step_mul isn't mastered yet.
    m = mastery(integer_ops=0.9, combine_like_terms=0.8, distributive=0.8,
                one_step_add=0.9, one_step_mul=0.5, two_step=0.1)
    assert not is_unlocked("two_step", m)
    assert recommend(m, NINE) == "one_step_mul"


def test_picks_lowest_among_unlocked():
    m = mastery(integer_ops=0.9, combine_like_terms=0.6, distributive=0.4,
                one_step_add=0.5, one_step_mul=0.65)
    assert recommend(m, NINE) == "distributive"


def test_ties_go_to_the_more_basic_skill():
    m = mastery(integer_ops=0.9)  # four unlocked skills, all at 0.0
    assert recommend(m, NINE) == "combine_like_terms"  # first in topological order


def test_threshold_is_inclusive():
    m = mastery(integer_ops=0.7, one_step_add=0.7, one_step_mul=0.7,
                combine_like_terms=0.9, distributive=0.9)
    assert is_unlocked("two_step", m)
    assert recommend(m, NINE) == "two_step"
