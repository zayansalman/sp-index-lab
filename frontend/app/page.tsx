import Hero from "@/components/landing/Hero";
import StatsPreview from "@/components/landing/StatsPreview";
import EnterButton from "@/components/landing/EnterButton";

/* ================================================================
   Landing Page
   Dark, cinematic, minimal page that introduces the thesis.
   Assembles Hero, StatsPreview, and EnterButton over a subtle
   grid-patterned background with a radial accent glow.
   ================================================================ */

export default function Home() {
  return (
    <main
      className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-bg-primary"
      style={{
        backgroundImage: [
          /* Radial green glow in the centre for depth */
          "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(0, 212, 170, 0.03) 0%, transparent 70%)",
          /* Subtle grid pattern using repeating linear gradients */
          "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px)",
          "linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)",
        ].join(", "),
        backgroundSize: "100% 100%, 60px 60px, 60px 60px",
      }}
    >
      {/* ── Hero Section ──────────────────────────────────────── */}
      <Hero />

      {/* ── Stats Preview Cards ───────────────────────────────── */}
      <div className="mt-16">
        <StatsPreview />
      </div>

      {/* ── CTA Button ────────────────────────────────────────── */}
      <div className="mt-12">
        <EnterButton />
      </div>

      {/* ── Footer Attribution ────────────────────────────────── */}
      <p className="absolute bottom-8 text-xs text-text-muted">
        Built by Zayan Khan
      </p>
    </main>
  );
}
