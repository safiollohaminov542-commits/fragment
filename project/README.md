# Donezo Userbot Admin Panel

Flask admin panel with a Donezo-style green dashboard for managing Telegram userbots.

## Features

- Beautiful single-file dashboard UI (HTML + CSS + JS in one file)
- Add a new userbot through the GUI by entering `api_id`, `api_hash`, and a name
- Telegram login flow inside the panel:
  1. Enter phone number (`+992...`, `+7...`, etc.)
  2. Enter the 6-digit code Telegram sends
  3. Enter 2FA password (only if the account has one)
- Automatically generates `app/users/<bot_id>/main.py` from the template
  with `api_id`, `api_hash`, and `ADMIN_USER_ID` substituted
- Automatically starts the generated bot file as a background process
- Start / stop / restart / delete bots from the UI
- Live logs viewer

## Project structure

```
project/
├── requirements.txt
└── app/
    ├── main.py                  # Flask admin panel (backend)
    ├── templates/
    │   └── index.html           # Dashboard UI (single file: HTML+CSS+JS)
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

Then open `http://localhost:5000` in your browser.

Set `PORT` and `HOST` env vars if you want to bind elsewhere:

```bash
PORT=8080 HOST=0.0.0.0 python app/main.py
```

## How the login flow works

1. **Create**: `POST /api/bots` with `{name, api_id, api_hash}` returns a `bot_id`.
2. **Phone**: `POST /api/bots/<bot_id>/send-code` with `{phone}` triggers Telegram
   to send a 6-digit code to the user's Telegram app.
3. **Code**: `POST /api/bots/<bot_id>/verify-code` with `{code}` signs in.
   - If the account has 2FA, it returns `{step: "password"}` and asks for one more step.
4. **Password (optional)**: `POST /api/bots/<bot_id>/verify-password` with `{password}`.
5. On success the backend:
   - Saves the Telethon `.session` file
   - Generates `app/users/<bot_id>/main.py` from the template
   - Starts that file as a subprocess
   - Returns `{step: "done", started: true, pid: ...}`

Each in-progress login owns its own asyncio event loop in a background thread,
so the Telethon client survives between HTTP requests.

## Notes

- The original `main.py` at the repo root remains untouched.
- Generated bot files are isolated in `app/users/<bot_id>/` with their own
  `session_<bot_id>.session` so multiple bots can run side-by-side.
- The template lives at `app/users/main.py` with placeholders
  `__API_ID__`, `__API_HASH__`, `__ADMIN_USER_ID__`, `__SESSION_NAME__`.
