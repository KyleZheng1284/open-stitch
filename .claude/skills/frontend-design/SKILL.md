---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, or applications. Generates creative, polished code that avoids generic AI aesthetics.
license: Complete terms in LICENSE.txt
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

---

## Project: Open-Stitch (Auto-Vid)

An AI-powered short-form video editor. The frontend is a **dark, tool-grade editor UI** — think DaVinci Resolve meets a node-based AI pipeline dashboard. Users upload footage, describe a style, watch the agentic pipeline run on a React Flow canvas, then accept/publish clips.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 15 (App Router), React 19 |
| Language | TypeScript (strict) |
| Styling | Tailwind CSS v4 (`@tailwindcss/postcss`) |
| Canvas | `@xyflow/react` v12 (React Flow) |
| Drag & Drop | `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities` |
| Video | `remotion`, `@remotion/player`, `@remotion/renderer`, `@remotion/cli` |
| State | Custom hooks (`useProjectState`, `useWebSocket`) |
| API | REST via `src/lib/api.ts`, WebSocket for real-time agent updates |

### File Structure for New Components

```
frontend/src/
  app/                   # Next.js App Router pages
  components/
    canvas/              # React Flow nodes and canvas panel
    sidebar/             # Upload, video list, style prompt, clip previews
    common/              # StatusDot, ProgressBadge, shared primitives
    traces/              # Phoenix observability embed
  hooks/                 # useProjectState, useWebSocket
  lib/                   # api.ts (REST client), sync.ts
```

New components go in the appropriate subfolder. All files must include `"use client"` if they use hooks or interactivity.

---

## Design System

### Color Tokens (tailwind.config.ts)

Always use the project's semantic tokens — never raw hex values:

```
canvas.bg       = #0f1117   (page background)
canvas.surface  = #1a1d27   (panels, cards, nodes)
canvas.border   = #2a2d3a   (borders, dividers)
canvas.accent   = #3b82f6   (primary blue, handles, links)

status.idle     = #6b7280   (gray)
status.running  = #3b82f6   (blue, matches accent)
status.success  = #22c55e   (green)
status.error    = #ef4444   (red)
status.warning  = #f59e0b   (amber)
```

### Animations

Two project-defined keyframes are available:

```
animate-pulse-border   — border pulses blue (running state on agent nodes)
animate-flow-dot       — dot travels along a path (offset-distance, for edge animations)
```

For new animations: prefer CSS-only via Tailwind `keyframes` extensions or inline `style` props. There is no Motion library installed — do not import `framer-motion` or `motion`.

### Established Patterns

- **Layout**: Fixed 48px header + `flex h-screen`. Sidebar is `w-80 min-w-72`. Canvas is `flex-1`.
- **Surfaces**: Panels use `bg-canvas-surface border border-canvas-border`.
- **Nodes (React Flow)**: `border-2 border-canvas-border rounded-lg bg-canvas-surface`, accent handles `!bg-canvas-accent`. Status borders override with `border-blue-500`, `border-green-500`, `border-red-500`.
- **Text scale**: Headings `text-sm font-bold tracking-wide`, labels `text-xs`, metadata `text-[10px] text-gray-400`.
- **Transitions**: `transition-colors` on hover. Keep transitions short (150–200ms).
- **Status indicators**: Use `StatusDot` from `@/components/common/StatusDot` — do not reinvent inline.
- **Dark mode**: The app is dark-only. `darkMode: "class"` is configured but the root layout always sets the dark class. Do not add light-mode variants.

---

## Design Thinking

Before coding, understand the context and commit to a **BOLD aesthetic direction**:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: For this project the baseline is **industrial/utilitarian dark tool** — like a professional NLE or node compositor. Extensions should feel *native* to this aesthetic. When building new pages or standalone components, you may deviate — but they must still feel like they belong to a serious creative tool, not a marketing site.
- **Constraints**: Must work within the existing Tailwind token system. New tokens may be added to `tailwind.config.ts` if justified.
- **Differentiation**: What makes this component UNFORGETTABLE within the editor context?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. For this project that means: purposeful density, information hierarchy at a glance, live/reactive states that feel alive, and zero decorative noise.

Then implement working code that is:
- Production-grade and functional (typed, no `any` unless unavoidable)
- Visually striking and memorable within the tool aesthetic
- Cohesive with the existing dark canvas design language
- Meticulously refined in every detail

---

## Frontend Aesthetics Guidelines

Focus on:

- **Typography**: Avoid generic fonts (Inter, Roboto, Arial, system-ui). For this project's tool chrome, monospace-adjacent or condensed grotesque fonts work well. Display elements (clip titles, agent names) can use something more expressive. Pair a distinctive display font with a refined body font.
- **Color & Theme**: Extend the existing canvas/status token system. Dominant dark surfaces with sharp blue accents. Status colors are semantic — never repurpose them decoratively.
- **Motion**: Use animations for purposeful feedback only (running states, transitions, reveals). No idle/ambient animations that distract from the editor workflow. One well-orchestrated state transition is better than scattered micro-interactions. CSS Tailwind keyframes only — no external animation libraries.
- **Spatial Composition**: The main layout is fixed (sidebar/canvas split). Within panels, prefer controlled density: compact rows for lists, generous space for interactive zones (upload, preview). Avoid excessive padding that wastes editor real estate.
- **Backgrounds & Visual Details**: Stick to the dark palette. Subtle `bg-gradient-to-b` or `bg-[radial-gradient(...)]` can add depth to panels. Avoid noise textures or decorative gradients on the canvas itself — the React Flow graph is the visual hero.

NEVER use:
- Generic AI-generated aesthetics (purple gradients, glassy cards on white)
- Overused font families (Inter, Space Grotesk, Roboto)
- Cookie-cutter component patterns that don't match the editor context
- Light mode or mixed-theme elements

**IMPORTANT**: Match implementation complexity to the vision. This is a professional tool UI — elegance comes from precision, information density, and reactive states, not decorative excess.

---

## React Flow / Canvas-Specific Rules

- Always wrap canvas components in `ReactFlowProvider` (done at the page level — do not add a second provider)
- Custom node components receive `NodeProps` from `@xyflow/react`; cast `data` to a typed interface
- Handles use `!bg-canvas-accent` to override React Flow's default handle styles
- Node status classes follow the `statusColors` map pattern from `AgentNode.tsx`
- Edge styles should use `stroke: canvas.accent` / `stroke-width: 1.5` for consistency
- Do not use `useReactFlow` outside of a `ReactFlowProvider` subtree

## dnd-kit / Sortable-Specific Rules

- Use `@dnd-kit/sortable` for ordered video lists
- Drag handles should be visually obvious (grip icon, cursor-grab)
- During drag, apply `opacity-50` or a scale transform to the dragged item
- Use `arrayMove` from `@dnd-kit/sortable` for reorder logic

## API & State Rules

- All backend calls go through `src/lib/api.ts` — never call `fetch` directly in components
- Real-time agent state comes from `useWebSocket(jobId)` — do not open raw WebSockets
- Project state (videos, clips, stylePrompt, actions) comes from `useProjectState()`
- Components receive state/callbacks as props; keep hooks at the page level

---

Remember: Claude is capable of extraordinary creative work within constraints. The best tool UIs are not plain — they are precise, expressive, and feel purpose-built. Execute every detail with intentionality.
