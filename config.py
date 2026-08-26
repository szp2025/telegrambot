# --- ИГРОВЫЕ СЛОВАРИ И ДАННЫЕ ПРОЕКТОВ ---

COMBO_GAMES_DATA = {
    
    "doodle-jump": {
        "name": "🟡 Doodle Jump",
        "path": "/doodle-jump/",
        "ref_link_1": "https://t.me/DoodlePlayBot/app?startapp=DJ2FHPOLZ",
        "ref_link_2": "https://t.me/DoodlePlayBot/app?startapp=DJ2FHPOLZ",
        "strategy": """🟡 Стратегия Doodle Jump.
Таблица прокачки:
• Уровень 1 | Стоимость: 99 (99) | Монет в час: 0.21 (5,00%/d)
• Уровень 2 | Стоимость: 108 (207) | Монет в час: 0.43 (5,00%/d)"""
    },
    
    "golden-miner": {
        "name": "⛏️ Golden Miner",
        "path": "/golden-miner/",
        "ref_link_1": "https://t.me/GoldenMinerBot/app?startapp=ref_FD7F4601",
        "ref_link_2": "https://t.me/GoldenMinerBot/app?startapp=ref_FD7F4601",
        "strategy": "⛏️ Стратегия Golden Miner.",
    },
    "grow-tea": {
        "name": "🌿 Grow Tea",
        "path": "/grow-tea/",
        "ref_link_1": "https://t.me/GrowTeaBot/app?startapp=5290309079",
        "ref_link_2": "https://t.me/GrowTeaBot/app?startapp=5290309079",
        "strategy": "🌿 Стратегия Grow Tea.",
    },
    "signal-2193": {
        "name": "📡 Signal 2193",
        "path": "/signal-2193/",
        "ref_link_1": "https://t.me/signal2193bot/app?startapp=ref_FD7F4601",
        "ref_link_2": "https://t.me/signal2193bot/app?startapp=ref_FD7F4601",
        "strategy": "📡 Стратегия Signal 2193.",
    },
    "meme-mining": {
        "name": "🃏 Meme Mining",
        "path": "/meme-mining-3/",
        "ref_link_1": "https://t.me/MiningComboBot",
        "ref_link_2": "https://t.me/MiningComboBot",
        "strategy": "🃏 Стратегия Meme Mining.",
    },
}


PHONE_MINER_ACTIONS = {
    "info_prefix": "pinfo_",
    "play_text": "📥 Play",
    "play_1_text": "🎮  1",
    "play_2_text": "🎮  2"
}

FAUCETS_ACTIONS = {
    "info_prefix": "finfo_",
    "play_1_text": "🎮  1",
    "play_2_text": "🎮  2"
}

FARMS_ACTIONS = {
    "strat_prefix": "farm_strat_",
    "strat_suffix_template": "📋 {name} (Стратегия)",
    "play_1_text": "🎮  1",
    "play_2_text": "🎮  2"
}

TIMER_DURATIONS = [1, 3, 6, 8, 12, 24]  # Список часов для кнопок быстрого выбора

TIMER_ACTIONS = {
    "set_prefix": "settimer_",
    "custom_prefix": "customtimer_",
    "cancel_prefix": "canceltimer_",
    "custom_text": "✏️ Ввести своё время (ч/м)",
    "cancel_text": "❌ Отключить таймер",
    "back_text": "🔙 Назад к списку игр",
    "back_callback": "timers_menu_back"
}


FIAT_CURRENCIES = [
    ("USD ($)", "usd"),
    ("EUR (€)", "eur"),
    ("RUB (₽)", "rub")
]

