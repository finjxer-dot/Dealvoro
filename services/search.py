import gzip
import re
from pathlib import Path

import ijson

from services.store_feeds import (
    FEEDS,
    load_store_products,
)


# =========================================
# ПУТИ
# =========================================

PROJECT_ROOT = (
    Path(__file__).parent.parent
)

PRODUCTS_FILE = (
    PROJECT_ROOT
    / "answear_products.json.gz"
)


# =========================================
# GENERIC-СЛОВА (ЗАЩИТА)
# =========================================

GENERIC_TERMS = {
    "underwear",
    "clothing",
    "clothes",
    "apparel",
    "wear",
    "shoes",
    "footwear",
    "accessories",
    "accessory",
    "sportswear",
    "sport",
    "sports",
    "fashion",
    "outfit",

    "electronics",
    "devices",
    "device",
    "gadgets",
    "gadget",
    "tech",
    "technology",

    "goods",
    "product",
    "products",
    "item",
    "items",
}


# =========================================
# ПОТОКОВАЯ ЗАГРУЗКА JSON.GZ
# =========================================

def iter_json_gz(
    file_path,
):
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
    if cache_path.exists():

        print(
            f"{store}: "
            "потоковая загрузка .gz"
        )

        yield from iter_json_gz(
            cache_path
        )

        return

    print(
        f"{store}: "
        ".gz не найден, "
        "используется загрузчик фида"
    )

    products = load_store_products(
        store
    )

    for product in products:

        yield product


# =========================================
# ВСЕ МАГАЗИНЫ
# =========================================

def iter_all_products():

    if not PRODUCTS_FILE.exists():

        raise FileNotFoundError(
            "Файл каталога Answear "
            f"не найден:\n{PRODUCTS_FILE}"
        )

    print(
        "Answear: "
        "потоковая загрузка .gz"
    )

    yield from iter_json_gz(
        PRODUCTS_FILE
    )

    for store, config in FEEDS.items():

        cache_path = config.get(
            "cache"
        )

        if not cache_path:

            print(
                f"{store}: "
                "не указан cache"
            )

            continue

        yield from iter_store_products(
            store,
            cache_path,
        )


# =========================================
# НОРМАЛИЗАЦИЯ
# =========================================

def normalize(
    text,
):
    if not text:
        return ""

    text = str(
        text
    ).lower()

    text = re.sub(
        r"[^a-zа-яёіїєґ0-9]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def get_words(
    text,
):
    return normalize(
        text
    ).split()


# =========================================
# ПОЛЯ ТОВАРА
# =========================================

def get_product_title(
    product,
):
    return normalize(
        product.get("name")
        or product.get("title")
        or ""
    )


def get_product_description(
    product,
):
    return normalize(
        product.get(
            "description",
            "",
        )
    )


def get_product_vendor(
    product,
):
    return normalize(
        product.get(
            "vendor",
            "",
        )
    )


def get_product_category(
    product,
):
    return normalize(
        product.get(
            "category",
            "",
        )
    )


def extract_attributes_text(
    product,
):

    attribute_fields = [
        "color",
        "colour",
        "material",
        "composition",
        "style",
        "fit",
        "length",
        "pattern",
        "season",
        "gender",
        "age_group",
        "ageGroup",
        "attributes",
        "features",
        "tags",
        "keywords",
        "category_path",
        "category_name",
        "subcategory",
    ]

    parts = []

    for field in attribute_fields:

        value = product.get(field)

        if value is None:
            continue

        if isinstance(value, (list, tuple)):

            for item in value:

                if item is not None:
                    parts.append(str(item))

        elif isinstance(value, dict):

            for sub_value in value.values():

                if sub_value is not None:
                    parts.append(str(sub_value))

        else:

            parts.append(str(value))

    if not parts:
        return ""

    return normalize(" ".join(parts))


def get_product_title_text(
    product,
):
    return get_product_title(product)


def get_product_strong_search_text(
    product,
):
    return " ".join(
        [
            get_product_title(product),
            get_product_vendor(product),
        ]
    ).strip()


def get_product_soft_search_text(
    product,
):

    parts = [
        get_product_title(product),
        get_product_vendor(product),
        get_product_description(product),
        extract_attributes_text(product),
    ]

    return " ".join(
        part
        for part in parts
        if part
    ).strip()


