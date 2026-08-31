# ══════════════════════════════════════════════════════════════════════════
# private_config.py — SECRETS DU BOT
# ══════════════════════════════════════════════════════════════════════════
# ⚠️ NE JAMAIS pousser ce fichier sur GitHub (il contient le token du bot).
# ⚠️ Remplace CHAQUE "REMPLACE_..." par ta vraie valeur avant de l'utiliser.
# ⚠️ Si tu copies ce fichier sur le téléphone : reporte tes VRAIES adresses
#    BTC / TON déjà en place, sinon les paiements BTC/TON cesseront de marcher.
# ══════════════════════════════════════════════════════════════════════════

# ID du chat administrateur (toi).
ADMIN_CHAT_ID = ''

# Token du bot Telegram (@BotFather).
TOKEN = ''

# ── Mini App web (botv2.py) ───────────────────────────────────────────────
# URL HTTPS PUBLIQUE du Mini App. DEUX possibilités :
#
#  A) AUTOMATIQUE (recommandé) : laisse WEBAPP_URL = '' et WEBAPP_AUTOTUNNEL = True.
#     botv2 lance cloudflared tout seul, récupère l'URL https://…trycloudflare.com,
#     l'installe et t'envoie l'URL par message admin. Rien à copier à la main.
#     Prérequis (une seule fois sur le tel) : cloudflared installé + `pip install flask`
#     (Flask s'installe aussi automatiquement si absent).
#
#  B) MANUEL / URL fixe : mets ton URL ici, ex. WEBAPP_URL = 'https://app.mondomaine.com'
#     (un tunnel nommé cloudflared ou un hébergement). L'auto-tunnel est alors ignoré.
#
# ⚠️ Une IP locale (127.0.0.1 / 192.168.x.x) NE marche PAS : Telegram exige du HTTPS public.
WEBAPP_URL = ''
WEBAPP_AUTOTUNNEL = True   # False = ne pas lancer cloudflared automatiquement

# ── Adresses de réception des paiements (pub + VIP) ───────────────────────
# Chaque clé correspond à un "wallet_key" dans config.py → PAYMENT_METHODS.
#   • speedwallet_btc  → réseau Bitcoin  (adresse BTC : bc1... ou 1... ou 3...)
#   • ton              → réseau TON      (adresse TON : UQ... / EQ...)
#   • safepal_usdttrc  → réseau Tron     (adresse USDT-TRC20 : commence par T...)
SAFEPAL_WALLETS = {
    "speedwallet_btc": {
        "name": "SpeedWallet BTC",
        "address": "",       # ⬅️ ton adresse BTC actuelle
    },
    "ton": {
        "name": "TON",
        "address": "",       # ⬅️ ton adresse TON actuelle
    },
    "safepal_usdttrc": {
        "name": "SafePal USDT-TRC20",
        "address": "",    # ⬅️ NOUVELLE : adresse Tron (T...) pour USDT-TRC20
    },
}
