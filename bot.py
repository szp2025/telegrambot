import logging
import io
import random
import time
import threading
import re
import os
import requests
from bs4 import BeautifulSoup
from PIL import Image
import telebot
from telebot import types
from datetime import datetime
from config import ( 
    COMBO_GAMES_DATA,
    CRYPTO_FAUCETS_DATA,
    INDEPENDENT_FARMS_DATA,
    LOG_COLORS,
    GHOST_MODE_DOMAINS,  # <-- Импортируем домены призрачного режима
    NETWORK_CORE_BLACKLIST,  # <-- Импортируем черный список
    SCAM_USERNAME_MARKERS,  # <-- Импортируем маркеры скам-юзернеймов
    PHONE_MINERS_DATA,
    VERIFIED_FILE,
    ACTIVE_ADS_FILE,  # <-- Импортируем путь к файлу рекламы
    SCAM_PATTERNS,
    DANGEROUS_INJECTION_PATTERNS,
    BOT_COMMANDS,
    MAIN_MENU_BUTTONS,
    PHISHING_DOMAINS
)

from private_config import (
    ADMIN_CHAT_ID,
    SAFEPAL_WALLETS,
    TOKEN,
)

logger = logging.getLogger(__name__)

class AdvancedSecurityGuard:
    def __init__(self):
        # 1. Анти-Флуд (Rate Limiting)
        self.flood_storage = {}
        self.flood_limit_count = 5
        self.flood_time_window = 3.0
        
        # 6. Анти-Брутфорс
        self.brute_storage = {}
        
        # 9. Анти-Дубликат (хранилище последних сообщений: {chat_id: (text, timestamp)})
        self.last_messages = {}
        
        # Черный список мошеннических паттернов
        self.scam_patterns = SCAM_PATTERNS        
        # Фишинговые домены
        self.phishing_domains = PHISHING_DOMAINS
        self.injection_patterns = DANGEROUS_INJECTION_PATTERNS

    # 1. Триггер «Анти-Флуд / Rate Limiting»
    def check_flood(self, chat_id: int) -> bool:
        now = time.time()
        if chat_id not in self.flood_storage:
            self.flood_storage[chat_id] = []
        
        self.flood_storage[chat_id] = [t for t in self.flood_storage[chat_id] if now - t < self.flood_time_window]
        self.flood_storage[chat_id].append(now)
        
        if len(self.flood_storage[chat_id]) > self.flood_limit_count:
            return True
        return False

    # 2. Триггер обнаружения фишинговых и вредоносных ссылок
    def detect_phishing(self, text: str) -> bool:
        text_lower = text.lower()
        for domain in self.phishing_domains:
            if domain in text_lower:
                return True
        if re.search(r"https?://[^\s]*[а-яА-ЯёЁ][^\s]*", text):
            return True
        return False

    # 3. Триггер проверки «Инъекций»
    def sanitize_and_check_injection(self, text: str) -> tuple[bool, str]:
        if not text:
            return False, text
        text_lower = text.lower()
        for pattern in self.injection_patterns:
            # Поддерживаем как обычные подстроки, так и регулярные выражения если нужно
            if pattern.lower() in text_lower or re.search(pattern, text, re.IGNORECASE):
                return True, "[BLOCKED_INJECTION_ATTEMPT]"
        return False, text

    # 5. Триггер «Черный список по паттернам мошенничества»
    def detect_scam(self, text: str) -> bool:
        text_lower = text.lower()
        for pattern in self.scam_patterns:
            if re.search(pattern, text_lower):
                return True
        return False

    # 6. Триггер «Анти-Брутфорс / Защита от перебора команд»
    def check_brute_force(self, chat_id: int) -> bool:
        now = time.time()
        if chat_id not in self.brute_storage:
            self.brute_storage[chat_id] = []
            
        self.brute_storage[chat_id] = [t for t in self.brute_storage[chat_id] if now - t < 10.0]
        self.brute_storage[chat_id].append(now)
        
        if len(self.brute_storage[chat_id]) > 8:
            return True
        return False

    # 7. Триггер обнаружения скрытых символов и RTL-атак
    def detect_rtl_spoofing(self, text: str) -> bool:
        rtl_chars = ["\u202e", "\u202a", "\u202b", "\u202d", "\u200b", "\u200e"]
        for char in rtl_chars:
            if char in text:
                return True
        return False

    # 8. Ловушка для сканеров / Honeypot Trigger
    def check_honeypot(self, data_str: str) -> bool:
        if "honeypot_trap_marker" in data_str:
            return True
        return False

    # 9. Триггер «Анти-Дубликат / Защита от повторной отправки»
    def check_duplicate(self, chat_id: int, text: str) -> bool:
        now = time.time()
        if chat_id in self.last_messages:
            last_text, last_time = self.last_messages[chat_id]
            # Если текст идентичен и прошло меньше 1.5 секунд
            if last_text == text and (now - last_time) < 1.5:
                return True
        self.last_messages[chat_id] = (text, now)
        return False

    # 10. Триггер «Детектор тяжелого спама / Лимит размера текста»
    def check_payload_size(self, text: str, max_length: int = 1000) -> bool:
        if len(text) > max_length:
            return True
        return False

    # 11. Триггер «Проверка на пустые сообщения и Null-байты»
    def check_null_bytes_and_empty(self, text: str) -> bool:
        if "\x00" in text:
            return True
        if not text.strip():
            return True
        return False

    # 12. Триггер «Контроль языковых аномалий (Смешивание кириллицы и латиницы в словах)»
    def detect_mixed_charset(self, text: str) -> bool:
        # Ищем слова, где вперемешку идут русские и английские буквы (омоглиф-атака)
        words = text.split()
        for word in words:
            has_cyrillic = bool(re.search(r'[а-яА-ЯёЁ]', word))
            has_latin = bool(re.search(r'[a-zA-Z]', word))
            if has_cyrillic and has_latin:
                return True
        return False

# Инициализируем защитный модуль
sec_guard = AdvancedSecurityGuard()

# --- ЦВЕТНОЕ И ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ДЛЯ TERMUX ---
class TermuxColorFormatter(logging.Formatter):
    def format(self, record):
        log_message = super().format(record)
        color = LOG_COLORS.get(record.levelname, LOG_COLORS["RESET"])
        return f"{color}[🛡️ ZERO-LAG SECURITY CORE] {log_message}{LOG_COLORS['RESET']}"

