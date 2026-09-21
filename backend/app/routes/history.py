from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, SurveyVisit
from app.schemas import SurveyVisitCreate, SurveyVisitResponse
from app.security import require_surveyor
from app import crud

router = APIRouter(prefix="/api/v1/records", tags=["Survey History"])

@router.get("/{asset_id}/history", response_model=List[SurveyVisitResponse], dependencies=[Depends(require_surveyor)])
def get_equipment_history(
    asset_id: str,
    db: Session = Depends(get_db)
):
    eq = crud.get_equipment_by_id(db, asset_id.strip())
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with code '{asset_id}' does not exist."
        )
    visits = db.query(SurveyVisit).filter(
        SurveyVisit.equipment_id == asset_id.strip(),
        SurveyVisit.is_active == True
    ).order_by(SurveyVisit.surveyed_on.desc()).all()
    return visits

@router.post("/{asset_id}/history", response_model=SurveyVisitResponse, status_code=status.HTTP_201_CREATED)
def add_equipment_visit(
    asset_id: str,
    payload: SurveyVisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_surveyor)
):
    eq = crud.get_equipment_by_id(db, asset_id.strip())
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with code '{asset_id}' does not exist."
        )
    return crud.add_survey_visit(db, asset_id.strip(), payload, user_id=current_user.id)