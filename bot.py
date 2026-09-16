import asyncio
import html
import json
import os
from datetime import datetime, timezone

from database import (
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
    get_subscription,
    count_favorites,
    count_search_history,
    get_user_language,
    set_user_language,
    get_tracker_notification_info,

    # Отслеживание — из database
    count_active_trackers,
    can_add_tracker,
    add_price_tracker,
    get_price_tracker,
    get_price_trackers,
    get_all_active_price_trackers,
    remove_price_tracker,
    update_price_tracker,
    get_price_history,
    cleanup_price_history,
)

from services.subscriptions import (
    SUBSCRIPTION_PLANS,
    get_active_plan,
    has_plan,
    activate_subscription,
    get_subscription_info,

    # Лимиты — из subscriptions
    get_usage_info,
    can_search,
    consume_search,
    get_tracker_limit,
    get_price_history_days,
    get_price_drop_threshold,
)

from services.i18n import (
    t,
    get_lang_name,
    SUPPORTED_LANGS,
    DEFAULT_LANG,
)

from services.ai_parser import (
    analyze_search_request,
    check_query_allowed,
)

from services.search import search_products

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command
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
    LabeledPrice,
    PreCheckoutQuery,
    SuccessfulPayment,
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
# АДМИНЫ
# =========================================

ADMIN_IDS = [
    1477455722,  # ← ЗАМЕНИ на свой Telegram user_id
]


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
# СОСТОЯНИЕ ОТСЛЕЖИВАНИЯ
# =========================================

class PriceTrackingForm(StatesGroup):
    target_price = State()


# =========================================
# ЯЗЫК ПОЛЬЗОВАТЕЛЯ
# =========================================

def lang_of(user_id: int) -> str:
    try:
        return get_user_language(user_id)
    except Exception:
        return DEFAULT_LANG

# =========================================
# ГЛАВНОЕ МЕНЮ
# =========================================

def main_keyboard(lang: str = DEFAULT_LANG) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("menu_find", lang)),
                KeyboardButton(text=t("menu_my_searches", lang)),
            ],
            [
                KeyboardButton(text=t("menu_tracking", lang)),
                KeyboardButton(text=t("menu_favorites", lang)),
            ],
            [
                KeyboardButton(text=t("menu_subscription", lang)),
                KeyboardButton(text=t("menu_settings", lang)),
            ],
        ],
        resize_keyboard=True,
    )


# =========================================
# КЛАВИАТУРЫ
# =========================================

def currency_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="₴ UAH"),
                KeyboardButton(text="$ USD"),
            ],
            [KeyboardButton(text="€ EUR")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def condition_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("condition_new", lang)),
                KeyboardButton(text=t("condition_used", lang)),
            ],
            [KeyboardButton(text=t("condition_any", lang))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def country_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("settings_country_name", lang))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# =========================================
# ПОДПИСКА
# =========================================

def subscription_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Pro — 100 Stars",
                    callback_data="subscription:pro",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👑 Ultra — 200 Stars",
                    callback_data="subscription:ultra",
                )
            ],
        ]
    )


def subscription_buy_keyboard(
    lang: str,
    plan: str,
    stars: int,
):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("subscription_btn_buy", lang, stars=stars),
                    callback_data=f"subscription:buy:{plan}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("subscription_btn_back", lang),
                    callback_data="subscription:back",
                )
            ],
        ]
    )


def subscription_active_keyboard(lang: str = DEFAULT_LANG):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Pro — 100 Stars",
                    callback_data="subscription:pro",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👑 Ultra — 200 Stars",
                    callback_data="subscription:ultra",
                )
            ],
        ]
    )

def format_subscription_date(expires_at) -> str:

    if not expires_at:
        return ""

    try:
        value = str(expires_at)

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        date = datetime.fromisoformat(value)

        return date.strftime(
            "%d.%m.%Y %H:%M"
        )

    except (
        ValueError,
        TypeError,
    ):
        return str(expires_at).replace(
            "T",
            " ",
        )


def subscription_text(user_id: int) -> str:
    lang = lang_of(user_id)

    info = get_subscription_info(user_id)
    active_plan = info.get("plan", "free")
    plan_name = info.get("name", "🆓 Free")
    expires_at = info.get("expires_at")

    usage = get_usage_info(user_id)
    searches_used = usage.get("used", 0)
    searches_limit = usage.get("limit", 5)

    if active_plan == "ultra":
        period_label = t("subscription_period_day", lang)
    else:
        period_label = t("subscription_period_month", lang)

    trackers_used = count_active_trackers(user_id)
    trackers_limit = get_tracker_limit(user_id)

    favorites_used = count_favorites(user_id)
    favorites_limit = info.get("max_favorites")

    if favorites_limit is not None:
        favorites_text = t(
            "subscription_favorites",
            lang,
            used=favorites_used,
            limit=favorites_limit,
        )
    else:
        favorites_text = t(
            "subscription_favorites_unlimited",
            lang,
            used=favorites_used,
        )

    history_used = count_search_history(user_id)
    history_limit = info.get("max_history")

    if history_limit is not None:
        history_text = t(
            "subscription_history",
            lang,
            used=history_used,
            limit=history_limit,
        )
    else:
        history_text = t(
            "subscription_history_unlimited",
            lang,
            used=history_used,
        )

    if active_plan == "free":
        status_text = t("subscription_current_free", lang)
    else:
        if expires_at:
            status_text = t(
                "subscription_current_paid_until",
                lang,
                name=plan_name,
                date=format_subscription_date(expires_at),
            )
        else:
            status_text = t(
                "subscription_current_paid",
                lang,
                name=plan_name,
            )

    if trackers_limit > 0:
        trackers_text = t(
            "subscription_tracking",
            lang,
            used=trackers_used,
            limit=trackers_limit,
        )
    else:
        trackers_text = t("subscription_tracking_na", lang)

    searches_text = t(
        "subscription_searches",
        lang,
        period=period_label,
        used=searches_used,
        limit=searches_limit,
    )

    return (
        t("subscription_title", lang)
        + "\n\n"

        + status_text
        + "\n\n"

        + t("subscription_usage_title", lang)
        + "\n"
        + searches_text
        + "\n"
        + trackers_text
        + "\n"
        + favorites_text
        + "\n"
        + history_text
        + "\n\n"

        + "🆓 <b>Free</b>\n"
        + "• 5 / month\n"
        + "• 5 favorites\n"
        + "• 5 history\n\n"

        + "⭐ <b>Pro — 100 Stars / 30</b>\n"
        + "• 15 / month\n"
        + "• 50 favorites\n"
        + "• 50 history\n"
        + "• 3 trackers\n"
        + "• Price drop alerts\n"
        + "• Sharp drop (20%+)\n"
        + "• 30 days price history\n\n"

        + "👑 <b>Ultra — 200 Stars / 30</b>\n"
        + "• 15 / day\n"
        + "• ∞ favorites\n"
        + "• ∞ history\n"
        + "• 25 trackers\n"
        + "• Price drop alerts\n"
        + "• Sharp drop (20%+)\n"
        + "• 90 days price history\n\n"

        + t("subscription_choose", lang)
    )


# =========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================

def condition_name(condition: str, lang: str) -> str:
    if condition == "new":
        return t("condition_new", lang)
    if condition == "used":
        return t("condition_used", lang)
    if condition == "any":
        return t("condition_any", lang)
    return t("condition_unknown", lang)


def currency_symbol(currency: str) -> str:

    symbols = {
        "UAH": "₴",
        "USD": "$",
        "EUR": "€",
    }

    return symbols.get(
        currency,
        currency,
    )


def clean_url(url: str) -> str:

    if not url:
        return ""

    url = str(url).strip()

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


def format_price(price) -> str:

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


# =========================================
# КЛАВИАТУРА ТОВАРА
# =========================================

