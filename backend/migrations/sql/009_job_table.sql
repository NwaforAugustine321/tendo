
-- ============================================================
-- Background Jobs
-- ============================================================

-- Generic durable job queue for all background processing.

-- PostgreSQL:
--   - owns durable job state
--   - claims jobs atomically
--   - controls retries
--   - controls retry backoff
--   - controls recurring scheduling
--   - recovers stale jobs

-- Workers:
--   - execute the actual job logic
--   - never sleep for retry backoff


-- ============================================================
-- INTERVAL UNIT
-- ============================================================

do $$

begin

    if not exists (

        select 1

        from pg_type

        where typname = 'background_job_interval_unit'

    ) then

        create type background_job_interval_unit as enum (

            'seconds',

            'minutes',

            'hours',

            'days',

            'weeks',

            'months',

            'years'

        );

    end if;

end;

$$;



-- ============================================================
-- TABLE
-- ============================================================

create table if not exists background_jobs (

    id uuid primary key,

    job_type text not null,

    payload jsonb not null default '{}'::jsonb,

    status text not null default 'pending'

        check (

            status in (

                'pending',

                'running',

                'completed',

                'failed',

                'cancelled'

            )

        ),

    priority integer not null default 0,

    attempts integer not null default 0,

    max_attempts integer not null default 8,

    worker_name text null,

    scheduled_at timestamptz not null default now(),

    -- ========================================================
    -- Recurring job configuration
    -- ========================================================

    interval_value integer null,

    interval_unit background_job_interval_unit null,

    started_at timestamptz null,

    completed_at timestamptz null,

    failed_at timestamptz null,

    heartbeat_at timestamptz null,

    last_error text null,

    result jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    -- Both interval fields must be supplied together.

    constraint background_jobs_interval_consistency

        check (

            (

                interval_value is null

                and interval_unit is null

            )

            or

            (

                interval_value is not null

                and interval_unit is not null

                and interval_value > 0

            )

        )

);



-- ============================================================
-- RLS POLICY
-- ============================================================

ALTER TABLE background_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_manage" ON background_jobs

    FOR ALL USING (true) WITH CHECK (true);



-- ============================================================
-- MIGRATION FOR EXISTING DATABASES
-- ============================================================

alter table background_jobs

    add column if not exists interval_value integer null;

alter table background_jobs

    add column if not exists interval_unit

        background_job_interval_unit null;



-- ============================================================
-- INDEXES
-- ============================================================

create index if not exists idx_background_jobs_pending

on background_jobs (

    status,

    priority desc,

    scheduled_at asc,

    created_at asc

)

where status = 'pending';



create index if not exists idx_background_jobs_business

on background_jobs (

    id,

    status,

    scheduled_at

);



create index if not exists idx_background_jobs_type

on background_jobs (

    job_type,

    status,

    scheduled_at

);



create index if not exists idx_background_jobs_stale

on background_jobs (

    heartbeat_at

)

where status = 'running';



create index if not exists idx_background_jobs_worker

on background_jobs (

    worker_name,

    status,

    updated_at

)

where worker_name is not null;



-- ============================================================
-- RETRY BACKOFF
-- ============================================================

create or replace function background_job_retry_delay(

    p_attempt integer

)

returns interval

language plpgsql

immutable

as $$

begin

    return make_interval(

        secs => least(

            10 + (

                (

                    greatest(

                        p_attempt,

                        1

                    ) - 1

                ) * 5

            ),

            40

        )

    );

end;

$$;



-- ============================================================
-- RECURRING JOB NEXT RUN
-- ============================================================

create or replace function background_job_next_schedule(

    p_scheduled_at timestamptz,

    p_interval_value integer,

    p_interval_unit background_job_interval_unit

)

returns timestamptz

language plpgsql

immutable

as $$

begin

    if p_interval_value is null

       or p_interval_unit is null then

        return null;

    end if;

    if p_interval_value <= 0 then

        raise exception

            'interval_value must be greater than zero';

    end if;

    case p_interval_unit

        when 'seconds' then

            return p_scheduled_at

                + make_interval(

                    secs => p_interval_value

                );

        when 'minutes' then

            return p_scheduled_at

                + make_interval(

                    mins => p_interval_value

                );

        when 'hours' then

            return p_scheduled_at

                + make_interval(

                    hours => p_interval_value

                );

        when 'days' then

            return p_scheduled_at

                + make_interval(

                    days => p_interval_value

                );

        when 'weeks' then

            return p_scheduled_at

                + make_interval(

                    days => p_interval_value * 7

                );

        when 'months' then

            return p_scheduled_at

                + make_interval(

                    months => p_interval_value

                );

        when 'years' then

            return p_scheduled_at

                + make_interval(

                    years => p_interval_value

                );

        else

            raise exception

                'Unsupported interval unit: %',

                p_interval_unit;

    end case;

