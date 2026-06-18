-- Add logo_url and phone/location to business_profiles
ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS logo_url TEXT DEFAULT '';
ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS phone TEXT DEFAULT '';
ALTER TABLE business_profiles ADD COLUMN IF NOT EXISTS location TEXT DEFAULT '';
