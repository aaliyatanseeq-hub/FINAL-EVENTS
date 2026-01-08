import os
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from Backend.services.location_validator import LocationValidator


def days_from_today(n: int) -> str:
    return (datetime.now().date() + timedelta(days=n)).strftime('%Y-%m-%d')


class DummyResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


# ----------------------
# validate_location tests
# ----------------------

def test_validate_location_rejects_too_short():
    lv = LocationValidator()
    ok, normalized, err = lv.validate_location("a")
    assert ok is False
    assert normalized is None
    assert "at least 2 characters" in err


def test_validate_location_rejects_numeric_only():
    lv = LocationValidator()
    ok, normalized, err = lv.validate_location("123456")
    assert ok is False
    assert normalized is None
    assert "doesn't appear to be a valid location" in err


def test_validate_location_normalizes_capitalization_without_serpapi(monkeypatch):
    # Ensure no SERP_API_KEY so basic normalization path is used
    monkeypatch.delenv("SERP_API_KEY", raising=False)
    lv = LocationValidator()
    ok, normalized, err = lv.validate_location("new york, ny")
    assert ok is True
    # Normalization capitalizes each word; 'ny' -> 'Ny'
    assert normalized == "New York, Ny"
    assert err is None


def test_validate_location_uses_serpapi_success(monkeypatch):
    # Set SERP_API_KEY to force SerpAPI path
    monkeypatch.setenv("SERP_API_KEY", "dummy")

    # Create a fresh instance to pick up env var
    lv = LocationValidator()

    # Mock requests.get to return a successful geocoding-like payload
    def fake_get(url, params=None, timeout=10):
        assert "serpapi.com" in url
        return DummyResponse(
            status_code=200,
            json_data={
                "local_results": [
                    {"address": "New York, NY, USA"}
                ]
            },
        )

    monkeypatch.setattr("Backend.services.location_validator.requests.get", fake_get)

    ok, normalized, err = lv.validate_location("nyc")
    assert ok is True
    # Extracted from address -> first part "New York"
    assert normalized == "New York"
    assert err is None


def test_validate_location_serpapi_no_results(monkeypatch):
    monkeypatch.setenv("SERP_API_KEY", "dummy")
    lv = LocationValidator()

    def fake_get(url, params=None, timeout=10):
        return DummyResponse(status_code=200, json_data={"local_results": []})

    monkeypatch.setattr("Backend.services.location_validator.requests.get", fake_get)

    ok, normalized, err = lv.validate_location("SomeUnknownPlaceXYZ")
    assert ok is False
    assert normalized is None
    assert "not a recognized location" in err


# ----------------------
# validate_date_range tests
# ----------------------

def test_validate_date_range_accepts_various_formats():
    lv = LocationValidator()

    # Use dates in the near future relative to today
    start_iso = days_from_today(1)
    end_iso = days_from_today(5)

    # Also try a different input format for start and end
    start_us = datetime.strptime(start_iso, "%Y-%m-%d").strftime("%m/%d/%Y")  # mm/dd/YYYY
    end_pretty = datetime.strptime(end_iso, "%Y-%m-%d").strftime("%B %d, %Y")  # Month dd, YYYY

    ok, err, start_dt, end_dt = lv.validate_date_range(start_us, end_pretty)
    assert ok is True
    assert err is None
    assert start_dt is not None and end_dt is not None
    assert start_dt.date().strftime("%Y-%m-%d") == start_iso
    assert end_dt.date().strftime("%Y-%m-%d") == end_iso


def test_validate_date_range_invalid_start_format():
    lv = LocationValidator()
    ok, err, s, e = lv.validate_date_range("15-01-2025", "2025-01-20")
    assert ok is False
    assert s is None and e is None
    assert "Invalid start date format" in err


def test_validate_date_range_rejects_past_start_date():
    lv = LocationValidator()
    start = days_from_today(-1)
    end = days_from_today(1)
    ok, err, s, e = lv.validate_date_range(start, end)
    assert ok is False
    assert "in the past" in err


def test_validate_date_range_rejects_end_before_start():
    lv = LocationValidator()
    start = days_from_today(10)
    end = days_from_today(5)
    ok, err, s, e = lv.validate_date_range(start, end)
    assert ok is False
    assert "must be after start date" in err


def test_validate_date_range_rejects_over_90_days_and_too_far_future():
    lv = LocationValidator()

    # Case 1: Range exceeds 90 days
    start1 = days_from_today(1)
    end1 = (datetime.strptime(start1, "%Y-%m-%d").date() + timedelta(days=91)).strftime("%Y-%m-%d")
    ok1, err1, s1, e1 = lv.validate_date_range(start1, end1)
    assert ok1 is False
    assert "exceeds 3 months" in err1

    # Case 2: End date more than 3 months from today, but range itself is 90 days (allowed range check, fails future check)
    start2 = days_from_today(1)
    end2 = days_from_today(91)  # This makes range = 90 days, but beyond today + 90
    ok2, err2, s2, e2 = lv.validate_date_range(start2, end2)
    assert ok2 is False
    assert "more than 3 months in the future" in err2
