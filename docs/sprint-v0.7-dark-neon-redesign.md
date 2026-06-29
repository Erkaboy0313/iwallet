# Sprint v0.7 — Dark Neon Redesign

**Designer:** Sally · 2026-06-29
**Mandate from Eric (2026-06-29):** Spendly-style dark theme bilan neon emerald accent. "Hamma pagelarimiz ham shunaqa dizaynda bo'lsin, hammasi interaktiv animatsiyalar bilan."
**Replaces:** the light-mode v0.6 visual layer. URL routes, views, data model untouched.

---

## 1. Design tokens (the whole sprint rides on these)

`static/css/tokens.css` is rewritten end-to-end. Every page that already uses `var(--color-*)` auto-rebrands; hardcoded `#FFFFFF` / `#F1F5F9` / `slate-*` Tailwind classes get hunted down per page.

### 1.1 Palette

| Token | Value | Use |
| --- | --- | --- |
| `--color-bg` | `#0A0F0C` | Page background — near-black with a green undertone |
| `--color-bg-elevated` | `#10171A` | Subtle elevation tier (between bg and surface) |
| `--color-surface` | `#161E1A` | Cards, sheets, list backgrounds |
| `--color-surface-hi` | `#1F2A24` | Hover / active row, chip rest state |
| `--color-text` | `#F0F4EF` | Primary text — soft warm white |
| `--color-text-secondary` | `#A8B0A6` | Captions, secondary labels |
| `--color-text-muted` | `#6E7A6E` | Tertiary — date stamps, hint text |
| `--color-border` | `rgba(255, 255, 255, 0.07)` | Hairline dividers |
| `--color-primary` | `#9FF87C` | Neon emerald — primary CTA, active accent |
| `--color-primary-hover` | `#7CE357` | Pressed/focus |
| `--color-primary-light` | `rgba(159, 248, 124, 0.14)` | Chip backgrounds, tinted surfaces |
| `--color-primary-gradient-start` | `#C7FFA0` | Top of gradient — almost pastel highlight |
| `--color-primary-gradient-end` | `#5DBF38` | Bottom of gradient — deep saturated emerald |
| `--color-danger` | `#FF6B6B` | Destructive — outflow, delete |
| `--color-warning` | `#FFB547` | Warning — stale rate, ambiguous draft |
| `--color-success` | `#9FF87C` | Same as primary — inflow, success toast |

### 1.2 Gradients & glows

- `--gradient-hero`: radial gradient from `#C7FFA0` at top-centre through `#5DBF38` mid to `#1A2D1A` edge — used on Home balance card.
- `--glow-primary`: `0 8px 32px rgba(159, 248, 124, 0.35), 0 0 0 1px rgba(159, 248, 124, 0.18)` — CTA shadow.
- `--glow-soft`: `0 6px 20px rgba(0, 0, 0, 0.5)` — dark elevation for cards on bg.

### 1.3 Motion

`--motion-micro: 120ms`, `--motion-standard: 220ms`, `--motion-page: 280ms`. Reduced-motion blocks them all.

### 1.4 Interactive primitives

- **Button press:** `transform: scale(0.96)` on `:active` with 120ms ease.
- **Card / row tap:** `background: var(--color-surface-hi)` on `:active`.
- **Chip select:** outline-grow from 1px to 2px + glow on transition.
- **Page enter:** existing `iw-enter` fade-up keyframe stays, slightly more lift (12px → 16px).
- **Bottom nav glow:** the centre "+" button has a soft pulsing glow.
- **Voice mic:** already done in v0.6 follow-up.

---

## 2. Component partials — what changes

`core/templates/core/components/` already exists. Each gets a dark adaptation:

| Component | Change |
| --- | --- |
| `_card.html` | `--color-surface` bg, `--glow-soft`, 16px radius default (was 14px) |
| `_list_row.html` | `:active` ripple → `--color-surface-hi`; chevron tint to `--color-text-muted` |
| `_empty_state.html` | Larger emoji slot (64px), softer caption |
| `_section_label.html` | Same letter-spacing, colour shift to `--color-text-muted` |
| `_toggle.html` | iOS toggle with neon track when ON |
| `_pill.html` | Active = neon outline + glow; inactive = surface-hi |
| `_sheet.html` | Dark surface, drag handle visible against dark |
| `_page_header.html` | 44px back arrow, optional right slot, dark surface bar |

---

## 3. Per-page design intent

Order = traffic = build order.

