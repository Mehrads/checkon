"""Add complimentary test accounts

Revision ID: c3f1a7d2e9b4
Revises: 9557c2d34348
Create Date: 2026-10-23 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'c3f1a7d2e9b4'
down_revision = '9557c2d34348'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('customer', sa.Column('complimentary', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('customer', 'stripe_customer_id', existing_type=sqlmodel.sql.sqltypes.AutoString(length=255),
                    nullable=True)


def downgrade():
    op.execute("DELETE FROM customer WHERE complimentary")
    op.alter_column('customer', 'stripe_customer_id', existing_type=sqlmodel.sql.sqltypes.AutoString(length=255),
                    nullable=False)
    op.drop_column('customer', 'complimentary')
