"""Shared pytest helpers.

Tests must never call the real AI provider (it costs money and needs a key),
so every test gets a fake provider by default. Tests that want the REAL
provider code (to check missing-key / error handling) use `real_provider`.
"""
import atexit
import os
import shutil
import sys
import tempfile

# SAFETY GUARD: point the app at a throw-away database for the whole test run.
# This must happen before any `app` import. It guarantees no test can ever write
# into your real backend/nexareach.db, even if a test forgets to override get_db.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="nexareach_pytest_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TEST_DB_DIR, "pytest.db").replace("\\", "/")
atexit.register(shutil.rmtree, _TEST_DB_DIR, ignore_errors=True)

import pytest

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services import translation_service as ts  # noqa: E402

_REAL_CALL_PROVIDER = ts._call_provider

# A tiny known-answer table so tests can prove the output depends on the input.
KNOWN = {
    ("prevention", "te"): "నివారణ",
    ("prevention", "hi"): "रोकथाम",
    ("water", "te"): "నీరు",
    ("safety", "ta"): "பாதுகாப்பு",
}


class FakeProvider:
    """Stands in for OpenAI. Keeps [[#n]] tokens, like a well-behaved model."""

    def __init__(self):
        self.calls = []

    def __call__(self, protected_text, source, target):
        self.calls.append((protected_text, source.code, target.code))
        known = KNOWN.get((protected_text.strip().lower(), target.code))
        return known if known else f"<{target.code}> {protected_text}"


@pytest.fixture(autouse=True)
def fake_provider(monkeypatch):
    ts.clear_translation_cache()
    provider = FakeProvider()
    monkeypatch.setattr(ts, "_call_provider", provider)
    yield provider
    ts.clear_translation_cache()


@pytest.fixture(autouse=True)
def logged_in_as_admin():
    """Most tests are not about login, so they run as a fake logged-in admin.

    Tests that check real login / permissions use the `real_auth` fixture instead.
    """
    from types import SimpleNamespace

    from app.core.security import get_current_user
    from app.main import app

    fake = SimpleNamespace(
        id=1, full_name="Test Admin", email="admin@test.local",
        is_active=True, role_id=None, role_name="admin",
    )
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: fake
    yield
    if previous is None:
        app.dependency_overrides.pop(get_current_user, None)
    else:
        app.dependency_overrides[get_current_user] = previous


@pytest.fixture
def real_auth():
    """Switch the fake admin OFF so the real token checks run."""
    from app.core.security import get_current_user
    from app.main import app

    app.dependency_overrides.pop(get_current_user, None)
    yield


@pytest.fixture
def real_provider(monkeypatch):
    """Put the real provider function back (it will fail fast without a key)."""
    monkeypatch.setattr(ts, "_call_provider", _REAL_CALL_PROVIDER)
    return _REAL_CALL_PROVIDER



@pytest.fixture
def db(monkeypatch):
    """A throw-away in-memory database filled with the demo seed data.

    Tests that ask for `db` never touch nexareach.db.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app import seed
    from app.db.session import Base
    import app.models  # noqa: F401  (makes sure every table is registered)

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(seed, "SessionLocal", Session)  # seed into the test DB, not the real one
    seed.seed_initial_data()

    session = Session()
    yield session
    session.close()
    engine.dispose()