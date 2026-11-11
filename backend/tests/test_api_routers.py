import os
import sys
import pytest
import importlib
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.db.session import Base, get_db

# Global client placeholder – will be set by fixture
client = None

@pytest.fixture(scope="function", autouse=True)
def setup_testdb():
    """Create a fresh isolated SQLite DB, seed data, and provide a TestClient.
    Teardown disposes the engine and removes the DB file.
    """
    # Path for isolated test DB (separate from production)
    TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "nexareach_test_isolated.db"))
    # Ensure a clean start – delete existing file if present
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

    # Create engine and sessionmaker bound to test DB
    engine_test = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionTest = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

    # Create tables (including any new columns) in test DB
    Base.metadata.create_all(bind=engine_test)
    # Ensure the `consent` column exists (no‑op if present)
    with engine_test.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE audience_members ADD COLUMN consent BOOLEAN NOT NULL DEFAULT 0"))
        except Exception:
            pass

    # Override FastAPI's get_db dependency to use the test session
    def get_test_db():
        db = SessionTest()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = get_test_db

    # Monkey‑patch SessionLocal used by seed_initial_data and other imports
    db_mod = importlib.import_module("app.db.session")
    db_mod.SessionLocal = SessionTest
    seed_mod = importlib.import_module("app.seed")
    seed_mod.SessionLocal = SessionTest
    # Seed minimal data required for the tests
    seed_mod.seed_initial_data()

    # Create a TestClient that will use the overridden dependency
    global client
    client = TestClient(app)

    # Yield control to the test functions
    yield

    # Teardown: dispose engine, delete test DB file, and clean overrides
    engine_test.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    app.dependency_overrides.pop(get_db, None)

# ---------------------------------------------------------------------
# 1. AI Generation & History API Tests
# ---------------------------------------------------------------------

def _mock_openai(text):
    """Context managers that fake the OpenAI call (no cost, no key needed)."""
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_completion
    return mock_client_instance


def test_api_ai_generate_without_key_is_an_honest_503():
    """No API key -> clear error. Never made-up text pretending to be AI output."""
    payload = {
        "prompt": "Vaccination drive for infants this Saturday at Community Center",
        "channel": "SMS",
        "tone": "Urgent",
    }
    with patch("app.services.ai_service._api_key", return_value=""):
        response = client.post("/ai/generate", json=payload)
    assert response.status_code == 503, response.text
    assert "not configured" in response.json()["detail"]


def test_api_ai_generate_with_mocked_openai():
    """Mock external OpenAI provider to verify the real-AI code path."""
    text = "CRITICAL: Infant vaccination camp on Saturday. Register now at PHC. Call 1800-000-111."
    with patch("app.core.config.settings.API_KEY", "sk-mock-valid-openai-key-1234567890abcdef"):
        with patch("openai.OpenAI", return_value=_mock_openai(text)):
            payload = {"prompt": "Infant immunization advisory", "channel": "SMS", "tone": "Urgent"}
            response = client.post("/ai/generate", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["provider"].startswith("openai:")
    assert data["is_fallback"] is False
    assert "CRITICAL: Infant vaccination camp" in data["content"]
    assert data["channel"] == "SMS" and data["tone"] == "Urgent"
    assert data["id"] is not None  # saved to history


def test_api_ai_history_retrieval():
    text = "Wash your hands with soap before eating."
    with patch("app.core.config.settings.API_KEY", "sk-mock-valid-openai-key-1234567890abcdef"):
        with patch("openai.OpenAI", return_value=_mock_openai(text)):
            client.post("/ai/generate", json={"prompt": "hand washing awareness", "channel": "SMS"})
    response = client.get("/ai/history?limit=10")
    assert response.status_code == 200, response.text
    history = response.json()
    assert isinstance(history, list)
    assert len(history) > 0
    first = history[0]
    assert first["prompt"] == "hand washing awareness"
    assert first["generated_content"] == text
    assert "created_at" in first


# ---------------------------------------------------------------------
# 2. Translation & Languages API Tests
# ---------------------------------------------------------------------

def test_api_supported_languages():
    response = client.get("/translate/languages")
    assert response.status_code == 200, response.text
    langs = response.json()
    lang_dict = {l["name"]: l for l in langs}
    expected_langs = [
        "Hindi", "Kannada", "Tamil", "Telugu", "Marathi",
        "Bengali", "Gujarati", "Malayalam", "Punjabi", "Urdu",
    ]
    for lang in expected_langs:
        assert lang in lang_dict, f"Missing language {lang}"
    urdu = lang_dict["Urdu"]
    assert urdu["is_rtl"] is True
    assert urdu["direction"] == "rtl"
    assert urdu["native_name"] == "اردو"
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
    # Real provider path (faked in tests): never an "offline demo" result
    assert data["provider"].startswith("openai")
    assert data["is_fallback"] is False
    assert "{{name}}" in data["translated_text"]
    assert "https://nexareach.org" in data["translated_text"]
    assert "1800-000-111" in data["translated_text"]
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
    for lang in ["Hindi", "Telugu", "Urdu", "Marathi"]:
        assert lang in result_map
    assert result_map["Urdu"]["is_rtl"] is True
    assert result_map["Hindi"]["is_rtl"] is False

# Additional tests (personalization, analysis, compliance, review, workflow, etc.) are unchanged and follow after this section.