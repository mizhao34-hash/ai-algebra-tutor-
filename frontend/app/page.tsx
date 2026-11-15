"use client";

// Home: enter a user id, then pick a course from the catalog.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Course } from "@/lib/api";
import { USER_ID_PATTERN, saveUserId, useUserId } from "@/lib/user";

export default function Home() {
  const [savedId, loaded] = useUserId();
  const [userId, setUserId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [joined, setJoined] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loaded) setUserId(savedId);
  }, [loaded, savedId]);

  useEffect(() => {
    api.courses().then(setCourses, (e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => {
    if (!userId) return;
    api.myCourses(userId).then((mine) => setJoined(new Set(mine.map((c) => c.id))), () => {});
  }, [userId]);

  function signIn(e: React.FormEvent) {
    e.preventDefault();
    if (!USER_ID_PATTERN.test(draft)) return;
    saveUserId(draft);
    setUserId(draft);
  }

  function signOut() {
    saveUserId(null);
    setUserId(null);
    setDraft("");
    setJoined(new Set());
  }

  if (!loaded) return null;

  if (!userId) {
    const valid = USER_ID_PATTERN.test(draft);
    return (
      <div className="mx-auto max-w-md">
        <h1 className="text-2xl font-semibold">Learn algebra, one skill at a time</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-300">
          Read the concepts, practice with step-by-step hints, and the tutor tracks what you&apos;ve mastered.
        </p>
        <form onSubmit={signIn} className="mt-6 space-y-3">
          <label htmlFor="uid" className="block text-sm font-medium">
            Your user ID
          </label>
          <input
            id="uid"
            value={draft}
            onChange={(e) => setDraft(e.target.value.trim())}
            placeholder="e.g. student_01"
            autoComplete="off"
            className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
          />
          {draft && !valid && (
            <p className="text-sm text-red-600 dark:text-red-400">Use letters, numbers, - or _ (up to 40).</p>
          )}
          <button
            type="submit"
            disabled={!valid}
            className="w-full rounded-md bg-sky-600 px-4 py-2 font-medium text-white hover:bg-sky-700 disabled:opacity-50"
          >
            Start
          </button>
        </form>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Courses</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Signed in as <span className="font-medium text-slate-700 dark:text-slate-200">{userId}</span> ·{" "}
            <button onClick={signOut} className="underline">
              change
            </button>
          </p>
        </div>
      </div>

      {error && <p className="mt-4 text-sm text-red-700 dark:text-red-300">{error}</p>}
      {!courses && !error && (
        <p className="mt-6 text-slate-500">Loading… If the server was idle, it can take up to a minute to wake up.</p>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {courses?.map((c) => {
          const isJoined = joined.has(c.id);
          return (
            <div key={c.id} className="flex flex-col rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-start justify-between gap-2">
                <h2 className="text-lg font-semibold">{c.name}</h2>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {c.grades}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{c.description}</p>
              <ul className="mt-3 flex-1 space-y-1 text-sm text-slate-500 dark:text-slate-400">
                {c.units.map((u) => (
                  <li key={u.id}>
                    {u.name}: {u.skills.map((s) => s.name).join(", ")}
                  </li>
                ))}
              </ul>
              <Link
                href={`/courses/${c.id}`}
                className="mt-4 rounded-md bg-sky-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-sky-700"
              >
                {isJoined ? "Continue" : "Join course"}
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
