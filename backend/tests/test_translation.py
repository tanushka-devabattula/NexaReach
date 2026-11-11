"""Translation tests. The AI provider is faked, so these check OUR logic:
protection of placeholders, language handling, honest errors, batch, cache."""
import httpx
import openai
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.models import TranslationRecord
from app.schemas.translation import BatchTranslationRequest, TranslationRequest
from app.services import translation_service as ts


@pytest.fixture
def client_and_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app), Session
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


# ---------------------------------------------------------------- languages
def test_all_languages_listed_with_urdu_rtl():
    langs = {l.name: l for l in ts.get_supported_languages()}
    for name in ["Hindi", "Kannada", "Tamil", "Telugu", "Marathi", "Bengali",
                 "Gujarati", "Malayalam", "Punjabi", "Urdu", "English"]:
        assert name in langs
    assert langs["Urdu"].is_rtl and langs["Urdu"].direction == "rtl"
    assert not langs["Hindi"].is_rtl


@pytest.mark.parametrize("value,code", [("Telugu", "te"), ("telugu", "te"), ("te", "te"),
                                        ("Telugu — తెలుగు", "te"), ("  Urdu ", "ur")])
def test_language_resolution(value, code):
    assert ts.resolve_language(value).code == code


def test_unsupported_language_is_an_error_not_a_silent_default():
    with pytest.raises(ValueError):
        ts.resolve_language("Klingon")


# ------------------------------------------------- output depends on the input
def test_prevention_to_telugu_uses_the_users_text(fake_provider):
    res = ts.translate_text(TranslationRequest(text="prevention", target_language="Telugu"))
    assert res.translated_text == "నివారణ"
    assert fake_provider.calls[0][0] == "prevention"  # provider received what the user typed
    assert res.is_fallback is False


def test_different_inputs_give_different_outputs():
    a = ts.translate_text(TranslationRequest(text="prevention", target_language="Hindi"))
    b = ts.translate_text(TranslationRequest(text="Protect your family", target_language="Hindi"))
    assert a.translated_text == "रोकथाम"
    assert "Protect your family" in b.translated_text and a.translated_text != b.translated_text


# ------------------------------------------------------- placeholder safety
def test_placeholders_links_phone_preserved_and_bidi_wrapped_for_urdu():
    text = "URGENT: Dear {{name}}, visit https://nexareach.org or call 1800-000-111."
    res = ts.translate_text(TranslationRequest(text=text, target_language="Urdu"))
    for item in ["{{name}}", "https://nexareach.org", "1800-000-111"]:
        assert item in res.translated_text
        assert f"\u2068{item}\u2069" in res.bidi_safe_text
    assert res.is_rtl and res.direction == "rtl"


def test_no_bidi_markers_for_left_to_right_languages():
    res = ts.translate_text(TranslationRequest(text="Hello {name}, call 1800-000-111.", target_language="Hindi"))
    assert "{name}" in res.translated_text and "1800-000-111" in res.translated_text
    assert res.bidi_safe_text == res.translated_text


def test_provider_that_drops_a_placeholder_is_retried_then_rejected(monkeypatch):
    calls = []

    def bad(protected, source, target):
        calls.append(1)
        return "translated but the token vanished"

    monkeypatch.setattr(ts, "_call_provider", bad)
    with pytest.raises(ts.TranslationProviderError):
        ts.translate_text(TranslationRequest(text="Hi {{name}}", target_language="Hindi"))
    assert len(calls) == 2  # first try + one retry


def test_provider_that_fixes_itself_on_retry_succeeds(monkeypatch):
    answers = iter(["token vanished", "नमस्ते [[#0]]"])
    monkeypatch.setattr(ts, "_call_provider", lambda p, s, t: next(answers))
    res = ts.translate_text(TranslationRequest(text="Hi {{name}}", target_language="Hindi"))
    assert res.translated_text == "नमस्ते {{name}}"


# ---------------------------------------------------- honest failure cases
def test_missing_api_key_gives_clear_error(real_provider, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ts.TranslationProviderError) as exc:
        ts.translate_text(TranslationRequest(text="prevention", target_language="Telugu"))
    assert "API_KEY" in str(exc.value)


