"""
botdb.py — Couche base de données SQLite du bot (autonome, thread-safe, robuste).

Pourquoi SQLite ici :
• Intégré à Python (module `sqlite3`) — AUCUN serveur, AUCUNE installation, 1 fichier.
• Mode WAL activé → écritures ATOMIQUES qui survivent aux crashs / redémarrages
  (le bot fait os.execv toutes les 2h + watchdogs : c'est exactement ce qu'il faut).
• Accès concurrent sûr : un verrou global sérialise les écritures, WAL permet aux
  lectures de ne pas bloquer les écritures. Fini les JSON tronqués et les races.

Ce module gère les NOUVEAUX domaines (quêtes, badges, tombola, airdrops) et ne
dépend de rien d'autre : il ne connaît pas botv2. Les POINTS restent gérés par
botv2 (gamify_store) — les fonctions de ce module RENVOIENT la récompense à
créditer, et botv2 l'applique via son add_points(). Couplage minimal, zéro import
circulaire.
"""

import os
import time
import json
import random
import sqlite3
import threading
import logging

logger = logging.getLogger(__name__)

# Fichier base de données, à côté du script (comme les .json actuels).
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "botdata.db")

# Un seul verrou global sérialise TOUTES les écritures : simple et sûr.
_LOCK = threading.RLock()
_CONN = None


# ============================================================
# Connexion + schéma
# ============================================================
def _connect():
    global _CONN
    if _CONN is not None:
        return _CONN
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL = robustesse (commits atomiques, survit aux crashs) + concurrence.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")   # bon compromis durabilité/vitesse
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    _CONN = conn
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS user_quests (
    uid         INTEGER NOT NULL,
    quest_key   TEXT    NOT NULL,
    period_key  TEXT    NOT NULL,   -- 'YYYY-MM-DD' (daily) ou 'YYYY-Www' (weekly)
    progress    INTEGER NOT NULL DEFAULT 0,
    completed   INTEGER NOT NULL DEFAULT 0,
    claimed     INTEGER NOT NULL DEFAULT 0,
    updated_at  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (uid, quest_key, period_key)
);

CREATE TABLE IF NOT EXISTS user_badges (
    uid          INTEGER NOT NULL,
    badge_key    TEXT    NOT NULL,
    unlocked_at  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (uid, badge_key)
);

