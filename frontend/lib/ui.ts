// Small design system: one accent color per course, and four button levels so
// the most important action on a screen is always the most visible one.
//
// Tailwind only ships classes it can find as complete strings in the source,
// so every class below is written out in full (no string building).

export type Theme = {
  name: string;
  solid: string;    // filled button / active marker
  soft: string;     // tinted background with readable text
  text: string;     // accent-colored text
  border: string;   // accent border
  bar: string;      // progress bar fill
  ring: string;     // focus / highlight ring
};

const THEMES: Record<string, Theme> = {
  pre_algebra: {
    name: "teal",
    solid: "bg-teal-600 hover:bg-teal-700 focus-visible:outline-teal-600",
    soft: "bg-teal-50 text-teal-900 dark:bg-teal-950/60 dark:text-teal-100",
    text: "text-teal-700 dark:text-teal-300",
    border: "border-teal-500",
    bar: "bg-teal-500",
    ring: "ring-teal-500/30",
  },
  algebra_1: {
    name: "indigo",
    solid: "bg-indigo-600 hover:bg-indigo-700 focus-visible:outline-indigo-600",
    soft: "bg-indigo-50 text-indigo-900 dark:bg-indigo-950/60 dark:text-indigo-100",
    text: "text-indigo-700 dark:text-indigo-300",
    border: "border-indigo-500",
    bar: "bg-indigo-500",
    ring: "ring-indigo-500/30",
  },
  algebra_2: {
    name: "rose",
    solid: "bg-rose-600 hover:bg-rose-700 focus-visible:outline-rose-600",
    soft: "bg-rose-50 text-rose-900 dark:bg-rose-950/60 dark:text-rose-100",
    text: "text-rose-700 dark:text-rose-300",
    border: "border-rose-500",
    bar: "bg-rose-500",
    ring: "ring-rose-500/30",
  },
};

const DEFAULT_THEME: Theme = {
  name: "sky",
  solid: "bg-sky-600 hover:bg-sky-700 focus-visible:outline-sky-600",
  soft: "bg-sky-50 text-sky-900 dark:bg-sky-950/60 dark:text-sky-100",
  text: "text-sky-700 dark:text-sky-300",
  border: "border-sky-500",
  bar: "bg-sky-500",
  ring: "ring-sky-500/30",
};

export function theme(courseId?: string): Theme {
  return (courseId && THEMES[courseId]) || DEFAULT_THEME;
}

const base =
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition " +
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 " +
  "disabled:cursor-not-allowed disabled:opacity-50";

export const btn = {
  /** The one main action on the screen (Check, Next problem, Continue). */
  primary: (t: Theme, size: "md" | "lg" = "md") =>
    `${base} ${t.solid} text-white shadow-sm ${size === "lg" ? "px-5 py-2.5 text-base" : "px-4 py-2 text-sm"}`,
  /** Alternatives next to a primary action (Lesson, Practice this topic). */
  secondary:
    `${base} border border-slate-300 bg-white px-4 py-2 text-sm text-slate-800 hover:bg-slate-50 ` +
    "focus-visible:outline-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800",
  /** Help actions: always purple, so hints are recognizable everywhere. */
  hint:
    `${base} bg-violet-100 px-4 py-2 text-sm text-violet-900 hover:bg-violet-200 ` +
    "focus-visible:outline-violet-600 dark:bg-violet-900/50 dark:text-violet-100 dark:hover:bg-violet-900",
  /** Low-emphasis actions (Skip, switch user). */
  subtle:
    "inline-flex items-center gap-1.5 rounded text-sm font-medium text-slate-500 hover:text-slate-900 " +
    "disabled:opacity-50 dark:text-slate-400 dark:hover:text-white",
};

export const card = "rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900";
