"""
===========================================================
J.A.R.V.I.S. — Messaging Tool
===========================================================
Automates sending messages via WhatsApp Desktop or Web.
Uses pyautogui for UI interaction.
===========================================================
"""

import time
import logging
import platform
import subprocess
import pyautogui
from typing import Optional

logger = logging.getLogger("jarvis.tools.messaging")

class MessagingTool:
    """Tool for sending messages through various platforms."""

    def __init__(self, memory=None):
        self.memory = memory
        self._is_windows = platform.system() == "Windows"

    def execute(self, params: dict) -> str:
        """
        Send a message.
        
        Params:
            to (str): Recipient name
            body (str): Message content
            platform (str): 'whatsapp' (default)
        """
        recipient = params.get("to", "")
        message = params.get("body", params.get("message", ""))
        target_platform = params.get("platform", "whatsapp").lower()

        if not recipient or not message:
            return "Sir, I need both a recipient and a message body."

        if target_platform == "whatsapp":
            return self._send_whatsapp(recipient, message)
        else:
            return f"Sir, I currently only support messaging via WhatsApp. '{target_platform}' is not yet integrated."

    def _send_whatsapp(self, recipient: str, message: str) -> str:
        """Automate sending a WhatsApp message."""
        try:
            logger.info(f"Sending WhatsApp message to {recipient}")
            
            # 1. Open WhatsApp
            if self._is_windows:
                subprocess.Popen(["start", "whatsapp:"], shell=True)
            else:
                return "WhatsApp automation is currently only optimized for Windows, Sir."
            
            # Wait for app to open and focus
            time.sleep(3)
            
            # 2. Search for recipient
            # Ctrl+F is the standard search hotkey in WhatsApp Desktop
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)
            pyautogui.typewrite(recipient)
            time.sleep(1.5)
            pyautogui.press('enter')
            time.sleep(1)
            
            # 3. Type message
            pyautogui.typewrite(message)
            time.sleep(0.5)
            pyautogui.press('enter')
            
            return f"Message sent to {recipient}, Sir: '{message}'"
            
        except Exception as e:
            logger.error(f"WhatsApp automation failed: {e}")
            return f"Failed to send message to {recipient}, Sir. {str(e)}"

    def _send_whatsapp_web(self, recipient: str, message: str) -> str:
        """Fallback: Send via WhatsApp Web in browser."""
        # Not implemented yet, but could use webbrowser.open(f"https://web.whatsapp.com/send?phone={phone}&text={text}")
        pass
