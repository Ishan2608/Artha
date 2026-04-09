import yfinance as yf
import pandas as pd
import datetime
from utils.formatters import sanitize_dataframe, sanitize_info_dict
from langchain_core.tools import tool

def _build_ticker(symbol: str, exchange: str = "NSE") -> yf.Ticker:
    """
    Build a yfinance Ticker with the correct exchange suffix.

    NSE tickers get .NS appended, BSE tickers get .BO appended.
    Example: "TCS" + "NSE" -> yf.Ticker("TCS.NS")

    Args:
        symbol: Ticker without suffix. Must be uppercase.
        exchange: "NSE" or "BSE". Default NSE.

    Returns:
        A yfinance Ticker object ready to query.
    """
    suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
    return yf.Ticker(symbol.upper() + suffix)

def get_stock_info(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch key fundamental and real-time pricing info for a stock.

    IMPORTANT: Store ticker.info in a local variable before accessing any keys.
    Every direct access to ticker.info triggers a fresh HTTP request to Yahoo Finance.
    Calling it twice in the same function doubles your network time.

    Args:
        symbol: Ticker symbol without suffix. Example: "TCS", "INFY", "HDFCBANK".
        exchange: "NSE" or "BSE".

    Returns:
        Clean dict with ~35 fields including current_price, 52w range, PE ratios,
        margins, debt-to-equity, analyst targets, and recommendation key.
        All values are plain Python types safe for JSON serialization.
    """
    try:
        ticker = _build_ticker(symbol, exchange)
        info = ticker.info
        
        if not info:
            return {"error": "No info available", "symbol": symbol}
            
        return sanitize_info_dict(info)
        
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


def get_stock_history(symbol: str, exchange: str = "NSE", period: str = "1mo", interval: str = "1d") -> dict:
    """
    Fetch OHLCV historical price data in chart-ready format.

    The returned dict is structured so the frontend can directly feed it
    to a candlestick chart with zero transformation:
      dates -> x-axis labels
      open, high, low, close -> candlestick OHLC values
      volume -> volume bar chart below the candlestick

    Args:
        symbol: Ticker symbol. Example: "WIPRO"
        exchange: "NSE" or "BSE"
        period: yfinance period string.
                Valid values: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"
        interval: Candle size. Valid: "1m"(last 7d only), "5m", "15m", "1h", "1d", "1wk", "1mo"

    Returns:
        Dict with keys: ticker, period, interval, dates, open, high, low, close, volume.
        All numeric lists are rounded to 2 decimal places.
        If no data is found, returns {"error": "No data found", "ticker": symbol}.
    """
    ticker = _build_ticker(symbol, exchange)
    df = ticker.history(period = period, interval = interval)
    if df.empty:
        return {"error": "No data found", "ticker": symbol, "period": period}
    dates = df.index.strftime("%Y-%m-%d").tolist()
    return {    
        "ticker": symbol,
        "period": period,
        "interval": interval,
        "dates": dates,
        "open": df['Open'].round(2).tolist(),
        "high": df['High'].round(2).tolist(),
        "low": df['Low'].round(2).tolist(),
        "close": df['Close'].round(2).tolist(),
        "volume": df['Volume'].astype(int).tolist()
    }


def get_financials(symbol: str, exchange: str = "NSE", statement: str = "income", quarterly: bool = False) -> dict:
    """
    Fetch one of the three core financial statements.

    The three statements are:
      income  -> Revenue, Gross Profit, EBITDA, Net Income (P&L statement)
      balance_sheet -> Total Assets, Total Debt, Stockholders Equity
      cashflow -> Operating, Investing, Financing cash flows

    Rows represent financial metrics. Columns represent reporting dates (4 periods max).
    We transpose before returning so rows become dates and columns become metrics —
    this makes it easier for the frontend to render as a time-series table or bar chart.

    Args:
        symbol: Ticker symbol.
        exchange: "NSE" or "BSE"
        statement: One of "income", "balance_sheet", or "cashflow".
        quarterly: True for quarterly data (last 4 quarters), False for annual (last 4 years).

    Returns:
        Dict with keys: symbol, statement, frequency ("annual"/"quarterly"), data (sanitized).
        data is a dict of lists, one key per financial metric.
    """
    try:
        ticker = _build_ticker(symbol, exchange)
        
        attr_map = {
            "income": {True: ticker.quarterly_financials, False: ticker.financials},
            "balance_sheet": {True: ticker.quarterly_balance_sheet, False: ticker.balance_sheet},
            "cashflow": {True: ticker.quarterly_cashflow, False: ticker.cashflow},
        }
        
        df = attr_map.get(statement, {}).get(quarterly)
        
        if df is None or df.empty:
            return {"error": "Data not available", "symbol": symbol}
            
        # Transpose: dates become rows, metrics become columns
        df = df.T
        data = sanitize_dataframe(df)
        
        return {
            "symbol": symbol, 
            "statement": statement,
            "frequency": "quarterly" if quarterly else "annual", 
            "data": data
        }
        
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


def get_corporate_actions(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch dividends and stock split history for a company.

    Dividends tell you about shareholder returns policy.
    Splits tell you about historical price adjustments.
    Together they give context to long-term price history charts.

    Args:
        symbol: Ticker symbol. Example: "ITC"
        exchange: "NSE" or "BSE"

    Returns:
        Dict with keys: symbol, last_5_dividends, all_splits.
        last_5_dividends: list of {date: str, amount: float} dicts.
        all_splits: list of {date: str, ratio: float} dicts.
        Either list may be empty if the company has no history.
    """
    try:
        ticker = _build_ticker(symbol, exchange)
        
        divs = ticker.dividends
        splits = ticker.splits
        
        div_list = []
        if divs is not None and not divs.empty:
            div_list = [{"date": ts.isoformat(), "amount": round(float(val), 4)} for ts, val in divs.tail(5).items()]
            
        split_list = []
        if splits is not None and not splits.empty:
            split_list = [{"date": ts.isoformat(), "ratio": float(val)} for ts, val in splits.items()]
            
        return {
            "symbol": symbol, 
            "last_5_dividends": div_list, 
            "all_splits": split_list
        }
        
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


def get_analyst_data(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch analyst price targets and recommendation summary counts.

    This is one of the most useful signals for decision-making context because
    it tells you what professional analysts think the stock is worth and
    whether more analysts are bullish or bearish.

    Args:
        symbol: Ticker symbol. Example: "SBIN"
        exchange: "NSE" or "BSE"

    Returns:
        Dict with: symbol, current_price, mean_target, high_target, low_target,
        recommendation_key (string like "buy", "hold", "sell"),
        recommendations_summary (list of dicts with period and count columns).
    """
    try:
        ticker = _build_ticker(symbol, exchange)
        info = ticker.info
        rec_summary = ticker.recommendations_summary
        
        rec_list = []
        if rec_summary is not None and not rec_summary.empty:
            rec_list = sanitize_dataframe(rec_summary)
            
        return {
            "symbol": symbol,
            "current_price": info.get("currentPrice"),
            "mean_target": info.get("targetMeanPrice"),
            "high_target": info.get("targetHighPrice"),
            "low_target": info.get("targetLowPrice"),
            "recommendation_key": info.get("recommendationKey"),
            "recommendations_summary": rec_list
        }
        
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


def get_holders(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch institutional and mutual fund holders for a stock.

    Institutional ownership is a useful signal — high institutional ownership
    often indicates analyst coverage and liquidity. Changes in institutional
    holdings can precede price moves.

    Args:
        symbol: Ticker symbol. Example: "HDFCBANK"
        exchange: "NSE" or "BSE"

    Returns:
        Dict with: symbol, major_holders (list), top_5_institutional (list),
        top_5_mutual_fund (list). Any list may be empty if data is unavailable.
    """
    try:
        ticker = _build_ticker(symbol, exchange)
        
        major = ticker.major_holders
        inst = ticker.institutional_holders
        mf = ticker.mutualfund_holders
        
        return {
            "symbol": symbol,
            "major_holders": sanitize_dataframe(major) if major is not None and not major.empty else [],
            "top_5_institutional": sanitize_dataframe(inst.head(5)) if inst is not None and not inst.empty else [],
            "top_5_mutual_fund": sanitize_dataframe(mf.head(5)) if mf is not None and not mf.empty else []
        }
        
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


def get_esg_data(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch ESG (Environmental, Social, Governance) risk scores from Sustainalytics.

    ESG data is only available for large-cap stocks that Sustainalytics covers.
    Most mid-cap and small-cap Indian stocks will return the error dict.
    A lower total ESG score means lower risk.

    Args:
        symbol: Ticker symbol. Example: "INFY"
        exchange: "NSE" or "BSE"

    Returns:
        Dict with ESG scores and ratings, or {"error": "ESG data not available"}.
    """
    try:
        ticker = _build_ticker(symbol, exchange)
        esg = ticker.sustainability
        
        if esg is None or esg.empty:
            return {"error": "ESG data not available for this ticker.", "symbol": symbol}
            
        data = sanitize_dataframe(esg)
        return {"symbol": symbol, "data": data}
        
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


def get_upcoming_events(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch upcoming earnings announcement dates and ex-dividend dates.

    The calendar dict from yfinance contains datetime.date objects which
    are not JSON serializable. We convert every value that is a date or
    datetime to an ISO string.

    Args:
        symbol: Ticker symbol. Example: "TCS"
        exchange: "NSE" or "BSE"

    Returns:
        Dict of calendar events with ISO-formatted dates.
        Keys vary by ticker but commonly include: Earnings Date, Ex-Dividend Date.
    """
    try:
        ticker = _build_ticker(symbol, exchange)
        cal = ticker.calendar
        
        if cal is None or not isinstance(cal, dict):
            return {"error": "No calendar data", "symbol": symbol}
            
        clean_cal = {"symbol": symbol}
        
        for key, value in cal.items():
            if isinstance(value, (pd.Timestamp, datetime.date, datetime.datetime)):
                clean_cal[key] = value.isoformat()
            elif isinstance(value, list):
                clean_cal[key] = [
                    v.isoformat() if isinstance(v, (pd.Timestamp, datetime.date, datetime.datetime)) else v 
                    for v in value
                ]
            else:
                clean_cal[key] = value
                
        return clean_cal
        
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


if __name__ == "__main__":
    import json

    def test_and_print(test_name: str, func, *args, **kwargs):
        print(f"\n{'='*40}")
        print(f"TESTING: {test_name}")
        print(f"{'='*40}")
        
        result = func(*args, **kwargs)
        
        try:
            # The ultimate test: Will it serialize to JSON?
            # We truncate the output to 500 characters so it doesn't flood your terminal.
            json_str = json.dumps(result, indent=2)
            if len(json_str) > 500:
                print(json_str[:500] + "\n... [TRUNCATED]")
            else:
                print(json_str)
            print("[SUCCESS] JSON Serializable")
        except TypeError as e:
            print(f"[ERROR] JSON SERIALIZATION FAILED: {e}")
            print("Raw Data:", result)

    # 1. Test Stock Info
    test_and_print("get_stock_info ('TCS', 'NSE')", get_stock_info, "TCS", "NSE")

    # 2. Test Historical Data (5 days to keep it brief)
    test_and_print("get_stock_history ('WIPRO', 'NSE', period='5d')", get_stock_history, "WIPRO", "NSE", period="5d")

    # 3. Test Financials (Income Statement)
    test_and_print("get_financials ('RELIANCE', 'NSE', income)", get_financials, "RELIANCE", "NSE", statement="income")

    # 4. Test Corporate Actions
    test_and_print("get_corporate_actions ('ITC', 'NSE')", get_corporate_actions, "ITC", "NSE")

    # 5. Test Analyst Data
    test_and_print("get_analyst_data ('SBIN', 'NSE')", get_analyst_data, "SBIN", "NSE")

    # 6. Test Shareholders
    test_and_print("get_holders ('HDFCBANK', 'NSE')", get_holders, "HDFCBANK", "NSE")

    # 7. Test ESG Data
    test_and_print("get_esg_data ('INFY', 'NSE')", get_esg_data, "INFY", "NSE")

    # 8. Test Upcoming Events
    test_and_print("get_upcoming_events ('TCS', 'NSE')", get_upcoming_events, "TCS", "NSE")

    # 9. Test Error Handling (Fake Ticker)
    test_and_print("Error Handling ('FAKETICKER99', 'NSE')", get_stock_info, "FAKETICKER99", "NSE")
