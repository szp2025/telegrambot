#!/usr/bin/env sh
# Auto-update : télécharge bot.py -> botv1.py, config.py, et ce script lui-même.
# ÉCRIT EN POSIX SH (pas de tableaux bash / [[ ]]) car lancé via `sh updatebot.sh`
# depuis le bot (Termux/dash). Sauver en fins de ligne UNIX (LF), pas CRLF.

# Liste "URL:fichier_cible", une par ligne (aucun espace dans les tokens).
FILES_TO_UPDATE="
https://raw.githubusercontent.com/szp2025/telegrambot/refs/heads/main/bot.py:botv1.py
https://raw.githubusercontent.com/szp2025/telegrambot/refs/heads/main/config.py:config.py
https://raw.githubusercontent.com/szp2025/telegrambot/refs/heads/main/updatebot.sh:updatebot.sh
"

for item in $FILES_TO_UPDATE; do
    # URL = tout AVANT le dernier ':' (un seul %) ; cible = tout APRÈS le dernier ':'.
    URL="${item%:*}"
    TARGET_FILE="${item##*:}"
    TEMP_FILE="${TARGET_FILE}_new"

    echo "🔄 Обработка файла: $TARGET_FILE"
    echo "📥 Скачивание..."

    # Crée le dossier cible si besoin.
    mkdir -p "$(dirname "$TARGET_FILE")"

    if curl -s -L "$URL" -o "$TEMP_FILE"; then
        case "$TARGET_FILE" in
            *.py)
                echo "🔍 Проверка Python-синтаксиса..."
                if python3 -m py_compile "$TEMP_FILE"; then
                    echo "✅ Синтаксис корректен."
                    mv "$TEMP_FILE" "$TARGET_FILE"
                    echo "🚀 Файл $TARGET_FILE успешно обновлен!"
                else
                    echo "❌ ОШИБКА: Синтаксические ошибки в $TEMP_FILE!"
                    echo "🛑 Обновление для $TARGET_FILE отменено."
                    rm -f "$TEMP_FILE"
                fi
                ;;
            *)
                # Script shell (.sh) ou autre : on remplace directement.
                mv "$TEMP_FILE" "$TARGET_FILE"
                chmod +x "$TARGET_FILE" 2>/dev/null
                echo "🚀 Файл $TARGET_FILE успешно обновлен!"
                ;;
        esac
    else
        echo "❌ ОШИБКА: Не удалось скачать файл с адреса $URL"
        rm -f "$TEMP_FILE"
    fi
    echo "----------------------------------------"
done
