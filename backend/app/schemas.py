from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, ConfigDict

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: str = "surveyor"

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_on: Optional[date] = None
    updated_on: Optional[date] = None

class SurveyVisitBase(BaseModel):
    surveyed_on: date
    surveyor: str
    condition_score: int
    attribute_json: Optional[Dict[str, Any]] = None

class SurveyVisitCreate(SurveyVisitBase):
    pass

class SurveyVisitResponse(SurveyVisitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: str
    condition_band: str
    is_active: bool
    created_by: Optional[int] = None
    created_on: datetime
    updated_by: Optional[int] = None
    updated_on: datetime

class EquipmentBase(BaseModel):
    asset_id: str
    name: str
    asset_type: str
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    status: str
    surveyor: Optional[str] = None
    surveyed_on: Optional[date] = None
    condition_score: Optional[int] = None
    condition_band: Optional[str] = None

class EquipmentCreate(EquipmentBase):
    surveyed_on: date
    surveyor: str
    condition_score: int
    attribute_json: Optional[Dict[str, Any]] = None

class EquipmentReplace(BaseModel):
    name: str
    asset_type: str
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    status: str
    surveyor: Optional[str] = None
    surveyed_on: Optional[date] = None
    condition_score: Optional[int] = None

class EquipmentPatch(BaseModel):
    name: Optional[str] = None
    asset_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_m: Optional[float] = None
    status: Optional[str] = None
    surveyor: Optional[str] = None
    surveyed_on: Optional[date] = None
    condition_score: Optional[int] = None

class EquipmentResponse(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_by: Optional[int] = None
    created_on: datetime
    updated_by: Optional[int] = None
    updated_on: datetime
    visits: List[SurveyVisitResponse] = []

class PaginatedEquipmentResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[EquipmentResponse]

class AssetTypeSummary(BaseModel):
    asset_type: str
    total_surveyed: int
    average_condition_score: float
    worst_condition_asset: Optional[str] = None
    worst_condition_score: Optional[int] = None

class GeographicExtent(BaseModel):
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float

class SummaryReportResponse(BaseModel):
    generated_at: str
    total_assets: int
    total_visits: int
    by_asset_type: List[AssetTypeSummary]
    geographic_extent: Optional[GeographicExtent] = None

class RepairAssetResponse(BaseModel):
    asset_id: str
    name: str
    asset_type: str
    latitude: float
    longitude: float
    status: str
    latest_condition_score: int
    latest_condition_band: str
    latest_surveyed_on: date

class FrequentVisitResponse(BaseModel):
    asset_id: str
    name: str
    asset_type: str
    visit_count: int
    latest_condition_score: Optional[int] = None

class NearestEquipmentResponse(BaseModel):
    asset_id: str
    name: str
    asset_type: str
    latitude: float
    longitude: float
    distance_km: float
    condition_score: Optional[int] = None

class BulkUploadResponse(BaseModel):
    rows_read: int
    rows_accepted: int
    rows_rejected: int
    rejects_file: Optional[str] = None