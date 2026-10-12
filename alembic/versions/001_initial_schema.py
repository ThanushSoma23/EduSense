"""Initial EduSense AI Database Schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-09 12:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('TEACHER', 'STUDENT', name='userrole'), nullable=False),
        sa.Column('account_status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email_role', 'users', ['email', 'role'])

    # 2. exams table
    op.create_table(
        'exams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_exams_teacher_id', 'exams', ['teacher_id'])

    # 3. questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('question_number', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('model_answer', sa.Text(), nullable=False),
        sa.Column('max_marks', sa.Float(), nullable=False),
        sa.Column('rubric', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('max_marks > 0', name='chk_max_marks_positive'),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('exam_id', 'question_number', name='uq_exam_question_number')
    )
    op.create_index('idx_questions_exam_id', 'questions', ['exam_id'])

    # 4. answer_sheets table
    op.create_table(
        'answer_sheets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('file_reference', sa.String(length=512), nullable=False),
        sa.Column('submission_time', sa.DateTime(), nullable=False),
        sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'exam_id', name='uq_student_exam_submission')
    )
    op.create_index('idx_answer_sheets_student_exam', 'answer_sheets', ['student_id', 'exam_id'])

    # 5. student_answers table
    op.create_table(
        'student_answers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('submission_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('ocr_confidence', sa.Float(), nullable=True),
        sa.Column('extraction_status', sa.String(length=50), nullable=False, server_default='SUCCESS'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submission_id'], ['answer_sheets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('submission_id', 'question_id', name='uq_submission_question')
    )
    op.create_index('idx_student_answers_sub_q', 'student_answers', ['submission_id', 'question_id'])

    # 6. evaluations table
    op.create_table(
        'evaluations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('answer_id', sa.Integer(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('concept_coverage', sa.Float(), nullable=True),
        sa.Column('suggested_marks', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('supporting_references', sa.Text(), nullable=True),
        sa.Column('evaluation_status', sa.String(length=50), nullable=False, server_default='COMPLETED'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['answer_id'], ['student_answers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('answer_id')
    )
    op.create_index('idx_evaluations_answer_id', 'evaluations', ['answer_id'])

    # 7. final_marks table
    op.create_table(
        'final_marks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('answer_id', sa.Integer(), nullable=False),
        sa.Column('approved_marks', sa.Float(), nullable=False),
        sa.Column('reviewing_teacher_id', sa.Integer(), nullable=False),
        sa.Column('approval_status', sa.String(length=50), nullable=False, server_default='APPROVED'),
        sa.Column('approval_timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['answer_id'], ['student_answers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewing_teacher_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('answer_id')
    )
    op.create_index('idx_final_marks_answer_teacher', 'final_marks', ['answer_id', 'reviewing_teacher_id'])

    # 8. audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('final_mark_id', sa.Integer(), nullable=True),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('previous_value', sa.Text(), nullable=True),
        sa.Column('updated_value', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['final_mark_id'], ['final_marks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_logs_teacher_time', 'audit_logs', ['teacher_id', 'timestamp'])
    op.create_index('idx_audit_logs_mark_id', 'audit_logs', ['final_mark_id'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('final_marks')
    op.drop_table('evaluations')
    op.drop_table('student_answers')
    op.drop_table('answer_sheets')
    op.drop_table('questions')
    op.drop_table('exams')
    op.drop_table('users')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP TYPE IF EXISTS userrole;")