def get_product_full_search_text(
    product,
):
    return " ".join(
        [
            get_product_title(
                product
            ),
            get_product_description(
                product
            ),
            get_product_vendor(
                product
            ),
        ]
    ).strip()


# =========================================
# DEAL SCORE
# =========================================

def calculate_deal_score(
    product,
):
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
            float(
                old_price
            )
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
        (
            old_price
            - price
        )
        / old_price
    ) * 100

    return min(
        round(
            discount_percent
        ),
        100,
    )


def calculate_discount(
    product,
):
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
            float(
                old_price
            )
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
            (
                old_price
                - price
            )
            / old_price
        ) * 100
    )


# =========================================
# СОВПАДЕНИЕ ТЕРМИНА
# =========================================

def term_matches_text(
    term,
    text,
):

    normalized_term = normalize(
        term
    )

    normalized_text = normalize(
        text
    )

    if (
        not normalized_term
        or not normalized_text
    ):

        return False

    term_words = (
        normalized_term.split()
    )

    text_words = (
        normalized_text.split()
    )

    if len(term_words) == 1:

        return (
            normalized_term
            in text_words
        )

    return (
        normalized_term
        in normalized_text
    )


# =========================================
# GROUPS
# =========================================

def clean_groups(
    groups,
):
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


def remove_generic_terms_from_first_group(
    must_groups,
):

    if not must_groups:
        return must_groups

    result = []

    for index, group in enumerate(must_groups):

        if not isinstance(group, list):
            continue

        if index != 0:

            result.append(list(group))
            continue

        filtered = []

        for term in group:

            if not isinstance(term, str):
                continue

            key = normalize(term)

            if not key:
                continue

            if key in GENERIC_TERMS:
                continue

            filtered.append(term)

        if filtered:

            result.append(filtered)

    return result


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
# MUST GROUPS (ЖЁСТКИЕ)
# =========================================

def matches_required_groups(
    product,
    must_groups,
):
    """
    ВСЕ группы обязательны.

    Внутри одной группы достаточно
    одного совпадения.

    Логика поиска:

    - Первая группа (must_groups[0] —
      это ТИП ТОВАРА) проверяется
      ТОЛЬКО по названию.

      Причина: если проверять по vendor,
      то "Calvin Klein Underwear" в vendor
      подменяет собой тип товара.

    - Остальные группы (бренд, модель,
      цвет, пол, размер) проверяются
      по title + vendor.
    """

    if not must_groups:

        return True

    title_text = get_product_title_text(
        product
    )

    strong_text = get_product_strong_search_text(
        product
    )

    if not strong_text:

        return False

    for index, group in enumerate(must_groups):

        if not isinstance(
            group,
            list,
        ):

            return False

        if not group:

            return False

        is_first_group = (index == 0)

        if is_first_group:

            search_text = title_text

        else:

            search_text = strong_text

        if not search_text:

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

            if term_matches_text(
                normalized_term,
                search_text,
            ):

                group_matched = True

                break

        if not group_matched:

            return False

    return True


# =========================================
# SOFT GROUPS (МЯГКИЕ)
# =========================================

def matches_soft_groups(
    product,
    soft_groups,
):

    if not soft_groups:

        return True

    title = get_product_title(product)
    vendor = get_product_vendor(product)
    description = get_product_description(product)
    attributes = extract_attributes_text(product)

    has_extra_text = bool(
        description or attributes
    )

    soft_text = get_product_soft_search_text(
        product
    )

    for group in soft_groups:

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

            if term_matches_text(
                normalized_term,
                soft_text,
            ):

                group_matched = True

                break

        if not group_matched:

            if not has_extra_text:

                continue

            return False

    return True


# =========================================
# EXCLUDE TERMS
# =========================================

def contains_excluded_term(
    product,
    exclude_terms,
):
    """
    Проверяет exclude_terms.

    ВАЖНО: проверяем ТОЛЬКО название (title).

    Причина: если проверять description, то
    описание смартфона может содержать
    "в комплекте чехол" — и смартфон
    отсеется по exclude-термину "чехол".
    Это баг.

    Title — главное поле. Если в названии
    написано "Чехол для iPhone" — это точно
    чехол, а не смартфон.
    """

    if not exclude_terms:
        return False

    title = get_product_title(product)

    if not title:
        return False

    for term in exclude_terms:

        if not isinstance(term, str):
            continue

        normalized_term = normalize(term)

        if not normalized_term:
            continue

        if term_matches_text(
            normalized_term,
            title,
        ):
            return True

    return False


