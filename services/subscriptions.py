from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from database import (
    get_subscription,
    set_subscription,
    get_usage_counter,
    reset_usage_counter,
    consume_search as db_consume_search,
)


# =========================================
# ЧАСОВОЙ ПОЯС
# =========================================

KYIV_TZ = ZoneInfo("Europe/Kyiv")


def now_kyiv() -> datetime:
    """Текущее время в Киеве."""
    return datetime.now(KYIV_TZ)


# =========================================
# ТАРИФЫ
# =========================================

SUBSCRIPTION_PLANS = {
    "free": {
        "name": "🆓 Free",
        "stars": 0,
        "days": None,

        # 5 поисков в месяц
        "searches_per_month": 5,
        "searches_per_day": None,

        # Free не может отслеживать цены
        "max_trackers": 0,

        # Free: избранное — 5, история — 5
        "max_favorites": 5,
        "max_history": 5,

        # История цены не хранится
        "price_history_days": 0,

        # Уведомления о падении недоступны
        "price_drop_threshold": 0,

        # Период: месяц
        "period": "month",
    },

    "pro": {
        "name": "⭐ Pro",
        "stars": 100,
        "days": 30,

        # 15 поисков в месяц
        "searches_per_month": 15,
        "searches_per_day": None,

        # Максимум активных отслеживаний
        "max_trackers": 3,

        "max_favorites": 50,
        "max_history": 50,

        # История цены — 30 дней
        "price_history_days": 30,

        # Уведомление при падении на 20%+
        "price_drop_threshold": 20,

        "period": "month",
    },

    "ultra": {
        "name": "👑 Ultra",
        "stars": 200,
        "days": 30,

        # 15 поисков в день
        "searches_per_month": None,
        "searches_per_day": 15,

        # Максимум активных отслеживаний
        "max_trackers": 25,

        # Без лимита
        "max_favorites": None,
        "max_history": None,

        # История цены — 90 дней
        "price_history_days": 90,

        # Уведомление при падении на 20%+
        "price_drop_threshold": 20,

        "period": "day",
    },
}


# =========================================
# УРОВНИ ТАРИФОВ
# =========================================

PLAN_LEVELS = {
    "free": 0,
    "pro": 1,
    "ultra": 2,
}


# =========================================
# ПОЛУЧЕНИЕ АКТИВНОГО ТАРИФА
# =========================================

def get_active_plan(user_id: int) -> str:
    """
    Возвращает текущий активный тариф:
        free | pro | ultra

    Если подписка отсутствует,
    истекла или повреждена — free.
    """

    subscription = get_subscription(user_id)

    if not subscription:
        return "free"

    plan = subscription.get("plan", "free")

    expires_at = subscription.get("expires_at")

    if plan not in SUBSCRIPTION_PLANS:
        return "free"

    if plan == "free":
        return "free"

    if not expires_at:
        return "free"

    try:
        if isinstance(expires_at, datetime):
            expiration = expires_at
        else:
            expiration = datetime.fromisoformat(
                str(expires_at).replace("Z", "+00:00")
            )

        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        if expiration <= now:
            return "free"

    except (ValueError, TypeError):
        return "free"

    return plan


# =========================================
# ПРОВЕРКА ДОСТУПА
# =========================================

def has_plan(user_id: int, required_plan: str) -> bool:
    """
    Проверяет уровень подписки.

    has_plan(uid, "pro") -> True для Pro и Ultra
    """

    if required_plan not in PLAN_LEVELS:
        return False

    active_plan = get_active_plan(user_id)

    active_level = PLAN_LEVELS.get(active_plan, 0)
    required_level = PLAN_LEVELS.get(required_plan, 0)

    return active_level >= required_level


# =========================================
# АКТИВАЦИЯ ПОДПИСКИ
# =========================================

def activate_subscription(user_id: int, plan: str) -> bool:
    """
    Активирует тариф пользователя
    и СБРАСЫВАЕТ счётчик поисков в 0.

    Сейчас — тестовая активация.
    Потом — после оплаты Telegram Stars.
    """

    if plan not in SUBSCRIPTION_PLANS:
        return False

    # =====================================
    # FREE
    # =====================================

    if plan == "free":
        set_subscription(
            user_id=user_id,
            plan="free",
            expires_at=None,
        )
        reset_usage_counter(user_id)
        return True

    # =====================================
    # ПЛАТНЫЙ ТАРИФ
    # =====================================

    days = SUBSCRIPTION_PLANS[plan].get("days")

    if not days:
        return False

    expiration = (
        datetime.now(timezone.utc)
        + timedelta(days=days)
    )

    set_subscription(
        user_id=user_id,
        plan=plan,
        expires_at=expiration.isoformat(),
    )

    reset_usage_counter(user_id)

    return True


# =========================================
# ИНФОРМАЦИЯ О ПОДПИСКЕ
# =========================================

