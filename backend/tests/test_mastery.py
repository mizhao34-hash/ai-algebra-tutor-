"""Tests against the real trained DKT checkpoint (skipped if it isn't present,
e.g. on a fresh clone, since ml/checkpoints/ is gitignored)."""

import pytest

from app.mastery import DEFAULT_CKPT_DIR, DEFAULT_SKILL_MAP
from app.skills import SKILLS

if not (DEFAULT_CKPT_DIR / "dkt.pt").exists() or not DEFAULT_SKILL_MAP.exists():
    pytest.skip("DKT checkpoint not found; run `python -m ml.train_dkt` first", allow_module_level=True)

from app.mastery import DKT_SKILLS, CombinedMastery, DKTMastery  # noqa: E402


@pytest.fixture(scope="module")
def model():
    return DKTMastery()


def test_no_history_means_no_mastery(model):
    assert model.mastery([]) == {s: 0.0 for s in DKT_SKILLS}
    assert CombinedMastery(model).mastery([]) == {s: 0.0 for s in SKILLS}


def test_returns_probability_for_every_skill(model):
    m = CombinedMastery(model).mastery([("two_step", True), ("integer_ops", False), ("quad_factored", True)])
    assert set(m) == set(SKILLS)
    assert all(0.0 <= v <= 1.0 for v in m.values())


def test_combined_routes_each_skill_to_its_model(model):
    from app import bkt

    combined = CombinedMastery(model)
    h = [("two_step", True), ("quad_factored", True), ("quad_factored", True)]
    m = combined.mastery(h)
    # Algebra 2 skills: BKT on that skill's own answers; untried ones stay at 0.
    assert m["quad_factored"] == bkt.p_correct_next([True, True])
    assert m["quad_square_root"] == 0.0
    # DKT skills: identical to running DKT without the Algebra 2 answers.
    dkt_only = model.mastery([("two_step", True)])
    assert all(m[s] == dkt_only[s] for s in DKT_SKILLS)


def test_right_answers_beat_wrong_answers(model):
    right = model.mastery([("integer_ops", True)] * 5)
    wrong = model.mastery([("integer_ops", False)] * 5)
    assert right["integer_ops"] > wrong["integer_ops"]
    assert right["two_step"] > wrong["two_step"]  # DKT generalizes across skills


def test_deterministic(model):
    h = [("one_step_add", True), ("one_step_mul", False), ("two_step", True)]
    assert model.mastery(h) == model.mastery(h)
