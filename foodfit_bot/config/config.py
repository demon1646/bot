import os
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.intelligence.io.solutions/api/v1/chat/completions"
API_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer io-v2-eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
BOT_TOKEN = os.getenv("BOT_TOKEN")
