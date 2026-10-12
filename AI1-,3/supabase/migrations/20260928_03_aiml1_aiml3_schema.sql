-- Migration: 20260928_03_aiml1_aiml3_schema.sql
-- AIML-1 & AIML-3 Schema Hardening, Preprocessing, Evaluation & Knowledge Base Tables

-- 1. Create sheet_status enum
DO $$ BEGIN
    CREATE TYPE sheet_status_enum AS ENUM (
        'UPLOADED', 'PREPROCESSED', 'OCR_COMPLETE', 'SEGMENTED', 'INDEXED',
        'EVALUATING', 'EVALUATED', 'UNDER_REVIEW', 'FINALIZED', 'PUBLISHED',
        'APPEALED', 'RE_EVALUATED', 'FAILED'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 2. Rubric Concepts Table
CREATE TABLE IF NOT EXISTS public.rubric_concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    concept TEXT NOT NULL,
    weight NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    approved_by_teacher BOOLEAN NOT NULL DEFAULT false,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Update answer_sheets Table
ALTER TABLE public.answer_sheets
    ADD COLUMN IF NOT EXISTS failed_stage TEXT,
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

-- 4. Sheet Pages Table (AIML-1)
CREATE TABLE IF NOT EXISTS public.sheet_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sheet_id UUID NOT NULL REFERENCES public.answer_sheets(id) ON DELETE CASCADE,
    page_number INT NOT NULL,
    clean_path TEXT NOT NULL,
    binary_path TEXT NOT NULL,
    quality_score NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    flags TEXT[] NOT NULL DEFAULT '{}',
    skew_deg NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    page_detected BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(sheet_id, page_number)
);

-- 5. OCR Lines Table
CREATE TABLE IF NOT EXISTS public.ocr_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID NOT NULL REFERENCES public.sheet_pages(id) ON DELETE CASCADE,
    bbox JSONB NOT NULL DEFAULT '[]'::jsonb,
    text TEXT NOT NULL DEFAULT '',
    confidence NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Answer Segments Table
CREATE TABLE IF NOT EXISTS public.answer_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sheet_id UUID NOT NULL REFERENCES public.answer_sheets(id) ON DELETE CASCADE,
    question_id UUID REFERENCES public.questions(id) ON DELETE SET NULL,
    page_number INT NOT NULL DEFAULT 1,
    bbox JSONB NOT NULL DEFAULT '[]'::jsonb,
    text TEXT NOT NULL DEFAULT '',
    confidence NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Update evaluations Table (AIML-3)
ALTER TABLE public.evaluations
    ADD COLUMN IF NOT EXISTS covered JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS partial JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS missing JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS keywords_missing JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS ai_suggested_min NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS ai_suggested_max NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS ai_confidence NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    ADD COLUMN IF NOT EXISTS rationale TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS flags TEXT[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS prompt_version TEXT NOT NULL DEFAULT 'v1.0',
    ADD COLUMN IF NOT EXISTS model TEXT NOT NULL DEFAULT 'mock-llm',
    ADD COLUMN IF NOT EXISTS tokens INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS latency_ms INT NOT NULL DEFAULT 0;

-- Remove single-evaluation unique constraint on answer_id to allow evaluation versioning
ALTER TABLE public.evaluations DROP CONSTRAINT IF EXISTS evaluations_answer_id_key;

-- 8. KB Documents & Chunks Tables
CREATE TABLE IF NOT EXISTS public.kb_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID REFERENCES public.exams(id) ON DELETE CASCADE,
    subject_id TEXT NOT NULL DEFAULT '',
    institution_id UUID REFERENCES public.colleges(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    file_url TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.kb_chunks
    ADD COLUMN IF NOT EXISTS institution_id UUID REFERENCES public.colleges(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS subject_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS heading TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS fts tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED;

-- Full-text GIN index & HNSW vector index
CREATE INDEX IF NOT EXISTS kb_chunks_fts_idx ON public.kb_chunks USING GIN(fts);
CREATE INDEX IF NOT EXISTS kb_chunks_embedding_hnsw_idx ON public.kb_chunks USING hnsw (embedding vector_cosine_ops);

-- 9. Tutor Messages Table
CREATE TABLE IF NOT EXISTS public.tutor_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    exam_id UUID NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,
    question_id UUID REFERENCES public.questions(id) ON DELETE SET NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. Re-assert Trigger Function checking BEFORE INSERT OR UPDATE on marks
CREATE OR REPLACE FUNCTION public.check_teacher_role_for_marks()
RETURNS TRIGGER AS $$
DECLARE
  awarder_role user_role;
BEGIN
  IF NEW.final_marks IS NOT NULL THEN
    IF NEW.awarded_by IS NULL THEN
      RAISE EXCEPTION 'final_marks cannot be set without an awarded_by user ID.';
    END IF;

    SELECT role INTO awarder_role FROM public.profiles WHERE id = NEW.awarded_by;

    IF awarder_role IS NULL OR awarder_role != 'teacher' THEN
      RAISE EXCEPTION 'Unauthorized: Only users with role teacher can set final_marks.';
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_enforce_teacher_marks ON public.marks;
CREATE TRIGGER trigger_enforce_teacher_marks
  BEFORE INSERT OR UPDATE ON public.marks
  FOR EACH ROW
  EXECUTE FUNCTION public.check_teacher_role_for_marks();

-- 11. Row Level Security Policies
ALTER TABLE public.rubric_concepts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sheet_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ocr_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.answer_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kb_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tutor_messages ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY rubric_concepts_teacher ON public.rubric_concepts
        FOR ALL USING (
            EXISTS (
                SELECT 1 FROM public.questions q
                JOIN public.exams e ON q.exam_id = e.id
                WHERE q.id = rubric_concepts.question_id AND e.teacher_id = auth.uid()
            )
        );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
