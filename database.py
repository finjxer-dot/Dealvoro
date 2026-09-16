import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path


# =========================================
# ПУТИ
# =========================================

PROJECT_ROOT = Path(__file__).parent

DATA_DIR = PROJECT_ROOT / "data"

DATABASE_FILE = DATA_DIR / "dealvoro.db"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================
# ПОДПИСКИ
# =========================================

SUBSCRIPTION_PLANS = {
    "free": {
        "name": "🆓 Free",
        "stars": 0,
        "days": None,
        "searches_per_month": 5,
        "max_trackers": 0,
    },
    "pro": {
        "name": "⭐ Pro",
        "stars": 100,
        "days": 30,
        "searches_per_month": 15,
        "max_trackers": 3,
    },
    "ultra": {
        "name": "👑 Ultra",
        "stars": 200,
        "days": 30,
        "searches_per_month": 15,
        "max_trackers": 25,
    },
}


# =========================================
# CONNECTION
# =========================================

def get_connection():
    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================

def normalize_number(value):
    if value is None:
        return None

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def get_current_period(plan: str = None):
    """
    Текущий период для лимитов.
    Для month — 2026-09, для day — 2026-09-16.
    """

    if plan is None:
        plan = "free"

    if plan == "ultra":
        return datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d")

    return datetime.now(
        timezone.utc
    ).strftime("%Y-%m")


def utc_now_iso():
    """
    Текущее UTC-время в ISO формате.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


# =========================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ
# =========================================

def init_db():

    connection = get_connection()

    cursor = connection.cursor()

    # =====================================
    # НАСТРОЙКИ
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            currency TEXT NOT NULL DEFAULT 'UAH',
            country TEXT NOT NULL DEFAULT 'UA',
            condition TEXT NOT NULL DEFAULT 'new'
        )
        """
    )

    # =====================================
    # ИСТОРИЯ ПОИСКОВ
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product TEXT NOT NULL,
            requirements TEXT,
            min_price REAL NOT NULL,
            max_price REAL,
            currency TEXT NOT NULL,
            country TEXT NOT NULL,
            condition TEXT NOT NULL,
            ai_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # =====================================
    # ИЗБРАННОЕ
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            store TEXT,
            price REAL,
            currency TEXT,
            old_price REAL,
            url TEXT NOT NULL,
            picture TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, url)
        )
        """
    )

    # =====================================
    # КАНДИДАТЫ ДЛЯ ИЗБРАННОГО
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS favorite_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            store TEXT,
            price REAL,
            currency TEXT,
            old_price REAL,
            url TEXT NOT NULL,
            picture TEXT
        )
        """
    )

    # =====================================
    # ПОДПИСКИ
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            plan TEXT NOT NULL DEFAULT 'free',
            expires_at TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # =====================================
    # ЛИМИТЫ ИСПОЛЬЗОВАНИЯ
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_counters (
            user_id INTEGER PRIMARY KEY,
            period_key TEXT NOT NULL,
            searches_used INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # =====================================
    # РЕФЕРАЛЫ
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # =====================================
    # РЕФЕРАЛЬНЫЕ БОНУСЫ
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS referral_bonuses (
            user_id INTEGER PRIMARY KEY,
            given_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_referrals_referrer
        ON referrals(referrer_id)
        """
    )

    # =====================================
    # ОТСЛЕЖИВАНИЕ ЦЕН
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS price_trackers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            store TEXT,
            url TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'UAH',
            current_price REAL,
            previous_price REAL,
            target_price REAL,
            product_query TEXT,
            condition TEXT DEFAULT 'any',
            picture TEXT,
            last_checked_at TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            target_notified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, url)
        )
        """
    )

    # =====================================
    # МИГРАЦИЯ: language
    # =====================================

    cursor.execute(
        "PRAGMA table_info(user_settings)"
    )

    user_settings_columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "language" not in user_settings_columns:

        cursor.execute(
            """
            ALTER TABLE user_settings
            ADD COLUMN language TEXT NOT NULL DEFAULT 'en'
            """
        )
    
    # =====================================
    # МИГРАЦИЯ: last_notified_at
    # =====================================

    cursor.execute(
        "PRAGMA table_info(price_trackers)"
    )

    columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    if "last_notified_at" not in columns:

        cursor.execute(
            """
            ALTER TABLE price_trackers
            ADD COLUMN last_notified_at TEXT
            """
        )


    # =====================================
    # ИСТОРИЯ ЦЕН
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracker_id INTEGER NOT NULL,
            price REAL NOT NULL,
            recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tracker_id)
                REFERENCES price_trackers(id)
                ON DELETE CASCADE
        )
        """
    )

    # =====================================
    # ИНДЕКСЫ
    # =====================================

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_search_history_user
        ON search_history(user_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_favorites_user
        ON favorites(user_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_trackers_user
        ON price_trackers(user_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_trackers_active
        ON price_trackers(active)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_price_history_tracker
        ON price_history(tracker_id)
        """
    )

    connection.commit()

    connection.close()


