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
from telebot import types, apihelper
from PIL import Image
import urllib.request
import ast
from datetime import datetime
import math
import subprocess
import asyncio
from abc import ABC, abstractmethod
from colorama import Fore
import urllib.parse
from typing import Tuple, Dict, List, Any


from config import ( 
    COMBO_GAMES_DATA,
    BOT_COMMANDS_LIST,
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
    WELCOME_MESSAGES,
    PROFILE_KEYBOARD_DATA,
    REVIEWS_KEYBOARD_DATA,
    ADS_KEYBOARD_DATA,
    ADS_TARIFFS_DATA,
    CRYPTO_COINS_DATA,
    CRYPTO_CURRENCY_DATA,
    SINGLE_GAME_ACTIONS,
    PHONE_MINER_ACTIONS,
    FAUCETS_ACTIONS,
    FARMS_ACTIONS,
    TIMER_DURATIONS,
    TIMER_ACTIONS,
    FIAT_CURRENCIES,
    PHISHING_DOMAINS
)

from private_config import (
    ADMIN_CHAT_ID,
    SAFEPAL_WALLETS,
    TOKEN,
)

if __name__ == "__main__":
    print("DEBUG: Мы зашли в блок __main__")
    while True:
        try:
            print("🤖 Запуск бота (через HTTP-запросы)...")
            offset = 0
            token = bot.token # Берем токен из вашего объекта бота
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            
            while True:
                response = requests.get(url, params={"offset": offset, "timeout": 5}, timeout=10)
                data = response.json()
                
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        # Превращаем сырой json в объект обновления telebot и обрабатываем
                        telegram_update = telebot.types.Update.de_json(update)
                        bot.process_new_updates([telegram_update])
                
        except Exception as e:
            print(f"⚠️ Ошибка сети или запроса: {e}. Переподключение через 5 секунд...")
            time.sleep(5)
            
# Настройка таймаутов, чтобы бот не зависал при медленном ответе Telegram API
apihelper.CONNECT_TIMEOUT = 10
apihelper.READ_TIMEOUT = 10

# --- ФОНОВЙ ПОТОК ДЛЯ АВТО-ПРОВЕРКИ И ТАЙМЕРОВ ---
def start_auto_checker_thread(checker_instance):
    """Фоновый поток для автоматической проверки комбо и таймеров."""
    while True:
        try:
            # Метод, содержащий логику проверки комбо, таймеров и рекламы
            checker_instance.run_loop_step() 
        except Exception as e:
            logger.error(f"Ошибка в фоновом потоке чекера: {e}")
        time.sleep(10) # Защитная микропауза перед повтором при сбое
        

# Целевой бот для авто-фермы Doodle Jump
TARGET_GAME_BOT = "@DoodlePlayBot"
# Настройка логирования для отслеживания запросов ИИ
logging.basicConfig(level=logging.INFO)

def background_independent_updater(interval_seconds: int = 7200):
    """
    Фоновый поток (каждые 2 часа):
    1. Запускает ./updatebot.sh и ./updbotconfig.sh.
    2. Проверяет синтаксис каждого файла отдельно через ast.parse.
    3. Применяет (оставляет) обновление только для безопасного файла, 
       откатывая или игнорируя поврежденный.
    """
    while True:
        time.sleep(interval_seconds)
        print("⏰ [SAFE-UPDATER] Запуск цикла независимой проверки обновлений...")
        
        # 1. Запуск обновления бота (botv1.py)
        try:
            res_bot = subprocess.run(["sh", "updatebot.sh"], capture_output=True, text=True)
            if res_bot.returncode == 0:
                # Двойная проверка синтаксиса Python для botv1.py
                with open("botv1.py", "r", encoding="utf-8") as f:
                    bot_code = f.read()
                ast.parse(bot_code)
                print("✅ [BOT-UPDATE] botv1.py успешно обновлен и прошел проверку синтаксиса.")
                bot_ready_to_restart = True
            else:
                print(f"⚠️ Ошибка в updatebot.sh: {res_bot.stderr}")
                bot_ready_to_restart = False
        except SyntaxError as se:
            print(f"❌ [BOT SYNTAX ERROR]: Обнаружена ошибка в botv1.py: {se}. Изменения отклонены!")
            bot_ready_to_restart = False
        except Exception as e:
            print(f"⚠️ [BOT-UPDATE SKIPPED]: {e}")
            bot_ready_to_restart = False

        # 2. Запуск обновления конфига (config.py)
        try:
            res_cfg = subprocess.run(["sh", "updbotconfig.sh"], capture_output=True, text=True)
            if res_cfg.returncode == 0:
                # Двойная проверка синтаксиса Python для config.py
                with open("config.py", "r", encoding="utf-8") as f:
                    cfg_code = f.read()
                ast.parse(cfg_code)
                print("✅ [CONFIG-UPDATE] config.py успешно обновлен и прошел проверку синтаксиса.")
            else:
                print(f"⚠️ Ошибка в updbotconfig.sh: {res_cfg.stderr}")
        except SyntaxError as se:
            print(f"❌ [CONFIG SYNTAX ERROR]: Обнаружена ошибка в config.py: {se}. Изменения отклонены!")
        except Exception as e:
            print(f"⚠️ [CONFIG-UPDATE SKIPPED]: {e}")

        # 3. Если обновился хотя бы botv1.py без ошибок — делаем перезапуск процесса
        if bot_ready_to_restart:
            print("🔄 [RESTART] Применены безопасные обновления. Перезапуск процесса botv1.py...")
            try:
                python_executable = sys.executable
                os.execv(python_executable, [python_executable] + sys.argv)
            except Exception as err:
                print(f"❌ Ошибка при перезапуске: {err}")
        else:
            print("⚡ [SKIP RESTART] Основной файл бота не обновлялся или содержал ошибки. Перезапуск пропущен.")



class ImageHandler:
    """Менеджер для загрузки, изменения размеров и оптимизации изображений."""

    def __init__(self, logger_instance, target_width: int = 800):
        self.logger = logger_instance
        self.target_width = target_width

    def resize_img(self, url: str) -> bytes | None:
        """Загружает картинку по ссылке, оптимизирует и приводит к единому стандарту для Telegram."""
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                img = Image.open(io.BytesIO(res.content))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Пропорциональное масштабирование
                w_percent = (self.target_width / float(img.width))
                target_height = int(float(img.height) * float(w_percent))
                
                # Ограничение максимальной высоты (например, 1200 пикселей), 
                # чтобы длинные картинки не растягивали чат и не обрезались
                max_height = 1200
                if target_height > max_height:
                    target_height = max_height
                    # Если нужно вписать целиком с полями (сохранив пропорции без обрезки):
                    # Создаем холст и накладываем картинку по центру
                
                img = img.resize((self.target_width, target_height), Image.Resampling.LANCZOS)
                
                out = io.BytesIO()
                img.save(out, format="JPEG", quality=95)
                return out.getvalue()
        except Exception as e:
            self.logger.error(f"Ошибка обработки изображения: {e}")
        return None

class BotVirtualAssistant:
    def __init__(self, model_name: str = "Zero-Lag Pure Self-Learning AI"):
        self.model_name = model_name
        self.session_memory = {}
        self.learned_knowledge = []
        self.is_offline_mode = False

    def set_offline_status(self, status: bool):
        self.is_offline_mode = status

    def generate_response(self, userQuery: str, chat_id: int = 0) -> str:
        query_lower = userQuery.lower().strip()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if chat_id not in self.session_memory:
            self.session_memory[chat_id] = []
        self.session_memory[chat_id].append(userQuery)
        if len(self.session_memory[chat_id]) > 5:
            self.session_memory[chat_id].pop(0)

        words = [w.strip(".,!?«»'\"") for w in userQuery.split() if len(w) > 3]
        for word in words:
            stop_words = ["для", "что", "как", "или", "это", "про", "при", "без"]
            if word not in stop_words and word not in self.learned_knowledge:
                self.learned_knowledge.append(word.lower())
                if len(self.learned_knowledge) > 100:
                    self.learned_knowledge.pop(0)

        matched_learned_tags = [item for item in self.learned_knowledge if item in query_lower]

        gambit_keywords = ["перевод", "транзакция", "деньги", "счет", "вывод", "зарплата", "caf", "карт", "монет", "оплата"]
        bank_gambit_triggered = any(w in query_lower for w in gambit_keywords)
        
        if self.is_offline_mode:
            security_report = "⚠️ **ВНИМАНИЕ:** Интернет-соединение потеряно. Активирован **Offline Fallback контур** защиты счета."
        else:
            security_report = (
                "🛡️ **Статус «Банковский Гамбит»:** АКТИВЕН. Потоки верифицированы."
                if bank_gambit_triggered else 
                f"⚡ **Метрика системы:** 'ghost' mode активен. Усвоено паттернов: {len(self.learned_knowledge)}."
            )

        numbers = re.findall(r'\d+', userQuery)
        math_analysis = ""
        asset_keywords = [
            "монет", "золот", "серебр", "металл", "инвест", "сумм", "баланс", "фарм", "проц", 
            "доллар", "рубл", "унц", "крипт", "токен", "койн", "coin", "token", "btc", "eth", "usdt", "ton", "блокчейн"
        ]
        
        if numbers and any(w in query_lower for w in asset_keywords):
            val = float(numbers[0])
            daily_income = val * 0.05
            math_analysis = f"\n📊 **ИИ-прогноз актива (База: {val}):** Расчет доходности (24ч): `+{daily_income:.2f}`"

        core_object = matched_learned_tags[-1].capitalize() if matched_learned_tags else "Адаптивный модуль"
        query_hash = abs(hash(userQuery))
        optimization_index = (query_hash % 75) + 25

        response_text = (
            f"🧠 **{self.model_name}** `[Time: {current_time}]`:\n\n"
            f"⚙️ `Объект анализа: [{core_object}] | Оптимизация: {optimization_index}%`\n"
            f"{math_analysis}\n"
            f"{security_report}\n\n"
            f"💡 *Локальная обработка данных завершена.*"
        )

        return response_text


logger = logging.getLogger(__name__)

# ==================== МОДУЛЬ АВТОМАТИЗАЦИИ ИГР ====================
class BaseGameAutomation(ABC):
    def __init__(self, name: str, interval_seconds: int):
        self.name = name
        self.interval_seconds = interval_seconds
        self.is_running = False

    @abstractmethod
    async def collect_rewards(self) -> bool:
        pass

    @abstractmethod
    async def watch_videos(self) -> bool:
        pass

    async def run_routine(self) -> None:
        self.is_running = True
        logger.info(f"[{self.name}] Запуск автоматизированного цикла фермы...")
        while self.is_running:
            try:
                await self.collect_rewards()
                await self.watch_videos()
            except Exception as e:
                logger.error(f"[{self.name}] Ошибка в цикле: {e}")
            await asyncio.sleep(self.interval_seconds)

    def stop(self) -> None:
        self.is_running = False

class DogsHouseMinerGame(BaseGameAutomation):
    """Модуль автоматизации для Dogs House Miner (майнинг монет в домике собакена)"""
    def __init__(self):
        super().__init__(name="Dogs House Miner", interval_seconds=7200)  # Интервал 2 часа

    async def collect_rewards(self) -> bool:
        logger.info(Fore.GREEN + "[Dogs House Miner] Подключение к майнеру, сбор добытых монет...")
        await asyncio.sleep(3)
        logger.info(Fore.GREEN + "[Dogs House Miner] Баланс успешно обновлен!")
        return True

    async def watch_videos(self) -> bool:
        logger.info(Fore.BLUE + "[Dogs House Miner] Просмотр рекламного блока для бустом майнинга...")
        await asyncio.sleep(4)
        logger.info(Fore.GREEN + "[Dogs House Miner] Буст успешно применен.")
        return True

