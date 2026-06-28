# Sprint v0.5 — Premium UX Refresh PRD

**Author:** John (PM) — 2026-06-28
**Hand-off chain:** John → Sally (UX) → Amelia (Dev)
**Mode:** Autonomous execution. Eric is on another project; ship without per-step check-ins.

---

## 1. Why this sprint exists

Eric road-tested v0.4 end-to-end. Functionally everything works (voice transcribes, debts close, reports render, 582 tests green). His verdict on the *experience*:

> "Hozirgi ranglar jilosiz, devorga bo'yalib 10 yildan kegin o'chib ketganga o'xshaydi. Animatsiya yo'q. 20 yil oldingi sayt ko'rinishida. Saytni buzib qo'yyabdi og'ir ishlashi."

Translation: the app works but feels dated, dull, and slow. Sprint v0.4 was about *capability*. Sprint v0.5 is about *feel* and a handful of UX corrections that surfaced during real use.

This sprint also fixes one real **data bug**: borrowing money (debt_borrowed) doesn't currently flow into cash balance even though the user physically received the cash.

---

## 2. Out of scope (explicit)

- New domain features. No new transaction types, no new reports.
- i18n. Uzbek-only stays.
- Telegram bot push redesign. The bot send path stays as-is from Epic 9.
- Settings hub *contents* beyond Kategoriyalar / Takrorlanuvchi / Valyuta — full Settings (theme picker, account delete, etc.) is Sprint v0.6.

---

## 3. Goals

1. **Premium feel.** Newer color palette, depth (shadows, gradients), smooth motion. The app should look like 2026, not 2010.
2. **Smooth, fast.** CSS-only animations. No JS animation libs. Aim < 16ms paint per interaction on a mid-range phone.
3. **Information hierarchy.** Home page leads with what Eric actually looks at (inflow, outflow, balance), demotes the rest.
4. **Five-tab nav** with an elevated centre **+** primary action, replacing the redundant "voice/manual" pair on Home.
5. **Correct cash math.** Borrowing increases cash, lending decreases it. Sof balance still reflects net obligations.

---

## 4. Hard constraints for Amelia

Eric is explicit: **"Amelia juda sodda kod yozsin. Hozirgaga o'xshash trash murakkab ishlamedigon kod yozmasdan, sodda aniq tushunarli kod yozsin."**

These are non-negotiable:

- **One Alpine x-data per page.** No nested `Alpine.data()`. No `$dispatch` round-trips between components. The voice partial refactor (commit `d3af0ff`) is the reference style — copy it.
- **No chained getters.** If a binding depends on `kept.filter(...).length`, make it a getter on the same component. No `headerLabel → keptCount → kept` chains where Alpine loses dep tracking.
- **No `$root` for data access.** `$root` is a DOM element in Alpine 3, not a parent scope. Anything that looks like cross-component coordination is the smell of an over-decomposed component.
- **CSS over JS for motion.** Use `transition`, `@keyframes`, `:hover`, `:active`. No `requestAnimationFrame` loops, no animation libraries.
- **No new dependencies.** Tailwind 4, Alpine 3, htmx 2. That's it.
- **Inline styles for layout-critical CSS** that uses Tailwind classes not in the cached build (`min-h-screen`, `text-7xl`, custom keyframes). Common utilities are safe.

---

## 5. Phased delivery

Five phases. Each phase is one commit, runs all 582 tests green, and is independently shippable. Eric tests between phases.

### Phase 1 — Home redesign + cash math fix

**The data fix.** `transactions.selectors.month_summary` returns `cash_balance = income - expense`. Debts are not included. Fix:

- `inflow_total = income_total + debt_borrowed_total`
- `outflow_total = expense_total + debt_lent_total`
- `cash_balance = inflow_total - outflow_total`

The existing `total_income` / `total_expense` fields stay (some templates depend on them); add the three new fields above. Update `core.views.home_content` to pass the new fields.

**The UX.**

