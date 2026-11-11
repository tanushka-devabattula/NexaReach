"""Real login / role tests (no fake admin): register, login, /auth/me,
route protection, admin-only user management, deactivation."""
import jwt
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import Base, get_db
from app.main import app
from app.models.models import Role, User
from app.services.auth_service import ensure_default_roles, password_hash

STRONG = "Strong#Pass1"


@pytest.fixture
def ctx(real_auth):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    db = Session()
    ensure_default_roles(db)
    admin_role = db.query(Role).filter_by(name="admin").first()
    db.add(User(full_name="Boss", email="boss@example.com", hashed_password=password_hash.hash(STRONG), role_id=admin_role.id))
    db.commit()
    db.close()
    yield TestClient(app), Session
    app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def register(client, email, role="communication_team", password=STRONG):
    return client.post("/auth/register", json={
        "full_name": "Test Person", "email": email, "password": password, "role": role})


def login(client, email, password=STRONG):
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------ register
def test_register_with_requested_role_and_hashed_password(ctx):
    client, Session = ctx
    r = register(client, "cm@example.com", role="campaign_manager")
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "campaign_manager"
    db = Session()
    stored = db.query(User).filter_by(email="cm@example.com").one()
    assert stored.hashed_password != STRONG and STRONG not in stored.hashed_password
    db.close()


def test_cannot_register_as_admin(ctx):
    client, _ = ctx
    assert register(client, "evil@example.com", role="admin").status_code == 422


@pytest.mark.parametrize("password", ["short1A", "alllowercase1", "ALLUPPERCASE1", "NoNumbersHere"])
def test_weak_passwords_rejected(ctx, password):
    client, _ = ctx
    assert register(client, "weak@example.com", password=password).status_code == 422


def test_duplicate_email_is_409_and_bad_email_is_422(ctx):
    client, _ = ctx
    assert register(client, "dup@example.com").status_code == 201
    assert register(client, "dup@example.com").status_code == 409
    assert register(client, "not-an-email").status_code == 422


# --------------------------------------------------------------- login
def test_login_returns_token_and_role_and_me_works(ctx):
    client, _ = ctx
    register(client, "ct@example.com")
    r = login(client, "ct@example.com")
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "communication_team" and data["access_token"]
    me = client.get("/auth/me", headers=auth(data["access_token"]))
    assert me.status_code == 200 and me.json()["email"] == "ct@example.com"
    assert me.json()["role"] == "communication_team"


def test_wrong_password_and_unknown_user_are_401(ctx):
    client, _ = ctx
    register(client, "ct@example.com")
    assert login(client, "ct@example.com", "Wrong#Pass9").status_code == 401
    assert login(client, "ghost@example.com").status_code == 401


# --------------------------------------------------- route protection
def test_protected_routes_need_a_token(ctx):
    client, _ = ctx
    for method, path in [("get", "/audience"), ("get", "/campaigns"), ("get", "/segments"),
                         ("get", "/templates"), ("get", "/ai/history"), ("get", "/auth/me"),
                         ("get", "/admin/users")]:
        assert getattr(client, method)(path).status_code == 401, path
    assert client.post("/translate", json={"text": "hi", "target_language": "Hindi"}).status_code == 401
    assert client.post("/campaigns/1/send").status_code == 401


def test_public_routes_stay_public(ctx):
    client, _ = ctx
    assert client.get("/health").status_code == 200
    assert client.post("/push/register", json={"token": "x"}).status_code != 401


def test_garbage_and_expired_tokens_are_401(ctx):
    client, _ = ctx
    assert client.get("/auth/me", headers=auth("not-a-real-token")).status_code == 401
    expired = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
                         settings.SECRET_KEY, algorithm=ALGORITHM)
    assert client.get("/auth/me", headers=auth(expired)).status_code == 401


# ------------------------------------------------------- role checks
def test_only_admin_can_use_admin_apis(ctx):
    client, _ = ctx
    register(client, "ct@example.com")
    ct = login(client, "ct@example.com").json()["access_token"]
    assert client.get("/admin/users", headers=auth(ct)).status_code == 403
    boss = login(client, "boss@example.com").json()["access_token"]
    r = client.get("/admin/users", headers=auth(boss))
    assert r.status_code == 200 and len(r.json()) == 2


