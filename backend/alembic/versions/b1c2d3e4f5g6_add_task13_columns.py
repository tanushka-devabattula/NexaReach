"""add_task13_columns

Revision ID: b1c2d3e4f5g6
Revises: 0e500f4ad1da
Create Date: 2026-11-02 15:22:00.000000
"""

from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5g6"
down_revision = "0e500f4ad1da"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add consent column to audience_members (Boolean, NOT NULL, default FALSE)
    op.add_column(
        "audience_members",
        sa.Column(
            "consent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # 2. Add tracking_id (nullable for now) and provider_message_id to messages
    with op.batch_alter_table("messages") as batch_op:
        batch_op.add_column(
            sa.Column("tracking_id", sa.String(length=36), nullable=True)
        )
        batch_op.add_column(
            sa.Column("provider_message_id", sa.String(), nullable=True)
        )

    # 3. Add provider_message_id to delivery_logs
    op.add_column(
        "delivery_logs",
        sa.Column("provider_message_id", sa.String(), nullable=True),
    )

    # 4. Backfill a distinct UUID for each existing message that lacks a tracking_id
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id FROM messages WHERE tracking_id IS NULL"))
    for row in result:
        uid = str(uuid.uuid4())
        conn.execute(
            sa.text("UPDATE messages SET tracking_id = :uid WHERE id = :mid"),
            {"uid": uid, "mid": row.id},
        )

    # 5. Make tracking_id NOT NULL and add a unique constraint (SQLite compatible via batch mode)
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column("tracking_id", nullable=False)
        batch_op.create_unique_constraint("uq_messages_tracking_id", ["tracking_id"])


def downgrade() -> None:
    # Remove unique constraint and set tracking_id back to nullable before dropping
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_constraint("uq_messages_tracking_id", type_="unique")
        batch_op.alter_column("tracking_id", nullable=True)
        batch_op.drop_column("provider_message_id")
        batch_op.drop_column("tracking_id")

    # Remove provider_message_id from delivery_logs
    op.drop_column("delivery_logs", "provider_message_id")

    # Remove consent column from audience_members
    op.drop_column("audience_members", "consent")
