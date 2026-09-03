#!/usr/bin/env sh
# Auto-update : telecharge bot.py -> botv1.py, config.py, et ce script lui-meme.
# POSIX SH (pas de tableaux bash / [[ ]]) car lance via `sh updatebot.sh` (Termux/dash).
# Sauver en fins de ligne UNIX (LF), pas CRLF.

# Met a jour un fichier : $1 = URL source, $2 = fichier cible local.
update_file() {
    URL="$1"
    TARGET_FILE="$2"
    TEMP_FILE="${TARGET_FILE}_new"

    echo "[UPDATE] Fichier: $TARGET_FILE"
    echo "[UPDATE] Telechargement..."

    # Cree le dossier cible si besoin.
    mkdir -p "$(dirname "$TARGET_FILE")"

    if curl -s -L "$URL" -o "$TEMP_FILE"; then
        # Extension du fichier = tout apres le dernier point.
        EXT="${TARGET_FILE##*.}"
        if [ "$EXT" = "py" ]; then
            echo "[UPDATE] Verification syntaxe Python..."
            if python3 -m py_compile "$TEMP_FILE"; then
                echo "[UPDATE] Syntaxe OK."
                mv "$TEMP_FILE" "$TARGET_FILE"
                echo "[UPDATE] $TARGET_FILE mis a jour."
            else
                echo "[UPDATE] ERREUR de syntaxe dans $TEMP_FILE - annule."
                rm -f "$TEMP_FILE"
            fi
        else
            # Script shell (.sh) ou autre : on remplace directement.
            mv "$TEMP_FILE" "$TARGET_FILE"
            chmod +x "$TARGET_FILE" 2>/dev/null
            echo "[UPDATE] $TARGET_FILE mis a jour."
        fi
    else
        echo "[UPDATE] ERREUR: telechargement echoue depuis $URL"
        rm -f "$TEMP_FILE"
    fi
    echo "----------------------------------------"
}

BASE="https://raw.githubusercontent.com/szp2025/telegrambot/refs/heads/main"
update_file "$BASE/bot.py" "botv1.py"
update_file "$BASE/config.py" "config.py"
update_file "$BASE/updatebot.sh" "updatebot.sh"
