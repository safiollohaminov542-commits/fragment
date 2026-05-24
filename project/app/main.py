# -*- coding: utf-8 -*-
"""
Donezo-style Flask Admin Panel for Telegram Userbots.

Features:
  - Login auth (admin / xxxcoderxxxtj) via session cookie
  - SQLite DB (auto-created) for bot registry & audit
  - Telegram login flow: phone -> code -> 2FA password (only when needed)
  - Auto-generates app/users/<bot_id>/main.py from template
  - Subprocess lifecycle: start / stop / restart / status with uptime
  - Edit (rename) / delete bots
  - Files & sessions browser
  - Live logs viewer
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask, jsonify, render_template, request,
    session, redirect, url_for, send_from_directory,
)

from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
    FloodWaitError,
)

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
USERS_DIR = BASE_DIR / "users"
SESSIONS_DIR = BASE_DIR / "sessions"
LOGS_DIR = BASE_DIR / "logs"
TEMPLATE_BOT_FILE = USERS_DIR / "main.py"
DB_FILE = BASE_DIR / "panel.db"

USERS_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ─── Auth ────────────────────────────────────────────────────────────────────
ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "xxxcoderxxxtj")
SECRET_KEY = os.environ.get("SECRET_KEY", "donezo-" + uuid.uuid4().hex)

# ─── Flask ───────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7  # 7 days

# ─── SQLite DB ───────────────────────────────────────────────────────────────
_db_lock = threading.Lock()


def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _db_lock, db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS bots (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                api_id          INTEGER NOT NULL,
                api_hash        TEXT NOT NULL,
                phone           TEXT,
                admin_user_id   INTEGER,
                username        TEXT,
                first_name      TEXT,
                status          TEXT NOT NULL DEFAULT 'pending',
                pid             INTEGER,
                started_at      TEXT,
                stopped_at      TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                total_runtime   INTEGER NOT NULL DEFAULT 0  -- accumulated seconds across runs
            );

            CREATE TABLE IF NOT EXISTS audit (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id      TEXT,
                action      TEXT NOT NULL,
                meta        TEXT,
                created_at  TEXT NOT NULL
            );
            """
        )
        conn.commit()