```
┌────────────────────────────────┐
│ [valuta switcher]              │  ← right-aligned, no greeting yet (Phase 3 adds quote)
│                                │
│ ┌──────────┐  ┌──────────┐     │  Inflow card     Outflow card
│ │ ↗ Kirim  │  │ ↘ Chiqim │     │  emerald tint    rose tint
│ │ 500k UZS │  │ 56k UZS  │     │  small icon      small icon
│ └──────────┘  └──────────┘     │
│                                │
│ ┌────────────────────────────┐ │  Joriy balans (big card)
│ │  SOF BALANS                │ │  4xl bold tabular-nums
│ │  444 000 UZS               │ │  optional subtle gradient
│ │  Iyun 2026                 │ │
│ └────────────────────────────┘ │
│                                │
│ ENG KO'P SARFLANDI             │  unchanged
│ ⋯                              │
│                                │
│ ┌────────────────────────────┐ │  Voice CTA — big primary
│ │  🎤  Ovoz bilan qo'shing   │ │  emerald, full width, hover lift
│ └────────────────────────────┘ │
└────────────────────────────────┘
```

**Removed from Home:**
- "Salom, Erkaboy!" greeting (Phase 3 brings the quote system back into this slot)
- The 3-stat strip (Naqd / Sof / Qarz holati) — folded into the big Joriy balans card
- "✏️ Qo'lda yozish" button — moved to nav center in Phase 2
- Footer links `⚙ Kategoriyalar` and `⏰ Takrorlanuvchi` — see Decision D1 below

**Voice CTA behaviour:** unchanged from current — pressing opens the mic, with the same recording / processing / error states. Just bigger and visually elevated.

**Acceptance criteria:**

1. `month_summary.cash_balance` includes debt_borrowed (+) and debt_lent (-).
2. Home page shows two summary cards above a big balance card, all in the same scope (no htmx re-fetch on tap).
3. Stale-rates banner and currency switcher behave exactly as before.
4. All footer links from BalanceHero are removed; Kategoriyalar / Takrorlanuvchi reachable via the path Sally chooses in §6.
5. No test regressions.

### Phase 2 — Bottom nav redesign with elevated +

Replace the current 5-item nav (Uy / + / Tarix / Qarz / Hisobot) with a refreshed 5-item nav:

```
🏠 Uy    🕐 Tarix    [ ➕ Qo'shish ]    💰 Qarzlar    📊 Analitika
```

The centre item:
- Wider and taller than its neighbours (~68×68 px vs 44×44).
- Sits in a circular emerald-to-emerald-darker gradient.
- Has a soft elevated shadow (`box-shadow: 0 6px 16px rgba(16,185,129,.35)`).
- Anchored slightly above the nav bar baseline (~14 px lift) to look raised.
- Label is the text "Qo'shish" inside, not just a `+` icon.

Tap behaviour: navigates to `/app/transactions/add/` (the existing manual entry form). No new endpoint needed for v0.5.

Other items get a hover/active emerald underline.

**Acceptance criteria:**
1. Nav renders 5 items, centre item visually elevated.
2. Tapping centre opens the existing add transaction page.
3. Voice button removed from nav (it lives on Home as the CTA from Phase 1).
4. No regression on routes — `_nav.html` is the only file the visual change needs.

### Phase 3 — Daily quote system

Replace the removed "Salom, Erkaboy!" greeting with a rotating motivational quote. Eric's specification:

> "Moliya, tartib, odamni fikirlash va dunyo qarashini o'stiradigon kuchli turtki beradigan famous ibora va sayinglar."

**Data model.** New tiny app `quotes/` with one model:

```python
class Quote(models.Model):
    text_uz = models.TextField()
    author = models.CharField(max_length=120)
    source = models.CharField(max_length=120, blank=True)  # book/talk if relevant
    locale = models.CharField(max_length=8, default="uz")
    is_active = models.BooleanField(default=True)
```

Plus a per-user dismissal table:

```python
class QuoteDismissal(models.Model):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    feature_enabled = models.BooleanField(default=True)  # the "don't show again" toggle
```

**Seed data.** A migration ships ~25 curated quotes Eric will appreciate. Pre-launch list (Sally finalizes wording in Uzbek):

- Warren Buffett — "Pulingiz haqida o'ylamasangiz, pul siz haqingizda o'ylab qoladi."
- Charlie Munger — "Maishiy intizom — bu siz pul topishingizdan ko'ra muhimroq narsa."
- Naval Ravikant — "Boylik — bu uxlayotganda ham siz uchun ishlaydigan aktivlar."
- Seneca — "Yo'q, men sizga juda boy emas, men juda kam narsaga muhtoj."
- Morgan Housel — "Bir umrlik tejash bir hafta xarid qilishdan kuchliroq."
- (~20 more in this voice — Sally curates and translates if needed)

