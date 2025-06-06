"""added apartment tag enum table

Revision ID: 9f5ad1a3fa87
Revises: 626177592f6d
Create Date: 2025-05-18 11:04:35.772712

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9f5ad1a3fa87'
down_revision: str | None = '626177592f6d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('apartment_tags',
    sa.Column('apartment_tag_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('apartment_tag_id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('apartment_tag_mappings',
    sa.Column('apartment_tag_mapping_id', sa.UUID(), nullable=False),
    sa.Column('apartment_id', sa.UUID(), nullable=False),
    sa.Column('apartment_tag_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['apartment_id'], ['apartments.apartment_id'], ),
    sa.ForeignKeyConstraint(['apartment_tag_id'], ['apartment_tags.apartment_tag_id'], ),
    sa.PrimaryKeyConstraint('apartment_tag_mapping_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('apartment_tag_mappings')
    op.drop_table('apartment_tags')
    # ### end Alembic commands ###