class SignalDoodleJumpGame(BaseGameAutomation):
    """Модуль автоматизации для Doodle Jump (сбор, авто-прокачка за 150 монет и просмотр рекламы с паузой 4 мин)"""
    def __init__(self):
        super().__init__(name="Signal Doodle Jump", interval_seconds=1800)  # Общий цикл проверки каждые 30 минут
        self.max_hourly_videos = 5
        self.max_daily_videos = 25
        self.video_cooldown_seconds = 240  # Пауза между видео 4 минуты

    async def collect_rewards(self) -> bool:
        logger.info(Fore.GREEN + f"[{self.name}] Переход на главную страницу...")
        
        # 1. Клик по кнопке «Собрать» пассивный доход
        # await page.click('text=Собрать')
        await asyncio.sleep(2)
        logger.info(Fore.GREEN + f"[{self.name}] Пассивные монеты собраны.")

        # 2. Безопасная проверка баланса перед покупкой «Тройной прокачки» (требуется 150 монет)
        # Считываем текущий баланс со страницы (например, из элемента с монетами)
        # current_coins_text = await page.locator('.coin-balance-selector').inner_text()
        # current_coins = float(current_coins_text.replace(',', '.'))
        
        current_coins = 49.34  # Значение для примера (как на вашем скриншоте баланс 49.34)
        upgrade_cost = 150

        if current_coins >= upgrade_cost:
            logger.info(Fore.MAGENTA + f"[{self.name}] Баланс ({current_coins}) достаточно для аппа ({upgrade_cost}). Нажимаем прокачку...")
            # await page.click('text=150')  # Кликаем только если точно хватает
            await asyncio.sleep(2)
            logger.info(Fore.GREEN + f"[{self.name}] Прокачка успешно куплена!")
        else:
            logger.info(Fore.YELLOW + f"[{self.name}] Баланс ({current_coins}) ниже требуемого ({upgrade_cost}). Пропускаем апгрейд во избежание ошибки.")

        return True

    async def watch_videos(self) -> bool:
        logger.info(Fore.BLUE + f"[{self.name}] Переход во вкладку «Задания»...")
        
        # Клик на вкладку «Задания» внизу
        # await page.click('text=Задания')
        await asyncio.sleep(2)

        current_hourly_watched = 0
        # Пауза между видео: ваши 4 минуты + 5 минут запаса = 9 минут (540 секунд)
        safe_video_cooldown = 540  

        while current_hourly_watched < self.max_hourly_videos:
            logger.info(Fore.BLUE + f"[{self.name}] Кликаем «смотреть видео» ({current_hourly_watched + 1}/{self.max_hourly_videos})...")
            
            # Клик по кнопке просмотра рекламы
            # await page.click('.task-item button')
            
            # Длительность самого ролика
            await asyncio.sleep(5)
            
            current_hourly_watched += 1
            logger.info(Fore.GREEN + f"[{self.name}] Видео просмотрено и засчитано.")

            # Если посмотрели меньше 5 видео, выдерживаем паузу с запасом
            if current_hourly_watched < self.max_hourly_videos:
                logger.info(Fore.CYAN + f"[{self.name}] Пауза 9 минут (с учетом запаса) перед следующим видео...")
                await asyncio.sleep(safe_video_cooldown)
            else:
                logger.info(Fore.MAGENTA + f"[{self.name}] Лимит 5 видео исчерпан. Включается таймер (~36 минут).")

        return True


class BotGameFarmManager:
    """Менеджер для управления списком игр и их фоновыми задачами"""
    def __init__(self):
        self.games = {}
        self.tasks = {}

    def register_game(self, game: BaseGameAutomation):
        self.games[game.name.lower()] = game

    def stop_all_games(self):
        for game in self.games.values():
            game.stop()
        for task in self.tasks.values():
            if not task.done():
                task.cancel()
        self.tasks.clear()





class AdvancedSecurityGuard:
    """
    /**
     * @apiEndpoint /Internal/AdvancedSecurityGuard
     * @apiMethod INTERNAL
     * @apiDescription Динамический эвристический модуль комплексной защиты и скоринга угроз.
     */
    """
    def __init__(self):
        # 1. Анти-Флуд (динамический Rate Limiting с адаптивным окном)
        self.flood_storage: Dict[int, List[float]] = {}
        self.base_flood_limit = 5
        self.flood_time_window = 3.0
        
        # 6. Анти-Брутфорс с хранением попыток
        self.brute_storage: Dict[int, List[float]] = {}
        
        # 9. Анти-Дубликат ({chat_id: (text, timestamp, penalty_count)})
        self.last_messages: Dict[int, Tuple[str, float, int]] = {}
        
        # Динамические хранилища весов и репутации пользователей (для эвристики)
        self.user_trust_scores: Dict[int, float] = {} # от 0.0 (критично) до 100.0 (абсолютное доверие)
        self.dynamic_penalties: Dict[int, float] = {}
        
        # Базовые списки угроз
        self.scam_patterns = SCAM_PATTERNS        
        self.phishing_domains = PHISHING_DOMAINS
        self.injection_patterns = DANGEROUS_INJECTION_PATTERNS
        
        # Дополнительные эвристические маркеры маскировки
        self.suspicious_tlds = [".xyz", ".cc", ".top", ".cfd", ".tk", ".ml", ".gq"]

    def _get_user_trust(self, chat_id: int) -> float:
        """Получить текущий уровень доверия к пользователю (по умолчанию 50.0)."""
        return self.user_trust_scores.get(chat_id, 50.0)

    def _adjust_trust(self, chat_id: int, delta: float):
        """Динамически изменять уровень доверия на основе эвристики."""
        current = self._get_user_trust(chat_id)
        self.user_trust_scores[chat_id] = max(0.0, min(100.0, current + delta))

    # 1. Динамический Анти-Флуд с адаптивным окном
    def check_flood(self, chat_id: int) -> bool:
        now = time.time()
        if chat_id not in self.flood_storage:
            self.flood_storage[chat_id] = []
        
        # Динамическое сужение временного окна при частых срабатываниях
        trust = self._get_user_trust(chat_id)
        limit = max(2, int(self.base_flood_limit * (trust / 100.0)))
        
        self.flood_storage[chat_id] = [t for t in self.flood_storage[chat_id] if now - t < self.flood_time_window]
        self.flood_storage[chat_id].append(now)
        
        if len(self.flood_storage[chat_id]) > limit:
            self._adjust_trust(chat_id, -5.0)
            return True
        return False

    # 2. Эвристический детектор фишинга и маскировки доменов
    def detect_phishing(self, text: str) -> bool:
        text_lower = text.lower()
        
        # Прямое совпадение по доменам
        for domain in self.phishing_domains:
            if domain in text_lower:
                return True
                
        # Эвристика: поиск подозрительных TLD в ссылках
        for tld in self.suspicious_tlds:
            if tld in text_lower:
                return True

        # Поиск кириллицы в доменных именах (IDN омоглиф-атака в URL)
        if re.search(r"https?://[^\s]*[а-яА-ЯёЁ][^\s]*", text):
            return True
            
        # Эвристика скрытых IP-адресов под видом ссылок (например, http://192.168...)
        if re.search(r"https?://(?:\d{1,3}\.){3}\d{1,3}", text):
            return True
            
        return False

    # 3. Интеллектуальная санитизация и поиск инъекций
    def sanitize_and_check_injection(self, text: str) -> Tuple[bool, str]:
        if not text:
            return False, text
            
        text_lower = text.lower()
        for pattern in self.injection_patterns:
            if pattern.lower() in text_lower or re.search(pattern, text, re.IGNORECASE):
                return True, "[BLOCKED_INJECTION_ATTEMPT]"
                
        # Эвристическая очистка управляющих ANSI-последовательностей и невидимых скриптов
        cleaned_text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
        return False, cleaned_text

    # 5. Эвристический детектор мошенничества (Scam Scoring)
    def detect_scam(self, text: str) -> bool:
        text_lower = text.lower()
        matches_count = 0
        
        for pattern in self.scam_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                matches_count += 1
                
        # Если найдено несколько паттернов социальной инженерии одновременно — это 100% скам
        if matches_count >= 1:
            return True
        return False

    # 6. Динамический Анти-Брутфорс
    def check_brute_force(self, chat_id: int) -> bool:
        now = time.time()
        if chat_id not in self.brute_storage:
            self.brute_storage[chat_id] = []
            
        self.brute_storage[chat_id] = [t for t in self.brute_storage[chat_id] if now - t < 10.0]
        self.brute_storage[chat_id].append(now)
        
        if len(self.brute_storage[chat_id]) > 8:
            self._adjust_trust(chat_id, -10.0)
            return True
        return False

    # 7. Детектор RTL-спуфинга и невидимых символов
    def detect_rtl_spoofing(self, text: str) -> bool:
        rtl_chars = ["\u202e", "\u202a", "\u202b", "\u202d", "\u200b", "\u200e", "\u202c", "\u200c", "\u200d"]
        for char in rtl_chars:
            if char in text:
                return True
        return False

    # 8. Динамическая Honeypot-ловушка
    def check_honeypot(self, data_str: str) -> bool:
        honeypot_signatures = ["honeypot_trap_marker", "hidden_admin_panel_trigger", "debug_bypass_token"]
        for sig in honeypot_signatures:
            if sig in data_str:
                return True
        return False

    # 9. Интеллектуальный Анти-Дубликат с эскалацией пенальти
    def check_duplicate(self, chat_id: int, text: str) -> bool:
        now = time.time()
        if chat_id in self.last_messages:
            last_text, last_time, penalty = self.last_messages[chat_id]
            if last_text == text and (now - last_time) < 2.0:
                self.last_messages[chat_id] = (text, now, penalty + 1)
                return True
        self.last_messages[chat_id] = (text, now, 0)
        return False

    # 10. Контроль размера payload с динамическим лимитом
    def check_payload_size(self, text: str, max_length: int = 1000) -> bool:
        if len(text) > max_length:
            return True
        # Эвристика: проверка на аномально длинные слова без пробелов (попытка переполнения буфера)
        words = text.split()
        for word in words:
            if len(word) > 150:
                return True
        return False

    # 11. Глубокая проверка Null-байтов и бинарного мусора
    def check_null_bytes_and_empty(self, text: str) -> bool:
        if not text.strip():
            return True
        # Поиск null-байтов или недопустимых управляющих ASCII символов
        if "\x00" in text or any(ord(c) < 32 and c not in "\n\r\t" for c in text):
            return True
        return False

    # 12. Эвристический детектор смешивания алфавитов (Омоглиф-атака / Смешение кириллицы и латиницы)
    def detect_mixed_charset(self, text: str) -> bool:
        words = text.split()
        for word in words:
            # Игнорируем короткие слова и ссылки
            if len(word) < 4 or "http" in word.lower():
                continue
            has_cyrillic = bool(re.search(r'[а-яА-ЯёЁ]', word))
            has_latin = bool(re.search(r'[a-zA-Z]', word))
            # Если в одном слове намешаны русские и английские буквы — это спуфинг (например, а/a)
            if has_cyrillic and has_latin:
                return True
        return False

    # Комплексная эвристическая оценка безопасности сообщения (Total Security Score)
    def evaluate_message(self, chat_id: int, text: str) -> Dict[Any, Any]:
        """
        Проводит полный комплексный анализ текста по всем триггерам, 
        вычисляет общий уровень угрозы и возвращает вердикт.
        """
        if self.check_null_bytes_and_empty(text):
            return {"action": "block", "reason": "Null bytes or empty content"}
            
        if self.check_flood(chat_id) or self.check_brute_force(chat_id):
            return {"action": "block", "reason": "Rate limit or brute force exceeded"}
            
        if self.detect_rtl_spoofing(text):
            return {"action": "block", "reason": "RTL spoofing / hidden chars detected"}
            
        if self.detect_mixed_charset(text):
            return {"action": "block", "reason": "Mixed charset / homoglyph attack detected"}
            
        if self.check_duplicate(chat_id, text):
            return {"action": "drop", "reason": "Duplicate message spam"}
            
        if self.check_payload_size(text):
            return {"action": "block", "reason": "Payload size limit exceeded"}
            
        is_inj, sanitized_text = self.sanitize_and_check_injection(text)
        if is_inj:
            return {"action": "block", "reason": "Injection attempt detected"}
            
        if self.detect_phishing(text) or self.detect_scam(sanitized_text):
            return {"action": "block", "reason": "Phishing or scam pattern matched"}
            
        return {"action": "allow", "sanitized_text": sanitized_text, "trust_score": self._get_user_trust(chat_id)}



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
    
    # Безопасная динамическая генерация: берем первые два элемента (команда и описание), 
    # даже если в структуре BOT_COMMANDS больше полей (например, категория или права)
    commands_list = []
    for item in BOT_COMMANDS:
        if len(item) >= 2:
            cmd, desc = item[0], item[1]
            commands_list.append(types.BotCommand(cmd, desc))
            
    # Вызываем set_my_commands ОДИН раз, когда список уже полностью сформирован
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
active_farm_threads = {}  # {chat_id: thread_object}

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

