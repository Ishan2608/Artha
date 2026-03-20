# Phase 2 — Training a Custom Stock Forecasting Model

## Overview

The goal is to replace the Chronos zero-shot model in `tools/ts_model.py` with a model
you trained yourself on Indian stock data. The function signature stays identical —
only the internals of `ts_model.py` change.

The pipeline has four stages:

```
Raw price data  →  Cleaning  →  Feature engineering  →  Sequences  →  Model
```

---

## 1. Where to Get Data

### Option A — External Datasets (ready-made, no engineering)

| Source | What you get | Free? | Notes |
|---|---|---|---|
| **Kaggle** | Pre-downloaded NIFTY/BSE CSVs | Yes | Search "NSE historical data". Good for quick starts but may be stale. |
| **NSE India** | Official NIFTY index and stock CSVs | Yes | `nseindia.com` → Market Data → Download. Requires manual browser download. |
| **BSE India** | BSE listed stock CSVs | Yes | `bseindia.com` → Market Data. Same manual process. |
| **Quandl / Nasdaq Data Link** | Clean historical data API | Freemium | Indian equities coverage is limited on free tier. |
| **Alpha Vantage** | OHLCV API, 25 req/day free | Freemium | Covers NSE. Slow on free tier. |

**When to use:** If you want to skip the fetching step and get straight to model building.
The downside is stale data, inconsistent formatting, and no control over the date range.

### Option B — Engineer It Yourself with yfinance (recommended)

You already have `tools/stock_data.py` and `get_stock_history()`. Use that.

Advantages over external datasets:
- Always fresh — fetch any date range on demand
- Consistent format — already sanitized by your `formatters.py`
- Scalable — fetch one stock or all NIFTY 50 with a loop
- No manual downloads or API registrations

This is what `ml/data_pipeline.py` is built for.

---

## 2. Deciding What to Train On

Before writing any code, decide the scope:

**Single stock (start here)**
Train on TCS or WIPRO. One ticker, 5 years of daily OHLCV. Fast to iterate.
This is the right starting point — get the pipeline working before scaling up.

**Sector basket**
Train on 5–10 stocks from the same sector (e.g. all IT stocks).
The model sees more patterns but training takes longer.

**NIFTY 50 (Phase 2 final goal)**
Train on all 50 constituents. Best generalization.
Requires a loop over tickers and careful handling of missing data.

**Recommended starting ticker:** `TCS` (NSE) — liquid, long history, well-behaved price series.

---

## 3. Fetching and Storing the Data

### 3.1 Fetching via `get_stock_history()`

Your existing function returns a clean dict. Convert it to a DataFrame for ML use:

```python
import pandas as pd
from tools.stock_data import get_stock_history

def fetch_ohlcv(symbol: str, exchange: str = "NSE", period: str = "5y") -> pd.DataFrame:
    """
    Fetch OHLCV for a single stock and return as a clean DataFrame.
    Index: DatetimeIndex. Columns: open, high, low, close, volume.
    """
    raw = get_stock_history(symbol, exchange, period=period, interval="1d")
    if "error" in raw:
        raise ValueError(f"Failed to fetch {symbol}: {raw['error']}")

    df = pd.DataFrame({
        "open":   raw["open"],
        "high":   raw["high"],
        "low":    raw["low"],
        "close":  raw["close"],
        "volume": raw["volume"],
    }, index=pd.to_datetime(raw["dates"]))

    df.index.name = "date"
    return df
```

### 3.2 Fetching Multiple Stocks (NIFTY 50)

```python
NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BAJFINANCE", "BHARTIARTL",
    "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO", "NESTLEIND",
    # ... add remaining 30
]

def fetch_nifty50(period: str = "5y") -> dict[str, pd.DataFrame]:
    """
    Fetch OHLCV for all NIFTY 50 stocks.
    Returns {"TCS": df, "INFY": df, ...}. Skips failed tickers with a warning.
    """
    import sys
    data = {}
    for symbol in NIFTY_50:
        try:
            data[symbol] = fetch_ohlcv(symbol, period=period)
            print(f"  ✔ {symbol}: {len(data[symbol])} rows", file=sys.stderr)
        except Exception as e:
            print(f"  ✖ {symbol}: {e}", file=sys.stderr)
    return data
```

### 3.3 Saving to Disk

Fetching takes time. Cache locally so you don't re-fetch every training run:

```python
import os

def save_ohlcv(df: pd.DataFrame, symbol: str, folder: str = "ml/data") -> None:
    os.makedirs(folder, exist_ok=True)
    df.to_csv(os.path.join(folder, f"{symbol}.csv"))

def load_ohlcv(symbol: str, folder: str = "ml/data") -> pd.DataFrame:
    path = os.path.join(folder, f"{symbol}.csv")
    return pd.read_csv(path, index_col="date", parse_dates=True)
```

---

## 4. Data Cleaning

