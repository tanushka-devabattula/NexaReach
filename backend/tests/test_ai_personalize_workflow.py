"""Tests for AI generate, personalization and the workflow endpoint.

Isolated: in-memory SQLite + fake AI call. Never touches nexareach.db or OpenAI.
(conftest.py already fakes the translation provider.)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models.models import AudienceMember, Campaign, CampaignContent, Segment, Template
from app.services import ai_service


@pytest.fixture
def client_and_db(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    db = Session()
    yield TestClient(app), db
    db.close()
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous
    engine.dispose()


@pytest.fixture
def fake_ai(monkeypatch):
    """Pretend OpenAI answered. The answer depends on the prompt (not hardcoded)."""
    def fake(system_prompt, user_prompt, n):
        return [f"MSG about {user_prompt}"] * n
    monkeypatch.setattr(ai_service, "_call_openai", fake)


# ----------------------------------------------------------------- generate
def test_generate_uses_prompt_and_saves_history(client_and_db, fake_ai):
    client, _ = client_and_db
    res = client.post("/ai/generate", json={"prompt": "polio camp Sunday", "channel": "SMS", "variations": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["content"] == "MSG about polio camp Sunday"
    assert len(body["variations"]) == 2
    assert body["is_fallback"] is False

    history = client.get("/ai/history?limit=5").json()
    assert len(history) == 1
    assert history[0]["generated_content"] == "MSG about polio camp Sunday"


def test_generate_empty_prompt_is_400(client_and_db, fake_ai):
    client, _ = client_and_db
    assert client.post("/ai/generate", json={"prompt": "   "}).status_code == 400


def test_generate_without_key_is_honest_503(client_and_db, monkeypatch):
    client, _ = client_and_db
    monkeypatch.setattr(ai_service, "_api_key", lambda: "")
    res = client.post("/ai/generate", json={"prompt": "dengue"})
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"]
    assert client.get("/ai/history").json() == []  # nothing fake was saved


# ------------------------------------------------------------- personalize
def _member(db, **kw):
    m = AudienceMember(full_name=kw.get("name", "Ravi"), email="ravi@example.com",
                       phone="9999999999", preferred_language=kw.get("lang", "English"), consent=True)
    db.add(m); db.commit(); db.refresh(m)
    return m


def test_preview_fills_real_member_and_reports_missing(client_and_db):
    client, db = client_and_db
    m = _member(db)
    res = client.post("/personalize/preview", json={
        "template_text": "Hello {{name}}, call {phone}. Area: {{city}}",
        "audience_member_id": m.id,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["personalized_text"] == "Hello Ravi, call 9999999999. Area: {{city}}"
    assert body["missing_tokens"] == ["city"]


def test_preview_custom_attribute_and_unknown_member(client_and_db):
    client, db = client_and_db
    ok = client.post("/personalize/preview", json={
        "template_text": "Hi {{name}}", "custom_attributes": {"name": "Sita"}})
    assert ok.json()["personalized_text"] == "Hi Sita"
    missing = client.post("/personalize/preview", json={"template_text": "Hi", "audience_member_id": 999})
    assert missing.status_code == 404


def test_segment_variants_translate_per_language(client_and_db):
    client, db = client_and_db
    _member(db, name="Lakshmi", lang="Telugu")
    _member(db, name="John", lang="English")
    seg = Segment(name="Telugu only", criteria={"preferred_language": "Telugu"})
    db.add(seg); db.commit(); db.refresh(seg)

    res = client.post("/personalize/variants", json={"base_text": "prevention", "segment_id": seg.id})
    assert res.status_code == 200
    body = res.json()
    assert body["total_matched_members"] == 1
    assert body["sample_variants"][0]["personalized_content"] == "నివారణ"
    assert client.post("/personalize/variants", json={"base_text": "x", "segment_id": 404}).status_code == 404


def test_segment_with_unknown_field_matches_nobody(client_and_db):
    client, db = client_and_db
    _member(db)
    seg = Segment(name="Farmers", criteria={"occupation": "farmer"})
    db.add(seg); db.commit(); db.refresh(seg)
    body = client.post("/personalize/variants", json={"base_text": "hi", "segment_id": seg.id}).json()
    assert body["total_matched_members"] == 0


# ---------------------------------------------------------------- workflow
def test_workflow_runs_every_step(client_and_db, fake_ai):
    client, db = client_and_db
    res = client.post("/workflow/run", json={
        "prompt": "water", "channel": "SMS", "tone": "Informative",
        "target_languages": ["Telugu"], "auto_submit_for_review": True})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["generated_content"]["content"] == "MSG about water"
    assert len(body["translations"]["results"]) == 1
    assert body["translations"]["results"][0]["language"] == "Telugu"
    assert "public_clarity_score" in body["analysis"]["readability"]
    assert "score" in body["compliance"]
    assert body["review"]["status"] == "pending_review"
    assert body["personalization"] is None


def test_workflow_without_key_is_503(client_and_db, monkeypatch):
    client, _ = client_and_db
    monkeypatch.setattr(ai_service, "_api_key", lambda: "")
    res = client.post("/workflow/run", json={"prompt": "dengue", "target_languages": ["Hindi"]})
    assert res.status_code == 503

# ---------------------------------------- M1 campaign CRUD and template linking

def test_campaign_create_with_template_creates_draft_content(client_and_db):
    client, db = client_and_db
    template = Template(
        name="Campaign integration template",
        channel="SMS",
        language="English",
        body="Please attend your regular health checkup.",
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    response = client.post("/campaigns", json={
        "name": "Template Integration Campaign",
        "objective": "Verify template-to-campaign integration",
        "template_id": template.id,
    })

    assert response.status_code == 201, response.text
    campaign_data = response.json()
    assert campaign_data["template_id"] == template.id

    content = db.query(CampaignContent).filter_by(
        campaign_id=campaign_data["id"]
    ).one()

    assert content.content == template.body
    assert content.language == template.language
    assert content.channel == "SMS"
    assert content.status == "draft"


def test_campaign_patch_updates_campaign(client_and_db):
    client, db = client_and_db
    campaign = Campaign(
        name="Original campaign",
        objective="Original objective",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    response = client.patch(
        f"/campaigns/{campaign.id}",
        json={"name": "Updated campaign name"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated campaign name"


def test_campaign_delete_is_blocked_when_content_exists(client_and_db):
    client, db = client_and_db
    campaign = Campaign(name="Protected campaign")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    db.add(CampaignContent(
        campaign_id=campaign.id,
        content="A retained campaign draft.",
        language="English",
        channel="SMS",
        status="draft",
    ))
    db.commit()

    response = client.delete(f"/campaigns/{campaign.id}")

    assert response.status_code == 409, response.text
    assert db.query(Campaign).filter_by(id=campaign.id).first() is not None


def test_campaign_delete_allows_campaign_without_dependencies(client_and_db):
    client, db = client_and_db
    campaign = Campaign(name="Unused disposable campaign")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    campaign_id = campaign.id

    response = client.delete(f"/campaigns/{campaign_id}")

    assert response.status_code == 200, response.text
    assert db.query(Campaign).filter_by(id=campaign_id).first() is None


# --------------------------------------------- M2 multilingual review workflow

def test_workflow_links_each_successful_language_to_campaign_review(
    client_and_db, fake_ai
):
    client, db = client_and_db
    campaign = Campaign(
        name="Multilingual workflow integration campaign",
        objective="Verify English and Telugu review records",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    response = client.post("/workflow/run", json={
        "prompt": "water",
        "channel": "SMS",
        "tone": "Informative",
        "target_languages": ["Telugu"],
        "campaign_id": campaign.id,
        "auto_submit_for_review": True,
    })

    assert response.status_code == 200, response.text
    result = response.json()

    assert result["review"]["status"] == "pending_review"
    assert result["review"]["campaign_id"] == campaign.id
    assert result["review"]["campaign_content_id"] is not None

    translation_reviews = result["translation_reviews"]
    assert len(translation_reviews) == 1
    assert translation_reviews[0]["language"] == "Telugu"
    assert translation_reviews[0]["status"] == "pending_review"
    assert translation_reviews[0]["campaign_id"] == campaign.id
    assert translation_reviews[0]["campaign_content_id"] is not None

    contents = (
        db.query(CampaignContent)
        .filter_by(campaign_id=campaign.id)
        .order_by(CampaignContent.id)
        .all()
    )

    assert len(contents) == 2
    assert {item.language for item in contents} == {"English", "Telugu"}
    assert all(item.status == "in_review" for item in contents)

    assert {
        result["review"]["campaign_content_id"],
        translation_reviews[0]["campaign_content_id"],
    } == {item.id for item in contents}


# ------------------------------------------- M1 segment and template API tests

def test_segment_preview_uses_combined_targeting_rules(client_and_db):
    client, db = client_and_db

    db.add_all([
        AudienceMember(
            full_name="Eligible Member",
            email="eligible@example.test",
            phone="9999999999",
            preferred_language="Telugu",
            consent=True,
            age=25,
            gender="Female",
        ),
        AudienceMember(
            full_name="Ineligible Member",
            email="other@example.test",
            phone="8888888888",
            preferred_language="Telugu",
            consent=False,
            age=42,
            gender="Female",
        ),
    ])
    db.commit()

    created = client.post("/segments", json={
        "name": "Combined targeting test",
        "criteria": {
            "language": "Telugu",
            "min_age": 18,
            "max_age": 35,
            "gender": "Female",
            "consent": True,
        },
    })
    assert created.status_code == 201, created.text

    result = client.get(
        f"/segments/{created.json()['id']}/preview"
    )
    assert result.status_code == 200, result.text

    preview = result.json()
    assert preview["total_matched_members"] == 1
    assert preview["consented_members"] == 1
    assert preview["members_with_phone"] == 1
    assert preview["members_with_email"] == 1


def test_segment_patch_and_delete_endpoints(client_and_db):
    client, _ = client_and_db

    created = client.post("/segments", json={
        "name": "Disposable segment",
        "description": "Original",
        "criteria": {"language": "Hindi"},
    })
    assert created.status_code == 201, created.text
    segment_id = created.json()["id"]

    updated = client.patch(
        f"/segments/{segment_id}",
        json={
            "description": "Updated description",
            "criteria": {"language": "Telugu"},
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["description"] == "Updated description"
    assert updated.json()["criteria"] == {"language": "Telugu"}

    deleted = client.delete(f"/segments/{segment_id}")
    assert deleted.status_code == 200, deleted.text
    assert client.get(f"/segments/{segment_id}").status_code == 404


def test_segment_delete_is_blocked_when_campaign_uses_it(client_and_db):
    client, db = client_and_db

    segment = Segment(name="Protected segment", criteria={})
    db.add(segment)
    db.commit()
    db.refresh(segment)

    campaign = Campaign(
        name="Segment reference test",
        segment_id=segment.id,
    )
    db.add(campaign)
    db.commit()

    response = client.delete(f"/segments/{segment.id}")
    assert response.status_code == 409, response.text
    assert db.query(Segment).filter_by(id=segment.id).first() is not None


def test_template_create_patch_and_delete_endpoints(client_and_db):
    client, _ = client_and_db

    created = client.post("/templates", json={
        "name": "CRUD test template",
        "channel": "SMS",
        "language": "English",
        "body": "Original template message.",
    })
    assert created.status_code == 201, created.text
    template_id = created.json()["id"]

    updated = client.patch(
        f"/templates/{template_id}",
        json={
            "name": "Updated CRUD test template",
            "body": "Updated template message.",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Updated CRUD test template"
    assert updated.json()["body"] == "Updated template message."

    deleted = client.delete(f"/templates/{template_id}")
    assert deleted.status_code == 200, deleted.text
    assert client.get(f"/templates/{template_id}").status_code == 404


def test_template_delete_is_blocked_when_campaign_uses_it(client_and_db):
    client, db = client_and_db

    template = Template(
        name="Protected template",
        channel="SMS",
        language="English",
        body="Retained template content.",
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    campaign = Campaign(
        name="Template reference test",
        template_id=template.id,
    )
    db.add(campaign)
    db.commit()

    response = client.delete(f"/templates/{template.id}")
    assert response.status_code == 409, response.text
    assert db.query(Template).filter_by(id=template.id).first() is not None
