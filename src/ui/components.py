"""Reusable UI blocks for decision-focused dashboard."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from config import DATA_PATH, UI
from src.analytics.kpis import KpiSnapshot


BUSINESS_QUESTIONS = [
    ("Is trade growing or declining?", "Executive KPIs + trend chart"),
    ("Which regions are driving change?", "Countries → World map & rankings"),
    ("Which products matter most?", "Commodities → category breakdown"),
    ("Why did a metric change?", "Root cause panel on this page"),
    ("What needs attention now?", "Alerts below KPIs"),
]


def render_questions_expander() -> None:
    with st.expander("What questions does this dashboard answer?", expanded=False):
        for q, where in BUSINESS_QUESTIONS:
            st.markdown(f"**{q}** — *{where}*")


def render_kpi_row(kpis: list[KpiSnapshot]) -> None:
    if not kpis:
        return
    cols = st.columns(min(len(kpis), 4))
    for col, kpi in zip(cols, kpis[:4]):
        with col:
            delta_color = "normal"
            if kpi.delta_direction == "up":
                delta_color = "normal"
            elif kpi.delta_direction == "down":
                delta_color = "inverse"
            st.metric(
                label=kpi.label,
                value=kpi.value,
                delta=kpi.delta,
                delta_color=delta_color,
                help=kpi.context or None,
            )


def render_alerts(alerts: list[dict]) -> None:
    if not alerts:
        st.success("No critical exceptions in the current selection.")
        return
    for a in alerts:
        level = a["level"]
        if level == "critical":
            st.error(f"**{a['title']}** — {a['detail']}")
        elif level == "warning":
            st.warning(f"**{a['title']}** — {a['detail']}")
        elif level == "positive":
            st.success(f"**{a['title']}** — {a['detail']}")
        else:
            st.info(f"**{a['title']}** — {a['detail']}")


def render_data_footer(view, filters: dict) -> None:
    """Transparency: source, freshness, filter state."""
    st.divider()
    p = view.profile
    src = Path(DATA_PATH).name
    mtime = datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime("%Y-%m-%d")
    rows = f"{p['rows']:,} records" if p["rows"] else "aggregated view"
    preset = filters.get("preset", "Custom")
    st.caption(
        f"**Source:** UN Comtrade · **Indexed:** {mtime} · **Preset:** {preset} · "
        f"**Period:** {filters['year_range'][0]}–{filters['year_range'][1]} · "
        f"**Scope:** {rows}, {p['countries']} countries · "
        f"**Excl. aggregate bucket:** {filters['exclude_aggregate']}"
    )


def section(title: str, hint: str = "") -> None:
    st.markdown(f'<p class="section-label">{title}</p>', unsafe_allow_html=True)
    if hint:
        st.caption(hint)


def render_scope_banner(filters: dict, view) -> None:
    """Compact context strip — active period, scope, and data grain."""
    preset = filters.get("preset", "Custom")
    y0, y1 = filters["year_range"]
    parts = [f"**{preset}**", f"{y0}–{y1}"]
    if filters.get("countries"):
        parts.append(f"{len(filters['countries'])} countries")
    if filters.get("categories"):
        parts.append(f"{len(filters['categories'])} categories")
    flows = filters.get("flows")
    if flows and len(flows) < 4:
        parts.append(", ".join(flows))
    if view.has_country_filter or view.has_category_filter:
        parts.append("filtered view")
    st.markdown(
        f'<p style="color:{UI["muted"]};font-size:0.82rem;margin:0 0 1rem 0;">'
        f'{" · ".join(parts)} · yearly totals · USD trade value'
        f"</p>",
        unsafe_allow_html=True,
    )
