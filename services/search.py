import gzip
import json
import re
from pathlib import Path

from services.store_feeds import load_additional_products


# answear_products.json находится в корне Dealvoro
PROJECT_ROOT = Path(__file__).parent.parent
PRODUCTS_FILE = PROJECT_ROOT / "answear_products.json.gz"


# =========================================
# КЭШ КАТАЛОГА В ПАМЯТИ
# =========================================

_PRODUCTS_CACHE = None


def load_products():
    """
    Загружает каталог только один раз за время работы бота.

    При первом вызове:
    - загружает Answear;
    - загружает TOUCH;
    - загружает INTERTOP;
    - заранее нормализует нужные поля;
    - сохраняет объединённый каталог в памяти.

    Последующие вызовы получают тот же каталог
    без повторного чтения gzip-файла и без повторной
    загрузки/парсинга фидов.
    """

    global _PRODUCTS_CACHE

    if _PRODUCTS_CACHE is not None:
        return _PRODUCTS_CACHE

    print("Загрузка каталога в память...")

    if not PRODUCTS_FILE.exists():
        raise FileNotFoundError(
            f"Файл каталога не найден: {PRODUCTS_FILE}"
        )

    with gzip.open(
        PRODUCTS_FILE,
        "rt",
        encoding="utf-8",
    ) as file:
        answear_products = json.load(file)

    additional_products = load_additional_products()

    print(
        "Каталог:",
        len(answear_products),
        "Answear +",
        len(additional_products),
        "других товаров",
    )

    products = answear_products + additional_products

    print("Подготовка каталога для быстрого поиска...")

    # =========================================
    # ПРЕДВАРИТЕЛЬНАЯ НОРМАЛИЗАЦИЯ
    # =========================================

    for product in products:

        title = (
            product.get("name")
            or product.get("title")
            or ""
        )

        description = product.get(
            "description",
            "",
        )

        vendor = product.get(
            "vendor",
            "",
        )

        category = product.get(
            "category",
            "",
        )

        product["_normalized_title"] = normalize(
            title
        )

        product["_normalized_description"] = normalize(
            description
        )

        product["_normalized_vendor"] = normalize(
            vendor
        )

        product["_normalized_category"] = normalize(
            category
        )

        # Основная идентичность товара.
        product["_identity_text"] = " ".join(
            [
                product["_normalized_title"],
                product["_normalized_vendor"],
                product["_normalized_category"],
            ]
        ).strip()

        # Полный текст используется только
        # для дополнительного поискового бонуса.
        product["_full_search_text"] = " ".join(
            [
                product["_normalized_title"],
                product["_normalized_description"],
            ]
        ).strip()

    _PRODUCTS_CACHE = products

    print(
        "Каталог загружен в память:",
        len(_PRODUCTS_CACHE),
        "товаров",
    )

    return _PRODUCTS_CACHE


def preload_products():
    """
    Явно загружает каталог при запуске бота.

    Это позволяет не ждать загрузку каталога
    после первого пользовательского запроса.
    """

    load_products()


def clear_products_cache():
    """
    Очищает кэш каталога.

    После этого следующий вызов load_products()
    загрузит каталог заново.

    Можно использовать для ручного обновления.
    """

    global _PRODUCTS_CACHE

    _PRODUCTS_CACHE = None


def normalize(text):
    """
    Приводит текст к удобному для поиска виду.
    """

    if not text:
        return ""

    text = str(text).lower()

    # Оставляем латиницу, кириллицу и цифры.
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
    """
    Возвращает нормализованное название товара.

    Использует заранее подготовленное значение,
    если каталог был загружен через load_products().
    """

    if "_normalized_title" in product:
        return product["_normalized_title"]

    return normalize(
        product.get("name")
        or product.get("title")
        or ""
    )


def get_product_description(product):
    """
    Возвращает нормализованное описание.
    """

    if "_normalized_description" in product:
        return product["_normalized_description"]

    return normalize(
        product.get(
            "description",
            "",
        )
    )


