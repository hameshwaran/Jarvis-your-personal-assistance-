"""
===========================================================
J.A.R.V.I.S. — HUD (Heads-Up Display)
===========================================================
PyQt5 overlay with Iron Man aesthetics:
  - Dark blue (#0A1628) + cyan glow (#00D4FF)
  - Audio waveform visualizer
  - Typing effect for responses
  - System status bar
  - Command history panel
  - Boot animation sequence
===========================================================
"""

import sys
import time
import math
import logging
import threading
from datetime import datetime
from typing import Optional

logger = logging.getLogger("jarvis.hud")

# Try PyQt5 import
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QTextEdit, QFrame, QSystemTrayIcon, QMenu, QAction,
        QGraphicsDropShadowEffect, QScrollArea, QLineEdit, QPushButton
    )
    from PyQt5.QtCore import (
        Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation,
        QEasingCurve, QThread, QSize, QPoint
    )
    from PyQt5.QtGui import (
        QFont, QColor, QPainter, QPainterPath, QLinearGradient,
        QRadialGradient, QPen, QBrush, QIcon, QPixmap, QFontDatabase
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    logger.warning("PyQt5 not installed — HUD disabled")

from jarvis.config import (
    HUD_BG_COLOR, HUD_ACCENT_COLOR, HUD_TEXT_COLOR,
    HUD_WARNING_COLOR, HUD_SUCCESS_COLOR, HUD_DANGER_COLOR,
    HUD_SECONDARY_COLOR, HUD_FONT_FAMILY, HUD_OPACITY,
    HUD_WIDTH, HUD_HEIGHT, USER_TITLE
)


class SignalBridge(QObject):
    """Thread-safe signal bridge for updating HUD from other threads."""
    update_status = pyqtSignal(str)
    update_response = pyqtSignal(str)
    update_command = pyqtSignal(str)
    update_system_stats = pyqtSignal(dict)
    boot_step = pyqtSignal(str, bool)  # module_name, success
    set_listening = pyqtSignal(bool)
    set_speaking = pyqtSignal(bool)


if PYQT_AVAILABLE:

    class ArcReactorWidget(QWidget):
        """Animated arc reactor / audio visualizer widget."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setFixedSize(180, 180)
            self._phase = 0.0
            self._intensity = 0.3
            self._is_active = False
            self._ring_angles = [0, 0, 0]

            self._timer = QTimer(self)
            self._timer.timeout.connect(self._animate)
            self._timer.start(33)  # ~30 FPS

        def set_active(self, active: bool):
            self._is_active = active
            self._intensity = 0.9 if active else 0.3

        def _animate(self):
            self._phase += 0.05
            if self._is_active:
                self._ring_angles[0] += 2
                self._ring_angles[1] -= 1.5
                self._ring_angles[2] += 1
            else:
                self._ring_angles[0] += 0.3
                self._ring_angles[1] -= 0.2
                self._ring_angles[2] += 0.15
            self.update()

        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            cx, cy = self.width() // 2, self.height() // 2

            # Outer glow
            glow = QRadialGradient(cx, cy, 85)
            glow.setColorAt(0, QColor(0, 212, 255, int(60 * self._intensity)))
            glow.setColorAt(0.7, QColor(0, 212, 255, int(20 * self._intensity)))
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(cx - 85, cy - 85, 170, 170)

            # Ring 1 — outer
            pen = QPen(QColor(0, 212, 255, int(150 * self._intensity)), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self._ring_angles[0])
            for i in range(8):
                angle = i * 45
                x1 = 65 * math.cos(math.radians(angle))
                y1 = 65 * math.sin(math.radians(angle))
                x2 = 75 * math.cos(math.radians(angle))
                y2 = 75 * math.sin(math.radians(angle))
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.restore()

            # Ring 2 — middle dashed
            pen = QPen(QColor(0, 180, 220, int(100 * self._intensity)), 1.5, Qt.DashLine)
            painter.setPen(pen)
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self._ring_angles[1])
            painter.drawEllipse(-50, -50, 100, 100)
            painter.restore()

            # Ring 3 — inner
            pen = QPen(QColor(0, 212, 255, int(200 * self._intensity)), 2)
            painter.setPen(pen)
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self._ring_angles[2])
            painter.drawEllipse(-35, -35, 70, 70)

            # Inner segments
            for i in range(6):
                angle = i * 60
                x1 = 25 * math.cos(math.radians(angle))
                y1 = 25 * math.sin(math.radians(angle))
                x2 = 33 * math.cos(math.radians(angle))
                y2 = 33 * math.sin(math.radians(angle))
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.restore()

            # Center core
            core_glow = QRadialGradient(cx, cy, 18)
            core_glow.setColorAt(0, QColor(200, 240, 255, int(255 * self._intensity)))
            core_glow.setColorAt(0.5, QColor(0, 212, 255, int(180 * self._intensity)))
            core_glow.setColorAt(1, QColor(0, 100, 150, int(50 * self._intensity)))
            painter.setBrush(QBrush(core_glow))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(cx - 18, cy - 18, 36, 36)

            # Pulsing inner dot
            pulse = 0.7 + 0.3 * math.sin(self._phase * 3)
            painter.setBrush(QColor(255, 255, 255, int(200 * pulse)))
            r = int(6 * pulse)
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

            painter.end()


    class JarvisHUD(QMainWindow):
        """Main HUD window — Iron Man inspired overlay."""

        def __init__(self, on_text_input: callable = None):
            super().__init__()
            self.on_text_input = on_text_input
            self.signals = SignalBridge()
            self._command_history = []
            self._typing_text = ""
            self._typing_index = 0
            self._boot_complete = False

            self._setup_window()
            self._build_ui()
            self._connect_signals()
            self._setup_tray()

            # Typing animation timer
            self._typing_timer = QTimer(self)
            self._typing_timer.timeout.connect(self._typing_tick)

        def _setup_window(self):
            """Configure window properties."""
            self.setWindowTitle("J.A.R.V.I.S.")
            self.setFixedSize(HUD_WIDTH, HUD_HEIGHT)
            self.setWindowFlags(
                Qt.FramelessWindowHint |
                Qt.WindowStaysOnTopHint |
                Qt.Tool
            )
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setWindowOpacity(HUD_OPACITY)

            # Position at top-right of screen
            screen = QApplication.primaryScreen().geometry()
            self.move(screen.width() - HUD_WIDTH - 20, 40)

        def _build_ui(self):
            """Construct the HUD interface."""
            central = QWidget()
            self.setCentralWidget(central)
            central.setStyleSheet(f"""
                QWidget {{
                    background-color: {HUD_BG_COLOR};
                    color: {HUD_TEXT_COLOR};
                    font-family: 'Consolas', 'Courier New', monospace;
                }}
            """)

            layout = QVBoxLayout(central)
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(10)

            # ── Header ──────────────────────────────
            header = QHBoxLayout()
            title = QLabel("J.A.R.V.I.S.")
            title.setStyleSheet(f"""
                font-size: 18px; font-weight: bold;
                color: {HUD_ACCENT_COLOR};
                letter-spacing: 4px;
            """)
            header.addWidget(title)
            header.addStretch()

            self._status_dot = QLabel("●")
            self._status_dot.setStyleSheet(f"font-size: 14px; color: {HUD_SUCCESS_COLOR};")
            header.addWidget(self._status_dot)
            layout.addLayout(header)

            # Separator
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet(f"background-color: {HUD_ACCENT_COLOR}; max-height: 1px;")
            layout.addWidget(sep)

            # ── Arc Reactor ─────────────────────────
            reactor_container = QHBoxLayout()
            reactor_container.addStretch()
            self._reactor = ArcReactorWidget()
            reactor_container.addWidget(self._reactor)
            reactor_container.addStretch()
            layout.addLayout(reactor_container)

            # ── Status Label ────────────────────────
            self._status_label = QLabel("INITIALIZING...")
            self._status_label.setAlignment(Qt.AlignCenter)
            self._status_label.setStyleSheet(f"""
                font-size: 11px; color: {HUD_ACCENT_COLOR};
                letter-spacing: 2px; padding: 5px;
            """)
            layout.addWidget(self._status_label)

            # ── Response Area ───────────────────────
            self._response_area = QTextEdit()
            self._response_area.setReadOnly(True)
            self._response_area.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {HUD_SECONDARY_COLOR};
                    border: 1px solid {HUD_ACCENT_COLOR}40;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 12px;
                    color: {HUD_TEXT_COLOR};
                    selection-background-color: {HUD_ACCENT_COLOR}40;
                }}
            """)
            self._response_area.setMaximumHeight(180)
            layout.addWidget(self._response_area)

            # ── System Stats Bar ────────────────────
            stats_layout = QHBoxLayout()
            self._cpu_label = QLabel("CPU: --%")
            self._ram_label = QLabel("RAM: --%")
            self._time_label = QLabel("--:--")

            for lbl in [self._cpu_label, self._ram_label, self._time_label]:
                lbl.setStyleSheet(f"""
                    font-size: 10px; color: {HUD_ACCENT_COLOR}90;
                    padding: 3px 6px;
                    background-color: {HUD_SECONDARY_COLOR};
                    border-radius: 3px;
                """)
                stats_layout.addWidget(lbl)

            layout.addLayout(stats_layout)

            # ── Command History ─────────────────────
            history_label = QLabel("COMMAND LOG")
            history_label.setStyleSheet(f"""
                font-size: 9px; color: {HUD_ACCENT_COLOR}70;
                letter-spacing: 2px; margin-top: 5px;
            """)
            layout.addWidget(history_label)

            self._history_area = QTextEdit()
            self._history_area.setReadOnly(True)
            self._history_area.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {HUD_SECONDARY_COLOR};
                    border: 1px solid {HUD_ACCENT_COLOR}20;
                    border-radius: 4px;
                    padding: 6px;
                    font-size: 10px;
                    color: {HUD_TEXT_COLOR}90;
                }}
            """)
            self._history_area.setMaximumHeight(100)
            layout.addWidget(self._history_area)

            # ── Text Input ──────────────────────────
            input_layout = QHBoxLayout()
            self._text_input = QLineEdit()
            self._text_input.setPlaceholderText("Type a command...")
            self._text_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {HUD_SECONDARY_COLOR};
                    border: 1px solid {HUD_ACCENT_COLOR}40;
                    border-radius: 4px;
                    padding: 8px;
                    font-size: 12px;
                    color: {HUD_TEXT_COLOR};
                }}
                QLineEdit:focus {{
                    border-color: {HUD_ACCENT_COLOR};
                }}
            """)
            self._text_input.returnPressed.connect(self._on_enter)
            input_layout.addWidget(self._text_input)

            send_btn = QPushButton("►")
            send_btn.setFixedSize(36, 36)
            send_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {HUD_ACCENT_COLOR}30;
                    border: 1px solid {HUD_ACCENT_COLOR};
                    border-radius: 4px;
                    color: {HUD_ACCENT_COLOR};
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {HUD_ACCENT_COLOR}60;
                }}
            """)
            send_btn.clicked.connect(self._on_enter)
            input_layout.addWidget(send_btn)

            layout.addLayout(input_layout)

            # ── Stats update timer ──────────────────
            self._stats_timer = QTimer(self)
            self._stats_timer.timeout.connect(self._update_stats)
            self._stats_timer.start(2000)

        def _connect_signals(self):
            """Connect thread-safe signals."""
            self.signals.update_status.connect(self._set_status)
            self.signals.update_response.connect(self._show_response)
            self.signals.update_command.connect(self._add_command)
            self.signals.boot_step.connect(self._boot_step)
            self.signals.set_listening.connect(self._set_listening)
            self.signals.set_speaking.connect(self._set_speaking)

        def _setup_tray(self):
            """Setup system tray icon."""
            try:
                self._tray = QSystemTrayIcon(self)
                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor(HUD_ACCENT_COLOR))
                self._tray.setIcon(QIcon(pixmap))

                menu = QMenu()
                show_action = QAction("Show/Hide", self)
                show_action.triggered.connect(self._toggle_visibility)
                menu.addAction(show_action)

                quit_action = QAction("Quit JARVIS", self)
                quit_action.triggered.connect(QApplication.quit)
                menu.addAction(quit_action)

                self._tray.setContextMenu(menu)
                self._tray.activated.connect(lambda r: self._toggle_visibility() if r == QSystemTrayIcon.Trigger else None)
                self._tray.show()
            except Exception as e:
                logger.debug(f"System tray setup failed: {e}")

        # ── UI Update Methods ───────────────────────────

        def _set_status(self, text: str):
            self._status_label.setText(text)

        def _show_response(self, text: str):
            """Show response with typing animation."""
            self._typing_text = text
            self._typing_index = 0
            self._response_area.clear()
            self._typing_timer.start(20)  # 20ms per character

        def _typing_tick(self):
            """Add one character at a time for typing effect."""
            if self._typing_index < len(self._typing_text):
                self._response_area.setPlainText(
                    self._typing_text[:self._typing_index + 1]
                )
                self._typing_index += 1
                # Auto-scroll
                scrollbar = self._response_area.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
            else:
                self._typing_timer.stop()

        def _add_command(self, cmd: str):
            """Add command to history."""
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._command_history.append(f"[{timestamp}] {cmd}")
            if len(self._command_history) > 10:
                self._command_history.pop(0)
            self._history_area.setPlainText("\n".join(self._command_history))
            scrollbar = self._history_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        def _boot_step(self, module: str, success: bool):
            """Show a boot step in the response area."""
            icon = "✓" if success else "✗"
            color = HUD_SUCCESS_COLOR if success else HUD_DANGER_COLOR
            current = self._response_area.toPlainText()
            self._response_area.setPlainText(
                current + f"  [{icon}] {module}\n"
            )

        def _set_listening(self, active: bool):
            if active:
                self._reactor.set_active(True)
                self._status_label.setText("LISTENING...")
                self._status_dot.setStyleSheet(f"font-size: 14px; color: {HUD_ACCENT_COLOR};")
            else:
                self._reactor.set_active(False)
                self._status_label.setText("READY")
                self._status_dot.setStyleSheet(f"font-size: 14px; color: {HUD_SUCCESS_COLOR};")

        def _set_speaking(self, active: bool):
            if active:
                self._status_label.setText("SPEAKING...")
                self._reactor.set_active(True)
            else:
                self._status_label.setText("READY")
                self._reactor.set_active(False)

        def _update_stats(self):
            """Update system stats in the status bar."""
            try:
                import psutil
                self._cpu_label.setText(f"CPU: {psutil.cpu_percent():.0f}%")
                self._ram_label.setText(f"RAM: {psutil.virtual_memory().percent:.0f}%")
            except Exception:
                pass
            self._time_label.setText(datetime.now().strftime("%H:%M:%S"))

        def _on_enter(self):
            """Handle text input."""
            text = self._text_input.text().strip()
            if text:
                self._text_input.clear()
                self._add_command(text)
                if self.on_text_input:
                    threading.Thread(
                        target=self.on_text_input, args=(text,), daemon=True
                    ).start()

        def _toggle_visibility(self):
            if self.isVisible():
                self.hide()
            else:
                self.show()

        # ── Window Dragging ─────────────────────────────
        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

        def mouseMoveEvent(self, event):
            if event.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos'):
                self.move(event.globalPos() - self._drag_pos)
                event.accept()

        def paintEvent(self, event):
            """Draw rounded rectangle background."""
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)

            # Gradient background
            gradient = QLinearGradient(0, 0, 0, self.height())
            gradient.setColorAt(0, QColor(HUD_BG_COLOR))
            gradient.setColorAt(1, QColor(8, 16, 30))
            painter.fillPath(path, QBrush(gradient))

            # Border
            painter.setPen(QPen(QColor(HUD_ACCENT_COLOR + "40"), 1))
            painter.drawPath(path)
            painter.end()


def create_hud(on_text_input=None):
    """Create and return the HUD (must be called from main thread)."""
    if not PYQT_AVAILABLE:
        logger.warning("PyQt5 not available — HUD cannot be created")
        return None, None

    app = QApplication.instance() or QApplication(sys.argv)
    hud = JarvisHUD(on_text_input=on_text_input)
    return app, hud