handler = logging.StreamHandler()
handler.setFormatter(TermuxColorFormatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

bot = telebot.TeleBot(TOKEN, threaded=True)

# --- БЕЗОПАСНАЯ РЕГИСТРАЦИЯ КОМАНД ---
try:
    print("[🛡️ SECURITY CORE] Регистрация команд в Telegram API...")
    
    # Динамическая генерация из импортированного списка BOT_COMMANDS
    commands_list = [types.BotCommand(cmd, desc) for cmd, desc in BOT_COMMANDS]
    
    bot.set_my_commands(commands_list)
    print("[🛡️ SECURITY CORE] Команды успешно зарегистрированы.")
except Exception as e:
    print(f"[⚠️ WARNING] Команды не зарегистрированы (проблема сети/таймаут): {e}")
    print("[🛡️ SECURITY CORE] Бот продолжает запуск в автономном режиме обхода...")
    
# Хранилища данных
user_game_timers = {}
cloud_proofs = []
user_calc_states = {}
advanced_captchas = {} 
user_reviews_storage = [] 
pending_ad_orders = {} 

def load_verified_users():
    users = set()
    if os.path.exists(VERIFIED_FILE):
        try:
            with open(VERIFIED_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.isdigit():
                        users.add(int(line))
        except Exception as e:
            logger.error(f"Ошибка загрузки верифицированных пользователей: {e}")
    return users

def save_verified_user(user_id):
    try:
        verified_users.add(user_id)
        with open(VERIFIED_FILE, "a", encoding="utf-8") as f:
            f.write(f"{user_id}\n")
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователя в файл: {e}")

verified_users = load_verified_users()  
user_game_stats = {}  
user_input_states = {} 

# Управление активной рекламой с сохранением в файл
def load_active_ads():
    ads = {}
    if os.path.exists(ACTIVE_ADS_FILE):
        try:
            with open(ACTIVE_ADS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) >= 3:
                        order_id, user_id, expire_time = parts[0], int(parts[1]), float(parts[2])
                        ads[order_id] = {"user_id": user_id, "expire_time": expire_time}
        except Exception as e:
            logger.error(f"Ошибка загрузки активной рекламы: {e}")
    return ads

def save_active_ads_to_file():
    try:
        with open(ACTIVE_ADS_FILE, "w", encoding="utf-8") as f:
            for oid, data in active_ads_storage.items():
                f.write(f"{oid}|{data['user_id']}|{data['expire_time']}\n")
    except Exception as e:
        logger.error(f"Ошибка сохранения активной рекламы в файл: {e}")

active_ads_storage = load_active_ads()

class UltimateSecurityCore:

    def __init__(self):
        self.network_core_blacklist = NETWORK_CORE_BLACKLIST
        self.ghost_mode_domains = GHOST_MODE_DOMAINS
        self.scam_username_markers = SCAM_USERNAME_MARKERS
        self.dangerous_patterns = DANGEROUS_INJECTION_PATTERNS

    @staticmethod
    def sanitize_input(text: str) -> str:
        if not text:
            return ""           
            

        text_lower = text.lower()
        for pattern in DANGEROUS_INJECTION_PATTERNS:
            if pattern.lower() in text_lower:
                return "[BLOCKED_INJECTION_ATTEMPT]"
        return textt

    def analyze_traffic(self, text: str) -> tuple[bool, str]:
        lower_text = text.lower()
        for keyword in self.network_core_blacklist:
            if keyword in lower_text:
                return True, f"🚨 **Network Core [88] Заблокировал угрозу!**\nОбнаружен запрещенный паттерн: `{keyword}`."
        
        usernames = re.findall(r'@([a-zA-Z0-9_]{5,32})', text)
        for uname in usernames:
            if any(marker in uname.lower() for marker in self.scam_username_markers):
                return True, f"🚨 **Active City Protection [90]:** Обнаружен фишинговый юзернейм `@ {uname}`."

        if "http://" in lower_text or "https://" in lower_text or "t.me/" in lower_text or "@" in lower_text:
            if any(domain in lower_text for domain in self.ghost_mode_domains) or "fake" in lower_text or "scam" in lower_text:
                return True, "🚨 **Active City Protection [90]:** Ссылка или домен заблокированы."

        return False, "✅ **Sterile Channel [95]:** Канал абсолютно чист."

security_core = UltimateSecurityCore()

class MiningComboManager:
    def __init__(self):
        self.base_url = "https://miningcombo.com"
        self.combo_games = COMBO_GAMES_DATA
        self.independent_farms = INDEPENDENT_FARMS_DATA
        self.phone_miners = PHONE_MINERS_DATA
        self.crypto_faucets = CRYPTO_FAUCETS_DATA
        self.found_today = {key: False for key in self.combo_games}

    def reset_daily_status(self):
        for key in self.found_today:
            self.found_today[key] = False

    def fetch_combo(self, game_key: str):
        if game_key not in self.combo_games:
            return None, "Игра не найдена"
        try:
            url = f"{self.base_url}{self.combo_games[game_key]['path']}"
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if res.status_code != 200:
                return None, "Ошибка доступа"
                
            soup = BeautifulSoup(res.text, "html.parser")
            content = soup.find("article") or soup.find("main") or soup
            
            date_text = "Дата не указана"

            
            for p in content.find_all(["p", "span", "div", "time", "strong", "b"]):
                txt = p.get_text(strip=True)
                if ("August" in txt or "July" in txt or "September" in txt or "2026" in txt) and len(txt) < 40:
                    date_text = txt
                    break
            # Затем получаем текущую реальную дату (день, месяц, год)
            now = datetime.now()
            current_day = now.strftime("%d")
            current_month = now.strftime("%B")
            current_year = now.strftime("%Y")
            
            # Проверяем, совпадает ли дата на сайте с сегодняшней
            is_today = current_day in date_text and current_month in date_text
            
            date_status_icon = "📅"
            if not is_today:
                # Если дата отличается, добавляем предупреждение в текст даты
                date_text = f"{date_text} ⚠️ (Рассинхрон с системной датой: {current_day} {current_month})"
                logger.warning(f"⚠️ Внимание для {game_key}: дата на сайте ({date_text}) отличается от текущей системной ({current_day} {current_month} {current_year})!")
                
            is_searching = False
            for p in content.find_all(["p", "div", "span"], limit=5):
                if "searching for" in p.get_text(strip=True).lower():
                    is_searching = True
                    break
                    
            img_url = None
            if not is_searching:
                # Специальный поиск для Doodle Jump или стандартных классов
                if game_key == "doodle-jump":
                    target_img = soup.find("img", {"class": "wp-image-1"}) or soup.find("div", {"class": "entry-content"}).find("img") if soup.find("div", {"class": "entry-content"}) else None
                    if not target_img:
                        # Берем первую подходящую картинку из контента статьи
                        images = content.find_all("img")
                        for img in images:
                            src = img.get("data-lazy-src") or img.get("src") or img.get("data-src")
                            if src and "wp-content/uploads" in src.lower():
                                img_url = src if not src.startswith("/") else f"{self.base_url}{src}"
                                break
                
                if not img_url:
                    target_img = soup.find("img", {"class": "daily-combo-image"}) or soup.find("img", {"alt": "Countdown Image"})
                    if target_img:
                        img_url = target_img.get("data-lazy-src") or target_img.get("src") or target_img.get("data-src")
                
                if not img_url:
                    images = content.find_all("img")
                    valid_images = []
                    for img in images:
                        src = img.get("data-lazy-src") or img.get("src") or img.get("data-src")
                        if src:
                            if src.startswith("/"):
                                src = f"{self.base_url}{src}"
                            src_lower = src.lower()
                            skip_words = ["logo", "icon", "avatar", "cover", "header", "banner"]
                            if "wp-content/uploads" in src_lower and not any(x in src_lower for x in skip_words):
                                valid_images.append(src)
                    if valid_images:
                        img_url = valid_images[0]
                        
            if is_searching:
                return None, date_text
                
            return img_url, date_text
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге {game_key}: {e}")
            
        return None, "Ошибка парсинга"

    def resize_img(self, url: str, game_key: str = ""):
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                img = Image.open(io.BytesIO(res.content))
                max_width = 200 if game_key == "grow-tea" else 600
                if img.width > max_width:
                    w_percent = (max_width / float(img.width))
                    h_size = int(float(img.height) * float(w_percent))
                    img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
                out = io.BytesIO()
                img.convert("RGB").save(out, format="JPEG", quality=85)
                return out.getvalue()
        except Exception as e:
            logger.error(f"Ошибка изменения размера: {e}")
        return None
manager = MiningComboManager()

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # Создаем кнопки из списка в конфиге в один подход
    buttons = [types.KeyboardButton(btn_text) for btn_text in MAIN_MENU_BUTTONS]
    markup.add(*buttons)
    return markup

def get_profile_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text="➕ Добавить / Обновить игру", callback_data="prof_add"))
    keyboard.row(types.InlineKeyboardButton(text="📋 Посмотреть мои статы", callback_data="prof_view"))
    return keyboard