# =========================================
# ПОДПИСКИ — ПОЛЬЗОВАТЕЛЬ
# =========================================

def ensure_user_subscription(user_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO subscriptions (
            user_id,
            plan,
            expires_at
        )
        VALUES (?, 'free', NULL)
        """,
        (
            user_id,
        ),
    )

    connection.commit()

    connection.close()


# =========================================
# ПОЛУЧИТЬ ПОДПИСКУ
# =========================================

def get_subscription(user_id):

    ensure_user_subscription(user_id)

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            user_id,
            plan,
            expires_at,
            updated_at
        FROM subscriptions
        WHERE user_id = ?
        """,
        (
            user_id,
        ),
    )

    row = cursor.fetchone()

    connection.close()

    if not row:

        return {
            "user_id": user_id,
            "plan": "free",
            "expires_at": None,
            "updated_at": None,
        }

    return dict(row)


# =========================================
# УСТАНОВИТЬ ПОДПИСКУ
# =========================================

def set_subscription(
    user_id,
    plan,
    expires_at=None,
):

    if plan not in SUBSCRIPTION_PLANS:

        raise ValueError(
            f"Недопустимый тариф: {plan}"
        )

    ensure_user_subscription(user_id)

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE subscriptions
        SET
            plan = ?,
            expires_at = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (
            plan,
            expires_at,
            user_id,
        ),
    )

    connection.commit()

    connection.close()


# =========================================
# ПРОВЕРКА АКТИВНОСТИ ПОДПИСКИ
# =========================================

def has_active_subscription(
    user_id,
    required_plan=None,
):

    subscription = get_subscription(user_id)

    plan = subscription.get(
        "plan",
        "free",
    )

    expires_at = subscription.get(
        "expires_at"
    )

    plan_levels = {
        "free": 0,
        "pro": 1,
        "ultra": 2,
    }

    current_level = plan_levels.get(
        plan,
        0,
    )

    required_level = plan_levels.get(
        required_plan,
        0,
    )

    if plan == "free":

        return required_level == 0

    if not expires_at:

        return False

    try:

        expiration = datetime.fromisoformat(
            str(expires_at).replace(
                "Z",
                "+00:00",
            )
        )

    except (
        ValueError,
        TypeError,
    ):

        return False

    if expiration.tzinfo is None:

        expiration = expiration.replace(
            tzinfo=timezone.utc
        )

    now = datetime.now(
        timezone.utc
    )

    if expiration <= now:

        return False

    return current_level >= required_level


# =========================================
# ПОЛУЧИТЬ АКТИВНЫЙ ТАРИФ
# =========================================

def get_active_plan(user_id):

    subscription = get_subscription(user_id)

    plan = subscription.get(
        "plan",
        "free",
    )

    if plan not in SUBSCRIPTION_PLANS:

        return "free"

    if plan == "free":

        return "free"

    if not has_active_subscription(user_id):

        return "free"

    return plan


# =========================================
# ЛИМИТЫ ПОЛЬЗОВАТЕЛЯ
# =========================================

def get_plan_limits(user_id):

    plan = get_active_plan(user_id)

    plan_info = SUBSCRIPTION_PLANS.get(
        plan,
        SUBSCRIPTION_PLANS["free"],
    )

    return {
        "plan": plan,
        "searches_per_month": plan_info.get(
            "searches_per_month",
            5,
        ),
        "max_trackers": plan_info.get(
            "max_trackers",
            0,
        ),
    }