Raw yfinance data is mostly clean, but you must handle these:

### 4.1 Missing Values

```python
def clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle missing values in OHLCV data.

    Approach:
    - Forward fill gaps of 1–2 days (weekends, minor holidays).
    - Drop rows where close is still NaN after forward fill (data outage, stock suspension).
    - Drop rows where volume is 0 (non-trading days that slipped through).
    """
    df = df.copy()
    df = df.ffill(limit=2)          # fill short gaps
    df = df.dropna(subset=["close"])
    df = df[df["volume"] > 0]
    return df
```

### 4.2 Adjusted Prices

yfinance returns adjusted close by default (adjusted for splits and dividends).
For OHLC, it returns unadjusted values. For training, use the adjusted close only
or adjust all OHLC values by the same ratio. The simplest approach: use only `close`
as the target column and all OHLCV columns as features — yfinance handles the
close adjustment automatically.

### 4.3 Outliers

Indian stocks can have circuit breaker events (±20% in a day). These are real events,
not data errors — do NOT remove them. Your model should learn that large moves exist.

```python
def check_outliers(df: pd.DataFrame, threshold: float = 0.25) -> pd.DataFrame:
    """
    Print rows where daily return exceeds threshold. Does NOT remove them.
    Use for inspection only — circuit breaker events are real data points.
    """
    returns = df["close"].pct_change().abs()
    suspect = df[returns > threshold]
    if not suspect.empty:
        print(f"  Large moves found ({len(suspect)} rows):")
        print(suspect[["close"]])
    return df   # return unchanged
```

### 4.4 Date Alignment (Multi-stock)

When training on multiple stocks, align them to a common trading calendar:

```python
def align_to_common_dates(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Find dates where ALL stocks have data. Drop the rest.
    Handles cases where one stock listed later than others.
    """
    common_index = dfs[list(dfs.keys())[0]].index
    for df in dfs.values():
        common_index = common_index.intersection(df.index)
    return {sym: df.loc[common_index] for sym, df in dfs.items()}
```

---

## 5. Feature Engineering

Raw OHLCV alone is usable but adding technical indicators significantly improves
model signal. All features must be computable from price and volume data only —
no external data sources needed.

### 5.1 Features to Add

```python
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicator features to the OHLCV DataFrame.
    All NaN rows produced by rolling windows are dropped at the end.
    """
    df = df.copy()

    # Returns
    df["return_1d"]  = df["close"].pct_change(1)
    df["return_5d"]  = df["close"].pct_change(5)
    df["return_20d"] = df["close"].pct_change(20)

    # Moving averages
    df["sma_20"]  = df["close"].rolling(20).mean()
    df["sma_50"]  = df["close"].rolling(50).mean()
    df["ema_12"]  = df["close"].ewm(span=12, adjust=False).mean()
    df["ema_26"]  = df["close"].ewm(span=26, adjust=False).mean()

    # MACD
    df["macd"]        = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]

    # RSI (14-day)
    delta     = df["close"].diff()
    gain      = delta.clip(lower=0).rolling(14).mean()
    loss      = (-delta.clip(upper=0)).rolling(14).mean()
    rs        = gain / loss.replace(0, float("nan"))
    df["rsi"] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    rolling_std     = df["close"].rolling(20).std()
    df["bb_upper"]  = df["sma_20"] + 2 * rolling_std
    df["bb_lower"]  = df["sma_20"] - 2 * rolling_std
    df["bb_width"]  = (df["bb_upper"] - df["bb_lower"]) / df["sma_20"]
    df["bb_pct"]    = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

    # Volatility
    df["volatility_20"] = df["return_1d"].rolling(20).std()

    # Volume
    df["volume_sma_20"] = df["volume"].rolling(20).mean()
    df["volume_ratio"]  = df["volume"] / df["volume_sma_20"].replace(0, float("nan"))

    # Candle shape
    df["body"]        = (df["close"] - df["open"]).abs() / df["open"]
    df["upper_wick"]  = (df["high"] - df[["open", "close"]].max(axis=1)) / df["open"]
    df["lower_wick"]  = (df[["open", "close"]].min(axis=1) - df["low"]) / df["open"]

    # Drop NaN rows created by rolling windows
    df = df.dropna()
    return df
```

### 5.2 Which Features to Use for Training

Start simple. Add complexity only if the model underfits.

| Stage | Feature set |
|---|---|
| Baseline | `close`, `volume` only |
| Standard | OHLCV + returns + SMA + RSI |
| Full | All features from `add_features()` |

Define the feature set in `DataPipeline.__init__` as a list of column names.
The model input size must match `len(features)`.

---

## 6. Normalization

### Why normalize?

Neural networks are sensitive to input scale. A raw close price of ₹3800 and a
volume of 2,000,000 in the same input vector will cause the network to ignore the
price signal. Normalization puts all features on the same scale.

