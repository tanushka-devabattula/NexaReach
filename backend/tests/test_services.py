from app.db.session import SessionLocal
from app.schemas.ai import AIGenerateRequest
from app.schemas.analysis import ToneAnalysisRequest
from app.schemas.personalization import (
    PersonalizePreviewRequest,
    SegmentVariantRequest,
)
from app.schemas.review import (
    ComplianceCheckRequest,
    ReviewDecisionRequest,
    ReviewSubmitRequest,
)
from app.schemas.translation import (
    BatchTranslationRequest,
    TranslationRequest,
)
from app.services.ai_service import generate_content, list_generation_history
from app.services.analysis_service import analyze_tone_and_readability, calculate_readability
from app.services.compliance_service import check_compliance, decide_review, submit_for_review
from app.services.personalization_service import (
    extract_tokens,
    generate_segment_variants,
    preview_personalization,
    render_personalization,
)
from app.services.translation_service import (
    get_supported_languages,
    translate_text,
    batch_translate,
)


def get_test_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------
# Task 7: AI Content Generation & History Tests
# ---------------------------------------------------------
def test_ai_generation_offline_fallback(db):
    req = AIGenerateRequest(
        prompt="Free flood relief camps in district 4",
        channel="SMS",
        tone="Urgent",
        variations=2,
    )
    res = generate_content(req, db=db)

    assert res.content != ""
    assert res.provider == "offline-fallback"
    assert res.is_fallback is True
    assert len(res.variations) >= 1
    assert "1800-000-111" in res.content

    # Verify history was saved to DB
    history = list_generation_history(db, limit=5)
    assert len(history) > 0
    assert any(h.prompt == "Free flood relief camps in district 4" for h in history)


# ---------------------------------------------------------
# Task 8: Multilingual Translation & Urdu RTL Tests
# ---------------------------------------------------------
def test_all_10_languages_supported():
    langs = get_supported_languages()
    names = {l.name for l in langs}
    expected = {
        "Hindi", "Kannada", "Tamil", "Telugu", "Marathi",
        "Bengali", "Gujarati", "Malayalam", "Punjabi", "Urdu", "English"
    }
    assert expected.issubset(names), f"Missing languages: {expected - names}"


def test_urdu_rtl_and_bidi_isolation(db):
    prompt_text = "URGENT ADVISORY: Dear citizen {{name}}, visit https://nexareach.org or call 1800-000-111."
    req = TranslationRequest(
        text=prompt_text,
        target_language="Urdu",
    )
    res = translate_text(req, db=db)

    # Must be marked as RTL
    assert res.is_rtl is True
    assert res.direction == "rtl"

    # Placeholders must be intact
    assert "{{name}}" in res.translated_text
    assert "https://nexareach.org" in res.translated_text
    assert "1800-000-111" in res.translated_text

    # Bidi-safe isolation markers must wrap LTR tokens
    assert "\u2068{{name}}\u2069" in res.bidi_safe_text
    assert "\u2068https://nexareach.org\u2069" in res.bidi_safe_text
    assert "\u20681800-000-111\u2069" in res.bidi_safe_text


def test_batch_translation_all_10_languages(db):
    req = BatchTranslationRequest(
        text="Public notice: protect your family and stay safe.",
    )
    res = batch_translate(req, db=db)
    assert len(res.results) == 10
    lang_names = [r.language for r in res.results]
    for required in ["Hindi", "Telugu", "Tamil", "Kannada", "Marathi", "Bengali", "Gujarati", "Malayalam", "Punjabi", "Urdu"]:
        assert required in lang_names


# ---------------------------------------------------------
# Task 9: Personalization & Segment Variants Tests
# ---------------------------------------------------------
def test_token_extraction_and_rendering():
    text = "Hello {{name}}, your clinic appointment in {{city|Your Town}} is on {{date}}."
    tokens = extract_tokens(text)
    assert "name" in tokens
    assert "city|Your Town" in tokens
    assert "date" in tokens

    rendered, replaced, missing = render_personalization(text, {"name": "Aarav", "date": "Monday"})
    assert "Hello Aarav" in rendered
    assert "Your Town" in rendered
    assert "Monday" in rendered
    assert len(missing) == 0


def test_segment_variants_generation(db):
    req = SegmentVariantRequest(
        base_text="Dear {{name}}, emergency health update for you.",
        segment_id=1,
        sample_limit=3,
    )
    res = generate_segment_variants(req, db=db)
    assert res.segment_id == 1
    assert len(res.sample_variants) > 0
    # Make sure personalization occurred with real names
    assert not any("{{name}}" in v.personalized_content for v in res.sample_variants)


# ---------------------------------------------------------
# Task 10: Tone & Readability Analysis Tests
# ---------------------------------------------------------
def test_readability_calculation():
    simple_text = "Wash your hands. Drink clean water. Stay safe and healthy."
    metrics = calculate_readability(simple_text)
    assert metrics.flesch_reading_ease >= 70.0
    assert metrics.public_clarity_score >= 80

    complex_text = (
        "Pursuant to statutory administrative regulations and epidemiological mandates, "
        "inter-departmental jurisdictional operatives shall orchestrate institutional protocols "
        "notwithstanding prior informational dissemination parameters."
    )
    complex_metrics = calculate_readability(complex_text)
    assert complex_metrics.flesch_reading_ease < 50.0
    assert complex_metrics.avg_words_per_sentence > 15.0


def test_tone_and_sentiment_analysis():
    req = ToneAnalysisRequest(
        content="CRITICAL ALERT: Severe cyclone warning! Immediate evacuation required. Call 1800-000-111.",
        channel="SMS",
    )
    res = analyze_tone_and_readability(req)
    assert res.tone.primary_tone == "Urgent"
    assert "Urgent" in res.tone.sentiment
    assert res.readability.character_count <= 160


# ---------------------------------------------------------
# Task 11: Compliance & Approval Workflow Tests
# ---------------------------------------------------------
def test_compliance_rules():
    # Compliant message
    ok_req = ComplianceCheckRequest(
        content="Health alert: Free dengue testing camp at Primary Health Center. Helpline: 1800-000-111. Reply STOP to opt out.",
        channel="SMS",
    )
    ok_res = check_compliance(ok_req)
    assert ok_res.passed is True
    assert ok_res.score >= 80

    # Non-compliant message: prohibited claim + SMS overflow
    bad_req = ComplianceCheckRequest(
        content="Special announcement! We offer a 100% cure and miracle medicine for all seasonal illnesses. " * 4,
        channel="SMS",
    )
    bad_res = check_compliance(bad_req)
    assert bad_res.passed is False
    assert any("prohibited" in i.message.lower() for i in bad_res.issues)
    assert any("exceeds" in i.message.lower() for i in bad_res.issues)


def test_approval_workflow_lifecycle(db):
    submit_req = ReviewSubmitRequest(
        campaign_id=1,
        content="Official Advisory: Dengue prevention tips for all residents. Helpline: 1800-000-111.",
        channel="SMS",
        reviewer_notes="Ready for managerial review",
    )
    review = submit_for_review(submit_req, db=db)
    assert review.id is not None
    assert review.status == "pending_review"

    # Decide review
    decision_req = ReviewDecisionRequest(
        decision="approved",
        reviewer_notes="Content verified by Health Officer.",
    )
    updated = decide_review(review.id, decision_req, db=db, reviewer_id=1)
    assert updated.status == "approved"
    assert updated.reviewer_id == 1
    assert updated.reviewed_at is not None