# =========================================
# USAGE — ПОЛУЧИТЬ СЧЁТЧИК
# =========================================

def get_usage_counter(user_id):
    """
    Читает счётчик пользователя.
    НЕ сбрасывает — сброс делает consume_search.
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            user_id,
            period_key,
            searches_used,
            updated_at
        FROM usage_counters
        WHERE user_id = ?
        """,
        (
            user_id,
        ),
    )

    row = cursor.fetchone()

    if not row:
        current_period = get_current_period()

        cursor.execute(
            """
            INSERT INTO usage_counters (
                user_id,
                period_key,
                searches_used,
                updated_at
            )
            VALUES (?, ?, 0, ?)
            """,
            (
                user_id,
                current_period,
                utc_now_iso(),
            ),
        )

        connection.commit()
        connection.close()

        return {
            "user_id": user_id,
            "period_key": current_period,
            "searches_used": 0,
            "updated_at": utc_now_iso(),
        }

    result = dict(row)

    connection.close()

    return result


# =========================================
# USAGE — СКОЛЬКО ПОИСКОВ ИСПОЛЬЗОВАНО
# =========================================

def get_searches_used(user_id):

    usage = get_usage_counter(user_id)

    return int(
        usage.get(
            "searches_used",
            0,
        )
    )


def reset_usage_counter(user_id):
    """
    Сбрасывает счётчик поисков пользователя в 0
    в текущем периоде.
    """

    current_period = get_current_period()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO usage_counters (
            user_id,
            period_key,
            searches_used,
            updated_at
        )
        VALUES (?, ?, 0, ?)
        """,
        (
            user_id,
            current_period,
            utc_now_iso(),
        ),
    )

    cursor.execute(
        """
        UPDATE usage_counters
        SET
            searches_used = 0,
            period_key = ?,
            updated_at = ?
        WHERE user_id = ?
        """,
        (
            current_period,
            utc_now_iso(),
            user_id,
        ),
    )

    connection.commit()
    connection.close()


# =========================================
# USAGE — ЛИМИТ ПОИСКОВ
# =========================================

def get_search_limit(user_id):

    limits = get_plan_limits(user_id)

    return int(
        limits.get(
            "searches_per_month",
            5,
        )
    )


# =========================================
# USAGE — МОЖНО ЛИ ИСКАТЬ
# =========================================

def can_use_search(user_id):

    used = get_searches_used(user_id)

    limit = get_search_limit(user_id)

    return used < limit


# =========================================
# USAGE — ИСПОЛЬЗОВАТЬ ПОИСК
# =========================================

def consume_search(user_id, plan=None, period_key=None):
    """
    Списывает один поиск.

    plan и period_key передаются из services/subscriptions.
    Проверка лимита — только в subscriptions.can_search().
    """

    if plan is None:
        plan = "free"

    if period_key is None:
        period_key = get_current_period(plan)

    connection = get_connection()
    cursor = connection.cursor()

    # 1. Если запись есть и period_key другой —
    #    сбрасываем счётчик.
    cursor.execute(
        """
        UPDATE usage_counters
        SET
            period_key = ?,
            searches_used = 0,
            updated_at = ?
        WHERE user_id = ?
        AND period_key != ?
        """,
        (
            period_key,
            utc_now_iso(),
            user_id,
            period_key,
        ),
    )

    # 2. Если записи нет — создаём.
    cursor.execute(
        """
        INSERT OR IGNORE INTO usage_counters (
            user_id,
            period_key,
            searches_used,
            updated_at
        )
        VALUES (?, ?, 0, ?)
        """,
        (
            user_id,
            period_key,
            utc_now_iso(),
        ),
    )

    # 3. Инкремент.
    cursor.execute(
        """
        UPDATE usage_counters
        SET
            searches_used = searches_used + 1,
            updated_at = ?
        WHERE user_id = ?
        """,
        (
            utc_now_iso(),
            user_id,
        ),
    )

    connection.commit()
    connection.close()

    return True


# =========================================
# USAGE — ИНФОРМАЦИЯ
# =========================================

def get_usage_info(user_id):

    used = get_searches_used(user_id)

    limit = get_search_limit(user_id)

    return {
        "used": used,
        "limit": limit,
        "remaining": max(
            0,
            limit - used,
        ),
        "period": get_current_period(),
    }


# =========================================
# НАСТРОЙКИ
# =========================================

def ensure_user_settings(user_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO user_settings (
            user_id,
            currency,
            country,
            condition
        )
        VALUES (?, 'UAH', 'UA', 'new')
        """,
        (
            user_id,
        ),
    )

    connection.commit()

    connection.close()