end;

$$;



-- ============================================================
-- CLAIM BACKGROUND JOBS
-- ============================================================

create or replace function claim_background_jobs(

    p_worker_name text,

    p_limit integer,

    p_now timestamptz

)

returns setof background_jobs

language plpgsql

as $$

begin

    if p_limit <= 0 then

        return;

    end if;

    return query

    with candidates as (

        select bj.id

        from background_jobs bj

        where bj.status = 'pending'

          and bj.scheduled_at <= p_now

          and bj.attempts < bj.max_attempts

        order by

            bj.priority desc,

            bj.scheduled_at asc,

            bj.created_at asc

        limit p_limit

        for update skip locked

    )

    update background_jobs bj

    set

        status = 'running',

        worker_name = p_worker_name,

        attempts = bj.attempts + 1,

        started_at = coalesce(

            bj.started_at,

            p_now

        ),

        heartbeat_at = p_now,

        updated_at = p_now

    from candidates

    where bj.id = candidates.id

    returning bj.*;

end;

$$;



-- ============================================================
-- RECOVER STALE JOBS
-- ============================================================

create or replace function recover_stale_background_jobs(

    p_timeout_seconds integer

)

returns setof background_jobs

language plpgsql

as $$

begin

    if p_timeout_seconds <= 0 then

        return;

    end if;

    return query

    update background_jobs bj

    set

        status = case

            when bj.attempts < bj.max_attempts

                then 'pending'

            else 'failed'

        end,

        worker_name = null,

        heartbeat_at = null,

        last_error = coalesce(

            bj.last_error,

            'Worker heartbeat timed out'

        ),

        scheduled_at = case

            when bj.attempts < bj.max_attempts

                then now()

                     + background_job_retry_delay(

                         bj.attempts

                     )

            else bj.scheduled_at

        end,

        failed_at = case

            when bj.attempts >= bj.max_attempts

                then now()

            else null

        end,

        updated_at = now()

    where bj.status = 'running'

      and bj.heartbeat_at is not null

      and bj.heartbeat_at < (

          now()

          - make_interval(

              secs => p_timeout_seconds

          )

      )

    returning bj.*;

end;

$$;



-- ============================================================
-- COMPLETE BACKGROUND JOB
-- ============================================================

-- Remove the previous function signature so the old RPC
-- cannot remain as an overloaded function.

drop function if exists complete_background_job(uuid, jsonb);


create or replace function complete_background_job(

    p_job_id uuid,

    p_worker_name text,

    p_result jsonb default '{}'::jsonb

)

returns setof background_jobs

language plpgsql

as $$

begin

    return query

    update background_jobs bj

    set

        -- ----------------------------------------------------
        -- Recurring job:
        --
        -- running
        --    ↓
        -- pending
        --    ↓
        -- next scheduled_at
        --
        -- One-time job:
        --
        -- running
        --    ↓
        -- completed
        -- ----------------------------------------------------

        status = case

            when bj.interval_value is not null

                 and bj.interval_unit is not null

                then 'pending'

            else 'completed'

        end,

        result = coalesce(

            p_result,

            '{}'::jsonb

        ),

        completed_at = now(),

        heartbeat_at = null,

        -- A completed recurring job becomes pending again,
        -- so it no longer belongs to the worker that just
        -- completed the previous execution.

        worker_name = case

            when bj.interval_value is not null

                 and bj.interval_unit is not null

                then null

            else null

        end,

        -- Reset attempts for the next recurring execution.

        attempts = case

            when bj.interval_value is not null

                 and bj.interval_unit is not null

                then 0

            else bj.attempts

        end,

        -- Calculate the next occurrence automatically.

        scheduled_at = case

            when bj.interval_value is not null

                 and bj.interval_unit is not null

                then background_job_next_schedule(

                    bj.scheduled_at,

                    bj.interval_value,

                    bj.interval_unit

                )

            else bj.scheduled_at

        end,

        updated_at = now()

    where bj.id = p_job_id

      and bj.status = 'running'

      and bj.worker_name = p_worker_name

    returning bj.*;

end;

$$;



-- ============================================================
-- FAIL BACKGROUND JOB
-- ============================================================

-- Remove the previous function signature so the old RPC
-- cannot remain as an overloaded function.

drop function if exists fail_background_job(uuid, text, boolean);


