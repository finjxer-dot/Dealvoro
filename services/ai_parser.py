import json
import os

from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
Ты — анализатор поисковых запросов для Telegram-бота Dealvoro.

На входе:
1. запрос пользователя о товаре;
2. дополнительные требования.

Твоя задача — определить:
1. какие признаки ОБЯЗАТЕЛЬНО должны присутствовать в найденном товаре;
2. какие варианты написания могут использоваться в каталогах;
3. какие типы, подкатегории или назначения товара явно НЕ подходят пользователю.

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

Если товар содержит только Nike, но относится к другой категории,
например к шортам, футболкам или курткам, он НЕ подходит.

Правила:

- бренд выделяй отдельной обязательной группой;
- тип товара выделяй отдельной обязательной группой;
- важную модель выделяй отдельной обязательной группой;
- важные характеристики, без которых товар становится другим товаром,
  также могут быть отдельными обязательными группами;
- для каждого признака добавляй русские, украинские и английские варианты,
  если они реально используются в каталогах;
- исправляй очевидные опечатки;
- не придумывай бренды, модели, характеристики или свойства;
- сохраняй смысл исходного запроса пользователя.

ОБРАБОТКА exclude_terms:

exclude_terms должен содержать не только явно другие типы товаров,
но и подкатегории или назначения товара, которые существенно меняют
смысл исходного запроса и НЕ были указаны пользователем.

Например:

Если пользователь ищет:
"футболка Nike"

то специализированные варианты, такие как:
- футболка для плавания;
- купальная футболка;
- swim shirt;
- rash guard;

нужно считать неподходящими и добавить в exclude_terms.

Если пользователь ищет:
"кроссовки Nike"

то явно другие типы обуви, например:
- сандали;
- сандалі;
- sandals;
- ботинки;
- черевики;
- boots;
- тапочки;
- капці;
- slippers;

нужно считать неподходящими, если они явно относятся к другой категории обуви.

Если пользователь прямо указал специальное назначение,
например:
"футболка для плавания",

то это назначение уже является частью запроса и НЕ должно
попадать в exclude_terms.

ВАЖНО:
- Не добавляй в exclude_terms обычные характеристики, которые могут
  нормально встречаться у подходящего товара.
- Добавляй только то, что реально делает товар неподходящим.
- Для каждого exclude_terms по возможности добавляй русский,
  украинский и английский варианты.
- Учитывай морфологические варианты слов.
  Например:
  ["шорты", "шорти", "shorts"]
  ["куртка", "куртки", "jacket"]
  ["сандали", "сандалі", "sandals"]
- Не создавай слишком широкий список исключений.
- Обычно достаточно 2–4 вариантов на один тип исключения.

ОБРАБОТКА requirements:

requirements — это дополнительные пожелания пользователя,
например:
- мужская;
- беспроводная;
- с гарантией;
- официальная версия.

requirements НЕ являются обязательными для базового поиска.

requirement_terms используются для повышения соответствия товара,
но отсутствие совпадения по requirement_terms само по себе
не должно автоматически исключать товар.

Цена, минимальная цена, максимальная цена, валюта, страна
и состояние товара сюда НЕ включаются.

Пример 1:

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
    "sandals",
    "ботинки",
    "черевики",
    "boots",
    "тапочки",
    "капці",
    "slippers"
  ]
}

Пример 2:

Запрос:
"футболка найк"

Результат:

{
  "product_query": "Nike футболка",
  "search_terms": [
    "Nike футболка",
    "Nike футболки",
    "Nike t-shirt"
  ],
  "must_groups": [
    ["nike"],
    ["футболка", "футболки", "t-shirt", "tshirt"]
  ],
  "requirements": null,
  "requirement_terms": [],
  "exclude_terms": [
    "для плавания",
    "для плавання",
    "купальная",
    "купальна",
    "swim shirt",
    "rash guard"
  ]
}

Пример 3:

Запрос:
"кросовки найк"

Дополнительные требования:
"мужские"

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
  "requirements": "мужские",
  "requirement_terms": [
    "мужские",
    "чоловічі",
    "men",
    "men's"
  ],
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

Пример 4:

Запрос:
"футболка найк для плавания"

Результат НЕ должен исключать плавательные футболки,
потому что пользователь сам указал это назначение.

В этом случае:
- "для плавания" становится частью обязательных признаков;
- аналогичные варианты "для плавання", "swim shirt", "rash guard"
  могут входить в ту же обязательную группу;
- они НЕ должны добавляться в exclude_terms.

Главный принцип:

Найденный товар должен соответствовать СМЫСЛУ запроса,
а не просто содержать отдельные слова из запроса.
"""

def check_query_allowed(product: str) -> bool:
    """
    Проверяет, допустим ли запрос пользователя для Dealvoro.
    True = можно продолжать поиск.
    False = запрос запрещён.
    """

    if not os.getenv("OPENAI_API_KEY"):
        # Если API недоступен, не ломаем бота.
        return True

    moderation_prompt = """
Ты — модератор поисковых запросов интернет-магазина Dealvoro.

Определи, относится ли запрос пользователя к запрещённым 18+ товарам
или сексуальному контенту.

ЗАПРЕЩЕНО:
- секс-игрушки;
- вибраторы;
- фаллоимитаторы;
- эротические товары;
- интимные игрушки;
- товары сексуального назначения;
- другие явно предназначенные для сексуальной стимуляции товары.

РАЗРЕШЕНО:
- обычная одежда;
- нижнее бельё без сексуального назначения;
- косметика;
- парфюмерия;
- товары для здоровья без сексуального назначения;
- обычные товары, даже если слово потенциально двусмысленное.

Верни строго JSON:

{
  "allowed": true
}

или

{
  "allowed": false
}

Не оценивай ничего кроме категории запроса.
"""

    try:
        response = client.responses.create(
            model="gpt-5.4-mini",
            input=[
                {
                    "role": "system",
                    "content": moderation_prompt,
                },
                {
                    "role": "user",
                    "content": product,
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "dealvoro_query_moderation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "allowed": {
                                "type": "boolean"
                            }
                        },
                        "required": ["allowed"],
                        "additionalProperties": False,
                    },
                }
            },
        )

        result = json.loads(response.output_text)
        return bool(result["allowed"])

    except Exception as error:
        print(f"Ошибка проверки запроса: {error}")
        return True

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