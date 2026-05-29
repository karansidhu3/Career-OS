# Design Doctrine

A reusable product identity and design language.
Applies to CareerOS, MarketMind, Folio, and all future products.

Last updated: 2026-05-28

---

## Core Philosophy

These products are personal tools. Personal tools are fundamentally different from enterprise software.

Enterprise software hedges — it shows all options, labels everything, requires the user to understand its structure before using it. It is built for committees and evaluated by procurement teams.

Personal tools are decisive. They know who they're for. They know what the user needs to do next. They don't compete for attention with their own content. They feel like they were made by a person, for a person.

**The goal:** Calm intelligence. The product should feel like a quiet, capable collaborator — not a dashboard, not a service, not an app. A workspace that already knows you.

**The test:** Would someone who uses three different products built on this doctrine recognize them as coming from the same maker? Not because of shared colors, but because of shared values: restraint, precision, motion that communicates, hierarchy that guides.

---

## Product Principles

**1. The signal is always the hero.**
Every product produces a primary output — a score, a result, a status, an answer. That output is the largest, most visually prominent element in its view. It is never treated as metadata.

**2. One primary action per screen.**
Each screen knows what the user should do next and presents that action clearly. Secondary and tertiary actions are visually subordinate. The product has an opinion — it does not present three equal-weight options and ask the user to choose.

**3. Progressive disclosure.**
Show what the user needs right now. Everything else is available but not visible. Reference material is collapsed. History is behind a drawer. Secondary options are ghost buttons or toggles. Cognitive load matches intent.

**4. Restraint is confidence.**
The decision to remove an element is a design decision. The products are confident enough to leave things out. An interface that shows everything communicates anxiety. An interface that shows precisely what matters communicates trust.

**5. The reading experience is a product feature.**
When the product produces prose — a letter, a summary, a recommendation — that prose is rendered like writing, not data. Correct line length. Generous line height. No competition from surrounding UI.

**6. The product knows you.**
Personal tools carry context. The experience should feel continuous — not like opening a new session, but returning to a workspace that has been quietly maintaining itself in your absence.

---

## Visual Language

### Typography

**The scale communicates hierarchy before content does.**

| Role | Size | Weight | Tracking | Line Height |
|------|------|--------|----------|-------------|
| Display (signal hero) | 4–5rem | 700 | −0.04em | 1.0 |
| Title | 1.75rem | 600 | −0.025em | 1.2 |
| Body | 0.9375rem (15px) | 400 | 0 | 1.75 |
| Small / metadata | 0.8125rem (13px) | 400 | 0 | 1.5 |
| Label (section) | 0.6875rem (11px) | 500 | +0.07em + uppercase | — |
| Mono | 0.75rem (12px) | 400 | 0 | 1.6 |

**Principles:**
- Use system fonts (`system-ui, -apple-system`). Native rendering is faster and matches the "personal tool" register. Add `'Inter'` as a fallback for non-Apple platforms.
- The gap between the largest and smallest type creates hierarchy. Don't compress the scale.
- Section labels (`SectionLabel` component) are always 11px, uppercase, tracked. They whisper a category — they don't announce a heading.

### Spacing

Base unit: 4px. All spacing is a multiple.

```
4   — tight pairs (icon + label)
8   — internal component gaps
12  — metadata, secondary spacing
16  — between components
20  — card padding (compact)
24  — card padding (standard)
32  — section gaps (within a screen)
40  — major section separation
56  — screen-level breathing room
80  — between major thematic sections
```

More space than you think you need. Then add more. Whitespace is structural.

### Color

**One accent. Three semantics. Everything else is neutral.**

- **Accent** (`--c-accent`): Used for primary actions, interactive affordances, the brand mark. Not for decoration. One color carries this role — changing it is a product-level decision, not a style choice.
- **Success** (`--c-success`, dim, border variants): Achieved states, positive results, "applied" status.
- **Warn** (`--c-warn`, dim, border): Active milestone states — interview, offer, flagged items. Amber. Used sparingly: when it appears, it means something.
- **Danger** (`--c-danger`, dim, border): Destructive actions, errors, failed states.
- **Neutrals**: Do all structural work. The Tailwind neutral scale is overridden in dark mode so all `text-neutral-*` utilities adapt automatically.

**Color encodes meaning, not variety.** If a color appears somewhere new, it should be because that thing has the same semantic weight as the other places that color appears.

### Surfaces

Three levels of surface elevation:

```
--c-surface         — standard cards, input backgrounds
--c-surface-raised  — navbar, drawers, floating panels
--c-surface-overlay — any true overlay (rare)
```

