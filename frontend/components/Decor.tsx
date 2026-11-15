// Decorative pieces: floating math symbols for banners, a progress ring, and
// section headings with an icon tile. Purely visual (aria-hidden where decorative).

// Fixed positions so the layout is the same on every render (no randomness).
const SPOTS = [
  { top: "8%", left: "62%", size: "text-5xl", r: "-12deg", delay: "0s" },
  { top: "52%", left: "78%", size: "text-6xl", r: "8deg", delay: "1.2s" },
  { top: "18%", left: "88%", size: "text-3xl", r: "14deg", delay: "2.1s" },
  { top: "62%", left: "56%", size: "text-3xl", r: "-6deg", delay: "0.6s" },
  { top: "4%", left: "76%", size: "text-2xl", r: "4deg", delay: "3s" },
  { top: "70%", left: "92%", size: "text-2xl", r: "-10deg", delay: "1.8s" },
];

export function FloatingSymbols({ symbols }: { symbols: string[] }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 hidden overflow-hidden sm:block">
      {symbols.slice(0, SPOTS.length).map((sym, i) => {
        const s = SPOTS[i];
        return (
          <span
            key={i}
            className={`absolute animate-float font-mono font-bold text-white/25 ${s.size}`}
            style={{ top: s.top, left: s.left, animationDelay: s.delay, ["--r" as string]: s.r }}
          >
            {sym}
          </span>
        );
      })}
    </div>
  );
}

/** Circular progress (0..1) with a label in the middle. */
export function ProgressRing({
  value,
  size = 56,
  stroke = 6,
  label,
  className = "text-white",
  track = "stroke-white/25",
}: {
  value: number;
  size?: number;
  stroke?: number;
  label?: string;
  className?: string;
  track?: string;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className={`relative shrink-0 ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} className={track} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          stroke="currentColor"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - Math.max(0, Math.min(1, value)))}
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-bold tabular-nums">
        {label ?? `${Math.round(value * 100)}%`}
      </span>
    </div>
  );
}

/** A labeled block heading: colored icon tile + title. */
export function BlockTitle({ icon, title, tone }: { icon: React.ReactNode; title: string; tone: string }) {
  return (
    <h4 className="flex items-center gap-2 text-sm font-bold">
      <span className={`flex h-7 w-7 items-center justify-center rounded-lg ${tone}`}>{icon}</span>
      {title}
    </h4>
  );
}
