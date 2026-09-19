from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import FieldEquipment
from app.security import require_surveyor
from app.geo_calculator import build_geojson_feature_collection

router = APIRouter(
    prefix="/api/v1/map",
    tags=["Web Map Feeds"],
    dependencies=[Depends(require_surveyor)]
)

@router.get("/equipment-locations")
def get_equipment_geojson(db: Session = Depends(get_db)):
    equipment_list = db.query(FieldEquipment).filter(FieldEquipment.is_active == True).all()
    return build_geojson_feature_collection(equipment_list)

@router.get("/geojson")
def get_geojson_alias(db: Session = Depends(get_db)):
    return get_equipment_geojson(db=db)