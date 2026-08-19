import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "DVAH — Damn Vulnerable Agent Harness",
  description: "Patch-the-runtime security lab for AI agent platforms.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>
          <div className="flex h-screen flex-col">
            <header className="flex items-center gap-4 border-b border-border bg-panel px-4 py-2 text-sm">
              <Link href="/" className="mono font-semibold text-accent">
                DVAH
              </Link>
              <nav className="flex gap-3 text-muted">
                <Link href="/" className="hover:text-fg">
                  Home
                </Link>
                <Link href="/labs" className="hover:text-fg">
                  Labs
                </Link>
                <Link href="/concepts" className="hover:text-fg">
                  Learn
                </Link>
                <Link href="/settings" className="hover:text-fg">
                  Settings
                </Link>
              </nav>
              <span className="ml-auto text-xs text-muted">Damn Vulnerable Agent Harness</span>
            </header>
            <main className="min-h-0 flex-1 overflow-auto">{children}</main>
            <footer className="flex items-center justify-between border-t border-border bg-panel px-4 py-1.5 text-xs text-muted">
              <span>DVAH — Damn Vulnerable Agent Harness</span>
              <span>
                Built by{" "}
                <a
                  href="https://avishay.co.il"
                  target="_blank"
                  rel="noreferrer"
                  className="text-accent hover:underline"
                >
                  Avishay Bar
                </a>
              </span>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
