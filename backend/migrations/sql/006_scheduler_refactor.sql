-- Scheduler Refactoring:
-- 1. Rebuild learning_checkpoint with proper PK and no stream_key
-- 2. Drop learning_jobs table
-- 3. Create scheduler_jobs table (general-purpose APScheduler persistence)

-- 1. Drop old learning_checkpoint and recreate with proper schema
DROP TABLE IF EXISTS learning_checkpoint;

CREATE TABLE learning_checkpoint (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_name TEXT NOT NULL,
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    last_processed_sequence BIGINT NOT NULL DEFAULT 0,
    start_sequence BIGINT NOT NULL DEFAULT 0,
    end_sequence BIGINT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'idle'
        CHECK (status IN ('idle', 'pending', 'running', 'completed', 'failed')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(worker_name, business_id)
);

CREATE INDEX idx_learning_checkpoint_worker_status
    ON learning_checkpoint (worker_name, status);

ALTER TABLE learning_checkpoint ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_manage" ON learning_checkpoint
    FOR ALL USING (true) WITH CHECK (true);

-- 2. Drop learning_jobs table (no longer needed)
DROP TABLE IF EXISTS learning_jobs;

-- 3. Create scheduler_jobs table (general-purpose APScheduler persistence)
CREATE TABLE IF NOT EXISTS scheduler_jobs (
    id TEXT PRIMARY KEY,
    job_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (status IN ('scheduled', 'completed', 'removed')),
    next_run_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    job_state TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_scheduler_jobs_status_next_run
    ON scheduler_jobs (status, next_run_at);

ALTER TABLE scheduler_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_manage" ON scheduler_jobs
    FOR ALL USING (true) WITH CHECK (true);
