# -*- coding: utf-8 -*-
"""
Donezo-style Flask Admin Panel for Telegram Userbots.

Жараён:
  1. Корбар api_id, api_hash ва номи ботро ворид мекунад.
  2. Backend файли main.py-и нав дар app/users/<bot_name>/ месозад.
  3. Корбар рақами телефонро ворид мекунад -> Telegram коди тасдиқ мефиристад.
  4. Корбар коди 6-ракамаро ворид мекунад. Агар 2FA фаъол бошад,
     парол низ пурсида мешавад.
  5. Сессия захира карда мешавад ва бот ҳамчун subprocess оғоз мегардад.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
    FloodWaitError,
)

# ─── Роҳҳо ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
USERS_DIR = BASE_DIR / "users"
SESSIONS_DIR = BASE_DIR / "sessions"
LOGS_DIR = BASE_DIR / "logs"
TEMPLATE_BOT_FILE = USERS_DIR / "main.py"
REGISTRY_FILE = BASE_DIR / "bots_registry.json"

USERS_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ─── Flask ────────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

# ─── Реестри ботҳо (bots_registry.json) ──────────────────────────────────────
_registry_lock = threading.Lock()


def load_registry() -> dict:
    if not REGISTRY_FILE.exists():
        return {}
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_registry(data: dict) -> None:
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_bot(bot_id: str, **fields) -> dict:
    with _registry_lock:
        data = load_registry()
        if bot_id not in data:
            data[bot_id] = {}
        data[bot_id].update(fields)
        save_registry(data)
        return data[bot_id]


def get_bot(bot_id: str) -> dict | None:
    return load_registry().get(bot_id)


def remove_bot(bot_id: str) -> None:
    with _registry_lock:
        data = load_registry()
        data.pop(bot_id, None)
        save_registry(data)


# ─── Сессияҳои фаъоли login (дар хотира) ─────────────────────────────────────
# bot_id -> {"client": TelegramClient, "phone": str, "phone_code_hash": str, "loop": asyncio.AbstractEventLoop, "thread": threading.Thread}
LOGIN_SESSIONS: dict[str, dict] = {}
_login_lock = threading.Lock()


def _slugify(name: str) -> str:
    name = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE)
    return name.strip("_") or "bot"


# ─── Async helper: ҳар як login сессия event loop-и худро дар thread дорад ──
class AsyncLoopThread:
    """Loop-и asyncio дар background thread барои Telethon мизоҷ."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run(self, coro, timeout: float = 60):
        """Coroutine-ро дар loop иҷро мекунад ва натиҷаро бармегардонад."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def stop(self):
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass


# ─── Bot file generator ──────────────────────────────────────────────────────
def generate_bot_file(bot_id: str, api_id: int, api_hash: str, admin_user_id: int, bot_name: str) -> Path:
    """
    Шаблони users/main.py-ро мехонад, placeholders-ро иваз мекунад
    ва ба users/<bot_name>/main.py менависад.
    """
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

    # Сессияи воридшударо ба ҷузвдони бот мекӯчонем (агар вуҷуд дошта бошад)
    src_session = SESSIONS_DIR / f"{session_name}.session"
    if src_session.exists():
        shutil.copy2(src_session, bot_dir / f"{session_name}.session")

    return target


# ─── Subprocess manager: ботҳоро ҳамчун subprocess мегузаронад ──────────────
RUNNING_PROCS: dict[str, subprocess.Popen] = {}
_proc_lock = threading.Lock()


def start_bot_process(bot_id: str) -> dict:
    """Файли users/<bot_id>/main.py-ро ҳамчун subprocess оғоз мекунад."""
    bot = get_bot(bot_id)
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

    update_bot(
        bot_id,
        status="running",
        pid=proc.pid,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )
    return {"ok": True, "pid": proc.pid, "already": False}


def stop_bot_process(bot_id: str) -> dict:
    with _proc_lock:
        proc = RUNNING_PROCS.get(bot_id)
        if not proc:
            update_bot(bot_id, status="stopped", pid=None)
            return {"ok": True, "stopped": False, "msg": "Процесс корбариашуда нест"}

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

    update_bot(bot_id, status="stopped", pid=None)
    return {"ok": True, "stopped": True}


def get_bot_log(bot_id: str, lines: int = 200) -> str:
    log_path = LOGS_DIR / f"{bot_id}.log"
    if not log_path.exists():
        return ""
    try:
        with open(log_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            chunk = min(size, 64 * 1024)
            f.seek(size - chunk)
            data = f.read().decode("utf-8", errors="replace")
        return "\n".join(data.splitlines()[-lines:])
    except Exception as e:
        return f"[log read error] {e}"


# ─── Routes: HTML ────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ─── Routes: API ─────────────────────────────────────────────────────────────
@app.route("/api/bots", methods=["GET"])
def api_list_bots():
    data = load_registry()
    bots = []
    for bot_id, b in data.items():
        # Холати воқеии процесс
        proc = RUNNING_PROCS.get(bot_id)
        if proc and proc.poll() is None:
            b["status"] = "running"
        else:
            if b.get("status") == "running":
                b["status"] = "stopped"
                update_bot(bot_id, status="stopped", pid=None)
        bots.append({"id": bot_id, **b})
    bots.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    summary = {
        "total": len(bots),
        "running": sum(1 for b in bots if b.get("status") == "running"),
        "stopped": sum(1 for b in bots if b.get("status") == "stopped"),
        "pending": sum(1 for b in bots if b.get("status") in ("pending", "awaiting_code", "awaiting_password")),
    }
    return jsonify({"bots": bots, "summary": summary})


@app.route("/api/bots", methods=["POST"])
def api_create_bot():
    """
    Қадами 1: api_id, api_hash, name -> сохтани сабт.
    """
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

    bot_id = f"{_slugify(name)}_{uuid.uuid4().hex[:6]}"
    update_bot(
        bot_id,
        name=name,
        api_id=api_id,
        api_hash=api_hash,
        status="pending",
        created_at=datetime.now().isoformat(timespec="seconds"),
        pid=None,
        admin_user_id=None,
        phone=None,
    )

    return jsonify({"ok": True, "id": bot_id})


@app.route("/api/bots/<bot_id>/send-code", methods=["POST"])
def api_send_code(bot_id):
    """
    Қадами 2: рақами телефонро қабул мекунад, Telegram коди тасдиқ мефиристад.
    """
    bot = get_bot(bot_id)
    if not bot:
        return jsonify({"ok": False, "error": "Бот ёфт нашуд"}), 404

    payload = request.get_json(silent=True) or {}
    phone = (payload.get("phone") or "").strip()
    if not re.match(r"^\+\d{7,15}$", phone):
        return jsonify({"ok": False, "error": "Рақами телефон нодуруст. Намуна: +992123456789"}), 400

    # Сессияи кӯҳнаро тоза мекунем (агар бошад)
    _cleanup_login_session(bot_id)

    session_name = f"session_{bot_id}"
    session_path = str(SESSIONS_DIR / session_name)

    loop_thread = AsyncLoopThread()

    async def _connect_and_send():
        client = TelegramClient(session_path, bot["api_id"], bot["api_hash"])
        await client.connect()
        if await client.is_user_authorized():
            await client.disconnect()
            return {"already_authorized": True}
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
        update_bot(bot_id, phone=phone, status="authorized")
        return jsonify({"ok": True, "already_authorized": True})

    with _login_lock:
        LOGIN_SESSIONS[bot_id] = {
            "client": res["client"],
            "phone": phone,
            "phone_code_hash": res["phone_code_hash"],
            "loop_thread": loop_thread,
        }
    update_bot(bot_id, phone=phone, status="awaiting_code")
    return jsonify({"ok": True, "step": "code"})


@app.route("/api/bots/<bot_id>/verify-code", methods=["POST"])
def api_verify_code(bot_id):
    """
    Қадами 3: коди 6-ракамаро месанҷад. Агар 2FA фаъол бошад -> step=password.
    """
    bot = get_bot(bot_id)
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
        update_bot(bot_id, status="awaiting_password")
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
def api_verify_password(bot_id):
    bot = get_bot(bot_id)
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


def _finalize_login(bot_id: str, me) -> "flask.Response":
    """
    Сессия захира шуд, акнун:
      - api_id, api_hash, admin_user_id-ро дар template ҷо мегузорем
      - файли users/<bot_id>/main.py месозем
      - subprocess-ро оғоз мекунем
    """
    bot = get_bot(bot_id)
    admin_user_id = me.id
    update_bot(
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
            bot_name=bot.get("name", "bot"),
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"Хатои сохтани файл: {e}"}), 500

    _cleanup_login_session(bot_id)

    # Автоматӣ оғоз мекунем
    start_res = start_bot_process(bot_id)
    if not start_res.get("ok"):
        return jsonify({"ok": True, "step": "done", "started": False, "warn": start_res.get("error")})

    return jsonify(
        {
            "ok": True,
            "step": "done",
            "started": True,
            "pid": start_res.get("pid"),
            "user": {
                "id": me.id,
                "username": getattr(me, "username", None),
                "first_name": getattr(me, "first_name", None),
            },
        }
    )


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
def api_start(bot_id):
    return jsonify(start_bot_process(bot_id))


@app.route("/api/bots/<bot_id>/stop", methods=["POST"])
def api_stop(bot_id):
    return jsonify(stop_bot_process(bot_id))


@app.route("/api/bots/<bot_id>/restart", methods=["POST"])
def api_restart(bot_id):
    stop_bot_process(bot_id)
    time.sleep(0.5)
    return jsonify(start_bot_process(bot_id))


@app.route("/api/bots/<bot_id>/logs", methods=["GET"])
def api_logs(bot_id):
    lines = int(request.args.get("lines", 200))
    return jsonify({"ok": True, "log": get_bot_log(bot_id, lines)})


@app.route("/api/bots/<bot_id>", methods=["DELETE"])
def api_delete(bot_id):
    stop_bot_process(bot_id)
    _cleanup_login_session(bot_id)

    bot_dir = USERS_DIR / bot_id
    if bot_dir.exists():
        shutil.rmtree(bot_dir, ignore_errors=True)

    for ext in (".session", ".session-journal"):
        p = SESSIONS_DIR / f"session_{bot_id}{ext}"
        if p.exists():
            p.unlink(missing_ok=True)

    log_path = LOGS_DIR / f"{bot_id}.log"
    if log_path.exists():
        log_path.unlink(missing_ok=True)

    remove_bot(bot_id)
    return jsonify({"ok": True})


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"ok": True, "ts": datetime.now().isoformat(timespec="seconds")})


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[ADMIN] Starting Flask admin panel on http://{host}:{port}")
    print(f"[ADMIN] BASE_DIR = {BASE_DIR}")
    print(f"[ADMIN] USERS_DIR = {USERS_DIR}")
    app.run(host=host, port=port, debug=False, threaded=True)
