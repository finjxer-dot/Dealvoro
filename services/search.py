import gzip
import json
import re
from pathlib import Path


# answear_products.json находится в корне Dealvoro
PROJECT_ROOT = Path(__file__).parent.parent
PRODUCTS_FILE = PROJECT_ROOT / "answear_products.json.gz"


def load_products():
    if not PRODUCTS_FILE.exists():
        raise FileNotFoundError(
            f"Файл каталога не найден: {PRODUCTS_FILE}"
        )

    with gzip.open(PRODUCTS_FILE, "rt", encoding="utf-8") as file:
        return json.load(file)


def normalize(text):
    """
    Приводит текст к удобному для поиска виду.
    """

    if not text:
        return ""

    text = str(text).lower()

    # Оставляем латиницу, кириллицу и цифры
    text = re.sub(r"[^a-zа-яёіїєґ0-9]+", " ", text)

    return re.sub(r"\s+", " ", text).strip()


def get_words(text):
    return normalize(text).split()


def calculate_match_score(query, product):
    """
    Оценивает, насколько товар соответствует запросу.
    """

    query_words = get_words(query)

    if not query_words:
        return 0

    name = normalize(product.get("name", ""))
    description = normalize(product.get("description", ""))
    vendor = normalize(product.get("vendor", ""))
    category = normalize(product.get("category", ""))

    name_words = name.split()

    score = 0

    for word in query_words:

        # Точное совпадение слова в названии
        if word in name_words:
            score += 40

        # Частичное совпадение в названии
        elif any(word in name_word for name_word in name_words):
            score += 25

        # Совпадение с брендом
        elif word in vendor:
            score += 30

        # Совпадение в описании
        elif word in description:
            score += 10

        # Совпадение в категории
        elif word in category:
            score += 5

    normalized_query = normalize(query)

    # Весь запрос встречается в названии
    if normalized_query in name:
        score += 50

    # Название товара начинается с запроса
    if name.startswith(normalized_query):
        score += 20

    return score


def calculate_deal_score(product):
    """
    Рассчитывает Deal Score.

    Для Answear используем скидку,
    если есть old_price.
    """

    price = float(product.get("price", 0))
    old_price = product.get("old_price")

    if not old_price or old_price <= price:
        return 0

    discount_percent = ((old_price - price) / old_price) * 100

    # Максимум 100 баллов
    return min(round(discount_percent), 100)


def calculate_discount(product):
    """
    Возвращает размер скидки в процентах.
    """

    price = float(product.get("price", 0))
    old_price = product.get("old_price")

    if not old_price or old_price <= price:
        return 0

    return round(
        ((old_price - price) / old_price) * 100
    )


def search_products(
    product_query,
    min_price=0,
    max_price=None,
    currency="UAH",
    country="UA",
    condition="any",
    requirements=None,
    search_terms=None,
    requirement_terms=None,
):
    """
    Поиск товаров в каталоге Answear.

    country и condition пока принимаются
    для совместимости с bot.py.
    """

    products = load_products()

    results = []

    if search_terms:
        search_terms = [
            term.strip()
            for term in search_terms
            if isinstance(term, str) and term.strip()
        ]
    else:
        search_terms = [product_query]

    if requirement_terms:
        requirement_terms = [
            term.strip()
            for term in requirement_terms
            if isinstance(term, str) and term.strip()
    ]
    else:
        requirement_terms = []

    normalized_requirements = normalize(requirements or "")

    for product in products:

        # ---------------------------------
        # ВАЛЮТА
        # ---------------------------------

        if product.get("currency") != currency:
            continue

        # ---------------------------------
        # ЦЕНА
        # ---------------------------------

        try:
            price = float(product.get("price", 0))
        except (TypeError, ValueError):
            continue

        if price < min_price:
            continue

        if max_price is not None and price > max_price:
            continue

        # ---------------------------------
        # СОСТОЯНИЕ
        # ---------------------------------

        # Answear — каталог новых товаров.
        # Поэтому "Б/у" здесь пока ничего не найдёт.
        if condition == "used":
            continue

        # ---------------------------------
        # ПОИСК
        # ---------------------------------

        match_score = max(
            calculate_match_score(term, product)
            for term in search_terms
        )

        if match_score == 0:
            continue

        # ---------------------------------
        # ДОПОЛНИТЕЛЬНЫЕ ТРЕБОВАНИЯ
        # ---------------------------------

        if requirement_terms:
            searchable_text = normalize(
                " ".join(
                    [
                        str(product.get("name", "")),
                        str(product.get("description", "")),
                        str(product.get("vendor", "")),
                        str(product.get("category", "")),
                    ]
                )
            )

            matched_requirements = 0

            for requirement in requirement_terms:
                normalized_requirement = normalize(requirement)

                if (
                    normalized_requirement
                    and normalized_requirement in searchable_text
                ):
                    matched_requirements += 1

            # Требование влияет на рейтинг,
            # но отсутствие совпадения НЕ удаляет товар.
            match_score += matched_requirements * 15

        # ---------------------------------
        # СОЗДАЁМ ФОРМАТ ДЛЯ bot.py
        # ---------------------------------

        old_price = product.get("old_price")

        discount = calculate_discount(product)
        deal_score = calculate_deal_score(product)

        product_copy = {
            "title": product.get(
                "name",
                "Без названия"
            ),

            "store": "Answear",

            "rating": None,

            "reviews": None,

            "price": price,

            "old_price": old_price,

            "currency": product.get(
                "currency",
                currency
            ),

            "condition": "new",

            "description": product.get(
                "description",
                ""
            ),

            "vendor": product.get(
                "vendor",
                ""
            ),

            "category": product.get(
                "category",
                ""
            ),

            "picture": product.get(
                "picture",
                ""
            ),

            "url": product.get(
                "url",
                ""
            ),

            "match_score": match_score,

            "deal_score": deal_score,

            "discount": discount,
        }

        results.append(product_copy)

    # ---------------------------------
    # СОРТИРОВКА
    # ---------------------------------

    results.sort(
        key=lambda item: (
            item["match_score"],
            item["deal_score"],
            -item["price"],
        ),
        reverse=True,
    )

    return results