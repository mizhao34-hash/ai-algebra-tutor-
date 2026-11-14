import type { SkillMastery } from "@/lib/api";

export type SkillState = "mastered" | "unlocked" | "locked";

export function skillState(s: SkillMastery): SkillState {
  if (s.mastered) return "mastered";
  return s.unlocked ? "unlocked" : "locked";
}

const BAR_COLOR: Record<SkillState, string> = {
  mastered: "bg-emerald-500",
  unlocked: "bg-sky-500",
  locked: "bg-slate-400 dark:bg-slate-500",
};

const CHIP: Record<SkillState, string> = {
  mastered: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200",
  unlocked: "bg-sky-100 text-sky-800 dark:bg-sky-900/50 dark:text-sky-200",
  locked: "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200",
};

const LABEL: Record<SkillState, string> = { mastered: "Mastered", unlocked: "Practicing", locked: "Locked" };

export function StateChip({ state }: { state: SkillState }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CHIP[state]}`}>{LABEL[state]}</span>;
}

/** Horizontal bar with a tick at the mastery threshold. */
export function MasteryBar({ skill, threshold }: { skill: SkillMastery; threshold: number }) {
  const pct = Math.round(skill.mastery * 100);
  return (
    <div
      className="relative h-2.5 w-full rounded-full bg-slate-200 dark:bg-slate-700"
      role="progressbar"
      aria-label={`${skill.name} mastery`}
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className={`h-full rounded-full ${BAR_COLOR[skillState(skill)]}`} style={{ width: `${pct}%` }} />
      <div
        className="absolute -top-1 h-[1.125rem] w-0.5 bg-slate-700 dark:bg-slate-200"
        style={{ left: `${threshold * 100}%` }}
        title={`Mastery threshold ${Math.round(threshold * 100)}%`}
      />
    </div>
  );
}

/** Compact list used beside the practice problem. */
export function MasteryList({
  skills,
  threshold,
  recommended,
}: {
  skills: SkillMastery[];
  threshold: number;
  recommended: string;
}) {
  return (
    <>
    <ul className="space-y-3">
      {skills.map((s) => (
        <li key={s.id}>
          <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
            <span className={s.id === recommended ? "font-semibold" : ""}>
              {s.name}
              {s.id === recommended && <span className="ml-1 text-xs text-sky-600 dark:text-sky-400">← next</span>}
            </span>
            <span className="tabular-nums text-slate-500 dark:text-slate-400">
              {Math.round(s.mastery * 100)}%
              {s.attempts === 0 && <span title="Not practiced yet: estimated from your other answers">*</span>}
            </span>
          </div>
          <MasteryBar skill={s} threshold={threshold} />
        </li>
      ))}
    </ul>
    <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
      * not practiced yet; estimated from your other answers. The tick marks the {Math.round(threshold * 100)}% mastery threshold.
    </p>
    </>
  );
}
