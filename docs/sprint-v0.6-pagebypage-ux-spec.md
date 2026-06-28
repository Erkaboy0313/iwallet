# Sprint v0.6 — Page-by-Page UX Redesign

**Designer:** Sally — 2026-06-28
**For:** Amelia (implementation), Eric (review)
**Replaces:** the slim v0.5 spec where I painted the system but skimped on the screens.

---

## 0. What this document is

A serious, page-by-page brief. Each section has the page's **purpose**, what's **wrong now**, the **target design**, and an **acceptance checklist** Amelia can tick off.

Order = build order. Top-tier pages first (Home, Add, History) because Eric touches them every day. Settings + Debts list next because they're frequently visited. Reports + low-traffic pages last.

I make every design call inline. Where I genuinely defer to Amelia, it's flagged "[Amelia]". Nothing is ambiguous on purpose.

---

## 1. Design system — the spine

These foundations propagate to every page. They live in `static/css/tokens.css` and `static/css/app.css`. Amelia touches them once at the start of the sprint.

### 1.1 Icon library

**Decision:** stick with Heroicons (already vendored implicitly via inline SVG), but pick *cleaner* variants. The current gear with the zigzag teeth is the worst offender — it reads as busy. We want sharp, calm icons.

Adopted set (Heroicons v2, 24×24 outline unless noted):

| Use | Icon | Stroke |
| --- | --- | --- |
| Home (nav) | `home` | 1.5px |
| History (nav) | `list-bullet` | 1.5px |
| Add (nav centre) | `plus` | 2.2px (intentional weight) |
| Debts (nav) | `arrows-right-left` | 1.5px |
| Reports (nav) | `chart-bar` | 1.5px |
| Settings (Home top-right) | `adjustments-horizontal` | 1.8px |
| Currency switcher chevron | `chevron-down-mini` (20×20 solid) | n/a |
| Voice mic | custom mic (existing `🎤` replaced with proper svg, see §11) | 1.8px |
| Back arrow (page header) | `arrow-left` | 1.8px |
| Close × on toast / sheet | `x-mark` | 1.8px |
| Edit | `pencil-square` | 1.8px |
| Delete | `trash` | 1.8px |
| Filter active dot | filled `circle` (4px) | n/a |
| Inflow card arrow | `arrow-up-right` | 2px |
| Outflow card arrow | `arrow-down-right` | 2px |

Why this matters: replacing the busy `cog-6-tooth` with `adjustments-horizontal` is the single biggest "premium" tweak we can make for one icon's effort. Three horizontal sliders read as "preferences" and look modern.

### 1.2 Typography scale

| Token | Size / weight / line-height | Usage |
| --- | --- | --- |
| `--text-display` | 36/700/1.1 | Big balance amount |
| `--text-h1` | 22/600/1.3 | Page titles |
| `--text-h2` | 16/600/1.4 | Card titles, sheet titles |
| `--text-body` | 14/400/1.5 | Body, list items |
| `--text-body-strong` | 14/600/1.5 | List item amounts |
| `--text-caption` | 12/400/1.4 | Meta, captions |
| `--text-label` | 10/600/1.0 letter-spacing 0.06em uppercase | Section labels |

Single font: Inter. Tabular nums on amounts (already done in tokens.css).

### 1.3 Spacing (no change from v0.5)

4px base. Use `--space-N` tokens.

### 1.4 Components Amelia builds once and reuses

Each is a `{% include %}` partial under `core/templates/core/components/`. The component layer didn't exist before — making it explicit is half the v0.6 polish.

| Component | Include path | Purpose |
| --- | --- | --- |
| `_page_header.html` | core/components | Standard top bar: back arrow ←, centred title, optional right slot |
| `_section_label.html` | core/components | `<p class="section-label">…</p>` — the uppercase 10px header |
| `_card.html` | core/components | White surface, 14px radius, soft shadow, configurable padding |
| `_list_row.html` | core/components | 56px tall row: left label, right value/chevron/toggle |
| `_toggle.html` | core/components | iOS-style switch — already inline in settings.html, lift to component |
| `_pill.html` | core/components | Rounded chip used by filter tabs |
| `_empty_state.html` | core/components | Centred icon + 16px headline + 14px caption |
| `_sheet.html` | core/components | Bottom-sheet wrapper (header + body + cancel) |

