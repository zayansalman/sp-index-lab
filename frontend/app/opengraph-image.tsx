import { ImageResponse } from "next/og";

/* ================================================================
   opengraph-image -- 1200×630 social card
   Generated at build time via next/og (Satori). Next.js auto-injects
   the resulting og:image / twitter:image meta tags from this file
   convention, so no manual metadata.openGraph.images entry is needed
   (adding one would duplicate the tag). Kept qualitative so it never
   contradicts the daily-refreshed numbers.

   Light institutional card: this is the first thing a reader sees
   when the link is pasted into a message, so it should look like the
   page it opens — a document, not a product splash.
   ================================================================ */

export const alt =
  "S&P Index Lab — the S&P 500 is effectively a ~20-stock index";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const INK = "#0B1220";
const INK_MUTED = "#5C6875";
const BORDER = "#E3E7EB";
const SURFACE = "#F4F6F8";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px 80px",
          backgroundColor: "#FFFFFF",
          fontFamily: "sans-serif",
        }}
      >
        {/* Masthead rule + eyebrow, as on a factsheet */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              borderBottom: `2px solid ${INK}`,
              paddingBottom: 18,
            }}
          >
            <div
              style={{
                display: "flex",
                color: INK,
                fontSize: 24,
                fontWeight: 700,
                letterSpacing: "0.22em",
                textTransform: "uppercase",
              }}
            >
              S&P Index Lab
            </div>
            <div style={{ display: "flex", color: INK_MUTED, fontSize: 20 }}>
              Point-in-time / net of costs / vs ^SP500TR
            </div>
          </div>
        </div>

        {/* Headline */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              display: "flex",
              color: INK,
              fontSize: 72,
              fontWeight: 600,
              lineHeight: 1.1,
              letterSpacing: "-0.025em",
            }}
          >
            The S&P 500 is effectively
          </div>
          <div
            style={{
              display: "flex",
              color: INK,
              fontSize: 72,
              fontWeight: 600,
              lineHeight: 1.1,
              letterSpacing: "-0.025em",
            }}
          >
            a ~20-stock index.
          </div>
          <div
            style={{
              display: "flex",
              color: INK_MUTED,
              fontSize: 28,
              marginTop: 20,
            }}
          >
            Four portfolios, shown side by side. None is crowned.
          </div>
        </div>

        {/* Fact chips — square, hairline, no colour dots */}
        <div style={{ display: "flex", alignItems: "center" }}>
          {[
            "R-squared ~95% at 20 stocks",
            "Pre-registered holdout",
            "No difference clears t > 3",
          ].map((label) => (
            <div
              key={label}
              style={{
                display: "flex",
                alignItems: "center",
                marginRight: 16,
                padding: "12px 22px",
                border: `1px solid ${BORDER}`,
                backgroundColor: SURFACE,
                color: INK,
                fontSize: 26,
                fontWeight: 500,
              }}
            >
              {label}
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size },
  );
}
