import asyncio
import html
import json
import os

from services.database import (
    init_db,
    get_settings,
    set_setting,
    reset_settings,
    save_search_history,
    get_search_history,
    get_search_history_item,
    add_favorite,
    remove_favorite,
    get_favorites,
    is_favorite,
    save_favorite_candidate,
    get_favorite_candidate,
)

from services.ai_parser import (
    analyze_search_request,
    check_query_allowed,
)

from services.search import search_products

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
    CallbackQuery,
)

from dotenv import load_dotenv


# =========================================
# ENV
# =========================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN не найден в .env"
    )


# =========================================
# BOT
# =========================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()


# =========================================
# СОСТОЯНИЯ ПОИСКА
# =========================================

class SearchForm(StatesGroup):
    product = State()
    min_price = State()
    max_price = State()
    currency = State()
    country = State()
    condition = State()
    requirements = State()

# =========================================
# ГЛАВНОЕ МЕНЮ
# =========================================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="🛒 Найти товар"
            ),
            KeyboardButton(
                text="📋 Мои поиски"
            ),
        ],
        [
            KeyboardButton(
                text="🔔 Отслеживание цен"
            ),
            KeyboardButton(
                text="⭐ Избранное"
            ),
        ],
        [
            KeyboardButton(
                text="⚙️ Настройки"
            ),
        ],
    ],
    resize_keyboard=True,
)


# =========================================
# КЛАВИАТУРЫ
# =========================================

currency_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="₴ UAH"
            ),
            KeyboardButton(
                text="$ USD"
            ),
        ],
        [
            KeyboardButton(
                text="€ EUR"
            ),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


condition_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="🆕 Новый"
            ),
            KeyboardButton(
                text="♻️ Б/у"
            ),
        ],
        [
            KeyboardButton(
                text="📦 Любое"
            ),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


country_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="🇺🇦 Украина"
            ),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


# =========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================

def condition_name(
    condition: str
) -> str:
    names = {
        "new": "Новый",
        "used": "Б/у",
        "any": "Любое",
    }

    return names.get(
        condition,
        "Не указано",
    )


def currency_symbol(
    currency: str
) -> str:
    symbols = {
        "UAH": "₴",
        "USD": "$",
        "EUR": "€",
    }

    return symbols.get(
        currency,
        currency,
    )


def clean_url(
    url: str
) -> str:
    """
    Убирает случайный Markdown-формат
    из URL.
    """

    if not url:
        return ""

    url = str(
        url
    ).strip()

    if (
        url.startswith("[")
        and "](" in url
        and url.endswith(")")
    ):
        url = url.split(
            "](",
            1,
        )[1][:-1]

    return url


def format_price(
    price: float
) -> str:
    """
    3499 -> 3 499
    24999.50 -> 24 999.50
    """

    try:
        price = float(price)
    except (
        TypeError,
        ValueError,
    ):
        return "0"

    if price.is_integer():
        return f"{int(price):,}".replace(
            ",",
            " ",
        )

    return f"{price:,.2f}".replace(
        ",",
        " ",
    )


def create_product_keyboard(
    candidate_id: int,
    url: str,
    favorite: bool = False,
):
    """
    Кнопки товара.

    candidate_id — ID кандидата товара
    в SQLite.
    """

    url = clean_url(
        url
    )

    rows = []

    if url:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🛒 Открыть товар",
                    url=url,
                )
            ]
        )

    if favorite:
        rows.append(
            [
                InlineKeyboardButton(
                    text="★ Удалить из избранного",
                    callback_data=(
                        f"fav:remove:{candidate_id}"
                    ),
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⭐ В избранное",
                    callback_data=(
                        f"fav:add:{candidate_id}"
                    ),
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def settings_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💵 Валюта",
                    callback_data="settings:currency",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Состояние",
                    callback_data="settings:condition",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇺🇦 Страна",
                    callback_data="settings:country",
                )
            ],
            [
                InlineKeyboardButton(
                    text="♻️ Сбросить настройки",
                    callback_data="settings:reset",
                )
            ],
        ]
    )


