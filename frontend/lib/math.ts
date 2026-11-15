// Display-only formatting. The backend writes math the way students can type
// it (x^2, sqrt(49), <=); on screen we show x², √49 and ≤. Never send the
// pretty form back.
const SUPERSCRIPT: Record<string, string> = { "2": "²", "3": "³", "4": "⁴" };

export function pretty(math: string): string {
  return math
    .replace(/\^([234])/g, (_, d: string) => SUPERSCRIPT[d])
    .replace(/sqrt\((\d+)\)/g, "√$1")
    .replace(/<=/g, "≤")
    .replace(/>=/g, "≥");
}
