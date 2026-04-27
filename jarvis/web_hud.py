"""
===========================================================
J.A.R.V.I.S. — Web HUD (Flask + WebSocket)
===========================================================
Optional browser-based Heads-Up Display using Flask and Socket.IO.
Runs on localhost:5000 and connects to the main JARVIS event loop.
===========================================================
"""

import logging
import threading
from typing import Callable

logger = logging.getLogger("jarvis.web_hud")

try:
    from flask import Flask, render_template, request
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logger.warning("Flask or Flask-SocketIO not installed — Web HUD disabled")


class WebHUD:
    """Browser-based HUD server using Flask and WebSockets."""

    def __init__(self, on_text_input: Callable = None):
        self.on_text_input = on_text_input
        self._app = None
        self._socketio = None
        self._thread = None
        self._running = False

        if FLASK_AVAILABLE:
            self._init_app()

    def _init_app(self):
        """Initialize the Flask application and SocketIO."""
        import os
        from jarvis.config import BASE_DIR
        template_dir = os.path.join(BASE_DIR, 'templates')
        self._app = Flask(__name__, template_folder=template_dir)
        self._app.config['SECRET_KEY'] = 'jarvis_secret_key'
        
        # Suppress Flask default logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        self._socketio = SocketIO(self._app, cors_allowed_origins="*", async_mode='threading')

        # Define routes
        @self._app.route('/')
        def index():
            return render_template('index.html')

        # Define WebSocket events
        @self._socketio.on('connect')
        def handle_connect():
            logger.info("Web HUD client connected")
            emit('status_update', {'status': 'READY', 'color': '#00FF88'})

        @self._socketio.on('command')
        def handle_command(data):
            command = data.get('text', '').strip()
            if command and self.on_text_input:
                logger.info(f"Web HUD command: {command}")
                # Emit command back to show it in UI
                self.update_command(command)
                self.update_status("PROCESSING...")
                
                # Process asynchronously so we don't block the socket
                threading.Thread(
                    target=self.on_text_input, 
                    args=(command,), 
                    daemon=True
                ).start()

    def start(self, port=5000):
        """Start the Web HUD server in a background thread."""
        if not FLASK_AVAILABLE:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_server,
            args=(port,),
            daemon=True
        )
        self._thread.start()
        logger.info(f"Web HUD running at http://localhost:{port}")

    def _run_server(self, port):
        try:
            self._socketio.run(self._app, host='127.0.0.1', port=port, allow_unsafe_werkzeug=True)
        except Exception as e:
            logger.error(f"Web HUD server error: {e}")

    def stop(self):
        """Stop the Web HUD server."""
        self._running = False
        # SocketIO doesn't have a clean stop method in threading mode,
        # but the daemon thread will die when the main process exits.

    # ── Methods to send updates to connected clients ──

    def update_status(self, text: str, success: bool = True):
        """Update the status label."""
        if not FLASK_AVAILABLE or not self._running:
            return
        color = '#00FF88' if success else '#FF3366'
        if text in ["PROCESSING...", "LISTENING...", "SPEAKING..."]:
            color = '#00D4FF'
        self._socketio.emit('status_update', {'status': text, 'color': color})

    def update_response(self, text: str):
        """Show JARVIS response."""
        if not FLASK_AVAILABLE or not self._running:
            return
        self._socketio.emit('response', {'text': text})

    def update_command(self, text: str):
        """Add command to history."""
        if not FLASK_AVAILABLE or not self._running:
            return
        self._socketio.emit('command_history', {'text': text})

    def set_listening(self, active: bool):
        """Toggle listening visualizer."""
        if not FLASK_AVAILABLE or not self._running:
            return
        self._socketio.emit('set_active', {'active': active, 'type': 'listening'})

    def set_speaking(self, active: bool):
        """Toggle speaking visualizer."""
        if not FLASK_AVAILABLE or not self._running:
            return
        self._socketio.emit('set_active', {'active': active, 'type': 'speaking'})

    def update_system_stats(self, stats: dict):
        """Update CPU/RAM stats."""
        if not FLASK_AVAILABLE or not self._running:
            return
        self._socketio.emit('stats_update', stats)

    def boot_step(self, module: str, success: bool):
        """Add a boot sequence step."""
        if not FLASK_AVAILABLE or not self._running:
            return
        self._socketio.emit('boot_step', {'module': module, 'success': success})
