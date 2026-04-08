"""Pydantic models for Withings API responses."""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel


class MeasureType(IntEnum):
    """Withings measurement type IDs."""

    # Balance
    WEIGHT = 1
    HEIGHT = 4
    FAT_FREE_MASS = 5
    FAT_RATIO = 6
    FAT_MASS = 8
    MUSCLE_MASS = 76
    HYDRATION = 77
    BONE_MASS = 88

    # BPM Core / Cardio
    DIASTOLIC_BP = 9
    SYSTOLIC_BP = 10
    HEART_RATE = 11

    # Other
    TEMPERATURE = 12
    SP_O2 = 54
    PULSE_WAVE_VELOCITY = 91

    @property
    def unit(self) -> str:
        units: dict[int, str] = {
            1: "kg",
            4: "m",
            5: "kg",
            6: "%",
            8: "kg",
            9: "mmHg",
            10: "mmHg",
            11: "bpm",
            12: "°C",
            54: "%",
            76: "kg",
            77: "kg",
            88: "kg",
            91: "m/s",
        }
        return units.get(self.value, "")

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


# Groups for CLI filtering
SCALE_TYPES = {
    MeasureType.WEIGHT,
    MeasureType.HEIGHT,
    MeasureType.FAT_FREE_MASS,
    MeasureType.FAT_RATIO,
    MeasureType.FAT_MASS,
    MeasureType.MUSCLE_MASS,
    MeasureType.HYDRATION,
    MeasureType.BONE_MASS,
}
CARDIO_TYPES = {
    MeasureType.DIASTOLIC_BP,
    MeasureType.SYSTOLIC_BP,
    MeasureType.HEART_RATE,
    MeasureType.PULSE_WAVE_VELOCITY,
}


class Measure(BaseModel):
    """A single measurement value within a group."""

    type: int
    value: int
    unit: int  # power of 10 to multiply value by

    @property
    def measure_type(self) -> MeasureType | None:
        """Return the MeasureType if known, None otherwise."""
        try:
            return MeasureType(self.type)
        except ValueError:
            return None

    @property
    def real_value(self) -> float:
        return self.value * (10**self.unit)


class MeasureGroup(BaseModel):
    """A group of measurements taken at the same time."""

    grpid: int
    attrib: int
    date: int
    created: int
    measures: list[Measure]

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.date)


class MeasureResponse(BaseModel):
    """Response from Measure - Getmeas."""

    updatetime: int
    timezone: str = ""
    measuregrps: list[MeasureGroup] = []


class AFibClassification(IntEnum):
    """ECG atrial fibrillation classification."""

    NEGATIVE = 0
    POSITIVE = 1
    INCONCLUSIVE = 2
    UNCLASSIFIED = 3


class ECGData(BaseModel):
    """ECG sub-object within a heart record."""

    signalid: int
    afib: int = 0


class BloodPressureData(BaseModel):
    """Blood pressure sub-object within a heart record."""

    diastole: int
    systole: int


class HeartRecord(BaseModel):
    """A heart recording from the Heart list endpoint."""

    deviceid: str = ""
    model: int = 0
    ecg: ECGData | None = None
    bloodpressure: BloodPressureData | None = None
    heart_rate: int = 0
    timestamp: int = 0
    modified: int = 0

    @property
    def signal_id(self) -> int | None:
        return self.ecg.signalid if self.ecg else None

    @property
    def afib(self) -> int:
        return self.ecg.afib if self.ecg else 0

    @property
    def classification(self) -> AFibClassification:
        try:
            return AFibClassification(self.afib)
        except ValueError:
            return AFibClassification.UNCLASSIFIED

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)


class HeartListResponse(BaseModel):
    """Response from Heart - list."""

    series: list[HeartRecord] = []
    more: bool = False
    offset: int = 0


class HeartRateValue(BaseModel):
    """Heart rate sub-object in Heart - get response."""

    value: int = 0
    date: int = 0


class HeartSignalResponse(BaseModel):
    """Response from Heart - get (ECG signal data)."""

    signal: list[int] = []
    sampling_frequency: int = 500
    wearposition: int = 0
    model: int = 0
    heart_rate: HeartRateValue = HeartRateValue()
