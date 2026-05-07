import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEATLOGS_API_KEY = os.getenv("NEATLOGS_API_KEY")
NEATLOGS_BASE_URL = os.getenv("NEATLOGS_BASE_URL", "https://staging-cloud.neatlogs.com")

GEMINI_PRO = "gemini/gemini-2.5-pro"
GEMINI_FLASH = "gemini/gemini-2.5-flash"

os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY or ""
