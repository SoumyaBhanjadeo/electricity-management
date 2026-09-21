from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models import FieldEquipment, SurveyVisit
from app.schemas import EquipmentReplace, EquipmentPatch, SurveyVisitCreate
from app.data_cleaner import get_condition_band, clean_text
from app.geo_calculator import haversine_distance_km, calculate_geographic_extent
from app.cache import summary_cache

def get_equipment_paginated(
    db: Session,
    offset: int = 0,
    limit: int = 25,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    surveyor: Optional[str] = None,
    min_condition: Optional[int] = None,
    max_condition: Optional[int] = None,
    search: Optional[str] = None,
) -> Tuple[List[FieldEquipment], int]:
    limit = max(1, min(limit, 100))
    query = db.query(FieldEquipment).filter(FieldEquipment.is_active == True)

    if asset_type:
        query = query.filter(func.lower(FieldEquipment.asset_type) == asset_type.strip().lower())
    if status:
        query = query.filter(func.lower(FieldEquipment.status) == status.strip().lower())
    if search:
        query = query.filter(FieldEquipment.name.ilike(f"%{search.strip()}%"))

    if surveyor or min_condition is not None or max_condition is not None:
        query = query.join(SurveyVisit, FieldEquipment.asset_id == SurveyVisit.equipment_id)
        if surveyor:
            query = query.filter(SurveyVisit.surveyor.ilike(f"%{surveyor.strip()}%"))
        if min_condition is not None:
            query = query.filter(SurveyVisit.condition_score >= min_condition)
        if max_condition is not None:
            query = query.filter(SurveyVisit.condition_score <= max_condition)
        query = query.distinct()

    total = query.count()
    items = query.order_by(FieldEquipment.asset_id).offset(offset).limit(limit).all()
    return items, total

def get_equipment_by_id(db: Session, asset_id: str) -> Optional[FieldEquipment]:
    return db.query(FieldEquipment).filter(
        FieldEquipment.asset_id == asset_id,
        FieldEquipment.is_active == True
    ).first()

