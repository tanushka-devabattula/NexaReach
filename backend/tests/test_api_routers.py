import os
import sys
from unittest.mock import MagicMock, patch

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------
# 1. AI Generation & History API Tests
# ---------------------------------------------------------------------
def test_api_ai_generate_offline_fallback():
    payload = {
        "prompt": "Vaccination drive for infants this Saturday at Community Center",
        "channel": "SMS",
        "tone": "Urgent",
        "variations": 2,
    }
    response = client.post("/ai/generate", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()

    assert data["content"] != ""
    assert data["provider"] == "offline-fallback"
    assert data["is_fallback"] is True
    assert data["channel"] == "SMS"
    assert data["tone"] == "Urgent"
    assert len(data["variations"]) >= 1
    # Verify DB write
    assert data["history_id"] is not None


def test_api_ai_history_retrieval():
    response = client.get("/ai/history?limit=10")
    assert response.status_code == 200, response.text
    history = response.json()
    assert isinstance(history, list)
    assert len(history) > 0
    # Verify DB read
    first = history[0]
    assert "prompt" in first
    assert "generated_content" in first
    assert "created_at" in first


def test_api_ai_generate_with_mocked_openai():
    """Mock external OpenAI provider to verify real-AI integration code path."""
    mock_choice = MagicMock()
    mock_choice.message.content = "CRITICAL: Infant vaccination camp on Saturday. Register now at PHC. Call 1800-000-111."

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("app.core.config.settings.API_KEY", "sk-mock-valid-openai-key-1234567890abcdef"):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client_instance = MagicMock()
            mock_client_instance.chat.completions.create.return_value = mock_completion
            mock_openai_cls.return_value = mock_client_instance

            payload = {
                "prompt": "Infant immunization advisory",
                "channel": "SMS",
                "tone": "Urgent",
            }
            response = client.post("/ai/generate", json=payload)
            assert response.status_code == 201, response.text
            data = response.json()

            # Verify mocked AI output and transparency labels
            assert data["provider"] == "openai"
            assert data["is_fallback"] is False
            assert data["model"] == "gpt-3.5-turbo"
            assert "CRITICAL: Infant vaccination camp" in data["content"]
            assert data["history_id"] is not None


# ---------------------------------------------------------------------
# 2. Translation & Languages API Tests
# ---------------------------------------------------------------------
def test_api_supported_languages():
    response = client.get("/translate/languages")
    assert response.status_code == 200, response.text
    langs = response.json()

    lang_dict = {l["name"]: l for l in langs}
    # Verify all 10 Indian languages are present
    expected_langs = [
        "Hindi", "Kannada", "Tamil", "Telugu", "Marathi",
        "Bengali", "Gujarati", "Malayalam", "Punjabi", "Urdu"
    ]
    for lang in expected_langs:
        assert lang in lang_dict, f"Missing language {lang}"

    # Verify Urdu directional metadata
    urdu = lang_dict["Urdu"]
    assert urdu["is_rtl"] is True
    assert urdu["direction"] == "rtl"
    assert urdu["native_name"] == "اردو"

    # Verify Hindi directional metadata
    hindi = lang_dict["Hindi"]
    assert hindi["is_rtl"] is False
    assert hindi["direction"] == "ltr"


def test_api_single_translation_urdu_rtl():
    payload = {
        "text": "URGENT ADVISORY: Dear citizen {{name}}, visit https://nexareach.org or call 1800-000-111.",
        "target_language": "Urdu",
        "source_language": "English",
    }
    response = client.post("/translate", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["language"] == "Urdu"
    assert data["is_rtl"] is True
    assert data["direction"] == "rtl"
    assert data["provider"] == "offline-fallback"
    assert data["is_fallback"] is True

    # Placeholders & numbers preserved
    assert "{{name}}" in data["translated_text"]
    assert "https://nexareach.org" in data["translated_text"]
    assert "1800-000-111" in data["translated_text"]

    # Unicode Bidi isolation markers in bidi_safe_text
    assert "\u2068{{name}}\u2069" in data["bidi_safe_text"]
    assert "\u2068https://nexareach.org\u2069" in data["bidi_safe_text"]
    assert "\u20681800-000-111\u2069" in data["bidi_safe_text"]


def test_api_batch_translation():
    payload = {
        "text": "Public notice: stay safe and protect your family.",
        "target_languages": ["Hindi", "Telugu", "Urdu", "Marathi"],
    }
    response = client.post("/translate/batch", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["source_text"] == payload["text"]
    assert len(data["results"]) == 4
    result_map = {r["language"]: r for r in data["results"]}
    assert "Hindi" in result_map
    assert "Telugu" in result_map
    assert "Urdu" in result_map
    assert "Marathi" in result_map
    assert result_map["Urdu"]["is_rtl"] is True
    assert result_map["Hindi"]["is_rtl"] is False


# ---------------------------------------------------------------------
# 3. Personalization & Segment Variants API Tests
# ---------------------------------------------------------------------
def test_api_personalization_preview():
    payload = {
        "template_text": "Hello {{name}}, your clinic code is {{code|GEN-101}}.",
        "audience_member_id": 1,
        "custom_attributes": {"code": "CLINIC-789"},
    }
    response = client.post("/personalize/preview", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["original_text"] == payload["template_text"]
    assert "CLINIC-789" in data["personalized_text"]
    assert "name" in data["tokens_found"]
    # Verify DB read replaced name with member 1's actual name
    assert not ("{{name}}" in data["personalized_text"])


def test_api_segment_variants():
    payload = {
        "base_text": "Dear {{name}}, please attend the health camp.",
        "segment_id": 1,
        "sample_limit": 3,
    }
    response = client.post("/personalize/variants", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["segment_id"] == 1
    assert data["total_matched_members"] > 0
    assert len(data["sample_variants"]) > 0
    first = data["sample_variants"][0]
    assert "full_name" in first
    assert "preferred_language" in first
    assert not ("{{name}}" in first["personalized_content"])


def test_api_segment_variants_not_found():
    payload = {
        "base_text": "Hello {{name}}",
        "segment_id": 99999,
    }
    response = client.post("/personalize/variants", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------
# 4. Tone & Readability Analysis API Tests
# ---------------------------------------------------------------------
def test_api_tone_and_readability_analysis():
    payload = {
        "content": "CRITICAL NOTICE: Cyclone alert for coastal areas. Move to designated storm shelters immediately. Call 1800-000-111.",
        "channel": "SMS",
        "target_tone": "Urgent",
    }
    response = client.post("/analysis/tone-readability", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # Readability
    readability = data["readability"]
    assert readability["character_count"] <= 160
    assert readability["flesch_reading_ease"] > 0
    assert readability["public_clarity_score"] > 0

    # Tone
    tone = data["tone"]
    assert tone["primary_tone"] == "Urgent"
    assert "Urgent" in tone["sentiment"]
    assert isinstance(data["recommendations"], list)


# ---------------------------------------------------------------------
# 5. Compliance & Review Workflow API Tests
# ---------------------------------------------------------------------
def test_api_compliance_check_compliant():
    payload = {
        "content": "Public Advisory: Dengue prevention fogging today. Helpline: 1800-000-111. Reply STOP to opt out.",
        "channel": "SMS",
    }
    response = client.post("/review/compliance-check", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["passed"] is True
    assert data["score"] >= 80
    assert data["contains_opt_out"] is True


def test_api_compliance_check_prohibited_terms():
    payload = {
        "content": "Special offer! Get 100% cure and win cash prize today! " * 3,
        "channel": "SMS",
    }
    response = client.post("/review/compliance-check", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["passed"] is False
    assert any("prohibited" in i["message"].lower() for i in data["issues"])


def test_api_review_lifecycle_submit_and_decide():
    # Submit review
    submit_payload = {
        "campaign_id": 1,
        "content": "Health Advisory: Free health camp this Sunday. Helpline: 1800-000-111.",
        "channel": "SMS",
        "language": "English",
        "reviewer_notes": "Submitted for approval",
    }
    sub_res = client.post("/review/submit", json=submit_payload)
    assert sub_res.status_code == 201, sub_res.text
    review = sub_res.json()
    assert review["id"] is not None
    assert review["status"] == "pending_review"
    assert review["compliance_score"] is not None
    review_id = review["id"]

    # Verify DB read via get by ID
    get_res = client.get(f"/review/{review_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == review_id

    # Verify DB read via list
    list_res = client.get("/review/list?status_filter=pending_review")
    assert list_res.status_code == 200
    reviews = list_res.json()
    assert any(r["id"] == review_id for r in reviews)

    # Decide review -> approve
    decision_payload = {
        "decision": "approved",
        "reviewer_notes": "Verified and approved by Public Health Officer.",
    }
    dec_res = client.post(f"/review/{review_id}/decision", json=decision_payload)
    assert dec_res.status_code == 200, dec_res.text
    updated = dec_res.json()
    assert updated["status"] == "approved"
    assert updated["reviewed_at"] is not None
    assert "Health Officer" in updated["reviewer_notes"]


# ---------------------------------------------------------------------
# 6. Integrated Campaign Content Workflow API Tests
# ---------------------------------------------------------------------
def test_api_integrated_workflow_run():
    payload = {
        "prompt": "Severe water contamination warning in Sector 9. Boil drinking water.",
        "channel": "SMS",
        "tone": "Urgent",
        "target_languages": ["Hindi", "Telugu", "Urdu"],
        "segment_id": 1,
        "campaign_id": 1,
        "auto_submit_for_review": True,
        "reviewer_notes": "Urgent broadcast workflow execution",
    }
    response = client.post("/workflow/run", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "completed"

    # 1. Generated Content
    assert data["generated_content"]["content"] != ""
    assert data["generated_content"]["is_fallback"] is True
    assert data["generated_content"]["provider"] == "offline-fallback"

    # 2. Translations
    translations = data["translations"]["results"]
    assert len(translations) == 3
    trans_map = {t["language"]: t for t in translations}
    assert "Urdu" in trans_map
    assert trans_map["Urdu"]["is_rtl"] is True
    assert trans_map["Urdu"]["direction"] == "rtl"

    # 3. Personalization
    assert data["personalization"] is not None
    assert len(data["personalization"]["sample_variants"]) > 0

    # 4. Analysis
    assert data["analysis"]["tone"]["primary_tone"] == "Urgent"

    # 5. Compliance
    assert data["compliance"]["score"] is not None

    # 6. Review
    assert data["review"] is not None
    assert data["review"]["status"] == "pending_review"
    assert data["review"]["id"] is not None


# ---------------------------------------------------------------------
# 7. Milestone 1 Regression Verification
# ---------------------------------------------------------------------
def test_milestone_1_routes_intact():
    # Health check
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "ok"

    # Audience
    aud_res = client.get("/audience")
    assert aud_res.status_code == 200
    assert isinstance(aud_res.json(), list)
    assert len(aud_res.json()) >= 4

    # Campaigns
    camp_res = client.get("/campaigns")
    assert camp_res.status_code == 200
    assert isinstance(camp_res.json(), list)
    assert len(camp_res.json()) >= 2

    # Templates
    tmpl_res = client.get("/templates")
    assert tmpl_res.status_code == 200
    assert isinstance(tmpl_res.json(), list)
    assert len(tmpl_res.json()) >= 2

    # Segments
    seg_res = client.get("/segments")
    assert seg_res.status_code == 200
    assert isinstance(seg_res.json(), list)
    assert len(seg_res.json()) >= 4

    # Messages
    msg_res = client.get("/messages")
    assert msg_res.status_code == 200
    assert isinstance(msg_res.json(), list)
    assert len(msg_res.json()) >= 1


# ---------------------------------------------------------------------
# 8. Priority 1 Correctness Fixes: Compliance Blocking, Tone Improvement, Provider Retry
# ---------------------------------------------------------------------
def test_api_approval_blocked_on_critical_issues():
    """Verify approval is strictly blocked (HTTP 400) if content has critical compliance issues."""
    bad_payload = {
        "campaign_id": 1,
        "content": "Special offer! 100% cure guaranteed and win cash prizes! " * 3,
        "channel": "SMS",
        "reviewer_notes": "Attempting approval on non-compliant content",
    }
    sub_res = client.post("/review/submit", json=bad_payload)
    assert sub_res.status_code == 201, sub_res.text
    review_id = sub_res.json()["id"]

    # Attempt to approve -> MUST be blocked with HTTP 400
    dec_res = client.post(
        f"/review/{review_id}/decision",
        json={"decision": "approved", "reviewer_notes": "Trying to approve critical error"},
    )
    assert dec_res.status_code == 400, f"Expected 400 blocked, got {dec_res.status_code}"
    assert "approval blocked" in dec_res.json()["detail"].lower()

    # Rejection should still succeed
    rej_res = client.post(
        f"/review/{review_id}/decision",
        json={"decision": "rejected", "reviewer_notes": "Properly rejected due to critical claims"},
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "rejected"


def test_api_approval_succeeds_on_valid_content():
    """Verify compliant content with score >= 60 and no critical errors can be approved."""
    good_payload = {
        "campaign_id": 1,
        "content": "Health Advisory: Dengue prevention camp at Primary Health Center. Helpline: 1800-000-111. Reply STOP to opt out.",
        "channel": "SMS",
        "reviewer_notes": "Valid broadcast content",
    }
    sub_res = client.post("/review/submit", json=good_payload)
    assert sub_res.status_code == 201, sub_res.text
    review_id = sub_res.json()["id"]

    dec_res = client.post(
        f"/review/{review_id}/decision",
        json={"decision": "approved", "reviewer_notes": "Approved by Health Director"},
    )
    assert dec_res.status_code == 200, dec_res.text
    assert dec_res.json()["status"] == "approved"
    assert dec_res.json()["reviewed_at"] is not None


def test_api_tone_improvement_offline_fallback_and_sms_limit():
    """Verify POST /ai/improve-tone offline fallback and strict SMS 160-char cap."""
    payload = {
        "content": "Health camp for child vaccination this Sunday at Gandhi Community Hall. Please bring your family and follow safety steps.",
        "target_tone": "Urgent",
        "channel": "SMS",
    }
    response = client.post("/ai/improve-tone", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["provider"] == "offline-fallback"
    assert data["is_fallback"] is True
    assert data["target_tone"] == "Urgent"
    assert data["channel"] == "SMS"
    assert len(data["improved_content"]) <= 160
    assert data["character_count"] <= 160
    assert len(data["suggestions"]) > 0
    assert "1800-000-111" in data["improved_content"]


def test_api_tone_improvement_mocked_openai():
    """Verify POST /ai/improve-tone with mocked external AI provider."""
    mock_choice = MagicMock()
    mock_choice.message.content = "URGENT: Free infant vaccination camp this Sunday. Call 1800-000-111 now."

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("app.core.config.settings.API_KEY", "sk-mock-valid-openai-key-1234567890abcdef"):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client_instance = MagicMock()
            mock_client_instance.chat.completions.create.return_value = mock_completion
            mock_openai_cls.return_value = mock_client_instance

            payload = {
                "content": "Vaccination camp on Sunday.",
                "target_tone": "Urgent",
                "channel": "SMS",
            }
            response = client.post("/ai/improve-tone", json=payload)
            assert response.status_code == 200, response.text
            data = response.json()

            assert data["provider"] == "openai"
            assert data["is_fallback"] is False
            assert "URGENT" in data["improved_content"]
            assert data["character_count"] <= 160


def test_api_ai_provider_error_retry_and_graceful_fallback():
    """Verify finite timeout/retry and graceful offline fallback when provider throws transient errors."""
    with patch("app.core.config.settings.API_KEY", "sk-mock-valid-openai-key-1234567890abcdef"):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client_instance = MagicMock()
            # Simulate network timeout / API error
            mock_client_instance.chat.completions.create.side_effect = Exception("Connection timeout to sk-mock-valid-openai-key")
            mock_openai_cls.return_value = mock_client_instance

            payload = {
                "prompt": "Urgent flood advisory",
                "channel": "SMS",
                "tone": "Urgent",
            }
            # Should NOT crash with 500; should gracefully fallback to offline generator
            response = client.post("/ai/generate", json=payload)
            assert response.status_code == 201, response.text
            data = response.json()
            assert data["provider"] == "offline-fallback"
            assert data["is_fallback"] is True
            assert "1800-000-111" in data["content"]


