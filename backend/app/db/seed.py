"""Idempotent seed data: the 21 job categories and default app_settings (Chapter 9.1 / 16.1)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSetting, Category

# (slug, English, Marathi, Hindi, sort_order)
CATEGORIES: list[tuple[str, str, str, str, int]] = [
    ("govt-jobs", "Government Jobs", "सरकारी नोकरी", "सरकारी नौकरी", 10),
    ("banking", "Banking & Insurance", "बँकिंग व विमा", "बैंकिंग व बीमा", 20),
    ("it-software", "IT / Software", "IT / सॉफ्टवेअर", "IT / सॉफ्टवेयर", 30),
    ("data-entry", "Data Entry / Computer Operator", "डेटा एंट्री / कॉम्प्युटर ऑपरेटर",
     "डेटा एंट्री / कंप्यूटर ऑपरेटर", 40),
    ("accounts-finance", "Accounts / Finance", "अकाउंट्स / फायनान्स", "अकाउंट्स / फाइनेंस", 50),
    ("sales-marketing", "Sales / Marketing", "सेल्स / मार्केटिंग", "सेल्स / मार्केटिंग", 60),
    ("bpo-support", "BPO / Customer Support", "BPO / कस्टमर सपोर्ट", "BPO / कस्टमर सपोर्ट", 70),
    ("teaching", "Teaching / Education", "शिक्षक / शिक्षण", "शिक्षक / शिक्षा", 80),
    ("healthcare", "Healthcare / Nursing", "आरोग्य / नर्सिंग", "स्वास्थ्य / नर्सिंग", 90),
    ("pharma", "Pharma / Medical Rep", "फार्मा / मेडिकल", "फार्मा / मेडिकल", 100),
    ("iti-mechanical", "ITI / Mechanical", "ITI / मेकॅनिकल", "ITI / मैकेनिकल", 110),
    ("electrical", "Electrical / Electronics", "इलेक्ट्रिकल / इलेक्ट्रॉनिक्स",
     "इलेक्ट्रिकल / इलेक्ट्रॉनिक्स", 120),
    ("civil", "Civil / Construction", "सिव्हिल / बांधकाम", "सिविल / निर्माण", 130),
    ("manufacturing", "Manufacturing / Production", "उत्पादन / कंपनी कामगार",
     "उत्पादन / प्रोडक्शन", 140),
    ("hr-admin", "HR / Admin / Office", "HR / ऑफिस काम", "HR / ऑफिस", 150),
    ("design-media", "Design / Media", "डिझाईन / मीडिया", "डिज़ाइन / मीडिया", 160),
    ("hotel-hospitality", "Hotel / Hospitality", "हॉटेल / हॉस्पिटॅलिटी",
     "होटल / हॉस्पिटैलिटी", 170),
    ("retail-store", "Retail / Store", "रिटेल / दुकान", "रिटेल / स्टोर", 180),
    ("delivery-logistics", "Delivery / Logistics / Driver", "डिलिव्हरी / ड्रायव्हर",
     "डिलीवरी / ड्राइवर", 190),
    ("agriculture", "Agriculture", "कृषी", "कृषि", 200),
    ("other", "Other", "इतर", "अन्य", 999),
]

DEFAULT_SETTINGS: dict[str, object] = {
    "price_inr": 99,
    "subscription_days": 30,
    "trial_days": 3,
    "digest_times": ["09:00", "18:00"],
    "digest_max_jobs": 10,
    "max_categories": 3,
    "teaser_every_hours": 48,
    "last_digest_slot": None,
}


async def seed_categories(db: AsyncSession) -> None:
    existing = {row.slug for row in (await db.execute(select(Category.slug))).all()}
    for slug, name, name_mr, name_hi, sort_order in CATEGORIES:
        if slug in existing:
            continue
        db.add(
            Category(
                slug=slug, name=name, name_mr=name_mr, name_hi=name_hi,
                is_active=True, sort_order=sort_order,
            )
        )
    await db.flush()


async def seed_settings(db: AsyncSession) -> None:
    existing = {row.key for row in (await db.execute(select(AppSetting.key))).all()}
    for key, value in DEFAULT_SETTINGS.items():
        if key in existing:
            continue
        db.add(AppSetting(key=key, value=value))
    await db.flush()


async def seed_all(db: AsyncSession) -> None:
    await seed_categories(db)
    await seed_settings(db)
    await db.commit()


if __name__ == "__main__":
    import asyncio

    from app.db.session import SessionLocal

    async def _main() -> None:
        async with SessionLocal() as session:
            await seed_all(session)
            print("Seed complete.")

    asyncio.run(_main())
