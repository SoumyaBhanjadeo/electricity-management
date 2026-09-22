import pytest
from app.models import FieldEquipment, SurveyVisit

def create_sample_equipment(client, token, asset_id="TR-9901"):
    payload = {
        "asset_id": asset_id,
        "name": "Test Substation Transformer",
        "asset_type": "transformer",
        "latitude": 20.298,
        "longitude": 85.831,
        "elevation_m": 48.0,
        "status": "active",
        "surveyed_on": "2026-09-01",
        "surveyor": "Ramesh Sharma",
        "condition_score": 9,
        "attribute_json": {"rating_kva": 500}
    }
    headers = {"Authorization": f"Bearer {token}"}
    return client.post("/api/v1/records", json=payload, headers=headers)

def test_create_and_fetch_record(client, surveyor_token):
    res = create_sample_equipment(client, surveyor_token, "TR-9901")
    assert res.status_code == 201
    assert res.json()["asset_id"] == "TR-9901"

    headers = {"Authorization": f"Bearer {surveyor_token}"}
    fetch_res = client.get("/api/v1/records/TR-9901", headers=headers)
    assert fetch_res.status_code == 200
    assert fetch_res.json()["name"] == "Test Substation Transformer"

def test_list_records_pagination_and_filter(client, surveyor_token):
    create_sample_equipment(client, surveyor_token, "TR-9902")
    headers = {"Authorization": f"Bearer {surveyor_token}"}
    res = client.get("/api/v1/records?limit=10&offset=0", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data

def test_replace_record_put(client, surveyor_token):
    create_sample_equipment(client, surveyor_token, "TR-9903")
    headers = {"Authorization": f"Bearer {surveyor_token}"}
    replace_payload = {
        "name": "Updated Substation Transformer Full Replace",
        "asset_type": "transformer",
        "latitude": 20.299,
        "longitude": 85.832,
        "elevation_m": 50.0,
        "status": "active"
    }
    res = client.put("/api/v1/records/TR-9903", json=replace_payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Substation Transformer Full Replace"

def test_patch_record(client, surveyor_token):
    create_sample_equipment(client, surveyor_token, "TR-9904")
    headers = {"Authorization": f"Bearer {surveyor_token}"}
    patch_payload = {"name": "Patched Transformer Name Only"}
    res = client.patch("/api/v1/records/TR-9904", json=patch_payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Patched Transformer Name Only"
    assert res.json()["asset_type"] == "transformer"

def test_delete_record_cascade(client, admin_token, surveyor_token, db_session):
    create_sample_equipment(client, surveyor_token, "TR-9905")
    headers = {"Authorization": f"Bearer {admin_token}"}
    del_res = client.delete("/api/v1/records/TR-9905", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
    assert "TR-9905" in del_res.json()["message"]

    get_res = client.get("/api/v1/records/TR-9905", headers=headers)
    assert get_res.status_code == 404

    orphaned_visits = db_session.query(SurveyVisit).filter(SurveyVisit.equipment_id == "TR-9905").all()
    assert len(orphaned_visits) == 0