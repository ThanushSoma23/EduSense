"""Add subjects catalog, semester, and section to exams and users

Revision ID: 004_class_structure_and_subjects
Revises: 003_enrollments_and_user_fields
Create Date: 2026-10-18 16:30:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_class_structure_and_subjects'
down_revision: Union[str, None] = '003_enrollments_and_user_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create subjects table
    op.create_table(
        'subjects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('default_semester', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_subjects_name'),
        sa.UniqueConstraint('code', name='uq_subjects_code')
    )
    op.create_index('ix_subjects_id', 'subjects', ['id'], unique=False)
    op.create_index('ix_subjects_name', 'subjects', ['name'], unique=True)
    op.create_index('ix_subjects_code', 'subjects', ['code'], unique=False)

    # 2. Add class fields to exams table (nullable to safely preserve older historical records)
    op.add_column('exams', sa.Column('code', sa.String(length=50), nullable=True))
    op.add_column('exams', sa.Column('semester', sa.Integer(), nullable=True))
    op.add_column('exams', sa.Column('section', sa.Integer(), nullable=True))
    op.create_index('ix_exams_semester', 'exams', ['semester'], unique=False)
    op.create_index('ix_exams_section', 'exams', ['section'], unique=False)
    op.create_index('idx_exams_class_lookup', 'exams', ['semester', 'section', 'subject'], unique=False)

    # 3. Add registered academic class fields to users table
    op.add_column('users', sa.Column('semester', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('section', sa.Integer(), nullable=True))
    op.create_index('ix_users_semester', 'users', ['semester'], unique=False)
    op.create_index('ix_users_section', 'users', ['section'], unique=False)
    op.create_index('idx_users_class', 'users', ['semester', 'section'], unique=False)


def downgrade() -> None:
    # Drop user class fields
    op.drop_index('idx_users_class', table_name='users')
    op.drop_index('ix_users_section', table_name='users')
    op.drop_index('ix_users_semester', table_name='users')
    op.drop_column('users', 'section')
    op.drop_column('users', 'semester')

    # Drop exam class fields
    op.drop_index('idx_exams_class_lookup', table_name='exams')
    op.drop_index('ix_exams_section', table_name='exams')
    op.drop_index('ix_exams_semester', table_name='exams')
    op.drop_column('exams', 'section')
    op.drop_column('exams', 'semester')
    op.drop_column('exams', 'code')

    # Drop subjects table
    op.drop_index('ix_subjects_code', table_name='subjects')
    op.drop_index('ix_subjects_name', table_name='subjects')
    op.drop_index('ix_subjects_id', table_name='subjects')
    op.drop_table('subjects')