# =========================================
# REQUIREMENT TERMS
# =========================================

def _term_words_for_comparison(
    term,
):

    stop_words = {
        "для",
        "for",
        "of",
        "with",
        "и",
        "й",
        "та",
        "з",
        "у",
        "в",
        "во",
        "на",
        "по",
        "с",
        "со",
    }

    return [
        word
        for word in normalize(
            term
        ).split()
        if word
        and word not in stop_words
    ]


def _terms_are_variants(
    first,
    second,
):

    first_words = (
        _term_words_for_comparison(
            first
        )
    )

    second_words = (
        _term_words_for_comparison(
            second
        )
    )

    if not first_words or not second_words:

        return False

    for first_word in first_words:

        for second_word in second_words:

            if first_word == second_word:

                return True

            if (
                len(first_word) >= 4
                and len(second_word) >= 4
                and (
                    first_word[:4]
                    == second_word[:4]
                )
            ):

                return True

    return False


def filter_duplicate_requirement_terms(
    requirement_terms,
    required_groups,
    soft_groups=None,
):

    if not requirement_terms:

        return []

    normalized_required_terms = []

    for group in required_groups:

        if not isinstance(
            group,
            list,
        ):

            continue

        for term in group:

            if not isinstance(
                term,
                str,
            ):

                continue

            normalized_term = normalize(
                term
            )

            if normalized_term:

                normalized_required_terms.append(
                    normalized_term
                )

    if soft_groups:

        for group in soft_groups:

            if not isinstance(
                group,
                list,
            ):

                continue

            for term in group:

                if not isinstance(
                    term,
                    str,
                ):

                    continue

                normalized_term = normalize(
                    term
                )

                if normalized_term:

                    normalized_required_terms.append(
                        normalized_term
                    )

    result = []

    seen = set()

    for term in requirement_terms:

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

        if normalized_term in seen:

            continue

        duplicate = False

        for required_term in (
            normalized_required_terms
        ):

            if (
                normalized_term
                == required_term
            ):

                duplicate = True
                break

            if _terms_are_variants(
                normalized_term,
                required_term,
            ):

                duplicate = True
                break

        if duplicate:

            continue

        seen.add(
            normalized_term
        )

        result.append(
            normalized_term
        )

    return result


def matches_requirement_terms(
    product,
    requirement_terms,
):

    if not requirement_terms:

        return True

    title = get_product_title(
        product
    )

    vendor = get_product_vendor(
        product
    )

    description = get_product_description(
        product
    )

    for term in requirement_terms:

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

        if term_matches_text(
            normalized_term,
            title,
        ):

            continue

        if term_matches_text(
            normalized_term,
            vendor,
        ):

            continue

        if term_matches_text(
            normalized_term,
            description,
        ):

            continue

        return False

    return True


# =========================================
# АУДИТОРИЯ ТОВАРА
# =========================================

def get_structured_audience(
    product,
):

    field_names = [
        "audience",
        "age_group",
        "ageGroup",
        "gender_age",
        "target_age",
        "targetAge",
    ]

    values = []

    for field_name in field_names:

        value = product.get(
            field_name
        )

        if value is None:
            continue

        if isinstance(
            value,
            (list, tuple),
        ):

            values.extend(
                str(item)
                for item in value
                if item is not None
            )

        else:

            values.append(
                str(value)
            )

    if not values:

        return None

    combined = normalize(
        " ".join(
            values
        )
    )

    if not combined:

        return None

    child_patterns = [
        r"\bchild\b",
        r"\bchildren\b",
        r"\bkids\b",
        r"\bjuvenile\b",
        r"\bдит",
        r"\bдет",
        r"\bподрост",
        r"\bпідліт",
    ]

    for pattern in child_patterns:

        if re.search(
            pattern,
            combined,
            flags=re.IGNORECASE,
        ):

            return "child"

    adult_patterns = [
        r"\badult\b",
        r"\badults\b",
    ]

    for pattern in adult_patterns:

        if re.search(
            pattern,
            combined,
            flags=re.IGNORECASE,
        ):

            return "adult"

    return None