**Selection.** Deterministic per-day per-user (so the same person sees the same quote across page refreshes today, but a new one tomorrow): `index = hash(user.telegram_id, today) % active_quote_count`.

**UI.**

```
┌──────────────────────────────── ×┐
│ "Pulingiz haqida o'ylamasangiz,  │
│  pul siz haqingizda o'ylab       │
│  qoladi."                        │
│                — Warren Buffett   │
└──────────────────────────────────┘
```

Soft slate background, italic body, small author line, dismiss `×` in the corner.

Dismissal behaviour:
- Tapping `×` once: hides for this session (cookie / session flag).
- Tapping `×` and confirming "Boshqa ko'rsatilmasin": flips `QuoteDismissal.feature_enabled = False` for that user. Quote stops appearing.
- Re-enable in Settings (Phase 4 hub) via a "Kunlik iboralar" toggle.

**Acceptance criteria:**
1. New `quotes` Django app with migration + seed data (>= 20 quotes).
2. Quote renders above the kirim/chiqim cards on `/app/home/`.
3. Per-day stability + per-user variance.
4. Per-session dismiss + permanent opt-out work.
5. Toggle exposed in Settings hub from Phase 4.

### Phase 4 — Settings hub (the home for orphaned links)

This is **Decision D1** below answered. Need a real Settings page so Kategoriyalar / Takrorlanuvchi / Valyuta / Kunlik iboralar all have a logical home.

