-- Business Snapshots: one active snapshot per business

CREATE TABLE IF NOT EXISTS business_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES business_profiles(id),
    stories JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(business_id)
);

CREATE INDEX idx_business_snapshots_business_id
    ON business_snapshots (business_id);

ALTER TABLE business_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "business_scope" ON business_snapshots
    FOR SELECT USING (business_id IN (
        SELECT id FROM business_profiles WHERE user_id = auth.uid()
    ));

CREATE POLICY "service_role_manage" ON business_snapshots
    FOR ALL USING (true)
    WITH CHECK (true);
