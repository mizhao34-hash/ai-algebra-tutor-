"use client";

// Shared frame for a course: a gradient banner (course color, floating math
// symbols, overall progress), and Lesson / Practice tabs on the left (on top on phones).
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FloatingSymbols, ProgressRing } from "@/components/Decor";
import { BookIcon, PencilIcon } from "@/components/Icons";
import { useTutorPage } from "@/components/tutor/TutorProvider";
import { api, type Course, type MasteryReport } from "@/lib/api";
import { theme } from "@/lib/ui";
import { useUserId } from "@/lib/user";

export default function CourseLayout({ children }: { children: React.ReactNode }) {
  const { courseId } = useParams<{ courseId: string }>();
  const pathname = usePathname();
  const router = useRouter();
  const [userId, loaded] = useUserId();
  const [course, setCourse] = useState<Course | null>(null);
  const [report, setReport] = useState<MasteryReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const t = theme(courseId);
  useTutorPage({ course: courseId }); // the AI tutor knows which course you're in

  useEffect(() => {
    if (loaded && !userId) router.replace("/");
  }, [loaded, userId, router]);

  useEffect(() => {
    api.course(courseId).then(setCourse, (e) => setError(e instanceof Error ? e.message : String(e)));
  }, [courseId]);

  // Opening a course joins it (idempotent), so it shows up on the Dashboard.
  // Refresh the banner's progress when switching tabs (e.g. after practicing).
  useEffect(() => {
    if (!userId) return;
    api.join(userId, courseId).catch(() => {});
    api.mastery(userId, courseId).then(setReport, () => {});
  }, [userId, courseId, pathname]);

  if (!userId) return null;

  const tabs = [
    { href: `/courses/${courseId}`, label: "Lesson", hint: "Learn the ideas", Icon: BookIcon },
    { href: `/courses/${courseId}/practice`, label: "Practice", hint: "Solve problems", Icon: PencilIcon },
  ];
  const mastered = report?.skills.filter((s) => s.mastered).length ?? 0;
  const total = report?.skills.length ?? 0;
  const units = course?.units.length ?? 0;

  return (
    <div>
      <section className={`relative mb-8 overflow-hidden rounded-3xl px-6 py-8 text-white shadow-lg sm:px-8 ${t.gradient}`}>
        <FloatingSymbols symbols={t.symbols} />
        <div className="relative flex flex-wrap items-center justify-between gap-6">
          <div className="max-w-xl">
            <span className="inline-block rounded-full bg-white/20 px-3 py-1 text-xs font-bold uppercase tracking-wider backdrop-blur">
              {course?.grades ?? "Course"}
            </span>
            <h1 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
              {course?.name ?? (error ? "Course" : "Loading…")}
            </h1>
            {course && <p className="mt-2 text-white/90">{course.description}</p>}
            {course && (
              <p className="mt-3 text-sm font-medium text-white/80">
                {units} units · {total || course.units.reduce((n, u) => n + u.skills.length, 0)} topics
              </p>
            )}
            {error && <p className="mt-2 rounded bg-white/20 px-2 py-1 text-sm">{error}</p>}
          </div>
          {report && total > 0 && (
            <div className="flex items-center gap-3 rounded-2xl bg-white/15 px-4 py-3 backdrop-blur">
              <ProgressRing value={mastered / total} size={64} label={`${mastered}/${total}`} />
              <div className="text-sm">
                <p className="font-bold">Topics mastered</p>
                <p className="text-white/80">Keep going!</p>
              </div>
            </div>
          )}
        </div>
      </section>

      <div className="grid gap-8 md:grid-cols-[12rem_1fr]">
        <nav aria-label="Course sections" className="flex gap-2 md:sticky md:top-20 md:h-fit md:flex-col">
          {tabs.map(({ href, label, hint, Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex flex-1 items-center gap-3 rounded-2xl border px-3 py-3 transition md:flex-none ${
                  active
                    ? "border-transparent bg-white shadow-md dark:bg-slate-900"
                    : "border-transparent text-slate-600 hover:bg-white/70 dark:text-slate-300 dark:hover:bg-slate-900/70"
                }`}
              >
                <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${active ? `${t.gradient} text-white` : t.icon}`}>
                  <Icon className="h-4 w-4" />
                </span>
                <span>
                  <span className="block text-sm font-bold">{label}</span>
                  <span className="hidden text-xs text-slate-500 md:block dark:text-slate-400">{hint}</span>
                </span>
              </Link>
            );
          })}
        </nav>
        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}