INDEPENDENT_FARMS_DATA = {
    "jacks-farm": {
        "name": "👨‍🌾 Jack's Farm",
        "ref_link_1": "https://t.me/JacksFarm_bot",
        "ref_link_2": "https://telegram.me/JacksFarm_bot?start=474934",
        "strategy": "👨‍🌾 Стратегия Jack's Farm.",
    },
    "honey-farm": {
        "name": "🍯 Honey Farm",
        "ref_link_1": "https://t.me/Honey_FarmBot?start=14604",
        "ref_link_2": "https://t.me/Honey_FarmBot?start=16420",
        "strategy": "🍯 Стратегия Honey Farm.",
    },
    "birds-empire": {
        "name": "🦅 Bird's Empire",
        "ref_link_1": "https://t.me/BirdsEmpireBot?start=2093638",
        "ref_link_2": "https://t.me/BirdsEmpireBot?start=2093853",
        "strategy": "🦅 Стратегия Bird's Empire.",
    },
}

PHONE_MINERS_DATA = {
    "cloudmine": {
        "name": "⚡ Cloud Mine Crypto",
        "ref_link_1": "https://cloudminecrypto.com/?invite_code=d7OmYqvR4G4q5nz2",
        "ref_link_2": "https://cloudminecrypto.com/?invite_code=d7OmYqvR4G4q5nz2",
        "play_market": "https://cloudminecrypto.com/?invite_code=d7OmYqvR4G4q5nz2",
        "code": "d7OmYqvR4G4q5nz2",
        "description": "📈 Майнинг.",
    },
    "hashflow": {
        "name": "⚡ Hashflow",
        "ref_link_1": "https://hashflow.cc/?ref=8621",
        "ref_link_2": "https://hashflow.cc/?ref=8621",
        "play_market": "https://hashflow.cc/?ref=8621",
        "code": "8621",
        "description": "🌐 Децентрализованная платформа.",
    },
     "gomining": {
        "name": "⚡ gomining",
        "ref_link_1": "https://gomining.com/fr",
        "ref_link_2": "https://gomining.com/fr",
        "play_market": "https://gomining.com/fr",
        "code": "d7OmYqvR4G4q5nz2",
        "description": "📈 Майнинг.",
    },
}

CRYPTO_FAUCETS_DATA = {
 "firefaucet": {
        "name": "🔥 Fire Faucet",
        "ref_link_1": "https://firefaucet.win/ref/661552",  # Ваша ссылка
        "ref_link_2": "https://firefaucet.win/ref/1371528",  # Ссылка подруги
        "description": "🎁 Авто-кран.",
    },
    "btcadspace": {
        "name": "🌐 BTC AdSpace",
        "ref_link_1": "https://btcadspace.com/ref/cherylsy",
        "ref_link_2": "https://btcadspace.com/ref/cherylsy",
        "description": "💼 Просмотр рекламы и заработок BTC.",
    },
    "toniabux": {
        "name": "💵 ToniaBux",
        "ref_link_1": "https://toniabux.com/i/20087",
        "ref_link_2": "https://toniabux.com/i/20087",
        "description": "💰 Рекламный букс.",
    },
    "bestchange": {
        "name": "🔄 BestChange Monitor",
        "ref_link_1": "https://www.bestchange.ru/?p=1JhfNK3GoewmeyruTC1k1KjbC6mtC9CHCA",
        "ref_link_2": "https://www.bestchange.ru/?p=1JhfNK3GoewmeyruTC1k1KjbC6mtC9CHCA",
        "description": "💱 Мониторинг обменников.",
    },
    "free-litecoin": {
        "name": "🪙 Free Litecoin",
        "ref_link_1": "https://free-litecoin.com/login?referer=6504067",
        "ref_link_2": "https://free-litecoin.com/login?referer=6504067",
        "description": "⚡ Кран Litecoin.",
    },
    "referzone": {
        "name": "🎯 ReferZone",
        "ref_link_1": "https://referzone.ru/?ref=15122",
        "ref_link_2": "https://referzone.ru/?ref=15122",
        "description": "🚀 Реферальная платформа.",
    },
    "viefaucet": {
        "name": "💧 VieFaucet",
        "ref_link_1": "https://viefaucet.com?r=6750fdd8e3c023610a9224dc",
        "ref_link_2": "https://viefaucet.com?r=6750fdd8e3c023610a9224dc",
        "description": "💦 Мультивалютный кран.",
    },
    "cointiply": {
        "name": "💎 Cointiply",
        "ref_link_1": "https://cointiply.mobi/n51w3E",
        "ref_link_2": "https://cointiply.mobi/n51w3E",
        "description": "⭐ Популярный крипто-кран.",
    },
}


