"""
MCP: api_miro
Tools for creating, reading, updating, and deleting boards and sticky notes in MIRO
using the MIRO REST API v2.
"""
from typing import Optional

import requests
from langchain_core.tools import tool

from Business.config import CONFIG

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


@tool
def create_miro_shape(
    content: str,
    shape: str = "rectangle",
    x: int = 0,
    y: int = 0,
    width: int = 200,
    height: int = 80,
    fill_color: str = "#ffffff",
    parent_id: str = "",
    board_id: str = "",
) -> str:
    """Create a shape (box, circle, etc.) with a text label on a MIRO board.

    Args:
        content: Text label inside the shape.
        shape: Shape type — rectangle, circle, triangle, rhombus, parallelogram,
               trapezoid, pentagon, hexagon, octagon, star, cross, arrow,
               callout, cloud, cylinder (default: rectangle).
        x: Horizontal centre position (default 0).
        y: Vertical centre position (default 0).
        width: Shape width in pixels (default 200).
        height: Shape height in pixels (default 80).
        fill_color: Background color as hex string (default #ffffff).
        parent_id: Frame ID to nest this shape inside (optional but recommended).
        board_id: Target board id (defaults to configured board).

    Returns:
        New shape id or an error message.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}/shapes"
    payload = {
        "data": {"content": content, "shape": shape},
        "style": {"fillColor": fill_color, "borderColor": "#1a1a1a", "borderWidth": "2"},
        "position": {"x": x, "y": y},
        "geometry": {"width": width, "height": height},
    }
    if parent_id:
        payload["parent"] = {"id": parent_id}
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return f"Shape '{content}' created. ID: {data.get('id')} | x={x}, y={y}"
    except Exception as exc:
        return f"MIRO create shape failed: {exc}"


@tool
def create_miro_connector(
    start_item_id: str,
    end_item_id: str,
    label: str = "",
    board_id: str = "",
) -> str:
    """Create an arrow/connector between two items on a MIRO board.

    Args:
        start_item_id: ID of the source item (shape, sticky note, frame, etc.).
        end_item_id: ID of the destination item.
        label: Optional text label on the connector.
        board_id: Target board id (defaults to configured board).

    Returns:
        New connector id or an error message.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}/connectors"
    payload = {
        "startItem": {"id": start_item_id},
        "endItem": {"id": end_item_id},
        "style": {"strokeColor": "#1a1a1a", "strokeWidth": "2", "endStrokeCap": "arrow"},
    }
    if label:
        payload["captions"] = [{"content": label, "position": "0.5"}]
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        return f"Connector created. ID: {resp.json().get('id')}"
    except Exception as exc:
        return f"MIRO create connector failed: {exc}"


@tool
def create_miro_text(
    content: str,
    x: int = 0,
    y: int = 0,
    font_size: int = 14,
    parent_id: str = "",
    board_id: str = "",
) -> str:
    """Add a standalone text label to a MIRO board.

    Args:
        content: Text content.
        x: Horizontal position (default 0).
        y: Vertical position (default 0).
        font_size: Font size in pt (default 14).
        parent_id: Frame ID to nest this text inside (optional but recommended).
        board_id: Target board id (defaults to configured board).

    Returns:
        New text item id or an error message.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}/texts"
    payload = {
        "data": {"content": content},
        "style": {"fontSize": str(font_size), "color": "#1a1a1a"},
        "position": {"x": x, "y": y},
    }
    if parent_id:
        payload["parent"] = {"id": parent_id}
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=15)
        resp.raise_for_status()
        return f"Text created. ID: {resp.json().get('id')}"
    except Exception as exc:
        return f"MIRO create text failed: {exc}"


@tool
def get_miro_board_url(board_id: str = "") -> str:
    """Return the shareable URL of a MIRO board.

    Args:
        board_id: Board id (defaults to configured board).

    Returns:
        The board view URL.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}"
    try:
        resp = requests.get(url, headers=_headers(), timeout=15)
        resp.raise_for_status()
        data = resp.json()
        view_link = data.get("viewLink", f"https://miro.com/app/board/{bid}/")
        return f"Board URL: {view_link}"
    except Exception as exc:
        return f"MIRO get board url failed: {exc}"


@tool
def get_miro_canvas_offset(board_id: str = "") -> str:
    """Scan all existing items on the board and return a safe (x, y) origin
    that is completely clear of existing content — so new drawings never
    overlap existing work.

    Args:
        board_id: Board id (defaults to configured board).

    Returns:
        JSON-like string: {"offset_x": N, "offset_y": N, "items_found": N}
        The returned offset adds 400 px of padding beyond the rightmost item.
    """
    bid = _board_id(board_id)
    url = f"{_MIRO_BASE}/boards/{bid}/items"
    try:
        # Paginate through ALL items (cursor-based)
        max_x, max_y = 0.0, 0.0
        items_found = 0
        cursor = None
        while True:
            params = {"limit": 50}
            if cursor:
                params["cursor"] = cursor
            resp = requests.get(url, headers=_headers(), params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])
            items_found += len(items)
            for item in items:
                pos = item.get("position", {})
                geo = item.get("geometry", {})
                ix = float(pos.get("x", 0) or 0)
                iy = float(pos.get("y", 0) or 0)
                iw = float(geo.get("width", 0) or 0)
                ih = float(geo.get("height", 0) or 0)
                max_x = max(max_x, ix + iw / 2)
                max_y = max(max_y, iy + ih / 2)
            cursor = data.get("cursor")
            if not cursor or not items:
                break
        # Place new content 400 px to the right of everything existing
        offset_x = int(max_x) + 400 if items_found else 0
        offset_y = -600  # start near top of canvas
        return f'{{"offset_x": {offset_x}, "offset_y": {offset_y}, "items_found": {items_found}}}'
    except Exception as exc:
        return f'{{"offset_x": 0, "offset_y": 0, "items_found": 0, "error": "{exc}"}}'


MIRO_TOOLS = [
    create_miro_board,
    get_miro_board,
    get_miro_canvas_offset,
    create_sticky_note,
    update_sticky_note,
    delete_sticky_note,
    list_miro_items,
    create_miro_frame,
    create_sticky_note_in_frame,
    create_miro_shape,
    create_miro_connector,
    create_miro_text,
    get_miro_board_url,
]