def get_reviews_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="review_add"))
    keyboard.row(types.InlineKeyboardButton(text="📖 Читать отзывы", callback_data="review_read"))
    return keyboard

def get_ads_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text="💰 Купить рекламу", callback_data="ads_buy"))
    keyboard.row(types.InlineKeyboardButton(text="📊 Статистика аудитории", callback_data="ads_stats"))
    return keyboard

def get_ads_tariffs_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text="⏱ Закреп на 24 часа — $15", callback_data="adtariff_24h"))
    keyboard.row(types.InlineKeyboardButton(text="📢 Рассылка по всей базе — $30", callback_data="adtariff_broadcast"))
    keyboard.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="ads_menu_back"))
    return keyboard

def get_safepal_coins_keyboard(tariff_key):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton(text="💵 USDT (TRC20)", callback_data=f"pay_{tariff_key}_usdt"))
    keyboard.row(types.InlineKeyboardButton(text="💎 GRAM / TON", callback_data=f"pay_{tariff_key}_gram"))
    keyboard.row(types.InlineKeyboardButton(text="🪙 Bitcoin (BTC)", callback_data=f"pay_{tariff_key}_btc"))
    keyboard.row(types.InlineKeyboardButton(text="⚡ Tron (TRX)", callback_data=f"pay_{tariff_key}_tron"))
    keyboard.row(types.InlineKeyboardButton(text="🔙 К выбору тарифов", callback_data="ads_buy"))
    return keyboard

def get_combo_list_keyboard(page=0):
    keyboard = types.InlineKeyboardMarkup()
    combo_keys = list(manager.combo_games.keys())
    total_games = len(combo_keys)
    ITEMS_PER_PAGE = 5
    total_pages = (total_games + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    for key in combo_keys[start_idx:end_idx]:
        data = manager.combo_games[key]
        keyboard.row(types.InlineKeyboardButton(text=f"🎮 {data['name']}", callback_data=f"gamemenu_{key}_{page}"))
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"combopage_{page-1}"))
    nav_buttons.append(types.InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"combopage_{page+1}"))
    if nav_buttons:
        keyboard.row(*nav_buttons)
    return keyboard, total_games

def get_single_game_keyboard(key, page):
    data = manager.combo_games[key]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(text="🎯 Открыть комбо", callback_data=f"game_{key}"),
        types.InlineKeyboardButton(text="🧠 Тактика", callback_data=f"strat_{key}")
    )
    keyboard.row(
        types.InlineKeyboardButton(text="🎮 Играть 1", url=data["ref_link_1"]),
        types.InlineKeyboardButton(text="🎮 Играть 2", url=data["ref_link_2"])
    )
    keyboard.row(types.InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"combopage_{page}"))
    return keyboard

def get_phone_miners_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for key, data in manager.phone_miners.items():
        keyboard.row(
            types.InlineKeyboardButton(text=data["name"], callback_data=f"pinfo_{key}"),
            types.InlineKeyboardButton(text="📥 Play", url=data["play_market"])
        )
        keyboard.row(
            types.InlineKeyboardButton(text="🎮 Играть 1", url=data["ref_link_1"]),
            types.InlineKeyboardButton(text="🎮 Играть 2", url=data["ref_link_2"])
        )
    return keyboard

def get_faucets_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for key, data in manager.crypto_faucets.items():
        keyboard.row(types.InlineKeyboardButton(text=data["name"], callback_data=f"finfo_{key}"))
        keyboard.row(
            types.InlineKeyboardButton(text="🎮 Играть 1", url=data["ref_link_1"]),
            types.InlineKeyboardButton(text="🎮 Играть 2", url=data["ref_link_2"])
        )
    return keyboard

def get_farms_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for key, data in manager.independent_farms.items():
        keyboard.row(types.InlineKeyboardButton(text=f"📋 {data['name']} (Стратегия)", callback_data=f"farm_strat_{key}"))
        keyboard.row(
            types.InlineKeyboardButton(text="🎮 Играть 1", url=data["ref_link_1"]),
            types.InlineKeyboardButton(text="🎮 Играть 2", url=data["ref_link_2"])
        )
    return keyboard

