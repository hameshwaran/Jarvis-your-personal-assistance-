"""
===========================================================
J.A.R.V.I.S. — Music Tool
===========================================================
yt-dlp for YouTube streaming + python-vlc for playback.
===========================================================
"""

import logging
import threading
import subprocess
from pathlib import Path
from jarvis.config import MUSIC_CACHE_DIR

logger = logging.getLogger("jarvis.tools.music")


class MusicTool:
    """Play music via yt-dlp (YouTube) + VLC."""

    def __init__(self, memory=None):
        self.memory = memory
        self._player = None
        self._vlc_instance = None
        self._current_track = None
        self._init_vlc()

    def _init_vlc(self):
        try:
            import vlc
            self._vlc_instance = vlc.Instance("--no-xlib")
            self._player = self._vlc_instance.media_player_new()
            logger.info("VLC player initialized")
        except Exception as e:
            logger.warning(f"VLC init failed: {e}")

    def execute(self, params: dict) -> str:
        action = params.get("action", "play").lower()
        handlers = {
            "play": self._play, "pause": self._pause, "resume": self._resume,
            "stop": self._stop, "next": self._play, "volume": self._volume,
            "status": self._status,
        }
        handler = handlers.get(action)
        if handler:
            return handler(params)
        return f"Unknown music action: '{action}', Sir."

    def _play(self, params):
        query = params.get("query", "")
        if not query:
            return "What would you like me to play, Sir?"
        try:
            url = self._search_youtube(query)
            if not url:
                return f"Couldn't find '{query}' on YouTube, Sir."
            stream_url = self._get_stream_url(url)
            if not stream_url:
                return f"Couldn't get audio stream for '{query}', Sir."
            if self._player:
                import vlc
                media = self._vlc_instance.media_new(stream_url)
                self._player.set_media(media)
                self._player.play()
                self._current_track = query
                return f"Now playing: {query}, Sir."
            return "VLC player not available, Sir."
        except Exception as e:
            logger.error(f"Music play failed: {e}")
            return f"Playback failed, Sir: {str(e)}"

    def _pause(self, params):
        if self._player:
            self._player.pause()
            return "Music paused, Sir."
        return "No player active, Sir."

    def _resume(self, params):
        if self._player:
            self._player.play()
            return "Resuming playback, Sir."
        return "No player active, Sir."

    def _stop(self, params):
        if self._player:
            self._player.stop()
            self._current_track = None
            return "Music stopped, Sir."
        return "No player active, Sir."

    def _volume(self, params):
        value = params.get("value", 50)
        if self._player:
            self._player.audio_set_volume(int(value))
            return f"Music volume set to {value}%, Sir."
        return "No player active, Sir."

    def _status(self, params):
        if self._current_track:
            return f"Currently playing: {self._current_track}, Sir."
        return "No music is playing, Sir."

    def _search_youtube(self, query: str) -> str:
        """Search YouTube and return first video URL."""
        try:
            result = subprocess.run(
                ["yt-dlp", f"ytsearch1:{query}", "--get-url", "--no-playlist", "-f", "bestaudio"],
                capture_output=True, text=True, timeout=15
            )
            url = result.stdout.strip().split("\n")[0]
            return url if url.startswith("http") else None
        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return None

    def _get_stream_url(self, url: str) -> str:
        """Get direct audio stream URL via yt-dlp."""
        try:
            result = subprocess.run(
                ["yt-dlp", url, "--get-url", "-f", "bestaudio/best"],
                capture_output=True, text=True, timeout=15
            )
            stream = result.stdout.strip().split("\n")[0]
            return stream if stream.startswith("http") else url
        except Exception:
            return url
