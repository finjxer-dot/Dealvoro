import gzip
import json
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import requests
from dotenv import load_dotenv


load_dotenv()


PROJECT_ROOT = Path(__file__).parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "feeds"

CACHE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CACHE_TTL = 6 * 60 * 60


FEEDS = {
    "TOUCH": {
        "url_env": "TOUCH_FEED_URL",
        "cache": CACHE_DIR / "touch_products.json.gz",
    },
    "INTERTOP": {
        "url_env": "INTERTOP_FEED_URL",
        "cache": CACHE_DIR / "intertop_products.json.gz",
    },
}


def clean_url(url):
    """
    Очищает URL от случайных внешних кавычек
    и пробелов.

    Например:

    '"https://example.com/feed"'
    ->
    'https://example.com/feed'
    """

    if not url:
        return ""

    url = str(url).strip()

    # Убираем внешние кавычки.
    if (
        len(url) >= 2
        and url[0] in "\"'"
        and url[-1] == url[0]
    ):
        url = url[1:-1].strip()

    # Дополнительная защита от ситуации,
    # когда после первой очистки остались кавычки.
    url = url.strip("\"'").strip()

    return url


def clean_tag(tag):
    return tag.split("}")[-1]


def get_text(element):
    return (
        element.text or ""
    ).strip()


def get_first_text(element, names):
    names = {
        name.lower()
        for name in names
    }

    for child in list(element):

        if (
            clean_tag(child.tag).lower()
            in names
        ):

            text = get_text(child)

            if text:
                return text

    return ""


def get_all_text(element, name):
    result = []

    for child in list(element):

        if (
            clean_tag(child.tag).lower()
            == name.lower()
        ):

            text = get_text(child)

            if text:
                result.append(text)

    return result


def get_tracked_url(url):
    """
    Извлекает исходную ссылку магазина
    из Admitad tracked URL через параметр ulp.
    """

    if not url:
        return ""

    url = clean_url(url)

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    ulp = query.get("ulp")

    if ulp:
        return unquote(
            ulp[0]
        )

    return url


def parse_offer(offer, store):
    """
    Преобразует offer из XML в единый формат Dealvoro.
    """

    name = get_first_text(
        offer,
        [
            "name",
            "title",
        ],
    )

    description = get_first_text(
        offer,
        [
            "description",
            "description_ua",
        ],
    )

    price_text = get_first_text(
        offer,
        [
            "price",
        ],
    )

    old_price_text = get_first_text(
        offer,
        [
            "oldprice",
            "old_price",
        ],
    )

    currency = (
        get_first_text(
            offer,
            [
                "currencyId",
                "currency",
            ],
        )
        or "UAH"
    )

    url = get_first_text(
        offer,
        [
            "url",
            "link",
        ],
    )

    vendor = get_first_text(
        offer,
        [
            "vendor",
            "brand",
            "manufacturer",
        ],
    )

    pictures = get_all_text(
        offer,
        "picture",
    )

    category_id = get_first_text(
        offer,
        [
            "categoryId",
        ],
    )

    params = get_all_text(
        offer,
        "param",
    )

    keywords = get_first_text(
        offer,
        [
            "keywords",
        ],
    )

    in_stock = get_first_text(
        offer,
        [
            "in_stock",
            "available",
        ],
    )

    try:
        price = float(
            price_text
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    try:

        old_price = (
            float(old_price_text)
            if old_price_text
            else None
        )

    except (
        TypeError,
        ValueError,
    ):
        old_price = None

    if not name:
        return None

    extra_text = " ".join(
        [
            description,
            keywords,
            " ".join(params),
        ]
    ).strip()

    canonical_url = get_tracked_url(
        url
    )

    return {
        "name": name,
        "title": name,
        "store": store,
        "rating": None,
        "reviews": None,
        "price": price,
        "old_price": old_price,
        "currency": currency,
        "condition": "new",
        "description": extra_text,
        "vendor": vendor,
        "category": category_id,
        "picture": (
            pictures[0]
            if pictures
            else ""
        ),
        "url": url,
        "canonical_url": canonical_url,
        "match_score": 0,
        "deal_score": 0,
        "discount": 0,
        "in_stock": in_stock,
    }


def download_feed(store, config):
    """
    Скачивает XML-фид магазина,
    парсит его и сохраняет gzip-кэш.
    """

    raw_url = os.getenv(
        config["url_env"]
    )

    url = clean_url(
        raw_url
    )

    if not url:

        print(
            f"{store}: "
            f"{config['url_env']} "
            f"не найден в .env"
        )

        return []

    print(
        f"{store}: скачивание XML..."
    )

    response = requests.get(
        url,
        timeout=180,
        stream=True,
    )

    response.raise_for_status()

    temp_xml = (
        CACHE_DIR
        / f"{store.lower()}_feed.xml"
    )

    try:

        with open(
            temp_xml,
            "wb",
        ) as file:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:
                    file.write(chunk)

        products = []

        context = ET.iterparse(
            temp_xml,
            events=("end",),
        )

        for _, element in context:

            tag = clean_tag(
                element.tag
            ).lower()

            if tag != "offer":
                continue

            product = parse_offer(
                element,
                store,
            )

            if product:
                products.append(
                    product
                )

            element.clear()

        with gzip.open(
            config["cache"],
            "wt",
            encoding="utf-8",
        ) as file:

            json.dump(
                products,
                file,
                ensure_ascii=False,
            )

        print(
            f"{store}: "
            f"сохранено товаров: "
            f"{len(products)}"
        )

        return products

    finally:

        temp_xml.unlink(
            missing_ok=True
        )


def load_store_products(store):
    """
    Загружает готовый каталог магазина из .gz.

    Если файла нет, скачивает XML и создаёт его.
    """

    config = FEEDS[store]
    cache = config["cache"]

    if cache.exists():
        print(
            f"{store}: загрузка готового каталога из .gz"
        )

        with gzip.open(
            cache,
            "rt",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    return download_feed(
        store,
        config,
    )


def load_additional_products():
    """
    Загружает товары всех дополнительных магазинов.

    Если один магазин недоступен,
    остальные продолжают работать.
    """

    products = []

    for store in FEEDS:

        try:

            products.extend(
                load_store_products(
                    store
                )
            )

        except Exception as error:

            print(
                f"{store}: "
                f"ошибка загрузки фида: "
                f"{error}"
            )

    return products