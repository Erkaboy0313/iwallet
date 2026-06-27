# IWALLET — Product Brief

**Versiya:** 0.1 (approved)
**Sana:** 2026-06-25
**PM:** John
**Mahsulot egasi:** Eric

---

## Bir gap

Telegram WebApp, voice-first shaxsiy moliya tracker — kirim, chiqim, qarz oldi-berdi — o'zbek tilida, mobile-only.

## Muammo

Pul qayerga ketayotgani ko'rinmaydi. Qo'lda yozish — eriniladi. Mavjud app'lar (Money Lover, 1Money, CoinKeeper) inglizcha, manual kiritishga asoslangan, o'zbek voice'ni qo'llab-quvvatlamaydi, o'zbek konteksti (qarz oldi-berdi mexanikasi) yo'q yoki yomon ishlangan.

## Target user

**v1 (1 oylik shaxsiy sinov):** Eric — mahsulot egasi. Maqsad: qo'lda yozishni butunlay tashlash.

**v2 (omma chiqishi):** O'zbek tilida gaplashuvchi, Telegram'da kun bo'yi turadigan, oddiy moliyaviy ko'rinish istovchi foydalanuvchilar.

## Muvaffaqiyat mezoni (1 oylik sinov)

- 30 kun ichida **> 80%** tranzaksiyalar app'ga kiritildi (qog'oz/xotira emas)
- O'rtacha tranzaksiya kiritish vaqti **< 10 soniya** voice bilan
- Oy oxirida sof balans **± 5%** aniqlikda (qo'lda hisoblash bilan solishtirib)

---

## MVP scope (v1)

### IN — qilamiz

#### 1. Tranzaksiya turlari (4 ta)

| Tur | Maydonlar |
|-----|-----------|
| Kirim | manba (kategoriya), summa, valyuta, sana, note |
| Chiqim | kategoriya, summa, valyuta, sana, note |
| Qarz oldim | shaxs, summa, valyuta, qaytarish kuni (ixtiyoriy), note |
| Qarz berdim | shaxs, summa, valyuta, qaytarish kuni (ixtiyoriy), note |

#### 2. Valyutalar

- Qo'llab-quvvatlash: **UZS, RUB, USD**
- Default: **UZS**
- Har tranzaksiya **o'z valyutasida saqlanadi**
- **Model A — display conversion:** Home/Reports'da userning tanlagan valyutasiga **bugungi kurs** bo'yicha aylantirib ko'rsatadi
- Manba: **CBU.uz** (Markaziy Bank), 24 soat cache, bitta cron job
- Model B (historical conversion) — kelajak versiya uchun, agar aniqlik kerak bo'lsa

#### 3. Kategoriyalar

- Preset (chiqim): oziq-ovqat, transport, kommunal, ko'ngilochar, kiyim, sog'liq, ta'lim, taxi, qahva/kafe, boshqa
- Preset (kirim): oylik, biznes, sovg'a, qaytgan qarz, boshqa
- User qo'sha oladi, o'chira oladi, emoji bilan

#### 4. Voice input (Gemini)

- Mic tugma → audio → Gemini → strukturalashtirilgan tranzaksiyalar
- **Multi-transaction support:** *"bugun 15k taxi, 30k qahva, 200k oylik oldim"* → 3 ta draft
- Confirm screen: hammasini ko'rsatadi, har birini edit/delete, "Hammasini saqlash" tugmasi
- Error case: agar Gemini noaniq tushunsa, qaysi maydon bo'sh — user qo'lda to'ldiradi
- **Audio fayllar saqlanmaydi:** Gemini'ga yuborilib darrov o'chiriladi
- **Recurring intent:** voice'da "har oy/hafta" iborasini recurring sifatida tushunadi va recurring sozlamasiga qo'shadi (tasdiqlash bilan)

#### 5. Manual input

- Voice'siz hammasini kiritish mumkin
- Tez kirish: numpad + kategoriya tanlash, ~3 tap'da save

#### 6. Qarz mexanikasi

- Qarz oldim → balansga **+**, "qarz puli" tag bilan vizual ajraladi
- Qarz berdim → balansga **−**, "qarz" turi bilan hisoblanadi
- Dashboard'da **3 ta raqam:** Naqd balans · Sof balans (qarzlar minus) · Qarz holati (oldim/berdim summasi)
- Qarz qaytarilsa → "qarz yopildi" alohida amal (yangi chiqim yaratmaydi)

#### 7. Recurring (takrorlanuvchi) xarajatlar

- User yozadi: *"har dushanba — internet 50k UZS"*
- Eslatish kuni keladi → **notification + 1-tap confirm to add**
- Auto-add EMAS (user trust uchun)

#### 8. Ekranlar (6 ta)

1. **Home** — joriy oy: kirim/chiqim/sof balans, top 3 kategoriya, voice mic katta tugmasi, valyuta switcher
2. **Add** — manual form (turi tanla → maydonlar)
3. **History** — list, filter: turi/sana/kategoriya/valyuta
4. **Debts** — 2 ta list: kim qarzdor menga / men kimga qarzdorman, har qaysi qatorda "yopish" tugmasi
5. **Reports** — haftalik, oylik, yillik
6. **Settings** — kategoriyalar, recurring xarajatlar, til, valyuta default

#### 9. Hisobotlar

- **Haftalik:** kategoriya bo'yicha pie chart + kunlik bar chart
- **Oylik:** kirim/chiqim trend, eng katta 5 ta xarajat, valyuta bo'yicha taqsimot
- **Yillik:** oylar bo'yicha bar chart, eng "qimmat" oy, kategoriya taqsimoti
- AI tavsiyalar **v1 da yo'q** — v2'ga

#### 10. Eslatmalar

- Qarz qaytarish kuni
- Recurring chiqim kuni
- Yo'l: **Telegram Bot API** orqali push (WebApp restriction'i — push WebApp'dan ketmaydi, bot kerak)

### OUT — v1 da YO'Q

- ❌ AI tavsiyalar / "keraksiz xarajat" detection
- ❌ Premium / to'lov tier
- ❌ Historical currency conversion (Model B)
- ❌ Receipt OCR
- ❌ Excel / PDF export
- ❌ Multi-user / shared wallet
- ❌ Bank integratsiyasi
- ❌ Web / desktop UI (faqat Telegram mobile WebApp viewport)
- ❌ Offline mode
- ❌ Budget limits / xarajat chegaralari

---

## Tech stack

| Layer | Tanlov |
|-------|--------|
| Backend | Python + Django (server-rendered templates) |
| Frontend | Django templates + **htmx** (dynamic qismlar uchun, JS minimum) |
| Voice | **Gemini API** (STT + intent parsing bir chaqiriqda), audio saqlamaymiz |
| Auth | Telegram WebApp `initData` validation |
| Storage | PostgreSQL (Django ORM) |
| Notifications | Telegram Bot API |
| Currency rates | CBU.uz API, 24h cache |
| Hosting | TBD (arxitektura bosqichida) |
| Platform | **Telegram WebApp only**, mobile viewport (desktopda ham mobile ko'rinish) |
| UI/UX | Chiroyli mustaqil dizayn, Telegram theme'ga moslashish shart emas |

---

## Voice scenariylar (acceptance misollar)

| Foydalanuvchi gapi | Kutilgan natija |
|---|---|
| *"Bugun 200 ming so'm taxi qildim"* | Chiqim · taxi · 200,000 · UZS · bugun |
| *"Akramga 1 million qarz berdim, oyiga qaytaradi"* | Qarz berdim · Akram · 1,000,000 · UZS · note: "oyiga" |
| *"Oylik tushdi 12 million"* | Kirim · oylik · 12,000,000 · UZS |
| *"Bugun 15k taxi, 30k qahva, 200k oylik oldim"* | 3 ta draft → confirm screen |
| *"Akram qarzini qaytardi"* | Debt close action (agar 1 ta qarz bo'lsa avtomatik, ko'p bo'lsa so'raydi) |
| *"Har oy 500k uchun ijara"* | Recurring xarajat sozlamasiga taklif |

---

## Roadmap (taxminiy)

| Bosqich | Vaqt | Mazmun |
|---------|------|--------|
| v0.1 | 1-hafta | Manual kirim/chiqim/qarz + Home + History |
| v0.2 | 2-hafta | Voice (single transaction) + Categories CRUD |
| v0.3 | 3-hafta | Multi-transaction voice + Debts ekrani + Recurring |
| v0.4 | 4-hafta | Reports (haftalik/oylik) + Notifications (Telegram Bot) |
| v1.0 | 5-6 hafta | Yillik hisobot + Polish + 30 kunlik shaxsiy sinov |

---

## Arxitektura va sifat talablari (PRD/Architecture'da batafsil)

- Loyiha tuzilmasi qat'iy belgilangan
- Testing strategiyasi (unit, integration, e2e) yozilgan
- Coding standards / lint qoidalari qat'iy
- CI/CD pipeline mavjud
- Code review checklist

Bu bo'limlar Architecture (Winston) bosqichida to'liq belgilanadi.

---

## Hal qilingan qarorlar (changelog)

| Sana | Qaror |
|------|-------|
| 2026-06-25 | htmx tanlandi (server-rendered + dynamic) |
| 2026-06-25 | UZS default valyuta |
| 2026-06-25 | Voice multi-transaction qo'llab-quvvatlanadi |
| 2026-06-25 | Voice'da recurring intent tushuniladi |
| 2026-06-25 | Reports UI mustaqil chiroyli dizayn |
| 2026-06-25 | Audio fayllar saqlanmaydi |
| 2026-06-25 | Valyuta — Model A (display conversion), CBU.uz |
| 2026-06-25 | Reports — yillik kiritildi (v1 da bo'ladi, oxiriga qoldiriladi) |
