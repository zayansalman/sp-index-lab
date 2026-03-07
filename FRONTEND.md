# S&P Index Lab — Frontend Specification

## Overview
The frontend is a Next.js 16 static site that visualizes the S&P 500 concentration thesis through an interactive machine metaphor. Users flip a switch to "start" an analysis engine that sequentially activates SVG components, each representing a real part of the analytics pipeline. Results appear as charts, metrics, and data tables after the machine completes.

## Tech Stack
| Tool | Version | Purpose |
|------|---------|---------|
| Next.js | 16.1.6 | React framework, App Router |
| React | 19.2.3 | UI components |
| TypeScript | 5.x | Strict type safety |
| Tailwind CSS | 4.x | `@theme inline` syntax, custom dark tokens |
| Framer Motion | 12.35+ | Animations, spring physics, AnimatePresence |
| Recharts | 3.8+ | Line, area, bar charts |
| @radix-ui/react-tooltip | 1.2.8 | Accessible tooltips |
| clsx + tailwind-merge | latest | Class composition |

## Architecture
```
frontend/
├── app/
│   ├── layout.tsx         # Root: fonts (Space Grotesk, Geist), metadata, dark theme
│   ├── page.tsx           # Landing page (/)
│   ├── globals.css        # Tailwind config, CSS keyframes, custom properties
│   └── lab/
│       └── page.tsx       # Machine visualization (/lab)
├── components/
│   ├── landing/           # Hero, StatsPreview, EnterButton
│   ├── machine/           # MachineCanvas, FlipSwitch, Wire, ComponentNode, 5 nodes
│   ├── results/           # ResultsPanel, charts, tables, MetricCard, ThinkingPanel
│   └── ui/                # AnimatedCounter, GlowText, Tooltip
├── hooks/
│   ├── useLabData.ts      # Fetches JSON, transforms snake→camel, returns typed data
│   └── useMachineState.ts # useReducer state machine for animation sequence
├── lib/
│   ├── types.ts           # All TypeScript interfaces (LabData, MetaData, etc.)
│   ├── constants.ts       # Colors, timing, stage configs, chart colors
│   ├── tooltips.ts        # Rich tooltip content for each machine component
│   └── formatters.ts      # formatPercent, formatRatio, formatCurrency, etc.
└── public/data/           # 8 pre-computed JSON files (~200KB total)
```

## Color System
| Token | Hex | Use |
|-------|-----|-----|
| `bg.primary` | `#0A0A0F` | Page background |
| `bg.secondary` | `#111118` | Card/component background |
| `bg.tertiary` | `#1A1A24` | Nested containers |
| `accent.primary` | `#00D4AA` | Green — wires, active states, SP-20 Mirror |
| `accent.secondary` | `#FFD700` | Gold — SP-20 Equal, secondary highlights |
| `accent.tertiary` | `#6366F1` | Indigo — AI/optimizer elements |
| `text.primary` | `#F0F0F0` | Main text |
| `text.secondary` | `#888899` | Subdued text, S&P 500 chart line |
| `text.muted` | `#555566` | Disabled/placeholder |
| `wire.inactive` | `#2A2A35` | Dim wire paths |
| `wire.active` | `#00D4AA` | Energized wire paths |

## Typography
- **Space Grotesk** (400-700): Headings, display text, machine labels
- **Geist Sans**: Body text, UI elements
- **Geist Mono**: Numbers, data labels, code

## Pages

### Landing Page (`/`)
- Dark background with CSS grid pattern and radial green glow
- Hero: "S&P INDEX LAB" — Space Grotesk, uppercase, tracking-widest
- Tagline: "The S&P 500 is a 20-stock index. Here's the machine that proves it."
- 3 stat cards with staggered Framer Motion entrance:
  - R² = 94.9% (green)
  - CAGR = 15.3% (gold)
  - Alpha = +4.0% (indigo)
- CTA: "Enter the Lab →" with animated glow border
- Footer: "Built by Zayan Khan"

### Machine Lab (`/lab`)
- Header: "← Back" link + "S&P INDEX LAB" centered
- SVG machine canvas (viewBox 0 0 800 600)
- 5 machine components connected by animated wires
- Flip switch at top — toggles animation on/off
- Results panel slides in from below after machine completes

## Machine Components (SVG)
Each component is a `ComponentNode` with: rounded rectangle, icon, label, `LightBulb` indicator.

| Component | SVG Position | Icon | Tooltip ID |
|-----------|-------------|------|------------|
| Data Pipeline | Top center | Server/DB | `data-pipeline` |
| Concentration Analyzer | Center | Prism | `concentration-analyzer` |
| Mirror Index Builder | Left | Gears | `mirror-builder` |
| Alpha Optimizer | Right | Brain | `alpha-optimizer` |
| Performance Monitor | Bottom center | Gauges | `performance-monitor` |

