# withings-cli

Read-only CLI for Withings health data. Fetches body measurements (scale, BPM Core) and ECG recordings via the Withings API.

Designed to be consumed by both humans (rich tables) and AI agents (`--format json`).

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

### Withings API credentials

1. Create a Withings developer account at https://developer.withings.com
2. Create an application to get your `client_id` and `client_secret`
3. Set the redirect URI to `https://localhost:8888`

## Commands

### `withings login`

Interactive OAuth2 authentication. Prompts for `client_id` and `client_secret`, displays an authorization URL, then waits for the user to paste back the authorization code.

Credentials are stored in `~/.config/withings-cli/credentials.json`.
Tokens are stored in `~/.config/withings-cli/tokens.json` and refreshed automatically on each API call.

```bash
withings login
```

### `withings logout`

Removes stored tokens.

```bash
withings logout
```

---

### `withings measures`

Fetches body measurements from all Withings devices (scale, BPM Core, thermometer, etc.).

```bash
withings measures [--type TYPE] [--since SINCE] [--format table|json]
```

**Options:**

| Option | Description |
|---|---|
| `--type TYPE` | Filter by measurement type (see table below) |
| `--since SINCE` | Start date. Accepts relative (`7d`, `30d`, `90d`) or absolute (`2024-01-01`) |
| `--format` | Output format: `table` (default, rich) or `json` |

**Type filters:**

| Filter | Measurements included |
|---|---|
| `weight` | Weight (kg) |
| `fat` | Fat Ratio (%) + Fat Mass (kg) |
| `muscle` | Muscle Mass (kg) |
| `bone` | Bone Mass (kg) |
| `hydration` | Hydration (kg) |
| `bp` | Systolic BP + Diastolic BP (mmHg) |
| `hr` | Heart Rate (bpm) |
| `spo2` | SpO2 (%) |
| `temp` | Temperature (C) |
| `pwv` | Pulse Wave Velocity (m/s) |
| `scale` | All scale measurements (weight, fat, muscle, bone, hydration, height, fat free mass) |
| `cardio` | All cardio measurements (systolic BP, diastolic BP, heart rate, PWV) |

**JSON output format (`--format json`):**

Returns a JSON array of measurement objects, sorted by date descending.

```json
[
  {
    "date": "2025-03-15T08:30:00",
    "type": "weight",
    "value": 75.3,
    "unit": "kg"
  },
  {
    "date": "2025-03-15T08:30:00",
    "type": "fat_ratio",
    "value": 21.5,
    "unit": "%"
  },
  {
    "date": "2025-03-14T19:00:00",
    "type": "systolic_bp",
    "value": 125.0,
    "unit": "mmHg"
  },
  {
    "date": "2025-03-14T19:00:00",
    "type": "diastolic_bp",
    "value": 80.0,
    "unit": "mmHg"
  }
]
```

**JSON fields:**

| Field | Type | Description |
|---|---|---|
| `date` | string | ISO 8601 datetime of the measurement |
| `type` | string | Measurement type identifier (see below) |
| `value` | float | Measurement value, already converted to the display unit |
| `unit` | string | Unit of measurement |

**Possible `type` values:**

| `type` | Unit | Source device |
|---|---|---|
| `weight` | kg | Scale |
| `height` | m | Scale |
| `fat_free_mass` | kg | Scale |
| `fat_ratio` | % | Scale |
| `fat_mass` | kg | Scale |
| `muscle_mass` | kg | Scale |
| `hydration` | kg | Scale |
| `bone_mass` | kg | Scale |
| `systolic_bp` | mmHg | BPM Core |
| `diastolic_bp` | mmHg | BPM Core |
| `heart_rate` | bpm | BPM Core |
| `temperature` | C | Thermo |
| `sp_o2` | % | ScanWatch / Pulse |
| `pulse_wave_velocity` | m/s | BPM Core |

---

### `withings ecg list`

Lists heart recordings from BPM Core (ECG, blood pressure, heart rate).

```bash
withings ecg list [--since SINCE] [--format table|json]
```

**Options:**

| Option | Description |
|---|---|
| `--since SINCE` | Start date. Accepts relative (`7d`, `30d`) or absolute (`2024-01-01`) |
| `--format` | Output format: `table` (default) or `json` |

