import re
import json
from datetime import datetime, date
from typing import Tuple, Optional, Dict, Any

VALID_ASSET_TYPES = {"pole", "valve", "manhole", "transformer"}
VALID_STATUSES = {"active", "decommissioned", "proposed"}
ASSET_ID_REGEX = re.compile(r"^[A-Z]{2}-\d{4}$")

def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned

def standardize_surveyor(name: Optional[str]) -> str:
    if not name:
        return ""
    return re.sub(r"\s+", " ", name.strip()).title()

def parse_coordinate(val: Any, is_latitude: bool = True) -> Tuple[Optional[float], Optional[str]]:
    if val is None or str(val).strip() == "":
        return None, "Coordinate is required"
    s = str(val).strip().upper()
    multiplier = 1.0
    if is_latitude:
        if s.endswith("N"):
            s = s[:-1].strip()
        elif s.endswith("S"):
            s = s[:-1].strip()
            multiplier = -1.0
    else:
        if s.endswith("E"):
            s = s[:-1].strip()
        elif s.endswith("W"):
            s = s[:-1].strip()
            multiplier = -1.0
    try:
        coord = float(s) * multiplier
    except ValueError:
        coord_name = "Latitude" if is_latitude else "Longitude"
        return None, f"{coord_name} must be a valid numeric value"

    if is_latitude:
        if coord < -90.0 or coord > 90.0:
            return None, f"Latitude {coord} is outside the valid range of -90 to 90"
    else:
        if coord < -180.0 or coord > 180.0:
            return None, f"Longitude {coord} is outside the valid range of -180 to 180"

    return coord, None

def get_condition_band(score: int) -> str:
    if 8 <= score <= 10:
        return "GOOD"
    elif 5 <= score <= 7:
        return "FAIR"
    elif 3 <= score <= 4:
        return "POOR"
    elif 0 <= score <= 2:
        return "CRITICAL"
    return "UNKNOWN"

def validate_and_clean_record(raw: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    asset_id = str(raw.get("asset_id", "")).strip()
    if not asset_id:
        return None, "asset_id is missing or blank"
    if not ASSET_ID_REGEX.match(asset_id):
        return None, f"asset_id '{asset_id}' does not match required format (two uppercase letters, hyphen, four digits, e.g. PL-0142)"

    raw_name = raw.get("name", "")
    name = clean_text(raw_name)
    if not name or len(name) < 3 or len(name) > 120:
        return None, f"name must be between 3 and 120 characters after cleaning (was '{name}')"

    raw_type = str(raw.get("asset_type", "")).strip().lower()
    if raw_type not in VALID_ASSET_TYPES:
        return None, f"asset_type '{raw_type}' is unrecognized (must be one of: {', '.join(sorted(VALID_ASSET_TYPES))})"

    lat, lat_err = parse_coordinate(raw.get("latitude"), is_latitude=True)
    if lat_err:
        return None, lat_err

    lon, lon_err = parse_coordinate(raw.get("longitude"), is_latitude=False)
    if lon_err:
        return None, lon_err

    raw_elev = raw.get("elevation_m")
    elevation_m = None
    if raw_elev is not None and str(raw_elev).strip() != "":
        try:
            elevation_m = float(str(raw_elev).strip())
        except ValueError:
            elevation_m = None

    raw_date = str(raw.get("surveyed_on", "")).strip()
    if not raw_date:
        return None, "surveyed_on date is required"
    try:
        survey_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        return None, f"surveyed_on '{raw_date}' is not a valid date in YYYY-MM-DD format"
    if survey_date > date.today():
        return None, f"surveyed_on '{survey_date}' cannot be a future date"

    surveyor = standardize_surveyor(str(raw.get("surveyor", "")))
    if not surveyor:
        return None, "surveyor name is required"

    raw_status = str(raw.get("status", "")).strip().lower()
    if raw_status not in VALID_STATUSES:
        return None, f"status '{raw_status}' is invalid (must be one of: {', '.join(sorted(VALID_STATUSES))})"

    raw_score = raw.get("condition_score")
    if raw_score is None or str(raw_score).strip() == "":
        return None, "condition_score is blank"
    try:
        score = int(float(str(raw_score).strip()))
    except ValueError:
        return None, f"condition_score '{raw_score}' is not a valid integer"
    if score < 0 or score > 10:
        return None, f"condition_score {score} is out of valid range (0 to 10)"

    if raw_status == "decommissioned" and score > 2:
        return None, f"field validation failed: decommissioned asset cannot have condition_score above 2 (got {score})"

    raw_attr = raw.get("attribute_json")
    attr_data = None
    if raw_attr is not None and str(raw_attr).strip() != "":
        if isinstance(raw_attr, dict):
            attr_data = raw_attr
        else:
            try:
                attr_data = json.loads(str(raw_attr))
            except Exception as e:
                return None, f"attribute_json is not valid JSON: {str(e)}"
    else:
        return None, "attribute_json is missing or empty"

    cleaned = {
        "asset_id": asset_id,
        "name": name,
        "asset_type": raw_type,
        "latitude": lat,
        "longitude": lon,
        "elevation_m": elevation_m,
        "surveyed_on": survey_date,
        "surveyor": surveyor,
        "status": raw_status,
        "condition_score": score,
        "condition_band": get_condition_band(score),
        "attribute_json": attr_data,
    }
    return cleaned, None