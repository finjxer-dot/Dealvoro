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
    Разбирает XML Answear потоково (iterparse).
    Это не грузит весь XML в память сразу.
    """

    print("🔍 Разбираю XML (потоково)...")

    import io

    # =====================================
    # КАТЕГОРИИ — отдельным проходом
    # =====================================

    categories = {}

    context = ET.iterparse(
        io.BytesIO(xml_data),
        events=("end",),
    )

    for _, element in context:

        tag = element.tag.split("}")[-1].lower()

        if tag == "category":
            category_id = element.get("id")

            if category_id:
                categories[category_id] = element.text or ""

            element.clear()

        elif tag == "categories":
            # Категории закончились — выходим
            break

    print(f"📂 Категорий найдено: {len(categories)}")

    # =====================================
    # ТОВАРЫ — отдельным проходом
    # =====================================

    print("📦 Читаю товары...")

    products = []
    count = 0

    context = ET.iterparse(
        io.BytesIO(xml_data),
        events=("end",),
    )

    for _, element in context:

        tag = element.tag.split("}")[-1].lower()

        if tag != "offer":
            continue

        offer = element

        def get_text(t):
            el = offer.find(t)

            if el is None or el.text is None:
                return ""

            return el.text.strip()

        category_id = get_text("categoryId")
        name = get_text("name")
        price_text = get_text("price")
        url = get_text("url")

        if name and price_text and url:

            try:
                price = float(price_text)
            except (TypeError, ValueError):
                price = None

            if price is not None:

                old_price_text = get_text("oldprice")

                try:
                    old_price = (
                        float(old_price_text)
                        if old_price_text
                        else None
                    )
                except (TypeError, ValueError):
                    old_price = None

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

        element.clear()

        count += 1

        if count % 20000 == 0:
            print(f"   Обработано: {count}")

    print(f"✅ Товаров сохранено: {len(products)}")

    return products

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
    print("[ANSWEAR] Начинаю обновление...")

    xml_data = download_feed()

    print(f"[ANSWEAR] XML в памяти: {len(xml_data) / 1024 / 1024:.2f} MB")

    products = parse_feed(xml_data)

    save_products(products)

    print(f"[ANSWEAR] Готово. Товаров: {len(products)}")

    return len(products)


# =========================================
# РУЧНОЙ ЗАПУСК
# =========================================

if __name__ == "__main__":
    refresh_answear()