**JSON output format (`--format json`):**

Returns a JSON array of heart recording summaries, sorted by date descending.

```json
[
  {
    "signal_id": 630578273,
    "date": "2025-12-18T19:43:40",
    "heart_rate": 63,
    "afib_classification": "negative",
    "systole": 132,
    "diastole": 78
  },
  {
    "signal_id": 630412100,
    "date": "2025-12-16T10:15:00",
    "heart_rate": 75,
    "afib_classification": "negative",
    "systole": 128,
    "diastole": 82
  }
]
```

**JSON fields:**

| Field | Type | Description |
|---|---|---|
| `signal_id` | int | Unique ECG signal identifier. Pass to `ecg get` for full signal data |
| `date` | string | ISO 8601 datetime of the recording |
| `heart_rate` | int | Heart rate in bpm at time of recording |
| `afib_classification` | string | AFib detection result: `negative`, `positive`, `inconclusive`, or `unclassified` |
| `systole` | int | Systolic blood pressure in mmHg (present if BP was measured) |
| `diastole` | int | Diastolic blood pressure in mmHg (present if BP was measured) |

---

### `withings ecg get <signal_id>`

Fetches the full ECG signal data for a specific recording, including the raw waveform.

```bash
withings ecg get <signal_id> [--format table|json] [--no-signal]
```

**Arguments:**

| Argument | Description |
|---|---|
| `signal_id` | ECG signal ID (from `ecg list` output) |

**Options:**

| Option | Description |
|---|---|
| `--format` | Output format: `table` (default) or `json` |
| `--no-signal` | Omit the raw ECG waveform from JSON output (metadata only). Useful for quick summaries without the ~15000-point signal array |

**JSON output format (`--format json`):**

Returns a single JSON object with the full ECG signal and metadata.

```json
{
  "signal_id": 630578273,
  "date": "2025-12-18T19:43:40",
  "heart_rate": 63,
  "sampling_frequency": 500,
  "duration_seconds": 30.0,
  "data_points": 15000,
  "afib_classification": "negative",
  "systole": 132,
  "diastole": 78,
  "signal": [-145, -152, -157, -157, -153, -145, -133, "...15000 integers total"]
}
```

**JSON fields:**

| Field | Type | Description |
|---|---|---|
| `signal_id` | int | Unique ECG signal identifier |
| `date` | string | ISO 8601 datetime (present if metadata found in recent recordings) |
| `heart_rate` | int | Heart rate in bpm |
| `sampling_frequency` | int | Sampling rate in Hz (typically 500) |
| `duration_seconds` | float | Recording duration in seconds |
| `data_points` | int | Number of samples in the signal array |
| `afib_classification` | string | `negative`, `positive`, `inconclusive`, or `unclassified` |
| `systole` | int | Systolic blood pressure in mmHg |
| `diastole` | int | Diastolic blood pressure in mmHg |
| `signal` | int[] | Raw ECG waveform (omitted with `--no-signal`). Each integer is a sample in microvolts (uV). At 500 Hz, 15000 points = 30 seconds |

**Interpreting the ECG signal:**
- The `signal` array is a time series of voltage samples in microvolts
- Sample interval = 1 / `sampling_frequency` seconds (2ms at 500 Hz)
- Typical recording: 30 seconds, 15000 data points
- The waveform contains the standard PQRST complexes of each heartbeat
- Useful for rhythm analysis, QRS morphology, and interval measurements

---

## Typical workflows

### Get a health snapshot (last 7 days)

```bash
withings measures --since 7d --format json
withings ecg list --since 7d --format json
```

### Retrieve full ECG for analysis

```bash
# 1. List recent ECGs to find the signal_id
withings ecg list --since 30d --format json

# 2. Fetch the full signal
withings ecg get 630578273 --format json
```

### Track weight over time

```bash
withings measures --type weight --since 90d --format json
```

### Get all cardio data (BP + HR + PWV)

```bash
withings measures --type cardio --since 30d --format json
```

## Development

```bash
uv run pytest              # tests
uv run ruff check src/     # lint
uv run mypy src/           # type check
```

## License

MIT
