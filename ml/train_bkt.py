"""Week 2: BKT baseline with pyBKT (one HMM per skill, standard 4 parameters:
prior, learn, guess, slip; no forgetting).

Usage (from repo root):
    .venv/bin/python ml/train_bkt.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from pyBKT.models import Model

from ml.evaluation import log_result, metrics, target_mask

DATA_DIR = Path("data/processed")
CKPT_DIR = Path("ml/checkpoints")
SEED = 42


def to_pybkt(df: pd.DataFrame) -> pd.DataFrame:
    # pyBKT looks for a column literally named "skill_name" and fits one model
    # per distinct value; we use our contiguous skill index as that name.
    out = df[["user_id", "order_id", "correct"]].copy()
    out["skill_name"] = df.skill_idx.astype(str)
    return out


def predict(model: Model, df: pd.DataFrame) -> pd.Series:
    """P(correct) for every row. pyBKT may reorder rows, so we join back on
    order_id. Each prediction uses only the student's EARLIER answers on the
    same skill (BKT's forward pass), so there is no peeking at the label."""
    pred = model.predict(data=to_pybkt(df))
    return df.order_id.map(pred.set_index("order_id").correct_predictions)


def main():
    train = pd.read_csv(DATA_DIR / "train.csv")
    # parallel=False: pyBKT's multiprocessing pool is far slower than serial
    # fitting on macOS (process start-up dominates for small per-skill fits).
    model = Model(seed=SEED, num_fits=5, parallel=False)
    model.fit(data=to_pybkt(train))

    # pyBKT 1.4.1 silently "fit" on zero sequences and returned prior=NaN;
    # fail loudly if anything like that happens again.
    for skill, params in model.coef_.items():
        assert not np.isnan(params["prior"]), f"skill {skill}: prior is NaN"

    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    model.save(str(CKPT_DIR / "bkt.pkl"))

    for split in ["val", "test"]:
        df = pd.read_csv(DATA_DIR / f"{split}.csv")
        # A skill never seen in training has no fitted parameters.
        unseen = ~df.skill_idx.astype(str).isin(model.coef_.keys())
        if unseen.any():
            print(f"{split}: dropping {unseen.sum()} rows with skills unseen in train")
        df = df[~unseen].reset_index(drop=True)

        p = predict(model, df)
        mask = target_mask(df)
        m = metrics(df.correct[mask], p[mask])
        print(split, m)
        log_result("1: BKT vs DKT", "BKT (pyBKT)", split, m, f"seed={SEED}, num_fits=5")


if __name__ == "__main__":
    main()
