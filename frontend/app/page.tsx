"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { USER_ID_PATTERN, saveUserId, useUserId } from "@/lib/user";

export default function Home() {
  const router = useRouter();
  const [savedId, loaded] = useUserId();
  const [id, setId] = useState("");

  useEffect(() => {
    if (savedId) setId(savedId);
  }, [savedId]);

  const valid = USER_ID_PATTERN.test(id);

  function start(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    saveUserId(id);
    router.push("/practice");
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-2xl font-semibold">Practice linear equations</h1>
      <p className="mt-2 text-slate-600 dark:text-slate-300">
        The tutor tracks what you&apos;ve mastered and picks the next skill to practice.
      </p>
      <form onSubmit={start} className="mt-6 space-y-3">
        <label htmlFor="uid" className="block text-sm font-medium">
          Your user ID
        </label>
        <input
          id="uid"
          value={id}
          onChange={(e) => setId(e.target.value.trim())}
          placeholder="e.g. student_01"
          autoComplete="off"
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
        />
        {id && !valid && (
          <p className="text-sm text-red-600 dark:text-red-400">Use letters, numbers, - or _ (up to 40).</p>
        )}
        <button
          type="submit"
          disabled={!valid || !loaded}
          className="w-full rounded-md bg-sky-600 px-4 py-2 font-medium text-white hover:bg-sky-700 disabled:opacity-50"
        >
          {savedId && savedId === id ? "Continue" : "Start"}
        </button>
      </form>
    </div>
  );
}
