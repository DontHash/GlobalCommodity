"""Human-readable labels for raw dataset codes."""

from __future__ import annotations

import re


def category_label(raw: str, max_len: int = 48) -> str:
    """16_meat_fish... → Meat, fish & seafood (title case)."""
    text = re.sub(r"^\d+_", "", str(raw))
    text = text.replace("_", " ").strip()
    if not text:
        return str(raw)
    return text[:max_len].title()


def format_billions(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}B"


def format_pct(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"
