"""add pg_trgm and paragraph index

Revision ID: 468cba96ea4b
Revises: dbf7f136ed15
Create Date: 2026-06-23 03:44:26.835151

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '468cba96ea4b'
down_revision: Union[str, Sequence[str], None] = 'dbf7f136ed15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use execute to run raw SQL
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("""
        CREATE INDEX IF NOT EXISTS search_lines_normalized_text_trgm_idx 
        ON paragraphs 
        USING GIN (normalized_text gin_trgm_ops)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF NOT EXISTS search_lines_normalized_text_trgm_idx")
    op.execute("DROP EXTENSION IF NOT EXISTS pg_trgm")
