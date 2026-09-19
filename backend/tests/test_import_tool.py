import os
import csv
import pytest
from import_daily_survey import run_ingestion

def test_import_tool_missing_columns(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    with open(bad_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["asset_id", "name"])
        writer.writerow(["PL-0001", "Incomplete Row"])

    with pytest.raises(SystemExit) as exc_info:
        run_ingestion(str(bad_csv))
    assert exc_info.value.code == 1

def test_import_tool_strict_mode_aborts_on_fault(tmp_path):
    fault_csv = tmp_path / "faulty.csv"
    with open(fault_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "asset_id", "name", "asset_type", "latitude", "longitude",
            "elevation_m", "surveyed_on", "surveyor", "status",
            "condition_score", "attribute_json"
        ])
        writer.writerow([
            "BAD_ID", "Faulty Pole", "pole", "20.29", "85.82",
            "40.0", "2026-09-01", "R. Sharma", "active",
            "8", '{"height_m": 10}'
        ])

    with pytest.raises(SystemExit) as exc_info:
        run_ingestion(str(fault_csv), strict_mode=True)
    assert exc_info.value.code == 1