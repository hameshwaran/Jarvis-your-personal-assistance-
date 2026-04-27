"""
===========================================================
J.A.R.V.I.S. — Main Entry Point
===========================================================
Just A Rather Very Intelligent System

Boots all modules in sequence, runs self-diagnostics,
and starts the main event loop connecting voice input,
brain, tools, and HUD output.
===========================================================
"""

import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime
from pathlib import Path

# ── Setup logging before anything else ──────────────────
from jarvis.config import LOG_FILE, LOG_LEVEL, LOG_FORMAT, USER_TITLE, BOOT_SEQUENCE_MODULES

# Force UTF-8 for console output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("jarvis.main")

# Rich console for pretty startup output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    console = Console()
    HAS_RICH = True
except ImportError:
    console = None
    HAS_RICH = False


def print_banner():
    """Print the JARVIS startup banner."""
    banner = r"""
      JH   AA   RRRR   V   V  II  SSSS
      JJ  A  A  R   R  V   V  II  S
      JJ  AAAA  RRRR   V   V  II  SSSS
  J   JJ  A  A  R R     V V   II     S
   JJJJ   A  A  R  R     V    II  SSSS
    Just A Rather Very Intelligent System  v1.0
    """
    if HAS_RICH:
        console.print(Panel(
            Text(banner, style="bold cyan"),
            border_style="cyan",
            title="[bold white]STARK INDUSTRIES[/]",
            subtitle="[dim]All Systems Initializing[/]"
        ))
    else:
        print(banner)


