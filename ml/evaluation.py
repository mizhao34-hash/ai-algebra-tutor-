"""Shared evaluation + logging so BKT and DKT are scored identically."""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score

RESULTS_PATH = Path("experiments/results.md")


def target_mask(df: pd.DataFrame) -> np.ndarray:
    """True for every answer except each student's first one.

    DKT predicts answer t from answers 0..t-1, so it has no prediction for a
    student's first answer. We drop those rows for BOTH models so the AUCs are
    computed on exactly the same set of answers. Assumes df is sorted by
    (user_id, order_id), as preprocess.py writes it.
    """
    return (df.user_id.values == np.roll(df.user_id.values, 1)) & (np.arange(len(df)) > 0)


def metrics(y_true, y_prob) -> dict:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    return {
        "auc": roc_auc_score(y_true, y_prob),
        "acc": accuracy_score(y_true, y_prob >= 0.5),
        "n": len(y_true),
    }


def log_result(experiment: str, model: str, split: str, m: dict, notes: str = ""):
    """Append one row to experiments/results.md (creates the table if needed)."""
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not RESULTS_PATH.exists():
        RESULTS_PATH.write_text(
            "# Experiment results\n\n"
            "| date | experiment | model | split | AUC | ACC | n | notes |\n"
            "|---|---|---|---|---|---|---|---|\n"
        )
    with open(RESULTS_PATH, "a") as f:
        f.write(
            f"| {date.today()} | {experiment} | {model} | {split} | "
            f"{m['auc']:.4f} | {m['acc']:.4f} | {m['n']} | {notes} |\n"
        )
