"""
ts_model.py — Stock price forecasting.

Two backends are available — only one is active at a time:

  [ACTIVE]   Custom Transformer model  (ml/custom/nifty50_model/)
  [INACTIVE] Amazon Chronos T5 Tiny    (commented-out section at the bottom)

To revert to Chronos:
  1. Comment out the entire CUSTOM MODEL section.
  2. Uncomment the CHRONOS section at the bottom.
  No other files need to change.
"""

import os
import numpy as np

# ─── Path helpers ─────────────────────────────────────────────────────────────
_HERE         = os.path.dirname(os.path.abspath(__file__))   # …/tools/
_PROJECT_ROOT = os.path.dirname(_HERE)                        # project root
_MODEL_DIR    = os.path.join(_PROJECT_ROOT, "ml", "custom", "nifty50_model")


def _load_checkpoint(path: str) -> dict:
    """
    Load a PyTorch checkpoint from either a .pt file or an unpacked directory.

    Background
    ----------
    torch.save() writes a zip archive (usually named *.pt). The internal zip
    root is always called 'archive/', so a saved checkpoint contains entries:
        archive/data.pkl
        archive/data/0
        archive/byteorder  ...

    When that zip is extracted into a folder the directory holds those same
    files *without* the 'archive/' prefix:
        nifty50_model/data.pkl
        nifty50_model/data/
        nifty50_model/byteorder  ...

    On Linux/macOS torch.load(directory_path) falls back to the legacy loader
    after an OSError. On **Windows** the OS returns ERROR_ACCESS_DENIED
    (errno 13) when trying to open a directory as a file — which is the
    exact "Permission denied" error seen in the test output.

    Fix: when the path is a directory, repack its contents into an in-memory
    zip under the 'archive/' root that PyTorch expects, then pass the BytesIO
    to torch.load. The resulting checkpoint dict is identical to loading from
    the original .pt file.
    """
    import torch

    if not os.path.isdir(path):
        # Ordinary .pt file — load directly (unchanged behaviour).
        return torch.load(path, map_location=torch.device("cpu"), weights_only=False)

    # Directory case: repack into an in-memory zip with the 'archive/' root.
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for root, _dirs, files in os.walk(path):
            for fname in sorted(files):               # sorted for determinism
                fpath = os.path.join(root, fname)
                # Forward-slash relative path — required inside zip on all OS.
                rel   = os.path.relpath(fpath, path).replace("\\", "/")
                zf.write(fpath, f"archive/{rel}")

    buf.seek(0)
    return torch.load(buf, map_location=torch.device("cpu"), weights_only=False)



# ═════════════════════════════════════════════════════════════════════════════
# CUSTOM MODEL  (Active)
# ═════════════════════════════════════════════════════════════════════════════

# ── Constants — must match the training notebook exactly ──────────────────────
_INPUT_LEN   = 120   # timesteps fed into the model as the look-back window
_OUTPUT_LEN  = 5     # days the model predicts in one forward pass (fixed)
_INPUT_FEATS = 15    # features per timestep
_NUM_STOCKS  = 48    # number of stocks the model was trained on (embedding table size)

# Stocks that have a dedicated learned embedding in the checkpoint.
# Order matters — index i must match the embedding row used during training.
_TICKERS = [
    "RELIANCE.NS", "TCS.NS",       "HDFCBANK.NS",  "ICICIBANK.NS",  "KOTAKBANK.NS",
    "SBIN.NS",     "AXISBANK.NS",  "BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS",
    "SBILIFE.NS",  "ITC.NS",       "HINDUNILVR.NS", "NESTLEIND.NS",  "TATACONSUM.NS",
    "BRITANNIA.NS","ASIANPAINT.NS","ULTRACEMCO.NS", "GRASIM.NS",     "LT.NS",
    "ADANIENT.NS", "ADANIPORTS.NS","BHARTIARTL.NS", "INDUSINDBK.NS", "MARUTI.NS",
    "HEROMOTOCO.NS","EICHERMOT.NS","BAJAJ-AUTO.NS", "POWERGRID.NS",  "NTPC.NS",
    "ONGC.NS",     "COALINDIA.NS", "JSWSTEEL.NS",   "TATASTEEL.NS",  "HCLTECH.NS",
    "WIPRO.NS",    "TECHM.NS",     "INFY.NS",        "CIPLA.NS",     "DRREDDY.NS",
    "APOLLOHOSP.NS","SUNPHARMA.NS","DIVISLAB.NS",    "LTIM.NS",      "TITAN.NS",
    "INDIGO.NS",   "TRENT.NS",     "JIOFIN.NS",
]
_TICKER_TO_ID = {t: i for i, t in enumerate(_TICKERS)}

