// Typed client for the FastAPI backend (backend/app/main.py).
// The types mirror the JSON the backend returns; keep them in sync.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Problem = {
  id: string; // "skill:seed"; the server regenerates the problem from it to grade
  skill: string;
  skill_name: string;
  kind: "evaluate" | "simplify" | "solve";
  prompt: string;
  expression: string;
  // No answer field: the backend never sends it.
};

export type SkillMastery = {
  id: string;
  name: string;
  prerequisites: string[];
  mastery: number; // DKT's P(correct next time), 0..1
  mastered: boolean;
  unlocked: boolean;
  attempts: number; // problems attempted (first graded attempts)
  correct: number; // of those, correct on the first try
};

export type MasteryReport = {
  user_id: string;
  threshold: number;
  recommended: string;
  skills: SkillMastery[]; // in prerequisite (topological) order
};

export type GradeStatus = "correct" | "not_simplified" | "incorrect" | "invalid";

export type AttemptResult = {
  status: GradeStatus;
  correct: boolean;
  message: string;
  counts_for_mastery: boolean;
  mastery: MasteryReport;
};

export type Hint = {
  hint: string;
  next_step: string; // "" when writing the step would reveal the answer
  verified: boolean; // passed the SymPy check
  source: "llm" | "fallback";
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(API_URL + path, {
      ...init,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    throw new Error(`Can't reach the tutor server at ${API_URL}. Is the backend running?`);
  }
  if (!res.ok) {
    // FastAPI errors look like {"detail": "..."}; show that text when present.
    const text = await res.text();
    let detail = text;
    try {
      detail = JSON.parse(text).detail ?? text;
    } catch {
      /* not JSON */
    }
    throw new Error(res.status === 503 ? `Hints are unavailable: ${detail}` : `Server error ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

const user = (id: string) => `/users/${encodeURIComponent(id)}`;

export const api = {
  mastery: (userId: string) => request<MasteryReport>(`${user(userId)}/mastery`),

  // Without `skill`, the backend picks the recommended skill.
  nextProblem: (userId: string, skill?: string) =>
    request<Problem>(`${user(userId)}/next${skill ? `?skill=${encodeURIComponent(skill)}` : ""}`),

  submit: (userId: string, problemId: string, answer: string) =>
    request<AttemptResult>(`${user(userId)}/attempts`, {
      method: "POST",
      body: JSON.stringify({ problem_id: problemId, answer }),
    }),

  // `current` = the step the student is on (defaults to the problem itself).
  hint: (userId: string, problemId: string, current?: string) =>
    request<Hint>(`${user(userId)}/hints`, {
      method: "POST",
      body: JSON.stringify({ problem_id: problemId, current: current ?? null }),
    }),
};
