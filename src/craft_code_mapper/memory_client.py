"""
Memory Client — connette craft-code-mapper a craft-memory via MCP.

Ogni chiamata a un tool MCP di craft-memory viene fatta via HTTP.
"""

import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MemoryClient:
    """Client per chiamare i tool MCP di craft-memory."""

    def __init__(self, base_url: str = "http://127.0.0.1:8392/mcp", max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=30)
        self._req_id = 0
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._max_retries = max_retries

    def _call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Chiama un tool MCP su craft-memory."""
        self._req_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }
        try:
            resp = self._client.post(
                self.base_url, json=payload, headers=self._headers, timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
            if "error" in result:
                logger.error(f"MCP error in {tool}: {result['error']}")
                return {"error": result["error"]["message"]}
            # Estrai il testo dal content
            content = result.get("result", {}).get("content", [])
            text = "\n".join(
                c["text"] for c in content if c.get("type") == "text"
            )
            return {"text": text, "raw": result}
        except Exception as e:
            logger.error(f"HTTP error calling {tool}: {e}")
            return {"error": str(e)}

    def _call_with_retry(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Chiama un tool MCP con retry esponenziale su errore."""
        for attempt in range(self._max_retries):
            result = self._call(tool, args)
            if "error" not in result:
                return result
            if attempt < self._max_retries - 1:
                wait = 2 ** attempt
                logger.warning(
                    f"Retry {attempt + 1}/{self._max_retries} for {tool} "
                    f"after {wait}s (error: {result['error'][:80]})"
                )
                time.sleep(wait)
        return result

    def remember(
        self,
        content: str,
        category: str = "note",
        importance: int = 5,
        tags: list[str] | None = None,
    ) -> int | None:
        """Salva un'entità di codice come memoria."""
        args = {
            "content": content,
            "category": category,
            "importance": importance,
        }
        if tags:
            args["tags"] = tags

        result = self._call_with_retry("remember", args)
        text = result.get("text", "")
        if "Memory #" in text:
            # Estrai ID: "Memory #42 stored: ..."
            try:
                return int(text.split("Memory #")[1].split()[0])
            except (IndexError, ValueError):
                return None
        if "Duplicate" in text:
            logger.info(f"Duplicate memory skipped: {content[:60]}...")
            return None
        logger.warning(f"Failed to store memory: {text}")
        return None

    def link_memories(
        self,
        source_id: int,
        target_id: int,
        relation: str = "semantically_similar_to",
    ) -> bool:
        """Crea una relazione tra due memorie."""
        result = self._call_with_retry("link_memories", {
            "source_id": source_id,
            "target_id": target_id,
            "relation": relation,
            "confidence_type": "extracted",
            "confidence_score": 1.0,
        })
        text = result.get("text", "")
        if "Relation #" in text:
            return True
        if "already exists" in text:
            return True
        logger.warning(f"Failed to link memories: {text}")
        return False

    def upsert_fact(self, key: str, value: str) -> bool:
        """Registra un fatto (es. file hash)."""
        result = self._call_with_retry("upsert_fact", {
            "key": key,
            "value": value,
            "confidence_type": "extracted",
        })
        text = result.get("text", "")
        return "Fact #" in text

    def close(self):
        self._client.close()