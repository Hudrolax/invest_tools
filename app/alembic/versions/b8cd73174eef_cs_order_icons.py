"""cs_order_icons

Revision ID: b8cd73174eef
Revises: 606b31db9652
Create Date: 2024-11-06 14:39:13.365532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8cd73174eef'
down_revision: Union[str, None] = '606b31db9652'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('chart_settings', sa.Column('show_order_icons', sa.BOOLEAN(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('chart_settings', 'show_order_icons')
    # ### end Alembic commands ###