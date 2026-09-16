"""
Локализация Dealvoro.

Поддерживаемые языки:
    uk — украинский
    en — английский (по умолчанию)

Использование:
    from services.i18n import t
    text = t("menu_find", lang="en")
"""


DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "uk")

LANG_NAMES = {
    "en": "🇬🇧 English",
    "uk": "🇺🇦 Українська",
}


# =========================================
# СЛОВАРЬ ПЕРЕВОДОВ
# =========================================

TEXTS = {

    # =====================================
    # ГЛАВНОЕ МЕНЮ
    # =====================================

    "menu_find": {
        "en": "🛒 Find product",
        "uk": "🛒 Знайти товар",
    },
    "menu_my_searches": {
        "en": "📋 My searches",
        "uk": "📋 Мої пошуки",
    },
    "menu_tracking": {
        "en": "🔔 Price tracking",
        "uk": "🔔 Відстеження цін",
    },
    "menu_favorites": {
        "en": "⭐ Favorites",
        "uk": "⭐ Обране",
    },
    "menu_subscription": {
        "en": "💎 Subscription",
        "uk": "💎 Підписка",
    },
    "menu_settings": {
        "en": "⚙️ Settings",
        "uk": "⚙️ Налаштування",
    },

    # =====================================
    # START
    # =====================================

    "start_welcome": {
        "en": (
            "👋 Welcome to Dealvoro!\n\n"
            "🛒 I will help you find the best deals "
            "on Ukrainian marketplaces and shops.\n\n"
            "Choose an action:"
        ),
        "uk": (
            "👋 Вітаю в Dealvoro!\n\n"
            "🛒 Я допоможу знайти вигідні пропозиції "
            "в українських маркетплейсах і магазинах.\n\n"
            "Обери дію:"
        ),
    },

    # =====================================
    # ПОДПИСКА НА КАНАЛ
    # =====================================

    "subscribe_required": {
        "en": (
            "🔒 <b>Please subscribe to our channel</b>\n\n"
            "To use Dealvoro you must subscribe to "
            "<b>@dealvoro_info</b>.\n\n"
            "After subscribing — tap «✅ I subscribed»."
        ),
        "uk": (
            "🔒 <b>Підпишись на наш канал</b>\n\n"
            "Щоб користуватися Dealvoro, "
            "підпишись на <b>@dealvoro_info</b>.\n\n"
            "Після підписки — натисни «✅ Я підписався»."
        ),
    },
    "subscribe_channel_btn": {
        "en": "Subscribe",
        "uk": "Підписатися",
    },
    "subscribe_check_btn": {
        "en": "I subscribed",
        "uk": "Я підписався",
    },
    "subscribe_alert": {
        "en": "Please subscribe first",
        "uk": "Спочатку підпишись",
    },
    "subscribe_error": {
        "en": "Failed to verify. Try again.",
        "uk": "Не вдалося перевірити. Спробуй ще.",
    },
    "subscribe_still_not": {
        "en": "❌ You are still not subscribed.",
        "uk": "❌ Ти ще не підписався.",
    },
    "subscribe_thanks_alert": {
        "en": "✅ Thank you!",
        "uk": "✅ Дякуємо!",
    },

    # =====================================
    # РЕФЕРАЛЫ
    # =====================================

    "settings_btn_referral": {
        "en": "🔗 Invite friends",
        "uk": "🔗 Запросити друзів",
    },
    "referral_info": {
        "en": (
            "🔗 <b>Your invite link</b>\n\n"
            "<code>{link}</code>\n\n"
            "👥 Invited: <b>{count} / {target}</b>\n\n"
            "🎁 Invite <b>{target}</b> friends — "
            "get <b>Pro</b> for <b>{days} days</b> for free!"
        ),
        "uk": (
            "🔗 <b>Твоє запрошувальне посилання</b>\n\n"
            "<code>{link}</code>\n\n"
            "👥 Запрошено: <b>{count} / {target}</b>\n\n"
            "🎁 Запроси <b>{target}</b> друзів — "
            "отримай <b>Pro</b> на <b>{days} днів</b> безкоштовно!"
        ),
    },
    "referral_new_friend": {
        "en": "🎉 New friend joined! Total: <b>{count} / {target}</b>",
        "uk": "🎉 Новий друг приєднався! Всього: <b>{count} / {target}</b>",
    },
    "referral_pro_granted": {
        "en": (
            "🎉 <b>Congratulations!</b>\n\n"
            "You invited <b>15 friends</b>!\n\n"
            "🎁 <b>Pro</b> is now active for <b>{days} days</b>."
        ),
        "uk": (
            "🎉 <b>Вітаємо!</b>\n\n"
            "Ти запросив <b>15 друзів</b>!\n\n"
            "🎁 <b>Pro</b> активовано на <b>{days} днів</b>."
        ),
    },

    # =====================================
    # ПОИСК — ОБЩИЕ
    # =====================================

    "search_what_to_find": {
        "en": (
            "🛒 <b>What do you want to find?</b>\n\n"
            "For example:\n"
            "• iPhone 15\n"
            "• Logitech gaming mouse\n"
            "• 144 Hz monitor\n"
            "• wireless headphones"
        ),
        "uk": (
            "🛒 <b>Що ти хочеш знайти?</b>\n\n"
            "Наприклад:\n"
            "• iPhone 15\n"
            "• ігрова мишка Logitech\n"
            "• монітор 144 Гц\n"
            "• бездротові навушники"
        ),
    },
    "search_min_price": {
        "en": (
            "💰 <b>Minimum price</b>\n\n"
            "Enter the minimum price.\n"
            "If there's no minimum — send <b>0</b>."
        ),
        "uk": (
            "💰 <b>Мінімальна ціна</b>\n\n"
            "Введи мінімальну ціну.\n"
            "Якщо мінімальної ціни немає — надішли <b>0</b>."
        ),
    },
    "search_max_price": {
        "en": (
            "💰 <b>Maximum price</b>\n\n"
            "Enter the maximum price."
        ),
        "uk": (
            "💰 <b>Максимальна ціна</b>\n\n"
            "Введи максимальну ціну."
        ),
    },
    "search_requirements": {
        "en": (
            "📝 <b>Any additional requirements?</b>\n\n"
            "For example:\n"
            "• warranty only\n"
            "• wireless mouse\n"
            "• seller rating 4.8+\n"
            "• original only\n\n"
            "If no requirements — send <b>no</b>."
        ),
        "uk": (
            "📝 <b>Є додаткові вимоги?</b>\n\n"
            "Наприклад:\n"
            "• тільки з гарантією\n"
            "• бездротова мишка\n"
            "• продавець від 4.8 ⭐\n"
            "• тільки оригінал\n\n"
            "Якщо вимог немає — надішли <b>ні</b>."
        ),
    },
    "search_analyzing": {
        "en": "🧠 <b>Analyzing request...</b>",
        "uk": "🧠 <b>Аналізую запит...</b>",
    },
    "search_searching": {
        "en": (
            "🔎 <b>Searching for matching offers...</b>\n\n"
            "⏳ Checking products by your parameters."
        ),
        "uk": (
            "🔎 <b>Шукаю відповідні пропозиції...</b>\n\n"
            "⏳ Перевіряю товари за твоїми параметрами."
        ),
    },
    "search_not_found": {
        "en": (
            "😔 <b>Nothing found.</b>\n\n"
            "Try changing parameters.\n\n"
            "🔎 Searches left: <b>{remaining}</b>"
        ),
        "uk": (
            "😔 <b>Нічого не знайдено.</b>\n\n"
            "Спробуй змінити параметри.\n\n"
            "🔎 Залишилось пошуків: <b>{remaining}</b>"
        ),
    },
    "search_found_count": {
        "en": (
            "🔎 <b>Found offers: {count}</b>\n\n"
            "Showing top {shown}.\n"
            "📊 Searches left: <b>{remaining}</b>"
        ),
        "uk": (
            "🔎 <b>Знайдено пропозицій: {count}</b>\n\n"
            "Показую найкращі {shown}.\n"
            "📊 Залишилось пошуків: <b>{remaining}</b>"
        ),
    },
    "search_done": {
        "en": (
            "✅ <b>Search completed.</b>\n\n"
            "You can start a new search or pick "
            "another Dealvoro section."
        ),
        "uk": (
            "✅ <b>Пошук завершено.</b>\n\n"
            "Можеш виконати новий пошук або обрати "
            "інший розділ Dealvoro."
        ),
    },
    "search_limit_reached": {
        "en": (
            "🔒 <b>Search limit reached.</b>\n\n"
            "Used: <b>{used} / {limit}</b>\n\n"
            "Choose Pro or Ultra to get more searches."
        ),
        "uk": (
            "🔒 <b>Ліміт пошуків вичерпано.</b>\n\n"
            "Використано: <b>{used} / {limit}</b>\n\n"
            "Обери Pro або Ultra, щоб отримати більше пошуків."
        ),
    },
    "search_limit_reached_today": {
        "en": (
            "🔒 <b>Today's limit reached. "
            "Come back tomorrow.</b>\n\n"
            "Used: <b>{used} / {limit}</b>\n\n"
            "Choose Pro or Ultra to get more searches."
        ),
        "uk": (
            "🔒 <b>Ліміт на сьогодні вичерпано. "
            "Повертайся завтра.</b>\n\n"
            "Використано: <b>{used} / {limit}</b>\n\n"
            "Обери Pro або Ultra, щоб отримати більше пошуків."
        ),
    },
    "search_limit_already_used": {
        "en": "🔒 Search limit already reached.",
        "uk": "🔒 Ліміт пошуків вже вичерпано.",
    },

    # =====================================
    # ВАЛЮТА И СТРАНА
    # =====================================

    "search_currency_prompt": {
        "en": "🇺🇦 <b>Choose search country</b>",
        "uk": "🇺🇦 <b>Обери країну пошуку</b>",
    },
    "search_condition_prompt": {
        "en": "📦 <b>What condition do you need?</b>",
        "uk": "📦 <b>Який стан товару тобі потрібен?</b>",
    },

    # =====================================
    # СОСТОЯНИЕ ТОВАРА
    # =====================================

    "condition_new": {
        "en": "🆕 New",
        "uk": "🆕 Новий",
    },
    "condition_used": {
        "en": "♻️ Used",
        "uk": "♻️ Вживаний",
    },
    "condition_any": {
        "en": "📦 Any",
        "uk": "📦 Будь-який",
    },
    "condition_unknown": {
        "en": "Not specified",
        "uk": "Не вказано",
    },

    # =====================================
    # ОШИБКИ ВВОДА
    # =====================================

    "error_text_only": {
        "en": "❌ Please send text.",
        "uk": "❌ Надішли текст.",
    },
    "error_product_too_short": {
        "en": "❌ Query is too short.",
        "uk": "❌ Запит занадто короткий.",
    },
    "error_query_invalid": {
        "en": (
            "❌ <b>Invalid query.</b>\n\n"
            "This type of request is not supported by Dealvoro."
        ),
        "uk": (
            "❌ <b>Некоректний запит.</b>\n\n"
            "Цей тип запитів не підтримується Dealvoro."
        ),
    },
    "error_number_only": {
        "en": (
            "❌ Please enter a number.\n\n"
            "For example: <code>500</code>"
        ),
        "uk": (
            "❌ Введи число.\n\n"
            "Наприклад: <code>500</code>"
        ),
    },
    "error_max_less_min": {
        "en": "❌ Max price cannot be less than min price.",
        "uk": "❌ Максимальна ціна не може бути меншою за мінімальну.",
    },
    "error_ai_failed": {
        "en": (
            "❌ <b>Failed to analyze the request.</b>"
        ),
        "uk": (
            "❌ <b>Не вдалося проаналізувати запит.</b>"
        ),
    },
    "error_search_failed": {
        "en": (
            "❌ <b>An error occurred during search.</b>"
        ),
        "uk": (
            "❌ <b>Сталася помилка під час пошуку.</b>"
        ),
    },
    "error_choose_button": {
        "en": "❌ Please use the buttons below.",
        "uk": "❌ Будь ласка, скористайся кнопками нижче.",
    },
    "error_choose_button_currency": {
        "en": "❌ Please choose the currency using a button.",
        "uk": "❌ Будь ласка, обери валюту кнопкою.",
    },
    "error_choose_button_country": {
        "en": "❌ Please choose the country using a button.",
        "uk": "❌ Будь ласка, обери країну кнопкою.",
    },

    # =====================================
    # КАРТОЧКА ТОВАРА
    # =====================================

    "product_price": {
        "en": "💰 Price: <b>{price} {symbol}</b>",
        "uk": "💰 Ціна: <b>{price} {symbol}</b>",
    },
    "product_store": {
        "en": "🏪 Store: <b>{store}</b>",
        "uk": "🏪 Магазин: <b>{store}</b>",
    },
    "product_seller_rating": {
        "en": "⭐ Seller rating: <b>{rating}</b>",
        "uk": "⭐ Рейтинг продавця: <b>{rating}</b>",
    },
    "product_reviews": {
        "en": "👥 Reviews: <b>{reviews}</b>",
        "uk": "👥 Відгуків: <b>{reviews}</b>",
    },
    "product_condition": {
        "en": "📦 Condition: <b>{condition}</b>",
        "uk": "📦 Стан: <b>{condition}</b>",
    },
    "product_match": {
        "en": "🎯 Match: <b>{score}</b>",
        "uk": "🎯 Збіг: <b>{score}</b>",
    },
    "product_deal_score": {
        "en": "🔥 Deal Score: <b>{score}/100</b>",
        "uk": "🔥 Deal Score: <b>{score}/100</b>",
    },
    "product_no_data": {
        "en": "No data",
        "uk": "Немає даних",
    },
    "product_untitled": {
        "en": "Untitled",
        "uk": "Без назви",
    },
    "product_unknown_store": {
        "en": "Unknown store",
        "uk": "Невідомий магазин",
    },

    # =====================================
    # КНОПКИ ТОВАРА
    # =====================================

    "btn_open_product": {
        "en": "🛒 Open product",
        "uk": "🛒 Відкрити товар",
    },
    "btn_track_price": {
        "en": "🔔 Track price",
        "uk": "🔔 Відстежувати ціну",
    },
    "btn_add_favorite": {
        "en": "⭐ Add to favorites",
        "uk": "⭐ В обране",
    },
    "btn_remove_favorite": {
        "en": "★ Remove from favorites",
        "uk": "★ Прибрати з обраного",
    },

    # =====================================
    # ИЗБРАННОЕ
    # =====================================

    "favorites_title": {
        "en": "⭐ <b>Favorites</b>",
        "uk": "⭐ <b>Обране</b>",
    },
    "favorites_empty": {
        "en": "You haven't added any products yet.",
        "uk": "Ти ще не додав жодного товару.",
    },
    "favorites_limit_empty": {
        "en": "Limit: <b>0 / {limit}</b>",
        "uk": "Ліміт: <b>0 / {limit}</b>",
    },
    "favorites_unlimited": {
        "en": "Limit: <b>unlimited</b>",
        "uk": "Ліміт: <b>без обмежень</b>",
    },
    "favorites_saved": {
        "en": "Saved: <b>{count} / {limit}</b>",
        "uk": "Збережено: <b>{count} / {limit}</b>",
    },
    "favorites_saved_unlimited": {
        "en": "Saved: <b>{count}</b> (unlimited)",
        "uk": "Збережено: <b>{count}</b> (без обмежень)",
    },
    "favorites_added": {
        "en": "⭐ Added to favorites!",
        "uk": "⭐ Додано в обране!",
    },
    "favorites_removed": {
        "en": "🗑 Removed from favorites.",
        "uk": "🗑 Прибрано з обраного.",
    },
    "favorites_already_removed": {
        "en": "Product is no longer in favorites.",
        "uk": "Товар вже не в обраному.",
    },
    "favorites_limit_reached": {
        "en": (
            "🔒 Favorites limit: {limit}. "
            "Upgrade to Pro or Ultra to save more."
        ),
        "uk": (
            "🔒 Ліміт обраного: {limit}. "
            "Оформи Pro або Ultra, щоб зберігати більше."
        ),
    },
    "favorites_add_error": {
        "en": "❌ Failed to add product.",
        "uk": "❌ Не вдалося додати товар.",
    },
    "favorites_product_unavailable": {
        "en": "❌ Product is no longer available.",
        "uk": "❌ Товар більше недоступний.",
    },

    # =====================================
    # МОИ ПОИСКИ
    # =====================================

    "history_title": {
        "en": "📋 <b>My searches</b>",
        "uk": "📋 <b>Мої пошуки</b>",
    },
    "history_empty": {
        "en": "History is empty.",
        "uk": "Історія поки порожня.",
    },
    "history_last": {
        "en": "📋 <b>Recent searches</b>",
        "uk": "📋 <b>Останні пошуки</b>",
    },
    "history_no_requirements": {
        "en": "no requirements",
        "uk": "без вимог",
    },
    "history_from": {
        "en": "from {min} {currency}",
        "uk": "від {min} {currency}",
    },
    "history_repeat": {
        "en": "🔄 Repeat search",
        "uk": "🔄 Повторити пошук",
    },
    "history_search_not_found": {
        "en": "❌ Search not found.",
        "uk": "❌ Пошук не знайдено.",
    },
    "history_repeating": {
        "en": "🔎 <b>Repeating search...</b>",
        "uk": "🔎 <b>Повторюю пошук...</b>",
    },
    "history_repeat_failed": {
        "en": "❌ Failed to repeat search.",
        "uk": "❌ Не вдалося повторити пошук.",
    },
    "history_found": {
        "en": "🔎 <b>Found: {count}</b>\n\nShowing top {shown}.\n📊 Searches left: <b>{remaining}</b>",
        "uk": "🔎 <b>Знайдено: {count}</b>\n\nПоказую найкращі {shown}.\n📊 Залишилось пошуків: <b>{remaining}</b>",
    },
    "history_nothing_found": {
        "en": "😔 Nothing found with these parameters.",
        "uk": "😔 За цими параметрами нічого не знайдено.",
    },

    # =====================================
    # ПОДПИСКА
    # =====================================

    "subscription_title": {
        "en": "💎 <b>Dealvoro Subscription</b>",
        "uk": "💎 <b>Підписка Dealvoro</b>",
    },
    "subscription_current_free": {
        "en": "🟢 Current plan: <b>Free</b>.",
        "uk": "🟢 Поточний тариф: <b>Free</b>.",
    },
    "subscription_current_paid": {
        "en": "🟢 Current plan: <b>{name}</b>.",
        "uk": "🟢 Поточний тариф: <b>{name}</b>.",
    },
    "subscription_current_paid_until": {
        "en": "🟢 Current plan: <b>{name}</b>.\n📅 Valid until: <b>{date}</b> UTC",
        "uk": "🟢 Поточний тариф: <b>{name}</b>.\n📅 Діє до: <b>{date}</b> UTC",
    },
    "subscription_usage_title": {
        "en": "📊 <b>Usage</b>",
        "uk": "📊 <b>Використання</b>",
    },
    "subscription_searches": {
        "en": "🔎 Searches {period}: <b>{used} / {limit}</b>",
        "uk": "🔎 Пошуки {period}: <b>{used} / {limit}</b>",
    },
    "subscription_tracking": {
        "en": "🔔 Tracking: <b>{used} / {limit}</b>",
        "uk": "🔔 Відстеження: <b>{used} / {limit}</b>",
    },
    "subscription_tracking_na": {
        "en": "🔔 Tracking: <b>not available</b>",
        "uk": "🔔 Відстеження: <b>недоступно</b>",
    },
    "subscription_favorites": {
        "en": "⭐ Favorites: <b>{used} / {limit}</b>",
        "uk": "⭐ Обране: <b>{used} / {limit}</b>",
    },
    "subscription_favorites_unlimited": {
        "en": "⭐ Favorites: <b>{used} / ∞</b>",
        "uk": "⭐ Обране: <b>{used} / ∞</b>",
    },
    "subscription_history": {
        "en": "📋 Search history: <b>{used} / {limit}</b>",
        "uk": "📋 Історія пошуків: <b>{used} / {limit}</b>",
    },
    "subscription_history_unlimited": {
        "en": "📋 Search history: <b>{used} / ∞</b>",
        "uk": "📋 Історія пошуків: <b>{used} / ∞</b>",
    },
    "subscription_choose": {
        "en": "👇 <b>Choose a plan:</b>",
        "uk": "👇 <b>Обери тариф:</b>",
    },
    "subscription_period_month": {
        "en": "this month",
        "uk": "цього місяця",
    },
    "subscription_period_day": {
        "en": "today",
        "uk": "сьогодні",
    },
    "subscription_plan_details": {
        "en": (
            "💎 <b>{name}</b>\n\n"
            "💰 Price: <b>{stars} Stars</b>\n"
            "📅 Duration: <b>{days} days</b>\n"
            "🔎 Searches: <b>{searches}</b>\n"
            "🔔 Trackers: <b>{trackers}</b>\n\n"
            "👇 Choose an action:"
        ),
        "uk": (
            "💎 <b>{name}</b>\n\n"
            "💰 Вартість: <b>{stars} Stars</b>\n"
            "📅 Тривалість: <b>{days} днів</b>\n"
            "🔎 Пошуків: <b>{searches}</b>\n"
            "🔔 Трекерів: <b>{trackers}</b>\n\n"
            "👇 Обери дію:"
        ),
    },
    "subscription_searches_per_month": {
        "en": "{n} searches/month",
        "uk": "{n} пошуків/місяць",
    },
    "subscription_searches_per_day": {
        "en": "{n} searches/day",
        "uk": "{n} пошуків/день",
    },
    "subscription_btn_back": {
        "en": "⬅️ Back",
        "uk": "⬅️ Назад",
    },
    "subscription_btn_buy": {
        "en": "💳 Buy for {stars} Stars",
        "uk": "💳 Купити за {stars} Stars",
    },
    "subscription_payment_success": {
        "en": (
            "🎉 <b>Payment received!</b>\n\n"
            "Plan <b>{name}</b> activated for <b>30 days</b>.\n\n"
            "💎 Thank you for supporting Dealvoro!"
        ),
        "uk": (
            "🎉 <b>Оплату отримано!</b>\n\n"
            "Тариф <b>{name}</b> активовано на <b>30 днів</b>.\n\n"
            "💎 Дякуємо за підтримку Dealvoro!"
        ),
    },
    "subscription_activation_failed": {
        "en": (
            "❌ Payment received, but failed to activate "
            "the subscription. Please contact support."
        ),
        "uk": (
            "❌ Оплату отримано, але не вдалося активувати "
            "підписку. Звернись до підтримки."
        ),
    },
    "subscription_invoice_title": {
        "en": "Dealvoro {name}",
        "uk": "Dealvoro {name}",
    },
    "subscription_invoice_description": {
        "en": "Subscription {name} for {days} days. Full access to Dealvoro features.",
        "uk": "Підписка {name} на {days} днів. Повний доступ до функцій Dealvoro.",
    },
    "subscription_invoice_label": {
        "en": "{name} ({days} days)",
        "uk": "{name} ({days} днів)",
    },
    "subscription_invoice_opening": {
        "en": "💳 Opening invoice for {stars} Stars",
        "uk": "💳 Відкриваю рахунок на {stars} Stars",
    },
    "subscription_invoice_failed": {
        "en": "❌ Failed to create invoice. Try later.",
        "uk": "❌ Не вдалося створити рахунок. Спробуй пізніше.",
    },
    "subscription_unknown_plan": {
        "en": "❌ Unknown plan.",
        "uk": "❌ Невідомий тариф.",
    },
    "subscription_plan_not_found": {
        "en": "❌ Plan not found.",
        "uk": "❌ Тариф не знайдено.",
    },

    # =====================================
    # ОТСЛЕЖИВАНИЕ ЦЕН
    # =====================================

    "tracking_title": {
        "en": "🔔 <b>Price tracking</b>",
        "uk": "🔔 <b>Відстеження цін</b>",
    },
    "tracking_locked": {
        "en": (
            "🔒 <b>Price tracking</b>\n\n"
            "This feature is available on "
            "<b>Pro</b> and <b>Ultra</b> plans.\n\n"
            "Add products for tracking directly "
            "from search results."
        ),
        "uk": (
            "🔒 <b>Відстеження цін</b>\n\n"
            "Функція доступна на тарифах "
            "<b>Pro</b> і <b>Ultra</b>.\n\n"
            "Додавай товари у відстеження прямо "
            "з результатів пошуку."
        ),
    },
    "tracking_connect_pro": {
        "en": "⭐ Connect Pro",
        "uk": "⭐ Підключити Pro",
    },
    "tracking_connect_ultra": {
        "en": "👑 Connect Ultra",
        "uk": "👑 Підключити Ultra",
    },
    "tracking_no_trackers": {
        "en": (
            "🔔 <b>Price tracking</b>\n\n"
            "You have no tracked products yet.\n\n"
            "Do a search and tap "
            "«🔔 Track price» on the product you need."
        ),
        "uk": (
            "🔔 <b>Відстеження цін</b>\n\n"
            "У тебе поки немає відстежуваних товарів.\n\n"
            "Виконай пошук і натисни "
            "«🔔 Відстежувати ціну» на потрібному товарі."
        ),
    },
    "tracking_your_trackers": {
        "en": "🔔 <b>Your tracked products</b>",
        "uk": "🔔 <b>Твої відстежувані товари</b>",
    },
    "tracking_used": {
        "en": "Used: <b>{used} / {limit}</b>",
        "uk": "Використано: <b>{used} / {limit}</b>",
    },
    "tracking_already_tracked": {
        "en": "🔔 This product is already tracked.",
        "uk": "🔔 Цей товар вже відстежується.",
    },
    "tracking_limit_reached": {
        "en": (
            "Tracker limit: {current}/{limit}. "
            "Upgrade to Ultra for a bigger limit."
        ),
        "uk": (
            "Ліміт трекерів: {current}/{limit}. "
            "Оформи Ultra для більшого ліміту."
        ),
    },
    "tracking_not_available": {
        "en": "🔒 Tracking available on Pro and higher.",
        "uk": "🔒 Відстеження доступне з Pro.",
    },
    "tracking_setup_title": {
        "en": "🔔 <b>Tracking setup</b>",
        "uk": "🔔 <b>Налаштування відстеження</b>",
    },
    "tracking_product_label": {
        "en": "Product: <b>{title}</b>",
        "uk": "Товар: <b>{title}</b>",
    },
    "tracking_current_price": {
        "en": "Current price: <b>{price} {symbol}</b>",
        "uk": "Поточна ціна: <b>{price} {symbol}</b>",
    },
    "tracking_target_prompt": {
        "en": (
            "🎯 Send the price at which "
            "I should notify you.\n\n"
            "For example: <code>3000</code>"
        ),
        "uk": (
            "🎯 Надішли ціну, при досягненні якої "
            "я повинен повідомити тебе.\n\n"
            "Наприклад: <code>3000</code>"
        ),
    },
    "tracking_added_title": {
        "en": "✅ <b>Tracking enabled!</b>",
        "uk": "✅ <b>Відстеження увімкнено!</b>",
    },
    "tracking_added_note": {
        "en": "🔔 Now Dealvoro will track the price of this product.",
        "uk": "🔔 Тепер Dealvoro відстежуватиме ціну цього товару.",
    },
    "tracking_add_failed": {
        "en": "❌ Failed to add product.",
        "uk": "❌ Не вдалося додати товар.",
    },
    "tracking_limit_reached_plain": {
        "en": "🔒 Tracking limit reached.",
        "uk": "🔒 Ліміт відстеження вичерпано.",
    },
    "tracking_product_lost": {
        "en": "❌ Product data lost. Try adding tracking again.",
        "uk": "❌ Дані товару загублено. Спробуй додати відстеження знову.",
    },
    "tracking_no_price": {
        "en": "❌ Product has no price.",
        "uk": "❌ У товару немає ціни.",
    },
    "tracking_no_url": {
        "en": "❌ Product has no link.",
        "uk": "❌ У товару немає посилання.",
    },
    "tracking_input_positive_price": {
        "en": (
            "❌ Enter a positive price.\n\n"
            "For example: <code>3000</code>"
        ),
        "uk": (
            "❌ Введи додатну ціну.\n\n"
            "Наприклад: <code>3000</code>"
        ),
    },

    # =====================================
    # КАРТОЧКА ТРЕКЕРА
    # =====================================

    "tracker_store": {
        "en": "🏪 Store: <b>{store}</b>",
        "uk": "🏪 Магазин: <b>{store}</b>",
    },
    "tracker_current_price": {
        "en": "💰 Current price: <b>{price} {symbol}</b>",
        "uk": "💰 Поточна ціна: <b>{price} {symbol}</b>",
    },
    "tracker_no_price": {
        "en": "💰 Current price: <b>No data</b>",
        "uk": "💰 Поточна ціна: <b>Немає даних</b>",
    },
    "tracker_target_price": {
        "en": "🎯 Target price: <b>{price} {symbol}</b>",
        "uk": "🎯 Цільова ціна: <b>{price} {symbol}</b>",
    },
    "tracker_last_check": {
        "en": "🕐 Last check: <b>{date}</b>",
        "uk": "🕐 Остання перевірка: <b>{date}</b>",
    },
    "tracker_target_reached_badge": {
        "en": "🎉 <b>Target price reached!</b>",
        "uk": "🎉 <b>Цільова ціна досягнута!</b>",
    },
    "tracker_btn_check": {
        "en": "🔄 Check price",
        "uk": "🔄 Перевірити ціну",
    },
    "tracker_btn_history": {
        "en": "📈 History",
        "uk": "📈 Історія",
    },
    "tracker_btn_delete": {
        "en": "❌ Delete",
        "uk": "❌ Видалити",
    },

    # =====================================
    # ПРОВЕРКА ЦЕНЫ
    # =====================================

    "check_checking": {
        "en": "🔎 Checking price...",
        "uk": "🔎 Перевіряю ціну...",
    },
    "check_failed": {
        "en": "❌ Failed to check price.",
        "uk": "❌ Не вдалося перевірити ціну.",
    },
    "check_not_found": {
        "en": (
            "⚠️ <b>Product not found right now.</b>\n\n"
            "Keeping the previous price unchanged."
        ),
        "uk": (
            "⚠️ <b>Товар зараз не знайдено.</b>\n\n"
            "Залишаю попереднє значення ціни без змін."
        ),
    },
    "check_no_price": {
        "en": "⚠️ Found product has no price.",
        "uk": "⚠️ У знайденого товару немає ціни.",
    },
    "check_updated": {
        "en": "🔄 <b>Price updated</b>",
        "uk": "🔄 <b>Ціну оновлено</b>",
    },
    "check_price_decreased": {
        "en": "📉 Price decreased by <b>{amount} {symbol}</b>",
        "uk": "📉 Ціна знизилась на <b>{amount} {symbol}</b>",
    },
    "check_price_increased": {
        "en": "📈 Price increased by <b>{amount} {symbol}</b>",
        "uk": "📈 Ціна зросла на <b>{amount} {symbol}</b>",
    },
    "check_price_same": {
        "en": "➡️ Price hasn't changed.",
        "uk": "➡️ Ціна не змінилась.",
    },
    "check_first_price": {
        "en": "🆕 First actual price received.",
        "uk": "🆕 Отримано першу актуальну ціну.",
    },
    "check_target_reached": {
        "en": (
            "🎉 <b>Target price reached!</b>\n\n"
            "Product now costs <b>{price} {symbol}</b>.\n"
            "Your target: <b>{target} {symbol}</b>."
        ),
        "uk": (
            "🎉 <b>Цільова ціна досягнута!</b>\n\n"
            "Товар тепер коштує <b>{price} {symbol}</b>.\n"
            "Твоя ціль: <b>{target} {symbol}</b>."
        ),
    },
    "check_tracker_not_found": {
        "en": "❌ Tracker not found.",
        "uk": "❌ Трекер не знайдено.",
    },

    # =====================================
    # ИСТОРИЯ ЦЕН
    # =====================================

    "price_history_title": {
        "en": "📈 <b>Price history</b>",
        "uk": "📈 <b>Історія ціни</b>",
    },
    "price_history_empty": {
        "en": "History is empty.",
        "uk": "Історія поки порожня.",
    },
    "price_history_line": {
        "en": "• <b>{price} {symbol}</b> — {date}",
        "uk": "• <b>{price} {symbol}</b> — {date}",
    },

    # =====================================
    # УВЕДОМЛЕНИЯ (фоновый цикл)
    # =====================================

    "notify_target_reached": {
        "en": (
            "🎉 <b>Target price reached!</b>\n\n"
            "🔹 {title}\n"
            "💰 Now: <b>{price} {symbol}</b>\n"
            "🎯 Target: <b>{target} {symbol}</b>"
        ),
        "uk": (
            "🎉 <b>Цільова ціна досягнута!</b>\n\n"
            "🔹 {title}\n"
            "💰 Зараз: <b>{price} {symbol}</b>\n"
            "🎯 Ціль: <b>{target} {symbol}</b>"
        ),
    },
    "notify_sharp_drop": {
        "en": (
            "🚨 <b>Sharp price drop!</b>\n\n"
            "🔹 {title}\n"
            "📉 Was: <b>{old} {symbol}</b>\n"
            "💰 Now: <b>{new} {symbol}</b>\n"
            "🔥 Discount: <b>-{discount}%</b>"
        ),
        "uk": (
            "🚨 <b>Різке падіння ціни!</b>\n\n"
            "🔹 {title}\n"
            "📉 Було: <b>{old} {symbol}</b>\n"
            "💰 Стало: <b>{new} {symbol}</b>\n"
            "🔥 Знижка: <b>-{discount}%</b>"
        ),
    },
    "notify_drop": {
        "en": (
            "📉 <b>Price dropped!</b>\n\n"
            "🔹 {title}\n"
            "📉 Was: <b>{old} {symbol}</b>\n"
            "💰 Now: <b>{new} {symbol}</b>\n"
            "🔥 Discount: <b>-{discount}%</b>"
        ),
        "uk": (
            "📉 <b>Ціна знизилась!</b>\n\n"
            "🔹 {title}\n"
            "📉 Було: <b>{old} {symbol}</b>\n"
            "💰 Стало: <b>{new} {symbol}</b>\n"
            "🔥 Знижка: <b>-{discount}%</b>"
        ),
    },
    "notify_open_product": {
        "en": "🛒 Open product",
        "uk": "🛒 Відкрити товар",
    },

    # =====================================
    # НАСТРОЙКИ
    # =====================================

    "settings_title": {
        "en": "⚙️ <b>Dealvoro Settings</b>",
        "uk": "⚙️ <b>Налаштування Dealvoro</b>",
    },
    "settings_currency": {
        "en": "💵 Currency: <b>{currency}</b>",
        "uk": "💵 Валюта: <b>{currency}</b>",
    },
    "settings_country": {
        "en": "🌍 Country: <b>{country}</b>",
        "uk": "🌍 Країна: <b>{country}</b>",
    },
    "settings_condition": {
        "en": "📦 Condition: <b>{condition}</b>",
        "uk": "📦 Стан: <b>{condition}</b>",
    },
    "settings_language": {
        "en": "🌐 Language: <b>{name}</b>",
        "uk": "🌐 Мова: <b>{name}</b>",
    },
    "settings_btn_currency": {
        "en": "💵 Currency",
        "uk": "💵 Валюта",
    },
    "settings_btn_condition": {
        "en": "📦 Condition",
        "uk": "📦 Стан",
    },
    "settings_btn_country": {
        "en": "🌍 Country",
        "uk": "🌍 Країна",
    },
    "settings_btn_language": {
        "en": "🌐 Language",
        "uk": "🌐 Мова",
    },
    "settings_btn_reset": {
        "en": "♻️ Reset settings",
        "uk": "♻️ Скинути налаштування",
    },
    "settings_btn_back": {
        "en": "⬅️ Back",
        "uk": "⬅️ Назад",
    },
    "settings_currency_saved": {
        "en": "✅ Currency: {currency}",
        "uk": "✅ Валюта: {currency}",
    },
    "settings_condition_saved": {
        "en": "✅ Condition saved.",
        "uk": "✅ Стан збережено.",
    },
    "settings_country_saved": {
        "en": "🌍 Country: {country}",
        "uk": "🌍 Країна: {country}",
    },
    "settings_reset_done": {
        "en": "♻️ Settings reset.",
        "uk": "♻️ Налаштування скинуто.",
    },
    "settings_invalid_currency": {
        "en": "❌ Invalid currency.",
        "uk": "❌ Некоректна валюта.",
    },
    "settings_invalid_condition": {
        "en": "❌ Invalid condition.",
        "uk": "❌ Некоректний стан.",
    },
    "settings_language_title": {
        "en": "🌐 <b>Choose language</b>",
        "uk": "🌐 <b>Обери мову</b>",
    },
    "settings_language_saved": {
        "en": "✅ Language: {name}",
        "uk": "✅ Мову збережено: {name}",
    },
    "settings_country_name": {
        "en": "🇺🇦 Ukraine",
        "uk": "🇺🇦 Україна",
    },
    "settings_unknown_option": {
        "en": "❌ Unknown option.",
        "uk": "❌ Невідомий параметр.",
    },

    # =====================================
    # ОБЩИЕ ОШИБКИ
    # =====================================

    "error_generic": {
        "en": "❌ An error occurred.",
        "uk": "❌ Сталася помилка.",
    },

        # =====================================
    # АДМИН-КОМАНДЫ
    # =====================================

    "admin_give_usage": {
        "en": (
            "Usage: <code>/give &lt;user_id&gt; &lt;pro|ultra&gt;</code>\n\n"
            "Example: <code>/give 123456789 pro</code>"
        ),
        "uk": (
            "Використання: <code>/give &lt;user_id&gt; &lt;pro|ultra&gt;</code>\n\n"
            "Приклад: <code>/give 123456789 pro</code>"
        ),
    },
    "admin_give_bad_id": {
        "en": "❌ user_id must be a number",
        "uk": "❌ user_id має бути числом",
    },
    "admin_give_bad_plan": {
        "en": "❌ plan must be <b>pro</b> or <b>ultra</b>",
        "uk": "❌ тариф має бути <b>pro</b> або <b>ultra</b>",
    },
    "admin_give_failed": {
        "en": "❌ Failed to activate subscription",
        "uk": "❌ Не вдалося активувати підписку",
    },
    "admin_give_success": {
        "en": "✅ <b>{plan}</b> activated for <code>{user_id}</code> for 30 days",
        "uk": "✅ <b>{plan}</b> активовано для <code>{user_id}</code> на 30 днів",
    },
    "admin_gift_to_user": {
        "en": (
            "🎁 <b>You have been gifted a {plan_name} subscription!</b>\n\n"
            "Activated for <b>30 days</b>.\n\n"
            "💎 Enjoy using Dealvoro!"
        ),
        "uk": (
            "🎁 <b>Вам видано підписку {plan_name}!</b>\n\n"
            "Активовано на <b>30 днів</b>.\n\n"
            "💎 Приємного користування Dealvoro!"
        ),
    },
    "admin_revoke_usage": {
        "en": "Usage: <code>/revoke &lt;user_id&gt;</code>",
        "uk": "Використання: <code>/revoke &lt;user_id&gt;</code>",
    },
    "admin_revoke_failed": {
        "en": "❌ Failed to revoke",
        "uk": "❌ Не вдалося скасувати",
    },
    "admin_revoke_success": {
        "en": "✅ Subscription revoked for <code>{user_id}</code>",
        "uk": "✅ Підписку скасовано для <code>{user_id}</code>",
    },
    "admin_whois_usage": {
        "en": "Usage: <code>/whois &lt;user_id&gt;</code>",
        "uk": "Використання: <code>/whois &lt;user_id&gt;</code>",
    },
    "admin_whois_title": {
        "en": "👤 <b>User</b>: <code>{user_id}</code>",
        "uk": "👤 <b>Користувач</b>: <code>{user_id}</code>",
    },
    "admin_whois_plan": {
        "en": "💎 Plan: <b>{plan_name}</b>",
        "uk": "💎 Тариф: <b>{plan_name}</b>",
    },
    "admin_whois_until": {
        "en": "📅 Until: <b>{date}</b>",
        "uk": "📅 До: <b>{date}</b>",
    },
    "admin_whois_usage_block": {
        "en": (
            "\n📊 <b>Usage</b>\n"
            "🔎 Searches: <b>{searches_used} / {searches_limit}</b>\n"
            "🔔 Trackers: <b>{trackers_used} / {trackers_limit}</b>\n"
            "⭐ Favorites: <b>{favorites_used}</b>\n"
            "📋 History: <b>{history_used}</b>\n"
        ),
        "uk": (
            "\n📊 <b>Використання</b>\n"
            "🔎 Пошуки: <b>{searches_used} / {searches_limit}</b>\n"
            "🔔 Трекери: <b>{trackers_used} / {trackers_limit}</b>\n"
            "⭐ Обране: <b>{favorites_used}</b>\n"
            "📋 Історія: <b>{history_used}</b>\n"
        ),
    },
}


# =========================================
# ФУНКЦИЯ ПЕРЕВОДА
# =========================================

def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """
    Возвращает перевод по ключу.

    Если ключа нет в словаре — возвращает сам ключ
    (это позволяет легко увидеть пропуски).

    Если язык не поддерживается — fallback на en.
    """

    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG

    entry = TEXTS.get(key)

    if not entry:
        # Ключ не найден — вернём сам ключ
        print(f"[i18n] MISSING KEY: {key}")
        return key

    text = entry.get(lang) or entry.get(DEFAULT_LANG) or key

    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError) as error:
            print(f"[i18n] FORMAT ERROR for '{key}': {error}")
            return text

    return text


def get_lang_name(lang: str) -> str:
    """Название языка для отображения."""
    return LANG_NAMES.get(lang, lang)