import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    SESSION = os.getenv("SESSION_STRING")  # optional
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
    LOG_CHAT = int(os.getenv("LOG_CHAT", 0))
