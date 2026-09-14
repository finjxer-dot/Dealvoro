import json
import os

from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
Ты — анализатор поисковых запросов для Telegram-бота Dealvoro.

На входе:
1. запрос пользователя о товаре;
2. дополнительные требования.

Твоя задача — определить, какие признаки ОБЯЗАТЕЛЬНО должны присутствовать
в найденном товаре.

Верни строго JSON:

{
  "product_query": "основной запрос",
  "search_terms": [
    "полный вариант 1",
    "полный вариант 2"
  ],
  "must_groups": [
    ["nike"],
    ["кроссовки", "кросівки", "sneakers"]
  ],
  "requirements": "требования или null",
  "requirement_terms": [
    "мужские",
    "чоловічі",
    "men",
    "men's"
  ],
  "exclude_terms": [
    "шорты",
    "шорти",
    "shorts"
  ]
}

ОЧЕНЬ ВАЖНО:

must_groups — это обязательные группы признаков.

Каждая внутренняя группа означает:
"должен совпасть хотя бы ОДИН вариант из этой группы".

Например:

[
  ["nike"],
  ["кроссовки", "кросівки", "sneakers"]
]

означает:

Nike ОБЯЗАТЕЛЕН
И
кроссовки/кросівки/sneakers ОБЯЗАТЕЛЬНЫ.

Если товар содержит только Nike, но это шорты — он НЕ подходит.

Правила:

- бренд выделяй отдельной обязательной группой;
- тип товара выделяй отдельной обязательной группой;
- важную модель также выделяй отдельной обязательной группой;
- для каждого признака добавляй русские, украинские и английские варианты,
  если они реально используются в каталогах;
- исправляй очевидные опечатки;
- не придумывай свойства и модели;
- exclude_terms должен содержать ЯВНЫЕ альтернативные типы товара,
  которые противоречат запросу;
- для каждого exclude_terms обязательно добавляй варианты:
  русский + украинский + английский, если они существуют;
- requirements НЕ являются обязательными для базового поиска;
- requirements используются отдельно для повышения соответствия;
- цена, валюта, страна и состояние товара сюда НЕ включаются;
- обычно достаточно 2–4 вариантов в каждой группе;
- не создавай слишком широкие группы;
- не добавляй в exclude_terms обычные слова, которые могут встречаться
  у подходящего товара случайно.

Примеры вариантов исключений:

шорты:
["шорты", "шорти", "shorts"]

футболка:
["футболка", "футболки", "t-shirt", "tshirt"]

куртка:
["куртка", "куртки", "jacket"]

сандали:
["сандали", "сандалі", "sandals"]

Пример:

Запрос:
"кросовки найк"

Результат:

{
  "product_query": "Nike кроссовки",
  "search_terms": [
    "Nike кроссовки",
    "Nike кросівки",
    "Nike sneakers"
  ],
  "must_groups": [
    ["nike"],
    ["кроссовки", "кросівки", "sneakers"]
  ],
  "requirements": null,
  "requirement_terms": [],
  "exclude_terms": [
    "шорты",
    "шорти",
    "shorts",
    "футболка",
    "футболки",
    "t-shirt",
    "куртка",
    "куртки",
    "jacket",
    "сандали",
    "сандалі",
    "sandals"
  ]
}

Если запрос содержит:
"кросовки найк" + "мужские"

то:

requirements:
"мужские"

requirement_terms:
[
  "мужские",
  "чоловічі",
  "men",
  "men's"
]

Важно:
requirement_terms должны помогать определить соответствие товара,
но отсутствие совпадения по requirement_terms само по себе не означает,
что товар нужно исключить.
"""


def analyze_search_request(
    product: str,
    requirements: str | None,
) -> dict:

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY не найден.")

        return {
            "product_query": product,
            "search_terms": [product],
            "must_groups": [[product]],
            "requirements": requirements,
            "requirement_terms": (
                [requirements] if requirements else []
            ),
            "exclude_terms": [],
        }

    user_text = (
        f"Запрос товара:\n{product}\n\n"
        f"Дополнительные требования:\n"
        f"{requirements if requirements else 'нет'}"
    )

    try:
        response = client.responses.create(
            model="gpt-5.4-mini",
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_text,
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "dealvoro_search_analysis",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "product_query": {
                                "type": "string"
                            },
                            "search_terms": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "minItems": 1,
                                "maxItems": 4
                            },
                            "must_groups": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "minItems": 1,
                                    "maxItems": 4
                                },
                                "minItems": 1,
                                "maxItems": 6
                            },
                            "requirements": {
                                "type": [
                                    "string",
                                    "null"
                                ]
                            },
                            "requirement_terms": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "maxItems": 4
                            },
                            "exclude_terms": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "maxItems": 8
                            },
                        },
                        "required": [
                            "product_query",
                            "search_terms",
                            "must_groups",
                            "requirements",
                            "requirement_terms",
                            "exclude_terms"
                        ],
                        "additionalProperties": False,
                    },
                }
            },
        )

        result = json.loads(response.output_text)

        search_terms = [
            str(term).strip()
            for term in result["search_terms"]
            if str(term).strip()
        ]

        must_groups = []

        for group in result["must_groups"]:
            cleaned_group = [
                str(term).strip()
                for term in group
                if str(term).strip()
            ]

            if cleaned_group:
                must_groups.append(cleaned_group)

        requirement_terms = [
            str(term).strip()
            for term in result["requirement_terms"]
            if str(term).strip()
        ]

        exclude_terms = []

        for term in result["exclude_terms"]:
            parts = (
                str(term)
                .replace('"', "")
                .split(",")
            )

            for part in parts:
                cleaned = part.strip()

                if cleaned:
                    exclude_terms.append(cleaned)

        return {
            "product_query": result["product_query"].strip(),
            "search_terms": search_terms or [product],
            "must_groups": must_groups or [[product]],
            "requirements": (
                result["requirements"].strip()
                if result["requirements"]
                else None
            ),
            "requirement_terms": requirement_terms,
            "exclude_terms": exclude_terms,
        }

    except Exception as error:
        print(f"Ошибка OpenAI: {error}")

        return {
            "product_query": product,
            "search_terms": [product],
            "must_groups": [[product]],
            "requirements": requirements,
            "requirement_terms": (
                [requirements] if requirements else []
            ),
            "exclude_terms": [],
        }