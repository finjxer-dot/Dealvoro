import asyncio
import html
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from dotenv import load_dotenv

from services.search import search_products


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# СОСТОЯНИЯ ПОИСКА
# =========================

class SearchForm(StatesGroup):
    product = State()
    min_price = State()
    max_price = State()
    currency = State()
    country = State()
    condition = State()
    requirements = State()


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🛒 Найти товар"),
            KeyboardButton(text="📋 Мои поиски"),
        ],
        [
            KeyboardButton(text="🔔 Отслеживание цен"),
            KeyboardButton(text="⭐ Избранное"),
        ],
        [
            KeyboardButton(text="⚙️ Настройки"),
        ],
    ],
    resize_keyboard=True,
)


# =========================
# КНОПКИ ВЫБОРА
# =========================

currency_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="₴ UAH"),
            KeyboardButton(text="$ USD"),
        ],
        [
            KeyboardButton(text="€ EUR"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


condition_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🆕 Новый"),
            KeyboardButton(text="♻️ Б/у"),
        ],
        [
            KeyboardButton(text="📦 Любое"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


country_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🇺🇦 Украина"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


# =========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================

def condition_name(condition: str) -> str:
    names = {
        "new": "Новый",
        "used": "Б/у",
        "any": "Любое",
    }

    return names.get(condition, "Не указано")


def currency_symbol(currency: str) -> str:
    symbols = {
        "UAH": "₴",
        "USD": "$",
        "EUR": "€",
    }

    return symbols.get(currency, currency)


def clean_url(url: str) -> str:
    """
    Исправляет тестовые URL, если они случайно
    сохранились в Markdown-формате:
    [https://example.com](https://example.com)
    """

    if not url:
        return ""

    url = url.strip()

    if url.startswith("[") and "](" in url and url.endswith(")"):
        url = url.split("](", 1)[1][:-1]

    return url


def format_price(price: float) -> str:
    """
    Красивое отображение цены:
    3499 -> 3 499
    24999 -> 24 999
    """

    if float(price).is_integer():
        return f"{int(price):,}".replace(",", " ")

    return f"{price:,.2f}".replace(",", " ")


def create_product_keyboard(url: str):
    url = clean_url(url)

    if not url:
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Открыть товар",
                    url=url,
                )
            ]
        ]
    )


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "👋 Добро пожаловать в Dealvoro!\n\n"
        "🛒 Я помогу найти выгодные предложения "
        "на украинских маркетплейсах и магазинах.\n\n"
        "Выбери действие:",
        reply_markup=main_keyboard,
    )


# =========================
# НАЧАЛО ПОИСКА
# =========================

