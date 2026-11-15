import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Fonts are loaded with next/font in app/layout.tsx and exposed as CSS variables.
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      keyframes: {
        float: { "0%, 100%": { transform: "translateY(0) rotate(var(--r, 0deg))" }, "50%": { transform: "translateY(-10px) rotate(var(--r, 0deg))" } },
      },
      animation: { float: "float 7s ease-in-out infinite" },
    },
  },
  plugins: [],
} satisfies Config;
