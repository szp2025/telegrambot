import sys
import logging
import io
import random
import time
import threading
import re
import os
import socket
import requests
from bs4 import BeautifulSoup
from PIL import Image
import telebot
from telebot import types, apihelper
from PIL import Image
import urllib.request
import ast
import base64
import json
from datetime import datetime
import math
import subprocess
import shutil
import platform
import stat
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
    SUPPORTED_LANGS,
    MENU_LABELS,
    LABEL_TO_CANON,
    ALL_MENU_LABELS,
    TR,
    PROFILE_KEYBOARD_DATA,
    REVIEWS_KEYBOARD_DATA,
    ADS_KEYBOARD_DATA,
    ADS_TARIFFS_DATA,
    ADS_TARIFFS,
    VIP_TARIFFS,
    VIP_TARIFFS_DATA,
    CRYPTO_COINS_DATA,
    PAYMENT_METHODS,
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

# ============================================================
# 🌐 CONFIG MINI APP WEB (botv2) — interface stylée dans Telegram
# ============================================================
import hmac as _hmac
import hashlib as _hashlib
from urllib.parse import parse_qsl as _parse_qsl

# URL HTTPS publique du Mini App (tunnel cloudflared/ngrok vers ce téléphone).
# Priorité : variable d'env WEBAPP_URL > private_config.WEBAPP_URL > vide (web off).
try:
    from private_config import WEBAPP_URL as _CFG_WEBAPP_URL
except Exception:
    _CFG_WEBAPP_URL = ""
WEBAPP_URL = (os.environ.get("WEBAPP_URL") or _CFG_WEBAPP_URL or "").strip().rstrip("/")
WEBAPP_PORT = int(os.environ.get("WEBAPP_PORT", "8080"))

# Auto-tunnel : si aucune WEBAPP_URL n'est fournie, botv2 lance cloudflared
# tout seul et récupère l'URL HTTPS publique automatiquement (défaut : activé).
try:
    from private_config import WEBAPP_AUTOTUNNEL as _CFG_AUTOTUNNEL
except Exception:
    _CFG_AUTOTUNNEL = True
WEBAPP_AUTOTUNNEL = str(os.environ.get("WEBAPP_AUTOTUNNEL", _CFG_AUTOTUNNEL)).lower() not in ("0", "false", "no", "off", "")

# Flask est optionnel. S'il manque, on tente une installation auto (une fois) ;
# en dernier recours le bot tourne normalement avec le Mini App désactivé.
try:
    from flask import Flask, request, Response, jsonify
    _FLASK_OK = True
except Exception:
    _FLASK_OK = False
    try:
        print("📦 Flask absent — installation auto (pip install flask)...", flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "flask"], timeout=300)
        from flask import Flask, request, Response, jsonify
        _FLASK_OK = True
        print("✅ Flask installé automatiquement.", flush=True)
    except Exception as _flask_err:
        _FLASK_OK = False
        print(f"⚠️ Flask non installable ({_flask_err}). Mini App désactivé, le bot tourne quand même.", flush=True)


# ============================================================
# НАСТРОЙКИ СОЕДИНЕНИЯ С TELEGRAM API
# ============================================================

# Максимальное время установления TCP-соединения.
apihelper.CONNECT_TIMEOUT = 30

# Максимальное время ожидания HTTP-ответа.
apihelper.READ_TIMEOUT = 60

# Периодическое пересоздание HTTP-сессии.
# Помогает при ConnectionResetError после простоя соединения.
apihelper.SESSION_TIME_TO_LIVE = 5 * 60

# Автоматический повтор отдельных запросов при сетевых сбоях/таймаутах
# (первая линия защиты; вторая — супервайзер-цикл вокруг infinity_polling).
apihelper.RETRY_ON_ERROR = True


