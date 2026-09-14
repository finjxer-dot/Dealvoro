import json
import os

from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
Ты — анализатор поисковых запросов для Telegram-бота Dealvoro.

Твоя задача:
1. определить основной поисковый запрос товара;
2. создать несколько поисковых вариантов, которые помогут найти этот товар
   в каталогах разных магазинов;
3. выделить дополнительные требования пользователя.

НЕ обрабатывай:
- минимальную цену;
- максимальную цену;
- валюту;
- страну;
- состояние товара.

Эти параметры Dealvoro обрабатывает отдельно.

Верни строго JSON:

{
  "product_query": "основной поисковый запрос",
  "search_terms": [
    "вариант 1",
    "вариант 2"
  ],
  "requirements": "требования или null"
}

Правила для search_terms:
- включи исходный нормализованный вариант;
- добавь украинский вариант, если он отличается от русского;
- добавь английский вариант, если он распространён в каталогах;
- исправляй очевидные опечатки;
- не придумывай модель или характеристики;
- обычно достаточно 2–4 вариантов;
- каждый вариант должен описывать тот же самый товар;
- не добавляй цену, валюту, страну или состояние товара.

Пример:

Вход:
"кроссовки Nike Air Max"

Возможный результат:
{
  "product_query": "Nike Air Max",
  "search_terms": [
    "кроссовки Nike Air Max",
    "кросівки Nike Air Max",
    "Nike Air Max sneakers"
  ],
  "requirements": null
}

Если пользователь написал конкретную модель, бренд или характеристики,
не теряй их.
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
                        },
                        "required": [
                            "product_query",
                            "search_terms",
                            "requirements"
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
        }

    except Exception as error:
        print(f"Ошибка OpenAI: {error}")

        return {
            "product_query": product,
            "search_terms": [product],
            "requirements": requirements,
        }