def test_only_manager_or_admin_can_send_campaigns(ctx):
    client, _ = ctx
    register(client, "ct@example.com")
    register(client, "cm@example.com", role="campaign_manager")
    ct = login(client, "ct@example.com").json()["access_token"]
    cm = login(client, "cm@example.com").json()["access_token"]
    assert client.post("/campaigns/999/send", headers=auth(ct)).status_code == 403
    assert client.post("/campaigns/999/send", headers=auth(cm)).status_code == 404  # allowed, campaign missing


def test_admin_changes_role_and_it_applies_immediately(ctx):
    client, _ = ctx
    r = register(client, "ct@example.com")
    uid = r.json()["id"]
    ct = login(client, "ct@example.com").json()["access_token"]
    boss = login(client, "boss@example.com").json()["access_token"]
    assert client.post("/campaigns/999/send", headers=auth(ct)).status_code == 403
    ch = client.patch(f"/admin/users/{uid}/role", json={"role": "campaign_manager"}, headers=auth(boss))
    assert ch.status_code == 200 and ch.json()["role"] == "campaign_manager"
    assert client.post("/campaigns/999/send", headers=auth(ct)).status_code == 404  # same token, new role
    assert client.patch(f"/admin/users/{uid}/role", json={"role": "wizard"}, headers=auth(boss)).status_code == 400
    assert client.patch("/admin/users/9999/role", json={"role": "user"}, headers=auth(boss)).status_code == 404


def test_deactivated_user_is_locked_out(ctx):
    client, _ = ctx
    uid = register(client, "ct@example.com").json()["id"]
    ct = login(client, "ct@example.com").json()["access_token"]
    boss = login(client, "boss@example.com").json()["access_token"]
    r = client.patch(f"/admin/users/{uid}/active", json={"is_active": False}, headers=auth(boss))
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert client.get("/auth/me", headers=auth(ct)).status_code == 401  # old token stops working
    assert login(client, "ct@example.com").status_code == 403           # cannot log in again
    client.patch(f"/admin/users/{uid}/active", json={"is_active": True}, headers=auth(boss))
    assert login(client, "ct@example.com").status_code == 200


def test_admin_cannot_lock_themselves_out(ctx):
    client, Session = ctx
    boss = login(client, "boss@example.com").json()
    me_id = client.get("/auth/me", headers=auth(boss["access_token"])).json()["id"]
    h = auth(boss["access_token"])
    assert client.patch(f"/admin/users/{me_id}/active", json={"is_active": False}, headers=h).status_code == 400
    assert client.patch(f"/admin/users/{me_id}/role", json={"role": "user"}, headers=h).status_code == 400

# ------------------------------------------------------- review route protection
def test_review_routes_require_authentication(ctx):
    client, _ = ctx

    assert client.get("/review/list").status_code == 401
    assert client.get("/review/999").status_code == 401
    assert client.post("/review/submit", json={
        "content": "Health checkups help people stay healthy.",
        "channel": "SMS",
        "language": "English",
    }).status_code == 401


def test_communication_team_can_submit_view_and_decide_reviews(ctx):
    client, _ = ctx

    registered = register(client, "reviewer@example.com")
    assert registered.status_code == 201, registered.text

    token = login(client, "reviewer@example.com").json()["access_token"]
    headers = auth(token)

    submitted = client.post("/review/submit", headers=headers, json={
        "content": "Health checkups help people stay healthy.",
        "channel": "SMS",
        "language": "English",
    })
    assert submitted.status_code == 201, submitted.text

    review_id = submitted.json()["id"]

    listed = client.get("/review/list", headers=headers)
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == review_id for item in listed.json())

    detail = client.get(f"/review/{review_id}", headers=headers)
    assert detail.status_code == 200, detail.text

    decision = client.post(
        f"/review/{review_id}/decision",
        headers=headers,
        json={"decision": "approved", "reviewer_notes": "Reviewed."},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "approved"
