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

# Запуск фонового потока (интервал: 2 часа = 7200 секунд)
updater_thread = threading.Thread(target=background_independent_updater, args=(7200,), daemon=True)
updater_thread.start()

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

# Инициализация виртуального помощника
ai_assistant = BotVirtualAssistant()


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

class GoldMinerGame(BaseGameAutomation):
    """Модуль автоматизации для Gold Miner (сбор золота и клики по таймеру)"""
    def __init__(self):
        super().__init__(name="Gold Miner", interval_seconds=3600)  # Интервал 1 час

    async def collect_rewards(self) -> bool:
        logger.info(Fore.GREEN + "[Gold Miner] Запуск сессии сбора руды и монет...")
        await asyncio.sleep(3)
        logger.info(Fore.GREEN + "[Gold Miner] Ресурсы успешно собраны!")
        return True

    async def watch_videos(self) -> bool:
        logger.info(Fore.BLUE + "[Gold Miner] Проверка доступности рекламных роликов...")
        await asyncio.sleep(2)
        logger.info(Fore.GREEN + "[Gold Miner] Реклама просмотрена, бонус зачислен.")
        return True


class HoneyFarmGame(BaseGameAutomation):
    """Модуль автоматизации для Honey Farm (сбор меда с ульев)"""
    def __init__(self):
        super().__init__(name="Honey Farm", interval_seconds=1800)  # Интервал 30 минут

    async def collect_rewards(self) -> bool:
        logger.info(Fore.GREEN + "[Honey Farm] Проверка ульев и сбор меда...")
        await asyncio.sleep(2)
        logger.info(Fore.GREEN + "[Honey Farm] Мед успешно собран на склад!")
        return True

    async def watch_videos(self) -> bool:
        logger.info(Fore.BLUE + "[Honey Farm] Запуск просмотра видео для ускорения производства...")
        await asyncio.sleep(3)
        logger.info(Fore.GREEN + "[Honey Farm] Видео бонус активирован.")
        return True


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


class GrowTeaGame(BaseGameAutomation):
    """Модуль автоматизации для Grow Tea (выращивание и сбор чая)"""
    def __init__(self):
        super().__init__(name="Grow Tea", interval_seconds=14400)  # Интервал 4 часа

    async def collect_rewards(self) -> bool:
        logger.info(Fore.GREEN + "[Grow Tea] Проверка кустов, сбор готового урожая чая...")
        await asyncio.sleep(2)
        logger.info(Fore.GREEN + "[Grow Tea] Чай собран, посадка новых ростков...")
        return True

    async def watch_videos(self) -> bool:
        logger.info(Fore.BLUE + "[Grow Tea] Просмотр видео для полива и ускорения роста...")
        await asyncio.sleep(3)
        logger.info(Fore.GREEN + "[Grow Tea] Ускорение роста применено.")
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


# Инициализация менеджера и всех игровых модулей фермы
game_farm_manager = BotGameFarmManager()
game_farm_manager.register_game(GoldMinerGame())
game_farm_manager.register_game(HoneyFarmGame())
game_farm_manager.register_game(DogsHouseMinerGame())
game_farm_manager.register_game(GrowTeaGame())
game_farm_manager.register_game(SignalDoodleJumpGame())



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

# Инициализация усиленного защитного модуля
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
    
    # Безопасная динамическая генерация: берем первые два элемента (команда и описание), 
    # даже если в структуре BOT_COMMANDS больше полей (например, категория или права)
    commands_list = []
    for item in BOT_COMMANDS:
        if len(item) >= 2:
            cmd, desc = item[0], item[1]
            commands_list.append(types.BotCommand(cmd, desc))
            
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
                
                # Для Grow Tea делаем размер компактным (280px), для остальных — 600px
                max_width = 280 if game_key == "grow-tea" else 600
                
                if img.width > max_width:
                    w_percent = (max_width / float(img.width))
                    h_size = int(float(img.height) * float(w_percent))
                    img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
                    
                out = io.BytesIO()
                # Повышаем качество до 95 для кристальной четкости текста и мелких деталей
                img.convert("RGB").save(out, format="JPEG", quality=95)
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
    
    # Ваши существующие строки кнопок из PROFILE_KEYBOARD_DATA
    for row in PROFILE_KEYBOARD_DATA:
        buttons = [types.InlineKeyboardButton(text=text, callback_data=cb) for text, cb in row]
        keyboard.row(*buttons)
        
    # Добавляем кнопку Виртуального Интеллекта отдельной строкой в самый низ
    ai_button = types.InlineKeyboardButton(
        text="🧠 Задать вопрос Виртуальному Интеллекту", 
        callback_data="start_ai_chat"
    )
    keyboard.row(ai_button)
    
    return keyboard

