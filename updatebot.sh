#!/usr/bin/env bash

IFS=$'\n'
for item in \
    "https://raw.githubusercontent.com/szp2025/telegrambot/refs/heads/main/bot.py|botv1.py" \
    "https://raw.githubusercontent.com/szp2025/telegrambot/refs/heads/main/private_config.py|private_config.py" \
    "https://raw.githubusercontent.com/szp2025/telegrambot/refs/heads/main/updatebot.sh|storage/downloads/updatebot.sh"
do
    # Пропускаем пустые строки
    [ -z "$item" ] && continue

    # Разделяем строку на URL и целевой путь по символу '|'
    URL="${item%%|*}"
    TARGET_FILE="${item##*|}"
    TEMP_FILE="${TARGET_FILE}_new"

    echo "🔄 Обработка файла: $TARGET_FILE"
    echo "📥 Скачивание..."

    # Создаем директорию для файла, если её нет
    mkdir -p "$(dirname "$TARGET_FILE")"

    if curl -s -L "$URL" -o "$TEMP_FILE"; then
        # Если это Python-файл (.py), проверяем синтаксис
        if [[ "$TARGET_FILE" == *.py ]]; then
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
        else
            # Для скриптов оболочки (.sh) или других файлов заменяем сразу
            mv "$TEMP_FILE" "$TARGET_FILE"
            chmod +x "$TARGET_FILE"
            echo "🚀 Файл $TARGET_FILE успешно обновлен!"
        fi
    else
        echo "❌ ОШИБКА: Не удалось скачать файл с адреса $URL"
        rm -f "$TEMP_FILE"
    fi
    echo "----------------------------------------"
done