### 3.1 Home (`/app/home/`)

Top: greeting + avatar (right). Hero card: large green gradient with `Umumiy balans` + amount in tabular nums; two pills inside the hero footer for **Kirim** (inflow arrow) and **Chiqim** (outflow arrow). Below hero: sparkline strip in muted emerald. Quote card: surface card with neon-edge accent. Transactions section: section-label "So'nggi tranzaksiyalar" + horizontal filter pills (All, Ovqat, Yo'l, Xarid …). Bottom nav floats with elevated centre + button.

### 3.2 Add transaction (`/app/transactions/add/`)

Hero card at top: `Summa` label + huge amount in white on neon-glowing dark surface. Pill toggle row: Kirim / Chiqim / Qarz berdim / Qarz oldim — selected = filled neon, unselected = surface-hi outline. Category section: same chip row pattern as reference (All / Ovqat / Yo'l / Xarid / Sog'liq). Date row: minimal dark surface row with calendar glyph. Note: textarea on surface bg. Save button: full-width filled neon, butts against bottom nav.

### 3.3 History (`/app/transactions/history/`)

Filter pills horizontal scroll along the top. Day groups with sticky `O'tgan dushanba` style section headers. Each row: 40px round icon (category emoji on dark) + label + amount (neon for income, danger for expense).

### 3.4 Voice confirm sheet

Dark sheet, mic UI already correct (v0.6 fix). Confirm cards inside need dark surfaces — amber dashed border becomes amber-on-dark.

### 3.5 Edit transaction

Mirrors Add. Adds destructive "O'chirish" row at the bottom (red text).

### 3.6 Settings hub

Card stack of `_list_row`s, each tappable, chevron right.

### 3.7 Debts (list + detail + create)

- List: pill-pair tabs (Menga qarzdor / Men qarzdorman) on neon active. Counterparty rows with avatar (palette) + amount.
- Detail: hero card with remaining amount in 32px on dark. Timeline: vertical rail with neon dots, dark event cards.
- Create: form mirroring Add.

### 3.8 Reports

- Period header: 36px chevrons in surface-hi pills, `Joriy` neon outline.
- Pie / donut: same shapes; colours rebalanced for dark — emerald lead, slate tail.
- Bar charts: gradient bars stay; background of axis labels darkens.

### 3.9 Onboarding (`/app/onboarding/`)

Dark hero cards, dot indicators in neon, "Davom etish" CTA with glow.

### 3.10 Categories / recurring lists

Surface cards with divider rows. Edit/delete chip pair stays but colours invert.

---

## 4. Non-negotiables

- **Accessibility:** WCAG AA contrast. Dark surfaces × `--color-text` must hit 7:1. Neon on dark for CTAs hits 4.5:1.
- **Tap targets ≥ 44×44** everywhere.
- **One Alpine scope per page.** No nesting.
- **No new JS deps.** All animations CSS-only.
- **Reduced-motion respect** on every animation.
- **Component partials over inline duplication** — the v0.6 components stay the unit of reuse.
- **Tests stay green** throughout. Adjust assertions only for visual strings that genuinely changed (toast copy, etc.); never relax behaviour assertions.

---

## 5. Build order (for Amelia)

1. **Tokens** — full dark palette + glow/gradient tokens + motion. One commit.
2. **Base chrome** — base.html, _nav.html (floating + glow), _toast.html. One commit.
3. **Components** — purge whites from all `core/components/_*.html`. One commit.
4. **Home** — balance hero, sparkline, quote, transaction list. One commit.
5. **Add transaction** — hero amount, type pills, category chips. One commit.
6. **Voice confirm inside sheet** — dark surfaces, ambiguous = amber-on-dark. One commit.
7. **History** — filter scroll + dark rows + sticky group headers. One commit.
8. **Edit + Settings** — small touches; settings is mostly tokens-driven. One commit.
9. **Debts list + detail + create** — three templates. One commit.
10. **Reports** — weekly + monthly + yearly + period header + chart colours. One commit.
11. **Onboarding + categories + recurring + final polish** — last visual cleanup. One commit.

Eleven commits. Each ships independently; tests stay green between.

---

## 6. Hand-off

> "Amelia — UX spec at `docs/sprint-v0.7-dark-neon-redesign.md`. Eleven commits, build order in §5. Tokens first (§1), then base chrome, then pages in traffic order. Eric is autonomous-on — don't ask, ship. Stop only if a design call is genuinely ambiguous."