def extract_age_numbers(
    text,
):

    normalized = normalize(
        text
    )

    if not normalized:

        return False

    patterns = [

        r"\b\d{1,2}\s*(?:-|–|—|to)\s*\d{1,2}\s*(?:years?|лет|років|роки)\b",

        r"\b\d{1,2}\s*(?:years?|лет|років|роки)\b",

        r"\bage\s*\d{1,2}\b",

        r"\b\d{1,2}\s*(?:months?|месяцев|місяців)\b",
    ]

    for pattern in patterns:

        if re.search(
            pattern,
            normalized,
        ):

            return True

    return False


def looks_like_child_product(
    product,
):

    title = get_product_title(
        product
    )

    vendor = get_product_vendor(
        product
    )

    product_text = " ".join(
        [
            title,
            vendor,
        ]
    ).strip()

    if product_text:

        child_patterns = [
            r"\bдет",
            r"\bдит",
            r"\bchild\b",
            r"\bchildren\b",
            r"\bkid\b",
            r"\bkids\b",
            r"\bjunior\b",
            r"\byouth\b",
            r"\bteen\b",
            r"\bподрост",
            r"\bпідліт",
        ]

        for pattern in child_patterns:

            if re.search(
                pattern,
                product_text,
                flags=re.IGNORECASE,
            ):

                return True

        if extract_age_numbers(
            product_text
        ):

            return True

    structured_audience = (
        get_structured_audience(
            product
        )
    )

    if structured_audience == "child":

        return True

    return False


def matches_audience(
    product,
    audience,
):

    normalized_audience = str(
        audience or "adult"
    ).strip().lower()

    if normalized_audience == "child":

        return looks_like_child_product(
            product
        )

    if looks_like_child_product(
        product
    ):

        return False

    return True


# =========================================
# RELEVANCE SCORE
# =========================================

