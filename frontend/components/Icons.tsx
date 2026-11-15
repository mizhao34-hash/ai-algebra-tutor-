// Small inline icons (24×24 outline style), so buttons can be told apart at a glance.
type P = { className?: string };
const svg = (className = "h-4 w-4") => ({
  className,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
});

export const CheckIcon = ({ className }: P) => (
  <svg {...svg(className)}><path d="M20 6 9 17l-5-5" /></svg>
);
export const XIcon = ({ className }: P) => (
  <svg {...svg(className)}><path d="M18 6 6 18M6 6l12 12" /></svg>
);
export const ArrowRightIcon = ({ className }: P) => (
  <svg {...svg(className)}><path d="M5 12h14M13 6l6 6-6 6" /></svg>
);
export const SkipIcon = ({ className }: P) => (
  <svg {...svg(className)}><path d="m5 5 7 7-7 7M13 5l7 7-7 7" /></svg>
);
export const LightbulbIcon = ({ className }: P) => (
  <svg {...svg(className)}>
    <path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.4 1 1.1 1 1.8V16h5v-.3c0-.7.4-1.4 1-1.8A6 6 0 0 0 12 3Z" />
  </svg>
);
export const BookIcon = ({ className }: P) => (
  <svg {...svg(className)}><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2V5Z" /><path d="M4 19a2 2 0 0 1 2-2h13" /></svg>
);
export const PencilIcon = ({ className }: P) => (
  <svg {...svg(className)}><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
);
export const ChartIcon = ({ className }: P) => (
  <svg {...svg(className)}><path d="M3 3v18h18" /><path d="M7 15l4-4 3 3 5-6" /></svg>
);
export const ChevronDownIcon = ({ className }: P) => (
  <svg {...svg(className)}><path d="m6 9 6 6 6-6" /></svg>
);
export const WarningIcon = ({ className }: P) => (
  <svg {...svg(className)}><path d="M12 9v4M12 17h.01" /><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /></svg>
);
