import { ImageResponse } from "next/og";

/* ================================================================
   opengraph-image -- 1200×630 social card
   Generated at build time via next/og (Satori). Next.js auto-injects
   the resulting og:image / twitter:image meta tags from this file
   convention, so no manual metadata.openGraph.images entry is needed
   (adding one would duplicate the tag). Kept qualitative so it never
   contradicts the daily-refreshed numbers.
   ================================================================ */

export const alt =
  "S&P Index Lab — the S&P 500 is effectively a ~20-stock index";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

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
          padding: "80px",
          backgroundColor: "#0A0A0F",
          backgroundImage:
            "radial-gradient(ellipse 70% 60% at 50% 40%, rgba(0,212,170,0.10) 0%, transparent 70%)",
          fontFamily: "sans-serif",
        }}
      >
        {/* Eyebrow */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            color: "#00D4AA",
            fontSize: 26,
            fontWeight: 700,
            letterSpacing: "0.28em",
            textTransform: "uppercase",
          }}
        >
          S&P Index Lab
        </div>

        {/* Headline */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              display: "flex",
              color: "#F0F0F0",
              fontSize: 76,
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: "-0.02em",
            }}
          >
            The S&P 500 is effectively
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 76,
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: "-0.02em",
            }}
          >
            <span style={{ color: "#F0F0F0" }}>a&nbsp;</span>
            <span style={{ color: "#00D4AA" }}>~20-stock&nbsp;</span>
            <span style={{ color: "#F0F0F0" }}>index.</span>
          </div>
        </div>

        {/* Stat chips */}
        <div style={{ display: "flex", alignItems: "center" }}>
          {[
            { label: "R-squared ~95%", accent: "#00D4AA" },
            { label: "20 stocks", accent: "#FFD700" },
            { label: "Point-in-time, net of costs", accent: "#6366F1" },
          ].map((chip) => (
            <div
              key={chip.label}
              style={{
                display: "flex",
                alignItems: "center",
                marginRight: 20,
                padding: "12px 24px",
                borderRadius: 999,
                border: "1px solid #2A2A35",
                backgroundColor: "#111118",
                color: "#F0F0F0",
                fontSize: 28,
                fontWeight: 600,
              }}
            >
              <div
                style={{
                  display: "flex",
                  width: 12,
                  height: 12,
                  borderRadius: 999,
                  marginRight: 14,
                  backgroundColor: chip.accent,
                }}
              />
              {chip.label}
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size },
  );
}
