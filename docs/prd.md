---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
releaseMode: phased
partyModeInsights:
  - voice-equal (not voice-first) — manual and voice equal hierarchy on Home
  - timeline v1.0 = 3 months (realistic, per Amelia)
  - yearly report stays — shows months with available data
  - Gemini free tier OK for v1; v2 needs privacy disclosure or Vertex AI
  - v2 future vision — two-sided debt (mutual ledger) for network effects moat
  - strategy — 30d solo, then 5-10 closed beta, then public
inputDocuments:
  - docs/product-brief.md
workflowType: 'prd'
project_name: 'IWALLET'
user_name: 'Eric'
date: '2026-06-25'
classification:
  projectType: web_app
  domain: fintech
  domainNiche: personal_finance_tracker_no_payment_processing
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - IWALLET

**Author:** Eric
**Date:** 2026-06-25

## Executive Summary

IWALLET — Telegram WebApp shaklidagi shaxsiy moliyaviy tracker. Mobile viewport, o'zbek tilida, voice va manual kiritishni **teng huquqli birinchi-class flow** sifatida taklif qiladi. v1 founder-as-user; 30 kunlik shaxsiy sinovdan keyin 5-10 closed beta, so'ngra omma chiqishi.

**Target user.** O'zbek tilida gaplashuvchi, Telegram'ni kun bo'yi ishlatuvchi, shaxsiy pulini Excel/qog'ozsiz tezda yozish istovchi foydalanuvchi. v1 birinchi maqsadi — mahsulot egasi Eric uchun "qo'lda yozish" muammosini butunlay yopish.

**Hal qilinayotgan muammo.** Pul qayerga ketayotgani ko'rinmaydi. Mavjud app'lar (Money Lover, 1Money, CoinKeeper) inglizcha yoki ruscha, manual kiritishga asoslangan, voice'siz, o'zbek konteksti (qarz oldi-berdi mexanikasi, voice intent) hisobga olinmagan. Friction katta — odamlar yozishni tashlab qo'yadi.

### What Makes This Special

**Asosiy farqlar (v1):**

1. **O'zbek voice** — Gemini orqali *"bugun 15k taxi, 30k qahva, 200k oylik"* tipidagi multi-transaction gaplarni real vaqtda tushunadi va strukturalashtiradi.
2. **Telegram-native distribution** — App Store / Play Market install yo'q. Bot orqali bir bosishda ochiladi. O'zbekistonda Telegram penetration ~90%+.
3. **Qarz mexanikasi balansga oqishi** — qarz olgan pul balansga `+`, lekin tag bilan ajraladi; qarz berish chiqim sifatida hisoblanadi. Dashboard 3 ta raqamni ko'rsatadi: **naqd balans · sof balans · qarz holati**.
4. **Voice-equal hierarchy** — Home'da voice va manual teng huquqli; kontekstga qarab foydalanuvchi tanlaydi (taxi'da voice, ofisda manual).

**Core insight.** Voice kiritish friction'ni ~0 ga tushiradi, **lekin public space'da manual ham kerak** — daromad maxfiyligi va ijtimoiy kontekst sabab. Shuning uchun voice-first emas, voice-equal model.

**Future moat (v2).** Ikki tomonlama qarz (*mutual debt ledger*) — har qarz potentsial yangi foydalanuvchi keltirishi orqali viral network effect tug'iladi. v1 dizayni shu yo'lga **ochiq qoldiriladi** (counterparty maydoni — `User` foreign key, hozir `String`).

**Nima uchun foydalanuvchi shuni tanlaydi.**

- Alternatives'da o'zbek voice yo'q
- Alternatives'da qarz hisobi primitive yoki umuman yo'q
- Alternatives'da install/onboarding friction katta
- IWALLET'da — 10 soniyada birinchi tranzaksiya, til mos, kontekst mos

## Project Classification

