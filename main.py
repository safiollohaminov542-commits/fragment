# -*- coding: utf-8 -*-

from telethon import TelegramClient, events
import asyncio
import random
from datetime import datetime
import time
import json
import os
import re

api_id = 12569261
api_hash = '8af141f1319209019eb45cef2467f10e'
ADMIN_USER_ID = 8396977241

client = TelegramClient('session_name', api_id, api_hash)

# Шрифтҳо
fonts = {
    "fancy": "𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁ᥲδʙᴦдᥱёжᤋᥙᥔκ᧘ⲙн᧐ᥰρᥴᴛуɸ᥊цчɯщъыь϶юяАБВ𐌲ДЕЁЖЗИЙ𐌺𐌡𐌑𐋏𐌏𐌿Р𑀝ТУФ𐌗ЦԿШЩЪЫЬЭЮЯ",
    "bold": "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭",
    "italic": "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡",
    "bold_italic": "𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕",
    "monospace": "𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉",
    "cursive": "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩",
    "outline": "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ",
    "smallcaps": "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ",
    "upsidedown": "ɐqɔpǝɟƃɥıɾʞlɯuodbɹsʇnʌʍxʎz∀ᗺƆᗡƎℲפHIſʞ˥WNOԀὉᴚS⊥∩ΛMX⅄Z",
    "circled": "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏᥲδʙᴦдᥱёжᤋᥙᥔκ᧘ⲙн᧐ᥰρᥴᴛуɸ᥊цчɯщъыь϶юяАБВ𐌲ДЕЁЖЗИЙ𐌺𐌡𐌑𐋏𐌏𐌿Р𑀝ТУФ𐌗ЦԿШЩЪЫЬЭЮЯ",
    "square": "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉",
    "gothic": "𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔷𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ",
    "script": "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩",
    "double": "𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ",
    "fractur": "𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅"
}

normal_letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZабвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"

current_font = "fancy"
animation_speed = 0.1
animation_style = "typing"
cursor_style = "▮"
user_stats = {}
active_users = set()

FONT_DATA_FILE = 'data.json'

# Нав: Барои пауза
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

def beautify_text(text, font_name=current_font):
    if font_name not in fonts:
        font_name = "fancy"
    
    result = []
    for char in text:
        if char in normal_letters:
            fancy_char = fonts[font_name][normal_letters.index(char)]
            result.append(fancy_char)
        else:
            result.append(char)
    return ''.join(result)

def beautify_with_exceptions(text, font_name):
    # Парс кардани матн барои силкаҳо ва @mentions
    parts = re.split(r'(https?://[^\s]+|@[^\s]+)', text)
    result = []
    for part in parts:
        if part.startswith('http') or part.startswith('@'):
            result.append(part)  # Бе тағйир
        else:
            result.append(beautify_text(part, font_name))
    return ''.join(result)

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if event.sender_id != ADMIN_USER_ID:
        return  # Танҳо ҷавоб надиҳад
    
    user = await event.get_sender()
    welcome_text = f"""
✨ Салом {user.first_name}!

Ман боти зебонависи Telegram ҳастам. Ман метавонам паёмҳои шуморо бо шрифтҳои гуногун ва аниматсияҳои ҷолиб навиштам.

📜 Барои оғоз метавонед паёмеро фиристед ё аз фармонҳои зерин истифода баред:

• /font - Иваз кардани шрифт
• /style - Иваз кардани услуби аниматсия
• /speed - Танзими суръати аниматсия
• /stats - Дидани омори корбарӣ
• /help - Дидани ҳамаи фармонҳо
"""
    await event.reply(welcome_text)
    update_stats(event.sender_id, current_font)

    # Нав: Агар паузашуда бошад, фаъол кунад
    global paused_global
    if paused_global:
        paused_global = False
    if event.chat_id in paused_chats:
        paused_chats.remove(event.chat_id)