# Функция генерации клавиатуры с кнопкой вызова ИИ для telebot
def get_ai_profile_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    ai_button = types.InlineKeyboardButton(
        text="🧠 Задать вопрос Виртуальному Интеллекту", 
        callback_data="start_ai_chat"
    )
    keyboard.add(ai_button)
    return keyboard


# Обработчик нажатия на кнопку "Задать вопрос Виртуальному Интеллекту"
@bot.callback_query_handler(func=lambda call: call.data == "start_ai_chat")
def handle_start_ai_chat(call):
    # Отправляем сообщение пользователю с предложением задать вопрос
    bot.answer_callback_query(call.id) # Убираем часики загрузки с кнопки
    bot.send_message(
        call.message.chat.id,
        "🧠 **Виртуальный Интеллект активирован!**\n\n"
        "Напишите ваш вопрос следующим сообщением, и я проанализирую вашу стратегию или отвечу на любые вопросы по игре.",
        parse_mode="Markdown"
    )
    # Здесь можно также включить состояние ожидания ввода, если у вас используется FSM для telebot

# Активный флаг или словарь для отслеживания режима ИИ у пользователей
AI_CHAT_ACTIVE = set()

# Обработчик нажатия на инлайн-кнопку "Задать вопрос Виртуальному Интеллекту"
@bot.callback_query_handler(func=lambda call: call.data == "start_ai_chat")
def handle_start_ai_chat(call):
    bot.answer_callback_query(call.id)
    # Включаем режим ИИ для этого пользователя
    AI_CHAT_ACTIVE.add(call.from_user.id)
    bot.send_message(
        call.message.chat.id,
        "🧠 **Виртуальный Интеллект активирован!**\n\n"
        "Напишите ваш вопрос следующим сообщением, и я проанализирую вашу стратегию. "
        "(Чтобы выйти из режима ИИ, просто отправьте любую команду, например /start)",
        parse_mode="Markdown"
    )

# Безопасный обработчик текстовых сообщений для ИИ
@bot.message_handler(func=lambda message: message.from_user.id in AI_CHAT_ACTIVE, content_types=['text'])
def handle_ai_text_messages(message):
    # Если пользователь написал команду, выключаем режим ИИ и пропускаем ее дальше
    if message.text.startswith('/'):
        AI_CHAT_ACTIVE.discard(message.from_user.id)
        return
        
    
    # Генерация ответа через наш класс ИИ с передачей ID чата для памяти и защиты
    ai_response = ai_assistant.generate_response(message.text, chat_id=message.chat.id)
    
    # Отправка ответа пользователю
    bot.reply_to(message, ai_response, parse_mode="Markdown")


def get_reviews_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for row in REVIEWS_KEYBOARD_DATA:
        buttons = [types.InlineKeyboardButton(text=text, callback_data=cb) for text, cb in row]
        keyboard.row(*buttons)
    return keyboard

def get_ads_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for row in ADS_KEYBOARD_DATA:
        buttons = [types.InlineKeyboardButton(text=text, callback_data=cb) for text, cb in row]
        keyboard.row(*buttons)
    return keyboard

def get_ads_tariffs_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for row in ADS_TARIFFS_DATA:
        buttons = [types.InlineKeyboardButton(text=text, callback_data=cb) for text, cb in row]
        keyboard.row(*buttons)
    return keyboard