def get_timers_games_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    all_games = {}
    all_games.update({k: v["name"] for k, v in manager.combo_games.items()})
    all_games.update({k: v["name"] for k, v in manager.independent_farms.items()})
    for key, name in all_games.items():
        keyboard.row(types.InlineKeyboardButton(text=f"⏰ Таймер: {name}", callback_data=f"timer_game_{key}"))
    return keyboard

def get_timer_duration_keyboard(key):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(text="⏱ 1 час", callback_data=f"settimer_{key}_1"),
        types.InlineKeyboardButton(text="⏱ 3 часа", callback_data=f"settimer_{key}_3"),
        types.InlineKeyboardButton(text="⏱ 6 часов", callback_data=f"settimer_{key}_6")
    )
    keyboard.row(
        types.InlineKeyboardButton(text="⏱ 8 часов", callback_data=f"settimer_{key}_8"),
        types.InlineKeyboardButton(text="⏱ 12 часов", callback_data=f"settimer_{key}_12"),
        types.InlineKeyboardButton(text="⏱ 24 часа", callback_data=f"settimer_{key}_24")
    )
    keyboard.row(types.InlineKeyboardButton(text="✏️ Ввести своё время (ч/м)", callback_data=f"customtimer_{key}"))
    keyboard.row(types.InlineKeyboardButton(text="❌ Отключить таймер", callback_data=f"canceltimer_{key}"))
    keyboard.row(types.InlineKeyboardButton(text="🔙 Назад к списку игр", callback_data="timers_menu_back"))
    return keyboard

def get_crypto_currency_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="🪙 BTC", callback_data="cur_btc"),
        types.InlineKeyboardButton(text="🪙 ETH", callback_data="cur_eth"),
        types.InlineKeyboardButton(text="🪙 USDT", callback_data="cur_usdt"),
        types.InlineKeyboardButton(text="🪙 GRAM", callback_data="cur_gram")
    )
    return keyboard

def get_fiat_currency_keyboard(crypto_symbol):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        types.InlineKeyboardButton(text="USD ($)", callback_data=f"fiat_{crypto_symbol}_usd"),
        types.InlineKeyboardButton(text="EUR (€)", callback_data=f"fiat_{crypto_symbol}_eur"),
        types.InlineKeyboardButton(text="RUB (₽)", callback_data=f"fiat_{crypto_symbol}_rub")
    )
    return keyboard