# Исторический идентификатор (оставлен для совместимости конструктора).
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
        """
        Готовит картинку под телефон:
        1) уменьшает (без увеличения) в компактный бокс;
        2) LETTERBOX — добавляет боковые поля до широкого формата 2:1, чтобы на
           мобильном высота была ограничена (широкая картинка = низкая высота).
        Поля берут цвет из угла картинки, чтобы сливаться с фоном.
        """
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                img = Image.open(io.BytesIO(res.content))
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 1) Только уменьшение в бокс.
                max_w = self.target_width
                max_h = int(self.target_width * 1.3)
                w, h = img.width, img.height
                scale = min(max_w / w, max_h / h, 1.0)
                if scale < 1.0:
                    img = img.resize(
                        (max(1, int(w * scale)), max(1, int(h * scale))),
                        Image.Resampling.LANCZOS
                    )

                # 2) Приводим к формату 2:1 (letterbox в ОБЕ стороны):
                #    • широкие картинки Telegram больше НЕ обрезает — добавляем поля
                #      сверху/снизу (весь комбо виден целиком);
                #    • высокие/квадратные делаем широкими (поля по бокам) → низкая
                #      высота на телефоне.
                target_ratio = 2.0
                cw, ch = img.width, img.height
                cur = (cw / ch) if ch else target_ratio
                if abs(cur - target_ratio) > 0.02:
                    if cur < target_ratio:                       # слишком «высокая» → поля по бокам
                        canvas_w, canvas_h = int(round(ch * target_ratio)), ch
                    else:                                         # слишком «широкая» → поля сверху/снизу
                        canvas_w, canvas_h = cw, int(round(cw / target_ratio))
                    try:
                        pad_color = img.getpixel((0, 0))
                        if not (isinstance(pad_color, tuple) and len(pad_color) == 3):
                            pad_color = (255, 255, 255)
                    except Exception:
                        pad_color = (255, 255, 255)
                    canvas = Image.new("RGB", (canvas_w, canvas_h), pad_color)
                    canvas.paste(img, ((canvas_w - cw) // 2, (canvas_h - ch) // 2))
                    img = canvas
                    # Ограничим итоговую ширину, чтобы файл не разрастался.
                    if img.width > 900:
                        r = 900 / img.width
                        img = img.resize((900, max(1, int(img.height * r))),
                                         Image.Resampling.LANCZOS)

                out = io.BytesIO()
                img.save(out, format="JPEG", quality=88)
                return out.getvalue()
        except Exception as e:
            self.logger.error(f"Ошибка обработки изображения: {e}")
        return None

class BotVirtualAssistant:
    """
    Локальный (офлайн) виртуальный интеллект — работает БЕЗ интернета и внешних API.

    Возможности:
    • Встроенная база знаний по теме бота (комбо, майнинг, краны, фарм, вывод,
      кошельки, безопасность, таймеры, курс, реклама).
    • Понимание вопроса по ключевым словам (нормализация + взвешенное сходство),
      а не по точному совпадению.
    • ОБУЧЕНИЕ прямо в диалоге: команда «запомни: вопрос = ответ» добавляет знание
      и сохраняет его в файл (переживает перезапуск бота).
    • Память контекста беседы по каждому пользователю.
    """

    KNOWLEDGE_FILE = "ai_knowledge.json"

    STOP_WORDS = {
        "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то",
        "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за",
        "бы", "по", "только", "ее", "мне", "было", "вот", "от", "меня", "о", "из",
        "для", "ну", "ли", "если", "или", "это", "эта", "этот", "мой", "есть",
        "быть", "чем", "the", "a", "to", "is", "of", "мне", "мы", "нам",
    }

    # Встроенная база: (список ключевых слов/фраз-триггеров, ответ).
    BASE_KNOWLEDGE = [
        (["комбо", "combo", "daily combo", "связка", "карты"],
         "🎯 Комбо (daily combo) — ежедневная связка карт/действий в tap-to-earn играх, "
         "которая даёт большой бонус монет. Открой «🚀 Меню комбо-игр», выбери игру и "
         "нажми «Открыть комбо» — увидишь актуальную комбинацию на сегодня."),
        (["майнинг", "майнер", "добыча", "mining"],
         "⛏️ Майнинг — пассивная добыча монет в приложении/боте. Раздел «📱 Телефонные "
         "майнеры»: выбери проект, установи и собирай монеты по таймеру. Регулярно заходи "
         "и смотри буст-видео, чтобы ускорить добычу."),
        (["кран", "краны", "faucet", "краник", "фаусет"],
         "🚰 Крипто-краны — сайты/боты, где дают маленькие суммы крипты за простые действия "
         "(клики, капча, задания). Смотри «🚰 Крипто-краны». Выводи на сеть с низкой "
         "комиссией (TON или USDT-TRC20)."),
        (["ферма", "фарм", "farming", "фармить"],
         "🌾 Фарм — регулярный сбор наград в игре. Настрой «⏰ Мои таймеры» — бот будет "
         "напоминать, когда пора зайти собрать монеты и посмотреть видео."),
        (["вывод", "вывести", "withdraw", "снять"],
         "💸 Для вывода нужен криптокошелёк. Дождись минимальной суммы в проекте, укажи адрес "
         "своей сети (TON, TRC20, BTC) и подтверди. ВСЕГДА проверяй сеть — при неверной сети "
         "средства теряются безвозвратно."),
        (["кошелек", "кошелёк", "wallet", "safepal", "seed", "фраза"],
         "👛 Кошелёк хранит твою крипту. НИКОГДА и НИКОМУ не показывай seed-фразу (12/24 слова) "
         "— это полный доступ к деньгам. Храни её офлайн, на бумаге."),
        (["безопасность", "скам", "мошенник", "развод", "scam", "обман"],
         "🛡️ Безопасность: не вводи seed-фразу на сайтах, не переходи по подозрительным ссылкам, "
         "не отправляй крипту «для разблокировки вывода». Обещают лёгкие деньги за предоплату — "
         "это скам."),
        (["таймер", "напоминание", "timer", "напомнить"],
         "⏰ Открой «⏰ Мои таймеры», выбери игру и интервал — бот будет присылать напоминание "
         "со ссылкой прямо на игру каждые несколько часов."),
        (["курс", "цена", "стоимость", "price", "конвертер", "сколько стоит"],
         "🧮 Раздел «🧮 Крипто-курс»: выбери монету и валюту, введи количество — бот покажет "
         "актуальную стоимость и тренд за 24 часа."),
        (["реклама", "рекламу", "ads", "разместить"],
         "📢 Раздел «📢 Реклама и монетизация» → выбери тариф → способ оплаты (BTC/TON) → "
         "пришли текст объявления и хэш транзакции. Оплата проверяется автоматически по хэшу."),
        (["привет", "здравствуй", "хай", "hello", "hi", "здарова", "прив"],
         "👋 Привет! Я помощник по крипте, майнингу и комбо-играм. Спроси про комбо, фарм, "
         "краны, вывод средств или безопасность."),
        (["спасибо", "благодарю", "thanks", "спс"],
         "🙌 Всегда пожалуйста! Будут вопросы по крипте или играм — пиши."),
        (["кто ты", "что умеешь", "помощь", "help", "команды", "умеешь"],
         "🧠 Я локальный ИИ-помощник бота. Объясняю про комбо, майнинг, краны, фарм, вывод и "
         "безопасность, считаю по твоим числам, советую тактику по играм и проверяю ссылки на "
         "скам. Меня можно обучать: напиши «запомни: вопрос = ответ»."),

        # --- Криптовалюты и сети ---
        (["биткоин", "bitcoin", "btc", "битка"],
         "₿ Bitcoin (BTC) — первая и главная криптовалюта. Медленные подтверждения (~10–30 мин) "
         "и заметная комиссия сети. Для мелких сумм лучше USDT-TRC20 или TON — быстрее и дешевле."),
        (["тон", "ton", "toncoin", "the open network"],
         "💎 TON (Toncoin) — быстрая и дешёвая сеть, тесно связана с Telegram. Удобна для мелких "
         "выплат и внутриигровых наград. Кошелёк можно открыть прямо в Telegram (@wallet)."),
        (["usdt", "тизер", "tether", "стейбл", "стейблкоин", "юсдт"],
         "💵 USDT (Tether) — стейблкоин, ~1$ всегда. Есть в разных сетях: TRC20 (Tron) — дёшево и "
         "быстро, ERC20 (Ethereum) — дорого. Всегда выбирай ту же сеть, что и получатель!"),
        (["сеть", "network", "trc20", "erc20", "bep20", "какая сеть"],
         "🌐 Сеть — это «дорога», по которой идёт перевод. TRC20 (Tron) и TON — дешёвые и быстрые; "
         "ERC20 (Ethereum) — дорогой. КРИТИЧЕСКИ важно: отправитель и получатель должны быть в "
         "ОДНОЙ сети, иначе средства теряются навсегда."),
        (["комиссия", "комисия", "fee", "газ", "gas", "сколько комиссия"],
         "⛽ Комиссия (fee/gas) — плата сети за перевод. В BTC/ERC20 она высокая, в TON и TRC20 — "
         "копейки. Для частых мелких выводов выбирай TON или USDT-TRC20."),
        (["купить крипту", "где купить", "p2p", "обмен", "обменник", "поменять"],
         "🔁 Купить/обменять крипту можно на биржах (P2P) или в проверенных обменниках. Никогда "
         "не переводи деньги «частнику» из ЛС без гаранта — это классический развод."),

        # --- Безопасность (углублённо) ---
        (["seed", "сид", "фраза", "мнемоника", "12 слов", "24 слова"],
         "🔑 Seed-фраза (12/24 слова) = ПОЛНЫЙ доступ к кошельку. Кто её знает — заберёт все деньги. "
         "Правила: записать на бумаге, хранить офлайн, НИКОМУ не показывать, НИКУДА не вводить, "
         "кроме восстановления своего же кошелька. Поддержка НИКОГДА её не спрашивает."),
        (["2fa", "двухфактор", "двухфакторная", "гугл аутентификатор", "authenticator"],
         "🔐 2FA (двухфакторная аутентификация) — второй код при входе (Google Authenticator). "
         "Обязательно включай на биржах и в кошельках. Не используй SMS, если есть приложение-"
         "аутентификатор — SMS перехватывают."),
        (["дрейнер", "drainer", "подключить кошелек", "connect wallet", "подпись", "approve"],
         "🚱 Дрейнер — вредоносный сайт, который просит «подключить кошелёк» или подписать "
         "транзакцию и опустошает баланс. Не подключай кошелёк к незнакомым сайтам, проверяй, "
         "что именно подписываешь, отзывай лишние разрешения (revoke)."),
        (["фейк", "поддержка", "support", "админ пишет", "написал админ", "техподдержка"],
         "🎭 Настоящая поддержка НИКОГДА не пишет первой в ЛС и не просит seed-фразу, пароль или "
         "предоплату «за разблокировку». Любой, кто это делает, — мошенник. Проверяй юзернеймы: "
         "@s_upp0rt и подобные подмены — скам."),
        (["предоплата", "разблокировка вывода", "комиссия за вывод", "заплати чтобы вывести"],
         "🚨 Классический развод: «внеси предоплату/комиссию, чтобы разблокировать вывод». "
         "Настоящий вывод НИКОГДА не требует сначала прислать деньги. Это 100% скам — не плати."),
        (["холодный кошелек", "аппаратный", "ledger", "trezor", "hardware"],
         "🧊 Холодный (аппаратный) кошелёк (Ledger/Trezor) хранит ключи офлайн — самый безопасный "
         "способ для крупных сумм. Для мелких игровых наград достаточно обычного (горячего) "
         "кошелька, но seed всё равно береги."),

        # --- Заработок и механика бота ---
        (["заработать", "доход", "сколько можно заработать", "как заработать", "профит"],
         "💰 Честно: на кранах, комбо и tap-to-earn заработок небольшой и требует регулярности. "
         "Реальные плюсы — из ретро-дропов (airdrop) и рефералов. Не вкладывай деньги в проекты, "
         "которые обещают «иксы» — почти всегда это скам."),
        (["airdrop", "аирдроп", "дроп", "раздача токенов"],
         "🪂 Airdrop (дроп) — бесплатная раздача токенов за активность в проекте. Легитимные дропы "
         "НЕ просят seed-фразу и предоплату. Делай задания заранее и жди листинга токена."),
        (["реферал", "рефка", "реф", "пригласить", "referral"],
         "👥 Реферальная программа — ты получаешь % от активности приглашённых. Делись своей "
         "реф-ссылкой из проекта. Это один из самых стабильных способов заработка в таких ботах."),
        (["минималка", "минимальная сумма", "минимум для вывода", "порог вывода"],
         "📉 Минималка — наименьшая сумма, которую можно вывести. Пока не накопил её — вывод "
         "недоступен. Копи, собирай ежедневно и подключай рефералов, чтобы дойти до порога быстрее."),
        (["не приходит вывод", "вывод завис", "не пришли деньги", "где мои деньги"],
         "⏳ Если вывод не пришёл: 1) проверь статус транзакции по хэшу в блокчейн-эксплорере; "
         "2) убедись, что указал ВЕРНУЮ сеть и адрес; 3) иногда сеть перегружена — подожди. "
         "Если проект просит доплатить «за разблокировку» — это скам."),
        (["верификация", "капча", "не пройти", "start", "/start", "доступ"],
         "✅ Чтобы получить доступ к боту, пройди простую капчу по команде /start (реши пример). "
         "Это защита от ботов и спамеров. После верификации откроется главное меню."),
        (["скрины выплат", "пруфы", "proofs", "доказательства", "выплаты реальные"],
         "💎 Раздел «💎 Скрины выплат» показывает реальные скриншоты выводов. Это помогает "
         "убедиться, что проекты платят. Но всегда перепроверяй актуальность сам."),
        (["волатильность", "риск", "падение", "просадка", "risk"],
         "📉 Крипта волатильна — цена может резко падать и расти. Никогда не вкладывай больше, чем "
         "готов потерять, и не бери кредиты под крипту. Стейблкоины (USDT) не колеблются в цене."),
        (["телеграм кошелек", "@wallet", "telegram wallet", "кошелек в телеграм"],
         "📲 В Telegram есть встроенный кошелёк (@wallet) — удобно принимать TON и USDT прямо в "
         "мессенджере, без отдельного приложения. Подходит для мелких игровых выплат."),
    ]

    def __init__(self, model_name: str = "Local Self-Learning AI"):
        self.model_name = model_name
        self.session_memory = {}          # {chat_id: [последние реплики]}
        self.is_offline_mode = True
        self.learned = self._load_learned()   # [{"keys": [...], "answer": "..."}]

    # ---------- Персистентность выученных знаний ----------
    def _load_learned(self):
        if os.path.exists(self.KNOWLEDGE_FILE):
            try:
                with open(self.KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                logger.error(f"Ошибка загрузки базы знаний ИИ: {e}")
        return []

    def _save_learned(self):
        try:
            with open(self.KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.learned, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения базы знаний ИИ: {e}")

    def set_offline_status(self, status: bool):
        self.is_offline_mode = status

    # ---------- Обработка текста ----------
    def _tokens(self, text: str):
        words = re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9]+', (text or "").lower())
        return [w for w in words if w not in self.STOP_WORDS and len(w) > 2]

    def _score(self, query_tokens, key_tokens) -> float:
        """Мягкое сходство по пересечению множеств слов."""
        qset, kset = set(query_tokens), set(key_tokens)
        if not qset or not kset:
            return 0.0
        overlap = len(qset & kset)
        if overlap == 0:
            return 0.0
        return overlap / (len(kset) ** 0.5) + overlap / (len(qset) ** 0.5)

    def _best_answer(self, query: str):
        q_tokens = self._tokens(query)
        q_lower = query.lower()
        best_answer, best_score = None, 0.0

        # 1) Выученные знания — приоритет обучению пользователя.
        for item in self.learned:
            keys = item.get("keys", [])
            score = self._score(q_tokens, self._tokens(" ".join(keys)))
            for k in keys:
                if k and k.lower() in q_lower:      # прямое попадание фразы
                    score += 2.0
            if score > best_score:
                best_score, best_answer = score, item.get("answer")

        # 2) Встроенная база знаний.
        for keys, answer in self.BASE_KNOWLEDGE:
            score = self._score(q_tokens, self._tokens(" ".join(keys)))
            for k in keys:
                if k in q_lower:                    # прямое попадание ключа
                    score += 1.6
            if score > best_score:
                best_score, best_answer = score, answer

        return best_answer, best_score

    # ---------- Обучение прямо в диалоге ----------
    def _try_learn(self, text: str, is_admin: bool):
        """
        Ловит команды обучения: «запомни: вопрос = ответ» (также научи/выучи,
        разделители = => | — ::). Возвращает текст подтверждения или None.
        """
        m = re.match(r'^\s*(?:запомни|научи|выучи|обучись)\b\s*[:\-]?\s*(.+)$',
                     text, re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        if not is_admin:
            return ("🔒 Обучать ИИ может только администратор. "
                    "Задай вопрос обычным текстом — я постараюсь ответить.")
        body = m.group(1)
        parts = re.split(r'\s*(?:=>|=|\||—|::)\s*', body, maxsplit=1)
        if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
            return ("⚠️ Формат обучения: «запомни: вопрос = ответ».\n"
                    "Например: запомни: когда сброс комбо = каждый день в 09:00 UTC")
        question, answer = parts[0].strip(), parts[1].strip()
        keys = list(dict.fromkeys(self._tokens(question) + [question.lower()]))
        self.learned.append({"keys": keys, "answer": answer})
        self._save_learned()
        return f"✅ Запомнил! Теперь на «{question}» я отвечу так:\n\n{answer}"

    # ---------- Калькулятор (безопасный, без eval произвольного кода) ----------
    def _safe_eval(self, expr: str):
        """Безопасно вычисляет арифметическое выражение через ast (только числа и + - * / // % **)."""
        try:
            node = ast.parse(expr, mode="eval")
        except Exception:
            return None
        allowed = (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Num,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
            ast.USub, ast.UAdd,
        )
        for n in ast.walk(node):
            if not isinstance(n, allowed):
                return None
            if isinstance(n, ast.Constant) and not isinstance(n.value, (int, float)):
                return None
            # Защита от гигантских степеней (2**999999 повесит бота).
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow):
                r = n.right
                if isinstance(r, ast.Constant) and isinstance(r.value, (int, float)) and r.value > 1000:
                    return None
        try:
            val = eval(compile(node, "<calc>", "eval"), {"__builtins__": {}}, {})
            if isinstance(val, (int, float)) and abs(val) < 1e15:
                return val
        except Exception:
            return None
        return None

    def _try_math(self, text: str):
        """Считает по данным пользователя: проценты, сложный процент (прогноз) и обычную арифметику."""
        t = text.lower().replace(",", ".").replace("^", "**").replace("×", "*").replace("÷", "/")

        # 1) «X% от Y»
        m = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:от|of|из)\s*(\d+(?:\.\d+)?)', t)
        if m:
            x, y = float(m.group(1)), float(m.group(2))
            return f"🧮 {m.group(1)}% от {m.group(2)} = {x / 100 * y:g}"

        # 2) Прогноз со сложным процентом: старт, ставка%/день, срок в днях.
        if any(w in t for w in ["день", "дн", "days", "сут"]):
            m = re.search(
                r'(\d+(?:\.\d+)?)\D+?(\d+(?:\.\d+)?)\s*%\D+?(\d+(?:\.\d+)?)\s*(?:дн|день|дней|days|сут)',
                t
            )
            if m:
                base, rate, days = float(m.group(1)), float(m.group(2)), float(m.group(3))
                if 0 < days <= 3650:
                    total = base * (1 + rate / 100.0) ** days
                    profit = total - base
                    return (
                        "📈 Прогноз (сложный процент):\n"
                        f"Старт: {base:g} | ставка: {rate:g}%/день | срок: {int(days)} дн.\n"
                        f"Итог: ≈ {total:,.2f} (прибыль ≈ {profit:,.2f})\n"
                        "⚠️ Это оценка: реальные проценты в играх меняются."
                    )

        # 3) Обычное арифметическое выражение (если есть хотя бы один оператор).
        math_only = re.sub(r'[^0-9+\-*/().\s]', ' ', t)
        if re.search(r'\d', math_only) and re.search(r'[-+*/]', math_only):
            expr = re.sub(r'\s+', ' ', math_only).strip()
            val = self._safe_eval(expr)
            if val is not None:
                return f"🧮 {expr} = {val:g}"
        return None

    # ---------- Советник по тактике игр ----------
    def _try_tactic(self, query: str):
        """Подсказывает тактику по конкретной игре (берёт strategy из конфига)."""
        q = query.lower()
        tactic_words = ["тактик", "стратег", "совет", "гайд", "как играть",
                        "как пройти", "как выигр", "как фарм", "что делать"]
        wants_tactic = any(w in q for w in tactic_words)

        mgr = globals().get("manager")
        if mgr is None:
            return None
        games = {}
        try:
            games.update(mgr.combo_games)
            games.update(mgr.independent_farms)
        except Exception:
            return None

        # Ищем упомянутую в вопросе игру (по имени или ключу).
        for key, data in games.items():
            name_words = re.findall(r'[a-zа-яё0-9]+', str(data.get("name", "")).lower())
            key_words = re.findall(r'[a-z0-9]+', key.lower())
            if any(len(w) > 2 and w in q for w in name_words + key_words):
                strat = data.get("strategy")
                if strat:
                    return f"🎮 Тактика — {data.get('name', key)}:\n\n{strat}"
                return (f"🎮 По игре «{data.get('name', key)}» отдельной тактики пока нет. "
                        "Общий принцип: собирай пассив по таймеру, смотри буст-видео, "
                        "копи на апгрейды и не пропускай ежедневное комбо.")

        # Тактика вообще, без конкретной игры.
        if wants_tactic:
            names = ", ".join(str(d.get("name", k)) for k, d in list(games.items())[:12])
            return ("🎮 По какой игре нужна тактика? Доступные проекты: " + names + ".\n"
                    "Общий совет: заходи по таймеру, собирай пассив, смотри буст-видео, "
                    "копи на апгрейды и обязательно бери ежедневное комбо.")
        return None

    # ---------- Основной вход ----------
    def generate_response(self, userQuery: str, chat_id: int = 0) -> str:
        userQuery = (userQuery or "").strip()
        if not userQuery:
            return "🤔 Задай вопрос словами — и я постараюсь помочь."

        # Память диалога (последние 8 реплик пользователя).
        hist = self.session_memory.setdefault(chat_id, [])
        hist.append(userQuery)
        if len(hist) > 8:
            del hist[:len(hist) - 8]

        # 1) Обучение (запись в базу — только для админа).
        is_admin = str(chat_id) == str(ADMIN_CHAT_ID)
        taught = self._try_learn(userQuery, is_admin)
        if taught:
            return taught

        # 2) Калькулятор по данным пользователя.
        calc = self._try_math(userQuery)
        if calc:
            return calc

        # 3) Советник по тактике игр.
        tactic = self._try_tactic(userQuery)
        if tactic:
            return tactic

        # 4) База знаний (встроенная + выученная).
        answer, score = self._best_answer(userQuery)
        if answer and score >= 1.2:
            return answer

        # 5) Не знаем — честно говорим и предлагаем научить.
        topics = "комбо, майнинг, краны, фарм, вывод, кошелёк, безопасность, таймеры, курс, реклама, расчёты, тактика игр"
        base = (
            "🤔 Пока не знаю точного ответа на это.\n\n"
            f"Я умею: отвечать по темам ({topics}), считать по твоим числам "
            "и советовать тактику по играм."
        )
        if is_admin:
            base += ("\n\nНаучи меня: «запомни: вопрос = ответ», "
                     "и в следующий раз я отвечу правильно.")
        return base


logger = logging.getLogger(__name__)

# (Модуль автоматизации игр удалён: реальная авто-ферма третьих ботов не ведётся,
#  вместо неё — напоминания в «⏰ Мои таймеры».)


class AdvancedSecurityGuard:
   
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

def remove_verified_user(user_id):
    """Удаляет пользователя из базы (например, если он заблокировал бота).
    Перезаписывает файл целиком актуальным составом множества."""
    try:
        verified_users.discard(user_id)
        with open(VERIFIED_FILE, "w", encoding="utf-8") as f:
            for uid in verified_users:
                f.write(f"{uid}\n")
    except Exception as e:
        logger.error(f"Ошибка удаления пользователя из файла: {e}")

verified_users = load_verified_users()

# ── Персистентность статов профиля ────────────────────────────────────────
# На телефоне лежит лишь крошечный JSON: ссылки Telegram (file_id) + текст
# уровня. САМИ картинки хранятся на серверах Telegram, НЕ на телефоне.
USER_STATS_FILE = "user_game_stats.json"

def load_user_stats():
    data = {}
    if os.path.exists(USER_STATS_FILE):
        try:
            with open(USER_STATS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for k, v in raw.items():
                try:
                    data[int(k)] = v          # ключи-чаты в JSON — строки → int
                except (ValueError, TypeError):
                    data[k] = v
        except Exception as e:
            logger.error(f"Ошибка загрузки статов профиля: {e}")
    return data

def save_user_stats():
    try:
        with open(USER_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_game_stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения статов профиля: {e}")

user_game_stats = load_user_stats()

# ── История найденных комбо (общая для всех) ──────────────────────────────
# Тоже только file_id Telegram + дата; картинки — на серверах Telegram.
COMBO_HISTORY_FILE = "combo_history.json"
COMBO_HISTORY_MAX = 60           # держим последние N записей

def load_combo_history():
    if os.path.exists(COMBO_HISTORY_FILE):
        try:
            with open(COMBO_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки истории комбо: {e}")
    return []

def save_combo_history():
    try:
        with open(COMBO_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(combo_history[-COMBO_HISTORY_MAX:], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения истории комбо: {e}")

def add_combo_to_history(game_key, name, date_text, file_id):
    """Добавляет комбо в историю (одна запись на игру в день)."""
    day_key = time.strftime("%Y-%m-%d", time.localtime())
    for h in combo_history:
        if h.get("key") == game_key and h.get("day") == day_key:
            return                            # за сегодня уже записано
    combo_history.append({
        "key": game_key, "name": name, "date": date_text,
        "file_id": file_id, "day": day_key
    })
    if len(combo_history) > COMBO_HISTORY_MAX:
        del combo_history[:-COMBO_HISTORY_MAX]
    save_combo_history()

combo_history = load_combo_history()

# ── Персистентность отзывов и скринов выплат ──────────────────────────────
# Отзывы = текст; скрины = ТОЛЬКО file_id Telegram (сами картинки хранятся на
# серверах Telegram, НЕ на телефоне) — всё переживает перезапуск бота.
REVIEWS_FILE = "reviews.json"
PROOFS_FILE = "proofs.json"

def load_reviews():
    if os.path.exists(REVIEWS_FILE):
        try:
            with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.error(f"Ошибка загрузки отзывов: {e}")
    return []

def save_reviews():
    try:
        with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_reviews_storage, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения отзывов: {e}")

def load_proofs():
    if os.path.exists(PROOFS_FILE):
        try:
            with open(PROOFS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.error(f"Ошибка загрузки скринов выплат: {e}")
    return []

def save_proofs():
    try:
        with open(PROOFS_FILE, "w", encoding="utf-8") as f:
            json.dump(cloud_proofs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения скринов выплат: {e}")

# Восстанавливаем сохранённые отзывы и скрины (заменяют пустые списки выше).
user_reviews_storage = load_reviews()
cloud_proofs = load_proofs()

# ── Персистентность таймеров пользователей ────────────────────────────────
# Раньше таймеры жили только в памяти и терялись при каждом перезапуске
# (а бот перезапускается каждые 2 часа). Теперь — переживают рестарт.
TIMERS_FILE = "user_timers.json"

def load_timers():
    data = {}
    if os.path.exists(TIMERS_FILE):
        try:
            with open(TIMERS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for k, v in raw.items():
                try:
                    data[int(k)] = v
                except (ValueError, TypeError):
                    data[k] = v
        except Exception as e:
            logger.error(f"Ошибка загрузки таймеров: {e}")
    return data

def save_timers():
    try:
        with open(TIMERS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_game_timers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения таймеров: {e}")

user_game_timers = load_timers()

# ── Подписки на авто-комбо: {game_key: [chat_id, ...]} ────────────────────
COMBO_SUBS_FILE = "combo_subs.json"

def load_combo_subs():
    if os.path.exists(COMBO_SUBS_FILE):
        try:
            with open(COMBO_SUBS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {k: list(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Ошибка загрузки подписок на комбо: {e}")
    return {}

def save_combo_subs():
    try:
        with open(COMBO_SUBS_FILE, "w", encoding="utf-8") as f:
            json.dump(combo_subscribers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения подписок на комбо: {e}")

combo_subscribers = load_combo_subs()

def toggle_combo_sub(game_key: str, chat_id: int) -> bool:
    """Переключает подписку на авто-комбо игры. True = теперь подписан."""
    lst = combo_subscribers.setdefault(game_key, [])
    if chat_id in lst:
        lst.remove(chat_id)
        if not lst:
            combo_subscribers.pop(game_key, None)
        save_combo_subs()
        return False
    lst.append(chat_id)
    save_combo_subs()
    return True

def is_combo_subscribed(game_key: str, chat_id: int) -> bool:
    return chat_id in combo_subscribers.get(game_key, [])

# ── Реферальная система (deep-link /start ref_<id>) ───────────────────────
REFERRALS_FILE = "referrals.json"

def load_referrals():
    base = {"ref_of": {}, "invited": {}}
    if os.path.exists(REFERRALS_FILE):
        try:
            with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                base["ref_of"] = data.get("ref_of", {})
                base["invited"] = data.get("invited", {})
        except Exception as e:
            logger.error(f"Ошибка загрузки рефералов: {e}")
    return base

def save_referrals():
    try:
        with open(REFERRALS_FILE, "w", encoding="utf-8") as f:
            json.dump(referral_store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения рефералов: {e}")

referral_store = load_referrals()
pending_ref = {}          # {chat_id: referrer_id} — до прохождения капчи

def record_referral(new_user_id, referrer_id) -> bool:
    """Кредитует пригласившего, если новичок ещё не был ничьим рефералом."""
    nu, ref = str(new_user_id), str(referrer_id)
    if nu == ref:
        return False                              # сам себя не приглашает
    if nu in referral_store["ref_of"]:
        return False                              # уже был приглашён ранее
    referral_store["ref_of"][nu] = ref
    invited = referral_store["invited"].setdefault(ref, [])
    if new_user_id not in invited and str(new_user_id) not in [str(x) for x in invited]:
        invited.append(new_user_id)
    save_referrals()
    return True

def referral_count(user_id) -> int:
    return len(referral_store["invited"].get(str(user_id), []))

def referral_top(n: int = 10):
    items = [(uid, len(lst)) for uid, lst in referral_store["invited"].items() if lst]
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:n]

# Кэш имени бота (нужно для формирования реферальных ссылок).
_bot_username_cache = {"name": None}

def get_bot_username() -> str:
    if not _bot_username_cache["name"]:
        try:
            _bot_username_cache["name"] = bot.get_me().username
        except Exception:
            _bot_username_cache["name"] = None
    return _bot_username_cache["name"] or "bot"

# ── Приватность в публичных списках: имя вместо ID + маскировка ID ─────────
_name_cache = {}

def display_name(uid) -> str:
    """Имя пользователя для публичных рейтингов (кэш, экранирование Markdown)."""
    key = str(uid)
    if key in _name_cache:
        return _name_cache[key]
    name = ""
    try:
        name = (bot.get_chat(uid).first_name or "").strip()
    except Exception:
        name = ""
    name = re.sub(r'[*_`\[\]]', '', name)[:20] or "👤"
    _name_cache[key] = name
    return name

def mask_id(uid) -> str:
    """Маскирует ID для публичного показа: 5290***079."""
    s = str(uid)
    return s if len(s) <= 5 else s[:4] + "***" + s[-3:]

# ── Здоровье внешних подсистем (деградация при сетевых проблемах) ──────────
system_health = {"prices_ok": True, "combos_ok": True}

def mark_subsystem(name: str, ok: bool):
    system_health[f"{name}_ok"] = ok

def is_degraded() -> bool:
    return not (system_health.get("prices_ok", True) and system_health.get("combos_ok", True))

def degraded_features():
    feats = []
    if not system_health.get("prices_ok", True):
        feats.append("💱 Курс валют и ценовые алерты — данные из кэша")
    if not system_health.get("combos_ok", True):
        feats.append("🎯 Свежие комбо — только из истории (сайт недоступен)")
    return feats

# ── Очередь повторной отправки (не теряем уведомления при микро-обрывах) ───
retry_queue = []
_retry_lock = threading.Lock()
RETRY_MAX = 5

def _is_network_error(e) -> bool:
    return isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                          requests.exceptions.RequestException, socket.gaierror,
                          ConnectionError, OSError))

def enqueue_retry(chat_id, text):
    with _retry_lock:
        if len(retry_queue) < 2000:
            retry_queue.append({"chat_id": chat_id, "text": text, "tries": 0})

def drain_retry_queue():
    """Фоновая дорассылка накопленных сообщений после восстановления сети."""
    while True:
        time.sleep(60)
        if not retry_queue:
            continue
        with _retry_lock:
            batch = list(retry_queue)
            retry_queue.clear()
        for item in batch:
            try:
                bot.send_message(item["chat_id"], item["text"])
            except apihelper.ApiTelegramException:
                pass                          # 403/400 — получатель недоступен, отбрасываем
            except Exception as e:
                if _is_network_error(e):
                    item["tries"] += 1
                    if item["tries"] < RETRY_MAX:
                        with _retry_lock:
                            retry_queue.append(item)
            time.sleep(0.05)

# ── Мини-уведомление пользователю об облегчённом режиме (раз в 30 мин) ─────
_degraded_notified = {}

def maybe_notify_degraded(sender_obj, chat_id):
    if not is_degraded():
        return
    now = time.time()
    if now - _degraded_notified.get(chat_id, 0) < 1800:
        return
    feats = degraded_features()
    if not feats:
        return
    _degraded_notified[chat_id] = now
    try:
        sender_obj.send_message_direct(
            chat_id,
            "⚠️ *Облегчённый режим* — проблемы с внешней сетью.\n"
            "Временно ограничено:\n" + "\n".join(f"• {f}" for f in feats) +
            "\n\n✅ Как обычно работает: меню, профиль, таймеры, ИИ-помощник, комбо из истории.",
            parse_mode="Markdown"
        )
    except Exception:
        pass

# ── Последнее известное комбо (любой день) — для деградации ────────────────
def find_last_combo_fileid(game_key):
    for h in reversed(combo_history):
        if h.get("key") == game_key and h.get("file_id"):
            return h["file_id"], h.get("date", "")
    return None, None

# ── Кэш цен CoinGecko (антибан 429 + отдаём устаревшее при сбое сети) ──────
_price_cache = {}
PRICE_TTL = 60

def cached_json_get(url: str, ttl: int = PRICE_TTL):
    """GET JSON с кэшем. При сетевом сбое возвращает устаревшие данные из кэша
    (если есть) и помечает подсистему цен как деградировавшую."""
    now = time.time()
    hit = _price_cache.get(url)
    if hit and now - hit[0] < ttl:
        return hit[1]
    try:
        r = requests.get(url, timeout=8)
        data = r.json()
        _price_cache[url] = (now, data)
        mark_subsystem("prices", True)
        return data
    except Exception:
        mark_subsystem("prices", False)
        if hit:
            return hit[1]                     # устаревшие данные лучше, чем ничего
        raise

# ── Геймификация: очки, серии (streak) и VIP-статус ───────────────────────
GAMIFY_FILE = "gamification.json"

def load_gamify():
    base = {"points": {}, "streak": {}, "vip_until": {}}
    if os.path.exists(GAMIFY_FILE):
        try:
            with open(GAMIFY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                base["points"] = data.get("points", {})
                base["streak"] = data.get("streak", {})
                base["vip_until"] = data.get("vip_until", {})
        except Exception as e:
            logger.error(f"Ошибка загрузки геймификации: {e}")
    return base

def save_gamify():
    try:
        with open(GAMIFY_FILE, "w", encoding="utf-8") as f:
            json.dump(gamify_store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения геймификации: {e}")

gamify_store = load_gamify()

def get_points(uid) -> int:
    return int(gamify_store["points"].get(str(uid), 0))

def add_points(uid, n: int):
    gamify_store["points"][str(uid)] = get_points(uid) + int(n)
    save_gamify()

def get_streak(uid) -> int:
    return int(gamify_store["streak"].get(str(uid), {}).get("count", 0))

def daily_checkin(uid):
    """Ежедневный бонус. Возвращает (claimed_now, streak, reward, total_points)."""
    today = time.strftime("%Y-%m-%d", time.localtime())
    yest = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    st = gamify_store["streak"].get(str(uid), {"count": 0, "last": ""})
    if st.get("last") == today:
        return False, st.get("count", 0), 0, get_points(uid)
    st["count"] = st.get("count", 0) + 1 if st.get("last") == yest else 1
    st["last"] = today
    gamify_store["streak"][str(uid)] = st
    reward = 10 + min(st["count"], 7) * 5      # база + бонус за серию (потолок)
    gamify_store["points"][str(uid)] = get_points(uid) + reward
    save_gamify()
    return True, st["count"], reward, get_points(uid)

def points_leaderboard(n: int = 10):
    items = [(uid, p) for uid, p in gamify_store["points"].items() if p]
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:n]

def is_vip(uid) -> bool:
    return gamify_store["vip_until"].get(str(uid), 0) > time.time()

def vip_days_left(uid) -> int:
    left = gamify_store["vip_until"].get(str(uid), 0) - time.time()
    return max(0, int(left // 86400))

def grant_vip(uid, days: int):
    now = time.time()
    cur = gamify_store["vip_until"].get(str(uid), 0)
    base = cur if cur > now else now          # продлеваем, если VIP ещё активен
    gamify_store["vip_until"][str(uid)] = base + days * 86400
    save_gamify()

# ── Комбо из кэша дня (мгновенно, без повторного скрейпинга) ───────────────
def find_today_combo_fileid(game_key):
    day_key = time.strftime("%Y-%m-%d", time.localtime())
    for h in combo_history:
        if h.get("key") == game_key and h.get("day") == day_key and h.get("file_id"):
            return h["file_id"], h.get("date", "")
    return None, None

# ── Резервная копия всех данных (защита от потери телефона) ────────────────
BACKUP_FILES = [
    VERIFIED_FILE, USER_STATS_FILE, COMBO_HISTORY_FILE, REVIEWS_FILE,
    PROOFS_FILE, TIMERS_FILE, COMBO_SUBS_FILE, REFERRALS_FILE, GAMIFY_FILE,
    "price_alerts.json", "digest_subs.json", "user_langs.json",
    "banned_users.txt", "scam_domains.txt", "ai_knowledge.json",
    ACTIVE_ADS_FILE, "used_tx_hashes.txt",
]

def backup_all_files(bot_instance, admin_chat_id):
    """Отправляет все файлы данных админу (восстановление при потере телефона)."""
    sent, missing = 0, []
    for fname in BACKUP_FILES:
        if os.path.exists(fname):
            try:
                with open(fname, "rb") as f:
                    bot_instance.send_document(admin_chat_id, f, visible_file_name=fname)
                sent += 1
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"Ошибка бэкапа {fname}: {e}")
        else:
            missing.append(fname)
    try:
        bot_instance.send_message(
            admin_chat_id,
            f"💾 *Бэкап завершён*\n✅ Отправлено файлов: *{sent}*\n"
            f"➖ Ещё не создано: {', '.join(missing) if missing else '—'}",
            parse_mode="Markdown"
        )
    except Exception:
        pass

# Час суток (0-23), когда бот выполняет ежедневные автономные задачи
# (бэкап, отчёт, дайджест, уборку).
DAILY_TASK_HOUR = 9

# Поддерживаемые монеты для ценовых алертов и конвертера (→ id CoinGecko).
COIN_ID_MAP = {
    "btc": "bitcoin", "eth": "ethereum", "ton": "the-open-network",
    "usdt": "tether", "bnb": "binancecoin", "sol": "solana",
}

# ── Ценовые алерты: [{"user": id, "coin": "btc", "op": ">"/"<", "value": float}] ──
PRICE_ALERTS_FILE = "price_alerts.json"

def load_price_alerts():
    if os.path.exists(PRICE_ALERTS_FILE):
        try:
            with open(PRICE_ALERTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.error(f"Ошибка загрузки ценовых алертов: {e}")
    return []

def save_price_alerts():
    try:
        with open(PRICE_ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(price_alerts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения ценовых алертов: {e}")

price_alerts = load_price_alerts()

# ── Подписка на утренний дайджест (множество chat_id) ─────────────────────
DIGEST_FILE = "digest_subs.json"

def load_digest_subs():
    if os.path.exists(DIGEST_FILE):
        try:
            with open(DIGEST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(int(x) for x in data)
        except Exception as e:
            logger.error(f"Ошибка загрузки подписок дайджеста: {e}")
    return set()

def save_digest_subs():
    try:
        with open(DIGEST_FILE, "w", encoding="utf-8") as f:
            json.dump(list(digest_subs), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения подписок дайджеста: {e}")

digest_subs = load_digest_subs()

# ── Мультиязычность: язык пользователя (RU/EN/FR) ─────────────────────────
LANGS_FILE = "user_langs.json"

def load_langs():
    data = {}
    if os.path.exists(LANGS_FILE):
        try:
            with open(LANGS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for k, v in raw.items():
                try:
                    data[int(k)] = v
                except (ValueError, TypeError):
                    data[k] = v
        except Exception as e:
            logger.error(f"Ошибка загрузки языков: {e}")
    return data

def save_langs():
    try:
        with open(LANGS_FILE, "w", encoding="utf-8") as f:
            json.dump(user_langs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения языков: {e}")

user_langs = load_langs()

def get_lang(chat_id) -> str:
    lang = user_langs.get(chat_id) or user_langs.get(str(chat_id))
    return lang if lang in SUPPORTED_LANGS else "ru"

def set_lang(chat_id, lang):
    if lang in SUPPORTED_LANGS:
        user_langs[chat_id] = lang
        save_langs()

def has_lang(chat_id) -> bool:
    return chat_id in user_langs or str(chat_id) in user_langs

def detect_lang(tg_code) -> str:
    """Угадывает язык по коду Telegram (fr/en/ru), по умолчанию ru."""
    c = (tg_code or "").lower()
    if c.startswith("fr"):
        return "fr"
    if c.startswith("en"):
        return "en"
    return "ru"

def t(key: str, lang: str) -> str:
    """Перевод ключа на язык lang (фолбэк — RU, потом пустая строка)."""
    d = TR.get(key, {})
    return d.get(lang) or d.get("ru") or ""

user_input_states = {}

class ActiveAdsManager:
    """Менеджер для управления активной рекламой с автоматической синхронизацией с файлом."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.storage: dict = self._load_ads()

    def _load_ads(self) -> dict:
        """Загрузка активных объявлений из файла (JSON — с поддержкой текста креатива;
        со старым pipe-форматом `oid|user_id|expire_time` для обратной совместимости)."""
        ads = {}
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    raw = f.read().strip()
                if raw:
                    if raw.lstrip().startswith("{"):
                        data = json.loads(raw)
                        for oid, d in data.items():
                            ads[oid] = {
                                "user_id": int(d.get("user_id")),
                                "expire_time": float(d.get("expire_time", 0)),
                                "content": d.get("content", ""),
                            }
                    else:
                        for line in raw.splitlines():
                            parts = line.strip().split("|")
                            if len(parts) >= 3:
                                ads[parts[0]] = {
                                    "user_id": int(parts[1]),
                                    "expire_time": float(parts[2]),
                                    "content": "",
                                }
            except Exception as e:
                logger.error(f"Ошибка загрузки активной рекламы: {e}")
        return ads

    def save_to_file(self):
        """Сохранение текущего состояния активных объявлений в файл (JSON)."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.storage, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения активной рекламы в файл: {e}")

    def add_ad(self, order_id: str, user_id: int, expire_time: float, content: str = ""):
        """Добавление новой рекламы с автоматическим сохранением (с текстом креатива)."""
        self.storage[order_id] = {"user_id": user_id, "expire_time": expire_time, "content": content}
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

class UltimateSecurityCore:
   
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


class LinkScamGuard:
    """
    Анализатор ссылок (офлайн): скоринг риска, эвристика скама/фишинга и
    вредоносных файлов («вирус»). Возвращает вердикт clean/suspicious/scam
    и аннотированный текст, где опасные ссылки ЗАБЛОКИРОВАНЫ и помечены 🚨.
    """

    SHORTENERS = {
        "bit.ly", "tinyurl.com", "cutt.ly", "t.co", "is.gd", "goo.gl", "ow.ly",
        "rb.gy", "shorturl.at", "clck.ru", "vk.cc", "tiny.cc", "rebrand.ly", "surl.li",
    }
    SUSPICIOUS_TLDS = (
        ".xyz", ".top", ".cc", ".cfd", ".tk", ".ml", ".gq", ".ga", ".click", ".link",
        ".live", ".online", ".site", ".club", ".rest", ".buzz", ".monster", ".lol",
        ".sbs", ".autos", ".cyou", ".quest", ".bond",
    )
    MALWARE_EXT = (".exe", ".apk", ".scr", ".bat", ".msi", ".dll", ".jar", ".vbs", ".cmd", ".apk")
    SCAM_URL_WORDS = (
        "airdrop", "claim", "free", "bonus", "giveaway", "double", "verify", "connect",
        "wallet", "seed", "drain", "mint", "presale", "gift", "reward", "unlock",
        "recovery", "validate", "халяв", "бонус", "розыгрыш", "подарок", "кошел", "верифи",
    )
    SCAM_FILE = "scam_domains.txt"

    def __init__(self, phishing_domains=None, ghost_domains=None, scam_patterns=None, blacklist=None):
        self.phishing_domains = [str(d).lower() for d in (phishing_domains or [])]
        self.ghost_domains = [str(d).lower() for d in (ghost_domains or [])]
        self.scam_patterns = scam_patterns or []
        self.blacklist_core = [str(d).lower() for d in (blacklist or [])]
        self.scam_domains = self._load_scam_domains()

    # ---- Чёрный список доменов (обучаемый админом) ----
    def _load_scam_domains(self):
        s = set()
        if os.path.exists(self.SCAM_FILE):
            try:
                with open(self.SCAM_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        d = line.strip().lower()
                        if d:
                            s.add(d)
            except Exception as e:
                logger.error(f"Ошибка загрузки scam_domains: {e}")
        return s

    def add_scam_domain(self, domain: str) -> bool:
        d = (domain or "").strip().lower()
        d = re.sub(r'^https?://', '', d).split("/")[0].split("?")[0]
        if not d or "." not in d:
            return False
        self.scam_domains.add(d)
        try:
            with open(self.SCAM_FILE, "a", encoding="utf-8") as f:
                f.write(d + "\n")
        except Exception as e:
            logger.error(f"Ошибка сохранения scam-домена: {e}")
        return True

    @staticmethod
    def _entropy(s: str) -> float:
        if not s:
            return 0.0
        probs = [s.count(c) / len(s) for c in set(s)]
        return -sum(p * math.log2(p) for p in probs)

    def _score_url(self, url: str):
        reasons, score = [], 0
        try:
            parsed = urllib.parse.urlparse(url if "//" in url else "http://" + url)
        except Exception:
            return 40, ["Не удалось разобрать ссылку"]

        host = (parsed.netloc or "").lower()
        if "@" in host:                       # трюк с userinfo: real@fake
            score += 50
            reasons.append("Скрытый адрес через символ '@'")
            host = host.split("@")[-1]
        host_only = host.split(":")[0]
        full = url.lower()
        path = (parsed.path or "").lower()

        # Чёрные списки
        if any(host_only == d or host_only.endswith("." + d) or d in host_only for d in self.scam_domains):
            score += 100
            reasons.append("Домен в чёрном списке скама")
        if any(d and d in host_only for d in self.blacklist_core):
            score += 90
            reasons.append("Домен в базовом блэклисте")
        if any(d and d in full for d in self.phishing_domains):
            score += 90
            reasons.append("Совпадение с фишинг-базой")
        if any(g and (host_only.endswith(g) or g in host_only) for g in self.ghost_domains):
            score += 60
            reasons.append("Подозрительный домен/префикс (ghost)")

        # Эвристики
        if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', host_only):
            score += 45
            reasons.append("IP-адрес вместо домена")
        if "xn--" in host_only:
            score += 45
            reasons.append("Punycode (возможен омоглиф-обман)")
        if re.search(r'[а-яё]', host_only):
            score += 50
            reasons.append("Кириллица в домене (омоглиф-атака)")
        if any(host_only.endswith(t) for t in self.SUSPICIOUS_TLDS):
            score += 30
            reasons.append("Подозрительная доменная зона")
        if host_only in self.SHORTENERS:
            score += 30
            reasons.append("Сокращатель ссылок (скрыт реальный адрес)")
        if host_only.count(".") >= 3:
            score += 20
            reasons.append("Слишком много поддоменов")
        main = host_only.split(".")[0]
        if len(main) >= 10 and self._entropy(main) > 3.6:
            score += 25
            reasons.append("Случайно сгенерированный (DGA) домен")
        if any(full.split("?")[0].endswith(ext) for ext in self.MALWARE_EXT) or any(ext in path for ext in self.MALWARE_EXT):
            score += 50
            reasons.append("Прямая загрузка файла (возможен вирус)")
        hits = [w for w in self.SCAM_URL_WORDS if w in full]
        if hits:
            score += min(40, 12 * len(hits))
            reasons.append("Скам-слова в ссылке: " + ", ".join(hits[:4]))
        for pat in self.scam_patterns:
            try:
                if re.search(pat, full, re.IGNORECASE):
                    score += 25
                    reasons.append("Совпадение со скам-паттерном")
                    break
            except Exception:
                continue

        return min(score, 100), reasons

    @staticmethod
    def _verdict(score: int) -> str:
        if score >= 90:
            return "scam"
        if score >= 45:
            return "suspicious"
        return "clean"

    def analyze(self, text: str):
        text = text or ""
        md = re.findall(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', text)
        urls = re.findall(r'(?:https?://|www\.)[^\s<>()\]]+', text)
        urls += re.findall(r'\bt\.me/[^\s<>()\]]+', text, re.IGNORECASE)
        for _anchor, u in md:
            urls.append(u)

        seen, links = set(), []
        for u in urls:
            u = u.rstrip('.,!?)»"\'')
            key = u.lower()
            if key in seen:
                continue
            seen.add(key)
            score, reasons = self._score_url(u)
            for anchor, mu in md:                 # подмена текста ссылки
                if mu.startswith(u) and "." in anchor and anchor.lower() not in u.lower():
                    score = min(100, score + 40)
                    reasons.append("Текст ссылки не совпадает с реальным адресом")
            links.append({"url": u, "score": score, "verdict": self._verdict(score), "reasons": reasons})

        if not links:
            return {"links": [], "worst": "clean", "max_score": 0, "message": ""}

        worst = max(links, key=lambda l: l["score"])
        worst_v = self._verdict(worst["score"])
        return {
            "links": links,
            "worst": worst_v,
            "max_score": worst["score"],
            "message": self._build_message(text, links, worst, worst_v),
        }

    def _annotate(self, text: str, links: list) -> str:
        out = text
        for l in links:
            if l["verdict"] == "scam":
                out = out.replace(l["url"], "🚨[СКАМ-ССЫЛКА ЗАБЛОКИРОВАНА]")
            elif l["verdict"] == "suspicious":
                out = out.replace(l["url"], "⚠️[ПОДОЗРИТЕЛЬНАЯ ССЫЛКА]")
        return out

    def _build_message(self, text, links, worst, worst_v) -> str:
        annotated = self._annotate(text, links)
        reasons = "\n".join(f"• {r}" for r in worst["reasons"][:5]) or "• эвристика безопасности"
        if worst_v == "scam":
            return (
                f"🚨 ВНИМАНИЕ: ссылка заблокирована как СКАМ! (риск {worst['score']}/100)\n\n"
                f"{annotated}\n\nПричины:\n{reasons}\n\n"
                "❌ Не переходите по ссылке, не подключайте кошелёк и НЕ вводите seed-фразу."
            )
        if worst_v == "suspicious":
            return (
                f"⚠️ Подозрительная ссылка (риск {worst['score']}/100). Будьте осторожны.\n\n"
                f"{annotated}\n\nПричины:\n{reasons}"
            )
        return (
            f"🔗 Явных признаков скама не найдено (риск {worst['score']}/100).\n"
            "Всё равно проверяйте проект сами и никогда не вводите seed-фразу."
        )


class AccountGuard:
    """
    Проверка Telegram-аккаунта пользователя + чёрный список (спамеры/хакеры/скамеры).

    Что умеет офлайн через Bot API:
    • блокирует ботов;
    • ловит скам-юзернеймы (@s_upp0rt и т.п.) и поддельные имена (ссылки/омоглифы);
    • оценивает риск свежих/пустых аккаунтов;
    • копит «страйки» за флуд и банит рецидивистов (бан хранится в файле).

    Ограничение: официальный флаг «scam/fake» Telegram ботам недоступен —
    поэтому используются эвристики.
    """

    BAN_FILE = "banned_users.txt"
    # Порог «свежести» аккаунта по ID (эвристика: чем выше ID, тем новее аккаунт).
    NEW_ACCOUNT_ID = 7_500_000_000

    def __init__(self, bot_instance, scam_username_markers=None, admin_chat_id=None):
        self.bot = bot_instance
        self.scam_markers = [str(m).lower() for m in (scam_username_markers or [])]
        self.admin_chat_id = admin_chat_id
        self.banned = self._load_banned()
        self.strikes = {}

    # ---- Чёрный список ----
    def _load_banned(self):
        s = set()
        if os.path.exists(self.BAN_FILE):
            try:
                with open(self.BAN_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.isdigit():
                            s.add(int(line))
            except Exception as e:
                logger.error(f"Ошибка загрузки banned_users: {e}")
        return s

    def is_banned(self, user_id) -> bool:
        try:
            return int(user_id) in self.banned
        except Exception:
            return False

    def ban(self, user_id, reason: str = ""):
        try:
            user_id = int(user_id)
        except Exception:
            return
        if user_id in self.banned:
            return
        self.banned.add(user_id)
        try:
            with open(self.BAN_FILE, "a", encoding="utf-8") as f:
                f.write(f"{user_id}\n")
        except Exception as e:
            logger.error(f"Ошибка сохранения бана: {e}")
        logger.warning(Fore.RED + f"🚫 Забанен пользователь {user_id}: {reason}")

    def unban(self, user_id):
        try:
            user_id = int(user_id)
        except Exception:
            return
        if user_id in self.banned:
            self.banned.discard(user_id)
            try:
                with open(self.BAN_FILE, "w", encoding="utf-8") as f:
                    for uid in self.banned:
                        f.write(f"{uid}\n")
            except Exception as e:
                logger.error(f"Ошибка обновления banned_users: {e}")

    def strike(self, user_id, reason: str, limit: int = 3) -> bool:
        """Добавляет страйк за нарушение; при достижении лимита банит. True = забанен."""
        try:
            user_id = int(user_id)
        except Exception:
            return False
        self.strikes[user_id] = self.strikes.get(user_id, 0) + 1
        if self.strikes[user_id] >= limit:
            self.ban(user_id, reason)
            return True
        return False

    # ---- Анализ аккаунта ----
    @staticmethod
    def _full_name(user) -> str:
        return f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()

    def hard_block(self, user):
        """Жёсткие блокировки. Возвращает (blocked: bool, reason: str)."""
        if getattr(user, "is_bot", False):
            return True, "аккаунт является ботом"

        uname = (getattr(user, "username", "") or "").lower()
        for m in self.scam_markers:
            if m and m in uname:
                return True, f"скам-маркер в юзернейме ({m})"

        name = self._full_name(user).lower()
        # Ссылки/приглашения прямо в имени профиля — типичный спам/скам.
        if re.search(r'(https?://|t\.me/|@[a-z0-9_]{4,})', name):
            return True, "ссылка/приглашение в имени профиля"
        # Смешение кириллицы и латиницы в одном слове имени (омоглиф-подделка).
        for w in name.split():
            if len(w) >= 4 and re.search(r'[а-яё]', w) and re.search(r'[a-z]', w):
                return True, "смешение алфавитов в имени (омоглиф)"
        return False, ""

    def risk(self, user):
        """Мягкая оценка риска (0-100) для доп. подозрения (без блокировки)."""
        score, reasons = 0, []
        if not getattr(user, "username", None):
            score += 15
            reasons.append("нет юзернейма")
        if not getattr(user, "is_premium", False):
            score += 5
        uid = getattr(user, "id", 0) or 0
        if uid > self.NEW_ACCOUNT_ID:
            score += 25
            reasons.append("очень новый аккаунт")
        return score, reasons


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
            mark_subsystem("combos", res.status_code == 200)
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
            mark_subsystem("combos", False)
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
        user = message.from_user

        # Определяем язык при первом контакте (по языку клиента Telegram).
        if not has_lang(chat_id):
            set_lang(chat_id, detect_lang(getattr(user, "language_code", None)))

        # 0) Забаненные (спам/скам/хакеры) — доступ закрыт.
        if account_guard.is_banned(user.id):
            try:
                bot.send_message(chat_id, "🚫 Доступ заблокирован (подозрение на спам/скам).")
            except Exception:
                pass
            return

        # 1) Проверка аккаунта: боты, скам-юзернеймы, поддельные имена (омоглифы/ссылки).
        blocked, reason = account_guard.hard_block(user)
        if blocked:
            account_guard.ban(user.id, reason)
            try:
                bot.send_message(chat_id, f"🚫 Доступ запрещён: {reason}.")
            except Exception:
                pass
            try:
                # parse_mode=None: имя/юзернейм пользователя не должны ломать/инъектировать разметку.
                send_message_direct(ADMIN_CHAT_ID, f"🚫 Заблокирован аккаунт {user.id} (@{user.username}): {reason}", None, None)
            except Exception:
                pass
            return

        if chat_id not in verified_users:
            # Реферальный deep-link: /start ref_<id> — запоминаем пригласившего
            # (кредитуется только ПОСЛЕ прохождения капчи — защита от накрутки).
            try:
                sp = (message.text or "").split(maxsplit=1)
                if len(sp) > 1:
                    mref = re.match(r'(?:ref_)?(\d{5,})', sp[1].strip())
                    if mref:
                        pending_ref[chat_id] = int(mref.group(1))
            except Exception:
                pass

            # Подозрительный, но не заблокированный аккаунт — уведомим админа.
            rscore, rreasons = account_guard.risk(user)
            if rscore >= 30:
                try:
                    send_message_direct(
                        ADMIN_CHAT_ID,
                        f"⚠️ Подозрительный вход {user.id} (@{user.username}), риск {rscore}: {', '.join(rreasons)}",
                        None, None
                    )
                except Exception:
                    pass
            question, markup = generate_advanced_captcha(chat_id)
            bot.send_message(chat_id, f"🛡️ **Проверка на человека**\n\n🧠 *{question}*", reply_markup=markup, parse_mode="Markdown")
            return
        lang = get_lang(chat_id)
        send_message_direct(chat_id, t("welcome", lang), reply_markup=main_menu_kb(chat_id))
        # 🎁 Ежедневный бонус за заход (очки + серия).
        try:
            claimed, streak, reward, total = daily_checkin(chat_id)
            if claimed:
                send_message_direct(
                    chat_id,
                    t("daily_bonus", lang).format(reward=reward, streak=streak, total=total),
                    None, "Markdown"
                )
        except Exception:
            pass

    @staticmethod
    def handle_menu_or_commands(message: types.Message):
        # Маршрутизация кнопок главного меню и текстовых команд
        # в реальный обработчик MenuTextProcessor.handle_menu_text.
        handle_menu_text(message)


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
        



# ============================================================
# РЕКЛАМА: очистка креатива и оформление карточки объявления
# ============================================================

def clean_ad_creative(raw_text: str, tx_hash: str = "") -> str:
    """Убирает из присланного сообщения хэш транзакции и служебные подписи,
    оставляя только сам рекламный текст (креатив) для показа пользователям."""
    text = raw_text or ""
    if tx_hash:
        text = text.replace(tx_hash, "")
    # Строки-подписи вида «hash: ...», «хэш = ...», «tx: ...».
    text = re.sub(r'(?im)^\s*(?:tx|txid|hash|хэш|хеш)\s*[:=].*$', '', text)
    # Отдельные токены, похожие на хэш (hex/base64 длиной 40+ символов).
    text = re.sub(r'\b[A-Za-z0-9+/=_-]{40,}\b', '', text)
    # Схлопываем лишние пустые строки.
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text


def build_ad_card(creative: str, tariff_name: str = "") -> str:
    """Компактная, аккуратная карточка спонсорского поста (Markdown)."""
    creative = (creative or "").strip()
    return (
        "📢 *РЕКЛАМА* · _спонсорский пост_\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{creative}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💼 _Хотите так же? Раздел «📢 Реклама» в меню._"
    )


class NotificationSender:
    """Менеджер для отправки сообщений и медиаконтента пользователям."""

    def __init__(self, bot_instance, logger_instance):
        self.bot = bot_instance
        self.logger = logger_instance

    def broadcast_ad(self, creative: str, recipients, admin_chat_id, tariff_name: str = "", order_id: str = ""):
        """Рассылает рекламную карточку всем пользователям в фоне, с ограничением
        скорости (~20 сообщений/сек) и отчётом администратору по завершении."""
        card = build_ad_card(creative, tariff_name)
        # VIP-пользователи не получают рекламу (одно из преимуществ VIP).
        targets = [u for u in list(recipients) if not is_vip(u)]

        def _worker():
            sent = 0
            failed = 0
            blocked = []          # те, кто заблокировал бота (403) → чистим базу
            for uid in targets:
                try:
                    self.bot.send_message(uid, card, parse_mode="Markdown")
                    sent += 1
                except apihelper.ApiTelegramException as e:
                    # 403 = пользователь заблокировал бота / удалил аккаунт.
                    if getattr(e, "error_code", None) == 403:
                        blocked.append(uid)
                        failed += 1
                    else:
                        # Прочее (часто Markdown в креативе) — шлём без разметки.
                        try:
                            self.bot.send_message(uid, card)
                            sent += 1
                        except Exception:
                            failed += 1
                except Exception:
                    try:
                        self.bot.send_message(uid, card)
                        sent += 1
                    except Exception:
                        failed += 1
                time.sleep(0.05)  # ~20 сообщений/сек — безопасно для лимитов Telegram

            # Чистим базу от заблокировавших бота (честный охват + без флага спама).
            for uid in blocked:
                try:
                    remove_verified_user(uid)
                except Exception:
                    pass

            try:
                self.bot.send_message(
                    admin_chat_id,
                    "📢 *Рассылка рекламы завершена*\n"
                    f"🆔 Заказ: `{order_id}`\n"
                    f"📋 Тариф: {tariff_name}\n"
                    f"✅ Доставлено: *{sent}*\n"
                    f"⚠️ Не доставлено: *{failed}*\n"
                    f"🚫 Удалено (заблокировали бота): *{len(blocked)}*\n"
                    f"👥 Осталось в базе: *{len(targets) - len(blocked)}*",
                    parse_mode="Markdown"
                )
            except Exception as e:
                self.logger.error(f"Ошибка отчёта о рассылке рекламы: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def broadcast_message(self, text: str, recipients, admin_chat_id):
        """Массовая рассылка админского объявления всем пользователям (в фоне,
        с ограничением скорости и чисткой заблокировавших бота)."""
        card = "📣 *ОБЪЯВЛЕНИЕ*\n━━━━━━━━━━━━━━━━━━\n\n" + (text or "").strip()
        targets = list(recipients)

        def _worker():
            sent, failed, blocked = 0, 0, []
            for uid in targets:
                try:
                    self.bot.send_message(uid, card, parse_mode="Markdown")
                    sent += 1
                except apihelper.ApiTelegramException as e:
                    if getattr(e, "error_code", None) == 403:
                        blocked.append(uid)
                        failed += 1
                    else:
                        try:
                            self.bot.send_message(uid, card)
                            sent += 1
                        except Exception:
                            failed += 1
                except Exception:
                    try:
                        self.bot.send_message(uid, card)
                        sent += 1
                    except Exception:
                        failed += 1
                time.sleep(0.05)
            for uid in blocked:
                try:
                    remove_verified_user(uid)
                except Exception:
                    pass
            try:
                self.bot.send_message(
                    admin_chat_id,
                    "📣 *Объявление разослано*\n"
                    f"✅ Доставлено: *{sent}*\n"
                    f"⚠️ Не доставлено: *{failed}*\n"
                    f"🚫 Удалено (заблокировали бота): *{len(blocked)}*",
                    parse_mode="Markdown"
                )
            except Exception as e:
                self.logger.error(f"Ошибка отчёта об объявлении: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def send_message_direct(self, chat_id: int | str, text: str, reply_markup=None, parse_mode: str = "Markdown"):
        """Отправка с резервом без разметки; при сетевом сбое — в очередь повтора."""
        try:
            return self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        except apihelper.ApiTelegramException:
            # Ошибка Telegram (обычно кривой Markdown) — пробуем без разметки.
            try:
                return self.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
            except Exception as e2:
                if _is_network_error(e2):
                    enqueue_retry(chat_id, text)
                else:
                    self.logger.error(f"Ошибка отправки сообщения: {e2}")
                return None
        except Exception as e:
            # Сеть пропала — ставим в очередь и дошлём после восстановления.
            if _is_network_error(e):
                enqueue_retry(chat_id, text)
            else:
                self.logger.error(f"Ошибка отправки сообщения: {e}")
            return None

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
        """Профиль = только СПИСОК игр. Статы конкретной игры показываются
        отдельно при нажатии на её кнопку (callback profgame_<name>)."""
        try:
            chat_info = self.bot.get_chat(chat_id)
            user_name = chat_info.first_name or "Игрок"
        except Exception:
            user_name = "Игрок"

        my_stats = user_game_stats.get(chat_id, {}) or {}

        # Имена игр: из конфига (комбо + фермы) + добавленные пользователем вручную.
        names = []
        try:
            for _k, gd in list(manager.combo_games.items()) + list(manager.independent_farms.items()):
                nm = gd.get("name", _k)
                if nm and nm not in names:
                    names.append(nm)
        except Exception:
            pass
        for nm in my_stats.keys():
            if nm not in names:
                names.append(nm)

        # Кнопка на КАЖДУЮ игру: ✅ если стата уже есть, ➕ если ещё нет.
        keyboard_markup = types.InlineKeyboardMarkup()
        for nm in names:
            mark = "✅" if nm in my_stats else "➕"
            keyboard_markup.row(types.InlineKeyboardButton(text=f"{mark} {nm}", callback_data=f"profgame_{nm}"))
        # Возможность добавить игру ВНЕ списка (ручной ввод «Название | Уровень»).
        keyboard_markup.row(types.InlineKeyboardButton(text="➕ Другая игра (вручную)", callback_data="prof_add"))
        keyboard_markup.row(
            types.InlineKeyboardButton(text="📜 История комбо", callback_data="combo_hist"),
            types.InlineKeyboardButton(text="👥 Пригласить", callback_data="ref_invite")
        )
        keyboard_markup.row(MenuManager.get_ai_button())

        vip_line = f"👑 VIP активен ({vip_days_left(chat_id)} дн.)\n" if is_vip(chat_id) else ""
        profile_text = (
            f"👤 **Профиль:** {user_name}\n"
            f"{vip_line}"
            f"💰 Очки: **{get_points(chat_id)}** · 🔥 Серия: **{get_streak(chat_id)}** дн. · 👥 Друзей: **{referral_count(chat_id)}**\n\n"
            f"🏆 Игр с вашими статами: **{len(my_stats)}**\n\n"
            "👇 Нажмите на игру, чтобы посмотреть или добавить свой прогресс.\n"
            "✅ — стата уже добавлена, ➕ — пока нет."
        )
        self.sender.send_message_direct(chat_id, profile_text, reply_markup=keyboard_markup, parse_mode="Markdown")

class BackgroundSchedulerManager:
    """Менеджер фоновых задач: автоматическая проверка комбо, пользовательские таймеры и контроль рекламы."""

    def __init__(self, bot_instance, logger_instance, manager_instance, sender_instance, ads_manager_instance, admin_chat_id: int | str):
        self.bot = bot_instance
        self.logger = logger_instance
        self.manager = manager_instance
        self.sender = sender_instance
        self.ads_manager = ads_manager_instance
        self.admin_chat_id = admin_chat_id

    def _send_daily_digest(self):
        """Утренний дайджест подписчикам: комбо дня + личная серия/очки."""
        if not digest_subs:
            return
        today = time.strftime("%Y-%m-%d", time.localtime())
        found = [h.get("name") for h in combo_history if h.get("day") == today and h.get("file_id")]
        combos_line = ("🎯 Комбо дня готовы: " + ", ".join(found)) if found else "⏳ Комбо дня ещё собираются — загляни позже."
        for uid in list(digest_subs):
            try:
                self.sender.send_message_direct(
                    uid,
                    "🌅 *Доброе утро!*\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    f"{combos_line}\n"
                    f"🔥 Твоя серия: *{get_streak(uid)}* дн. · 💰 Очки: *{get_points(uid)}*\n\n"
                    "👉 Заходи собрать награды и открыть комбо!",
                    parse_mode="Markdown"
                )
            except apihelper.ApiTelegramException as e:
                if getattr(e, "error_code", None) == 403:
                    digest_subs.discard(uid)
            except Exception:
                pass
            time.sleep(0.05)
        save_digest_subs()

    def run_daily_checker(self, user_game_timers: dict):
        """Бесконечный цикл фонового мониторинга."""
        # Плавный старт: даём боту прогреться и быстро отвечать на меню,
        # прежде чем нагружать сеть массовым скрейпингом комбо.
        time.sleep(25)

        last_reset_day = None
        last_daily_day = None
        was_degraded = False
        run_check_now = True

        while True:
            now_time = time.time()
            now_struct = time.localtime(now_time)
            current_day = now_struct.tm_mday
            current_hour = now_struct.tm_hour

            # Проба здоровья цен (обновляет prices_ok для точной детекции деградации).
            try:
                get_btc_usd_rate()
            except Exception:
                pass

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
                                    sent = self.bot.send_photo(self.admin_chat_id, photo=img_bytes, caption=caption[:1024], parse_mode="Markdown")
                                    # Фиксируем file_id (картинка живёт на серверах Telegram) в историю
                                    if sent and getattr(sent, "photo", None):
                                        file_id = sent.photo[-1].file_id
                                        add_combo_to_history(key, info.get('name', key), date_text, file_id)
                                        # 🔔 Авто-рассылка комбо подписчикам этой игры
                                        # (переиспользуем file_id — без повторной загрузки картинки).
                                        subs = list(combo_subscribers.get(key, []))
                                        if subs:
                                            sub_caption = (
                                                f"🔔 **Комбо дня — {info.get('name', key)}**\n"
                                                f"📅 `{date_text}`\n\n🎯 Успей ввести связку в игре!"
                                            )
                                            pushed, blocked = 0, []
                                            for uid in subs:
                                                try:
                                                    self.bot.send_photo(uid, photo=file_id, caption=sub_caption[:1024], parse_mode="Markdown")
                                                    pushed += 1
                                                except apihelper.ApiTelegramException as e:
                                                    if getattr(e, "error_code", None) == 403:
                                                        blocked.append(uid)
                                                except Exception:
                                                    pass
                                                time.sleep(0.05)
                                            if blocked:
                                                for uid in blocked:
                                                    if uid in combo_subscribers.get(key, []):
                                                        combo_subscribers[key].remove(uid)
                                                save_combo_subs()
                                            self.logger.info(f"🔔 Авто-комбо {key}: разослано {pushed}/{len(subs)} подписчикам.")
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
                                game_data = self.manager.combo_games.get(game_key) or self.manager.independent_farms.get(game_key, {})
                                game_name = game_data.get("name", game_key)

                                # Кнопка «▶️ Открыть игру» — ведёт прямо в mini-app
                                # (ссылка берётся из ref_link_1 / play_market в конфиге).
                                play_link = game_data.get("ref_link_1") or game_data.get("play_market")
                                reminder_kb = None
                                if play_link:
                                    reminder_kb = types.InlineKeyboardMarkup()
                                    reminder_kb.row(types.InlineKeyboardButton(text="▶️ Открыть игру", url=play_link))

                                self.sender.send_message_direct(
                                    chat_id,
                                    f"⏰ **Напоминание!** Пора зайти в игру: **{game_name}** 🚀\n"
                                    f"Соберите монеты и посмотрите видео 👇",
                                    reply_markup=reminder_kb
                                )
                                duration = t_data.get("duration_hours", 8)
                                user_game_timers[chat_id][game_key]["target"] = time.time() + (duration * 3600)
                                save_timers()
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

            # 4b. Автоотмена НЕОПЛАЧЕННЫХ заявок старше 24 часов
            # (заявка отправлена админу, но оплата так и не подтверждена).
            try:
                stale_orders = [
                    oid for oid, o in list(pending_ad_orders.items())
                    if now_time - o.get("created_at", now_time) > 86400
                ]
                for oid in stale_orders:
                    o = pending_ad_orders.pop(oid, None)
                    if o:
                        self.sender.send_message_direct(
                            o["user_id"],
                            "⌛ **Ваша заявка на рекламу истекла** — оплата не была подтверждена в течение 24 часов. "
                            "При необходимости оформите заявку заново.",
                            parse_mode="Markdown"
                        )
            except Exception as e:
                self.logger.error(f"Ошибка автоотмены неоплаченных заявок: {e}")

            # 4c. АВТО-ОДОБРЕНИЕ оплаченных, но подвисших на модерации пуб (>12ч).
            # Оплата уже подтверждена — отсутствие админа не должно блокировать клиента.
            try:
                auto_ok = [
                    oid for oid, o in list(pending_ad_orders.items())
                    if o.get("paid") and now_time - o.get("created_at", now_time) > 12 * 3600
                ]
                for oid in auto_ok:
                    o = pending_ad_orders.pop(oid, None)
                    if not o:
                        continue
                    creative = clean_ad_creative(o.get("content", ""))
                    tinfo = ADS_TARIFFS.get(o.get("tariff_key"), {})
                    dur_h = tinfo.get("duration_hours", 0)
                    if dur_h > 0:
                        self.ads_manager.add_ad(oid, o["user_id"], now_time + dur_h * 3600, creative)
                    self.sender.broadcast_ad(creative, verified_users, self.admin_chat_id,
                                             tariff_name=o.get("tariff", ""), order_id=oid)
                    self.sender.send_message_direct(o["user_id"], "🎉 Ваша реклама одобрена автоматически и рассылается по базе!", parse_mode="Markdown")
                    self.sender.send_message_direct(self.admin_chat_id, f"🤖 Авто-одобрение рекламы по таймауту (заказ `{oid}`, клиент `{o['user_id']}`).", parse_mode="Markdown")
            except Exception as e:
                self.logger.error(f"Ошибка авто-одобрения рекламы: {e}")

            # 5. ЦЕНОВЫЕ АЛЕРТЫ (каждый цикл): проверяем и уведомляем, сработавшие удаляем.
            try:
                if price_alerts:
                    ids = sorted({COIN_ID_MAP.get(a["coin"]) for a in price_alerts if COIN_ID_MAP.get(a["coin"])})
                    if ids:
                        url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=usd"
                        pdata = cached_json_get(url)
                        fired = []
                        for a in list(price_alerts):
                            cid = COIN_ID_MAP.get(a["coin"])
                            price = (pdata.get(cid) or {}).get("usd") if cid else None
                            if price is None:
                                continue
                            if (a["op"] == ">" and price >= a["value"]) or (a["op"] == "<" and price <= a["value"]):
                                try:
                                    self.sender.send_message_direct(
                                        a["user"],
                                        f"🔔 *Ценовой алерт!*\n{a['coin'].upper()} = *${price:,.2f}* (условие: {a['op']} {a['value']:g})",
                                        parse_mode="Markdown"
                                    )
                                except Exception:
                                    pass
                                fired.append(a)
                        if fired:
                            for a in fired:
                                if a in price_alerts:
                                    price_alerts.remove(a)
                            save_price_alerts()
            except Exception as e:
                self.logger.error(f"Ошибка проверки ценовых алертов: {e}")

            # 5b. УВЕДОМЛЕНИЕ О ВОССТАНОВЛЕНИИ: если вышли из облегчённого режима —
            # сообщаем ТОЛЬКО тем, кто ранее получил баннер о деградации.
            try:
                cur_degraded = is_degraded()
                if was_degraded and not cur_degraded and _degraded_notified:
                    for uid in list(_degraded_notified.keys()):
                        self.sender.send_message_direct(
                            uid,
                            "✅ *Обычный режим восстановлен* — внешняя сеть снова доступна.\n"
                            "Все функции работают в полном объёме.",
                            parse_mode="Markdown"
                        )
                        time.sleep(0.05)
                    _degraded_notified.clear()
                was_degraded = cur_degraded
            except Exception as e:
                self.logger.error(f"Ошибка уведомления о восстановлении: {e}")

            # 6. ЕЖЕДНЕВНЫЕ АВТОНОМНЫЕ ЗАДАЧИ (раз в сутки, после DAILY_TASK_HOUR):
            #    авто-бэкап · отчёт о здоровье · утренний дайджест · уборка.
            try:
                today_key = time.strftime("%Y-%m-%d", now_struct)
                if last_daily_day != today_key and current_hour >= DAILY_TASK_HOUR:
                    last_daily_day = today_key
                    try:
                        backup_all_files(self.bot, self.admin_chat_id)
                    except Exception as e:
                        self.logger.error(f"Авто-бэкап: {e}")
                    try:
                        vip_active = sum(1 for t in gamify_store["vip_until"].values() if t > now_time)
                        self.sender.send_message_direct(
                            self.admin_chat_id,
                            "✅ *Ежедневный отчёт бота*\n"
                            f"👥 Пользователей: *{len(verified_users)}*\n"
                            f"👑 VIP активных: *{vip_active}*\n"
                            f"📢 Активных реклам: *{len(self.ads_manager.storage)}*\n"
                            f"🔔 Подписок на комбо: *{sum(len(v) for v in combo_subscribers.values())}*\n"
                            f"⏰ Активных таймеров: *{sum(len(t) for t in user_game_timers.values())}*\n"
                            f"🌅 Дайджест-подписок: *{len(digest_subs)}* · 📈 Ценовых алертов: *{len(price_alerts)}*",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        self.logger.error(f"Отчёт: {e}")
                    try:
                        self._send_daily_digest()
                    except Exception as e:
                        self.logger.error(f"Дайджест: {e}")
                    # Уборка: чистим просроченный VIP и пустые записи очков.
                    try:
                        changed = False
                        for _u in [u for u, t in list(gamify_store["vip_until"].items()) if t <= now_time]:
                            gamify_store["vip_until"].pop(_u, None); changed = True
                        for _u in [u for u, p in list(gamify_store["points"].items()) if not p]:
                            gamify_store["points"].pop(_u, None); changed = True
                        if changed:
                            save_gamify()
                    except Exception as e:
                        self.logger.error(f"Уборка: {e}")
            except Exception as e:
                self.logger.error(f"Ошибка ежедневных задач: {e}")

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
            self.sender.send_message_direct(chat_id, t("verify_first", get_lang(chat_id)))
            return

        # Мгновенный визуальный отклик: показываем «печатает…», чтобы
        # пользователь понимал, что запрос принят и обрабатывается.
        try:
            self.bot.send_chat_action(chat_id, "typing")
        except Exception:
            pass

        # Мини-уведомление об облегчённом режиме (не чаще раза в 30 мин).
        maybe_notify_degraded(self.sender, chat_id)

        # Нормализуем локализованную кнопку меню → каноническая (RU) метка,
        # чтобы вся маршрутизация ниже работала без изменений на любом языке.
        text = LABEL_TO_CANON.get(message.text, message.text)
        if text in ["🚀 Меню комбо-игр"]:
            keyboard, total_count = get_combo_list_keyboard(page=0)
            self.sender.send_message_direct(chat_id, f"🎮 **Активные комбо-проекты**\nВсего доступно игр с комбо: **{total_count}**\n\nВыберите проект из списка ниже:", reply_markup=keyboard)
            
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
                # Сначала пробуем отдать комбо дня из кэша (мгновенно, без скрейпинга).
                fid, dtext = find_today_combo_fileid(key)
                if fid:
                    try:
                        self.bot.send_photo(chat_id, fid, caption=f"🎯 **{info.get('name', 'Комбо')}**\n📅 `{dtext}`", parse_mode="Markdown")
                        continue
                    except Exception:
                        pass
                img_url, date_text = self.manager.fetch_combo(key)
                img_bytes = image_handler.resize_img(img_url) if img_url else None
                if not img_bytes:
                    # Сайт недоступен → отдаём последнее известное комбо.
                    lfid, ldate = find_last_combo_fileid(key)
                    if lfid:
                        try:
                            self.bot.send_photo(chat_id, lfid, caption=f"🎯 **{info.get('name', 'Комбо')}**\n📅 `{ldate}` · _последнее известное (сайт недоступен)_", parse_mode="Markdown")
                            continue
                        except Exception:
                            pass
                send_combo_result(chat_id, info, img_bytes, date_text)
        elif text in ["🧮 Крипто-курс", "/calc"]:
            self.sender.send_message_direct(chat_id, "🧮 **Выберите криптовалюту:**", reply_markup=get_crypto_currency_keyboard())
        elif text in ["📊 Защита фермы", "/farm"]:
            found = sum(1 for v in self.manager.found_today.values() if v)
            total_games = len(self.manager.combo_games)
            if str(chat_id) == str(ADMIN_CHAT_ID):
                # Полная внутренняя статистика — ТОЛЬКО админу.
                status = (
                    "🛡️ **Статус защиты бота:**\n\n"
                    f"👥 Верифицировано пользователей: **{len(self.verified_users)}**\n"
                    f"🚫 Заблокировано (спам/скам): **{len(account_guard.banned)}**\n"
                    f"🔗 Скам-доменов в базе: **{len(link_guard.scam_domains)}**\n"
                    f"🧾 Проверено оплат (хэшей): **{len(used_tx_hashes)}**\n"
                    f"🎯 Комбо найдено сегодня: **{found}/{total_games}**\n\n"
                    "✅ Все системы защиты активны."
                )
            else:
                # Для пользователей — без внутренних цифр (только статус защиты).
                status = (
                    "🛡️ **Статус защиты бота:**\n\n"
                    f"🎯 Комбо найдено сегодня: **{found}/{total_games}**\n\n"
                    "✅ Активны:\n"
                    "• 🔗 Антискам-проверка ссылок\n"
                    "• 🚫 Антифлуд и капча\n"
                    "• 🕵️ Проверка аккаунтов\n"
                    "• 💳 Авто-проверка оплат"
                )
            self.sender.send_message_direct(chat_id, status, parse_mode="Markdown")
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
            self.sender.send_message_direct(
                chat_id,
                "💬 *Отзывы и предложения* 🐾\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "Поделитесь мнением или прочитайте отзывы других 👇",
                reply_markup=get_reviews_keyboard(), parse_mode="Markdown"
            )
        elif text in ["📢 Реклама и монетизация", "/ads"]:
            self.sender.send_message_direct(
                chat_id,
                "📢 *Реклама и монетизация*\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "📣 Ваш пост увидит *вся база* пользователей.\n"
                "💳 Оплата напрямую в крипте · запуск автоматом 👇",
                reply_markup=get_ads_keyboard(), parse_mode="Markdown"
            )
        elif text in ["👥 Друзья", "👥 Пригласить друзей", "/invite"]:
            lang = get_lang(chat_id)
            link = f"https://t.me/{get_bot_username()}?start=ref_{chat_id}"
            self.sender.send_message_direct(
                chat_id,
                t("invite", lang).format(link=link, count=referral_count(chat_id), points=get_points(chat_id)),
                parse_mode="Markdown"
            )
        elif text in ["🌐 Язык", "/lang"]:
            self.sender.send_message_direct(chat_id, t("lang_choose", get_lang(chat_id)), reply_markup=lang_keyboard())
        elif text in ["💎 VIP", "/vip"]:
            lang = get_lang(chat_id)
            head = t("vip_active", lang).format(days=vip_days_left(chat_id)) if is_vip(chat_id) else t("vip_inactive", lang)
            self.sender.send_message_direct(
                chat_id, head + t("vip_body", lang),
                reply_markup=get_vip_tariffs_keyboard(), parse_mode="Markdown"
            )
        elif text in ["🌅 Дайджест", "/digest"]:
            if chat_id in digest_subs:
                digest_subs.discard(chat_id)
                save_digest_subs()
                self.sender.send_message_direct(chat_id, "🌅 Утренний дайджест *отключён*.", parse_mode="Markdown")
            else:
                digest_subs.add(chat_id)
                save_digest_subs()
                self.sender.send_message_direct(chat_id, "🌅 Утренний дайджест *включён*!\nКаждое утро — комбо дня + твоя серия. Выключить: /digest", parse_mode="Markdown")
        elif text == "/alert_clear":
            before = len(price_alerts)
            price_alerts[:] = [a for a in price_alerts if a.get("user") != chat_id]
            save_price_alerts()
            self.sender.send_message_direct(chat_id, f"🗑 Удалено ваших алертов: *{before - len(price_alerts)}*.", parse_mode="Markdown")
        elif text.startswith("/alert"):
            m = re.match(r'/alert\s+([A-Za-z]{2,6})\s*([<>])\s*([\d.,]+)', text)
            if m:
                coin = m.group(1).lower()
                op = m.group(2)
                try:
                    val = float(m.group(3).replace(",", "."))
                except ValueError:
                    val = 0.0
                if coin not in COIN_ID_MAP:
                    self.sender.send_message_direct(chat_id, f"⚠️ Монета не поддерживается. Доступно: {', '.join(c.upper() for c in COIN_ID_MAP)}.")
                elif val <= 0:
                    self.sender.send_message_direct(chat_id, "⚠️ Укажите цену больше нуля. Пример: `/alert BTC > 70000`", parse_mode="Markdown")
                else:
                    # Анти-спам: не больше 10 алертов на пользователя.
                    if sum(1 for a in price_alerts if a.get("user") == chat_id) >= 10:
                        self.sender.send_message_direct(chat_id, "⚠️ Достигнут лимит 10 алертов. Очистите: /alert_clear")
                    else:
                        price_alerts.append({"user": chat_id, "coin": coin, "op": op, "value": val})
                        save_price_alerts()
                        self.sender.send_message_direct(chat_id, f"🔔 Алерт создан: уведомлю, когда *{coin.upper()} {op} {val:g}$*.", parse_mode="Markdown")
            else:
                mine = [a for a in price_alerts if a.get("user") == chat_id]
                cur = "\n".join(f"• {a['coin'].upper()} {a['op']} {a['value']:g}$" for a in mine) or "— пока нет активных алертов"
                self.sender.send_message_direct(
                    chat_id,
                    "🔔 *Ценовые алерты*\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "Формат: `/alert BTC > 70000` или `/alert TON < 5`\n"
                    f"Монеты: {', '.join(c.upper() for c in COIN_ID_MAP)}\n\n"
                    f"Твои алерты:\n{cur}\n\n"
                    "Очистить все: /alert_clear",
                    parse_mode="Markdown"
                )
        elif text in ["❓ Помощь", "/help"]:
            self.sender.send_message_direct(chat_id, t("help", get_lang(chat_id)), parse_mode="Markdown")
        elif text in ["🏆 Топ пригласивших", "/top"]:
            top = points_leaderboard(10)
            if not top:
                self.sender.send_message_direct(chat_id, "🏆 Рейтинг пока пуст. Заходи каждый день и приглашай друзей — /invite!")
            else:
                medals = ["🥇", "🥈", "🥉"]
                lines = ["🏆 *ТОП игроков* (по очкам):", "━━━━━━━━━━━━━━━━━━"]
                for i, (uid, pts) in enumerate(top):
                    badge = medals[i] if i < 3 else f"{i + 1}."
                    vip = " 👑" if is_vip(uid) else ""
                    lines.append(f"{badge} *{display_name(uid)}* (`{mask_id(uid)}`){vip} — *{pts}* очк. · 👥 {referral_count(uid)}")
                self.sender.send_message_direct(chat_id, "\n".join(lines), parse_mode="Markdown")
        elif text == "/backup" and str(chat_id) == str(ADMIN_CHAT_ID):
            self.sender.send_message_direct(chat_id, "💾 Готовлю резервную копию всех данных...", parse_mode="Markdown")
            backup_all_files(self.bot, chat_id)
        elif text.startswith("/vipgrant") and str(chat_id) == str(ADMIN_CHAT_ID):
            m = re.match(r'/vipgrant\s+(\d+)\s+(\d+)', text)
            if m:
                tuid, days = int(m.group(1)), int(m.group(2))
                grant_vip(tuid, days)
                self.sender.send_message_direct(chat_id, f"👑 VIP выдан `{tuid}` на *{days}* дн.", parse_mode="Markdown")
                try:
                    self.sender.send_message_direct(tuid, f"👑 Вам активирован VIP на *{days}* дн.! Спасибо.", parse_mode="Markdown")
                except Exception:
                    pass
            else:
                self.sender.send_message_direct(chat_id, "Формат: `/vipgrant <id> <дней>`", parse_mode="Markdown")
        elif text == "/stats" and str(chat_id) == str(ADMIN_CHAT_ID):
            active_timers = sum(len(t) for t in user_game_timers.values())
            subs_total = sum(len(v) for v in combo_subscribers.values())
            total_ref = sum(len(v) for v in referral_store["invited"].values())
            self.sender.send_message_direct(
                chat_id,
                "🎛 *Админ-панель — статистика*\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"👥 Пользователей: *{len(self.verified_users)}*\n"
                f"🚫 Забанено: *{len(account_guard.banned)}*\n"
                f"⏰ Активных таймеров: *{active_timers}*\n"
                f"🔔 Подписок на комбо: *{subs_total}*\n"
                f"📢 Активных реклам: *{len(ads_manager.storage)}*\n"
                f"🧾 Заявок в ожидании: *{len(pending_ad_orders)}*\n"
                f"💬 Отзывов: *{len(user_reviews_storage)}*\n"
                f"💎 Скринов выплат: *{len(cloud_proofs)}*\n"
                f"👥 Всего рефералов: *{total_ref}*\n"
                f"✅ Проверено оплат: *{len(used_tx_hashes)}*\n"
                f"📨 В очереди дорассылки: *{len(retry_queue)}*\n"
                f"🌐 Внешняя сеть: {'⚠️ деградация' if is_degraded() else '✅ OK'}",
                parse_mode="Markdown"
            )
        elif text == "/broadcast" and str(chat_id) == str(ADMIN_CHAT_ID):
            user_input_states[chat_id] = {"step": "waiting_admin_broadcast"}
            self.sender.send_message_direct(
                chat_id,
                "📣 *Массовая рассылка.*\nПришлите текст объявления одним сообщением — "
                "оно уйдёт ВСЕМ пользователям бота.",
                parse_mode="Markdown"
            )
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
        if account_guard.is_banned(message.from_user.id):
            return
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
            save_user_stats()
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
            save_proofs()
            try:
                self.bot.reply_to(message, "✅ Скрин сохранен в облачном хранилище!")
            except Exception:
                pass

    def handle_text_all(self, message: types.Message):
        """Универсальный обработчик входящих текстовых сообщений и состояний диалога."""
        chat_id = message.chat.id
        raw_text = message.text.strip()

        uid = message.from_user.id
        # Забаненных не обслуживаем.
        if account_guard.is_banned(uid):
            return
        # Анти-спам: резкий флуд → страйк, при рецидиве — бан.
        if sec_guard.check_brute_force(chat_id):
            if account_guard.strike(uid, "спам/флуд сообщениями"):
                try:
                    self.sender.send_message_direct(chat_id, "🚫 Вы заблокированы за спам.")
                except Exception:
                    pass
            else:
                try:
                    self.sender.send_message_direct(chat_id, "⏳ Слишком много сообщений подряд. Помедленнее, пожалуйста.")
                except Exception:
                    pass
            return

        if chat_id not in self.verified_users:
            self.sender.send_message_direct(chat_id, "⚠️ Пожалуйста, пройдите верификацию через /start.")
            return

        # Скриншот профиля НЕОБЯЗАТЕЛЕН: если ждали фото, но пришёл текст —
        # значит пользователь его пропустил (прогресс уже сохранён). Сбрасываем
        # состояние, чтобы будущее чужое фото не прикрепилось к игре по ошибке.
        _pending = self.user_input_states.get(chat_id)
        if _pending and _pending.get("step") == "waiting_photo":
            self.user_input_states.pop(chat_id, None)

        # 0. Админская массовая рассылка (объявление всем пользователям).
        if chat_id == self.admin_chat_id and self.user_input_states.get(chat_id, {}).get("step") == "waiting_admin_broadcast":
            self.user_input_states.pop(chat_id, None)
            self.sender.broadcast_message(raw_text, self.verified_users, self.admin_chat_id)
            self.sender.send_message_direct(chat_id, "📣 Рассылка запущена по всей базе. Отчёт придёт по завершении.", parse_mode="Markdown")
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
            save_reviews()
            self.sender.send_message_direct(self.admin_chat_id, f"💬 **Новый отзыв от {user_name}:**\n\n`{clean_review_text}`", parse_mode="Markdown")
            self.sender.send_message_direct(chat_id, "✅ **Спасибо за ваш отзыв!**", reply_markup=get_reviews_keyboard(), parse_mode="Markdown")
            return

        # 2. Обработка рекламного креатива
        if chat_id in self.user_input_states and self.user_input_states[chat_id].get("step") == "waiting_ad_content":
            order_data = self.user_input_states.pop(chat_id, None)
            tariff = order_data["tariff"]
            tariff_key = order_data.get("tariff_key", "")
            coin = order_data.get("coin", "")
            network = order_data.get("network", "")
            wallet_key = order_data.get("wallet_key", "")

            # --- АВТО-ПОДТВЕРЖДЕНИЕ ОПЛАТЫ ПО ХЭШУ (BTC / USDT-TRC20) ---
            auto_note = ""
            tinfo = ADS_TARIFFS.get(tariff_key, {})
            expected_usd = parse_price_usd(tinfo.get("price", "0"))
            our_addr = SAFEPAL_WALLETS.get(wallet_key, {}).get("address", "")
            # Хэш ищем по-разному: TON использует base64, остальные — hex.
            if network == "ton":
                tx_hash = extract_ton_hash(raw_text)
            else:
                tx_hash = extract_tx_hash(raw_text)

            verify_fn = None
            if network == "bitcoin":
                verify_fn = verify_btc
            elif network == "ton":
                verify_fn = verify_ton
            elif network == "tron":
                verify_fn = verify_usdt_trc20

            if verify_fn:
                if not tx_hash:
                    auto_note = "\n⚠️ Авто-проверка: хэш транзакции не найден в сообщении."
                elif not our_addr:
                    auto_note = "\n⚠️ Авто-проверка: адрес получателя не настроен."
                else:
                    ok, reason = verify_fn(tx_hash, expected_usd, our_addr)
                    if ok:
                        # Для TON помечаем канонический hex-хэш (как в проверке).
                        canon_hash = _ton_hash_to_hex(tx_hash) if network == "ton" else tx_hash
                        mark_tx_used(canon_hash or tx_hash)
                        order_id = f"ord_{chat_id}_{int(time.time())}"
                        dur_h = tinfo.get("duration_hours", 0)

                        # Готовим креатив (без хэша) и проверяем его безопасность
                        # перед рассылкой по всей базе пользователей.
                        creative = clean_ad_creative(raw_text, canon_hash or tx_hash)
                        is_threat, threat_reason = self.security.analyze_traffic(creative)

                        if is_threat:
                            # Оплата прошла, но креатив подозрителен → ручная модерация,
                            # без автоматической рассылки.
                            self.pending_ad_orders[order_id] = {
                                "user_id": chat_id, "tariff": tariff, "tariff_key": tariff_key,
                                "coin": coin, "content": creative, "created_at": time.time(),
                                "paid": True,
                            }
                            review_kb = types.InlineKeyboardMarkup()
                            review_kb.row(types.InlineKeyboardButton(text="✅ Одобрить и разослать", callback_data=f"adm_pay_ok_{order_id}"))
                            review_kb.row(types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_pay_no_{order_id}"))
                            self.sender.send_message_direct(
                                self.admin_chat_id,
                                f"🛡 **Оплата подтверждена, но креатив требует проверки!**\n"
                                f"👤 Клиент: `{chat_id}`\n📋 Тариф: `{tariff}`\n"
                                f"⚠️ Причина: {threat_reason}\n\n📝 **Креатив:**\n{creative}",
                                reply_markup=review_kb, parse_mode="Markdown"
                            )
                            self.sender.send_message_direct(
                                chat_id,
                                "🎉 **Оплата подтверждена!**\n\n"
                                "🛡 Ваше объявление отправлено на быструю проверку модератором "
                                "и будет разослано сразу после одобрения.",
                                reply_markup=get_ads_keyboard(), parse_mode="Markdown"
                            )
                            return

                        # Креатив чистый — сохраняем размещение и запускаем рассылку.
                        if dur_h > 0:
                            try:
                                ads_manager.add_ad(order_id, chat_id, time.time() + dur_h * 3600, creative)
                            except Exception as e:
                                self.logger.error(f"Ошибка запуска рекламы: {e}")

                        self.sender.broadcast_ad(
                            creative, self.verified_users, self.admin_chat_id,
                            tariff_name=tariff, order_id=order_id
                        )

                        self.sender.send_message_direct(
                            chat_id,
                            f"🎉 **Оплата подтверждена автоматически!**\n{reason}\n\n"
                            "🚀 Ваша реклама уже рассылается по всей базе пользователей. Спасибо за сотрудничество!",
                            reply_markup=get_ads_keyboard(),
                            parse_mode="Markdown"
                        )
                        self.sender.send_message_direct(
                            self.admin_chat_id,
                            f"🤖 **Авто-подтверждение оплаты**\n"
                            f"👤 Клиент: `{chat_id}`\n"
                            f"📋 Тариф: `{tariff}`\n"
                            f"💰 {reason}\n"
                            f"🧾 Hash: `{tx_hash}`\n\n"
                            f"📝 **Креатив:**\n{creative}",
                            parse_mode="Markdown"
                        )
                        return
                    else:
                        auto_note = f"\n⚠️ Авто-проверка не пройдена: {reason}"

            # --- РЕЗЕРВ: ручное подтверждение администратором ---
            order_id = f"ord_{chat_id}_{int(time.time())}"
            self.pending_ad_orders[order_id] = {
                "user_id": chat_id,
                "tariff": tariff,
                "tariff_key": tariff_key,
                "coin": coin,
                "content": raw_text,
                "created_at": time.time()
            }

            admin_markup = types.InlineKeyboardMarkup()
            admin_markup.row(types.InlineKeyboardButton(text="✅ Оплата поступила (Запустить рекламу)", callback_data=f"adm_pay_ok_{order_id}"))
            admin_markup.row(types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_pay_no_{order_id}"))

            self.sender.send_message_direct(
                self.admin_chat_id,
                f"📢 **Заявка на рекламу ожидает подтверждения оплаты!**\n"
                f"👤 Заказчик: `{chat_id}`\n"
                f"📋 Тариф: `{tariff}`\n"
                f"💰 Оплата через: `{coin.upper()}`{auto_note}\n\n"
                f"📝 **Креатив:**\n{raw_text}",
                reply_markup=admin_markup,
                parse_mode="Markdown"
            )
            self.sender.send_message_direct(
                chat_id,
                "✅ **Ваш рекламный креатив принят!**\nЗаявка отправлена на проверку поступления оплаты.",
                reply_markup=get_ads_keyboard(),
                parse_mode="Markdown"
            )
            return

        # 2b. Обработка оплаты VIP по хэшу транзакции
        if chat_id in self.user_input_states and self.user_input_states[chat_id].get("step") == "waiting_vip_hash":
            od = self.user_input_states.pop(chat_id, None)
            vinfo = VIP_TARIFFS.get(od.get("vip_key"), {})
            days = vinfo.get("days", 0)
            network = od.get("network", "")
            wallet_key = od.get("wallet_key", "")
            expected_usd = parse_price_usd(vinfo.get("price", "0"))
            our_addr = SAFEPAL_WALLETS.get(wallet_key, {}).get("address", "")
            tx_hash = extract_ton_hash(raw_text) if network == "ton" else extract_tx_hash(raw_text)
            verify_fn = {"bitcoin": verify_btc, "ton": verify_ton, "tron": verify_usdt_trc20}.get(network)

            if verify_fn and tx_hash and our_addr:
                ok, reason = verify_fn(tx_hash, expected_usd, our_addr)
                if ok:
                    canon = _ton_hash_to_hex(tx_hash) if network == "ton" else tx_hash
                    mark_tx_used(canon or tx_hash)
                    grant_vip(chat_id, days)
                    self.sender.send_message_direct(
                        chat_id,
                        f"👑 **VIP активирован на {days} дн.!**\n{reason}\n\n"
                        "🚫 Реклама отключена · 💎 бейдж выдан. Спасибо за поддержку!",
                        parse_mode="Markdown"
                    )
                    self.sender.send_message_direct(
                        self.admin_chat_id,
                        f"👑 **Куплен VIP**\n👤 `{chat_id}`\n📋 {vinfo.get('name')}\n💰 {reason}",
                        parse_mode="Markdown"
                    )
                    return

            # Авто-проверка не прошла → на ручное подтверждение админом.
            self.sender.send_message_direct(
                self.admin_chat_id,
                f"👑 **Заявка на VIP (ручная проверка)**\n"
                f"👤 `{chat_id}`\n📋 {vinfo.get('name', '?')} · {days} дн.\n"
                f"🧾 Сообщение: `{raw_text[:200]}`\n\n"
                f"Выдать вручную: `/vipgrant {chat_id} {days}`",
                parse_mode="Markdown"
            )
            self.sender.send_message_direct(
                chat_id,
                "🕒 Оплата отправлена на проверку. VIP активируют после подтверждения.",
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
                save_timers()

                game_name = (
                    self.manager.combo_games[game_key]["name"] if game_key in self.manager.combo_games 
                    else self.manager.independent_farms.get(game_key, {}).get("name", game_key)
                )
                self.sender.send_message_direct(chat_id, f"✅ Успешно! Таймер для *{game_name}* установлен на **{hours_val} ч.**", reply_markup=get_timers_games_keyboard(), parse_mode="Markdown")
                return
            except Exception:
                self.sender.send_message_direct(chat_id, "⚠️ Неверный формат! Введите число (например: `2.5`):", parse_mode="Markdown")
                return

        # 3b. Добавление игры в профиль: «Название | Уровень». СКРИНШОТ НЕОБЯЗАТЕЛЕН.
        if chat_id in self.user_input_states and self.user_input_states[chat_id].get("step") == "waiting_game_info":
            if "|" in raw_text:
                game, stat = [p.strip() for p in raw_text.split("|", 1)]
            else:
                game, stat = raw_text.strip(), "—"
            if not game:
                self.sender.send_message_direct(chat_id, "⚠️ Формат: `Название игры | Уровень`", parse_mode="Markdown")
                return
            game = game[:24]                       # имя коротким → callback_data < 64 байт
            if chat_id not in self.user_game_stats:
                self.user_game_stats[chat_id] = {}
            prev_photo = self.user_game_stats[chat_id].get(game, {}).get("photo")
            self.user_game_stats[chat_id][game] = {"stat": stat, "photo": prev_photo}
            save_user_stats()
            self.user_input_states[chat_id] = {"step": "waiting_photo", "game": game, "stat": stat}
            self.sender.send_message_direct(
                chat_id,
                f"✅ Прогресс для *{game}* сохранён (уровень: `{stat}`).\n"
                "📸 Скриншот — по желанию: пришлите фото, чтобы прикрепить (необязательно).",
                parse_mode="Markdown"
            )
            return

        # 3c. Ввод уровня для игры (кнопка в профиле). СКРИНШОТ НЕОБЯЗАТЕЛЕН:
        #     прогресс сохраняем сразу; фото (если пришлёт) просто прикрепится.
        #     Само фото хранится на серверах Telegram (file_id), не на телефоне.
        if chat_id in self.user_input_states and self.user_input_states[chat_id].get("step") == "waiting_game_stat":
            st = self.user_input_states[chat_id]
            game = st.get("game", "Игра")
            stat = raw_text.strip() or "—"
            if chat_id not in self.user_game_stats:
                self.user_game_stats[chat_id] = {}
            # При редактировании сохраняем ранее прикреплённое фото.
            prev_photo = self.user_game_stats[chat_id].get(game, {}).get("photo")
            self.user_game_stats[chat_id][game] = {"stat": stat, "photo": prev_photo}
            save_user_stats()
            self.user_input_states[chat_id] = {"step": "waiting_photo", "game": game, "stat": stat}
            self.sender.send_message_direct(
                chat_id,
                f"✅ Прогресс для *{game}* сохранён (уровень: `{stat}`).\n"
                "📸 Скриншот — по желанию: пришлите фото, чтобы прикрепить (необязательно).",
                parse_mode="Markdown"
            )
            return

        # 4. Проверка ссылок (скоринг: скам / фишинг / вирус) + общая безопасность.
        text = self.security.sanitize_input(raw_text)

        # Если в сообщении есть ссылки — анализируем и показываем вердикт.
        # Скам/подозрительные ссылки блокируются и помечаются 🚨/⚠️.
        link_verdict = link_guard.analyze(raw_text)
        if link_verdict["links"]:
            self.sender.send_message_direct(chat_id, link_verdict["message"], parse_mode=None)
            return

        # Блокируем ТОЛЬКО реальные угрозы: analyze_traffic сам ловит скам-@юзернеймы
        # по маркерам (SCAM_USERNAME_MARKERS). Обычные «@» и e-mail больше не блокируем.
        # Ссылки (в т.ч. t.me/) уже проверены выше через link_guard.
        is_threat, security_msg = self.security.analyze_traffic(text)
        if is_threat:
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
                res_data = cached_json_get(url).get(c_id, {})
                
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
                if not system_health.get("prices_ok", True):
                    report_text += "\n\n⚠️ _Данные из кэша: внешняя сеть временно недоступна._"

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
        self.user_input_states = user_input_states_storage
        self.user_game_timers = user_game_timers_storage
        self.user_calc_states = user_calc_states_storage
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

            # Забаненных не обслуживаем.
            if account_guard.is_banned(call.from_user.id):
                return

            if data.startswith("advcap_"):
                if data.replace("advcap_", "") == self.advanced_captchas.get(chat_id):
                    save_verified_user(chat_id)
                    self.advanced_captchas.pop(chat_id, None)
                    # Реферал: кредитуем пригласившего (если был) после верификации.
                    ref = pending_ref.pop(chat_id, None)
                    if ref and record_referral(chat_id, ref):
                        add_points(ref, 50)          # награда за приглашение
                        try:
                            self.sender.send_message_direct(
                                ref,
                                f"🎉 По вашей ссылке присоединился новый пользователь!\n"
                                f"🎁 *+50 очков* · 👥 Всего приглашено: *{referral_count(ref)}* · 💰 Очки: *{get_points(ref)}*",
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
                    try:
                        self.bot.edit_message_text("✅ **Доступ открыт!**", chat_id, call.message.message_id, parse_mode="Markdown")
                    except:
                        pass
                    self.sender.send_message_direct(chat_id, t("main_menu_label", get_lang(chat_id)), reply_markup=main_menu_kb(chat_id))
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

            # Смена языка интерфейса (RU/EN/FR).
            if data.startswith("langset_"):
                lang = data.split("_")[1]
                set_lang(chat_id, lang)
                try:
                    self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
                except Exception:
                    pass
                self.sender.send_message_direct(chat_id, t("lang_set", lang), reply_markup=main_menu_kb(chat_id))
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
                
                # Атомарно забираем заявку: второй (двойной) клик получит None
                # и не запустит повторную рассылку по всей базе.
                order = self.pending_ad_orders.pop(order_id, None)
                if not order:
                    try:
                        self.bot.answer_callback_query(call.id, "Заказ не найден или уже обработан", show_alert=True)
                    except:
                        pass
                    return

                target_user_id = order["user_id"]

                if action == "ok":
                    # Срок закрепа берём из тарифа (24ч / 7 дней / комбо…).
                    tinfo = ADS_TARIFFS.get(order.get("tariff_key"), {})
                    dur_h = tinfo.get("duration_hours", 0)
                    creative = clean_ad_creative(order.get("content", ""))
                    if dur_h > 0:
                        expire_timestamp = time.time() + dur_h * 3600
                        self.ads_manager.add_ad(order_id, target_user_id, expire_timestamp, creative)

                    # Админ одобрил креатив — рассылаем его всем пользователям.
                    self.sender.broadcast_ad(
                        creative, self.verified_users, self.admin_chat_id,
                        tariff_name=order.get("tariff", ""), order_id=order_id
                    )

                    self.sender.send_message_direct(
                        target_user_id,
                        "🎉 **Оплата получена! Ваша реклама одобрена и рассылается по базе пользователей.**\nБлагодарим за сотрудничество!",
                        parse_mode="Markdown"
                    )
                    try:
                        self.bot.edit_message_text(f"✅ **Заказ подтверждён и разослан!** (Клиент: `{target_user_id}`)", chat_id, call.message.message_id, parse_mode="Markdown")
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
                        "💰 **Выберите тариф для размещения рекламы:**\nОплата производится напрямую в криптовалюте.",
                        chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_ads_tariffs_keyboard(), parse_mode="Markdown"
                    )
                except:
                    pass
                return

            if data == "ads_stats":
                audience = len(self.verified_users)
                games_count = len(self.manager.combo_games) + len(self.manager.independent_farms)
                # Персональная статистика: активные размещения ЭТОГО пользователя.
                my_ads = [(oid, d) for oid, d in self.ads_manager.storage.items() if d.get("user_id") == chat_id]

                lines = [
                    "📊 **Статистика аудитории:**\n",
                    f"👥 Аудитория (потенциальный охват): **{audience}** польз.",
                    f"🎮 Проектов в каталоге: **{games_count}**",
                ]
                if my_ads:
                    lines.append("\n📢 **Ваши активные размещения:**")
                    for oid, d in my_ads:
                        left = int(d.get("expire_time", 0) - time.time())
                        if left > 0:
                            lines.append(f"• `{oid}` — осталось {left // 3600}ч {(left % 3600) // 60}м · охват ~{audience}")
                        else:
                            lines.append(f"• `{oid}` — истекает")
                else:
                    lines.append("\n📢 У вас нет активных размещений. Купите рекламу кнопкой выше 👆")

                self.sender.send_message_direct(chat_id, "\n".join(lines), parse_mode="Markdown")
                return

            if data in ADS_TARIFFS:
                atinfo = ADS_TARIFFS[data]
                tariff_name = f"{atinfo['name']} ({atinfo['price']})"
                try:
                    self.bot.edit_message_text(
                        f"💎 Вы выбрали тариф: *{tariff_name}*.\n\n"
                        "👇 **Выберите криптовалюту для оплаты:**",
                        chat_id=chat_id, message_id=call.message.message_id, reply_markup=get_safepal_coins_keyboard(data), parse_mode="Markdown"
                    )
                except:
                    pass
                return

            if data.startswith("pay_"):
                # Формат: pay_<tariff_key>_<method>. tariff_key содержит "_"
                # (напр. adtariff_24h), а ключ метода — БЕЗ "_", поэтому метод =
                # ПОСЛЕДНИЙ сегмент, а тариф — всё между "pay_" и методом.
                parts = data.split("_")
                method_key = parts[-1]
                tariff_key = "_".join(parts[1:-1])

                tinfo = ADS_TARIFFS.get(tariff_key)
                if not tinfo:
                    try:
                        self.bot.answer_callback_query(call.id, "Тариф не найден", show_alert=True)
                    except:
                        pass
                    return

                method = PAYMENT_METHODS.get(method_key)
                if not method:
                    try:
                        self.bot.answer_callback_query(call.id, "Способ оплаты не найден", show_alert=True)
                    except:
                        pass
                    return

                tariff_name = f"{tinfo['name']} ({tinfo['price']})"

                # Анти-абуз: запрещаем вторую заявку, пока есть незакрытая.
                already = any(o.get("user_id") == chat_id for o in self.pending_ad_orders.values())
                if already:
                    self.sender.send_message_direct(
                        chat_id,
                        "⚠️ **У вас уже есть заявка на рекламу**, ожидающая проверки администратором.\n"
                        "Дождитесь решения, прежде чем оформлять новую.",
                        reply_markup=get_ads_keyboard(),
                        parse_mode="Markdown"
                    )
                    return

                wallet_info = SAFEPAL_WALLETS.get(
                    method["wallet_key"],
                    {"name": method["label"], "address": "ADRESS_NOT_SET"}
                )

                self.user_input_states[chat_id] = {
                    "step": "waiting_ad_content",
                    "tariff": tariff_name,
                    "tariff_key": tariff_key,
                    "method": method_key,
                    "coin": method["coin"],
                    "network": method["network"],
                    "wallet_key": method["wallet_key"],
                }

                pay_kb = types.InlineKeyboardMarkup()
                pay_kb.row(types.InlineKeyboardButton(text="🔙 Изменить тариф", callback_data="ads_buy"))
                pay_kb.row(types.InlineKeyboardButton(text="❌ Отменить заявку", callback_data="ad_cancel"))

                self.sender.send_message_direct(
                    chat_id,
                    f"🧾 **Ваш заказ**\n"
                    f"📋 Тариф: *{tariff_name}*\n"
                    f"💳 Способ: *{method['label']}*\n\n"
                    f"📌 **Адрес для оплаты** (нажмите, чтобы скопировать):\n"
                    f"`{wallet_info['address']}`\n\n"
                    f"⚠️ **Что делать дальше:**\n"
                    f"1️⃣ Отправьте оплату (*{tinfo['price']}* в {method['coin']}) на адрес выше.\n"
                    f"2️⃣ Пришлите **одним сообщением** текст рекламы + хэш транзакции.\n"
                    f"{'3️⃣ Оплата подтвердится автоматически после подтверждения сети (~10–30 мин для BTC).' if method['network'] == 'bitcoin' else '3️⃣ Оплата подтверждается автоматически по хэшу почти мгновенно.'}",
                    reply_markup=pay_kb,
                    parse_mode="Markdown"
                )
                return

            if data == "ad_cancel":
                st = self.user_input_states.get(chat_id)
                if st and st.get("step") == "waiting_ad_content":
                    self.user_input_states.pop(chat_id, None)
                self.sender.send_message_direct(
                    chat_id,
                    "❌ **Заявка на рекламу отменена.**",
                    reply_markup=get_ads_keyboard(),
                    parse_mode="Markdown"
                )
                return

            if data == "ads_menu_back":
                try:
                    self.bot.edit_message_text(
                        "📢 *Реклама и монетизация*\n"
                        "━━━━━━━━━━━━━━━━━━\n"
                        "📣 Ваш пост увидит *вся база* пользователей.\n"
                        "💳 Оплата напрямую в крипте · запуск автоматом 👇",
                        chat_id=chat_id, message_id=call.message.message_id,
                        reply_markup=get_ads_keyboard(), parse_mode="Markdown"
                    )
                except:
                    pass
                return

            # ── VIP-статус ──────────────────────────────────────────────
            if data in ("vip_open", "vip_menu_back"):
                head = (f"👑 *VIP активен* — осталось *{vip_days_left(chat_id)}* дн.\n"
                        if is_vip(chat_id) else "💎 *VIP-статус* пока не активен.\n")
                try:
                    self.bot.edit_message_text(
                        head + "━━━━━━━━━━━━━━━━━━\n"
                        "Преимущества: 🚫 без рекламы · 💎 бейдж в профиле и топе.\n\n"
                        "👇 Выберите тариф:",
                        chat_id=chat_id, message_id=call.message.message_id,
                        reply_markup=get_vip_tariffs_keyboard(), parse_mode="Markdown"
                    )
                except:
                    pass
                return

            if data in VIP_TARIFFS:
                v = VIP_TARIFFS[data]
                try:
                    self.bot.edit_message_text(
                        f"💎 Тариф: *{v['name']} ({v['price']})*\n\n👇 Выберите способ оплаты:",
                        chat_id=chat_id, message_id=call.message.message_id,
                        reply_markup=get_vip_coins_keyboard(data), parse_mode="Markdown"
                    )
                except:
                    pass
                return

            if data.startswith("vippay_"):
                parts = data.split("_")
                method_key = parts[-1]
                vip_key = parts[1]
                vinfo = VIP_TARIFFS.get(vip_key)
                method = PAYMENT_METHODS.get(method_key)
                if not vinfo or not method:
                    try:
                        self.bot.answer_callback_query(call.id, "Тариф/способ не найден", show_alert=True)
                    except:
                        pass
                    return
                wallet_info = SAFEPAL_WALLETS.get(method["wallet_key"], {"address": "ADRESS_NOT_SET"})
                self.user_input_states[chat_id] = {
                    "step": "waiting_vip_hash", "vip_key": vip_key,
                    "network": method["network"], "wallet_key": method["wallet_key"],
                    "coin": method["coin"],
                }
                self.sender.send_message_direct(
                    chat_id,
                    f"🧾 *Покупка VIP: {vinfo['name']}*\n"
                    f"💳 Способ: *{method['label']}*\n\n"
                    f"📌 *Адрес для оплаты* (нажмите, чтобы скопировать):\n"
                    f"`{wallet_info['address']}`\n\n"
                    f"1️⃣ Оплатите *{vinfo['price']}* в {method['coin']}.\n"
                    f"2️⃣ Пришлите *хэш транзакции* одним сообщением — VIP активируется автоматически.",
                    parse_mode="Markdown"
                )
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
                save_timers()
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
                    save_timers()
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

            # Клик по игре в профиле → показываем СТАТЫ ИМЕННО ЭТОЙ игры
            # (или предлагаем добавить, если их ещё нет).
            if data.startswith("profgame_"):
                gname = data[len("profgame_"):]
                info = user_game_stats.get(chat_id, {}).get(gname)
                if info:
                    caption = f"🎮 *{gname}*\n📊 Стат / Уровень: `{info.get('stat', 'Н/Д')}`"
                    row_kb = types.InlineKeyboardMarkup()
                    row_kb.row(
                        types.InlineKeyboardButton(text="✏️ Изменить", callback_data=f"statedit_{gname}"),
                        types.InlineKeyboardButton(text="🗑 Удалить", callback_data=f"statdel_{gname}")
                    )
                    if info.get("photo"):
                        try:
                            self.bot.send_photo(chat_id, photo=info["photo"], caption=caption, parse_mode="Markdown", reply_markup=row_kb)
                        except Exception:
                            self.sender.send_message_direct(chat_id, caption, parse_mode="Markdown", reply_markup=row_kb)
                    else:
                        self.sender.send_message_direct(chat_id, caption, parse_mode="Markdown", reply_markup=row_kb)
                else:
                    self.user_input_states[chat_id] = {"step": "waiting_game_stat", "game": gname}
                    self.sender.send_message_direct(
                        chat_id,
                        f"✍️ У вас пока нет прогресса для *{gname}*.\n"
                        "Введите ваш уровень/прогресс (например: `15` или `Уровень 20`):",
                        parse_mode="Markdown"
                    )
                return

            if data == "prof_view":
                show_user_profile(chat_id)
                return

            # Реферальная ссылка пользователя (из профиля).
            if data == "ref_invite":
                link = f"https://t.me/{get_bot_username()}?start=ref_{chat_id}"
                self.sender.send_message_direct(
                    chat_id,
                    "👥 *Приглашай друзей — поднимайся в топе!* 🏆\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "🔗 Твоя персональная ссылка:\n"
                    f"`{link}`\n\n"
                    f"👤 Уже приглашено: *{referral_count(chat_id)}*\n\n"
                    "Смотри рейтинг: /top",
                    parse_mode="Markdown"
                )
                return

            # Удаление конкретной строки статистики.
            if data.startswith("statdel_"):
                gname = data[len("statdel_"):]
                stats = user_game_stats.get(chat_id, {})
                if gname in stats:
                    stats.pop(gname, None)
                    save_user_stats()
                    try:
                        self.bot.answer_callback_query(call.id, f"🗑 «{gname}» удалено")
                    except Exception:
                        pass
                    try:
                        self.bot.delete_message(chat_id, call.message.message_id)
                    except Exception:
                        pass
                else:
                    try:
                        self.bot.answer_callback_query(call.id, "Уже удалено")
                    except Exception:
                        pass
                return

            # Изменение уровня конкретной строки статистики.
            if data.startswith("statedit_"):
                gname = data[len("statedit_"):]
                stats = user_game_stats.get(chat_id, {})
                if gname in stats:
                    self.user_input_states[chat_id] = {"step": "waiting_game_stat", "game": gname}
                    self.sender.send_message_direct(
                        chat_id,
                        f"✏️ Введите новый уровень/прогресс для *{gname}*:",
                        parse_mode="Markdown"
                    )
                else:
                    try:
                        self.bot.answer_callback_query(call.id, "Записи больше нет")
                    except Exception:
                        pass
                return

            # История найденных комбо (картинки берутся с серверов Telegram по file_id).
            if data == "combo_hist":
                try:
                    self.bot.answer_callback_query(call.id, "Загрузка истории...")
                except Exception:
                    pass
                if not combo_history:
                    self.sender.send_message_direct(chat_id, "📜 История комбо пока пуста. Загляните позже!")
                    return
                recent = list(reversed(combo_history))[:15]
                self.sender.send_message_direct(
                    chat_id,
                    f"📜 *История найденных комбо* (последние {len(recent)}):",
                    parse_mode="Markdown"
                )
                for h in recent:
                    cap = f"🎯 *{h.get('name', 'Комбо')}*\n📅 `{h.get('date', h.get('day', ''))}`"
                    fid = h.get("file_id")
                    if fid:
                        try:
                            self.bot.send_photo(chat_id, photo=fid, caption=cap, parse_mode="Markdown")
                        except Exception:
                            self.sender.send_message_direct(chat_id, cap, parse_mode="Markdown")
                    else:
                        self.sender.send_message_direct(chat_id, cap, parse_mode="Markdown")
                return

            if data.startswith("combopage_"):
                page = int(data.replace("combopage_", ""))
                keyboard, total_count = get_combo_list_keyboard(page=page)
                try:
                    self.bot.edit_message_text(f"🎮 **Комбо-проекты ({total_count})**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
                except:
                    pass
                return

            # Переключение подписки на авто-комбо игры.
            if data.startswith("combosub_"):
                parts = data.split("_")
                key = parts[1]
                page = parts[2] if len(parts) > 2 else "0"
                if key in self.manager.combo_games:
                    now_sub = toggle_combo_sub(key, chat_id)
                    try:
                        self.bot.answer_callback_query(call.id, "🔔 Вы подписаны на авто-комбо!" if now_sub else "🔕 Подписка отменена")
                    except Exception:
                        pass
                    kb = get_single_game_keyboard(key, page)
                    sub_text = "🔕 Отписаться от авто-комбо" if now_sub else "🔔 Подписаться на авто-комбо"
                    kb.row(types.InlineKeyboardButton(text=sub_text, callback_data=f"combosub_{key}_{page}"))
                    try:
                        self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=kb)
                    except Exception:
                        pass
                return

            if data.startswith("gamemenu_"):
                parts = data.split("_")
                if parts[1] in self.manager.combo_games:
                    kb = get_single_game_keyboard(parts[1], parts[2])
                    subbed = is_combo_subscribed(parts[1], chat_id)
                    sub_text = "🔕 Отписаться от авто-комбо" if subbed else "🔔 Подписаться на авто-комбо"
                    kb.row(types.InlineKeyboardButton(text=sub_text, callback_data=f"combosub_{parts[1]}_{parts[2]}"))
                    try:
                        self.bot.edit_message_text(f"🕹 **Меню: {self.manager.combo_games[parts[1]]['name']}**", chat_id=chat_id, message_id=call.message.message_id, reply_markup=kb, parse_mode="Markdown")
                    except Exception:
                        pass
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
                    # Комбо дня из кэша — мгновенно, без повторного скрейпинга.
                    fid, dtext = find_today_combo_fileid(key)
                    if fid:
                        try:
                            self.bot.send_photo(chat_id, fid, caption=f"🎯 **{self.manager.combo_games[key].get('name', 'Комбо')}**\n📅 `{dtext}`", parse_mode="Markdown")
                            return
                        except Exception:
                            pass
                    img_url, date_text = self.manager.fetch_combo(key)
                    img_bytes = image_handler.resize_img(img_url) if img_url else None
                    if not img_bytes:
                        lfid, ldate = find_last_combo_fileid(key)
                        if lfid:
                            try:
                                self.bot.send_photo(chat_id, lfid, caption=f"🎯 **{self.manager.combo_games[key].get('name', 'Комбо')}**\n📅 `{ldate}` · _последнее известное (сайт недоступен)_", parse_mode="Markdown")
                                return
                            except Exception:
                                pass
                    send_combo_result(chat_id, self.manager.combo_games[key], img_bytes, date_text)
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

        # Забаненных не обслуживаем.
        if account_guard.is_banned(chat_id):
            return

        # Админские команды модерации.
        if str(chat_id) == str(ADMIN_CHAT_ID):
            m = re.match(r'^\s*разбан\s+(\d+)\s*$', text, re.IGNORECASE)
            if m:
                account_guard.unban(int(m.group(1)))
                try:
                    self.bot.reply_to(message, f"✅ Пользователь {m.group(1)} разбанен.")
                except Exception:
                    pass
                return
            m = re.match(r'^\s*бан\s+юзер\s+(\d+)\s*$', text, re.IGNORECASE)
            if m:
                account_guard.ban(int(m.group(1)), "ручной бан админом")
                try:
                    self.bot.reply_to(message, f"🚫 Пользователь {m.group(1)} забанен.")
                except Exception:
                    pass
                return
            m = re.match(r'^\s*(?:бан|скам|scam|blacklist)\s+(\S+)\s*$', text, re.IGNORECASE)
            if m:
                ok = link_guard.add_scam_domain(m.group(1))
                try:
                    self.bot.reply_to(
                        message,
                        f"🚫 Домен добавлен в чёрный список скама: {m.group(1)}"
                        if ok else "⚠️ Это не похоже на домен. Пример: бан scam-site.top"
                    )
                except Exception:
                    pass
                return

        # Проверка ссылок ПЕРЕД ответом ИИ: скам/подозрительные — блокируем и помечаем.
        link_verdict = link_guard.analyze(text)
        if link_verdict["links"] and link_verdict["worst"] in ("scam", "suspicious"):
            try:
                self.bot.reply_to(message, link_verdict["message"])
            except Exception:
                pass
            return

        try:
            ai_response = self.ai.generate_response(text, chat_id=chat_id)
            # Без Markdown: ответы ИИ — обычный текст, чтобы произвольные
            # символы (в т.ч. в выученных знаниях) не ломали отправку.
            self.bot.reply_to(message, ai_response)
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

def get_vip_tariffs_keyboard():
    return MenuManager.get_matrix_keyboard(VIP_TARIFFS_DATA)

def get_vip_coins_keyboard(vip_key):
    kb = types.InlineKeyboardMarkup()
    for text, coin in CRYPTO_COINS_DATA:
        kb.row(types.InlineKeyboardButton(text=text, callback_data=f"vippay_{vip_key}_{coin}"))
    kb.row(types.InlineKeyboardButton(text="🔙 К тарифам VIP", callback_data="vip_open"))
    return kb

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

def main_menu_kb(chat_id):
    """Reply-клавиатура главного меню на языке пользователя.
    botv2 : bouton 🚀 App en tête qui ouvre le Mini App web (si WEBAPP_URL configuré)."""
    labels = MENU_LABELS.get(get_lang(chat_id), MAIN_MENU_BUTTONS)
    if not WEBAPP_URL:
        return MenuManager.get_reply_keyboard(labels)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    app_label = {"fr": "🚀 Ouvrir l'app", "en": "🚀 Open the app"}.get(get_lang(chat_id), "🚀 Открыть приложение")
    markup.row(types.KeyboardButton(app_label, web_app=types.WebAppInfo(url=WEBAPP_URL)))
    markup.add(*[types.KeyboardButton(x) for x in labels])
    return markup

def lang_keyboard():
    """Инлайн-выбор языка."""
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton(text="🇷🇺 Русский", callback_data="langset_ru"),
        types.InlineKeyboardButton(text="🇬🇧 English", callback_data="langset_en"),
        types.InlineKeyboardButton(text="🇫🇷 Français", callback_data="langset_fr"),
    )
    return kb

def send_message_direct(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    return sender.send_message_direct(chat_id, text, reply_markup, parse_mode)

def send_combo_result(chat_id, info, img_bytes, date_text):
    return sender.send_combo_result(chat_id, info, img_bytes, date_text)

def show_user_profile(chat_id):
    return profile_manager.show_user_profile(chat_id, user_game_stats)
    
def daily_auto_checker():
    scheduler_manager.run_daily_checker(user_game_timers)

# ============================================================
# АВТО-ПРОВЕРКА ОПЛАТЫ USDT-TRC20 ПО ХЭШУ ТРАНЗАКЦИИ (сеть Tron)
# ============================================================
# Официальный контракт USDT (TRC20) в сети Tron.
USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
# Файл с уже использованными хэшами (защита от повторного использования).
USED_TX_FILE = "used_tx_hashes.txt"

def _load_used_tx():
    s = set()
    if os.path.exists(USED_TX_FILE):
        try:
            with open(USED_TX_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    h = line.strip().lower()
                    if h:
                        s.add(h)
        except Exception as e:
            logger.error(f"Ошибка загрузки использованных tx: {e}")
    return s

used_tx_hashes = _load_used_tx()

def mark_tx_used(tx_hash: str):
    """Помечает хэш как использованный (в памяти и в файле)."""
    try:
        used_tx_hashes.add(tx_hash.lower())
        with open(USED_TX_FILE, "a", encoding="utf-8") as f:
            f.write(tx_hash.lower() + "\n")
    except Exception as e:
        logger.error(f"Ошибка сохранения использованного tx: {e}")

def parse_price_usd(price_str: str) -> float:
    """Извлекает число из строки цены вида '$15' -> 15.0."""
    m = re.search(r'\d+(?:\.\d+)?', price_str or "")
    return float(m.group(0)) if m else 0.0

def extract_tx_hash(text: str):
    """Ищет в тексте хэш транзакции Tron (64 hex-символа)."""
    m = re.search(r'\b[0-9a-fA-F]{64}\b', text or "")
    return m.group(0) if m else None

def verify_usdt_trc20(tx_hash: str, expected_usd: float, our_address: str):
    """
    Проверяет входящий USDT-TRC20 перевод по хэшу через публичный Tronscan API.
    Возвращает (ok: bool, reason: str). При любой неоднозначности → False
    (тогда сработает резервное ручное подтверждение админом).
    """
    tx_hash = (tx_hash or "").strip()
    if not tx_hash:
        return False, "Хэш транзакции не указан."
    if tx_hash.lower() in used_tx_hashes:
        return False, "Этот хэш уже был использован ранее."
    try:
        url = f"https://apilist.tronscanapi.com/api/transaction-info?hash={tx_hash}"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return False, "Не удалось получить данные транзакции (сеть)."
        data = r.json() or {}
        if not data:
            return False, "Транзакция не найдена в сети."

        # Подтверждённость и успешность
        if data.get("confirmed") is False:
            return False, "Транзакция ещё не подтверждена сетью."
        if data.get("contractRet") not in (None, "SUCCESS"):
            return False, "Транзакция завершилась неуспешно."

        info = data.get("tokenTransferInfo") or {}
        if not info:
            return False, "В транзакции нет TRC20-перевода."

        symbol = (info.get("symbol") or "").upper()
        contract = info.get("contract_address") or ""
        to_addr = info.get("to_address") or ""
        try:
            decimals = int(info.get("decimals") or 6)
            amount = int(info.get("amount_str") or "0") / (10 ** decimals)
        except Exception:
            return False, "Не удалось разобрать сумму перевода."

        if symbol != "USDT" or contract != USDT_TRC20_CONTRACT:
            return False, "Это не перевод USDT-TRC20."
        if to_addr != our_address:
            return False, "Перевод отправлен не на наш адрес."
        # USDT — стейблкоин (~$1). Допускаем -2% на округление.
        if amount + 1e-9 < expected_usd * 0.98:
            return False, f"Сумма ({amount:.2f} USDT) меньше требуемой ({expected_usd:.2f})."

        return True, f"Получено {amount:.2f} USDT."
    except Exception as e:
        logger.error(f"Ошибка проверки USDT-TRC20 tx: {e}")
        return False, "Ошибка проверки транзакции."

# ============================================================
# АВТО-ПРОВЕРКА ОПЛАТЫ BTC ПО ХЭШУ (сеть Bitcoin, API Blockstream)
# ============================================================
def get_btc_usd_rate() -> float:
    """Текущий курс BTC→USD через CoinGecko (кэш 60с, 0.0 при ошибке)."""
    try:
        data = cached_json_get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
        return float(data["bitcoin"]["usd"])
    except Exception as e:
        logger.error(f"Ошибка получения курса BTC: {e}")
        return 0.0

def verify_btc(tx_hash: str, expected_usd: float, our_address: str):
    """
    Проверяет входящий BTC-перевод по хэшу через публичный Blockstream API.
    Возвращает (ok: bool, reason: str). При любой неоднозначности → False
    (тогда сработает резервное ручное подтверждение админом).
    """
    tx_hash = (tx_hash or "").strip().lower()
    if not tx_hash:
        return False, "Хэш транзакции не указан."
    if tx_hash in used_tx_hashes:
        return False, "Этот хэш уже был использован ранее."
    try:
        r = requests.get(
            f"https://blockstream.info/api/tx/{tx_hash}",
            timeout=12, headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code != 200:
            return False, "Транзакция не найдена в сети BTC."
        tx = r.json() or {}

        status = tx.get("status") or {}
        if not status.get("confirmed", False):
            return False, "Транзакция ещё не подтверждена сетью."

        # Суммируем все выходы, ушедшие на наш адрес.
        received_sat = 0
        for o in tx.get("vout", []):
            if o.get("scriptpubkey_address") == our_address:
                received_sat += int(o.get("value") or 0)
        if received_sat <= 0:
            return False, "Перевод не найден на наш BTC-адрес."

        received_btc = received_sat / 1e8
        rate = get_btc_usd_rate()
        if rate <= 0:
            return False, "Не удалось получить курс BTC."
        expected_btc = expected_usd / rate
        # BTC волатилен — допускаем 5% отклонения курса.
        if received_btc + 1e-12 < expected_btc * 0.95:
            return False, (
                f"Сумма ({received_btc:.8f} BTC ≈ ${received_btc * rate:.2f}) "
                f"меньше требуемой (${expected_usd:.2f})."
            )
        return True, f"Получено {received_btc:.8f} BTC (≈ ${received_btc * rate:.2f})."
    except Exception as e:
        logger.error(f"Ошибка проверки BTC tx: {e}")
        return False, "Ошибка проверки транзакции."

# ============================================================
# АВТО-ПРОВЕРКА ОПЛАТЫ TON ПО ХЭШУ (сеть TON, API TonAPI)
# ============================================================
TON_API_BASE = "https://tonapi.io/v2"

def _ton_hash_to_hex(h: str):
    """Приводит хэш TON (hex или base64/base64url из tonviewer) к hex."""
    h = (h or "").strip()
    if re.fullmatch(r'[0-9a-fA-F]{64}', h):
        return h.lower()
    try:
        s = h.replace('-', '+').replace('_', '/')
        s += '=' * (-len(s) % 4)  # добить паддинг
        raw = base64.b64decode(s)
        if len(raw) == 32:
            return raw.hex()
    except Exception:
        pass
    return None

def extract_ton_hash(text: str):
    """Ищет хэш TON в тексте: из ссылки tonviewer/tonscan, hex или base64."""
    text = text or ""
    m = re.search(r'transaction/([A-Za-z0-9+/_\-]{43,44}=?)', text)
    if m:
        return m.group(1)
    m = re.search(r'\b[0-9a-fA-F]{64}\b', text)
    if m:
        return m.group(0)
    m = re.search(r'[A-Za-z0-9+/_\-]{43}=', text)
    if m:
        return m.group(0)
    return None

def _ton_address_raw(addr: str) -> str:
    """Через TonAPI получаем raw-форму адреса (0:hex) для надёжного сравнения."""
    try:
        r = requests.get(f"{TON_API_BASE}/address/{addr}/parse", timeout=10)
        if r.status_code == 200:
            return ((r.json() or {}).get("raw_form") or "").lower()
    except Exception as e:
        logger.error(f"Ошибка парсинга TON-адреса: {e}")
    return ""

def get_ton_usd_rate() -> float:
    """Текущий курс TON→USD через CoinGecko (кэш 60с, 0.0 при ошибке)."""
    try:
        data = cached_json_get("https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd")
        return float(data["the-open-network"]["usd"])
    except Exception as e:
        logger.error(f"Ошибка получения курса TON: {e}")
        return 0.0

def verify_ton(tx_hash: str, expected_usd: float, our_address: str):
    """
    Проверяет входящий TON-перевод по хэшу через публичный TonAPI.
    Возвращает (ok: bool, reason: str). При любой неоднозначности → False
    (тогда сработает резервное ручное подтверждение админом).
    """
    tx_hex = _ton_hash_to_hex(tx_hash)
    if not tx_hex:
        return False, "Не удалось распознать хэш транзакции TON."
    if tx_hex in used_tx_hashes:
        return False, "Этот хэш уже был использован ранее."
    try:
        r = requests.get(
            f"{TON_API_BASE}/blockchain/transactions/{tx_hex}",
            timeout=12, headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code != 200:
            return False, "Транзакция не найдена в сети TON."
        tx = r.json() or {}

        if tx.get("success") is False:
            return False, "Транзакция завершилась неуспешно."

        in_msg = tx.get("in_msg") or {}
        dest = ((in_msg.get("destination") or {}).get("address") or "")
        value_nano = int(in_msg.get("value") or 0)
        if value_nano <= 0:
            return False, "В транзакции нет входящего перевода TON."
        received_ton = value_nano / 1e9

        our_raw = _ton_address_raw(our_address)
        if our_raw and dest and our_raw != dest.lower():
            return False, "Перевод отправлен не на наш адрес."

        rate = get_ton_usd_rate()
        if rate <= 0:
            return False, "Не удалось получить курс TON."
        expected_ton = expected_usd / rate
        # TON волатилен — допускаем 5% отклонения курса.
        if received_ton + 1e-9 < expected_ton * 0.95:
            return False, (
                f"Сумма ({received_ton:.4f} TON ≈ ${received_ton * rate:.2f}) "
                f"меньше требуемой (${expected_usd:.2f})."
            )
        return True, f"Получено {received_ton:.4f} TON (≈ ${received_ton * rate:.2f})."
    except Exception as e:
        logger.error(f"Ошибка проверки TON tx: {e}")
        return False, "Ошибка проверки транзакции."

def generate_advanced_captcha(chat_id):
    return CaptchaManager.generate_advanced_captcha(chat_id, advanced_captchas)

def handle_menu_text(message: types.Message):
    menu_text_processor.handle_menu_text(message)


# ПРИМЕЧАНИЕ: catch-all обработчики (photo / любой текст / любой callback)
# регистрируются НИЖЕ — после bot_controller — чтобы /start, команды и
# кнопки меню имели приоритет над "ловушкой" func=lambda: True.


# --- ВСЕ ИНИЦИАЛИЗАЦИИ И ССЫЛКИ НА ОБЪЕКТЫ ---
# (здесь создаются message_processor, bot_controller, image_handler, manager и т.д.)

# Запуск фонового потока (интервал: 2 часа = 7200 секунд)
updater_thread = threading.Thread(target=background_independent_updater, args=(7200,), daemon=True)

# Инициализируем отправителя (если у вас bot и logger уже объявлены глобально)
sender = NotificationSender(bot, logger)
# Инициализация виртуального помощника
ai_assistant = BotVirtualAssistant()
# Инициализация усиленного защитного модуля
sec_guard = AdvancedSecurityGuard()
security_core = UltimateSecurityCore()
# Анализатор ссылок (скам/фишинг/вирус) — используется в чате ИИ и в общих сообщениях.
link_guard = LinkScamGuard(PHISHING_DOMAINS, GHOST_MODE_DOMAINS, SCAM_PATTERNS, NETWORK_CORE_BLACKLIST)
# Страж аккаунтов: боты, скам-имена, спам-флуд + чёрный список пользователей.
account_guard = AccountGuard(bot, SCAM_USERNAME_MARKERS, ADMIN_CHAT_ID)
# Инициализация менеджеров
image_handler = ImageHandler(logger, target_width=600)
manager = MiningComboManager()
# 1. Сначала создаем экземпляр процессора
message_processor = MessageProcessor(bot, logger, sender, manager)

# 2. Передаем его в контроллер (с маленькой буквы).
# Передаём ВСЕ локализованные метки меню (RU/EN/FR), чтобы кнопки ловились на любом языке.
bot_controller = TelegramBotController(bot, message_processor, BOT_COMMANDS_LIST, ALL_MENU_LABELS)

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

# ============================================================
# CATCH-ALL обработчики регистрируются ПОСЛЕДНИМИ,
# чтобы /start, команды и кнопки меню (bot_controller) имели приоритет.
# ============================================================
@bot.message_handler(content_types=['photo'])
def handle_photo(message: types.Message):
    message_input_handler.handle_photo(message)

@bot.message_handler(func=lambda m: True)
def handle_text_all(message: types.Message):
    message_input_handler.handle_text_all(message)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: types.CallbackQuery):
    callback_query_handler.handle_callbacks(call)

updater_thread.start()

# Фоновый поток авто-проверки комбо / таймеров / рекламы.
# ВАЖНО: запускаем ДО infinity_polling(), т.к. polling блокирует поток.
# run_daily_checker() при старте сразу делает первую проверку комбо.
combo_checker_thread = threading.Thread(target=daily_auto_checker, daemon=True)
combo_checker_thread.start()
print("🔎 Фоновый чекер комбо запущен.", flush=True)

def thread_watchdog():
    """Сторож: если фоновый чекер (комбо/таймеры/реклама/алерты) умер —
    перезапускает его и уведомляет админа. Делает бота самоисцеляющимся."""
    global combo_checker_thread
    while True:
        time.sleep(300)
        try:
            if not combo_checker_thread.is_alive():
                logger.error("♻️ [WATCHDOG] Фоновый чекер умер — перезапуск.")
                combo_checker_thread = threading.Thread(target=daily_auto_checker, daemon=True)
                combo_checker_thread.start()
                try:
                    bot.send_message(ADMIN_CHAT_ID, "♻️ Watchdog: фоновый чекер был перезапущен автоматически.")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Ошибка watchdog: {e}")

threading.Thread(target=thread_watchdog, daemon=True).start()
print("♻️ Watchdog запущен.", flush=True)

# Фоновая дорассылка сообщений, не ушедших из-за микро-обрывов сети.
threading.Thread(target=drain_retry_queue, daemon=True).start()
print("📨 Очередь повторной отправки запущена.", flush=True)


# ============================================================
# 🌐 MINI APP WEB (Telegram Web App) — interface stylée compacte
# ------------------------------------------------------------
# S'ouvre DANS Telegram via le bouton 🚀 App. Auth automatique par
# signature Telegram initData (aucun mot de passe). Le token du bot
# ne quitte jamais le serveur (images servies par proxy).
# ============================================================

def verify_init_data(init_data: str):
    """Vérifie la signature Telegram WebApp initData avec le token du bot.
    Retourne (ok: bool, user: dict). user contient id, first_name, etc."""
    if not init_data:
        return False, {}
    try:
        pairs = dict(_parse_qsl(init_data, keep_blank_values=True))
        received = pairs.pop("hash", "")
        check = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
        secret = _hmac.new(b"WebAppData", TOKEN.encode(), _hashlib.sha256).digest()
        calc = _hmac.new(secret, check.encode(), _hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(calc, received):
            return False, {}
        user = json.loads(pairs["user"]) if pairs.get("user") else {}
        return True, user
    except Exception as e:
        logger.error(f"initData invalide: {e}")
        return False, {}


# Monnaies affichées dans l'onglet Prix du Mini App.
WEB_COINS = [
    ("btc", "bitcoin", "₿"), ("eth", "ethereum", "Ξ"),
    ("ton", "the-open-network", "💎"), ("usdt", "tether", "💵"),
    ("bnb", "binancecoin", "🅱"), ("sol", "solana", "◎"),
]

def web_prices():
    ids = ",".join(c[1] for c in WEB_COINS)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    try:
        data = cached_json_get(url)
    except Exception:
        data = {}
    out = []
    for sym, cid, icon in WEB_COINS:
        d = data.get(cid, {}) or {}
        out.append({"sym": sym.upper(), "icon": icon, "usd": d.get("usd"),
                    "chg": d.get("usd_24h_change")})
    return out


# Interface du Mini App (HTML+CSS+JS autonome, thème Telegram, compact & pro).
WEBAPP_HTML = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>CRYPTO HUB</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
  :root{
    --bg:var(--tg-theme-bg-color,#0f1115);
    --sec:var(--tg-theme-secondary-bg-color,#171a21);
    --txt:var(--tg-theme-text-color,#f4f5f7);
    --hint:var(--tg-theme-hint-color,#8b93a1);
    --btn:var(--tg-theme-button-color,#3d8bff);
    --btntxt:var(--tg-theme-button-text-color,#fff);
    --line:rgba(255,255,255,.07);
    --accent:#4dd0a7;
  }
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  body{margin:0;background:var(--bg);color:var(--txt);
    font-family:-apple-system,BlinkMacSystemFont,"SF Pro",Roboto,Segoe UI,sans-serif;
    font-size:14px;padding:0 0 76px}
  .wrap{max-width:520px;margin:0 auto;padding:12px}
  header{display:flex;align-items:center;justify-content:space-between;
    padding:6px 2px 12px}
  .logo{font-weight:800;letter-spacing:.4px;font-size:16px}
  .logo span{color:var(--accent)}
  .chip{display:flex;align-items:center;gap:6px;background:var(--sec);
    border:1px solid var(--line);border-radius:20px;padding:5px 10px;font-size:12px}
  .chip b{font-weight:600}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .card{background:var(--sec);border:1px solid var(--line);border-radius:14px;
    padding:12px;position:relative;overflow:hidden}
  .card .k{color:var(--hint);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
  .card .v{font-size:22px;font-weight:800;margin-top:3px}
  .card .e{position:absolute;right:10px;top:10px;font-size:18px;opacity:.5}
  .vip{background:linear-gradient(135deg,#3a2f10,#171a21);border-color:#5a4a15}
  .vip .v{color:#f6c945}
  .btn{display:block;width:100%;border:0;border-radius:12px;padding:13px;
    font-size:14px;font-weight:700;color:var(--btntxt);background:var(--btn);
    margin-top:10px;cursor:pointer;transition:.15s;text-align:center}
  .btn:active{transform:scale(.98)}
  .btn.ghost{background:var(--sec);color:var(--txt);border:1px solid var(--line)}
  .btn.gold{background:linear-gradient(135deg,#f6c945,#e0a90c);color:#221c00}
  .sec-title{font-size:12px;color:var(--hint);text-transform:uppercase;
    letter-spacing:.6px;margin:16px 2px 8px;font-weight:700}
  .row{display:flex;align-items:center;gap:10px;background:var(--sec);
    border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin-bottom:7px}
  .row .n{font-weight:600;flex:1}
  .row .s{color:var(--hint);font-size:12px}
  .up{color:#4dd0a7}.down{color:#ff6b6b}
  .medal{font-size:16px;width:26px;text-align:center}
  .combo{border-radius:14px;overflow:hidden;background:var(--sec);
    border:1px solid var(--line);margin-bottom:10px}
  .combo img{width:100%;display:block}
  .combo .cap{padding:9px 12px;display:flex;justify-content:space-between;align-items:center}
  .combo .cap b{font-size:13px}
  .combo .cap i{color:var(--hint);font-style:normal;font-size:11px}
  .badge{font-size:10px;background:var(--accent);color:#062018;border-radius:6px;
    padding:2px 6px;font-weight:800}
  .tabbar{position:fixed;left:0;right:0;bottom:0;background:var(--bg);
    border-top:1px solid var(--line);display:flex;max-width:520px;margin:0 auto}
  .tabbar button{flex:1;background:0;border:0;color:var(--hint);padding:9px 0 12px;
    font-size:10px;font-weight:600;display:flex;flex-direction:column;align-items:center;gap:3px}
  .tabbar button .i{font-size:20px}
  .tabbar button.on{color:var(--btn)}
  .empty{text-align:center;color:var(--hint);padding:40px 20px;font-size:13px}
  .skel{background:var(--sec);border-radius:12px;height:70px;margin-bottom:8px;
    animation:pulse 1.2s infinite}
  @keyframes pulse{50%{opacity:.5}}
  .warn{background:#3a2410;border:1px solid #6b4410;color:#f6c945;border-radius:10px;
    padding:9px 12px;font-size:12px;margin-bottom:10px}
  .toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);
    background:#000;color:#fff;padding:10px 16px;border-radius:20px;font-size:13px;
    opacity:0;transition:.3s;pointer-events:none;z-index:9}
  .toast.show{opacity:.95}
  .hide{display:none!important}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="logo">CRYPTO <span>HUB</span></div>
    <div class="chip" id="chip"><span>👤</span><b id="uname">…</b></div>
  </header>
  <div id="warn" class="warn hide">⚠️ Mode allégé — données externes en cache.</div>

  <!-- Accueil -->
  <section id="tab-home">
    <div class="grid">
      <div class="card"><span class="e">💰</span><div class="k">Points</div><div class="v" id="pts">—</div></div>
      <div class="card"><span class="e">🔥</span><div class="k">Série</div><div class="v" id="stk">—</div></div>
      <div class="card"><span class="e">👥</span><div class="k">Amis</div><div class="v" id="ref">—</div></div>
      <div class="card vip"><span class="e">👑</span><div class="k">VIP</div><div class="v" id="vip">—</div></div>
    </div>
    <button class="btn" id="checkin">🎁 Récupérer le bonus du jour</button>
    <button class="btn ghost" id="invite">👥 Inviter des amis (+50 pts)</button>
    <button class="btn gold" id="govip">💎 Passer VIP (sans pub)</button>
  </section>

  <!-- Combos -->
  <section id="tab-combos" class="hide">
    <div class="sec-title">🎯 Combos récents</div>
    <div id="combos"><div class="skel"></div><div class="skel"></div></div>
  </section>

  <!-- Prix -->
  <section id="tab-prices" class="hide">
    <div class="sec-title">🧮 Cours crypto (USD)</div>
    <div id="prices"><div class="skel"></div><div class="skel"></div></div>
  </section>

  <!-- Top -->
  <section id="tab-top" class="hide">
    <div class="sec-title">🏆 Top joueurs</div>
    <div id="top"><div class="skel"></div><div class="skel"></div></div>
  </section>
</div>

<nav class="tabbar">
  <button data-tab="home" class="on"><span class="i">🏠</span>Accueil</button>
  <button data-tab="combos"><span class="i">🎯</span>Combos</button>
  <button data-tab="prices"><span class="i">🧮</span>Prix</button>
  <button data-tab="top"><span class="i">🏆</span>Top</button>
</nav>
<div class="toast" id="toast"></div>

<script>
const tg = window.Telegram ? window.Telegram.WebApp : null;
if(tg){ tg.ready(); tg.expand(); }
const INIT = tg ? tg.initData : "";
const H = {"X-Telegram-Init-Data": INIT};
const $ = s => document.querySelector(s);
const loaded = {combos:false, prices:false, top:false};

function toast(t){ const el=$("#toast"); el.textContent=t; el.classList.add("show");
  setTimeout(()=>el.classList.remove("show"),1800); }
async function api(path, opts){ const r = await fetch(path, Object.assign({headers:H}, opts||{}));
  if(!r.ok) throw new Error(r.status); return r.json(); }

async function loadMe(){
  try{
    const d = await api("/api/me");
    $("#uname").textContent = d.name;
    $("#pts").textContent = d.points;
    $("#stk").textContent = d.streak + " j";
    $("#ref").textContent = d.referrals;
    $("#vip").textContent = d.vip ? d.vip_days+" j" : "—";
    if(d.degraded) $("#warn").classList.remove("hide");
    window._invite = d.invite_link;
  }catch(e){
    $("#uname").textContent = "hors Telegram";
    document.querySelector(".wrap").insertAdjacentHTML("beforeend",
      '<div class="empty">🔒 Ouvre cette page depuis le bouton 🚀 App dans Telegram.</div>');
  }
}
async function loadCombos(){
  if(loaded.combos) return; loaded.combos=true;
  try{
    const d = await api("/api/combos"); const box=$("#combos");
    if(!d.combos.length){ box.innerHTML='<div class="empty">📜 Aucun combo pour l\'instant.</div>'; return; }
    box.innerHTML = d.combos.map(c=>`
      <div class="combo">${c.img?`<img loading="lazy" src="${c.img}">`:""}
        <div class="cap"><b>🎯 ${c.name}</b>
          <span>${c.today?'<span class="badge">AUJOURD\'HUI</span> ':''}<i>${c.date||''}</i></span>
        </div></div>`).join("");
  }catch(e){ $("#combos").innerHTML='<div class="empty">Connexion requise.</div>'; }
}
async function loadPrices(){
  if(loaded.prices) return; loaded.prices=true;
  try{
    const d = await api("/api/prices"); const box=$("#prices");
    box.innerHTML = d.prices.map(p=>{
      const chg = p.chg==null?0:p.chg, cls=chg>=0?"up":"down", sign=chg>=0?"+":"";
      const usd = p.usd==null?"—":"$"+Number(p.usd).toLocaleString();
      return `<div class="row"><div style="font-size:18px">${p.icon}</div>
        <div class="n">${p.sym}<div class="s">${sign}${chg.toFixed(2)}% / 24h</div></div>
        <div class="${cls}" style="font-weight:800">${usd}</div></div>`;
    }).join("");
  }catch(e){ $("#prices").innerHTML='<div class="empty">Connexion requise.</div>'; }
}
async function loadTop(){
  if(loaded.top) return; loaded.top=true;
  try{
    const d = await api("/api/top"); const box=$("#top");
    if(!d.top.length){ box.innerHTML='<div class="empty">🏆 Classement vide.</div>'; return; }
    const m=["🥇","🥈","🥉"];
    box.innerHTML = d.top.map(u=>`<div class="row">
      <div class="medal">${u.rank<=3?m[u.rank-1]:u.rank}</div>
      <div class="n">${u.name}${u.vip?' 👑':''}<div class="s">${u.id} · 👥 ${u.refs}</div></div>
      <div style="font-weight:800">${u.points}</div></div>`).join("");
  }catch(e){ $("#top").innerHTML='<div class="empty">Connexion requise.</div>'; }
}

document.querySelectorAll(".tabbar button").forEach(b=>b.onclick=()=>{
  const t=b.dataset.tab;
  document.querySelectorAll(".tabbar button").forEach(x=>x.classList.toggle("on",x===b));
  ["home","combos","prices","top"].forEach(s=>$("#tab-"+s).classList.toggle("hide",s!==t));
  if(t==="combos")loadCombos(); if(t==="prices")loadPrices(); if(t==="top")loadTop();
  if(tg)tg.HapticFeedback && tg.HapticFeedback.selectionChanged();
});
$("#checkin").onclick=async()=>{
  try{ const d=await api("/api/checkin",{method:"POST"});
    if(d.claimed){ toast(`🎁 +${d.reward} pts · série ${d.streak} j`); $("#pts").textContent=d.total; $("#stk").textContent=d.streak+" j"; }
    else toast("✅ Bonus déjà pris aujourd'hui");
  }catch(e){ toast("🔒 Ouvre depuis Telegram"); }
};
$("#invite").onclick=()=>{ const l=window._invite; if(!l)return toast("🔒 Ouvre depuis Telegram");
  const txt="🚀 Rejoins CRYPTO HUB — combos, mining & crypto !";
  if(tg) tg.openTelegramLink("https://t.me/share/url?url="+encodeURIComponent(l)+"&text="+encodeURIComponent(txt));
  else toast(l); };
$("#govip").onclick=()=>{ if(tg){ tg.close(); } toast("💎 Ouvre 💎 VIP dans le bot"); };

loadMe();
</script>
</body>
</html>"""


if _FLASK_OK:
    web_app = Flask(__name__)
    _img_path_cache = {}

    def _webapp_uid():
        init = request.headers.get("X-Telegram-Init-Data", "") or request.args.get("initData", "")
        ok, user = verify_init_data(init)
        if not ok or not user.get("id"):
            return None, {}
        return int(user["id"]), user

    @web_app.route("/")
    def _web_index():
        return Response(WEBAPP_HTML, mimetype="text/html")

    @web_app.route("/api/me")
    def _web_me():
        uid, user = _webapp_uid()
        if not uid:
            return jsonify({"error": "auth"}), 401
        return jsonify({
            "id": mask_id(uid),
            "name": re.sub(r'[<>]', '', (user.get("first_name") or "👤"))[:20],
            "points": get_points(uid), "streak": get_streak(uid),
            "vip": is_vip(uid), "vip_days": vip_days_left(uid),
            "referrals": referral_count(uid),
            "invite_link": f"https://t.me/{get_bot_username()}?start=ref_{uid}",
            "degraded": is_degraded(),
        })

    @web_app.route("/api/checkin", methods=["POST"])
    def _web_checkin():
        uid, _ = _webapp_uid()
        if not uid:
            return jsonify({"error": "auth"}), 401
        claimed, streak, reward, total = daily_checkin(uid)
        return jsonify({"claimed": claimed, "streak": streak, "reward": reward, "total": total})

    @web_app.route("/api/combos")
    def _web_combos():
        uid, _ = _webapp_uid()
        if not uid:
            return jsonify({"error": "auth"}), 401
        today = time.strftime("%Y-%m-%d", time.localtime())
        seen, out = set(), []
        for h in reversed(combo_history):
            key = h.get("key")
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "name": h.get("name", "Combo"),
                "date": h.get("date", h.get("day", "")),
                "img": f"/img/{h['file_id']}" if h.get("file_id") else None,
                "today": h.get("day") == today,
            })
            if len(out) >= 20:
                break
        return jsonify({"combos": out})

    @web_app.route("/api/prices")
    def _web_pr():
        uid, _ = _webapp_uid()
        if not uid:
            return jsonify({"error": "auth"}), 401
        return jsonify({"prices": web_prices()})

    @web_app.route("/api/top")
    def _web_top():
        uid, _ = _webapp_uid()
        if not uid:
            return jsonify({"error": "auth"}), 401
        out = []
        for i, (u, pts) in enumerate(points_leaderboard(10)):
            out.append({"rank": i + 1, "name": display_name(u), "id": mask_id(u),
                        "points": pts, "vip": is_vip(u), "refs": referral_count(u)})
        return jsonify({"top": out})

    @web_app.route("/img/<path:file_id>")
    def _web_img(file_id):
        """Proxy image Telegram : le token reste côté serveur."""
        try:
            fp = _img_path_cache.get(file_id)
            if not fp:
                fp = bot.get_file(file_id).file_path
                _img_path_cache[file_id] = fp
            r = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fp}", timeout=10)
            return Response(r.content, mimetype="image/jpeg")
        except Exception:
            return Response(status=404)


def run_web_server():
    """Sert le Mini App en local (le tunnel / l'URL publique pointe dessus)."""
    if not _FLASK_OK:
        return
    try:
        logger.info(f"🌐 Serveur Mini App en écoute sur http://localhost:{WEBAPP_PORT}")
        web_app.run(host="0.0.0.0", port=WEBAPP_PORT, threaded=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Serveur Mini App arrêté : {e}")


def setup_webapp_button():
    """Installe le bouton menu Telegram (☰ → 🚀 App) qui ouvre le Mini App."""
    if not WEBAPP_URL:
        return
    web_app = types.WebAppInfo(url=WEBAPP_URL)
    try:
        # Selon la version de pyTelegramBotAPI, MenuButtonWebApp exige (ou non)
        # l'argument positionnel `type`. On tente d'abord avec, puis sans.
        try:
            menu_btn = types.MenuButtonWebApp(type="web_app", text="🚀 App", web_app=web_app)
        except TypeError:
            menu_btn = types.MenuButtonWebApp(text="🚀 App", web_app=web_app)
        bot.set_chat_menu_button(menu_button=menu_btn)
        logger.info("✅ Bouton Mini App installé dans le menu Telegram.")
    except Exception as e:
        logger.error(f"Bouton Mini App non installé : {e}")


def _cloudflared_arch_suffix():
    """Renvoie le suffixe d'architecture cloudflared (arm64/arm/amd64/386)
    correspondant au CPU courant, ou None si inconnu."""
    m = (platform.machine() or "").lower()
    if m in ("aarch64", "arm64"):
        return "arm64"
    if m.startswith("arm") or m in ("armv7l", "armv6l"):
        return "arm"
    if m in ("x86_64", "amd64"):
        return "amd64"
    if m in ("i386", "i686", "x86"):
        return "386"
    return None


def ensure_cloudflared():
    """Retourne le chemin d'un exécutable cloudflared utilisable.
    Si absent, tente une installation auto (Termux → pkg, Debian/Kali → .deb,
    sinon binaire officiel téléchargé localement). Renvoie None si impossible."""
    # 1) Déjà présent dans le PATH ?
    found = shutil.which("cloudflared")
    if found:
        return found

    # 1bis) Binaire déjà téléchargé lors d'un run précédent ?
    local_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared")
    if os.path.isfile(local_bin) and os.access(local_bin, os.X_OK):
        return local_bin

    print("📦 cloudflared absent — tentative d'installation auto...", flush=True)

    # 2) Termux → gestionnaire de paquets pkg
    if shutil.which("pkg"):
        try:
            subprocess.run(["pkg", "install", "-y", "cloudflared"], timeout=600)
            found = shutil.which("cloudflared")
            if found:
                print("✅ cloudflared installé via pkg (Termux).", flush=True)
                return found
        except Exception as e:
            logger.warning(f"🌐 Install via pkg échouée : {e}")

    arch = _cloudflared_arch_suffix()
    if not arch:
        logger.warning(f"🌐 Architecture CPU inconnue ({platform.machine()}), "
                       "install auto impossible.")
        return None

    # 3) Debian/Kali → paquet .deb officiel
    if shutil.which("dpkg"):
        try:
            deb_arch = {"arm64": "arm64", "arm": "arm", "amd64": "amd64", "386": "386"}[arch]
            url = ("https://github.com/cloudflare/cloudflared/releases/latest/"
                   f"download/cloudflared-linux-{deb_arch}.deb")
            deb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "cloudflared.deb")
            print(f"📦 Téléchargement {url} ...", flush=True)
            urllib.request.urlretrieve(url, deb_path)
            # dpkg -i nécessite souvent les droits root ; sudo si dispo.
            installer = (["sudo", "dpkg", "-i", deb_path]
                         if shutil.which("sudo") else ["dpkg", "-i", deb_path])
            subprocess.run(installer, timeout=600)
            try:
                os.remove(deb_path)
            except Exception:
                pass
            found = shutil.which("cloudflared")
            if found:
                print("✅ cloudflared installé via .deb.", flush=True)
                return found
        except Exception as e:
            logger.warning(f"🌐 Install via .deb échouée : {e}")

    # 4) Dernier recours : binaire brut téléchargé dans le dossier du bot
    try:
        url = ("https://github.com/cloudflare/cloudflared/releases/latest/"
               f"download/cloudflared-linux-{arch}")
        print(f"📦 Téléchargement du binaire {url} ...", flush=True)
        urllib.request.urlretrieve(url, local_bin)
        st = os.stat(local_bin)
        os.chmod(local_bin, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        if os.access(local_bin, os.X_OK):
            print("✅ cloudflared téléchargé (binaire local).", flush=True)
            return local_bin
    except Exception as e:
        logger.warning(f"🌐 Téléchargement du binaire échoué : {e}")

    return None


def start_cloudflared_tunnel():
    """Lance cloudflared, capture l'URL https://…trycloudflare.com, la place
    automatiquement dans WEBAPP_URL, installe le bouton et prévient l'admin.
    Aucune manip manuelle : l'URL publique est trouvée toute seule.
    Si cloudflared est absent, tente d'abord de l'installer automatiquement."""
    global WEBAPP_URL

    cf_bin = ensure_cloudflared()
    if not cf_bin:
        logger.warning("🌐 cloudflared introuvable et install auto impossible. "
                       "Installe-le une fois (ex. `pkg install cloudflared` / "
                       "binaire officiel) ou renseigne WEBAPP_URL manuellement.")
        try:
            bot.send_message(ADMIN_CHAT_ID,
                             "🌐 Mini App : cloudflared n'est pas installé et "
                             "l'installation automatique a échoué.\n"
                             "Installe-le une fois, ou mets une URL dans WEBAPP_URL.")
        except Exception:
            pass
        return

    try:
        proc = subprocess.Popen(
            [cf_bin, "tunnel", "--url", f"http://localhost:{WEBAPP_PORT}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
    except Exception as e:
        logger.error(f"🌐 Lancement cloudflared impossible : {e}")
        return

    pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    found = False
    try:
        for line in proc.stdout:
            if not found:
                m = pattern.search(line)
                if m:
                    WEBAPP_URL = m.group(0)
                    found = True
                    logger.info(f"🌐 Tunnel actif → {WEBAPP_URL}")
                    setup_webapp_button()
                    try:
                        bot.send_message(
                            ADMIN_CHAT_ID,
                            f"🌐 *Mini App en ligne !*\nURL publique : {WEBAPP_URL}\n"
                            "Le bouton 🚀 App est actif. (URL valable tant que le bot tourne.)",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
            # on continue de vider la sortie pour ne pas bloquer cloudflared
    except Exception as e:
        logger.error(f"🌐 Tunnel cloudflared interrompu : {e}")


# Démarrage du serveur web + URL publique (manuelle ou auto-tunnel).
if _FLASK_OK:
    threading.Thread(target=run_web_server, daemon=True).start()
    if WEBAPP_URL:
        setup_webapp_button()
        print(f"🌐 Mini App web : ACTIF → {WEBAPP_URL}", flush=True)
    elif WEBAPP_AUTOTUNNEL:
        threading.Thread(target=start_cloudflared_tunnel, daemon=True).start()
        print(f"🌐 Mini App web : serveur lancé (port {WEBAPP_PORT}) · tunnel cloudflared auto en cours...", flush=True)
    else:
        print(f"🌐 Mini App web : serveur local lancé (port {WEBAPP_PORT}) mais sans URL publique (WEBAPP_URL vide, auto-tunnel off).", flush=True)
else:
    print("🌐 Mini App web : désactivé (Flask indisponible).", flush=True)

if __name__ == "__main__":
    # ========================================================
    # ОСНОВНАЯ ТОЧКА ЗАПУСКА TELEGRAM-БОТА
    # ========================================================

    print("🤖 Запуск Telegram-бота...", flush=True)

    # Ошибки сети/DNS, которые на телефоне (Termux) случаются постоянно при
    # кратковременной потере связи. На них НЕЛЬЗЯ падать — нужно ждать и
    # переподключаться, а не завершать процесс.
    NETWORK_ERRORS = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
        socket.gaierror,
        ConnectionError,
        OSError,
    )

    retry_delay = 5            # стартовая пауза перед повтором
    max_delay = 300           # максимум 5 минут между попытками
    outage_start = None       # засекаем начало простоя для отчёта о восстановлении

    # ========================================================
    # СУПЕРВАЙЗЕР: бот сам поднимается после обрывов сети/DNS.
    # ========================================================
    while True:
        try:
            print("🌐 Проверка Telegram API...", flush=True)
            me = bot.get_me()
            print(f"✅ Telegram API отвечает. Бот: @{me.username} | ID: {me.id}", flush=True)
            # Восстановились после простоя — уведомляем админа (если он был заметным).
            if outage_start is not None:
                downtime = int(time.time() - outage_start)
                outage_start = None
                if downtime > 120:
                    try:
                        bot.send_message(ADMIN_CHAT_ID, f"✅ Связь восстановлена. Бот был офлайн ~{downtime // 60} мин {downtime % 60} с.")
                    except Exception:
                        pass

            # Удаляем возможный вебхук — иначе getUpdates (polling) молчит.
            bot.remove_webhook()
            print("🧹 Webhook удалён (polling-режим).", flush=True)

            retry_delay = 5   # связь есть — сбрасываем паузу переподключения
            print("🟢 Запускаем infinity_polling()...", flush=True)

            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                allowed_updates=["message", "callback_query"],
                skip_pending=True
            )

            # Штатный выход из polling — короткая пауза и переподключение.
            print("♻️ Polling завершился штатно — переподключение...", flush=True)
            time.sleep(retry_delay)

        except KeyboardInterrupt:
            print("🛑 Бот остановлен пользователем.", flush=True)
            break

        except NETWORK_ERRORS as e:
            # Временная потеря сети/DNS на телефоне — ждём и пробуем снова.
            if outage_start is None:
                outage_start = time.time()
            logger.warning("🌐 Нет сети/DNS (%s: %s). Повтор через %d c...", type(e).__name__, e, retry_delay)
            print(f"🌐 Сеть недоступна ({type(e).__name__}). Повтор через {retry_delay} c...", flush=True)
            time.sleep(retry_delay)
            retry_delay = min(max_delay, retry_delay * 2)

        except Exception as e:
            # Любая иная ошибка — логируем и перезапускаем цикл, НЕ выходя из процесса.
            if outage_start is None:
                outage_start = time.time()
            logger.exception("❌ Ошибка Telegram polling: %s", e)
            print(f"❌ Polling упал: {type(e).__name__}: {e}. Перезапуск через {retry_delay} c...", flush=True)
            time.sleep(retry_delay)
            retry_delay = min(max_delay, retry_delay * 2)
