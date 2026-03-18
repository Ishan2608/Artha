from newsapi import NewsApiClient
from datetime import datetime, timedelta
from config import settings


_client = NewsApiClient(api_key=settings.NEWS_API_KEY)


def search_news(query: str, days_back: int = 7, page_size: int = 10) -> list[dict]:
    
    """
    Search recent financial news using NewsAPI.

    Prefer this over search_web when the user asks specifically about news,
    press releases, or recent events related to a company or market sector.
    NewsAPI returns structured metadata (source, date, description) that is
    more useful for presenting a news digest than raw web search snippets.

    Args:
        query: Search string. Examples: "Tata Motors EV sales", "Nifty 50 correction"
        days_back: How many days back to search. Default 7. Max 30 on free plan.
        page_size: Articles to return. Default 10. Max 100 on free plan.

    Returns:
        List of dicts. Each dict has: title, source, published_at (ISO string),
        description (snippet), url.
        Articles where title is "[Removed]" (NewsAPI placeholder) are filtered out.
        On API error, returns [{"error": str}] — never raises.
    """
    try:
      
        from_date = (datetime.now() - timedelta(days = days_back)).strftime("%Y-%m-%d")
        response = _client.get_everything(
            q=query,
            from_param=from_date,
            sort_by="relevancy",
            language="en",
            page_size=page_size
        )
        articles = response.get("articles", [])
        ans = []
        for art in articles:
            if art.get("title") == "[Removed]":
                continue
            ans.append(art)
        return ans
    except Exception as e:
        print(f"EXCEPTION in sear_news() tool. It is as follows\n{e}")
        return [{"error": str(e), "message": "An error occured in search_news() tool."}]
