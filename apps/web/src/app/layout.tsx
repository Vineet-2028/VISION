import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "VISION · More context. Less noise.",
  description:
    "A local research prototype for assistive scene understanding. Explore Guardian, its privacy boundaries and its limitations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#content">
          Skip to content
        </a>
        <header className="site-header">
          <Link className="wordmark" href="/">
            ◉{" "}
            <span>
              Vision<small>by Sentinel</small>
            </span>
          </Link>
          <nav aria-label="Main navigation">
            {["demo", "how-it-works", "privacy", "get-vision"].map((route) => (
              <Link key={route} href={`/${route}`}>
                {
                  {
                    demo: "Explore",
                    "how-it-works": "How it works",
                    privacy: "Privacy",
                    "get-vision": "Test VISION",
                  }[route]
                }
              </Link>
            ))}
          </nav>
          <span className="local-badge">Research Alpha</span>
        </header>
        <div id="content">{children}</div>
        <footer>
          <span>
            VISION / Sentinel · Assistive understanding, under evaluation.
          </span>
          <nav aria-label="Footer">
            <Link href="/limitations">Limitations</Link>{" "}
            <Link href="/technology">Technology</Link>{" "}
            <Link href="/research">Research</Link>
          </nav>
        </footer>
      </body>
    </html>
  );
}
