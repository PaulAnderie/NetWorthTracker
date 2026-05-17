"""Pure helpers for quarter math and Harvey Ball completeness scoring.

Extracted from app.py so the logic can be unit-tested without spinning up
Flask or the database.
"""
import calendar
from datetime import date


def format_quarter(d):
    """Return the quarter label for a date, e.g. ``Q4 2025``."""
    return f"Q{(d.month - 1) // 3 + 1} {d.year}"


def parse_quarter(quarter_str):
    """Parse a quarter label like ``Q4 2025`` into ``(quarter_number, year)``."""
    q_part, year_part = quarter_str.split()
    return int(q_part[1:]), int(year_part)


def quarter_sort_key(quarter_str):
    """Sort key for chronological ordering of quarter labels.

    ``sorted(labels, key=quarter_sort_key)`` puts oldest first; pass
    ``reverse=True`` for newest first.
    """
    q_num, year = parse_quarter(quarter_str)
    return (year, q_num)


def quarter_date_range(quarter_str):
    """Return ``(start_date, end_date)`` (inclusive) for a quarter label."""
    q_num, year = parse_quarter(quarter_str)
    start_month = (q_num - 1) * 3 + 1
    end_month = q_num * 3
    last_day = calendar.monthrange(year, end_month)[1]
    return date(year, start_month, 1), date(year, end_month, last_day)


def completeness_quartile(percentage):
    """Map a 0.0-1.0 fraction to the nearest Harvey Ball quartile.

    Returns one of 0, 25, 50, 75, 100.
    """
    if percentage >= 0.875:
        return 100
    if percentage >= 0.625:
        return 75
    if percentage >= 0.375:
        return 50
    if percentage >= 0.125:
        return 25
    return 0