# ── Lazy-loaded singletons ────────────────────────────────────────────────────
_custom_model    = None   # loaded Model instance
_custom_scalers  = {}     # {yf_ticker: fitted MinMaxScaler} from checkpoint
_custom_mean_emb = None   # mean of all embedding rows — used for zero-shot stocks


def _get_custom_model():
    """
    Lazy-load the custom Transformer from ml/custom/nifty50_model/.

    Returns:
        (model, scalers, mean_emb)
          model     : nn.Module, already in eval() mode on CPU
          scalers   : dict {yf_ticker -> MinMaxScaler} from checkpoint
          mean_emb  : Tensor (1, 64) — mean embedding for unseen stocks
    """
    global _custom_model, _custom_scalers, _custom_mean_emb

    if _custom_model is not None:
        return _custom_model, _custom_scalers, _custom_mean_emb

    import torch
    import torch.nn as nn

    # ── Architecture — must be identical to the training notebook ─────────────
    class PositionalEncoding(nn.Module):
        def __init__(self, d_model):
            super().__init__()
            pe  = torch.zeros(500, d_model)
            pos = torch.arange(0, 500).unsqueeze(1)
            div = torch.exp(torch.arange(0, d_model, 2) * (-np.log(10000.0) / d_model))
            pe[:, 0::2] = torch.sin(pos * div)
            pe[:, 1::2] = torch.cos(pos * div)
            self.pe = pe.unsqueeze(0)

        def forward(self, x):
            return x + self.pe[:, :x.size(1)].to(x.device)

    class Model(nn.Module):
        def __init__(self, input_size, num_stocks):
            super().__init__()
            self.use_embedding = num_stocks > 1
            self.proj  = nn.Linear(input_size, 64)
            self.pos   = PositionalEncoding(64)
            if self.use_embedding:
                self.embed = nn.Embedding(num_stocks, 64)
            enc        = nn.TransformerEncoderLayer(d_model=64, nhead=4, batch_first=True)
            self.trans = nn.TransformerEncoder(enc, num_layers=2)
            self.fc    = nn.Linear(64, _OUTPUT_LEN)

        def forward(self, x, sid=None):
            x = self.proj(x)
            x = self.pos(x)
            if self.use_embedding and sid is not None:
                x = x + self.embed(sid).unsqueeze(1)
            x = self.trans(x)
            return self.fc(x[:, -1, :])

    # ── Load checkpoint ────────────────────────────────────────────────────────
    if not os.path.exists(_MODEL_DIR):
        raise FileNotFoundError(
            f"Custom model not found at '{_MODEL_DIR}'. "
            "Ensure ml/custom/nifty50_model/ exists relative to the project root."
        )

    print("  [Forecasting] Loading custom Transformer model...")
    checkpoint = _load_checkpoint(_MODEL_DIR)

    input_size = checkpoint.get("input_size", _INPUT_FEATS)
    model      = Model(input_size, _NUM_STOCKS)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    scalers = checkpoint.get("scalers", {})

    # Pre-compute mean embedding for zero-shot (unseen) stocks.
    # This is the same approach used in the training notebook's BATCH_UNSEEN section.
    mean_emb = None
    if model.use_embedding:
        mean_emb = model.embed.weight.mean(dim=0, keepdim=True).cpu().detach().clone()

    _custom_model    = model
    _custom_scalers  = scalers
    _custom_mean_emb = mean_emb

    known = sum(1 for t in _TICKERS if t in scalers)
    print(f"  [Forecasting] Model ready — input_size={input_size}, "
          f"{known}/{_NUM_STOCKS} scalers in checkpoint.")
    return _custom_model, _custom_scalers, _custom_mean_emb


