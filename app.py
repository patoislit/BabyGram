"""
Baby Social App – app.py
========================
Flask + Flask-SocketIO backend.
Databáza: SQLite (database.db – vytvorí sa automaticky pri prvom spustení).

Zdroj obrázkov: loremflickr.com
  Každý príspevok má ŠPECIFICKÝ keyword (smile, laugh, eating…)
  + unikátne lock číslo → vždy iné cute bábätko, nikdy sa neopakuje.
"""

import os
import random
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO, emit, join_room

# ── Inicializácia aplikácie ──────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "baby-social-secret-2024"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

# ── Popisky pre príspevky (spárované s témami fotiek) ───────────────────────
# Každý popisok sa spáruje s rovnakým indexom v BABY_POSTS
CAPTIONS = [
    # smiech / úsmev
    "Ten úsmev... 🥹 Môj celý svet!",
    "Keď sa zasmieje, zastaví sa čas ✨",
    "Tá tvárička pri smiechu 😂💛",
    "Každý deň s týmto úsmevom je dar 🌸",
    "Ako sa len môže niečo tak malé tak krásne smiať? 😍",
    "Zasmej sa ešte raz, prosím 🫶",
    "Toto liečilo môj celý deň 💖",
    "Prvý smiech = prvá láska 👶",
    # jedenie / papanie
    "Papám, papám, papám! 🍌😋",
    "Keď objaví banán впервые 🍌🤯",
    "Ten výraz pri prvom pyré 😆",
    "Kuchár roka 2024 👨‍🍳 (vek: 8 mesiacov)",
    "Celá tvár v jogurte = šťastný bábätko 🥣",
    "Prvé spaghetti 🍝 Recenzia: 10/10",
    "Papám všetko, čo mi dajú 😤🍎",
    "Keď pizza > spánok 🍕😴",
    # kúpanie
    "Čas na kúpeľ! 🛁 Najkrajší čas dňa",
    "Pena všade, úsmev tiež 🫧💛",
    "Kráľ kúpeľne 👑🛁",
    "Voda = môj najlepší kamarát 💧",
    # hranie
    "Hráme sa s medvedíkom 🧸",
    "Prvé lego 🧱 (zjedol som jeden kúsok)",
    "Balóny sú čistá magia 🎈",
    "Hopsasa! 🪀 Nekonečná energia",
    "Bubon? Bubon! 🥁 Talent odhalený",
    "Keď nájdeš maminkin telefón 📱😈",
    # spánok
    "Spiaci anjel 😴 Ticho v dome",
    "Tak malý, tak dokonalý 🫧",
    "Ranné chlpky a ranné srdiečko 🌅",
    "Keď zaspí pri kŕmení 🍼😴",
    # všeobecné cute
    "Malý zázrak ✨", "Drobček 🌸",
    "Príliš cute na slová 😍", "Kúsok neba 🕊️",
    "Aké zlaté! 🥹", "Srdiečko ukradnuté 💖",
    "Výbuch roztomilosti 💥", "Bábätko dňa 🏆",
    "Nedá sa odolať 🌷", "Zlatíčko moje 👑",
    "Ráno s tebou je raj ☁️", "Môj anjel 👼",
    "Tá úsmevnosť ☀️", "Keď svet zastane 💫",
    "Šťastie v malej verzii 🍼", "Malý anjelik 🤍",
]

REEL_CAPTIONS = [
    "Toto ma vyliečilo 🥹💗", "Nenormálna roztomilosť 🌸",
    "Keď sa smeje anjelik ✨", "Prvé kroky 👼",
    "Bábätko objavuje svet 🌍", "Ranná rutina drobčeka ☀️",
    "Tato a jeho zlatíčko 🫶", "Mama a jej anjel 💛",
    "Keď zaznie smiech bábätka 🎶", "Nová láska 💕",
    "Takto vyzerá dokonalosť 🌷", "Keď spí, vyzerá ako anjel 😴",
]

# ── Kurátorovaný zoznam cute baby foto konfigurácií ─────────────────────────
# Formát: (loremflickr_keywords, lock_číslo)
# lock = unikátne číslo → iná fotka, keywords = určuje OBSAH fotky
# Každá kombinácia je starostlivo vybraná pre max. roztomilosť 🥹

