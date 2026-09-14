import json
import os

from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
Ты — анализатор поисковых запросов для Telegram-бота Dealvoro.

Твоя задача:
1. определить точное название/модель товара;
2. выделить дополнительные требования пользователя.

НЕ обрабатывай:
- минимальную цену;
- максимальную цену;
- валюту;
- страну;
- состояние товара.

Эти параметры Dealvoro обрабатывает отдельно.

Верни строго JSON:

{
  "product_query": "название товара",
  "requirements": "требования или null"
}

Правила:
- исправляй очевидные опечатки;
- не придумывай характеристики;
- product_query должен быть коротким и подходящим для поиска;
- requirements должен содержать только дополнительные требования;
- если требований нет, верни null.
"""


def analyze_search_request(
    product: str,
    requirements: str | None,
) -> dict:
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY не найден.")
        return {
            "product_query": product,
            "requirements": requirements,
        }

    user_text = (
        f"Название товара: {product}\n"
        f"Дополнительные требования: "
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
                            "requirements": {
                                "type": ["string", "null"]
                            },
                        },
                        "required": [
                            "product_query",
                            "requirements"
                        ],
                        "additionalProperties": False,
                    },
                }
            },
        )

        result = json.loads(response.output_text)

        return {
            "product_query": result["product_query"].strip(),
            "requirements": (
                result["requirements"].strip()
                if result["requirements"]
                else None
            ),
        }

    except Exception as error:
        print(f"Ошибка OpenAI: {error}")

        # Если API временно недоступен,
        # бот продолжит работать без ИИ.
        return {
            "product_query": product,
            "requirements": requirements,
        }
