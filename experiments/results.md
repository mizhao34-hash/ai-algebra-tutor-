# Experiment results

| date | experiment | model | split | AUC | ACC | n | notes |
|---|---|---|---|---|---|---|---|
| 2026-10-08 | 1: BKT vs DKT | DKT (LSTM) | val | 0.7554 | 0.7388 | 44174 | seed=42, hidden=100, lr=0.001 |
| 2026-10-08 | 1: BKT vs DKT | DKT (LSTM) | test | 0.7514 | 0.7306 | 35789 | seed=42, hidden=100, lr=0.001 |
| 2026-10-08 | 1: BKT vs DKT | BKT (pyBKT) | val | 0.7156 | 0.7212 | 44174 | seed=42, num_fits=5 |
| 2026-10-08 | 1: BKT vs DKT | BKT (pyBKT) | test | 0.7077 | 0.7076 | 35789 | seed=42, num_fits=5 |
