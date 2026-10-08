# StoreLab Frontend — Design System

Single source of truth for the frontend rewrite. Every color, font, spacing,
radius, shadow, and animation in the app traces back to a token here. Mode:
**preserve** — this reuses `founder/brand.md` as-is; nothing in the visual
layer was redesigned.

## Visual thesis

> A light, paper-and-ink instrument panel — Inter for scanable UI text, Space
> Grotesk for headlines and the numbers that matter, a disciplined 4px
> spacing scale with dashboard density (not luxury air), flat bordered
> components with small consistent radii and one named exception (the
> existing topbar glass panel), where Insight blue marks data/links, Proof
> green marks only validated wins, and Amber/Red mark only risk — color as a
> confidence signal, never decoration.

**Allowed patterns:** topbar glassmorphism panel (`backdrop-filter: blur`,
existing), the perpetual loading spinner (0.8s linear infinite, functional),
em dash in body copy (existing voice).

**Mood:** plain, honest, precise, grounded, instrumented. Derived from
`brand.md`'s voice table (plain/honest/practical) plus the rule that color
always pairs with an icon + label. "Instrumented" comes from the product's
own differentiation (`founder/competitors.md`): StoreLab's edge is reading
real camera/POS data and giving a trustworthy number before anyone touches a
shelf — the opposite of the glossy VR-simulation look a direct competitor
(the Australian "StoreLab™") already occupies. Avoid that look entirely.

## Interaction thesis

> Fast, dry UI feedback (140ms ease-out, no bounce or elastic) with subtle
> border/background hover states and zero scroll-triggered reveals or
> parallax; state transitions that carry real meaning (a simulation result
> landing, a screen change) get a slightly longer 320ms ease-out cross-fade;
> the Three.js Store scene moves only on user input (drag-to-orbit) or real
> data (shopper trajectories replayed at their true 2Hz pace), never an
> auto-rotating showroom sweep.

**Allowed patterns:** the existing perpetual spinner, loading only.

**Forbidden patterns:** spring/bounce/elastic easing, scroll-triggered
stagger reveals, scale-on-hover, auto-rotating camera, confetti/celebration
flourishes on a "win" (a win is shown with a clear number, not a party —
this is a trust-weighted product, not a consumer app).

## Dials

| Dial | Value | From |
|---|---|---|
| `--variance` | 2/10 | Visual thesis: flat, bordered, small consistent radii — centered/minimal end |
| `--motion` | 2/10 | Interaction thesis: "fast and dry... no bounce... zero scroll reveals" |
| `--density` | 7/10 | Visual thesis: "dashboard density, not luxury air" |

## Tokens

Source of truth: [`src/styles/tokens.css`](src/styles/tokens.css) — CSS
custom properties, light + dark (the existing app had both; preserve mode
keeps them). [`src/theme/tokens.ts`](src/theme/tokens.ts) reads these live
via `getComputedStyle` for the one place that can't use `var()`: Three.js
materials/lights, which need resolved values. No second copy of the
palette to drift — the CSS file is the only place colors are written down.

### Color

| Token | Light | Role |
|---|---|---|
| `--color-ink` | `#0B0B0B` | Headlines, primary buttons, body text |
| `--color-paper` | `#F6F5F1` | Page background |
| `--color-surface` / `-2` / `-3` | `#FCFCFB` / `#F1F0EB` / `#E7E6E0` | Card/panel backgrounds, nested by elevation |
| `--color-insight` | `#2A78D6` | Links, data highlights, the "insight" aisle |
| `--color-proof` | `#0CA30C` (text: `#006300`) | Recommended / validated wins only |
| `--color-amber` | `#FAB219` | Risk — always with icon + label |
| `--color-red` | `#D03B3B` | Constraint breach — always with icon + label |
| `--color-change` | `#EB6834` | What an experiment changes — distinct from the four semantic colors above |
| `--color-ink-muted` / `--color-subtle` / `--color-axis` | secondary/tertiary text, hairline strokes |
| `--color-*-wash` (insight/proof/amber/red/change) | tinted backgrounds for badges/chips, always paired with an icon + label, never the color alone |

Dark mode mirrors every token (see the `prefers-color-scheme: dark` block
and `[data-theme="dark"]` override in `tokens.css`) — this was already a
real feature of the existing app, not a new addition.

**Store floorplan tokens** (for the Three.js scene, stage 2): `--color-floor`,
`--color-zone`, `--color-fixture`, `--color-particle-buyer` /
`-particle-browser`, and the 7-step `--color-heat-0`…`-6` heatmap scale —
all carried over from the existing canvas floorplan's palette.

Color is a confidence signal, not decoration: never introduce a new color
for visual variety. New states reuse these tokens or an explicitly-approved
tint of them.

### Typography

- **Body/UI**: Inter — `--font-body`
- **Display/headlines/decision-critical numbers** (uplift %, budget,
  confidence): Space Grotesk — `--font-display`
- **Data/code**: `ui-monospace` stack — `--font-mono`
- Scale: `--text-xs` 12px → `--text-2xl` 36px, moderate contrast — this is a
  scanned dashboard, not an editorial page.
- Bold (`--weight-bold`) is reserved for decision-critical numbers, never
  used decoratively.

### Spacing

4px base: `--space-1` (4px) through `--space-16` (64px). Dense enough to
respect the amount of real data on screen (fixtures, metrics, heatmaps)
without feeling cramped.

### Radii

`--radius-none` (0, flat elements like table rows) · `--radius-sm` (6px,
inputs/chips) · `--radius-md` (10px, buttons) · `--radius-lg` (14px,
cards/panels — the existing app's one radius, kept) · `--radius-pill`
(999px, badges/segmented controls) · `--radius-circle` (50%,
avatars/dots/spinner).

### Shadows

`--shadow-none` (default — flat, bordered) · `--shadow-overlay` (cards and
overlays; `none` in dark mode, matching the existing app — dark surfaces
read their elevation from surface-color contrast, not shadow).

### Motion

`--duration-micro` 140ms / `--duration-meaningful` 320ms, both
`--ease-standard` (`cubic-bezier(0.4, 0, 0.2, 1)`). `--duration-spin` 0.8s
linear, the one perpetual exception (loading only). All durations collapse
to 0ms under `prefers-reduced-motion: reduce`.

## Base components

Styled per the tokens above as they're built; no component ships a color,
radius, spacing, or shadow value that isn't one of these tokens. Every
interactive element implements the 5 states: default, hover, focus, active,
disabled.

## Stack

React + Vite + TypeScript. Three.js is vanilla (not react-three-fiber),
mounted inside one lifecycle-managed wrapper component per the Store screen's
needs — see that screen's own notes when built. API calls go through a typed
client generated from the backend's OpenAPI schema (`src/api/schema.d.ts`,
regenerate with `npx openapi-typescript openapi.schema.json -o src/api/schema.d.ts`
after dumping a fresh schema from `storelab.main.app.openapi()`).
