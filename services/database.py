import json
import sqlite3
from pathlib import Path


# =========================================
# ПУТИ
# =========================================

PROJECT_ROOT = Path(__file__).parent.parent

DATA_DIR = PROJECT_ROOT / "data"

DATABASE_FILE = (
    DATA_DIR / "dealvoro.db"
)

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================
# CONNECTION
# =========================================

def get_connection():
    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = sqlite3.Row

    return connection

def normalize_number(
    value
    ):
    if value is None:
        return None

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


# =========================================
# ИНИЦИАЛИЗАЦИЯ
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

    connection.commit()

    connection.close()


# =========================================
# НАСТРОЙКИ
# =========================================

def ensure_user_settings(
    user_id
):
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


def get_settings(
    user_id
):
    ensure_user_settings(
        user_id
    )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            user_id,
            currency,
            country,
            condition
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
        }

    return dict(row)


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

    ensure_user_settings(
        user_id
    )

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


def reset_settings(
    user_id
):
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO user_settings (
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

    cleanup_search_history(
        user_id
    )

    return history_id


def cleanup_search_history(
    user_id
):
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
            LIMIT 20
        )
        """,
        (
            user_id,
            user_id,
        ),
    )

    connection.commit()

    connection.close()


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
                product.get(
                    "price"
                )
            ),
            product.get(
                "currency",
                "UAH",
            ),
            normalize_number(
                product.get(
                    "old_price"
                )
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

    favorite_id = cursor.lastrowid

    connection.close()

    return favorite_id


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


def remove_all_favorites(
    user_id
):
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
                product.get(
                    "price"
                )
            ),
            product.get(
                "currency",
                "UAH",
            ),
            normalize_number(
                product.get(
                    "old_price"
                )
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