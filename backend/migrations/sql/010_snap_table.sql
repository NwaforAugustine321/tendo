create table if not exists snaps (
    snap_id uuid primary key,
    business_id text not null,

    type text not null,
    priority text not null,
    confidence double precision not null,

    title text not null,
    message text not null,
    why_it_matters text not null,
    action text not null,

    domain text not null default 'others',

    status text not null default 'active',

    created_at timestamptz not null default now()
);

alter table snaps
    add column if not exists domain text not null default '';

alter table snaps
    add column if not exists status text not null default 'active';

alter table snaps
    add column if not exists created_at timestamptz not null default now();

alter table snaps
    drop constraint if exists snaps_status_check;

alter table snaps
    add constraint snaps_status_check
        check (status in ('active', 'pending', 'completed'));

create index if not exists snaps_business_id_idx
    on snaps (business_id);

create index if not exists snaps_business_status_idx
    on snaps (business_id, status);

alter table snaps enable row level security;

drop policy if exists "business_scope" on snaps;

create policy "business_scope" on snaps
    for all using (
        business_id in (
            select id::text
            from business_profiles
            where user_id = auth.uid()
        )
    );
