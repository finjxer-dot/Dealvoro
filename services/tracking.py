import asyncio
from typing import Optional

from database import (
    get_price_tracker,
    get_price_trackers,
    get_all_active_price_trackers,
    add_price_tracker,
    remove_price_tracker,
    count_active_trackers,
    update_price_tracker,
    add_price_history,
    get_price_history,
)

from services.search import search_products


# =========================================
# ДОБАВЛЕНИЕ ОТСЛЕЖИВАНИЯ
# =========================================

def create_tracker(
    user_id: int,
    title: str,
    store: str,
    price: float,
    currency: str,
    target_price: float,
    url: str,
    picture: Optional[str] = None,
    product_query: Optional[str] = None,
):
    """
    Создаёт новое отслеживание товара.

    Важно:
    add_price_tracker() в database.py
    САМ пишет первую точку в price_history.
    Повторно вызывать add_price_history НЕ нужно.
    """

    tracker_id = add_price_tracker(
        user_id=user_id,
        title=title,
        store=store,
        url=url,
        currency=currency,
        current_price=price,
        target_price=target_price,
        product_query=product_query or title,
        picture=picture,
    )

    return tracker_id


# =========================================
# ПОЛУЧЕНИЕ ОТСЛЕЖИВАНИЙ
# =========================================

def get_user_trackers(
    user_id: int,
):
    """
    Возвращает все активные отслеживания
    пользователя.
    """

    return get_price_trackers(
        user_id=user_id,
        active_only=True,
    )


# =========================================
# КОЛИЧЕСТВО ОТСЛЕЖИВАНИЙ
# =========================================

def get_tracker_count(
    user_id: int,
) -> int:
    """
    Возвращает количество активных
    отслеживаний пользователя.
    """

    return count_active_trackers(
        user_id
    )


# =========================================
# УДАЛЕНИЕ
# =========================================

def delete_tracker(
    user_id: int,
    tracker_id: int,
) -> bool:
    """
    Удаляет отслеживание пользователя.
    """

    tracker = get_price_tracker(
        user_id=user_id,
        tracker_id=tracker_id,
    )

    if not tracker:
        return False

    return remove_price_tracker(
        user_id=user_id,
        tracker_id=tracker_id,
    )


# =========================================
# ПОИСК ТОВАРА ДЛЯ ПРОВЕРКИ
# =========================================

def find_current_product(
    tracker: dict,
):
    """
    Выполняет новый поиск товара
    и пытается найти нужный товар.

    Сначала ищем по URL.

    Если URL немного изменился,
    дополнительно проверяем название.
    """

    product_query = (
        tracker.get("product_query")
        or tracker.get("title")
        or ""
    )

    currency = tracker.get(
        "currency",
        "UAH",
    )

    if not product_query:
        return None

    try:

        results = search_products(
            product_query=product_query,
            min_price=0,
            max_price=None,
            currency=currency,
            country="UA",
            condition="any",
        )

    except Exception as error:

        print(
            f"[TRACKING] Ошибка поиска "
            f"'{product_query}': {error}"
        )

        return None

    if not results:
        return None

    tracker_url = tracker.get(
        "url"
    )

    tracker_title = str(
        tracker.get(
            "title",
            ""
        )
    ).lower().strip()

    # =====================================
    # 1. ИЩЕМ ПО URL
    # =====================================

    if tracker_url:

        for product in results:

            product_url = product.get(
                "url"
            )

            if product_url == tracker_url:
                return product

    # =====================================
    # 2. ИЩЕМ ПО НАЗВАНИЮ
    # =====================================

    if tracker_title:

        for product in results:

            title = str(
                product.get(
                    "title",
                    ""
                )
            ).lower().strip()

            if (
                title == tracker_title
                or tracker_title in title
                or title in tracker_title
            ):
                return product

    # =====================================
    # 3. ЕСЛИ ТОВАР ОДИН
    # =====================================

    if len(results) == 1:
        return results[0]

    return None


