# Sprint v0.5 — UX Specification

**Designer:** Sally — 2026-06-28
**Companion to:** [`sprint-v0.5-redesign-plan.md`](./sprint-v0.5-redesign-plan.md)
**For:** Amelia (implementation)

This spec gives Amelia exact pixels, hex codes, easing curves, and the copy. Anywhere Eric will *see* something, the answer is here. Anywhere Amelia needs to make a JS/architecture call, John's PRD §4 binds her.

---

## 0. Reading order

Read top to bottom on first pass. Sections are independent on second pass — Amelia can jump to §3 for Phase 1 layout, §5 for color tokens, §7 for motion.

---

## 1. Voice and tone

Polite Uzbek, "siz" form, conversational but never marketing. Short over clever. Recurring rules:

- **Numbers in copy:** "Iyun oyida", not "06/2026"; "10 ming so'm", not "10 000 UZS" *in body copy*. Numbers shown as data stay numeric ("10 000 UZS").
- **No exclamation marks** in headings. "Sof balans" not "Sof balans!". Reserves !! for empty-state nudges where it actually means something.
- **Apostrophe is `'`** (U+0027 ASCII) — Eric's keyboard. Not `'` (U+2019). Templates and migrations must stick to U+0027 so Alpine expressions don't break (we hit that bug in voice — never again).
- **No emoji in headings.** Body, pills, icons fine. Headings stay clean.

---

## 2. Color palette (final hex)

Lands in `static/css/tokens.css`. Replaces the current flat-emerald palette.

### Surface and ink

| Token | Hex | Usage |
| --- | --- | --- |
| `--color-bg` | `#F4F6F2` | App background — softer than today's `#FAFAF7`, slight warm green wash |
| `--color-bg-gradient-stop` | `#E9EFE5` | Optional vertical gradient (top → bottom) |
| `--color-surface` | `#FFFFFF` | Card background |
| `--color-surface-elevated` | `#FFFFFF` | Same hex, paired with stronger shadow |
| `--color-text` | `#0B1220` | Primary ink. Was `#0F172A` — deepen 2 stops |
| `--color-text-secondary` | `#475569` | Body, labels |
| `--color-text-muted` | `#94A3B8` | Captions, hint text |
| `--color-border` | `rgba(15,23,42,0.08)` | Card hairlines — was `#E2E8F0` solid, now translucent slate for depth |

### Primary (CTA, balance, brand)

| Token | Hex | Usage |
| --- | --- | --- |
| `--color-primary` | `#059669` | Default emerald |
| `--color-primary-hover` | `#047857` | Hover state |
| `--color-primary-light` | `#D1FAE5` | Tinted backgrounds (inflow card surface) |
| `--color-primary-gradient-start` | `#10B981` | CTAs, elevated `+` button |
| `--color-primary-gradient-end` | `#047857` | Same gradient pair |

### Inflow / outflow (the new Phase 1 cards)

| Token | Hex | Usage |
| --- | --- | --- |
| `--color-inflow-surface` | `#ECFDF5` | Kirim card background tint |
| `--color-inflow-text` | `#047857` | Kirim card amount |
| `--color-inflow-icon` | `#10B981` | Kirim icon stroke |
| `--color-outflow-surface` | `#FEF2F2` | Chiqim card background tint (was neutral slate — Eric explicitly asked for red) |
| `--color-outflow-text` | `#BE123C` | Chiqim card amount |
| `--color-outflow-icon` | `#E11D48` | Chiqim icon stroke |

### Secondary roles

