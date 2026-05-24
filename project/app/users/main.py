# -*- coding: utf-8 -*-
"""
Шаблони боти юсер.
Flask ин файлро ба ҷузвдони бот копи мекунад ва қиматҳоро иваз менамояд:
  __API_ID__, __API_HASH__, __ADMIN_USER_ID__, __SESSION_NAME__
"""

from telethon import TelegramClient, events
import asyncio
import random
from datetime import datetime
import json
import os
import re

# === Танзимоти автоматӣ (аз ҷониби админ-панел иваз карда мешавад) ===
api_id = __API_ID__
api_hash = '__API_HASH__'
ADMIN_USER_ID = __ADMIN_USER_ID__
SESSION_NAME = '__SESSION_NAME__'
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_PATH = os.path.join(BASE_DIR, SESSION_NAME)

client = TelegramClient(SESSION_PATH, api_id, api_hash)

# Шрифтҳо
fonts = {
    "fancy": "𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁",
    "bold": "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭",
    "italic": "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡",
    "bold_italic": "𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕",
    "monospace": "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉",
    "cursive": "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩",
    "outline": "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ",
    "smallcaps": "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ",
    "upsidedown": "ɐqɔpǝɟƃɥıɾʞlɯuodbɹsʇnʌʍxʎz∀ᗺƆᗡƎℲפHIſʞ˥WNOԀὉᴚS⊥∩ΛMX⅄Z",
    "circled": "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ",
    "gothic": "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ",
    "double": "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ",
    "fractur": "𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅",
}

normal_letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

current_font = "fancy"
animation_speed = 0.1
animation_style = "typing"
cursor_style = "▮"
user_stats = {}
active_users = set()

FONT_DATA_FILE = os.path.join(BASE_DIR, 'data.json')

paused_chats = set()
paused_global = False


