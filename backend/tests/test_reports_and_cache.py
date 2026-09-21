import pytest
from datetime import date
from app.models import FieldEquipment, SurveyVisit

def test_summary_report_and_caching(client, surveyor_token, db_session):
    eq = FieldEquipment(
        asset_id="PL-7701",
        name="Test Pole 7701",
        asset_type="pole",
        latitude=20.290,
        longitude=85.820,
        status="active"
    )
    db_session.add(eq)
    db_session.flush()

    visit = SurveyVisit(
        equipment_id="PL-7701",
        surveyed_on=date(2026, 9, 1),
        surveyor="Ramesh Sharma",
        condition_score=8,
        condition_band="GOOD"
    )
    db_session.add(visit)
    db_session.commit()

    headers = {"Authorization": f"Bearer {surveyor_token}"}
    res1 = client.get("/api/v1/reports/summary", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total_assets"] >= 1
    assert "geographic_extent" in data1

    res2 = client.get("/api/v1/reports/summary", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["total_assets"] == data1["total_assets"]

def test_map_geojson_feed(client, surveyor_token):
    headers = {"Authorization": f"Bearer {surveyor_token}"}
    res = client.get("/api/v1/map/equipment-locations", headers=headers)
    assert res.status_code == 200
    geojson = res.json()
    assert geojson["type"] == "FeatureCollection"
    assert "features" in geojson

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"