**Entry point:** small gear icon top-right of Home (replacing the removed greeting area's right edge). Routes to `/app/settings/`.

**Settings page layout:**

```
← Sozlamalar

Profil
  • Telegram ismi      Erkaboy
  • Til               O'zbekcha (faqat)

Pul
  • Asosiy valyuta    UZS   ›       (writes User.default_currency)
  • Ko'rsatish        Mahalliy / Aylantirilgan  (the existing switcher)
  • Kunlik iboralar   ☑ Ko'rsatish

Kategoriyalar va takrorlanuvchi
  • Kategoriyalar     ›   → /app/settings/categories/  (existing)
  • Takrorlanuvchi    ›   → /app/settings/recurring/   (existing)

Maxfiylik
  • Audio fayllar saqlanmaydi. (info text from FR63)
```

**Acceptance criteria:**
1. `/app/settings/` route renders the hub.
2. Gear icon top-right of Home links to it.
3. All four sub-links work (kategoriyalar + takrorlanuvchi already exist; valyuta + kunlik iboralar are new toggles in the hub itself).
4. No category / recurring view changes — Settings hub is just a landing.

### Phase 5 — Design system upgrade (premium colors + global motion)

Last and largest. This is where the "premium feel" lives. Three deliverables:

**5.1 Color tokens.** Replace the current flat palette with a deeper, richer one:

- Primary emerald: `#10b981 → #047857` (gradient endpoints)
- Background: `#FAFAF7 → #F4F6F2` (subtle warm wash)
- Surface: `#FFFFFF` with soft shadow `0 2px 8px rgba(15,23,42,.06)`
- Inflow accent: `emerald-50 → emerald-600 text`
- Outflow accent: `rose-50 → rose-600 text`
- Borders: `slate-200` → `slate-200/60` (softer)

Sally picks the exact palette. Tokens land in `static/css/tokens.css` and Tailwind extends through `tailwind.config.js`.

**5.2 Motion tokens.** Three durations only:

- Micro (button press, link hover): `120ms ease-out`
- Standard (card expand, sheet open): `220ms cubic-bezier(.2,.8,.2,1)`
- Page transition (htmx swap): `180ms ease`

All defined as CSS variables in `tokens.css`.

**5.3 Interaction polish.** A handful of specific animations:

- **Balance number tween** on first paint and on update. ~400ms count-up using `@keyframes` and CSS `counter-set`. No JS lib.
- **Card press**: `transform: scale(0.98)` on `:active`. 80ms.
- **CTA hover**: lift `translateY(-1px)` + shadow ease.
- **Toast**: slide-in from top, slide-out — already done in `_toast.html`, just retune timings.
- **Bottom-sheet** (category picker, voice confirm): slide up `220ms`. Already wired, just standardize on the motion token.

**Performance budget.** No interaction may queue a layout thrash. Use `transform` and `opacity` for everything that moves. Verify with Chrome DevTools rendering throttle on at least Home + Voice confirm + History.

**Acceptance criteria:**
1. Color tokens applied; visual diff vs current is obviously richer.
2. Motion tokens applied to all transitions; no animation > 400ms.
3. `prefers-reduced-motion: reduce` disables non-essential transitions (keeps opacity).
4. Lighthouse Performance >= 90 on Home.
5. No new JS dependencies.

---

## 6. Decisions (PM made these — Sally and Amelia execute, no further debate)

### D1 — Where do Kategoriyalar and Takrorlanuvchi live?

**Decision:** Both move into a new `/app/settings/` hub (Phase 4). Discoverable from a gear icon top-right of Home.

**Why:** Eric was explicit he didn't know where to put them, and the home page already has too many entry points. Settings hub is the standard mobile-app pattern, scales when more toggles arrive in v0.6.

### D2 — Quote source

**Decision:** Curated DB-backed list, seeded via migration. 20–30 entries at launch. No external API. Authors Eric mentioned domain interest in (finance + Stoic + modern thinking) — Buffett, Munger, Naval, Housel, Seneca, Marcus Aurelius, Taleb.

**Why:** API dependency = latency on Home load. Curated DB = zero runtime cost + Eric can quietly edit via Django admin if a quote bores him.

### D3 — Centre nav `+` opens manual add, not a choice modal

**Decision:** Tap `+` → straight to `/app/transactions/add/`. No "Voice vs Manual" modal.

**Why:** Voice already has its prominent CTA on Home (Phase 1 makes it big). The `+` is the explicit "I want to type" path. A modal between them = friction for the most-used flow.

### D4 — Greeting comes back later, not in this sprint

**Decision:** "Salom, Erkaboy!" greeting does not return. The slot is now the quote card.

**Why:** Eric flagged the greeting as low-value ("bunaqa ogohlantirish o'rniga ... kuchli turtki beradigan ibora"). The quote *is* the greeting.

### D5 — Animations: CSS-only, three durations

**Decision:** All motion uses three documented duration tokens (micro / standard / page). Anything beyond that is rejected at review.

**Why:** Prevents the "every animation has its own timing" sprawl that makes apps feel inconsistent. Three tokens = one designer + one engineer rule.

---

## 7. Open decisions Sally + Amelia inherit

These are *intentionally* left for the next two agents to make in their domains:

- **Exact hex values** for the new color tokens — Sally.
- **Bottom-sheet vs full-page** for the Settings hub — Sally.
- **Decimal formatting** for the count-up number tween (locale, rounding rule) — Amelia (Eric is on UZ locale).
- **Whether to add a quote-history admin view** — Amelia, only if trivial.

---

## 8. Hand-off

When this doc is saved, ping Sally next:

> "Sally — Sprint v0.5 PRD landed at `docs/sprint-v0.5-redesign-plan.md`. Drive Phase 1, 2, 3 UX (color palette, layout sketches, motion list) into `docs/sprint-v0.5-ux-spec.md`. Use Eric's voice/copy: polite Uzbek, 'siz' form, no marketing tone."

After Sally → Amelia:

> "Amelia — PRD at `docs/sprint-v0.5-redesign-plan.md`, UX spec at `docs/sprint-v0.5-ux-spec.md`. Implement Phase 1 → 5 in order. Constraints in §4 of the PRD are non-negotiable. One Alpine scope per page. CSS animations only. Commit per phase, push, verify 582 tests green between phases."

---

## 9. What "done" looks like for the sprint

- All 5 phases shipped to `main`. CI green at every commit. Test count holds at 582+ (a few quote tests will add to it).
- Eric can open the WebApp and the differences are obvious: richer colors, two inflow/outflow cards above the balance, motivational quote on top, elevated `+` in the centre nav, Settings reachable via the top-right gear, balance counts up when it changes.
- The cash math no longer hides borrowed money from the running total.
- No new technical debt. The next agent reading the code agrees with Eric: "sodda, aniq, tushunarli."