class JarvisSystem:
    """
    Main system class — boots, connects, and runs all JARVIS modules.
    """

    def __init__(self):
        self.memory = None
        self.brain = None
        self.voice_in = None
        self.voice_out = None
        self.orchestrator = None
        self.vision = None
        self.hud = None
        self.hud_app = None
        self.web_hud = None
        self._running = False
        self._boot_results = {}

    def boot(self):
        """Execute the full boot sequence."""
        print_banner()
        logger.info("=" * 60)
        logger.info("J.A.R.V.I.S. BOOT SEQUENCE INITIATED")
        logger.info("=" * 60)

        boot_start = time.time()

        # ── Step 1: Memory Systems ──────────────────────
        self._boot_module("Memory Systems", self._init_memory)

        # ── Step 2: Brain (LLM) ────────────────────────
        self._boot_module("Language Processing", self._init_brain)

        # ── Step 3: Voice Output (TTS) ─────────────────
        self._boot_module("Speech Synthesis", self._init_tts)

        # ── Step 4: Orchestrator ───────────────────────
        self._boot_module("Command Router", self._init_orchestrator)

        # ── Step 5: Voice Input (Wake Word + STT) ──────
        self._boot_module("Voice Recognition", self._init_voice_in)

        # ── Step 6: Vision ─────────────────────────────
        self._boot_module("Vision Systems", self._init_vision)

        # ── Step 7: Proactive Engine ───────────────────
        self._boot_module("Proactive Engine", self._init_proactive)

        # ── Step 8: Web HUD (Optional) ─────────────────
        self._boot_module("Web Interface", self._init_web_hud)

        # ── Boot Summary ───────────────────────────────
        elapsed = time.time() - boot_start
        success_count = sum(1 for v in self._boot_results.values() if v)
        total = len(self._boot_results)

        logger.info(f"Boot complete: {success_count}/{total} modules online ({elapsed:.1f}s)")

        if HAS_RICH:
            for module, success in self._boot_results.items():
                icon = "[green]✓[/]" if success else "[red]✗[/]"
                console.print(f"  {icon} {module}")
            console.print(f"\n[bold cyan]All systems nominal, {USER_TITLE}.[/]\n")

        # Startup announcement
        if self.voice_out:
            self.voice_out.speak(
                f"Good day, {USER_TITLE}. J.A.R.V.I.S. online. "
                f"{success_count} of {total} systems operational. "
                "All systems nominal. How may I assist you?"
            )

    def _boot_module(self, name: str, init_func):
        """Boot a single module with error handling."""
        try:
            if HAS_RICH:
                console.print(f"  [cyan]⟳[/] Initializing {name}...", end="")
            init_func()
            self._boot_results[name] = True
            if HAS_RICH:
                console.print(f"\r  [green]✓[/] {name}")
            logger.info(f"[BOOT] {name}: OK")
        except Exception as e:
            self._boot_results[name] = False
            if HAS_RICH:
                console.print(f"\r  [red]✗[/] {name}: {e}")
            logger.error(f"[BOOT] {name}: FAILED — {e}")

    # ── Module Initialization ───────────────────────────

    def _init_memory(self):
        from jarvis.memory import MemoryManager
        self.memory = MemoryManager()

    def _init_brain(self):
        from jarvis.brain import JarvisBrain
        self.brain = JarvisBrain(memory_manager=self.memory)

    def _init_tts(self):
        from jarvis.voice_out import TextToSpeech
        self.voice_out = TextToSpeech()

    def _init_orchestrator(self):
        from jarvis.orchestrator import Orchestrator
        self.orchestrator = Orchestrator(
            brain=self.brain,
            memory=self.memory,
            tts=self.voice_out,
            vision=self.vision
        )

    def _init_voice_in(self):
        from jarvis.voice_in import VoiceInput
        self.voice_in = VoiceInput(on_command=self._on_voice_command)

    def _init_vision(self):
        from jarvis.vision import VisionSystem
        self.vision = VisionSystem(
            memory=self.memory,
            on_face_detected=self._on_face_detected
        )

    def _init_proactive(self):
        if self.orchestrator:
            proactive = self.orchestrator.get_proactive_engine()
            if proactive:
                proactive.set_speak_callback(
                    lambda msg: self.voice_out.speak(msg) if self.voice_out else None
                )
                proactive.start()

    def _init_web_hud(self):
        from jarvis.web_hud import WebHUD
        self.web_hud = WebHUD(on_text_input=self._on_text_command)
        self.web_hud.start()

    # ── Event Handlers ──────────────────────────────────

    def _on_voice_command(self, text: str):
        """Handle a voice command from the wake word + STT pipeline."""
        logger.info(f"Voice command received: \"{text}\"")

        # Update HUDs
        if self.hud:
            self.hud.signals.update_command.emit(text)
            self.hud.signals.set_listening.emit(False)
        if self.web_hud:
            self.web_hud.update_command(text)
            self.web_hud.set_listening(False)

        # Process through orchestrator
        response = self.orchestrator.process_command(text)

        # Speak response
        if response and self.voice_out:
            if self.hud:
                self.hud.signals.set_speaking.emit(True)
                self.hud.signals.update_response.emit(response)
            if self.web_hud:
                self.web_hud.set_speaking(True)
                self.web_hud.update_response(response)
            self.voice_out.speak_blocking(response)
            if self.hud:
                self.hud.signals.set_speaking.emit(False)
            if self.web_hud:
                self.web_hud.set_speaking(False)

    def _on_text_command(self, text: str):
        """Handle a text command from the HUD input."""
        logger.info(f"Text command: \"{text}\"")

        if self.hud:
            self.hud.signals.update_status.emit("PROCESSING...")
        if self.web_hud:
            self.web_hud.update_status("PROCESSING...")

        response = self.orchestrator.process_command(text)

        if self.hud:
            self.hud.signals.update_response.emit(response)
            self.hud.signals.update_status.emit("READY")
        if self.web_hud:
            self.web_hud.update_response(response)
            self.web_hud.update_status("READY")

        if response and self.voice_out:
            self.voice_out.speak(response)

    def _on_face_detected(self, name: str, known: bool):
        """Handle face detection event."""
        if known:
            logger.info(f"Known face detected: {name}")
            if self.hud:
                self.hud.signals.update_status.emit(f"IDENTIFIED: {name}")
            if self.web_hud:
                self.web_hud.update_status(f"IDENTIFIED: {name}", success=True)
        else:
            logger.info("Unidentified individual detected")
            if self.hud:
                self.hud.signals.update_status.emit("UNIDENTIFIED INDIVIDUAL")
            if self.web_hud:
                self.web_hud.update_status("UNIDENTIFIED INDIVIDUAL", success=False)

    # ── Main Run Loop ───────────────────────────────────

    def run(self):
        """Start the main event loop with HUD."""
        self._running = True

        # Start voice input pipeline
        if self.voice_in:
            self.voice_in.start()

        # Start vision (optional — don't start camera by default)
        # self.vision.start_camera()  # Uncomment to enable webcam

        # Create and show HUD
        try:
            from jarvis.hud import create_hud, PYQT_AVAILABLE
            if PYQT_AVAILABLE:
                self.hud_app, self.hud = create_hud(
                    on_text_input=self._on_text_command
                )
                if self.hud:
                    self.hud.show()

                    # Show boot results in HUD
                    for module, success in self._boot_results.items():
                        self.hud.signals.boot_step.emit(module, success)
                        if self.web_hud:
                            self.web_hud.boot_step(module, success)
                    self.hud.signals.update_status.emit("READY")
                    if self.web_hud:
                        self.web_hud.update_status("READY")

                    # Run Qt event loop (blocks until quit)
                    self.hud_app.exec_()
                else:
                    self._run_console_mode()
            else:
                self._run_console_mode()
        except Exception as e:
            logger.warning(f"HUD failed, falling back to console: {e}")
            self._run_console_mode()

    def _run_console_mode(self):
        """Fallback console mode when HUD is not available."""
        if HAS_RICH:
            console.print(
                f"\n[bold cyan]J.A.R.V.I.S. is ready, {USER_TITLE}.[/]"
                "\n[dim]Type commands below, or say 'Hey Jarvis'.[/]"
                "\n[dim]Type 'quit' to exit.[/]\n"
            )
        else:
            print(f"\nJ.A.R.V.I.S. is ready, {USER_TITLE}.")
            print("Type commands below, or say 'Hey Jarvis'.")
            print("Type 'quit' to exit.\n")

        while self._running:
            try:
                user_input = input(f"[{USER_TITLE}] > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "shutdown"):
                    self.shutdown()
                    break

                response = self.orchestrator.process_command(user_input)
                if HAS_RICH:
                    console.print(f"[cyan][JARVIS][/] {response}\n")
                else:
                    print(f"[JARVIS] {response}\n")

                if self.voice_out:
                    self.voice_out.speak(response)

            except KeyboardInterrupt:
                self.shutdown()
                break
            except EOFError:
                self.shutdown()
                break

    def shutdown(self):
        """Graceful shutdown of all systems."""
        logger.info("Initiating shutdown sequence...")
        self._running = False

        if self.voice_out:
            self.voice_out.speak_blocking(
                f"Shutting down, {USER_TITLE}. Goodbye."
            )

        if self.voice_in:
            self.voice_in.stop()
        if self.vision:
            self.vision.stop_camera()
        if self.orchestrator and self.orchestrator.get_proactive_engine():
            self.orchestrator.get_proactive_engine().stop()
        if self.web_hud:
            self.web_hud.stop()
        if self.memory:
            self.memory.close()

        logger.info("All systems shut down. Goodbye.")


def main():
    """Entry point."""
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

    jarvis = JarvisSystem()

    try:
        jarvis.boot()
        jarvis.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"\n[FATAL] {e}")
    finally:
        jarvis.shutdown()


if __name__ == "__main__":
    main()