def _build_features(raw_df):
    """
    Replicate DataPipeline.add_features() from the training notebook exactly.

    Input  : DataFrame with columns [open, high, low, close, volume]
    Output : DataFrame with 15 columns in the order the model was trained on,
             NaN rows dropped.

    Feature order (columns 0–14):
      0  open        1  high         2  low          3  close       4  volume
      5  return_1d   6  return_5d    7  sma_20       8  ema_12      9  ema_26
      10 macd        11 rsi          12 bb_width     13 volatility  14 volume_ratio
    """
    df = raw_df.copy()
    df["return_1d"]    = df["close"].pct_change()
    df["return_5d"]    = df["close"].pct_change(5)
    df["sma_20"]       = df["close"].rolling(20).mean()
    df["ema_12"]       = df["close"].ewm(span=12).mean()
    df["ema_26"]       = df["close"].ewm(span=26).mean()
    df["macd"]         = df["ema_12"] - df["ema_26"]
    delta              = df["close"].diff()
    gain               = delta.clip(lower=0).rolling(14).mean()
    loss               = (-delta.clip(upper=0)).rolling(14).mean()
    rs                 = gain / loss.replace(0, np.nan)
    df["rsi"]          = 100 - (100 / (1 + rs))
    std                = df["close"].rolling(20).std()
    df["bb_width"]     = (2 * std) / df["sma_20"]
    df["volatility"]   = df["return_1d"].rolling(20).std()
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()
    df = df.replace([np.inf, -np.inf], np.nan)
    return df.dropna()


