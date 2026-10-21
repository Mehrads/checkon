"""Merge the paid-plans and employer-size migrations

Revision ID: 083c2fe327d4
Revises: 110e1822b4ac, efc0ba474aa6
Create Date: 2026-10-21 16:54:45.540881

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '083c2fe327d4'
down_revision = ('110e1822b4ac', 'efc0ba474aa6')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