| O'lcham | Qiymat | Izoh |
|---|---|---|
| **Project Type** | `web_app` | Telegram WebApp — Django server-rendered + htmx, mobile viewport (desktopda ham mobile ko'rinish) |
| **Domain** | `fintech` (personal finance niche) | **No payment processing, no KYC/AML, no custody** — bu standart fintech'dan complexity'ni pasaytiradi |
| **Complexity** | `medium` | Standart web app + voice AI integratsiya + Telegram WebApp auth |
| **Project Context** | `greenfield` | Mavjud kod yo'q, noldan |

**Compliance.** v1 shaxsiy ishlatish — qonuniy talab yo'q. v2 omma chiqishida: O'zbekiston Persdata qonuni (2019), Telegram TOS, Gemini privacy disclosure (free tier paid tier'ga o'tish yoki halol disclaim).

## Success Criteria

### User Success

**v1 — Solo (oy 1-4):**
- Eric (founder) 30 kun ichida **>80%** moliyaviy harakatlarni IWALLET'ga yozadi (qog'oz, Excel, xotira yo'q)
- O'rtacha tranzaksiya kiritish vaqti **< 10 soniya** voice bilan, **< 20 soniya** manual bilan
- Oy oxirida sof balans **±5%** aniqlikda (qo'lda hisoblash bilan solishtirib)
- "Aha!" momenti: birinchi multi-transaction voice (*"bugun 15k taxi, 30k qahva, 200k oylik"*) — 3 ta tranzaksiya 1 ta gapdan 10 soniyada

**v1 — Closed beta (oy 5):**
- 5-10 beta foydalanuvchi 14 kun aktiv ishlatish (kuniga ≥1 tranzaksiya, hech bo'lmaganda 10 kun)
- Voice STT accuracy real foydalanuvchilarda **≥85%**
- NPS interview: 10 ta beta'dan ≥6 tasi "ishlatishni davom etaman"

### Business Success

**v1 (oy 6 — omma chiqishi):**
- Birinchi oyda **100 organic foydalanuvchi**
- 30-kunlik retention **≥30%**
- Go/no-go decision: voice accuracy + retention + infra capacity

**v2 (oy 12 — paid tier):**
- 1000 oylik aktiv foydalanuvchi
- Premium conversion **≥3%**

### Technical Success

- **Voice end-to-end latency**: p50 < 3s, p95 < 6s
- **Voice multi-transaction parsing accuracy**: ≥85%
- **API availability**: 99%
- **Concurrent voice request capacity**: ≥50
- **PostgreSQL data loss**: 0 (daily backup)
- **Telegram WebApp boot time**: < 1.5s 3G'da
- **CBU.uz outage UX'ni bloklamaydi** (stale rate + banner)

### Measurable Outcomes

| Mezon | Maqsad | O'lchash usuli |
|---|---|---|
| Daily Active User (Eric) | 28/30 kun | App log |
| Tranzaksiya kiritish vaqti (voice) | p50 < 10s | Frontend timing event |
| Voice STT accuracy | ≥85% | Confirm screen tahrir foizi |
| 30-kunlik retention (beta) | ≥40% | Cohort analysis |
| Voice failure rate (Gemini error) | ≤5% | Backend log |
| Average qarz yopish vaqti | < 5s | Action log |

## Product Scope

### MVP — v1.0 (3 oy)

**Kirish nuqtalari:**
1. Voice input (single + multi-transaction)
2. Manual input (4 ta tranzaksiya turi)
3. Telegram WebApp auth (initData validation)

**Asosiy ekranlar (6):**
1. Home (joriy oy summary + valyuta switcher + voice/manual teng tugmalar)
2. Add (manual form)
3. History (filter)
4. Debts (2 ta list, close action)
5. Reports (haftalik, oylik, yillik partial)
6. Settings (kategoriyalar, recurring, valyuta default)

**Asosiy funksiyalar:**
- 4 ta tranzaksiya turi (kirim, chiqim, qarz oldim, qarz berdim)
- 3 valyuta (UZS, RUB, USD) + display conversion (CBU.uz, 24h cache + stale fallback)
- Kategoriyalar (preset + user qo'shish, emoji)
- Recurring xarajatlar (eslatish + 1-tap add)
- Telegram Bot push (recurring + debt due)
- Debt state machine (open → closed/partial/cancelled)
- Async voice pipeline (WSGI'ni bloklamaydi)
- Privacy: audio biz tomondan saqlanmaydi

### Growth Features (Post-MVP, v1.1 — v1.5)

- AI tavsiyalar — *"bu hafta 3x ko'p qahva ichdingiz"*
- Premium tier — chuqur statistika, eksport, custom kategoriya cheklovi yo'q
- Receipt OCR — chek surat orqali tranzaksiya
- Budget limits — kategoriya bo'yicha xarajat chegarasi
- Vertex AI ko'chish — privacy va paid tier uchun
- Polish — animatsiyalar, mikro-interactions, dark theme

### Vision (Future, v2+)

- **Ikki tomonlama qarz (mutual debt ledger)** — viral network effect moat
- Multi-user / shared wallet — oilaviy yoki sherikchilik byudjeti
- Bank integratsiyasi (Click, Payme)
- Goal-based saving — *"yangi telefon uchun 6 oyda 5 mln yig'ish"*
- Yillik moliyaviy hisobot AI insights bilan

## User Journeys

### Persona 1 — Eric (founder, primary user, v1)

**Vaziyat.** 28 yosh, frontend dev, NextIN'da ishlaydi. Oyligi 20+ mln so'm UZS + ba'zan USD/RUB freelance. Pul qayerga ketganini hech qachon aniq bilmaydi. Excel'da 2 oy yozdi, tashlab qo'ydi — eriniladi. Telegram'da kuniga 4+ soat.

**Maqsad.** Har bir tranzaksiyani 10 soniyada yozish, oy oxirida "qaerga ketdi" savoliga aniq javob.

**To'siq.** Mavjud app'lar inglizcha, manual input, voice yo'q, o'zbek qarz mexanikasi yo'q. Friction katta.

#### Journey 1.1 — Voice success path (taxi'da)

1. **Opening:** Eric Yandex Taxi'dan tushadi, telefonni oladi. Bot chat'idan WebApp'ni ochadi (1 tap, < 1.5s boot).
2. **Action:** Home ekran ochiladi — yuqorida sof balans, pastda **ikki teng tugma**: 🎤 Voice · ✏️ Qo'lda.
3. **Voice tap:** Mic'ni bosadi, gapiradi: *"Hozir 25k taxi qildim."* 2-3 soniya kutadi.
4. **Confirm:** Confirm screen — bitta karta: `Chiqim · Taxi · 25,000 · UZS · bugun · 25.06.2026`. Tahrir tugmasi bor.
5. **Climax:** "Tasdiqlash" bosiladi → balans yangilanadi, Home'ga qaytadi.
6. **Resolution:** 8 soniyada hammasi tugadi. Eric piyoda yo'lda davom etadi. Birinchi marta — hayron: *"Shu darajada oson edimi?"*

**Reveal qiluvchi capability'lar:** voice STT, single-transaction parsing, confirm/edit UI, instant balance update.

#### Journey 1.2 — Multi-transaction voice (kun oxirida)

1. **Opening:** Eric uyda, oqshom. Bugun 5 ta xarajat qildi, hech birini yozmagan.
2. **Action:** WebApp ochib, mic bosadi: *"Bugun ertalab 15k metro, peshindan 80k osh, kechqurun 30k qahva, va Akramga 500 ming qarz berdim."*
3. **Confirm:** Confirm screen — **4 ta karta** scroll qilinadigan list. Har biri editable, har biri o'chiriladigan. Pastda jami summary: `4 ta tranzaksiya · −125,000 UZS + qarz 500,000 UZS`.
4. **Edit:** Eric 3-chi kartani ko'radi — qahva 30k emas, 35k edi. Tahrir bosib summa o'zgartiradi.
5. **Climax:** "Hammasini saqlash" bosadi → 4 ta tranzaksiya atomic save.
6. **Resolution:** 25 soniyada 4 ta tranzaksiya yozildi. Eric: *"Ertaga ham shunday qilaman."*

**Reveal qiluvchi capability'lar:** multi-tx parsing, batch confirm UI, per-card edit/delete, atomic save, currency unit parsing ("k" = ming, "ming" = ming, "mln" = million).

#### Journey 1.3 — Edge case: voice failure / partial parse

1. **Action:** Eric mic bosadi, lekin shovqinli yo'lda: *"Bugun 15... no, 25 mingmi, ehh, taxi qildim."*
2. **Gemini response:** 1 ta valid draft (`Chiqim · Taxi · ?`) summa noaniq.
3. **Confirm screen:** Karta sariq border bilan — *"Summa noaniq. Iltimos, kiriting."* Inline numpad ochiladi.
4. **Recovery:** Eric `25000` kiritadi, tasdiqlaydi.

**Reveal qiluvchi capability'lar:** partial parse handling, ambiguity flagging, inline edit, error recovery without losing context.

#### Journey 1.4 — Manual input (ofisda, mic'siz)

1. **Opening:** Eric ofisda, ko'p odam atrofda, oylik tushdi. Voice bosishni xohlamaydi.
2. **Action:** Home → ✏️ Qo'lda → modal/screen ochiladi.
3. **Tap flow:** Turi tanlaydi (Kirim) → kategoriya (Oylik) → numpad (`12000000`) → valyuta (UZS default) → Save.
4. **Resolution:** 12 soniyada tugadi. Voice'siz ham friction past.

**Reveal qiluvchi capability'lar:** manual form, numpad UX, category quick-select, voice-equal Home (manual emas "ikkinchi darajali").

#### Journey 1.5 — Debt close action (asymmetric edge case)

1. **Vaziyat:** Eric 3 hafta oldin Akramga 500k qarz berdi (Journey 1.2 dan). Akram bugun 300k qaytardi.
2. **Action:** Debts ekran → "Akramga bergan qarz: 500k" qator → "Qaytarish" tugmasi.
3. **Dialog:** "Qancha qaytarildi?" → `300000` → Save.
4. **State:** Qarz partial-closed (200k qolgan). Akram qator: `−200k UZS · 1 ta qisman to'lov`.
5. **Climax:** Bir hafta keyin Akram qolganini qaytaradi. Eric yana "Qaytarish" → `200000` → debt fully closed → balans yangilanmaydi (qaytgan pul kirim emas, debt return).

**Reveal qiluvchi capability'lar:** debt state machine (open → partial → closed), partial repayment, no double-counting of returned debt.

### Persona 2 — Malika (closed beta user, v1 oy 5)

**Vaziyat.** 32 yosh, marketing manager. Eric'ning tanishi. Telegram'da kun bo'yi, biroz English biladi. Oyligi UZS, oilaviy budjet.

**Maqsad.** Tezroq hisob, oyligi qaerga ketganini do'sti Eric'ga aytmoqchi.

#### Journey 2.1 — Onboarding (birinchi kun)

1. **Opening:** Eric Telegram'da link yuboradi. Malika bosadi → bot ochiladi → "Boshlash" → WebApp ochiladi.
2. **Action:** Onboarding card ko'rinadi — *"IWALLET — pulingni 10 soniyada yozasan. Voice yoki qo'lda. Birinchi yozuvni qilamizmi?"*
3. **Mic permission card:** *"Voice ishlatishni xohlasangiz mic ruxsati kerak. Audio biz tomondan saqlanmaydi, faqat Google Gemini'ga matnga aylantirish uchun yuboriladi."* — bu kontekst-bilan tushuntirish (Sally'ning insight).
4. **First transaction:** Malika "Keyinroq" deydi mic'ga, manual'ga o'tadi. Birinchi kirim: oylik 8 mln UZS. Hammasi 25 soniya.
5. **Resolution:** Home ekran sof balans 8 mln ko'rsatadi. Confidence yuqori.

**Reveal qiluvchi capability'lar:** onboarding flow, deferred mic permission (no panic), first-transaction success path.

#### Journey 2.2 — Recurring expense setup

1. **Action:** Settings → Recurring → "+ Qo'shish" → "Har oy 1-chisida — Ijara 2.5 mln UZS · Chiqim".
2. **Climax:** Oy bahsiga keladi → bot push: *"Bugun ijara to'lash kuni. Yozayinmi? [Ha — 1 tap] [Yo'q] [Tahrir qilish]"*.
3. **Resolution:** Malika "Ha" bosadi → tranzaksiya avtomatik yaratiladi → Telegram chat'ida tasdiq xabari.

**Reveal qiluvchi capability'lar:** recurring CRUD, scheduled bot push, 1-tap confirmation, deep-link from bot to WebApp action.

### Persona 3 — Adminstrative / Operations user (Eric o'zi, v2 dan keyin)

Bu hozircha out-of-scope, lekin v2 da omma chiqishi paytida moderator/support tool kerak bo'lishi mumkin (foydalanuvchi murojaatlari, debt dispute). v1 PRD'ga shu qayd qilinadi, dizayn v2 da.

### Journey Requirements Summary

Yuqoridagi journey'lar quyidagi capability'larni ochib beradi (FRs'da to'liq ro'yxat):

- **Auth & onboarding:** Telegram WebApp auth, first-run onboarding, deferred permission asks
- **Voice input pipeline:** STT, intent parse, single + multi parse, partial/error handling, edit-before-save
- **Manual input pipeline:** form-based CRUD, numpad UX, category quick-select
- **Transactions:** 4 ta turi (kirim/chiqim/qarz oldim/qarz berdim), filter, history
- **Debts:** state machine (open/partial/closed), partial repayment, dual list (kim qarzdor / men qarzdorman)
- **Categories:** preset + custom, emoji, CRUD
- **Multi-currency:** UZS/RUB/USD store-as-is, display-convert via CBU.uz, stale fallback
- **Recurring:** schedule, bot push, 1-tap confirm
- **Notifications:** Telegram Bot push, deep-links to WebApp actions
- **Reports:** weekly/monthly/yearly with partial data display
- **Settings:** language, default currency, categories, recurring

## Domain-Specific Requirements

`fintech` domeni, `personal_finance_tracker_no_payment_processing` niche. Standart fintech complexity'dan engil — to'lov ishlash yo'q, KYC/AML yo'q, custody yo'q. Lekin shaxsiy moliyaviy ma'lumotlar uchun **data integrity va privacy** asosiy.

### Compliance & Regulatory

- **v1 (shaxsiy ishlatish):** Hech qanday qonuniy talab yo'q.
- **v2 (omma chiqishidan oldin):**
  - O'zbekiston "Shaxsiy ma'lumotlar to'g'risida" qonuni (LRU-547, 2019) — foydalanuvchi roziligini olish, ma'lumotlarni mahalliy saqlash talabi (hosting O'zbekiston'da bo'lishi mumkin, lekin Telegram saqlash'iga tushadigan ma'lumotlar alohida)
  - Telegram WebApp TOS — initData validation majburiy, Telegram brand guideline
  - Gemini privacy — free tier uchun foydalanuvchiga aniq disclaim (audio Google'ga yuboriladi va training'da ishlatilishi mumkin), yoki Vertex AI'ga ko'chish

### Technical Constraints

- **Data integrity (kritik):** Hech qachon `Float` ishlatma. `Decimal(15,2)` UZS/RUB uchun (1 trillion + 2 kasr), `Decimal(15,2)` USD/EUR uchun (bir xil schema).
- **Audit trail (yengil v1):** Har tranzaksiya `created_at`, `updated_at` saqlaydi. Tahrir tarixi v1 da yo'q, v2 da qo'shiladi (compliance va dispute uchun).
- **Privacy boundary:** Audio fayllar **bizning server'imizda saqlanmaydi** — Gemini'ga stream qilinadi va o'sha ondayoq tashlanadi. Backend log'larda audio bo'lmasligi kerak (request body logging audio request'lar uchun o'chirilgan).
- **initData validation:** Har request'da HMAC-SHA256 bilan, `auth_date` ≤ 24 soat. Session cache yo'q.
- **No payment processing:** PCI-DSS scope'idan tashqari. Karta ma'lumoti hech qachon kiritilmaydi yoki saqlanmaydi.

### Integration Requirements

- **Gemini API** (Google AI Studio):
  - Use case: speech-to-text + intent parsing (single call, structured output)
  - Model: `gemini-2.0-flash` yoki yangiroq (audio understanding bilan)
  - Failure: graceful (user'ga "qaytib urinish" yoki manual fallback)
- **CBU.uz API** (Markaziy Bank):
  - Use case: kunlik UZS/RUB/USD kurs
  - Refresh: kuniga 1 marta (cron job, 09:00 Toshkent)
  - Failure: stale rate qaytariladi + "kurs eski" banner UI'da
- **Telegram Bot API:**
  - Use case: push notifications, deep-link from bot chat to WebApp action
  - Webhook mode, separate process from WebApp
- **Telegram WebApp SDK:**
  - Use case: initData (auth), `MainButton`, theme detection (optional v1)

### Risk Mitigations

| Risk | Mitigation |
|---|---|
| Gemini ovoz ma'lumotini training'da ishlatadi | v1: Eric uchun qabul qilingan. v2: Vertex AI yoki halol disclosure + opt-in |
| CBU.uz outage | Stale rate fallback + UI banner |
| WSGI worker blocked by Gemini latency | Async views + Celery yoki gevent workers |
| Telegram WebApp iframe quirks | Polling-based htmx (SSE emas) |
| Multi-currency conversion confusion | Reports'da har valyuta alohida ko'rsatish, "konvertatsiya kursi" alohida label |
| Debt partial repayment edge cases | State machine + explicit `repayments` table (one-to-many) |

## Innovation & Novel Patterns

Innovation signal'lari aniqlandi — bu loyiha incremental emas, bir nechta novel pattern bor.

### Detected Innovation Areas

1. **O'zbek voice-first personal finance** — O'zbek tilida voice STT + intent parse + finance domain bilan birga ishlovchi mahsulot mavjud emas (Mary'ning analizi).
2. **Multi-transaction voice parsing** — Voice'da bir gapda 3-5 ta turli tranzaksiya: industry standart emas. Mavjud apps (Money Lover, etc.) faqat ekran orqali bir-bittadan kiritish taklif qiladi.
3. **Telegram-native distribution + WebApp viewport-only** — Personal finance app'lar odatda native iOS/Android. Telegram WebApp'da to'liq finance UX'ni qurish kam tarqalgan pattern.
4. **Voice-equal hierarchy** — Standart UX patterns: voice-first (Siri, ChatGPT) yoki manual-first (Money Lover). Bizning hybrid voice-equal — context'ga ko'ra teng — kam ishlatiladigan dizayn qarori.
5. **Debt mechanics balansga oqishi (asymmetric)** — Borrowed = balance+, Lent = expense, Repayment = special close action. Mavjud trackers debt'ni alohida modul qiladi, balansga oqmasdan. Bizning yondashuv — accounting jihatdan to'g'ri va UX jihatdan tushunarli.

### Market Context & Competitive Landscape

| Mahsulot | Voice | Uzbek | Telegram-native | Multi-tx | Qarz | Narx |
|---|---|---|---|---|---|---|
| Money Lover | ❌ | ❌ | ❌ | ❌ | ⚠️ primitive | Freemium |
| 1Money | ❌ | ❌ | ❌ | ❌ | ❌ | Freemium |
| CoinKeeper | ❌ | ❌ | ❌ | ❌ | ⚠️ | Freemium |
| Wallet by BudgetBakers | ❌ | ❌ | ❌ | ❌ | ✅ | Premium |
| Excel/qog'oz | ❌ | ✅ | — | — | manual | Bepul |
| **IWALLET** | ✅ | ✅ | ✅ | ✅ | ✅ | Bepul v1 |

### Validation Approach

Innovation'larni real validatsiya qilish rejasi:

1. **Voice STT accuracy** (Mary skepticism'ga javob): 100 ta o'zbekcha test gap (kun, summa, kategoriya kombinatsiyalari) — Gemini'ga yuborib aniqlik o'lchaymiz. **Target: ≥85% to'g'ri parse.** O'lchov: tahrirlanmagan draft foizi.
2. **Multi-tx parsing**: 50 ta kombinatsiya gap (2-5 tranzaksiya bir gapda) — partial parse rate, type confusion rate o'lchanadi.
3. **Voice-equal hypothesis**: Closed beta'da analytics — voice vs manual usage ratio. Agar ratio ekstrem (95% bir tomonda) — model noto'g'ri, qayta ko'rib chiqamiz.
4. **Telegram-native retention**: 30-kunlik retention 30%+ bo'lsa — distribution channel to'g'ri tanlangani isbotlanadi.

### Risk Mitigation

| Innovation | Risk | Fallback |
|---|---|---|
| O'zbek voice STT | Aniqlik 70%'dan past | Manual fully functional — voice ixtiyoriy |
| Multi-tx parsing | Edge case'lar ko'p | Single-tx fallback har doim ishlaydi |
| Telegram-native | Telegram TOS yangilansa cheklov | Standalone PWA backup plan v2 |
| Voice-equal | Userlar bittasini ko'p ishlatmasa | Adaptive UI v2 (smart default) |
| Debt asymmetric model | User chalkashishi | UI'da aniq labels + onboarding tutorial |

## web_app Specific Requirements

`web_app` project type — Telegram WebApp container, mobile viewport-only.

### Project-Type Overview

IWALLET — server-rendered web application Django shabloni asosida, htmx bilan kuchaytirilgan dinamik UI parchalari. Standalone SPA emas. Telegram WebApp ichida ishlaydi, lekin browser'da ham ochilishi mumkin (debug uchun). Mobile viewport — har doim 360-430px width assumption.

### Technical Architecture Considerations

- **Server-rendered (SSR)** — Django templates, page navigation HTTP yoki htmx swap orqali
- **Progressive enhancement via htmx** — JS minimum, faqat htmx + alpine.js (agar kerak bo'lsa state uchun)
- **Mobile viewport lock** — `<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">`, max-width container ~430px
- **Telegram WebApp SDK** — `telegram-web-app.js` bootstrap, `initData` har request'da Authorization header'da
- **No PWA** v1 da — offline mode out-of-scope

### Browser Matrix

| Browser | Versiya | Support |
|---|---|---|
| Telegram iOS WebView | Safari 15+ asoslangan | **Primary** |
| Telegram Android WebView | Chromium 100+ | **Primary** |
| Telegram Desktop WebView (mobile mode) | Chromium 100+ | Best-effort |
| Standalone Chrome/Safari mobile | Latest | Debug/testing |

### Responsive Design

- Mobile-only viewport (360px - 430px width)
- Touch-first interactions (44×44px minimum tap target)
- Bottom-sheet patterns for modals (thumb reach)
- Sticky top bar (balance + currency switcher)
- Bottom nav (5 ekran: Home, Add, History, Debts, Reports — Settings bosh menyu'da)

### Performance Targets

- **Boot time (cold cache, 3G):** < 1.5s to interactive
- **htmx swap latency (typical):** < 200ms server response
- **Voice end-to-end:** p50 < 3s (mic stop → confirm screen), p95 < 6s
- **JS bundle size:** < 50KB gzipped (htmx + alpine + custom)
- **CSS bundle:** < 30KB gzipped

### SEO Strategy

**N/A** — Telegram WebApp ichida ishlaydi, public web'da indeksatsiya kerak emas. `noindex` meta tag.

### Accessibility Level

- **WCAG 2.1 AA** ga intilamiz mobile context'ida
- Voice input — bu accessibility'ning + tomoni (motor impairment'lar uchun)
- Color contrast ≥ 4.5:1
- Touch target ≥ 44×44px
- Aria labels for icon-only buttons
- Telegram theme detection (light/dark) v1 da — out of scope, faqat light theme

### Implementation Considerations

- **Auth pattern:** custom Django middleware `TelegramAuthMiddleware` — `initData` HMAC validate qiladi, user'ni `request.user` ga qo'yadi (Django'ning standart `AuthenticationMiddleware` o'rniga)
- **Voice flow pattern:** browser MediaRecorder API → POST audio (multipart) → Django async view → Gemini API call → JSON draft list → htmx swap to confirm screen
- **State management:** Django session minimum, htmx hyperscript-style local state, no React/Vue
- **Build tools:** Django collectstatic + Tailwind CSS CLI (yoki UnoCSS), no webpack/vite

## Scoping Strategy & Risks

### MVP Strategy & Philosophy

**MVP Approach: Problem-solving MVP** — biz validatsiya qilamiz: "voice + manual bilan kun davomida personal finance yozish — odat shaklida ishlaydimi?" Bu *experience* MVP emas (polish v0.1 da minimal), revenue MVP emas (paid tier yo'q).

**Resource Requirements (3 oy):**
- **1 dev** (Eric o'zi, Amelia hand-off bilan) — full-stack Python/Django + htmx + frontend
- **0.25 designer** (Sally hand-off — wireframes/Figma key ekranlar uchun)
- **0.1 architect** (Winston hand-off — pipeline va data model decisions)
- **Infra:** kichik VPS (2 vCPU, 4GB RAM) + managed PostgreSQL — ~$20/oy
- **API:** Gemini free tier (1500 req/day cap), CBU.uz bepul

### Phased Delivery Plan

Phased delivery — Eric ravshan vaqt budget'i bor (3 oy v1.0'gacha).

#### Phase v0.1 (Hafta 1-2) — Manual CRUD Foundation

**Maqsad:** Eric manual'da 4 ta tranzaksiya turini yoza oladi va Home'da balans ko'radi.

**Capabilities:**
- Telegram WebApp auth (initData middleware)
- 4 ta tranzaksiya turi manual input
- Home — sof balans, top 3 kategoriya
- History — list + basic filter
- Categories — preset only (yet)
- UZS only (multi-currency yet)

**Out of phase:** Voice, debts ekran, recurring, reports, multi-currency.

#### Phase v0.2 (Hafta 3-5) — Voice (single transaction)

**Maqsad:** Voice → Gemini → bitta tranzaksiya draft → confirm.

**Capabilities:**
- Voice recording (MediaRecorder)
- Async Django endpoint
- Gemini integration (single intent)
- Confirm screen (single card, editable)
- UZS unit parsing ("k", "ming", "mln", "million")
- Categories CRUD (user-add)

**Out of phase:** Multi-tx voice, multi-currency, recurring.

#### Phase v0.3 (Hafta 6-9) — Multi-tx Voice + Debts + Recurring

**Maqsad:** Power features.

**Capabilities:**
- Multi-transaction voice parsing (partial-success handling)
- Debts ekran (2 list, state machine, partial close)
- Recurring expenses CRUD + scheduler
- Multi-currency (UZS/RUB/USD store + manual select)
- CBU.uz integration (display conversion)

**Out of phase:** Reports, push notifications.

#### Phase v0.4 (Hafta 10-11) — Reports + Notifications

**Maqsad:** Insights + retention loops.

**Capabilities:**
- Reports — haftalik (pie+bar), oylik (trend, top 5, currency split)
- Yillik report scaffolding (data bo'lsa ko'rsatadi, "yetarli data yo'q" empty state)
- Telegram Bot service (alohida process, webhook mode)
- Bot push — recurring kuni, debt due date
- Deep-link bot → WebApp action

**Out of phase:** AI insights, premium features.

#### Phase v1.0 (Hafta 12) — Polish + Self-trial

**Maqsad:** Eric 30 kun ishlatishga tayyor bo'lgan polished product.

**Capabilities:**
- UX polish (animations, micro-interactions, error states)
- Onboarding flow (first-run, mic permission contextual)
- Settings ekran to'liq (kategoriya CRUD, recurring management, valyuta default)
- Loading/empty/error states har joyda
- Manual QA pass

### Risk Mitigation Strategy

| Risk turi | Risk | Mitigation |
|---|---|---|
| **Texnik** | Voice STT accuracy past — Gemini o'zbek tilini yetarli tushunmaydi | v0.2 oxirida real-world 100 gap test → ≥85% bo'lmasa scope qisqartiriladi (manual focus) |
| **Texnik** | Multi-tx parsing complexity 80/20 trap | v0.3 budgeted 4 hafta (1 emas). Edge case'lar release blocker emas, log + iterate |
| **Texnik** | WSGI blocking voice scalability | v0.2 dan boshlab async views + httpx, gunicorn gevent workers |
| **Texnik** | Telegram Bot + WebApp auth sync | Single `User` model, `telegram_id` PK, har request'da revalidate. Middleware first hafta |
| **Texnik** | CBU.uz outage | Stale rate fallback day 1, UI banner |
| **Bozor** | Closed beta'da retention past (<40%) | Go/no-go gate oy 5 oxirida. Yo retention'ni tuzatamiz, yo public release kechiktiriladi |
| **Bozor** | "Voice ishlatmaymiz" — userlar manual bilan kifoyalanadi | Voice-equal model bu risk'ni allaqachon yumshatadi. Analytics'da ratio kuzatiladi |
| **Resurs** | Eric vaqt yetishmasligi (full-time dev emas) | Scope reduction yo'l xaritasi: yillik report → quarterly only, multi-currency → UZS only, recurring → manual only |
| **Resurs** | Gemini free tier 1500 req/day cap yetmaydi | Closed beta paid tier (Vertex AI'ga ko'chish) — taxminan $20-50/oy |

## Functional Requirements

Bu **capability contract** — UX dizayn, arxitektura va story breakdown faqat shu yerda yozilganlarni qo'llab-quvvatlaydi. Yo'q FR = yo'q feature.

### Authentication & Onboarding

- **FR1:** Foydalanuvchi Telegram bot orqali WebApp'ni ochishi va avtomatik autentifikatsiyadan o'tishi mumkin (`initData` HMAC validation).
- **FR2:** Tizim har request'da `initData` HMAC va `auth_date` (≤ 24 soat) ni qayta validate qiladi.
- **FR3:** Birinchi marta kirgan foydalanuvchi onboarding ekranini ko'radi (3-card max: ne, qanday ishlaydi, mic permission contextual prompt).
- **FR4:** Foydalanuvchi mic permission'ni keyinroq berishi mumkin (deferred consent, manual flow har doim ochiq).

### Transaction Management (Core)

- **FR5:** Foydalanuvchi 4 turdagi tranzaksiya yarata oladi: kirim, chiqim, qarz oldim, qarz berdim.
- **FR6:** Har tranzaksiya majburiy maydonlarga ega: turi, summa, valyuta, sana. Qo'shimcha: kategoriya, manba/shaxs, note.
- **FR7:** Foydalanuvchi mavjud tranzaksiyani tahrirlay oladi (summa, kategoriya, note, sana).
- **FR8:** Foydalanuvchi tranzaksiyani o'chira oladi (soft-delete v1 da — undo imkoniyati uchun 7 kun).
- **FR9:** Tranzaksiya sanasi default `bugun`, lekin foydalanuvchi orqaga sana qo'ya oladi (calendar pick yoki "kecha"/"o'tgan hafta" quick shortcuts).

### Manual Input

- **FR10:** Foydalanuvchi Home'dan "✏️ Qo'lda" tugmasi orqali manual input flow'ga kira oladi.
- **FR11:** Manual flow: turi → kategoriya → summa (numpad) → valyuta → save (maks 4 ta tap state).
- **FR12:** Numpad katta, mobile-friendly; "ming/mln" shortcut tugmalari (1k = 1000, 1mln = 1000000).
- **FR13:** Save tugmasi bosilgach foydalanuvchi Home'ga qaytariladi va yangi balans ko'radi (instant feedback).

### Voice Input

- **FR14:** Foydalanuvchi Home'dan "🎤 Voice" tugmasi orqali audio yozib olishni boshlay oladi.
- **FR15:** Audio recording 60 soniya maksimum, foydalanuvchi to'xtatish tugmasi bilan tugatadi.
- **FR16:** Audio Gemini'ga yuboriladi va tizim **structured transaction draft(s)** qaytaradi (1 yoki bir nechta).
- **FR17:** Audio fayllar bizning server'imizda **saqlanmaydi** — Gemini'ga yuborilgandan keyin darrov tashlanadi.
- **FR18:** Voice parser qo'llab-quvvatlaydigan birliklar: `k`, `ming`, `mln`, `million`, `mlrd`, sonni so'z bilan ("o'n besh ming") va raqam bilan ("15000") gibrid.
- **FR19:** Voice parser sanani tushunadi: "bugun", "kecha", "o'tgan dushanba", aniq sana ("25-iyul") — parse fail bo'lsa default bugun.
- **FR20:** Voice parser kategoriyaga avtomatik moslashtirishga harakat qiladi (taxi → Taxi kategoriyasi). Topa olmasa "Boshqa" qo'yadi va flag qiladi.
- **FR21:** Voice'da bir gapda **bir nechta tranzaksiya** kiritish qo'llab-quvvatlanadi (multi-tx parse).
- **FR22:** Voice'da **recurring intent** ("har oy/hafta") tushuniladi va recurring setup'ga aylantirish taklif qilinadi (auto-add emas, foydalanuvchi tasdiqlaydi).
- **FR23:** Voice confirm ekran har bir draft'ni alohida karta sifatida ko'rsatadi (editable + deletable).
- **FR24:** Confirm ekran'da kamida bitta noaniq maydon bor karta vizual ravishda flagged bo'ladi (sariq border + "noaniq" label).
- **FR25:** Foydalanuvchi confirm ekranda hammasini saqlay olishi mumkin (atomic save: hammasi yoki hech narsa) yoki bir nechtasini o'chirib qolganini saqlash mumkin.

### Categories Management

- **FR26:** Tizim preset kategoriyalarni taqdim etadi: kirim uchun (oylik, biznes, sovg'a, qaytgan qarz, boshqa); chiqim uchun (oziq-ovqat, transport, kommunal, ko'ngilochar, kiyim, sog'liq, ta'lim, taxi, qahva/kafe, boshqa).
- **FR27:** Foydalanuvchi yangi kategoriya qo'sha oladi (nom + emoji + tur: kirim/chiqim).
- **FR28:** Foydalanuvchi o'z kategoriyasini tahrirlay yoki o'chira oladi (preset'lar o'chirilmaydi, faqat yashiriladi).
- **FR29:** Har kategoriya bilan bog'liq emoji ko'rsatiladi history va reports'da.

### Debt Management

- **FR30:** Qarz oldim → balansga `+` qo'shadi, lekin **"qarz pul" tag** bilan ajratiladi.
- **FR31:** Qarz berdim → balansga `−` (chiqim sifatida hisoblanadi), lekin "qarz" turi bilan tag qilinadi.
- **FR32:** Qarz tranzaksiyasi `counterparty` (shaxs nomi — v1 da `String`, v2 da `User` FK) saqlaydi.
- **FR33:** Qarz tranzaksiyasi ixtiyoriy `expected_return_date` saqlaydi.
- **FR34:** Tizim qarzlarni state machine bilan boshqaradi: `open` → `partial` → `closed`, yoki `cancelled` (kechirilgan).
- **FR35:** Foydalanuvchi qarzni qisman qaytarganini yozishi mumkin (`repayment_amount` < `original_amount`). Tizim qoldiq miqdorni avtomatik hisoblaydi.
- **FR36:** Qarz qaytarilishi yangi kirim tranzaksiyasi yaratmaydi (double-counting prevent).
- **FR37:** Debts ekran ikkita ro'yxat ko'rsatadi: "Kim qarzdor menga" va "Men kimga qarzdorman", har biri summasi bilan.
- **FR38:** Dashboard'da 3 ta raqam: **Naqd balans · Sof balans (qarzlardan tozalangan) · Qarz holati**.

### Multi-Currency

- **FR39:** Tizim 3 ta valyutani qo'llab-quvvatlaydi: UZS (default), RUB, USD.
- **FR40:** Har tranzaksiya o'z valyutasida saqlanadi (no conversion at write).
- **FR41:** Home/Reports'da foydalanuvchi tanlagan valyutada balanslar ko'rsatiladi (display conversion).
- **FR42:** Konvertatsiya kursi CBU.uz API'dan kuniga 1 marta yangilanadi va cache qilinadi.
- **FR43:** CBU.uz unavailable bo'lsa, eng oxirgi ma'lum kurs ishlatiladi va UI'da "kurs eski (N kun)" banner ko'rsatiladi. Tranzaksiyalar saqlanishni davom etadi.
- **FR44:** Foydalanuvchi default valyutani Settings'da o'zgartirishi mumkin.

### Recurring Transactions

- **FR45:** Foydalanuvchi takrorlanuvchi xarajat/kirim qo'sha oladi: nom, summa, valyuta, kategoriya, jadval (haftalik/oylik + kun raqami).
- **FR46:** Tizim har takrorlanuvchi yozuv uchun belgilangan kuni Telegram Bot push yuboradi.
- **FR47:** Bot xabari foydalanuvchiga 1 tap'da tasdiqlash (kirim/chiqim qo'shadi) yoki skip qilish imkonini beradi.
- **FR48:** Recurring auto-add ETMAYDI — har doim user tasdiqlashi kerak.
- **FR49:** Foydalanuvchi recurring yozuvni Settings'dan tahrirlay yoki o'chira oladi.

### Reports & Analytics

- **FR50:** Reports ekran 3 ta vaqt oralig'iga ega: **Hafta · Oy · Yil**.
- **FR51:** Haftalik report: kategoriya bo'yicha pie chart + kunlik bar chart.
- **FR52:** Oylik report: kirim/chiqim trend, eng katta 5 ta xarajat, valyuta bo'yicha taqsimot.
- **FR53:** Yillik report: oylar bo'yicha bar chart, eng "qimmat" oy, kategoriya taqsimoti. Data yetarli bo'lmasa "ma'lumot to'planmoqda" empty state ko'rsatiladi (≥3 oylik data kerak).
- **FR54:** Foydalanuvchi reports'da valyutani almashtira oladi (display).
- **FR55:** Qarz tranzaksiyalari reports'da alohida toggle bilan ko'rsatiladi/yashiriladi.

### Notifications (via Telegram Bot)

- **FR56:** Tizim qarz qaytarish kuni keladigan bo'lsa, foydalanuvchiga 1 kun oldin Telegram push yuboradi.
- **FR57:** Tizim recurring xarajat kuni keladigan bo'lsa, push yuboradi (FR46 bilan bir xil).
- **FR58:** Push xabarlari deep-link orqali WebApp'ning kerakli ekraniga (action context bilan) olib boradi.

### History & Search

- **FR59:** Foydalanuvchi tranzaksiyalar tarixini ko'ra oladi (chronological reverse order).
- **FR60:** Foydalanuvchi history'ni filter qila oladi: turi, sana oralig'i, kategoriya, valyuta.
- **FR61:** Foydalanuvchi history'da tranzaksiya bosib tahrir/o'chir qila oladi.

### Settings & Configuration

- **FR62:** Foydalanuvchi Settings'da til (v1: faqat o'zbek), default valyuta, kategoriyalar, recurring yozuvlarini boshqara oladi.
- **FR63:** Settings'da "Audio fayllar saqlanmaydi" va "Gemini privacy disclosure" ma'lumotlari ko'rsatiladi.
- **FR64:** Foydalanuvchi o'z hisobini va barcha ma'lumotlarini export qila oladi (JSON, v1.5'ga qoldirilishi mumkin — v1.0 da out of scope).

## Non-Functional Requirements

### Performance

- **NFR1:** Telegram WebApp cold-start to interactive < 1.5s, 3G network simulatsiyasida.
- **NFR2:** htmx swap server response p95 < 200ms.
- **NFR3:** Voice end-to-end latency p50 < 3s, p95 < 6s (mic stop → confirm screen).
- **NFR4:** Manual transaction save → Home redirect < 500ms.
- **NFR5:** Reports rendering (oylik) < 1s 1 yillik ma'lumot uchun.

### Security

- **NFR6:** `initData` HMAC-SHA256 har request'da revalidate; ≤ 24 soatdan eski `auth_date` reject qilinadi.
- **NFR7:** Hech qanday kredit karta yoki bank ma'lumoti olinmaydi yoki saqlanmaydi (PCI-DSS scope tashqarisida).
- **NFR8:** HTTPS only, HSTS enabled, strict CSP header'lar.
- **NFR9:** Audio fayllar disk'ga yozilmaydi (memory only) va Gemini response qaytgandan keyin GC qilinadi.
- **NFR10:** Backend log'larda audio request body yozilmaydi (request body logging audio endpoint'lar uchun o'chirilgan).
- **NFR11:** Foydalanuvchi ma'lumotlari faqat o'zining `telegram_id` orqali ko'rinishi (row-level access enforce qilingan).
- **NFR12:** Pul summa maydonlari `Decimal(15, 2)`, hech qachon `Float` — accounting bug'lar prevent.

### Scalability

- **NFR13:** API ≥ 50 concurrent voice request handle qiladi (async views + connection pool).
- **NFR14:** Database 100k tranzaksiya/foydalanuvchi sig'imida ishlaydi (indexing: `(user_id, created_at)`, `(user_id, type, created_at)`).
- **NFR15:** Gemini free tier limit (1500/day) yetishi uchun monitoring + alerting paid tier'ga o'tish chegarasini belgilash.

### Reliability

- **NFR16:** API availability ≥ 99% (single VPS yetadi v1 uchun).
- **NFR17:** PostgreSQL kunlik backup (off-site), recovery RPO ≤ 24 soat.
- **NFR18:** CBU.uz yoki Gemini outage UX'ni bloklamaydi — graceful degradation (stale rate, manual fallback).

### Accessibility

- **NFR19:** Mobile WCAG 2.1 AA ga intilish — color contrast ≥ 4.5:1, touch target ≥ 44×44px, focus indicators.
- **NFR20:** Icon-only tugmalarda aria-label.
- **NFR21:** Voice input — bu accessibility uchun + (motor impairment foydalanuvchilar uchun manual alternative).

### Integration

- **NFR22:** Gemini API integration retry strategy: exponential backoff, max 3 retries, 30s total timeout.
- **NFR23:** Telegram Bot va WebApp alohida process'lar — biri ikkinchisining lag'idan ta'sirlanmasligi kerak.
- **NFR24:** CBU.uz API call kunlik 1 marta, cache stale (last_known) fallback bilan.

### Code Quality & Maintainability (Eric'ning xohishi)

- **NFR25:** Kod SOLID printsiplariga rioya qiladi — Single Responsibility, Open/Closed (extension), Liskov, Interface Segregation, Dependency Inversion.
- **NFR26:** Modullar ravshan domain bo'limlari bo'yicha tuzilgan (e.g., `transactions/`, `debts/`, `voice/`, `currencies/`) — texnologiya layer'lari bo'yicha emas.
- **NFR27:** Test coverage ≥ 80% domain logic uchun (transaction calculation, debt state machine, currency conversion).
- **NFR28:** Lint qoidalari qat'iy: ruff (Python) + djlint (templates) + prettier (CSS/JS) — CI'da enforced.
- **NFR29:** Har Pull Request'da self-review + AC checklist (story acceptance criteria'lari).
- **NFR30:** Code comments faqat *nima uchun* — *nima* qilayotgani aniq nomdan ko'rinishi kerak.

### UX Polish (Eric'ning xohishi)

- **NFR31:** Har ekranda loading state, empty state, error state aniq dizayn qilingan — boshi-oxiri yo'q "qalqa" yo'q.
- **NFR32:** Mikro-interactions (button press, save confirmation, debt close) — 200-300ms animatsiya.
- **NFR33:** Typography hierarchy aniq — balans katta, summa raqamlar tabular-nums, sana muted.
- **NFR34:** Color palette UX-driven (kirim yashil, chiqim qizg'ish-qora, qarz sariq accent) — accessibility-safe.

## Document Polish Notes

PRD yagona session'da yaratildi va integration polish quyidagicha qilindi:

- Section transitions: Executive Summary → Classification → Success → Scope → Journeys → Domain → Innovation → Web-app reqs → Scoping Strategy → FRs → NFRs — har biri keyingisi uchun fundament.
- Duplikatsiya minimal: Product Scope (yuqorida) yengil overview, Scoping Strategy & Risks (pastda) chuqur strategik analiz va phased delivery plan. Bir-birini takrorlamaydi.
- Capability contract (FRs) bo'limi binding — UX, Architecture, va Stories faqat shu yerda ro'yxatga olinganlarni qo'llab-quvvatlaydi.
- Frontmatter party-mode insights va classification metadata'ni saqlaydi (downstream workflows uchun).
- Til: o'zbek, mixed register (texnik atamalar inglizcha qoldirilgan — accuracy uchun).

## Workflow Completion

PRD to'ldi: Executive Summary · Classification · Success Criteria · Product Scope · User Journeys · Domain Requirements · Innovation Analysis · web_app Requirements · Scoping Strategy & Risks · 64 Functional Requirements · 34 Non-Functional Requirements.

**Keyingi qadamlar (BMad planning faza):**

1. **UX Design** (`bmad-create-ux-design` → Sally) — wireframes, user flows, key ekran mockups
2. **Architecture** (`bmad-create-architecture` → Winston) — Django struktura, async voice pipeline, DB schema, deployment plan
3. **Project Context** (`bmad-generate-project-context`) — SOLID kod standartlari, file naming, test guidelines (Eric'ning talabi)
4. **Epics & Stories** (`bmad-create-epics-and-stories`) — phased delivery (v0.1 → v1.0) ishni sprint'larga ajratish
5. **Readiness Check** (`bmad-check-implementation-readiness`) — gate before dev cycle

PRD downstream qadamlar uchun **fundament**. Har yangi feature yoki o'zgarish ushbu hujjatga qaytib trace qilinishi kerak — agar shu yerda FR yo'q bo'lsa, dizayn yoki kod'da paydo bo'lmasligi kerak.
