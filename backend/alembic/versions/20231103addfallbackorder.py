from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20231103addfallbackorder"
down_revision = "b1c2d3e4f5g6"
branch_labels = None
depends_on = None


def upgrade():
    # Add fallback_order column if it does not already exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("campaigns")]
    if "fallback_order" not in columns:
        op.add_column(
            "campaigns",
            sa.Column("fallback_order", sa.JSON(), nullable=True),
        )


def downgrade():
    # Remove fallback_order column if it exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("campaigns")]
    if "fallback_order" in columns:
        op.drop_column("campaigns", "fallback_order")