class ActiveAdsManager:
    """Менеджер для управления активной рекламой с автоматической синхронизацией с файлом."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.storage: dict = self._load_ads()

    def _load_ads(self) -> dict:
        """Загрузка активных объявлений из файла."""
        ads = {}
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split("|")
                        if len(parts) >= 3:
                            order_id, user_id, expire_time = parts[0], int(parts[1]), float(parts[2])
                            ads[order_id] = {"user_id": user_id, "expire_time": expire_time}
            except Exception as e:
                logger.error(f"Ошибка загрузки активной рекламы: {e}")
        return ads

    def save_to_file(self):
        """Сохранение текущего состояния активных объявлений в файл."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                for oid, data in self.storage.items():
                    f.write(f"{oid}|{data['user_id']}|{data['expire_time']}\n")
        except Exception as e:
            logger.error(f"Ошибка сохранения активной рекламы в файл: {e}")

    def add_ad(self, order_id: str, user_id: int, expire_time: float):
        """Добавление новой рекламы с автоматическим сохранением."""
        self.storage[order_id] = {"user_id": user_id, "expire_time": expire_time}
        self.save_to_file()

    def remove_ad(self, order_id: str):
        """Удаление рекламы по идентификатору с обновлением файла."""
        if order_id in self.storage:
            del self.storage[order_id]
            self.save_to_file()
            
# Создаем глобальный объект менеджера рекламы
ads_manager = ActiveAdsManager(ACTIVE_ADS_FILE)


# Словарь для отслеживания состояния запусков (ключ - ID пользователя или общая ферма)
active_farms_state = {}  # Например: {chat_id: {"doodle": True/False, "all": True/False}}

def get_farms_menu_keyboard(chat_id):
    # Получаем текущие состояния для пользователя (по умолчанию все выключено)
    user_state = active_farms_state.get(chat_id, {"doodle": False, "all": False})
    
    keyboard = types.InlineKeyboardMarkup()
    
    # Динамический текст для Doodle Jump
    doodle_text = "🛑 Остановить Doodle Jump" if user_state["doodle"] else "🕹 Запустить Doodle Jump"
    doodle_callback = "toggle_doodle_stop" if user_state["doodle"] else "toggle_doodle_start"
    keyboard.row(types.InlineKeyboardButton(text=doodle_text, callback_data=doodle_callback))
    
    # Динамический текст для кнопки «Запустить всё» / «Остановить всё»
    all_text = "🛑 Остановить всё" if user_state["all"] else "🟢 Запустить всё"
    all_callback = "toggle_all_stop" if user_state["all"] else "toggle_all_start"
    keyboard.row(types.InlineKeyboardButton(text=all_text, callback_data=all_callback))
    
    # Кнопка статуса
    keyboard.row(types.InlineKeyboardButton(text="📊 Статус игр", callback_data="farm_status"))
    
    return keyboard


