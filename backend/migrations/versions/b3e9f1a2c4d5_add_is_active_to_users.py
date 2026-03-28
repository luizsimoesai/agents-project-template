"""add is_active to users

Revision ID: b3e9f1a2c4d5
Revises: 95ddd19a5855
Create Date: 2026-03-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b3e9f1a2c4d5'
down_revision: Union[str, Sequence[str], None] = '95ddd19a5855'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active column to users table.

    server_default='true' ensures that:
    1. Existing rows (already in the database) are backfilled with True.
    2. New rows that don't explicitly set is_active also default to True.
    """
    op.add_column(
        'users',
        sa.Column(
            'is_active',
            sa.Boolean(),
            nullable=False,
            server_default='true',
        ),
    )


def downgrade() -> None:
    """Remove the is_active column, reverting to the previous schema."""
    op.drop_column('users', 'is_active')