# =========================================
# ПОЛУЧИТЬ НАСТРОЙКИ
# =========================================

def get_settings(user_id):

    ensure_user_settings(user_id)

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            user_id,
            currency,
            country,
            condition,
            language
        FROM user_settings
        WHERE user_id = ?
        """,
        (
            user_id,
        ),
    )

    row = cursor.fetchone()

    connection.close()

    if not row:

        return {
            "user_id": user_id,
            "currency": "UAH",
            "country": "UA",
            "condition": "new",
             "language": "en",
        }

    return dict(row)

# =========================================
# ЯЗЫК ПОЛЬЗОВАТЕЛЯ
# =========================================

def get_user_language(user_id):
    """
    Возвращает язык пользователя.
    Если не задан — 'en' (по умолчанию).
    """

    ensure_user_settings(user_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT language
        FROM user_settings
        WHERE user_id = ?
        """,
        (user_id,),
    )

    row = cursor.fetchone()

    connection.close()

    if not row:
        return "en"

    lang = row["language"]

    if lang not in ("en", "uk"):
        return "en"

    return lang


def set_user_language(user_id, lang):
    """
    Устанавливает язык пользователя.
    """

    if lang not in ("en", "uk"):
        return False

    ensure_user_settings(user_id)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE user_settings
        SET language = ?
        WHERE user_id = ?
        """,
        (lang, user_id),
    )

    connection.commit()
    connection.close()

    return True


# =========================================
# ИЗМЕНИТЬ НАСТРОЙКУ
# =========================================

def set_setting(
    user_id,
    field,
    value,
):

    allowed_fields = {
        "currency",
        "country",
        "condition",
    }

    if field not in allowed_fields:

        raise ValueError(
            f"Недопустимая настройка: {field}"
        )

    ensure_user_settings(user_id)

    connection = get_connection()

    cursor = connection.cursor()

    query = f"""
        UPDATE user_settings
        SET {field} = ?
        WHERE user_id = ?
    """

    cursor.execute(
        query,
        (
            value,
            user_id,
        ),
    )

    connection.commit()

    connection.close()


# =========================================
# СБРОС НАСТРОЕК
# =========================================

def reset_settings(user_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO user_settings (
            user_id,
            currency,
            country,
            condition,
            language
        )
        VALUES (?, 'UAH', 'UA', 'new', 'en')
        """,
        (
            user_id,
        ),
    )

    connection.commit()

    connection.close()


# =========================================
# ИСТОРИЯ ПОИСКОВ
# =========================================

def save_search_history(
    user_id,
    product,
    requirements,
    min_price,
    max_price,
    currency,
    country,
    condition,
    ai_data=None,
):

    connection = get_connection()

    cursor = connection.cursor()

    ai_json = (
        json.dumps(
            ai_data,
            ensure_ascii=False,
        )
        if ai_data
        else None
    )

    cursor.execute(
        """
        INSERT INTO search_history (
            user_id,
            product,
            requirements,
            min_price,
            max_price,
            currency,
            country,
            condition,
            ai_data
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            product,
            requirements,
            min_price,
            max_price,
            currency,
            country,
            condition,
            ai_json,
        ),
    )

    connection.commit()

    history_id = cursor.lastrowid

    connection.close()

    cleanup_search_history(user_id)

    return history_id


# =========================================
# ОЧИСТКА ИСТОРИИ ПОИСКОВ
# =========================================

def cleanup_search_history(user_id):
    """
    Оставляет N последних записей истории.

    N зависит от тарифа:
        Free  — 5
        Pro   — 50
        Ultra — без лимита
    """

    from services.subscriptions import (
        get_history_limit,
    )

    limit = get_history_limit(user_id)

    if limit is None:
        return

    if limit <= 0:
        limit = 5

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM search_history
        WHERE user_id = ?
        AND id NOT IN (
            SELECT id
            FROM search_history
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        )
        """,
        (user_id, user_id, limit),
    )

    connection.commit()
    connection.close()


