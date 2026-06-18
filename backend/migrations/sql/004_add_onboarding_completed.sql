-- Add onboarding_completed column to business_profiles
ALTER TABLE business_profiles
  ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT false;

-- Allow empty string in name column for empty profiles created before onboarding
ALTER TABLE business_profiles
  ALTER COLUMN name SET DEFAULT '';