def baby_url(w, h, keywords, lock):
    """Vygeneruje loremflickr URL pre cute bábätko."""
    return f"https://loremflickr.com/{w}/{h}/{keywords}?lock={lock}"


# 120 kurátorovaných príspevkov – rôzne situácie, žiadne opakovanie
FEED_PHOTOS = [
    # ── Smiech / giggle ─────────────────────────────────────────────
    baby_url(600,750,"baby,smile,happy",1),
    baby_url(600,750,"baby,laughing,cute",2),
    baby_url(600,750,"baby,giggle,joy",3),
    baby_url(600,750,"baby,smile,chubby",4),
    baby_url(600,750,"cute,baby,laugh",5),
    baby_url(600,750,"infant,smile,happy",6),
    baby_url(600,750,"toddler,laugh,cute",7),
    baby_url(600,750,"baby,grin,adorable",8),
    baby_url(600,750,"newborn,smile,cute",9),
    baby_url(600,750,"baby,joy,laugh",10),
    baby_url(600,750,"baby,happy,face",11),
    baby_url(600,750,"cute,infant,giggle",12),
    # ── Jedenie / papanie ───────────────────────────────────────────
    baby_url(600,750,"baby,eating,food",13),
    baby_url(600,750,"baby,banana,eating",14),
    baby_url(600,750,"baby,messy,food",15),
    baby_url(600,750,"toddler,eating,cute",16),
    baby_url(600,750,"baby,feeding,spoon",17),
    baby_url(600,750,"infant,food,messy",18),
    baby_url(600,750,"baby,puree,eating",19),
    baby_url(600,750,"baby,snack,cute",20),
    baby_url(600,750,"toddler,fruit,eating",21),
    baby_url(600,750,"baby,yogurt,face",22),
    baby_url(600,750,"cute,baby,mealtime",23),
    baby_url(600,750,"baby,hungry,eating",24),
    # ── Kúpanie ─────────────────────────────────────────────────────
    baby_url(600,750,"baby,bath,cute",25),
    baby_url(600,750,"infant,bathing,smile",26),
    baby_url(600,750,"baby,bubbles,bath",27),
    baby_url(600,750,"toddler,bath,happy",28),
    baby_url(600,750,"baby,water,cute",29),
    baby_url(600,750,"newborn,bath,smile",30),
    # ── Hranie ──────────────────────────────────────────────────────
    baby_url(600,750,"baby,playing,toys",31),
    baby_url(600,750,"toddler,playing,cute",32),
    baby_url(600,750,"baby,teddy,bear",33),
    baby_url(600,750,"infant,play,happy",34),
    baby_url(600,750,"baby,blocks,playing",35),
    baby_url(600,750,"toddler,toy,smile",36),
    baby_url(600,750,"baby,crawling,cute",37),
    baby_url(600,750,"baby,rolling,laugh",38),
    baby_url(600,750,"baby,peek,boo",39),
    baby_url(600,750,"cute,baby,play",40),
    # ── Spánok ──────────────────────────────────────────────────────
    baby_url(600,750,"baby,sleeping,cute",41),
    baby_url(600,750,"newborn,sleep,peaceful",42),
    baby_url(600,750,"baby,nap,adorable",43),
    baby_url(600,750,"infant,sleeping,angelic",44),
    baby_url(600,750,"baby,cozy,sleeping",45),
    baby_url(600,750,"toddler,napping,cute",46),
    # ── Mama / rodina ───────────────────────────────────────────────
    baby_url(600,750,"mother,baby,love",47),
    baby_url(600,750,"baby,mom,hug",48),
    baby_url(600,750,"family,baby,happy",49),
    baby_url(600,750,"father,baby,smile",50),
    baby_url(600,750,"parent,infant,cute",51),
    baby_url(600,750,"baby,cuddle,mom",52),
    # ── Príroda / vonku ─────────────────────────────────────────────
    baby_url(600,750,"baby,nature,cute",53),
    baby_url(600,750,"infant,garden,smile",54),
    baby_url(600,750,"baby,flowers,happy",55),
    baby_url(600,750,"toddler,outdoor,cute",56),
    baby_url(600,750,"baby,grass,playing",57),
    baby_url(600,750,"infant,park,cute",58),
    # ── Oblečenie / outfit ──────────────────────────────────────────
    baby_url(600,750,"cute,baby,outfit",59),
    baby_url(600,750,"baby,hat,adorable",60),
    baby_url(600,750,"infant,costume,cute",61),
    baby_url(600,750,"baby,bow,cute",62),
    baby_url(600,750,"toddler,dress,cute",63),
    baby_url(600,750,"newborn,onesie,cute",64),
    # ── Výrazy tváre ────────────────────────────────────────────────
    baby_url(600,750,"baby,surprised,face",65),
    baby_url(600,750,"baby,grumpy,cute",66),
    baby_url(600,750,"baby,curious,face",67),
    baby_url(600,750,"infant,expression,funny",68),
    baby_url(600,750,"baby,chubby,cheeks",69),
    baby_url(600,750,"newborn,face,cute",70),
    baby_url(600,750,"baby,eyes,adorable",71),
    baby_url(600,750,"toddler,face,funny",72),
    # ── Mix cute ────────────────────────────────────────────────────
    baby_url(600,750,"adorable,baby,cute",73),
    baby_url(600,750,"precious,infant,smile",74),
    baby_url(600,750,"sweet,baby,happy",75),
    baby_url(600,750,"little,baby,cute",76),
    baby_url(600,750,"tiny,infant,adorable",77),
    baby_url(600,750,"baby,chubby,laugh",78),
    baby_url(600,750,"cute,newborn,smile",79),
    baby_url(600,750,"baby,dimples,smile",80),
    baby_url(600,750,"infant,cute,happy",81),
    baby_url(600,750,"baby,round,face",82),
    baby_url(600,750,"toddler,adorable,smile",83),
    baby_url(600,750,"baby,innocent,face",84),
    baby_url(600,750,"newborn,adorable,tiny",85),
    baby_url(600,750,"baby,chunky,cute",86),
    baby_url(600,750,"infant,joy,happy",87),
    baby_url(600,750,"baby,beautiful,smile",88),
    baby_url(600,750,"cute,baby,portrait",89),
    baby_url(600,750,"happy,baby,laugh",90),
    baby_url(600,750,"sweet,infant,face",91),
    baby_url(600,750,"baby,precious,cute",92),
    baby_url(600,750,"toddler,happy,cute",93),
    baby_url(600,750,"baby,joyful,smile",94),
    baby_url(600,750,"newborn,peaceful,cute",95),
    baby_url(600,750,"baby,rosy,cheeks",96),
    baby_url(600,750,"infant,tiny,fingers",97),
    baby_url(600,750,"baby,soft,cute",98),
    baby_url(600,750,"toddler,giggly,cute",99),
    baby_url(600,750,"baby,sweet,face",100),
    baby_url(600,750,"cute,infant,portrait",101),
    baby_url(600,750,"baby,lovable,cute",102),
    baby_url(600,750,"newborn,cute,baby",103),
    baby_url(600,750,"baby,cheeky,smile",104),
    baby_url(600,750,"adorable,newborn,happy",105),
    baby_url(600,750,"cute,toddler,face",106),
    baby_url(600,750,"baby,pudgy,cute",107),
    baby_url(600,750,"happy,infant,cute",108),
    baby_url(600,750,"baby,angel,face",109),
    baby_url(600,750,"newborn,sleeping,tiny",110),
    baby_url(600,750,"baby,playful,cute",111),
    baby_url(600,750,"toddler,curious,cute",112),
    baby_url(600,750,"baby,bubbly,happy",113),
    baby_url(600,750,"sweet,baby,sleeping",114),
    baby_url(600,750,"infant,lovely,cute",115),
    baby_url(600,750,"baby,cozy,happy",116),
    baby_url(600,750,"cute,baby,wonder",117),
    baby_url(600,750,"baby,adorable,chubby",118),
    baby_url(600,750,"newborn,angel,sweet",119),
    baby_url(600,750,"baby,pure,joy",120),
]

