"""Merge careers page audits and the archive

Revision ID: 9557c2d34348
Revises: 16177d2b07f2, 57f387f77ff4
Create Date: 2026-10-23 10:12:44.125356

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '9557c2d34348'
down_revision = ('16177d2b07f2', '57f387f77ff4')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