def get_subscription_info(user_id: int) -> dict:
    """
    Возвращает информацию
    о текущем тарифе.
    """

    active_plan = get_active_plan(user_id)

    subscription = get_subscription(user_id)

    plan_info = SUBSCRIPTION_PLANS.get(
        active_plan,
        SUBSCRIPTION_PLANS["free"],
    )

    # Для free не показываем дату —
    # чтобы не тащить старую дату из Pro/Ultra.

    expires_at = None

    if active_plan != "free" and subscription:
        expires_at = subscription.get("expires_at")

    return {
        "plan": active_plan,

        "name": plan_info.get("name", "🆓 Free"),

        "stars": plan_info.get("stars", 0),

        "expires_at": expires_at,

        "searches_per_month": plan_info.get("searches_per_month"),

        "searches_per_day": plan_info.get("searches_per_day"),

        "max_trackers": plan_info.get("max_trackers", 0),

        "max_favorites": plan_info.get("max_favorites"),

        "max_history": plan_info.get("max_history"),

        "price_history_days": plan_info.get("price_history_days", 0),

        "price_drop_threshold": plan_info.get("price_drop_threshold", 0),

        "period": plan_info.get("period", "month"),
    }


# =========================================
# ТЕКУЩИЙ ПЕРИОД
# =========================================

def get_current_period(plan: str = None) -> str:
    """
    Возвращает ключ периода для счётчика поисков.

    Для free и pro (period = "month"):
        2026-09

    Для ultra (period = "day"):
        2026-09-16
    """

    now = now_kyiv()

    if plan is None:
        plan = "free"

    plan_info = SUBSCRIPTION_PLANS.get(
        plan,
        SUBSCRIPTION_PLANS["free"],
    )

    period = plan_info.get("period", "month")

    if period == "day":
        return now.strftime("%Y-%m-%d")

    return now.strftime("%Y-%m")


def get_period_label(plan: str = None) -> str:
    """
    Человекочитаемый период.

    "day"   -> "сегодня"
    "month" -> "в этом месяце"
    """

    if plan is None:
        plan = "free"

    plan_info = SUBSCRIPTION_PLANS.get(
        plan,
        SUBSCRIPTION_PLANS["free"],
    )

    period = plan_info.get("period", "month")

    if period == "day":
        return "сегодня"

    return "в этом месяце"


# =========================================
# ЛИМИТ ПОИСКОВ ПО ТАРИФУ
# =========================================

def get_search_limit(plan: str) -> int:
    """
    Возвращает лимит поисков
    для указанного тарифа.
    """

    plan_info = SUBSCRIPTION_PLANS.get(
        plan,
        SUBSCRIPTION_PLANS["free"],
    )

    period = plan_info.get("period", "month")

    if period == "day":
        return int(plan_info.get("searches_per_day") or 0)

    return int(plan_info.get("searches_per_month") or 0)


# =========================================
# ИНФОРМАЦИЯ О ЛИМИТЕ ПОИСКОВ
# =========================================

def get_usage_info(user_id: int) -> dict:
    """
    Информация об использовании поисков.

    {
        "plan": "ultra",
        "used": 7,
        "limit": 15,
        "remaining": 8,
        "period": "2026-09-16",
        "period_label": "сегодня"
    }
    """

    plan = get_active_plan(user_id)

    limit = get_search_limit(plan)

    usage = get_usage_counter(user_id)

    current_period = get_current_period(plan)

    # Если счётчик относится к прошлому периоду —
    # считаем использование равным 0.

    if not usage:
        used = 0

    elif usage.get("period_key") != current_period:
        used = 0

    else:
        used = int(usage.get("searches_used", 0))

    remaining = max(0, limit - used)

    return {
        "plan": plan,
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "period": current_period,
        "period_label": get_period_label(plan),
    }


# =========================================
# МОЖНО ЛИ ИСКАТЬ
# =========================================

def can_search(user_id: int) -> bool:
    """
    Проверяет, остались ли поиски
    в текущем периоде.
    """

    usage = get_usage_info(user_id)

    return usage["remaining"] > 0


# =========================================
# ИСПОЛЬЗОВАТЬ ОДИН ПОИСК
# =========================================

def consume_search(user_id: int) -> bool:
    """
    Списывает один поиск.

    True  — списан
    False — лимит закончился
    """

    if not can_search(user_id):
        return False

    plan = get_active_plan(user_id)

    current_period = get_current_period(plan)

    return db_consume_search(
        user_id,
        plan=plan,
        period_key=current_period,
    )


# =========================================
# ЛИМИТ ОТСЛЕЖИВАНИЙ
# =========================================

def get_tracker_limit(user_id: int) -> int:
    """
    Максимум активных отслеживаний
    для пользователя.
    """

    plan = get_active_plan(user_id)

    plan_info = SUBSCRIPTION_PLANS.get(
        plan,
        SUBSCRIPTION_PLANS["free"],
    )

    return int(plan_info.get("max_trackers", 0))


