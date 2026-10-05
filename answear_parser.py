import gzip
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv


# =========================================
# ENV
# =========================================

load_dotenv()

FEED_URL = os.getenv("ANSWEAR_FEED_URL")


# =========================================
# ПУТИ
# =========================================

PROJECT_ROOT = Path(__file__).parent

OUTPUT_FILE = PROJECT_ROOT / "answear_products.json.gz"


# =========================================
# СКАЧИВАНИЕ
# =========================================

def download_feed():
    """
    Скачивает XML Answear синхронно.
    """

    if not FEED_URL:
        raise ValueError("ANSWEAR_FEED_URL не найден в .env")

    print("📥 Скачиваю XML Answear...")

    response = requests.get(
        FEED_URL,
        timeout=300,
        stream=True,
    )

    response.raise_for_status()

    chunks = []

    for chunk in response.iter_content(chunk_size=1024 * 1024):
        if chunk:
            chunks.append(chunk)

    data = b"".join(chunks)

    print(f"✅ XML скачан: {len(data) / 1024 / 1024:.2f} MB")

    return data


# =========================================
# ПАРСИНГ
# =========================================

def parse_feed(xml_data):
    """
    Разбирает XML и возвращает список товаров
    в формате, совместимом с search.py.
    """

    print("🔍 Разбираю XML...")

    root = ET.fromstring(xml_data)

    # =====================================
    # КАТЕГОРИИ
    # =====================================

    categories = {}

    for category in root.findall(".//categories/category"):
        category_id = category.get("id")

        if category_id:
            categories[category_id] = category.text or ""

    print(f"📂 Категорий найдено: {len(categories)}")

    # =====================================
    # ТОВАРЫ
    # =====================================

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
        price_text = get_text("price")
        url = get_text("url")

        # Минимально необходимые данные
        if not name or not price_text or not url:
            continue

        try:
            price = float(price_text)
        except (TypeError, ValueError):
            continue

        # old_price
        old_price_text = get_text("oldprice")

        try:
            old_price = (
                float(old_price_text)
                if old_price_text
                else None
            )
        except (TypeError, ValueError):
            old_price = None

        # =====================================
        # ЕДИНЫЙ ФОРМАТ (как в search.py)
        # =====================================

        product = {
            "id": offer.get("id"),
            "name": name,
            "title": name,
            "store": "Answear",
            "price": price,
            "old_price": old_price,
            "currency": get_text("currencyId") or "UAH",
            "condition": "new",
            "description": get_text("description"),
            "picture": get_text("picture"),
            "url": url,
            "canonical_url": url,
            "vendor": get_text("vendor"),
            "category_id": category_id,
            "category": categories.get(category_id, ""),
            "rating": None,
            "reviews": None,
            "match_score": 0,
            "deal_score": 0,
            "discount": 0,
        }

        products.append(product)

    print(f"✅ Товаров сохранено: {len(products)}")

    return products


# =========================================
# СОХРАНЕНИЕ
# =========================================

def save_products(products):
    """
    Сохраняет товары в .gz (совместимо с search.py).
    """

    print(f"💾 Сохраняю в {OUTPUT_FILE}...")

    with gzip.open(
        OUTPUT_FILE,
        "wt",
        encoding="utf-8",
    ) as file:
        json.dump(
            products,
            file,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    print("✅ Файл сохранён")


# =========================================
# ГЛАВНАЯ ФУНКЦИЯ (СИНХРОННАЯ)
# =========================================

def refresh_answear():
    """
    Скачивает, парсит и сохраняет Answear.

    Вызывается из bot.py через
    asyncio.to_thread(refresh_answear).
    """

    print("[ANSWEAR] Начинаю обновление...")

    xml_data = download_feed()

    products = parse_feed(xml_data)

    save_products(products)

    print(f"[ANSWEAR] Готово. Товаров: {len(products)}")

    return len(products)


# =========================================
# РУЧНОЙ ЗАПУСК
# =========================================

if __name__ == "__main__":
    refresh_answear()