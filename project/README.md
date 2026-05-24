# Donezo Userbot Admin Panel

Flask admin panel with a Donezo-style green dashboard for managing Telegram userbots.

## Features

- 🔐 **Login auth** — `admin` / `xxxcoderxxxtj` (configurable via env)
- 💾 **SQLite DB** — auto-created on first run (`app/panel.db`)
- ✨ **Single-file dashboard UI** with sidebar tabs:
  - **Dashboard** — stats, currently running bots
  - **Ботҳо** — full CRUD: Start / Stop / Restart / Logs / Files / Edit / Delete
  - **Файлҳо ва сессияҳо** — browse all bot directories and Telegram sessions
  - **Таърих** — audit log of all actions
- 🚀 **Telegram login flow**: phone → 6-digit code → 2FA password (only if needed)
- 🤖 **Auto-generates** `app/users/<bot_id>/main.py` from the template
- ⏱ **Live uptime** — see how long each bot has been running (updated every second)
- 📊 **Total runtime** — accumulated runtime across multiple start/stop cycles
- 📜 **Logs viewer** — last 300 lines, refresh, clear
- ✏️ **Edit** — rename a bot, change `api_id` / `api_hash`
- 🗑️ **Delete** — removes bot, its files, sessions, and logs in one click

## Login

Default credentials:
- **Login:** `admin`
- **Password:** `xxxcoderxxxtj`

To change them, set environment variables:
```bash
ADMIN_LOGIN=myuser ADMIN_PASSWORD=mysecret python app/main.py
```

## Project structure

```
project/
├── requirements.txt
├── README.md
├── .gitignore
└── app/
    ├── main.py                  # Flask admin panel (backend + auth + DB)
    ├── panel.db                 # SQLite DB (auto-created, gitignored)
    ├── templates/
    │   ├── login.html           # Login screen
    │   └── index.html           # Dashboard UI (HTML + CSS + JS in one file)
    ├── static/
    ├── users/
    │   ├── main.py              # TEMPLATE bot file (with placeholders)
    │   ├── main1.py             # placeholder
    │   ├── main2.py             # placeholder
    │   └── <bot_id>/main.py     # auto-generated bots live here
    ├── sessions/                # Telethon .session files
    └── logs/                    # bot stdout/stderr logs
```

## Quick start

```bash
cd project
pip install -r requirements.txt
python app/main.py
```

Then open `http://localhost:5000` in your browser. You'll be redirected to the
login screen — enter `admin` / `xxxcoderxxxtj`.

Set `PORT` and `HOST` env vars if you want to bind elsewhere:
```bash
PORT=8080 HOST=0.0.0.0 python app/main.py
```

## How the bot login flow works

1. **Create**: `POST /api/bots` with `{name, api_id, api_hash}` returns a `bot_id`.
2. **Phone**: `POST /api/bots/<bot_id>/send-code` with `{phone}` triggers Telegram
   to send a 6-digit code to the user's Telegram app.
3. **Code**: `POST /api/bots/<bot_id>/verify-code` with `{code}` signs in.
   - If the account has 2FA, returns `{step: "password"}` and asks for one more step.
4. **Password (optional)**: `POST /api/bots/<bot_id>/verify-password` with `{password}`.
5. On success the backend:
   - Saves the Telethon `.session` file
   - Generates `app/users/<bot_id>/main.py` from the template
   - Starts that file as a subprocess
   - Returns `{step: "done", started: true, pid: ...}`

Each in-progress login owns its own asyncio event loop in a background thread,
so the Telethon client survives between HTTP requests.

## API endpoints

All endpoints (except `/api/health` and `/login`) require authentication.

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/api/me` | Current auth status |
| `GET`  | `/api/bots` | List all bots + summary |
| `POST` | `/api/bots` | Create bot (`name`, `api_id`, `api_hash`) |
| `GET`  | `/api/bots/<id>` | Bot detail + its files + its sessions |
| `PATCH`| `/api/bots/<id>` | Edit `name` / `api_id` / `api_hash` |
| `DELETE`| `/api/bots/<id>` | Delete bot + files + sessions + logs |
| `POST` | `/api/bots/<id>/send-code` | Step 2: phone |
| `POST` | `/api/bots/<id>/verify-code` | Step 3: code |
| `POST` | `/api/bots/<id>/verify-password` | Step 4: 2FA |
| `POST` | `/api/bots/<id>/start` | Start subprocess |
| `POST` | `/api/bots/<id>/stop`  | Stop subprocess |
| `POST` | `/api/bots/<id>/restart` | Stop + start |
| `GET`  | `/api/bots/<id>/logs` | Tail last N lines |
| `POST` | `/api/bots/<id>/logs/clear` | Wipe log file |
| `GET`  | `/api/files` | All bot directories + global sessions |
| `GET`  | `/api/audit?limit=50` | Audit log entries |

## Notes

- The original `main.py` at the repo root remains untouched.
- Generated bot files are isolated in `app/users/<bot_id>/` with their own
  `session_<bot_id>.session` so multiple bots can run side-by-side.
- The template lives at `app/users/main.py` with placeholders
  `__API_ID__`, `__API_HASH__`, `__ADMIN_USER_ID__`, `__SESSION_NAME__`.
- Uptime is tracked from the `started_at` timestamp; total runtime is
  accumulated in DB on every stop.
- The DB is created on first run — no manual migration needed.
