import os
import json
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import aiohttp
import asyncio

load_dotenv()

FEED_URL = os.getenv("ANSWEAR_FEED_URL")
OUTPUT_FILE = "answear_products.json"


async def download_feed():
    if not FEED_URL:
        raise ValueError("ANSWEAR_FEED_URL не найден в .env")

    print("📥 Скачиваю XML Answear...")

    async with aiohttp.ClientSession() as session:
        async with session.get(FEED_URL) as response:
            response.raise_for_status()

            data = await response.read()

    print(f"✅ XML скачан: {len(data) / 1024 / 1024:.2f} MB")

    return data


def parse_feed(xml_data):
    print("🔍 Разбираю XML...")

    root = ET.fromstring(xml_data)

    # Категории
    categories = {}

    for category in root.findall(".//categories/category"):
        category_id = category.get("id")

        if category_id:
            categories[category_id] = category.text or ""

    print(f"📂 Категорий найдено: {len(categories)}")

    # Товары
    offers = root.findall(".//offer")

    print(f"📦 Всего товаров в XML: {len(offers)}")

    products = []

    for offer in offers:

        def get_text(tag):
            element = offer.find(tag)

            if element is None or element.text is None:
                return ""

            return element.text.strip()

        category_id = get_text("categoryId")
        name = get_text("name")
        price = get_text("price")
        url = get_text("url")

        # Минимально необходимые данные
        if not name or not price or not url:
            continue

        product = {
            "id": offer.get("id"),
            "name": name,
            "price": float(price),
            "old_price": (
                float(get_text("oldprice"))
                if get_text("oldprice")
                else None
            ),
            "currency": get_text("currencyId"),
            "description": get_text("description"),
            "picture": get_text("picture"),
            "url": url,
            "vendor": get_text("vendor"),
            "category_id": category_id,
            "category": categories.get(category_id, ""),
        }

        products.append(product)

    print(f"✅ Товаров сохранено: {len(products)}")

    return products


def save_products(products):
    print(f"💾 Сохраняю в {OUTPUT_FILE}...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            products,
            file,
            ensure_ascii=False,
            separators=(",", ":")
        )

    print("✅ Файл сохранён")


async def main():
    xml_data = await download_feed()

    products = parse_feed(xml_data)

    save_products(products)

    print()
    print("🎉 Импорт завершён!")
    print(f"📦 Товаров: {len(products)}")
    print(f"📄 Файл: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())