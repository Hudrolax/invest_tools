"""checklist

Revision ID: 8d369b0af14a
Revises: cd39becf60bc
Create Date: 2024-01-24 18:21:06.511247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d369b0af14a'
down_revision: Union[str, None] = 'cd39becf60bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('checklist',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('text', sa.String(), nullable=False),
    sa.Column('checked', sa.BOOLEAN(), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_checklist_id'), 'checklist', ['id'], unique=False)
    op.create_index(op.f('ix_checklist_user_id'), 'checklist', ['user_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_checklist_user_id'), table_name='checklist')
    op.drop_index(op.f('ix_checklist_id'), table_name='checklist')
    op.drop_table('checklist')
    # ### end Alembic commands ###