# =========================================
# ПОЛУЧИТЬ ИСТОРИЮ
# =========================================

def get_search_history(
    user_id,
    limit=10,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM search_history
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (
            user_id,
            limit,
        ),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================
# ПОЛУЧИТЬ ОДИН ПОИСК
# =========================================

def get_search_history_item(
    history_id,
    user_id,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM search_history
        WHERE id = ?
        AND user_id = ?
        """,
        (
            history_id,
            user_id,
        ),
    )

    row = cursor.fetchone()

    connection.close()

    if not row:

        return None

    return dict(row)


# =========================================
# ИЗБРАННОЕ
# =========================================

def add_favorite(
    user_id,
    product,
):
    """
    Добавляет товар в избранное.

    Проверяет лимит избранного для тарифа.
    Возвращает:
        favorite_id — добавлено
        None        — лимит достигнут
    """

    from services.subscriptions import (
        get_favorites_limit,
    )

    url = product.get("url", "")

    if url:

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM favorites
            WHERE user_id = ?
            AND url = ?
            LIMIT 1
            """,
            (user_id, url),
        )

        row = cursor.fetchone()

        connection.close()

        if row:
            return int(row["id"])

    limit = get_favorites_limit(user_id)

    if limit is not None:

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM favorites
            WHERE user_id = ?
            """,
            (user_id,),
        )

        row = cursor.fetchone()

        connection.close()

        current = int(row["count"]) if row else 0

        if current >= limit:
            return None

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO favorites (
            user_id,
            title,
            store,
            price,
            currency,
            old_price,
            url,
            picture
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            str(product.get("title", "Без названия")),
            product.get("store", ""),
            normalize_number(product.get("price")),
            product.get("currency", "UAH"),
            normalize_number(product.get("old_price")),
            product.get("url", ""),
            product.get("picture", ""),
        ),
    )

    connection.commit()

    favorite_id = cursor.lastrowid

    connection.close()

    return favorite_id


# =========================================
# УДАЛИТЬ ИЗ ИЗБРАННОГО
# =========================================

def remove_favorite(
    user_id,
    favorite_id=None,
    url=None,
):

    connection = get_connection()

    cursor = connection.cursor()

    if favorite_id is not None:

        cursor.execute(
            """
            DELETE FROM favorites
            WHERE id = ?
            AND user_id = ?
            """,
            (
                favorite_id,
                user_id,
            ),
        )

    elif url:

        cursor.execute(
            """
            DELETE FROM favorites
            WHERE url = ?
            AND user_id = ?
            """,
            (
                url,
                user_id,
            ),
        )

    else:

        connection.close()

        return False

    connection.commit()

    deleted = (
        cursor.rowcount > 0
    )

    connection.close()

    return deleted


# =========================================
# ПОЛУЧИТЬ ИЗБРАННОЕ
# =========================================

def get_favorites(
    user_id,
    limit=50,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM favorites
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (
            user_id,
            limit,
        ),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


def count_favorites(user_id):
    """
    Количество товаров в избранном.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM favorites
        WHERE user_id = ?
        """,
        (user_id,),
    )

    row = cursor.fetchone()

    connection.close()

    return int(row["count"]) if row else 0


def count_search_history(user_id):
    """
    Количество записей в истории поисков.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM search_history
        WHERE user_id = ?
        """,
        (user_id,),
    )

    row = cursor.fetchone()

    connection.close()

    return int(row["count"]) if row else 0


# =========================================
# ПОЛУЧИТЬ ОДИН FAVORITE
# =========================================

def get_favorite(
    user_id,
    favorite_id,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM favorites
        WHERE id = ?
        AND user_id = ?
        """,
        (
            favorite_id,
            user_id,
        ),
    )

    row = cursor.fetchone()

    connection.close()

    if not row:

        return None

    return dict(row)


# =========================================
# ПРОВЕРКА ИЗБРАННОГО
# =========================================

