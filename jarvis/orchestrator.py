"""
===========================================================
J.A.R.V.I.S. — Orchestrator
===========================================================
Central nervous system: routes commands from voice input
to the brain, dispatches tool calls, chains multi-step tasks,
and returns results to the TTS output.
===========================================================
"""

import json
import time
import logging
import threading
from datetime import datetime
from typing import Optional, Callable

import sympy

from jarvis.config import USER_TITLE

logger = logging.getLogger("jarvis.orchestrator")


class Orchestrator:
    """
    The command router and task executor.
    Receives text → queries brain → dispatches tools → returns response.
    """

    def __init__(self, brain=None, memory=None, tts=None, vision=None):
        self.brain = brain
        self.memory = memory
        self.tts = tts
        self.vision = vision
        self._tools = {}
        self._proactive = None
        self._processing = False

        # Initialize tools
        self._init_tools()

        logger.info("Orchestrator initialized")

    def _init_tools(self):
        """Initialize all tool modules."""
        try:
            from jarvis.tools.web_search import WebSearchTool
            from jarvis.tools.weather import WeatherTool
            from jarvis.tools.news import NewsTool
            from jarvis.tools.system_control import SystemControlTool
            from jarvis.tools.email_tool import EmailTool
            from jarvis.tools.calendar_tool import CalendarTool
            from jarvis.tools.music import MusicTool
            from jarvis.tools.code_runner import CodeRunnerTool
            from jarvis.tools.smart_home import SmartHomeTool
            from jarvis.tools.proactive import ProactiveEngine
            from jarvis.tools.messaging import MessagingTool

            self._tools = {
                "web_search": WebSearchTool(self.memory),
                "weather": WeatherTool(self.memory),
                "news": NewsTool(self.memory),
                "system_control": SystemControlTool(self.memory),
                "email": EmailTool(self.memory),
                "calendar": CalendarTool(self.memory),
                "music": MusicTool(self.memory),
                "code_runner": CodeRunnerTool(self.memory),
                "smart_home": SmartHomeTool(self.memory),
                "messaging": MessagingTool(self.memory),
            }

            self._proactive = ProactiveEngine(self, self.memory)
            logger.info(f"Loaded {len(self._tools)} tool modules")

        except Exception as e:
            logger.error(f"Tool initialization error: {e}")

    def process_command(self, text: str) -> str:
        """
        Main entry point: process a user command end-to-end.
        
        Flow:
        1. Log input to memory
        2. Check for special commands (remember, calculate, timer, etc.)
        3. Send to brain with context
        4. Parse response for tool calls
        5. Execute tools and feed results back
        6. Return final response
        """
        if not text or not text.strip():
            return ""

        self._processing = True
        start_time = time.time()

        try:
            logger.info(f"Processing command: \"{text}\"")

            # Check for special built-in commands first
            special = self._handle_special_commands(text)
            if special:
                if self.memory:
                    self.memory.add_turn("user", text)
                    self.memory.add_turn("assistant", special)
                self._finalize_response(special, text, start_time)
                return special

            # Send to brain
            if not self.brain:
                return "My language processing systems are offline, " + USER_TITLE + "."

            response = self.brain.think(text)

            # Check if the brain wants to call a tool
            tool_call = self.brain.parse_tool_call(response)

            if tool_call:
                tool_result = self._execute_tool(tool_call)

                # Feed tool result back to brain for a natural response
                augmented_input = (
                    f"The user asked: \"{text}\"\n"
                    f"I called the tool '{tool_call['tool']}' and got this result:\n"
                    f"{tool_result}\n\n"
                    f"Now give a natural, conversational response to the user "
                    f"based on this result. Be concise."
                )
                response = self.brain.think(augmented_input)

                # Log tool usage
                if self.memory:
                    self.memory.log_command(
                        text, tool_call["tool"], "success", tool_result[:500]
                    )
                    self.memory.add_turn("user", text)
                    self.memory.add_turn("assistant", response,
                                         tool_call=json.dumps(tool_call),
                                         tool_result=tool_result[:500])
            else:
                # No tool call — direct response
                if self.memory:
                    self.memory.add_turn("user", text)
                    self.memory.add_turn("assistant", response)

            self._finalize_response(response, text, start_time)
            return response

        except Exception as e:
            logger.error(f"Command processing error: {e}")
            error_msg = f"I encountered an error processing that, {USER_TITLE}. {str(e)}"
            return error_msg

        finally:
            self._processing = False

    def _finalize_response(self, response: str, command: str, start_time: float):
        """Log and speak the response."""
        elapsed = time.time() - start_time
        logger.info(f"Response ({elapsed:.1f}s): \"{response[:100]}...\"")

    def _execute_tool(self, tool_call: dict) -> str:
        """Execute a tool call and return the result."""
        tool_name = tool_call.get("tool", "")
        params = tool_call.get("params", {})
        reason = tool_call.get("reason", "")

        logger.info(f"Tool call: {tool_name} | Params: {params} | Reason: {reason}")

        # Special tools handled internally
        if tool_name == "memory_save":
            return self._save_memory(params)
        elif tool_name == "set_timer":
            return self._set_timer(params)
        elif tool_name == "calculate":
            return self._calculate(params)

        # Look up tool module
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Tool '{tool_name}' not found."

        try:
            result = tool.execute(params)
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {e}")
            return f"Tool error: {str(e)}"

    # ================================================================
    # Special Commands (handled without LLM)
    # ================================================================

    def _handle_special_commands(self, text: str) -> Optional[str]:
        """Handle commands that don't need the LLM."""
        text_lower = text.lower().strip()

        # Diagnostics
        if "run diagnostics" in text_lower or "system diagnostic" in text_lower:
            return self._run_diagnostics()

        # System status
        if text_lower in ("system status", "status report"):
            tool = self._tools.get("system_control")
            if tool:
                return tool.execute({"action": "system_info"})

        # Remember command
        if text_lower.startswith("remember that") or text_lower.startswith("remember "):
            content = text[text_lower.index("remember") + 9:].strip()
            if content and self.memory:
                self.memory.save_to_long_term(content, {"type": "user_note", "role": "user"})
                return f"I'll remember that, {USER_TITLE}."

        # What do you know about me?
        if "what do you know about me" in text_lower:
            if self.memory:
                profile = self.memory.get_full_profile()
                if profile:
                    lines = [f"Here's what I know about you, {USER_TITLE}:\n"]
                    for k, v in profile.items():
                        lines.append(f"  • {k}: {v}")
                    return "\n".join(lines)
            return f"I don't have much information stored yet, {USER_TITLE}."

        # Timer
        if "set a timer" in text_lower or "set timer" in text_lower:
            import re
            match = re.search(r'(\d+)\s*(minute|min|second|sec|hour|hr)', text_lower)
            if match:
                amount = int(match.group(1))
                unit = match.group(2)
                if "hour" in unit or "hr" in unit:
                    seconds = amount * 3600
                elif "min" in unit:
                    seconds = amount * 60
                else:
                    seconds = amount
                return self._set_timer({"duration_seconds": seconds, "label": f"{amount} {unit} timer"})

        # Calculator
        if text_lower.startswith("calculate "):
            expr = text[10:].strip()
            return self._calculate({"expression": expr})

        # Joke
        if "tell me a joke" in text_lower:
            return None  # Let the LLM handle personality responses

        return None  # Not a special command

    def _save_memory(self, params: dict) -> str:
        """Save content to long-term memory."""
        content = params.get("content", "")
        tags = params.get("tags", [])
        if content and self.memory:
            self.memory.save_to_long_term(content, {"type": "saved", "tags": str(tags)})
            return f"Saved to memory: {content[:100]}"
        return "Nothing to save."

    def _set_timer(self, params: dict) -> str:
        """Set a countdown timer."""
        seconds = params.get("duration_seconds", 60)
        label = params.get("label", "Timer")
        if self._proactive:
            return self._proactive.add_timer(seconds, label)
        return f"Timer not available — scheduler not running."

    def _calculate(self, params: dict) -> str:
        """Evaluate a math expression using sympy."""
        expression = params.get("expression", "")
        if not expression:
            return "No expression provided."
        try:
            result = sympy.sympify(expression)
            evaluated = float(result.evalf()) if hasattr(result, 'evalf') else result
            return f"Result: {expression} = {evaluated}"
        except Exception as e:
            return f"Calculation error: {str(e)}"

    def _run_diagnostics(self) -> str:
        """Full system health report."""
        lines = [f"Running diagnostics, {USER_TITLE}...\n"]

        # Brain status
        if self.brain:
            status = self.brain.get_status()
            backend = status["active_backend"] or "OFFLINE"
            lines.append(f"  ✦ Language Processing: {backend.upper()}")
            lines.append(f"    Ollama: {'✓' if status['ollama_available'] else '✗'}")
            lines.append(f"    Groq:   {'✓' if status['groq_available'] else '✗'}")
            lines.append(f"    Gemini: {'✓' if status['gemini_available'] else '✗'}")
        else:
            lines.append("  ✗ Language Processing: OFFLINE")

        # Memory status
        if self.memory:
            stats = self.memory.get_stats()
            lines.append(f"  ✦ Memory Systems: ONLINE")
            lines.append(f"    Short-term: {stats['short_term_turns']} turns")
            lines.append(f"    Long-term:  {stats['long_term_memories']} memories")
            lines.append(f"    ChromaDB:   {'✓' if stats['chromadb_connected'] else '✗'}")
        else:
            lines.append("  ✗ Memory Systems: OFFLINE")

        # TTS status
        if self.tts:
            tts_status = self.tts.get_status()
            lines.append(f"  ✦ Speech Synthesis: {tts_status['engine'].upper()}")
        else:
            lines.append("  ✗ Speech Synthesis: OFFLINE")

        # Vision status
        if self.vision:
            vis = self.vision.get_status()
            lines.append(f"  ✦ Vision: {'ACTIVE' if vis['camera_active'] else 'STANDBY'}")
            lines.append(f"    Known faces: {vis['known_faces']}")
        else:
            lines.append("  ✗ Vision: OFFLINE")

        # Tool status
        lines.append(f"  ✦ Tools loaded: {len(self._tools)}")
        for name in self._tools:
            lines.append(f"    • {name}")

        # System info
        try:
            import psutil
            lines.append(f"\n  System: CPU {psutil.cpu_percent()}% | RAM {psutil.virtual_memory().percent}%")
        except Exception:
            pass

        lines.append(f"\nAll systems nominal, {USER_TITLE}.")
        return "\n".join(lines)

    # ================================================================
    # Properties
    # ================================================================

    @property
    def is_processing(self) -> bool:
        return self._processing

    def get_proactive_engine(self):
        return self._proactive
