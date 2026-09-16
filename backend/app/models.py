from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import relationship
from app.database import Base

IdType = BigInteger().with_variant(Integer, "sqlite")

class User(Base):
    __tablename__ = "users"

    id = Column(IdType, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="surveyor")
    is_active = Column(Boolean, default=True, nullable=False)
    created_on = Column(Date, default=func.current_date())
    updated_on = Column(Date, default=func.current_date(), onupdate=func.current_date())

class FieldEquipment(Base):
    __tablename__ = "field_equipment"

    id = Column(IdType, primary_key=True, index=True, autoincrement=True)
    asset_id = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(120), nullable=False)
    asset_type = Column(String(50), index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation_m = Column(Float, nullable=True)
    status = Column(String(50), index=True, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(IdType, ForeignKey("users.id"), nullable=True)
    created_on = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_by = Column(IdType, ForeignKey("users.id"), nullable=True)
    updated_on = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    visits = relationship("SurveyVisit", back_populates="equipment", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

class SurveyVisit(Base):
    __tablename__ = "survey_visits"

    id = Column(IdType, primary_key=True, index=True, autoincrement=True)
    equipment_id = Column(String(20), ForeignKey("field_equipment.asset_id", ondelete="CASCADE"), index=True, nullable=False)
    surveyed_on = Column(Date, nullable=False)
    surveyor = Column(String(100), index=True, nullable=False)
    condition_score = Column(Integer, nullable=False)
    condition_band = Column(String(20), nullable=False)
    attribute_json = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(IdType, ForeignKey("users.id"), nullable=True)
    created_on = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_by = Column(IdType, ForeignKey("users.id"), nullable=True)
    updated_on = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    equipment = relationship("FieldEquipment", back_populates="visits")
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(IdType, primary_key=True, index=True, autoincrement=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    duration_ms = Column(Float, nullable=False)
    client_ip = Column(String(50), nullable=True)

    created_by = Column(IdType, ForeignKey("users.id"), nullable=True)
    created_on = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)