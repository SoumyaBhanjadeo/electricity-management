import io
import csv
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import BulkUploadResponse
from app.security import require_admin
from app.data_cleaner import validate_and_clean_record
from app.config import settings
from app import crud

router = APIRouter(prefix="/api/v1/upload", tags=["Bulk Upload"])

REQUIRED_COLUMNS = [
    "asset_id", "name", "asset_type", "latitude", "longitude",
    "elevation_m", "surveyed_on", "surveyor", "status",
    "condition_score", "attribute_json"
]

@router.post("", response_model=BulkUploadResponse)
async def upload_csv_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a CSV file."
        )

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty or missing header row."
        )

    missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV missing required columns: {', '.join(missing)}"
        )

    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rejects_path = os.path.join(settings.OUTPUT_DIR, f"unusable_records_{timestamp_str}.csv")

    rows_read = 0
    rows_accepted = 0
    rows_rejected = 0
    rejected_rows = []

    for row in reader:
        rows_read += 1
        cleaned_data, error_reason = validate_and_clean_record(row)
        if error_reason:
            rows_rejected += 1
            row_copy = dict(row)
            row_copy["rejection_reason"] = error_reason
            rejected_rows.append(row_copy)
            continue

        existing = crud.get_equipment_by_id(db, cleaned_data["asset_id"])
        if existing:
            rows_rejected += 1
            row_copy = dict(row)
            row_copy["rejection_reason"] = f"Equipment ID '{cleaned_data['asset_id']}' already exists in database"
            rejected_rows.append(row_copy)
            continue

        crud.create_equipment_with_visit(db, cleaned_data, user_id=admin_user.id)
        rows_accepted += 1

    saved_rejects_file = None
    if rejected_rows:
        with open(rejects_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = list(rejected_rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rejected_rows)
        saved_rejects_file = rejects_path

    return BulkUploadResponse(
        rows_read=rows_read,
        rows_accepted=rows_accepted,
        rows_rejected=rows_rejected,
        rejects_file=saved_rejects_file
    )