def is_favorite(
    user_id,
    url,
):

    if not url:

        return False

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM favorites
        WHERE user_id = ?
        AND url = ?
        LIMIT 1
        """,
        (
            user_id,
            url,
        ),
    )

    row = cursor.fetchone()

    connection.close()

    return row is not None


# =========================================
# УДАЛИТЬ ВСЁ ИЗ ИЗБРАННОГО
# =========================================

def remove_all_favorites(user_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM favorites
        WHERE user_id = ?
        """,
        (
            user_id,
        ),
    )

    connection.commit()

    deleted = cursor.rowcount

    connection.close()

    return deleted


# =========================================
# КАНДИДАТЫ ДЛЯ ИЗБРАННОГО
# =========================================

def save_favorite_candidate(
    user_id,
    product,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO favorite_candidates (
            user_id,
            title,
            store,
            price,
            currency,
            old_price,
            url,
            picture
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            str(
                product.get(
                    "title",
                    "Без названия",
                )
            ),
            product.get(
                "store",
                "",
            ),
            normalize_number(
                product.get("price")
            ),
            product.get(
                "currency",
                "UAH",
            ),
            normalize_number(
                product.get("old_price")
            ),
            product.get(
                "url",
                "",
            ),
            product.get(
                "picture",
                "",
            ),
        ),
    )

    connection.commit()

    candidate_id = cursor.lastrowid

    connection.close()

    return candidate_id


# =========================================
# ПОЛУЧИТЬ КАНДИДАТА
# =========================================

def get_favorite_candidate(
    user_id,
    candidate_id,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM favorite_candidates
        WHERE id = ?
        AND user_id = ?
        """,
        (
            candidate_id,
            user_id,
        ),
    )

    row = cursor.fetchone()

    connection.close()

    if not row:

        return None

    return dict(row)


# =========================================
# ОТСЛЕЖИВАНИЕ ЦЕН
# =========================================

def count_active_trackers(user_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM price_trackers
        WHERE user_id = ?
        AND active = 1
        """,
        (
            user_id,
        ),
    )

    row = cursor.fetchone()

    connection.close()

    return int(row["count"])


# =========================================
# ПОЛУЧИТЬ ЛИМИТ ТРЕКЕРОВ
# =========================================

def get_tracker_limit(user_id):

    plan = get_active_plan(user_id)

    plan_info = SUBSCRIPTION_PLANS.get(
        plan,
        SUBSCRIPTION_PLANS["free"],
    )

    return int(
        plan_info.get(
            "max_trackers",
            0,
        )
    )


# =========================================
# МОЖНО ЛИ ДОБАВИТЬ ТРЕКЕР
# =========================================

def can_add_tracker(user_id):

    limit = get_tracker_limit(user_id)

    if limit <= 0:

        return False

    current = count_active_trackers(user_id)

    return current < limit


# =========================================
# ДОБАВИТЬ ТРЕКЕР
# =========================================

def add_price_tracker(
    user_id,
    title,
    store,
    url,
    currency,
    current_price,
    target_price,
    product_query=None,
    condition="any",
    picture=None,
):

    if not url:

        return None

    connection = get_connection()

    cursor = connection.cursor()

    now = utc_now_iso()

    try:

        cursor.execute(
            """
            INSERT INTO price_trackers (
                user_id,
                title,
                store,
                url,
                currency,
                current_price,
                previous_price,
                target_price,
                product_query,
                condition,
                picture,
                last_checked_at,
                active,
                target_notified,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
            """,
            (
                user_id,
                str(title or "Без названия"),
                str(store or ""),
                url,
                currency or "UAH",
                normalize_number(current_price),
                None,
                normalize_number(target_price),
                product_query,
                condition or "any",
                picture or "",
                now,
                now,
            ),
        )

        tracker_id = cursor.lastrowid

        initial_price = normalize_number(
            current_price
        )

        if initial_price is not None:

            cursor.execute(
                """
                INSERT INTO price_history (
                    tracker_id,
                    price,
                    recorded_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    tracker_id,
                    initial_price,
                    now,
                ),
            )

        connection.commit()

    except sqlite3.IntegrityError:

        connection.rollback()

        cursor.execute(
            """
            SELECT id
            FROM price_trackers
            WHERE user_id = ?
            AND url = ?
            LIMIT 1
            """,
            (
                user_id,
                url,
            ),
        )

        row = cursor.fetchone()

        connection.close()

        if row:

            return int(row["id"])

        return None

    connection.close()

    return tracker_id


# =========================================
# ПОЛУЧИТЬ ТРЕКЕР
# =========================================

def get_price_tracker(
    user_id,
    tracker_id,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM price_trackers
        WHERE id = ?
        AND user_id = ?
        """,
        (
            tracker_id,
            user_id,
        ),
    )

    row = cursor.fetchone()

    connection.close()

    if not row:

        return None

    return dict(row)