# =========================================
# ОБНОВЛЕНИЕ ЦЕНЫ
# =========================================

def update_tracker_price(
    tracker: dict,
    new_price: float,
) -> dict:
    """
    Обновляет цену товара
    и добавляет запись в историю.

    Возвращает:

    {
        "old_price": ...,
        "new_price": ...,
        "changed": True/False,
        "target_reached": True/False
    }
    """

    old_price = tracker.get(
        "current_price"
    )

    target_price_raw = tracker.get(
        "target_price"
    )

    target_price = (
        float(target_price_raw)
        if target_price_raw is not None
        else 0.0
    )

    new_price = float(
        new_price
    )

    old_price_float = (
        float(old_price)
        if old_price is not None
        else None
    )

    changed = (
        old_price_float is None
        or old_price_float != new_price
    )

    # =====================================
    # ДОСТИГНУТА ЦЕЛЕВАЯ ЦЕНА
    # =====================================

    target_reached = (
        target_price > 0
        and new_price <= target_price
    )

    # =====================================
    # ОБНОВЛЯЕМ БАЗУ
    #
    # update_price_tracker() САМ:
    #   - обновит previous_price / current_price
    #   - обновит target_notified (если передать)
    #   - запишет новую точку в price_history
    #
    # Повторно вызывать add_price_history НЕ нужно.
    # =====================================

    update_price_tracker(
        tracker_id=tracker["id"],
        current_price=new_price,
        target_notified=target_reached,
    )

    return {
        "old_price": old_price_float,
        "new_price": new_price,
        "changed": changed,
        "target_reached": target_reached,
    }


# =========================================
# ПРОВЕРКА ОДНОГО ТРЕКЕРА
# =========================================

def check_tracker(
    user_id: int,
    tracker_id: int,
) -> Optional[dict]:
    """
    Проверяет актуальную цену
    одного товара.

    Возвращает информацию
    об изменении цены.
    """

    tracker = get_price_tracker(
        user_id=user_id,
        tracker_id=tracker_id,
    )

    if not tracker:
        return None

    product = find_current_product(
        tracker
    )

    if not product:
        return {
            "success": False,
            "tracker": tracker,
            "message": (
                "Не удалось найти товар "
                "в магазинах."
            ),
        }

    new_price = product.get(
        "price"
    )

    if new_price is None:
        return {
            "success": False,
            "tracker": tracker,
            "message": (
                "У товара не удалось "
                "получить актуальную цену."
            ),
        }

    try:
        new_price = float(
            new_price
        )

    except (
        ValueError,
        TypeError,
    ):

        return {
            "success": False,
            "tracker": tracker,
            "message": (
                "Цена товара имеет "
                "неверный формат."
            ),
        }

    result = update_tracker_price(
        tracker=tracker,
        new_price=new_price,
    )

    return {
        "success": True,
        "tracker": tracker,
        "product": product,
        **result,
    }


# =========================================
# ИСТОРИЯ ЦЕНЫ
# =========================================

def get_tracker_history(
    user_id: int,
    tracker_id: int,
    limit: int = 20,
):
    """
    Возвращает историю изменения цены.
    """

    tracker = get_price_tracker(
        user_id=user_id,
        tracker_id=tracker_id,
    )

    if not tracker:
        return []

    return get_price_history(
        tracker_id=tracker_id,
        limit=limit,
    )


# =========================================
# ФОРМАТИРОВАНИЕ ИЗМЕНЕНИЯ ЦЕНЫ
# =========================================

