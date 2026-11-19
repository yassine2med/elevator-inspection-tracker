"""Track elevator inspection certificate expiry dates."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REQUIRED = ("unit", "building", "type", "last_inspection", "certificate_expires")
BANDS = ((0, "EXPIRED"), (30, "DUE 30"), (60, "DUE 60"), (90, "DUE 90"))


class TrackerError(ValueError):
    """Raised when the input file or a row is not valid."""


@dataclass(frozen=True)
class Unit:
    """One elevator or lift with its certificate state on a given day."""

    unit: str
    building: str
    kind: str
    last_inspection: date
    expires: date
    days_left: int
    band: str


def classify(days_left: int) -> str:
    """Return EXPIRED, DUE 30, DUE 60, DUE 90 or OK for days left on the certificate."""
    if days_left < 0:
        return "EXPIRED"
    for limit, label in BANDS[1:]:
        if days_left <= limit:
            return label
    return "OK"


def _date(value: str, line: int, field: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise TrackerError(f"line {line}: bad {field} '{value}', use YYYY-MM-DD") from exc


def load_units(path: str | Path, today: date) -> list[Unit]:
    """Read the CSV and compute each unit's band as of today."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise TrackerError("missing columns: " + ", ".join(missing))
        units: list[Unit] = []
        seen: set[str] = set()
        for line, row in enumerate(reader, start=2):
            name = row["unit"].strip()
            if not name:
                raise TrackerError(f"line {line}: unit is empty")
            if name in seen:
                raise TrackerError(f"line {line}: duplicate unit {name}")
            seen.add(name)
            last = _date(row["last_inspection"], line, "last_inspection")
            expires = _date(row["certificate_expires"], line, "certificate_expires")
            if expires < last:
                raise TrackerError(f"line {line}: certificate expires before the last inspection")
            days_left = (expires - today).days
            units.append(Unit(name, row["building"].strip(), row["type"].strip(),
                              last, expires, days_left, classify(days_left)))
    return sorted(units, key=lambda u: (u.days_left, u.unit))


def needs_action(units: list[Unit], within: int = 90) -> list[Unit]:
    """Units already expired or expiring within the given number of days."""
    return [u for u in units if u.days_left <= within]


def format_report(units: list[Unit]) -> str:
    """Plain text table, soonest expiry first."""
    lines = [f"{'Unit':<8}{'Building':<12}{'Type':<12}{'Expires':<12}{'Days':>6}  Status"]
    for u in units:
        lines.append(f"{u.unit:<8}{u.building:<12}{u.kind:<12}{u.expires.isoformat():<12}{u.days_left:>6}  {u.band}")
    return "\n".join(lines)
