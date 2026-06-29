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

ALTER TABLE business_events ENABLE ROW LEVEL SECURITY;

-- RLS policies (service role bypasses, these protect direct access)
CREATE POLICY "business_scope" ON business_events
    FOR ALL USING (business_id IN (
        SELECT id FROM business_profiles WHERE user_id = auth.uid()
    ));

