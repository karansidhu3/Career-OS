"""
Integration tests for soft-delete + undo on profile sections (Phase 6).

DELETE endpoints set deleted_at rather than removing the row; list/get and
full-profile endpoints filter deleted rows out; a /restore endpoint clears
deleted_at. Covers all four sections: education, experience, projects, skills.
"""
import pytest

pytestmark = pytest.mark.integration

EDU_PAYLOAD = {"school": "State U", "degree": "BSc", "field": "CS", "minor": None, "start_date": "2020", "end_date": "2024"}
EXP_PAYLOAD = {"company": "Acme Corp", "role": "Engineer", "start_date": "2024", "end_date": "Present", "location": "Remote", "description": "", "sort_order": 0}
PROJECT_PAYLOAD = {"name": "MarketMind AI", "start_date": "2025", "end_date": "Present", "github_url": None, "description": "", "sort_order": 0}
SKILL_PAYLOAD = {"category": "Languages", "items": ["Python"], "sort_order": 0}

_SECTIONS = [
    ("education", EDU_PAYLOAD, "school"),
    ("experience", EXP_PAYLOAD, "company"),
    ("projects", PROJECT_PAYLOAD, "name"),
    ("skills", SKILL_PAYLOAD, "category"),
]


@pytest.mark.parametrize("path,payload,key_field", _SECTIONS)
async def test_deleted_item_disappears_from_list(client, path, payload, key_field):
    create_resp = await client.post(f"/admin/profile/{path}", json=payload)
    item_id = create_resp.json()["id"]

    await client.delete(f"/admin/profile/{path}/{item_id}")

    resp = await client.get(f"/admin/profile/{path}")
    assert item_id not in [item["id"] for item in resp.json()]


@pytest.mark.parametrize("path,payload,key_field", _SECTIONS)
async def test_restore_brings_item_back(client, path, payload, key_field):
    create_resp = await client.post(f"/admin/profile/{path}", json=payload)
    item_id = create_resp.json()["id"]

    await client.delete(f"/admin/profile/{path}/{item_id}")
    restore_resp = await client.post(f"/admin/profile/{path}/{item_id}/restore")
    assert restore_resp.status_code == 200
    assert restore_resp.json()[key_field] == payload[key_field]

    list_resp = await client.get(f"/admin/profile/{path}")
    assert item_id in [item["id"] for item in list_resp.json()]


@pytest.mark.parametrize("path,payload,key_field", _SECTIONS)
async def test_restore_nonexistent_or_not_deleted_returns_404(client, path, payload, key_field):
    create_resp = await client.post(f"/admin/profile/{path}", json=payload)
    item_id = create_resp.json()["id"]

    # Never deleted — restore should 404, not silently succeed.
    resp = await client.post(f"/admin/profile/{path}/{item_id}/restore")
    assert resp.status_code == 404


@pytest.mark.parametrize("path,payload,key_field", _SECTIONS)
async def test_cannot_edit_a_deleted_item(client, path, payload, key_field):
    create_resp = await client.post(f"/admin/profile/{path}", json=payload)
    item_id = create_resp.json()["id"]
    await client.delete(f"/admin/profile/{path}/{item_id}")

    resp = await client.put(f"/admin/profile/{path}/{item_id}", json=payload)
    assert resp.status_code == 404


@pytest.mark.parametrize("path,payload,key_field", _SECTIONS)
async def test_double_delete_returns_404(client, path, payload, key_field):
    create_resp = await client.post(f"/admin/profile/{path}", json=payload)
    item_id = create_resp.json()["id"]
    first = await client.delete(f"/admin/profile/{path}/{item_id}")
    assert first.status_code == 204

    second = await client.delete(f"/admin/profile/{path}/{item_id}")
    assert second.status_code == 404


async def test_full_profile_excludes_soft_deleted_items_across_all_sections(client):
    edu = (await client.post("/admin/profile/education", json=EDU_PAYLOAD)).json()
    exp = (await client.post("/admin/profile/experience", json=EXP_PAYLOAD)).json()
    proj = (await client.post("/admin/profile/projects", json=PROJECT_PAYLOAD)).json()
    skill = (await client.post("/admin/profile/skills", json=SKILL_PAYLOAD)).json()

    await client.delete(f"/admin/profile/education/{edu['id']}")
    await client.delete(f"/admin/profile/experience/{exp['id']}")
    await client.delete(f"/admin/profile/projects/{proj['id']}")
    await client.delete(f"/admin/profile/skills/{skill['id']}")

    resp = await client.get("/admin/profile")
    data = resp.json()
    assert data["education"] == []
    assert data["experience"] == []
    assert data["projects"] == []
    assert data["skills"] == []
