"""link content reviews to campaign content"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("content_reviews") as batch_op:
        batch_op.add_column(
            sa.Column("campaign_content_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_content_reviews_campaign_content_id_campaign_contents",
            "campaign_contents",
            ["campaign_content_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("content_reviews") as batch_op:
        batch_op.drop_constraint(
            "fk_content_reviews_campaign_content_id_campaign_contents",
            type_="foreignkey",
        )
        batch_op.drop_column("campaign_content_id")