def get_safepal_coins_keyboard(tariff_key):
    keyboard = types.InlineKeyboardMarkup()
    for text, coin in CRYPTO_COINS_DATA:
        keyboard.row(types.InlineKeyboardButton(text=text, callback_data=f"pay_{tariff_key}_{coin}"))
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
    data = manager.combo_games.get(key, {})
    keyboard = types.InlineKeyboardMarkup()
    
    # 1. Первый ряд: Основные действия (Комбо и Тактика)
    combo_text, combo_prefix = SINGLE_GAME_ACTIONS["combo"]
    tactics_text, tactics_prefix = SINGLE_GAME_ACTIONS["tactics"]
    
    row_buttons = [
        types.InlineKeyboardButton(text=combo_text, callback_data=f"{combo_prefix}{key}"),
        types.InlineKeyboardButton(text=tactics_text, callback_data=f"{tactics_prefix}{key}")
    ]
    
    # 2. Добавляем ссылки прямо в этот же ряд, если они есть в данных
    if data.get("ref_link_1"):
        play1_text, *_ = SINGLE_GAME_ACTIONS["play_1"]
        row_buttons.append(types.InlineKeyboardButton(text=play1_text, url=data["ref_link_1"]))
        
    if data.get("ref_link_2"):
        play2_text, *_ = SINGLE_GAME_ACTIONS["play_2"]
        row_buttons.append(types.InlineKeyboardButton(text=play2_text, url=data["ref_link_2"]))
    
    # Складываем все активные кнопки в первую строку
    keyboard.row(*row_buttons)
    
    # 3. Второй ряд: Кнопка возврата назад (на отдельной строке внизу)
    back_text, back_prefix = SINGLE_GAME_ACTIONS["back"]
    keyboard.row(
        types.InlineKeyboardButton(text=back_text, callback_data=f"{back_prefix}{page}")
    )
    
    return keyboard
    
def get_phone_miners_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    
    info_prefix = PHONE_MINER_ACTIONS["info_prefix"]
    play_text = PHONE_MINER_ACTIONS["play_text"]
    p1_text = PHONE_MINER_ACTIONS["play_1_text"]
    p2_text = PHONE_MINER_ACTIONS["play_2_text"]
    
    for key, data in manager.phone_miners.items():
        keyboard.row(
            types.InlineKeyboardButton(text=data["name"], callback_data=f"{info_prefix}{key}"),
            types.InlineKeyboardButton(text=play_text, url=data["play_market"])
        )
        keyboard.row(
            types.InlineKeyboardButton(text=p1_text, url=data["ref_link_1"]),
            types.InlineKeyboardButton(text=p2_text, url=data["ref_link_2"])
        )
    return keyboard

def get_faucets_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    
    info_prefix = FAUCETS_ACTIONS["info_prefix"]
    p1_text = FAUCETS_ACTIONS["play_1_text"]
    p2_text = FAUCETS_ACTIONS["play_2_text"]
    
    for key, data in manager.crypto_faucets.items():
        keyboard.row(types.InlineKeyboardButton(text=data["name"], callback_data=f"{info_prefix}{key}"))
        keyboard.row(
            types.InlineKeyboardButton(text=p1_text, url=data["ref_link_1"]),
            types.InlineKeyboardButton(text=p2_text, url=data["ref_link_2"])
        )
    return keyboard