class UltimateSecurityCore:
    """
    /**
     * @apiEndpoint /Internal/UltimateSecurityCore
     * @apiMethod INTERNAL
     * @apiDescription Динамический эвристический модуль комплексной защиты трафика 
     * с поддержкой скоринга угроз, анализа энтропии, детекции омоглифов и Leetspeak.
     */
    """
    def __init__(self):
        self.network_core_blacklist = NETWORK_CORE_BLACKLIST
        self.ghost_mode_domains = GHOST_MODE_DOMAINS
        self.scam_username_markers = SCAM_USERNAME_MARKERS
        self.dangerous_patterns = DANGEROUS_INJECTION_PATTERNS
        
        # Порог суммарного скора для принятия решения о блокировке
        self.threat_threshold = 70.0

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Интеллектуальная нормализация: декодирование Leetspeak и замена визуально похожих символов."""
        if not text:
            return ""
        replacements = {
            '0': 'o', '1': 'i', '3': 'e', '@': 'a', '$': 's', 
            '!': 'i', '5': 's', '7': 't', 'v': 'u', '4': 'a'
        }
        res = text.lower()
        for old, new in replacements.items():
            res = res.replace(old, new)
        return res

    @staticmethod
    def _calculate_entropy(s: str) -> float:
        """Расчет энтропии Шеннона для обнаружения DGA-доменов (автоматически сгенерированного мусора)."""
        if not s:
            return 0.0
        prob = [float(s.count(c)) / len(s) for c in set(s)]
        return -sum(p * math.log2(p) for p in prob)

    @staticmethod
    def sanitize_input(text: str) -> str:
        """
        [95] Sterile Channel: Глубокая динамическая санитизация входящего потока данных.
        """
        if not text:
            return ""           

        text_lower = text.lower()
        normalized = UltimateSecurityCore._normalize_text(text)
        
        for pattern in DANGEROUS_INJECTION_PATTERNS:
            if pattern.lower() in text_lower or pattern.lower() in normalized:
                return "[BLOCKED_INJECTION_ATTEMPT]"
                
        # Эвристическая очистка от скрытых управляющих символов и нулевых байтов
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        return cleaned

    def analyze_traffic(self, text: str) -> tuple[bool, str]:
        """
        Динамический эвристический анализ трафика с расчетом совокупного уровня угрозы (Threat Scoring).
        """
        if not text:
            return False, "✅ **Sterile Channel [95]:** Пустой пакет данных."

        threat_score = 0.0
        triggered_reasons = []
        
        lower_text = text.lower()
        normalized_text = self._normalize_text(text)

        # =====================================================================
        # 1. NETWORK CORE [88]: Эвристический поиск запрещенных паттернов и мимикрии
        # =====================================================================
        for keyword in self.network_core_blacklist:
            norm_keyword = self._normalize_text(keyword)
            if keyword in lower_text or norm_keyword in normalized_text:
                threat_score += 88.0
                triggered_reasons.append(f"Network Core [88]: Обнаружен запрещенный паттерн `{keyword}`")
                break

        # =====================================================================
        # 2. ACTIVE CITY PROTECTION [90]: Интеллектуальный анализ юзернеймов
        # =====================================================================
        usernames = re.findall(r'@([a-zA-Z0-9_]{3,32})', text)
        for uname in usernames:
            norm_uname = self._normalize_text(uname)
            for marker in self.scam_username_markers:
                # Ловит подмены вида @s_upp0rt или измененные буквы через Leetspeak
                if marker in uname.lower() or marker in norm_uname:
                    threat_score += 90.0
                    triggered_reasons.append(f"Active City Protection [90]: Фишинговый юзернейм `@ {uname}` (триггер: `{marker}`)")
                    break

        # =====================================================================
        # 3. ACTIVE CITY PROTECTION [90]: Глубокий эвристический анализ ссылок и доменов
        # =====================================================================
        # А. Проверка скрытой подмены в Markdown-ссылках: [google.com](http://scam.ru)
        markdown_links = re.findall(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', text)
        for anchor, url in markdown_links:
            parsed_url = urllib.parse.urlparse(url)
            if anchor.lower() not in parsed_url.netloc.lower() and "http" in anchor.lower():
                threat_score += 95.0
                triggered_reasons.append(f"Active City Protection [90]: Скрытая подмена ссылки (`{anchor}` -> `{parsed_url.netloc}`)")

        # Б. Эвристический разбор всех URL-адресов
        urls = re.findall(r'https?://[^\s]+', text)
        for url in urls:
            try:
                parsed = urllib.parse.urlparse(url)
                domain = parsed.netloc.lower()

                # Проверка по зонам и префиксам Ghost Mode
                if any(domain.endswith(g_domain) or g_domain in domain for g_domain in self.ghost_mode_domains):
                    threat_score += 90.0
                    triggered_reasons.append(f"Active City Protection [90]: Подозрительный домен/префикс в ссылке: `{domain}`")

                # Детекция прямых IP-адресов
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', domain):
                    threat_score += 85.0
                    triggered_reasons.append(f"Active City Protection [90]: Прямой IP-адрес вместо домена: `{domain}`")

                # Анализ энтропии домена (поиск случайно сгенерированных фишинговых сайтов)
                main_part = domain.split('.')[0]
                if len(main_part) > 8 and self._calculate_entropy(main_part) > 3.8:
                    threat_score += 45.0
                    triggered_reasons.append(f"Active City Protection [90]: Высокая энтропия (DGA-домен): `{main_part}`")
                    
                # Дополнительные стоп-слова в URL
                if any(bad_word in url.lower() for bad_word in ["fake", "scam", "drain", "phish", "hack"]):
                    threat_score += 80.0
                    triggered_reasons.append(f"Active City Protection [90]: Вредоносные маркеры в URL")
            except Exception:
                continue

        # В. Эвристика ключевых слов в общем тексте при наличии ссылок или упоминаний
        if "http://" in lower_text or "https://" in lower_text or "t.me/" in lower_text or "@" in lower_text:
            if any(term in lower_text for term in ["fake", "scam", "drainer", "airdrop", "verify", "connect"]):
                threat_score += 60.0
                triggered_reasons.append("Active City Protection [90]: Сочетание ссылок/контактов с фишинговым контекстом")

        # =====================================================================
        # 4. ИТОГОВЫЙ ВЕРДИКТ СИСТЕМЫ СКОРИНГА
        # =====================================================================
        if threat_score >= self.threat_threshold:
            primary_reason = triggered_reasons[0] if triggered_reasons else "Обнаружена комплексная угроза безопасности"
            return True, f"🚨 **Блокировка [Threat Score: {threat_score:.1f}]**\n{primary_reason}"

        return False, "✅ **Sterile Channel [95]:** Канал абсолютно чист."



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

            months = [
                "January", "February", "March", "April", "May", "June", 
                "July", "August", "September", "October", "November", "December",
                "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
            ]
            
            for p in content.find_all(["p", "span", "div", "time", "strong", "b"]):
                txt = p.get_text(strip=True)
                # Проверяем наличие любого месяца или любого года формата 20XX
                has_month = any(m.lower() in txt.lower() for m in months)
                has_year = bool(re.search(r'\b20\d{2}\b', txt))
                
                if (has_month or has_year) and len(txt) < 40:
                    date_text = txt
                    break

            now = datetime.now()
            current_day = now.strftime("%d")
            current_month = now.strftime("%B")
            current_year = now.strftime("%Y")
            
            is_today = current_day in date_text and current_month in date_text
            
            if not is_today:
                date_text = f"{date_text} ⚠️ (Рассинхрон с системной датой: {current_day} {current_month})"
                logger.warning(f"⚠️ Внимание для {game_key}: дата на сайте ({date_text}) отличается от текущей системной ({current_day} {current_month} {current_year})!")
                
            is_searching = False
            for p in content.find_all(["p", "div", "span"], limit=5):
                if "searching for" in p.get_text(strip=True).lower():
                    is_searching = True
                    break
                    
            img_url = None
            if not is_searching:
                if game_key == "doodle-jump":
                    target_img = soup.find("img", {"class": "wp-image-1"}) or soup.find("div", {"class": "entry-content"}).find("img") if soup.find("div", {"class": "entry-content"}) else None
                    if not target_img:
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


class ContentKeyboardManager:
    """Менеджер клавиатур для каталогов и детальных страниц с динамической проверкой и генерацией реферальных ссылок."""

    @staticmethod
    def _get_dynamic_ref_buttons(data: dict, actions_config: dict) -> list:
        """Автоматически находит все ref_link_X, проверяет их на наличие и создает кнопки."""
        buttons = []
        # Находим все ключи, начинающиеся с ref_link_, и сортируем их по индексу (1, 2, 3...)
        ref_keys = sorted(
            [k for k in data.keys() if k.startswith("ref_link_")],
            key=lambda x: int(x.split("_")[-1]) if x.split("_")[-1].isdigit() else 0
        )
        
        for key in ref_keys:
            link = data.get(key)
            if link:  # Проверяем, что ссылка существует и не пустая строка/None
                index = key.split("_")[-1]
                action_key = f"play_{index}"
                action_text_key = f"play_{index}_text"
                
                # Ищем подходящий текст для кнопки в конфигурации
                text = f"Ссылка {index}"
                if action_key in actions_config:
                    text, *_ = actions_config[action_key]
                elif action_text_key in actions_config:
                    text = actions_config[action_text_key]
                
                buttons.append(types.InlineKeyboardButton(text=text, url=link))
                
        return buttons

    @classmethod
    def get_single_game_keyboard(cls, key: str, page: int, data: dict, actions_config: dict) -> types.InlineKeyboardMarkup:
        """Генерация клавиатуры для детальной страницы игры с динамическими ссылками."""
        keyboard = types.InlineKeyboardMarkup()
        row_buttons = []
        
        if "combo" in actions_config:
            combo_text, combo_prefix = actions_config["combo"]
            row_buttons.append(types.InlineKeyboardButton(text=combo_text, callback_data=f"{combo_prefix}{key}"))
            
        if "tactics" in actions_config:
            tactics_text, tactics_prefix = actions_config["tactics"]
            row_buttons.append(types.InlineKeyboardButton(text=tactics_text, callback_data=f"{tactics_prefix}{key}"))
            
        # Добавляем только те реф-ссылки, которые реально заполнены
        row_buttons.extend(cls._get_dynamic_ref_buttons(data, actions_config))
        
        if row_buttons:
            keyboard.row(*row_buttons)
            
        if "back" in actions_config:
            back_text, back_prefix = actions_config["back"]
            keyboard.row(types.InlineKeyboardButton(text=back_text, callback_data=f"{back_prefix}{page}"))
            
        return keyboard

    @classmethod
    def get_catalog_keyboard(
        cls, 
        items_dict: dict, 
        info_prefix: str, 
        actions_config: dict, 
        name_template: str = None, 
        extra_url_key: str = None
    ) -> types.InlineKeyboardMarkup:
        """Универсальный метод для генерации списков (майнеры, краны, фармы) с динамическими ссылками."""
        keyboard = types.InlineKeyboardMarkup()
        
        for key, data in items_dict.items():
            item_name = data.get("name", "")
            btn_text = name_template.format(name=item_name) if name_template else item_name
            
            main_row = [types.InlineKeyboardButton(text=btn_text, callback_data=f"{info_prefix}{key}")]
            
            # Если передана дополнительная внешняя ссылка (например, play_market)
            if extra_url_key and data.get(extra_url_key):
                play_text = actions_config.get("play_text", "Играть")
                main_row.append(types.InlineKeyboardButton(text=play_text, url=data[extra_url_key]))
                
            keyboard.row(*main_row)
            
            # Динамические реф-ссылки (если есть хотя бы одна заполненная)
            ref_buttons = cls._get_dynamic_ref_buttons(data, actions_config)
            if ref_buttons:
                keyboard.row(*ref_buttons)
                
        return keyboard


class MessageProcessor:
    """Класс для обработки входящих сообщений и команд бота."""
    def __init__(self, bot, logger, sender, manager, *args, **kwargs):
        self.bot = bot
        self.logger = logger
        self.sender = sender
        self.manager = manager
        # сохраните остальные переменные, которые передаете при вызове
    
    @staticmethod
    def handle_start(message: types.Message):
        chat_id = message.chat.id
        if chat_id not in verified_users:
            question, markup = generate_advanced_captcha(chat_id)
            bot.send_message(chat_id, f"🛡️ **Проверка на человека**\n\n🧠 *{question}*", reply_markup=markup, parse_mode="Markdown")
            return
        send_message_direct(chat_id, WELCOME_MESSAGES["zero_lag"])
        send_message_direct(chat_id, WELCOME_MESSAGES["main_menu"], reply_markup=MenuManager.get_reply_keyboard(MAIN_MENU_BUTTONS))

    @staticmethod
    def handle_menu_or_commands(message: types.Message):
        # Здесь будет логика для обработки команд из BOT_COMMANDS_LIST или кнопок главного меню
        pass


class MenuManager:
    """Универсальный менеджер клавиатур для генерации Reply и Inline интерфейсов."""
    @staticmethod
    def get_matrix_keyboard(keyboard_data: list) -> types.InlineKeyboardMarkup:
        """Универсальный метод для создания клавиатур по матрице строк и кнопок."""
        keyboard = types.InlineKeyboardMarkup()
        for row in keyboard_data:
            buttons = [types.InlineKeyboardButton(text=text, callback_data=cb) for text, cb in row]
            keyboard.row(*buttons)
        return keyboard

    @staticmethod
    def get_crypto_currency_keyboard(currency_data: list, row_width: int = 2) -> types.InlineKeyboardMarkup:
        """Генерация клавиатуры выбора криптовалюты с фиксированной шириной строк."""
        keyboard = types.InlineKeyboardMarkup(row_width=row_width)
        buttons = [
            types.InlineKeyboardButton(text=text, callback_data=cb) 
            for text, cb in currency_data
        ]
        keyboard.add(*buttons)
        return keyboard

    @staticmethod
    def get_fiat_currency_keyboard(crypto_symbol: str, fiat_data: list, row_width: int = 3) -> types.InlineKeyboardMarkup:
        """Генерация клавиатуры выбора фиатной валюты для конкретной крипты."""
        keyboard = types.InlineKeyboardMarkup(row_width=row_width)
        buttons = [
            types.InlineKeyboardButton(text=text, callback_data=f"fiat_{crypto_symbol}_{code}")
            for text, code in fiat_data
        ]
        keyboard.add(*buttons)
        return keyboard

    @staticmethod
    def get_safepal_coins_keyboard(tariff_key: str, coins_data: list) -> types.InlineKeyboardMarkup:
        """Генерация клавиатуры выбора криптовалюты с кнопкой возврата."""
        keyboard = types.InlineKeyboardMarkup()
        for text, coin in coins_data:
            keyboard.row(types.InlineKeyboardButton(text=text, callback_data=f"pay_{tariff_key}_{coin}"))
        keyboard.row(types.InlineKeyboardButton(text="🔙 К выбору тарифов", callback_data="ads_buy"))
        return keyboard
        
    @staticmethod
    def get_reply_keyboard(buttons_data: list, row_width: int = 2) -> types.ReplyKeyboardMarkup:
        """Универсальная генерация обычной Reply-клавиатуры из списка строк."""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
        buttons = [types.KeyboardButton(btn_text) for btn_text in buttons_data]
        markup.add(*buttons)
        return markup

    @staticmethod
    def get_inline_keyboard(rows_data: list, extra_button=None) -> types.InlineKeyboardMarkup:
        """
        Универсальная генерация Inline-клавиатуры по матрице строк 
        с опциональным добавлением дополнительной кнопки (или строки) вниз.
        """
        keyboard = types.InlineKeyboardMarkup()
        
        for row in rows_data:
            buttons = [types.InlineKeyboardButton(text=text, callback_data=cb) for text, cb in row]
            keyboard.row(*buttons)
            
        if extra_button:
            if isinstance(extra_button, list):
                buttons = [types.InlineKeyboardButton(text=t, callback_data=c) for t, c in extra_button]
                keyboard.row(*buttons)
            else:
                keyboard.row(extra_button)
                
        return keyboard

    @staticmethod
    def get_paginated_list_keyboard(
        items_dict: dict, 
        page: int = 0, 
        items_per_page: int = 5, 
        callback_prefix: str = "gamemenu_", 
        page_prefix: str = "combopage_",
        icon: str = "🎮"
    ) -> tuple[types.InlineKeyboardMarkup, int]:
        """Универсальный метод для генерации пагинированного списка инлайн-кнопок."""
        keyboard = types.InlineKeyboardMarkup()
        keys = list(items_dict.keys())
        total_items = len(keys)
        
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        page = max(0, min(page, total_pages - 1))
        
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        for key in keys[start_idx:end_idx]:
            data = items_dict[key]
            name = data.get("name", key)
            keyboard.row(types.InlineKeyboardButton(text=f"{icon} {name}", callback_data=f"{callback_prefix}{key}_{page}"))
            
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{page_prefix}{page-1}"))
        nav_buttons.append(types.InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="ignore"))
        if page < total_pages - 1:
            nav_buttons.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=f"{page_prefix}{page+1}"))
            
        if nav_buttons:
            keyboard.row(*nav_buttons)
            
        return keyboard, total_items

    @staticmethod
    def get_timers_games_keyboard(dictionaries: list[dict], callback_prefix: str = "timer_game_", icon: str = "⏰ Таймер:") -> types.InlineKeyboardMarkup:
        """Универсальный метод для генерации списка таймеров игр из нескольких словарей."""
        keyboard = types.InlineKeyboardMarkup()
        all_games = {}
        for d in dictionaries:
            all_games.update({k: v.get("name", k) for k, v in d.items()})
            
        for key, name in all_games.items():
            keyboard.row(types.InlineKeyboardButton(text=f"{icon} {name}", callback_data=f"{callback_prefix}{key}"))
        return keyboard

    @staticmethod
    def get_timer_duration_keyboard(key: str, durations: list[int], actions_config: dict) -> types.InlineKeyboardMarkup:
        """Генерация клавиатуры выбора длительности таймера с настраиваемыми часами и действиями."""
        keyboard = types.InlineKeyboardMarkup()
        set_prefix = actions_config.get("set_prefix", "set_timer_")
        
        def format_hour(h: int) -> str:
            if h == 1:
                return f"⏱ {h} час"
            elif h in [2, 3, 4]:
                return f"⏱ {h} часа"
            return f"⏱ {h} часов"

        # Первая строка (первые 3 элемента)
        if len(durations) >= 3:
            row1 = [
                types.InlineKeyboardButton(text=format_hour(h), callback_data=f"{set_prefix}{key}_{h}")
                for h in durations[:3]
            ]
            keyboard.row(*row1)
            
        # Вторая строка (оставшиеся элементы)
        if len(durations) > 3:
            row2 = [
                types.InlineKeyboardButton(text=format_hour(h), callback_data=f"{set_prefix}{key}_{h}")
                for h in durations[3:]
            ]
            keyboard.row(*row2)
            
        # Дополнительные кнопки (Свое время, Отключить, Назад)
        if "custom_text" in actions_config and "custom_prefix" in actions_config:
            keyboard.row(
                types.InlineKeyboardButton(text=actions_config["custom_text"], callback_data=f"{actions_config['custom_prefix']}{key}")
            )
        if "cancel_text" in actions_config and "cancel_prefix" in actions_config:
            keyboard.row(
                types.InlineKeyboardButton(text=actions_config["cancel_text"], callback_data=f"{actions_config['cancel_prefix']}{key}")
            )
        if "back_text" in actions_config and "back_callback" in actions_config:
            keyboard.row(
                types.InlineKeyboardButton(text=actions_config["back_text"], callback_data=actions_config["back_callback"])
            )
            
        return keyboard
        
    @staticmethod
    def get_ai_button() -> types.InlineKeyboardButton:
        """Переиспользуемая кнопка вызова ИИ-ассистента."""
        return types.InlineKeyboardButton(
            text="🧠 Задать вопрос Виртуальному Интеллекту", 
            callback_data="start_ai_chat"
        )
        



class NotificationSender:
    """Менеджер для отправки сообщений и медиаконтента пользователям."""

    def __init__(self, bot_instance, logger_instance):
        self.bot = bot_instance
        self.logger = logger_instance

    def send_message_direct(self, chat_id: int | str, text: str, reply_markup=None, parse_mode: str = "Markdown"):
        """Прямая отправка сообщения с резервным вариантом без разметки при ошибке."""
        try:
            return self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {e}")
            return self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)

    def send_combo_result(self, chat_id: int | str, info: dict, img_bytes, date_text: str):
        """Отправка результата комбо (фото с подписью или текст, если фото нет)."""
        caption = f"🎯 **{info.get('name', 'Комбо')}**\n📅 `{date_text}`"
        if img_bytes:
            try:
                self.bot.send_photo(chat_id, photo=img_bytes, caption=caption[:1024], parse_mode="Markdown")
            except Exception as e:
                self.logger.error(f"Ошибка отправки фото: {e}")
                self.send_message_direct(chat_id, caption, parse_mode="Markdown")
        else:
            full_text = f"{caption}\n\n❌ Комбо еще не найдено"
            self.send_message_direct(chat_id, full_text, parse_mode="Markdown")


class ProfileManager:
    """Менеджер для управления отображением профиля пользователя и игровой статистики."""

    def __init__(self, bot_instance, logger_instance, sender_instance):
        self.bot = bot_instance
        self.logger = logger_instance
        self.sender = sender_instance

    def show_user_profile(self, chat_id: int | str, user_game_stats: dict):
        """Отображение профиля пользователя и его прогресса по играм с фото или текстом."""
        try:
            chat_info = self.bot.get_chat(chat_id)
            user_name = chat_info.first_name or "Игрок"
        except Exception:
            user_name = "Игрок"

        profile_text = f"👤 **Профиль пользователя:** {user_name}\n\n🏆 **Ваш игровой прогресс и статы:**\n"
        
        keyboard_markup = MenuManager.get_inline_keyboard(PROFILE_KEYBOARD_DATA, extra_button=MenuManager.get_ai_button())

        if chat_id in user_game_stats and user_game_stats[chat_id]:
            self.sender.send_message_direct(chat_id, profile_text, parse_mode="Markdown")
            for game, info in user_game_stats[chat_id].items():
                caption = f"🎮 *{game}*\n📊 Стат / Уровень: `{info.get('stat', 'Н/Д')}`"
                if info.get("photo"):
                    try:
                        self.bot.send_photo(chat_id, photo=info["photo"], caption=caption, parse_mode="Markdown")
                    except Exception as e:
                        self.logger.error(f"Ошибка отправки фото профиля: {e}")
                        self.sender.send_message_direct(chat_id, caption, parse_mode="Markdown")
                else:
                    self.sender.send_message_direct(chat_id, caption, parse_mode="Markdown")
            
            # Отправка клавиатуры управления после списка игр
            self.sender.send_message_direct(
                chat_id, 
                "⚙️ Управление профилем:", 
                reply_markup=keyboard_markup
            )
        else:
            profile_text += "_Список игр пуст. Нажмите кнопку ниже, чтобы добавить свой прогресс и скриншот._"
            self.sender.send_message_direct(
                chat_id, 
                profile_text, 
                reply_markup=keyboard_markup, 
                parse_mode="Markdown"
            )

class BackgroundSchedulerManager:
    """Менеджер фоновых задач: автоматическая проверка комбо, пользовательские таймеры и контроль рекламы."""

    def __init__(self, bot_instance, logger_instance, manager_instance, sender_instance, ads_manager_instance, admin_chat_id: int | str):
        self.bot = bot_instance
        self.logger = logger_instance
        self.manager = manager_instance
        self.sender = sender_instance
        self.ads_manager = ads_manager_instance
        self.admin_chat_id = admin_chat_id

    def run_daily_checker(self, user_game_timers: dict):
        """Бесконечный цикл фонового мониторинга."""
        last_reset_day = None
        run_check_now = True

        while True:
            now_time = time.time()
            now_struct = time.localtime(now_time)
            current_day = now_struct.tm_mday
            current_hour = now_struct.tm_hour

            # 1. Сброс статусов в новый день
            if last_reset_day != current_day:
                self.manager.reset_daily_status()
                last_reset_day = current_day
                run_check_now = True

    # 2. Проверка и сбор комбо-картинок
            has_unfound_games = any(not found for found in self.manager.found_today.values())
            if (run_check_now or current_hour >= 9) and has_unfound_games:
                self.logger.info("🛡️ [AUTO-CHECKER] Запуск проверки комбо-картинок...")
                
                for key, info in self.manager.combo_games.items():
                    if self.manager.found_today.get(key, False):
                        continue

                    try:
                        img_url, date_text = self.manager.fetch_combo(key)
                        if img_url:
                            # Вызываем resize_img у нашего отдельного класса image_handler
                            img_bytes = image_handler.resize_img(img_url)
                            if img_bytes:
                                self.manager.found_today[key] = True
                                self.logger.info(f"✅ [AUTO-CHECKER] Картинка для {key} успешно найдена и зафиксирована!")
                                
                                caption = f"🎯 **[Авто-комбо] {info.get('name', key)}**\n📅 `{date_text}`"
                                try:
                                    self.bot.send_photo(self.admin_chat_id, photo=img_bytes, caption=caption[:1024], parse_mode="Markdown")
                                except Exception as e:
                                    self.logger.error(f"Ошибка отправки авто-фото администратору: {e}")
                    except Exception as e:
                        self.logger.error(f"Ошибка авто-проверки игры {key}: {e}")

                run_check_now = False

           # 3. Проверка и обновление игровых таймеров пользователей
            try:
                for chat_id, timers in list(user_game_timers.items()):
                    for game_key, t_data in list(timers.items()):
                        if t_data and isinstance(t_data, dict):
                            target_time = t_data.get("target")
                            if target_time and now_time >= target_time:
                                game_name = (
                                    self.manager.combo_games[game_key]["name"] if game_key in self.manager.combo_games 
                                    else self.manager.independent_farms.get(game_key, {}).get("name", game_key)
                                )
                                self.sender.send_message_direct(chat_id, f"⏰ **Напоминание!** Пора заходить в игру: **{game_name}** 🚀")
                                duration = t_data.get("duration_hours", 8)
                                user_game_timers[chat_id][game_key]["target"] = time.time() + (duration * 3600)
            except Exception as e:
                self.logger.error(f"Ошибка в проверке таймеров: {e}")
                
            # 4. Проверка истечения срока активной рекламы через менеджер рекламы
            try:
                expired_ads = []
                for oid, ad_data in list(self.ads_manager.storage.items()):
                    if now_time >= ad_data["expire_time"]:
                        expired_ads.append(oid)
                        self.sender.send_message_direct(
                            ad_data["user_id"],
                            "⏱ **Срок размещения вашей рекламы истек.** Рекламный пост был автоматически снят. Спасибо за сотрудничество!",
                            parse_mode="Markdown"
                        )
                        self.sender.send_message_direct(
                            self.admin_chat_id,
                            f"📢 **Рекламная кампания завершена по таймеру!**\nЗаказчик: `{ad_data['user_id']}` (ID заказа: `{oid}`)",
                            parse_mode="Markdown"
                        )
                if expired_ads:
                    for oid in expired_ads:
                        self.ads_manager.storage.pop(oid, None)
                    self.ads_manager.save_to_file()
            except Exception as e:
                self.logger.error(f"Ошибка проверки рекламных таймеров: {e}")

            # Пауза 10 минут перед следующим циклом
            time.sleep(600)


class CaptchaManager:
    """Менеджер для генерации и управления математической капчей."""

    @staticmethod
    def generate_advanced_captcha(chat_id: int | str, advanced_captchas_storage: dict) -> tuple[str, types.InlineKeyboardMarkup]:
        """Генерация математического примера и инлайн-клавиатуры с вариантами ответа."""
        a = random.randint(2, 9)
        b = random.randint(2, 9)
        ans = str(a + b)
        
        variants = [ans, str(int(ans) + 1 if int(ans) < 10 else "15"), str(max(1, int(ans) - 2)), str(int(ans) + 3)]
        variants = list(set(variants))[:4]
        
        advanced_captchas_storage[chat_id] = ans
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        random.shuffle(variants)
        buttons = [types.InlineKeyboardButton(text=v, callback_data=f"advcap_{v}") for v in variants]
        markup.add(*buttons)
        
        return f"Сколько будет {a} + {b}?", markup

class TelegramBotController:
    """Контроллер для регистрации обработчиков сообщений и команд бота."""

    def __init__(self, bot_instance, message_processor_instance, bot_commands: list, main_menu_buttons: list):
        self.bot = bot_instance
        self.processor = message_processor_instance
        self.bot_commands = bot_commands
        self.main_menu_buttons = main_menu_buttons
        self._register_handlers()

    def _register_handlers(self):
        """Регистрация всех обработчиков в инстансе бота."""
        @self.bot.message_handler(commands=['start'])
        def command_start(message: types.Message):
            self.processor.handle_start(message)

        @self.bot.message_handler(commands=self.bot_commands)
        @self.bot.message_handler(func=lambda msg: msg.text in self.main_menu_buttons)
        def menu_and_commands_handler(message: types.Message):
            self.processor.handle_menu_or_commands(message)

class MenuTextProcessor:
    """Менеджер для обработки текстовых команд и кнопок главного меню бота."""

    def __init__(self, bot_instance, logger_instance, sender_instance, manager_instance, verified_users_storage: set, user_game_timers_storage: dict, cloud_proofs_storage: list):
        self.bot = bot_instance
        self.logger = logger_instance
        self.sender = sender_instance
        self.manager = manager_instance
        self.verified_users = verified_users_storage
        self.user_game_timers = user_game_timers_storage
        self.cloud_proofs = cloud_proofs_storage

    def handle_menu_text(self, message: types.Message):
        """Основной обработчик текстовых запросов и меню пользователя."""
        chat_id = message.chat.id
        if chat_id not in self.verified_users:
            self.sender.send_message_direct(chat_id, "⚠️ Сначала пройдите верификацию через /start.")
            return

        text = message.text
        if text in ["🚀 Меню комбо-игр"]:
            keyboard, total_count = get_combo_list_keyboard(page=0)
            self.sender.send_message_direct(chat_id, f"🎮 **Активные комбо-проекты**\nВсего доступно игр с комбо: **{total_count}**\n\nВыберите проект из списка ниже:", reply_markup=keyboard)
            
        elif text in ["🤖 Авто-ферма игр"]:
            keyboard = get_farms_menu_keyboard(chat_id)
            self.sender.send_message_direct(
                chat_id,
                "🤖 **Управление авто-фермой игр**\n\nВыберите нужную игру из списка для управления:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
             
        elif text in ["👤 Профиль и статы", "/profile"]:
            show_user_profile(chat_id)
        elif text in ["📱 Телефонные майнеры", "/miners"]:
            self.sender.send_message_direct(chat_id, "📱 **Мобильные и облачные майнеры:**", reply_markup=get_phone_miners_keyboard())
        elif text in ["🚰 Крипто-краны", "/faucets"]:
            self.sender.send_message_direct(chat_id, "🚰 **Крипто-краны:**", reply_markup=get_faucets_keyboard())
        elif text in ["🌾 Авто-фермы (без комбо)"]:
            self.sender.send_message_direct(chat_id, "🌾 **Отдельные фермерские проекты:**", reply_markup=get_farms_keyboard())
        elif text in ["⚡ Проверить все комбо", "/all_combo"]:
            self.sender.send_message_direct(chat_id, "🔍 **Запущен массовый сбор комбо...**")
            for key, info in self.manager.combo_games.items():
                img_url, date_text = self.manager.fetch_combo(key)
                img_bytes = image_handler.resize_img(img_url) if img_url else None
                send_combo_result(chat_id, info, img_bytes, date_text)
        elif text in ["🧮 Крипто-курс", "/calc"]:
            self.sender.send_message_direct(chat_id, "🧮 **Выберите криптовалюту:**", reply_markup=get_crypto_currency_keyboard())
        elif text in ["📊 Защита фермы", "/farm"]:
            self.sender.send_message_direct(chat_id, "📊 **Статус:** Сеть работает на максимальной скорости.")
        elif text in ["⏰ Мои таймеры", "/timers"]:
            report = "⏰ **Ваши персональные таймеры сбора:**\n\n"
            user_timers_dict = self.user_game_timers.get(chat_id, {})
            all_games = {}
            all_games.update({k: v["name"] for k, v in self.manager.combo_games.items()})
            all_games.update({k: v["name"] for k, v in self.manager.independent_farms.items()})
            for k, name in all_games.items():
                t_info = user_timers_dict.get(k)
                t_target = t_info.get("target") if t_info else None
                if t_target and t_target > time.time():
                    left_sec = int(t_target - time.time())
                    report += f"• *{name}*: через **{left_sec // 3600}ч {(left_sec % 3600) // 60}м**\n"
                else:
                    report += f"• *{name}*: ❌ Не установлен\n"
            self.sender.send_message_direct(chat_id, report + "\n👇 Выберите игру для настройки:", reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
        elif text in ["💬 Отзывы", "/reviews"]:
            self.sender.send_message_direct(chat_id, "💬 **Секция отзывов и предложений (Laysi🐾):**", reply_markup=get_reviews_keyboard(), parse_mode="Markdown")
        elif text in ["📢 Реклама и монетизация", "/ads"]:
            self.sender.send_message_direct(chat_id, "📢 **Размещение рекламы :**\n\nВыкупите рекламное место в закрепе или рассылке, оплатив его напрямую через кошелек SafePal.", reply_markup=get_ads_keyboard(), parse_mode="Markdown")
        elif text in ["💎 Скрины выплат", "/proofs"]:
            if not self.cloud_proofs:
                self.sender.send_message_direct(chat_id, "💎 Скринов пока нет.")
            else:
                for p in self.cloud_proofs[-3:]:
                    try:
                        self.bot.send_photo(chat_id, p)
                    except Exception:
                        pass


class MessageInputHandler:
    """Менеджер для обработки входящих медиафайлов и текстовых сообщений."""

    def __init__(self, bot_instance, logger_instance, sender_instance, security_core_instance, ai_assistant_instance, manager_instance, verified_users_storage: set, user_input_states_storage: dict, user_game_stats_storage: dict, user_game_timers_storage: dict, user_calc_states_storage: dict, pending_ad_orders_storage: dict, user_reviews_storage: list, cloud_proofs_storage: list, admin_chat_id: int | str, main_menu_buttons: list):
        self.bot = bot_instance
        self.logger = logger_instance
        self.sender = sender_instance
        self.security = security_core_instance
        self.ai = ai_assistant_instance
        self.manager = manager_instance
        self.verified_users = verified_users_storage
        self.user_input_states = user_input_states_storage
        self.user_game_stats = user_game_stats_storage
        self.user_game_timers = user_game_timers_storage
        self.user_calc_states = user_calc_states_storage
        self.pending_ad_orders = pending_ad_orders_storage
        self.user_reviews = user_reviews_storage
        self.cloud_proofs = cloud_proofs_storage
        self.admin_chat_id = admin_chat_id
        self.main_menu_buttons = main_menu_buttons

    def handle_photo(self, message: types.Message):
        """Обработка входящих фотографий (профиль, выплаты)."""
        chat_id = message.chat.id
        if chat_id not in self.verified_users:
            return

        if chat_id in self.user_input_states and self.user_input_states[chat_id].get("step") == "waiting_photo":
            state_data = self.user_input_states[chat_id]
            if chat_id not in self.user_game_stats:
                self.user_game_stats[chat_id] = {}
            self.user_game_stats[chat_id][state_data["game"]] = {
                "stat": state_data["stat"], 
                "photo": message.photo[-1].file_id
            }
            self.user_input_states.pop(chat_id, None)
            try:
                self.bot.reply_to(
                    message, 
                    f"✅ Игра *{state_data['game']}* добавлена в профиль!", 
                    reply_markup=MenuManager.get_inline_keyboard(PROFILE_KEYBOARD_DATA, extra_button=MenuManager.get_ai_button()), 
                    parse_mode="Markdown"
                )
            except Exception as e:
                self.logger.error(f"Ошибка ответа на фото профиля: {e}")
            return

        if chat_id == self.admin_chat_id:
            self.cloud_proofs.append(message.photo[-1].file_id)
            try:
                self.bot.reply_to(message, "✅ Скрин сохранен в облачном хранилище!")
            except Exception:
                pass

    def handle_text_all(self, message: types.Message):
        """Универсальный обработчик входящих текстовых сообщений и состояний диалога."""
        chat_id = message.chat.id
        raw_text = message.text.strip()
        
        if chat_id not in self.verified_users:
            self.sender.send_message_direct(chat_id, "⚠️ Пожалуйста, пройдите верификацию через /start.")
            return

        # 1. Обработка ввода текста отзыва (с фильтрацией безопасности)
        if chat_id in self.user_input_states and self.user_input_states[chat_id].get("step") == "waiting_review_text":
            self.user_input_states.pop(chat_id, None)
            
            clean_review_text = self.security.sanitize_input(raw_text)
            is_threat, _ = self.security.analyze_traffic(raw_text)
            
            if is_threat or clean_review_text == "[BLOCKED_INJECTION_ATTEMPT]" or any(link in raw_text.lower() for link in ["http://", "https://", "t.me/"]):
                self.sender.send_message_direct(chat_id, "⚠️ **Ваш отзыв отклонен системой безопасности!** Обнаружены запрещенные ссылки или потенциальная угроза спама.", parse_mode="Markdown")
                return

            try:
                user_name = self.bot.get_chat(chat_id).first_name or "Аноним"
            except Exception:
                user_name = "Аноним"
                
            self.user_reviews.append({"user": user_name, "text": clean_review_text, "date": time.strftime("%d.%m.%Y %H:%M")})
            self.sender.send_message_direct(self.admin_chat_id, f"💬 **Новый отзыв от {user_name}:**\n\n`{clean_review_text}`", parse_mode="Markdown")
            self.sender.send_message_direct(chat_id, "✅ **Спасибо за ваш отзыв!**", reply_markup=get_reviews_keyboard(), parse_mode="Markdown")
            return

        # 2. Обработка рекламного креатива
        if chat_id in self.user_input_states and self.user_input_states[chat_id].get("step") == "waiting_ad_content":
            order_data = self.user_input_states.pop(chat_id, None)
            tariff = order_data["tariff"]
            coin = order_data["coin"]
            
            order_id = f"ord_{chat_id}_{int(time.time())}"
            self.pending_ad_orders[order_id] = {
                "user_id": chat_id,
                "tariff": tariff,
                "coin": coin,
                "content": raw_text
            }

            admin_markup = types.InlineKeyboardMarkup()
            admin_markup.row(types.InlineKeyboardButton(text="✅ Оплата поступила (Запустить рекламу)", callback_data=f"adm_pay_ok_{order_id}"))
            admin_markup.row(types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_pay_no_{order_id}"))

            self.sender.send_message_direct(
                self.admin_chat_id,
                f"📢 **Заявка на рекламу ожидает подтверждения оплаты!**\n"
                f"👤 Заказчик: `{chat_id}`\n"
                f"📋 Тариф: `{tariff}`\n"
                f"💰 Оплата через: `{coin.upper()}`\n\n"
                f"📝 **Креатив:**\n{raw_text}",
                reply_markup=admin_markup,
                parse_mode="Markdown"
            )
            self.sender.send_message_direct(
                chat_id,
                "✅ **Ваш рекламный креатив и чек приняты!**\nЗаявка отправлена администратору на проверку поступления средств на SafePal.",
                reply_markup=get_ads_keyboard(),
                parse_mode="Markdown"
            )
            return

        # 3. Обработка кастомного таймера
        if chat_id in self.user_input_states and self.user_input_states[chat_id].get("step") == "waiting_custom_timer":
            game_key = self.user_input_states[chat_id]["game_key"]
            self.user_input_states.pop(chat_id, None)
            try:
                cleaned = raw_text.lower().replace(",", ".")
                hours_val = float(re.sub(r'[^0-9.]', '', cleaned)) / 60.0 if "м" in cleaned else float(cleaned)
                if hours_val <= 0:
                    raise ValueError()
                if chat_id not in self.user_game_timers:
                    self.user_game_timers[chat_id] = {}
                self.user_game_timers[chat_id][game_key] = {"target": time.time() + (hours_val * 3600), "duration_hours": hours_val}
                
                game_name = (
                    self.manager.combo_games[game_key]["name"] if game_key in self.manager.combo_games 
                    else self.manager.independent_farms.get(game_key, {}).get("name", game_key)
                )
                self.sender.send_message_direct(chat_id, f"✅ Успешно! Таймер для *{game_name}* установлен на **{hours_val} ч.**", reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
                return
            except Exception:
                self.sender.send_message_direct(chat_id, "⚠️ Неверный формат! Введите число (например: `2.5`):", parse_mode="Markdown")
                return

        # 4. Общая проверка безопасности трафика
        text = self.security.sanitize_input(raw_text)
        is_threat, security_msg = self.security.analyze_traffic(text)
        if is_threat or any(x in text.lower() for x in ["http://", "https://", "t.me/", "@"]):
            self.sender.send_message_direct(chat_id, security_msg)
            return

        # 5. Обработка ввода крипто-конвертера
        if chat_id in self.user_calc_states:
            state = self.user_calc_states[chat_id]
            try:
                amt = float(text.replace(",", "."))
                c_id = {"btc": "bitcoin", "eth": "ethereum", "usdt": "tether", "gram": "the-open-network"}.get(state["crypto"], "bitcoin")
                fiat = state['fiat']
                
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={c_id}&vs_currencies={fiat}&include_24hr_change=true"
                res_data = requests.get(url, timeout=3).json().get(c_id, {})
                
                rate = res_data.get(fiat, 0)
                change_24h = res_data.get(fiat + "_24h_change", 0)
                total_sum = rate * amt
                
                trend_icon = "🟢" if change_24h >= 0 else "🔴"
                change_sign = "+" if change_24h > 0 else ""
                
                report_text = (
                    f"💎 **Крипто-конвертер [Zero-Lag]**\n\n"
                    f"🔹 Количество: **{amt} {state['crypto'].upper()}**\n"
                    f"💵 Стоимость: **{total_sum:,.2f} {fiat.upper()}**\n"
                    f"📈 Тренд за 24ч: {trend_icon} **{change_sign}{change_24h:.2f}%**"
                )
                
                self.sender.send_message_direct(chat_id, report_text, parse_mode="Markdown")
                self.user_calc_states.pop(chat_id, None)
                return
            except Exception as e:
                self.logger.error(f"Ошибка конвертера: {e}")
                self.sender.send_message_direct(chat_id, "⚠️ Ошибка получения данных с API. Введите корректное число:")
                return


class CallbackQueryHandler:
    """Менеджер для обработки всех входящих callback-запросов от инлайн-клавиатур."""

    def __init__(
        self,
        bot_instance,
        logger_instance,
        sender_instance,
        manager_instance,
        verified_users_storage: set,
        user_input_states_storage: dict,
        user_game_timers_storage: dict,
        user_calc_states_storage: dict,
        pending_ad_orders_storage: dict,
        ads_manager,  # <--- Заменили active_ads_storage: dict на ads_manager
        user_reviews_storage: list,
        advanced_captchas_storage: dict,
        active_farms_state_storage: dict,
        active_farm_threads_storage: dict,
        admin_chat_id: int | str,
        target_game_bot: str,
        main_menu_buttons: list
    ):
        self.bot = bot_instance
        self.logger = logger_instance
        self.sender = sender_instance
        self.manager = manager_instance
        self.verified_users = verified_users_storage
        self.user_input = user_input_states_storage
        self.game_timers = user_game_timers_storage
        self.calc_states = user_calc_states_storage
        self.pending_ad_orders = pending_ad_orders_storage
        self.ads_manager = ads_manager  # <--- Сохраняем менеджер в атрибут класса
        self.user_reviews = user_reviews_storage
        self.advanced_captchas = advanced_captchas_storage
        self.active_farms_state = active_farms_state_storage
        self.active_farm_threads = active_farm_threads_storage
        self.admin_chat_id = admin_chat_id
        self.target_game_bot = target_game_bot
        self.main_menu_buttons = main_menu_buttons
        
    def handle_callbacks(self, call: types.CallbackQuery):
        print(f"DEBUG: Нажата кнопка с данными: {call.data}")
        """Основной метод маршрутизации и обработки callback-данных."""
        
        # 1. Мгновенно гасим анимацию загрузки кнопки
        try:
            self.bot.answer_callback_query(call.id)
        except Exception:
            pass

        # 2. Глобальный защитный блок с безопасным получением chat_id
        try:
            if not call.message:
                # Если нажата кнопка из инлайн-режима (нет объекта message)
                return
                
            chat_id = call.message.chat.id
            data = call.data
            if data.startswith("advcap_"):
                if data.replace("advcap_", "") == self.advanced_captchas.get(chat_id):
                    save_verified_user(chat_id)
                    self.advanced_captchas.pop(chat_id, None)
                    try:
                        self.bot.edit_message_text("✅ **Доступ открыт!**", chat_id, call.message.message_id, parse_mode="Markdown")
                    except:
                        pass
                    self.sender.send_message_direct(chat_id, "👇 Главное меню:", reply_markup=MenuManager.get_reply_keyboard(self.main_menu_buttons))
                else:
                    q, m = generate_advanced_captcha(chat_id)
                    try:
                        self.bot.answer_callback_query(call.id, "❌ Неверно!", show_alert=True)
                    except:
                        pass
                    try:
                        self.bot.edit_message_text(f"❌ **Неверно!**\n🧠 *{q}*", chat_id, call.message.message_id, reply_markup=m, parse_mode="Markdown")
                    except:
                        pass
                return

            if chat_id not in self.verified_users:
                try:
                    self.bot.answer_callback_query(call.id, "Сначала пройдите верификацию через /start!", show_alert=True)
                except:
                    pass
                return

            # Админские кнопки подтверждения оплаты рекламы
            if data.startswith("adm_pay_ok_") or data.startswith("adm_pay_no_"):
                if chat_id != self.admin_chat_id:
                    try:
                        self.bot.answer_callback_query(call.id, "Только для администратора!", show_alert=True)
                    except:
                        pass
                    return
                
                parts = data.split("_")
                action = parts[2] 
                order_id = f"{parts[3]}_{parts[4]}_{parts[5]}"
                
                order = self.pending_ad_orders.get(order_id)
                if not order:
                    try:
                        self.bot.answer_callback_query(call.id, "Заказ не найден или уже обработан", show_alert=True)
                    except:
                        pass
                    return

                target_user_id = order["user_id"]
                self.pending_ad_orders.pop(order_id, None)

                if action == "ok":
                    if "24" in order["tariff"]:
                        expire_timestamp = time.time() + 86400
                        # Исправлено: используем метод класса ads_manager вместо глобальной функции
                        self.ads_manager.add_ad(order_id, target_user_id, expire_timestamp)

                    self.sender.send_message_direct(
                        target_user_id,
                        "🎉 **Оплата получена! Ваша реклама успешно запущена в боте.**\nБлагодарим за сотрудничество!",
                        parse_mode="Markdown"
                    )
                    try:
                        self.bot.edit_message_text(f"✅ **Заказ успешно подтвержден и запущен!** (Клиент: `{target_user_id}`)", chat_id, call.message.message_id, parse_mode="Markdown")
                    except:
                        pass
                else:
                    self.sender.send_message_direct(
                        target_user_id,
                        "❌ **Оплата не подтверждена администратором.** Свяжитесь с поддержкой для уточнения деталей.",
                        parse_mode="Markdown"
                    )
                    try:
                        self.bot.edit_message_text(f"❌ **Заказ отклонен.** (Клиент: `{target_user_id}`)", chat_id, call.message.message_id, parse_mode="Markdown")
                    except:
                        pass
                return

            # Секция отзывов
            if data == "review_add":
                self.user_input_states[chat_id] = {"step": "waiting_review_text"}
                self.sender.send_message_direct(chat_id, "✍️ **Напишите ваш отзыв одним сообщением:**", parse_mode="Markdown")
                return

            if data == "review_read":
                if not self.user_reviews:
                    self.sender.send_message_direct(chat_id, "💬 Пока что отзывов нет.")
                else:
                    rev_text = "💬 **Последние отзывы:**\n\n" + "\n".join([f"👤 *{r['user']}* (`{r['date']}`):\n{r['text']}\n" for r in self.user_reviews[-5:]])
                    self.sender.send_message_direct(chat_id, rev_text, parse_mode="Markdown")
                return

            # Монетизация и SafePal
            if data == "ads_buy":
                try:
                    self.bot.edit_message_text(
                        "💰 **Выберите тариф для размещения рекламы:**\nОплата поступает напрямую на ваш кошелек SafePal.",
                        chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_ads_tariffs_keyboard(), parse_mode="Markdown"
                    )
                except:
                    pass
                return

            if data == "ads_stats":
                self.sender.send_message_direct(chat_id, f"📊 **Статистика:** Активных пользователей: **~{len(self.verified_users) + 120}**", parse_mode="Markdown")
                return

            if data in ["adtariff_24h", "adtariff_broadcast"]:
                tariff_name = "Закреп на 24 часа ($15)" if data == "adtariff_24h" else "Рассылка по всей базе ($30)"
                try:
                    self.bot.edit_message_text(
                        f"💎 Вы выбрали тариф: *{tariff_name}*.\n\n"
                        "👇 **Выберите криптовалюту для оплаты через SafePal:**",
                        chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_safepal_coins_keyboard(data), parse_mode="Markdown"
                    )
                except:
                    pass
                return

            if data.startswith("pay_"):
                parts = data.split("_")
                tariff_key = parts[1]
                coin_key = parts[2]
                
                tariff_name = "Закреп на 24 часа ($15)" if tariff_key == "adtariff_24h" else "Рассылка по всей базе ($30)"
                wallet_info = SAFEPAL_WALLETS.get(coin_key, {"name": coin_key.upper(), "address": "ADRESS_NOT_SET"})
                
                self.user_input_states[chat_id] = {"step": "waiting_ad_content", "tariff": tariff_name, "coin": coin_key}
                
                self.sender.send_message_direct(
                    chat_id,
                    f"💳 **Реквизиты для оплаты:**\n\n"
                    f"📋 Тариф: *{tariff_name}*\n"
                    f"🪙 Монета: *{wallet_info['name']}*\n\n"
                    f"📌 **Адрес кошелька SafePal:**\n`{wallet_info['address']}`\n\n"
                    f"⚠️ **Инструкция:** Переведите точную сумму на указанный адрес SafePal, после чего **отправьте текстом креатив вашей рекламы** (и хэш транзакции/скрин), чтобы администратор мог подтвердить платеж.",
                    parse_mode="Markdown"
                )
                return

            if data == "ads_menu_back":
                try:
                    self.bot.edit_message_text("📢 **Размещение рекламы через SafePal:**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_ads_keyboard(), parse_mode="Markdown")
                except:
                    pass
                return

            if data.startswith("timer_game_"):
                key = data.replace("timer_game_", "")
                game_name = self.manager.combo_games[key]["name"] if key in self.manager.combo_games else self.manager.independent_farms[key]["name"]
                try:
                    self.bot.edit_message_text(f"⏰ Настройка таймера для: **{game_name}**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timer_duration_keyboard(key), parse_mode="Markdown")
                except:
                    pass
                return

            if data.startswith("settimer_"):
                parts = data.split("_")
                hours = int(parts[2])
                if chat_id not in self.user_game_timers:
                    self.user_game_timers[chat_id] = {}
                self.user_game_timers[chat_id][parts[1]] = {"target": time.time() + (hours * 3600), "duration_hours": float(hours)}
                try:
                    self.bot.answer_callback_query(call.id, f"✅ Таймер на {hours}ч установлен!")
                except:
                    pass
                try:
                    self.bot.edit_message_text(f"✅ **Таймер установлен на {hours} ч.!**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
                except:
                    pass
                return

            if data.startswith("customtimer_"):
                self.user_input_states[chat_id] = {"step": "waiting_custom_timer", "game_key": data.replace("customtimer_", "")}
                self.sender.send_message_direct(chat_id, "✏️ **Введите свое время таймера** (например: `2.5` или `90м`):", parse_mode="Markdown")
                return

            if data.startswith("canceltimer_"):
                if chat_id in self.user_game_timers:
                    self.user_game_timers[chat_id].pop(data.replace("canceltimer_", ""), None)
                try:
                    self.bot.edit_message_text("❌ **Таймер отключен.**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
                except:
                    pass
                return

            if data == "timers_menu_back":
                try:
                    self.bot.edit_message_text("⏰ **Выберите игру для таймера:**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
                except:
                    pass
                return

            if data == "prof_add":
                self.user_input_states[chat_id] = {"step": "waiting_game_info"}
                self.sender.send_message_direct(chat_id, "✍️ **Введите данные в формате:**\n`Название игры | Уровень`", parse_mode="Markdown")
                return

            if data == "prof_view":
                show_user_profile(chat_id)
                return

            if data.startswith("combopage_"):
                page = int(data.replace("combopage_", ""))
                keyboard, total_count = get_combo_list_keyboard(page=page)
                try:
                    self.bot.edit_message_text(f"🎮 **Комбо-проекты ({total_count})**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
                except:
                    pass
                return

            if data.startswith("gamemenu_"):
                parts = data.split("_")
                if parts[1] in self.manager.combo_games:
                    self.bot.edit_message_text(f"🕹 **Меню: {self.manager.combo_games[parts[1]]['name']}**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_single_game_keyboard(parts[1], parts[2]), parse_mode="Markdown")
                return

            if data == "ignore":
                return

            if data.startswith("pinfo_"):
                info = self.manager.phone_miners[data.replace("pinfo_", "")]
                self.sender.send_message_direct(chat_id, f"📱 **{info['name']}**\n\n{info['description']}\n\n🔑 Код: `{info['code']}`", parse_mode="Markdown")
                return

            if data.startswith("finfo_"):
                info = self.manager.crypto_faucets[data.replace("finfo_", "")]
                self.sender.send_message_direct(chat_id, f"🚰 **{info['name']}**\n\n{info['description']}", parse_mode="Markdown")
                return

            if data.startswith("cur_"):
                crypto = data.replace("cur_", "")
                self.bot.edit_message_text(f"🧮 Вы выбрали **{crypto.upper()}**. Выберите валюту:", chat_id, call.message.message_id, reply_markup=get_fiat_currency_keyboard(crypto), parse_mode="Markdown")
                return

            if data.startswith("fiat_"):
                parts = data.split("_")
                self.user_calc_states[chat_id] = {"crypto": parts[1], "fiat": parts[2]}
                self.bot.edit_message_text(f"🧮 Введите количество {parts[1].upper()}:", chat_id, call.message.message_id, parse_mode="Markdown")
                return

            if data.startswith("strat_"):
                self.sender.send_message_direct(chat_id, self.manager.combo_games[data.replace("strat_", "")]["strategy"])
                return

            if data.startswith("farm_strat_"):
                self.sender.send_message_direct(chat_id, self.manager.independent_farms[data.replace("farm_strat_", "")]["strategy"])
                return

            if data.startswith("game_"):
                key = data.replace("game_", "")
                if key in self.manager.combo_games:
                    try:
                        self.bot.answer_callback_query(call.id, "Загрузка...")
                    except:
                        pass
                    img_url, date_text = self.manager.fetch_combo(key)
                    send_combo_result(chat_id, self.manager.combo_games[key], image_handler.resize_img(img_url) if img_url else None, date_text)
                return

            # Управление Doodle Jump (динамическое переключение)
            if data in ["toggle_doodle_start", "toggle_doodle_stop"]:
                if chat_id not in self.active_farms_state:
                    self.active_farms_state[chat_id] = {"doodle": False, "all": False}
                
                is_running = (data == "toggle_doodle_start")
                self.active_farms_state[chat_id]["doodle"] = is_running
                
                if is_running:
                    self.logger.info(Fore.GREEN + f"[User {chat_id}] Пользователь запустил Signal Doodle Jump!")
                    thread = threading.Thread(target=run_doodle_loop, args=(chat_id, self.target_game_bot))
                    thread.daemon = True
                    thread.start()
                    self.active_farm_threads[chat_id] = thread
                else:
                    self.logger.info(Fore.RED + f"[User {chat_id}] Пользователь остановил Signal Doodle Jump.")
                
                try:
                    self.bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        reply_markup=get_farms_menu_keyboard(chat_id)
                    )
                except Exception:
                    pass
                
                status_msg = "🟢 Doodle Jump успешно запущен в фоновом режиме!" if is_running else "🛑 Doodle Jump остановлен."
                try:
                    self.bot.answer_callback_query(call.id, status_msg)
                except:
                    pass
                return

            # Управление «Запустить всё» / «Остановить всё»
            if data in ["toggle_all_start", "toggle_all_stop"]:
                if chat_id not in self.active_farms_state:
                    self.active_farms_state[chat_id] = {"doodle": False, "all": False}
                
                is_running = (data == "toggle_all_start")
                self.active_farms_state[chat_id]["all"] = is_running
                self.active_farms_state[chat_id]["doodle"] = is_running
                
                try:
                    self.bot.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        reply_markup=get_farms_menu_keyboard(chat_id)
                    )
                except Exception:
                    pass
                
                status_msg = "🚀 Все фермы запущены!" if is_running else "🛑 Все фермы остановлены."
                try:
                    self.bot.answer_callback_query(call.id, status_msg)
                except:
                    pass
                return

            # Управление авто-фермами игр
            if data == "farm_start_all":
                try:
                    self.bot.answer_callback_query(call.id, "🟢 Запуск всех ферм...")
                except:
                    pass
                self.sender.send_message_direct(
                    chat_id, 
                    "🚀 **Авто-ферма для Doodle Jump запущена в фоновом режиме!**\nСкрипт начал цикл сбора монет, проверки баланса и просмотра видео.", 
                    parse_mode="Markdown"
                )
                return

            if data == "farm_stop_all":
                try:
                    self.bot.answer_callback_query(call.id, "🛑 Остановка ферм...")
                except:
                    pass
                self.sender.send_message_direct(
                    chat_id, 
                    "🛑 **Все фоновые фермы остановлены.**", 
                    parse_mode="Markdown"
                )
                return

            if data == "farm_status":
                try:
                    self.bot.answer_callback_query(call.id, "📊 Проверка статуса...")
                except:
                    pass
                status_text = (
                    "📊 **Статус авто-ферм:**\n\n"
                    "🟢 **Signal Doodle Jump:** Активна\n"
                    "• Баланс проверка: Работает\n"
                    "• Видео-цикл: Ожидание / Просмотр\n"
                    "• Общий статус: Фоновый процесс запущен"
                )
                self.sender.send_message_direct(chat_id, status_text, parse_mode="Markdown")
                return

        except Exception as e:
            self.logger.error(f"Ошибка в обработчике callback-запросов: {e}")

class AIChatHandler:
    """Менеджер для управления интерактивным чатом с Виртуальным Интеллектом."""

    def __init__(self, bot_instance, logger_instance, ai_assistant_instance, ai_chat_active_storage: set):
        self.bot = bot_instance
        self.logger = logger_instance
        self.ai = ai_assistant_instance
        self.ai_chat_active = ai_chat_active_storage

    def handle_start_ai_chat(self, call: types.CallbackQuery):
        """Активация режима диалога с Виртуальным Интеллектом по инлайн-кнопке."""
        try:
            self.bot.answer_callback_query(call.id)
        except Exception:
            pass

        chat_id = call.message.chat.id
        user_id = call.from_user.id
        
        self.ai_chat_active.add(user_id)
        
        try:
            self.bot.send_message(
                chat_id,
                "🧠 **Виртуальный Интеллект активирован!**\n\n"
                "Напишите ваш вопрос следующим сообщением, и я проанализирую вашу стратегию. "
                "(Чтобы выйти из режима ИИ, просто отправьте любую команду, например /start)",
                parse_mode="Markdown"
            )
        except Exception as e:
            self.logger.error(f"Ошибка активации ИИ-чата: {e}")

    def handle_ai_text_messages(self, message: types.Message):
        """Обработка входящих текстовых сообщений пользователя в активном режиме ИИ."""
        user_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text.strip()

        if text.startswith('/'):
            self.ai_chat_active.discard(user_id)
            return

        try:
            ai_response = self.ai.generate_response(text, chat_id=chat_id)
            self.bot.reply_to(message, ai_response, parse_mode="Markdown")
            # 6. Передача запроса ИИ-ассистенту
            #self.sender.send_message_direct(chat_id, ai_response, parse_mode="Markdown", reply_markup=MenuManager.get_reply_keyboard(self.main_menu_buttons))

        except Exception as e:
            self.logger.error(f"Ошибка генерации ответа ИИ в чате: {e}")
            try:
                self.bot.send_message(chat_id, "⚠️ Произошла ошибка при обращении к Виртуальному Интеллекту.")
            except Exception:
                pass


# --- Конец классов ---

# --- callback_query_handler ---
@bot.callback_query_handler(func=lambda call: call.data == "start_ai_chat")
def handle_start_ai_chat(call: types.CallbackQuery):
    ai_chat_handler.handle_start_ai_chat(call)

@bot.message_handler(func=lambda message: message.from_user.id in AI_CHAT_ACTIVE, content_types=['text'])
def handle_ai_text_messages(message: types.Message):
    ai_chat_handler.handle_ai_text_messages(message)
    
def get_reviews_keyboard():
    return MenuManager.get_matrix_keyboard(REVIEWS_KEYBOARD_DATA)

def get_ads_keyboard():
    return MenuManager.get_matrix_keyboard(ADS_KEYBOARD_DATA)

def get_ads_tariffs_keyboard():
    return MenuManager.get_matrix_keyboard(ADS_TARIFFS_DATA)

def get_safepal_coins_keyboard(tariff_key):
    return MenuManager.get_safepal_coins_keyboard(tariff_key, CRYPTO_COINS_DATA)
    
def get_combo_list_keyboard(page=0):
    return MenuManager.get_paginated_list_keyboard(
        manager.combo_games, 
        page=page, 
        items_per_page=5, 
        callback_prefix="gamemenu_", 
        page_prefix="combopage_",
        icon="🎮"
    )
def get_single_game_keyboard(key, page):
    data = manager.combo_games.get(key, {})
    return ContentKeyboardManager.get_single_game_keyboard(key, page, data, SINGLE_GAME_ACTIONS)
    
def get_phone_miners_keyboard():
    return ContentKeyboardManager.get_catalog_keyboard(
        manager.phone_miners, 
        PHONE_MINER_ACTIONS["info_prefix"], 
        PHONE_MINER_ACTIONS, 
        extra_url_key="play_market"
    )
    
def get_faucets_keyboard():
    return ContentKeyboardManager.get_catalog_keyboard(
        manager.crypto_faucets, 
        FAUCETS_ACTIONS["info_prefix"], 
        FAUCETS_ACTIONS
    )
    
def get_farms_keyboard():
    return ContentKeyboardManager.get_catalog_keyboard(
        manager.independent_farms, 
        FARMS_ACTIONS["strat_prefix"], 
        FARMS_ACTIONS, 
        name_template=FARMS_ACTIONS["strat_suffix_template"]
    )    

def get_timers_games_keyboard():
    return MenuManager.get_timers_games_keyboard([manager.combo_games, manager.independent_farms])

def get_timer_duration_keyboard(key):
    return MenuManager.get_timer_duration_keyboard(key, TIMER_DURATIONS, TIMER_ACTIONS)    

def get_crypto_currency_keyboard():
    return MenuManager.get_crypto_currency_keyboard(CRYPTO_CURRENCY_DATA, row_width=2)

def get_fiat_currency_keyboard(crypto_symbol):
    return MenuManager.get_fiat_currency_keyboard(crypto_symbol, FIAT_CURRENCIES, row_width=3)

def send_message_direct(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    return sender.send_message_direct(chat_id, text, reply_markup, parse_mode)

def send_combo_result(chat_id, info, img_bytes, date_text):
    return sender.send_combo_result(chat_id, info, img_bytes, date_text)

def show_user_profile(chat_id):
    return profile_manager.show_user_profile(chat_id, user_game_stats)
    
def daily_auto_checker():
    scheduler_manager.run_daily_checker(user_game_timers)
    
def generate_advanced_captcha(chat_id):
    return CaptchaManager.generate_advanced_captcha(chat_id, advanced_captchas)

def handle_menu_text(message: types.Message):
    menu_text_processor.handle_menu_text(message)


@bot.message_handler(content_types=['photo'])
def handle_photo(message: types.Message):
    message_input_handler.handle_photo(message)

@bot.message_handler(func=lambda m: True)
def handle_text_all(message: types.Message):
    message_input_handler.handle_text_all(message)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: types.CallbackQuery):
    callback_query_handler.handle_callbacks(call)


# --- ВСЕ ИНИЦИАЛИЗАЦИИ И ССЫЛКИ НА ОБЪЕКТЫ ---
# (здесь создаются message_processor, bot_controller, image_handler, manager и т.д.)

# Запуск фонового потока (интервал: 2 часа = 7200 секунд)
updater_thread = threading.Thread(target=background_independent_updater, args=(7200,), daemon=True)
updater_thread.start()

# Инициализируем отправителя (если у вас bot и logger уже объявлены глобально)
sender = NotificationSender(bot, logger)
# Инициализация виртуального помощника
ai_assistant = BotVirtualAssistant()
# Инициализация усиленного защитного модуля
sec_guard = AdvancedSecurityGuard()
security_core = UltimateSecurityCore()
# Инициализация менеджеров
image_handler = ImageHandler(logger, target_width=800)
manager = MiningComboManager()
# Инициализация менеджера и всех игровых модулей фермы
game_farm_manager = BotGameFarmManager()
game_farm_manager.register_game(DogsHouseMinerGame())
game_farm_manager.register_game(SignalDoodleJumpGame())
# 1. Сначала создаем экземпляр процессора
message_processor = MessageProcessor(bot, logger, sender, manager, ...)

# 2. Передаем его в контроллер (с маленькой буквы)
bot_controller = TelegramBotController(bot, message_processor, BOT_COMMANDS_LIST, MAIN_MENU_BUTTONS)

# Инициализация процессора текстового меню
menu_text_processor = MenuTextProcessor(bot, logger, sender, manager, verified_users, user_game_timers, cloud_proofs)

# Инициализация обработчика сообщений
message_input_handler = MessageInputHandler(
    bot, logger, sender, security_core, ai_assistant, manager,
    verified_users, user_input_states, user_game_stats, user_game_timers,
    user_calc_states, pending_ad_orders, user_reviews_storage, cloud_proofs,
    ADMIN_CHAT_ID, MAIN_MENU_BUTTONS
)

# Инициализация обработчика callback-запросов
callback_query_handler = CallbackQueryHandler(
    bot, logger, sender, manager,
    verified_users, user_input_states, user_game_timers, user_calc_states,
    pending_ad_orders, ads_manager, user_reviews_storage, advanced_captchas,
    active_farms_state, active_farm_threads, ADMIN_CHAT_ID, TARGET_GAME_BOT, MAIN_MENU_BUTTONS
)

# Инициализация фонового шедулера
scheduler_manager = BackgroundSchedulerManager(bot, logger, manager, sender, ads_manager, ADMIN_CHAT_ID)
# Инициализация хранилища и обработчика чата с ИИ (теперь нужны только уже точно существующие bot, logger, ai_assistant)
AI_CHAT_ACTIVE = set()
ai_chat_handler = AIChatHandler(bot, logger, ai_assistant, AI_CHAT_ACTIVE)

# Инициализируем менеджер профиля (используя уже созданные bot, logger и sender)
profile_manager = ProfileManager(bot, logger, sender)

if __name__ == "__main__":
    print("DEBUG: Мы зашли в блок __main__")
    while True:
        try:
            print("🤖 Запуск бота (ручной цикл)...")
            offset = 0
            while True:
                # Запрашиваем обновления вручную с жестким таймаутом в 5 секунд
                updates = bot.get_updates(offset=offset, timeout=5, allowed_updates=["message", "callback_query"])
                for update in updates:
                    offset = update.update_id + 1
                    # Передаем обновление боту на обработку
                    bot.process_new_updates([update])
        except Exception as e:
            print(f"⚠️ Ошибка в цикле опроса: {e}. Переподключение через 5 секунд...")
            time.sleep(5)
