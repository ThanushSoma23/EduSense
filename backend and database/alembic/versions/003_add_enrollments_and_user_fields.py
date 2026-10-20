"""Add exam_enrollments table and users roll_number and department fields

Revision ID: 003_enrollments_and_user_fields
Revises: 002_sec_integrity_constraints
Create Date: 2026-10-18 14:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_enrollments_and_user_fields'
down_revision: Union[str, None] = '002_sec_integrity_constraints'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add roll_number and department to users table
    # Both are nullable to safely accommodate existing users without requiring table rebuilds or backfill.
    op.add_column('users', sa.Column('roll_number', sa.String(length=50), nullable=True))
    op.create_index('ix_users_roll_number', 'users', ['roll_number'], unique=False)
    op.add_column('users', sa.Column('department', sa.String(length=100), nullable=True))

    # 2. Create exam_enrollments table
    # Table starts empty; no default enrollments are synthesized for existing users or exams.
    op.create_table(
        'exam_enrollments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exam_id', 'student_id', name='uq_exam_student_enrollment')
    )
    op.create_index('ix_exam_enrollments_id', 'exam_enrollments', ['id'], unique=False)
    op.create_index('ix_exam_enrollments_exam_id', 'exam_enrollments', ['exam_id'], unique=False)
    op.create_index('ix_exam_enrollments_student_id', 'exam_enrollments', ['student_id'], unique=False)
    op.create_index('idx_enrollment_exam_student', 'exam_enrollments', ['exam_id', 'student_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_enrollment_exam_student', table_name='exam_enrollments')
    op.drop_index('ix_exam_enrollments_student_id', table_name='exam_enrollments')
    op.drop_index('ix_exam_enrollments_exam_id', table_name='exam_enrollments')
    op.drop_index('ix_exam_enrollments_id', table_name='exam_enrollments')
    op.drop_table('exam_enrollments')

    op.drop_index('ix_users_roll_number', table_name='users')
    op.drop_column('users', 'department')
    op.drop_column('users', 'roll_number')
