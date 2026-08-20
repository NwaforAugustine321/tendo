-- ============================================================
-- Business Events
-- ============================================================

create table if not exists public.business_events (
    id uuid primary key
        default gen_random_uuid(),

    sequence_id bigint generated always as identity
        unique
        not null,

    business_id uuid not null
        references public.business_profiles(id)
        on delete cascade,

    event_type text not null,

 
    document_key uuid not null,

    chunk_index integer not null,

    total_chunks integer not null,

    payload text not null,

    status text not null default 'pending'
        check (status in ('pending', 'processed')),

    created_at timestamptz not null
        default now(),

    constraint business_events_event_type_not_empty
        check (
            length(trim(event_type)) > 0
        ),

    constraint business_events_chunk_index_valid
        check (
            chunk_index >= 1
        ),

    constraint business_events_total_chunks_valid
        check (
            total_chunks > 0
        ),

    constraint business_events_chunk_index_within_total
        check (
            chunk_index <= total_chunks
        ),

    constraint business_events_payload_not_empty
        check (
            length(trim(payload)) > 0
        )
);

-- Migration for existing databases
alter table public.business_events
    add column if not exists status text not null default 'pending';


-- ============================================================
-- Indexes
-- ============================================================

create index if not exists idx_business_events_business_sequence
on public.business_events (
    business_id,
    sequence_id
);


create index if not exists idx_business_events_business_created
on public.business_events (
    business_id,
    created_at
);


create index if not exists idx_business_events_document
on public.business_events (
    document_key,
    chunk_index
);


create index if not exists idx_business_events_type
on public.business_events (
    business_id,
    event_type
);


-- Index for finding pending events efficiently
create index if not exists idx_business_events_pending
on public.business_events (
    business_id,
    status,
    sequence_id
)
where status = 'pending';


-- Index for bulk update by document_key
create index if not exists idx_business_events_document_status
on public.business_events (
    business_id,
    document_key,
    status
);