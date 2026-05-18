"""add refresh_jti to users

Revision ID: c4f7d2a8e1b3
Revises: b3e9f1a2c4d5
Create Date: 2026-05-18 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c4f7d2a8e1b3'
down_revision: Union[str, Sequence[str], None] = '3189b185e75b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add refresh_jti column to users for refresh-token replay detection.

    Each refresh token embeds a jti claim that must match the user's stored
    refresh_jti. On every successful refresh the jti is rotated; presenting a
    stale jti (theft or reuse) is rejected. Nullable: legacy refresh tokens
    issued before this migration carry no jti and are simply ignored — the
    next /auth/login establishes the first jti.
    """
    op.add_column(
        'users',
        sa.Column(
            'refresh_jti',
            sa.String(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'refresh_jti')
