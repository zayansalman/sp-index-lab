import type { Metadata } from "next";
import { Space_Grotesk, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

/* ──────────────────────────────────────────────────────────────
   Font configuration
   - Space Grotesk : headings & display text
   - Geist Sans    : body / UI text
   - Geist Mono    : code, numbers, data labels
   ────────────────────────────────────────────────────────────── */

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

/* ──────────────────────────────────────────────────────────────
   Metadata & Open Graph
   ────────────────────────────────────────────────────────────── */

export const metadata: Metadata = {
  // Resolves relative asset URLs (e.g. the generated opengraph-image) to
  // absolute ones for crawlers. Uses the Vercel deployment URL in prod and
  // falls back to localhost in dev, so no domain is hardcoded.
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ??
      (process.env.VERCEL_URL
        ? `https://${process.env.VERCEL_URL}`
        : "http://localhost:3000"),
  ),
  title: "S&P Index Lab",
  description:
    "Proving the S&P 500 is driven by ~20 stocks. An interactive analytics platform that deconstructs index concentration, builds point-in-time mirror indices, and compares four portfolios side by side under a pre-registered holdout.",
  keywords: [
    "S&P 500",
    "index concentration",
    "portfolio analytics",
    "variance decomposition",
    "mirror index",
    "alpha optimization",
    "market concentration",
  ],
  authors: [{ name: "S&P Index Lab" }],
  // Metadata is static at build time — keep descriptions qualitative so
  // they can't contradict the daily-refreshed data.
  openGraph: {
    title: "S&P Index Lab",
    description:
      "A handful of stocks explain the vast majority of S&P 500 variance. Explore the concentration thesis with point-in-time Mirror, Equal, and SP-N Alpha portfolios.",
    siteName: "S&P Index Lab",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "S&P Index Lab",
    description:
      "A handful of stocks explain the vast majority of S&P 500 variance. Explore the concentration thesis with interactive analytics.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

/* ──────────────────────────────────────────────────────────────
   Root Layout
   ────────────────────────────────────────────────────────────── */

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${spaceGrotesk.variable} ${geistSans.variable} ${geistMono.variable} antialiased bg-ground text-ink`}
      >
        {children}
      </body>
    </html>
  );
}
