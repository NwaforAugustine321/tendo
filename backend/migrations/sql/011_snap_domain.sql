-- Snaps carry the business domain they belong to.
alter table snaps
    add column if not exists domain text not null default 'others';
