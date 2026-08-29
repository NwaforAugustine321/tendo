# Migrations

Run these SQL files against your Supabase project in order.

## How to apply

Via Supabase SQL Editor:
1. Go to your Supabase dashboard → SQL Editor
2. Paste the contents of each file in `sql/` and run

Via Supabase CLI:
```bash
supabase db push
```

## Files

- `sql/001_init.sql` — All tables, RLS policies
- `sql/002_vector_store_table.sql` — Vector store table
- `sql/003_business_events.sql` — Business event system (append-only store, checkpoints, jobs)
- `sql/004_folders_records.sql` — Folders and records
- `sql/005_business_snapshots.sql` — Business snapshots (one active per business)
