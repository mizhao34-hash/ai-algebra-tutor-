"use client";

// Top bar: Dashboard and one tab per course; the active tab is highlighted.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { COURSE_TABS } from "@/lib/courses";
import { theme } from "@/lib/ui";

export function NavBar() {
  const pathname = usePathname();
  const tabs = [
    { href: "/dashboard", label: "Dashboard", active: "bg-slate-900 text-white dark:bg-white dark:text-slate-900" },
    // Each course tab lights up in that course's own color.
    ...COURSE_TABS.map((c) => ({ href: `/courses/${c.id}`, label: c.name, active: theme(c.id).soft })),
  ];
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/75 backdrop-blur-md dark:border-slate-800/70 dark:bg-slate-900/75">
      <nav className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-1 gap-y-2 px-4 py-2.5">
        <Link href="/" className="mr-4 flex items-center gap-2 font-bold">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-violet-500 to-rose-500 font-mono text-sm text-white shadow-md shadow-violet-500/30">
            x²
          </span>
          <span className="text-lg tracking-tight">Algebra Tutor</span>
        </Link>
        {tabs.map((t) => {
          const active = pathname === t.href || pathname.startsWith(t.href + "/");
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={active ? "page" : undefined}
              className={`rounded-lg px-3 py-1.5 text-sm font-semibold ${
                active ? t.active : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
              }`}
            >
              {t.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
