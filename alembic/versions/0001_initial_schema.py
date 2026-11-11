"""Create conversation, message, and explicit memory tables."""

import sqlalchemy as sa

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sender", sa.String(length=32), nullable=False, unique=True),
        sa.Column("language", sa.String(length=24), nullable=False, server_default="english"),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("handoff_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_messages_conversation_created", "messages", ["conversation_id", "created_at"]
    )
    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("memories")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_table("messages")
    op.drop_table("conversations")
