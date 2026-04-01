"""
MCP: api_web
Tools for web research, browsing, and content extraction.
Uses Tavily (preferred) with a fallback to direct HTTP + BeautifulSoup scraping.
"""
from langchain_core.tools import tool

from Business.config import CONFIG

_MAX_SNIPPET_LENGTH = 200


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web and return a summarized list of results.

    Uses Tavily API when a key is configured; otherwise falls back to DuckDuckGo.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        Formatted list of results with titles, URLs, and snippets.
    """
    tavily_key = CONFIG.web.tavily_api_key
    if tavily_key:
        try:
            from tavily import TavilyClient  # type: ignore
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query, max_results=max_results)
            results = response.get("results", [])
            lines = []
            for r in results:
                lines.append(f"- [{r.get('title','')}]({r.get('url','')})\n  {r.get('content','')[:_MAX_SNIPPET_LENGTH]}")
            return "\n\n".join(lines) if lines else "No results."
        except Exception as exc:
            return f"Tavily search failed: {exc}"

    # Fallback: DuckDuckGo instant answer API
    try:
        import requests  # type: ignore
        params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        resp = requests.get("https://api.duckduckgo.com/", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        abstract = data.get("AbstractText", "")
        topics = data.get("RelatedTopics", [])[:max_results]
        lines = [abstract] if abstract else []
        for t in topics:
            if isinstance(t, dict) and "Text" in t:
                url = t.get("FirstURL", "")
                lines.append(f"- {t['Text']} ({url})")
        return "\n".join(lines) if lines else "No results from DuckDuckGo fallback."
    except Exception as exc:
        return f"Web search failed: {exc}"


@tool
def fetch_webpage(url: str, max_chars: int = 4000) -> str:
    """Fetch and extract readable text content from a webpage.

    Args:
        url: Full URL of the page to fetch.
        max_chars: Maximum characters to return from the extracted text.

    Returns:
        Extracted plain text from the page.
    """
    try:
        import requests  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        return "ERROR: requests or beautifulsoup4 not installed. Run: pip install requests beautifulsoup4"

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BusinessAgent/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return text[:max_chars]
    except Exception as exc:
        return f"Failed to fetch {url}: {exc}"


@tool
def extract_links(url: str) -> str:
    """Extract all hyperlinks from a webpage.

    Args:
        url: Full URL of the page to parse.

    Returns:
        Newline-separated list of absolute URLs found on the page.
    """
    try:
        import requests  # type: ignore
        from bs4 import BeautifulSoup  # type: ignore
        from urllib.parse import urljoin, urlparse
    except ImportError:
        return "ERROR: requests or beautifulsoup4 not installed."

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BusinessAgent/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        links = set()
        for a in soup.find_all("a", href=True):
            full = urljoin(base, a["href"])
            if full.startswith("http"):
                links.add(full)
        return "\n".join(sorted(links)) if links else "No links found."
    except Exception as exc:
        return f"Failed to extract links from {url}: {exc}"


WEB_TOOLS = [
    web_search,
    fetch_webpage,
    extract_links,
]
