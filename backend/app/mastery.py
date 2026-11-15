"""Per-skill mastery from the trained DKT model.

DKT was trained on ASSISTments skills, not on our 9 tutor skills, so we
translate in both directions using Skill.assistments_skill_ids:
  - input:  a tutor-skill attempt is fed to the LSTM as its FIRST mapped
            ASSISTments skill (token = skill_idx + correct * K, as in training).
  - output: mastery of a tutor skill = mean predicted P(correct) over all of
            its mapped ASSISTments skills.
"Mastery" here means DKT's probability that the student answers that skill
correctly on the next try, which is what DKT is trained to predict.

Skills without any ASSISTments mapping (Algebra 2) are invisible to DKT; the
CombinedMastery below gives those a BKT estimate instead (see bkt.py).
"""

import csv
import json
from pathlib import Path

import torch

from ml.dkt_model import DKT

from . import bkt
from .skills import SKILLS

# Skills DKT can track (they map to ASSISTments skills it was trained on).
DKT_SKILLS = [sid for sid, s in SKILLS.items() if s.assistments_skill_ids]

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CKPT_DIR = REPO_ROOT / "ml" / "checkpoints"
DEFAULT_SKILL_MAP = REPO_ROOT / "data" / "processed" / "skill_map.csv"


class DKTMastery:
    def __init__(self, ckpt_dir: Path = DEFAULT_CKPT_DIR, skill_map_path: Path = DEFAULT_SKILL_MAP):
        cfg = json.loads((Path(ckpt_dir) / "dkt_config.json").read_text())
        self.num_skills = cfg["num_skills"]
        self.model = DKT(self.num_skills, cfg["embed_size"], cfg["hidden_size"], cfg["dropout"])
        self.model.load_state_dict(torch.load(Path(ckpt_dir) / "dkt.pt", weights_only=True))
        self.model.eval()  # turns dropout off

        # skill_map.csv: ASSISTments skill_id -> skill_idx (the model's 0..K-1 index).
        with open(skill_map_path) as f:
            id_to_idx = {int(row["skill_id"]): int(row["skill_idx"]) for row in csv.DictReader(f)}
        self.indices = {sid: [id_to_idx[a] for a in SKILLS[sid].assistments_skill_ids] for sid in DKT_SKILLS}

    @torch.no_grad()
    def mastery(self, history: list[tuple[str, bool]]) -> dict[str, float]:
        """history: (tutor_skill, correct) pairs in time order, DKT skills only.
        Returns mastery for the DKT skills."""
        if not history:
            # DKT only predicts after seeing at least one answer. With no
            # evidence we report 0, so only skills without prerequisites unlock.
            return {sid: 0.0 for sid in DKT_SKILLS}
        tokens = [self.indices[skill][0] + int(correct) * self.num_skills for skill, correct in history]
        logits = self.model(torch.tensor([tokens]))[0, -1]  # prediction after the LAST answer
        probs = torch.sigmoid(logits)
        return {sid: float(probs[idx].mean()) for sid, idx in self.indices.items()}


class CombinedMastery:
    """DKT for skills it was trained on, BKT for the rest (Algebra 2).

    Each model only sees answers on its own skills: DKT has no input token for
    an Algebra 2 skill, and BKT tracks every skill separately anyway.
    """

    def __init__(self, dkt: DKTMastery | None = None):
        self.dkt = dkt or DKTMastery()

    def mastery(self, history: list[tuple[str, bool]]) -> dict[str, float]:
        out = self.dkt.mastery([(s, ok) for s, ok in history if s in self.dkt.indices])
        for sid in SKILLS:
            if sid not in out:
                results = [ok for s, ok in history if s == sid]
                # No answers on this skill yet: no evidence, so 0 (BKT doesn't transfer between skills).
                out[sid] = bkt.p_correct_next(results) if results else 0.0
        return out
