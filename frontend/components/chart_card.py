"""
components/chart_card.py — Plotly chart renderer

render(data) takes the raw data dict from the backend's chat response
and renders a Plotly figure inline below the message bubble.

Silently does nothing if data is None or the chart type is unrecognised —
the caller never has to guard against it.
"""

import streamlit as st
from utils.formatters import build_chart


def render(data: dict | None):
    """Render a chart below the current message. No-op if data is None."""
    if not data:
        return

    fig = build_chart(data)
    if fig is None:
        # Unrecognised chart type — show a raw data expander as fallback
        with st.expander("📊 View raw data", expanded=False):
            st.json(data)
        return

    st.markdown('<div class="chart-wrapper">', unsafe_allow_html=True)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo":     False,
            "modeBarButtonsToRemove": [
                "select2d", "lasso2d", "autoScale2d",
                "hoverClosestCartesian", "hoverCompareCartesian",
            ],
            "toImageButtonOptions": {
                "format": "png",
                "filename": f"artha_{data.get('chart_type', 'chart')}",
                "scale": 2,
            },
        },
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Compact metadata strip below chart
    symbol = data.get("symbol")
    ct     = data.get("chart_type", "").replace("_", " ").title()
    if symbol or ct:
        st.markdown(
            f'<div style="text-align:center;padding:4px 0 12px">'
            f'<span class="stat-chip">{ct}</span>'
            + (f'&nbsp;<span class="stat-chip" style="color:var(--teal)">{symbol}</span>' if symbol else "")
            + '</div>',
            unsafe_allow_html=True,
        )