@client.on(events.NewMessage(pattern='/sts'))
async def sts_handler(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    
    global paused_global
    if paused_global:
        paused_global = False
    if event.chat_id in paused_chats:
        paused_chats.remove(event.chat_id)
    
    await event.reply("✅ Бот фаъол шуд!")

@client.on(events.NewMessage(pattern='/stop'))
async def stop_handler(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    
    paused_chats.add(event.chat_id)
    await event.reply("✅ Бот дар ин чат боздошта шуд. Барои фаъол кардан /sts истифода баред.")

@client.on(events.NewMessage(pattern='/stopall'))
async def stopall_handler(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    
    global paused_global
    paused_global = True
    await event.reply("✅ Бот дар ҳама ҷо боздошта шуд. Барои фаъол кардан /sts истифода баред.")

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
        sample_text = beautify_text("AbcXyz", font_name)
        await event.reply(f"✅ Шрифт ба «{font_name}» иваз шуд.\nНамуна: {sample_text}")
    else:
        available_fonts = "\n".join([f"• {name}" for name in fonts.keys()])
        await event.reply(f"❌ Ин шрифт вуҷуд надорад. Шрифтҳои дастрас:\n{available_fonts}")

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
    available_styles = ["typing", "wave", "random", "glitch", "reveal"]

    if style in available_styles:
        global animation_style
        animation_style = style
        await event.reply(f"🎭 Услуби аниматсия ба «{style}» иваз шуд")
    else:
        await event.reply(f"❌ Ин услуб дастрас нест. Услубҳо:\n" + "\n".join(f"• {s}" for s in available_styles))

@client.on(events.NewMessage(pattern=r'/cursor (.+)'))
async def set_cursor_style(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    
    cursor = event.pattern_match.group(1).strip()
    if len(cursor) > 0:
        global cursor_style
        cursor_style = cursor
        await event.reply(f"🖍 Намуди курсор ба «{cursor}» иваз шуд")
    else:
        await event.reply("❌ Лутфан аломати курсорро ворид кунед")

@client.on(events.NewMessage(pattern=r'/stats'))
async def show_stats(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    
    user_id = event.sender_id
    if user_id not in user_stats:
        update_stats(user_id, current_font)

    stats = user_stats[user_id]
    most_used_font = max(stats["fonts_used"].items(), key=lambda x: x[1], default=("Ҳеҷ", 0))

    text = f"""
📊 Омори корбар:

👤 Корбар аз: {stats['first_seen']}
✉️ Паёмҳои фиристода: {stats["messages"]}
🏆 Бештарин шрифт: {most_used_font[0]} ({most_used_font[1]} маротиба)
🎨 Шрифтҳои истифодашуда: {len(stats["fonts_used"])}
🔄 Охирин фаъолият: {stats['last_active']}

🌐 Ҳамагӣ {len(active_users)} корбари фаъол
"""
    await event.reply(text)

@client.on(events.NewMessage(pattern=r'/virus'))
async def slow_fake_virus(event):
    if event.sender_id != ADMIN_USER_ID:
        return

    user_font = get_user_font(event.sender_id)
    
    msg = await event.reply("🦠 Вирус муайян шуд...")

    virus_steps = [
        "🔍 Сканкунии система...",
        "📁 Ҷустуҷӯи файлҳои осебпазир...",
        "🧬 Хатари вирус дар 'System32' ёфт шуд!",
        "⚠️ Оғози безарарсозӣ...",
        "🧹 Ҳузфи файлҳои зараровар...",
        "💀 Барқароркунии кортҳои кредитӣ...",
        "📡 Ирсоли маълумот ба сервери махфӣ...",
        "🛑 Хато! Система ивазнашаванда шуд!",
        "😱 Диск формат шуд... (шӯхӣ!)",
        "✅ Вирус безарар шуд!"
    ]

    # Агар шрифт "fancy" (default) набошад, зебо кунад
    if user_font != "fancy":
        virus_steps = [beautify_with_exceptions(step, user_font) for step in virus_steps]

    for i, step in enumerate(virus_steps):
        dots = "." * (i % 4)
        await msg.edit(f"{step}{dots}")
        await asyncio.sleep(random.uniform(1.2, 2.4))

    await asyncio.sleep(1)
    await msg.edit("Ҳама чиз гирифта шуд")

@client.on(events.NewMessage(pattern=r'/hack'))
async def fake_hack(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    
    user_font = get_user_font(event.sender_id)
    
    hacking_steps = [
        ("🖥️ [1%] Интишоби системаи ахборот...", 0.5),
        ("🔥 [5%] Ҷустуҷӯи унвони IP... ҲАМА ҶОИЗ АСТ", 0.7),
        ("📡 [12%] Паёмад ба серверҳои Telegram... ҲУҶҶАТҲО ДАРҲОЛ ГИРФТА МЕШАВАД", 1),
        ("⚠️ [23%] ОШКОР КАРДАНИ ҲИФЗ... СИСТЕМА МЕТАВОНАД БЛОК ШАВАД", 1.2),
        ("🔓 [37%] КУШОДАНИ РАМЗҲО... ҲАМАИ МАЪЛУМОТ ҲОЗИР АСТ", 1),
        ("💀 [51%] ДАРЁФТИ МАЪЛУМОТИ ШАХСӢ... ИН БАРВАҚТ АЗ ҲАД ЗИЁД АСТ", 1.5),
        ("🛑 [68%] ДАСТРАСӢ БА ЧАТИ ҲАДАФ... ИСТИФОДАБАРАНДА ФАҚАТ 30 СОНИЯ ДОРАД", 1),
        ("🚨 [84%] ВУРУД БА СИСТЕМАИ ҲАДАФ... ИН ОХИРИН ИМКОН АСТ", 1.5),
        ("💣 [97%] ТАҲРИР КАРДАНИ ҲУҶҶАТҲО... ҲАМА ЧИЗ ГУМ ШУДААСТ", 2),
        ("✅ [100%] ВЗЛОМ АНҶОМ ЁФТ! ТАМОМИ МАЪЛУМОТ ГИРФТА ШУД!", 3)
    ]

    # Агар шрифт "fancy" (default) набошад, зебо кунад
    if user_font != "fancy":
        hacking_steps = [(beautify_with_exceptions(step, user_font), delay) for step, delay in hacking_steps]

    msg = await event.reply("🚀 ОГОЗИ АМАЛИЁТИ ВЗЛОМИ ХАТАРНОК...")
    await asyncio.sleep(1)

    for i in range(5):
        await msg.edit(f"🚀 ОГОЗИ АМАЛИЁТИ ВЗЛОМИ ХАТАРНОК{'!' * (i+1)}")
        await asyncio.sleep(0.3)

    for step, delay in hacking_steps:
        await asyncio.sleep(delay)
        
        if random.random() < 0.3:
            scary_effects = ["💀", "☠️", "⚠️", "🚨", "🔥", "💣"]
            step = f"{random.choice(scary_effects)} {step}"
        
        percent = int(re.search(r'\[(\d+)%\]', step).group(1))
        progress_bar = "█" * (percent // 10) + "▒" * (10 - percent // 10)
        
        if random.random() < 0.4 and percent > 30:
            warnings = [
                "СИСТЕМА МЕТАВОНАД БЛОК ШАВАД!",
                "ХАТАРИ ГУМ КАРДАНИ МАЪЛУМОТ!",
                "ИСТИФОДАБАРАНДА ОГОҲ НАМЕШАВАД!",
                "ИН АМАЛИЁТ ҚОНУНӢ НЕСТ!",
                "МАЪЛУМОТ ҲАМИША ҲАЗФ МЕШАВАД!"
            ]
            step += f"\n⚠️ {random.choice(warnings)}"
        
        await msg.edit(f"{step}\n{progress_bar} {percent}%")

    await asyncio.sleep(2)
    for i in range(3):
        await msg.edit(f"💀 ВЗЛОМ АНҶОМ ЁФТ! ДАРҲОЛ ЧАВОБ ДИҲЕД {'!' * (i+1)}")
        await asyncio.sleep(0.5)

    system_msgs = [
        "СИСТЕМА: ИСТИФОДАБАРАНДА ҲАЗФ ШУД",
        "СЕРВЕР: ҲАМАИ МАЪЛУМОТ ГИРИФТА ШУД"
    ]
    await msg.edit(f"✅ ВЗЛОМ АНҶОМ ЁФТ!\n💀 {random.choice(system_msgs)}")

@client.on(events.NewMessage(pattern=r'/help'))
async def show_help(event):
    if event.sender_id != ADMIN_USER_ID:
        return
    
    help_text = f"""
📘 Рӯйхати пурраи фармонҳо:

• /start - Оғози кор бо бот
• /font [ном] - Иваз кардани шрифт ({len(fonts)} намуд)
• /speed [1-100] - Танзими суръати аниматсия
• /style [ном] - Иваз кардани услуби аниматсия
• /cursor [аломат] - Тағйири намуди курсор
• /stats - Намоиши омори корбарӣ
• /hack - Аниматсияи взлом (фақат барои мазҳака)
• /help - Ин рӯйхат

📊 Танзимоти ҷорӣ:
• Шрифт: {current_font}
• Суръат: {int((1 - animation_speed * 200 / 100) * 100)}%
• Услуб: {animation_style}
• Курсор: {cursor_style}
"""
    await event.reply(help_text)

# Функсияҳои аниматсия (бо тағйир барои exceptions)
async def animate_typing(event, original, font_name=current_font):
    display_text = ""
    await event.edit(cursor_style)
    await asyncio.sleep(animation_speed)

    for i, char in enumerate(original):
        fancy_char = beautify_with_exceptions(char, font_name)
        display_text += fancy_char
        
        try:
            await event.edit(display_text + cursor_style)
            await asyncio.sleep(animation_speed)
            
            if i == len(original) - 1:
                await event.edit(display_text)
                await asyncio.sleep(animation_speed * 2)
                
        except Exception as e:
            if "message was not modified" not in str(e):
                print(f"Хатогӣ: {e}")

async def animate_wave(event, original, font_name=current_font):
    display_text = ""
    await event.edit(cursor_style)
    await asyncio.sleep(animation_speed)

    for i in range(len(original)):
        wave_pos = i % 4
        display_text = ""
        
        for j, char in enumerate(original[:i+1]):
            if j >= i - wave_pos:
                display_text += beautify_with_exceptions(char, font_name)
            else:
                display_text += beautify_with_exceptions(char, font_name)
        
        try:
            await event.edit(display_text + cursor_style)
            await asyncio.sleep(animation_speed * 0.7)
            
            if i == len(original) - 1:
                await event.edit(display_text)
                await asyncio.sleep(animation_speed * 2)
                
        except Exception as e:
            if "message was not modified" not in str(e):
                print(f"Хатогӣ: {e}")

async def animate_random(event, original, font_name=current_font):
    temp_text = ["_" if c != " " else " " for c in original]

    await event.edit(cursor_style)
    await asyncio.sleep(animation_speed)

    for i in range(len(original)):
        if original[i] == " ":
            continue
            
        for _ in range(3):
            temp_text[i] = random.choice(normal_letters)
            await event.edit("".join(temp_text) + cursor_style)
            await asyncio.sleep(animation_speed * 0.3)
        
        temp_text[i] = beautify_with_exceptions(original[i], font_name)
        await event.edit("".join(temp_text) + cursor_style)
        await asyncio.sleep(animation_speed * 0.5)

    await event.edit("".join(temp_text))
    await asyncio.sleep(animation_speed * 2)

async def animate_glitch(event, original, font_name=current_font):
    display_text = ""
    await event.edit(cursor_style)
    await asyncio.sleep(animation_speed)

    for i, char in enumerate(original):
        fancy_char = beautify_with_exceptions(char, font_name)
        display_text += fancy_char
        
        try:
            if random.random() < 0.3:
                glitch_text = display_text + random.choice(["#", "@", "&", "~"]) + cursor_style
                await event.edit(glitch_text)
                await asyncio.sleep(animation_speed * 0.3)
            
            await event.edit(display_text + cursor_style)
            await asyncio.sleep(animation_speed)
            
            if i == len(original) - 1:
                await event.edit(display_text)
                await asyncio.sleep(animation_speed * 2)
                
        except Exception as e:
            if "message was not modified" not in str(e):
                print(f"Хатогӣ: {e}")

async def animate_reveal(event, original, font_name=current_font):
    hidden_text = "•" * len(original)
    await event.edit(hidden_text + cursor_style)
    await asyncio.sleep(animation_speed * 2)

    display_text = ""
    for i, char in enumerate(original):
        fancy_char = beautify_with_exceptions(char, font_name)
        display_text += fancy_char
        revealed_text = display_text + hidden_text[i+1:]
        
        try:
            await event.edit(revealed_text + cursor_style)
            await asyncio.sleep(animation_speed)
            
            if i == len(original) - 1:
                await event.edit(display_text)
                await asyncio.sleep(animation_speed * 2)
                
        except Exception as e:
            if "message was not modified" not in str(e):
                print(f"Хатогӣ: {e}")

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


client.start()
client.run_until_disconnected()
