"""Free web search (DuckDuckGo) so answers can use current information."""


def search_web(query: str, n: int = 5) -> list:
    try:
        try:
            from ddgs import DDGS
        except ImportError:  # older package name
            from duckduckgo_search import DDGS
        results = list(DDGS().text(query, max_results=n))
    except Exception:
        return []
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in results
    ]