def get_product_vendor(product):
    """
    Возвращает нормализованный бренд.
    """

    if "_normalized_vendor" in product:
        return product["_normalized_vendor"]

    return normalize(
        product.get(
            "vendor",
            "",
        )
    )


def get_product_category(product):
    """
    Возвращает нормализованную категорию.
    """

    if "_normalized_category" in product:
        return product["_normalized_category"]

    return normalize(
        product.get(
            "category",
            "",
        )
    )


def get_product_identity_text(product):
    """
    Возвращает основной текст идентичности товара.
    """

    if "_identity_text" in product:
        return product["_identity_text"]

    return " ".join(
        [
            get_product_title(product),
            get_product_vendor(product),
            get_product_category(product),
        ]
    ).strip()


def get_product_full_search_text(product):
    """
    Возвращает название + описание.
    """

    if "_full_search_text" in product:
        return product["_full_search_text"]

    return " ".join(
        [
            get_product_title(product),
            get_product_description(product),
        ]
    ).strip()


def calculate_match_score(query, product):
    """
    Базовая оценка соответствия поисковой фразы.

    Поддерживает:
    - Answear: name
    - TOUCH / INTERTOP: title
    """

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

        # Точное совпадение в названии.
        if word in name_words:
            score += 40

        # Частичное совпадение в названии.
        elif any(
            word in name_word
            for name_word in name_words
        ):
            score += 25

        # Совпадение с брендом.
        elif word in vendor:
            score += 30

        # Совпадение в описании.
        elif word in description:
            score += 10

        # Совпадение в категории.
        elif word in category:
            score += 5

    normalized_query = normalize(query)

    # Весь запрос встречается в названии.
    if (
        normalized_query
        and normalized_query in name
    ):
        score += 50

    # Название начинается с полного запроса.
    if (
        normalized_query
        and name.startswith(normalized_query)
    ):
        score += 20

    return score


def calculate_deal_score(product):
    """
    Рассчитывает Deal Score на основе скидки.
    """

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

    if not old_price or old_price <= price:
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
    """
    Возвращает скидку в процентах.
    """

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

    if not old_price or old_price <= price:
        return 0

    return round(
        (
            (old_price - price)
            / old_price
        ) * 100
    )


def term_matches_text(
    term,
    text,
):
    """
    Проверяет совпадение термина с текстом.

    Для одного слова:
    точное совпадение по отдельным словам.

    Для фраз:
    обычное вхождение.
    """

    normalized_term = normalize(term)

    if not normalized_term or not text:
        return False

    term_words = normalized_term.split()

    if len(term_words) == 1:
        return normalized_term in text.split()

    return normalized_term in text


def clean_groups(groups):
    """
    Очищает группы обязательных терминов.
    """

    if not groups:
        return []

    cleaned_groups = []

    for group in groups:

        if not isinstance(group, list):
            continue

        cleaned_group = []

        for term in group:

            if not isinstance(term, str):
                continue

            term = normalize(term)

            if not term:
                continue

            cleaned_group.append(term)

        if cleaned_group:
            cleaned_groups.append(
                cleaned_group
            )

    return cleaned_groups


def merge_required_groups(
    must_groups,
    requirement_groups=None,
):
    """
    Объединяет основные обязательные группы
    и обязательные группы требований.
    """

    result = []

    result.extend(
        clean_groups(must_groups)
    )

    result.extend(
        clean_groups(requirement_groups)
    )

    return result


def matches_required_groups(
    product,
    must_groups,
):
    """
    Проверяет все обязательные группы.

    Каждая группа должна иметь хотя бы одно совпадение.

    Проверяются:
    - название;
    - бренд;
    - категория.

    Описание НЕ используется.
    """

    if not must_groups:
        return True

    identity_text = get_product_identity_text(
        product
    )

    identity_words = identity_text.split()

    for group in must_groups:

        if not isinstance(group, list):
            return False

        if not group:
            return False

        group_matched = False

        for term in group:

            if not isinstance(term, str):
                continue

            normalized_term = (
                normalize(term)
            )

            if not normalized_term:
                continue

            term_words = normalized_term.split()

            # Одно слово.
            if len(term_words) == 1:

                if (
                    normalized_term
                    in identity_words
                ):
                    group_matched = True
                    break

            # Фраза.
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


