"""
===========================================================
J.A.R.V.I.S. — Brain Module (LLM Reasoning Engine)
===========================================================
Multi-backend LLM with automatic failover:
  Primary:    Ollama (local, llama3:8b)
  Fallback 1: Groq API (free tier, llama3-70b)
  Fallback 2: Google Gemini 1.5 Flash (free tier)

Supports:
  - JARVIS personality via system prompt
  - Tool/function calling via JSON output
  - Conversation history injection
  - Streaming responses
  - Memory-augmented context
===========================================================
"""

import json
import logging
import re
from typing import Generator, Optional

from jarvis.config import (
    OLLAMA_BASE_URL, OLLAMA_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    GEMINI_API_KEY, GEMINI_MODEL,
    JARVIS_SYSTEM_PROMPT, MAX_CONVERSATION_HISTORY
)

logger = logging.getLogger("jarvis.brain")


class JarvisBrain:
    """
    The reasoning engine of JARVIS.
    Routes queries through available LLM backends with automatic failover.
    """

    def __init__(self, memory_manager=None):
        self.memory = memory_manager
        self.active_backend = None

        # Track which backends are available
        self._ollama_available = False
        self._groq_available = False
        self._gemini_available = False

        # Clients (lazy init)
        self._ollama_client = None
        self._groq_client = None
        self._gemini_model = None

        # Probe available backends
        self._probe_backends()

        logger.info(f"Brain initialized — active backend: {self.active_backend or 'NONE'}")

    # ================================================================
    # Backend Probing
    # ================================================================

    def _probe_backends(self):
        """Check which LLM backends are available."""
        # 1. Try Ollama (local)
        try:
            import ollama
            self._ollama_client = ollama.Client(host=OLLAMA_BASE_URL)
            # Quick check — list models
            models = self._ollama_client.list()
            model_names = [m.get("name", m.get("model", "")) for m in models.get("models", [])]
            if any(OLLAMA_MODEL.split(":")[0] in m for m in model_names):
                self._ollama_available = True
                self.active_backend = "ollama"
                logger.info(f"Ollama backend ready with model: {OLLAMA_MODEL}")
            else:
                logger.warning(f"Ollama running but model '{OLLAMA_MODEL}' not found. Available: {model_names}")
                # Still mark as available — we'll try to pull it
                self._ollama_available = True
                self.active_backend = "ollama"
        except Exception as e:
            logger.info(f"Ollama not available: {e}")

        # 2. Try Groq (free tier)
        if GROQ_API_KEY:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=GROQ_API_KEY)
                self._groq_available = True
                if not self.active_backend:
                    self.active_backend = "groq"
                logger.info("Groq backend available")
            except Exception as e:
                logger.info(f"Groq not available: {e}")

        # 3. Try Gemini (free tier)
        if GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                self._gemini_model = genai.GenerativeModel(GEMINI_MODEL)
                self._gemini_available = True
                if not self.active_backend:
                    self.active_backend = "gemini"
                logger.info("Gemini backend available")
            except Exception as e:
                logger.info(f"Gemini not available: {e}")

        if not self.active_backend:
            logger.error(
                "NO LLM BACKEND AVAILABLE! Install Ollama or provide API keys."
            )

    # ================================================================
    # Main Query Interface
    # ================================================================

    def think(self, user_input: str, system_override: str = None) -> str:
        """
        Process a user query through the LLM and return a response.
        Tries backends in order: Ollama → Groq → Gemini.
        
        Args:
            user_input: The user's transcribed speech or text
            system_override: Optional override for the system prompt
            
        Returns:
            The LLM's response string
        """
        system_prompt = system_override or self._build_system_prompt(user_input)
        history = self._get_history()

        # Try each backend in failover order (prioritizing speed: Groq/Gemini > Ollama)
        backends = [
            ("groq", self._groq_available, self._query_groq),
            ("gemini", self._gemini_available, self._query_gemini),
            ("ollama", self._ollama_available, self._query_ollama),
        ]

        for name, available, query_fn in backends:
            if not available:
                continue
            try:
                response = query_fn(system_prompt, history, user_input)
                self.active_backend = name
                return response
            except Exception as e:
                logger.warning(f"{name} backend failed: {e}")
                continue

        # All backends failed
        return (
            f"I apologize, {self._get_title()}. All my language processing systems "
            "are currently offline. Please ensure Ollama is running, or provide "
            "API keys for Groq or Gemini in the .env file."
        )

    def think_stream(self, user_input: str, system_override: str = None) -> Generator[str, None, None]:
        """
        Stream a response token by token. Falls back to non-streaming if needed.
        
        Yields:
            Individual text chunks as they arrive
        """
        system_prompt = system_override or self._build_system_prompt(user_input)
        history = self._get_history()

        # Try streaming from each backend (prioritizing speed)
        backends = [
            ("groq", self._groq_available, self._stream_groq),
            ("gemini", self._gemini_available, self._stream_gemini),
            ("ollama", self._ollama_available, self._stream_ollama),
        ]

        for name, available, stream_fn in backends:
            if not available:
                continue
            try:
                yielded = False
                for chunk in stream_fn(system_prompt, history, user_input):
                    yielded = True
                    yield chunk
                if yielded:
                    self.active_backend = name
                    return
            except Exception as e:
                logger.warning(f"{name} streaming failed: {e}")
                continue

        # Fallback to non-streaming
        yield self.think(user_input, system_override)

    # ================================================================
    # Ollama Backend
    # ================================================================

    def _query_ollama(self, system: str, history: list, user_input: str) -> str:
        """Query Ollama local model."""
        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        response = self._ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages
        )
        return response["message"]["content"]

    def _stream_ollama(self, system: str, history: list, user_input: str) -> Generator[str, None, None]:
        """Stream from Ollama."""
        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        stream = self._ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            stream=True
        )
        for chunk in stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content

    # ================================================================
    # Groq Backend
    # ================================================================

    def _query_groq(self, system: str, history: list, user_input: str) -> str:
        """Query Groq cloud API."""
        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        response = self._groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )
        return response.choices[0].message.content

    def _stream_groq(self, system: str, history: list, user_input: str) -> Generator[str, None, None]:
        """Stream from Groq."""
        messages = [{"role": "system", "content": system}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        stream = self._groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            stream=True
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    # ================================================================
    # Gemini Backend
    # ================================================================

    def _query_gemini(self, system: str, history: list, user_input: str) -> str:
        """Query Google Gemini."""
        # Gemini uses a different message format
        full_prompt = f"{system}\n\n"
        for msg in history:
            role = "User" if msg["role"] == "user" else "JARVIS"
            full_prompt += f"{role}: {msg['content']}\n"
        full_prompt += f"User: {user_input}\nJARVIS:"

        response = self._gemini_model.generate_content(full_prompt)
        return response.text

    def _stream_gemini(self, system: str, history: list, user_input: str) -> Generator[str, None, None]:
        """Stream from Gemini."""
        full_prompt = f"{system}\n\n"
        for msg in history:
            role = "User" if msg["role"] == "user" else "JARVIS"
            full_prompt += f"{role}: {msg['content']}\n"
        full_prompt += f"User: {user_input}\nJARVIS:"

        response = self._gemini_model.generate_content(full_prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

    # ================================================================
    # Prompt Construction
    # ================================================================

    def _build_system_prompt(self, user_input: str) -> str:
        """
        Build the full system prompt with:
          - Base JARVIS personality
          - Relevant memories from long-term storage
          - Current date/time context
        """
        from datetime import datetime
        prompt = JARVIS_SYSTEM_PROMPT

        # Add current timestamp
        now = datetime.now()
        prompt += f"\n\nCurrent date/time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}"

        # Inject relevant memories
        if self.memory:
            context = self.memory.get_relevant_context(user_input)
            if context:
                prompt += f"\n\n{context}"

            # Inject user profile
            profile = self.memory.get_full_profile()
            if profile:
                prompt += "\n\n[User profile:]"
                for key, value in profile.items():
                    prompt += f"\n  - {key}: {value}"

        return prompt

    def _get_history(self) -> list[dict]:
        """Get conversation history for LLM context."""
        if self.memory:
            return self.memory.get_conversation_history()
        return []

    def _get_title(self) -> str:
        """Get the user's preferred title."""
        from jarvis.config import USER_TITLE
        return USER_TITLE

    # ================================================================
    # Tool Call Parsing
    # ================================================================

    @staticmethod
    def parse_tool_call(response: str) -> Optional[dict]:
        """
        Extract a tool call JSON from the LLM response.
        
        The LLM is prompted to output tool calls in this format:
        {"tool": "name", "params": {...}, "reason": "..."}
        
        Returns:
            Parsed tool call dict, or None if no tool call found.
        """
        # Try to find JSON in the response
        # Pattern 1: Direct JSON object
        try:
            # Look for JSON-like structures in the response
            json_patterns = re.findall(r'\{[^{}]*"tool"[^{}]*\}', response, re.DOTALL)
            for pattern in json_patterns:
                try:
                    parsed = json.loads(pattern)
                    if "tool" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass

        # Pattern 2: JSON in code block
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if code_block_match:
            try:
                parsed = json.loads(code_block_match.group(1))
                if "tool" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass

        # Pattern 3: Try parsing entire response as JSON
        try:
            parsed = json.loads(response.strip())
            if isinstance(parsed, dict) and "tool" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

        return None

    # ================================================================
    # Status
    # ================================================================

    def get_status(self) -> dict:
        """Return brain status information."""
        return {
            "active_backend": self.active_backend,
            "ollama_available": self._ollama_available,
            "groq_available": self._groq_available,
            "gemini_available": self._gemini_available,
            "ollama_model": OLLAMA_MODEL if self._ollama_available else None,
            "groq_model": GROQ_MODEL if self._groq_available else None,
            "gemini_model": GEMINI_MODEL if self._gemini_available else None,
        }
