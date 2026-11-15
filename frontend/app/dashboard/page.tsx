"use client";

// Dashboard: the courses this user has joined and their mastery, with a
// per-skill breakdown grouped by prerequisite level inside each course.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MasteryBar, StateChip, skillState } from "@/components/Mastery";
import { api, type Course, type JoinedCourse, type SkillMastery } from "@/lib/api";
import { saveUserId, useUserId } from "@/lib/user";

/** Group skills by prerequisite depth: 0 = no prerequisites (inside this course),
 *  otherwise 1 + the deepest prerequisite. Works in one pass because the
 *  backend lists skills in topological order (prerequisites first). */
function byLevel(skills: SkillMastery[]): SkillMastery[][] {
  const depth: Record<string, number> = {};
  const levels: SkillMastery[][] = [];
  for (const s of skills) {
    const d = s.prerequisites.length ? 1 + Math.max(...s.prerequisites.map((p) => depth[p])) : 0;
    depth[s.id] = d;
    (levels[d] ??= []).push(s);
  }
  return levels;
}

const pct = (x: number) => `${Math.round(x * 100)}%`;

export default function Dashboard() {
  const router = useRouter();
  const [userId, loaded] = useUserId();
  const [courses, setCourses] = useState<JoinedCourse[] | null>(null);
  const [catalog, setCatalog] = useState<Course[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loaded && !userId) router.replace("/");
  }, [loaded, userId, router]);

  useEffect(() => {
    if (!userId) return;
    api.myCourses(userId).then(setCourses, (e) => setError(e instanceof Error ? e.message : String(e)));
    api.courses().then(setCatalog, () => {});
  }, [userId]);

  function switchUser() {
    saveUserId(null);
    router.push("/");
  }

  if (!userId) return null;
  if (error)
    return (
      <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
        {error}
      </div>
    );
  if (!courses)
    return <p className="text-slate-500">Loading… If the server was idle, it can take up to a minute to wake up.</p>;

  return (
    <div>
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Signed in as <span className="font-medium text-slate-700 dark:text-slate-200">{userId}</span> ·{" "}
        <button onClick={switchUser} className="underline">
          switch user
        </button>{" "}
        · a skill is mastered at a 70% predicted chance of answering correctly
      </p>

      {courses.length === 0 && (
        <p className="mt-6 text-slate-600 dark:text-slate-300">You haven&apos;t started a course yet. Pick one below.</p>
      )}

      <div className="mt-6 space-y-8">
        {courses.map((c) => {
          const s = c.summary;
          const names = Object.fromEntries(c.mastery.skills.map((k) => [k.id, k.name]));
          return (
            <section key={c.id} className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">{c.name}</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{c.grades}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link href={`/courses/${c.id}`} className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
                    Lesson
                  </Link>
                  <Link href={`/courses/${c.id}/practice`} className="rounded-md bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-700">
                    Practice {names[c.mastery.recommended]}
                  </Link>
                </div>
              </div>

              <dl className="mt-4 grid grid-cols-3 gap-3">
                {[
                  ["Skills mastered", `${s.mastered} / ${s.skills}`],
                  ["Problems tried", String(s.attempts)],
                  ["First-try accuracy", s.attempts ? pct(s.correct / s.attempts) : "—"],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-md bg-slate-50 p-3 dark:bg-slate-950">
                    <dt className="text-xs text-slate-500 dark:text-slate-400">{label}</dt>
                    <dd className="mt-1 text-xl font-semibold tabular-nums">{value}</dd>
                  </div>
                ))}
              </dl>

              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-medium">Skill breakdown</summary>
                <div className="mt-4 space-y-5">
                  {byLevel(c.mastery.skills).map((level, i) => (
                    <div key={i}>
                      <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Level {i + 1}</h3>
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {level.map((k) => (
                          <div
                            key={k.id}
                            className={`rounded-md border p-3 ${
                              k.id === c.mastery.recommended ? "border-sky-500 ring-2 ring-sky-500/30" : "border-slate-200 dark:border-slate-800"
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <h4 className="text-sm font-medium">{k.name}</h4>
                              <StateChip state={skillState(k)} />
                            </div>
                            <p className="mt-1 text-xl font-semibold tabular-nums">{pct(k.mastery)}</p>
                            <div className="mt-1">
                              <MasteryBar skill={k} threshold={c.mastery.threshold} />
                            </div>
                            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                              {k.attempts
                                ? `${k.correct} of ${k.attempts} right on first try`
                                : k.mastery > 0
                                  ? "Not practiced yet · estimated from your other answers"
                                  : "Not practiced yet"}
                            </p>
                            {k.prerequisites.length > 0 && (
                              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                                Needs: {k.prerequisites.map((p) => names[p]).join(", ")}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            </section>
          );
        })}
      </div>

      {catalog.some((c) => !courses.some((j) => j.id === c.id)) && (
        <section className="mt-10">
          <h2 className="text-lg font-semibold">{courses.length ? "Other courses" : "Courses"}</h2>
          <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {catalog
              .filter((c) => !courses.some((j) => j.id === c.id))
              .map((c) => (
                <div key={c.id} className="flex flex-col rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold">{c.name}</h3>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                      {c.grades}
                    </span>
                  </div>
                  <p className="mt-2 flex-1 text-sm text-slate-600 dark:text-slate-300">{c.description}</p>
                  <Link href={`/courses/${c.id}`} className="mt-4 rounded-md bg-sky-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-sky-700">
                    Start course
                  </Link>
                </div>
              ))}
          </div>
        </section>
      )}
    </div>
  );
}
