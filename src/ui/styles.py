"""Inject global dashboard styles."""

from __future__ import annotations

import streamlit as st

from config import UI


def apply_styles() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');

        html, body, [class*="css"] {{
            font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
        }}

        .block-container {{
            padding-top: 1.25rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }}

        h1 {{
            font-size: 1.75rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
            color: {UI['text']};
            margin-bottom: 0.25rem !important;
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
            border-right: 1px solid {UI['border']};
        }}

        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
            font-size: 0.8rem !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: {UI['muted']} !important;
            font-weight: 600 !important;
        }}

        div[data-testid="stMetric"] {{
            background: {UI['surface']};
            border: 1px solid {UI['border']};
            border-radius: 10px;
            padding: 0.75rem 1rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }}

        div[data-testid="stMetric"] label {{
            color: {UI['muted']} !important;
            font-size: 0.75rem !important;
            font-weight: 500 !important;
        }}

        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
            font-size: 1.35rem !important;
            font-weight: 700 !important;
            color: {UI['text']} !important;
        }}

        .dash-subtitle {{
            color: {UI['muted']};
            font-size: 0.95rem;
            margin-bottom: 1.25rem;
            line-height: 1.5;
        }}

        .section-label {{
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {UI['muted']};
            margin: 1rem 0 0.5rem 0;
        }}

        [data-testid="stRadio"] > div {{
            gap: 0.35rem;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.25rem;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px 8px 0 0;
            padding: 0.5rem 1rem;
            font-weight: 500;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    st.title(title)
    if subtitle:
        st.markdown(f'<p class="dash-subtitle">{subtitle}</p>', unsafe_allow_html=True)
