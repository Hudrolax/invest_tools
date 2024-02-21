"""color

Revision ID: 9c2c2eb5c185
Revises: 8d369b0af14a
Create Date: 2024-02-21 19:19:29.949469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c2c2eb5c185'
down_revision: Union[str, None] = '8d369b0af14a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем новые столбцы с дефолтными значениями
    op.add_column('wallets', sa.Column('color', sa.String(),
                  server_default='#f9a60a', nullable=True))
    op.add_column('wallets', sa.Column('in_balance', sa.BOOLEAN(),
                  server_default='true', nullable=False))

    # Обновляем существующие записи со значениями по умолчанию
    op.execute('UPDATE wallets SET color = \'#f9a60a\' WHERE color IS NULL;')
    op.execute('UPDATE wallets SET in_balance = true WHERE in_balance IS NULL;')


def downgrade() -> None:
    op.drop_column('wallets', 'in_balance')
    op.drop_column('wallets', 'color')