def format_price_change(
    old_price,
    new_price,
    currency: str = "UAH",
) -> str:
    """
    Формирует красивый текст
    изменения цены.
    """

    symbols = {
        "UAH": "₴",
        "USD": "$",
        "EUR": "€",
    }

    symbol = symbols.get(
        currency,
        currency,
    )

    if old_price is None:
        return (
            f"{symbol}{new_price:,.2f}"
        )

    difference = (
        new_price - old_price
    )

    if difference < 0:

        return (
            f"📉 "
            f"<b>{symbol}{new_price:,.2f}</b>\n"
            f"Было: "
            f"{symbol}{old_price:,.2f}\n"
            f"Изменение: "
            f"<b>-{symbol}{abs(difference):,.2f}</b>"
        )

    if difference > 0:

        return (
            f"📈 "
            f"<b>{symbol}{new_price:,.2f}</b>\n"
            f"Было: "
            f"{symbol}{old_price:,.2f}\n"
            f"Изменение: "
            f"<b>+{symbol}{difference:,.2f}</b>"
        )

    return (
        f"➡️ Цена не изменилась:\n"
        f"<b>{symbol}{new_price:,.2f}</b>"
    )


# =========================================
# ПРОВЕРКА ВСЕХ ТРЕКЕРОВ
# =========================================

async def check_all_trackers(
    bot=None,
):
    """
    Проверяет все активные отслеживания.

    Проверка выполняется в отдельном потоке,
    чтобы синхронный search_products()
    не блокировал Telegram-бота.
    """

    trackers = get_all_active_price_trackers()

    if not trackers:
        return

    print(
        f"[TRACKING] Проверяем "
        f"{len(trackers)} отслеживаний..."
    )

    for tracker in trackers:

        try:

            user_id = tracker.get(
                "user_id"
            )

            tracker_id = tracker.get(
                "id"
            )

            if not user_id or not tracker_id:
                continue

            result = await asyncio.to_thread(
                check_tracker,
                user_id,
                tracker_id,
            )

            if not result:
                continue

            if not result.get(
                "success"
            ):
                continue

            # =================================
            # ЦЕЛЕВАЯ ЦЕНА ДОСТИГНУТА
            # =================================

            if result.get(
                "target_reached"
            ):

                # Уведомление отправляется
                # только если бот передан.

                if bot is not None:

                    title = tracker.get(
                        "title",
                        "Товар",
                    )

                    currency = tracker.get(
                        "currency",
                        "UAH",
                    )

                    new_price = result.get(
                        "new_price"
                    )

                    target_price = tracker.get(
                        "target_price"
                    )

                    symbols = {
                        "UAH": "₴",
                        "USD": "$",
                        "EUR": "€",
                    }

                    symbol = symbols.get(
                        currency,
                        currency,
                    )

                    text = (
                        "🔔 <b>Цена достигла "
                        "вашей цели!</b>\n\n"
                        f"📦 {title}\n\n"
                        f"💰 Сейчас: "
                        f"<b>{symbol}{new_price:,.2f}</b>\n"
                        f"🎯 Цель: "
                        f"<b>{symbol}{target_price:,.2f}</b>"
                    )

                    url = tracker.get(
                        "url"
                    )

                    if url:
                        text += (
                            f"\n\n"
                            f"🛒 <a href=\"{url}\">"
                            f"Открыть товар</a>"
                        )

                    try:

                        await bot.send_message(
                            chat_id=user_id,
                            text=text,
                        )

                    except Exception as error:

                        print(
                            "[TRACKING] "
                            f"Ошибка отправки уведомления "
                            f"{user_id}: {error}"
                        )

        except Exception as error:

            print(
                "[TRACKING] Ошибка проверки "
                f"трекера: {error}"
            )

    print(
        "[TRACKING] Проверка завершена."
    )


# =========================================
# ФОНОВЫЙ ЦИКЛ
# =========================================

async def tracking_loop(
    bot,
    interval: int = 3600,
):
    """
    Постоянный фоновый цикл.

    По умолчанию проверяет цены
    один раз в час.

    interval = 3600 секунд.
    """

    print(
        "[TRACKING] Фоновый мониторинг запущен."
    )

    while True:

        try:

            await check_all_trackers(
                bot=bot
            )

        except asyncio.CancelledError:

            print(
                "[TRACKING] "
                "Фоновый мониторинг остановлен."
            )

            raise

        except Exception as error:

            print(
                "[TRACKING] Ошибка фонового "
                f"цикла: {error}"
            )

        await asyncio.sleep(
            interval
        )