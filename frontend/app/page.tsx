"use client";

// Home: a welcome hero with sign-in (a simple user id), then the Dashboard.
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FloatingSymbols } from "@/components/Decor";
import { USER_ID_PATTERN, saveUserId, useUserId } from "@/lib/user";

const FEATURES = [
  { icon: "📘", title: "Clear lessons", text: "Ideas, steps, worked examples and common mistakes for every topic." },
  { icon: "🎯", title: "Smart practice", text: "A neural network tracks what you've mastered and picks your next problem." },
  { icon: "✦", title: "AI tutor", text: "Ask anything. Every step it shows you is checked by a math engine." },
];

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
    <div className="space-y-12">
      <section className="grid items-center gap-10 lg:grid-cols-2">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1 text-xs font-bold text-violet-700 shadow-sm ring-1 ring-violet-200 dark:bg-slate-900 dark:text-violet-300 dark:ring-violet-800">
            ✦ Pre-Algebra · Algebra 1 · Algebra 2
          </span>
          <h1 className="mt-4 text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl">
            Learn algebra,{" "}
            <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-rose-500 bg-clip-text text-transparent">one skill at a time</span>
          </h1>
          <p className="mt-4 max-w-lg text-lg text-slate-600 dark:text-slate-300">
            Read short lessons, practice with step-by-step hints, and let the tutor figure out what you should learn next.
          </p>

          <form onSubmit={signIn} className="mt-8 max-w-md rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-lg backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
            <label htmlFor="uid" className="block text-sm font-bold">
              Choose a user ID to start
            </label>
            <div className="mt-2 flex gap-2">
              <input
                id="uid"
                value={draft}
                onChange={(e) => setDraft(e.target.value.trim())}
                placeholder="e.g. student_01"
                autoComplete="off"
                className="min-w-0 flex-1 rounded-xl border-2 border-slate-200 bg-white px-3 py-2.5 focus:border-violet-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950"
              />
              <button
                type="submit"
                disabled={!valid}
                className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-2.5 font-bold text-white shadow-md shadow-violet-500/30 hover:from-indigo-700 hover:to-violet-700 disabled:opacity-50"
              >
                Start →
              </button>
            </div>
            {draft && !valid ? (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">Use letters, numbers, - or _ (up to 40).</p>
            ) : (
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Use the same ID next time to keep your progress.</p>
            )}
          </form>
        </div>

        {/* Decorative chalkboard with a worked example */}
        <div aria-hidden className="relative">
          <div className="absolute -inset-4 rotate-2 rounded-[2rem] bg-gradient-to-br from-indigo-500 via-violet-500 to-rose-500 opacity-80 blur-sm" />
          <div className="chalkboard relative overflow-hidden rounded-[1.75rem] p-8 text-white shadow-2xl">
            <FloatingSymbols symbols={["π", "√", "x²"]} />
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-white/50">Worked example</p>
            <div className="mt-5 space-y-3 font-mono text-2xl">
              <p>3x + 5 = 17</p>
              <p className="flex items-center gap-3 font-sans text-sm text-violet-200">
                <span>↓</span>
                <span className="rounded-full bg-violet-500/30 px-3 py-1">Subtract 5 from both sides</span>
              </p>
              <p>
                3x + 5 <span className="rounded bg-emerald-400/40 px-1">− 5</span> = 17 <span className="rounded bg-emerald-400/40 px-1">− 5</span>
              </p>
              <p className="flex items-center gap-3 font-sans text-sm text-violet-200">
                <span>↓</span>
                <span className="rounded-full bg-violet-500/30 px-3 py-1">Divide both sides by 3</span>
              </p>
              <p className="inline-block rounded-lg bg-white/15 px-3 py-1 font-bold text-amber-300">x = 4</p>
            </div>
            <p className="mt-6 text-xs text-white/50">✓ every step checked</p>
          </div>
          <div className="absolute -bottom-5 -left-4 flex gap-2">
            {[
              ["Pre-Algebra", "from-teal-500 to-cyan-600"],
              ["Algebra 1", "from-indigo-500 to-purple-600"],
              ["Algebra 2", "from-rose-500 to-orange-500"],
            ].map(([name, g]) => (
              <span key={name} className={`rounded-full bg-gradient-to-r px-3 py-1.5 text-xs font-bold text-white shadow-md ${g}`}>
                {name}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {FEATURES.map((f) => (
          <div key={f.title} className="rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-900/80">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-xl dark:bg-violet-900/50">{f.icon}</span>
            <h2 className="mt-3 font-extrabold">{f.title}</h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{f.text}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