def create_product_keyboard(
    lang: str,
    candidate_id: int,
    url: str,
    favorite: bool = False,
):

    url = clean_url(url)

    rows = []

    if url:

        rows.append(
            [
                InlineKeyboardButton(
                     t("btn_open_product", lang),
                    url=url,
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                t("btn_track_price", lang),
                callback_data=(
                    f"track:add:{candidate_id}"
                ),
            )
        ]
    )

    if favorite:

        rows.append(
            [
                InlineKeyboardButton(
                    t("btn_remove_favorite", lang),
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
                    t("btn_add_favorite", lang),
                    callback_data=(
                        f"fav:add:{candidate_id}"
                    ),
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# =========================================
# КЛАВИАТУРА ТРЕКЕРОВ
# =========================================

def tracker_keyboard(
    lang: str,
    tracker_id: int,
):

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    t("tracker_btn_check", lang),
                    callback_data=(
                        f"track:check:{tracker_id}"
                    ),
                ),
                InlineKeyboardButton(
                    t("tracker_btn_history", lang),
                    callback_data=(
                        f"track:history:{tracker_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    t("tracker_btn_delete", lang),
                    callback_data=(
                        f"track:remove:{tracker_id}"
                    ),
                ),
            ],
        ]
    )


def tracker_text(
    tracker: dict,
    lang: str,
) -> str:

    title = html.escape(
        str(
            tracker.get(
                "title",
                t("product_untitled", lang),
            )
        )
    )

    store = html.escape(
        str(
            tracker.get(
                "store",
                t("product_unknown_store", lang),
            )
        )
    )

    currency = tracker.get(
        "currency",
        "UAH",
    )

    symbol = currency_symbol(
        currency
    )

    current_price = tracker.get(
        "current_price"
    )

    target_price = tracker.get(
        "target_price"
    )

    last_checked = tracker.get(
        "last_checked_at"
    )

    text = (
        f"🔔 <b>{title}</b>\n\n"
        + t("tracker_store", lang, store=store)
        + "\n"
    )

    if current_price is not None:

        text += (
            t(
                "tracker_current_price",
                lang,
                price=format_price(current_price),
                symbol=symbol,
            )
            + "\n"
        )

    else:

        text += (
            t("tracker_no_price", lang)
            + "\n"
        )

    if target_price is not None:

        text += (
            t(
                "tracker_target_price",
                lang,
                price=format_price(target_price),
                symbol=symbol,
            )
            + "\n"
        )

    if last_checked:

        text += (
            t(
                "tracker_last_check",
                lang,
                date=str(last_checked).replace("T", " ")[:19],
            )
            + "\n"
        )

    if (
        current_price is not None
        and target_price is not None
        and float(current_price) <= float(target_price)
    ):

        text += (
            "\n"
            + t("tracker_target_reached_badge", lang)
        )

    return text


# =========================================
# START
# =========================================

@dp.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext,
):

    await state.clear()

    init_db()

    get_subscription(
        message.from_user.id
    )

    lang = lang_of(message.from_user.id)

    await message.answer(
        t("start_welcome", lang),
        reply_markup=main_keyboard(lang),
    )


# =========================================
# НАЧАЛО ПОИСКА
# =========================================