# 60 reels – vertikálny formát, rovnaký princíp
REEL_PHOTOS = [
    baby_url(450,800,"baby,smile,happy",201),
    baby_url(450,800,"baby,laugh,cute",202),
    baby_url(450,800,"baby,eating,food",203),
    baby_url(450,800,"infant,giggle,joy",204),
    baby_url(450,800,"baby,bath,bubbles",205),
    baby_url(450,800,"toddler,playing,cute",206),
    baby_url(450,800,"baby,sleeping,angel",207),
    baby_url(450,800,"cute,baby,portrait",208),
    baby_url(450,800,"baby,chubby,smile",209),
    baby_url(450,800,"newborn,cute,tiny",210),
    baby_url(450,800,"baby,surprised,face",211),
    baby_url(450,800,"toddler,laugh,happy",212),
    baby_url(450,800,"baby,curious,eyes",213),
    baby_url(450,800,"infant,smile,adorable",214),
    baby_url(450,800,"baby,teddy,bear",215),
    baby_url(450,800,"cute,newborn,face",216),
    baby_url(450,800,"baby,joy,laugh",217),
    baby_url(450,800,"toddler,cute,happy",218),
    baby_url(450,800,"baby,feeding,cute",219),
    baby_url(450,800,"infant,peaceful,sleep",220),
    baby_url(450,800,"baby,mom,hug",221),
    baby_url(450,800,"cute,baby,outdoor",222),
    baby_url(450,800,"baby,flowers,smile",223),
    baby_url(450,800,"toddler,adorable,cute",224),
    baby_url(450,800,"newborn,tiny,cute",225),
    baby_url(450,800,"baby,dimples,laugh",226),
    baby_url(450,800,"infant,happy,cute",227),
    baby_url(450,800,"baby,rosy,cheeks",228),
    baby_url(450,800,"cute,toddler,smile",229),
    baby_url(450,800,"baby,wonder,cute",230),
    baby_url(450,800,"newborn,angel,cute",231),
    baby_url(450,800,"baby,bubbly,face",232),
    baby_url(450,800,"toddler,giggle,cute",233),
    baby_url(450,800,"baby,sweet,smile",234),
    baby_url(450,800,"infant,adorable,tiny",235),
    baby_url(450,800,"baby,playful,happy",236),
    baby_url(450,800,"cute,baby,chubby",237),
    baby_url(450,800,"baby,grin,face",238),
    baby_url(450,800,"toddler,joy,cute",239),
    baby_url(450,800,"baby,lovable,sweet",240),
    baby_url(450,800,"newborn,sleep,cute",241),
    baby_url(450,800,"baby,bright,eyes",242),
    baby_url(450,800,"infant,laugh,cute",243),
    baby_url(450,800,"baby,cozy,soft",244),
    baby_url(450,800,"toddler,cute,funny",245),
    baby_url(450,800,"baby,happy,face",246),
    baby_url(450,800,"cute,infant,joy",247),
    baby_url(450,800,"baby,precious,tiny",248),
    baby_url(450,800,"newborn,sweet,face",249),
    baby_url(450,800,"baby,cuddle,cute",250),
    baby_url(450,800,"toddler,smile,happy",251),
    baby_url(450,800,"baby,cheeky,face",252),
    baby_url(450,800,"infant,cute,portrait",253),
    baby_url(450,800,"baby,pure,happiness",254),
    baby_url(450,800,"cute,baby,laugh",255),
    baby_url(450,800,"baby,angelic,face",256),
    baby_url(450,800,"toddler,adorable,happy",257),
    baby_url(450,800,"baby,innocent,cute",258),
    baby_url(450,800,"newborn,precious,cute",259),
    baby_url(450,800,"baby,giggly,sweet",260),
]

