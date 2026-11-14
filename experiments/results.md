# Experiment results

| date | experiment | model | split | AUC | ACC | n | notes |
|---|---|---|---|---|---|---|---|
| 2026-10-08 | 1: BKT vs DKT | DKT (LSTM) | val | 0.7554 | 0.7388 | 44174 | seed=42, hidden=100, lr=0.001 |
| 2026-10-08 | 1: BKT vs DKT | DKT (LSTM) | test | 0.7514 | 0.7306 | 35789 | seed=42, hidden=100, lr=0.001 |
| 2026-10-08 | 1: BKT vs DKT | BKT (pyBKT) | val | 0.7156 | 0.7212 | 44174 | seed=42, num_fits=5 |
| 2026-10-08 | 1: BKT vs DKT | BKT (pyBKT) | test | 0.7077 | 0.7076 | 35789 | seed=42, num_fits=5 |

## Experiment 2: hint verification

| date | model | condition | n | math error % | leak % (checker) | leak % (broad) | fallback % | LLM calls/hint | s/hint | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-14 | claude-opus-5-5 | ~~without check~~ INVALID | 150 | 8.0 | 1.3 | 11.3 | n/a | 1 | n/a | seed=42, per_skill=10, paired, raw: experiments/results/hints-claude-opus-5-5-2026-11-14-INVALID-run1.jsonl, cost $0.88; INVALID: checker flagged correct distribution steps as no_progress, and synthetic last steps weren't reachable from the problem. Superseded by the next run. |
| 2026-11-14 | claude-opus-5-5 | ~~with check~~ INVALID | 150 | 0.0 | 0.0 | 12.0 | 0.7 | 1.17 | 3.3 | seed=42, per_skill=10, paired, raw: experiments/results/hints-claude-opus-5-5-2026-11-14-INVALID-run1.jsonl, cost $0.88; INVALID: checker flagged correct distribution steps as no_progress, and synthetic last steps weren't reachable from the problem. Superseded by the next run. |
| 2026-11-14 | claude-opus-5-5 | without check | 127 | 0.0 | 0.0 | 8.7 | n/a | 1 | n/a | seed=42, per_skill=10, paired, raw: experiments/results/hints-claude-opus-5-5-2026-11-14.jsonl, cost $0.48 |
| 2026-11-14 | claude-opus-5-5 | with check | 127 | 0.0 | 0.0 | 8.7 | 0.0 | 1.0 | 2.3 | seed=42, per_skill=10, paired, raw: experiments/results/hints-claude-opus-5-5-2026-11-14.jsonl, cost $0.48 |
| 2026-11-14 | claude-haiku-5-5 | without check | 127 | 0.0 | 10.2 | 18.9 | n/a | 1 | n/a | seed=42, per_skill=10, paired, raw: experiments/results/hints-claude-haiku-5-5-2026-11-14.jsonl, cost $0.02 |
| 2026-11-14 | claude-haiku-5-5 | with check | 127 | 0.0 | 0.0 | 9.4 | 0.8 | 1.11 | 2.0 | seed=42, per_skill=10, paired, raw: experiments/results/hints-claude-haiku-5-5-2026-11-14.jsonl, cost $0.02 |
| 2026-11-14 | claude-opus-5-5 | without check | 127 | 0.0 | 0.0 | 8.7 | (see run) | (see run) | (see run) | RESCORED hints-claude-opus-5-5-2026-11-14.jsonl with fixed leak checker (no new API calls) -> experiments/results/hints-claude-opus-5-5-2026-11-14-rescored.jsonl |
| 2026-11-14 | claude-opus-5-5 | with check | 127 | 0.0 | 0.0 | 8.7 | (see run) | (see run) | (see run) | RESCORED hints-claude-opus-5-5-2026-11-14.jsonl with fixed leak checker (no new API calls) -> experiments/results/hints-claude-opus-5-5-2026-11-14-rescored.jsonl |
| 2026-11-14 | claude-haiku-5-5 | without check | 127 | 0.0 | 8.7 | 18.9 | (see run) | (see run) | (see run) | RESCORED hints-claude-haiku-5-5-2026-11-14.jsonl with fixed leak checker (no new API calls) -> experiments/results/hints-claude-haiku-5-5-2026-11-14-rescored.jsonl |
| 2026-11-14 | claude-haiku-5-5 | with check | 127 | 0.0 | 0.0 | 9.4 | (see run) | (see run) | (see run) | RESCORED hints-claude-haiku-5-5-2026-11-14.jsonl with fixed leak checker (no new API calls) -> experiments/results/hints-claude-haiku-5-5-2026-11-14-rescored.jsonl |