| Token | Hex | Usage |
| --- | --- | --- |
| `--color-debt` | `#D97706` | Amber-600 — debt obligation flag (deeper than today's `#F59E0B`) |
| `--color-danger` | `#DC2626` | Destructive: delete |
| `--color-warning-bg` | `#FEF3C7` | Amber soft (stale-rate banner, ambiguous voice card) |

### Shadows

| Token | Value | Usage |
| --- | --- | --- |
| `--shadow-soft` | `0 1px 2px rgba(15,23,42,0.04), 0 2px 6px rgba(15,23,42,0.04)` | Default card |
| `--shadow-elevated` | `0 4px 10px rgba(15,23,42,0.08), 0 8px 24px rgba(15,23,42,0.06)` | Big balance card, modals |
| `--shadow-cta` | `0 6px 20px rgba(5,150,105,0.35)` | The elevated centre `+` button |

---

## 3. Phase 1 — Home page (the screen Eric stares at)

Vertical order, top to bottom:

```
┌─────────────────────────── padding 20 ───┐
│                                    [⚙]   │  Gear icon, top-right, 24px, slate-500
│                                          │
│ ┌─ Quote card (Phase 3, placeholder Φ1)─┐│  Slate-50 bg, italic body, 14px
│ │ "Pulingiz haqida o'ylamasangiz, pul   ││  Soft border, 16px radius
│ │  siz haqingizda o'ylab qoladi."     × ││  × dismiss top-right, 12px from edges
│ │                — Warren Buffett       ││
│ └───────────────────────────────────────┘│
│                                          │
│ ┌──────────────┐  ┌──────────────┐       │  Inflow + Outflow side-by-side
│ │ ↗ KIRIM      │  │ ↘ CHIQIM     │       │  12px gap, equal width
│ │ 500 000 UZS  │  │  56 000 UZS  │       │  Card: padding 14px, radius 14px
│ └──────────────┘  └──────────────┘       │
│                                          │
│ ┌──────────────────────────────────────┐ │  Big balance card
│ │ SOF BALANS                           │ │  10px label (slate-500, uppercase)
│ │                                      │ │
│ │ 444 000 UZS                          │ │  text 36px, tabular-nums, bold
│ │                                      │ │  Slight gradient bg: surface → tinted
│ │ Iyun 2026 · UZS                      │ │  12px caption, slate-500
│ └──────────────────────────────────────┘ │
│                                          │
│ ENG KO'P SARFLANDI                       │  10px uppercase label, slate-500
│ ┌──────────────────────────────────────┐ │
│ │ 🛒 Oziq-ovqat              46 000 UZS│ │  unchanged from current
│ │ 📦 Boshqa                  24 000 UZS│ │
│ │ 🚕 Taxi                    15 000 UZS│ │
│ └──────────────────────────────────────┘ │
│                                          │
│ ┌──────────────────────────────────────┐ │  Voice CTA — emerald gradient
│ │     🎤   Ovoz bilan qo'shing         │ │  Full-width, 56px tall, 14px radius
│ │                                      │ │  Gradient start → end
│ └──────────────────────────────────────┘ │  Shadow-cta on default state
│                                          │
└──────────────────────────────────────────┘
        ↓ (bottom nav from Phase 2)
```

### 3.1 Quote card

Placeholder for Phase 1, real content arrives Phase 3.

- Background `#F1F5F9` (slate-100).
- Body text: `font-style: italic`, 14px line-height 1.55, `--color-text-secondary`.
- Author line: not italic, 12px, `--color-text-muted`, 8px top margin, em-dash prefix (` — Warren Buffett`).
- Dismiss `×`: 18px stroke icon, top-right corner, 8px from edges. Tap target stretches to 36×36 (transparent padding) for thumb hit.
- Border-radius: 14px. Soft 1px border in `--color-border`. No shadow (it's a passive card, not actionable).
- Padding: 14px 16px.

### 3.2 Inflow card

- Background: `--color-inflow-surface` (`#ECFDF5`).
- Border-radius: 14px.
- Padding: 14px.
- Icon: 16×16 stroke icon, `--color-inflow-icon`. Use a north-east arrow (`↗`). Heroicons `arrow-trending-up` works.
- Label "KIRIM": uppercase, 10px, letter-spacing 0.06em, `--color-inflow-text` at 70% opacity.
- Amount: 18px, tabular-nums, weight 600, `--color-inflow-text`.
- The card itself is `:active` press-scale 0.98, transition `--motion-micro`.

Tap behaviour: route to `/app/transactions/history/?type=income`. Already supported.

### 3.3 Outflow card

Mirror of inflow:

- Background: `--color-outflow-surface` (`#FEF2F2`).
- Icon: `↘`, `--color-outflow-icon`.
- Label "CHIQIM" + Amount: `--color-outflow-text`.
- Tap: `/app/transactions/history/?type=expense`.

### 3.4 Big balance card

- Background: `linear-gradient(180deg, var(--color-surface) 0%, var(--color-bg-gradient-stop) 140%)`.
- Border: 1px `--color-border`.
- Border-radius: 18px.
- Padding: 20px.
- Shadow: `--shadow-elevated`.
- Label "SOF BALANS": same uppercase 10px style as other section labels.
- Amount: 36px, weight 700, tabular-nums, `--color-text`.
- Caption: 12px, `--color-text-muted`, format `{Month} {Year} · {Currency}`.
- On update, the amount runs the count-up animation (§7.4).

### 3.5 Voice CTA

- Background: `linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%)`.
- Color: white.
- Border: none.
- Border-radius: 14px.
- Height: 56px.
- Font: 16px, weight 600.
- Shadow: `--shadow-cta`.
- Layout: flex centred, mic icon 20px on left, 8px gap, label "Ovoz bilan qo'shing".
- Hover/active: `translateY(-1px)` and shadow grows by ~2px. Transition `--motion-micro`.
- `:active`: `transform: scale(0.98)`.
- When voice recording is open, the CTA pulses (existing `vb-pulse` keyframe from `_voice_button.html`).

### 3.6 What is removed

- "Salom, {first_name}!" greeting.
- "Joriy oy" caption row.
- The 3-stat strip (Naqd / Sof / Qarz holati).
- "✏️ Qo'lda yozish" secondary button next to the mic.
- Footer links `⚙ Kategoriyalar` and `⏰ Takrorlanuvchi`.

Gear icon top-right replaces the entire bottom footer-links cluster.

---

## 4. Phase 2 — Bottom navigation

Five items, fixed bottom, max-width 430px, centred.

```
┌─────────────────────────────────────────────────┐
│  🏠       🕐      ┌─────────┐      💰      📊   │
│  Uy      Tarix    │   ➕    │     Qarz   Hisobot│
│                    │ Qo'shish│                  │
│                    └─────────┘                  │
└─────────────────────────────────────────────────┘
                       ↑
                       Elevated 14px above baseline
```

### 4.1 Nav bar container

- Position: `fixed`, `bottom: 0`, full-width up to 430px.
- Background: `--color-surface` with 96% opacity + `backdrop-filter: blur(12px)`.
- Border-top: 1px `--color-border`.
- Padding: `8px 12px calc(8px + env(safe-area-inset-bottom)) 12px`.
- Height: ~70px (excluding the safe-area bottom).

### 4.2 Standard nav item (Uy, Tarix, Qarz, Hisobot)

- Layout: flex column, centred.
- Icon: 22px, stroke 1.8px, color `--color-text-muted` default, `--color-primary` active.
- Label: 11px, weight 500, color matches icon.
- Tap target: 56×44 minimum.
- Active state: icon and label switch to `--color-primary`. A 3px dot under the label (centred), color `--color-primary`. The dot is the active indicator.
- Transition: `--motion-micro` on color.

### 4.3 Centre `+` (Qo'shish)

- Circle, 64×64.
- Background: `linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%)`.
- Border: 4px solid `--color-surface` (white ring against the nav background so it looks lifted).
- Shadow: `--shadow-cta`.
- Translate up: `margin-top: -22px` so the circle sits above the nav baseline.
- Content: 24px white `+` icon, label "Qo'shish" 10px below the icon, all-caps not needed — sentence case, weight 600, white.
- Tap: `transform: scale(0.96)` on `:active`, transition `--motion-micro`.
- Route: `/app/transactions/add/`.
- ARIA: `aria-label="Yangi tranzaksiya qo'shish"`.

### 4.4 Hide rule

The centre nav button does **not** render on `/app/transactions/add/` itself or any `/app/voice/confirm/` swap target (avoids the user smashing `+` while already on the add form). Implementation: a small Django template context flag `hide_center_nav` that the relevant views set.

---

## 5. Phase 3 — Daily quote

### 5.1 Curated seed list (25 quotes)

Sally curated. Authors and Uzbek translations below. Amelia seeds these via migration.

| # | Author | Uzbek text |
| -- | --- | --- |
| 1 | Warren Buffett | Pulingiz haqida o'ylamasangiz, pul siz haqingizda o'ylab qoladi. |
| 2 | Warren Buffett | Hech qachon yo'qotmaslik birinchi qoida. Birinchi qoidani unutmaslik ikkinchi qoida. |
| 3 | Charlie Munger | Maishiy intizom — sizning daromadingizdan ham muhim. |
| 4 | Charlie Munger | Aqlli kishi tez-tez fikrini o'zgartiradi. Ahmoq esa hech qachon. |
| 5 | Naval Ravikant | Boylik — uxlayotganda ham siz uchun ishlaydigan aktivlar. |
| 6 | Naval Ravikant | Pul muammoni hal qilmaydi, lekin u sizga muammoni tanlash erkinligini beradi. |
| 7 | Morgan Housel | Bir umrlik tejash bir hafta xarid qilishdan kuchliroq. |
| 8 | Morgan Housel | Vaqt — moliyaning sehridir. |
| 9 | Seneca | Boy odam — bu kam narsaga muhtoj bo'lgan kishi. |
| 10 | Seneca | Hech narsa egamiz emas; bizda faqat vaqt bor. |
| 11 | Marcus Aurelius | Kuningizning birinchi soati o'zingiz uchun bo'lsin. |
| 12 | Marcus Aurelius | Sizga mavjud bo'lgan narsani ko'paytirish, yo'qni izlashdan yengilroq. |
| 13 | Benjamin Franklin | Bir tiyin tejashga — bir tiyin topganga teng. |
| 14 | Benjamin Franklin | Vaqt — pul. |
| 15 | Nassim Taleb | Boylik — sizning ehtiyojlaringizning kichikligida. |
| 16 | Nassim Taleb | Tasodifga ishonmang. Strukturani quring. |
| 17 | Thomas Sowell | Hech bo'lmaganda biror narsa bepul deganlarga ishonmang. |
| 18 | Peter Drucker | O'lchamasangiz — boshqara olmaysiz. |
| 19 | Robert Kiyosaki | Boylar pulni o'zlari uchun ishlatadi. Kambag'allar pul uchun ishlaydi. |
| 20 | James Clear | Siz maqsadlarga yetganingiz uchun emas, tizimingiz tufayli o'sasiz. |
| 21 | Jim Rohn | Maoshingiz uchun ishlang; boylik uchun o'rganing. |
| 22 | Confucius | Insonni biror narsa qo'rqitmasin — kechikishdan tashqari. |
| 23 | Lao Tzu | Bin kilometrlik yo'l bir qadamdan boshlanadi. |
| 24 | Local saying | Tomchi-tomchi ko'l bo'lar. |
| 25 | Local saying | Yeb-ichganing — o'zingniki, sarflaganing — yelga ketganing. |

### 5.2 Display

See §3.1. Already specified above as part of Home layout.

### 5.3 Dismiss flow

- Tap `×` → quote fades out 220ms (`--motion-standard`), height collapses (margin animates).
- A small chip appears in its place for 4 seconds: "Kunlik ibora yashirildi. [Qaytarish]" with a tappable "Qaytarish" inline link.
- Chip auto-dismisses after 4s, OR user taps "Qaytarish" → quote re-renders.

Per-session dismiss: a Django session flag `iw_quote_hidden_today = True`.

Permanent dismiss path: from Settings (§6). Not from Home — Eric should not be able to accidentally turn off the feature with one tap. Two taps minimum, via the hub.

### 5.4 Quote selection rule

```python
# quotes/selectors.py
def quote_of_the_day(user, *, today=None) -> Quote | None:
    today = today or timezone.localdate()
    if not QuoteDismissal.objects.filter(user=user, feature_enabled=False).exists():
        active = list(Quote.objects.filter(is_active=True))
        if not active:
            return None
        seed = hash((user.telegram_id, today.isoformat()))
        return active[seed % len(active)]
    return None
```

Deterministic per-day per-user. Eric sees the same Buffett quote whenever he refreshes today; tomorrow morning, new quote.

---

## 6. Phase 4 — Settings hub

**Format decision:** full page, not a bottom sheet. Bottom sheets are for one-off actions (pick category, confirm delete). A hub with 6+ rows wants a stable home users can land on, share via URL, and scroll.

### 6.1 Layout

```
┌── [← Orqaga]   Sozlamalar ────────────┐
│                                       │
│ PROFIL                                │  10px uppercase label
│ ┌───────────────────────────────────┐ │
│ │ Telegram ismi             Erkaboy │ │  Row 56px tall
│ │ Til                       O'zbekcha│ │
│ └───────────────────────────────────┘ │
│                                       │
│ PUL                                   │
│ ┌───────────────────────────────────┐ │
│ │ Asosiy valyuta            UZS  ›  │ │  Routes to a bottom sheet picker
│ │ Ko'rsatish        Mahalliy ‹›     │ │  Segmented control inline
│ │ Kunlik ibora              [Toggle]│ │  iOS-style toggle
│ └───────────────────────────────────┘ │
│                                       │
│ TARTIB                                │
│ ┌───────────────────────────────────┐ │
│ │ Kategoriyalar                   › │ │  Routes to /app/settings/categories/
│ │ Takrorlanuvchi                  › │ │  Routes to /app/settings/recurring/
│ └───────────────────────────────────┘ │
│                                       │
│ MAXFIYLIK                             │
│ ┌───────────────────────────────────┐ │
│ │ Audio fayllar saqlanmaydi.        │ │  static info text, 14px
│ │ Gemini'ga matnga aylantirish      │ │
│ │ uchun yuboriladi va o'chiriladi.  │ │
│ └───────────────────────────────────┘ │
│                                       │
└───────────────────────────────────────┘
```

### 6.2 Row anatomy

- Height 56px.
- Padding 16px horizontal.
- Left: label, 15px, `--color-text`.
- Right: value (15px, `--color-text-secondary`), or chevron `›`, or toggle, or segmented control.
- Divider: 1px `--color-border` between rows within the same section.
- Section gap: 24px.

### 6.3 Group cards

Wrap each section's rows in a `--color-surface` card with 12px radius, `--shadow-soft`, no internal padding (rows handle their own).

### 6.4 Settings entry point

Top-right of `/app/home/`: gear icon, 22px stroke, `--color-text-muted`. Tap target 44×44. Routes to `/app/settings/`.

### 6.5 Sub-pages reuse existing routes

- "Kategoriyalar" row → existing `/app/settings/categories/` from Epic 3.
- "Takrorlanuvchi" row → existing `/app/settings/recurring/` from Epic 7.

No re-implementation. Just point the chevrons at the routes.

---

## 7. Phase 5 — Motion and interactions

### 7.1 Duration tokens

Lands in `tokens.css`:

```css
:root {
  --motion-micro: 120ms;
  --motion-standard: 220ms;
  --motion-page: 180ms;

  --ease-out: cubic-bezier(0.2, 0.8, 0.2, 1);
  --ease-out-soft: cubic-bezier(0.16, 1, 0.3, 1);
}
```

All transitions across the app must use one of these. No `0.3s`, no `1s`, no inline magic numbers.

### 7.2 Reduced-motion fallback

The existing `prefers-reduced-motion: reduce` block in `tokens.css` already collapses animation/transition durations to 0.01ms. Keep it; just verify Phase 5 changes respect it (they will because they all use the same tokens).

### 7.3 Standard interaction states

Apply globally:

- **Button press:** `transform: scale(0.97)` on `:active`. Duration `--motion-micro`, ease `--ease-out`.
- **Card press (rows, top cards):** `transform: scale(0.99)` on `:active`. Same timing.
- **Hover (desktop / Telegram Desktop only):** brightness `1.03` on CTAs, no movement.
- **Focus-visible:** 2px solid `--color-primary` outline, 2px offset.

### 7.4 Number tween for the big balance card

When `cash_balance` changes (initial load counts as a change from 0):

- Duration 400ms.
- Easing `--ease-out-soft`.
- Implementation: pure CSS using `@property --balance` + custom property animation if browser supports, else jump-set. Browsers without `@property` (most Telegram WebViews now support it via Chromium 85+) just see the final value.

CSS sketch:

```css
@property --balance {
  syntax: '<integer>';
  inherits: false;
  initial-value: 0;
}

.balance-amount {
  transition: --balance 400ms var(--ease-out-soft);
  counter-set: bal var(--balance);
}

.balance-amount::after {
  content: counter(bal);
}
```

Set `--balance` via inline style on render. If `@property` isn't supported, the amount just appears (no animation) — no error, no fallback animation lib.

### 7.5 Bottom-sheet motion

Already used for category picker, voice confirm. Standardize on:

- Enter: `translateY(100%)` → `translateY(0)`, `--motion-standard`, `--ease-out-soft`.
- Exit: reverse.
- Backdrop fades 0 → 0.4 alpha in `--motion-standard`.

### 7.6 Toast

Already present. Retune to:

- Enter: slide from `translateY(-20px) + opacity 0` to `translateY(0) + opacity 1` in `--motion-standard`.
- Persist 3s.
- Exit: reverse over `--motion-micro`.

### 7.7 Voice button states

Unchanged structurally (idle / recording / processing / error). Tweak:

- Recording pulse: keep `vb-pulse` keyframe but slow to 1.6s loop. Current 1.5s reads as urgent.
- Processing dots: keep `vb-bounce`, no change.
- Error shake: change from `vb-shake` 300ms once to a single `transform: translateX` wobble in `--motion-standard`. Less aggressive.

### 7.8 Performance ceiling

Amelia tests Phase 5 with Chrome DevTools Performance throttling set to "Mid-tier mobile" + 4x CPU slowdown. Interactions must stay in the 16ms per-frame budget for the duration of the animation. If something drops frames, the offender goes back to opacity-only.

---

## 8. Component inventory

Files Amelia touches, sequenced by phase:

| Phase | Files | Notes |
| --- | --- | --- |
| 1 | `transactions/selectors.py` | Add inflow_total, outflow_total, fix cash_balance |
| 1 | `core/views.py::home_content` | Pass new fields to template |
| 1 | `core/templates/core/_balance_hero.html` | Full rewrite to the §3 layout |
| 2 | `core/templates/core/_nav.html` | New 5-item layout, elevated centre |
| 2 | `core/templates/base.html` | Add `hide_center_nav` block hook |
| 2 | `transactions/views.py`, `voice/views.py` | Set `hide_center_nav=True` in their contexts |
| 3 | New app `quotes/` | model, migration, selector, seed |
| 3 | `core/templates/core/_balance_hero.html` | Wire quote card at top |
| 3 | `accounts/models.py` | Add `QuoteDismissal` model (or own app) |
| 4 | New `core/templates/core/settings.html` | The hub layout |
| 4 | `core/views.py::settings_view`, `core/urls.py` | New `/app/settings/` route |
| 4 | `core/templates/core/_balance_hero.html` | Gear icon top-right |
| 5 | `static/css/tokens.css` | New palette + motion tokens |
| 5 | `static/css/app.css` (or new `motion.css`) | Press states, hover, count-up keyframes |
| 5 | `core/templates/core/_balance_hero.html` | Wire `--balance` inline style for count-up |
| 5 | `voice/templates/voice/_voice_button.html` | Retime pulse/shake |

Total templates new: 1 (settings.html). Total new apps: 1 (quotes). The other six files are edits.

---

## 9. Accessibility

- All tap targets ≥ 44×44.
- All icon-only buttons get `aria-label` in Uzbek.
- Big balance card: `aria-live="polite"` so screen readers announce the new value after count-up.
- Quote card body: real text content (not background-image), so screen readers can read it.
- Quote dismiss `×`: `aria-label="Kunlik iborani yashirish"`.
- Settings rows: each is a `<button>` or `<a>`, never a `<div>` with onclick.

---

## 10. Open questions Amelia answers in code

These are Amelia's calls (per PRD §7):

- Exact decimal formatting for the count-up: I propose `n.toLocaleString('uz-UZ', { maximumFractionDigits: 0 })` for the big balance card (round to whole UZS), tabular-nums via CSS. RUB/USD when shown gets 2 decimal places.
- Quote admin view: yes, register `Quote` in `quotes/admin.py` with a list display of `text_uz`, `author`, `is_active`. Trivial, ~6 lines.

---

## 11. Hand-off line

> "Amelia — UX spec at `docs/sprint-v0.5-ux-spec.md`, PRD at `docs/sprint-v0.5-redesign-plan.md`. Build Phase 1 → 5 in order, one commit per phase, push and verify 582 tests green between phases. The constraints in PRD §4 are the rule — one Alpine scope per page, CSS animations only, no new deps. Use the voice partial refactor `d3af0ff` as the code-style reference. Reach me only if a design call I left genuinely ambiguous blocks you."
