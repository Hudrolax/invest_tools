"""wallet

Revision ID: 817b8a315443
Revises: b69f743e110e
Create Date: 2023-12-26 18:02:35.003519

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '817b8a315443'
down_revision: Union[str, None] = 'b69f743e110e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('currencies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_currencies_id'), 'currencies', ['id'], unique=False)
    op.create_table('exin_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('income', sa.BOOLEAN(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'income', name='_exin_item_name_income_uc')
    )
    op.create_index(op.f('ix_exin_items_id'), 'exin_items', ['id'], unique=False)
    op.create_table('user_exin_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('exin_item_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['exin_item_id'], ['exin_items.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'exin_item_id', name='_user_exin_items_user_id_exin_item_id_uc')
    )
    op.create_index(op.f('ix_user_exin_items_id'), 'user_exin_items', ['id'], unique=False)
    op.create_table('wallets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('currency_id', sa.Integer(), nullable=False),
    sa.Column('balance', sa.DECIMAL(precision=20, scale=8), nullable=False),
    sa.ForeignKeyConstraint(['currency_id'], ['currencies.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_wallets_id'), 'wallets', ['id'], unique=False)
    op.create_table('user_wallets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('wallet_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'wallet_id', name='_user_wallets_user_id_wallet_id_uc')
    )
    op.create_index(op.f('ix_user_wallets_id'), 'user_wallets', ['id'], unique=False)
    op.create_table('wallet_transactions',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('wallet_id', sa.Integer(), nullable=False),
    sa.Column('exin_item_id', sa.Integer(), nullable=True),
    sa.Column('amount', sa.DECIMAL(precision=20, scale=8), nullable=False),
    sa.Column('amountBTC', sa.DECIMAL(precision=20, scale=8), nullable=False),
    sa.Column('amountUSD', sa.DECIMAL(precision=20, scale=2), nullable=False),
    sa.Column('amountRUB', sa.DECIMAL(precision=20, scale=2), nullable=False),
    sa.Column('amountARS', sa.DECIMAL(precision=20, scale=2), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('doc_id', sa.String(), nullable=False),
    sa.Column('comment', sa.TEXT(), nullable=True),
    sa.ForeignKeyConstraint(['exin_item_id'], ['exin_items.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_wallet_transactions_doc_id'), 'wallet_transactions', ['doc_id'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_exin_item_id'), 'wallet_transactions', ['exin_item_id'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_id'), 'wallet_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_user_id'), 'wallet_transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_wallet_transactions_wallet_id'), 'wallet_transactions', ['wallet_id'], unique=False)
    op.create_index(op.f('ix_alerts_created_at'), 'alerts', ['created_at'], unique=False)
    op.create_index(op.f('ix_alerts_triggered_at'), 'alerts', ['triggered_at'], unique=False)
    op.add_column('symbols', sa.Column('rate', sa.DECIMAL(precision=20, scale=8), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('symbols', 'rate')
    op.drop_index(op.f('ix_alerts_triggered_at'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_created_at'), table_name='alerts')
    op.drop_index(op.f('ix_wallet_transactions_wallet_id'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_user_id'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_id'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_exin_item_id'), table_name='wallet_transactions')
    op.drop_index(op.f('ix_wallet_transactions_doc_id'), table_name='wallet_transactions')
    op.drop_table('wallet_transactions')
    op.drop_index(op.f('ix_user_wallets_id'), table_name='user_wallets')
    op.drop_table('user_wallets')
    op.drop_index(op.f('ix_wallets_id'), table_name='wallets')
    op.drop_table('wallets')
    op.drop_index(op.f('ix_user_exin_items_id'), table_name='user_exin_items')
    op.drop_table('user_exin_items')
    op.drop_index(op.f('ix_exin_items_id'), table_name='exin_items')
    op.drop_table('exin_items')
    op.drop_index(op.f('ix_currencies_id'), table_name='currencies')
    op.drop_table('currencies')
    # ### end Alembic commands ###