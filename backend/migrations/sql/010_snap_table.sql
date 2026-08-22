create table snaps (
    snap_id uuid primary key,
    business_id text not null,

    type text not null,
    priority text not null,
    confidence double precision not null,

    title text not null,
    message text not null,
    why_it_matters text not null,
    action text not null,

    domain text not null default '';

    status text not null default 'active',

    created_at timestamptz not null default now()
);

create index snaps_business_id_idx
    on snaps (business_id);

create index snaps_business_status_idx
    on snaps (business_id, status);