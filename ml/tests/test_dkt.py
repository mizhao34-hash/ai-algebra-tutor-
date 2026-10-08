import numpy as np
import pandas as pd
import torch

from ml.evaluation import target_mask
from ml.train_dkt import DKT, predict, to_batch


def test_to_batch_shifts_inputs_and_targets():
    # Student A: skill 0 right, skill 1 wrong, skill 0 right. Student B: shorter.
    seqs = [(np.array([0, 1, 0]), np.array([1, 0, 1])), (np.array([1, 1]), np.array([0, 1]))]
    inputs, q_next, y_next, mask = to_batch(seqs, num_skills=2)
    # token = skill + correct * K, for answers 0..L-2
    assert inputs.tolist() == [[2, 1], [1, 0]]
    # target = skill and correctness of the NEXT answer
    assert q_next.tolist() == [[1, 0], [1, 0]]
    assert y_next.tolist() == [[0.0, 1.0], [1.0, 0.0]]
    assert mask.tolist() == [[True, True], [True, False]]  # B is padded


def test_predict_lines_up_with_target_mask():
    df = pd.DataFrame({
        "user_id": [1, 1, 1, 2, 2],
        "order_id": [1, 2, 3, 4, 5],
        "skill_idx": [0, 1, 0, 1, 1],
        "correct": [1, 0, 1, 0, 1],
    })
    torch.manual_seed(0)
    model = DKT(num_skills=2, embed_size=4, hidden_size=4, dropout=0.0)
    assert len(predict(model, df)) == target_mask(df).sum() == 3
