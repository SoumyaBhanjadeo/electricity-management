import pytest

def test_unauthenticated_request_rejected(client):
    res = client.get("/api/v1/records")
    assert res.status_code == 401

def test_surveyor_cannot_delete_record(client, surveyor_token):
    headers = {"Authorization": f"Bearer {surveyor_token}"}
    del_res = client.delete("/api/v1/records/PL-0101", headers=headers)
    assert del_res.status_code == 403
    assert "Access forbidden" in del_res.json()["detail"]

def test_surveyor_cannot_create_user(client, surveyor_token):
    headers = {"Authorization": f"Bearer {surveyor_token}"}
    payload = {
        "email": "newuser@gmail.com",
        "username": "newuser",
        "password": "Password123",
        "role": "surveyor"
    }
    res = client.post("/api/v1/auth/users", json=payload, headers=headers)
    assert res.status_code == 403

def test_admin_can_create_user(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "email": "anil@gmail.com",
        "username": "anil",
        "password": "Password123",
        "role": "surveyor"
    }
    res = client.post("/api/v1/auth/users", json=payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["username"] == "anil"