def calculate_relevance_score(
    product,
    must_groups,
    soft_groups=None,
    requirement_terms=None,
):

    title = get_product_title(
        product
    )

    vendor = get_product_vendor(
        product
    )

    description = get_product_description(
        product
    )

    score = 0

    for index, group in enumerate(must_groups):

        if not isinstance(group, list):
            continue

        is_first_group = (index == 0)

        best_group_score = 0

        for term in group:

            normalized_term = normalize(
                term
            )

            if not normalized_term:

                continue

            if is_first_group:

                if term_matches_text(
                    normalized_term,
                    title,
                ):

                    best_group_score = max(
                        best_group_score,
                        100,
                    )

                continue

            if term_matches_text(
                normalized_term,
                title,
            ):

                best_group_score = max(
                    best_group_score,
                    100,
                )

            elif term_matches_text(
                normalized_term,
                vendor,
            ):

                best_group_score = max(
                    best_group_score,
                    70,
                )

        if best_group_score == 0:

            return 0

        score += (
            best_group_score
        )

    if soft_groups:

        for group in soft_groups:

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
                        30,
                    )

                elif term_matches_text(
                    normalized_term,
                    vendor,
                ):

                    best_group_score = max(
                        best_group_score,
                        20,
                    )

                elif term_matches_text(
                    normalized_term,
                    description,
                ):

                    best_group_score = max(
                        best_group_score,
                        15,
                    )

            score += (
                best_group_score
            )

    if requirement_terms:

        for term in requirement_terms:

            normalized_term = normalize(
                term
            )

            if not normalized_term:

                continue

            if term_matches_text(
                normalized_term,
                title,
            ):

                score += 40

            elif term_matches_text(
                normalized_term,
                vendor,
            ):

                score += 25

            elif term_matches_text(
                normalized_term,
                description,
            ):

                score += 15

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
    soft_groups=None,
    requirement_terms=None,
    exclude_terms=None,
    requirement_groups=None,
    audience="adult",
):

    results = []

    seen_products = set()

    products_checked = 0

    target_currency = normalize_currency(
        currency
    )

    target_condition = normalize_condition(
        condition
    )

    target_audience = (
        str(
            audience or "adult"
        )
        .strip()
        .lower()
    )

    if target_audience not in {
        "adult",
        "child",
    }:

        target_audience = "adult"

    try:

        min_price = float(
            min_price
        )

    except (
        TypeError,
        ValueError,
    ):

        min_price = 0

    if max_price in (
        None,
        "",
        0,
        0.0,
    ):

        max_price = None

    else:

        try:

            max_price = float(
                max_price
            )

        except (
            TypeError,
            ValueError,
        ):

            max_price = None

    if search_terms:

        cleaned_search_terms = []

        for term in search_terms:

            if not isinstance(
                term,
                str,
            ):

                continue

            term = normalize(
                term
            )

            if term:

                cleaned_search_terms.append(
                    term
                )

        search_terms = list(
            dict.fromkeys(
                cleaned_search_terms
            )
        )

    else:

        normalized_product = normalize(
            product_query
        )

        search_terms = (
            [normalized_product]
            if normalized_product
            else []
        )

    if must_groups:

        must_groups = clean_groups(
            must_groups
        )

    else:

        normalized_product = normalize(
            product_query
        )

        words = (
            normalized_product.split()
            if normalized_product
            else []
        )

        must_groups = [
            [word]
            for word in words
        ]

    must_groups = remove_generic_terms_from_first_group(
        must_groups
    )

    if not must_groups:

        normalized_product = normalize(
            product_query
        )

        if normalized_product:

            must_groups = [[normalized_product]]

        else:

            must_groups = []

    if soft_groups:

        soft_groups = clean_groups(
            soft_groups
        )

    else:

        soft_groups = []

    required_groups = (
        merge_required_groups(
            must_groups,
            requirement_groups,
        )
    )

    if requirement_terms:

        cleaned_requirement_terms = []

        for term in requirement_terms:

            if not isinstance(
                term,
                str,
            ):

                continue

            term = normalize(
                term
            )

            if term:

                cleaned_requirement_terms.append(
                    term
                )

        requirement_terms = list(
            dict.fromkeys(
                cleaned_requirement_terms
            )
        )

    else:

        requirement_terms = []

    requirement_terms = (
        filter_duplicate_requirement_terms(
            requirement_terms,
            required_groups,
            soft_groups,
        )
    )

    if exclude_terms:

        cleaned_exclude_terms = []

        for term in exclude_terms:

            if not isinstance(
                term,
                str,
            ):

                continue

            term = normalize(
                term
            )

            if term:

                cleaned_exclude_terms.append(
                    term
                )

        exclude_terms = list(
            dict.fromkeys(
                cleaned_exclude_terms
            )
        )

    else:

        exclude_terms = []

    # =====================================
    # ПОТОКОВЫЙ ПОИСК
    # =====================================

    for product in iter_all_products():

        products_checked += 1

        if not isinstance(
            product,
            dict,
        ):

            continue

        # =================================
        # ВАЛЮТА
        # =================================

        product_currency = normalize_currency(
            product.get(
                "currency"
            )
            or product.get(
                "currencyId"
            )
            or product.get(
                "priceCurrency"
            )
        )

        if not product_currency:

            continue

        if (
            product_currency
            != target_currency
        ):

            continue

        # =================================
        # ЦЕНА
        # =================================

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

        # =================================
        # TITLE (нужно для condition)
        # =================================

        title_raw = (
            product.get(
                "name"
            )
            or product.get(
                "title"
            )
            or "Без названия"
        )

        # =================================
        # СОСТОЯНИЕ
        # =================================

        product_condition = normalize_condition(
            product.get("condition"),
            title=title_raw,
        )

        if (
            target_condition == "used"
            and product_condition != "used"
        ):

            continue

        if (
            target_condition == "new"
            and product_condition == "used"
        ):

            continue

        # =================================
        # АУДИТОРИЯ
        # =================================

        if not matches_audience(
            product,
            target_audience,
        ):

            continue

        # =================================
        # ОБЯЗАТЕЛЬНЫЕ ГРУППЫ (STRONG)
        # =================================

        if not matches_required_groups(
            product,
            required_groups,
        ):

            continue

        # =================================
        # МЯГКИЕ ГРУППЫ (SOFT)
        # =================================

        if not matches_soft_groups(
            product,
            soft_groups,
        ):

            continue

        # =================================
        # ДОПОЛНИТЕЛЬНЫЕ ТРЕБОВАНИЯ
        # =================================

        if not matches_requirement_terms(
            product,
            requirement_terms,
        ):

            continue

        # =================================
        # ОБЫЧНЫЕ EXCLUDE TERMS
        # =================================

        if contains_excluded_term(
            product,
            exclude_terms,
        ):

            continue

        # =================================
        # RELEVANCE
        # =================================

        match_score = (
            calculate_relevance_score(
                product,
                required_groups,
                soft_groups,
                requirement_terms,
            )
        )

        if match_score <= 0:

            continue

        # =================================
        # SEARCH BONUS
        # =================================

        title = get_product_title(
            product
        )

        full_search_text = (
            get_product_full_search_text(
                product
            )
        )

        search_term_score = 0

        for term in search_terms:

            if not term:

                continue

            if term_matches_text(
                term,
                title,
            ):

                search_term_score = max(
                    search_term_score,
                    30,
                )

            elif term_matches_text(
                term,
                full_search_text,
            ):

                search_term_score = max(
                    search_term_score,
                    3,
                )

        match_score += (
            search_term_score
        )

        # =================================
        # OLD PRICE
        # =================================

        old_price = product.get(
            "old_price"
        )

        try:

            old_price_float = (
                float(
                    old_price
                )
                if old_price is not None
                else None
            )

        except (
            TypeError,
            ValueError,
        ):

            old_price_float = None

        # =================================
        # DEAL
        # =================================

        discount = calculate_discount(
            product
        )

        deal_score = calculate_deal_score(
            product
        )

        # =================================
        # STORE
        # =================================

        store = (
            product.get(
                "store"
            )
            or product.get(
                "shop"
            )
            or "Неизвестный магазин"
        )

        # =================================
        # URL
        # =================================

        url = (
            product.get(
                "url"
            )
            or product.get(
                "link"
            )
            or product.get(
                "productUrl"
            )
            or ""
        )

        # =================================
        # PICTURE
        # =================================

        picture = (
            product.get(
                "picture"
            )
            or product.get(
                "image"
            )
            or product.get(
                "image_url"
            )
            or product.get(
                "imageUrl"
            )
            or ""
        )

        # =================================
        # ЕДИНЫЙ ФОРМАТ
        # =================================

        product_copy = {

            "title": title_raw,

            "store": store,

            "rating": product.get(
                "rating"
            ),

            "reviews": product.get(
                "reviews"
            ),

            "price": float(
                price
            ),

            "old_price": (
                old_price_float
            ),

            "currency": (
                product_currency
            ),

            "condition": (
                product_condition
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

            "picture": picture,

            "url": url,

            "canonical_url": product.get(
                "canonical_url",
                "",
            ),

            "match_score": (
                match_score
            ),

            "deal_score": (
                deal_score
            ),

            "discount": (
                discount
            ),

            "audience": (
                target_audience
            ),
        }

        # =================================
        # ДУБЛИКАТЫ
        # =================================

        if url:

            product_key = (
                store,
                url,
            )

        else:

            product_key = (
                store,
                normalize(
                    title_raw
                ),
                float(
                    price
                ),
            )

        if product_key in seen_products:

            continue

        seen_products.add(
            product_key
        )

        results.append(
            product_copy
        )

    # =====================================
    # СТАТИСТИКА
    # =====================================

    print(
        f"Каталог проверен: "
        f"{products_checked} товаров"
    )

    print(
        f"Подходящих товаров: "
        f"{len(results)}"
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


# =========================================
# CURRENCY
# =========================================

def normalize_currency(
    value,
):
    if value is None:

        return ""

    text = str(
        value
    ).strip().upper()

    aliases = {

        "₴": "UAH",
        "UAH": "UAH",
        "ГРН": "UAH",
        "ГРН.": "UAH",

        "$": "USD",
        "USD": "USD",
        "US$": "USD",

        "€": "EUR",
        "EUR": "EUR",
    }

    return aliases.get(
        text,
        text,
    )


# =========================================
# CONDITION
# =========================================

def normalize_condition(
    value,
    title=None,
):
    """
    Нормализует состояние товара.

    Приоритет:

    1. Явное поле condition.
    2. Признак б/у в названии (title).

    Если поле condition = "new",
    но в названии есть "Б/У" —
    ставим "used".
    """

    if value is not None:

        text = normalize(value)

        if text in {
            "used",
            "б у",
            "бу",
            "вживаний",
            "вживана",
            "вживане",
            "бивший у використанні",
            "second hand",
            "pre owned",
        }:

            return "used"

        if text in {
            "any",
            "любое",
            "любая",
            "будь яке",
            "будь який",
        }:

            return "any"

    if title:

        title_normalized = normalize(title)

        if re.search(r"\bб у\b", title_normalized):
            return "used"

        if re.match(r"^бу\b", title_normalized):
            return "used"

        if re.search(r"\bвживан", title_normalized):
            return "used"

        if re.search(r"\bвідновлен", title_normalized):
            return "used"

        if re.search(
            r"\bsecond\s*hand\b|\bpre\s*owned\b",
            title_normalized,
        ):
            return "used"

    return "new"