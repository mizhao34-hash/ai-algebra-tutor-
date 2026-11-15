// Typed client for the FastAPI backend (backend/app/main.py).
// The types mirror the JSON the backend returns; keep them in sync.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Problem = {
  id: string; // "skill:seed"; the server regenerates the problem from it to grade
  skill: string;
  skill_name: string;
  kind: "evaluate" | "simplify" | "solve" | "inequality";
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
  course: string | null; // set when restricted to one course
  unit: { id: string; name: string } | null; // set when restricted to one unit
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

export type ConceptLesson = {
  summary: string;
  steps: string[];
  example: string[]; // worked example: first line is the problem, last line the answer
  mistake: string;
};

export type Course = {
  id: string;
  name: string;
  grades: string;
  description: string;
  units: { id: string; name: string; skills: { id: string; name: string; concept?: ConceptLesson }[] }[];
};

export type JoinedCourse = Course & {
  joined_at: string;
  summary: { skills: number; mastered: number; average_mastery: number; attempts: number; correct: number };
  units_progress: { id: string; name: string; skills: number; mastered: number; average_mastery: number }[];
  mastery: MasteryReport;
};

export type WalkthroughStep = { operation: string; result: string };
export type Walkthrough = { problem: string; steps: WalkthroughStep[] };

export type TutorRequest = {
  messages: { role: "user" | "assistant"; content: string }[]; // recent conversation, oldest first
  mode: "chat" | "selection" | "explain_unit";
  course?: string;
  unit?: string;
  problem_id?: string; // the practice problem on screen: the tutor won't give its answer
  selection?: string;  // highlighted text (mode "selection")
};

export type TutorReply = {
  message: string;
  walkthrough: Walkthrough | null; // every step verified by SymPy on the server
  verified: boolean;
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
    if (res.status === 429) throw new Error(detail); // rate limit: the message is meant for the student
    throw new Error(res.status === 503 ? `AI help is unavailable: ${detail}` : `Server error ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

const user = (id: string) => `/users/${encodeURIComponent(id)}`;

/** "?a=1&b=2" from the defined values, or "" if none. */
function query(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) q.set(k, v);
  const s = q.toString();
  return s ? `?${s}` : "";
}

export const api = {
  courses: () => request<Course[]>("/courses"),
  course: (courseId: string) => request<Course>(`/courses/${encodeURIComponent(courseId)}`),
  myCourses: (userId: string) => request<JoinedCourse[]>(`${user(userId)}/courses`),
  join: (userId: string, courseId: string) =>
    request<{ joined: string }>(`${user(userId)}/courses/${encodeURIComponent(courseId)}`, { method: "POST" }),

  // `unit` narrows a course to one of its units.
  mastery: (userId: string, course?: string, unit?: string) =>
    request<MasteryReport>(`${user(userId)}/mastery${query({ course, unit })}`),

  // Without `skill`, the backend picks the recommended skill (within the course/unit if given).
  nextProblem: (userId: string, skill?: string, course?: string, unit?: string) =>
    request<Problem>(`${user(userId)}/next${query({ skill, course, unit })}`),

  submit: (userId: string, problemId: string, answer: string, course?: string, unit?: string) =>
    request<AttemptResult>(`${user(userId)}/attempts${query({ course, unit })}`, {
      method: "POST",
      body: JSON.stringify({ problem_id: problemId, answer }),
    }),

  tutor: (userId: string, body: TutorRequest) =>
    request<TutorReply>(`${user(userId)}/tutor`, { method: "POST", body: JSON.stringify(body) }),

  // `current` = the step the student is on (defaults to the problem itself).
  hint: (userId: string, problemId: string, current?: string) =>
    request<Hint>(`${user(userId)}/hints`, {
      method: "POST",
      body: JSON.stringify({ problem_id: problemId, current: current ?? null }),
    }),
};