# =========================================
# МОЖНО ЛИ ДОБАВИТЬ ОТСЛЕЖИВАНИЕ
# =========================================

def can_add_tracker(
    user_id: int,
    current_trackers: int,
) -> bool:
    """
    Проверяет, можно ли добавить
    ещё одно отслеживание.
    """

    tracker_limit = get_tracker_limit(user_id)

    if tracker_limit <= 0:
        return False

    return current_trackers < tracker_limit


# =========================================
# ЛИМИТЫ ИЗБРАННОГО И ИСТОРИИ
# =========================================

def get_favorites_limit(user_id: int):
    """
    Лимит избранного.
    None = без лимита.
    """

    plan = get_active_plan(user_id)

    plan_info = SUBSCRIPTION_PLANS.get(
        plan,
        SUBSCRIPTION_PLANS["free"],
    )

    return plan_info.get("max_favorites")


def get_history_limit(user_id: int):
    """
    Лимит истории поисков.
    None = без лимита.
    """

    plan = get_active_plan(user_id)

    plan_info = SUBSCRIPTION_PLANS.get(
        plan,
        SUBSCRIPTION_PLANS["free"],
    )

    return plan_info.get("max_history")


# =========================================
# ИСТОРИЯ ЦЕНЫ И ПОРОГ ПАДЕНИЯ
# =========================================

def get_price_history_days(user_id: int) -> int:
    """
    Сколько дней хранить историю цены.
    0 = не хранить (Free).
    """

    plan = get_active_plan(user_id)

    plan_info = SUBSCRIPTION_PLANS.get(
        plan,
        SUBSCRIPTION_PLANS["free"],
    )

    return int(plan_info.get("price_history_days", 0))


def get_price_drop_threshold(user_id: int) -> int:
    """
    Порог «резкого падения» в процентах.
    0 = не уведомлять.
    """

    plan = get_active_plan(user_id)

    plan_info = SUBSCRIPTION_PLANS.get(
        plan,
        SUBSCRIPTION_PLANS["free"],
    )

    return int(plan_info.get("price_drop_threshold", 0))


# =========================================
# ФОРМАТИРОВАНИЕ ДАТЫ
# =========================================

def format_expiration_date(expires_at) -> str:
    """
    Дата подписки в формате:
        16.10.2026 08:15 UTC
    """

    if not expires_at:
        return ""

    try:
        if isinstance(expires_at, datetime):
            expiration = expires_at
        else:
            expiration = datetime.fromisoformat(
                str(expires_at).replace("Z", "+00:00")
            )

        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=timezone.utc)

        return expiration.strftime("%d.%m.%Y %H:%M UTC")

    except (ValueError, TypeError):
        return str(expires_at).replace("T", " ")


# =========================================
# ТЕКСТ ПОДПИСКИ
# =========================================

def format_subscription(user_id: int) -> str:
    """
    Формирует информацию
    о текущей подписке.
    """

    info = get_subscription_info(user_id)

    plan = info.get("plan", "free")
    name = info.get("name", "🆓 Free")
    expires_at = info.get("expires_at")

    max_trackers = info.get("max_trackers", 0)

    usage = get_usage_info(user_id)

    used_searches = usage.get("used", 0)
    limit_searches = usage.get("limit", 0)
    remaining_searches = usage.get("remaining", 0)
    period_label = usage.get("period_label", "в этом месяце")

    text = (
        "💎 <b>Ваша подписка</b>\n\n"
        f"Тариф: <b>{name}</b>\n\n"
    )

    # =====================================
    # ЛИМИТЫ ПОИСКОВ
    # =====================================

    text += (
        "📊 <b>Лимиты</b>\n"
        f"🔎 Поиски {period_label}: "
        f"<b>{used_searches}/{limit_searches}</b>\n"
        f"🟢 Осталось поисков: "
        f"<b>{remaining_searches}</b>\n"
    )

    # =====================================
    # ОТСЛЕЖИВАНИЕ
    # =====================================

    if max_trackers > 0:
        text += (
            f"🔔 Отслеживания: "
            f"до <b>{max_trackers}</b>\n"
        )
    else:
        text += (
            "🔔 Отслеживание цен: "
            "<b>недоступно</b>\n"
        )

    # =====================================
    # FREE
    # =====================================

    if plan == "free":
        text += "\n🟢 Вы используете бесплатный тариф."
        return text

    # =====================================
    # ПЛАТНЫЙ ТАРИФ
    # =====================================

    expiration_text = format_expiration_date(expires_at)

    if expiration_text:
        text += (
            f"\n⏳ Действует до: "
            f"<b>{expiration_text}</b>"
        )

    return text


# =========================================
# ПРОВЕРКА АКТИВНОЙ ПОДПИСКИ
# =========================================

def has_active_subscription(user_id: int) -> bool:
    """
    True, если активен Pro или Ultra.
    """

    return get_active_plan(user_id) != "free"