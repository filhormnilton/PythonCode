"""
MCP: api_miro
Tools for creating, reading, updating, and deleting boards and sticky notes in MIRO
using the MIRO REST API v2.
"""
from typing import Optional

import requests
from langchain_core.tools import tool

from business.config import CONFIG

_MIRO_BASE = "https://api.miro.com/v2"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {CONFIG.miro.access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _board_id(board_id: str = "") -> str:
    return board_id or CONFIG.miro.board_id


# ---------------------------------------------------------------------------
# Board tools
# ---------------------------------------------------------------------------

@tool
def create_miro_board(name: str, description: str = "") -> str:
    """Create a new MIRO board.

    Args:
        name: Name for the new board.
        description: Optional description.

    Returns:
        New board id and URL.
    """
    url = f"{_MIRO_BASE}/boards"
    payload = {"name": name, "description": description}
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return f"Board created. ID: {data.get('id')} | URL: {data.get('viewLink', '')}"
    except Exception as exc:
        return f"MIRO create board failed: {exc}"


@tool
def get_miro_board(board_id: str = "") -> str:
    """Get details about a MIRO board.

    Args:
        board_id: MIRO board id (defaults to configured board).

    Returns:
        Board metadata as a formatted string.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}"
    try:
        resp = requests.get(url, headers=_headers(), timeout=15)
        resp.raise_for_status()
        d = resp.json()
        return (
            f"ID: {d.get('id')}\n"
            f"Name: {d.get('name')}\n"
            f"Description: {d.get('description', '')}\n"
            f"URL: {d.get('viewLink', '')}"
        )
    except Exception as exc:
        return f"MIRO get board failed: {exc}"


@tool
def delete_miro_board(board_id: str) -> str:
    """Delete a MIRO board.

    Args:
        board_id: MIRO board id to delete.

    Returns:
        Confirmation message.
    """
    url = f"{_MIRO_BASE}/boards/{board_id}"
    try:
        resp = requests.delete(url, headers=_headers(), timeout=15)
        resp.raise_for_status()
        return f"Board {board_id} deleted."
    except Exception as exc:
        return f"MIRO delete board failed: {exc}"


# ---------------------------------------------------------------------------
# Sticky note tools
# ---------------------------------------------------------------------------

@tool
def create_sticky_note(content: str, color: str = "yellow", board_id: str = "") -> str:
    """Add a sticky note to a MIRO board.

    Args:
        content: Text content of the sticky note.
        color: Sticky note color (yellow, blue, green, pink, violet, red, orange, light_yellow, light_green, light_blue).
        board_id: Target board id (defaults to configured board).

    Returns:
        New sticky note id.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}/sticky_notes"
    payload = {
        "data": {"content": content, "shape": "square"},
        "style": {"fillColor": color},
    }
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        return f"Sticky note created. ID: {resp.json().get('id')}"
    except Exception as exc:
        return f"MIRO create sticky note failed: {exc}"


@tool
def update_sticky_note(item_id: str, content: str, board_id: str = "") -> str:
    """Update the text of an existing sticky note.

    Args:
        item_id: Id of the sticky note item.
        content: New text content.
        board_id: Board id (defaults to configured board).

    Returns:
        Confirmation message.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}/sticky_notes/{item_id}"
    payload = {"data": {"content": content}}
    try:
        resp = requests.patch(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        return f"Sticky note {item_id} updated."
    except Exception as exc:
        return f"MIRO update sticky note failed: {exc}"


@tool
def delete_sticky_note(item_id: str, board_id: str = "") -> str:
    """Delete a sticky note from a MIRO board.

    Args:
        item_id: Id of the sticky note item.
        board_id: Board id (defaults to configured board).

    Returns:
        Confirmation message.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}/sticky_notes/{item_id}"
    try:
        resp = requests.delete(url, headers=_headers(), timeout=15)
        resp.raise_for_status()
        return f"Sticky note {item_id} deleted."
    except Exception as exc:
        return f"MIRO delete sticky note failed: {exc}"


@tool
def list_miro_items(board_id: str = "") -> str:
    """List all items on a MIRO board.

    Args:
        board_id: Board id (defaults to configured board).

    Returns:
        Formatted list of board items.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}/items"
    try:
        resp = requests.get(url, headers=_headers(), timeout=15)
        resp.raise_for_status()
        items = resp.json().get("data", [])
        if not items:
            return "Board has no items."
        return "\n".join(f"[{i.get('type')}] id={i.get('id')}" for i in items)
    except Exception as exc:
        return f"MIRO list items failed: {exc}"


# ---------------------------------------------------------------------------
# Frame tools
# ---------------------------------------------------------------------------

@tool
def create_miro_frame(
    title: str,
    x: int = 0,
    y: int = 0,
    width: int = 800,
    height: int = 600,
    board_id: str = "",
) -> str:
    """Create a frame on a MIRO board to group and organise items visually.

    Args:
        title: Frame title displayed at the top.
        x: Horizontal position of the frame (default 0).
        y: Vertical position of the frame (default 0).
        width: Frame width in pixels (default 800).
        height: Frame height in pixels (default 600).
        board_id: Target board id (defaults to configured board).

    Returns:
        New frame id and its position, or an error message.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}/frames"
    payload = {
        "data": {"title": title, "format": "custom", "type": "freeform"},
        "position": {"x": x, "y": y},
        "geometry": {"width": width, "height": height},
    }
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return (
            f"Frame '{title}' created. ID: {data.get('id')} | "
            f"x={x}, y={y}, {width}x{height}"
        )
    except Exception as exc:
        return f"MIRO create frame failed: {exc}"


@tool
def create_sticky_note_in_frame(
    content: str,
    frame_id: str,
    color: str = "yellow",
    board_id: str = "",
) -> str:
    """Add a sticky note that is attached to an existing MIRO frame.

    Args:
        content: Text content of the sticky note.
        frame_id: Id of the target frame (use create_miro_frame to obtain it).
        color: Sticky note colour (yellow, blue, green, pink, violet, red, orange,
               light_yellow, light_green, light_blue).
        board_id: Target board id (defaults to configured board).

    Returns:
        New sticky note id, or an error message.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}/sticky_notes"
    payload = {
        "data": {"content": content, "shape": "square"},
        "style": {"fillColor": color},
        "parent": {"id": frame_id},
    }
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        return f"Sticky note created in frame {frame_id}. ID: {resp.json().get('id')}"
    except Exception as exc:
        return f"MIRO create sticky note in frame failed: {exc}"


MIRO_TOOLS = [
    create_miro_board,
    get_miro_board,
    delete_miro_board,
    create_sticky_note,
    update_sticky_note,
    delete_sticky_note,
    list_miro_items,
    create_miro_frame,
    create_sticky_note_in_frame,
]
