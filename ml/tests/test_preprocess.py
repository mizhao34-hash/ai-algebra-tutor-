import pandas as pd

from ml.preprocess import clean, split_by_student


def make_raw():
    # Student 1: answers out of order, one multi-skill answer (order 3 twice).
    # Student 2: one row with no skill. Student 3: a single answer (dropped).
    rows = [
        (2, 1, 10, 5.0, "a", 1),
        (1, 1, 11, 5.0, "a", 0),
        (3, 1, 12, 5.0, "a", 1),
        (3, 1, 12, 7.0, "b", 1),
        (4, 2, 10, 5.0, "a", 1),
        (5, 2, 13, None, None, 0),
        (6, 2, 14, 7.0, "b", 0),
        (7, 3, 10, 5.0, "a", 1),
    ]
    cols = ["order_id", "user_id", "problem_id", "skill_id", "skill_name", "correct"]
    return pd.DataFrame(rows, columns=cols)


def test_clean_dedups_sorts_and_filters():
    df = clean(make_raw(), {})
    assert df.order_id.is_unique
    assert set(df.user_id) == {1, 2}  # student 3 had only one answer
    assert df.skill_id.notna().all()
    for _, g in df.groupby("user_id"):
        assert g.order_id.is_monotonic_increasing
    assert sorted(df.skill_idx.unique()) == [0, 1]


def test_split_has_no_student_overlap():
    raw = pd.concat(
        [make_raw().assign(user_id=lambda d: d.user_id + 10 * k,
                           order_id=lambda d: d.order_id + 100 * k)
         for k in range(20)]
    )
    splits = split_by_student(clean(raw, {}), {})
    users = {name: set(part.user_id) for name, part in splits.items()}
    assert not users["train"] & users["val"]
    assert not users["train"] & users["test"]
    assert not users["val"] & users["test"]
