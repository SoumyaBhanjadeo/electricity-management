from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import (
    EquipmentCreate,
    EquipmentReplace,
    EquipmentPatch,
    EquipmentResponse,
    PaginatedEquipmentResponse,
)
from app.security import require_surveyor, require_admin
from app.data_cleaner import validate_and_clean_record
from app import crud

router = APIRouter(prefix="/api/v1/records", tags=["Equipment Records"])

@router.get("", response_model=PaginatedEquipmentResponse, dependencies=[Depends(require_surveyor)])
def list_records(
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    surveyor: Optional[str] = None,
    min_condition: Optional[int] = Query(None, ge=0, le=10),
    max_condition: Optional[int] = Query(None, ge=0, le=10),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    items, total = crud.get_equipment_paginated(
        db=db,
        offset=offset,
        limit=limit,
        asset_type=asset_type,
        status=status,
        surveyor=surveyor,
        min_condition=min_condition,
        max_condition=max_condition,
        search=search
    )
    return PaginatedEquipmentResponse(total=total, limit=limit, offset=offset, items=items)

@router.get("/{asset_id}", response_model=EquipmentResponse, dependencies=[Depends(require_surveyor)])
def get_record(
    asset_id: str,
    db: Session = Depends(get_db)
):
    eq = crud.get_equipment_by_id(db, asset_id.strip())
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with code '{asset_id}' does not exist."
        )
    return eq

@router.post("", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_surveyor)
):
    existing = crud.get_equipment_by_id(db, payload.asset_id.strip())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Equipment with code '{payload.asset_id}' already exists."
        )
    cleaned_data, error_reason = validate_and_clean_record(payload.model_dump())
    if error_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {error_reason}"
        )
    return crud.create_equipment_with_visit(db, cleaned_data, user_id=current_user.id)

@router.put("/{asset_id}", response_model=EquipmentResponse)
def replace_record(
    asset_id: str,
    payload: EquipmentReplace,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_surveyor)
):
    eq = crud.get_equipment_by_id(db, asset_id.strip())
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with code '{asset_id}' does not exist."
        )
    return crud.replace_equipment(db, eq, payload, user_id=current_user.id)

@router.patch("/{asset_id}", response_model=EquipmentResponse)
def patch_record(
    asset_id: str,
    payload: EquipmentPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_surveyor)
):
    eq = crud.get_equipment_by_id(db, asset_id.strip())
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with code '{asset_id}' does not exist."
        )
    return crud.patch_equipment(db, eq, payload, user_id=current_user.id)

@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_record(
    asset_id: str,
    db: Session = Depends(get_db)
):
    eq = crud.get_equipment_by_id(db, asset_id.strip())
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment with code '{asset_id}' does not exist."
        )
    crud.delete_equipment(db, eq)
    return None