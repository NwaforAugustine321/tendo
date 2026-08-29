-- Conversation messages table (replaces inline JSONB on conversation_sessions)
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    record_id UUID,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL DEFAULT '',
    message_type TEXT DEFAULT 'text',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_session ON conversation_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_business ON conversation_messages(business_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_record ON conversation_messages(record_id);

-- Enable RLS
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "business_scope" ON conversation_messages FOR ALL
    USING (business_id IN (SELECT id FROM business_profiles WHERE user_id = auth.uid()));
