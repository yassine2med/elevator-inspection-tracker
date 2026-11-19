from datetime import date

import pytest

from elevtrack.__main__ import main
from elevtrack.tracker import (TrackerError, classify, format_report, load_units,
                               needs_action)

TODAY = date(2026, 11, 19)
HEADER = "unit,building,type,last_inspection,certificate_expires\n"


def make(tmp_path, body, header=HEADER):
    p = tmp_path / "u.csv"
    p.write_text(header + body)
    return p


@pytest.mark.parametrize("days,band", [
    (-1, "EXPIRED"), (0, "DUE 30"), (30, "DUE 30"), (31, "DUE 60"),
    (60, "DUE 60"), (61, "DUE 90"), (90, "DUE 90"), (91, "OK"),
])
def test_classify_boundaries(days, band):
    assert classify(days) == band


def test_load_sorts_soonest_first(tmp_path):
    p = make(tmp_path, "A,B,P,2026-01-01,2027-01-01\nB,B,P,2026-01-01,2026-12-01\n")
    assert [u.unit for u in load_units(p, TODAY)] == ["B", "A"]


def test_days_left_computed(tmp_path):
    p = make(tmp_path, "A,B,P,2026-01-01,2026-11-30\n")
    u = load_units(p, TODAY)[0]
    assert u.days_left == 11 and u.band == "DUE 30"


def test_needs_action_filters(tmp_path):
    p = make(tmp_path, "A,B,P,2026-01-01,2028-01-01\nB,B,P,2026-01-01,2026-12-01\n")
    assert [u.unit for u in needs_action(load_units(p, TODAY))] == ["B"]


def test_missing_column(tmp_path):
    p = make(tmp_path, "A,B,P\n", header="unit,building,type\n")
    with pytest.raises(TrackerError, match="missing columns"):
        load_units(p, TODAY)


def test_bad_date(tmp_path):
    with pytest.raises(TrackerError, match="bad certificate_expires"):
        load_units(make(tmp_path, "A,B,P,2026-01-01,12/31/2026\n"), TODAY)


def test_duplicate_unit(tmp_path):
    with pytest.raises(TrackerError, match="duplicate"):
        load_units(make(tmp_path, "A,B,P,2026-01-01,2027-01-01\nA,B,P,2026-01-01,2027-01-01\n"), TODAY)


def test_expiry_before_inspection(tmp_path):
    with pytest.raises(TrackerError, match="before the last inspection"):
        load_units(make(tmp_path, "A,B,P,2026-06-01,2026-01-01\n"), TODAY)


def test_report_contains_status(tmp_path):
    out = format_report(load_units(make(tmp_path, "A,B,P,2025-01-01,2026-01-01\n"), TODAY))
    assert "EXPIRED" in out


def test_cli_exit_code_2_when_expired(capsys):
    assert main(["data/units.csv", "--today", "2026-11-19"]) == 2
    assert "EL-03" in capsys.readouterr().out


def test_cli_ok_exit_zero(capsys):
    assert main(["data/units.csv", "--today", "2026-01-01"]) == 0


def test_cli_missing_file(capsys):
    assert main(["nope.csv"]) == 1
