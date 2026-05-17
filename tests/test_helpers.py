from datetime import date

import pytest

from helpers import (
    completeness_quartile,
    format_quarter,
    parse_quarter,
    quarter_date_range,
    quarter_sort_key,
)


class TestFormatQuarter:
    @pytest.mark.parametrize("d,expected", [
        (date(2025, 1, 1), "Q1 2025"),
        (date(2025, 3, 31), "Q1 2025"),
        (date(2025, 4, 1), "Q2 2025"),
        (date(2025, 6, 30), "Q2 2025"),
        (date(2025, 7, 1), "Q3 2025"),
        (date(2025, 9, 30), "Q3 2025"),
        (date(2025, 10, 1), "Q4 2025"),
        (date(2025, 12, 31), "Q4 2025"),
    ])
    def test_quarter_boundaries(self, d, expected):
        assert format_quarter(d) == expected


class TestParseQuarter:
    @pytest.mark.parametrize("label,expected", [
        ("Q1 2025", (1, 2025)),
        ("Q4 2024", (4, 2024)),
        ("Q2 1999", (2, 1999)),
    ])
    def test_parses_valid_labels(self, label, expected):
        assert parse_quarter(label) == expected

    def test_round_trips_with_format_quarter(self):
        for d in [date(2024, 2, 14), date(2024, 7, 4), date(2025, 12, 31)]:
            q_num, year = parse_quarter(format_quarter(d))
            assert year == d.year
            assert q_num == (d.month - 1) // 3 + 1


class TestQuarterSortKey:
    def test_orders_chronologically(self):
        labels = ["Q4 2024", "Q1 2025", "Q2 2024", "Q3 2025"]
        assert sorted(labels, key=quarter_sort_key) == [
            "Q2 2024", "Q4 2024", "Q1 2025", "Q3 2025",
        ]

    def test_reverse_puts_newest_first(self):
        labels = ["Q1 2024", "Q4 2025", "Q2 2024", "Q3 2025"]
        assert sorted(labels, key=quarter_sort_key, reverse=True) == [
            "Q4 2025", "Q3 2025", "Q2 2024", "Q1 2024",
        ]

    def test_year_dominates_quarter(self):
        # Q1 of a newer year beats Q4 of an older year.
        assert quarter_sort_key("Q1 2025") > quarter_sort_key("Q4 2024")


class TestQuarterDateRange:
    @pytest.mark.parametrize("label,start,end", [
        ("Q1 2025", date(2025, 1, 1), date(2025, 3, 31)),
        ("Q2 2025", date(2025, 4, 1), date(2025, 6, 30)),
        ("Q3 2025", date(2025, 7, 1), date(2025, 9, 30)),
        ("Q4 2025", date(2025, 10, 1), date(2025, 12, 31)),
    ])
    def test_standard_quarters(self, label, start, end):
        assert quarter_date_range(label) == (start, end)

    def test_q1_leap_year_uses_correct_march_end(self):
        # Q1 always ends March 31, regardless of leap year.
        assert quarter_date_range("Q1 2024") == (date(2024, 1, 1), date(2024, 3, 31))

    def test_end_inclusive_of_quarter_last_day(self):
        _, end = quarter_date_range("Q2 2024")
        assert end == date(2024, 6, 30)


class TestCompletenessQuartile:
    @pytest.mark.parametrize("pct,expected", [
        (0.0, 0),
        (0.1249, 0),
        (0.125, 25),
        (0.3, 25),
        (0.3749, 25),
        (0.375, 50),
        (0.5, 50),
        (0.6249, 50),
        (0.625, 75),
        (0.8, 75),
        (0.8749, 75),
        (0.875, 100),
        (1.0, 100),
    ])
    def test_threshold_boundaries(self, pct, expected):
        assert completeness_quartile(pct) == expected

    def test_returns_one_of_five_buckets(self):
        for i in range(101):
            assert completeness_quartile(i / 100) in {0, 25, 50, 75, 100}
