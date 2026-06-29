"""Reusable chart builders (Plotly)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import CHART_TEMPLATE, COLOR_SEQUENCE, MAP_COLORSCALE, UI


def _base_layout(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=UI["text"]), x=0),
        template=CHART_TEMPLATE,
        font=dict(family="DM Sans, system-ui, sans-serif", size=12, color=UI["text"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=48, r=24, t=48, b=40),
        hoverlabel=dict(bgcolor="white", font_size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9", linecolor="#e2e8f0")
    fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9", linecolor="#e2e8f0")
    return fig


def _usd_axis_title(unit: str = "B") -> str:
    return {"T": "Trillions USD", "B": "Billions USD", "M": "Millions USD"}.get(unit, "USD")


def line_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    title: str = "",
    y_unit: str = "B",
) -> go.Figure:
    fig = px.line(
        df, x=x, y=y, color=color, markers=True, color_discrete_sequence=COLOR_SEQUENCE
    )
    fig.update_traces(line=dict(width=2.5), marker=dict(size=6))
    _base_layout(fig, title)
    fig.update_layout(yaxis_title=_usd_axis_title(y_unit), hovermode="x unified")
    return fig


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    orientation: str = "v",
    color: str | None = None,
) -> go.Figure:
    fig = px.bar(
        df, x=x, y=y, color=color, orientation=orientation, color_discrete_sequence=COLOR_SEQUENCE
    )
    fig.update_traces(marker_line_width=0, opacity=0.9)
    _base_layout(fig, title)
    return fig


def treemap_categories(df: pd.DataFrame, title: str = "Trade by category") -> go.Figure:
    fig = px.treemap(df, path=["short_label"], values="trade_usd", color_discrete_sequence=COLOR_SEQUENCE)
    fig.update_traces(hovertemplate="%{label}<br>$%{value:,.0f}<extra></extra>")
    _base_layout(fig, title)
    return fig


def heatmap_corr(corr: pd.DataFrame, title: str = "Correlation (log10 scale)") -> go.Figure:
    fig = px.imshow(
        corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", zmin=-1, zmax=1
    )
    _base_layout(fig, title)
    return fig


def choropleth_map(
    df: pd.DataFrame,
    title: str,
    color_label: str = "Value",
    colorscale: str | None = None,
    diverging: bool = False,
) -> go.Figure:
    """World map — requires iso3 and value columns."""
    scale = colorscale or ("RdBu_r" if diverging else MAP_COLORSCALE)
    fig = px.choropleth(
        df,
        locations="iso3",
        color="value",
        hover_name="country_or_area",
        color_continuous_scale=scale,
        labels={"value": color_label},
        projection="natural earth",
    )
    fig.update_geos(
        showcountries=True,
        countrycolor="#cbd5e1",
        showcoastlines=True,
        coastlinecolor="#cbd5e1",
        showland=True,
        landcolor="#f8fafc",
        showocean=True,
        oceancolor="#f1f5f9",
        bgcolor="rgba(0,0,0,0)",
    )
    _base_layout(fig, title)
    fig.update_layout(margin=dict(l=0, r=0, t=48, b=0), height=480)
    return fig


def dual_series_timeline(
    yearly: pd.DataFrame, y1: str, y2: str, label1: str, label2: str, title: str
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=yearly["year"], y=yearly[y1], mode="lines+markers", name=label1, line=dict(width=2.5, color=COLOR_SEQUENCE[0]))
    )
    fig.add_trace(
        go.Scatter(x=yearly["year"], y=yearly[y2], mode="lines+markers", name=label2, line=dict(dash="dash", width=2, color=COLOR_SEQUENCE[1]))
    )
    _base_layout(fig, title)
    fig.update_layout(yaxis_title="Trillions USD", hovermode="x unified")
    return fig


def stacked_flow_area(flow_df: pd.DataFrame, flow_cols: list[str], title: str) -> go.Figure:
    fig = go.Figure()
    for i, col in enumerate(flow_cols):
        if col in flow_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=flow_df["year"],
                    y=flow_df[col],
                    name=col,
                    stackgroup="one",
                    mode="lines",
                    line=dict(width=0.5, color=COLOR_SEQUENCE[i % len(COLOR_SEQUENCE)]),
                )
            )
    _base_layout(fig, title)
    fig.update_layout(yaxis_title="Trillions USD")
    return fig


def counterfactual_chart(years: list, actual: list, forecast: list, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=actual, name="Actual", mode="lines+markers", line=dict(color=COLOR_SEQUENCE[0])))
    fig.add_trace(
        go.Scatter(x=years, y=forecast, name="Forecast", mode="lines+markers", line=dict(dash="dash", color=COLOR_SEQUENCE[3]))
    )
    _base_layout(fig, title)
    fig.update_layout(yaxis_title="Trillions USD", hovermode="x unified")
    return fig


def scatter_clusters(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str,
    title: str,
    hover_name: str | None = None,
    labels: dict | None = None,
) -> go.Figure:
    fig = px.scatter(
        df, x=x, y=y, color=color, hover_name=hover_name, labels=labels or {}, color_discrete_sequence=COLOR_SEQUENCE
    )
    fig.add_hline(y=0, line_width=0.5, line_color="#94a3b8")
    fig.add_vline(x=0, line_width=0.5, line_color="#94a3b8")
    _base_layout(fig, title)
    return fig


def yoy_bar_chart(df: pd.DataFrame, x: str, y: str, title: str = "") -> go.Figure:
    colors = [COLOR_SEQUENCE[2] if v >= 0 else COLOR_SEQUENCE[3] for v in df[y]]
    fig = go.Figure(
        go.Bar(x=df[x], y=df[y], marker_color=colors, marker_line_width=0)
    )
    fig.add_hline(y=0, line_width=0.5, line_color="#94a3b8")
    _base_layout(fig, title)
    fig.update_layout(yaxis_title="YoY change (%)", hovermode="x unified")
    return fig


def driver_waterfall(drivers: pd.DataFrame, title: str = "Export change by category") -> go.Figure:
    """Waterfall of category contributions to export change."""
    df = drivers.sort_values("value_change_b", key=abs, ascending=False).copy()
    measures = ["relative"] * len(df) + ["total"]
    x_labels = df["short_label"].tolist() + ["Net"]
    y_vals = df["value_change_b"].tolist() + [df["value_change_b"].sum()]
    fig = go.Figure(
        go.Waterfall(
            x=x_labels,
            y=y_vals,
            measure=measures,
            increasing={"marker": {"color": COLOR_SEQUENCE[2]}},
            decreasing={"marker": {"color": COLOR_SEQUENCE[3]}},
            totals={"marker": {"color": COLOR_SEQUENCE[0]}},
            connector={"line": {"color": "#cbd5e1"}},
        )
    )
    _base_layout(fig, title)
    fig.update_layout(yaxis_title="Change (billions USD)", showlegend=False)
    return fig