LOG_COLORS = {
    "INFO": "\033[92m",  # Зеленый
    "WARNING": "\033[93m",  # Желтый
    "ERROR": "\033[91m",  # Красный
    "RESET": "\033[0m",
}

# --- НАСТРОЙКИ СИСТЕМЫ БЕЗОПАСНОСТИ ---

NETWORK_CORE_BLACKLIST = [
    # Финансовые пирамиды, удвоители и сомнительные инвестиции
    "free ton",
    "doubler",
    "x2 crypto",
    "1day profit",
    "invest 10 get",
    
    # Дрейнеры, фальшивые клеймы и фишинг кошельков
    "drainer",
    "connect wallet to claim",
    "airdrop-connect",
    "fast-withdraw-bot",
    "t.me/fake",
    "wallet-rectify",
    "sync-wallet",
    "verify-metamask",
    "claim-rewards",

    # Дополнительные маркеры для полного покрытия (рекомендуется для максимума)
    "validate-wallet",
    "migration-portal",
    "token-distribution",
    "airdrop-claim",
    "rectify-account",
    "fix-wallet-error",
    "manual-sync"
]


GHOST_MODE_DOMAINS = [
    # Подозрительные и дешевые доменные зоны, традиционно используемые для быстрого фишинга
    ".xyz", ".cc", ".top", ".bi", ".cfd", ".info", ".lat", ".pw", 
    ".gq", ".ml", ".tk", ".work", ".click", ".loan", ".date", ".win", ".bid",
    ".stream", ".trade", ".download", ".review", ".party", ".science", ".men",
    ".biz", ".pro", ".kim", ".loan", ".racing", ".ube", ".mom", ".quest",

    # Вредоносные префиксы и ключевые слова для маскировки под сервисы и кошельки
    "free-", "bonus-", "airdrop-", "drain-", "phish", "connect-", "fix-",
    "secure-", "login-", "verify-", "update-", "account-", "wallet-", "support-",
    "auth-", "portal-", "service-", "confirm-", "banking-", "help-", "admin-",

    # Дополнительные технические маркеры перехвата и дрейна средств
    "mint-", "claim-", "drop-", "reward-", "gift-", "auth-fix-", "web3-",
    "swap-", "bridge-", "validate-", "sec-", "guard-",

    # Расширенный блок Web3-скама и обхода авторизации (добавлено для максимума)
    "permit-", "setapproval-", "safe-", "claim-reward", "multicall-",
    "2fa-", "otp-", "recovery-", "reset-", "unban-", "appeal-"
]


SCAM_USERNAME_MARKERS = [
    # Техподдержка и администрация
    "support", "admin", "help", "manager", "security", "tech", "official_sup",
    "helpdesk", "service", "customer_care", "support_desk", "adm", "administrator",
    "moderator", "mod", "system", "sysadmin", "staff", "help_bot", "service_bot",
    
    # Финансовые сервисы, банки и кошельки (актуально для стратегии защиты)
    "wallet", "wallet_fix", "pay", "payment", "bank", "secure", "verification",
    "account", "account_fix", "recovery", "restore", "kyc", "aml", "compliance",
    "caf_support", "caf_aide", "ursa", "finance", "billing", "treasury",
    
    # Криптовалюта, аирдропы и раздачи (главные векторы спама)
    "airdrop", "airdrop_bot", "giveaway", "crypto", "token", "nft", "binance",
    "telegram", "tg_support", "bonus", "gift", "promo", "p2p", "exchange"
]