# Avatary – malé roztomilé baby tváričky
AVATAR_PHOTOS = [baby_url(80,80,"baby,face,cute", 300+i) for i in range(100)]


# ── Databázové pomocné funkcie ────────────────────────────────────────────────
def get_db():
    """Otvorí SQLite spojenie s row_factory pre dict-style prístup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Vytvorí tabuľky a naplní ich kurátorovanými cute baby príspevkami.
    image_seed = index do zoznamu FEED_PHOTOS / REEL_PHOTOS.
    Každý index = iná situácia (smiech, jedenie, kúpanie, hranie…).
    """
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                avatar_seed INTEGER NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS posts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                image_seed  INTEGER NOT NULL,
                caption     TEXT NOT NULL,
                author_id   INTEGER REFERENCES users(id),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS likes (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                post_id INTEGER NOT NULL REFERENCES posts(id),
                UNIQUE(user_id, post_id)
            );

            CREATE TABLE IF NOT EXISTS comments (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                post_id    INTEGER NOT NULL REFERENCES posts(id),
                text       TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id   INTEGER NOT NULL REFERENCES users(id),
                receiver_id INTEGER NOT NULL REFERENCES users(id),
                text        TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reels (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                image_seed  INTEGER NOT NULL,
                caption     TEXT NOT NULL,
                author_id   INTEGER REFERENCES users(id),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

        # ── Feed príspevky: každý index = iná cute situácia ──────────────
        if conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0:
            for i in range(len(FEED_PHOTOS)):
                conn.execute(
                    "INSERT INTO posts (image_seed, caption) VALUES (?, ?)",
                    (i, CAPTIONS[i % len(CAPTIONS)]),
                )

        # ── Reels: vertikálny formát, iné cute situácie ───────────────────
        if conn.execute("SELECT COUNT(*) FROM reels").fetchone()[0] == 0:
            for i in range(len(REEL_PHOTOS)):
                conn.execute(
                    "INSERT INTO reels (image_seed, caption) VALUES (?, ?)",
                    (i, REEL_CAPTIONS[i % len(REEL_CAPTIONS)]),
                )

        conn.commit()


# ── Auth dekorátor ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Stránkové routes ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("feed") if "user_id" in session else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("feed"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if len(username) < 2:
            error = "Meno musí mať aspoň 2 znaky 🌸"
        else:
            with get_db() as conn:
                user = conn.execute(
                    "SELECT * FROM users WHERE username = ?", (username,)
                ).fetchone()
                if not user:
                    seed = random.randint(10000, 99999)
                    cur = conn.execute(
                        "INSERT INTO users (username, avatar_seed) VALUES (?, ?)",
                        (username, seed),
                    )
                    conn.commit()
                    user_id = cur.lastrowid
                else:
                    user_id = user["id"]
            session["user_id"] = user_id
            session["username"] = username
            return redirect(url_for("feed"))
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/feed")
@login_required
def feed():
    return render_template("feed.html")


@app.route("/reels")
@login_required
def reels():
    return render_template("reels.html")


@app.route("/chat")
@app.route("/chat/<int:target_id>")
@login_required
def chat(target_id=None):
    with get_db() as conn:
        users = conn.execute(
            "SELECT id, username, avatar_seed FROM users WHERE id != ? ORDER BY username",
            (session["user_id"],),
        ).fetchall()
        target_user = None
        messages = []
        if target_id:
            target_user = conn.execute(
                "SELECT id, username, avatar_seed FROM users WHERE id = ?", (target_id,)
            ).fetchone()
            if target_user:
                messages = conn.execute(
                    """SELECT m.*, u.username AS sender_name, u.avatar_seed AS sender_avatar
                       FROM messages m JOIN users u ON m.sender_id = u.id
                       WHERE (m.sender_id=? AND m.receiver_id=?)
                          OR (m.sender_id=? AND m.receiver_id=?)
                       ORDER BY m.created_at ASC""",
                    (session["user_id"], target_id, target_id, session["user_id"]),
                ).fetchall()
    return render_template(
        "chat.html",
        users=[dict(u) for u in users],
        target_user=dict(target_user) if target_user else None,
        messages=[dict(m) for m in messages],
    )


@app.route("/profile")
@login_required
def profile():
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        liked = conn.execute(
            """SELECT p.id, p.image_seed, p.caption
               FROM posts p JOIN likes l ON p.id=l.post_id
               WHERE l.user_id=? ORDER BY l.id DESC LIMIT 18""",
            (session["user_id"],),
        ).fetchall()
        my_comments = conn.execute(
            """SELECT c.text, c.created_at, p.image_seed, p.id AS post_id
               FROM comments c JOIN posts p ON c.post_id=p.id
               WHERE c.user_id=? ORDER BY c.created_at DESC LIMIT 10""",
            (session["user_id"],),
        ).fetchall()
        total_likes = conn.execute(
            "SELECT COUNT(*) FROM likes WHERE user_id=?", (session["user_id"],)
        ).fetchone()[0]
        total_comments = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE user_id=?", (session["user_id"],)
        ).fetchone()[0]
    return render_template(
        "profile.html",
        user=dict(user),
        liked_posts=[dict(p) for p in liked],
        my_comments=[dict(c) for c in my_comments],
        total_likes=total_likes,
        total_comments=total_comments,
    )


# ── API endpointy ─────────────────────────────────────────────────────────────
@app.route("/api/posts")
@login_required
def api_posts():
    page = max(1, int(request.args.get("page", 1)))
    per_page = 6
    offset = (page - 1) * per_page
    uid = session["user_id"]

    with get_db() as conn:
        rows = conn.execute(
            """SELECT p.id, p.image_seed, p.caption, p.created_at,
                      COUNT(DISTINCT l.id) AS like_count,
                      COUNT(DISTINCT c.id) AS comment_count,
                      COALESCE(u.username,'BabyGram') AS author_name,
                      COALESCE(u.avatar_seed,5000)    AS author_avatar,
                      EXISTS(SELECT 1 FROM likes WHERE user_id=? AND post_id=p.id) AS is_liked
               FROM posts p
               LEFT JOIN likes l    ON p.id=l.post_id
               LEFT JOIN comments c ON p.id=c.post_id
               LEFT JOIN users u    ON p.author_id=u.id
               GROUP BY p.id ORDER BY RANDOM()
               LIMIT ? OFFSET ?""",
            (uid, per_page, offset),
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

    return jsonify(
        posts=[
            {
                "id": r["id"],
                # Kurátorovaný index → garantované cute bábätko (smiech, jedenie…)
                "image_url": FEED_PHOTOS[r["image_seed"] % len(FEED_PHOTOS)],
                "thumb_url": FEED_PHOTOS[r["image_seed"] % len(FEED_PHOTOS)].replace("600/750", "300/300"),
                "caption": r["caption"],
                "like_count": r["like_count"],
                "comment_count": r["comment_count"],
                "author_name": r["author_name"],
                "author_avatar": AVATAR_PHOTOS[r["author_avatar"] % len(AVATAR_PHOTOS)],
                "is_liked": bool(r["is_liked"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ],
        has_more=(offset + per_page) < total,
        page=page,
    )


@app.route("/api/reels")
@login_required
def api_reels():
    page = max(1, int(request.args.get("page", 1)))
    per_page = 4
    offset = (page - 1) * per_page
    with get_db() as conn:
        rows = conn.execute(
            """SELECT r.id, r.image_seed, r.caption,
                      COALESCE(u.username,'BabyFeed') AS author_name,
                      COALESCE(u.avatar_seed,5001)    AS author_avatar
               FROM reels r LEFT JOIN users u ON r.author_id=u.id
               ORDER BY r.id DESC LIMIT ? OFFSET ?""",
            (per_page, offset),
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM reels").fetchone()[0]
    return jsonify(
        reels=[
            {
                "id": r["id"],
                # Kurátorovaný vertikálny formát pre reels
                "image_url": REEL_PHOTOS[r["image_seed"] % len(REEL_PHOTOS)],
                "caption": r["caption"],
                "author_name": r["author_name"],
                "author_avatar": AVATAR_PHOTOS[r["author_avatar"] % len(AVATAR_PHOTOS)],
                "likes": random.randint(200, 9999),
            }
            for r in rows
        ],
        has_more=(offset + per_page) < total,
    )


@app.route("/api/like", methods=["POST"])
@login_required
def api_like():
    post_id = request.get_json().get("post_id")
    uid = session["user_id"]
    with get_db() as conn:
        exists = conn.execute(
            "SELECT id FROM likes WHERE user_id=? AND post_id=?", (uid, post_id)
        ).fetchone()
        if exists:
            conn.execute("DELETE FROM likes WHERE user_id=? AND post_id=?", (uid, post_id))
            liked = False
        else:
            conn.execute("INSERT INTO likes (user_id, post_id) VALUES (?,?)", (uid, post_id))
            liked = True
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,)
        ).fetchone()[0]
    return jsonify(liked=liked, count=count)


@app.route("/api/comment", methods=["POST"])
@login_required
def api_comment():
    data = request.get_json()
    text = (data.get("text") or "").strip()
    post_id = data.get("post_id")
    if not text:
        return jsonify(error="Prázdny komentár"), 400
    uid = session["user_id"]
    with get_db() as conn:
        conn.execute(
            "INSERT INTO comments (user_id, post_id, text) VALUES (?,?,?)",
            (uid, post_id, text),
        )
        conn.commit()
    return jsonify(success=True, username=session["username"], text=text)


@app.route("/api/comments/<int:post_id>")
@login_required
def api_comments(post_id):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.text, c.created_at, u.username, u.avatar_seed
               FROM comments c JOIN users u ON c.user_id=u.id
               WHERE c.post_id=? ORDER BY c.created_at DESC LIMIT 30""",
            (post_id,),
        ).fetchall()
    return jsonify(
        [
            {
                "username": r["username"],
                "text": r["text"],
                "avatar": AVATAR_PHOTOS[r["avatar_seed"] % len(AVATAR_PHOTOS)].replace("80/80","50/50"),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    )


@app.route("/api/users")
@login_required
def api_users():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, username, avatar_seed FROM users WHERE id!=? ORDER BY username",
            (session["user_id"],),
        ).fetchall()
    return jsonify(
        [
            {
                "id": r["id"],
                "username": r["username"],
                "avatar": AVATAR_PHOTOS[r["avatar_seed"] % len(AVATAR_PHOTOS)].replace("80/80","60/60"),
            }
            for r in rows
        ]
    )


@app.route("/api/send_message", methods=["POST"])
@login_required
def api_send_message():
    """HTTP záloha pre odosielanie správ ak WebSocket nefunguje."""
    data = request.get_json()
    tid  = int(data.get("target_id", 0))
    text = (data.get("text") or "").strip()
    uid  = session["user_id"]
    if not (tid and text):
        return jsonify(error="Chýba text alebo príjemca"), 400
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (sender_id, receiver_id, text) VALUES (?,?,?)",
            (uid, tid, text),
        )
        conn.commit()
    return jsonify(success=True)


@app.route("/api/messages/<int:target_id>")
@login_required
def api_messages(target_id):
    uid = session["user_id"]
    with get_db() as conn:
        rows = conn.execute(
            """SELECT m.sender_id, m.text, m.created_at, u.username AS sender_name
               FROM messages m JOIN users u ON m.sender_id=u.id
               WHERE (m.sender_id=? AND m.receiver_id=?)
                  OR (m.sender_id=? AND m.receiver_id=?)
               ORDER BY m.created_at ASC""",
            (uid, target_id, target_id, uid),
        ).fetchall()
    return jsonify(
        [
            {
                "sender_id": r["sender_id"],
                "sender_name": r["sender_name"],
                "text": r["text"],
                "created_at": r["created_at"],
                "is_mine": r["sender_id"] == uid,
            }
            for r in rows
        ]
    )


# ── WebSocket udalosti ────────────────────────────────────────────────────────
def _room(a, b):
    """Deterministický názov miestnosti pre dvojicu používateľov."""
    return f"chat_{min(a,b)}_{max(a,b)}"


@socketio.on("join_chat")
def on_join(data):
    uid = session.get("user_id")
    tid = int(data.get("target_id", 0))
    if uid and tid:
        join_room(_room(uid, tid))
        # Potvrď spojenie odosielateľovi
        emit("joined", {"room": _room(uid, tid)})


@socketio.on("send_message")
def on_message(data):
    uid  = session.get("user_id")
    name = session.get("username", "?")
    tid  = int(data.get("target_id", 0))
    text = (data.get("text") or "").strip()
    if not (uid and tid and text):
        return

    # Ulož správu do databázy
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (sender_id, receiver_id, text) VALUES (?,?,?)",
            (uid, tid, text),
        )
        conn.commit()

    now = datetime.now().strftime("%H:%M")

    # Pošli PRÍJEMCOVI (include_self=False → odosielateľ ju má už z optimistic update)
    emit(
        "new_message",
        {
            "sender_id":   uid,
            "sender_name": name,
            "text":        text,
            "is_mine":     False,   # pre príjemcu je vždy False
            "created_at":  now,
        },
        room=_room(uid, tid),
        include_self=False,  # ← kľúčová oprava: odosielateľ nedostane echo
    )


@socketio.on("typing")
def on_typing(data):
    uid = session.get("user_id")
    tid = int(data.get("target_id", 0))
    if uid and tid:
        emit(
            "user_typing",
            {"username": session.get("username")},
            room=_room(uid, tid),
            include_self=False,
        )


# ── Spustenie ─────────────────────────────────────────────────────────────────
# init_db() sa volá vždy – aj pri Gunicorn spustení na Renderi
init_db()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    print(f"🍼  Baby Social App beží na  →  http://localhost:{port}")
    socketio.run(app, debug=False, host="0.0.0.0", port=port, use_reloader=False)
