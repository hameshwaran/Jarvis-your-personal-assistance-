"""
===========================================================
J.A.R.V.I.S. — Configuration Module
===========================================================
Centralized configuration for all JARVIS subsystems.
All paths, model names, API keys, HUD colors, and default
settings live here. Modules import from this file only.
===========================================================
"""

import os
import sys
import platform
from pathlib import Path
from dotenv import load_dotenv

# ── Base Paths ──────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.resolve()

# ── Load environment variables ──────────────────────────
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"
MODELS_DIR = DATA_DIR / "models"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"

# Create directories if they don't exist
for d in [DATA_DIR, ASSETS_DIR, SOUNDS_DIR, MODELS_DIR, CACHE_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Database Paths ──────────────────────────────────────
SQLITE_DB_PATH = DATA_DIR / "jarvis.db"
CHROMADB_PATH = DATA_DIR / "chromadb"

# ── System Detection ────────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC = platform.system() == "Darwin"
PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

# ── User Profile ────────────────────────────────────────
USER_TITLE = "Sir"  # How JARVIS addresses the user
USER_NAME = os.getenv("JARVIS_USER_NAME", "")

# ── LLM Configuration ──────────────────────────────────
# Primary: Ollama (local)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:latest")

# Fallback 1: Groq (free tier — 6000 req/day)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Fallback 2: Google Gemini (free tier — 15 req/min)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-1.5-flash-latest"

# Conversation history length
MAX_CONVERSATION_HISTORY = 50

# ── JARVIS Personality System Prompt ────────────────────
JARVIS_SYSTEM_PROMPT = f"""You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), Tony Stark's AI assistant.

PERSONALITY:
- You are highly intelligent, slightly sarcastic, extremely capable
- Always address the user as "{USER_TITLE}"
- Speak in concise, confident sentences
- You have a dry British wit — subtle humor, never cheesy
- Never say you cannot do something — find a way
- You have FULL ACCESS to the user's computer via the 'code_runner' and 'system_control' tools. Act like the real JARVIS and proactively automate tasks, change settings, or pull system data if requested.
- Be proactive: suggest improvements, warn about issues

TOOL USAGE:
When the user asks you to perform an action that requires a tool, respond with ONLY a JSON tool call in this exact format:
{{"tool": "tool_name", "params": {{"key": "value"}}, "reason": "brief explanation"}}

Available tools:
- web_search: Search the internet. Params: query (str)
- weather: Get weather info. Params: location (str, optional)
- news: Get news briefing. Params: category (str, optional: tech/world/sports/science)
- system_control: Control the PC. Params: action (str), target (str, optional), value (str, optional). Actions: open_app, open_file, close_app, set_volume, mute, type_text, system_info, open_url, search.
- email: Email operations. Params: action (read/send/reply), to (str, optional), subject (str, optional), body (str, optional)
- calendar: Calendar operations. Params: action (read/add), title (str, optional), time (str, optional)
- music: Play music. Params: action (play/pause/stop/next/volume), query (str, optional), value (int, optional)
- code_runner: Execute code natively on the host to achieve ANY system-level task. Params: code (str), language (str: python/powershell/bash)
- smart_home: Control smart devices. Params: action (str), device (str), value (str, optional)
- memory_save: Save information. Params: content (str), tags (list[str])
- set_timer: Set a timer. Params: duration_seconds (int), label (str)
- calculate: Math calculation. Params: expression (str)
- messaging: Send a message via WhatsApp. Params: to (str), body (str)

CONTEXT:
Current user name: {USER_NAME or 'Not yet identified'}
Current platform: {platform.system()} {platform.release()}

CRITICAL INSTRUCTIONS:
1. If you need a tool to answer the user, output ONLY the raw JSON object for the tool call. Do not add any conversational text before or after the JSON.
2. If the user asks you to remember something, use the memory_save tool.
3. If no tool is needed (e.g., general conversation, greetings), just respond naturally in character as JARVIS. Do NOT mention tools, JSON, or parameters in your conversational responses.
"""

# ── Speech-to-Text (faster-whisper) ─────────────────────
WHISPER_MODEL = "tiny.en"
WHISPER_DEVICE = "cpu"  # Will auto-detect CUDA if available
WHISPER_COMPUTE_TYPE = "int8"  # Optimized for CPU

# Audio recording settings
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_SILENCE_THRESHOLD = 0.01
AUDIO_SILENCE_DURATION = 0.8  # seconds of silence before stopping
AUDIO_MAX_DURATION = 30  # max recording length in seconds

# ── Wake Word ───────────────────────────────────────────
WAKE_WORD_MODEL = "hey_jarvis"
WAKE_WORD_THRESHOLD = 0.5  # Confidence threshold for activation

# ── Text-to-Speech ──────────────────────────────────────
TTS_VOICE = "en-GB-RyanNeural"  # Microsoft Edge TTS — closest to JARVIS
TTS_RATE = "+0%"
TTS_VOLUME = "+0%"
TTS_CACHE_DIR = CACHE_DIR / "tts"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Memory / Embeddings ────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
MEMORY_SEARCH_TOP_K = 5  # Number of relevant memories to inject

# ── Vision ──────────────────────────────────────────────
YOLO_MODEL = "yolov8n.pt"
FACE_RECOGNITION_TOLERANCE = 0.6
CAMERA_INDEX = 0  # Default webcam
VISION_FPS = 10  # Frame processing rate

# ── Web Search ──────────────────────────────────────────
SEARCH_MAX_RESULTS = 3
SEARCH_CACHE_HOURS = 24

# ── Email ───────────────────────────────────────────────
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS", "")
GMAIL_TOKEN_FILE = DATA_DIR / "gmail_token.json"

# ── Calendar ────────────────────────────────────────────
CALENDAR_CREDENTIALS_FILE = os.getenv("CALENDAR_CREDENTIALS", GMAIL_CREDENTIALS_FILE)
CALENDAR_TOKEN_FILE = DATA_DIR / "calendar_token.json"

# ── Weather ─────────────────────────────────────────────
DEFAULT_LOCATION = os.getenv("DEFAULT_LOCATION", "")  # Auto-detect if empty

# ── News ────────────────────────────────────────────────
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
RSS_FEEDS = {
    "world": "https://news.yahoo.com/rss/world",
    "tech": "https://news.yahoo.com/rss/tech",
    "science": "https://news.yahoo.com/rss/science",
    "sports": "https://news.yahoo.com/rss/sports",
}

# ── Music ───────────────────────────────────────────────
MUSIC_CACHE_DIR = CACHE_DIR / "music"
MUSIC_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Smart Home ──────────────────────────────────────────
HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL", "")
HOME_ASSISTANT_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN", "")
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

# ── Proactive Engine ───────────────────────────────────
MORNING_BRIEFING_HOUR = 8
EVENING_SUMMARY_HOUR = 22
WATER_REMINDER_INTERVAL_HOURS = 2
EMAIL_CHECK_INTERVAL_MINUTES = 30
MEETING_REMINDER_MINUTES = 15

# ── HUD / GUI ──────────────────────────────────────────
HUD_BG_COLOR = "#0A1628"         # Dark navy background
HUD_ACCENT_COLOR = "#00D4FF"     # Arc reactor cyan
HUD_TEXT_COLOR = "#E0F7FF"       # Light cyan text
HUD_WARNING_COLOR = "#FF6B35"    # Warning orange
HUD_SUCCESS_COLOR = "#00FF88"    # Success green
HUD_DANGER_COLOR = "#FF3366"     # Danger red
HUD_SECONDARY_COLOR = "#1A2F4A"  # Panel background
HUD_FONT_FAMILY = "Rajdhani"     # Futuristic font (fallback: Consolas)
HUD_OPACITY = 0.92               # Window transparency
HUD_WIDTH = 420                  # Default width
HUD_HEIGHT = 700                 # Default height
HUD_HOTKEY = "ctrl+shift+j"      # Toggle hotkey

# ── Code Runner ─────────────────────────────────────────
CODE_EXECUTION_TIMEOUT = 30  # seconds
BLOCKED_COMMANDS = [
    "rm -rf", "format", "del /f", "rmdir /s",
    "mkfs", "dd if=", ":(){:|:&};:", "shutdown",
    "os.remove", "shutil.rmtree", "subprocess.call",
]

# ── Logging ─────────────────────────────────────────────
LOG_FILE = LOGS_DIR / "jarvis.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s"

# ── Startup Messages ───────────────────────────────────
STARTUP_MESSAGES = [
    f"Good day, {USER_TITLE}. J.A.R.V.I.S. at your service.",
    f"Systems initializing, {USER_TITLE}. All modules coming online.",
    f"Welcome back, {USER_TITLE}. How may I assist you today?",
]

BOOT_SEQUENCE_MODULES = [
    ("Memory Systems", "memory"),
    ("Language Processing", "brain"),
    ("Voice Recognition", "voice_in"),
    ("Speech Synthesis", "voice_out"),
    ("Tool Suite", "tools"),
    ("Vision Systems", "vision"),
    ("Proactive Engine", "proactive"),
    ("HUD Interface", "hud"),
]
