"""add optional template link to campaigns"""

from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "3fcb0d551278"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("campaigns") as batch_op:
        batch_op.add_column(sa.Column("template_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_campaigns_template_id_templates",
            "templates",
            ["template_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("campaigns") as batch_op:
        batch_op.drop_constraint(
            "fk_campaigns_template_id_templates",
            type_="foreignkey",
        )
        batch_op.drop_column("template_id")
