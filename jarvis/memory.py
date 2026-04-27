"""
===========================================================
J.A.R.V.I.S. — Memory Module
===========================================================
Dual-layer memory system:
  1. Short-term: In-memory deque of recent conversation turns
  2. Long-term: ChromaDB vector store with sentence-transformer embeddings
  3. User Profile: SQLite-backed persistent user data

All storage is local. No cloud. No paid APIs.
===========================================================
"""

import json
import time
import sqlite3
import logging
import hashlib
from datetime import datetime
from collections import deque
from pathlib import Path
from typing import Optional

from jarvis.config import (
    SQLITE_DB_PATH, CHROMADB_PATH, EMBEDDING_MODEL,
    MAX_CONVERSATION_HISTORY, MEMORY_SEARCH_TOP_K, USER_TITLE
)

logger = logging.getLogger("jarvis.memory")


class MemoryManager:
    """
    Central memory system for JARVIS.
    Handles short-term conversation context, long-term semantic memory,
    and persistent user profile storage.
    """

    def __init__(self):
        # ── Short-term memory (recent turns) ────────────
        self.short_term: deque = deque(maxlen=MAX_CONVERSATION_HISTORY)

        # ── SQLite for structured data ──────────────────
        self._init_sqlite()

        # ── ChromaDB + embeddings for long-term memory ──
        self._chroma_client = None
        self._collection = None
        self._embedder = None
        self._init_long_term_memory()

        logger.info("Memory systems initialized successfully")

    # ================================================================
    # SQLite Initialization
    # ================================================================

    def _init_sqlite(self):
        """Create SQLite database and tables if they don't exist."""
        try:
            self.db = sqlite3.connect(str(SQLITE_DB_PATH), check_same_thread=False)
            self.db.row_factory = sqlite3.Row
            cursor = self.db.cursor()

            # User profile table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Conversation log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_call TEXT,
                    tool_result TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Search cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT,
                    results TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Command log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS command_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT,
                    module TEXT,
                    status TEXT,
                    result TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Face embeddings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS known_faces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    encoding BLOB NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.db.commit()
            logger.info(f"SQLite database ready at {SQLITE_DB_PATH}")

        except Exception as e:
            logger.error(f"SQLite initialization failed: {e}")
            raise

    # ================================================================
    # Long-Term Memory (ChromaDB)
    # ================================================================

    def _init_long_term_memory(self):
        """Initialize ChromaDB and sentence-transformer embeddings."""
        try:
            import chromadb
            from chromadb.config import Settings

            self._chroma_client = chromadb.PersistentClient(
                path=str(CHROMADB_PATH),
                settings=Settings(anonymized_telemetry=False)
            )
            self._collection = self._chroma_client.get_or_create_collection(
                name="jarvis_memory",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"ChromaDB ready — {self._collection.count()} memories stored")

        except Exception as e:
            logger.warning(f"ChromaDB init failed (will retry later): {e}")
            self._chroma_client = None
            self._collection = None

        # Load sentence-transformer (lazy — only when first needed)
        self._embedder = None

    def _get_embedder(self):
        """Lazy-load the sentence-transformer model."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(EMBEDDING_MODEL)
                logger.info(f"Embedding model '{EMBEDDING_MODEL}' loaded")
            except Exception as e:
                logger.warning(f"Embedding model load failed: {e}")
        return self._embedder

    # ================================================================
    # Short-Term Memory
    # ================================================================

    def add_turn(self, role: str, content: str, tool_call: str = None, tool_result: str = None):
        """
        Add a conversation turn to short-term memory and log to SQLite.
        
        Args:
            role: 'user' or 'assistant'
            content: The message content
            tool_call: JSON string of tool call if any
            tool_result: Result from tool execution if any
        """
        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "tool_call": tool_call,
            "tool_result": tool_result,
        }
        self.short_term.append(turn)

        # Persist to SQLite
        try:
            self.db.execute(
                "INSERT INTO conversation_log (role, content, tool_call, tool_result) VALUES (?, ?, ?, ?)",
                (role, content, tool_call, tool_result)
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log conversation turn: {e}")

        # Also save to long-term memory for semantic search later
        if content and len(content) > 10:
            self.save_to_long_term(content, metadata={
                "role": role,
                "type": "conversation",
                "timestamp": turn["timestamp"]
            })

    def get_conversation_history(self) -> list[dict]:
        """Return the short-term conversation history for LLM context."""
        history = []
        for t in self.short_term:
            role = t["role"]
            content = t["content"]
            tool_call = t.get("tool_call")
            tool_result = t.get("tool_result")

            if role == "assistant" and tool_call and tool_result:
                try:
                    tool_name = json.loads(tool_call).get("tool", "unknown")
                except Exception:
                    tool_name = "unknown"
                # Inject tool context into the assistant's memory
                content = f"[Tool '{tool_name}' executed. Result: {tool_result}]\n{content}"

            history.append({"role": role, "content": content})
        return history

    def get_formatted_history(self) -> str:
        """Return conversation history as a formatted string for prompt injection."""
        lines = []
        for turn in self.short_term:
            prefix = f"{USER_TITLE}" if turn["role"] == "user" else "JARVIS"
            lines.append(f"{prefix}: {turn['content']}")
        return "\n".join(lines)

    # ================================================================
    # Long-Term Memory (Semantic)
    # ================================================================

    def save_to_long_term(self, content: str, metadata: dict = None):
        """
        Save a piece of information to long-term semantic memory.
        
        Args:
            content: Text to store and embed
            metadata: Optional metadata dict (tags, type, timestamp)
        """
        if self._collection is None:
            return

        try:
            doc_id = hashlib.md5(
                f"{content}{time.time()}".encode()
            ).hexdigest()

            meta = metadata or {}
            meta["saved_at"] = datetime.now().isoformat()
            # ChromaDB requires string values in metadata
            meta = {k: str(v) for k, v in meta.items()}

            embedder = self._get_embedder()
            if embedder:
                embedding = embedder.encode(content).tolist()
                self._collection.add(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[meta],
                    embeddings=[embedding]
                )
            else:
                # Fallback: store without custom embedding (ChromaDB uses default)
                self._collection.add(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[meta]
                )

        except Exception as e:
            logger.error(f"Failed to save to long-term memory: {e}")

    def search_memory(self, query: str, top_k: int = None) -> list[dict]:
        """
        Semantic search across long-term memory.
        
        Args:
            query: Search query text
            top_k: Number of results (default from config)
            
        Returns:
            List of dicts with 'content', 'metadata', 'distance'
        """
        if self._collection is None or self._collection.count() == 0:
            return []

        top_k = top_k or MEMORY_SEARCH_TOP_K

        try:
            embedder = self._get_embedder()
            if embedder:
                query_embedding = embedder.encode(query).tolist()
                results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, self._collection.count())
                )
            else:
                results = self._collection.query(
                    query_texts=[query],
                    n_results=min(top_k, self._collection.count())
                )

            memories = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    memories.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    })
            return memories

        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []

    def get_relevant_context(self, query: str) -> str:
        """
        Get relevant memories formatted for injection into the LLM prompt.
        Only includes memories with reasonable relevance scores.
        """
        memories = self.search_memory(query)
        if not memories:
            return ""

        # Filter by relevance (cosine distance < 0.8 means fairly relevant)
        relevant = [m for m in memories if m.get("distance", 1) < 0.8]
        if not relevant:
            return ""

        lines = ["[Relevant memories from past interactions:]"]
        for m in relevant:
            timestamp = m["metadata"].get("saved_at", "unknown time")
            lines.append(f"  - ({timestamp}) {m['content'][:200]}")

        return "\n".join(lines)

    # ================================================================
    # User Profile (SQLite)
    # ================================================================

    def set_user_data(self, key: str, value: str):
        """Store or update a user profile field."""
        try:
            self.db.execute(
                """INSERT OR REPLACE INTO user_profile (key, value, updated_at) 
                   VALUES (?, ?, CURRENT_TIMESTAMP)""",
                (key, value)
            )
            self.db.commit()
            logger.info(f"User profile updated: {key}")
        except Exception as e:
            logger.error(f"Failed to save user data: {e}")

    def get_user_data(self, key: str) -> Optional[str]:
        """Retrieve a user profile field."""
        try:
            row = self.db.execute(
                "SELECT value FROM user_profile WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else None
        except Exception as e:
            logger.error(f"Failed to get user data: {e}")
            return None

    def get_full_profile(self) -> dict:
        """Return the entire user profile as a dictionary."""
        try:
            rows = self.db.execute("SELECT key, value FROM user_profile").fetchall()
            return {row["key"]: row["value"] for row in rows}
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return {}

    # ================================================================
    # Search Cache
    # ================================================================

    def get_cached_search(self, query: str, max_age_hours: int = 24) -> Optional[str]:
        """Retrieve cached search results if they're fresh enough."""
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        try:
            row = self.db.execute(
                """SELECT results, cached_at FROM search_cache 
                   WHERE query_hash = ? 
                   AND cached_at > datetime('now', ? || ' hours')""",
                (query_hash, f"-{max_age_hours}")
            ).fetchone()
            if row:
                logger.info(f"Search cache hit for: {query[:50]}")
                return row["results"]
        except Exception as e:
            logger.error(f"Search cache retrieval failed: {e}")
        return None

    def cache_search(self, query: str, results: str):
        """Cache search results."""
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        try:
            self.db.execute(
                """INSERT OR REPLACE INTO search_cache (query_hash, query, results, cached_at) 
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                (query_hash, query, results)
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Search cache save failed: {e}")

    # ================================================================
    # Command Logging
    # ================================================================

    def log_command(self, command: str, module: str, status: str, result: str = ""):
        """Log a command execution for analytics and debugging."""
        try:
            self.db.execute(
                "INSERT INTO command_log (command, module, status, result) VALUES (?, ?, ?, ?)",
                (command, module, status, result[:500])
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Command log failed: {e}")

    # ================================================================
    # Face Data
    # ================================================================

    def save_face(self, name: str, encoding: bytes):
        """Save a face encoding for recognition."""
        try:
            self.db.execute(
                "INSERT INTO known_faces (name, encoding) VALUES (?, ?)",
                (name, encoding)
            )
            self.db.commit()
            logger.info(f"Face saved for: {name}")
        except Exception as e:
            logger.error(f"Failed to save face: {e}")

    def get_known_faces(self) -> list[dict]:
        """Retrieve all known face encodings."""
        try:
            rows = self.db.execute("SELECT name, encoding FROM known_faces").fetchall()
            return [{"name": row["name"], "encoding": row["encoding"]} for row in rows]
        except Exception as e:
            logger.error(f"Failed to get known faces: {e}")
            return []

    # ================================================================
    # Cleanup
    # ================================================================

    def close(self):
        """Clean shutdown of all memory systems."""
        try:
            if self.db:
                self.db.close()
            logger.info("Memory systems shut down cleanly")
        except Exception as e:
            logger.error(f"Error during memory shutdown: {e}")

    def get_stats(self) -> dict:
        """Return memory system statistics."""
        stats = {
            "short_term_turns": len(self.short_term),
            "long_term_memories": 0,
            "sqlite_connected": self.db is not None,
            "chromadb_connected": self._collection is not None,
            "embedder_loaded": self._embedder is not None,
        }
        if self._collection:
            stats["long_term_memories"] = self._collection.count()
        return stats
