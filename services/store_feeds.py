import gzip
import json
import os
import time
from lxml import etree as ET
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

    "iCases UA": {
        "url_env": "ICASES_FEED_URL",
        "cache": CACHE_DIR / "icases_products.json.gz",
    },

    "Будинок Іграшок UA": {
        "url_env": "BUDYNOK_IGRASHOK_FEED_URL",
        "cache": CACHE_DIR / "budynok_igrashok_products.json.gz",
    },

    "AliExpress": {
        "url_env": "ALIEXPRESS_FEED_URL",
        "cache": CACHE_DIR / "aliexpress_products.json.gz",
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

    Для AliExpress — минимум полей (без description,
    params, keywords), чтобы уменьшить размер фида.
    """

    name = get_first_text(
        offer,
        [
            "name",
            "title",
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
        or (
            "USD"
            if store == "AliExpress"
            else "UAH"
        )
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

    # =====================================
    # ДЛЯ ALIEXPRESS — МИНИМУМ ПОЛЕЙ
    # =====================================

    if store == "AliExpress":

        return {
            "name": name,
            "title": name,
            "store": store,
            "price": price,
            "old_price": old_price,
            "currency": currency,
            "condition": "new",
            "vendor": vendor,
            "category": category_id,
            "picture": (
                pictures[0]
                if pictures
                else ""
            ),
            "url": url,
            "canonical_url": get_tracked_url(url),
            "in_stock": in_stock,
        }

    # =====================================
    # ДЛЯ ОСТАЛЬНЫХ — ПОЛНЫЙ ФОРМАТ
    # =====================================

    description = get_first_text(
        offer,
        [
            "description",
            "description_ua",
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

    extra_text = " ".join(
        [
            description,
            keywords,
            " ".join(params),
        ]
    ).strip()

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
        "canonical_url": get_tracked_url(url),
        "match_score": 0,
        "deal_score": 0,
        "discount": 0,
        "in_stock": in_stock,
    }


def download_feed(store, config):
    """
    Скачивает XML-фид магазина и парсит его ПОТОКОВО,
    БЕЗ сохранения XML на диск.

    Это экономит место — особенно для AliExpress,
    где распакованный XML занимает 7+ GB.
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

    # =====================================
    # ЧИСТКА СТАРЫХ ВРЕМЕННЫХ ФАЙЛОВ
    # =====================================

    for old_file in CACHE_DIR.glob("*_feed.xml*"):

        try:

            size = (
                old_file.stat().st_size
                / 1024
                / 1024
            )

            print(
                f"[CLEANUP] Удаляю "
                f"{old_file.name} "
                f"({size:.0f} MB)"
            )

            old_file.unlink()

        except Exception:

            pass

    temp_gz = (
        CACHE_DIR
        / f"{store.lower()}_products.json.gz.tmp"
    )

    response = requests.get(
        url,
        timeout=1800 if store == "AliExpress" else 600,
        stream=True,
    )

    response.raise_for_status()

    try:

        count = 0

        with gzip.open(
            temp_gz,
            "wt",
            encoding="utf-8",
        ) as gz_file:

            gz_file.write("[")

            first = True

            # =====================================
            # lxml читает из HTTP-потока напрямую
            # =====================================

            context = ET.iterparse(
                response.raw,
                events=("end",),
                tag="offer",
                recover=True,
            )

            for _, element in context:

                product = parse_offer(
                    element,
                    store,
                )

                element.clear()

                if not product:
                    continue

                if not first:
                    gz_file.write(",")

                first = False

                json.dump(
                    product,
                    gz_file,
                    ensure_ascii=False,
                )

                count += 1

                if count % 100000 == 0:

                    print(
                        f"{store}: "
                        f"обработано {count}"
                    )

            gz_file.write("]")

        # =====================================
        # ЗАМЕНЯЕМ СТАРЫЙ .GZ НОВЫМ
        # =====================================

        if config["cache"].exists():
            config["cache"].unlink()

        temp_gz.rename(config["cache"])

        print(
            f"{store}: "
            f"сохранено товаров: {count}"
        )

        return count

    finally:

        if temp_gz.exists():

            try:
                temp_gz.unlink()
            except Exception:
                pass


def load_store_products(store):
    """
    Загружает каталог магазина из .gz.

    Если .gz нет ИЛИ он устарел (старше CACHE_TTL) —
    скачивает свежий XML.
    """

    config = FEEDS[store]
    cache = config["cache"]

    need_refresh = True

    if cache.exists():

        age = time.time() - cache.stat().st_mtime

        if age < CACHE_TTL:

            need_refresh = False

            print(
                f"{store}: кэш свежий "
                f"({int(age)} сек < {CACHE_TTL} сек)"
            )

        else:

            print(
                f"{store}: кэш устарел "
                f"({int(age)} сек > {CACHE_TTL} сек) — обновляю"
            )

    if need_refresh:

        try:

            download_feed(store, config)

        except Exception as error:

            print(f"{store}: ошибка скачивания: {error}")

            if cache.exists():

                print(f"{store}: использую старый кэш")

            else:

                return []

    with gzip.open(
        cache,
        "rt",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def refresh_all_feeds():
    """
    Скачивает свежие XML-фиды для всех магазинов
    и пересобирает .gz-кэши.

    Вызывается при старте бота и раз в 12 часов.
    """

    print("[FEEDS] Начинаю обновление фидов...")

    for store, config in FEEDS.items():

        try:

            print(f"[FEEDS] Обновляю {store}...")

            download_feed(store, config)

        except Exception as error:

            print(f"[FEEDS] Ошибка обновления {store}: {error}")

    print("[FEEDS] Обновление фидов завершено")


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
                load_store_products(store)
            )

        except Exception as error:

            print(
                f"{store}: "
                f"ошибка загрузки фида: "
                f"{error}"
            )

    return products