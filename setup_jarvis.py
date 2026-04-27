"""
===========================================================
J.A.R.V.I.S. — Setup Script
===========================================================
Automated setup: checks Python, installs deps, downloads
models, creates DB, and runs self-test.
===========================================================
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

def colored(text, color):
    colors = {"green": "\033[92m", "red": "\033[91m", "cyan": "\033[96m", "yellow": "\033[93m", "reset": "\033[0m", "bold": "\033[1m"}
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def step(msg):
    print(f"\n{colored('>', 'cyan')} {colored(msg, 'bold')}")

def ok(msg):
    print(f"  {colored('[OK]', 'green')} {msg}")

def warn(msg):
    print(f"  {colored('[!]', 'yellow')} {msg}")

def fail(msg):
    print(f"  {colored('[ERR]', 'red')} {msg}")


def check_python():
    step("Checking Python version")
    v = sys.version_info
    if v.major == 3 and v.minor >= 11:
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    elif v.major == 3 and v.minor >= 9:
        warn(f"Python {v.major}.{v.minor} — works but 3.11+ recommended")
        return True
    else:
        fail(f"Python {v.major}.{v.minor} — need 3.9+")
        return False


def install_requirements():
    step("Installing Python packages (this may take a while)")
    req_file = BASE_DIR / "requirements.txt"
    if not req_file.exists():
        fail("requirements.txt not found")
        return False
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(req_file),
            "--quiet", "--no-warn-script-location"
        ])
        ok("All packages installed")
        return True
    except subprocess.CalledProcessError as e:
        warn(f"Some packages may have failed: {e}")
        return True  # Continue anyway


def check_ollama():
    step("Checking Ollama")
    if shutil.which("ollama"):
        ok("Ollama found in PATH")
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
            if "llama3" in result.stdout.lower():
                ok("llama3 model found")
            else:
                warn("llama3 model not found — pulling now...")
                print("    This will download ~4.7 GB. Please wait...")
                subprocess.run(["ollama", "pull", "llama3:8b"], timeout=600)
                ok("llama3:8b pulled successfully")
        except Exception as e:
            warn(f"Ollama check failed: {e}")
            warn("You can pull the model manually: ollama pull llama3:8b")
    else:
        warn("Ollama not found. Install from https://ollama.ai")
        warn("JARVIS will work with Groq/Gemini API keys as fallback")


def download_whisper_model():
    step("Downloading Whisper STT model (base.en)")
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base.en", device="cpu", compute_type="int8")
        ok("Whisper base.en model ready")
        del model
    except ImportError:
        warn("faster-whisper not installed — skipping")
    except Exception as e:
        warn(f"Whisper download issue: {e}")


def download_wake_word_model():
    step("Downloading Wake Word model (hey_jarvis)")
    try:
        import openwakeword
        openwakeword.utils.download_models()
        ok("Wake word models downloaded")
    except ImportError:
        warn("openwakeword not installed — skipping")
    except Exception as e:
        warn(f"Wake word download issue: {e}")


def download_yolo_model():
    step("Downloading YOLOv8n model")
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        ok("YOLOv8n model ready")
        del model
    except ImportError:
        warn("ultralytics not installed — skipping")
    except Exception as e:
        warn(f"YOLO download issue: {e}")


def download_embedding_model():
    step("Downloading sentence-transformer model")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        ok("all-MiniLM-L6-v2 embedding model ready")
        del model
    except ImportError:
        warn("sentence-transformers not installed — skipping")
    except Exception as e:
        warn(f"Embedding model download issue: {e}")


def setup_env():
    step("Setting up environment file")
    env_file = BASE_DIR / ".env"
    template = BASE_DIR / ".env.template"
    if not env_file.exists() and template.exists():
        shutil.copy(str(template), str(env_file))
        ok("Created .env from template")
    elif env_file.exists():
        ok(".env already exists")
    else:
        warn("No .env template found")


def setup_database():
    step("Initializing databases")
    try:
        # Import config to create directories
        sys.path.insert(0, str(BASE_DIR))
        from config import DATA_DIR, SQLITE_DB_PATH, CHROMADB_PATH

        # SQLite
        import sqlite3
        conn = sqlite3.connect(str(SQLITE_DB_PATH))
        conn.execute("CREATE TABLE IF NOT EXISTS _setup_check (id INTEGER PRIMARY KEY)")
        conn.close()
        ok(f"SQLite database at {SQLITE_DB_PATH.name}")

        # ChromaDB
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMADB_PATH))
        client.get_or_create_collection("jarvis_memory")
        ok("ChromaDB initialized")

    except Exception as e:
        warn(f"Database setup issue: {e}")


def create_directories():
    step("Creating directory structure")
    dirs = ["data", "data/models", "data/cache", "data/cache/tts",
            "data/cache/music", "data/logs", "assets", "assets/sounds"]
    for d in dirs:
        (BASE_DIR / d).mkdir(parents=True, exist_ok=True)
    ok("All directories created")


def run_self_test():
    step("Running self-test")
    try:
        from voice_out import TextToSpeech
        tts = TextToSpeech()
        tts.speak_blocking("Jarvis online. All systems nominal.")
        ok("TTS self-test passed — JARVIS is speaking!")
    except Exception as e:
        warn(f"TTS self-test failed: {e}")
        warn("JARVIS will still work — TTS may need configuration")


def main():
    print(colored("\n" + "=" * 55, "cyan"))
    print(colored("  J.A.R.V.I.S. — Setup & Installation", "bold"))
    print(colored("  Just A Rather Very Intelligent System", "cyan"))
    print(colored("=" * 55, "cyan"))

    if not check_python():
        print(colored("\nSetup aborted: Python 3.9+ required.", "red"))
        sys.exit(1)

    create_directories()
    install_requirements()
    setup_env()
    check_ollama()
    download_whisper_model()
    download_wake_word_model()
    download_yolo_model()
    download_embedding_model()
    setup_database()
    run_self_test()

    print(colored("\n" + "=" * 55, "green"))
    print(colored("  Setup complete! To start JARVIS:", "bold"))
    print(colored("  python main.py", "cyan"))
    print(colored("=" * 55, "green"))
    print()


if __name__ == "__main__":
    main()
