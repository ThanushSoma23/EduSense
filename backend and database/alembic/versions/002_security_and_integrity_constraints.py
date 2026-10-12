"""Add Security and Data Integrity Constraints & Triggers for Max Marks Validation

Revision ID: 002_security_and_integrity_constraints
Revises: 001_initial_schema
Create Date: 2026-10-09 12:50:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_sec_integrity_constraints'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add check constraints to evaluations table
    op.create_check_constraint(
        'chk_eval_similarity_range',
        'evaluations',
        'similarity_score IS NULL OR (similarity_score >= 0.0 AND similarity_score <= 1.0)'
    )
    op.create_check_constraint(
        'chk_eval_concept_range',
        'evaluations',
        'concept_coverage IS NULL OR (concept_coverage >= 0.0 AND concept_coverage <= 1.0)'
    )
    op.create_check_constraint(
        'chk_eval_suggested_marks_positive',
        'evaluations',
        'suggested_marks >= 0.0'
    )

    # 2. Add check constraint to final_marks table
    op.create_check_constraint(
        'chk_final_marks_positive',
        'final_marks',
        'approved_marks >= 0.0'
    )

    # 3. Add PostgreSQL Trigger Functions & Triggers
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Trigger 1: Validate approved_marks <= questions.max_marks on final_marks INSERT/UPDATE
        op.execute("""
            CREATE OR REPLACE FUNCTION fn_validate_final_mark_max_marks()
            RETURNS TRIGGER AS $$
            DECLARE
                v_max_marks FLOAT;
            BEGIN
                SELECT q.max_marks INTO v_max_marks
                FROM student_answers sa
                JOIN questions q ON q.id = sa.question_id
                WHERE sa.id = NEW.answer_id;

                IF v_max_marks IS NOT NULL AND NEW.approved_marks > v_max_marks THEN
                    RAISE EXCEPTION 'Approved marks (%) exceed maximum marks (%) for associated question',
                        NEW.approved_marks, v_max_marks;
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)

        op.execute("""
            DROP TRIGGER IF EXISTS trg_validate_final_mark_max_marks ON final_marks;
            CREATE TRIGGER trg_validate_final_mark_max_marks
            BEFORE INSERT OR UPDATE ON final_marks
            FOR EACH ROW
            EXECUTE FUNCTION fn_validate_final_mark_max_marks();
        """)

        # Trigger 2: Prevent reducing question max_marks if existing approved final_marks exceed the new limit
        op.execute("""
            CREATE OR REPLACE FUNCTION fn_prevent_question_max_marks_reduction()
            RETURNS TRIGGER AS $$
            DECLARE
                v_highest_approved FLOAT;
            BEGIN
                IF NEW.max_marks < OLD.max_marks THEN
                    SELECT MAX(fm.approved_marks) INTO v_highest_approved
                    FROM student_answers sa
                    JOIN final_marks fm ON fm.answer_id = sa.id
                    WHERE sa.question_id = NEW.id;

                    IF v_highest_approved IS NOT NULL AND v_highest_approved > NEW.max_marks THEN
                        RAISE EXCEPTION 'Cannot reduce question max_marks to %: existing approved final mark (%) exceeds new limit',
                            NEW.max_marks, v_highest_approved;
                    END IF;
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)

        op.execute("""
            DROP TRIGGER IF EXISTS trg_prevent_question_max_marks_reduction ON questions;
            CREATE TRIGGER trg_prevent_question_max_marks_reduction
            BEFORE UPDATE ON questions
            FOR EACH ROW
            EXECUTE FUNCTION fn_prevent_question_max_marks_reduction();
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_question_max_marks_reduction ON questions;")
        op.execute("DROP FUNCTION IF EXISTS fn_prevent_question_max_marks_reduction();")
        op.execute("DROP TRIGGER IF EXISTS trg_validate_final_mark_max_marks ON final_marks;")
        op.execute("DROP FUNCTION IF EXISTS fn_validate_final_mark_max_marks();")

    op.drop_constraint('chk_final_marks_positive', 'final_marks', type_='check')
    op.drop_constraint('chk_eval_suggested_marks_positive', 'evaluations', type_='check')
    op.drop_constraint('chk_eval_concept_range', 'evaluations', type_='check')
    op.drop_constraint('chk_eval_similarity_range', 'evaluations', type_='check')
