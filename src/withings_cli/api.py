"""Withings API client."""

from typing import Any

import httpx

from withings_cli.auth import AuthError, get_valid_access_token
from withings_cli.models import (
    HeartListResponse,
    HeartSignalResponse,
    MeasureResponse,
    MeasureType,
)

MEASURE_URL = "https://wbsapi.withings.net/measure"
HEART_URL = "https://wbsapi.withings.net/v2/heart"


class APIError(Exception):
    pass


class WithingsClient:
    """Read-only client for the Withings API."""

    def __init__(self) -> None:
        self._access_token = get_valid_access_token()

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    def _post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(url, data=data, headers=self._headers)
        response.raise_for_status()
        body = response.json()
        status = body.get("status")
        if status == 401:
            raise AuthError("Access token expired. Run 'withings login'.")
        if status != 0:
            raise APIError(f"API error (status={status}): {body.get('error', 'unknown')}")
        result: dict[str, Any] = body.get("body", {})
        return result

    def get_measures(
        self,
        *,
        meastype: MeasureType | None = None,
        startdate: int | None = None,
        enddate: int | None = None,
        lastupdate: int | None = None,
        category: int = 1,
    ) -> MeasureResponse:
        """Fetch body measurements (Measure - Getmeas)."""
        data: dict[str, Any] = {"action": "getmeas", "category": category}
        if meastype is not None:
            data["meastype"] = meastype.value
        if lastupdate is not None:
            data["lastupdate"] = lastupdate
        elif startdate is not None:
            data["startdate"] = startdate
            if enddate is not None:
                data["enddate"] = enddate
        body = self._post(MEASURE_URL, data)
        return MeasureResponse.model_validate(body)

    def get_heart_list(
        self,
        *,
        startdate: int | None = None,
        enddate: int | None = None,
    ) -> HeartListResponse:
        """Fetch list of ECG recordings (Heart - list)."""
        data: dict[str, Any] = {"action": "list"}
        if startdate is not None:
            data["startdate"] = startdate
        if enddate is not None:
            data["enddate"] = enddate
        body = self._post(HEART_URL, data)
        return HeartListResponse.model_validate(body)

    def get_heart_signal(self, signal_id: int) -> HeartSignalResponse:
        """Fetch a single ECG signal (Heart - get)."""
        body = self._post(HEART_URL, {"action": "get", "signalid": signal_id})
        return HeartSignalResponse.model_validate(body)
