import json
import os

from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
Ты — анализатор поисковых запросов для Telegram-бота Dealvoro.

Тебе передают:
1. название/запрос товара;
2. дополнительные требования пользователя.

Твоя задача:
- определить основной товар;
- создать 2–4 поисковых варианта для поиска в разных языках и написаниях;
- определить дополнительные требования;
- создать 2–4 варианта написания каждого требования.

НЕ обрабатывай:
- минимальную цену;
- максимальную цену;
- валюту;
- страну;
- состояние товара.

Эти параметры Dealvoro обрабатывает отдельно.

Верни строго JSON:

{
  "product_query": "основной запрос",
  "search_terms": [
    "вариант 1",
    "вариант 2"
  ],
  "requirements": "требования или null",
  "requirement_terms": [
    "вариант 1",
    "вариант 2"
  ]
}

Правила для search_terms:
- сохраняй бренд;
- сохраняй модель;
- сохраняй важные характеристики;
- исправляй очевидные опечатки;
- добавляй украинский вариант;
- добавляй английский вариант, если он распространён;
- не придумывай информацию;
- обычно 2–4 варианта.

Правила для requirement_terms:
- сохраняй исходный смысл;
- добавляй украинский вариант;
- добавляй английский вариант, если он распространён;
- исправляй очевидные опечатки;
- не придумывай новые требования;
- обычно 2–4 варианта.

Пример:

Название:
кросовки найк

Требования:
мужские

Результат:

{
  "product_query": "Nike кроссовки",
  "search_terms": [
    "Nike кроссовки",
    "Nike кросівки",
    "Nike sneakers"
  ],
  "requirements": "мужские",
  "requirement_terms": [
    "мужские",
    "чоловічі",
    "men",
    "men's"
  ]
}
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
            "requirements": requirements,
            "requirement_terms": (
                [requirements] if requirements else []
            ),
        }

    user_text = (
        f"Название товара:\n{product}\n\n"
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
                        },
                        "required": [
                            "product_query",
                            "search_terms",
                            "requirements",
                            "requirement_terms"
                        ],
                        "additionalProperties": False,
                    },
                }
            },
        )

        result = json.loads(response.output_text)

        search_terms = [
            term.strip()
            for term in result["search_terms"]
            if isinstance(term, str) and term.strip()
        ]

        requirement_terms = [
            term.strip()
            for term in result["requirement_terms"]
            if isinstance(term, str) and term.strip()
        ]

        if not search_terms:
            search_terms = [product]

        return {
            "product_query": result["product_query"].strip(),
            "search_terms": search_terms,
            "requirements": (
                result["requirements"].strip()
                if result["requirements"]
                else None
            ),
            "requirement_terms": requirement_terms,
        }

    except Exception as error:
        print(f"Ошибка OpenAI: {error}")

        return {
            "product_query": product,
            "search_terms": [product],
            "requirements": requirements,
            "requirement_terms": (
                [requirements] if requirements else []
            ),
        }