def predict_stock_prices(symbol: str, exchange: str = "NSE", horizon_days: int = 10) -> dict:
    """
    Forecast the next N closing prices using the custom Transformer model.

    The model always produces exactly _OUTPUT_LEN (5) days per forward pass.
      - If horizon_days <= 5 : forecast is truncated to horizon_days values.
      - If horizon_days >  5 : only 5 days are returned (model limit); the
                                note field documents this clearly.

    The returned low/high bands are a pragmatic ±2% envelope around the point
    forecast — the custom model is deterministic and has no built-in uncertainty.
    This keeps the output schema identical to the Chronos version so callers
    (agent.py, test_tools.py) require zero changes.

    Args:
        symbol       : NSE/BSE ticker without exchange suffix (e.g. "TCS").
        exchange     : "NSE" (default) or "BSE".
        horizon_days : Requested forecast length in trading days.

    Returns:
        {
          "symbol", "chart_type", "historical_dates", "historical_closes",
          "forecast_median", "forecast_low", "forecast_high",
          "horizon_days", "note"
        }
        On error: {"error": <str>, "symbol": <symbol>}
    """
    import torch
    import yfinance as yf
    import pandas as pd
    from sklearn.preprocessing import MinMaxScaler

    try:
        model, saved_scalers, mean_emb = _get_custom_model()

        # ── Build yfinance ticker ──────────────────────────────────────────────
        suffix     = ".NS" if exchange.upper() == "NSE" else ".BO"
        yf_ticker  = f"{symbol.upper()}{suffix}"

        # ── Fetch OHLCV ────────────────────────────────────────────────────────
        # Feature engineering needs ~26 bars of warm-up on top of INPUT_LEN (120),
        # so 1 year (~252 trading days) is sufficient with margin to spare.
        raw = yf.download(
            yf_ticker, period="1y", interval="1d",
            progress=False, auto_adjust=True,
        )
        if raw.empty:
            return {"error": f"No price data returned for {yf_ticker}.", "symbol": symbol}

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw.rename(columns=str.lower)
        raw = raw[["open", "high", "low", "close", "volume"]].dropna()

        # ── Feature engineering ────────────────────────────────────────────────
        df = _build_features(raw)

        if len(df) < _INPUT_LEN:
            return {
                "error": (
                    f"Insufficient history after feature engineering: "
                    f"got {len(df)} valid rows, need at least {_INPUT_LEN}."
                ),
                "symbol": symbol,
            }

        # ── Scale ──────────────────────────────────────────────────────────────
        if yf_ticker in saved_scalers:
            # Known stock: use the scaler the model was trained with.
            # Fitting a new scaler would shift the distribution and degrade accuracy.
            scaler = saved_scalers[yf_ticker]
            scaled = scaler.transform(df.values)
        else:
            # Unseen stock: fit a fresh scaler on this stock's own data (zero-shot).
            scaler = MinMaxScaler()
            scaled = scaler.fit_transform(df.values)

        # ── Build input tensor: last INPUT_LEN rows ────────────────────────────
        seq = scaled[-_INPUT_LEN:]                                        # (120, 15)
        x_t = torch.tensor(seq, dtype=torch.float32).unsqueeze(0)        # (1, 120, 15)

        # ── Forward pass ──────────────────────────────────────────────────────
        model.eval()
        with torch.no_grad():
            xp = model.proj(x_t)
            xp = model.pos(xp)

            if yf_ticker in _TICKER_TO_ID:
                # Known stock → use its dedicated embedding row
                sid = torch.tensor([_TICKER_TO_ID[yf_ticker]], dtype=torch.long)
                xp  = xp + model.embed(sid).unsqueeze(1)
            elif mean_emb is not None:
                # Unseen stock → mean of all embedding rows (zero-shot transfer)
                xp  = xp + mean_emb.unsqueeze(1)

            xp         = model.trans(xp)
            fut_scaled = model.fc(xp[:, -1, :]).cpu().numpy()[0]          # (5,)

        # ── Inverse-transform: recover real price values ───────────────────────
        # The model outputs scaled close values. We need to place them in column 3
        # (close) of a dummy array and call inverse_transform to undo the scaler.
        dummy       = np.zeros((_OUTPUT_LEN, _INPUT_FEATS))
        dummy[:, 3] = fut_scaled                                          # col 3 = close
        fut_prices_arr = scaler.inverse_transform(dummy)[:, 3]           # (5,) real prices

        # ── Clamp to requested horizon ─────────────────────────────────────────
        actual_horizon = min(horizon_days, _OUTPUT_LEN)
        fut_prices     = [round(float(p), 2) for p in fut_prices_arr[:actual_horizon]]

        # ── Historical context for the chart ──────────────────────────────────
        # Last 60 bars gives a visually comfortable history window on the frontend.
        historical_dates  = [str(d.date()) for d in df.index[-60:]]
        historical_closes = [round(float(v), 2) for v in df["close"].values[-60:]]

        # ── Confidence bands (±2% symmetric envelope) ─────────────────────────
        # The custom model produces a single point forecast per day — no quantiles.
        # A fixed ±2% band is a pragmatic placeholder that keeps the output schema
        # backward-compatible with the Chronos version's low/median/high triplet.
        forecast_low  = [round(p * 0.98, 2) for p in fut_prices]
        forecast_high = [round(p * 1.02, 2) for p in fut_prices]

        horizon_note = (
            f" Note: this model always predicts exactly {_OUTPUT_LEN} trading days; "
            f"only the first {actual_horizon} day(s) are shown as requested."
            if horizon_days > _OUTPUT_LEN else ""
        )
        embedding_note = (
            " Known stock — dedicated embedding used."
            if yf_ticker in _TICKER_TO_ID
            else " Unseen stock — zero-shot mean embedding used."
        )

        return {
            "symbol":            symbol,
            "chart_type":        "forecast",
            "historical_dates":  historical_dates,
            "historical_closes": historical_closes,
            "forecast_median":   fut_prices,
            "forecast_low":      forecast_low,
            "forecast_high":     forecast_high,
            "horizon_days":      actual_horizon,
            "note": (
                "Forecast produced by a custom Transformer model trained on Nifty-50 data. "
                "Low/high bands represent ±2% around the point forecast. "
                "This model does not account for news, earnings, or macro events. "
                "This is for educational purposes and not financial advice."
                + embedding_note
                + horizon_note
            ),
        }

    except Exception as e:
        return {"error": str(e), "symbol": symbol}


