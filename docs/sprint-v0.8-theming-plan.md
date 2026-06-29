# Sprint v0.8 — Multi-theme System (Future)

**Status:** Planned · not yet scheduled
**Owner:** Sally → John → Amelia
**Trigger:** Public launch readiness. Eric (2026-06-29): *"public qilganimizda kerak bo'ladi"*.

---

## 1. The pitch

Today every screen renders with the Sprint v0.7 dark-neon palette. After launch we want users to pick one of **4–5 named themes** the same way they pick a language — once in Settings, and the whole app reskins.

Why this works cheaply:

- v0.7 already pushed every colour through `static/css/tokens.css`. All surfaces, ink, gradients, glows, and shadows resolve from CSS custom properties. Templates use `var(--*)`, never hex literals.
- Switching themes is just swapping the values of those custom properties. No template churn, no JS rewrites, no Tailwind rebuild.

So v0.8 is mostly a *delivery* sprint, not an *engineering* sprint. The hard part (token discipline) is already paid for.

---

## 2. Architecture

### 2.1 Token layering

Two tiers, both in `static/css/tokens.css`:

| Tier | Scope | Examples |
| --- | --- | --- |
| **Base tokens** | Theme-agnostic. Stay constant. | `--motion-micro`, `--space-4`, `--radius-card`, `--text-h1-*`, typography family |
| **Theme tokens** | Vary per theme. Selected by data-attribute on `<html>`. | Every `--color-*`, every `--gradient-*`, every `--shadow-*`, `--glow-*` |

Theme tokens are scoped by `[data-theme="<name>"]`:

```css
:root,
[data-theme="neon-dark"] {
  --color-bg: #0A0F0C;
  --color-primary: #9FF87C;
  /* …current v0.7 palette */
}

[data-theme="indigo-dark"] {
  --color-bg: #0E0E1A;
  --color-primary: #8B7AFF;
  /* … */
}

[data-theme="warm-light"] {
  --color-bg: #FAF8F5;
  --color-primary: #E76B3D;
  /* … */
}
```

The default block also lives under `:root` so users who never picked a theme still get something.

### 2.2 Activation

`<html data-theme="{{ active_theme }}">` set server-side from `user.theme_slug`. Theme switch endpoint mutates the field and forces a full page reload (no SPA dance, no FOUC — CSS cascade resolves the new tokens on the next paint).

Optional progressive enhancement: a small JS snippet in `base.html` reads `localStorage.iw-theme` and applies the data-attribute before paint, so anonymous / pre-auth pages also honour the preference.

### 2.3 Browser chrome colours

`<meta name="theme-color">` (Telegram WebApp chrome) must update with the theme. Server-renders the matching `theme-color` from a small map keyed by the active theme.

---

## 3. Proposed themes (4–5 candidates)

These are starting points — Sally will refine before implementation.

| Slug | Name (UI) | Mood | Brand colour | Surface |
| --- | --- | --- | --- | --- |
| `neon-dark` | Neon (default) | Current v0.7 — vibrant emerald on near-black | `#9FF87C` | `#0A0F0C` |
| `indigo-dark` | Tungi binafsha | Indigo / violet, calmer | `#8B7AFF` | `#0E0E1A` |
| `sunset-dark` | Quyosh botishi | Warm amber / coral on espresso | `#FF8A3D` | `#1A0F0A` |
| `warm-light` | Quyoshli | Soft beige / off-white, terracotta accent | `#E76B3D` | `#FAF8F5` |
| `mono-paper` | Qog'oz | High-contrast monochrome, paper-feel | `#0F0F0F` | `#FFFFFF` |

Notes:
- Two dark + one warm-light + one cool-light + one mono gives users meaningful range without analysis paralysis.
- Every theme must hit WCAG AA (4.5:1 for body text, 3:1 for large UI text). Light themes need a different `--shadow-*` set (lighter, less saturated).
- Gradients and glow halos vary per theme. `--gradient-hero` and `--gradient-cta` are theme-defined.

---

## 4. Migration prerequisites (already done in v0.7)

- ✅ Every template uses `var(--*)` for color, background, border, shadow.
- ✅ `app.css` `@layer components` (`.btn-primary` / `.btn-secondary` / `.card-default`) resolves to tokens.
- ✅ `_voice_quick_button` migrated off hardcoded emerald gradient (Sprint v0.7 follow-up).
- ✅ `_balance_hero` uses `--color-on-hero` for ink-on-gradient.
- ✅ `_recurring_card`, `_error_partial`, `_close_form` migrated to tokens.

Remaining inline hex (intentionally left for v0.8 audit):
- `core/templates/base.html` — `<meta theme-color>` and the debug-panel JS lines. These need a per-theme JS pickup.
- `voice/templates/voice/_voice_button.html` — legacy partial only rendered by tests. Either delete (probably) or token-ise alongside the v0.8 work.

---

## 5. Scope (when scheduled)

**Sprint v0.8 commits (estimate):**

1. **Token expansion** — promote every theme-variable group into one `[data-theme="…"]` block per theme. Keep `:root` defaults pointing at neon-dark.
2. **User model** — add `User.theme_slug` (charfield, default `"neon-dark"`). Migration.
3. **Settings UI** — new `_list_row` entry "Mavzu" → bottom sheet with the 4–5 theme tiles (preview swatch + label). Tap → POST → reload.
4. **Server wiring** — `core/views.base` context processor injecting `active_theme`. `base.html` uses it on `<html data-theme>` and `<meta theme-color>`.
5. **Anonymous fallback** — localStorage-backed pre-paint set in `base.html`.
6. **Theme audit** — visual QA pass per theme on every page (Home, Add, History, Edit, Settings, Debts, Reports, Voice sheet, Onboarding).
7. **Lint hook** — extend the existing pre-commit check (or add a sibling) to fail CI if any hex literal lands in `*.html` outside `tokens.css`.

Each ships independently; tests stay green between.

---

## 6. Non-goals

- Per-component theming. Themes are app-wide only — no "dark home, light reports" mixing.
- User-defined themes / custom palettes. Out of scope; reconsider later if churn.
- Auto-theme by system preference (`prefers-color-scheme`). The Telegram WebApp container doesn't always pass this through reliably; explicit choice is simpler and more predictable.

---

## 7. Open questions for John (PM)

- Do we charge for premium themes? (My take: no — themes are launch table-stakes, not monetisation.)
- Localised theme names? (Yes — Uzbek labels matching the project's i18n approach.)
- Do we tease the theme selector pre-launch to drive Settings discovery? (My take: yes, show a "Yangi: Mavzular" coachmark once on Home after upgrade.)
