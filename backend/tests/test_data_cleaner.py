import pytest
from app.data_cleaner import (
    clean_text,
    standardize_surveyor,
    parse_coordinate,
    get_condition_band,
    validate_and_clean_record
)

def test_clean_text():
    assert clean_text("   steel   pole  near market  ") == "Steel pole near market"
    assert clean_text("") == ""
    assert clean_text(None) == ""

def test_standardize_surveyor():
    assert standardize_surveyor("   amit   patel  ") == "Amit Patel"
    assert standardize_surveyor("r. sharma") == "R. Sharma"
    assert standardize_surveyor("") == ""

def test_parse_coordinate_compass():
    lat, err = parse_coordinate("20.2961 N", is_latitude=True)
    assert err is None
    assert round(lat, 4) == 20.2961

    lat_s, err = parse_coordinate("20.2961 S", is_latitude=True)
    assert err is None
    assert round(lat_s, 4) == -20.2961

    lon, err = parse_coordinate("85.8245 E", is_latitude=False)
    assert err is None
    assert round(lon, 4) == 85.8245

    lon_w, err = parse_coordinate("85.8245 W", is_latitude=False)
    assert err is None
    assert round(lon_w, 4) == -85.8245

def test_parse_coordinate_out_of_bounds():
    _, err = parse_coordinate("95.0", is_latitude=True)
    assert err is not None
    assert "outside the valid range" in err

    _, err = parse_coordinate("200.0", is_latitude=False)
    assert err is not None
    assert "outside the valid range" in err

    _, err = parse_coordinate("not_a_number", is_latitude=True)
    assert err is not None
    assert "must be a valid numeric" in err

def test_condition_band():
    assert get_condition_band(10) == "GOOD"
    assert get_condition_band(8) == "GOOD"
    assert get_condition_band(7) == "FAIR"
    assert get_condition_band(5) == "FAIR"
    assert get_condition_band(4) == "POOR"
    assert get_condition_band(3) == "POOR"
    assert get_condition_band(2) == "CRITICAL"
    assert get_condition_band(0) == "CRITICAL"

def test_validate_and_clean_record_valid():
    raw = {
        "asset_id": "PL-0142",
        "name": "Distribution Pole Sector 9",
        "asset_type": "POLE",
        "latitude": "20.2960 N",
        "longitude": "85.8245 E",
        "elevation_m": "45.2",
        "surveyed_on": "2026-09-01",
        "surveyor": "R. Sharma",
        "status": "active",
        "condition_score": "8",
        "attribute_json": '{"height_m": 11.5}'
    }
    cleaned, err = validate_and_clean_record(raw)
    assert err is None
    assert cleaned["asset_id"] == "PL-0142"
    assert cleaned["asset_type"] == "pole"
    assert cleaned["surveyor"] == "R. Sharma"
    assert cleaned["condition_band"] == "GOOD"

def test_validate_record_decommissioned_score_rule():
    raw = {
        "asset_id": "PL-0142",
        "name": "Decommissioned Pole",
        "asset_type": "pole",
        "latitude": "20.2960",
        "longitude": "85.8245",
        "surveyed_on": "2026-09-01",
        "surveyor": "Ramesh Sharma",
        "status": "decommissioned",
        "condition_score": "5",
        "attribute_json": '{"height_m": 11.5}'
    }
    cleaned, err = validate_and_clean_record(raw)
    assert cleaned is None
    assert "decommissioned asset cannot have condition_score above 2" in err

def test_validate_record_future_date():
    raw = {
        "asset_id": "PL-0142",
        "name": "Future Pole",
        "asset_type": "pole",
        "latitude": "20.2960",
        "longitude": "85.8245",
        "surveyed_on": "2035-01-01",
        "surveyor": "Ramesh Sharma",
        "status": "active",
        "condition_score": "8",
        "attribute_json": '{"height_m": 11.5}'
    }
    cleaned, err = validate_and_clean_record(raw)
    assert cleaned is None
    assert "cannot be a future date" in err