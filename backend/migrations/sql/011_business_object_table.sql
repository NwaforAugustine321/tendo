create table if not exists business_objects (
    id uuid primary key default gen_random_uuid(),
    business_id uuid not null,
    object_type text not null,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint business_object_status_check
        check (status in (
            'active',
            'unresolved',
            'merged',
            'archived'
        ))
);


alter table business_objects
    add column if not exists status text not null default 'active';

alter table business_objects
    drop constraint if exists business_object_status_check;

alter table business_objects
    add constraint business_object_status_check
        check (status in (
            'active',
            'unresolved',
            'merged',
            'archived'
        ));


create table if not exists customers (
    id uuid primary key
        references business_objects(id)
        on delete cascade,

    name text,
    email text,
    phone text,
    external_customer_id text,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);


create table if not exists business_object_identities (
    id uuid primary key default gen_random_uuid(),

    business_id uuid not null,
    object_id uuid not null
        references business_objects(id)
        on delete cascade,

    object_type text not null,
    identifier_type text not null,
    identifier_value text not null,
    identifier_hash text not null,

    created_at timestamptz not null default now()
);


create unique index if not exists business_object_identity_unique
on business_object_identities (
    business_id,
    object_type,
    identifier_type,
    identifier_hash
);

create index if not exists business_object_identity_lookup
on business_object_identities (
    business_id,
    object_type,
    identifier_hash
);


