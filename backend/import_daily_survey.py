import os
import sys
import csv
import json
import argparse
from datetime import datetime, timezone
from app.database import SessionLocal, engine, Base
from app.models import FieldEquipment, SurveyVisit, User
from app.data_cleaner import validate_and_clean_record
from app.geo_calculator import calculate_geographic_extent, build_geojson_feature_collection
from app.config import settings

REQUIRED_COLUMNS = [
    "asset_id", "name", "asset_type", "latitude", "longitude",
    "elevation_m", "surveyed_on", "surveyor", "status",
    "condition_score", "attribute_json"
]

def run_ingestion(
    csv_path: str,
    rejects_path: str = None,
    map_path: str = None,
    summary_path: str = None,
    strict_mode: bool = False
):
    if not os.path.exists(csv_path):
        print(f"Error: Input file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    if not rejects_path:
        rejects_path = os.path.join(settings.OUTPUT_DIR, "unusable_records.csv")
    if not map_path:
        map_path = os.path.join(settings.OUTPUT_DIR, "equipment_locations_map.geojson")
    if not summary_path:
        summary_path = os.path.join(settings.OUTPUT_DIR, "supervisor_summary_report.txt")

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("Error: The CSV file is empty or missing headers.", file=sys.stderr)
            sys.exit(1)

        missing_cols = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing_cols:
            print(f"Error: Missing required columns: {', '.join(missing_cols)}", file=sys.stderr)
            sys.exit(1)

        raw_rows = list(reader)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    default_user = db.query(User).filter(User.role == "admin").first()
    default_user_id = default_user.id if default_user else None

    rows_read = len(raw_rows)
    rows_accepted = 0
    rows_rejected = 0
    rejected_records = []
    accepted_records = []

    for row in raw_rows:
        cleaned_data, error_reason = validate_and_clean_record(row)
        if error_reason:
            if strict_mode:
                print(f"Strict mode aborted run: {error_reason} in row {row.get('asset_id')}", file=sys.stderr)
                db.close()
                sys.exit(1)
            rows_rejected += 1
            row_copy = dict(row)
            row_copy["rejection_reason"] = error_reason
            rejected_records.append(row_copy)
            continue

        existing = db.query(FieldEquipment).filter(FieldEquipment.asset_id == cleaned_data["asset_id"]).first()
        if existing:
            err = f"Duplicate asset_id: {cleaned_data['asset_id']} already exists in database"
            if strict_mode:
                print(f"Strict mode aborted run: {err}", file=sys.stderr)
                db.close()
                sys.exit(1)
            rows_rejected += 1
            row_copy = dict(row)
            row_copy["rejection_reason"] = err
            rejected_records.append(row_copy)
            continue

        eq = FieldEquipment(
            asset_id=cleaned_data["asset_id"],
            name=cleaned_data["name"],
            asset_type=cleaned_data["asset_type"],
            latitude=cleaned_data["latitude"],
            longitude=cleaned_data["longitude"],
            elevation_m=cleaned_data.get("elevation_m"),
            status=cleaned_data["status"],
            created_by=default_user_id,
            updated_by=default_user_id
        )
        db.add(eq)
        db.flush()

        visit = SurveyVisit(
            equipment_id=eq.asset_id,
            surveyed_on=cleaned_data["surveyed_on"],
            surveyor=cleaned_data["surveyor"],
            condition_score=cleaned_data["condition_score"],
            condition_band=cleaned_data["condition_band"],
            attribute_json=cleaned_data.get("attribute_json"),
            created_by=default_user_id,
            updated_by=default_user_id
        )
        db.add(visit)
        accepted_records.append((eq, visit))
        rows_accepted += 1

    db.commit()

    if rejected_records:
        with open(rejects_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = list(rejected_records[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rejected_records)

    all_equipment = db.query(FieldEquipment).filter(FieldEquipment.is_active == True).all()
    all_visits = db.query(SurveyVisit).filter(SurveyVisit.is_active == True).all()

    geojson_data = build_geojson_feature_collection(all_equipment)
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)

    extent = calculate_geographic_extent(all_equipment)

    by_type = {}
    eq_map = {eq.asset_id: eq for eq in all_equipment}
    for v in all_visits:
        eq = eq_map.get(v.equipment_id)
        if eq:
            by_type.setdefault(eq.asset_type, []).append(v)

    run_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("ELECTRICITY UTILITY - FIELD SURVEY SUMMARY REPORT\n")
        f.write("=" * 70 + "\n")
        f.write(f"Run Timestamp: {run_time_str}\n")
        f.write(f"Input File:    {csv_path}\n\n")
        f.write(f"{'Asset Type':<15} {'Surveyed':<10} {'Avg Condition':<15} {'Worst Asset':<15} {'Worst Score':<12}\n")
        f.write("-" * 70 + "\n")
        for asset_type, v_list in sorted(by_type.items()):
            count = len(v_list)
            avg_score = round(sum(v.condition_score for v in v_list) / count, 2) if count else 0.0
            worst = min(v_list, key=lambda x: x.condition_score) if v_list else None
            worst_id = worst.equipment_id if worst else "N/A"
            worst_score = str(worst.condition_score) if worst else "N/A"
            f.write(f"{asset_type.capitalize():<15} {count:<10} {avg_score:<15.2f} {worst_id:<15} {worst_score:<12}\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total Assets in Database: {len(all_equipment)}\n")
        f.write(f"Total Inspection Visits:  {len(all_visits)}\n\n")
        if extent:
            f.write("Geographic Extent (Bounding Box):\n")
            f.write(f"  Latitude Range:  {extent['min_latitude']} to {extent['max_latitude']}\n")
            f.write(f"  Longitude Range: {extent['min_longitude']} to {extent['max_longitude']}\n")
        f.write("=" * 70 + "\n")

    log_entry = f"[{run_time_str}] File: {csv_path} | Rows Read: {rows_read} | Accepted: {rows_accepted} | Rejected: {rows_rejected} | Strict: {strict_mode}\n"
    with open(settings.LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry)

    db.close()

    print("\n--- Daily Survey Import Completed ---")
    print(f"Rows read:      {rows_read}")
    print(f"Rows accepted:  {rows_accepted}")
    print(f"Rows rejected:  {rows_rejected}")
    if rows_rejected > 0:
        print(f"Rejects file:   {rejects_path}")
    print(f"Map layer file: {map_path}")
    print(f"Summary report: {summary_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Daily Field Survey Ingestion Tool for Electricity Utility Assets."
    )
    parser.add_argument("csv_path", help="Path to raw daily field survey CSV file.")
    parser.add_argument("--rejects", help="Optional custom output path for rejected records CSV.")
    parser.add_argument("--map", help="Optional custom output path for GeoJSON map file.")
    parser.add_argument("--summary", help="Optional custom output path for plain text summary report.")
    parser.add_argument("--strict", action="store_true", help="Strict mode: aborts entire run if any row is invalid.")
    args = parser.parse_args()

    run_ingestion(
        csv_path=args.csv_path,
        rejects_path=args.rejects,
        map_path=args.map,
        summary_path=args.summary,
        strict_mode=args.strict
    )

if __name__ == "__main__":
    main()