create or replace function fail_background_job(

    p_job_id uuid,

    p_worker_name text,

    p_error text,

    p_retry boolean default true

)

returns setof background_jobs

language plpgsql

as $$

declare

    v_attempts integer;

    v_max_attempts integer;

    v_retry_delay interval;

begin

    select

        bj.attempts,

        bj.max_attempts

    into

        v_attempts,

        v_max_attempts

    from background_jobs bj

    where bj.id = p_job_id

      and bj.status = 'running'

      and bj.worker_name = p_worker_name

    for update;



    if not found then

        return;

    end if;



    v_retry_delay :=

        background_job_retry_delay(

            v_attempts

        );



    return query

    update background_jobs bj

    set

        status = case

            when p_retry

                 and bj.attempts < bj.max_attempts

                then 'pending'

            else 'failed'

        end,

        worker_name = null,

        heartbeat_at = null,

        last_error = p_error,

        scheduled_at = case

            when p_retry

                 and bj.attempts < bj.max_attempts

                then now() + v_retry_delay

            else bj.scheduled_at

        end,

        failed_at = case

            when not (

                p_retry

                and bj.attempts < bj.max_attempts

            )

                then now()

            else null

        end,

        updated_at = now()

    where bj.id = p_job_id

      and bj.status = 'running'

      and bj.worker_name = p_worker_name

    returning bj.*;

end;

$$;



-- ============================================================
-- HEARTBEAT
-- ============================================================

create or replace function heartbeat_background_job(

    p_job_id uuid,

    p_worker_name text

)

returns setof background_jobs

language plpgsql

as $$

begin

    return query

    update background_jobs bj

    set

        heartbeat_at = now(),

        updated_at = now()

    where bj.id = p_job_id

      and bj.status = 'running'

      and bj.worker_name = p_worker_name

    returning bj.*;

end;

$$;



-- ============================================================
-- BLA CURSOR
-- ============================================================

-- cursor count table

create table if not exists public.bla_cursors (

    business_id uuid primary key

        references public.business_profiles(id)

        on delete cascade,

    cursor bigint null,

    status text not null default 'processing'

        check (status in ('processing', 'completed')),

    created_at timestamptz not null

        default now(),

    updated_at timestamptz not null

        default now()

);


-- Migration for existing databases

alter table public.bla_cursors

    add column if not exists status text not null default 'processing';



create or replace function public.update_bla_cursors_updated_at()

returns trigger

language plpgsql

as $$

begin

    new.updated_at = now();

    return new;

end;

$$;



drop trigger if exists bla_cursors_updated_at

on public.bla_cursors;



create trigger bla_cursors_updated_at

before update on public.bla_cursors

for each row

execute function public.update_bla_cursors_updated_at();



create index if not exists idx_bla_cursors_business_id

on public.bla_cursors(business_id);



-- ============================================================
-- BLA Learning Checkpoints
-- ============================================================

create table if not exists public.bla_checkpoints (

    business_id uuid not null

        references public.business_profiles(id)

        on delete cascade,

    document_key uuid not null,

    last_chunk_index integer not null,

    last_sequence_id bigint not null,

    accumulated_payload text not null,

    total_chunks integer not null,

    created_at timestamptz not null

        default now(),

    updated_at timestamptz not null

        default now(),

    primary key (

        business_id,

        document_key

    ),

    constraint bla_checkpoints_chunk_index_valid

        check (last_chunk_index >= 1),

    constraint bla_checkpoints_sequence_valid

        check (last_sequence_id >= 0),

    constraint bla_checkpoints_total_chunks_valid

        check (total_chunks > 0),

    constraint bla_checkpoints_payload_not_empty

        check (length(trim(accumulated_payload)) > 0),

    constraint bla_checkpoints_chunk_within_total

        check (last_chunk_index <= total_chunks)

);



-- ============================================================
-- Updated-at trigger
-- ============================================================

create or replace function public.update_bla_checkpoints_updated_at()

returns trigger

language plpgsql

as $$

begin

    new.updated_at = now();

    return new;

end;

$$;



drop trigger if exists bla_checkpoints_updated_at

on public.bla_checkpoints;



create trigger bla_checkpoints_updated_at

before update on public.bla_checkpoints

for each row

execute function public.update_bla_checkpoints_updated_at();



-- ============================================================
-- Index
-- ============================================================

create index if not exists idx_bla_checkpoints_business

on public.bla_checkpoints (

    business_id

);



create index if not exists idx_bla_checkpoints_document

on public.bla_checkpoints (

    business_id,

    document_key

);
