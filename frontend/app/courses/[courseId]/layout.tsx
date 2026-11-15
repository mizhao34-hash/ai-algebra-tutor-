"use client";

// Shared frame for a course: title, and tabs on the left (on top on phones).
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Course } from "@/lib/api";
import { useUserId } from "@/lib/user";

export default function CourseLayout({ children }: { children: React.ReactNode }) {
  const { courseId } = useParams<{ courseId: string }>();
  const pathname = usePathname();
  const router = useRouter();
  const [userId, loaded] = useUserId();
  const [course, setCourse] = useState<Course | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loaded && !userId) router.replace("/");
  }, [loaded, userId, router]);

  useEffect(() => {
    api.course(courseId).then(setCourse, (e) => setError(e instanceof Error ? e.message : String(e)));
  }, [courseId]);

  // Opening a course joins it (idempotent), so it shows up on the Dashboard.
  useEffect(() => {
    if (userId) api.join(userId, courseId).catch(() => {});
  }, [userId, courseId]);

  if (!userId) return null;

  const tabs = [
    { href: `/courses/${courseId}`, label: "Lesson" },
    { href: `/courses/${courseId}/practice`, label: "Practice" },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">{course?.name ?? (error ? "Course" : "Loading…")}</h1>
        {course && <p className="text-sm text-slate-500 dark:text-slate-400">{course.grades}</p>}
        {error && <p className="mt-2 text-sm text-red-700 dark:text-red-300">{error}</p>}
      </div>

      <div className="grid gap-6 md:grid-cols-[10rem_1fr]">
        <nav aria-label="Course sections" className="flex gap-2 md:flex-col">
          {tabs.map((t) => {
            const active = pathname === t.href;
            return (
              <Link
                key={t.href}
                href={t.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-md px-3 py-2 text-sm font-medium ${
                  active
                    ? "bg-sky-100 text-sky-900 dark:bg-sky-900/50 dark:text-sky-100"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}