def send_message_direct(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    try:
        return bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

def send_combo_result(chat_id, info, img_bytes, date_text):
    caption = f"🎯 **{info['name']}**\n📅 `{date_text}`"
    if img_bytes:
        try:
            bot.send_photo(chat_id, photo=img_bytes, caption=caption[:1024], parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            send_message_direct(chat_id, caption, parse_mode="Markdown")
    else:
        full_text = f"🎯 **{info['name']}**\n📅 `{date_text}`\n\n❌ Комбо еще не найдено"
        send_message_direct(chat_id, full_text, parse_mode="Markdown")

def show_user_profile(chat_id):
    try:
        chat_info = bot.get_chat(chat_id)
        user_name = chat_info.first_name or "Игрок"
    except:
        user_name = "Игрок"
    profile_text = f"👤 **Профиль пользователя:** {user_name}\n\n🏆 **Ваш игровой прогресс и статы:**\n"
    if chat_id in user_game_stats and user_game_stats[chat_id]:
        send_message_direct(chat_id, profile_text, parse_mode="Markdown")
        for game, info in user_game_stats[chat_id].items():
            caption = f"🎮 *{game}*\n📊 Стат / Уровень: `{info['stat']}`"
            if info.get("photo"):
                try:
                    bot.send_photo(chat_id, photo=info["photo"], caption=caption, parse_mode="Markdown")
                except:
                    send_message_direct(chat_id, caption, parse_mode="Markdown")
            else:
                send_message_direct(chat_id, caption, parse_mode="Markdown")
        send_message_direct(chat_id, "⚙️ Управление профилем:", reply_markup=get_profile_keyboard())
    else:
        profile_text += "_Список игр пуст. Нажмите кнопку ниже, чтобы добавить свой прогресс и скриншот._"
        send_message_direct(chat_id, profile_text, reply_markup=get_profile_keyboard(), parse_mode="Markdown")

def daily_auto_checker():
    last_reset_day = None
    # Флаг для принудительного запуска проверки сразу при старте бота
    run_check_now = True 

    while True:
        now_time = time.time()
        now_struct = time.localtime(now_time)
        current_day = now_struct.tm_mday
        current_hour = now_struct.tm_hour

        # Сброс статусов в новый день
        if last_reset_day != current_day:
            manager.reset_daily_status()
            last_reset_day = current_day
            run_check_now = True  # Разрешаем внеплановый запуск при смене дня, если нужно

        # Условия запуска проверки: либо сразу при старте (run_check_now), либо наступило 9:00 или позже
        # И проверяем, остались ли игры, по которым сегодня еще не нашли картинку
        has_unfound_games = any(not found for found in manager.found_today.values())

        if (run_check_now or current_hour >= 9) and has_unfound_games:
            logger.info("🛡️ [AUTO-CHECKER] Запуск проверки комбо-картинок...")
            
            for key, info in manager.combo_games.items():
                # Если на сегодня картинка для этой игры уже найдена, пропускаем её
                if manager.found_today.get(key, False):
                    continue

                try:
                    img_url, date_text = manager.fetch_combo(key)
                    if img_url:
                        img_bytes = manager.resize_img(img_url, game_key=key)
                        if img_bytes:
                            # Отмечаем, что на сегодня картинка найдена
                            manager.found_today[key] = True
                            logger.info(f"✅ [AUTO-CHECKER] Картинка для {key} успешно найдена и зафиксирована!")
                            
                            # Отправляем результат администратору (или в чат с админом)
                            caption = f"🎯 **[Авто-комбо] {info['name']}**\n📅 `{date_text}`"
                            try:
                                bot.send_photo(ADMIN_CHAT_ID, photo=img_bytes, caption=caption[:1024], parse_mode="Markdown")
                            except Exception as e:
                                logger.error(f"Ошибка отправки авто-фото администратору: {e}")
                except Exception as e:
                    logger.error(f"Ошибка авто-проверки игры {key}: {e}")

            # После первой попытки сбрасываем флаг старта, чтобы дальше работать по расписанию
            run_check_now = False

        # Проверка и обновление игровых таймеров пользователей
        try:
            for chat_id, timers in list(user_game_timers.items()):
                for game_key, t_data in list(timers.items()):
                    if t_data and isinstance(t_data, dict):
                        target_time = t_data.get("target")
                        if target_time and now_time >= target_time:
                            game_name = manager.combo_games[game_key]["name"] if game_key in manager.combo_games else manager.independent_farms[game_key]["name"]
                            send_message_direct(chat_id, f"⏰ **Напоминание!** Пора заходить в игру: **{game_name}** 🚀")
                            duration = t_data.get("duration_hours", 8)
                            user_game_timers[chat_id][game_key]["target"] = time.time() + (duration * 3600)
        except Exception as e:
            logger.error(f"Ошибка в проверке таймеров: {e}")

        # Проверка истечения срока активной рекламы из файла
        try:
            expired_ads = []
            for oid, ad_data in list(active_ads_storage.items()):
                if now_time >= ad_data["expire_time"]:
                    expired_ads.append(oid)
                    send_message_direct(
                        ad_data["user_id"],
                        "⏱ **Срок размещения вашей рекламы истек.** Рекламный пост был автоматически снят. Спасибо за сотрудничество!",
                        parse_mode="Markdown"
                    )
                    send_message_direct(
                        ADMIN_CHAT_ID,
                        f"📢 **Рекламная кампания завершена по таймеру!**\nЗаказчик: `{ad_data['user_id']}` (ID заказа: `{oid}`)",
                        parse_mode="Markdown"
                    )
            if expired_ads:
                for oid in expired_ads:
                    active_ads_storage.pop(oid, None)
                save_active_ads_to_file()
        except Exception as e:
            logger.error(f"Ошибка проверки рекламных таймеров: {e}")

        # Пауза 10 минут (600 секунд) перед следующим циклом опроса
        time.sleep(600)
        
def generate_advanced_captcha(chat_id):
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    ans = str(a + b)
    variants = [ans, str(ans + "1" if int(ans) < 10 else "5"), str(max(1, int(ans) - 2)), str(int(ans) + 3)]
    variants = list(set(variants))[:4]
    advanced_captchas[chat_id] = ans
    markup = types.InlineKeyboardMarkup(row_width=2)
    random.shuffle(variants)
    buttons = [types.InlineKeyboardButton(text=v, callback_data=f"advcap_{v}") for v in variants]
    markup.add(*buttons)
    return f"Сколько будет {a} + {b}?", markup

@bot.message_handler(commands=['start'])
def handle_start(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in verified_users:
        question, markup = generate_advanced_captcha(chat_id)
        bot.send_message(chat_id, f"🛡️ **Проверка на человека**\n\n🧠 *{question}*", reply_markup=markup, parse_mode="Markdown")
        return
    send_message_direct(chat_id, "⚡ **Бот работает в режиме Zero-Lag!**")
    send_message_direct(chat_id, "👇 Главное меню:", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['calc', 'farm', 'timers', 'proofs', 'all_combo', 'miners', 'faucets', 'profile', 'reviews', 'ads'])
@bot.message_handler(func=lambda msg: msg.text in [
    "🚀 Меню комбо-игр", "👤 Профиль и статы", "📱 Телефонные майнеры", "🚰 Крипто-краны", 
    "🌾 Авто-фермы (без комбо)", "⚡ Проверить все комбо", "🧮 Крипто-курс", "📊 Защита фермы", 
    "⏰ Мои таймеры", "💬 Отзывы", "📢 Реклама и монетизация", "💎 Скрины выплат"
])
def handle_menu_text(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in verified_users:
        send_message_direct(chat_id, "⚠️ Сначала пройдите верификацию через /start.")
        return

    text = message.text
    if text in ["🚀 Меню комбо-игр"]:
        keyboard, total_count = get_combo_list_keyboard(page=0)
        send_message_direct(chat_id, f"🎮 **Активные комбо-проекты**\nВсего доступно игр с комбо: **{total_count}**\n\nВыберите проект из списка ниже:", reply_markup=keyboard)
    elif text in ["👤 Профиль и статы", "/profile"]:
        show_user_profile(chat_id)
    elif text in ["📱 Телефонные майнеры", "/miners"]:
        send_message_direct(chat_id, "📱 **Мобильные и облачные майнеры:**", reply_markup=get_phone_miners_keyboard())
    elif text in ["🚰 Крипто-краны", "/faucets"]:
        send_message_direct(chat_id, "🚰 **Крипто-краны:**", reply_markup=get_faucets_keyboard())
    elif text in ["🌾 Авто-фермы (без комбо)"]:
        send_message_direct(chat_id, "🌾 **Отдельные фермерские проекты:**", reply_markup=get_farms_keyboard())
    elif text in ["⚡ Проверить все комбо", "/all_combo"]:
        send_message_direct(chat_id, "🔍 **Запущен массовый сбор комбо...**")
        for key, info in manager.combo_games.items():
            img_url, date_text = manager.fetch_combo(key)
            img_bytes = manager.resize_img(img_url, game_key=key) if img_url else None
            send_combo_result(chat_id, info, img_bytes, date_text)
    elif text in ["🧮 Крипто-курс", "/calc"]:
        send_message_direct(chat_id, "🧮 **Выберите криптовалюту:**", reply_markup=get_crypto_currency_keyboard())
    elif text in ["📊 Защита фермы", "/farm"]:
        send_message_direct(chat_id, "📊 **Статус:** Сеть работает на максимальной скорости.")
    elif text in ["⏰ Мои таймеры", "/timers"]:
        report = "⏰ **Ваши персональные таймеры сбора:**\n\n"
        user_timers_dict = user_game_timers.get(chat_id, {})
        all_games = {}
        all_games.update({k: v["name"] for k, v in manager.combo_games.items()})
        all_games.update({k: v["name"] for k, v in manager.independent_farms.items()})
        for k, name in all_games.items():
            t_info = user_timers_dict.get(k)
            t_target = t_info.get("target") if t_info else None
            if t_target and t_target > time.time():
                left_sec = int(t_target - time.time())
                report += f"• *{name}*: через **{left_sec // 3600}ч {(left_sec % 3600) // 60}м**\n"
            else:
                report += f"• *{name}*: ❌ Не установлен\n"
        send_message_direct(chat_id, report + "\n👇 Выберите игру для настройки:", reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
    elif text in ["💬 Отзывы", "/reviews"]:
        send_message_direct(chat_id, "💬 **Секция отзывов и предложений (Laysi🐾):**", reply_markup=get_reviews_keyboard(), parse_mode="Markdown")
    elif text in ["📢 Реклама и монетизация", "/ads"]:
        send_message_direct(chat_id, "📢 **Размещение рекламы через SafePal:**\n\nВыкупите рекламное место в закрепе или рассылке, оплатив его напрямую через кошелек SafePal.", reply_markup=get_ads_keyboard(), parse_mode="Markdown")
    elif text in ["💎 Скрины выплат", "/proofs"]:
        if not cloud_proofs:
            send_message_direct(chat_id, "💎 Скринов пока нет.")
        else:
            for p in cloud_proofs[-3:]:
                try: bot.send_photo(chat_id, p)
                except: pass

@bot.message_handler(content_types=['photo'])
def handle_photo(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in verified_users:
        return
    if chat_id in user_input_states and user_input_states[chat_id].get("step") == "waiting_photo":
        state_data = user_input_states[chat_id]
        if chat_id not in user_game_stats:
            user_game_stats[chat_id] = {}
        user_game_stats[chat_id][state_data["game"]] = {"stat": state_data["stat"], "photo": message.photo[-1].file_id}
        user_input_states.pop(chat_id, None)
        bot.reply_to(message, f"✅ Игра *{state_data['game']}* добавлена в профиль!", reply_markup=get_profile_keyboard(), parse_mode="Markdown")
        return
    if chat_id == ADMIN_CHAT_ID:
        cloud_proofs.append(message.photo[-1].file_id)
        try: bot.reply_to(message, "✅ Скрин сохранен в облачном хранилище!")
        except: pass

@bot.message_handler(func=lambda m: True)
def handle_text_all(message: types.Message):
    chat_id = message.chat.id
    raw_text = message.text.strip()
    if chat_id not in verified_users:
        send_message_direct(chat_id, "⚠️ Пожалуйста, пройдите верификацию через /start.")
        return

    if chat_id in user_input_states and user_input_states[chat_id].get("step") == "waiting_review_text":
        user_input_states.pop(chat_id, None)
        try: user_name = bot.get_chat(chat_id).first_name or "Аноним"
        except: user_name = "Аноним"
        user_reviews_storage.append({"user": user_name, "text": raw_text, "date": time.strftime("%d.%m.%Y %H:%M")})
        send_message_direct(ADMIN_CHAT_ID, f"💬 **Новый отзыв от {user_name}:**\n\n`{raw_text}`", parse_mode="Markdown")
        send_message_direct(chat_id, "✅ **Спасибо за ваш отзыв!**", reply_markup=get_reviews_keyboard(), parse_mode="Markdown")
        return

    if chat_id in user_input_states and user_input_states[chat_id].get("step") == "waiting_review_text":
        user_input_states.pop(chat_id, None)
        
        # --- НОВАЯ ПРОВЕРКА АНТИСПАМА И БЕЗОПАСНОСТИ ---
        clean_review_text = security_core.sanitize_input(raw_text)
        is_threat, security_msg = security_core.analyze_traffic(raw_text)
        
        if is_threat or clean_review_text == "[BLOCKED_INJECTION_ATTEMPT]" or "http://" in raw_text.lower() or "https://" in raw_text.lower() or "t.me/" in raw_text.lower():
            send_message_direct(chat_id, "⚠️ **Ваш отзыв отклонен системой безопасности!** Обнаружены запрещенные ссылки или потенциальная угроза спама.", parse_mode="Markdown")
            return
        # -----------------------------------------------

        try: user_name = bot.get_chat(chat_id).first_name or "Аноним"
        except: user_name = "Аноним"
        
        user_reviews_storage.append({"user": user_name, "text": clean_review_text, "date": time.strftime("%d.%m.%Y %H:%M")})
        send_message_direct(ADMIN_CHAT_ID, f"💬 **Новый отзыв от {user_name}:**\n\n`{clean_review_text}`", parse_mode="Markdown")
        send_message_direct(chat_id, "✅ **Спасибо за ваш отзыв!**", reply_markup=get_reviews_keyboard(), parse_mode="Markdown")
        return

    if chat_id in user_input_states and user_input_states[chat_id].get("step") == "waiting_ad_content":
        order_data = user_input_states.pop(chat_id, None)
        tariff = order_data["tariff"]
        coin = order_data["coin"]
        
        order_id = f"ord_{chat_id}_{int(time.time())}"
        pending_data = {
            "user_id": chat_id,
            "tariff": tariff,
            "coin": coin,
            "content": raw_text
        }
        pending_ad_orders[order_id] = pending_data

        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.row(types.InlineKeyboardButton(text="✅ Оплата поступила (Запустить рекламу)", callback_data=f"adm_pay_ok_{order_id}"))
        admin_markup.row(types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_pay_no_{order_id}"))

        send_message_direct(
            ADMIN_CHAT_ID,
            f"📢 **Заявка на рекламу ожидает подтверждения оплаты!**\n"
            f"👤 Заказчик: `{chat_id}`\n"
            f"📋 Тариф: `{tariff}`\n"
            f"💰 Оплата через: `{coin.upper()}`\n\n"
            f"📝 **Креатив:**\n{raw_text}",
            reply_markup=admin_markup,
            parse_mode="Markdown"
        )
        send_message_direct(
            chat_id,
            "✅ **Ваш рекламный креатив и чек приняты!**\nЗаявка отправлена администратору на проверку поступления средств на SafePal.",
            reply_markup=get_ads_keyboard(),
            parse_mode="Markdown"
        )
        return

    if chat_id in user_input_states and user_input_states[chat_id].get("step") == "waiting_custom_timer":
        game_key = user_input_states[chat_id]["game_key"]
        user_input_states.pop(chat_id, None)
        try:
            cleaned = raw_text.lower().replace(",", ".")
            hours_val = float(re.sub(r'[^0-9.]', '', cleaned)) / 60.0 if "м" in cleaned else float(cleaned)
            if hours_val <= 0: raise ValueError()
            if chat_id not in user_game_timers: user_game_timers[chat_id] = {}
            user_game_timers[chat_id][game_key] = {"target": time.time() + (hours_val * 3600), "duration_hours": hours_val}
            game_name = manager.combo_games[game_key]["name"] if game_key in manager.combo_games else manager.independent_farms[game_key]["name"]
            send_message_direct(chat_id, f"✅ Успешно! Таймер для *{game_name}* установлен на **{hours_val} ч.**", reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
            return
        except:
            send_message_direct(chat_id, "⚠️ Неверный формат! Введите число (например: `2.5`):", parse_mode="Markdown")
            return

    text = security_core.sanitize_input(raw_text)
    is_threat, security_msg = security_core.analyze_traffic(text)
    if is_threat or any(x in text.lower() for x in ["http://", "https://", "t.me/", "@"]):
        send_message_direct(chat_id, security_msg)
        return

    if chat_id in user_calc_states:
        state = user_calc_states[chat_id]
        try:
            amt = float(text.replace(",", "."))
            c_id = {"btc": "bitcoin", "eth": "ethereum", "usdt": "tether", "gram": "the-open-network"}.get(state["crypto"], "bitcoin")
            fiat = state['fiat']
            
            # Запрашиваем цену и изменение за 24 часа
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={c_id}&vs_currencies={fiat}&include_24hr_change=true"
            res_data = requests.get(url, timeout=3).json().get(c_id, {})
            
            rate = res_data.get(fiat, 0)
            change_24h = res_data.get(fiat + "_24h_change", 0)
            
            total_sum = rate * amt
            
            # Иконка и знак в зависимости от роста или падения
            trend_icon = "🟢" if change_24h >= 0 else "🔴"
            change_sign = "+" if change_24h > 0 else ""
            
            report_text = (
                f"💎 **Крипто-конвертер [Zero-Lag]**\n\n"
                f"🔹 Количество: **{amt} {state['crypto'].upper()}**\n"
                f"💵 Стоимость: **{total_sum:,.2f} {fiat.upper()}**\n"
                f"📈 Тренд за 24ч: {trend_icon} **{change_sign}{change_24h:.2f}%**"
            )
            
            send_message_direct(chat_id, report_text, parse_mode="Markdown")
            user_calc_states.pop(chat_id, None)
            return
        except Exception as e:
            logger.error(f"Ошибка конвертера: {e}")
            send_message_direct(chat_id, "⚠️ Ошибка получения данных с API. Введите корректное число:")
            return

    send_message_direct(chat_id, "⚡ Отклик мгновенный.", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("advcap_"):
        if data.replace("advcap_", "") == advanced_captchas.get(chat_id):
            save_verified_user(chat_id)
            advanced_captchas.pop(chat_id, None)
            bot.answer_callback_query(call.id, "✅ Доступ разрешен!")
            try: bot.edit_message_text("✅ **Доступ открыт!**", chat_id, call.message.message_id, parse_mode="Markdown")
            except: pass
            send_message_direct(chat_id, "👇 Главное меню:", reply_markup=get_main_keyboard())
        else:
            q, m = generate_advanced_captcha(chat_id)
            bot.answer_callback_query(call.id, "❌ Неверно!", show_alert=True)
            try: bot.edit_message_text(f"❌ **Неверно!**\n🧠 *{q}*", chat_id, call.message.message_id, reply_markup=m, parse_mode="Markdown")
            except: pass
        return

    if chat_id not in verified_users:
        bot.answer_callback_query(call.id, "Сначала пройдите верификацию через /start!", show_alert=True)
        return

    # Админские кнопки подтверждения оплаты рекламы
    if data.startswith("adm_pay_ok_") or data.startswith("adm_pay_no_"):
        if chat_id != ADMIN_CHAT_ID:
            bot.answer_callback_query(call.id, "Только для администратора!", show_alert=True)
            return
        
        parts = data.split("_")
        action = parts[2] 
        order_id = f"{parts[3]}_{parts[4]}_{parts[5]}"
        
        order = pending_ad_orders.get(order_id)
        if not order:
            bot.answer_callback_query(call.id, "Заказ не найден или уже обработан", show_alert=True)
            return

        target_user_id = order["user_id"]
        pending_ad_orders.pop(order_id, None)
        bot.answer_callback_query(call.id, "Обработано!")

        if action == "ok":
            # Если это закреп на 24 часа — сохраняем таймер окончания в файл (24 часа = 86400 секунд)
            if "24" in order["tariff"]:
                expire_timestamp = time.time() + 86400
                active_ads_storage[order_id] = {"user_id": target_user_id, "expire_time": expire_timestamp}
                save_active_ads_to_file()

            send_message_direct(
                target_user_id,
                "🎉 **Оплата получена! Ваша реклама успешно запущена в боте.**\nБлагодарим за сотрудничество!",
                parse_mode="Markdown"
            )
            try:
                bot.edit_message_text(f"✅ **Заказ успешно подтвержден и запущен!** (Клиент: `{target_user_id}`)", chat_id, call.message.message_id, parse_mode="Markdown")
            except: pass
        else:
            send_message_direct(
                target_user_id,
                "❌ **Оплата не подтверждена администратором.** Свяжитесь с поддержкой для уточнения деталей.",
                parse_mode="Markdown"
            )
            try:
                bot.edit_message_text(f"❌ **Заказ отклонен.** (Клиент: `{target_user_id}`)", chat_id, call.message.message_id, parse_mode="Markdown")
            except: pass
        return

    # Секция отзывов
    if data == "review_add":
        user_input_states[chat_id] = {"step": "waiting_review_text"}
        bot.answer_callback_query(call.id)
        send_message_direct(chat_id, "✍️ **Напишите ваш отзыв одним сообщением:**", parse_mode="Markdown")
        return

    if data == "review_read":
        bot.answer_callback_query(call.id)
        if not user_reviews_storage:
            send_message_direct(chat_id, "💬 Пока что отзывов нет.")
        else:
            rev_text = "💬 **Последние отзывы:**\n\n" + "\n".join([f"👤 *{r['user']}* (`{r['date']}`):\n{r['text']}\n" for r in user_reviews_storage[-5:]])
            send_message_direct(chat_id, rev_text, parse_mode="Markdown")
        return

    # Монетизация и SafePal
    if data == "ads_buy":
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                "💰 **Выберите тариф для размещения рекламы:**\nОплата поступает напрямую на ваш кошелек SafePal.",
                chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_ads_tariffs_keyboard(), parse_mode="Markdown"
            )
        except: pass
        return

    if data == "ads_stats":
        bot.answer_callback_query(call.id)
        send_message_direct(chat_id, f"📊 **Статистика:** Активных пользователей: **~{len(verified_users) + 120}**", parse_mode="Markdown")
        return

    if data in ["adtariff_24h", "adtariff_broadcast"]:
        tariff_name = "Закреп на 24 часа ($15)" if data == "adtariff_24h" else "Рассылка по всей базе ($30)"
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                f"💎 Вы выбрали тариф: *{tariff_name}*.\n\n"
                "👇 **Выберите криптовалюту для оплаты через SafePal:**",
                chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_safepal_coins_keyboard(data), parse_mode="Markdown"
            )
        except: pass
        return

    if data.startswith("pay_"):
        parts = data.split("_")
        tariff_key = parts[1]
        coin_key = parts[2]
        
        tariff_name = "Закреп на 24 часа ($15)" if tariff_key == "adtariff_24h" else "Рассылка по всей базе ($30)"
        wallet_info = SAFEPAL_WALLETS.get(coin_key, {"name": coin_key.upper(), "address": "ADRESS_NOT_SET"})
        
        user_input_states[chat_id] = {"step": "waiting_ad_content", "tariff": tariff_name, "coin": coin_key}
        bot.answer_callback_query(call.id)
        
        send_message_direct(
            chat_id,
            f"💳 **Реквизиты SafePal для оплаты:**\n\n"
            f"📋 Тариф: *{tariff_name}*\n"
            f"🪙 Монета: *{wallet_info['name']}*\n\n"
            f"📌 **Адрес кошелька SafePal:**\n`{wallet_info['address']}`\n\n"
            f"⚠️ **Инструкция:** Переведите точную сумму на указанный адрес SafePal, после чего **отправьте текстом креатив вашей рекламы** (и хэш транзакции/скрин), чтобы администратор мог подтвердить платеж.",
            parse_mode="Markdown"
        )
        return

    if data == "ads_menu_back":
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text("📢 **Размещение рекламы через SafePal:**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_ads_keyboard(), parse_mode="Markdown")
        except: pass
        return

    if data.startswith("timer_game_"):
        key = data.replace("timer_game_", "")
        game_name = manager.combo_games[key]["name"] if key in manager.combo_games else manager.independent_farms[key]["name"]
        bot.answer_callback_query(call.id)
        try: bot.edit_message_text(f"⏰ Настройка таймера для: **{game_name}**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timer_duration_keyboard(key), parse_mode="Markdown")
        except: pass
        return

    if data.startswith("settimer_"):
        parts = data.split("_")
        hours = int(parts[2])
        if chat_id not in user_game_timers: user_game_timers[chat_id] = {}
        user_game_timers[chat_id][parts[1]] = {"target": time.time() + (hours * 3600), "duration_hours": float(hours)}
        bot.answer_callback_query(call.id, f"✅ Таймер на {hours}ч установлен!")
        try: bot.edit_message_text(f"✅ **Таймер установлен на {hours} ч.!**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
        except: pass
        return

    if data.startswith("customtimer_"):
        user_input_states[chat_id] = {"step": "waiting_custom_timer", "game_key": data.replace("customtimer_", "")}
        bot.answer_callback_query(call.id)
        send_message_direct(chat_id, "✏️ **Введите свое время таймера** (например: `2.5` или `90м`):", parse_mode="Markdown")
        return

    if data.startswith("canceltimer_"):
        if chat_id in user_game_timers: user_game_timers[chat_id].pop(data.replace("canceltimer_", ""), None)
        bot.answer_callback_query(call.id, "❌ Таймер отключен")
        try: bot.edit_message_text("❌ **Таймер отключен.**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
        except: pass
        return

    if data == "timers_menu_back":
        bot.answer_callback_query(call.id)
        try: bot.edit_message_text("⏰ **Выберите игру для таймера:**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
        except: pass
        return

    if data == "prof_add":
        user_input_states[chat_id] = {"step": "waiting_game_info"}
        bot.answer_callback_query(call.id)
        send_message_direct(chat_id, "✍️ **Введите данные в формате:**\n`Название игры | Уровень`", parse_mode="Markdown")
        return

    if data == "prof_view":
        bot.answer_callback_query(call.id)
        show_user_profile(chat_id)
        return

    if data.startswith("combopage_"):
        page = int(data.replace("combopage_", ""))
        keyboard, total_count = get_combo_list_keyboard(page=page)
        bot.answer_callback_query(call.id)
        try: bot.edit_message_text(f"🎮 **Комбо-проекты ({total_count})**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
        except: pass
        return

    if data.startswith("gamemenu_"):
        parts = data.split("_")
        if parts[1] in manager.combo_games:
            bot.answer_callback_query(call.id)
            bot.edit_message_text(f"🕹 **Меню: {manager.combo_games[parts[1]]['name']}**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_single_game_keyboard(parts[1], parts[2]), parse_mode="Markdown")
        return

    if data == "ignore":
        bot.answer_callback_query(call.id)
        return

    if data.startswith("pinfo_"):
        info = manager.phone_miners[data.replace("pinfo_", "")]
        bot.answer_callback_query(call.id)
        send_message_direct(chat_id, f"📱 **{info['name']}**\n\n{info['description']}\n\n🔑 Код: `{info['code']}`", parse_mode="Markdown")
        return

    if data.startswith("finfo_"):
        info = manager.crypto_faucets[data.replace("finfo_", "")]
        bot.answer_callback_query(call.id)
        send_message_direct(chat_id, f"🚰 **{info['name']}**\n\n{info['description']}", parse_mode="Markdown")
        return

    if data.startswith("cur_"):
        crypto = data.replace("cur_", "")
        bot.answer_callback_query(call.id)
        bot.edit_message_text(f"🧮 Вы выбрали **{crypto.upper()}**. Выберите валюту:", chat_id, call.message.message_id, reply_markup=get_fiat_currency_keyboard(crypto), parse_mode="Markdown")
        return

    if data.startswith("fiat_"):
        parts = data.split("_")
        user_calc_states[chat_id] = {"crypto": parts[1], "fiat": parts[2]}
        bot.answer_callback_query(call.id)
        bot.edit_message_text(f"🧮 Введите количество {parts[1].upper()}:", chat_id, call.message.message_id, parse_mode="Markdown")
        return

    if data.startswith("strat_"):
        bot.answer_callback_query(call.id)
        send_message_direct(chat_id, manager.combo_games[data.replace("strat_", "")]["strategy"])
        return

    if data.startswith("farm_strat_"):
        bot.answer_callback_query(call.id)
        send_message_direct(chat_id, manager.independent_farms[data.replace("farm_strat_", "")]["strategy"])
        return

    if data.startswith("game_"):
        key = data.replace("game_", "")
        if key in manager.combo_games:
            bot.answer_callback_query(call.id, "Загрузка...")
            img_url, date_text = manager.fetch_combo(key)
            send_combo_result(chat_id, manager.combo_games[key], manager.resize_img(img_url, key) if img_url else None, date_text)
        return

if __name__ == "__main__":
    logger.info("=== ZERO-LAG TERMUX NATIVE BOT ЗАПУЩЕН ===")
    threading.Thread(target=daily_auto_checker, daemon=True).start()
    bot.infinity_polling(skip_pending=True, timeout=5, long_polling_timeout=3)
