-- EduSense AI — Supabase Row Level Security (RLS) Policies Script
-- Supported Identity Architecture:
-- 1. Backend Application Connection (DATABASE_URL): FastAPI server validates custom JWTs and enforces RBAC server-side.
-- 2. Direct PostgreSQL / Supabase Client Connections: RLS policies enforce student isolation & teacher ownership using current_app_user_id().

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE exams ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE answer_sheets ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE final_marks ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Helper function to extract current authenticated user_id from session setting or JWT sub claim or auth.uid()
CREATE OR REPLACE FUNCTION current_app_user_id() RETURNS TEXT AS $$
BEGIN
    RETURN COALESCE(
        nullif(current_setting('app.current_user_id', true), ''),
        auth.jwt() ->> 'sub',
        auth.uid()::text
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- 1. Users table policies
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (current_app_user_id() = id::text);

-- 2. Exams table policies
CREATE POLICY "Teachers can insert and modify own exams" ON exams
    FOR ALL
    USING (teacher_id::text = current_app_user_id())
    WITH CHECK (teacher_id::text = current_app_user_id());

CREATE POLICY "Students can view published exams" ON exams
    FOR SELECT USING (status IN ('PUBLISHED', 'COMPLETED'));

-- 3. Questions table policies
CREATE POLICY "Teachers can manage questions for their exams" ON questions
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM exams
            WHERE exams.id = questions.exam_id
            AND exams.teacher_id::text = current_app_user_id()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM exams
            WHERE exams.id = questions.exam_id
            AND exams.teacher_id::text = current_app_user_id()
        )
    );

CREATE POLICY "Students can view questions for published exams" ON questions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM exams
            WHERE exams.id = questions.exam_id
            AND exams.status IN ('PUBLISHED', 'COMPLETED')
        )
    );

-- 4. Answer Sheets policies
CREATE POLICY "Students can create and view own submissions" ON answer_sheets
    FOR ALL
    USING (student_id::text = current_app_user_id())
    WITH CHECK (student_id::text = current_app_user_id());

CREATE POLICY "Teachers can view submissions for their exams" ON answer_sheets
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM exams
            WHERE exams.id = answer_sheets.exam_id
            AND exams.teacher_id::text = current_app_user_id()
        )
    );

-- 5. Student Answers policies
CREATE POLICY "Students can view own extracted answers" ON student_answers
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM answer_sheets
            WHERE answer_sheets.id = student_answers.submission_id
            AND answer_sheets.student_id::text = current_app_user_id()
        )
    );

-- 6. Evaluations policies (AI & Teachers)
CREATE POLICY "Teachers can view evaluations for their exams" ON evaluations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM student_answers
            JOIN answer_sheets ON answer_sheets.id = student_answers.submission_id
            JOIN exams ON exams.id = answer_sheets.exam_id
            WHERE student_answers.id = evaluations.answer_id
            AND exams.teacher_id::text = current_app_user_id()
        )
    );

-- 7. Final Marks policies
CREATE POLICY "Teachers can create and update final marks" ON final_marks
    FOR ALL
    USING (reviewing_teacher_id::text = current_app_user_id())
    WITH CHECK (reviewing_teacher_id::text = current_app_user_id());

CREATE POLICY "Students can view approved final marks for their submissions" ON final_marks
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM student_answers
            JOIN answer_sheets ON answer_sheets.id = student_answers.submission_id
            WHERE student_answers.id = final_marks.answer_id
            AND answer_sheets.student_id::text = current_app_user_id()
        )
    );

-- 8. Audit Logs policies
CREATE POLICY "Only teachers can view audit logs" ON audit_logs
    FOR SELECT USING (teacher_id::text = current_app_user_id());
