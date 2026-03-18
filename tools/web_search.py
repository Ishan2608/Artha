from tavily import TavilyClient
from config import settings


_client = TavilyClient(api_key=settings.TAVILY_API_KEY)


def search_web(query: str, max_results: int = 5) -> list[dict]:
    
    """
    Search the internet using Tavily and return clean result dicts.

    Use this for questions requiring live internet data: macro events,
    regulatory changes, company announcements, general financial concepts.
    Do NOT use this for real-time stock prices — use get_stock_info for that.

    Args:
        query: Focused search query. More specific = better results.
               Example: "RBI repo rate decision June 2025"
               Bad example: "stocks" (too broad)
        max_results: Number of results to return. 5 is the right default.
                     Go up to 10 only if the user explicitly needs comprehensive coverage.

    Returns:
        List of dicts. Each dict has: title, url, content (snippet), score (0.0 to 1.0).
        On API error, returns [{"error": str}] — never raises.
    """
    try:
        response = _client.search(query=query, max_results=max_results)
        results = response.get("results", [])
        ans = []
        for r in results:
            res = {
                "title": r.get("title"), 
                "url": r.get("url"),
                "content": r.get("content"),
                "score": r.get("score")
            }
            ans.append(res)
        return ans
    except Exception as e:
        print(f"EXCEPTION: Inside search_web(), an exception occured. It is as follows:\n{e}")
        return [{"error": str(r), "message": "An error occured in search_web() tool."}]
