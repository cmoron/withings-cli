"""Shared fixtures for withings-cli tests."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture()
def token_response() -> dict[str, Any]:
    """A valid token exchange response body."""
    return {
        "status": 0,
        "body": {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 10800,
            "token_type": "Bearer",
            "scope": "user.metrics",
            "userid": 12345,
        },
    }


@pytest.fixture()
def measure_response() -> dict[str, Any]:
    """A valid Measure - Getmeas response."""
    return {
        "status": 0,
        "body": {
            "updatetime": 1700000000,
            "timezone": "Europe/Paris",
            "measuregrps": [
                {
                    "grpid": 1,
                    "attrib": 0,
                    "date": 1700000000,
                    "created": 1700000000,
                    "measures": [
                        {"type": 1, "value": 75300, "unit": -3},  # 75.3 kg
                        {"type": 6, "value": 215, "unit": -1},  # 21.5 %
                    ],
                },
                {
                    "grpid": 2,
                    "attrib": 0,
                    "date": 1699900000,
                    "created": 1699900000,
                    "measures": [
                        {"type": 10, "value": 125, "unit": 0},  # 125 mmHg systolic
                        {"type": 9, "value": 80, "unit": 0},  # 80 mmHg diastolic
                        {"type": 11, "value": 72, "unit": 0},  # 72 bpm
                    ],
                },
            ],
        },
    }


@pytest.fixture()
def heart_list_response() -> dict[str, Any]:
    """A valid Heart - list response."""
    return {
        "status": 0,
        "body": {
            "series": [
                {
                    "deviceid": "abc123",
                    "model": 44,
                    "ecg": {"signalid": 101, "afib": 0},
                    "bloodpressure": {"diastole": 78, "systole": 125},
                    "heart_rate": 68,
                    "timestamp": 1700000000,
                    "modified": 1700000100,
                },
                {
                    "deviceid": "abc123",
                    "model": 44,
                    "ecg": {"signalid": 102, "afib": 2},
                    "bloodpressure": {"diastole": 82, "systole": 130},
                    "heart_rate": 75,
                    "timestamp": 1699900000,
                    "modified": 1699900100,
                },
            ],
            "more": False,
            "offset": 0,
        },
    }