Surfaces are translucent with backdrop blur — they feel like materials (frosted glass, paper) rather than painted rectangles. The background atmospheric depth (`body::before` gradient) is always visible beneath them.

Shadows are asymmetric and grounded — more shadow at bottom than sides. Two levels: `--c-shadow-sm` (subtle lift) and `--c-shadow-md` (elevated surface).

---

## Motion Language

**Motion is communication. If an animation doesn't answer a question, remove it.**

### Spring System

Use spring physics exclusively. Springs have weight, momentum, and natural settling. They feel physical. Ease curves feel like software.

```ts
// lib/motion.ts
export const spring = {
  standard: { type: 'spring', stiffness: 320, damping: 30 }, // cards, sections, drawers
  gentle:   { type: 'spring', stiffness: 180, damping: 26 }, // page transitions, large reveals
  snappy:   { type: 'spring', stiffness: 520, damping: 32 }, // micro-interactions, toggles
  bouncy:   { type: 'spring', stiffness: 420, damping: 14 }, // celebration moments only
}
```

### Patterns

**Entry** — Elements rise from below: `y: 16 → 0, opacity: 0 → 1`. Not from the side, not from far below. A small, grounded rise. `spring.gentle`.

**Stagger** — Lists and grouped content reveal with `staggerChildren: 0.04–0.06`. Hierarchy communicated through sequence, not labels.

**Count-up** — Numeric outputs (scores, totals, results) count up from zero to their final value over ~600ms. This communicates: *calculated, not fetched.*

**Ring sweep** — Score ring arcs animate from 0 to final fill on mount. Same signal as count-up.

**Press response** — Every interactive element responds to press with `scale: 0.97`. Immediate. Physical.

**Hover lift** — Tappable cards and rows lift `y: -2` with shadow deepening. Confirms interactivity.

**Celebration** — Milestone moments (a goal achieved, a status advanced) get `spring.bouncy` — a single visual element blooms with slight overshoot. One piano note, not a fanfare.

**What motion never does:**
- Animate for longer than 500ms on anything the user is waiting on
- Apply `bounce`, `wiggle`, or `pulse` as decorative patterns
- Slide page transitions horizontally — pages enter from below

---

## Layout Patterns

### Single Column of Attention

Primary content lives in a single, centered column. The user reads one thing, then the next. There are no competing columns of information for primary content.

The content max-width depends on content type:
- Prose-heavy products: `680px` (≈65ch at 15px — optimal reading width)
- Data-adjacent products: up to `896px`

The max-width is a hard constraint, not a guideline.

### Page Structure

Vertical reading order maps to information hierarchy:

1. **What is this?** — Title, immediately, large
2. **What does it mean for me?** — Primary signal (the hero)
3. **What should I do?** — Primary action, clear, single
4. **What else do I need?** — Supporting content
5. **What is the reference material?** — Collapsed, reachable on demand

No screen inverts this order.

### Desktop Expansion

When a screen has a primary signal and a primary reading body (e.g., a score and a document), use a two-column layout on `md:` and above:

- Left (~38%): signal, primary actions, status controls
- Right (~62%): reading content, prose

This keeps the most important information and the most important action both visible while reading. On mobile, single column: signal first, then action, then reading.

### Page Padding

- Mobile: `24px` horizontal
- Desktop: `32px` horizontal
- Navbar max-width: slightly wider than content column (frames without constraining)

---

## Interaction Patterns

### Primary Actions

One per screen. Use the full primary button style (gradient background, drop shadow). Named specifically — not "Submit" but "Generate", not "OK" but "Mark as Applied". The name matches the outcome.

### Secondary Actions

Visually subordinate to the primary. Surface background + border. Lower type weight. Located below or beside the primary, never above.

### Ghost / Tertiary Actions

No background, no border in resting state. Used for: cancel, collapse, show more, skip, rare administrative actions. Ghost actions should not compete with the primary.

### Progressive Disclosure

Default to the minimum necessary view. Secondary content (source material, reference data, advanced options) is reachable via toggle — collapsed by default, smooth spring expansion.

The toggle affordance should be a ghost action. The collapse/expand itself should use a rotating chevron icon, not separate icons.

### Editing Philosophy

When the user wants to change something, they click on it and change it — not navigate to an edit page. Not open a modal. The save is automatic or triggered by leaving the field.

For structured content (cards with many fields), an edit mode toggle within the card is acceptable. The key principle: editing happens in context, not in a separate view.

### Destructive Confirmations

Destructive actions (delete, discard, clear) use an inline two-step confirmation. First click: the button transforms to "Confirm delete?" with a Cancel option. No browser `confirm()` dialogs. No modals.

The two-step pattern communicates gravity without interrupting the workspace.