SCAM_PATTERNS = [
    # Кража сид-фраз и приватных ключей
    r"seed[-_\s]*phrase", r"сид[-_\s]*фраз", r"private[-_\s]*key", 
    r"приватн[ых|ой]\s*ключ", r"mnemonic", r"мнемоник", r"secret[-_\s]*key",
    r"секретн\w*\s*ключ", r"backup[-_\s]*phrase", r"резервн\w*\s*фраз",

    # Верификация кошельков, аккаунтов и учетных записей
    r"wallet[-_\s]*verif", r"вериф[икация|уйте]\s*кошел", r"account[-_\s]*verify",
    r"подтверд[ите|уй]\s*аккаунт", r"sync[-_\s]*wallet", r"синхрониз[ируйте|ация]",
    r"connect[-_\s]*wallet", r"подключ[ите|уй]\s*кошел", r"validate[-_\s]*wallet",

    # Аирдропы, токены, бесплатные деньги и скам-раздачи
    r"airdrops?", r"бесплатн\w*\s*токен\w*", r"free[-_\s]*crypto", r"claim[-_\s]*reward",
    r"забер[ите|уй]\s*наград", r"giveaway[-_\s]*win", r"выигр\w*\s*приз",
    r"бонус[-_\s]*от\s*систем", r"раздач\w*\s*фонд",

    # Социальная инженерия, срочность и фишинговые ссылки
    r"клищ\s*по\sссылк", r"перейди\s*по\sссылк", r"срочн\w*\s*обновлен",
    r"заблокиров\w*\s*счет", r"block[-_\s]*account", r"suspicious[-_\s]*activity",
    r"подозрительн\w*\s*активност", r"требуетк\s*вмешательств",

    # Маскировка под государственные выплаты или соцпомощь (под банковский гамбит)
    r"caf[-_\s]* выплаты", r"компенсац\w*\s*счет", r"посол[ьств|е]\s*помощ"
]


PHISHING_DOMAINS = [
    # Популярные сокращатели ссылок (часто используются для сокрытия реального адреса)
    "bit.ly", "t.ly", "cutt.ly", "tinyurl.com", "goo.gl", "ow.ly", "buff.ly", 
    "adf.ly", "shorte.st", "bl.ink", "rebrand.ly", "is.gd", "v.gd", "qr.ae", 
    "lnkd.in", "db.tt", "qr.net", "1url.com", "cli.gs", "yfrog.com", "migre.me", 
    "ff.im", "su.pr", "twit.ac", "su.pr", "twurl.nl", "snipurl.com", "to.ly", 
    "bit.do", "coinurl.com", "trib.al", "short.revive-adserver.com", "linktr.ee",
    "beacons.ai", "hoo.be", "taplink.cc", "campsite.bio",

    # IP-логгеры и трекеры (сервисы скрытого сбора IP-адресов, геолокации и устройств)
    "grabify.link", "iplogger.org", "iplogger.com", "iplogger.ru", "2ip.ru", 
    "yip.su", "blasze.com", "psndeals.com", "steamcommunity.com.link", 
    "imgur.la", "imagetour.ru", "ip-api.com", "ipinfo.io", "anonym.to", 
    "dereferer.me", "ulx.me", "topster.me", "ezgif.com.link", "blasze.org",
    "geekprank.com", "free-ip-logger.com", "eert.me", "Is.gd",

    # Дополнительные подозрительные зоны и маскировочные домены
    "telegra.ph", # Часто используется для анонимного фишинга (хотя легитимен)
    "web.app", "firebaseapp.com", "github.io", "gitlab.io", # Бесплатные хостинги для фишинговых страниц
    "1drv.ms", "dropbox.com", "drive.google.com" # Легитимные облака, часто абузимые под фейк-логин формы
]


BOT_COMMANDS = [
    ("start", "Главное меню и проверка"),
    ("profile", "👤 Личный профиль и статы игр"),
    ("all_combo", "Проверить комбо-карты"),
    ("miners", "📱 Телефонные майнеры"),
    ("faucets", "🚰 Крипто-краны"),
    ("calc", "Крипто-конвертер"),
    ("farm", "Статус защищенной фермы"),
    ("timers", "⏰ Персональные таймеры сбора"),
    ("reviews", "💬 Отзывы пользователей"),
    ("ads", "📢 Реклама и монетизация"),
    ("proofs", "Скрины выплат")
]


