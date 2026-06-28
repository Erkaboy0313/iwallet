"""Seed the 25 curated quotes from Sprint v0.5 UX §5.1."""

from django.db import migrations

SEED = [
    ("Pulingiz haqida o'ylamasangiz, pul siz haqingizda o'ylab qoladi.", "Warren Buffett"),
    (
        "Hech qachon yo'qotmaslik birinchi qoida. Birinchi qoidani unutmaslik ikkinchi qoida.",
        "Warren Buffett",
    ),
    ("Maishiy intizom — sizning daromadingizdan ham muhim.", "Charlie Munger"),
    ("Aqlli kishi tez-tez fikrini o'zgartiradi. Ahmoq esa hech qachon.", "Charlie Munger"),
    ("Boylik — uxlayotganda ham siz uchun ishlaydigan aktivlar.", "Naval Ravikant"),
    (
        "Pul muammoni hal qilmaydi, lekin u sizga muammoni tanlash erkinligini beradi.",
        "Naval Ravikant",
    ),
    ("Bir umrlik tejash bir hafta xarid qilishdan kuchliroq.", "Morgan Housel"),
    ("Vaqt — moliyaning sehridir.", "Morgan Housel"),
    ("Boy odam — bu kam narsaga muhtoj bo'lgan kishi.", "Seneca"),
    ("Hech narsa egamiz emas; bizda faqat vaqt bor.", "Seneca"),
    ("Kuningizning birinchi soati o'zingiz uchun bo'lsin.", "Marcus Aurelius"),
    (
        "Sizga mavjud bo'lgan narsani ko'paytirish, yo'qni izlashdan yengilroq.",
        "Marcus Aurelius",
    ),
    ("Bir tiyin tejashga — bir tiyin topganga teng.", "Benjamin Franklin"),
    ("Vaqt — pul.", "Benjamin Franklin"),
    ("Boylik — sizning ehtiyojlaringizning kichikligida.", "Nassim Taleb"),
    ("Tasodifga ishonmang. Strukturani quring.", "Nassim Taleb"),
    ("Hech bo'lmaganda biror narsa bepul deganlarga ishonmang.", "Thomas Sowell"),
    ("O'lchamasangiz — boshqara olmaysiz.", "Peter Drucker"),
    ("Boylar pulni o'zlari uchun ishlatadi. Kambag'allar pul uchun ishlaydi.", "Robert Kiyosaki"),
    ("Siz maqsadlarga yetganingiz uchun emas, tizimingiz tufayli o'sasiz.", "James Clear"),
    ("Maoshingiz uchun ishlang; boylik uchun o'rganing.", "Jim Rohn"),
    ("Insonni biror narsa qo'rqitmasin — kechikishdan tashqari.", "Confucius"),
    ("Bin kilometrlik yo'l bir qadamdan boshlanadi.", "Lao Tzu"),
    ("Tomchi-tomchi ko'l bo'lar.", "Xalq maqoli"),
    ("Yeb-ichganing — o'zingniki, sarflaganing — yelga ketganing.", "Xalq maqoli"),
]


def seed_forward(apps, _schema):
    Quote = apps.get_model("quotes", "Quote")
    Quote.objects.bulk_create(
        [Quote(text_uz=text, author=author, locale="uz", is_active=True) for text, author in SEED],
        ignore_conflicts=True,
    )


def seed_backward(apps, _schema):
    Quote = apps.get_model("quotes", "Quote")
    Quote.objects.filter(author__in={author for _, author in SEED}).delete()


class Migration(migrations.Migration):
    dependencies = [("quotes", "0001_initial")]
    operations = [migrations.RunPython(seed_forward, seed_backward)]
