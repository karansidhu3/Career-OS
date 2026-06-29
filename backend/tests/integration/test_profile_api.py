"""
Integration tests for profile CRUD endpoints (/admin/profile/*).

Covers upsert semantics for PersonalInfo (singleton), sort_order preservation
for ordered resources, and standard CRUD for experience, projects, and skills.
"""
import pytest

pytestmark = pytest.mark.integration

PERSONAL_PAYLOAD = {
    "name": "Test User",
    "email": "test@example.com",
    "phone": "+1 555 000 0000",
    "linkedin": "linkedin.com/in/testuser",
    "github": "github.com/testuser",
    "location": "Vancouver, BC",
    "target_roles": ["SWE", "Backend Engineer"],
    "target_locations": ["Canada", "Remote"],
    "cover_letter_voice": "Direct. Short sentences.",
}


# ── Personal info (singleton upsert) ─────────────────────────────────────────

async def test_upsert_personal_creates_on_first_call(client):
    resp = await client.put("/admin/profile/personal", json=PERSONAL_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"


async def test_upsert_personal_updates_on_second_call(client):
    await client.put("/admin/profile/personal", json=PERSONAL_PAYLOAD)
    updated = {**PERSONAL_PAYLOAD, "name": "Updated Name"}
    resp = await client.put("/admin/profile/personal", json=updated)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


async def test_upsert_personal_does_not_create_duplicate(client):
    await client.put("/admin/profile/personal", json=PERSONAL_PAYLOAD)
    await client.put("/admin/profile/personal", json={**PERSONAL_PAYLOAD, "name": "Second"})

    resp = await client.get("/admin/profile")
    profile = resp.json()
    # personal is a singleton — only one record
    assert profile["personal"]["name"] == "Second"


async def test_get_personal_returns_404_when_absent(client):
    resp = await client.get("/admin/profile/personal")
    assert resp.status_code == 404


# ── Experience ────────────────────────────────────────────────────────────────

EXP_PAYLOAD = {
    "company": "Acme Corp",
    "role": "Software Engineer",
    "start_date": "Jan 2024",
    "end_date": "Aug 2024",
    "location": "Remote",
    "description": "Built things with FastAPI.",
    "sort_order": 0,
}


async def test_create_experience(client):
    resp = await client.post("/admin/profile/experience", json=EXP_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "Software Engineer"
    assert data["company"] == "Acme Corp"


async def test_update_experience(client):
    create_resp = await client.post("/admin/profile/experience", json=EXP_PAYLOAD)
    exp_id = create_resp.json()["id"]

    updated = {**EXP_PAYLOAD, "role": "Senior Engineer"}
    resp = await client.put(f"/admin/profile/experience/{exp_id}", json=updated)
    assert resp.status_code == 200
    assert resp.json()["role"] == "Senior Engineer"


async def test_delete_experience(client):
    create_resp = await client.post("/admin/profile/experience", json=EXP_PAYLOAD)
    exp_id = create_resp.json()["id"]

    resp = await client.delete(f"/admin/profile/experience/{exp_id}")
    assert resp.status_code == 204


async def test_delete_nonexistent_experience_returns_404(client):
    resp = await client.delete("/admin/profile/experience/99999")
    assert resp.status_code == 404


async def test_experience_returned_in_sort_order(client):
    await client.post("/admin/profile/experience", json={**EXP_PAYLOAD, "sort_order": 2, "role": "C"})
    await client.post("/admin/profile/experience", json={**EXP_PAYLOAD, "sort_order": 0, "role": "A"})
    await client.post("/admin/profile/experience", json={**EXP_PAYLOAD, "sort_order": 1, "role": "B"})

    resp = await client.get("/admin/profile/experience")
    roles = [e["role"] for e in resp.json()]
    assert roles == ["A", "B", "C"]


# ── Projects ──────────────────────────────────────────────────────────────────

PROJECT_PAYLOAD = {
    "name": "MarketMind AI",
    "start_date": "Dec 2025",
    "end_date": "Present",
    "github_url": "https://github.com/user/marketmind",
    "description": "Multi-agent investment intelligence platform.",
    "sort_order": 0,
}


async def test_create_project(client):
    resp = await client.post("/admin/profile/projects", json=PROJECT_PAYLOAD)
    assert resp.status_code == 201
    assert resp.json()["name"] == "MarketMind AI"


async def test_update_project(client):
    create_resp = await client.post("/admin/profile/projects", json=PROJECT_PAYLOAD)
    proj_id = create_resp.json()["id"]

    resp = await client.put(f"/admin/profile/projects/{proj_id}", json={**PROJECT_PAYLOAD, "name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


async def test_delete_project(client):
    create_resp = await client.post("/admin/profile/projects", json=PROJECT_PAYLOAD)
    proj_id = create_resp.json()["id"]

    resp = await client.delete(f"/admin/profile/projects/{proj_id}")
    assert resp.status_code == 204


async def test_projects_returned_in_sort_order(client):
    await client.post("/admin/profile/projects", json={**PROJECT_PAYLOAD, "sort_order": 1, "name": "B"})
    await client.post("/admin/profile/projects", json={**PROJECT_PAYLOAD, "sort_order": 0, "name": "A"})

    resp = await client.get("/admin/profile/projects")
    names = [p["name"] for p in resp.json()]
    assert names == ["A", "B"]


# ── Skills ────────────────────────────────────────────────────────────────────

SKILL_PAYLOAD = {
    "category": "Languages",
    "items": ["Python", "TypeScript", "Go"],
    "sort_order": 0,
}


async def test_create_skill_category(client):
    resp = await client.post("/admin/profile/skills", json=SKILL_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "Languages"
    assert "Python" in data["items"]


async def test_update_skill_category(client):
    create_resp = await client.post("/admin/profile/skills", json=SKILL_PAYLOAD)
    skill_id = create_resp.json()["id"]

    resp = await client.put(f"/admin/profile/skills/{skill_id}", json={**SKILL_PAYLOAD, "category": "Tools"})
    assert resp.status_code == 200
    assert resp.json()["category"] == "Tools"


async def test_delete_skill_category(client):
    create_resp = await client.post("/admin/profile/skills", json=SKILL_PAYLOAD)
    skill_id = create_resp.json()["id"]

    resp = await client.delete(f"/admin/profile/skills/{skill_id}")
    assert resp.status_code == 204


# ── GET /admin/profile (full profile) ────────────────────────────────────────

async def test_get_full_profile_shape(client):
    resp = await client.get("/admin/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert "personal" in data
    assert "education" in data
    assert "experience" in data
    assert "projects" in data
    assert "skills" in data
    assert isinstance(data["experience"], list)
    assert isinstance(data["projects"], list)
