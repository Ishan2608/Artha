"""
utils/formatters.py — Data formatting and chart building

build_chart(data)  -> plotly Figure or None
  Converts the backend's data block into a Plotly figure.
  Handles: candlestick, forecast, line, bar, table types.

format_timestamp(iso_str) -> human-readable string
format_file_size(n_bytes)  -> "2.3 MB" etc.
"""

from __future__ import annotations
from datetime import datetime, timezone

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    _PLOTLY = True
except ImportError:
    _PLOTLY = False

from config import Theme


# ─────────────────────────────────────────────────────────────────────────────
# CHART BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _base_layout(title: str = "") -> dict:
    """Shared Plotly layout settings — Obsidian Terminal theme."""
    return dict(
        title=dict(text=title, font=dict(color=Theme.TEXT, size=14, family="JetBrains Mono")),
        paper_bgcolor=Theme.BG_CARD,
        plot_bgcolor=Theme.BG_SURFACE,
        font=dict(color=Theme.TEXT_DIM, family="JetBrains Mono", size=11),
        xaxis=dict(
            gridcolor=Theme.BORDER,
            linecolor=Theme.BORDER,
            tickfont=dict(color=Theme.TEXT_DIM),
            showgrid=True,
        ),
        yaxis=dict(
            gridcolor=Theme.BORDER,
            linecolor=Theme.BORDER,
            tickfont=dict(color=Theme.TEXT_DIM),
            showgrid=True,
        ),
        legend=dict(
            bgcolor=Theme.BG_CARD_2,
            bordercolor=Theme.BORDER,
            borderwidth=1,
            font=dict(color=Theme.TEXT),
        ),
        margin=dict(l=48, r=24, t=48, b=48),
        hoverlabel=dict(
            bgcolor=Theme.BG_CARD_2,
            bordercolor=Theme.TEAL,
            font=dict(color=Theme.TEXT, family="JetBrains Mono"),
        ),
    )


def _candlestick(data: dict):
    """Render OHLCV candlestick chart with volume bars."""
    if not _PLOTLY:
        return None

    has_volume = bool(data.get("volume"))
    fig = make_subplots(
        rows=2 if has_volume else 1,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25] if has_volume else [1],
    )

    fig.add_trace(
        go.Candlestick(
            x=data.get("dates", []),
            open=data.get("open", []),
            high=data.get("high", []),
            low=data.get("low", []),
            close=data.get("close", []),
            name=data.get("symbol", ""),
            increasing_line_color=Theme.TEAL,
            decreasing_line_color=Theme.ROSE,
            increasing_fillcolor=Theme.TEAL,
            decreasing_fillcolor=Theme.ROSE,
        ),
        row=1, col=1,
    )

    if has_volume:
        closes = data.get("close", [])
        opens  = data.get("open", [])
        colors = [
            Theme.TEAL if (c >= o) else Theme.ROSE
            for c, o in zip(closes, opens)
        ]
        fig.add_trace(
            go.Bar(
                x=data.get("dates", []),
                y=data.get("volume", []),
                name="Volume",
                marker_color=colors,
                opacity=0.5,
            ),
            row=2, col=1,
        )
        fig.update_yaxes(title_text="Volume", row=2, col=1,
                         title_font=dict(color=Theme.TEXT_DIM, size=10))

    layout = _base_layout(f"{data.get('symbol', 'Stock')} — Candlestick")
    layout["xaxis_rangeslider_visible"] = False
    fig.update_layout(**layout)
    return fig


def _forecast(data: dict):
    """Render historical + forecast ribbon chart."""
    if not _PLOTLY:
        return None

    fig = go.Figure()

    # Historical line
    hist_dates = data.get("historical_dates", [])
    hist_vals  = data.get("historical_values", [])
    if hist_dates and hist_vals:
        fig.add_trace(go.Scatter(
            x=hist_dates, y=hist_vals,
            name="Historical",
            line=dict(color=Theme.TEAL, width=2),
            mode="lines",
        ))

    # Forecast ribbon (10th–90th percentile)
    fc_dates = data.get("forecast_dates", [])
    fc_lo    = data.get("forecast_low",    data.get("forecast_q10", []))
    fc_hi    = data.get("forecast_high",   data.get("forecast_q90", []))
    fc_med   = data.get("forecast_median", [])

    if fc_dates and fc_lo and fc_hi:
        fig.add_trace(go.Scatter(
            x=fc_dates + fc_dates[::-1],
            y=fc_hi + fc_lo[::-1],
            fill="toself",
            fillcolor=f"{Theme.AMBER}22",
            line=dict(color="rgba(0,0,0,0)"),
            name="80% interval",
            showlegend=True,
        ))

    if fc_dates and fc_med:
        fig.add_trace(go.Scatter(
            x=fc_dates, y=fc_med,
            name="Forecast",
            line=dict(color=Theme.AMBER, width=2, dash="dot"),
            mode="lines",
        ))

    fig.update_layout(**_base_layout(
        f"{data.get('symbol', 'Stock')} — {data.get('horizon_days', '?')}-Day Forecast"
    ))
    return fig


def _line(data: dict):
    """Generic line chart."""
    if not _PLOTLY:
        return None
    fig = go.Figure()
    x = data.get("x", data.get("dates", []))
    for i, (key, color) in enumerate(zip(
        [k for k in data if k not in ("chart_type", "x", "dates", "title")],
        Theme.CHART_COLORS,
    )):
        fig.add_trace(go.Scatter(
            x=x, y=data[key],
            name=key,
            line=dict(color=color, width=2),
        ))
    fig.update_layout(**_base_layout(data.get("title", "Chart")))
    return fig


def _bar(data: dict):
    """Generic bar chart."""
    if not _PLOTLY:
        return None
    x = data.get("x", data.get("labels", []))
    y = data.get("y", data.get("values", []))
    fig = go.Figure(go.Bar(
        x=x, y=y,
        marker_color=Theme.TEAL,
        marker_line_color=Theme.BORDER,
        marker_line_width=1,
    ))
    fig.update_layout(**_base_layout(data.get("title", "Bar Chart")))
    return fig


def build_chart(data: dict | None):
    """
    Convert a backend data block into a Plotly Figure.
    Returns None if data is None, chart_type is unknown, or Plotly is unavailable.
    """
    if not data or not _PLOTLY:
        return None

    chart_type = data.get("chart_type", "")
    handlers = {
        "candlestick": _candlestick,
        "forecast":    _forecast,
        "line":        _line,
        "bar":         _bar,
    }
    fn = handlers.get(chart_type)
    if fn:
        try:
            return fn(data)
        except Exception:
            return None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# TEXT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def format_timestamp(iso_str: str) -> str:
    """
    '2025-04-01T14:32:05.123456+00:00' → 'Apr 01, 02:32 PM'
    Gracefully falls back to the raw string on any parse error.
    """
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone(tz=None)  # convert to local time
        return dt.strftime("%b %d, %I:%M %p")
    except Exception:
        return iso_str[:16].replace("T", " ")


def format_file_size(n_bytes: int) -> str:
    """1_234_567 → '1.2 MB'"""
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"


def ext_icon(filename: str) -> str:
    """Return an emoji icon for the file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "pdf":  "📄", "docx": "📝", "doc": "📝",
        "xlsx": "📊", "xls":  "📊", "csv": "📋",
        "txt":  "📃", "ppt":  "📑", "pptx": "📑",
    }.get(ext, "📁")
