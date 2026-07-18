from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import re

def time_seconds(duration: int) -> str:
    m, s = divmod(duration, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def extract_youtube_id(url: str):
    patterns = [
        r"youtu\.be/([^?&]+)",
        r"youtube\.com/watch\?v=([^&]+)",
        r"youtube\.com/embed/([^?]+)"
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    return None

def control_buttons(chat_id, paused=False, loop=False):
    buttons = [
        [
            InlineKeyboardButton("⏸️ Pause" if not paused else "▶️ Resume", callback_data=f"pause_{chat_id}"),
            InlineKeyboardButton("⏭️ Skip", callback_data=f"skip_{chat_id}"),
            InlineKeyboardButton("⏹️ Stop", callback_data=f"stop_{chat_id}"),
        ],
        [
            InlineKeyboardButton("🔁 Loop" if not loop else "🔂 Looping", callback_data=f"loop_{chat_id}"),
            InlineKeyboardButton("🗑️ Clear Queue", callback_data=f"clear_{chat_id}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)
