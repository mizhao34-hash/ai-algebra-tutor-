"""Bayesian Knowledge Tracing for skills DKT has no training data for (Algebra 2).

BKT models each skill separately as a hidden "learned / not learned" state:
  prior  P(L0)  chance the student already knows the skill
  learn  P(T)   chance of learning it after each practice opportunity
  guess  P(G)   chance of answering right without knowing it
  slip   P(S)   chance of answering wrong despite knowing it
After each answer we update P(learned) with Bayes' rule, then apply learning.
Mastery is reported as P(correct on the next try), the same quantity DKT
predicts, so the 0.7 threshold means the same thing for both.

These parameters are hand-set, not fitted: ASSISTments has (almost) no data
for these skills, which is exactly why we can't use DKT here. Values are in
the usual range from the BKT literature; with them, two correct first
attempts in a row reach mastery (see tests/test_bkt.py).
"""

PRIOR, LEARN, GUESS, SLIP = 0.1, 0.1, 0.25, 0.1


def p_correct_next(results: list[bool]) -> float:
    """results: correctness of the student's first attempts on ONE skill, in order."""
    p_learned = PRIOR
    for correct in results:
        # Bayes: how likely is "learned", given what we just saw?
        if correct:
            p_learned = p_learned * (1 - SLIP) / (p_learned * (1 - SLIP) + (1 - p_learned) * GUESS)
        else:
            p_learned = p_learned * SLIP / (p_learned * SLIP + (1 - p_learned) * (1 - GUESS))
        # The practice opportunity itself may teach the skill.
        p_learned = p_learned + (1 - p_learned) * LEARN
    return p_learned * (1 - SLIP) + (1 - p_learned) * GUESS