Builds once, every page slots in. Stops the inline-style drift the codebase has now.

### 1.5 Motion (no change from v0.5)

Three durations, two easings. Already in tokens.css. Use them.

### 1.6 The {# #} hazard

`{# … #}` is single-line only in Django. Whenever Amelia writes multi-line context, it MUST be `{% comment %} … {% endcomment %}`. Add a CI lint:

```bash
# scripts/lint-no-multiline-comments.sh
grep -rn $'{#[^#]*\\n[^#]*#}' --include="*.html" \
    core accounts categories debts voice currencies reports recurring quotes transactions \
    && echo "Multi-line {# #} found — convert to {% comment %}{% endcomment %}" && exit 1
exit 0
```

Add to `pre-commit-config.yaml` so this regression never lands again.

---

## 2. Home page (`/app/home/`)

### 2.1 Purpose

The 90% screen. Eric opens IWALLET to see: *what's my month like right now?* Everything else is one tap away.

### 2.2 What's wrong now

- Top-left settings icon is the busy cog. Reads "cluttered".
- Stale-rate banner is loud orange and shows even when the user can't act on it. Wastes the first 60px.
- Quote card is good but its dismiss × is a thin grey symbol on grey, not a real tap target visually.
- Inflow / Outflow cards are flat one-line numbers. Eric can't see *what changed* — just the totals.
- Big balance has no context — there's no comparison to last month, no signal of trend.
- "Eng ko'p sarflandi" is a flat list. No bars, no proportion sense.
- Voice mic was on Home — already removed.

### 2.3 Target layout

```
┌─────────────────────────────────────┐
│ [⚙ adjustments]              [UZS ▾]│  56px header. Settings + switcher.
│                                     │
│ ┌─ Quote (only if not dismissed) ─┐ │  Soft slate-50 card, 14px radius.
│ │ "Aqlli kishi tez-tez fikrini    │ │  Real × button: 40×40 tap target,
│ │  o'zgartiradi…"           ×     │ │  visible hit area, slate-100 hover.
│ │             — Charlie Munger     │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─ Stale-rate (only if days > 2) ─┐ │  Compressed to one line.
│ │ ⓘ Kurslar 3 kun eski        × │ │  Single-line amber card, dismissible.
│ └─────────────────────────────────┘ │
│                                     │
│ ┌────────────┐  ┌────────────┐      │  Two cards. Now with a sparkline.
│ │ ↗ KIRIM    │  │ ↘ CHIQIM   │      │  Above the number: a 32px tall, 100px
│ │ ▁▂▃▅▇▆▅    │  │ ▁▁▃▆▇▆▅    │      │  wide CSS-only bar histogram showing
│ │ 5.5 mln UZS│  │ 1.81 mln    │      │  this month's 7 most recent days.
│ │ +12% bu oy │  │ +8% bu oy   │      │  Delta vs last month below number.
│ └────────────┘  └────────────┘      │
│                                     │
│ ┌─────────────────────────────────┐ │  Big balance.
│ │ SOF BALANS                      │ │
│ │ 3.69 mln UZS                    │ │  Display-only big amount.
│ │ Iyun 2026  ·  UZS               │ │  Subtle ↑/↓ chevron next to month,
│ │   ▴ Avvalgi oydan 410k yuqori    │ │  delta caption shows direction +
│ └─────────────────────────────────┘ │  absolute delta vs last month.
│                                     │
│ ENG KO'P SARFLANDI                  │
│ ┌─────────────────────────────────┐ │  Now each row has a thin bar
│ │ 🛒 Oziq-ovqat   ████████ 1.4 mln│ │  showing its proportion of total
│ │ 📦 Boshqa       ██▍   259 k     │ │  expense for the month.
│ │ 🚕 Taxi         ▌      75 k     │ │
│ └─────────────────────────────────┘ │
│                                     │
│ (no more voice CTA — lives on Add)  │
└─────────────────────────────────────┘
```

