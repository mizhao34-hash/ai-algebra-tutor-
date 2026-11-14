"""DKT network definition, kept separate from training code.

The backend imports only this file (plus torch) to load the trained weights,
so it doesn't need pandas, scikit-learn or the training data.
"""

import torch.nn as nn


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