# =========================================
# ПОЛУЧИТЬ ТРЕКЕРЫ ПОЛЬЗОВАТЕЛЯ
# =========================================

def get_price_trackers(
    user_id,
    active_only=True,
):

    connection = get_connection()

    cursor = connection.cursor()

    if active_only:

        cursor.execute(
            """
            SELECT *
            FROM price_trackers
            WHERE user_id = ?
            AND active = 1
            ORDER BY created_at DESC, id DESC
            """,
            (
                user_id,
            ),
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM price_trackers
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (
                user_id,
            ),
        )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================
# ПОЛУЧИТЬ ВСЕ АКТИВНЫЕ ТРЕКЕРЫ
# =========================================

def get_all_active_price_trackers():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM price_trackers
        WHERE active = 1
        ORDER BY last_checked_at ASC
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================
# УДАЛИТЬ ТРЕКЕР
# =========================================

def remove_price_tracker(
    user_id,
    tracker_id,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM price_trackers
        WHERE id = ?
        AND user_id = ?
        """,
        (
            tracker_id,
            user_id,
        ),
    )

    connection.commit()

    deleted = cursor.rowcount > 0

    connection.close()

    return deleted


# =========================================
# ВКЛЮЧИТЬ / ВЫКЛЮЧИТЬ ТРЕКЕР
# =========================================

def set_price_tracker_active(
    user_id,
    tracker_id,
    active,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE price_trackers
        SET active = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            1 if active else 0,
            tracker_id,
            user_id,
        ),
    )

    connection.commit()

    updated = cursor.rowcount > 0

    connection.close()

    return updated


# =========================================
# ОБНОВИТЬ ЦЕНУ ТРЕКЕРА
# =========================================

def update_price_tracker(
    tracker_id,
    current_price,
    last_checked_at=None,
    target_notified=None,
    last_notified_at=None,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT current_price
        FROM price_trackers
        WHERE id = ?
        """,
        (
            tracker_id,
        ),
    )

    row = cursor.fetchone()

    if not row:

        connection.close()

        return False

    old_price = row["current_price"]

    new_price = normalize_number(
        current_price
    )

    checked_at = (
        last_checked_at
        or utc_now_iso()
    )

    # =====================================
    # Собираем SET-часть динамически
    # =====================================

    set_parts = [
        "previous_price = ?",
        "current_price = ?",
        "last_checked_at = ?",
    ]

    params = [
        old_price,
        new_price,
        checked_at,
    ]

    if target_notified is not None:

        set_parts.append(
            "target_notified = ?"
        )

        params.append(
            1 if target_notified else 0
        )

    if last_notified_at is not None:

        set_parts.append(
            "last_notified_at = ?"
        )

        params.append(
            last_notified_at
        )

    params.append(tracker_id)

    cursor.execute(
        f"""
        UPDATE price_trackers
        SET {", ".join(set_parts)}
        WHERE id = ?
        """,
        tuple(params),
    )

    # =====================================
    # Записываем новую цену в историю
    # =====================================

    if new_price is not None:

        cursor.execute(
            """
            INSERT INTO price_history (
                tracker_id,
                price,
                recorded_at
            )
            VALUES (?, ?, ?)
            """,
            (
                tracker_id,
                new_price,
                checked_at,
            ),
        )

    connection.commit()

    connection.close()

    return True

def get_tracker_notification_info(tracker_id):
    """
    Возвращает время последнего уведомления
    и текущую/предыдущую цену для трекера.

    Используется для антиспама уведомлений.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            last_notified_at,
            current_price,
            previous_price
        FROM price_trackers
        WHERE id = ?
        """,
        (tracker_id,),
    )

    row = cursor.fetchone()

    connection.close()

    if not row:
        return None

    return {
        "last_notified_at": row["last_notified_at"],
        "current_price": row["current_price"],
        "previous_price": row["previous_price"],
    }

