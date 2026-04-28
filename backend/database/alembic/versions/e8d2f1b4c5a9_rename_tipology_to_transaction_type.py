"""rename_tipology_to_transaction_type

Revision ID: e8d2f1b4c5a9
Revises: 4423075ffe82
Create Date: 2026-04-28 09:44:00.000000

"""
from typing import Sequence, Optional
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8d2f1b4c5a9'
down_revision: Optional[str] = '4423075ffe82'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # Rename 'tipology' to 'transaction_type' in the 'transactions' table
    op.alter_column('transactions', 'tipology', new_column_name='transaction_type')


def downgrade() -> None:
    # Rename 'transaction_type' back to 'tipology'
    op.alter_column('transactions', 'transaction_type', new_column_name='tipology')
