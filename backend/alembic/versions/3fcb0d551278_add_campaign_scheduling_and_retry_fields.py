"""add campaign scheduling and retry fields"""

from alembic import op
import sqlalchemy as sa

revision = "3fcb0d551278"
down_revision = "c4a1d2e3f405"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "campaigns",
        sa.Column("scheduled_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "schedule_status",
            sa.String(30),
            nullable=False,
            server_default="not_scheduled"
        )
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0"
        )
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "max_retries",
            sa.Integer(),
            nullable=False,
            server_default="3"
        )
    )
    op.add_column(
        "campaigns",
        sa.Column("next_retry_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "campaigns",
        sa.Column("last_run_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "campaigns",
        sa.Column("last_error", sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_column("campaigns", "last_error")
    op.drop_column("campaigns", "last_run_at")
    op.drop_column("campaigns", "next_retry_at")
    op.drop_column("campaigns", "max_retries")
    op.drop_column("campaigns", "retry_count")
    op.drop_column("campaigns", "schedule_status")
    op.drop_column("campaigns", "scheduled_at")