def contains_excluded_term(
    product,
    exclude_terms,
):
    """
    Проверяет явно неподходящие типы/подкатегории.

    Используются:
    - название;
    - бренд;
    - категория.

    Описание НЕ используется.
    """

    if not exclude_terms:
        return False

    identity_text = get_product_identity_text(
        product
    )

    identity_words = identity_text.split()

    for term in exclude_terms:

        if not isinstance(term, str):
            continue

        normalized_term = normalize(term)

        if not normalized_term:
            continue

        term_words = normalized_term.split()

        if len(term_words) == 1:

            if normalized_term in identity_words:
                return True

        else:

            if normalized_term in identity_text:
                return True

    return False


def calculate_relevance_score(
    product,
    must_groups,
    requirement_terms=None,
):
    """
    Рассчитывает релевантность товара.

    Приоритет:
    1. название;
    2. бренд;
    3. категория.
    """

    title = get_product_title(product)
    vendor = get_product_vendor(product)
    category = get_product_category(product)

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
    Ищет товары по объединённому каталогу:

    - Answear
    - TOUCH
    - INTERTOP

    Каталог загружается только один раз
    и далее используется из памяти.
    """

    # =========================================
    # БЕРЁМ КАТАЛОГ ИЗ ПАМЯТИ
    # =========================================

    products = load_products()

    results = []
    seen_products = set()

    # =========================================
    # SEARCH TERMS
    # =========================================

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
            normalize(product_query)
        ]

    # =========================================
    # MUST GROUPS
    # =========================================

    if must_groups:

        must_groups = clean_groups(
            must_groups
        )

    else:

        must_groups = [
            [
                normalize(product_query)
            ]
        ]

    # =========================================
    # REQUIREMENT GROUPS
    # =========================================

    requirement_groups = clean_groups(
        requirement_groups
    )

    required_groups = merge_required_groups(
        must_groups,
        requirement_groups,
    )

    # =========================================
    # REQUIREMENT TERMS
    # =========================================

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

    # =========================================
    # EXCLUDE TERMS
    # =========================================

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

    # =========================================
    # ПОИСК
    # =========================================

    for product in products:

        # =====================================
        # ВАЛЮТА
        # =====================================

        product_currency = (
            product.get("currency")
            or product.get("currencyId")
        )

        if product_currency != currency:
            continue

        # =====================================
        # ЦЕНА
        # =====================================

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

        # =====================================
        # СОСТОЯНИЕ
        # =====================================

        if condition == "used":
            continue

        # =====================================
        # ОБЯЗАТЕЛЬНЫЕ ГРУППЫ
        # =====================================

        if not matches_required_groups(
            product,
            required_groups,
        ):
            continue

        # =====================================
        # ИСКЛЮЧЕНИЯ
        # =====================================

        if contains_excluded_term(
            product,
            exclude_terms,
        ):
            continue

        # =====================================
        # RELEVANCE SCORE
        # =====================================

        match_score = calculate_relevance_score(
            product,
            required_groups,
            requirement_terms,
        )

        if match_score == 0:
            continue

        # =====================================
        # SEARCH TERM BONUS
        # =====================================

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

            elif term in full_search_text:

                search_term_score = max(
                    search_term_score,
                    5,
                )

        match_score += search_term_score

        # =====================================
        # СКИДКА
        # =====================================

        old_price = product.get(
            "old_price"
        )

        discount = calculate_discount(
            product
        )

        deal_score = calculate_deal_score(
            product
        )

        # =====================================
        # ЕДИНЫЙ ФОРМАТ
        # =====================================

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

        # =====================================
        # УДАЛЕНИЕ ДУБЛИКАТОВ
        # =====================================

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

    # =========================================
    # СОРТИРОВКА
    # =========================================

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