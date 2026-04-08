"""Tests for withings_cli.api."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import respx

from withings_cli.api import HEART_URL, MEASURE_URL, WithingsClient
from withings_cli.models import AFibClassification, MeasureType


def _make_client() -> WithingsClient:
    with patch("withings_cli.api.get_valid_access_token", return_value="fake-token"):
        return WithingsClient()


def test_get_measures_parses_groups(measure_response: dict[str, Any]) -> None:
    with respx.mock:
        respx.post(MEASURE_URL).mock(return_value=httpx.Response(200, json=measure_response))
        client = _make_client()
        result = client.get_measures()

    assert len(result.measuregrps) == 2

    grp = result.measuregrps[0]
    assert len(grp.measures) == 2
    weight = grp.measures[0]
    assert weight.measure_type == MeasureType.WEIGHT
    assert abs(weight.real_value - 75.3) < 0.01

    fat = grp.measures[1]
    assert fat.measure_type == MeasureType.FAT_RATIO
    assert abs(fat.real_value - 21.5) < 0.01


def test_get_measures_blood_pressure(measure_response: dict[str, Any]) -> None:
    with respx.mock:
        respx.post(MEASURE_URL).mock(return_value=httpx.Response(200, json=measure_response))
        client = _make_client()
        result = client.get_measures()

    bp_grp = result.measuregrps[1]
    systolic = bp_grp.measures[0]
    assert systolic.measure_type == MeasureType.SYSTOLIC_BP
    assert systolic.real_value == 125.0

    diastolic = bp_grp.measures[1]
    assert diastolic.measure_type == MeasureType.DIASTOLIC_BP
    assert diastolic.real_value == 80.0


def test_get_measures_filter_by_meastype(measure_response: dict[str, Any]) -> None:
    with respx.mock:
        route = respx.post(MEASURE_URL).mock(
            return_value=httpx.Response(200, json=measure_response)
        )
        client = _make_client()
        client.get_measures(meastype=MeasureType.WEIGHT)

    request = route.calls.last.request
    body = request.content.decode()
    assert "meastype=1" in body


def test_heart_list_parses_records(heart_list_response: dict[str, Any]) -> None:
    with respx.mock:
        respx.post(HEART_URL).mock(return_value=httpx.Response(200, json=heart_list_response))
        client = _make_client()
        result = client.get_heart_list()

    assert len(result.series) == 2
    assert result.series[0].signal_id == 101
    assert result.series[0].heart_rate == 68
    assert result.series[0].bloodpressure is not None
    assert result.series[0].bloodpressure.systole == 125
    assert result.series[0].classification == AFibClassification.NEGATIVE
    assert result.series[1].classification == AFibClassification.INCONCLUSIVE