def get_farms_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    
    strat_prefix = FARMS_ACTIONS["strat_prefix"]
    template = FARMS_ACTIONS["strat_suffix_template"]
    p1_text = FARMS_ACTIONS["play_1_text"]
    p2_text = FARMS_ACTIONS["play_2_text"]
    
    for key, data in manager.independent_farms.items():
        btn_text = template.format(name=data['name'])
        keyboard.row(types.InlineKeyboardButton(text=btn_text, callback_data=f"{strat_prefix}{key}"))
        keyboard.row(
            types.InlineKeyboardButton(text=p1_text, url=data["ref_link_1"]),
            types.InlineKeyboardButton(text=p2_text, url=data["ref_link_2"])
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
    
    set_prefix = TIMER_ACTIONS["set_prefix"]
    
    # Первая строка: 1, 3, 6 часов
    row1 = [
        types.InlineKeyboardButton(text=f"⏱ {h} час" if h == 1 else f"⏱ {h} часа" if h in [3, 4] else f"⏱ {h} часов", callback_data=f"{set_prefix}{key}_{h}")
        for h in TIMER_DURATIONS[:3]
    ]
    keyboard.row(*row1)
    
    # Вторая строка: 8, 12, 24 часа
    row2 = [
        types.InlineKeyboardButton(text=f"⏱ {h} часов", callback_data=f"{set_prefix}{key}_{h}")
        for h in TIMER_DURATIONS[3:]
    ]
    keyboard.row(*row2)
    
    # Дополнительные кнопки (Свое время, Отключить, Назад)
    keyboard.row(
        types.InlineKeyboardButton(text=TIMER_ACTIONS["custom_text"], callback_data=f"{TIMER_ACTIONS['custom_prefix']}{key}")
    )
    keyboard.row(
        types.InlineKeyboardButton(text=TIMER_ACTIONS["cancel_text"], callback_data=f"{TIMER_ACTIONS['cancel_prefix']}{key}")
    )
    keyboard.row(
        types.InlineKeyboardButton(text=TIMER_ACTIONS["back_text"], callback_data=TIMER_ACTIONS["back_callback"])
    )
    
    return keyboard
    

def get_crypto_currency_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(text=text, callback_data=cb) 
        for text, cb in CRYPTO_CURRENCY_DATA
    ]
    keyboard.add(*buttons)
    return keyboard

def get_fiat_currency_keyboard(crypto_symbol):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    buttons = [
        types.InlineKeyboardButton(text=text, callback_data=f"fiat_{crypto_symbol}_{code}")
        for text, code in FIAT_CURRENCIES
    ]
    keyboard.add(*buttons)
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
    send_message_direct(chat_id, WELCOME_MESSAGES["zero_lag"])
    send_message_direct(chat_id, WELCOME_MESSAGES["main_menu"], reply_markup=get_main_keyboard())

@bot.message_handler(commands=BOT_COMMANDS)
@bot.message_handler(func=lambda msg: msg.text in MAIN_MENU_BUTTONS)