# =========================================
# ОБНОВИТЬ TARGET NOTIFIED
# =========================================

def set_tracker_target_notified(
    tracker_id,
    notified,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE price_trackers
        SET target_notified = ?
        WHERE id = ?
        """,
        (
            1 if notified else 0,
            tracker_id,
        ),
    )

    connection.commit()

    updated = cursor.rowcount > 0

    connection.close()

    return updated


# =========================================
# ИСТОРИЯ ЦЕН — ДОБАВИТЬ
# =========================================

def add_price_history(
    tracker_id,
    price,
    recorded_at=None,
):

    normalized_price = normalize_number(
        price
    )

    if normalized_price is None:

        return False

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO price_history (
            tracker_id,
            price,
            recorded_at
        )
        VALUES (?, ?, ?)
        """,
        (
            tracker_id,
            normalized_price,
            recorded_at or utc_now_iso(),
        ),
    )

    connection.commit()

    connection.close()

    return True


# =========================================
# ИСТОРИЯ ЦЕН — ОЧИСТКА ПО ТАРИФУ
# =========================================

def cleanup_price_history(tracker_id, days):
    """
    Удаляет записи истории цены старше N дней.

    days = 0 или None → ничего не удаляем.
    days > 0         → удаляем всё старше (now - days).
    """

    if not days or days <= 0:
        return

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=days)
    ).isoformat()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM price_history
        WHERE tracker_id = ?
        AND recorded_at < ?
        """,
        (tracker_id, cutoff),
    )

    connection.commit()
    connection.close()


# =========================================
# ПОЛУЧИТЬ ИСТОРИЮ ЦЕН
# =========================================

def get_price_history(
    tracker_id,
    limit=50,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            tracker_id,
            price,
            recorded_at
        FROM price_history
        WHERE tracker_id = ?
        ORDER BY recorded_at DESC, id DESC
        LIMIT ?
        """,
        (
            tracker_id,
            limit,
        ),
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]

# =========================================
# РЕФЕРАЛЫ
# =========================================

def add_referral(referrer_id, referred_id):
    """
    Записывает реферал.

    Возвращает True, если запись добавлена.
    Возвращает False, если:
      - referrer_id == referred_id
      - referred_id уже приходил по чьей-то ссылке
    """

    if referrer_id == referred_id:
        return False

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO referrals (referrer_id, referred_id)
            VALUES (?, ?)
            """,
            (referrer_id, referred_id),
        )
        connection.commit()
        added = True

    except sqlite3.IntegrityError:
        # referred_id уже в таблице
        added = False

    connection.close()

    return added


def get_referral_count(user_id):
    """
    Сколько человек пришло по ссылке пользователя.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM referrals
        WHERE referrer_id = ?
        """,
        (user_id,),
    )

    row = cursor.fetchone()
    connection.close()

    return int(row["count"]) if row else 0


def has_referral_bonus(user_id):
    """
    Проверяет, выдан ли уже Pro за 15 приглашённых.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT user_id
        FROM referral_bonuses
        WHERE user_id = ?
        LIMIT 1
        """,
        (user_id,),
    )

    row = cursor.fetchone()
    connection.close()

    return row is not None


def mark_referral_bonus_given(user_id):
    """
    Отмечает, что Pro за 15 приглашённых выдан.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO referral_bonuses (user_id)
        VALUES (?)
        """,
        (user_id,),
    )

    connection.commit()
    connection.close()


def get_referrer(referred_id):
    """
    Возвращает user_id того, кто пригласил.
    Или None.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT referrer_id
        FROM referrals
        WHERE referred_id = ?
        LIMIT 1
        """,
        (referred_id,),
    )

    row = cursor.fetchone()
    connection.close()

    if not row:
        return None

    return int(row["referrer_id"])

# =========================================
# ПОЛУЧИТЬ ПОСЛЕДНЮЮ ЦЕНУ
# =========================================

def get_latest_price(
    tracker_id,
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT price, recorded_at
        FROM price_history
        WHERE tracker_id = ?
        ORDER BY recorded_at DESC, id DESC
        LIMIT 1
        """,
        (
            tracker_id,
        ),
    )

    row = cursor.fetchone()

    connection.close()

    if not row:

        return None

    return dict(row)