## Wire Animation System
Three SVG layers per wire:
1. **Base**: Gray stroke (`#2A2A35`, 2px) — always visible
2. **Glow**: Accent color, `stroke-dasharray: 8 12`, animated `stroke-dashoffset`
3. **Filter**: `drop-shadow(0 0 6px rgba(0, 212, 170, 0.6))`

```css
@keyframes electricFlow {
  0%   { stroke-dashoffset: 40; }
  100% { stroke-dashoffset: 0; }
}
.wire-active {
  stroke: #00D4AA;
  stroke-dasharray: 8 12;
  animation: electricFlow 0.8s linear infinite;
  filter: drop-shadow(0 0 6px rgba(0, 212, 170, 0.6));
}
```

## Animation Sequence
The `useMachineState` hook manages a `useReducer`-based state machine:

```
IDLE → POWERING_UP → DATA_PIPELINE → CONCENTRATION → BUILDING → OPTIMIZING → MONITORING → COMPLETE
```

| Stage | Duration | Active Wires | Active Components |
|-------|----------|-------------|-------------------|
| idle | 0ms | none | none |
| powering_up | 1200ms | wire-power | power-switch |
| data_pipeline | 1500ms | +wire-data-in | +data-pipeline |
| concentration | 1500ms | +wire-concentration | +concentration-analyzer |
| building | 1500ms | +wire-builder | +mirror-builder |
| optimizing | 1500ms | +wire-optimizer | +alpha-optimizer |
| monitoring | 1500ms | +wire-monitor | +performance-monitor |
| complete | 0ms | +wire-output | all |

Toggle OFF: everything dims, results retract, state resets to IDLE.

## Tooltip System
Each machine component has a rich tooltip (Radix UI, dark styled):
- **Title** + **Subtitle**
- **Description** (1-2 sentences of what it does)
- **"The Thinking"** — methodology rationale (why this approach)
- **Key Insight** — one-line standout takeaway

Content sourced from `lib/tooltips.ts`. Positioned via HTML overlay `<div>` above the SVG canvas (Radix tooltips don't work inside `<foreignObject>`).

## Results Panel
Appears after machine `complete` stage. Framer Motion entrance animations:

1. **4 Hero Metric Cards** — R² (94.9%), CAGR (15.3%), Excess Return (+4.0%), Tracking Error (9.41%)
   - `AnimatedCounter` counts from 0 to target value
2. **Concentration Curve** (Recharts LineChart) — R² vs # stocks, annotations at N=20 and 95%
3. **Growth of $1** (Recharts LineChart) — S&P 500 (gray) vs Mirror (green) vs Equal (gold)
4. **Performance Table** — 11 metrics × 3 indices (Total Return, CAGR, Vol, Sharpe, Sortino, Max DD, Calmar, Beta, Alpha, TE, IR)
5. **Drawdown Chart** (Recharts AreaChart) — overlaid drawdown series
6. **Holdings Table** — 20 rows: rank, ticker, name, sector, weight with proportional bars
7. **"The Thinking" Panels** — 3 collapsible sections with methodology rationale

## Data Loading
The `useLabData` hook:
1. Fetches 8 JSON files from `/data/` in parallel via `Promise.all`
2. Applies 8 transform functions mapping snake_case → camelCase
3. Defensive defaults via nullish coalescing (`??`)
4. Returns `{ data: LabData | null, isLoading, error, refetch }`

JSON files (pre-computed by `scripts/export_frontend_data.py`):
- `meta.json` (1.0KB) — dates, counts, config
- `concentration_curve.json` (6.4KB) — R² curve data
- `variance_decomposition.json` (0.8KB) — per-N variance
- `performance_nav.json` (106KB) — weekly NAV series
- `performance_metrics.json` (1.4KB) — 15+ metrics × 3 indices
- `holdings.json` (3.2KB) — tickers, names, sectors, weights
- `drawdowns.json` (76KB) — weekly drawdown series
- `daily_deviations.json` (5.7KB) — histogram bins

## Responsive Design
- **Desktop (>1024px)**: Full spatial SVG machine + side-by-side results
- **Tablet (768-1024px)**: Scaled SVG (viewBox handles it), stacked results
- **Mobile (<768px)**: Simplified vertical pipeline, full-width cards

## Performance
- Static JSON (no API calls at runtime)
- Weekly downsampling reduces chart data from ~3000 to ~620 points
- Framer Motion `lazy` for below-fold components
- Recharts `isAnimationActive={false}` option for mobile
