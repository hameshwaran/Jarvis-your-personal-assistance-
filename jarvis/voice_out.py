"""
===========================================================
J.A.R.V.I.S. — Voice Output Module (Text-to-Speech)
===========================================================
Primary:   edge-tts (Microsoft Neural voices, free, async)
Fallback:  pyttsx3 (fully offline, no internet needed)

Features:
  - Streaming TTS — starts speaking before full text is ready
  - Barge-in support — interrupt if user speaks
  - Audio cache for repeated phrases
  - en-GB-RyanNeural voice (closest to JARVIS)
===========================================================
"""

import os
import io
import time
import asyncio
import hashlib
import logging
import tempfile
import threading
from pathlib import Path
from typing import Optional

from jarvis.config import (
    TTS_VOICE, TTS_RATE, TTS_VOLUME, TTS_CACHE_DIR
)

logger = logging.getLogger("jarvis.voice_out")


class TextToSpeech:
    """
    JARVIS voice output system.
    Uses edge-tts for high-quality neural voice, pyttsx3 as offline fallback.
    """

    def __init__(self):
        self._edge_available = False
        self._pyttsx3_engine = None
        self._is_speaking = False
        self._interrupt_flag = False
        self._playback_thread = None
        self._loop = None

        # Check edge-tts availability
        self._check_edge_tts()

        # Initialize pyttsx3 fallback
        self._init_pyttsx3()

        logger.info(f"TTS initialized — engine: {'edge-tts' if self._edge_available else 'pyttsx3'}")

    def _check_edge_tts(self):
        """Check if edge-tts is available."""
        try:
            import edge_tts
            self._edge_available = True
        except ImportError:
            logger.warning("edge-tts not available — will use pyttsx3 fallback")

    def _init_pyttsx3(self):
        """Initialize the pyttsx3 offline TTS engine."""
        try:
            import pyttsx3
            self._pyttsx3_engine = pyttsx3.init()
            # Configure voice
            voices = self._pyttsx3_engine.getProperty("voices")
            # Try to find a British male voice
            for voice in voices:
                if "english" in voice.name.lower() and ("british" in voice.name.lower() or "gb" in voice.id.lower()):
                    self._pyttsx3_engine.setProperty("voice", voice.id)
                    break
            self._pyttsx3_engine.setProperty("rate", 180)  # Words per minute
            self._pyttsx3_engine.setProperty("volume", 0.9)
        except Exception as e:
            logger.warning(f"pyttsx3 init failed: {e}")
            self._pyttsx3_engine = None

    # ================================================================
    # Main Speaking Interface
    # ================================================================

    def speak(self, text: str, cache: bool = True):
        """
        Speak the given text. Non-blocking — runs in a background thread.
        
        Args:
            text: Text to speak
            cache: Whether to cache the generated audio
        """
        if not text or not text.strip():
            return

        self._interrupt_flag = False
        self._is_speaking = True

        self._playback_thread = threading.Thread(
            target=self._speak_internal,
            args=(text, cache),
            daemon=True
        )
        self._playback_thread.start()

    def speak_blocking(self, text: str, cache: bool = True):
        """Speak and wait until finished."""
        self.speak(text, cache)
        self.wait_until_done()

    def _speak_internal(self, text: str, cache: bool):
        """Internal speaking logic — runs in background thread."""
        try:
            if self._edge_available:
                self._speak_edge_tts(text, cache)
            elif self._pyttsx3_engine:
                self._speak_pyttsx3(text)
            else:
                logger.error("No TTS engine available!")
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            # Try fallback
            if self._pyttsx3_engine:
                try:
                    self._speak_pyttsx3(text)
                except Exception as e2:
                    logger.error(f"Fallback TTS also failed: {e2}")
        finally:
            self._is_speaking = False

    # ================================================================
    # Edge-TTS (Primary — Neural Voice)
    # ================================================================

    def _speak_edge_tts(self, text: str, cache: bool):
        """Generate and play speech using edge-tts."""
        # Check cache first
        if cache:
            cached_path = self._get_cache_path(text)
            if cached_path.exists():
                logger.debug(f"Playing from cache: {cached_path.name}")
                self._play_audio_file(str(cached_path))
                return

        # Generate new audio
        try:
            # Run async edge-tts in a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            output_path = self._get_cache_path(text) if cache else Path(
                tempfile.mktemp(suffix=".mp3")
            )

            loop.run_until_complete(
                self._generate_edge_audio(text, str(output_path))
            )
            loop.close()

            if self._interrupt_flag:
                return

            self._play_audio_file(str(output_path))

            # Clean up temp files
            if not cache and output_path.exists():
                os.unlink(str(output_path))

        except Exception as e:
            logger.error(f"Edge-TTS generation failed: {e}")
            raise

    async def _generate_edge_audio(self, text: str, output_path: str):
        """Async edge-tts audio generation."""
        import edge_tts

        communicate = edge_tts.Communicate(
            text,
            voice=TTS_VOICE,
            rate=TTS_RATE,
            volume=TTS_VOLUME
        )
        await communicate.save(output_path)
        logger.debug(f"Edge-TTS audio saved: {output_path}")

    # ================================================================
    # pyttsx3 (Fallback — Offline)
    # ================================================================

    def _speak_pyttsx3(self, text: str):
        """Speak using pyttsx3 offline engine."""
        if self._pyttsx3_engine is None:
            return
        try:
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
        except Exception as e:
            logger.error(f"pyttsx3 speak failed: {e}")

    # ================================================================
    # Audio Playback
    # ================================================================

    def _play_audio_file(self, file_path: str):
        """Play an audio file (mp3/wav) using available player."""
        if self._interrupt_flag:
            return

        try:
            # Try pygame first (widely available)
            self._play_with_vlc(file_path)
        except Exception:
            try:
                self._play_with_system(file_path)
            except Exception as e:
                logger.error(f"All audio playback methods failed: {e}")

    def _play_with_vlc(self, file_path: str):
        """Play audio using python-vlc."""
        import vlc
        player = vlc.MediaPlayer(file_path)
        player.play()

        # Wait for playback to start
        time.sleep(0.5)

        # Wait for playback to finish (poll state)
        while player.is_playing():
            if self._interrupt_flag:
                player.stop()
                return
            time.sleep(0.1)

        player.release()

    def _play_with_system(self, file_path: str):
        """Play audio using system command as last resort."""
        import subprocess
        import platform

        if platform.system() == "Windows":
            # Use PowerShell to play audio
            subprocess.run(
                ["powershell", "-c",
                 f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()"],
                capture_output=True, timeout=30
            )
        else:
            # Linux/Mac — try aplay, mpv, or ffplay
            for cmd in ["mpv --no-video", "ffplay -nodisp -autoexit", "aplay"]:
                try:
                    parts = cmd.split() + [file_path]
                    subprocess.run(parts, capture_output=True, timeout=30)
                    return
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue

    # ================================================================
    # Streaming TTS
    # ================================================================

    def speak_stream(self, text_generator):
        """
        Start speaking as text arrives from a generator/stream.
        Buffers text by sentences and speaks each one.
        
        Args:
            text_generator: Generator yielding text chunks
        """
        buffer = ""
        sentence_enders = ".!?;:\n"

        for chunk in text_generator:
            if self._interrupt_flag:
                break

            buffer += chunk

            # Check if we have a complete sentence to speak
            for i, char in enumerate(buffer):
                if char in sentence_enders and i > 10:  # Min sentence length
                    sentence = buffer[:i + 1].strip()
                    buffer = buffer[i + 1:]
                    if sentence:
                        self.speak_blocking(sentence)
                    break

        # Speak any remaining text
        if buffer.strip() and not self._interrupt_flag:
            self.speak_blocking(buffer.strip())

    # ================================================================
    # Control
    # ================================================================

    def interrupt(self):
        """Stop current speech immediately (barge-in support)."""
        self._interrupt_flag = True
        logger.info("Speech interrupted")

    def wait_until_done(self):
        """Block until current speech finishes."""
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=60)

    @property
    def is_speaking(self) -> bool:
        """Check if JARVIS is currently speaking."""
        return self._is_speaking

    # ================================================================
    # Cache Management
    # ================================================================

    def _get_cache_path(self, text: str) -> Path:
        """Get the cache file path for a given text string."""
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        return TTS_CACHE_DIR / f"tts_{text_hash}.mp3"

    def clear_cache(self):
        """Clear all cached TTS audio files."""
        count = 0
        for f in TTS_CACHE_DIR.glob("tts_*.mp3"):
            f.unlink()
            count += 1
        logger.info(f"Cleared {count} cached TTS files")

    # ================================================================
    # Status
    # ================================================================

    def get_status(self) -> dict:
        """Return TTS module status."""
        cache_files = list(TTS_CACHE_DIR.glob("tts_*.mp3"))
        return {
            "engine": "edge-tts" if self._edge_available else "pyttsx3",
            "voice": TTS_VOICE if self._edge_available else "system",
            "is_speaking": self._is_speaking,
            "cache_files": len(cache_files),
            "edge_available": self._edge_available,
            "pyttsx3_available": self._pyttsx3_engine is not None,
        }