### 2.4 Specific changes

1. **Settings icon** → `adjustments-horizontal` outline 24px stroke 1.8.
2. **Stale-rate banner**: compress to single line `ⓘ Kurslar {{ days }} kun eski`, only render when `rates_stale_days > 2`, dismissible per-session (re-uses the quote-card dismissal pattern with hx-swap=outerHTML).
3. **Quote card ×**: 40×40 tap target with visible slate-100 disc background on hover/focus. Body padding adjusts so the visible card doesn't grow.
4. **Inflow / Outflow cards**:
   - Add a sparkline above the number. 100×32 inline SVG, 14 days of history (or fewer if newer user). Stroke 1.5 in inflow-text / outflow-text. Pure CSS shape, no JS lib. Data comes from a new `transactions.selectors.daily_inflow_outflow(user, currency, days=14)`.
   - Below the number, "+12% bu oy" delta caption against last month. Green up-tick or red down-tick mini-icon.
5. **Big balance card**:
   - Drop "≈ UZS bo'yicha" (it's redundant — the currency is already in the amount).
   - Add a *delta line* under the date caption: `▴ Avvalgi oydan {abs_delta} {currency} yuqori` (or `▾ … pastroq`). Arrow + amount + word. If first month or no previous data, hide.
6. **Eng ko'p sarflandi**:
   - Each row gets a thin horizontal bar (height 4px) on the left side showing this category's share of total expense. CSS-only: `width: calc({{ cat.share_pct }}% * (max_bar_width));`.
   - Render the bar via a `<div>` with computed inline width. No SVG.
7. **No voice CTA on Home.** Done.

### 2.5 Acceptance

- [ ] Cog → adjustments-horizontal everywhere we use settings glyph.
- [ ] Stale banner one line, dismissible.
- [ ] Quote × is a real 40×40 button.
- [ ] Inflow/Outflow cards have a 14-day sparkline + a month-over-month delta line.
- [ ] Big balance card has a month-over-month delta caption.
- [ ] Top-categories list shows proportional bars.
- [ ] No voice button anywhere on Home.

---

## 3. Add transaction (`/app/transactions/add/`)

### 3.1 Purpose

Manual entry, one tap from the centre `+`. Voice mic lives here too (Eric's spec).

### 3.2 What's wrong now

- Voice button is wedged into the header with a CSS `transform: scale(0.55)`. That's a tell. It should be a first-class inline action, not a shrunk artefact.
- The type radio (Kirim / Chiqim / Qarz berdim / Qarz oldim) is a 2×2 grid of plain rectangles. Hard to scan visually.
- Amount input is the largest hit area but the helper buttons (× ming, × mln, ⌫) feel like an afterthought below.
- Date picker is the browser default — looks unstyled compared to everything else.
- Saqlash button is sticky bottom over the nav. Already fixed in Sprint v0.5 cleanup (bottom: 72px).

### 3.3 Target layout

```
┌──────────────────────────────────────┐
│ ←  Yangi tranzaksiya         [🎤]    │  Mic is its own 44×44 icon-only
│                                      │  button at the right. Tap → opens
│                                      │  the existing voice flow inline
│ TURI                                 │  (no full-page reload).
│ ┌──────────┐ ┌──────────┐            │
│ │ Kirim    │ │ Chiqim   │  ← row 1   │  Each radio is a card with:
│ │ ↗        │ │ ↘        │            │   - 18px icon top-left
│ └──────────┘ └──────────┘            │   - 14px label below
│ ┌──────────┐ ┌──────────┐            │  Selected = emerald border + tint.
│ │ Qarz     │ │ Qarz     │  ← row 2   │
│ │ berdim ↗ │ │ oldim ↙  │            │
│ └──────────┘ └──────────┘            │
│                                      │
│ SUMMA                                │
│ ┌──────────────────────────────────┐ │  Bigger amount input, takes the
│ │ 0                                │ │  spotlight. Smaller helper row.
│ └──────────────────────────────────┘ │
│ [× ming]  [× mln]  [⌫]               │  Now: stronger chips, 36px tall,
│                                      │  emerald text on hover.
│ VALYUTA                              │
│ ┌──────────────────────────────────┐ │
│ │ so'm (UZS)                    ▾  │ │
│ └──────────────────────────────────┘ │
│                                      │
│ KATEGORIYA                           │  Only for kirim/chiqim.
│ ┌──────────────────────────────────┐ │
│ │ 📌 Kategoriyani tanlang       ›  │ │
│ └──────────────────────────────────┘ │
│                                      │
│ KIM BILAN                            │  Only for debt_lent/borrowed.
│ ┌──────────────────────────────────┐ │
│ │ Masalan: Akram                   │ │
│ └──────────────────────────────────┘ │
│                                      │
│ SANA                                 │
│ ┌──────────────────────────────────┐ │  Native picker but in a styled
│ │ 📅  28 iyun, 2026             ›  │ │  wrapper. Tap → opens.
│ └──────────────────────────────────┘ │
│                                      │
│ IZOH (IXTIYORIY)                     │
│ ┌──────────────────────────────────┐ │
│ │                                  │ │
│ └──────────────────────────────────┘ │
│                                      │
│       (sticky save above nav)        │
│ ┌──────────────────────────────────┐ │
│ │           Saqlash                │ │  Always emerald gradient.
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### 3.4 Specific changes

1. **Voice mic header button**: replace the scaled-down include. Build a small `_voice_quick_button.html` partial that's just the 44×44 mic icon, hooked to the same `voice:transcribe` POST. On result, swaps into `#voice-confirm-area` rendered below the form.
2. **Type radios**: each card 76px tall, 14px radius, 1.5px border. Selected: 2px emerald border + emerald-50 background + emerald-700 text + emerald-500 icon. Inactive: slate-200 border + slate-50 background + slate-700 text + slate-500 icon. Inside each: emoji-style icon at top, label below — same as the `pill` component but bigger and grid-aligned.
3. **Amount input**: keep the size, but bump the input padding to 18px vertical for breathing room. Helper chips become rounded 36px tall pills with emerald-700 text on slate-50 background — pressable feel.
4. **Date input**: wrap the native `<input type="date">` so it visually matches the other selects. Show formatted date next to a calendar icon in a tap-to-open wrapper. (Implementation: keep native input, just style it with `appearance: none` and absolute-position the chevron / icon.)
5. **Category / Counterparty selects**: identical visual treatment to date — large white card row, left icon, right chevron, label fills middle.
6. **Saqlash**: emerald gradient (`--color-primary-gradient-start → -end`) + `--shadow-cta`. Same as Home voice CTA pattern, consistency.

### 3.5 Acceptance

- [ ] Mic button is full-size (44×44) header action, not scaled.
- [ ] Type radios are visually scannable 2×2 grid of cards with icons.
- [ ] Amount input has more breathing room and helper chips look intentional.
- [ ] Date / Category / Counterparty fields all use the same row template.
- [ ] Save button has gradient + glow shadow, consistent with other primary CTAs.

---

## 4. Transaction history (`/app/transactions/history/`)

### 4.1 Purpose

Scrollable log of every transaction. Filterable by type + currency. Tap row → edit.

### 4.2 What's wrong now

- Filter pills run off the right edge (Eric flagged "Qar…" cut off). Need horizontal scroll OR wrap.
- Active filter pill has only a colour cue. No depth.
- Each row has a "📌" emoji when category is null — looks like a placeholder, but it's actually rendered for legitimate uncategorized rows.
- Date format is `28-Iyun` — fine, but year context is missing. If user scrolls back into 2025, the year matters.
- Delete is a tiny `O'chirish` link below the row. Easy to mis-tap given the row itself is also tappable.

### 4.3 Target layout

```
┌──────────────────────────────────────┐
│ ←  Tarix                             │  Standard page header.
│                                      │
│ ┌─[ Hammasi ][Kirim][Chiqim][Qarz▾]  │  Horizontal scroll. Active pill
│   ─────────                          │  has emerald-600 background + white
│                                      │  text + soft shadow. Inactive:
│                                      │  slate-100 bg + slate-700 text.
│ IYUN 2026                            │  Sticky section header per month.
│ ┌──────────────────────────────────┐ │
│ │ 🛒 Oziq-ovqat              + … │ │  Tap whole row → edit page.
│ │ 28 iyun • magazin           1.4 │ │  Long-press / swipe → delete sheet.
│ │ - - - - - - - - - - - - - - - -  │ │  4px slate-100 divider between rows.
│ │ 🚕 Taxi                          │ │
│ │ 27 iyun                      75k │ │
│ └──────────────────────────────────┘ │
│                                      │
│ MAY 2026                             │  Older month, sticky header rolls in.
│ ┌──────────────────────────────────┐ │
│ │ …                                │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### 4.4 Specific changes

1. **Filter pills**: wrap in `overflow-x-auto` scroll container with `scroll-snap-type: x mandatory`. Right-edge fade-out gradient hints at more content.
2. **Active pill**: emerald-600 background, white text, soft shadow `0 2px 4px rgba(5,150,105,.25)`.
3. **Row structure**:
   - Emoji + category name on top-left (or `Boshqa` if null, no 📌).
   - Date + counterparty/note on second line (smaller, slate-500).
   - Amount on the right, tabular-nums.
   - Sign in the amount: `+` for income/debt_borrowed, `−` for expense/debt_lent. Colour: emerald-600 / slate-900 / amber-700 / slate-900.
4. **Delete**: removed from the row. Tapping a row goes to **edit page** which has Delete prominently shown. Cleaner mental model, no accidental delete from a swipe.
5. **Month section headers**: sticky `position: sticky; top: 0;` per month group. The history view server-side already orders by date desc, so it's just a CSS / template tweak to insert a `<header>` whenever the month changes.
6. **Empty state**: replace today's centred plain text with the `_empty_state` component — empty-illustration emoji + headline + CTA button "+ Birinchi tranzaksiya".

### 4.5 Acceptance

- [ ] Filter pills scroll horizontally with snap.
- [ ] Active pill is visually distinct (emerald bg, white text, shadow).
- [ ] No 📌 placeholder; rows render their real category or "Boshqa".
- [ ] Delete moved entirely to the edit page.
- [ ] Sticky month headers.
- [ ] Empty state uses the component partial.

---

## 5. Settings hub (`/app/settings/`)

### 5.1 Purpose

Stable home for non-frequent toggles. Already shipped in v0.5 Phase 4, but the visual could go further.

### 5.2 What's wrong now

- Sections look like four bland white blocks. Hierarchy reads flat.
- Toggle for Kunlik ibora is custom-built per-row inline — not a real component yet.
- "Konvertatsiya" row is read-only — should be tappable to open a small bottom-sheet that lets the user toggle raw/converted display.

### 5.3 Target tweaks (small but compounding)

1. Wrap each section card with `--shadow-soft` and a 1px border in `--color-border`. Make the boundary visible.
2. Convert the inline toggle to `_toggle.html` component (cleaner DOM).
3. Make "Konvertatsiya" row a tappable item that opens a bottom sheet with two radio options (Mahalliy / Aylantirilgan). POSTs to `currencies:switch_display`.
4. Add a section divider line at section boundaries (4px slate-50 gutter inside the card group).

### 5.4 Acceptance

- [ ] Toggle uses the `_toggle.html` component.
- [ ] Konvertatsiya row opens a bottom sheet to change display mode.
- [ ] Section cards have softer borders + softer shadow.

---

## 6. Debts list (`/app/debts/`)

### 6.1 Purpose

See active obligations either direction. Tap row → detail. New debt → bottom sheet (already there).

### 6.2 What's wrong now

- Two-tab segmented control "Menga qarzdor / Men qarzdorman" is functional but the inactive tab is too quiet (looks disabled).
- Per-currency total strip at the top is useful but visually identical to the rows below — hierarchy collapses.
- Each debt row shows initials avatar — but the avatar is just slate-200 background with text. Looks generic.
- No filter or sort. Old debts and recent ones mix.

### 6.3 Target tweaks

1. **Tab control**: rebuild as a pill-pair styled to match the v0.5 segmented control. Active: white background + soft shadow + slate-900 text. Inactive: transparent + slate-500 text. Both wrapped in a slate-100 outer pill.
2. **Total strip**: a single header card, not a list — emerald tint when "Menga qarzdor" (good news, they owe me), rose tint when "Men qarzdorman" (less good, I owe). Big amount, smaller per-currency breakdown.
3. **Avatar colour**: assign deterministic colour from initials hash. 8 muted colours (slate-500, emerald-500, amber-500, rose-500, indigo-500, teal-500, purple-500, cyan-500). Same person → same colour every time.
4. **Sort**: newest first by default. Add a sort menu (Bottom-sheet from a small "Saralash" pill top-right). Options: yangi → eski, eski → yangi, miqdori bo'yicha.

### 6.4 Acceptance

- [ ] Tabs are a styled pill-pair, active state stands out.
- [ ] Total strip is a single bold card with direction-coloured tint.
- [ ] Avatars use a deterministic palette per counterparty.
- [ ] Sort menu (Saralash) implemented as bottom sheet, three options.

---

## 7. Voice confirm (`/app/voice/confirm/` ← swapped into `#voice-confirm-area`)

### 7.1 Purpose

Show 1–10 parsed drafts, let user delete/edit each, save atomically.

### 7.2 What's wrong now

We just rewrote this in commit `d3af0ff` to a single Alpine scope and it works. Visual still needs love:

- The "tap to edit" affordance is invisible until you tap. No hint that the category pill is editable.
- Ambiguous-field amber border looks like an error alert, not a "please confirm" cue.
- The summary header at top (`3 ta tranzaksiya · -85k UZS`) is useful but uses the same weight as everything else.

### 7.3 Target tweaks

1. Editable pills (category, currency, date, counterparty) get a tiny pencil glyph `✎` inside the pill, lower-right corner, slate-400. Tells the user "you can change this".
2. Ambiguous border colour shift: from solid amber-500 to a softer amber-300 dashed border. Still draws attention but reads as "review", not "error".
3. Summary header: amount in `text-h2` weight, label in `text-caption`. Visual lead.
4. Per-card delete `❌ O'chirish` button: keep, but lighter — slate-400 colour, hover rose-700. Currently the red is loud and looks dangerous.

### 7.4 Acceptance

- [ ] Editable pills carry a small pencil affordance.
- [ ] Ambiguous cards use dashed amber-300 border instead of solid amber-500.
- [ ] Summary header has clear typographic hierarchy.
- [ ] Delete buttons toned down.

---

## 8. Edit transaction (`/app/transactions/edit/<id>/`)

Mirror of Add (§3). Same exact field treatment. **Plus** at the bottom, above the Save button, an "O'chirish" destructive action:

```
   …form…
   ┌────────────────────────────────┐
   │ 🗑  Tranzaksiyani o'chirish    │  Light rose-50 background, rose-700
   └────────────────────────────────┘  text. Confirmation modal on tap.
   ┌────────────────────────────────┐
   │            Saqlash             │
   └────────────────────────────────┘
```

Same standardized form rows as Add. The header keeps the back arrow + title.

---

## 9. Reports (`/app/reports/weekly|monthly|yearly/`)

### 9.1 Purpose

Trend over time. Weekly bars, monthly overview, yearly story.

### 9.2 What's wrong now

- All three views use the same chrome — that's fine. But the donut chart for category share is grey when empty, looks broken.
- Bar charts are reasonable but flat-coloured. No depth.
- The "Joriy" anchor and prev/next nav arrows feel like a debug strip, not a tab.

### 9.3 Target tweaks

1. **Period header strip**: prev/next arrows become 36×36 buttons with the `chevron-left/right-mini` icons. The "Joriy" label is a subtle pill below the date range, only visible when viewing the current period.
2. **Bar charts**: same shape, but use the emerald-to-emerald-darker gradient fill instead of flat emerald. Bottom 2px shadow gives depth.
3. **Donut (category share)**: when no data, replace the empty circle with the `_empty_state` component ("Bu davrda kategoriya bo'lmagan") — don't try to render a chart with nothing in it.
4. **Yearly view**: amber highlight on the most-expensive month becomes a small badge `eng ko'p sarflandi` on the bar tip, not just a colour shift.

### 9.4 Acceptance

- [ ] Period nav strip refined (chevron buttons + subtle "Joriy" pill).
- [ ] Bar charts use gradient fills + soft shadow.
- [ ] Donut empty-state replaced with the component.
- [ ] Yearly amber-month carries a badge, not just colour.

---

## 10. Lower-traffic pages — fast pass

### 10.1 Onboarding (`/app/onboarding/`)

Visual reskin only. Use the new palette + motion. No structural change.

### 10.2 Categories list (`/app/settings/categories/`)

- Reskin rows to use `_list_row.html`.
- Add/Edit form moves into a bottom sheet (already partially there).
- Hidden-preset toggle row → use `_toggle.html`.

### 10.3 Recurring list (`/app/settings/recurring/`)

- Same `_list_row` template.
- Each row: name + cadence (e.g. "har oy 1-sanasida") + amount + pause/resume mini-toggle.
- Empty state component when the user has no rules yet.

### 10.4 Debt detail / create

- Detail page: lead with the obligation amount in `text-display`, then a timeline of repayments below. Timeline uses left-margin vertical bar with dots — already partly built.
- Create page: same row template as Add transaction.

### 10.5 Voice error partial (`voice/_error_partial.html`)

- Use `_empty_state` component with the broken-mic emoji + clear "Yana urinib ko'ring" CTA.

---

## 11. Voice button (the mic itself)

The button uses `🎤` emoji. Emoji ≠ icon — looks inconsistent next to all the line icons we're standardizing on. Replace with proper SVG mic.

```html
<!-- Heroicons microphone outline -->
<svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round"
          d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
</svg>
```

Stop state ⏹ — replace with `stop-circle` outline. Processing — keep the three-dot bounce, that's fine.

---

## 12. Build order (for Amelia)

1. **Foundations** — components partials (§1.4), tokens.css polish (typography), CI hook for multi-line `{# #}`. Single commit.
2. **Home** (§2) — settings icon swap, stale-banner compression, quote × button, sparklines, deltas, top-categories bars. One commit.
3. **Add transaction** (§3) — mic header button, type radio cards, amount polish, field rows. One commit.
4. **History** (§4) — filter pills scroll, active styling, row template, sticky month headers, delete moved to edit. One commit.
5. **Edit transaction** (§8). One commit.
6. **Settings hub polish** (§5). One commit.
7. **Debts list** (§6). One commit.
8. **Voice confirm polish** (§7). One commit.
9. **Reports polish** (§9). One commit.
10. **Lower-traffic pass** (§10) + voice mic SVG (§11). One commit.

Ten commits. Each ships independently; tests stay green between.

---

## 13. Non-negotiables I'm holding Amelia to

- **One Alpine scope per page.** No nested `Alpine.data()`. No `$dispatch` ladders.
- **No new JS deps.** Sparklines + bar charts are inline SVG or CSS.
- **CSS animations only.** Three duration tokens. Three only.
- **Reduced-motion respect** on every animation.
- **Tap target ≥ 44×44** everywhere.
- **`{% comment %}{% endcomment %}` for any multi-line context**. The lint rule enforces this.
- **No "trash" code.** Reference style: voice partial commit `d3af0ff`. Component partials over inline duplication.

---

## 14. Hand-off

> "Amelia — UX spec at `docs/sprint-v0.6-pagebypage-ux-spec.md`. Ten commits, build order in §12. Foundations first (§1.4 components + lint hook), then Home, then the rest in order. Reach me only if a design call I left genuinely ambiguous blocks you."
