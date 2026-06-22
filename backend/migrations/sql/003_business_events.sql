-- Business Event System: append-only event store, checkpoint, and job tables

-- 1. Event Store table (append-only)
CREATE TABLE IF NOT EXISTS business_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    session_id UUID REFERENCES conversation_sessions(id),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    sequence_number BIGINT NOT NULL,
    payload JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for stream queries (worker polling by stream + sequence)
CREATE INDEX idx_business_events_stream_seq
    ON business_events (business_id, entity_type, entity_id, sequence_number);

-- Index for business-wide queries
CREATE INDEX idx_business_events_business_id
    ON business_events (business_id, created_at);

-- Immutability: block UPDATE and DELETE operations
CREATE OR REPLACE FUNCTION prevent_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'business_events table is append-only: % operations are not permitted', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_update
    BEFORE UPDATE ON business_events
    FOR EACH ROW EXECUTE FUNCTION prevent_event_mutation();

CREATE TRIGGER trg_prevent_delete
    BEFORE DELETE ON business_events
    FOR EACH ROW EXECUTE FUNCTION prevent_event_mutation();

-- 2. Checkpoint table (worker progress tracking)
CREATE TABLE IF NOT EXISTS learning_checkpoint (
    worker_name TEXT NOT NULL,
    stream_key TEXT NOT NULL,
    last_processed_sequence BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (worker_name, stream_key)
);

-- 3. Jobs table (worker execution tracking)
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

CREATE INDEX idx_learning_jobs_worker_status
    ON learning_jobs (worker_name, status);

-- 5. Enable RLS on all three tables
ALTER TABLE business_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_checkpoint ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_jobs ENABLE ROW LEVEL SECURITY;

-- RLS policies (service role bypasses, these protect direct access)
CREATE POLICY "business_scope" ON business_events
    FOR ALL USING (business_id IN (
        SELECT id FROM business_profiles WHERE user_id = auth.uid()
    ));

CREATE POLICY "business_scope" ON learning_checkpoint
    FOR ALL USING (true);

CREATE POLICY "business_scope" ON learning_jobs
    FOR ALL USING (true);
