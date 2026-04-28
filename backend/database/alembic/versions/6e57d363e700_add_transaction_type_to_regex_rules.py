"""add_transaction_type_to_regex_rules

Revision ID: 6e57d363e700
Revises: e8d2f1b4c5a9
Create Date: 2026-04-28 09:49:00.832766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e57d363e700'
down_revision: Union[str, Sequence[str], None] = 'e8d2f1b4c5a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('regex_rules', sa.Column('transaction_type', sa.String(), nullable=True))
    # Initialize with 'Outgoing' for existing rules
    op.execute("UPDATE regex_rules SET transaction_type = 'Outgoing' WHERE transaction_type IS NULL")

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('regex_rules', 'transaction_type')
