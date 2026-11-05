"""drop Stripe billing and outreach reports: accounts have no plans

Revision ID: 5d2e8a1c7f30
Revises: 0a9ef9fb4970
Create Date: 2026-11-05 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '5d2e8a1c7f30'
down_revision = '0a9ef9fb4970'
branch_labels = None
depends_on = None

CUSTOMER_COLUMNS = (
    'stripe_customer_id', 'stripe_subscription_id', 'plan', 'subscription_status', 'current_period_start',
    'current_period_end', 'cancel_at_period_end', 'complimentary',
)


def upgrade():
    op.drop_table('outreach_posting')
    op.drop_table('outreach_report')
    op.drop_table('stripe_event')
    with op.batch_alter_table('paid_check') as batch:
        batch.drop_column('reported_at')
        batch.drop_column('extra')
    with op.batch_alter_table('customer') as batch:
        for column in CUSTOMER_COLUMNS:
            batch.drop_column(column)


def downgrade():
    # Accounts come back as complimentary Agency customers: an active plan with nothing at Stripe, as before.
    with op.batch_alter_table('customer') as batch:
        batch.add_column(sa.Column('stripe_customer_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
        batch.add_column(sa.Column('stripe_subscription_id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
        batch.add_column(sa.Column('plan', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=True))
        batch.add_column(sa.Column('subscription_status', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True))
        batch.add_column(sa.Column('current_period_start', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True))
        batch.add_column(sa.Column('current_period_end', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True))
        batch.add_column(sa.Column('cancel_at_period_end', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.add_column(sa.Column('complimentary', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.create_unique_constraint('customer_stripe_customer_id_key', ['stripe_customer_id'])
    op.execute("UPDATE customer SET plan = 'agency', subscription_status = 'active', complimentary = true")
    with op.batch_alter_table('paid_check') as batch:
        batch.add_column(sa.Column('extra', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch.add_column(sa.Column('reported_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True))
    op.create_table('stripe_event',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('type', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('received_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('outreach_report',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('token', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('created_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
    sa.Column('company', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('url', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=False),
    sa.Column('found', sa.Integer(), nullable=False),
    sa.Column('outside_ontario', sa.Integer(), nullable=False),
    sa.Column('checklist', sa.JSON(), nullable=True),
    sa.Column('customer_id', sa.Uuid(), nullable=True),
    sa.Column('saved_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
    sa.Column('first_viewed_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
    sa.Column('views', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customer.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_outreach_report_created_at'), 'outreach_report', ['created_at'], unique=False)
    op.create_index(op.f('ix_outreach_report_customer_id'), 'outreach_report', ['customer_id'], unique=False)
    op.create_index(op.f('ix_outreach_report_token'), 'outreach_report', ['token'], unique=True)
    op.create_table('outreach_posting',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('report_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
    sa.Column('location', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.Column('url', sqlmodel.sql.sqltypes.AutoString(length=2048), nullable=False),
    sa.Column('where', sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
    sa.Column('findings', sa.JSON(), nullable=True),
    sa.Column('form_status', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
    sa.Column('form_findings', sa.JSON(), nullable=True),
    sa.Column('note', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
    sa.ForeignKeyConstraint(['report_id'], ['outreach_report.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_outreach_posting_report_id'), 'outreach_posting', ['report_id'], unique=False)