create or replace function resolve_or_create_customer(
    p_business_id uuid,
    p_name text,
    p_email text,
    p_phone text,
    p_external_customer_id text,
    p_identities jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_identity jsonb;
    v_object_id uuid;
    v_created boolean := false;
    v_existing_ids uuid[];
    v_status text;
begin

    p_identities := coalesce(
        p_identities,
        '[]'::jsonb
    );


    /*
     * Serialize concurrent resolution attempts for the
     * same deterministic identities.
     */
    for v_identity in
        select value
        from jsonb_array_elements(p_identities)
        order by value->>'identifier_hash'
    loop

        perform pg_advisory_xact_lock(
            hashtextextended(
                concat(
                    p_business_id::text,
                    '|customer|',
                    v_identity->>'identifier_type',
                    '|',
                    v_identity->>'identifier_hash'
                ),
                0
            )
        );

    end loop;


    /*
     * Find all customers represented by the supplied identities.
     */
    select array_agg(distinct object_id)
    into v_existing_ids
    from business_object_identities
    where business_id = p_business_id
      and object_type = 'customer'
      and identifier_hash in (
          select value->>'identifier_hash'
          from jsonb_array_elements(p_identities)
      );


    /*
     * Multiple identities resolving to different customers
     * is an identity conflict.
     */
    if coalesce(array_length(v_existing_ids, 1), 0) > 1 then
        raise exception
            'Customer identity conflict: supplied identifiers belong to different customers';
    end if;


    /*
     * Existing customer.
     */
    if coalesce(array_length(v_existing_ids, 1), 0) = 1 then

        v_object_id := v_existing_ids[1];


        select status
        into v_status
        from business_objects
        where id = v_object_id
          and business_id = p_business_id
          and object_type = 'customer'
        for update;


        update customers
        set
            name = coalesce(p_name, name),
            email = coalesce(p_email, email),
            phone = coalesce(p_phone, phone),
            external_customer_id = coalesce(
                p_external_customer_id,
                external_customer_id
            ),
            updated_at = now()
        where id = v_object_id;


        update business_objects
        set
            status = 'active',
            updated_at = now()
        where id = v_object_id
          and business_id = p_business_id
          and object_type = 'customer';


        v_status := 'active';


    /*
     * No deterministic identity.
     */
    else

        v_status := case
            when jsonb_array_length(p_identities) > 0
                then 'active'
            else 'unresolved'
        end;


        insert into business_objects (
            business_id,
            object_type,
            status
        )
        values (
            p_business_id,
            'customer',
            v_status
        )
        returning id into v_object_id;


        insert into customers (
            id,
            name,
            email,
            phone,
            external_customer_id
        )
        values (
            v_object_id,
            p_name,
            p_email,
            p_phone,
            p_external_customer_id
        );


        v_created := true;

    end if;


    /*
     * Attach all discovered deterministic identities.
     */
    insert into business_object_identities (
        business_id,
        object_id,
        object_type,
        identifier_type,
        identifier_value,
        identifier_hash
    )
    select
        p_business_id,
        v_object_id,
        'customer',
        value->>'identifier_type',
        value->>'identifier_key',
        value->>'identifier_hash'
    from jsonb_array_elements(p_identities)
    on conflict (
        business_id,
        object_type,
        identifier_type,
        identifier_hash
    )
    do update
    set
        object_id = excluded.object_id,
        identifier_value = excluded.identifier_value;


    return jsonb_build_object(
        'id', v_object_id,
        'created', v_created,
        'status', v_status
    );

end;
$$;


create or replace function update_customer(
    p_business_id uuid,
    p_object_id uuid,
    p_data jsonb,
    p_identities jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_identity jsonb;
    v_customer customers%rowtype;
    v_existing_ids uuid[];
    v_status text;
begin

    p_data := coalesce(
        p_data,
        '{}'::jsonb
    );

    p_identities := coalesce(
        p_identities,
        '[]'::jsonb
    );


    /*
     * Lock the customer and verify ownership.
     */
    select customers.*
    into v_customer
    from customers
    join business_objects
        on business_objects.id = customers.id
    where customers.id = p_object_id
      and business_objects.business_id = p_business_id
      and business_objects.object_type = 'customer'
    for update;


    if v_customer.id is null then
        raise exception
            'Customer not found for business';
    end if;


    /*
     * Serialize concurrent identity updates.
     */
    for v_identity in
        select value
        from jsonb_array_elements(p_identities)
        order by value->>'identifier_hash'
    loop

        perform pg_advisory_xact_lock(
            hashtextextended(
                concat(
                    p_business_id::text,
                    '|customer|',
                    v_identity->>'identifier_type',
                    '|',
                    v_identity->>'identifier_hash'
                ),
                0
            )
        );

    end loop;


    /*
     * Make sure the supplied identities do not belong
     * to another customer.
     */
    select array_agg(distinct object_id)
    into v_existing_ids
    from business_object_identities
    where business_id = p_business_id
      and object_type = 'customer'
      and identifier_hash in (
          select value->>'identifier_hash'
          from jsonb_array_elements(p_identities)
      );


    if coalesce(array_length(v_existing_ids, 1), 0) > 0
       and (
           array_length(v_existing_ids, 1) > 1
           or v_existing_ids[1] <> p_object_id
       ) then

        raise exception
            'Customer identity conflict: supplied identifiers belong to another customer';

    end if;


    /*
     * Apply only fields supplied in p_data.
     * jsonb_populate_record preserves existing values
     * for fields that were not supplied.
     */
    v_customer := jsonb_populate_record(
        v_customer,
        p_data
    );


    update customers
    set
        name = v_customer.name,
        email = v_customer.email,
        phone = v_customer.phone,
        external_customer_id = v_customer.external_customer_id,
        updated_at = now()
    where id = p_object_id;


    /*
     * A customer becomes active once it has a deterministic identity.
     * Otherwise preserve its current status.
     */
    update business_objects
    set
        status = case
            when jsonb_array_length(p_identities) > 0
                then 'active'
            else status
        end,
        updated_at = now()
    where id = p_object_id
      and business_id = p_business_id
      and object_type = 'customer'
    returning status into v_status;


    /*
     * Attach newly discovered identities.
     */
    insert into business_object_identities (
        business_id,
        object_id,
        object_type,
        identifier_type,
        identifier_value,
        identifier_hash
    )
    select
        p_business_id,
        p_object_id,
        'customer',
        value->>'identifier_type',
        value->>'identifier_key',
        value->>'identifier_hash'
    from jsonb_array_elements(p_identities)
    on conflict (
        business_id,
        object_type,
        identifier_type,
        identifier_hash
    )
    do update
    set
        object_id = excluded.object_id,
        identifier_value = excluded.identifier_value;


    return jsonb_build_object(
        'id', p_object_id,
        'created', false,
        'updated', true,
        'status', v_status
    );

end;
$$;