### Loading States

Loading states communicate what is happening, not just that something is happening.

- **Under 300ms**: No indicator. Show the result.
- **300ms – 2s**: A spinner. Use the accent-colored ring pattern.
- **Over 2s**: A purposeful loading state with contextual messages that communicate the process (e.g., "Reading the job description… Scoring fit… Writing your resume…").

Do not use skeleton loaders. They predict content shape without communicating progress.

---

## Navigation Philosophy

Navigation should be peripheral, not central. The user should almost never think about navigation — they should be focused on the work.

### The Floating Pill

Navigation lives in a floating pill, centered at the top of the viewport. It is:
- Translucent with backdrop blur (frosted glass)
- Bordered with a single-pixel surface border
- Fixed position — content scrolls beneath it
- Pill-shaped (`rounded-2xl`)

The pill does not take up layout space. It floats above the content.

### Pill Contents

- **Left**: Brand mark + wordmark, linking to the primary surface
- **Right**: Maximum two icon buttons

Icons only. No labels. If an icon's meaning isn't obvious after the first use, it should be reconsidered. Icons should communicate their destination, not their mechanism. A list icon communicates "archive" better than a clock icon communicates "history."

### The Active Indicator

When there is something awaiting attention (a milestone reached, an active status), a single 4px dot appears on the relevant icon. Not a count, not a badge — a dot. The user decides when to look.

### Maximum Destinations

At any time, the product navigates to at most 3 destinations: the primary surface (via wordmark), and at most 2 secondary surfaces (via icon buttons). More destinations is a signal to simplify the information architecture, not to add navigation items.

### No Sidebars

Sidebars communicate that the product has structure complex enough to require a permanent map. Products built on this doctrine are simple enough not to need one. If a sidebar feels necessary, the product has too many features or a poorly designed information architecture — not a navigation problem.

---

## Recognizable Traits

A product built on this doctrine is recognizable within 10 seconds by seven things:

1. **The floating pill navbar** — not a header, not a sidebar. Centered, frosted, two icons.
2. **The large primary signal** — whatever the product's main output is, it is larger than most products would dare.
3. **The bounded content column** — the content never stretches to the viewport edge. There is a measured column with significant breathing room on either side.
4. **The atmospheric background** — a subtle radial depth, not a flat color. The background has air.
5. **The typography range** — from very large (the hero) to very small (11px uppercase labels). The dramatic scale communicates hierarchy before content does.
6. **The spring motion** — elements rise into place, settle with slight deceleration, press with physical response. The product has weight.
7. **The restraint** — no status badges on every item, no notification bells, no competing calls to action. Every element that remains is deliberate.

---

## Anti-Patterns

These patterns appear frequently in software and consistently degrade the personal tool experience. When the instinct to use them arises, ask what the pattern is compensating for — the answer usually reveals a better solution.

### Dashboard Grids of Equal-Weight Cards

Presents all information as simultaneously important. The eye has no hierarchy to follow. Better: identify what matters most and give it visual dominance. Use progressive disclosure for secondary information.

### Status Badges on Every Item

When everything has a badge, nothing communicates status. Badges used throughout a list become visual noise and lose their semantic function. Better: use a single status indicator per item (a dot, a color on the title, a muted label) and reserve distinct visual treatment for exceptional states.

### Full-Width Submit Buttons

Communicates "form step" rather than "workspace action." Better: proportional buttons positioned with intent — right-aligned to close a flow, centered for invitations, inline for contextual actions.

### Generic Icon Choices

Clock for history, bell for notifications, gear for settings. These are so universal they carry no identity. Better: choose icons for semantic fit with the specific product context. Consider custom SVG marks where the meaning is product-specific.

### Exposing Internal States to Users

Showing system states (processing, generated, queued) in user-facing filter or status UI. Users think in their own mental models, not the product's data model. Better: translate internal states to user-meaningful language, or collapse them into broader categories.

### Native Browser Dialogs (`confirm()`, `alert()`)

Interrupts the product's visual language with the OS's visual language. Communicates a lack of craft. Better: inline confirmation states that use the product's own typography and spacing.

### Skeleton Loaders

Predict content shape rather than communicating progress. Often wrong. Communicate "I don't know when this will be ready" rather than "this is what's happening." Better: purposeful loading states with contextual messages.

### Decorative Motion

Animations without semantic purpose. Hovers that pulse, transitions that bounce for visual delight, loading spinners that have elaborate choreography. Motion costs attention. If it doesn't communicate something, it costs more than it gives.

---

*This document is a living reference, updated when product decisions reveal new patterns or refine existing ones. It is not a rulebook — it is a set of values made concrete.*
