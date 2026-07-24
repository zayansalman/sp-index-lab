/* ================================================================
   Route template -- subtle enter transition between pages
   (landing ↔ lab). template.tsx remounts on every navigation, so the
   CSS enter animation re-runs on each route change.

   Robustness note: the animation is purely additive. The element's
   resting opacity is 1 (visible), and `.page-enter` only overrides it
   for the brief fade-up. If the animation never plays (JS disabled,
   throttled rAF, an old engine), the content is still fully visible —
   unlike a JS wrapper that parks the page at opacity 0 until an effect
   runs. Reduced-motion is handled centrally by the
   prefers-reduced-motion block in globals.css, which collapses this
   animation to an instant, motionless reveal.
   ================================================================ */

export default function Template({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="page-enter">{children}</div>;
}
