"""
Manual test script. Run with: python test_tools.py
Not a pytest suite. A quick sanity check to confirm each tool function
returns clean, JSON-serializable output before wiring into the agent.
Each test is wrapped independently so one failure does not block others.
"""

import json

def assert_json_safe(obj, label: str) -> bool:
    """
    Verify that obj can be serialized to JSON without errors.
    Prints PASS or FAIL with the label.
    Returns True if safe, False if not.
    """
    try:
        json.dumps(obj)
        print(f"  JSON-safe: PASS ({label})")
        return True
    except (TypeError, ValueError) as e:
        print(f"  JSON-safe: FAIL ({label}) — {e}")
        return False


def test_session_store():
    """Test all session store functions using no external dependencies."""
    print("\nSession Store Tests")
    from utils.session_store import (append_message, get_history, add_file, get_files, clear_session)
    
    sid = "test_session_001"
    append_message(sid, "user", "Hello")
    append_message(sid, "assistant", "Hi there")
    
    hist = get_history(sid)
    assert len(hist) == 2, "Expected 2 messages"
    assert hist[0]["role"] == "user"
    
    add_file(sid, "file001", "/tmp/test.pdf", "test.pdf")
    files = get_files(sid)
    assert len(files) == 1
    assert files[0]["file_id"] == "file001"
    
    clear_session(sid)
    assert get_history(sid) == []
    print("  All session store tests: PASS")


def test_formatters():
    """Test sanitize_dataframe and sanitize_info_dict with synthetic data."""
    print("\nFormatter Tests")
    import pandas as pd
    import numpy as np
    from utils.formatters import sanitize_dataframe, sanitize_info_dict
    
    # Build a test DataFrame with NaN, numpy float64, and Timestamp values
    df = pd.DataFrame({
        "Date": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")],
        "Close": [np.float64(1234.5), np.float64(float("nan"))],
        "Volume": [np.int64(1000000), np.int64(2000000)],
    })
    
    result = sanitize_dataframe(df)
    assert_json_safe(result, "sanitize_dataframe")
    assert result["Close"][1] is None, "NaN should become None"
    
    # Build a test info dict with numpy types and NaN
    info = {
        "longName": "Test Corp", 
        "currentPrice": np.float64(500.0),
        "trailingPE": np.float64(float("nan")), 
        "marketCap": np.int64(1000000000)
    }
    
    result2 = sanitize_info_dict(info)
    assert_json_safe(result2, "sanitize_info_dict")
    assert result2.get("trailingPE") is None, "NaN PE should become None"
    print("  All formatter tests: PASS")


def test_stock_info():
    """Test get_stock_info returns clean dict for TCS.NS."""
    print("\nStock Info Test (TCS.NS)")
    from tools.stock_data import get_stock_info
    
    result = get_stock_info("TCS", "NSE")
    # print(json.dumps(result, indent=2)) # Uncomment to see the full output payload
    
    assert "error" not in result, f"Unexpected error: {result}"
    assert result.get("currentPrice") is not None, "currentPrice missing"
    assert_json_safe(result, "get_stock_info TCS")
    print("  PASS")


def test_stock_history():
    """Test get_stock_history returns chart-ready arrays for WIPRO."""
    print("\nStock History Test (WIPRO.NS, 1mo)")
    from tools.stock_data import get_stock_history
    
    result = get_stock_history("WIPRO", "NSE", "1mo", "1d")
    
    assert "error" not in result, f"Unexpected error: {result}"
    assert "dates" in result and "close" in result
    assert len(result["dates"]) == len(result["close"]), "dates and close length mismatch"
    assert_json_safe(result, "get_stock_history WIPRO")
    
    print(f"  {len(result['dates'])} candles returned.")
    print(f"  First date: {result['dates'][0]}, Last close: {result['close'][-1]}")
    print("  PASS")


def test_web_search():
    """Test Tavily returns results for a finance query."""
    print("\nWeb Search Test")
    from tools.web_search import search_web
    
    result = search_web("TCS Tata Consultancy Services Q4 results 2025")
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert "error" not in result[0]
    assert_json_safe(result, "search_web")
    
    print(f"  First result: {result[0].get('title')}")
    print("  PASS")


def test_news_search():
    """Test NewsAPI returns articles."""
    print("\nNews Search Test")
    from tools.news_search import search_news
    
    result = search_news("Infosys", days_back=7)
    
    assert isinstance(result, list)
    assert_json_safe(result, "search_news")
    
    if len(result) > 0 and "error" not in result[0]:
        print(f"  First article: {result[0].get('title')}")
    print("  PASS")


def test_ticker_lookup():
    """Test ticker lookup by company name using the Indian listings file."""
    print("\nTicker Lookup Test")
    from tools.ticker_lookup import search_ticker
    
    results = search_ticker("tata steel")
    assert isinstance(results, list)
    print(f"  Results for 'tata steel': {results}")
    
    results2 = search_ticker("TCS")
    print(f"  Results for 'TCS': {results2}")
    print("  PASS (verify results manually)")


if __name__ == "__main__":
    print("=" * 55)
    print("Shree_v2 Tool Tests")
    print("=" * 55)

    test_functions = [
        test_session_store, 
        test_formatters, 
        test_stock_info,
        test_stock_history, 
        test_web_search, 
        test_news_search,
        test_ticker_lookup
    ]

    for test_fn in test_functions:
        try:
            test_fn()
        except Exception as e:
            print(f"  EXCEPTION in {test_fn.__name__}: {e}")

    print("\n" + "=" * 55)
    print("Testing Complete.")
    print("=" * 55)
