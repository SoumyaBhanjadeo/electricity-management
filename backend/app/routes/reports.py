from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    SummaryReportResponse,
    RepairAssetResponse,
    FrequentVisitResponse,
    NearestEquipmentResponse,
)
from app.security import require_surveyor
from app import crud

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["Analytical Reports"],
    dependencies=[Depends(require_surveyor)]
)

@router.get("/summary", response_model=SummaryReportResponse)
def get_summary(db: Session = Depends(get_db)):
    return crud.calculate_summary_report(db)

@router.get("/repairs", response_model=List[RepairAssetResponse])
def get_repair_assets(db: Session = Depends(get_db)):
    return crud.get_repair_list(db)

@router.get("/frequent-visits", response_model=List[FrequentVisitResponse])
def get_frequent_visits(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    return crud.get_frequently_visited(db, limit=limit)

@router.get("/nearest", response_model=NearestEquipmentResponse)
def get_nearest_equipment(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    db: Session = Depends(get_db)
):
    nearest = crud.find_nearest_equipment(db, latitude, longitude)
    if not nearest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No equipment records found in database."
        )
    return nearest