def test_rejected_key_is_reported(real_provider, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "sk-test-not-real")
    response = httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"))

    class BoomClient:
        def __init__(self, *a, **k):
            self.chat = self
            self.completions = self

        def create(self, **kwargs):
            raise openai.AuthenticationError("bad key", response=response, body=None)

    monkeypatch.setattr(openai, "OpenAI", BoomClient)
    with pytest.raises(ts.TranslationProviderError) as exc:
        ts.translate_text(TranslationRequest(text="prevention", target_language="Telugu"))
    assert "rejected" in str(exc.value)
    assert "sk-test" not in str(exc.value)  # never leak the key


def test_empty_text_is_rejected():
    with pytest.raises(ValueError):
        ts.translate_text(TranslationRequest(text="   ", target_language="Hindi"))


def test_same_language_returns_text_without_calling_provider(fake_provider):
    res = ts.translate_text(TranslationRequest(text="Hello", target_language="English"))
    assert res.translated_text == "Hello" and fake_provider.calls == []


def test_repeat_translation_uses_cache(fake_provider):
    req = TranslationRequest(text="Stay safe", target_language="Tamil")
    ts.translate_text(req)
    ts.translate_text(req)
    assert len(fake_provider.calls) == 1


# -------------------------------------------------------------------- batch
def test_batch_defaults_to_the_10_indian_languages():
    res = ts.batch_translate(BatchTranslationRequest(text="Public notice: stay safe."))
    assert [r.language for r in res.results] == ts.INDIAN_LANGUAGE_NAMES
    assert len(res.results) == 10 and res.errors == []


def test_batch_reports_partial_failures(monkeypatch):
    def flaky(protected, source, target):
        if target.code == "ta":
            raise ts.TranslationProviderError("Tamil is down")
        return f"<{target.code}> {protected}"

    monkeypatch.setattr(ts, "_call_provider", flaky)
    res = ts.batch_translate(BatchTranslationRequest(text="Hello", target_languages=["Hindi", "Tamil", "Klingon"]))
    assert [r.language for r in res.results] == ["Hindi"]
    assert {e.language for e in res.errors} == {"Tamil", "Klingon"}


# ----------------------------------------------------------------- the API
def test_api_languages(client_and_db):
    client, _ = client_and_db
    r = client.get("/translate/languages")
    assert r.status_code == 200 and len(r.json()) == 11


def test_api_translate_prevention_and_saves_record(client_and_db):
    client, Session = client_and_db
    r = client.post("/translate", json={"text": "prevention", "target_language": "Telugu"})
    assert r.status_code == 200, r.text
    assert r.json()["translated_text"] == "నివారణ"
    db = Session()
    try:
        rec = db.query(TranslationRecord).one()
        assert rec.translated_text == "నివారణ" and rec.is_fallback is False
    finally:
        db.close()


def test_api_missing_key_returns_503_with_reason_not_fake_text(client_and_db, real_provider, monkeypatch):
    client, _ = client_and_db
    monkeypatch.setattr(settings, "API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client.post("/translate", json={"text": "prevention", "target_language": "Telugu"})
    assert r.status_code == 503
    assert "API_KEY" in r.json()["detail"]
    assert "translated_text" not in r.json()


def test_api_unsupported_language_is_400(client_and_db):
    client, _ = client_and_db
    r = client.post("/translate", json={"text": "hello", "target_language": "Klingon"})
    assert r.status_code == 400 and "Unsupported" in r.json()["detail"]


def test_api_empty_text_is_rejected(client_and_db):
    client, _ = client_and_db
    assert client.post("/translate", json={"text": "", "target_language": "Hindi"}).status_code == 422
    assert client.post("/translate", json={"text": "   ", "target_language": "Hindi"}).status_code == 400


def test_api_batch_and_all_fail_case(client_and_db, real_provider, monkeypatch):
    client, _ = client_and_db
    monkeypatch.setattr(settings, "API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client.post("/translate/batch", json={"text": "Hello", "target_languages": ["Hindi", "Urdu"]})
    assert r.status_code == 503 and "API_KEY" in r.json()["detail"]
