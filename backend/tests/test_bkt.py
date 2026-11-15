from app.bkt import GUESS, SLIP, p_correct_next
from app.skills import MASTERY_THRESHOLD


def test_starts_low_and_stays_a_probability():
    assert p_correct_next([]) < 0.5
    for h in ([True] * 20, [False] * 20, [True, False] * 10):
        assert GUESS <= p_correct_next(h) <= 1 - SLIP


def test_right_answers_raise_and_wrong_answers_lower():
    assert p_correct_next([True]) > p_correct_next([])
    assert p_correct_next([True, True]) > p_correct_next([True])
    assert p_correct_next([True, False]) < p_correct_next([True])


def test_two_right_in_a_row_reach_mastery_but_one_does_not():
    assert p_correct_next([True]) < MASTERY_THRESHOLD <= p_correct_next([True, True])