MAIN_MENU_BUTTONS = [
    "🚀 Меню комбо-игр", "👤 Профиль и статы",
    "📱 Телефонные майнеры", "🚰 Крипто-краны",
    "🌾 Авто-фермы (без комбо)", "⚡ Проверить все комбо",
    "🧮 Крипто-курс", "📊 Защита фермы",
    "⏰ Мои таймеры", "💬 Отзывы",
    "📢 Реклама и монетизация", "💎 Скрины выплат"
]

BOT_COMMANDS = [
    'calc', 'farm', 'timers', 'proofs', 
    'all_combo', 'miners', 'faucets', 
    'profile', 'reviews', 'ads'
]

WELCOME_MESSAGES = {
    "zero_lag": "⚡ **Бот работает в режиме Zero-Lag!**",
    "main_menu": "👇 Главное меню:"
}

DANGEROUS_INJECTION_PATTERNS = [
    # === Выполнение кода и обход песочницы Python (Sandbox Escapes) ===
    "eval(", "exec(", "compile(", "__import__", "getattr(", "setattr(", "delattr(",
    "globals(", "locals(", "vars(", "input(", "breakpoint(",
    
    # === Магические атрибуты и рефлексия ===
    "__subclasses__", "__bases__", "__mro__", "__globals__", "__code__",
    "__builtins__", "__init__", "__class__", "__dict__", "__closure__",
    
    # === Опасные модули и системные вызовы ОС ===
    "import os", "import sys", "import subprocess", "import pty", "import socket",
    "import ctypes", "import pickle", "import marshal", "import urllib", "import http",
    "import requests", "subprocess", "os.system", "os.popen", "os.spawn", "os.exec",
    "shutil.rmtree", "pty.spawn", "ctypes.CDLL", "rm -rf", "sh",
    
    # === SQL-инъекции ===
    ";--", "DROP TABLE", "DROP DATABASE", "UNION SELECT", "UNION ALL SELECT",
    "OR 1=1", "OR '1'='1", "EXEC xp_", "INFORMATION_SCHEMA", "SLEEP(", "BENCHMARK(",
    "SELECT FROM",
    
    # === XSS / Web-инъекции ===
    "<script>", "javascript:", "onerror=", "onload="
]


PROFILE_KEYBOARD_DATA = [
    [("➕ Добавить / Обновить игру", "prof_add")],
    [("📋 Посмотреть мои статы", "prof_view")]
]

REVIEWS_KEYBOARD_DATA = [
    [("✍️ Оставить отзыв", "review_add")],
    [("📖 Читать отзывы", "review_read")]
]

ADS_KEYBOARD_DATA = [
    [("💰 Купить рекламу", "ads_buy")],
    [("📊 Статистика аудитории", "ads_stats")]
]

ADS_TARIFFS_DATA = [
    [("⏱ Закреп на 24 часа — $15", "adtariff_24h")],
    [("📢 Рассылка по всей базе — $30", "adtariff_broadcast")],
    [("🔙 Назад", "ads_menu_back")]
]

CRYPTO_COINS_DATA = [
    ("💵 USDT (TRC20)", "usdt"),
    ("💎 GRAM / TON", "gram"),
    ("🪙 Bitcoin (BTC)", "btc"),
    ("⚡ Tron (TRX)", "tron")
]

CRYPTO_CURRENCY_DATA = [
    ("🪙 BTC", "cur_btc"),
    ("🪙 ETH", "cur_eth"),
    ("🪙 USDT", "cur_usdt"),
    ("🪙 GRAM", "cur_gram")
]


# config.py

SINGLE_GAME_ACTIONS = {
    "combo": ("🎯 Открыть комбо", "game_"),
    "tactics": ("🧠 Тактика", "strat_"),
    "play_1": ("🎮 1",),
    "play_2": ("🎮 2",),
    "back": ("🔙 Назад к списку", "combopage_")
}


# --- ПУТИ К ФАЙЛАМ ДАННЫХ ---
VERIFIED_FILE = "verified_users.txt"
ACTIVE_ADS_FILE = "active_ads.txt"
