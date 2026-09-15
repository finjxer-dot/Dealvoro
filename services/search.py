import gzip
import json
import re
from pathlib import Path

import ijson

from services.store_feeds import (
    FEEDS,
    load_store_products,
)


PROJECT_ROOT = Path(__file__).parent.parent

PRODUCTS_FILE = (
    PROJECT_ROOT / "answear_products.json.gz"
)


# =========================================
# ПОТОКОВАЯ ЗАГРУЗКА КАТАЛОГА
# =========================================

def iter_json_gz(file_path):
    """
    Читает JSON-массив из .gz по одному товару.

    В отличие от json.load():
    весь каталог НЕ загружается в RAM.
    """

    with gzip.open(
        file_path,
        "rb",
    ) as file:

        for product in ijson.items(
            file,
            "item",
        ):
            yield product


def iter_store_products(
    store,
    cache_path,
):
    """
    Читает каталог магазина потоково.

    Если готового .gz нет,
    используем существующий механизм загрузки.
    """

    if cache_path.exists():

        print(
            f"{store}: "
            f"потоковая загрузка .gz"
        )

        yield from iter_json_gz(
            cache_path
        )

        return

    # Запасной вариант:
    # если кэша нет, store_feeds скачает
    # XML и создаст .gz.
    products = load_store_products(
        store
    )

    for product in products:
        yield product


def iter_all_products():
    """
    Последовательно отдаёт товары:

    1. Answear
    2. TOUCH
    3. INTERTOP

    Одновременно в памяти находится
    только текущий обрабатываемый товар.
    """

    # =====================================
    # ANSWEAR
    # =====================================

    if not PRODUCTS_FILE.exists():

        raise FileNotFoundError(
            f"Файл каталога не найден: "
            f"{PRODUCTS_FILE}"
        )

    print(
        "Answear: "
        "потоковая загрузка .gz"
    )

    yield from iter_json_gz(
        PRODUCTS_FILE
    )

    # =====================================
    # ДОПОЛНИТЕЛЬНЫЕ МАГАЗИНЫ
    # =====================================

    for store, config in FEEDS.items():

        yield from iter_store_products(
            store,
            config["cache"],
        )


# =========================================
# НОРМАЛИЗАЦИЯ
# =========================================

def normalize(text):
    """
    Приводит текст к удобному для поиска виду.
    """

    if not text:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-zа-яёіїєґ0-9]+",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def get_words(text):
    return normalize(text).split()


def get_product_title(product):
    return normalize(
        product.get("name")
        or product.get("title")
        or ""
    )


def get_product_description(product):
    return normalize(
        product.get(
            "description",
            "",
        )
    )


def get_product_vendor(product):
    return normalize(
        product.get(
            "vendor",
            "",
        )
    )


def get_product_category(product):
    return normalize(
        product.get(
            "category",
            "",
        )
    )


def get_product_identity_text(product):
    return " ".join(
        [
            get_product_title(product),
            get_product_vendor(product),
            get_product_category(product),
        ]
    ).strip()


def get_product_full_search_text(product):
    return " ".join(
        [
            get_product_title(product),
            get_product_description(product),
        ]
    ).strip()


# =========================================
# MATCH SCORE
# =========================================

def calculate_match_score(
    query,
    product,
):
    query_words = get_words(query)

    if not query_words:
        return 0

    name = get_product_title(product)
    description = get_product_description(product)
    vendor = get_product_vendor(product)
    category = get_product_category(product)

    name_words = name.split()

    score = 0

    for word in query_words:

        if word in name_words:
            score += 40

        elif any(
            word in name_word
            for name_word in name_words
        ):
            score += 25

        elif word in vendor:
            score += 30

        elif word in description:
            score += 10

        elif word in category:
            score += 5

    normalized_query = normalize(
        query
    )

    if (
        normalized_query
        and normalized_query in name
    ):
        score += 50

    if (
        normalized_query
        and name.startswith(
            normalized_query
        )
    ):
        score += 20

    return score


# =========================================
# DEAL SCORE
# =========================================