def audit(action: str, bot_id: str | None = None, meta: dict | None = None) -> None:
    try:
        with _db_lock, db() as conn:
            conn.execute(
                "INSERT INTO audit (bot_id, action, meta, created_at) VALUES (?,?,?,?)",
                (bot_id, action, json.dumps(meta or {}, ensure_ascii=False),
                 datetime.now().isoformat(timespec="seconds")),
            )
            conn.commit()
    except Exception:
        pass


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def db_insert_bot(bot_id: str, name: str, api_id: int, api_hash: str) -> None:
    with _db_lock, db() as conn:
        conn.execute(
            """INSERT INTO bots (id, name, api_id, api_hash, status, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (bot_id, name, api_id, api_hash, "pending", now_iso(), now_iso()),
        )
        conn.commit()


def db_update_bot(bot_id: str, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = now_iso()
    cols = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [bot_id]
    with _db_lock, db() as conn:
        conn.execute(f"UPDATE bots SET {cols} WHERE id=?", vals)
        conn.commit()


def db_get_bot(bot_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM bots WHERE id=?", (bot_id,)).fetchone()
        return dict(row) if row else None


def db_get_bot_by_name(name: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM bots WHERE name=?", (name,)).fetchone()
        return dict(row) if row else None


def db_list_bots() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM bots ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def db_delete_bot(bot_id: str) -> None:
    with _db_lock, db() as conn:
        conn.execute("DELETE FROM bots WHERE id=?", (bot_id,))
        conn.commit()


init_db()


# ─── Login sessions (in-memory, for active Telegram login flows) ─────────────
LOGIN_SESSIONS: dict[str, dict] = {}
_login_lock = threading.Lock()


def _slugify(name: str) -> str:
    name = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE)
    return name.strip("_") or "bot"


# ─── Async loop runner (Telethon survives across HTTP requests) ──────────────
class AsyncLoopThread:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self, coro, timeout: float = 60):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def stop(self):
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass


# ─── Bot file generator ──────────────────────────────────────────────────────
def generate_bot_file(bot_id: str, api_id: int, api_hash: str, admin_user_id: int) -> Path:
    bot_dir = USERS_DIR / bot_id
    bot_dir.mkdir(parents=True, exist_ok=True)

    template = TEMPLATE_BOT_FILE.read_text(encoding="utf-8")
    session_name = f"session_{bot_id}"

    rendered = (
        template
        .replace("__API_ID__", str(api_id))
        .replace("__API_HASH__", api_hash)
        .replace("__ADMIN_USER_ID__", str(admin_user_id))
        .replace("__SESSION_NAME__", session_name)
    )

    target = bot_dir / "main.py"
    target.write_text(rendered, encoding="utf-8")

    # Move generated session into the bot's own directory (so it self-contains)
    src_session = SESSIONS_DIR / f"{session_name}.session"
    if src_session.exists():
        shutil.copy2(src_session, bot_dir / f"{session_name}.session")

    return target


# ─── Subprocess manager ──────────────────────────────────────────────────────
RUNNING_PROCS: dict[str, subprocess.Popen] = {}
_proc_lock = threading.Lock()


def start_bot_process(bot_id: str) -> dict:
    bot = db_get_bot(bot_id)
    if not bot:
        return {"ok": False, "error": "Бот ёфт нашуд"}

    bot_main = USERS_DIR / bot_id / "main.py"
    if not bot_main.exists():
        return {"ok": False, "error": "Файли main.py барои ин бот вуҷуд надорад"}

    with _proc_lock:
        existing = RUNNING_PROCS.get(bot_id)
        if existing and existing.poll() is None:
            return {"ok": True, "pid": existing.pid, "already": True}

        log_path = LOGS_DIR / f"{bot_id}.log"
        log_file = open(log_path, "ab", buffering=0)

        proc = subprocess.Popen(
            [sys.executable, "-u", str(bot_main)],
            cwd=str(USERS_DIR / bot_id),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid if os.name != "nt" else None,
        )
        RUNNING_PROCS[bot_id] = proc

    db_update_bot(bot_id, status="running", pid=proc.pid, started_at=now_iso(), stopped_at=None)
    audit("start", bot_id, {"pid": proc.pid})
    return {"ok": True, "pid": proc.pid, "already": False}


def stop_bot_process(bot_id: str) -> dict:
    bot = db_get_bot(bot_id)
    if not bot:
        return {"ok": False, "error": "Бот ёфт нашуд"}

    with _proc_lock:
        proc = RUNNING_PROCS.get(bot_id)
        had_proc = proc is not None and proc.poll() is None

        if had_proc:
            try:
                if os.name != "nt":
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if os.name != "nt":
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
            except ProcessLookupError:
                pass
            finally:
                RUNNING_PROCS.pop(bot_id, None)

    # Accumulate runtime
    started = bot.get("started_at")
    extra = 0
    if started:
        try:
            extra = max(0, int((datetime.now() - datetime.fromisoformat(started)).total_seconds()))
        except Exception:
            extra = 0

    db_update_bot(
        bot_id,
        status="stopped",
        pid=None,
        stopped_at=now_iso(),
        total_runtime=(bot.get("total_runtime", 0) or 0) + extra,
        started_at=None,
    )
    audit("stop", bot_id, {"runtime_added": extra})
    return {"ok": True, "stopped": had_proc}


def get_bot_log(bot_id: str, lines: int = 300) -> str:
    log_path = LOGS_DIR / f"{bot_id}.log"
    if not log_path.exists():
        return ""
    try:
        with open(log_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            chunk = min(size, 256 * 1024)
            f.seek(size - chunk)
            data = f.read().decode("utf-8", errors="replace")
        return "\n".join(data.splitlines()[-lines:])
    except Exception as e:
        return f"[log read error] {e}"


def reconcile_status() -> None:
    """Sync DB status with real subprocess state."""
    for bot in db_list_bots():
        bid = bot["id"]
        proc = RUNNING_PROCS.get(bid)
        is_alive = proc is not None and proc.poll() is None
        if bot["status"] == "running" and not is_alive:
            # Process died externally
            started = bot.get("started_at")
            extra = 0
            if started:
                try:
                    extra = max(0, int((datetime.now() - datetime.fromisoformat(started)).total_seconds()))
                except Exception:
                    extra = 0
            db_update_bot(
                bid,
                status="stopped",
                pid=None,
                stopped_at=now_iso(),
                total_runtime=(bot.get("total_runtime", 0) or 0) + extra,
                started_at=None,
            )


def bot_uptime_seconds(bot: dict) -> int:
    if bot.get("status") == "running" and bot.get("started_at"):
        try:
            return max(0, int((datetime.now() - datetime.fromisoformat(bot["started_at"])).total_seconds()))
        except Exception:
            return 0
    return 0


# ─── Auth helpers ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("authed"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Unauthorized", "auth": False}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ─── Routes: HTML ────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    return render_template("index.html", admin_login=ADMIN_LOGIN)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_val = (request.form.get("login") or "").strip()
        pwd = request.form.get("password") or ""
        if login_val == ADMIN_LOGIN and pwd == ADMIN_PASSWORD:
            session.permanent = True
            session["authed"] = True
            session["user"] = login_val
            audit("login", None, {"user": login_val})
            return redirect(url_for("index"))
        return render_template("login.html", error="Логин ё парол нодуруст"), 401
    if session.get("authed"):
        return redirect(url_for("index"))
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    audit("logout", None, {"user": session.get("user")})
    session.clear()
    return redirect(url_for("login"))


# ─── Routes: API ─────────────────────────────────────────────────────────────
@app.route("/api/me", methods=["GET"])
def api_me():
    return jsonify({
        "authed": bool(session.get("authed")),
        "user": session.get("user"),
    })


@app.route("/api/bots", methods=["GET"])
@login_required
def api_list_bots():
    reconcile_status()
    bots = db_list_bots()
    out = []
    for b in bots:
        b["uptime_seconds"] = bot_uptime_seconds(b)
        b["has_file"] = (USERS_DIR / b["id"] / "main.py").exists()
        b["has_session"] = bool(list((USERS_DIR / b["id"]).glob("*.session"))) if (USERS_DIR / b["id"]).exists() else False
        out.append(b)

    summary = {
        "total": len(out),
        "running": sum(1 for b in out if b.get("status") == "running"),
        "stopped": sum(1 for b in out if b.get("status") == "stopped"),
        "pending": sum(1 for b in out if b.get("status") in ("pending", "awaiting_code", "awaiting_password")),
    }
    return jsonify({"bots": out, "summary": summary})


@app.route("/api/bots", methods=["POST"])
@login_required
def api_create_bot():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    api_id_raw = data.get("api_id")
    api_hash = (data.get("api_hash") or "").strip()

    if not name:
        return jsonify({"ok": False, "error": "Номи бот лозим аст"}), 400
    try:
        api_id = int(api_id_raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "api_id бояд адад бошад"}), 400
    if not api_hash or len(api_hash) < 10:
        return jsonify({"ok": False, "error": "api_hash нодуруст"}), 400

    if db_get_bot_by_name(name):
        return jsonify({"ok": False, "error": "Боте бо ин ном аллакай вуҷуд дорад"}), 400

    bot_id = f"{_slugify(name)}_{uuid.uuid4().hex[:6]}"
    db_insert_bot(bot_id, name, api_id, api_hash)
    audit("create", bot_id, {"name": name})
    return jsonify({"ok": True, "id": bot_id})


@app.route("/api/bots/<bot_id>", methods=["PATCH"])
@login_required
def api_edit_bot(bot_id):
    bot = db_get_bot(bot_id)
    if not bot:
        return jsonify({"ok": False, "error": "Бот ёфт нашуд"}), 404

    data = request.get_json(silent=True) or {}
    fields = {}

    if "name" in data:
        new_name = (data["name"] or "").strip()
        if not new_name:
            return jsonify({"ok": False, "error": "Ном холӣ буда наметавонад"}), 400
        existing = db_get_bot_by_name(new_name)
        if existing and existing["id"] != bot_id:
            return jsonify({"ok": False, "error": "Боте бо ин ном аллакай вуҷуд дорад"}), 400
        fields["name"] = new_name

    if "api_id" in data and data["api_id"] is not None:
        try:
            fields["api_id"] = int(data["api_id"])
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "api_id бояд адад бошад"}), 400

    if "api_hash" in data and data["api_hash"]:
        fields["api_hash"] = data["api_hash"].strip()

    if not fields:
        return jsonify({"ok": False, "error": "Чизе барои тағйир нест"}), 400

    db_update_bot(bot_id, **fields)
    audit("edit", bot_id, fields)

    # If the bot already has a generated file and creds changed, regenerate it
    if (USERS_DIR / bot_id / "main.py").exists() and bot.get("admin_user_id"):
        try:
            updated = db_get_bot(bot_id)
            generate_bot_file(
                bot_id=bot_id,
                api_id=updated["api_id"],
                api_hash=updated["api_hash"],
                admin_user_id=updated["admin_user_id"],
            )
        except Exception as e:
            return jsonify({"ok": True, "warn": f"DB updated, but file regeneration failed: {e}"})

    return jsonify({"ok": True})


@app.route("/api/bots/<bot_id>/send-code", methods=["POST"])
@login_required
def api_send_code(bot_id):
    bot = db_get_bot(bot_id)
    if not bot:
        return jsonify({"ok": False, "error": "Бот ёфт нашуд"}), 404

    payload = request.get_json(silent=True) or {}
    phone = (payload.get("phone") or "").strip()
    if not re.match(r"^\+\d{7,15}$", phone):
        return jsonify({"ok": False, "error": "Рақами телефон нодуруст. Намуна: +992123456789"}), 400

    _cleanup_login_session(bot_id)

    session_name = f"session_{bot_id}"
    session_path = str(SESSIONS_DIR / session_name)

    loop_thread = AsyncLoopThread()

    async def _connect_and_send():
        client = TelegramClient(session_path, bot["api_id"], bot["api_hash"])
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            await client.disconnect()
            return {"already_authorized": True, "me": me}
        result = await client.send_code_request(phone)
        return {"client": client, "phone_code_hash": result.phone_code_hash}

    try:
        res = loop_thread.run(_connect_and_send(), timeout=60)
    except PhoneNumberInvalidError:
        loop_thread.stop()
        return jsonify({"ok": False, "error": "Рақами телефон нодуруст"}), 400
    except FloodWaitError as e:
        loop_thread.stop()
        return jsonify({"ok": False, "error": f"Flood wait: {e.seconds}s"}), 429
    except Exception as e:
        loop_thread.stop()
        return jsonify({"ok": False, "error": f"Хато: {e}"}), 500

    if res.get("already_authorized"):
        loop_thread.stop()
        me = res.get("me")
        admin_id = me.id if me else bot.get("admin_user_id")
        db_update_bot(
            bot_id,
            phone=phone,
            admin_user_id=admin_id,
            username=getattr(me, "username", None) if me else None,
            first_name=getattr(me, "first_name", None) if me else None,
            status="authorized",
        )
        try:
            generate_bot_file(bot_id, bot["api_id"], bot["api_hash"], admin_id)
        except Exception as e:
            return jsonify({"ok": True, "already_authorized": True, "warn": str(e)})
        start_bot_process(bot_id)
        return jsonify({"ok": True, "already_authorized": True, "step": "done"})

    with _login_lock:
        LOGIN_SESSIONS[bot_id] = {
            "client": res["client"],
            "phone": phone,
            "phone_code_hash": res["phone_code_hash"],
            "loop_thread": loop_thread,
        }
    db_update_bot(bot_id, phone=phone, status="awaiting_code")
    return jsonify({"ok": True, "step": "code"})


@app.route("/api/bots/<bot_id>/verify-code", methods=["POST"])
@login_required
def api_verify_code(bot_id):
    bot = db_get_bot(bot_id)
    if not bot:
        return jsonify({"ok": False, "error": "Бот ёфт нашуд"}), 404

    sess = LOGIN_SESSIONS.get(bot_id)
    if not sess:
        return jsonify({"ok": False, "error": "Сессияи login ёфт нашуд. Аз нав оғоз кунед."}), 400

    payload = request.get_json(silent=True) or {}
    code = (payload.get("code") or "").strip().replace(" ", "")
    if not re.match(r"^\d{4,7}$", code):
        return jsonify({"ok": False, "error": "Коди нодуруст"}), 400

    client: TelegramClient = sess["client"]
    phone = sess["phone"]
    phone_code_hash = sess["phone_code_hash"]
    loop_thread: AsyncLoopThread = sess["loop_thread"]

    async def _sign_in():
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        me = await client.get_me()
        await client.disconnect()
        return me

    try:
        me = loop_thread.run(_sign_in(), timeout=60)
    except SessionPasswordNeededError:
        db_update_bot(bot_id, status="awaiting_password")
        return jsonify({"ok": True, "step": "password"})
    except PhoneCodeInvalidError:
        return jsonify({"ok": False, "error": "Код нодуруст"}), 400
    except PhoneCodeExpiredError:
        _cleanup_login_session(bot_id)
        return jsonify({"ok": False, "error": "Коди тасдиқ кӯҳна шудааст. Аз нав оғоз кунед."}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"Хато: {e}"}), 500

    return _finalize_login(bot_id, me)


@app.route("/api/bots/<bot_id>/verify-password", methods=["POST"])
@login_required
def api_verify_password(bot_id):
    bot = db_get_bot(bot_id)
    if not bot:
        return jsonify({"ok": False, "error": "Бот ёфт нашуд"}), 404

    sess = LOGIN_SESSIONS.get(bot_id)
    if not sess:
        return jsonify({"ok": False, "error": "Сессияи login ёфт нашуд"}), 400

    payload = request.get_json(silent=True) or {}
    password = payload.get("password") or ""
    if not password:
        return jsonify({"ok": False, "error": "Парол лозим аст"}), 400

    client: TelegramClient = sess["client"]
    loop_thread: AsyncLoopThread = sess["loop_thread"]

    async def _sign_in_2fa():
        await client.sign_in(password=password)
        me = await client.get_me()
        await client.disconnect()
        return me

    try:
        me = loop_thread.run(_sign_in_2fa(), timeout=60)
    except PasswordHashInvalidError:
        return jsonify({"ok": False, "error": "Парол нодуруст"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"Хато: {e}"}), 500

    return _finalize_login(bot_id, me)


def _finalize_login(bot_id: str, me):
    bot = db_get_bot(bot_id)
    admin_user_id = me.id
    db_update_bot(
        bot_id,
        admin_user_id=admin_user_id,
        username=getattr(me, "username", None),
        first_name=getattr(me, "first_name", None),
        status="authorized",
    )

    try:
        generate_bot_file(
            bot_id=bot_id,
            api_id=bot["api_id"],
            api_hash=bot["api_hash"],
            admin_user_id=admin_user_id,
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"Хатои сохтани файл: {e}"}), 500

    _cleanup_login_session(bot_id)

    start_res = start_bot_process(bot_id)
    if not start_res.get("ok"):
        return jsonify({"ok": True, "step": "done", "started": False, "warn": start_res.get("error")})

    audit("login_complete", bot_id, {"admin_user_id": admin_user_id})
    return jsonify({
        "ok": True,
        "step": "done",
        "started": True,
        "pid": start_res.get("pid"),
        "user": {
            "id": me.id,
            "username": getattr(me, "username", None),
            "first_name": getattr(me, "first_name", None),
        },
    })


def _cleanup_login_session(bot_id: str) -> None:
    with _login_lock:
        sess = LOGIN_SESSIONS.pop(bot_id, None)
    if not sess:
        return
    try:
        client = sess.get("client")
        loop_thread: AsyncLoopThread = sess.get("loop_thread")
        if client and loop_thread:
            try:
                loop_thread.run(client.disconnect(), timeout=10)
            except Exception:
                pass
        if loop_thread:
            loop_thread.stop()
    except Exception:
        pass


@app.route("/api/bots/<bot_id>/start", methods=["POST"])
@login_required
def api_start(bot_id):
    return jsonify(start_bot_process(bot_id))


@app.route("/api/bots/<bot_id>/stop", methods=["POST"])
@login_required
def api_stop(bot_id):
    return jsonify(stop_bot_process(bot_id))


@app.route("/api/bots/<bot_id>/restart", methods=["POST"])
@login_required
def api_restart(bot_id):
    stop_bot_process(bot_id)
    time.sleep(0.5)
    return jsonify(start_bot_process(bot_id))


@app.route("/api/bots/<bot_id>/logs", methods=["GET"])
@login_required
def api_logs(bot_id):
    lines = int(request.args.get("lines", 300))
    return jsonify({"ok": True, "log": get_bot_log(bot_id, lines)})


@app.route("/api/bots/<bot_id>/logs/clear", methods=["POST"])
@login_required
def api_logs_clear(bot_id):
    log_path = LOGS_DIR / f"{bot_id}.log"
    if log_path.exists():
        log_path.write_text("", encoding="utf-8")
    audit("logs_clear", bot_id)
    return jsonify({"ok": True})


@app.route("/api/bots/<bot_id>", methods=["GET"])
@login_required
def api_bot_detail(bot_id):
    reconcile_status()
    bot = db_get_bot(bot_id)
    if not bot:
        return jsonify({"ok": False, "error": "Бот ёфт нашуд"}), 404
    bot["uptime_seconds"] = bot_uptime_seconds(bot)

    bot_dir = USERS_DIR / bot_id
    files = []
    if bot_dir.exists():
        for p in sorted(bot_dir.iterdir()):
            try:
                stat = p.stat()
                files.append({
                    "name": p.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                    "is_session": p.suffix == ".session",
                    "is_dir": p.is_dir(),
                })
            except Exception:
                pass

    sessions = []
    for p in sorted(SESSIONS_DIR.glob(f"session_{bot_id}*")):
        try:
            stat = p.stat()
            sessions.append({
                "name": p.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            })
        except Exception:
            pass

    return jsonify({"ok": True, "bot": bot, "files": files, "sessions": sessions})


@app.route("/api/bots/<bot_id>", methods=["DELETE"])
@login_required
def api_delete(bot_id):
    bot = db_get_bot(bot_id)
    if not bot:
        return jsonify({"ok": False, "error": "Бот ёфт нашуд"}), 404

    stop_bot_process(bot_id)
    _cleanup_login_session(bot_id)

    bot_dir = USERS_DIR / bot_id
    if bot_dir.exists():
        shutil.rmtree(bot_dir, ignore_errors=True)

    for p in SESSIONS_DIR.glob(f"session_{bot_id}*"):
        try:
            p.unlink()
        except Exception:
            pass

    log_path = LOGS_DIR / f"{bot_id}.log"
    if log_path.exists():
        log_path.unlink(missing_ok=True)

    db_delete_bot(bot_id)
    audit("delete", bot_id, {"name": bot["name"]})
    return jsonify({"ok": True})


# ─── Files & sessions browser (global) ──────────────────────────────────────
@app.route("/api/files", methods=["GET"])
@login_required
def api_files():
    """Lists all bot directories under app/users/ and global sessions."""
    bot_dirs = []
    for p in sorted(USERS_DIR.iterdir()):
        if not p.is_dir():
            continue
        children = []
        for child in sorted(p.iterdir()):
            try:
                stat = child.stat()
                children.append({
                    "name": child.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                })
            except Exception:
                pass
        bot = db_get_bot(p.name)
        bot_dirs.append({
            "id": p.name,
            "name": (bot or {}).get("name") or p.name,
            "files": children,
        })

    sessions = []
    for p in sorted(SESSIONS_DIR.glob("*.session*")):
        try:
            stat = p.stat()
            sessions.append({
                "name": p.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            })
        except Exception:
            pass

    return jsonify({"ok": True, "bot_dirs": bot_dirs, "sessions": sessions})


@app.route("/api/audit", methods=["GET"])
@login_required
def api_audit():
    limit = int(request.args.get("limit", 50))
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return jsonify({"ok": True, "audit": [dict(r) for r in rows]})


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"ok": True, "ts": now_iso()})


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[ADMIN] Starting Flask admin panel on http://{host}:{port}")
    print(f"[ADMIN] Login: {ADMIN_LOGIN} / Password: {ADMIN_PASSWORD}")
    print(f"[ADMIN] DB: {DB_FILE}")
    app.run(host=host, port=port, debug=False, threaded=True)
