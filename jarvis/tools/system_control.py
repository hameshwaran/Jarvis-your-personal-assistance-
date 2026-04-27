"""
===========================================================
J.A.R.V.I.S. — System Control Tool
===========================================================
Full OS control using pyautogui, subprocess, psutil, win32api.
Open/close apps, volume control, screenshots, system info,
file operations, keyboard/mouse automation.
===========================================================
"""

import os
import sys
import time
import platform
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jarvis.tools.system_control")


class SystemControlTool:
    """Control the operating system — apps, volume, screenshots, system info."""

    def __init__(self, memory=None):
        self.memory = memory
        self._is_windows = platform.system() == "Windows"

    def execute(self, params: dict) -> str:
        """
        Execute a system control action.
        
        Params:
            action (str): The action to perform
            target (str): Target app/file/path
            value (str):  Value for the action (volume level, text, etc.)
        """
        action = params.get("action", "").lower().strip()
        target = params.get("target", "")
        value = params.get("value", "")

        action_map = {
            "open": self._open_app,
            "open_app": self._open_app,
            "open_file": self._open_file,
            "close": self._close_app,
            "close_app": self._close_app,
            "volume": self._set_volume,
            "set_volume": self._set_volume,
            "volume_up": lambda t, v: self._set_volume(t, "up"),
            "volume_down": lambda t, v: self._set_volume(t, "down"),
            "mute": lambda t, v: self._set_volume(t, "mute"),
            "screenshot": self._take_screenshot,
            "system_info": lambda t, v: self._get_system_info(),
            "system_status": lambda t, v: self._get_system_info(),
            "lock": lambda t, v: self._lock_screen(),
            "shutdown": self._schedule_shutdown,
            "restart": lambda t, v: self._restart(),
            "type": self._type_text,
            "type_text": self._type_text,
            "file_create": self._create_file,
            "file_delete": self._delete_file,
            "file_move": self._move_file,
            "brightness": self._set_brightness,
            "time": lambda t, v: self._get_time(t),
            "world_clock": lambda t, v: self._get_time(t),
            "open_url": self._open_url,
            "search": self._browser_search,
        }

        handler = action_map.get(action)
        if handler:
            try:
                return handler(target, value)
            except Exception as e:
                logger.error(f"System control action '{action}' failed: {e}")
                return f"Action '{action}' failed, Sir: {str(e)}"
        else:
            return f"Unknown system action: '{action}', Sir. Available: {', '.join(action_map.keys())}"

    # ================================================================
    # Application Control
    # ================================================================

    def _open_app(self, target: str, value: str) -> str:
        """Open an application by name."""
        if not target:
            return "Please specify which application to open, Sir."

        app_map = {
            "chrome": "chrome",
            "google chrome": "chrome",
            "firefox": "firefox",
            "edge": "msedge",
            "vscode": "code",
            "vs code": "code",
            "visual studio code": "code",
            "notepad": "notepad",
            "calculator": "calc",
            "terminal": "wt" if self._is_windows else "gnome-terminal",
            "cmd": "cmd",
            "powershell": "powershell",
            "explorer": "explorer",
            "file explorer": "explorer",
            "spotify": "spotify",
            "discord": "discord",
            "slack": "slack",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "paint": "mspaint",
            "task manager": "taskmgr",
            "settings": "ms-settings:" if self._is_windows else "gnome-control-center",
            "whatsapp": "whatsapp:",
            "instagram": "instagram:",
            "messenger": "ms-messenger:",
            "facebook": "fb:",
            "netflix": "netflix:",
            "brave": "brave",
            "brave browser": "brave",
        }

        app_cmd = app_map.get(target.lower(), target)

        try:
            if self._is_windows:
                # Handle Windows URIs (whatsapp:, ms-settings:, etc.)
                if ":" in app_cmd:
                    subprocess.Popen(["start", app_cmd], shell=True)
                else:
                    os.startfile(app_cmd)
            else:
                subprocess.Popen([app_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opening {target}, Sir."
        except FileNotFoundError:
            # Try shell command
            try:
                subprocess.Popen(f"start {app_cmd}" if self._is_windows else app_cmd, shell=True)
                return f"Opening {target}, Sir."
            except Exception as e:
                return f"I couldn't find '{target}' on your system, Sir."

    def _open_url(self, target: str, value: str) -> str:
        """Open a URL in the default browser (or Brave if specified)."""
        url = target or value
        if not url:
            return "Please specify a URL to open, Sir."
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            
        try:
            import webbrowser
            # Try to find Brave specifically if possible, otherwise use default
            webbrowser.open(url)
            return f"Opening {url}, Sir."
        except Exception as e:
            return f"Failed to open URL, Sir: {e}"

    def _browser_search(self, target: str, value: str) -> str:
        """Search the web using the browser."""
        query = target or value
        if not query:
            return "What would you like me to search for, Sir?"
            
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return self._open_url(url, "")

    def _open_file(self, target: str, value: str) -> str:
        """Search for and open a file by name."""
        if not target:
            return "Please specify the file name to open, Sir."
            
        path = Path(target)
        if path.exists() and path.is_file():
            try:
                if self._is_windows:
                    os.startfile(path)
                else:
                    subprocess.Popen(["xdg-open", str(path)])
                return f"Opening file {path.name}, Sir."
            except Exception as e:
                return f"Failed to open file: {e}"

        # Search in common directories
        home = Path.home()
        search_dirs = [
            home / "Documents",
            home / "Desktop",
            home / "Downloads",
            home / "OneDrive" / "Documents",
            home / "OneDrive" / "Desktop",
        ]
        
        target_lower = target.lower()
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            try:
                for root, _, files in os.walk(search_dir):
                    # Limit depth to avoid hanging
                    if root.count(os.sep) - str(search_dir).count(os.sep) > 3:
                        continue
                    for file in files:
                        if target_lower in file.lower() or target_lower == Path(file).stem.lower():
                            file_path = os.path.join(root, file)
                            try:
                                if self._is_windows:
                                    os.startfile(file_path)
                                else:
                                    subprocess.Popen(["xdg-open", file_path])
                                return f"Opening file {file}, Sir."
                            except Exception as e:
                                return f"Found the file {file} but couldn't open it, Sir: {e}"
            except Exception:
                continue

        return f"I couldn't find a file matching '{target}' in your common directories, Sir."

    def _close_app(self, target: str, value: str) -> str:
        """Close an application by name."""
        if not target:
            return "Please specify which application to close, Sir."

        try:
            import psutil
            target_lower = target.lower()
            closed = False

            for proc in psutil.process_iter(["name", "pid"]):
                proc_name = proc.info["name"].lower()
                if target_lower in proc_name:
                    proc.terminate()
                    closed = True

            if closed:
                return f"{target} has been closed, Sir."
            else:
                return f"I couldn't find a running instance of '{target}', Sir."
        except Exception as e:
            return f"Failed to close '{target}', Sir: {str(e)}"

    # ================================================================
    # Volume Control
    # ================================================================

    def _set_volume(self, target: str, value: str) -> str:
        """Set, increase, decrease, or mute system volume."""
        if self._is_windows:
            return self._set_volume_windows(value or target)
        else:
            return self._set_volume_linux(value or target)

    def _set_volume_windows(self, value: str) -> str:
        """Control volume on Windows."""
        try:
            import pyautogui

            if value.lower() == "mute":
                pyautogui.press("volumemute")
                return "Volume muted, Sir."
            elif value.lower() == "up":
                for _ in range(5):
                    pyautogui.press("volumeup")
                return "Volume increased, Sir."
            elif value.lower() == "down":
                for _ in range(5):
                    pyautogui.press("volumedown")
                return "Volume decreased, Sir."
            else:
                # Try to set to specific percentage
                try:
                    level = int(value.replace("%", ""))
                    # Use nircmd if available, otherwise approximate with key presses
                    subprocess.run(
                        ["powershell", "-c",
                         f"$obj = New-Object -ComObject WScript.Shell; "
                         f"for($i=0;$i -lt 50;$i++){{$obj.SendKeys([char]174)}}; "
                         f"for($i=0;$i -lt {level // 2};$i++){{$obj.SendKeys([char]175)}}"],
                        capture_output=True, timeout=10
                    )
                    return f"Volume set to approximately {level}%, Sir."
                except ValueError:
                    return f"Invalid volume value: {value}, Sir."
        except Exception as e:
            return f"Volume control failed, Sir: {str(e)}"

    def _set_volume_linux(self, value: str) -> str:
        """Control volume on Linux using pactl/amixer."""
        try:
            if value.lower() == "mute":
                subprocess.run(["amixer", "set", "Master", "toggle"], capture_output=True)
                return "Volume muted, Sir."
            elif value.lower() == "up":
                subprocess.run(["amixer", "set", "Master", "10%+"], capture_output=True)
                return "Volume increased, Sir."
            elif value.lower() == "down":
                subprocess.run(["amixer", "set", "Master", "10%-"], capture_output=True)
                return "Volume decreased, Sir."
            else:
                level = int(value.replace("%", ""))
                subprocess.run(["amixer", "set", "Master", f"{level}%"], capture_output=True)
                return f"Volume set to {level}%, Sir."
        except Exception as e:
            return f"Volume control failed, Sir: {str(e)}"

    # ================================================================
    # Screenshots
    # ================================================================

    def _take_screenshot(self, target: str, value: str) -> str:
        """Take a screenshot and save it."""
        try:
            import pyautogui
            from jarvis.config import DATA_DIR

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = DATA_DIR / filename

            screenshot = pyautogui.screenshot()
            screenshot.save(str(filepath))

            return f"Screenshot saved as {filename}, Sir."
        except Exception as e:
            return f"Screenshot failed, Sir: {str(e)}"

    # ================================================================
    # System Information
    # ================================================================

    def _get_system_info(self) -> str:
        """Get comprehensive system status."""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time

            # Battery info (if available)
            battery_info = ""
            try:
                battery = psutil.sensors_battery()
                if battery:
                    battery_info = f"\n  Battery: {battery.percent}% {'(Charging)' if battery.power_plugged else '(On battery)'}"
            except Exception:
                pass

            # Network info
            net = psutil.net_io_counters()

            cpu_freq = psutil.cpu_freq()
            freq_info = f" @ {cpu_freq.current:.0f}MHz" if cpu_freq else ""
            cpu_count = psutil.cpu_count(logical=True)
            
            # Top processes by Memory
            top_procs = []
            try:
                for proc in sorted(psutil.process_iter(['name', 'memory_percent']), 
                                   key=lambda p: p.info.get('memory_percent') or 0, 
                                   reverse=True)[:3]:
                    top_procs.append(f"{proc.info['name']} ({proc.info['memory_percent']:.1f}%)")
            except Exception:
                top_procs.append("Unavailable")
            top_procs_str = ", ".join(top_procs)

            return (
                f"System Status Report:\n"
                f"  CPU: {cpu_count} cores, Usage: {cpu_percent}%{freq_info}\n"
                f"  RAM: {memory.percent}% used ({memory.used // (1024**3):.1f} / {memory.total // (1024**3):.1f} GB)\n"
                f"  Disk: {disk.percent}% used ({disk.used // (1024**3):.0f} / {disk.total // (1024**3):.0f} GB)\n"
                f"  Top Processes: {top_procs_str}\n"
                f"  Uptime: {str(uptime).split('.')[0]}\n"
                f"  Network: Sent {net.bytes_sent // (1024**2):.0f} MB / Received {net.bytes_recv // (1024**2):.0f} MB"
                f"{battery_info}\n"
                f"  OS: {platform.system()} {platform.release()}\n"
                f"  Python: {platform.python_version()}"
            )
        except Exception as e:
            return f"System info unavailable, Sir: {str(e)}"

    # ================================================================
    # Lock / Shutdown / Restart
    # ================================================================

    def _lock_screen(self) -> str:
        """Lock the screen."""
        try:
            if self._is_windows:
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            else:
                subprocess.run(["loginctl", "lock-session"])
            return "Screen locked, Sir."
        except Exception as e:
            return f"Failed to lock screen, Sir: {str(e)}"

    def _schedule_shutdown(self, target: str, value: str) -> str:
        """Schedule a system shutdown."""
        try:
            minutes = int(value) if value else 0
            seconds = minutes * 60

            if self._is_windows:
                subprocess.run(["shutdown", "/s", "/t", str(seconds)])
            else:
                subprocess.run(["shutdown", "-h", f"+{minutes}"])

            if minutes > 0:
                return f"Shutdown scheduled in {minutes} minutes, Sir."
            else:
                return "Initiating shutdown now, Sir."
        except Exception as e:
            return f"Shutdown scheduling failed, Sir: {str(e)}"

    def _restart(self) -> str:
        """Restart the system."""
        try:
            if self._is_windows:
                subprocess.run(["shutdown", "/r", "/t", "5"])
            else:
                subprocess.run(["shutdown", "-r", "+0"])
            return "Restarting the system in 5 seconds, Sir."
        except Exception as e:
            return f"Restart failed, Sir: {str(e)}"

    # ================================================================
    # Typing & Input
    # ================================================================

    def _type_text(self, target: str, value: str) -> str:
        """Type text using pyautogui."""
        text = value or target
        if not text:
            return "No text specified to type, Sir."
        try:
            import pyautogui
            time.sleep(0.5)  # Brief pause to let user focus the target window
            pyautogui.typewrite(text, interval=0.02)
            return f"Text typed, Sir."
        except Exception as e:
            return f"Typing failed, Sir: {str(e)}"

    # ================================================================
    # File Operations
    # ================================================================

    def _create_file(self, target: str, value: str) -> str:
        """Create a file with optional content."""
        if not target:
            return "Please specify the file path, Sir."
        try:
            path = Path(target)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value or "")
            return f"File created: {target}, Sir."
        except Exception as e:
            return f"File creation failed, Sir: {str(e)}"

    def _delete_file(self, target: str, value: str) -> str:
        """Delete a file (with safety checks)."""
        if not target:
            return "Please specify the file to delete, Sir."
        try:
            path = Path(target)
            if not path.exists():
                return f"File not found: {target}, Sir."
            if path.is_dir():
                return "I won't delete directories for safety, Sir. Please use file explorer."
            path.unlink()
            return f"File deleted: {target}, Sir."
        except Exception as e:
            return f"File deletion failed, Sir: {str(e)}"

    def _move_file(self, target: str, value: str) -> str:
        """Move/rename a file."""
        if not target or not value:
            return "Please specify source and destination paths, Sir."
        try:
            import shutil
            shutil.move(target, value)
            return f"File moved from {target} to {value}, Sir."
        except Exception as e:
            return f"File move failed, Sir: {str(e)}"

    # ================================================================
    # Display
    # ================================================================

    def _set_brightness(self, target: str, value: str) -> str:
        """Set screen brightness."""
        try:
            level = int(value or target)
            if self._is_windows:
                subprocess.run(
                    ["powershell", "-c",
                     f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"],
                    capture_output=True
                )
            else:
                subprocess.run(["xrandr", "--output", "eDP-1", "--brightness", str(level / 100)])
            return f"Brightness set to {level}%, Sir."
        except Exception as e:
            return f"Brightness control failed, Sir: {str(e)}"

    # ================================================================
    # World Clock
    # ================================================================

    def _get_time(self, location: str) -> str:
        """Get current time, optionally for a different timezone."""
        from datetime import timezone, timedelta
        import json

        if not location:
            now = datetime.now()
            return f"The current time is {now.strftime('%I:%M %p on %A, %B %d, %Y')}, Sir."

        # Common timezone mappings
        tz_map = {
            "tokyo": 9, "japan": 9, "london": 0, "uk": 0, "new york": -5,
            "nyc": -5, "los angeles": -8, "la": -8, "paris": 1, "berlin": 1,
            "sydney": 11, "dubai": 4, "singapore": 8, "hong kong": 8,
            "moscow": 3, "delhi": 5.5, "mumbai": 5.5, "chennai": 5.5,
            "beijing": 8, "shanghai": 8, "seoul": 9, "bangkok": 7,
        }

        offset = tz_map.get(location.lower())
        if offset is not None:
            tz = timezone(timedelta(hours=offset))
            now = datetime.now(tz)
            return f"The current time in {location.title()} is {now.strftime('%I:%M %p, %A')}, Sir."
        else:
            now = datetime.now()
            return f"I don't have timezone data for '{location}', Sir. Local time is {now.strftime('%I:%M %p')}."
