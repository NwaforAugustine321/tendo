CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    source_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    UNIQUE(business_id, source_type)
);


CREATE INDEX IF NOT EXISTS idx_data_sources_business_id ON data_sources(business_id);
CREATE INDEX IF NOT EXISTS idx_data_sources_status ON data_sources(business_id, status);