@dp.message(F.text == "🛒 Найти товар")
async def find_product(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SearchForm.product)

    await message.answer(
        "🛒 <b>Что ты хочешь найти?</b>\n\n"
        "Например:\n"
        "• iPhone 15\n"
        "• игровая мышь Logitech\n"
        "• монитор 144 Гц\n"
        "• беспроводные наушники",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================
# ТОВАР
# =========================

@dp.message(SearchForm.product)
async def process_product(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(
            "❌ Напиши название товара текстом."
        )
        return

    product = message.text.strip()

    if len(product) < 2:
        await message.answer(
            "❌ Слишком короткий запрос.\n"
            "Напиши название товара ещё раз."
        )
        return

    await state.update_data(product=product)
    await state.set_state(SearchForm.min_price)

    await message.answer(
        "💰 <b>Минимальная цена</b>\n\n"
        "Напиши минимальную цену.\n"
        "Если минимальной цены нет — напиши <b>0</b>.",
        parse_mode="HTML",
    )


# =========================
# МИНИМАЛЬНАЯ ЦЕНА
# =========================

@dp.message(SearchForm.min_price)
async def process_min_price(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Введи цену числом.")
        return

    text = message.text.strip().replace(",", ".").replace(" ", "")

    try:
        min_price = float(text)

        if min_price < 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Введи цену числом.\n\n"
            "Например: <code>500</code>",
            parse_mode="HTML",
        )
        return

    await state.update_data(min_price=min_price)
    await state.set_state(SearchForm.max_price)

    await message.answer(
        "💰 <b>Максимальная цена</b>\n\n"
        "Напиши максимальную цену.",
        parse_mode="HTML",
    )


# =========================
# МАКСИМАЛЬНАЯ ЦЕНА
# =========================

@dp.message(SearchForm.max_price)
async def process_max_price(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Введи цену числом.")
        return

    text = message.text.strip().replace(",", ".").replace(" ", "")

    try:
        max_price = float(text)

        if max_price < 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Введи цену числом.\n\n"
            "Например: <code>15000</code>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()

    if max_price < data["min_price"]:
        await message.answer(
            "❌ Максимальная цена не может быть меньше "
            "минимальной.\n\n"
            "Попробуй ещё раз."
        )
        return

    await state.update_data(max_price=max_price)
    await state.set_state(SearchForm.currency)

    await message.answer(
        "💵 <b>Выбери валюту</b>",
        parse_mode="HTML",
        reply_markup=currency_keyboard,
    )


# =========================
# ВАЛЮТА
# =========================

@dp.message(SearchForm.currency)
async def process_currency(message: Message, state: FSMContext):
    currency_map = {
        "₴ UAH": "UAH",
        "$ USD": "USD",
        "€ EUR": "EUR",
    }

    currency = currency_map.get(message.text)

    if not currency:
        await message.answer(
            "❌ Пожалуйста, выбери валюту кнопкой.",
            reply_markup=currency_keyboard,
        )
        return

    await state.update_data(currency=currency)
    await state.set_state(SearchForm.country)

    await message.answer(
        "🇺🇦 <b>Выбери страну поиска</b>",
        parse_mode="HTML",
        reply_markup=country_keyboard,
    )


# =========================
# СТРАНА
# =========================

@dp.message(SearchForm.country)
async def process_country(message: Message, state: FSMContext):
    if message.text != "🇺🇦 Украина":
        await message.answer(
            "❌ Пожалуйста, выбери страну кнопкой.",
            reply_markup=country_keyboard,
        )
        return

    await state.update_data(country="UA")
    await state.set_state(SearchForm.condition)

    await message.answer(
        "📦 <b>Какое состояние товара тебе нужно?</b>",
        parse_mode="HTML",
        reply_markup=condition_keyboard,
    )


# =========================
# СОСТОЯНИЕ
# =========================

@dp.message(SearchForm.condition)
async def process_condition(message: Message, state: FSMContext):
    condition_map = {
        "🆕 Новый": "new",
        "♻️ Б/у": "used",
        "📦 Любое": "any",
    }

    condition = condition_map.get(message.text)

    if not condition:
        await message.answer(
            "❌ Пожалуйста, выбери вариант кнопкой.",
            reply_markup=condition_keyboard,
        )
        return

    await state.update_data(condition=condition)
    await state.set_state(SearchForm.requirements)

    await message.answer(
        "📝 <b>Есть дополнительные требования?</b>\n\n"
        "Например:\n"
        "• только с гарантией\n"
        "• беспроводная мышь\n"
        "• продавец от 4.8 ⭐\n"
        "• только официальная версия\n\n"
        "Если требований нет — напиши <b>нет</b>.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================
# ПОИСК ТОВАРОВ
# =========================

@dp.message(SearchForm.requirements)
async def process_requirements(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(
            "❌ Напиши требования текстом или напиши «нет»."
        )
        return

    requirements = message.text.strip()

    if requirements.lower() in ["нет", "нету", "-", "no"]:
        requirements = None

    await state.update_data(requirements=requirements)

    data = await state.get_data()

    # ---------------------------------
    # ПОКАЗЫВАЕМ, ЧТО НАЧАЛСЯ ПОИСК
    # ---------------------------------

    await message.answer(
        "🔎 <b>Ищу подходящие предложения...</b>\n\n"
        "⏳ Проверяю товары по твоим параметрам."
        ,
        parse_mode="HTML",
    )

    # ---------------------------------
    # ЗАПУСК ПОИСКОВОГО ДВИЖКА
    # ---------------------------------

    try:
        results = search_products(
            product_query=data["product"],
            min_price=data["min_price"],
            max_price=data["max_price"],
            currency=data["currency"],
            country=data["country"],
            condition=data["condition"],
            requirements=data["requirements"],
        )

    except Exception as error:
        print(f"Ошибка поиска: {error}")

        await message.answer(
            "❌ <b>Произошла ошибка при поиске.</b>\n\n"
            "Попробуй выполнить поиск ещё раз.",
            parse_mode="HTML",
            reply_markup=main_keyboard,
        )

        await state.clear()
        return

    # ---------------------------------
    # ЕСЛИ НИЧЕГО НЕ НАЙДЕНО
    # ---------------------------------

    if not results:
        await message.answer(
            "😔 <b>Ничего не найдено.</b>\n\n"
            "Попробуй:\n"
            "• увеличить диапазон цены;\n"
            "• изменить состояние товара;\n"
            "• написать более короткий запрос.",
            parse_mode="HTML",
            reply_markup=main_keyboard,
        )

        await state.clear()
        return

    # ---------------------------------
    # ОГРАНИЧИВАЕМ РЕЗУЛЬТАТЫ
    # ---------------------------------

    displayed_results = results[:5]

    symbol = currency_symbol(data["currency"])

    await message.answer(
        f"🔎 <b>Найдено предложений: {len(results)}</b>\n\n"
        f"Показываю лучшие {len(displayed_results)}:",
        parse_mode="HTML",
    )

    # ---------------------------------
    # ВЫВОД ТОВАРОВ
    # ---------------------------------

    for index, product in enumerate(displayed_results, start=1):

        title = html.escape(str(product.get("title", "Без названия")))
        store = html.escape(str(product.get("store", "Неизвестный магазин")))

        rating = product.get("rating")
        reviews = product.get("reviews")

        rating_text = (
            f"{rating}/5"
            if rating is not None
            else "Нет доступа к информации"
)

        reviews_text = (
            f"{reviews:,}"
            if reviews is not None
            else "Нет доступа к информации"
)

        price = product.get("price", 0)

        match_score = product.get("match_score", 0)
        deal_score = product.get("deal_score", 0)

        condition = product.get("condition", "any")

        condition_text = condition_name(condition)

        text = (
            f"{'🥇' if index == 1 else '🥈' if index == 2 else '🥉' if index == 3 else '🔹'} "
            f"<b>{index}. {title}</b>\n\n"
            f"💰 Цена: <b>{format_price(price)} {symbol}</b>\n"
            f"🏪 Магазин: <b>{store}</b>\n"
            f"⭐ Рейтинг продавца: <b>{rating_text}</b>\n"
            f"👥 Отзывов: <b>{reviews_text}</b>\n"
            f"📦 Состояние: <b>{condition_text}</b>\n"
            f"🎯 Совпадение: <b>{match_score}</b>\n"
            f"🔥 Deal Score: <b>{deal_score}/100</b>"
        )

        keyboard = create_product_keyboard(
            product.get("url", "")
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    # ---------------------------------
    # ЗАВЕРШЕНИЕ
    # ---------------------------------

    await message.answer(
        "✅ <b>Поиск завершён.</b>\n\n"
        "Можешь выполнить новый поиск или выбрать "
        "другой раздел Dealvoro.",
        parse_mode="HTML",
        reply_markup=main_keyboard,
    )

    await state.clear()


# =========================
# МОИ ПОИСКИ
# =========================

@dp.message(F.text == "📋 Мои поиски")
async def my_searches(message: Message):
    await message.answer(
        "📋 <b>Мои поиски</b>\n\n"
        "Здесь будут сохранённые поиски.\n\n"
        "Эта функция будет подключена следующим этапом.",
        parse_mode="HTML",
    )


# =========================
# ОТСЛЕЖИВАНИЕ ЦЕН
# =========================

@dp.message(F.text == "🔔 Отслеживание цен")
async def price_tracking(message: Message):
    await message.answer(
        "🔔 <b>Отслеживание цен</b>\n\n"
        "Позже ты сможешь указать товар и желаемую цену.\n\n"
        "Dealvoro сообщит тебе, когда цена станет подходящей.",
        parse_mode="HTML",
    )


# =========================
# ИЗБРАННОЕ
# =========================

@dp.message(F.text == "⭐ Избранное")
async def favorites(message: Message):
    await message.answer(
        "⭐ <b>Избранное</b>\n\n"
        "Здесь будут сохранённые товары.\n\n"
        "Функция будет подключена следующим этапом.",
        parse_mode="HTML",
    )


# =========================
# НАСТРОЙКИ
# =========================

@dp.message(F.text == "⚙️ Настройки")
async def settings(message: Message):
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь появятся настройки валюты, страны, "
        "уведомлений и другие параметры.",
        parse_mode="HTML",
    )


# =========================
# ЗАПУСК
# =========================

async def main():
    print("Dealvoro запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())