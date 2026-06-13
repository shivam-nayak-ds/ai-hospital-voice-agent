"""
Initial database schema migration
Generated: 2026-06-12
Includes all 12 core tables for the ASHA Hospital Agent.
"""
from alembic import op
import sqlalchemy as sa


revision: str = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── DEPARTMENTS ──────────────────────────────────────────────────────────
    op.create_table(
        'DEPARTMENTS',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('NAME', sa.String(), nullable=False),
        sa.Column('DESCRIPTION', sa.String(), nullable=True),
        sa.Column('LOCATION', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('ID'),
        sa.UniqueConstraint('NAME')
    )
    op.create_index('ix_DEPARTMENTS_NAME', 'DEPARTMENTS', ['NAME'])

    # ── DOCTORS ──────────────────────────────────────────────────────────────
    op.create_table(
        'DOCTORS',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('NAME', sa.String(), nullable=False),
        sa.Column('SPECIALIZATION', sa.String(), nullable=False),
        sa.Column('QUALIFICATION', sa.String(), nullable=True),
        sa.Column('EXPERIENCE_YEARS', sa.Integer(), nullable=True),
        sa.Column('CONSULTATION_FEE', sa.Integer(), nullable=True),
        sa.Column('LANGUAGES', sa.String(), nullable=True),
        sa.Column('STATUS', sa.String(), nullable=False, server_default='Active'),
        sa.Column('EMAIL', sa.String(), nullable=True),
        sa.Column('PHONE', sa.String(), nullable=True),
        sa.Column('DEPARTMENT_ID', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['DEPARTMENT_ID'], ['DEPARTMENTS.ID']),
        sa.PrimaryKeyConstraint('ID')
    )
    op.create_index('ix_DOCTORS_NAME', 'DOCTORS', ['NAME'])
    op.create_index('ix_DOCTORS_SPECIALIZATION', 'DOCTORS', ['SPECIALIZATION'])
    op.create_index('idx_doctors_name_spec', 'DOCTORS', ['NAME', 'SPECIALIZATION'])

    # ── DOCTOR_SCHEDULES ─────────────────────────────────────────────────────
    op.create_table(
        'DOCTOR_SCHEDULES',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('DOCTOR_ID', sa.Integer(), nullable=False),
        sa.Column('DAY_OF_WEEK', sa.String(), nullable=False),
        sa.Column('START_TIME', sa.String(), nullable=False),
        sa.Column('END_TIME', sa.String(), nullable=False),
        sa.Column('STATUS', sa.String(), nullable=False, server_default='Available'),
        sa.ForeignKeyConstraint(['DOCTOR_ID'], ['DOCTORS.ID']),
        sa.PrimaryKeyConstraint('ID')
    )

    # ── PATIENTS ─────────────────────────────────────────────────────────────
    op.create_table(
        'PATIENTS',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('NAME', sa.String(), nullable=False),
        sa.Column('AGE', sa.Integer(), nullable=True),
        sa.Column('GENDER', sa.String(), nullable=True),
        sa.Column('PHONE', sa.String(), nullable=False),
        sa.Column('EMAIL', sa.String(), nullable=True),
        sa.Column('ADDRESS', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('ID')
    )
    op.create_index('ix_PATIENTS_NAME', 'PATIENTS', ['NAME'])
    op.create_index('ix_PATIENTS_PHONE', 'PATIENTS', ['PHONE'])

    # ── APPOINTMENTS ─────────────────────────────────────────────────────────
    op.create_table(
        'APPOINTMENTS',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('PATIENT_NAME', sa.String(), nullable=False),
        sa.Column('DOCTOR_NAME', sa.String(), nullable=False),
        sa.Column('APPOINTMENT_TIME', sa.String(), nullable=False),
        sa.Column('APPOINTMENT_DATE', sa.Date(), nullable=False),
        sa.Column('PATIENT_ID', sa.Integer(), nullable=False),
        sa.Column('DOCTOR_ID', sa.Integer(), nullable=False),
        sa.Column('STATUS', sa.String(), nullable=False, server_default='Confirmed'),
        sa.ForeignKeyConstraint(['DOCTOR_ID'], ['DOCTORS.ID']),
        sa.ForeignKeyConstraint(['PATIENT_ID'], ['PATIENTS.ID']),
        sa.PrimaryKeyConstraint('ID'),
        sa.UniqueConstraint('DOCTOR_ID', 'APPOINTMENT_TIME', 'APPOINTMENT_DATE', name='uq_doctor_slot')
    )
    op.create_index('idx_appt_doctor_date', 'APPOINTMENTS', ['DOCTOR_ID', 'APPOINTMENT_DATE'])

    # ── BILLING_CATALOG ───────────────────────────────────────────────────────
    op.create_table(
        'BILLING_CATALOG',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ITEM_NAME', sa.String(), nullable=False),
        sa.Column('CATEGORY', sa.String(), nullable=False),
        sa.Column('PRICE', sa.Integer(), nullable=False),
        sa.Column('CODE', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('ID'),
        sa.UniqueConstraint('CODE')
    )
    op.create_index('ix_BILLING_CATALOG_ITEM_NAME', 'BILLING_CATALOG', ['ITEM_NAME'])
    op.create_index('ix_BILLING_CATALOG_CODE', 'BILLING_CATALOG', ['CODE'])

    # ── INSURANCE_PROVIDERS ───────────────────────────────────────────────────
    op.create_table(
        'INSURANCE_PROVIDERS',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('NAME', sa.String(), nullable=False),
        sa.Column('CASHLESS_AVAILABLE', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('HELPLINE', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('ID'),
        sa.UniqueConstraint('NAME')
    )
    op.create_index('ix_INSURANCE_PROVIDERS_NAME', 'INSURANCE_PROVIDERS', ['NAME'])

    # ── WARD_MANAGEMENT ───────────────────────────────────────────────────────
    op.create_table(
        'WARD_MANAGEMENT',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('WARD_TYPE', sa.String(), nullable=False),
        sa.Column('TOTAL_BEDS', sa.Integer(), nullable=False),
        sa.Column('OCCUPIED_BEDS', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('PRICE_PER_DAY', sa.Integer(), nullable=False),
        sa.CheckConstraint('"OCCUPIED_BEDS" >= 0', name='chk_occupied_beds_positive'),
        sa.CheckConstraint('"OCCUPIED_BEDS" <= "TOTAL_BEDS"', name='chk_occupied_beds_limit'),
        sa.PrimaryKeyConstraint('ID'),
        sa.UniqueConstraint('WARD_TYPE')
    )
    op.create_index('ix_WARD_MANAGEMENT_WARD_TYPE', 'WARD_MANAGEMENT', ['WARD_TYPE'])

    # ── LAB_REPORTS ───────────────────────────────────────────────────────────
    op.create_table(
        'LAB_REPORTS',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('PATIENT_ID', sa.Integer(), nullable=False),
        sa.Column('TEST_NAME', sa.String(), nullable=False),
        sa.Column('RESULT', sa.String(), nullable=True),
        sa.Column('STATUS', sa.String(), nullable=False, server_default='Pending'),
        sa.Column('ORDERED_DATE', sa.Date(), nullable=False),
        sa.Column('REPORT_URL', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['PATIENT_ID'], ['PATIENTS.ID']),
        sa.PrimaryKeyConstraint('ID')
    )
    op.create_index('ix_LAB_REPORTS_TEST_NAME', 'LAB_REPORTS', ['TEST_NAME'])

    # ── CONVERSATION_LOGS ─────────────────────────────────────────────────────
    op.create_table(
        'CONVERSATION_LOGS',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('SESSION_ID', sa.String(), nullable=False),
        sa.Column('ROLE', sa.String(), nullable=False),
        sa.Column('CONTENT', sa.Text(), nullable=False),
        sa.Column('TIMESTAMP', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('ID')
    )
    op.create_index('ix_CONVERSATION_LOGS_SESSION_ID', 'CONVERSATION_LOGS', ['SESSION_ID'])

    # ── AGENT_EVENTS ──────────────────────────────────────────────────────────
    op.create_table(
        'AGENT_EVENTS',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('SESSION_ID', sa.String(), nullable=False),
        sa.Column('EVENT_TYPE', sa.String(), nullable=False),
        sa.Column('ROUTER_NAME', sa.String(), nullable=True),
        sa.Column('EXECUTION_TIME_MS', sa.Float(), nullable=True),
        sa.Column('DETAILS', sa.Text(), nullable=True),
        sa.Column('TIMESTAMP', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('ID')
    )
    op.create_index('ix_AGENT_EVENTS_SESSION_ID', 'AGENT_EVENTS', ['SESSION_ID'])
    op.create_index('ix_AGENT_EVENTS_EVENT_TYPE', 'AGENT_EVENTS', ['EVENT_TYPE'])

    # ── AUDIT_LOGS ────────────────────────────────────────────────────────────
    op.create_table(
        'AUDIT_LOGS',
        sa.Column('ID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ACTION_TYPE', sa.String(), nullable=False),
        sa.Column('USER_ID', sa.String(), nullable=False),
        sa.Column('ACTION_DETAILS', sa.Text(), nullable=True),
        sa.Column('TIMESTAMP', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('ID')
    )


def downgrade() -> None:
    op.drop_table('AUDIT_LOGS')
    op.drop_table('AGENT_EVENTS')
    op.drop_table('CONVERSATION_LOGS')
    op.drop_table('LAB_REPORTS')
    op.drop_table('WARD_MANAGEMENT')
    op.drop_table('INSURANCE_PROVIDERS')
    op.drop_table('BILLING_CATALOG')
    op.drop_table('APPOINTMENTS')
    op.drop_table('PATIENTS')
    op.drop_table('DOCTOR_SCHEDULES')
    op.drop_table('DOCTORS')
    op.drop_table('DEPARTMENTS')