@dp.message(
    F.text.in_(
        [
            t("menu_find", "en"),
            t("menu_find", "uk"),
        ]
    )
)
async def find_product(
    message: Message,
    state: FSMContext,
):

    user_id = message.from_user.id
    lang = lang_of(user_id)

    await state.clear()

    if not can_search(user_id):

        usage = get_usage_info(user_id)
        plan = get_active_plan(user_id)

        if plan == "ultra":
            key = "search_limit_reached_today"
        else:
            key = "search_limit_reached"

        await message.answer(
            t(
                key,
                lang,
                used=usage["used"],
                limit=usage["limit"],
            ),
            parse_mode="HTML",
            reply_markup=subscription_active_keyboard(lang),
        )

        return

    settings = get_settings(user_id)

    await state.update_data(
        currency=settings.get("currency", "UAH"),
        country=settings.get("country", "UA"),
        condition=settings.get("condition", "new"),
    )

    await state.set_state(SearchForm.product)

    await message.answer(
        t("search_what_to_find", lang),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================
# ТОВАР
# =========================================

@dp.message(SearchForm.product)
async def process_product(
    message: Message,
    state: FSMContext,
):

    user_id = message.from_user.id
    lang = lang_of(user_id)

    if not message.text:

        await message.answer(
            t("error_text_only", lang)
        )

        return

    product = message.text.strip()

    if len(product) < 2:

        await message.answer(
            t("error_product_too_short", lang)
        )

        return

    allowed = check_query_allowed(
        product
    )

    if not allowed:

        await message.answer(
            t("error_query_invalid", lang),
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
        t("search_min_price", lang),
        parse_mode="HTML",
    )


# =========================================
# МИНИМАЛЬНАЯ ЦЕНА
# =========================================

@dp.message(SearchForm.min_price)
async def process_min_price(
    message: Message,
    state: FSMContext,
):

    lang = lang_of(message.from_user.id)

    if not message.text:

        await message.answer(
            t("error_number_only", lang),
            parse_mode="HTML",
        )

        return

    text = (
        message.text
        .strip()
        .replace(",", ".")
        .replace(" ", "")
    )

    try:

        min_price = float(text)

        if min_price < 0:
            raise ValueError

    except ValueError:

        await message.answer(
            t("error_number_only", lang),
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
        t("search_max_price", lang),
        parse_mode="HTML",
    )


# =========================================
# МАКСИМАЛЬНАЯ ЦЕНА
# =========================================

@dp.message(SearchForm.max_price)
async def process_max_price(
    message: Message,
    state: FSMContext,
):

    lang = lang_of(message.from_user.id)

    if not message.text:

        await message.answer(
            t("error_number_only", lang),
            parse_mode="HTML",
        )

        return

    text = (
        message.text
        .strip()
        .replace(",", ".")
        .replace(" ", "")
    )

    try:

        max_price = float(text)

        if max_price < 0:
            raise ValueError

    except ValueError:

        await message.answer(
            t("error_number_only", lang),
            parse_mode="HTML",
        )

        return

    data = await state.get_data()

    if max_price < data["min_price"]:

        await message.answer(
            t("error_max_less_min", lang)
        )

        return

    await state.update_data(
        max_price=max_price
    )

    await state.set_state(
        SearchForm.requirements
    )

    await message.answer(
        t("search_requirements", lang),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================
# ВАЛЮТА
# =========================================

@dp.message(SearchForm.currency)
async def process_currency(
    message: Message,
    state: FSMContext,
):

    lang = lang_of(message.from_user.id)

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
            t("error_choose_button_currency", lang),
            reply_markup=currency_keyboard(),
        )

        return

    await state.update_data(
        currency=currency
    )

    await state.set_state(
        SearchForm.country
    )

    await message.answer(
        t("search_currency_prompt", lang),
        parse_mode="HTML",
        reply_markup=country_keyboard(lang),
    )

# =========================================
# СТРАНА
# =========================================

@dp.message(SearchForm.country)
async def process_country(
    message: Message,
    state: FSMContext,
):

    lang = lang_of(message.from_user.id)

    if message.text != t("settings_country_name", lang):

        await message.answer(
            t("error_choose_button_country", lang),
            reply_markup=country_keyboard(lang),
        )

        return

    await state.update_data(
        country="UA"
    )

    await state.set_state(
        SearchForm.condition
    )

    await message.answer(
        t("search_condition_prompt", lang),
        parse_mode="HTML",
        reply_markup=condition_keyboard(lang),
    )


# =========================================
# СОСТОЯНИЕ
# =========================================

@dp.message(SearchForm.condition)
async def process_condition(
    message: Message,
    state: FSMContext,
):

    lang = lang_of(message.from_user.id)

    condition_map = {
        t("condition_new", "en"): "new",
        t("condition_new", "uk"): "new",
        t("condition_used", "en"): "used",
        t("condition_used", "uk"): "used",
        t("condition_any", "en"): "any",
        t("condition_any", "uk"): "any",
    }

    condition = condition_map.get(
        message.text
    )

    if not condition:

        await message.answer(
            t("error_choose_button", lang),
            reply_markup=condition_keyboard(lang),
        )

        return

    await state.update_data(
        condition=condition
    )

    await state.set_state(
        SearchForm.requirements
    )

    await message.answer(
        t("search_requirements", lang),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


# =========================================
# ПОИСК
# =========================================

@dp.message(SearchForm.requirements)
async def process_requirements(
    message: Message,
    state: FSMContext,
):

    user_id = message.from_user.id
    lang = lang_of(user_id)

    if not message.text:

        await message.answer(
            t("error_text_only", lang)
        )

        return

    requirements = message.text.strip()

    if requirements.lower() in {
        "нет",
        "нету",
        "ні",
        "no",
        "-",
    }:

        requirements = None

    if not can_search(user_id):

        usage = get_usage_info(user_id)

        plan = get_active_plan(user_id)

        if plan == "ultra":
            key = "search_limit_reached_today"
        else:
            key = "search_limit_reached"

        await message.answer(
            t(
                key,
                lang,
                used=usage["used"],
                limit=usage["limit"],
            ),
            parse_mode="HTML",
            reply_markup=main_keyboard(lang),
        )

        await state.clear()

        return

    data = await state.get_data()

    settings = get_settings(user_id)

    data["currency"] = data.get(
        "currency",
        settings.get("currency", "UAH"),
    )

    data["country"] = data.get(
        "country",
        settings.get("country", "UA"),
    )

    data["condition"] = data.get(
        "condition",
        settings.get("condition", "new"),
    )

    await message.answer(
        t("search_analyzing", lang),
        parse_mode="HTML",
    )

    try:

        ai_result = await asyncio.to_thread(
            analyze_search_request,
            product=data["product"],
            requirements=requirements,
        )

    except Exception as error:

        print(
            f"Ошибка AI-анализа: {error}"
        )

        await message.answer(
            t("error_ai_failed", lang),
            parse_mode="HTML",
            reply_markup=main_keyboard(lang),
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

    audience = ai_result.get(
        "audience",
        "adult",
    )

    await message.answer(
        t("search_searching", lang),
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
            audience=audience,
        )

    except Exception as error:

        print(
            f"Ошибка поиска: {error}"
        )

        await message.answer(
            t("error_search_failed", lang),
            parse_mode="HTML",
            reply_markup=main_keyboard(lang),
        )

        await state.clear()

        return

    if not consume_search(user_id):

        await message.answer(
            t("search_limit_already_used", lang),
            reply_markup=main_keyboard(lang),
        )

        await state.clear()

        return

    try:

        save_search_history(
            user_id=user_id,
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

    if not results:

        usage = get_usage_info(user_id)

        await message.answer(
            t(
                "search_not_found",
                lang,
                remaining=usage["remaining"],
            ),
            parse_mode="HTML",
            reply_markup=main_keyboard(lang),
        )

        await state.clear()

        return

    displayed_results = results[:5]

    symbol = currency_symbol(
        data["currency"]
    )

    usage = get_usage_info(user_id)

    await message.answer(
        t(
            "search_found_count",
            lang,
            count=len(results),
            shown=len(displayed_results),
            remaining=usage["remaining"],
        ),
        parse_mode="HTML",
    )

    for index, product in enumerate(
        displayed_results,
        start=1,
    ):

        title = html.escape(
            str(
                product.get(
                    "title",
                    t("product_untitled", lang),
                )
            )
        )

        store = html.escape(
            str(
                product.get(
                    "store",
                    t("product_unknown_store", lang),
                )
            )
        )

        rating = product.get("rating")
        reviews = product.get("reviews")

        rating_text = (
            f"{rating}/5"
            if rating is not None
            else t("product_no_data", lang)
        )

        reviews_text = (
            f"{reviews:,}"
            if reviews is not None
            else t("product_no_data", lang)
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
            product_condition,
            lang,
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
            + t(
                "product_price",
                lang,
                price=format_price(price),
                symbol=symbol,
            )
            + "\n"
            + t("product_store", lang, store=store)
            + "\n"
            + t("product_seller_rating", lang, rating=rating_text)
            + "\n"
            + t("product_reviews", lang, reviews=reviews_text)
            + "\n"
            + t("product_condition", lang, condition=condition_text)
            + "\n"
            + t("product_match", lang, score=match_score)
            + "\n"
            + t("product_deal_score", lang, score=deal_score)
        )

        product_url = clean_url(
            product.get(
                "url",
                "",
            )
        )

        try:

            candidate_id = save_favorite_candidate(
                user_id,
                product,
            )

            favorite = is_favorite(
                user_id,
                product_url,
            )

            keyboard = create_product_keyboard(
                lang,
                candidate_id,
                product_url,
                favorite,
            )

        except Exception as error:

            print(
                f"Ошибка подготовки товара: {error}"
            )

            keyboard = None

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    await message.answer(
        t("search_done", lang),
        parse_mode="HTML",
        reply_markup=main_keyboard(lang),
    )

    await state.clear()


# =========================================
# ИЗБРАННОЕ — ДОБАВЛЕНИЕ
# =========================================

@dp.callback_query(F.data.startswith("fav:add:"))
async def favorite_add(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    try:
        candidate_id = int(
            callback.data.split(":")[-1]
        )
    except (ValueError, AttributeError):
        await callback.answer(
            t("error_generic", lang),
            show_alert=True,
        )
        return

    product = get_favorite_candidate(
        user_id,
        candidate_id,
    )

    if not product:
        await callback.answer(
            t("favorites_product_unavailable", lang),
            show_alert=True,
        )
        return

    try:
        favorite_id = add_favorite(
            user_id,
            product,
        )

    except Exception as error:
        print(f"Ошибка добавления в избранное: {error}")
        await callback.answer(
            t("favorites_add_error", lang),
            show_alert=True,
        )
        return

    if favorite_id is None:

        info = get_subscription_info(user_id)
        limit = info.get("max_favorites")

        await callback.answer(
            t(
                "favorites_limit_reached",
                lang,
                limit=limit,
            ),
            show_alert=True,
        )

        return

    await callback.answer(
        t("favorites_added", lang)
    )

    keyboard = create_product_keyboard(
        lang,
        candidate_id,
        product.get("url", ""),
        True,
    )

    try:
        await callback.message.edit_reply_markup(
            reply_markup=keyboard
        )
    except Exception:
        pass


# =========================================
# ИЗБРАННОЕ — УДАЛЕНИЕ
# =========================================

@dp.callback_query(F.data.startswith("fav:remove:"))
async def favorite_remove_from_card(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    try:

        candidate_id = int(
            callback.data.split(":")[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            t("error_generic", lang),
            show_alert=True,
        )

        return

    product = get_favorite_candidate(
        user_id,
        candidate_id,
    )

    if not product:

        await callback.answer(
            t("favorites_product_unavailable", lang),
            show_alert=True,
        )

        return

    deleted = remove_favorite(
        user_id,
        url=product.get("url", ""),
    )

    if deleted:

        await callback.answer(
            t("favorites_removed", lang)
        )

        keyboard = create_product_keyboard(
            lang,
            candidate_id,
            product.get("url", ""),
            False,
        )

        await callback.message.edit_reply_markup(
            reply_markup=keyboard
        )

    else:

        await callback.answer(
            t("favorites_already_removed", lang)
        )


# =========================================
# МОИ ПОИСКИ
# =========================================

@dp.message(
    F.text.in_(
        [
            t("menu_my_searches", "en"),
            t("menu_my_searches", "uk"),
        ]
    )
)
async def my_searches(
    message: Message,
):

    user_id = message.from_user.id
    lang = lang_of(user_id)

    history = get_search_history(
        user_id,
        limit=10,
    )

    if not history:

        await message.answer(
            t("history_title", lang)
            + "\n\n"
            + t("history_empty", lang),
            parse_mode="HTML",
        )

        return

    await message.answer(
        t("history_last", lang),
        parse_mode="HTML",
    )

    for item in history:

        requirements = (
            item.get("requirements")
            or t("history_no_requirements", lang)
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

            price_text = t(
                "history_from",
                lang,
                min=format_price(min_price),
                currency=currency,
            )

        product_text = html.escape(
            str(
                item.get(
                    "product",
                    "—",
                )
            )
        )

        requirements_text = html.escape(
            str(requirements)
        )

        cond_text = condition_name(
            item.get("condition", "any"),
            lang,
        )

        text = (
            f"🔎 <b>{product_text}</b>\n"
            f"💰 {price_text}\n"
            f"📝 {requirements_text}\n"
            f"📦 {cond_text}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t("history_repeat", lang),
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

@dp.callback_query(F.data.startswith("hist:run:"))
async def repeat_search(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    if not can_search(user_id):

        usage = get_usage_info(user_id)

        plan = get_active_plan(user_id)

        if plan == "ultra":
            key = "search_limit_reached_today"
        else:
            key = "search_limit_reached"

        await callback.answer(
            t(
                key,
                lang,
                used=usage["used"],
                limit=usage["limit"],
            ),
            show_alert=True,
        )

        return

    try:

        history_id = int(
            callback.data.split(":")[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            t("error_generic", lang),
            show_alert=True,
        )

        return

    item = get_search_history_item(
        history_id,
        user_id,
    )

    if not item:

        await callback.answer(
            t("history_search_not_found", lang),
            show_alert=True,
        )

        return

    try:

        if item.get("ai_data"):

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
            t("history_repeating", lang),
            parse_mode="HTML",
        )

        audience = ai_data.get(
            "audience",
            "adult",
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
            requirements=item.get("requirements"),
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
            audience=audience,
        )

    except Exception as error:

        print(
            f"Ошибка повторного поиска: {error}"
        )

        await callback.message.answer(
            t("history_repeat_failed", lang)
        )

        await callback.answer()

        return

    if not consume_search(user_id):

        await callback.message.answer(
            t("search_limit_already_used", lang)
        )

        await callback.answer()

        return

    if not results:

        await callback.message.answer(
            t("history_nothing_found", lang)
        )

        await callback.answer()

        return

    symbol = currency_symbol(
        item["currency"]
    )

    usage = get_usage_info(user_id)

    await callback.message.answer(
        t(
            "history_found",
            lang,
            count=len(results),
            shown=min(5, len(results)),
            remaining=usage["remaining"],
        ),
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
                    t("product_untitled", lang),
                )
            )
        )

        store = html.escape(
            str(
                product.get(
                    "store",
                    t("product_unknown_store", lang),
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
            user_id,
            product,
        )

        favorite = is_favorite(
            user_id,
            url,
        )

        keyboard = create_product_keyboard(
            lang,
            candidate_id,
            url,
            favorite,
        )

        text = (
            f"🔹 <b>{index}. {title}</b>\n\n"
            + t(
                "product_price",
                lang,
                price=format_price(price),
                symbol=symbol,
            )
            + "\n"
            + t("product_store", lang, store=store)
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
    F.text.in_(
        [
            t("menu_favorites", "en"),
            t("menu_favorites", "uk"),
        ]
    )
)
async def favorites(
    message: Message,
):

    user_id = message.from_user.id
    lang = lang_of(user_id)

    items = get_favorites(
        user_id,
        limit=50,
    )

    info = get_subscription_info(user_id)
    limit = info.get("max_favorites")

    if not items:

        if limit is not None:
            limit_text = t(
                "favorites_limit_empty",
                lang,
                limit=limit,
            )
        else:
            limit_text = t("favorites_unlimited", lang)

        await message.answer(
            t("favorites_title", lang)
            + "\n\n"
            + limit_text
            + "\n"
            + t("favorites_empty", lang),
            parse_mode="HTML",
        )

        return

    if limit is not None:
        count_text = t(
            "favorites_saved",
            lang,
            count=len(items),
            limit=limit,
        )
    else:
        count_text = t(
            "favorites_saved_unlimited",
            lang,
            count=len(items),
        )

    await message.answer(
        t("favorites_title", lang)
        + "\n\n"
        + count_text,
        parse_mode="HTML",
    )

    for item in items:

        title = html.escape(
            str(
                item.get(
                    "title",
                    t("product_untitled", lang),
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
                        text=t("btn_open_product", lang),
                        url=url,
                    )
                ]
            )

        rows.append(
            [
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=(
                        f"favorite:remove:{item['id']}"
                    ),
                )
            ]
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=rows
            ),
        )


# =========================================
# УДАЛЕНИЕ ИЗ ИЗБРАННОГО
# =========================================

@dp.callback_query(F.data.startswith("favorite:remove:"))
async def favorite_remove(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    try:

        favorite_id = int(
            callback.data.split(":")[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            t("error_generic", lang),
            show_alert=True,
        )

        return

    deleted = remove_favorite(
        user_id,
        favorite_id=favorite_id,
    )

    if deleted:

        await callback.answer(
            t("favorites_removed", lang)
        )

        try:
            await callback.message.delete()
        except Exception:
            pass

    else:

        await callback.answer(
            t("favorites_already_removed", lang)
        )


# =========================================
# ПОДПИСКА
# =========================================

@dp.message(
    F.text.in_(
        [
            t("menu_subscription", "en"),
            t("menu_subscription", "uk"),
        ]
    )
)
async def subscription_page(
    message: Message,
):

    user_id = message.from_user.id
    lang = lang_of(user_id)

    get_subscription(user_id)

    await message.answer(
        subscription_text(user_id),
        parse_mode="HTML",
        reply_markup=subscription_active_keyboard(lang),
    )


# =========================================
# ВЫБОР ТАРИФА
# =========================================

@dp.callback_query(
    F.data.in_(
        {
            "subscription:pro",
            "subscription:ultra",
        }
    )
)
async def subscription_select(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    plan = callback.data.split(":")[-1]

    plan_data = SUBSCRIPTION_PLANS.get(plan)

    if not plan_data:

        await callback.answer(
            t("subscription_plan_not_found", lang),
            show_alert=True,
        )

        return

    name = plan_data.get("name", plan)
    stars = plan_data.get("stars", 0)
    days = plan_data.get("days", 30)

    if plan_data.get("searches_per_day"):
        searches_text = t(
            "subscription_searches_per_day",
            lang,
            n=plan_data["searches_per_day"],
        )
    else:
        searches_text = t(
            "subscription_searches_per_month",
            lang,
            n=plan_data.get("searches_per_month", 0),
        )

    trackers = plan_data.get("max_trackers", 0)

    await callback.message.edit_text(
        t(
            "subscription_plan_details",
            lang,
            name=name,
            stars=stars,
            days=days,
            searches=searches_text,
            trackers=trackers,
        ),
        parse_mode="HTML",
        reply_markup=subscription_buy_keyboard(
            lang,
            plan,
            stars,
        ),
    )

    await callback.answer()


# =========================================
# ТЕСТОВАЯ АКТИВАЦИЯ
# =========================================

@dp.callback_query(
    F.data.startswith("subscription:test:")
)
async def subscription_test_activate(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    plan = callback.data.split(":")[-1]

    if plan == "free":

        activated = activate_subscription(
            user_id,
            "free",
        )

        if not activated:

            await callback.answer(
                "❌",
                show_alert=True,
            )

            return

        await callback.message.edit_text(
            subscription_text(user_id),
            parse_mode="HTML",
            reply_markup=subscription_active_keyboard(lang),
        )

        await callback.answer(
            t("subscription_current_free", lang)
        )

        return

    if plan not in {"pro", "ultra"}:

        await callback.answer(
            t("subscription_unknown_plan", lang),
            show_alert=True,
        )

        return

    activated = activate_subscription(
        user_id,
        plan,
    )

    if not activated:

        await callback.answer(
            "❌",
            show_alert=True,
        )

        return

    plan_name = SUBSCRIPTION_PLANS[plan]["name"]

    await callback.message.edit_text(
        subscription_text(user_id),
        parse_mode="HTML",
        reply_markup=subscription_active_keyboard(lang),
    )

    await callback.answer(
        f"🧪 {plan_name}",
        show_alert=True,
    )


# =========================================
# ПОКУПКА
# =========================================

@dp.callback_query(
    F.data.startswith("subscription:buy:")
)
async def subscription_buy(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    plan = callback.data.split(":")[-1]

    if plan not in {"pro", "ultra"}:

        await callback.answer(
            t("subscription_unknown_plan", lang),
            show_alert=True,
        )

        return

    plan_data = SUBSCRIPTION_PLANS.get(plan)

    if not plan_data:

        await callback.answer(
            t("subscription_plan_not_found", lang),
            show_alert=True,
        )

        return

    stars = plan_data.get("stars", 0)

    sent = await send_subscription_invoice(
        chat_id=user_id,
        plan=plan,
        lang=lang,
    )

    if sent:
        await callback.answer(
            t(
                "subscription_invoice_opening",
                lang,
                stars=stars,
            )
        )
    else:
        await callback.answer(
            t("subscription_invoice_failed", lang),
            show_alert=True,
        )


# =========================================
# НАЗАД В ПОДПИСКУ
# =========================================

@dp.callback_query(F.data == "subscription:back")
async def subscription_back(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    await callback.message.edit_text(
        subscription_text(user_id),
        parse_mode="HTML",
        reply_markup=subscription_active_keyboard(lang),
    )

    await callback.answer()

# =========================================
# ОПЛАТА TELEGRAM STARS
# =========================================

async def send_subscription_invoice(
    chat_id: int,
    plan: str,
    lang: str,
):

    plan_data = SUBSCRIPTION_PLANS.get(plan)

    if not plan_data:
        return False

    stars = plan_data.get("stars", 0)
    days = plan_data.get("days", 30)
    name = plan_data.get("name", plan)

    if stars <= 0:
        return False

    try:
        await bot.send_invoice(
            chat_id=chat_id,
            title=t(
                "subscription_invoice_title",
                lang,
                name=name,
            ),
            description=t(
                "subscription_invoice_description",
                lang,
                name=name,
                days=days,
            ),
            payload=f"subscription:{plan}",
            provider_token="",
            currency="XTR",
            prices=[
                LabeledPrice(
                    label=t(
                        "subscription_invoice_label",
                        lang,
                        name=name,
                        days=days,
                    ),
                    amount=stars,
                )
            ],
            start_parameter=f"sub-{plan}",
        )
        return True

    except Exception as error:
        print(f"[STARS] Ошибка отправки инвойса: {error}")

        return False


# =========================================
# ОТСЛЕЖИВАНИЕ ЦЕН
# =========================================

@dp.message(
    F.text.in_(
        [
            t("menu_tracking", "en"),
            t("menu_tracking", "uk"),
        ]
    )
)
async def price_tracking(
    message: Message,
):

    user_id = message.from_user.id
    lang = lang_of(user_id)

    if not has_plan(user_id, "pro"):

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t("tracking_connect_pro", lang),
                        callback_data="subscription:pro",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=t("tracking_connect_ultra", lang),
                        callback_data="subscription:ultra",
                    )
                ],
            ]
        )

        await message.answer(
            t("tracking_locked", lang),
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        return

    trackers = get_price_trackers(
        user_id,
        active_only=True,
    )

    limit = get_tracker_limit(user_id)

    if not trackers:

        await message.answer(
            t("tracking_no_trackers", lang),
            parse_mode="HTML",
        )

        return

    await message.answer(
        t("tracking_your_trackers", lang)
        + "\n\n"
        + t(
            "tracking_used",
            lang,
            used=len(trackers),
            limit=limit,
        ),
        parse_mode="HTML",
    )

    for tracker in trackers:

        await message.answer(
            tracker_text(tracker, lang),
            parse_mode="HTML",
            reply_markup=tracker_keyboard(
                lang,
                tracker["id"],
            ),
        )


# =========================================
# ДОБАВЛЕНИЕ ТРЕКЕРА
# =========================================

@dp.callback_query(F.data.startswith("track:add:"))
async def track_add(
    callback: CallbackQuery,
    state: FSMContext,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    if not has_plan(user_id, "pro"):

        await callback.answer(
            t("tracking_not_available", lang),
            show_alert=True,
        )

        return

    if not can_add_tracker(user_id):

        limit = get_tracker_limit(user_id)

        current = count_active_trackers(user_id)

        await callback.answer(
            t(
                "tracking_limit_reached",
                lang,
                current=current,
                limit=limit,
            ),
            show_alert=True,
        )

        return

    try:

        candidate_id = int(
            callback.data.split(":")[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            t("error_generic", lang),
            show_alert=True,
        )

        return

    product = get_favorite_candidate(
        user_id,
        candidate_id,
    )

    if not product:

        await callback.answer(
            t("favorites_product_unavailable", lang),
            show_alert=True,
        )

        return

    current_price = product.get(
        "price"
    )

    if current_price is None:

        await callback.answer(
            t("tracking_no_price", lang),
            show_alert=True,
        )

        return

    url = clean_url(
        product.get(
            "url",
            "",
        )
    )

    if not url:

        await callback.answer(
            t("tracking_no_url", lang),
            show_alert=True,
        )

        return

    existing = get_price_trackers(
        user_id,
        active_only=False,
    )

    for tracker in existing:

        if tracker.get("url") == url:

            await callback.answer(
                t("tracking_already_tracked", lang),
                show_alert=True,
            )

            return

    await state.clear()

    await state.update_data(
        track_product=product,
    )

    await state.set_state(
        PriceTrackingForm.target_price
    )

    symbol = currency_symbol(
        product.get(
            "currency",
            "UAH",
        )
    )

    title = html.escape(
        str(
            product.get(
                "title",
                "—",
            )
        )
    )

    await callback.message.answer(
        t("tracking_setup_title", lang)
        + "\n\n"
        + t("tracking_product_label", lang, title=title)
        + "\n"
        + t(
            "tracking_current_price",
            lang,
            price=format_price(current_price),
            symbol=symbol,
        )
        + "\n\n"
        + t("tracking_target_prompt", lang),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )

    await callback.answer()


# =========================================
# ЦЕЛЕВАЯ ЦЕНА
# =========================================

@dp.message(PriceTrackingForm.target_price)
async def process_target_price(
    message: Message,
    state: FSMContext,
):

    user_id = message.from_user.id
    lang = lang_of(user_id)

    if not message.text:

        await message.answer(
            t("error_number_only", lang),
            parse_mode="HTML",
        )

        return

    text = (
        message.text
        .strip()
        .replace(",", ".")
        .replace(" ", "")
    )

    try:

        target_price = float(text)

        if target_price <= 0:
            raise ValueError

    except ValueError:

        await message.answer(
            t("tracking_input_positive_price", lang),
            parse_mode="HTML",
        )

        return

    if not can_add_tracker(user_id):

        await message.answer(
            t("tracking_limit_reached_plain", lang),
            reply_markup=main_keyboard(lang),
        )

        await state.clear()

        return

    data = await state.get_data()

    product = data.get(
        "track_product"
    )

    if not product:

        await message.answer(
            t("tracking_product_lost", lang),
            reply_markup=main_keyboard(lang),
        )

        await state.clear()

        return

    tracker_id = add_price_tracker(
        user_id=user_id,
        title=product.get(
            "title",
            "—",
        ),
        store=product.get(
            "store",
            "",
        ),
        url=clean_url(
            product.get(
                "url",
                "",
            )
        ),
        currency=product.get(
            "currency",
            "UAH",
        ),
        current_price=product.get(
            "price"
        ),
        target_price=target_price,
        product_query=product.get(
            "title"
        ),
        condition=product.get(
            "condition",
            "any",
        ),
        picture=product.get(
            "picture",
            "",
        ),
    )

    if not tracker_id:

        await message.answer(
            t("tracking_add_failed", lang),
            reply_markup=main_keyboard(lang),
        )

        await state.clear()

        return

    tracker = get_price_tracker(
        user_id,
        tracker_id,
    )

    await message.answer(
        t("tracking_added_title", lang)
        + "\n\n"
        + tracker_text(tracker, lang),
        parse_mode="HTML",
        reply_markup=tracker_keyboard(
            lang,
            tracker_id,
        ),
    )

    await message.answer(
        t("tracking_added_note", lang),
        reply_markup=main_keyboard(lang),
    )

    await state.clear()


# =========================================
# РУЧНАЯ ПРОВЕРКА ЦЕНЫ
# =========================================

@dp.callback_query(F.data.startswith("track:check:"))
async def track_check(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    try:

        tracker_id = int(
            callback.data.split(":")[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            t("error_generic", lang),
            show_alert=True,
        )

        return

    tracker = get_price_tracker(
        user_id,
        tracker_id,
    )

    if not tracker:

        await callback.answer(
            t("check_tracker_not_found", lang),
            show_alert=True,
        )

        return

    await callback.answer(
        t("check_checking", lang)
    )

    try:

        results = await asyncio.to_thread(
            search_products,
            product_query=tracker.get(
                "product_query"
            ) or tracker.get(
                "title"
            ),
            min_price=0,
            max_price=None,
            currency=tracker.get(
                "currency",
                "UAH",
            ),
            country="UA",
            condition=tracker.get(
                "condition",
                "any",
            ),
            requirements=None,
            search_terms=[
                tracker.get(
                    "product_query"
                ) or tracker.get(
                    "title"
                )
            ],
            must_groups=[
                [
                    tracker.get(
                        "product_query"
                    ) or tracker.get(
                        "title"
                    )
                ]
            ],
            requirement_terms=[],
            exclude_terms=[],
            audience="adult",
        )

    except Exception as error:

        print(
            f"Ошибка проверки трекера: {error}"
        )

        await callback.message.answer(
            t("check_failed", lang)
        )

        return

    target_url = clean_url(
        tracker.get(
            "url",
            "",
        )
    )

    found_product = None

    for product in results:

        product_url = clean_url(
            product.get(
                "url",
                "",
            )
        )

        if product_url == target_url:

            found_product = product

            break

    if not found_product:

        await callback.message.answer(
            t("check_not_found", lang),
            parse_mode="HTML",
        )

        return

    new_price = found_product.get(
        "price"
    )

    if new_price is None:

        await callback.message.answer(
            t("check_no_price", lang)
        )

        return

    old_price = tracker.get(
        "current_price"
    )

    target_price = tracker.get(
        "target_price"
    )

    target_reached = (
        target_price is not None
        and float(new_price) <= float(target_price)
    )

    previous_notified = bool(
        tracker.get(
            "target_notified",
            0,
        )
    )

    update_price_tracker(
        tracker_id=tracker_id,
        current_price=new_price,
        target_notified=target_reached,
    )

    days = get_price_history_days(user_id)

    cleanup_price_history(tracker_id, days)

    updated_tracker = get_price_tracker(
        user_id,
        tracker_id,
    )

    symbol = currency_symbol(
        tracker.get(
            "currency",
            "UAH",
        )
    )

    if old_price is not None:

        old_value = float(old_price)
        new_value = float(new_price)

        if new_value < old_value:

            difference = old_value - new_value

            price_change = t(
                "check_price_decreased",
                lang,
                amount=format_price(difference),
                symbol=symbol,
            )

        elif new_value > old_value:

            difference = new_value - old_value

            price_change = t(
                "check_price_increased",
                lang,
                amount=format_price(difference),
                symbol=symbol,
            )

        else:

            price_change = t("check_price_same", lang)

    else:

        price_change = t("check_first_price", lang)

    await callback.message.answer(
        t("check_updated", lang)
        + "\n\n"
        + price_change
        + "\n\n"
        + tracker_text(updated_tracker, lang),
        parse_mode="HTML",
        reply_markup=tracker_keyboard(
            lang,
            tracker_id,
        ),
    )

    if target_reached and not previous_notified:

        await callback.message.answer(
            t(
                "check_target_reached",
                lang,
                price=format_price(new_price),
                target=format_price(target_price),
                symbol=symbol,
            ),
            parse_mode="HTML",
        )


# =========================================
# ИСТОРИЯ ЦЕН
# =========================================

@dp.callback_query(F.data.startswith("track:history:"))
async def track_history(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    try:

        tracker_id = int(
            callback.data.split(":")[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            t("error_generic", lang),
            show_alert=True,
        )

        return

    tracker = get_price_tracker(
        user_id,
        tracker_id,
    )

    if not tracker:

        await callback.answer(
            t("check_tracker_not_found", lang),
            show_alert=True,
        )

        return

    history = get_price_history(
        tracker_id,
        limit=20,
    )

    if not history:

        await callback.answer(
            t("price_history_empty", lang),
            show_alert=True,
        )

        return

    symbol = currency_symbol(
        tracker.get(
            "currency",
            "UAH",
        )
    )

    title = html.escape(
        str(
            tracker.get(
                "title",
                "—",
            )
        )
    )

    lines = [
        t("price_history_title", lang),
        f"🔹 {title}",
        "",
    ]

    for item in history:

        price = item.get(
            "price"
        )

        date = str(
            item.get(
                "recorded_at",
                "",
            )
        ).replace(
            "T",
            " ",
        )

        date = date[:19]

        lines.append(
            t(
                "price_history_line",
                lang,
                price=format_price(price),
                symbol=symbol,
                date=date,
            )
        )

    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML",
    )

    await callback.answer()


# =========================================
# УДАЛЕНИЕ ТРЕКЕРА
# =========================================

@dp.callback_query(F.data.startswith("track:remove:"))
async def track_remove(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    try:

        tracker_id = int(
            callback.data.split(":")[-1]
        )

    except (
        ValueError,
        AttributeError,
    ):

        await callback.answer(
            t("error_generic", lang),
            show_alert=True,
        )

        return

    deleted = remove_price_tracker(
        user_id,
        tracker_id,
    )

    if not deleted:

        await callback.answer(
            "❌",
            show_alert=True,
        )

        return

    await callback.answer(
        t("favorites_removed", lang)
    )

    try:

        await callback.message.delete()

    except Exception:
        pass


# =========================================
# НАСТРОЙКИ
# =========================================

def settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t("settings_btn_currency", lang),
                callback_data="settings:currency",
            )],
            [InlineKeyboardButton(
                text=t("settings_btn_condition", lang),
                callback_data="settings:condition",
            )],
            [InlineKeyboardButton(
                text=t("settings_btn_country", lang),
                callback_data="settings:country",
            )],
            [InlineKeyboardButton(
                text=t("settings_btn_language", lang),
                callback_data="settings:language",
            )],
            [InlineKeyboardButton(
                text=t("settings_btn_reset", lang),
                callback_data="settings:reset",
            )],
        ]
    )


def settings_text(user_id: int) -> str:
    lang = lang_of(user_id)
    data = get_settings(user_id)

    currency = data.get("currency", "UAH")
    condition = data.get("condition", "new")

    country_text = t("settings_country_name", lang)
    cond_text = condition_name(condition, lang)
    lang_name = get_lang_name(lang)

    return (
        t("settings_title", lang)
        + "\n\n"
        + t("settings_currency", lang, currency=currency)
        + "\n"
        + t("settings_country", lang, country=country_text)
        + "\n"
        + t("settings_condition", lang, condition=cond_text)
        + "\n"
        + t("settings_language", lang, name=lang_name)
    )


@dp.message(
    F.text.in_(
        [
            t("menu_settings", "en"),
            t("menu_settings", "uk"),
        ]
    )
)
async def settings(
    message: Message,
):

    user_id = message.from_user.id
    lang = lang_of(user_id)

    await message.answer(
        settings_text(user_id),
        parse_mode="HTML",
        reply_markup=settings_keyboard(lang),
    )


# =========================================
# ВЫБОР ВАЛЮТЫ
# =========================================

@dp.callback_query(F.data == "settings:currency")
async def settings_currency(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

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
                    text=t("settings_btn_back", lang),
                    callback_data="settings:back",
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        settings_text(user_id),
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    await callback.answer()


# =========================================
# СОСТОЯНИЕ
# =========================================

@dp.callback_query(F.data == "settings:condition")
async def settings_condition(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("condition_new", lang),
                    callback_data="set:condition:new",
                ),
                InlineKeyboardButton(
                    text=t("condition_used", lang),
                    callback_data="set:condition:used",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("condition_any", lang),
                    callback_data="set:condition:any",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("settings_btn_back", lang),
                    callback_data="settings:back",
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        settings_text(user_id),
        parse_mode="HTML",
        reply_markup=keyboard,
    )

    await callback.answer()


# =========================================
# СТРАНА
# =========================================

@dp.callback_query(F.data == "settings:country")
async def settings_country(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    set_setting(
        user_id,
        "country",
        "UA",
    )

    try:
        await callback.message.edit_text(
            settings_text(user_id),
            parse_mode="HTML",
            reply_markup=settings_keyboard(lang),
        )
    except TelegramBadRequest:
        pass

    await callback.answer(
        t(
            "settings_country_saved",
            lang,
            country=t("settings_country_name", lang),
        )
    )


@dp.callback_query(F.data == "settings:language")
async def settings_language(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇬🇧 English",
                    callback_data="set:language:en",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇺🇦 Українська",
                    callback_data="set:language:uk",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("settings_btn_back", lang),
                    callback_data="settings:back",
                ),
            ],
        ]
    )

    try:
        await callback.message.edit_text(
            t("settings_language_title", lang),
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except TelegramBadRequest:
        pass

    await callback.answer()


@dp.callback_query(F.data.startswith("set:language:"))
async def set_language(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id

    new_lang = callback.data.split(":")[-1]

    if new_lang not in SUPPORTED_LANGS:
        await callback.answer("❌", show_alert=True)
        return

    set_user_language(user_id, new_lang)

    try:
        await callback.message.edit_text(
            settings_text(user_id),
            parse_mode="HTML",
            reply_markup=settings_keyboard(new_lang),
        )
    except TelegramBadRequest:
        pass

    await callback.message.answer(
        t(
            "settings_language_saved",
            new_lang,
            name=get_lang_name(new_lang),
        ),
        reply_markup=main_keyboard(new_lang),
    )

    await callback.answer()


# =========================================
# ВАЛЮТА
# =========================================

@dp.callback_query(F.data.startswith("set:currency:"))
async def set_currency(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    currency = callback.data.split(":")[-1]

    if currency not in {
        "UAH",
        "USD",
        "EUR",
    }:

        await callback.answer(
            t("settings_invalid_currency", lang),
            show_alert=True,
        )

        return

    set_setting(
        user_id,
        "currency",
        currency,
    )

    await callback.message.edit_text(
        settings_text(user_id),
        parse_mode="HTML",
        reply_markup=settings_keyboard(lang),
    )

    await callback.answer(
        t(
            "settings_currency_saved",
            lang,
            currency=currency,
        )
    )


# =========================================
# СОСТОЯНИЕ
# =========================================

@dp.callback_query(F.data.startswith("set:condition:"))
async def set_condition(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    condition = callback.data.split(":")[-1]

    if condition not in {
        "new",
        "used",
        "any",
    }:

        await callback.answer(
            t("settings_invalid_condition", lang),
            show_alert=True,
        )

        return

    set_setting(
        user_id,
        "condition",
        condition,
    )

    await callback.message.edit_text(
        settings_text(user_id),
        parse_mode="HTML",
        reply_markup=settings_keyboard(lang),
    )

    await callback.answer(
        t("settings_condition_saved", lang)
    )


# =========================================
# СБРОС
# =========================================

@dp.callback_query(F.data == "settings:reset")
async def settings_reset(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id

    reset_settings(user_id)

    lang = lang_of(user_id)

    await callback.message.edit_text(
        settings_text(user_id),
        parse_mode="HTML",
        reply_markup=settings_keyboard(lang),
    )

    await callback.answer(
        t("settings_reset_done", lang)
    )


# =========================================
# НАЗАД
# =========================================

@dp.callback_query(F.data == "settings:back")
async def settings_back(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id
    lang = lang_of(user_id)

    await callback.message.edit_text(
        settings_text(user_id),
        parse_mode="HTML",
        reply_markup=settings_keyboard(lang),
    )

    await callback.answer()

# =========================================
# PRE-CHECKOUT (подтверждение перед оплатой)
# =========================================

@dp.pre_checkout_query()
async def process_pre_checkout(
    pre_checkout_query: PreCheckoutQuery,
):
    """
    Telegram требует подтвердить
    или отклонить оплату ДО списания Stars.
    """

    try:
        await pre_checkout_query.answer(ok=True)
    except Exception as error:
        print(f"[STARS] Ошибка pre_checkout: {error}")


# =========================================
# УСПЕШНАЯ ОПЛАТА
# =========================================

@dp.message(F.successful_payment)
async def process_successful_payment(
    message: Message,
):

    payment = message.successful_payment

    if not payment:
        return

    payload = payment.invoice_payload or ""

    if not payload.startswith("subscription:"):
        print(f"[STARS] Неизвестный payload: {payload}")
        return

    plan = payload.split(":", 1)[1]

    if plan not in ("pro", "ultra"):
        print(f"[STARS] Неизвестный план: {plan}")
        return

    user_id = message.from_user.id
    lang = lang_of(user_id)

    activated = activate_subscription(user_id, plan)

    if not activated:
        await message.answer(
            t("subscription_activation_failed", lang),
            parse_mode="HTML",
        )
        return

    plan_name = SUBSCRIPTION_PLANS[plan]["name"]

    await message.answer(
        t(
            "subscription_payment_success",
            lang,
            name=plan_name,
        ),
        parse_mode="HTML",
    )

    print(
        f"[STARS] Оплата: user={user_id}, "
        f"plan={plan}, "
        f"amount={payment.total_amount} Stars, "
        f"charge_id={payment.telegram_payment_charge_id}"
    )


# =========================================
# ФОНОВАЯ ПРОВЕРКА ТРЕКЕРОВ
# =========================================

async def price_tracker_loop():

    while True:

        try:

            trackers = await asyncio.to_thread(
                get_all_active_price_trackers
            )

            for tracker in trackers:

                try:

                    user_id = tracker["user_id"]

                    if not has_plan(
                        user_id,
                        "pro",
                    ):
                        continue

                    lang = lang_of(user_id)

                    query = (
                        tracker.get("product_query")
                        or tracker.get("title")
                    )

                    if not query:
                        continue

                    results = await asyncio.to_thread(
                        search_products,
                        product_query=query,
                        min_price=0,
                        max_price=None,
                        currency=tracker.get(
                            "currency",
                            "UAH",
                        ),
                        country="UA",
                        condition=tracker.get(
                            "condition",
                            "any",
                        ),
                        requirements=None,
                        search_terms=[query],
                        must_groups=[[query]],
                        requirement_terms=[],
                        exclude_terms=[],
                        audience="adult",
                    )

                    target_url = clean_url(
                        tracker.get(
                            "url",
                            "",
                        )
                    )

                    found = None

                    for product in results:

                        if clean_url(
                            product.get(
                                "url",
                                "",
                            )
                        ) == target_url:

                            found = product

                            break

                    if not found:
                        continue

                    new_price = found.get(
                        "price"
                    )

                    if new_price is None:
                        continue

                    old_price = tracker.get(
                        "current_price"
                    )

                    target_price = tracker.get(
                        "target_price"
                    )

                    reached = (
                        target_price is not None
                        and float(new_price)
                        <= float(target_price)
                    )

                    already_notified = bool(
                        tracker.get(
                            "target_notified",
                            0,
                        )
                    )

                    now = datetime.now(timezone.utc)

                    last_notified_raw = tracker.get(
                        "last_notified_at"
                    )

                    last_notified_dt = None

                    if last_notified_raw:
                        try:
                            last_notified_dt = datetime.fromisoformat(
                                str(last_notified_raw).replace(
                                    "Z",
                                    "+00:00",
                                )
                            )
                            if last_notified_dt.tzinfo is None:
                                last_notified_dt = last_notified_dt.replace(
                                    tzinfo=timezone.utc,
                                )
                        except (ValueError, TypeError):
                            last_notified_dt = None

                    notifications_blocked = False

                    if last_notified_dt is not None:
                        elapsed = (now - last_notified_dt).total_seconds()
                        if elapsed < 24 * 3600:
                            notifications_blocked = True

                    price_dropped = False

                    if (
                        old_price is not None
                        and float(old_price) > 0
                    ):
                        old_value = float(old_price)
                        new_value = float(new_price)

                        if new_value < old_value:
                            price_dropped = True

                    drop_percent = 0.0

                    if price_dropped:
                        drop_percent = (
                            (float(old_price) - float(new_price))
                            / float(old_price)
                            * 100
                        )

                    threshold = get_price_drop_threshold(user_id) or 20

                    action = None

                    if reached and not already_notified:
                        action = "target"

                    elif price_dropped and not notifications_blocked:

                        if drop_percent >= threshold:
                            action = "sharp_drop"

                        elif drop_percent >= 5:
                            action = "drop"

                    update_kwargs = {
                        "tracker_id": tracker["id"],
                        "current_price": new_price,
                        "target_notified": reached,
                    }

                    if action in ("drop", "sharp_drop"):
                        update_kwargs["last_notified_at"] = now.isoformat()

                    update_price_tracker(**update_kwargs)

                    days = get_price_history_days(user_id)

                    cleanup_price_history(
                        tracker["id"],
                        days,
                    )

                    symbol = currency_symbol(
                        tracker.get(
                            "currency",
                            "UAH",
                        )
                    )

                    title = html.escape(
                        str(
                            tracker.get(
                                "title",
                                "—",
                            )
                        )
                    )

                    url = tracker.get("url")

                    if action == "target":

                        text = t(
                            "notify_target_reached",
                            lang,
                            title=title,
                            price=format_price(new_price),
                            target=format_price(target_price),
                            symbol=symbol,
                        )

                        if url:
                            text += (
                                f"\n\n"
                                f"<a href=\"{url}\">"
                                f"{t('notify_open_product', lang)}"
                                f"</a>"
                            )

                        try:
                            await bot.send_message(
                                user_id,
                                text,
                                parse_mode="HTML",
                            )
                        except Exception as error:
                            print(
                                f"[TRACKING] Ошибка отправки target: {error}"
                            )

                    elif action == "sharp_drop":

                        discount = round(drop_percent)

                        text = t(
                            "notify_sharp_drop",
                            lang,
                            title=title,
                            old=format_price(old_price),
                            new=format_price(new_price),
                            discount=discount,
                            symbol=symbol,
                        )

                        if url:
                            text += (
                                f"\n\n"
                                f"<a href=\"{url}\">"
                                f"{t('notify_open_product', lang)}"
                                f"</a>"
                            )

                        try:
                            await bot.send_message(
                                user_id,
                                text,
                                parse_mode="HTML",
                            )
                        except Exception as error:
                            print(
                                f"[TRACKING] Ошибка отправки sharp_drop: {error}"
                            )

                    elif action == "drop":

                        discount = round(drop_percent)

                        text = t(
                            "notify_drop",
                            lang,
                            title=title,
                            old=format_price(old_price),
                            new=format_price(new_price),
                            discount=discount,
                            symbol=symbol,
                        )

                        if url:
                            text += (
                                f"\n\n"
                                f"<a href=\"{url}\">"
                                f"{t('notify_open_product', lang)}"
                                f"</a>"
                            )

                        try:
                            await bot.send_message(
                                user_id,
                                text,
                                parse_mode="HTML",
                            )
                        except Exception as error:
                            print(
                                f"[TRACKING] Ошибка отправки drop: {error}"
                            )

                except Exception as error:

                    print(
                        f"Ошибка фонового трекера "
                        f"{tracker.get('id')}: {error}"
                    )

        except Exception as error:

            print(
                f"Ошибка фоновой проверки: {error}"
            )

        await asyncio.sleep(
            3600
        )

# =========================================
# АДМИН-КОМАНДЫ
# =========================================

@dp.message(Command("give"))
async def admin_give(
    message: Message,
):

    if message.from_user.id not in ADMIN_IDS:
        return

    parts = message.text.strip().split()

    if len(parts) != 3:
        await message.answer(
            "Usage: <code>/give &lt;user_id&gt; &lt;pro|ultra&gt;</code>\n\n"
            "Example: <code>/give 123456789 pro</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ user_id must be a number")
        return

    plan = parts[2].lower()

    if plan not in ("pro", "ultra"):
        await message.answer("❌ plan must be <b>pro</b> or <b>ultra</b>", parse_mode="HTML")
        return

    activated = activate_subscription(target_id, plan)

    if not activated:
        await message.answer("❌ Failed to activate subscription")
        return

    await message.answer(
        f"✅ <b>{plan}</b> activated for <code>{target_id}</code> "
        f"for 30 days",
        parse_mode="HTML",
    )

    # Уведомляем получателя
    try:
        plan_name = SUBSCRIPTION_PLANS[plan]["name"]
        await bot.send_message(
            target_id,
            f"🎁 <b>Вам выдана подписка {plan_name}!</b>\n\n"
            f"Активирована на <b>30 дней</b>.\n\n"
            f"💎 Приятного использования Dealvoro!",
            parse_mode="HTML",
        )
    except Exception as error:
        print(f"[ADMIN] Не удалось уведомить {target_id}: {error}")


@dp.message(Command("revoke"))
async def admin_revoke(
    message: Message,
):

    if message.from_user.id not in ADMIN_IDS:
        return

    parts = message.text.strip().split()

    if len(parts) != 2:
        await message.answer(
            "Usage: <code>/revoke &lt;user_id&gt;</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ user_id must be a number")
        return

    activated = activate_subscription(target_id, "free")

    if not activated:
        await message.answer("❌ Failed to revoke")
        return

    await message.answer(
        f"✅ Subscription revoked for <code>{target_id}</code>",
        parse_mode="HTML",
    )


@dp.message(Command("whois"))
async def admin_whois(
    message: Message,
):

    if message.from_user.id not in ADMIN_IDS:
        return

    parts = message.text.strip().split()

    if len(parts) != 2:
        await message.answer(
            "Usage: <code>/whois &lt;user_id&gt;</code>",
            parse_mode="HTML",
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("❌ user_id must be a number")
        return

    info = get_subscription_info(target_id)
    usage = get_usage_info(target_id)

    plan = info.get("plan", "free")
    plan_name = info.get("name", "🆓 Free")
    expires_at = info.get("expires_at")

    trackers_used = count_active_trackers(target_id)
    trackers_limit = get_tracker_limit(target_id)

    favorites_used = count_favorites(target_id)
    history_used = count_search_history(target_id)

    text = (
        f"👤 <b>User</b>: <code>{target_id}</code>\n\n"
        f"💎 Plan: <b>{plan_name}</b>\n"
    )

    if expires_at:
        text += f"📅 Until: <b>{expires_at}</b>\n"

    text += (
        f"\n📊 <b>Usage</b>\n"
        f"🔎 Searches: <b>{usage['used']} / {usage['limit']}</b>\n"
        f"🔔 Trackers: <b>{trackers_used} / {trackers_limit}</b>\n"
        f"⭐ Favorites: <b>{favorites_used}</b>\n"
        f"📋 History: <b>{history_used}</b>\n"
    )

    await message.answer(text, parse_mode="HTML")

# =========================================
# ЗАПУСК
# =========================================

async def main():

    init_db()

    print(
        "Dealvoro запущен!"
    )

    tracker_task = asyncio.create_task(
        price_tracker_loop()
    )

    try:

        await dp.start_polling(
            bot
        )

    finally:

        tracker_task.cancel()

        try:

            await tracker_task

        except asyncio.CancelledError:

            pass

        await bot.session.close()


# =========================================
# RUN
# =========================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )