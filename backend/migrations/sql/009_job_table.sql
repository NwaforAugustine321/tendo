-- ============================================================
-- Background Jobs
--
-- Generic durable job queue for all background processing.
--
-- APScheduler:
--   - triggers dispatchers
--
-- PostgreSQL:
--   - owns durable job state
--   - claims jobs atomically
--   - controls retries
--   - controls retry backoff
--   - recovers stale jobs
--
-- Workers:
--   - execute the actual job logic
--   - never sleep for retry backoff
-- ============================================================


-- ============================================================
-- TABLE
-- ============================================================

create table if not exists background_jobs (

    id uuid primary key,

    job_type text not null,

    user_id uuid null,

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

    started_at timestamptz null,

    completed_at timestamptz null,

    failed_at timestamptz null,

    heartbeat_at timestamptz null,

    last_error text null,

    result jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now()
);


-- ============================================================
-- INDEXES
-- ============================================================


-- Pending jobs.
--
-- The dispatcher primarily queries this index.
--
-- Higher priority jobs are processed first.
-- Older scheduled jobs are processed before newer ones.
-- ============================================================

create index if not exists idx_background_jobs_pending
on background_jobs (
    status,
    priority desc,
    scheduled_at asc,
    created_at asc
)
where status = 'pending';


-- Jobs belonging to a business.
-- ============================================================

create index if not exists idx_background_jobs_business
on background_jobs (
    user_id,
    status,
    scheduled_at
);


-- Jobs grouped by type.
-- ============================================================

create index if not exists idx_background_jobs_type
on background_jobs (
    job_type,
    status,
    scheduled_at
);


-- Running jobs that may require stale-job recovery.
-- ============================================================

create index if not exists idx_background_jobs_stale
on background_jobs (
    heartbeat_at
)
where status = 'running';


-- Worker diagnostics.
-- ============================================================

create index if not exists idx_background_jobs_worker
on background_jobs (
    worker_name,
    status,
    updated_at
)
where worker_name is not null;


-- ============================================================
-- RETRY BACKOFF
--
-- The delay is determined by the attempt that just failed.
--
-- Attempt 1 -> 10 seconds
-- Attempt 2 -> 15 seconds
-- Attempt 3 -> 20 seconds
-- Attempt 4 -> 25 seconds
-- Attempt 5 -> 30 seconds
-- Attempt 6 -> 35 seconds
-- Attempt 7 -> 40 seconds
--
-- Attempt 8 does not retry when max_attempts = 8.
--
-- The function is shared by:
--
--   1. Normal job failures
--   2. Stale-job recovery
--
-- This keeps retry behavior consistent.
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
-- CLAIM BACKGROUND JOBS
--
-- Atomically claims pending jobs.
--
-- FOR UPDATE SKIP LOCKED is critical because multiple
-- application instances can execute this function
-- simultaneously without claiming the same job.
--
-- attempts is incremented when the job is claimed.
-- Therefore:
--
--   attempts = 1 -> first execution
--   attempts = 2 -> second execution
--   ...
--   attempts = 8 -> eighth execution
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
--
-- A stale running job represents a failed execution attempt.
--
-- If attempts remain:
--
--   running
--      ↓
--   stale
--      ↓
--   pending
--      ↓
--   retry after backoff
--
-- If no attempts remain:
--
--   running
--      ↓
--   stale
--      ↓
--   failed
--
-- The retry delay is determined by the attempt that was lost.
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
--
-- Only a running job can be completed.
-- ============================================================

create or replace function complete_background_job(
    p_job_id uuid,
    p_result jsonb default '{}'::jsonb
)
returns setof background_jobs
language plpgsql
as $$
begin

    return query

    update background_jobs bj

    set

        status = 'completed',

        result = coalesce(
            p_result,
            '{}'::jsonb
        ),

        completed_at = now(),

        heartbeat_at = null,

        updated_at = now()

    where bj.id = p_job_id

      and bj.status = 'running'

    returning bj.*;

end;
$$;


-- ============================================================
-- FAIL BACKGROUND JOB
--
-- Normal failure path.
--
-- If retry is allowed and attempts remain:
--
--     running
--        ↓
--     pending
--        ↓
--     scheduled_at = now() + backoff
--
-- Otherwise:
--
--     running
--        ↓
--     failed
--
-- The application worker never sleeps.
-- PostgreSQL schedules the next attempt.
-- ============================================================

create or replace function fail_background_job(
    p_job_id uuid,
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

    returning bj.*;

end;
$$;


-- ============================================================
-- HEARTBEAT
--
-- Only the worker that currently owns the job can update
-- its heartbeat.
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