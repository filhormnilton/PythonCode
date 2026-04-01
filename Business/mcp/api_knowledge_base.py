"""
MCP: api_knowledge_base
Local knowledge base for storing, searching, and managing domain knowledge entries.

Each entry is stored as a plain-text file under business_output/knowledge_base/ and
indexed in a JSON manifest (index.json). No external vector-database is required.

Tools
-----
- add_knowledge_entry      : persist a new knowledge snippet with metadata
- search_knowledge_base    : full-text keyword search across all entries
- get_knowledge_entry      : retrieve a single entry by its id
- list_knowledge_entries   : list all stored entries (id, title, tags, created_at)
- update_knowledge_entry   : replace the content/tags of an existing entry
- remove_knowledge_entry   : delete an entry from the knowledge base

Directory layout
----------------
business_output/
  knowledge_base/
    index.json          <- manifest: list of entry metadata dicts
    <entry-id>.txt      <- one file per entry (raw content)
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from langchain_core.tools import tool

from Business.config import CONFIG

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INDEX_FILE = "index.json"


def _kb_dir() -> Path:
    d = CONFIG.output.knowledge_base_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _index_path() -> Path:
    return _kb_dir() / _INDEX_FILE


def _load_index() -> List[dict]:
    p = _index_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_index(entries: List[dict]) -> None:
    _index_path().write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def _entry_path(entry_id: str) -> Path:
    return _kb_dir() / f"{entry_id}.txt"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str) -> str:
    """Generate a short slug from the first 8 chars of a UUID."""
    return str(uuid.uuid4())[:8]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def add_knowledge_entry(title: str, content: str, tags: str = "", source: str = "") -> str:
    """Add a new knowledge entry to the local knowledge base.

    Args:
        title: Short descriptive title for the entry.
        content: Full text content of the knowledge entry.
        tags: Comma-separated list of topic tags for categorisation (e.g. 'jira,user-story').
        source: Optional source reference (URL, document name, author).

    Returns:
        Entry id and file path, or an error message.
    """
    try:
        entries = _load_index()
        entry_id = _slug(title)

        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        metadata = {
            "id": entry_id,
            "title": title,
            "tags": tag_list,
            "source": source,
            "created_at": _now(),
            "updated_at": _now(),
        }

        _entry_path(entry_id).write_text(content, encoding="utf-8")
        entries.append(metadata)
        _save_index(entries)

        return f"Knowledge entry added. ID={entry_id} | Title='{title}' | Path={_entry_path(entry_id)}"
    except Exception as exc:
        logger.exception("add_knowledge_entry failed")
        return f"ERROR adding knowledge entry: {exc}"


@tool
def search_knowledge_base(query: str, max_results: int = 10) -> str:
    """Search the knowledge base using keyword matching.

    The search is case-insensitive and checks the entry title, tags, source,
    and content for matches.

    Args:
        query: One or more keywords to search for (space-separated).
        max_results: Maximum number of results to return (default 10).

    Returns:
        Formatted list of matching entries with id, title, tags, and a content snippet.
    """
    try:
        entries = _load_index()
        if not entries:
            return "Knowledge base is empty."

        keywords = [kw.strip().lower() for kw in query.split() if kw.strip()]
        if not keywords:
            return "Please provide at least one search keyword."

        scored: List[Tuple[int, dict]] = []
        for meta in entries:
            content = ""
            ep = _entry_path(meta["id"])
            if ep.exists():
                content = ep.read_text(encoding="utf-8").lower()

            haystack = " ".join([
                meta.get("title", "").lower(),
                " ".join(meta.get("tags", [])),
                meta.get("source", "").lower(),
                content,
            ])

            score = sum(1 for kw in keywords if kw in haystack)
            if score > 0:
                scored.append((score, meta))

        if not scored:
            return f"No entries found matching '{query}'."

        scored.sort(key=lambda x: x[0], reverse=True)
        lines = []
        for _, meta in scored[:max_results]:
            ep = _entry_path(meta["id"])
            snippet = ""
            if ep.exists():
                raw = ep.read_text(encoding="utf-8")
                snippet = raw[:200].replace("\n", " ")
                if len(raw) > 200:
                    snippet += "..."
            lines.append(
                f"ID={meta['id']} | {meta['title']} | tags={meta.get('tags', [])} | {snippet}"
            )

        return "\n".join(lines)
    except Exception as exc:
        logger.exception("search_knowledge_base failed")
        return f"ERROR searching knowledge base: {exc}"


@tool
def get_knowledge_entry(entry_id: str) -> str:
    """Retrieve the full content of a knowledge entry by its id.

    Args:
        entry_id: The unique id of the entry (as returned by add_knowledge_entry
                  or list_knowledge_entries).

    Returns:
        Entry metadata followed by full content, or an error message.
    """
    try:
        entries = _load_index()
        meta = next((e for e in entries if e["id"] == entry_id), None)
        if meta is None:
            return f"ERROR: Entry '{entry_id}' not found."

        ep = _entry_path(entry_id)
        content = ep.read_text(encoding="utf-8") if ep.exists() else "(content file missing)"

        return (
            f"ID: {meta['id']}\n"
            f"Title: {meta['title']}\n"
            f"Tags: {', '.join(meta.get('tags', []))}\n"
            f"Source: {meta.get('source', '')}\n"
            f"Created: {meta.get('created_at', '')}\n"
            f"Updated: {meta.get('updated_at', '')}\n"
            f"---\n{content}"
        )
    except Exception as exc:
        logger.exception("get_knowledge_entry failed")
        return f"ERROR retrieving entry: {exc}"


@tool
def list_knowledge_entries(tag_filter: str = "") -> str:
    """List all entries in the knowledge base.

    Args:
        tag_filter: Optional tag to filter by (case-insensitive). Leave empty to list all.

    Returns:
        Formatted table of entries (id, title, tags, created_at).
    """
    try:
        entries = _load_index()
        if not entries:
            return "Knowledge base is empty."

        if tag_filter:
            tf = tag_filter.strip().lower()
            entries = [e for e in entries if tf in [t.lower() for t in e.get("tags", [])]]
            if not entries:
                return f"No entries found with tag '{tag_filter}'."

        lines = [f"{'ID':<10} {'Title':<40} {'Tags':<30} {'Created':<25}"]
        lines.append("-" * 110)
        for meta in entries:
            lines.append(
                f"{meta['id']:<10} {meta['title'][:38]:<40} "
                f"{', '.join(meta.get('tags', []))[:28]:<30} "
                f"{meta.get('created_at', '')[:24]:<25}"
            )
        return "\n".join(lines)
    except Exception as exc:
        logger.exception("list_knowledge_entries failed")
        return f"ERROR listing knowledge base: {exc}"


@tool
def update_knowledge_entry(entry_id: str, content: str = "", tags: str = "") -> str:
    """Update the content and/or tags of an existing knowledge entry.

    Args:
        entry_id: The unique id of the entry to update.
        content: New content to replace the current content (leave empty to keep current).
        tags: New comma-separated tags (leave empty to keep current tags).

    Returns:
        Confirmation message, or an error message.
    """
    try:
        entries = _load_index()
        meta = next((e for e in entries if e["id"] == entry_id), None)
        if meta is None:
            return f"ERROR: Entry '{entry_id}' not found."

        if content:
            _entry_path(entry_id).write_text(content, encoding="utf-8")
        if tags:
            meta["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
        meta["updated_at"] = _now()

        _save_index(entries)
        return f"Knowledge entry '{entry_id}' updated."
    except Exception as exc:
        logger.exception("update_knowledge_entry failed")
        return f"ERROR updating entry: {exc}"


@tool
def remove_knowledge_entry(entry_id: str) -> str:
    """Remove a knowledge entry from the knowledge base.

    Args:
        entry_id: The unique id of the entry to remove.

    Returns:
        Confirmation message, or an error message.
    """
    try:
        entries = _load_index()
        meta = next((e for e in entries if e["id"] == entry_id), None)
        if meta is None:
            return f"ERROR: Entry '{entry_id}' not found."

        ep = _entry_path(entry_id)
        if ep.exists():
            ep.unlink()

        entries = [e for e in entries if e["id"] != entry_id]
        _save_index(entries)
        return f"Knowledge entry '{entry_id}' ('{meta['title']}') removed."
    except Exception as exc:
        logger.exception("remove_knowledge_entry failed")
        return f"ERROR removing entry: {exc}"


# ---------------------------------------------------------------------------
# Exported tool list
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE_TOOLS = [
    add_knowledge_entry,
    search_knowledge_base,
    get_knowledge_entry,
    list_knowledge_entries,
    update_knowledge_entry,
    remove_knowledge_entry,
]
