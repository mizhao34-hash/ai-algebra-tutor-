"""Week 1: clean the ASSISTments 2009 skill-builder data and split it by student.

Usage (from repo root):
    .venv/bin/python ml/preprocess.py

Outputs in data/processed/:
    train.csv, val.csv, test.csv  one row per student answer, in time order
    skill_map.csv                 dataset skill_id -> contiguous skill_idx (0..K-1)
    stats.json                    row/student counts after each cleaning step
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW_PATH = Path("data/raw/skill_builder_data.csv")
OUT_DIR = Path("data/processed")
SEED = 42
SPLIT = (0.70, 0.15, 0.15)  # train / val / test, fractions of STUDENTS
MIN_INTERACTIONS = 2  # a sequence needs >= 2 answers to predict anything

# Only the columns the models need; keeps memory low and the output readable.
COLUMNS = ["order_id", "user_id", "problem_id", "skill_id", "skill_name", "correct"]


def load_raw(path: Path) -> pd.DataFrame:
    # The file has non-UTF-8 characters in skill names, so read it as latin-1.
    return pd.read_csv(path, encoding="latin-1", usecols=COLUMNS, low_memory=False)


def clean(df: pd.DataFrame, stats: dict) -> pd.DataFrame:
    stats["raw_rows"] = len(df)
    stats["raw_students"] = int(df.user_id.nunique())

    # 1. Rows with no skill tag can't be assigned to any knowledge component.
    df = df[df.skill_id.notna()].copy()
    df["skill_id"] = df.skill_id.astype(int)
    stats["after_drop_null_skill"] = len(df)

    # 2. One answer = one order_id. The raw file repeats a row once per skill
    #    when a problem has several skills (plus some exact repeats). Keeping
    #    the copies would let the model "see" the answer it is about to predict
    #    (the next row is the same answer), inflating AUC. We keep the first
    #    listed skill so each answer appears exactly once.
    df = df.drop_duplicates(subset="order_id", keep="first")
    stats["after_dedup_order_id"] = len(df)

    # 3. order_id increases with time, but the file is not sorted by it within
    #    each student. Sequence models need answers in chronological order.
    df = df.sort_values(["user_id", "order_id"], kind="stable")

    # 4. Students with a single answer give no (history -> next answer) pair.
    counts = df.groupby("user_id").order_id.transform("size")
    df = df[counts >= MIN_INTERACTIONS]
    stats["after_min_interactions"] = len(df)
    stats["students"] = int(df.user_id.nunique())

    # 5. Re-index skills to 0..K-1 so they can be used directly as embedding /
    #    one-hot indices in DKT.
    skill_ids = np.sort(df.skill_id.unique())
    skill_to_idx = {s: i for i, s in enumerate(skill_ids)}
    df["skill_idx"] = df.skill_id.map(skill_to_idx)
    stats["num_skills"] = len(skill_ids)

    return df.reset_index(drop=True)


def split_by_student(df: pd.DataFrame, stats: dict):
    """Assign whole students to train/val/test so no student's history leaks
    across splits (a row-level split would let the model memorise a student)."""
    rng = np.random.default_rng(SEED)
    students = df.user_id.unique()
    rng.shuffle(students)

    n = len(students)
    n_train = int(SPLIT[0] * n)
    n_val = int(SPLIT[1] * n)
    groups = {
        "train": students[:n_train],
        "val": students[n_train : n_train + n_val],
        "test": students[n_train + n_val :],
    }

    splits = {}
    for name, ids in groups.items():
        part = df[df.user_id.isin(set(ids))]
        splits[name] = part
        stats[f"{name}_students"] = len(ids)
        stats[f"{name}_rows"] = len(part)
    return splits


def main():
    stats = {"seed": SEED}
    df = clean(load_raw(RAW_PATH), stats)
    splits = split_by_student(df, stats)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_cols = ["user_id", "order_id", "problem_id", "skill_id", "skill_idx", "correct"]
    for name, part in splits.items():
        part[out_cols].to_csv(OUT_DIR / f"{name}.csv", index=False)

    skill_map = (
        df[["skill_idx", "skill_id", "skill_name"]]
        .drop_duplicates("skill_idx")
        .sort_values("skill_idx")
    )
    skill_map.to_csv(OUT_DIR / "skill_map.csv", index=False)

    with open(OUT_DIR / "stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