def load_font_data():
    if os.path.exists(FONT_DATA_FILE):
        with open(FONT_DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_font_data(user_id, font_name):
    data = load_font_data()
    data[str(user_id)] = font_name
    with open(FONT_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_user_font(user_id):
    data = load_font_data()
    return data.get(str(user_id), current_font)


def update_stats(user_id, font_used):
    if user_id not in user_stats:
        user_stats[user_id] = {
            "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": 0,
            "fonts_used": {},
            "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    user_stats[user_id]["messages"] += 1
    user_stats[user_id]["fonts_used"][font_used] = user_stats[user_id]["fonts_used"].get(font_used, 0) + 1
    user_stats[user_id]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    active_users.add(user_id)


def beautify_text(text, font_name=None):
    font_name = font_name or current_font
    if font_name not in fonts:
        font_name = "fancy"
    result = []
    for char in text:
        if char in normal_letters:
            result.append(fonts[font_name][normal_letters.index(char)])
        else:
            result.append(char)
    return ''.join(result)


def beautify_with_exceptions(text, font_name):
    parts = re.split(r'(https?://[^\s]+|@[^\s]+)', text)
    result = []
    for part in parts:
        if part.startswith('http') or part.startswith('@'):
            result.append(part)
        else:
            result.append(beautify_text(part, font_name))
    return ''.join(result)


@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    user = await event.get_sender()
    welcome_text = (
        f"✨ Салом {user.first_name}!\n\n"
        "Ман боти зебонависи Telegram ҳастам.\n\n"
        "📜 Фармонҳо:\n"
        "• /font - Иваз кардани шрифт\n"
        "• /style - Иваз кардани услуби аниматсия\n"
        "• /speed - Танзими суръат\n"
        "• /stats - Омор\n"
        "• /help - Ҳамаи фармонҳо\n"
    )
    await event.reply(welcome_text)
    update_stats(event.sender_id, current_font)
    global paused_global
    paused_global = False
    paused_chats.discard(event.chat_id)


@client.on(events.NewMessage(pattern='/sts'))
async def sts_handler(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    global paused_global
    paused_global = False
    paused_chats.discard(event.chat_id)
    await event.reply("✅ Бот фаъол шуд!")


@client.on(events.NewMessage(pattern='/stop'))
async def stop_handler(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    paused_chats.add(event.chat_id)
    await event.reply("✅ Бот дар ин чат боздошта шуд. /sts барои фаъол кардан.")


@client.on(events.NewMessage(pattern='/stopall'))
async def stopall_handler(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    global paused_global
    paused_global = True
    await event.reply("✅ Бот дар ҳама ҷо боздошта шуд. /sts барои фаъол кардан.")


@client.on(events.NewMessage(pattern=r'/font (.+)'))
async def change_font(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    font_name = event.pattern_match.group(1).strip().lower()
    user_id = event.sender_id
    if font_name in fonts:
        save_font_data(user_id, font_name)
        update_stats(user_id, font_name)
        global current_font
        current_font = font_name
        sample = beautify_text("AbcXyz", font_name)
        await event.reply(f"✅ Шрифт ба «{font_name}» иваз шуд.\nНамуна: {sample}")
    else:
        names = "\n".join(f"• {n}" for n in fonts.keys())
        await event.reply(f"❌ Шрифтҳои дастрас:\n{names}")


@client.on(events.NewMessage(pattern=r'/speed (\d+)'))
async def set_speed(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    try:
        speed = int(event.pattern_match.group(1))
        if 1 <= speed <= 100:
            global animation_speed
            animation_speed = (101 - speed) / 200
            await event.reply(f"⚡ Суръати аниматсия ба {speed}% танзим шуд")
        else:
            await event.reply("❌ Суръат бояд аз 1 то 100 бошад")
    except ValueError:
        await event.reply("❌ Лутфан адади аз 1 то 100 ворид кунед")


@client.on(events.NewMessage(pattern=r'/style (.+)'))
async def set_animation_style(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    style = event.pattern_match.group(1).strip().lower()
    available = ["typing", "wave", "random", "glitch", "reveal"]
    if style in available:
        global animation_style
        animation_style = style
        await event.reply(f"🎭 Услуб ба «{style}» иваз шуд")
    else:
        await event.reply("❌ Услубҳо:\n" + "\n".join(f"• {s}" for s in available))


@client.on(events.NewMessage(pattern=r'/help'))
async def show_help(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    text = (
        "📘 Фармонҳо:\n\n"
        "• /start - Оғози кор\n"
        f"• /font [ном] - Шрифт ({len(fonts)} намуд)\n"
        "• /speed [1-100] - Суръат\n"
        "• /style [ном] - Услуби аниматсия\n"
        "• /stop - Боздоштан дар ин чат\n"
        "• /stopall - Боздоштан дар ҳама ҷо\n"
        "• /sts - Фаъол кардан\n"
        f"\n📊 Шрифти ҷорӣ: {current_font}\n"
        f"📊 Услуби ҷорӣ: {animation_style}\n"
    )
    await event.reply(text)


async def animate_typing(event, original, font_name):
    display = ""
    await event.edit(cursor_style)
    await asyncio.sleep(animation_speed)
    for i, ch in enumerate(original):
        display += beautify_with_exceptions(ch, font_name)
        try:
            await event.edit(display + cursor_style)
            await asyncio.sleep(animation_speed)
            if i == len(original) - 1:
                await event.edit(display)
        except Exception as e:
            if "message was not modified" not in str(e):
                print(f"Error: {e}")


async def animate_wave(event, original, font_name):
    await event.edit(cursor_style)
    await asyncio.sleep(animation_speed)
    for i in range(len(original)):
        display = beautify_with_exceptions(original[:i+1], font_name)
        try:
            await event.edit(display + cursor_style)
            await asyncio.sleep(animation_speed * 0.7)
            if i == len(original) - 1:
                await event.edit(display)
        except Exception as e:
            if "message was not modified" not in str(e):
                print(f"Error: {e}")


async def animate_glitch(event, original, font_name):
    display = ""
    await event.edit(cursor_style)
    await asyncio.sleep(animation_speed)
    for i, ch in enumerate(original):
        display += beautify_with_exceptions(ch, font_name)
        try:
            if random.random() < 0.3:
                glitch = display + random.choice(["#", "@", "&", "~"]) + cursor_style
                await event.edit(glitch)
                await asyncio.sleep(animation_speed * 0.3)
            await event.edit(display + cursor_style)
            await asyncio.sleep(animation_speed)
            if i == len(original) - 1:
                await event.edit(display)
        except Exception as e:
            if "message was not modified" not in str(e):
                print(f"Error: {e}")


async def animate_reveal(event, original, font_name):
    hidden = "•" * len(original)
    await event.edit(hidden + cursor_style)
    await asyncio.sleep(animation_speed * 2)
    display = ""
    for i, ch in enumerate(original):
        display += beautify_with_exceptions(ch, font_name)
        revealed = display + hidden[i+1:]
        try:
            await event.edit(revealed + cursor_style)
            await asyncio.sleep(animation_speed)
            if i == len(original) - 1:
                await event.edit(display)
        except Exception as e:
            if "message was not modified" not in str(e):
                print(f"Error: {e}")


async def animate_random(event, original, font_name):
    temp = ["_" if c != " " else " " for c in original]
    await event.edit(cursor_style)
    await asyncio.sleep(animation_speed)
    for i in range(len(original)):
        if original[i] == " ":
            continue
        for _ in range(3):
            temp[i] = random.choice(normal_letters)
            await event.edit("".join(temp) + cursor_style)
            await asyncio.sleep(animation_speed * 0.3)
        temp[i] = beautify_with_exceptions(original[i], font_name)
        await event.edit("".join(temp) + cursor_style)
        await asyncio.sleep(animation_speed * 0.5)
    await event.edit("".join(temp))


@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    if event.raw_text.startswith('/'):
        return
    if event.sender_id != ADMIN_USER_ID:
        return
    global paused_global
    if paused_global or event.chat_id in paused_chats:
        return
    original = event.raw_text.strip()
    if not original:
        return
    user_id = event.sender_id
    user_font = get_user_font(user_id)
    update_stats(user_id, user_font)

    if animation_style == "typing":
        await animate_typing(event, original, user_font)
    elif animation_style == "wave":
        await animate_wave(event, original, user_font)
    elif animation_style == "random":
        await animate_random(event, original, user_font)
    elif animation_style == "glitch":
        await animate_glitch(event, original, user_font)
    elif animation_style == "reveal":
        await animate_reveal(event, original, user_font)


if __name__ == '__main__':
    print(f"[BOT] Starting userbot for ADMIN={ADMIN_USER_ID} session={SESSION_NAME}")
    client.start()
    client.run_until_disconnected()