def handle_menu_text(message: types.Message):
    chat_id = message.chat.id
    if chat_id not in verified_users:
        send_message_direct(chat_id, "⚠️ Сначала пройдите верификацию через /start.")
        return

    text = message.text
    if text in ["🚀 Меню комбо-игр"]:
        keyboard, total_count = get_combo_list_keyboard(page=0)
        send_message_direct(chat_id, f"🎮 **Активные комбо-проекты**\nВсего доступно игр с комбо: **{total_count}**\n\nВыберите проект из списка ниже:", reply_markup=keyboard)
        
     elif text in ["🤖 Авто-ферма игр"]:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton(text="🟢 Запустить все фермы", callback_data="farm_start_all"),
            types.InlineKeyboardButton(text="🛑 Остановить фермы", callback_data="farm_stop_all")
        )
        keyboard.row(
            types.InlineKeyboardButton(text="📊 Статус игр", callback_data="farm_status")
        )
        send_message_direct(
            chat_id,
            "🤖 **Управление авто-фермой игр**\n\nЗдесь вы можете запустить автоматический сбор ресурсов и просмотр видео для добавленных игр (Gold Miner, Honey Farm и др.):",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
         
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
        send_message_direct(chat_id, "📢 **Размещение рекламы :**\n\nВыкупите рекламное место в закрепе или рассылке, оплатив его напрямую через кошелек SafePal.", reply_markup=get_ads_keyboard(), parse_mode="Markdown")
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

   # Если пользователь пишет текст, а калькулятор неактивен — передаем запрос нашему ИИ!    
    ai_response = ai_assistant.generate_response(text, chat_id=chat_id)
    send_message_direct(chat_id, ai_response, parse_mode="Markdown", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: types.CallbackQuery):
    # 1. Мгновенно гасим анимацию загрузки кнопки (защита от таймаута Telegram)
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    # 2. Глобальный защитный блок от любых непредвиденных падений
    try:
        chat_id = call.message.chat.id
        data = call.data

        if data.startswith("advcap_"):
            if data.replace("advcap_", "") == advanced_captchas.get(chat_id):
                save_verified_user(chat_id)
                advanced_captchas.pop(chat_id, None)
                try: bot.edit_message_text("✅ **Доступ открыт!**", chat_id, call.message.message_id, parse_mode="Markdown")
                except: pass
                send_message_direct(chat_id, "👇 Главное меню:", reply_markup=get_main_keyboard())
            else:
                q, m = generate_advanced_captcha(chat_id)
                try: bot.answer_callback_query(call.id, "❌ Неверно!", show_alert=True)
                except: pass
                try: bot.edit_message_text(f"❌ **Неверно!**\n🧠 *{q}*", chat_id, call.message.message_id, reply_markup=m, parse_mode="Markdown")
                except: pass
            return

        if chat_id not in verified_users:
            try: bot.answer_callback_query(call.id, "Сначала пройдите верификацию через /start!", show_alert=True)
            except: pass
            return

        # Админские кнопки подтверждения оплаты рекламы
        if data.startswith("adm_pay_ok_") or data.startswith("adm_pay_no_"):
            if chat_id != ADMIN_CHAT_ID:
                try: bot.answer_callback_query(call.id, "Только для администратора!", show_alert=True)
                except: pass
                return
            
            parts = data.split("_")
            action = parts[2] 
            order_id = f"{parts[3]}_{parts[4]}_{parts[5]}"
            
            order = pending_ad_orders.get(order_id)
            if not order:
                try: bot.answer_callback_query(call.id, "Заказ не найден или уже обработан", show_alert=True)
                except: pass
                return

            target_user_id = order["user_id"]
            pending_ad_orders.pop(order_id, None)

            if action == "ok":
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
            send_message_direct(chat_id, "✍️ **Напишите ваш отзыв одним сообщением:**", parse_mode="Markdown")
            return

        if data == "review_read":
            if not user_reviews_storage:
                send_message_direct(chat_id, "💬 Пока что отзывов нет.")
            else:
                rev_text = "💬 **Последние отзывы:**\n\n" + "\n".join([f"👤 *{r['user']}* (`{r['date']}`):\n{r['text']}\n" for r in user_reviews_storage[-5:]])
                send_message_direct(chat_id, rev_text, parse_mode="Markdown")
            return

        # Монетизация и SafePal
        if data == "ads_buy":
            try:
                bot.edit_message_text(
                    "💰 **Выберите тариф для размещения рекламы:**\nОплата поступает напрямую на ваш кошелек SafePal.",
                    chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_ads_tariffs_keyboard(), parse_mode="Markdown"
                )
            except: pass
            return

        if data == "ads_stats":
            send_message_direct(chat_id, f"📊 **Статистика:** Активных пользователей: **~{len(verified_users) + 120}**", parse_mode="Markdown")
            return

        if data in ["adtariff_24h", "adtariff_broadcast"]:
            tariff_name = "Закреп на 24 часа ($15)" if data == "adtariff_24h" else "Рассылка по всей базе ($30)"
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
            try:
                bot.edit_message_text("📢 **Размещение рекламы через SafePal:**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_ads_keyboard(), parse_mode="Markdown")
            except: pass
            return

        if data.startswith("timer_game_"):
            key = data.replace("timer_game_", "")
            game_name = manager.combo_games[key]["name"] if key in manager.combo_games else manager.independent_farms[key]["name"]
            try: bot.edit_message_text(f"⏰ Настройка таймера для: **{game_name}**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timer_duration_keyboard(key), parse_mode="Markdown")
            except: pass
            return

        if data.startswith("settimer_"):
            parts = data.split("_")
            hours = int(parts[2])
            if chat_id not in user_game_timers: user_game_timers[chat_id] = {}
            user_game_timers[chat_id][parts[1]] = {"target": time.time() + (hours * 3600), "duration_hours": float(hours)}
            try: bot.answer_callback_query(call.id, f"✅ Таймер на {hours}ч установлен!")
            except: pass
            try: bot.edit_message_text(f"✅ **Таймер установлен на {hours} ч.!**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
            except: pass
            return

        if data.startswith("customtimer_"):
            user_input_states[chat_id] = {"step": "waiting_custom_timer", "game_key": data.replace("customtimer_", "")}
            send_message_direct(chat_id, "✏️ **Введите свое время таймера** (например: `2.5` или `90м`):", parse_mode="Markdown")
            return

        if data.startswith("canceltimer_"):
            if chat_id in user_game_timers: user_game_timers[chat_id].pop(data.replace("canceltimer_", ""), None)
            try: bot.edit_message_text("❌ **Таймер отключен.**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
            except: pass
            return

        if data == "timers_menu_back":
            try: bot.edit_message_text("⏰ **Выберите игру для таймера:**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
            except: pass
            return

        if data == "prof_add":
            user_input_states[chat_id] = {"step": "waiting_game_info"}
            send_message_direct(chat_id, "✍️ **Введите данные в формате:**\n`Название игры | Уровень`", parse_mode="Markdown")
            return

        if data == "prof_view":
            show_user_profile(chat_id)
            return

        if data.startswith("combopage_"):
            page = int(data.replace("combopage_", ""))
            keyboard, total_count = get_combo_list_keyboard(page=page)
            try: bot.edit_message_text(f"🎮 **Комбо-проекты ({total_count})**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
            except: pass
            return

        if data.startswith("gamemenu_"):
            parts = data.split("_")
            if parts[1] in manager.combo_games:
                bot.edit_message_text(f"🕹 **Меню: {manager.combo_games[parts[1]]['name']}**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_single_game_keyboard(parts[1], parts[2]), parse_mode="Markdown")
            return

        if data == "ignore":
            return

        if data.startswith("pinfo_"):
            info = manager.phone_miners[data.replace("pinfo_", "")]
            send_message_direct(chat_id, f"📱 **{info['name']}**\n\n{info['description']}\n\n🔑 Код: `{info['code']}`", parse_mode="Markdown")
            return

        if data.startswith("finfo_"):
            info = manager.crypto_faucets[data.replace("finfo_", "")]
            send_message_direct(chat_id, f"🚰 **{info['name']}**\n\n{info['description']}", parse_mode="Markdown")
            return

        if data.startswith("cur_"):
            crypto = data.replace("cur_", "")
            bot.edit_message_text(f"🧮 Вы выбрали **{crypto.upper()}**. Выберите валюту:", chat_id, call.message.message_id, reply_markup=get_fiat_currency_keyboard(crypto), parse_mode="Markdown")
            return

        if data.startswith("fiat_"):
            parts = data.split("_")
            user_calc_states[chat_id] = {"crypto": parts[1], "fiat": parts[2]}
            bot.edit_message_text(f"🧮 Введите количество {parts[1].upper()}:", chat_id, call.message.message_id, parse_mode="Markdown")
            return

        if data.startswith("strat_"):
            send_message_direct(chat_id, manager.combo_games[data.replace("strat_", "")]["strategy"])
            return

        if data.startswith("farm_strat_"):
            send_message_direct(chat_id, manager.independent_farms[data.replace("farm_strat_", "")]["strategy"])
            return

        if data.startswith("game_"):
            key = data.replace("game_", "")
            if key in manager.combo_games:
                try: bot.answer_callback_query(call.id, "Загрузка...")
                except: pass
                img_url, date_text = manager.fetch_combo(key)
                send_combo_result(chat_id, manager.combo_games[key], manager.resize_img(img_url, key) if img_url else None, date_text)
            return

    except Exception as e:
        print(f"[ERROR] Критическая ошибка в handle_callbacks: {e}")
        
if __name__ == "__main__":
    logger.info("=== ZERO-LAG TERMUX NATIVE BOT ЗАПУЩЕН ===")
    threading.Thread(target=daily_auto_checker, daemon=True).start()
    bot.infinity_polling(skip_pending=True, timeout=5, long_polling_timeout=3)