def create_equipment_with_visit(
    db: Session,
    data: Dict[str, Any],
    user_id: Optional[int] = None
) -> FieldEquipment:
    eq = FieldEquipment(
        asset_id=data["asset_id"],
        name=data["name"],
        asset_type=data["asset_type"],
        latitude=data["latitude"],
        longitude=data["longitude"],
        elevation_m=data.get("elevation_m"),
        status=data["status"],
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(eq)
    db.flush()

    visit = SurveyVisit(
        equipment_id=eq.asset_id,
        surveyed_on=data["surveyed_on"],
        surveyor=data["surveyor"],
        condition_score=data["condition_score"],
        condition_band=data.get("condition_band", get_condition_band(data["condition_score"])),
        attribute_json=data.get("attribute_json"),
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(visit)
    db.commit()
    db.refresh(eq)
    summary_cache.invalidate()
    return eq

def replace_equipment(
    db: Session,
    eq: FieldEquipment,
    replace_data: EquipmentReplace,
    user_id: Optional[int] = None
) -> FieldEquipment:
    eq.name = clean_text(replace_data.name)
    eq.asset_type = replace_data.asset_type.lower()
    eq.latitude = replace_data.latitude
    eq.longitude = replace_data.longitude
    eq.elevation_m = replace_data.elevation_m
    eq.status = replace_data.status.lower()
    eq.updated_by = user_id
    db.commit()
    db.refresh(eq)
    summary_cache.invalidate()
    return eq

def patch_equipment(
    db: Session,
    eq: FieldEquipment,
    patch_data: EquipmentPatch,
    user_id: Optional[int] = None
) -> FieldEquipment:
    if patch_data.name is not None:
        eq.name = clean_text(patch_data.name)
    if patch_data.asset_type is not None:
        eq.asset_type = patch_data.asset_type.lower()
    if patch_data.latitude is not None:
        eq.latitude = patch_data.latitude
    if patch_data.longitude is not None:
        eq.longitude = patch_data.longitude
    if patch_data.elevation_m is not None:
        eq.elevation_m = patch_data.elevation_m
    if patch_data.status is not None:
        eq.status = patch_data.status.lower()
    eq.updated_by = user_id
    db.commit()
    db.refresh(eq)
    summary_cache.invalidate()
    return eq

def delete_equipment(db: Session, eq: FieldEquipment) -> None:
    db.delete(eq)
    db.commit()
    summary_cache.invalidate()

def add_survey_visit(
    db: Session,
    equipment_id: str,
    visit_data: SurveyVisitCreate,
    user_id: Optional[int] = None
) -> SurveyVisit:
    visit = SurveyVisit(
        equipment_id=equipment_id,
        surveyed_on=visit_data.surveyed_on,
        surveyor=visit_data.surveyor,
        condition_score=visit_data.condition_score,
        condition_band=get_condition_band(visit_data.condition_score),
        attribute_json=visit_data.attribute_json,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    summary_cache.invalidate()
    return visit

def calculate_summary_report(db: Session) -> Dict[str, Any]:
    cached = summary_cache.get()
    if cached is not None:
        return cached

    equipment_items = db.query(FieldEquipment).filter(FieldEquipment.is_active == True).all()
    visits = db.query(SurveyVisit).filter(SurveyVisit.is_active == True).all()

    by_type: Dict[str, List[SurveyVisit]] = {}
    equipment_map = {eq.asset_id: eq for eq in equipment_items}

    for v in visits:
        eq = equipment_map.get(v.equipment_id)
        if eq:
            by_type.setdefault(eq.asset_type, []).append(v)

    type_summaries = []
    for asset_type, v_list in sorted(by_type.items()):
        total_surveyed = len(v_list)
        avg_score = round(sum(v.condition_score for v in v_list) / total_surveyed, 2) if total_surveyed else 0.0
        worst_visit = min(v_list, key=lambda x: x.condition_score) if v_list else None

        type_summaries.append({
            "asset_type": asset_type,
            "total_surveyed": total_surveyed,
            "average_condition_score": avg_score,
            "worst_condition_asset": worst_visit.equipment_id if worst_visit else None,
            "worst_condition_score": worst_visit.condition_score if worst_visit else None,
        })

    extent = calculate_geographic_extent(equipment_items)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_assets": len(equipment_items),
        "total_visits": len(visits),
        "by_asset_type": type_summaries,
        "geographic_extent": extent,
    }
    summary_cache.set(result)
    return result

def get_repair_list(db: Session) -> List[Dict[str, Any]]:
    active_equipment = db.query(FieldEquipment).filter(
        FieldEquipment.status == "active",
        FieldEquipment.is_active == True
    ).all()
    repairs = []
    for eq in active_equipment:
        if eq.visits:
            latest = sorted(eq.visits, key=lambda v: v.surveyed_on, reverse=True)[0]
            if latest.condition_score < 5:
                repairs.append({
                    "asset_id": eq.asset_id,
                    "name": eq.name,
                    "asset_type": eq.asset_type,
                    "latitude": eq.latitude,
                    "longitude": eq.longitude,
                    "status": eq.status,
                    "latest_condition_score": latest.condition_score,
                    "latest_condition_band": latest.condition_band,
                    "latest_surveyed_on": latest.surveyed_on,
                })
    return repairs

def get_frequently_visited(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    results = (
        db.query(
            FieldEquipment.asset_id,
            FieldEquipment.name,
            FieldEquipment.asset_type,
            func.count(SurveyVisit.id).label("visit_count")
        )
        .join(SurveyVisit, FieldEquipment.asset_id == SurveyVisit.equipment_id)
        .filter(FieldEquipment.is_active == True)
        .group_by(FieldEquipment.asset_id, FieldEquipment.name, FieldEquipment.asset_type)
        .order_by(func.count(SurveyVisit.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "asset_id": r.asset_id,
            "name": r.name,
            "asset_type": r.asset_type,
            "visit_count": r.visit_count,
            "latest_condition_score": None,
        }
        for r in results
    ]

def find_nearest_equipment(db: Session, lat: float, lon: float) -> Optional[Dict[str, Any]]:
    items = db.query(FieldEquipment).filter(FieldEquipment.is_active == True).all()
    if not items:
        return None

    nearest_item = None
    min_dist = float("inf")

    for eq in items:
        dist = haversine_distance_km(lat, lon, eq.latitude, eq.longitude)
        if dist < min_dist:
            min_dist = dist
            nearest_item = eq

    latest_score = nearest_item.visits[-1].condition_score if nearest_item.visits else None

    return {
        "asset_id": nearest_item.asset_id,
        "name": nearest_item.name,
        "asset_type": nearest_item.asset_type,
        "latitude": nearest_item.latitude,
        "longitude": nearest_item.longitude,
        "distance_km": round(min_dist, 3),
        "condition_score": latest_score,
    }