# ═════════════════════════════════════════════════════════════════════════════
# CHRONOS BACKEND  (Inactive — uncomment this entire section to revert)
# ═════════════════════════════════════════════════════════════════════════════

# To reactivate Chronos:
#   1. Comment out the entire CUSTOM MODEL section above (everything between
#      the two "═══" banners, from _INPUT_LEN to the end of predict_stock_prices).
#   2. Uncomment everything below.

# _pipeline = None
#
#
# def _get_pipeline():
#     """
#     Lazy-load the Amazon Chronos T5 Tiny forecasting pipeline.
#     torch and chronos are imported here, not at module level.
#     """
#     global _pipeline
#     if _pipeline is None:
#         import torch  # noqa: F401  (needed by chronos internals)
#         from chronos import BaseChronosPipeline
#         print("  [Forecasting] Loading Chronos T5 Tiny model on CPU...")
#         # Force CPU: AMD GPUs are not supported by PyTorch CUDA.
#         _pipeline = BaseChronosPipeline.from_pretrained(
#             "amazon/chronos-t5-tiny",
#             device_map="cpu",
#         )
#     return _pipeline
#
#
# def predict_stock_prices(symbol: str, exchange: str = "NSE", horizon_days: int = 10) -> dict:
#     """
#     Forecast the next N closing prices for a stock using Amazon Chronos.
#
#     Args:
#         symbol       : NSE/BSE ticker without suffix.
#         exchange     : 'NSE' or 'BSE'.
#         horizon_days : Number of trading days to forecast (recommended 5–20).
#
#     Returns:
#         Dict with historical_dates, historical_closes, forecast_median,
#         forecast_low, forecast_high, horizon_days, and a note.
#         On error, returns {"error": str, "symbol": symbol}.
#     """
#     import torch
#     from tools.stock_data import get_stock_history
#
#     try:
#         history = get_stock_history(symbol, exchange, period="3mo", interval="1d")
#         if "error" in history:
#             return history
#
#         closes           = history["close"]
#         historical_dates = history["dates"]
#
#         context  = torch.tensor(closes, dtype=torch.float32)
#         pipeline = _get_pipeline()
#
#         quantiles, _ = pipeline.predict_quantiles(
#             inputs=context,
#             prediction_length=horizon_days,
#             quantile_levels=[0.1, 0.5, 0.9],
#         )
#
#         # quantiles shape: [batch=1, horizon, levels=3]
#         forecast_low    = [round(x, 2) for x in quantiles[0, :, 0].tolist()]
#         forecast_median = [round(x, 2) for x in quantiles[0, :, 1].tolist()]
#         forecast_high   = [round(x, 2) for x in quantiles[0, :, 2].tolist()]
#
#         return {
#             "symbol":            symbol,
#             "chart_type":        "forecast",
#             "historical_dates":  historical_dates,
#             "historical_closes": closes,
#             "forecast_median":   forecast_median,
#             "forecast_low":      forecast_low,
#             "forecast_high":     forecast_high,
#             "horizon_days":      horizon_days,
#             "note": (
#                 "This forecast is generated by a statistical model using price patterns only. "
#                 "It does not account for news, earnings, or macro events. "
#                 "This is for educational purposes and not financial advice."
#             ),
#         }
#
#     except Exception as e:
#         return {"error": str(e), "symbol": symbol}
