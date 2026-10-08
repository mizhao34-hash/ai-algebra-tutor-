"""Week 2: Deep Knowledge Tracing (Piech et al., 2015) with an LSTM.

At each step t the model reads (skill_t, correct_t) and outputs, for EVERY
skill, the probability the student answers it correctly next. The loss uses
only the output for the skill actually attempted at t+1.

Usage (from repo root):
    .venv/bin/python -m ml.train_dkt
"""

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from ml.evaluation import log_result, metrics, target_mask

DATA_DIR = Path("data/processed")
CKPT_DIR = Path("ml/checkpoints")

CONFIG = {
    "seed": 42,
    "hidden_size": 100,
    "embed_size": 100,
    "dropout": 0.2,
    "lr": 1e-3,
    "batch_size": 64,
    "max_len": 200,  # training windows; evaluation uses full sequences
    "max_epochs": 30,
    "patience": 3,  # early stopping on validation AUC
}


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class DKT(nn.Module):
    def __init__(self, num_skills: int, embed_size: int, hidden_size: int, dropout: float):
        super().__init__()
        self.num_skills = num_skills
        # Input token encodes both skill and correctness: id = skill + correct * K.
        # So there are 2K possible tokens (an embedding instead of a 2K one-hot).
        self.embed = nn.Embedding(2 * num_skills, embed_size)
        self.lstm = nn.LSTM(embed_size, hidden_size, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.out = nn.Linear(hidden_size, num_skills)

    def forward(self, tokens):
        h, _ = self.lstm(self.embed(tokens))
        # Logits for every skill at every step: (batch, seq_len, K).
        return self.out(self.dropout(h))


def student_sequences(df: pd.DataFrame):
    """List of (skills, corrects) arrays, one per student, in time order."""
    return [
        (g.skill_idx.to_numpy(), g.correct.to_numpy())
        for _, g in df.groupby("user_id", sort=False)
    ]


def make_windows(seqs, max_len: int):
    """Cut long training sequences into chunks of <= max_len so batches stay
    small. Chunks of length 1 have no next-step target and are dropped."""
    windows = []
    for skills, correct in seqs:
        for start in range(0, len(skills), max_len):
            s, c = skills[start : start + max_len], correct[start : start + max_len]
            if len(s) >= 2:
                windows.append((s, c))
    return windows


def to_batch(seqs, num_skills: int):
    """Pad a list of sequences into tensors.

    inputs[t]  = token for answer t            (t = 0..L-2)
    q_next[t]  = skill of answer t+1           (which output to read)
    y_next[t]  = correctness of answer t+1     (the label)
    mask[t]    = False on padding
    """
    L = max(len(s) for s, _ in seqs) - 1
    B = len(seqs)
    inputs = torch.zeros(B, L, dtype=torch.long)
    q_next = torch.zeros(B, L, dtype=torch.long)
    y_next = torch.zeros(B, L)
    mask = torch.zeros(B, L, dtype=torch.bool)
    for i, (s, c) in enumerate(seqs):
        n = len(s) - 1
        inputs[i, :n] = torch.from_numpy(s[:-1] + c[:-1] * num_skills)
        q_next[i, :n] = torch.from_numpy(s[1:])
        y_next[i, :n] = torch.from_numpy(c[1:]).float()
        mask[i, :n] = True
    return inputs, q_next, y_next, mask


def next_step_logits(model, inputs, q_next):
    # Pick, at each step, the logit of the skill the student attempts next.
    logits = model(inputs)
    return logits.gather(2, q_next.unsqueeze(-1)).squeeze(-1)


@torch.no_grad()
def predict(model, df: pd.DataFrame, batch_size: int = 64) -> np.ndarray:
    """P(correct) for every row of df except each student's first answer,
    in the same order as target_mask(df) selects rows. Runs on FULL sequences
    (no windowing), so every prediction sees the student's whole history."""
    model.eval()
    seqs = student_sequences(df)
    preds = []
    for i in range(0, len(seqs), batch_size):
        batch = seqs[i : i + batch_size]
        inputs, q_next, _, mask = to_batch(batch, model.num_skills)
        p = torch.sigmoid(next_step_logits(model, inputs, q_next))
        preds.append(p[mask].numpy())  # row-major: student by student, in time order
    return np.concatenate(preds)


def evaluate(model, df: pd.DataFrame) -> dict:
    y = df.correct.to_numpy()[target_mask(df)]
    return metrics(y, predict(model, df))


def main():
    cfg = CONFIG
    set_seed(cfg["seed"])
    train = pd.read_csv(DATA_DIR / "train.csv")
    val = pd.read_csv(DATA_DIR / "val.csv")
    test = pd.read_csv(DATA_DIR / "test.csv")
    num_skills = int(pd.read_csv(DATA_DIR / "skill_map.csv").skill_idx.max()) + 1

    windows = make_windows(student_sequences(train), cfg["max_len"])
    model = DKT(num_skills, cfg["embed_size"], cfg["hidden_size"], cfg["dropout"])
    opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"])
    loss_fn = nn.BCEWithLogitsLoss()

    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    best_auc, bad_epochs = 0.0, 0
    for epoch in range(1, cfg["max_epochs"] + 1):
        model.train()
        order = np.random.permutation(len(windows))
        total = 0.0
        for i in range(0, len(order), cfg["batch_size"]):
            batch = [windows[j] for j in order[i : i + cfg["batch_size"]]]
            inputs, q_next, y_next, mask = to_batch(batch, num_skills)
            logits = next_step_logits(model, inputs, q_next)
            loss = loss_fn(logits[mask], y_next[mask])
            opt.zero_grad()
            loss.backward()
            # LSTMs can have exploding gradients on long sequences.
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total += loss.item() * len(batch)

        val_m = evaluate(model, val)
        print(f"epoch {epoch:2d}  loss {total / len(windows):.4f}  val AUC {val_m['auc']:.4f}")
        if val_m["auc"] > best_auc:
            best_auc, bad_epochs = val_m["auc"], 0
            torch.save(model.state_dict(), CKPT_DIR / "dkt.pt")
        else:
            bad_epochs += 1
            if bad_epochs >= cfg["patience"]:
                print("early stopping")
                break

    # Reload the best epoch (by validation AUC) before reporting.
    model.load_state_dict(torch.load(CKPT_DIR / "dkt.pt", weights_only=True))
    with open(CKPT_DIR / "dkt_config.json", "w") as f:
        json.dump({**cfg, "num_skills": num_skills}, f, indent=2)

    notes = f"seed={cfg['seed']}, hidden={cfg['hidden_size']}, lr={cfg['lr']}"
    for split, df in [("val", val), ("test", test)]:
        m = evaluate(model, df)
        print(split, m)
        log_result("1: BKT vs DKT", "DKT (LSTM)", split, m, notes)


if __name__ == "__main__":
    main()