def calculate_deal_score(product):
    try:
        price = float(
            product.get(
                "price",
                0,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0

    old_price = product.get(
        "old_price"
    )

    try:
        old_price = (
            float(old_price)
            if old_price is not None
            else None
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0

    if (
        not old_price
        or old_price <= price
    ):
        return 0

    discount_percent = (
        (old_price - price)
        / old_price
    ) * 100

    return min(
        round(discount_percent),
        100,
    )


def calculate_discount(product):
    try:
        price = float(
            product.get(
                "price",
                0,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0

    old_price = product.get(
        "old_price"
    )

    try:
        old_price = (
            float(old_price)
            if old_price is not None
            else None
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0

    if (
        not old_price
        or old_price <= price
    ):
        return 0

    return round(
        (
            (old_price - price)
            / old_price
        ) * 100
    )


# =========================================
# СОВПАДЕНИЕ ТЕРМИНОВ
# =========================================

def term_matches_text(
    term,
    text,
):
    normalized_term = normalize(
        term
    )

    if (
        not normalized_term
        or not text
    ):
        return False

    term_words = (
        normalized_term.split()
    )

    if len(term_words) == 1:
        return (
            normalized_term
            in text.split()
        )

    return (
        normalized_term
        in text
    )


# =========================================
# ГРУППЫ
# =========================================

def clean_groups(groups):
    if not groups:
        return []

    cleaned_groups = []

    for group in groups:

        if not isinstance(
            group,
            list,
        ):
            continue

        cleaned_group = []

        for term in group:

            if not isinstance(
                term,
                str,
            ):
                continue

            term = normalize(
                term
            )

            if term:
                cleaned_group.append(
                    term
                )

        if cleaned_group:
            cleaned_groups.append(
                cleaned_group
            )

    return cleaned_groups


def merge_required_groups(
    must_groups,
    requirement_groups=None,
):
    result = []

    result.extend(
        clean_groups(
            must_groups
        )
    )

    result.extend(
        clean_groups(
            requirement_groups
        )
    )

    return result


# =========================================
# ОБЯЗАТЕЛЬНЫЕ ГРУППЫ
# =========================================

def matches_required_groups(
    product,
    must_groups,
):
    """
    Все группы обязательны.

    Проверяется только:
    - название;
    - бренд;
    - категория.

    Описание не используется.
    """

    if not must_groups:
        return True

    identity_text = (
        get_product_identity_text(
            product
        )
    )

    identity_words = (
        identity_text.split()
    )

    for group in must_groups:

        if not isinstance(
            group,
            list,
        ):
            return False

        if not group:
            return False

        group_matched = False

        for term in group:

            if not isinstance(
                term,
                str,
            ):
                continue

            normalized_term = normalize(
                term
            )

            if not normalized_term:
                continue

            term_words = (
                normalized_term.split()
            )

            if len(term_words) == 1:

                if (
                    normalized_term
                    in identity_words
                ):
                    group_matched = True
                    break

            else:

                if (
                    normalized_term
                    in identity_text
                ):
                    group_matched = True
                    break

        if not group_matched:
            return False

    return True


# =========================================
# ИСКЛЮЧЕНИЯ
# =========================================

def contains_excluded_term(
    product,
    exclude_terms,
):
    """
    Исключения проверяются:
    - в названии;
    - в бренде;
    - в категории.

    Описание не используется.
    """

    if not exclude_terms:
        return False

    identity_text = (
        get_product_identity_text(
            product
        )
    )

    identity_words = (
        identity_text.split()
    )

    for term in exclude_terms:

        if not isinstance(
            term,
            str,
        ):
            continue

        normalized_term = normalize(
            term
        )

        if not normalized_term:
            continue

        term_words = (
            normalized_term.split()
        )

        if len(term_words) == 1:

            if (
                normalized_term
                in identity_words
            ):
                return True

        else:

            if (
                normalized_term
                in identity_text
            ):
                return True

    return False


# =========================================
# RELEVANCE
# =========================================

def calculate_relevance_score(
    product,
    must_groups,
    requirement_terms=None,
):
    """
    Приоритет:

    название > бренд > категория
    """

    title = get_product_title(
        product
    )

    vendor = get_product_vendor(
        product
    )

    category = get_product_category(
        product
    )

    score = 0

    for group in must_groups:

        best_group_score = 0

        for term in group:

            normalized_term = normalize(
                term
            )

            if not normalized_term:
                continue

            if term_matches_text(
                normalized_term,
                title,
            ):
                best_group_score = max(
                    best_group_score,
                    50,
                )

            if term_matches_text(
                normalized_term,
                vendor,
            ):
                best_group_score = max(
                    best_group_score,
                    40,
                )

            if term_matches_text(
                normalized_term,
                category,
            ):
                best_group_score = max(
                    best_group_score,
                    30,
                )

        if best_group_score == 0:
            return 0

        score += best_group_score

    return score


# =========================================
# ОСНОВНОЙ ПОИСК
# =========================================

def search_products(
    product_query,
    min_price=0,
    max_price=None,
    currency="UAH",
    country="UA",
    condition="any",
    requirements=None,
    search_terms=None,
    must_groups=None,
    requirement_terms=None,
    exclude_terms=None,
    requirement_groups=None,
):
    """
    Потоковый поиск по:

    - Answear
    - TOUCH
    - INTERTOP

    Весь каталог НЕ загружается в память.
    """

    results = []
    seen_products = set()

    # =====================================
    # SEARCH TERMS
    # =====================================

    if search_terms:

        search_terms = [
            normalize(term)
            for term in search_terms
            if isinstance(term, str)
            and term.strip()
        ]

        search_terms = [
            term
            for term in search_terms
            if term
        ]

    else:

        search_terms = [
            normalize(
                product_query
            )
        ]

    # =====================================
    # MUST GROUPS
    # =====================================

    if must_groups:

        must_groups = clean_groups(
            must_groups
        )

    else:

        must_groups = [
            [
                normalize(
                    product_query
                )
            ]
        ]

    # =====================================
    # REQUIREMENT GROUPS
    # =====================================

    required_groups = (
        merge_required_groups(
            must_groups,
            requirement_groups,
        )
    )

    # =====================================
    # REQUIREMENT TERMS
    # =====================================

    if requirement_terms:

        requirement_terms = [
            normalize(term)
            for term in requirement_terms
            if isinstance(term, str)
            and term.strip()
        ]

        requirement_terms = [
            term
            for term in requirement_terms
            if term
        ]

    else:

        requirement_terms = []

    # =====================================
    # EXCLUDE TERMS
    # =====================================

    if exclude_terms:

        exclude_terms = [
            normalize(term)
            for term in exclude_terms
            if isinstance(term, str)
            and term.strip()
        ]

        exclude_terms = [
            term
            for term in exclude_terms
            if term
        ]

    else:

        exclude_terms = []

    # =====================================
    # ПОТОКОВЫЙ КАТАЛОГ
    # =====================================

    products_checked = 0

    for product in iter_all_products():

        products_checked += 1

        # ---------------------------------
        # ВАЛЮТА
        # ---------------------------------

        product_currency = (
            product.get("currency")
            or product.get("currencyId")
        )

        if product_currency != currency:
            continue

        # ---------------------------------
        # ЦЕНА
        # ---------------------------------

        try:

            price = float(
                product.get(
                    "price",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        if price < min_price:
            continue

        if (
            max_price is not None
            and price > max_price
        ):
            continue

        # ---------------------------------
        # СОСТОЯНИЕ
        # ---------------------------------

        if condition == "used":
            continue

        # ---------------------------------
        # ОБЯЗАТЕЛЬНЫЕ ГРУППЫ
        # ---------------------------------

        if not matches_required_groups(
            product,
            required_groups,
        ):
            continue

        # ---------------------------------
        # ИСКЛЮЧЕНИЯ
        # ---------------------------------

        if contains_excluded_term(
            product,
            exclude_terms,
        ):
            continue

        # ---------------------------------
        # RELEVANCE
        # ---------------------------------

        match_score = (
            calculate_relevance_score(
                product,
                required_groups,
                requirement_terms,
            )
        )

        if match_score == 0:
            continue

        # ---------------------------------
        # SEARCH BONUS
        # ---------------------------------

        search_term_score = 0

        title = get_product_title(
            product
        )

        full_search_text = (
            get_product_full_search_text(
                product
            )
        )

        for term in search_terms:

            if not term:
                continue

            if term in title:

                search_term_score = max(
                    search_term_score,
                    20,
                )

            elif (
                term
                in full_search_text
            ):

                search_term_score = max(
                    search_term_score,
                    5,
                )

        match_score += (
            search_term_score
        )

        # ---------------------------------
        # DEAL SCORE
        # ---------------------------------

        old_price = product.get(
            "old_price"
        )

        discount = calculate_discount(
            product
        )

        deal_score = calculate_deal_score(
            product
        )

        # ---------------------------------
        # ЕДИНЫЙ ФОРМАТ
        # ---------------------------------

        title_raw = (
            product.get("name")
            or product.get("title")
            or "Без названия"
        )

        store = (
            product.get("store")
            or "Answear"
        )

        product_copy = {
            "title": title_raw,
            "store": store,
            "rating": product.get(
                "rating"
            ),
            "reviews": product.get(
                "reviews"
            ),
            "price": price,
            "old_price": old_price,
            "currency": (
                product.get("currency")
                or currency
            ),
            "condition": (
                product.get("condition")
                or "new"
            ),
            "description": product.get(
                "description",
                "",
            ),
            "vendor": product.get(
                "vendor",
                "",
            ),
            "category": product.get(
                "category",
                "",
            ),
            "picture": product.get(
                "picture",
                "",
            ),
            "url": product.get(
                "url",
                "",
            ),
            "canonical_url": product.get(
                "canonical_url",
                "",
            ),
            "match_score": match_score,
            "deal_score": deal_score,
            "discount": discount,
        }

        # ---------------------------------
        # ДУБЛИКАТЫ
        # ---------------------------------

        url = product_copy.get(
            "url"
        )

        if url:

            product_key = (
                store,
                url,
            )

        else:

            product_key = (
                store,
                normalize(title_raw),
                price,
            )

        if product_key in seen_products:
            continue

        seen_products.add(
            product_key
        )

        results.append(
            product_copy
        )

    print(
        f"Каталог проверен: "
        f"{products_checked} товаров"
    )

    # =====================================
    # СОРТИРОВКА
    # =====================================

    results.sort(
        key=lambda item: (
            item.get(
                "match_score",
                0,
            ),
            item.get(
                "deal_score",
                0,
            ),
            item.get(
                "discount",
                0,
            ),
            -float(
                item.get(
                    "price",
                    0,
                )
            ),
        ),
        reverse=True,
    )

    return results