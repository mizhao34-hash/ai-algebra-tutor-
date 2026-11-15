import type { Metadata } from "next";
import { JetBrains_Mono, Plus_Jakarta_Sans } from "next/font/google";
import { NavBar } from "@/components/NavBar";
import { TutorPanel } from "@/components/tutor/TutorPanel";
import { TutorProvider } from "@/components/tutor/TutorProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Algebra Tutor",
  description: "Algebra lessons and adaptive practice",
};

// Downloaded at build time and self-hosted by Next.js (no request to Google from the browser).
const sans = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body className="font-sans">
        <TutorProvider>
          <NavBar />
          {/* pb-24 leaves room for the floating "Ask the AI tutor" button */}
          <main className="mx-auto max-w-6xl px-4 pb-28 pt-8">{children}</main>
          <TutorPanel />
        </TutorProvider>
      </body>
    </html>
  );
}