def settings_text(
    user_id: int
) -> str:
    data = get_settings(
        user_id
    )

    currency = data.get(
        "currency",
        "UAH",
    )

    country = data.get(
        "country",
        "UA",
    )

    condition = data.get(
        "condition",
        "new",
    )

    country_text = {
        "UA": "🇺🇦 Украина",
    }.get(
        country,
        country,
    )

    return (
        "⚙️ <b>Настройки Dealvoro</b>\n\n"
        f"💵 Валюта: <b>{currency}</b>\n"
        f"🌍 Страна: <b>{country_text}</b>\n"
        f"📦 Состояние: <b>{condition_name(condition)}</b>"
    )


# =========================================
# START
# =========================================

@dp.message(
    CommandStart()
)
async def start(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    init_db()

    await message.answer(
        "👋 Добро пожаловать в Dealvoro!\n\n"
        "🛒 Я помогу найти выгодные предложения "
        "на украинских маркетплейсах и магазинах.\n\n"
        "Выбери действие:",
        reply_markup=main_keyboard,
    )


# =========================================
# НАЧАЛО ПОИСКА
# =========================================

@dp.message(
    F.text == "🛒 Найти товар"
)
async def find_product(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    # Получаем сохранённые настройки пользователя
    settings = get_settings(
        message.from_user.id
    )

    await state.update_data(
        currency=settings.get(
            "currency",
            "UAH",
        ),
        country=settings.get(
            "country",
            "UA",
        ),
        condition=settings.get(
            "condition",
            "new",
        ),
    )

    await state.set_state(
        SearchForm.product
    )

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


# =========================================
# ТОВАР
# =========================================

@dp.message(
    SearchForm.product
)
async def process_product(
    message: Message,
    state: FSMContext,
):
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

    allowed = check_query_allowed(
        product
    )

    if not allowed:
        await message.answer(
            "❌ <b>Некорректный запрос.</b>\n\n"
            "Этот тип запросов не поддерживается Dealvoro.",
            parse_mode="HTML",
        )

        await state.clear()
        return

    await state.update_data(
        product=product
    )

    await state.set_state(
        SearchForm.min_price
    )

    await message.answer(
        "💰 <b>Минимальная цена</b>\n\n"
        "Напиши минимальную цену.\n"
        "Если минимальной цены нет — напиши <b>0</b>.",
        parse_mode="HTML",
    )


# =========================================
# МИНИМАЛЬНАЯ ЦЕНА
# =========================================

@dp.message(
    SearchForm.min_price
)
async def process_min_price(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Введи цену числом."
        )
        return

    text = (
        message.text
        .strip()
        .replace(",", ".")
        .replace(" ", "")
    )

    try:
        min_price = float(
            text
        )

        if min_price < 0:
            raise ValueError

    except ValueError:
        await message.answer(
            "❌ Введи цену числом.\n\n"
            "Например: <code>500</code>",
            parse_mode="HTML",
        )
        return

    await state.update_data(
        min_price=min_price
    )

    await state.set_state(
        SearchForm.max_price
    )

    await message.answer(
        "💰 <b>Максимальная цена</b>\n\n"
        "Напиши максимальную цену.",
        parse_mode="HTML",
    )


# =========================================
# МАКСИМАЛЬНАЯ ЦЕНА
# =========================================

@dp.message(
    SearchForm.max_price
)
async def process_max_price(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Введи цену числом."
        )
        return

    text = (
        message.text
        .strip()
        .replace(",", ".")
        .replace(" ", "")
    )

    try:
        max_price = float(
            text
        )

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

    await state.update_data(
        max_price=max_price
    )

    await state.set_state(
        SearchForm.requirements
    )

    await message.answer(
        "📝 <b>Есть дополнительные требования?</b>\n\n"
        "Например:\n"
        "• только с гарантией\n"
        "• беспроводная мышь\n"
        "• продавец от 4.8 ⭐\n"
        "• только оригинал\n\n"
        "Если требований нет — напиши <b>нет</b>.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
)


# =========================================
# ВАЛЮТА
# =========================================

@dp.message(
    SearchForm.currency
)
async def process_currency(
    message: Message,
    state: FSMContext,
):
    currency_map = {
        "₴ UAH": "UAH",
        "$ USD": "USD",
        "€ EUR": "EUR",
    }

    currency = currency_map.get(
        message.text
    )

    if not currency:
        await message.answer(
            "❌ Пожалуйста, выбери валюту кнопкой.",
            reply_markup=currency_keyboard,
        )
        return

    await state.update_data(
        currency=currency
    )

    await state.set_state(
        SearchForm.country
    )

    await message.answer(
        "🇺🇦 <b>Выбери страну поиска</b>",
        parse_mode="HTML",
        reply_markup=country_keyboard,
    )


# =========================================
# СТРАНА
# =========================================

@dp.message(
    SearchForm.country
)
async def process_country(
    message: Message,
    state: FSMContext,
):
    if message.text != "🇺🇦 Украина":
        await message.answer(
            "❌ Пожалуйста, выбери страну кнопкой.",
            reply_markup=country_keyboard,
        )
        return

    await state.update_data(
        country="UA"
    )

    await state.set_state(
        SearchForm.condition
    )

    await message.answer(
        "📦 <b>Какое состояние товара тебе нужно?</b>",
        parse_mode="HTML",
        reply_markup=condition_keyboard,
    )


# =========================================
# СОСТОЯНИЕ
# =========================================

@dp.message(
    SearchForm.condition
)
async def process_condition(
    message: Message,
    state: FSMContext,
):
    condition_map = {
        "🆕 Новый": "new",
        "♻️ Б/у": "used",
        "📦 Любое": "any",
    }

    condition = condition_map.get(
        message.text
    )

    if not condition:
        await message.answer(
            "❌ Пожалуйста, выбери вариант кнопкой.",
            reply_markup=condition_keyboard,
        )
        return

    await state.update_data(
        condition=condition
    )

    await state.set_state(
        SearchForm.requirements
    )

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


# =========================================
# ПОИСК
# =========================================

@dp.message(
    SearchForm.requirements
)
async def process_requirements(
    message: Message,
    state: FSMContext,
):
    if not message.text:
        await message.answer(
            "❌ Напиши требования текстом или напиши «нет»."
        )
        return

    requirements = message.text.strip()

    if requirements.lower() in {
        "нет",
        "нету",
        "-",
        "no",
    }:
        requirements = None

    data = await state.get_data()

    settings = get_settings(
        message.from_user.id
)

    data["currency"] = settings.get(
        "currency",
        "UAH",
    )

    data["country"] = settings.get(
        "country",
        "UA",
    )

    data["condition"] = settings.get(
        "condition",
        "new",
    )

    await message.answer(
        "🧠 <b>Анализирую запрос...</b>",
        parse_mode="HTML",
    )

    try:
        ai_result = analyze_search_request(
            product=data["product"],
            requirements=requirements,
        )

    except Exception as error:

        print(
            f"Ошибка AI-анализа: {error}"
        )

        await message.answer(
            "❌ <b>Не удалось проанализировать запрос.</b>\n\n"
            "Попробуй ещё раз.",
            parse_mode="HTML",
            reply_markup=main_keyboard,
        )

        await state.clear()
        return

    product_query = ai_result.get(
        "product_query",
        data["product"],
    )

    search_terms = ai_result.get(
        "search_terms",
        [product_query],
    )

    must_groups = ai_result.get(
        "must_groups",
        [[product_query]],
    )

    requirements_result = ai_result.get(
        "requirements",
        requirements,
    )

    requirement_terms = ai_result.get(
        "requirement_terms",
        [requirements]
        if requirements
        else [],
    )

    exclude_terms = ai_result.get(
        "exclude_terms",
        [],
    )

    await state.update_data(
        product=product_query,
        requirements=requirements_result,
    )

    data = await state.get_data()

    await message.answer(
        "🔎 <b>Ищу подходящие предложения...</b>\n\n"
        "⏳ Проверяю товары по твоим параметрам.",
        parse_mode="HTML",
    )

    try:

        results = await asyncio.to_thread(
            search_products,
            product_query=product_query,
            min_price=data["min_price"],
            max_price=data["max_price"],
            currency=data["currency"],
            country=data["country"],
            condition=data["condition"],
            requirements=requirements_result,
            search_terms=search_terms,
            must_groups=must_groups,
            requirement_terms=requirement_terms,
            exclude_terms=exclude_terms,
        )

    except Exception as error:

        print(
            f"Ошибка поиска: {error}"
        )

        await message.answer(
            "❌ <b>Произошла ошибка при поиске.</b>\n\n"
            "Попробуй выполнить поиск ещё раз.",
            parse_mode="HTML",
            reply_markup=main_keyboard,
        )

        await state.clear()
        return

    # =====================================
    # СОХРАНЯЕМ ИСТОРИЮ
    # =====================================

    try:

        save_search_history(
            user_id=message.from_user.id,
            product=product_query,
            requirements=requirements_result,
            min_price=data["min_price"],
            max_price=data["max_price"],
            currency=data["currency"],
            country=data["country"],
            condition=data["condition"],
            ai_data=ai_result,
        )

    except Exception as error:

        print(
            f"Ошибка сохранения истории: {error}"
        )

    # =====================================
    # НИЧЕГО НЕ НАЙДЕНО
    # =====================================

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

    # =====================================
    # ТОП-5
    # =====================================

    displayed_results = results[:5]

    symbol = currency_symbol(
        data["currency"]
    )

    await message.answer(
        f"🔎 <b>Найдено предложений: {len(results)}</b>\n\n"
        f"Показываю лучшие {len(displayed_results)}:",
        parse_mode="HTML",
    )

    # =====================================
    # ТОВАРЫ
    # =====================================

    for index, product in enumerate(
        displayed_results,
        start=1,
    ):

        title = html.escape(
            str(
                product.get(
                    "title",
                    "Без названия",
                )
            )
        )

        store = html.escape(
            str(
                product.get(
                    "store",
                    "Неизвестный магазин",
                )
            )
        )

        rating = product.get(
            "rating"
        )

        reviews = product.get(
            "reviews"
        )

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

        price = product.get(
            "price",
            0,
        )

        match_score = product.get(
            "match_score",
            0,
        )

        deal_score = product.get(
            "deal_score",
            0,
        )

        product_condition = product.get(
            "condition",
            "new",
        )

        condition_text = condition_name(
            product_condition
        )

        if index == 1:
            icon = "🥇"
        elif index == 2:
            icon = "🥈"
        elif index == 3:
            icon = "🥉"
        else:
            icon = "🔹"

        text = (
            f"{icon} <b>{index}. {title}</b>\n\n"
            f"💰 Цена: <b>{format_price(price)} {symbol}</b>\n"
            f"🏪 Магазин: <b>{store}</b>\n"
            f"⭐ Рейтинг продавца: <b>{rating_text}</b>\n"
            f"👥 Отзывов: <b>{reviews_text}</b>\n"
            f"📦 Состояние: <b>{condition_text}</b>\n"
            f"🎯 Совпадение: <b>{match_score}</b>\n"
            f"🔥 Deal Score: <b>{deal_score}/100</b>"
        )

        product_url = clean_url(
            product.get(
                "url",
                "",
            )
        )

        try:

            candidate_id = save_favorite_candidate(
                message.from_user.id,
                product,
            )

            favorite = is_favorite(
                message.from_user.id,
                product_url,
            )

            keyboard = create_product_keyboard(
                candidate_id,
                product_url,
                favorite,
            )

        except Exception as error:

            print(
                f"Ошибка подготовки избранного: {error}"
            )

            keyboard = None

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    await message.answer(
        "✅ <b>Поиск завершён.</b>\n\n"
        "Можешь выполнить новый поиск или выбрать "
        "другой раздел Dealvoro.",
        parse_mode="HTML",
        reply_markup=main_keyboard,
    )

    await state.clear()


# =========================================
# ИЗБРАННОЕ — ДОБАВЛЕНИЕ
# =========================================

@dp.callback_query(
    F.data.startswith(
        "fav:add:"
    )
)
async def favorite_add(
    callback: CallbackQuery,
):
    try:

        candidate_id = int(
            callback.data.split(
                ":"
            )[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            "❌ Ошибка.",
            show_alert=True,
        )
        return

    product = get_favorite_candidate(
        callback.from_user.id,
        candidate_id,
    )

    if not product:

        await callback.answer(
            "❌ Товар больше недоступен.",
            show_alert=True,
        )
        return

    try:

        add_favorite(
            callback.from_user.id,
            product,
        )

        await callback.answer(
            "⭐ Добавлено в избранное!"
        )

        keyboard = create_product_keyboard(
            candidate_id,
            product.get(
                "url",
                "",
            ),
            True,
        )

        await callback.message.edit_reply_markup(
            reply_markup=keyboard
        )

    except Exception as error:

        print(
            f"Ошибка добавления в избранное: {error}"
        )

        await callback.answer(
            "❌ Не удалось добавить товар.",
            show_alert=True,
        )


# =========================================
# ИЗБРАННОЕ — УДАЛЕНИЕ
# =========================================

@dp.callback_query(
    F.data.startswith(
        "fav:remove:"
    )
)
async def favorite_remove_from_card(
    callback: CallbackQuery,
):
    try:

        candidate_id = int(
            callback.data.split(
                ":"
            )[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            "❌ Ошибка.",
            show_alert=True,
        )
        return

    product = get_favorite_candidate(
        callback.from_user.id,
        candidate_id,
    )

    if not product:

        await callback.answer(
            "❌ Товар больше недоступен.",
            show_alert=True,
        )
        return

    deleted = remove_favorite(
        callback.from_user.id,
        url=product.get(
            "url",
            "",
        ),
    )

    if deleted:

        await callback.answer(
            "🗑 Удалено из избранного."
        )

        keyboard = create_product_keyboard(
            candidate_id,
            product.get(
                "url",
                "",
            ),
            False,
        )

        await callback.message.edit_reply_markup(
            reply_markup=keyboard
        )

    else:

        await callback.answer(
            "Товар уже не находится в избранном."
        )


# =========================================
# МОИ ПОИСКИ
# =========================================

@dp.message(
    F.text == "📋 Мои поиски"
)
async def my_searches(
    message: Message,
):
    history = get_search_history(
        message.from_user.id,
        limit=10,
    )

    if not history:

        await message.answer(
            "📋 <b>Мои поиски</b>\n\n"
            "История пока пустая.",
            parse_mode="HTML",
        )

        return

    await message.answer(
        "📋 <b>Последние поиски</b>",
        parse_mode="HTML",
    )

    for item in history:

        requirements = (
            item.get(
                "requirements"
            )
            or "без требований"
        )

        min_price = item.get(
            "min_price",
            0,
        )

        max_price = item.get(
            "max_price"
        )

        currency = item.get(
            "currency",
            "UAH",
        )

        if max_price is not None:
            price_text = (
                f"{format_price(min_price)} — "
                f"{format_price(max_price)} "
                f"{currency}"
            )
        else:
            price_text = (
                f"от {format_price(min_price)} "
                f"{currency}"
            )

        product_text = html.escape(
            str(
                item.get(
                    "product",
                    "Поиск",
                )
            )
        )

        requirements_text = html.escape(
            str(requirements)
        )

        text = (
            f"🔎 <b>{product_text}</b>\n"
            f"💰 {price_text}\n"
            f"📝 {requirements_text}\n"
            f"📦 {condition_name(item.get('condition', 'any'))}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔄 Повторить поиск",
                        callback_data=(
                            f"hist:run:{item['id']}"
                        ),
                    )
                ]
            ]
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )


# =========================================
# ПОВТОР ПОИСКА
# =========================================

@dp.callback_query(
    F.data.startswith(
        "hist:run:"
    )
)
async def repeat_search(
    callback: CallbackQuery,
):
    try:

        history_id = int(
            callback.data.split(
                ":"
            )[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            "❌ Ошибка.",
            show_alert=True,
        )
        return

    item = get_search_history_item(
        history_id,
        callback.from_user.id,
    )

    if not item:

        await callback.answer(
            "❌ Поиск не найден.",
            show_alert=True,
        )
        return

    try:

        if item.get(
            "ai_data"
        ):

            ai_data = json.loads(
                item["ai_data"]
            )

        else:

            ai_data = await asyncio.to_thread(
                analyze_search_request,
                item["product"],
                item.get("requirements"),
            )

        await callback.message.answer(
            "🔎 <b>Повторяю поиск...</b>",
            parse_mode="HTML",
        )

        results = await asyncio.to_thread(
            search_products,
            product_query=ai_data.get(
                "product_query",
                item["product"],
            ),
            min_price=item["min_price"],
            max_price=item["max_price"],
            currency=item["currency"],
            country=item["country"],
            condition=item["condition"],
            requirements=item.get(
                "requirements"
            ),
            search_terms=ai_data.get(
                "search_terms",
                [item["product"]],
            ),
            must_groups=ai_data.get(
                "must_groups",
                [[item["product"]]],
            ),
            requirement_terms=ai_data.get(
                "requirement_terms",
                [],
            ),
            exclude_terms=ai_data.get(
                "exclude_terms",
                [],
            ),
        )

    except Exception as error:

        print(
            f"Ошибка повторного поиска: {error}"
        )

        await callback.message.answer(
            "❌ Не удалось повторить поиск."
        )

        await callback.answer()

        return

    if not results:

        await callback.message.answer(
            "😔 По этим параметрам сейчас ничего не найдено."
        )

        await callback.answer()

        return

    symbol = currency_symbol(
        item["currency"]
    )

    await callback.message.answer(
        f"🔎 <b>Найдено: {len(results)}</b>\n\n"
        f"Показываю лучшие {min(5, len(results))}:",
        parse_mode="HTML",
    )

    for index, product in enumerate(
        results[:5],
        start=1,
    ):

        title = html.escape(
            str(
                product.get(
                    "title",
                    "Без названия",
                )
            )
        )

        store = html.escape(
            str(
                product.get(
                    "store",
                    "Неизвестный магазин",
                )
            )
        )

        price = product.get(
            "price",
            0,
        )

        url = clean_url(
            product.get(
                "url",
                "",
            )
        )

        candidate_id = save_favorite_candidate(
            callback.from_user.id,
            product,
        )

        favorite = is_favorite(
            callback.from_user.id,
            url,
        )

        keyboard = create_product_keyboard(
            candidate_id,
            url,
            favorite,
        )

        text = (
            f"🔹 <b>{index}. {title}</b>\n\n"
            f"💰 Цена: <b>{format_price(price)} {symbol}</b>\n"
            f"🏪 Магазин: <b>{store}</b>"
        )

        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    await callback.answer()


# =========================================
# ИЗБРАННОЕ
# =========================================

@dp.message(
    F.text == "⭐ Избранное"
)
async def favorites(
    message: Message,
):
    items = get_favorites(
        message.from_user.id,
        limit=50,
    )

    if not items:

        await message.answer(
            "⭐ <b>Избранное</b>\n\n"
            "Ты ещё не добавил ни одного товара.",
            parse_mode="HTML",
        )

        return

    await message.answer(
        f"⭐ <b>Избранное</b>\n\n"
        f"Сохранено товаров: <b>{len(items)}</b>",
        parse_mode="HTML",
    )

    for item in items:

        title = html.escape(
            str(
                item.get(
                    "title",
                    "Без названия",
                )
            )
        )

        store = html.escape(
            str(
                item.get(
                    "store",
                    "",
                )
            )
        )

        price = item.get(
            "price",
            0,
        )

        currency = item.get(
            "currency",
            "UAH",
        )

        url = clean_url(
            item.get(
                "url",
                "",
            )
        )

        text = (
            f"⭐ <b>{title}</b>\n\n"
            f"💰 {format_price(price)} {currency}\n"
            f"🏪 {store}"
        )

        rows = []

        if url:

            rows.append(
                [
                    InlineKeyboardButton(
                        text="🛒 Открыть товар",
                        url=url,
                    )
                ]
            )

        rows.append(
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=(
                        f"favorite:remove:{item['id']}"
                    ),
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=rows
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )


# =========================================
# УДАЛЕНИЕ ИЗ ИЗБРАННОГО
# =========================================

@dp.callback_query(
    F.data.startswith(
        "favorite:remove:"
    )
)
async def favorite_remove(
    callback: CallbackQuery,
):
    try:

        favorite_id = int(
            callback.data.split(
                ":"
            )[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            "❌ Ошибка.",
            show_alert=True,
        )

        return

    deleted = remove_favorite(
        callback.from_user.id,
        favorite_id=favorite_id,
    )

    if deleted:

        await callback.answer(
            "🗑 Удалено из избранного."
        )

        try:
            await callback.message.delete()
        except Exception:
            pass

    else:

        await callback.answer(
            "❌ Товар уже удалён."
        )


# =========================================
# НАСТРОЙКИ
# =========================================

@dp.message(
    F.text == "⚙️ Настройки"
)
async def settings(
    message: Message,
):
    await message.answer(
        settings_text(
            message.from_user.id
        ),
        parse_mode="HTML",
        reply_markup=settings_keyboard(),
    )


# =========================================
# ВЫБОР ВАЛЮТЫ
# =========================================

@dp.callback_query(
    F.data == "settings:currency"
)
async def settings_currency(
    callback: CallbackQuery,
):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="₴ UAH",
                    callback_data="set:currency:UAH",
                ),
                InlineKeyboardButton(
                    text="$ USD",
                    callback_data="set:currency:USD",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="€ EUR",
                    callback_data="set:currency:EUR",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="settings:back",
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        settings_text(
            callback.from_user.id
        ),
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    await callback.answer()


# =========================================
# ВЫБОР СОСТОЯНИЯ
# =========================================

@dp.callback_query(
    F.data == "settings:condition"
)
async def settings_condition(
    callback: CallbackQuery,
):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆕 Новый",
                    callback_data="set:condition:new",
                ),
                InlineKeyboardButton(
                    text="♻️ Б/у",
                    callback_data="set:condition:used",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📦 Любое",
                    callback_data="set:condition:any",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="settings:back",
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        settings_text(
            callback.from_user.id
        ),
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    await callback.answer()


# =========================================
# СТРАНА
# =========================================

@dp.callback_query(
    F.data == "settings:country"
)
async def settings_country(
    callback: CallbackQuery,
):
    set_setting(
        callback.from_user.id,
        "country",
        "UA",
    )

    await callback.message.edit_text(
        settings_text(
            callback.from_user.id
        ),
        parse_mode="HTML",
        reply_markup=settings_keyboard(),
    )

    await callback.answer(
        "🇺🇦 Страна: Украина"
    )


# =========================================
# ИЗМЕНЕНИЕ ВАЛЮТЫ
# =========================================

@dp.callback_query(
    F.data.startswith(
        "set:currency:"
    )
)
async def set_currency(
    callback: CallbackQuery,
):
    currency = callback.data.split(
        ":"
    )[-1]

    if currency not in {
        "UAH",
        "USD",
        "EUR",
    }:

        await callback.answer(
            "❌ Недопустимая валюта.",
            show_alert=True,
        )

        return

    set_setting(
        callback.from_user.id,
        "currency",
        currency,
    )

    await callback.message.edit_text(
        settings_text(
            callback.from_user.id
        ),
        parse_mode="HTML",
        reply_markup=settings_keyboard(),
    )

    await callback.answer(
        f"✅ Валюта: {currency}"
    )


# =========================================
# ИЗМЕНЕНИЕ СОСТОЯНИЯ
# =========================================

@dp.callback_query(
    F.data.startswith(
        "set:condition:"
    )
)
async def set_condition(
    callback: CallbackQuery,
):
    condition = callback.data.split(
        ":"
    )[-1]

    if condition not in {
        "new",
        "used",
        "any",
    }:

        await callback.answer(
            "❌ Недопустимое состояние.",
            show_alert=True,
        )

        return

    set_setting(
        callback.from_user.id,
        "condition",
        condition,
    )

    await callback.message.edit_text(
        settings_text(
            callback.from_user.id
        ),
        parse_mode="HTML",
        reply_markup=settings_keyboard(),
    )

    await callback.answer(
        "✅ Состояние сохранено."
    )


# =========================================
# СБРОС НАСТРОЕК
# =========================================

@dp.callback_query(
    F.data == "settings:reset"
)
async def settings_reset(
    callback: CallbackQuery,
):
    reset_settings(
        callback.from_user.id
    )

    await callback.message.edit_text(
        settings_text(
            callback.from_user.id
        ),
        parse_mode="HTML",
        reply_markup=settings_keyboard(),
    )

    await callback.answer(
        "♻️ Настройки сброшены."
    )


# =========================================
# НАЗАД
# =========================================

@dp.callback_query(
    F.data == "settings:back"
)
async def settings_back(
    callback: CallbackQuery,
):
    await callback.message.edit_text(
        settings_text(
            callback.from_user.id
        ),
        parse_mode="HTML",
        reply_markup=settings_keyboard(),
    )

    await callback.answer()


# =========================================
# ОТСЛЕЖИВАНИЕ ЦЕН
# =========================================

@dp.message(
    F.text == "🔔 Отслеживание цен"
)
async def price_tracking(
    message: Message,
):
    await message.answer(
        "🔔 <b>Отслеживание цен</b>\n\n"
        "Функция будет подключена следующим этапом.",
        parse_mode="HTML",
    )


# =========================================
# ЗАПУСК
# =========================================

async def main():
    init_db()

    print(
        "Dealvoro запущен!"
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":
    asyncio.run(main())