### MinMaxScaler (used in DataPipeline)

```python
from sklearn.preprocessing import MinMaxScaler

scaler = MinMaxScaler(feature_range=(0, 1))

# CRITICAL: fit ONLY on training data
train_end = int(len(feature_array) * 0.70)
scaler.fit(feature_array[:train_end])

# Transform the FULL array using the training-fitted scaler
scaled = scaler.transform(feature_array)
```

**Why only fit on training data?**
If you fit on the full dataset, the scaler learns the min/max of the test set.
The model then effectively "sees" future data during training — this is data leakage
and will give you falsely optimistic evaluation metrics.

### Alternative: RobustScaler

If the price series has extreme outliers (circuit breaker events), `RobustScaler`
(scales by median and IQR rather than min/max) is more stable:

```python
from sklearn.preprocessing import RobustScaler
scaler = RobustScaler()
```

Start with `MinMaxScaler`. Switch to `RobustScaler` only if training is unstable.

---

## 7. Sliding Window Sequences

The model learns by seeing `input_len` days of history and predicting `output_len` future closes.
The sliding window creates these training examples from the time series:

```
Day 1–60   → predict Day 61–70    (sample 0)
Day 2–61   → predict Day 62–71    (sample 1)
Day 3–62   → predict Day 63–72    (sample 2)
...
```

```python
def create_sequences(data: np.ndarray, input_len: int, output_len: int,
                     close_idx: int) -> tuple[np.ndarray, np.ndarray]:
    """
    data: scaled array of shape [T, num_features]
    close_idx: index of the close column in the feature list

    Returns:
        X: [num_samples, input_len, num_features]
        y: [num_samples, output_len]  (close prices only)
    """
    X, y = [], []
    for i in range(len(data) - input_len - output_len):
        X.append(data[i : i + input_len])
        y.append(data[i + input_len : i + input_len + output_len, close_idx])
    return np.array(X), np.array(y)
```

---

## 8. Train / Validation / Test Split

**Always split chronologically. Never shuffle a time series.**

```
|─────── 70% train ───────|── 15% val ──|── 15% test ──|
  Day 1                                              Day N
```

The split is made on the raw time axis **before** creating sequences.
This guarantees no window in val or test overlaps with the training data.

```python
n         = len(scaled_data)
train_end = int(n * 0.70)
val_end   = int(n * 0.85)   # 0.70 + 0.15

train_data = scaled_data[:train_end]
val_data   = scaled_data[train_end:val_end]
test_data  = scaled_data[val_end:]
```

**Minimum data required:**
With `input_len=60` and `output_len=10`, you need at least `60 + 10 + 1 = 71` rows
per split. 5 years of daily data (~1250 rows) gives:
- Train: ~875 rows → ~805 sequences
- Val:   ~187 rows → ~117 sequences
- Test:  ~187 rows → ~117 sequences

---

## 9. Final DataPipeline Integration

```python
# Usage in a training script
pipeline = DataPipeline(
    symbol="TCS",
    exchange="NSE",
    input_len=60,
    output_len=10,
    features=["open", "high", "low", "close", "volume",
              "return_1d", "sma_20", "rsi", "macd", "volume_ratio"],
)

pipeline.fetch_and_prepare(period="5y")   # fetches, cleans, adds features, normalizes
splits = pipeline.get_splits()

X_train, y_train = splits["train"]
X_val,   y_val   = splits["val"]
X_test,  y_test  = splits["test"]

print(f"Train: {X_train.shape}  Val: {X_val.shape}  Test: {X_test.shape}")
# Expected: Train: (805, 60, 10)  Val: (117, 60, 10)  Test: (117, 60, 10)
```

---

## 10. What Goes in `ml/data_pipeline.py`

The complete `DataPipeline` class should contain all of the above:

| Method | Responsibility |
|---|---|
| `__init__` | Store config. Init scaler. |
| `fetch_and_prepare(period)` | Fetch via yfinance → clean → add features → normalize. |
| `_create_sequences(data)` | Sliding window → (X, y) arrays. |
| `get_splits()` | Chronological split → call `_create_sequences` on each slice. |
| `inverse_transform_predictions(scaled)` | Convert model output back to rupee prices. |

Keep data fetching and cleaning **inside** `DataPipeline`. Do not fetch raw data
outside the class — the pipeline owns the full data preparation contract.

---

## 11. Checklist Before Training

- [ ] At least 5 years of daily OHLCV fetched and saved to `ml/data/`
- [ ] No NaN values remaining after cleaning
- [ ] Scaler fitted only on training slice
- [ ] Sequences created from each split independently
- [ ] `X_train.shape` is `(N, input_len, num_features)` — confirm with print
- [ ] `y_train.shape` is `(N, output_len)` — confirm with print
- [ ] No data leakage: test dates are strictly after train dates
- [ ] `inverse_transform_predictions()` tested: scaled output → rupee prices correctly
