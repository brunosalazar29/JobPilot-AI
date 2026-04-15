"""profile detection fields

Revision ID: 0002_profile_detection
Revises: 0001_initial
Create Date: 2026-04-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_profile_detection"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("seniority", sa.String(length=80), nullable=True))
    op.add_column("profiles", sa.Column("target_roles", sa.JSON(), nullable=True))
    op.add_column("profiles", sa.Column("field_sources", sa.JSON(), nullable=True))
    op.add_column("profiles", sa.Column("missing_fields", sa.JSON(), nullable=True))
    op.add_column("profiles", sa.Column("recommendations", sa.JSON(), nullable=True))
    op.add_column("profiles", sa.Column("profile_completeness", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("profiles", "profile_completeness")
    op.drop_column("profiles", "recommendations")
    op.drop_column("profiles", "missing_fields")
    op.drop_column("profiles", "field_sources")
    op.drop_column("profiles", "target_roles")
    op.drop_column("profiles", "seniority")