CREATE TABLE IF NOT EXISTS raffles (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    prize     TEXT    NOT NULL,
    ends_at   INTEGER NOT NULL,
    status    TEXT    NOT NULL DEFAULT 'open',   -- open | drawn | cancelled
    winner    INTEGER,
    created_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS raffle_tickets (
    raffle_id  INTEGER NOT NULL,
    uid        INTEGER NOT NULL,
    tickets    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (raffle_id, uid)
);

CREATE TABLE IF NOT EXISTS airdrops (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    url        TEXT    NOT NULL,
    note       TEXT    NOT NULL DEFAULT '',
    active     INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS airdrop_subs (
    uid INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS airdrop_pushed (
    airdrop_id INTEGER NOT NULL,
    uid        INTEGER NOT NULL,
    PRIMARY KEY (airdrop_id, uid)
);

-- Magasin clé→valeur : persiste les structures existantes du bot (points,
-- profils, timers, etc.) de façon ATOMIQUE, en remplacement des fichiers .json.
CREATE TABLE IF NOT EXISTS kv_store (
    k          TEXT PRIMARY KEY,
    v          TEXT NOT NULL,
    updated_at INTEGER NOT NULL DEFAULT 0
);
"""


def init_db():
    """Crée le fichier + les tables si besoin. Idempotent (à appeler au démarrage)."""
    with _LOCK:
        conn = _connect()
        conn.executescript(SCHEMA)
        conn.commit()
    logger.info(f"🗄️ Base SQLite prête ({DB_PATH})")


def _now() -> int:
    return int(time.time())


def _day_key(ts=None) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(ts or time.time()))


def _week_key(ts=None) -> str:
    # Semaine ISO — reset chaque lundi.
    return time.strftime("%Y-W%W", time.localtime(ts or time.time()))


# ============================================================
# Magasin clé→valeur (persistance atomique des structures du bot)
# ============================================================
def kv_exists(key: str) -> bool:
    with _LOCK:
        conn = _connect()
        row = conn.execute("SELECT 1 FROM kv_store WHERE k=?", (key,)).fetchone()
    return row is not None

def kv_save(key: str, value):
    """Persiste une structure Python (dict/list) en JSON, de façon ATOMIQUE
    (transaction SQLite). Remplace open()+json.dump : plus de fichier tronqué."""
    blob = json.dumps(value, ensure_ascii=False)
    with _LOCK:
        conn = _connect()
        conn.execute(
            "INSERT INTO kv_store (k, v, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(k) DO UPDATE SET v=excluded.v, updated_at=excluded.updated_at",
            (key, blob, _now()),
        )
        conn.commit()

def kv_load(key: str, default=None):
    with _LOCK:
        conn = _connect()
        row = conn.execute("SELECT v FROM kv_store WHERE k=?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["v"])
    except Exception as e:
        logger.error(f"kv_load {key} corrompu: {e}")
        return default


# ============================================================
# 1) QUÊTES / MISSIONS
# ============================================================
# Définitions : key → (scope, titre, cible, récompense en points).
QUESTS = {
    "checkin":     {"scope": "daily",  "title": "🎁 Récupérer le bonus du jour", "target": 1, "reward": 5},
    "open_combo":  {"scope": "daily",  "title": "🎯 Ouvrir un combo",            "target": 1, "reward": 10},
    "converter":   {"scope": "daily",  "title": "🧮 Utiliser le convertisseur",  "target": 1, "reward": 5},
    "set_timer":   {"scope": "daily",  "title": "⏰ Programmer un timer",         "target": 1, "reward": 5},
    "faucet_visit":{"scope": "daily",  "title": "🚰 Ouvrir un crypto-faucet",     "target": 1, "reward": 5},
    "invite_week": {"scope": "weekly", "title": "👥 Inviter 1 ami",               "target": 1, "reward": 50},
    "streak_week": {"scope": "weekly", "title": "🔥 Atteindre 3 jours de série",  "target": 3, "reward": 30},
    "combo_week":  {"scope": "weekly", "title": "🎯 Ouvrir 5 combos",             "target": 5, "reward": 40},
}


def _period_key_for(quest_key: str) -> str:
    scope = QUESTS.get(quest_key, {}).get("scope", "daily")
    return _week_key() if scope == "weekly" else _day_key()


def quest_progress(uid: int, quest_key: str, inc: int = 1):
    """
    Incrémente la progression d'une quête pour l'utilisateur, sur la période
    courante. Renvoie un dict :
      {"completed_now": bool, "reward": int, "title": str, "progress": int, "target": int}
    'completed_now' = True SEULEMENT à l'instant où la quête vient d'être complétée
    (pour créditer les points UNE fois). botv2 applique alors add_points(reward).
    """
    q = QUESTS.get(quest_key)
    if not q:
        return {"completed_now": False, "reward": 0, "title": "", "progress": 0, "target": 0}
    period = _period_key_for(quest_key)
    target = q["target"]
    with _LOCK:
        conn = _connect()
        row = conn.execute(
            "SELECT progress, completed FROM user_quests WHERE uid=? AND quest_key=? AND period_key=?",
            (uid, quest_key, period),
        ).fetchone()
        if row is None:
            progress, completed = 0, 0
        else:
            progress, completed = row["progress"], row["completed"]

        if completed:
            return {"completed_now": False, "reward": 0, "title": q["title"],
                    "progress": progress, "target": target}

        progress = min(target, progress + inc)
        completed_now = progress >= target
        conn.execute(
            "INSERT INTO user_quests (uid, quest_key, period_key, progress, completed, claimed, updated_at) "
            "VALUES (?,?,?,?,?,0,?) "
            "ON CONFLICT(uid, quest_key, period_key) DO UPDATE SET "
            "progress=excluded.progress, completed=excluded.completed, updated_at=excluded.updated_at",
            (uid, quest_key, period, progress, 1 if completed_now else 0, _now()),
        )
        conn.commit()
    return {"completed_now": completed_now, "reward": q["reward"] if completed_now else 0,
            "title": q["title"], "progress": progress, "target": target}


def list_quests(uid: int):
    """État des quêtes de l'utilisateur (daily + weekly) pour l'affichage."""
    dkey, wkey = _day_key(), _week_key()
    with _LOCK:
        conn = _connect()
        rows = conn.execute(
            "SELECT quest_key, period_key, progress, completed FROM user_quests "
            "WHERE uid=? AND (period_key=? OR period_key=?)",
            (uid, dkey, wkey),
        ).fetchall()
    state = {r["quest_key"]: r for r in rows}
    out = []
    for key, q in QUESTS.items():
        r = state.get(key)
        progress = r["progress"] if r else 0
        completed = bool(r["completed"]) if r else False
        out.append({
            "key": key, "scope": q["scope"], "title": q["title"],
            "target": q["target"], "reward": q["reward"],
            "progress": progress, "completed": completed,
        })
    return out


def quests_completed_count(uid: int) -> int:
    """Nombre total de quêtes complétées (toutes périodes) — sert aux badges."""
    with _LOCK:
        conn = _connect()
        row = conn.execute(
            "SELECT COUNT(*) c FROM user_quests WHERE uid=? AND completed=1", (uid,)
        ).fetchone()
    return int(row["c"]) if row else 0


# ============================================================
# 2) BADGES / SUCCÈS
# ============================================================
# key → (emoji, titre, description, fonction condition(stats) -> bool)
# stats = {"points", "streak", "referrals", "quests_done", "vip"}
BADGES = {
    "first_step":  ("🐣", "Premier pas",     "Rejoindre le bot",           lambda s: True),
    "streak_7":    ("🔥", "Assidu",          "7 jours de série",           lambda s: s.get("streak", 0) >= 7),
    "streak_30":   ("🌋", "Inarrêtable",     "30 jours de série",          lambda s: s.get("streak", 0) >= 30),
    "points_500":  ("💰", "Collectionneur",  "500 points",                 lambda s: s.get("points", 0) >= 500),
    "points_5000": ("💎", "Fortune",         "5000 points",                lambda s: s.get("points", 0) >= 5000),
    "ref_5":       ("🤝", "Ambassadeur",     "5 amis invités",             lambda s: s.get("referrals", 0) >= 5),
    "ref_25":      ("👑", "Influenceur",     "25 amis invités",            lambda s: s.get("referrals", 0) >= 25),
    "quests_10":   ("🎯", "Aventurier",      "10 quêtes complétées",       lambda s: s.get("quests_done", 0) >= 10),
    "quests_50":   ("🏆", "Légende",         "50 quêtes complétées",       lambda s: s.get("quests_done", 0) >= 50),
    "vip_badge":   ("⭐", "Membre VIP",       "Devenir VIP",                lambda s: bool(s.get("vip"))),
}


def user_badges(uid: int) -> set:
    with _LOCK:
        conn = _connect()
        rows = conn.execute("SELECT badge_key FROM user_badges WHERE uid=?", (uid,)).fetchall()
    return {r["badge_key"] for r in rows}


def check_badges(uid: int, stats: dict):
    """
    Débloque les badges dont la condition est remplie et pas encore obtenus.
    Renvoie la liste des badges NOUVELLEMENT débloqués : [(emoji, titre), ...].
    À appeler après chaque action notable (check-in, invite, quête, achat VIP).
    """
    have = user_badges(uid)
    newly = []
    with _LOCK:
        conn = _connect()
        for key, (emoji, title, _desc, cond) in BADGES.items():
            if key in have:
                continue
            try:
                ok = bool(cond(stats))
            except Exception:
                ok = False
            if ok:
                conn.execute(
                    "INSERT OR IGNORE INTO user_badges (uid, badge_key, unlocked_at) VALUES (?,?,?)",
                    (uid, key, _now()),
                )
                newly.append((emoji, title))
        if newly:
            conn.commit()
    return newly


def badges_overview(uid: int):
    """Tous les badges avec leur état (obtenu ou non) pour l'affichage profil."""
    have = user_badges(uid)
    return [{"key": k, "emoji": e, "title": t, "desc": d, "unlocked": k in have}
            for k, (e, t, d, _c) in BADGES.items()]


def badges_line(uid: int, max_badges: int = 6) -> str:
    """Ligne compacte d'emojis des badges obtenus (pour profil / top)."""
    have = user_badges(uid)
    icons = [BADGES[k][0] for k in BADGES if k in have]
    return " ".join(icons[:max_badges])


# ============================================================
# 3) TOMBOLA / LOTERIE (les points servent de tickets)
# ============================================================
def get_open_raffle():
    with _LOCK:
        conn = _connect()
        row = conn.execute(
            "SELECT * FROM raffles WHERE status='open' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


def create_raffle(prize: str, duration_hours: float) -> int:
    """Ouvre une tombola. Renvoie son id. (Réservé admin côté botv2.)"""
    with _LOCK:
        conn = _connect()
        cur = conn.execute(
            "INSERT INTO raffles (prize, ends_at, status, created_at) VALUES (?,?, 'open', ?)",
            (prize, _now() + int(duration_hours * 3600), _now()),
        )
        conn.commit()
        return cur.lastrowid


def add_tickets(uid: int, count: int) -> dict:
    """
    Ajoute des tickets à l'utilisateur pour la tombola ouverte.
    NB : botv2 vérifie/déduit les POINTS avant d'appeler ceci (source de vérité).
    Renvoie {"ok": bool, "tickets": total_user, "reason": str, "raffle_id": int}.
    """
    if count <= 0:
        return {"ok": False, "tickets": 0, "reason": "Nombre de tickets invalide", "raffle_id": 0}
    r = get_open_raffle()
    if not r:
        return {"ok": False, "tickets": 0, "reason": "Aucune tombola en cours", "raffle_id": 0}
    with _LOCK:
        conn = _connect()
        conn.execute(
            "INSERT INTO raffle_tickets (raffle_id, uid, tickets) VALUES (?,?,?) "
            "ON CONFLICT(raffle_id, uid) DO UPDATE SET tickets = tickets + excluded.tickets",
            (r["id"], uid, count),
        )
        conn.commit()
        row = conn.execute(
            "SELECT tickets FROM raffle_tickets WHERE raffle_id=? AND uid=?", (r["id"], uid)
        ).fetchone()
    return {"ok": True, "tickets": row["tickets"], "reason": "", "raffle_id": r["id"]}


def raffle_stats(raffle_id: int = None) -> dict:
    r = get_open_raffle() if raffle_id is None else None
    if raffle_id is None:
        if not r:
            return {"raffle": None, "participants": 0, "total_tickets": 0}
        raffle_id = r["id"]
    with _LOCK:
        conn = _connect()
        if r is None:
            r = conn.execute("SELECT * FROM raffles WHERE id=?", (raffle_id,)).fetchone()
            r = dict(r) if r else None
        agg = conn.execute(
            "SELECT COUNT(*) p, COALESCE(SUM(tickets),0) t FROM raffle_tickets WHERE raffle_id=?",
            (raffle_id,),
        ).fetchone()
    return {"raffle": r, "participants": int(agg["p"]), "total_tickets": int(agg["t"])}


def user_tickets(uid: int, raffle_id: int = None) -> int:
    if raffle_id is None:
        r = get_open_raffle()
        if not r:
            return 0
        raffle_id = r["id"]
    with _LOCK:
        conn = _connect()
        row = conn.execute(
            "SELECT tickets FROM raffle_tickets WHERE raffle_id=? AND uid=?", (raffle_id, uid)
        ).fetchone()
    return int(row["tickets"]) if row else 0


def draw_raffle(raffle_id: int = None) -> dict:
    """
    Tire au sort un gagnant (probabilité pondérée par le nombre de tickets),
    clôture la tombola. Renvoie {"ok", "winner", "prize", "reason"}.
    """
    r = get_open_raffle() if raffle_id is None else None
    if raffle_id is None:
        if not r:
            return {"ok": False, "winner": None, "prize": "", "reason": "Aucune tombola en cours"}
        raffle_id = r["id"]
    with _LOCK:
        conn = _connect()
        if r is None:
            r = conn.execute("SELECT * FROM raffles WHERE id=?", (raffle_id,)).fetchone()
            r = dict(r) if r else None
        if not r:
            return {"ok": False, "winner": None, "prize": "", "reason": "Tombola introuvable"}
        rows = conn.execute(
            "SELECT uid, tickets FROM raffle_tickets WHERE raffle_id=? AND tickets > 0", (raffle_id,)
        ).fetchall()
        if not rows:
            conn.execute("UPDATE raffles SET status='cancelled' WHERE id=?", (raffle_id,))
            conn.commit()
            return {"ok": False, "winner": None, "prize": r["prize"], "reason": "Aucun participant"}
        pool = []
        for row in rows:
            pool.extend([row["uid"]] * int(row["tickets"]))
        winner = random.choice(pool)
        conn.execute("UPDATE raffles SET status='drawn', winner=? WHERE id=?", (winner, raffle_id))
        conn.commit()
    return {"ok": True, "winner": winner, "prize": r["prize"], "reason": ""}


def raffle_participants(raffle_id: int):
    """Liste des (uid, tickets) — sert à notifier tout le monde après tirage."""
    with _LOCK:
        conn = _connect()
        rows = conn.execute(
            "SELECT uid, tickets FROM raffle_tickets WHERE raffle_id=?", (raffle_id,)
        ).fetchall()
    return [(r["uid"], r["tickets"]) for r in rows]


# ============================================================
# 4) AGRÉGATEUR D'AIRDROPS
# ============================================================
def add_airdrop(title: str, url: str, note: str = "") -> int:
    with _LOCK:
        conn = _connect()
        cur = conn.execute(
            "INSERT INTO airdrops (title, url, note, active, created_at) VALUES (?,?,?,1,?)",
            (title.strip(), url.strip(), note.strip(), _now()),
        )
        conn.commit()
        return cur.lastrowid


def list_airdrops(active_only: bool = True, limit: int = 20):
    with _LOCK:
        conn = _connect()
        q = "SELECT * FROM airdrops"
        if active_only:
            q += " WHERE active=1"
        q += " ORDER BY id DESC LIMIT ?"
        rows = conn.execute(q, (limit,)).fetchall()
    return [dict(r) for r in rows]


def deactivate_airdrop(airdrop_id: int):
    with _LOCK:
        conn = _connect()
        conn.execute("UPDATE airdrops SET active=0 WHERE id=?", (airdrop_id,))
        conn.commit()


def toggle_airdrop_sub(uid: int) -> bool:
    """Abonne/désabonne aux notifications d'airdrops. True = désormais abonné."""
    with _LOCK:
        conn = _connect()
        row = conn.execute("SELECT uid FROM airdrop_subs WHERE uid=?", (uid,)).fetchone()
        if row:
            conn.execute("DELETE FROM airdrop_subs WHERE uid=?", (uid,))
            conn.commit()
            return False
        conn.execute("INSERT OR IGNORE INTO airdrop_subs (uid) VALUES (?)", (uid,))
        conn.commit()
        return True


def is_airdrop_subscribed(uid: int) -> bool:
    with _LOCK:
        conn = _connect()
        row = conn.execute("SELECT uid FROM airdrop_subs WHERE uid=?", (uid,)).fetchone()
    return row is not None


def airdrop_subscribers() -> list:
    with _LOCK:
        conn = _connect()
        rows = conn.execute("SELECT uid FROM airdrop_subs").fetchall()
    return [r["uid"] for r in rows]


def pending_airdrop_pushes():
    """
    Renvoie [(airdrop, [uid, ...])] pour chaque airdrop actif non encore poussé à
    des abonnés. botv2 envoie les messages puis appelle mark_airdrop_pushed().
    """
    subs = airdrop_subscribers()
    if not subs:
        return []
    out = []
    with _LOCK:
        conn = _connect()
        drops = conn.execute("SELECT * FROM airdrops WHERE active=1 ORDER BY id").fetchall()
        for d in drops:
            pushed = {r["uid"] for r in conn.execute(
                "SELECT uid FROM airdrop_pushed WHERE airdrop_id=?", (d["id"],)
            ).fetchall()}
            targets = [u for u in subs if u not in pushed]
            if targets:
                out.append((dict(d), targets))
    return out


def mark_airdrop_pushed(airdrop_id: int, uid: int):
    with _LOCK:
        conn = _connect()
        conn.execute(
            "INSERT OR IGNORE INTO airdrop_pushed (airdrop_id, uid) VALUES (?,?)",
            (airdrop_id, uid),
        )
        conn.commit()


# ============================================================
# Sauvegarde : snapshot cohérent de la base (sûr même en WAL)
# ============================================================
def backup_db(dest_path: str | None = None) -> str:
    """
    Crée une COPIE COHÉRENTE de la base via `VACUUM INTO` (SQLite ≥ 3.27).
    Contrairement à une simple copie de fichier, ceci intègre proprement le
    contenu du journal WAL → snapshot exploitable, jamais corrompu.
    Renvoie le chemin du fichier créé, ou lève une exception en cas d'échec.
    """
    dest = dest_path or (DB_PATH + ".bak")
    with _LOCK:
        conn = _connect()
        # VACUUM INTO exige que le fichier de destination n'existe pas encore.
        try:
            if os.path.exists(dest):
                os.remove(dest)
        except Exception:
            pass
        conn.execute("VACUUM INTO ?", (dest,))
    return dest


# ============================================================
# Utilitaire : import ponctuel depuis d'anciens fichiers JSON
# ============================================================
def import_json_list(path: str):
    """Charge une liste JSON si le fichier existe (aide à la migration douce)."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Import JSON {path} échoué: {e}")
        return []
