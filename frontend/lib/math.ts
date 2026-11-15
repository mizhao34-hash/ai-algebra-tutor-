// Display-only formatting: the backend writes powers as x^2 (what students can
// type); on screen we show superscripts. Never send the pretty form back.
const SUPERSCRIPT: Record<string, string> = { "2": "²", "3": "³", "4": "⁴" };

export function pretty(math: string): string {
  return math.replace(/\^([234])/g, (_, d: string) => SUPERSCRIPT[d]);
}
