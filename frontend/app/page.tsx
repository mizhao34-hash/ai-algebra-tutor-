"use client";

// Home: sign in with a user id, then go to the Dashboard.
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { USER_ID_PATTERN, saveUserId, useUserId } from "@/lib/user";

export default function Home() {
  const router = useRouter();
  const [savedId, loaded] = useUserId();
  const [draft, setDraft] = useState("");

  // Already signed in: nothing to do here.
  useEffect(() => {
    if (loaded && savedId) router.replace("/dashboard");
  }, [loaded, savedId, router]);

  if (!loaded || savedId) return null;

  const valid = USER_ID_PATTERN.test(draft);

  function signIn(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    saveUserId(draft);
    router.push("/dashboard");
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-2xl font-semibold">Learn algebra, one skill at a time</h1>
      <p className="mt-2 text-slate-600 dark:text-slate-300">
        Pre-Algebra, Algebra 1 and Algebra 2: read the lessons, practice with step-by-step hints, and the tutor
        tracks what you&apos;ve mastered.
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
        {draft && !valid && <p className="text-sm text-red-600 dark:text-red-400">Use letters, numbers, - or _ (up to 40).</p>}
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
