"""CLI entry point for withings-cli."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from withings_cli.auth import AuthError, exchange_code, get_authorize_url
from withings_cli.config import (
    delete_tokens,
    load_credentials,
    save_credentials,
)
from withings_cli.models import (
    CARDIO_TYPES,
    SCALE_TYPES,
    AFibClassification,
    MeasureType,
)

console = Console()

# CLI name aliases → MeasureType values
TYPE_ALIASES: dict[str, set[MeasureType]] = {
    "weight": {MeasureType.WEIGHT},
    "fat": {MeasureType.FAT_RATIO, MeasureType.FAT_MASS},
    "muscle": {MeasureType.MUSCLE_MASS},
    "bone": {MeasureType.BONE_MASS},
    "hydration": {MeasureType.HYDRATION},
    "bp": {MeasureType.SYSTOLIC_BP, MeasureType.DIASTOLIC_BP},
    "hr": {MeasureType.HEART_RATE},
    "spo2": {MeasureType.SP_O2},
    "temp": {MeasureType.TEMPERATURE},
    "pwv": {MeasureType.PULSE_WAVE_VELOCITY},
    "scale": SCALE_TYPES,
    "cardio": CARDIO_TYPES,
}

REDIRECT_URI = "https://localhost:8888"


def _parse_since(since: str) -> int:
    """Parse a --since value like '7d', '30d', or '2024-01-01' into a unix timestamp."""
    if since.endswith("d"):
        days = int(since[:-1])
        dt = datetime.now() - timedelta(days=days)
        return int(dt.timestamp())
    return int(datetime.strptime(since, "%Y-%m-%d").timestamp())


@click.group()
def main() -> None:
    """Withings health data CLI (read-only)."""


@main.command()
def login() -> None:
    """Authenticate with Withings via OAuth2."""
    creds = load_credentials()
    if creds:
        client_id = click.prompt("Client ID", default=creds["client_id"])
        client_secret = click.prompt("Client secret", default=creds["client_secret"])
    else:
        client_id = click.prompt("Client ID")
        client_secret = click.prompt("Client secret")

    save_credentials(client_id, client_secret)

    url = get_authorize_url(client_id, REDIRECT_URI)
    console.print(f"\n[bold]Open this URL in your browser:[/bold]\n\n{url}\n")
    console.print("After authorizing, you'll be redirected to a URL like:")
    console.print(f"  {REDIRECT_URI}?code=XXXX&state=YYYY\n")

    code = click.prompt("Paste the 'code' parameter from the redirect URL")
    try:
        exchange_code(client_id, client_secret, code.strip(), REDIRECT_URI)
        console.print("[green]Login successful! Tokens saved.[/green]")
    except AuthError as e:
        console.print(f"[red]Login failed: {e}[/red]")
        raise SystemExit(1) from None


@main.command()
def logout() -> None:
    """Remove stored tokens."""
    delete_tokens()
    console.print("Tokens deleted.")


@main.command()
@click.option(
    "--type",
    "measure_type",
    help="Filter by type. Single: weight, fat, muscle, bone, hydration, bp, hr, spo2, temp, pwv. "
    "Groups: scale (all scale metrics), cardio (BP + HR + PWV).",
)
@click.option("--since", help="Start date: '7d', '30d', or '2024-01-01'")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
def measures(measure_type: str | None, since: str | None, fmt: str) -> None:
    """Fetch body measurements."""
    from withings_cli.api import WithingsClient

    try:
        client = WithingsClient()
    except AuthError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from None

    kwargs: dict[str, Any] = {}
    if since:
        kwargs["startdate"] = _parse_since(since)

    # If type maps to a single MeasureType, filter server-side
    type_filter: set[MeasureType] | None = None
    if measure_type:
        type_filter = TYPE_ALIASES.get(measure_type)
        if type_filter is None:
            # Try matching enum name directly
            try:
                mt = MeasureType[measure_type.upper()]
                type_filter = {mt}
            except KeyError:
                console.print(
                    f"[red]Unknown type '{measure_type}'. Options: {', '.join(TYPE_ALIASES)}[/red]"
                )
                raise SystemExit(1) from None
        if len(type_filter) == 1:
            kwargs["meastype"] = next(iter(type_filter))

    response = client.get_measures(**kwargs)

    if fmt == "json":
        _print_measures_json(response, type_filter)
    else:
        _print_measures_table(response, type_filter)


def _print_measures_table(
    response: Any,
    type_filter: set[MeasureType] | None,
) -> None:
    table = Table(title="Withings Measurements")
    table.add_column("Date", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Value", justify="right", style="bold")
    table.add_column("Unit", style="dim")

    for grp in response.measuregrps:
        for m in grp.measures:
            mt = m.measure_type
            if mt is None:
                continue
            if type_filter and mt not in type_filter:
                continue
            table.add_row(
                grp.datetime.strftime("%Y-%m-%d %H:%M"),
                mt.label,
                f"{m.real_value:.1f}",
                mt.unit,
            )

    console.print(table)


def _print_measures_json(
    response: Any,
    type_filter: set[MeasureType] | None,
) -> None:
    import json

    rows = []
    for grp in response.measuregrps:
        for m in grp.measures:
            mt = m.measure_type
            if mt is None:
                continue
            if type_filter and mt not in type_filter:
                continue
            rows.append(
                {
                    "date": grp.datetime.isoformat(),
                    "type": mt.name.lower(),
                    "value": m.real_value,
                    "unit": mt.unit,
                }
            )
    console.print(json.dumps(rows, indent=2))


@main.group()
def ecg() -> None:
    """ECG recordings from BPM Core."""


@ecg.command("list")
@click.option("--since", help="Start date: '7d', '30d', or '2024-01-01'")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
def ecg_list(since: str | None, fmt: str) -> None:
    """List ECG recordings."""
    import json

    from withings_cli.api import WithingsClient

    try:
        client = WithingsClient()
    except AuthError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from None

    kwargs: dict[str, Any] = {}
    if since:
        kwargs["startdate"] = _parse_since(since)

    response = client.get_heart_list(**kwargs)

    if fmt == "json":
        rows = []
        for r in response.series:
            row: dict[str, Any] = {
                "signal_id": r.signal_id,
                "date": r.datetime.isoformat(),
                "heart_rate": r.heart_rate,
                "afib_classification": r.classification.name.lower(),
            }
            if r.bloodpressure:
                row["systole"] = r.bloodpressure.systole
                row["diastole"] = r.bloodpressure.diastole
            rows.append(row)
        console.print(json.dumps(rows, indent=2))
        return

    table = Table(title="Heart Recordings (BPM Core)")
    table.add_column("Signal ID", style="cyan")
    table.add_column("Date", style="cyan")
    table.add_column("Heart Rate", justify="right", style="bold")
    table.add_column("Blood Pressure", justify="right")
    table.add_column("AFib", style="green")

    classification_styles = {
        AFibClassification.NEGATIVE: "[green]Normal[/green]",
        AFibClassification.POSITIVE: "[red]AFib detected[/red]",
        AFibClassification.INCONCLUSIVE: "[yellow]Inconclusive[/yellow]",
        AFibClassification.UNCLASSIFIED: "[dim]Unclassified[/dim]",
    }

    for record in response.series:
        bp = ""
        if record.bloodpressure:
            bp = f"{record.bloodpressure.systole}/{record.bloodpressure.diastole}"
        table.add_row(
            str(record.signal_id or "-"),
            record.datetime.strftime("%Y-%m-%d %H:%M"),
            f"{record.heart_rate} bpm" if record.heart_rate else "-",
            bp or "-",
            classification_styles.get(record.classification, str(record.afib)),
        )

    console.print(table)


@ecg.command("get")
@click.argument("signal_id", type=int)
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
@click.option(
    "--no-signal", is_flag=True, help="Omit raw ECG waveform from JSON output (metadata only)."
)
def ecg_get(signal_id: int, fmt: str, no_signal: bool) -> None:
    """Show details of a specific ECG recording."""
    import json

    from withings_cli.api import WithingsClient

    try:
        client = WithingsClient()
    except AuthError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1) from None

    # Fetch signal data
    signal = client.get_heart_signal(signal_id)

    # Fetch metadata (BP, afib) from the list endpoint for this recording
    metadata = _find_heart_record(client, signal_id)

    duration = len(signal.signal) / signal.sampling_frequency if signal.sampling_frequency else 0

    if fmt == "json":
        data: dict[str, Any] = {
            "signal_id": signal_id,
            "heart_rate": signal.heart_rate.value,
            "sampling_frequency": signal.sampling_frequency,
            "duration_seconds": round(duration, 1),
            "data_points": len(signal.signal),
        }
        if not no_signal:
            data["signal"] = signal.signal
        if metadata:
            data["afib_classification"] = metadata.classification.name.lower()
            if metadata.bloodpressure:
                data["systole"] = metadata.bloodpressure.systole
                data["diastole"] = metadata.bloodpressure.diastole
            data["date"] = metadata.datetime.isoformat()
        console.print(json.dumps(data))
        return

    console.print(f"[bold]ECG Signal {signal_id}[/bold]")
    if metadata:
        console.print(f"Date: {metadata.datetime.strftime('%Y-%m-%d %H:%M')}")
    console.print(f"Heart rate: {signal.heart_rate.value} bpm")
    if metadata and metadata.bloodpressure:
        bp = metadata.bloodpressure
        console.print(f"Blood pressure: {bp.systole}/{bp.diastole} mmHg")
    if metadata:
        console.print(f"AFib: {metadata.classification.name}")
    console.print(
        f"Duration: {duration:.1f}s ({len(signal.signal)} points @ {signal.sampling_frequency} Hz)"
    )

    # Signal amplitude summary for quick assessment
    if signal.signal:
        console.print(
            f"Signal range: [{min(signal.signal)}, {max(signal.signal)}] "
            f"(mean: {sum(signal.signal) / len(signal.signal):.0f})"
        )


def _find_heart_record(client: Any, signal_id: int) -> Any:
    """Find the HeartRecord metadata matching a signal_id from the list endpoint."""
    response = client.get_heart_list()
    for record in response.series:
        if record.signal_id == signal_id:
            return record
    return None
