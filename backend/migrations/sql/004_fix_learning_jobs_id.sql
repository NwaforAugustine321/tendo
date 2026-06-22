-- Fix learning_jobs.id to TEXT to support both UUID and APScheduler string IDs

-- Drop the existing table and recreate with TEXT id
-- (safe since this is a new system with no production data)
DROP TABLE IF EXISTS learning_jobs;

CREATE TABLE IF NOT EXISTS learning_jobs (
    id TEXT PRIMARY KEY,
    worker_name TEXT NOT NULL,
    stream_key TEXT NOT NULL,
    start_sequence BIGINT NOT NULL DEFAULT 0,
    end_sequence BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'scheduled')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_learning_jobs_worker_status
    ON learning_jobs (worker_name, status);

ALTER TABLE learning_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "business_scope" ON learning_jobs
    FOR ALL USING (true);
