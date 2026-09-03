#!/usr/bin/env sh
# Auto-update : telecharge bot.py -> botv1.py, config.py, et ce script lui-meme.
# POSIX SH (pas de tableaux bash / [[ ]]) car lance via `sh updatebot.sh` (Termux/dash).
# Sauver en fins de ligne UNIX (LF), pas CRLF.

# Liste "URL:fichier_cible" (items entre guillemets, aucun espace dans un token).
for item in \
    "https://raw.githubusercontent.com/szp2025/telegrambot/refs/heads/main/bot.py:botv1.py" \
    "https://raw.githubusercontent.com/szp2025/telegrambot/refs/heads/main/config.py:config.py" \
    "https://raw.githubusercontent.com/szp2025/telegrambot/refs/heads/main/updatebot.sh:updatebot.sh"
do
    # URL = tout AVANT le dernier ':' (un seul %) ; cible = tout APRES le dernier ':'.
    URL="${item%:*}"
    TARGET_FILE="${item##*:}"
    TEMP_FILE="${TARGET_FILE}_new"

    echo "[UPDATE] Fichier: $TARGET_FILE"
    echo "[UPDATE] Telechargement..."

    # Cree le dossier cible si besoin.
    mkdir -p "$(dirname "$TARGET_FILE")"

    if curl -s -L "$URL" -o "$TEMP_FILE"; then
        case "$TARGET_FILE" in
            (*.py)
                echo "[UPDATE] Verification syntaxe Python..."
                if python3 -m py_compile "$TEMP_FILE"; then
                    echo "[UPDATE] Syntaxe OK."
                    mv "$TEMP_FILE" "$TARGET_FILE"
                    echo "[UPDATE] $TARGET_FILE mis a jour."
                else
                    echo "[UPDATE] ERREUR de syntaxe dans $TEMP_FILE - annule."
                    rm -f "$TEMP_FILE"
                fi
                ;;
            (*)
                # Script shell (.sh) ou autre : on remplace directement.
                mv "$TEMP_FILE" "$TARGET_FILE"
                chmod +x "$TARGET_FILE" 2>/dev/null
                echo "[UPDATE] $TARGET_FILE mis a jour."
                ;;
        esac
    else
        echo "[UPDATE] ERREUR: telechargement echoue depuis $URL"
        rm -f "$TEMP_FILE"
    fi
    echo "----------------------------------------"
done
