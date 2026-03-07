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
  title: "S&P Index Lab",
  description:
    "Proving the S&P 500 is driven by ~20 stocks. An interactive analytics platform that deconstructs index concentration, builds mirror indices, and optimizes alpha with machine learning.",
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
  openGraph: {
    title: "S&P Index Lab",
    description:
      "20 stocks explain 94.9% of S&P 500 variance. Explore the concentration thesis with interactive analytics and AI-optimized indices.",
    siteName: "S&P Index Lab",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "S&P Index Lab",
    description:
      "20 stocks explain 94.9% of S&P 500 variance. Explore the concentration thesis with interactive analytics.",
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
    <html lang="en" className="dark">
      <body
        className={`${spaceGrotesk.variable} ${geistSans.variable} ${geistMono.variable} antialiased bg-bg-primary text-text-primary`}
      >
        {children}
      </body>
    </html>
  );
}
