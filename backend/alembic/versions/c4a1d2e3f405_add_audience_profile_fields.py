"""add audience profile fields (age, gender, city, state, occupation, department, preferred_channel)

Only ADDS nullable columns, so existing audience rows are kept exactly as they are.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c4a1d2e3f405"
down_revision = "20231103addfallbackorder"
branch_labels = None
depends_on = None

NEW_COLUMNS = [
    ("age", sa.Integer()),
    ("gender", sa.String(20)),
    ("city", sa.String(100)),
    ("state", sa.String(100)),
    ("occupation", sa.String(100)),
    ("department", sa.String(150)),
    ("preferred_channel", sa.String(20)),
]


def upgrade():
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("audience_members")}
    for name, col_type in NEW_COLUMNS:
        if name not in existing:
            op.add_column("audience_members", sa.Column(name, col_type, nullable=True))


def downgrade():
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("audience_members")}
    with op.batch_alter_table("audience_members") as batch:
        for name, _ in NEW_COLUMNS:
            if name in existing:
                batch.drop_column(name)
