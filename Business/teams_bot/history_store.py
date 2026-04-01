"""
business/teams_bot/history_store.py — Conversation history persistence.

Provides two implementations of the history store interface:
  - InMemoryHistoryStore : simple dict, resets on restart (default/dev)
  - CosmosDBHistoryStore : Azure CosmosDB-backed, survives restarts (production)

The active implementation is chosen at runtime based on the presence of the
``COSMOS_ENDPOINT`` and ``COSMOS_KEY`` environment variables.

Usage::

    from Business.teams_bot.history_store import build_history_store

    store = build_history_store()
    history = store.get("conv-id-123")
    history.append(HumanMessage(content="..."))
    store.save("conv-id-123", history)
"""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, List

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _messages_to_json(messages: List[BaseMessage]) -> str:
    """Serialise a list of LangChain messages to a JSON string."""
    data = []
    for msg in messages:
        data.append({
            "type": "human" if isinstance(msg, HumanMessage) else "ai",
            "content": msg.content,
        })
    return json.dumps(data, ensure_ascii=False)


def _json_to_messages(raw: str) -> List[BaseMessage]:
    """Deserialise a JSON string back to LangChain messages."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    result: List[BaseMessage] = []
    for item in data:
        if item.get("type") == "human":
            result.append(HumanMessage(content=item["content"]))
        else:
            result.append(AIMessage(content=item["content"]))
    return result


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class HistoryStore(ABC):
    """Interface for conversation history backends."""

    @abstractmethod
    def get(self, conversation_id: str) -> List[BaseMessage]:
        """Return the full message history for a conversation."""

    @abstractmethod
    def save(self, conversation_id: str, history: List[BaseMessage]) -> None:
        """Persist the current history for a conversation."""

    @abstractmethod
    def clear(self, conversation_id: str) -> None:
        """Remove the history for a conversation."""


# ---------------------------------------------------------------------------
# In-memory implementation (development / fallback)
# ---------------------------------------------------------------------------

class InMemoryHistoryStore(HistoryStore):
    """Simple in-memory history store. Resets on process restart."""

    def __init__(self) -> None:
        self._data: Dict[str, List[BaseMessage]] = {}

    def get(self, conversation_id: str) -> List[BaseMessage]:
        return self._data.setdefault(conversation_id, [])

    def save(self, conversation_id: str, history: List[BaseMessage]) -> None:
        self._data[conversation_id] = history

    def clear(self, conversation_id: str) -> None:
        self._data.pop(conversation_id, None)


# ---------------------------------------------------------------------------
# Azure CosmosDB implementation (production)
# ---------------------------------------------------------------------------

class CosmosDBHistoryStore(HistoryStore):
    """Azure CosmosDB-backed history store.

    Required environment variables:
        COSMOS_ENDPOINT   – e.g. https://<account>.documents.azure.com:443/
        COSMOS_KEY        – Primary or secondary key for the CosmosDB account
        COSMOS_DATABASE   – Database name (default: "business_bot")
        COSMOS_CONTAINER  – Container name (default: "conversations")

    The container must have a partition key of ``/conversation_id``.
    Items are upserted on every save, so TTL can be configured on the
    container to automatically expire old conversations.
    """

    _CONTAINER_PARTITION_KEY = "/conversation_id"

    def __init__(
        self,
        endpoint: str,
        key: str,
        database_name: str = "business_bot",
        container_name: str = "conversations",
    ) -> None:
        try:
            from azure.cosmos import CosmosClient, PartitionKey, exceptions  # type: ignore
            self._exceptions = exceptions
        except ImportError as exc:
            raise ImportError(
                "azure-cosmos package is required for CosmosDBHistoryStore. "
                "Install it with: pip install azure-cosmos"
            ) from exc

        self._client = CosmosClient(url=endpoint, credential=key)
        db = self._client.create_database_if_not_exists(id=database_name)
        self._container = db.create_container_if_not_exists(
            id=container_name,
            partition_key=PartitionKey(path=self._CONTAINER_PARTITION_KEY),
        )
        logger.info(
            "[CosmosDBHistoryStore] connected to %s / %s",
            database_name,
            container_name,
        )

    # -- helpers ---------------------------------------------------------------

    def _item_id(self, conversation_id: str) -> str:
        # CosmosDB item IDs may not contain '/', '\', '?', '#'.
        # Teams conversation IDs commonly contain '|' and ':'; these are safe for CosmosDB IDs
        # but are replaced for URL-friendliness when used as REST path segments.
        # The forbidden characters are also sanitised as a safety measure.
        sanitised = conversation_id
        for ch in ("|", ":", "/", "\\", "?", "#"):
            sanitised = sanitised.replace(ch, "_")
        return sanitised

    # -- interface implementation ----------------------------------------------

    def get(self, conversation_id: str) -> List[BaseMessage]:
        try:
            item = self._container.read_item(
                item=self._item_id(conversation_id),
                partition_key=conversation_id,
            )
            return _json_to_messages(item.get("history", "[]"))
        except self._exceptions.CosmosResourceNotFoundError:
            return []
        except Exception as exc:
            logger.warning("[CosmosDBHistoryStore] get failed (%s), returning empty history", exc)
            return []

    def save(self, conversation_id: str, history: List[BaseMessage]) -> None:
        try:
            self._container.upsert_item({
                "id": self._item_id(conversation_id),
                "conversation_id": conversation_id,
                "history": _messages_to_json(history),
            })
        except Exception as exc:
            logger.warning("[CosmosDBHistoryStore] save failed (%s), history not persisted", exc)

    def clear(self, conversation_id: str) -> None:
        try:
            self._container.delete_item(
                item=self._item_id(conversation_id),
                partition_key=conversation_id,
            )
        except self._exceptions.CosmosResourceNotFoundError:
            pass
        except Exception as exc:
            logger.warning("[CosmosDBHistoryStore] clear failed (%s)", exc)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_history_store() -> HistoryStore:
    """Return the appropriate HistoryStore based on environment variables.

    If ``COSMOS_ENDPOINT`` and ``COSMOS_KEY`` are both set, returns a
    :class:`CosmosDBHistoryStore`.  Otherwise, returns an
    :class:`InMemoryHistoryStore` and logs a warning.
    """
    endpoint = os.getenv("COSMOS_ENDPOINT", "")
    key = os.getenv("COSMOS_KEY", "")

    if endpoint and key:
        database = os.getenv("COSMOS_DATABASE", "business_bot")
        container = os.getenv("COSMOS_CONTAINER", "conversations")
        logger.info("[HistoryStore] Using CosmosDB backend (database=%s, container=%s)", database, container)
        return CosmosDBHistoryStore(
            endpoint=endpoint,
            key=key,
            database_name=database,
            container_name=container,
        )

    logger.warning(
        "[HistoryStore] COSMOS_ENDPOINT / COSMOS_KEY not set — using in-memory store "
        "(conversation history will be lost on restart). "
        "Set these env vars to enable CosmosDB persistence."
    )
    return InMemoryHistoryStore()
