import pandas as pd
import numpy as np
from typing import Any

def sanitize_dataframe(df: pd.DataFrame) -> dict[str, list]:
  """
  Convert a pandas dataframe into a JSON safe dict of lists.

  The problem: yfinance DataFrames contain NaN values. numpy float64 and int64 
  (not JSON serializable), and pandas Timestamps (also not JSON serialization).
  FastAPI's json encoder will crash on all of these.

  The Solution: iterate every cell, detect the type, convert to plain Python.

  Args:
    df: Any pandas DataFrame from yfinance - history, financials, balance sheet, etc.

  Returns:
    Dict where keys are column name strings and values are plain Python lists.
    Timestamps become ISO Strings. NaN becomes None. numpy types becomes int/float.
    Example: {"Date": ["2024-01-01", ...], "Close": [1234.5, None, 1238.0, ...]}
  """
  # turn index, usually Date into regular column. Usually the Date Column.
  df.reset_index()
  # convert all column names to string because some yfinance financials have Timestamp columns names
  df.columns = [str(c) for c in df.columns]

  results = {}
  for col in df.columns:
    clean_col = []
    
    for value in df[col]:
      if isinstance(value, (pd.Timestamp, np.datetime64)):
        formatted = value.isoformat() if hasattr(value, 'isoformat') else str(value)
        clean_col.append(formatted)
      elif isinstance(value, float) and np.isnan(value):
        clean_col.append(None)
      elif isinstance(value, np.integer):
        clean_col.append(int(value))
      elif isinstance(value, np.floating):
        clean_col.append( round( float(value), 4 ) )
      else:
        clean_col.append(value)
        
    results[col] = clean_col
  return results


def sanitize_info_dict(info: dict) -> dict:
  """
  Clean a raw yfinance .info dictionary for JSON serialization.

  THe .info dict from yfinance has 150 keys, many of them have None or are irrelevant.
  This function uses a whitelist to return only the fields that matter with all values
  converted to plain Python types.

  Args:
    info: The raw dictionary from ticker.info. Call this ONCE per request - 
          every access to ticker.info triggers a network call.
  Returns:
    A clean flat dict. All values are str, int, float, or None.
  """
  WHITELIST = ["longName", "shortName", "currentPrice", "previousClose", "open",
     "dayHigh", "dayLow", "volume", "marketCap", "financialCurrency",
     "typeDisp", "exchange", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
     "fiftyTwoWeekChangePercent", "fiftyDayAverage", "twoHundredDayAverage",
     "trailingPE", "forwardPE", "priceToBook", "dividendYield",
     "targetMeanPrice", "targetHighPrice", "targetLowPrice", "recommendationKey", 
     "currentRatio", "debtToEquity", "returnOnEquity", "returnOnAssets", 
     "grossMargins", "operatingMargins", "profitMargins", "revenueGrowth", 
     "earningsGrowth", "totalRevenue", "totalDebt", "freeCashflow"
   ]

  result = {}
  for key in WHITELIST:
    value = info.get(key)
    if value is None: 
        result[key] = None
    elif isinstance(value, float) and np.isnan(value):
        result[key] = None
    elif isinstance(value, np.integer):
        result[key] = int(value)
    elif isinstance(value, np.floating):
        result[key] = round(float(value), 4)
    else:
        result[key] = value
  return result



def series_to_chart_arrays(dates: list, values: list) -> dict[str, list]:
    """
    Technical Definition:
    Packages two parallel lists (dates and values) into a standardized dictionary structure for frontend visualization. Ensures data integrity by raising a ValueError if the input arrays are of unequal length.

    Intuitive Explanation:
    This function acts as a final alignment check before sending time-series data to the user interface. It guarantees that every point on the x-axis (date) has a corresponding point on the y-axis (value), preventing chart rendering failures on the client side.

    Practical Example Context:
    Input: 
    dates = ["2026-01-15T00:00:00", "2026-02-15T00:00:00"]
    values = [1.5, 2.0]
    
    Output: 
    {"dates": ["2026-01-15T00:00:00", "2026-02-15T00:00:00"], "values": [1.5, 2.0]}
    """
    if len(dates) != len(values):
        raise ValueError(f"Data length mismatch: received {len(dates)} dates and {len(values)} values.")
    
    return {"dates": dates, "values": values}
