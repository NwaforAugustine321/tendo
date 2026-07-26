CREATE TABLE IF NOT EXISTS folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id TEXT NOT NULL,
    name TEXT NOT NULL,
    icon TEXT,
    color TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_folders_business_id ON folders(business_id);

CREATE TABLE IF NOT EXISTS records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id TEXT NOT NULL,
    folder_id UUID REFERENCES folders(id) ON DELETE SET NULL,
    user_id UUID,
    title TEXT NOT NULL,
    ai_insight JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_records_business_id ON records(business_id);
CREATE INDEX IF NOT EXISTS idx_records_folder_id ON records(folder_id);
CREATE INDEX IF NOT EXISTS idx_records_user_id ON records(user_id);

CREATE TABLE IF NOT EXISTS record_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id TEXT NOT NULL,
    record_id UUID NOT NULL REFERENCES records(id) ON DELETE CASCADE,
    content_type TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    file_url TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'processing',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_record_content_business_id ON record_content(business_id);
CREATE INDEX IF NOT EXISTS idx_record_content_record_id ON record_content(record_id);

ALTER TABLE folders ENABLE ROW LEVEL SECURITY;
CREATE POLICY folders_business_isolation ON folders
    FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE records ENABLE ROW LEVEL SECURITY;
CREATE POLICY records_business_isolation ON records
    FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE record_content ENABLE ROW LEVEL SECURITY;
CREATE POLICY record_content_business_isolation ON record_content
    FOR ALL USING (true) WITH CHECK (true);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER folders_updated_at BEFORE UPDATE ON folders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER records_updated_at BEFORE UPDATE ON records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER record_content_updated_at BEFORE UPDATE ON record_content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
