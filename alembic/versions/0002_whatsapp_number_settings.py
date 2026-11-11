"""Add configurable WhatsApp Business number."""

import sqlalchemy as sa

from alembic import op

revision = "0002_whatsapp_number_settings"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_numbers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("display_number", sa.String(length=24), nullable=False),
        sa.Column("phone_number_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("whatsapp_numbers")
