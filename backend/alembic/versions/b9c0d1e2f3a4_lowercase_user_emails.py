"""lowercase user emails

Revision ID: b9c0d1e2f3a4
Revises: a7b8c9d0e1f2
Create Date: 2026-10-07 00:00:00.000000

Hand-written per context/foundation/lessons.md — do not trust autogenerate.
Normalizes existing user emails to lowercase so lookups (which are now
case-insensitive by normalization) match rows created before the change.
No de-duplication is attempted: the unique constraint fails loudly on the
(unlikely) collision rather than silently merging accounts.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema/data."""
    op.execute("UPDATE users SET email = lower(email)")


def downgrade() -> None:
    """Downgrade schema/data.

    No-op: the original casing of each email is not recoverable.
    """
