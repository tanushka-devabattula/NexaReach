import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "nexareach.db")


def test_database_tables_exist():
    """Verify all 15 tables exist after the Milestone 2 Alembic migration."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}

    cursor.execute("PRAGMA table_info(translation_records);")
    cols = {row[1] for row in cursor.fetchall()}
    conn.close()

    expected_tables = {
        # Milestone 1 tables
        "roles",
        "users",
        "audience_members",
        "segments",
        "campaigns",
        "templates",
        "messages",
        "delivery_logs",
        "feedback",
        # Milestone 2 tables
        "translation_records",
        "ai_content_history",
        "content_reviews",
        "compliance_rules",
        "content_variants",
        "campaign_contents",
        # Alembic metadata
        "alembic_version",
    }

    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"
    assert {"campaign_id", "message_id", "status"}.issubset(cols), f"Missing columns in translation_records: {cols}"


def test_alembic_head_version():
    """Verify alembic version table holds the new Milestone 2 migration head."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT version_num FROM alembic_version;")
    version = cursor.fetchone()[0]
    conn.close()

    assert version == "0e500f4ad1da", f"Expected head 0e500f4ad1da, got {version}"


def test_milestone_1_records_preserved():
    """Ensure that Milestone 1 audience, user, segment, and campaign records remain intact."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    counts = {
        table: cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ["users", "roles", "audience_members", "segments", "campaigns", "templates", "messages"]
    }
    conn.close()

    assert counts["users"] >= 4, f"Users were lost: {counts['users']}"
    assert counts["roles"] >= 1, f"Roles were lost: {counts['roles']}"
    assert counts["audience_members"] >= 4, f"Audience members were lost: {counts['audience_members']}"
    assert counts["segments"] >= 4, f"Segments were lost: {counts['segments']}"
    assert counts["campaigns"] >= 2, f"Campaigns were lost: {counts['campaigns']}"
    assert counts["templates"] >= 2, f"Templates were lost: {counts['templates']}"
    assert counts["messages"] >= 1, f"Messages were lost: {counts['messages']}"

