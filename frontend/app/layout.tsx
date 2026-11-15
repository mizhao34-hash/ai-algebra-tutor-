import type { Metadata } from "next";
import { NavBar } from "@/components/NavBar";
import { TutorPanel } from "@/components/tutor/TutorPanel";
import { TutorProvider } from "@/components/tutor/TutorProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Algebra Tutor",
  description: "Algebra lessons and adaptive practice",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <TutorProvider>
          <NavBar />
          {/* pb-24 leaves room for the floating "Ask the AI tutor" button */}
          <main className="mx-auto max-w-5xl px-4 pb-24 pt-8">{children}</main>
          <TutorPanel />
        </TutorProvider>
      </body>
    </html>
  );
}
