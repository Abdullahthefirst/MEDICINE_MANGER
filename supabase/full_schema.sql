-- Medicine Manager: complete Supabase schema
-- Run in a NEW Supabase project's SQL Editor. Safe to rerun for schema objects and seed master data.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    full_name text not null,
    role text not null check (role in ('admin','management_viewer','hospital_staff','warehouse_staff')),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.customers (
    id uuid primary key default gen_random_uuid(),
    customer_code text not null unique,
    hospital_name text not null,
    branch_name text,
    city text,
    address text not null,
    contact_person text,
    phone text,
    email text,
    notes text,
    is_active boolean not null default true,
    created_by uuid references public.profiles(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.stock_locations (
    id uuid primary key default gen_random_uuid(),
    location_code text not null unique,
    location_name text not null,
    location_type text not null check (location_type in ('warehouse','hospital')),
    customer_id uuid references public.customers(id) on delete restrict,
    address text,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    check ((location_type = 'hospital' and customer_id is not null) or
           (location_type = 'warehouse' and customer_id is null))
);

create table if not exists public.user_location_access (
    user_id uuid not null references public.profiles(id) on delete cascade,
    location_id uuid not null references public.stock_locations(id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (user_id, location_id)
);

create table if not exists public.contracts (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid not null references public.customers(id) on delete restrict,
    contract_number text not null unique,
    start_date date not null,
    end_date date not null,
    contract_value numeric(16,2),
    status text not null default 'draft' check (status in ('draft','active','terminated','renewed','expired')),
    document_url text,
    notes text,
    created_by uuid references public.profiles(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (end_date >= start_date),
    check (contract_value is null or contract_value >= 0)
);

create table if not exists public.contract_services (
    id uuid primary key default gen_random_uuid(),
    contract_id uuid not null references public.contracts(id) on delete cascade,
    service_code text not null,
    service_name text not null,
    billing_unit text not null default 'service',
    unit_price numeric(16,2) not null default 0 check (unit_price >= 0),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    unique (contract_id, service_code)
);

create table if not exists public.customer_usage (
    id uuid primary key default gen_random_uuid(),
    usage_number text not null unique,
    customer_id uuid not null references public.customers(id) on delete restrict,
    contract_id uuid not null references public.contracts(id) on delete restrict,
    contract_service_id uuid not null references public.contract_services(id) on delete restrict,
    usage_date date not null,
    service_quantity numeric(14,3) not null check (service_quantity > 0),
    patients_served integer not null default 0 check (patients_served >= 0),
    unit_price numeric(16,2) not null check (unit_price >= 0),
    total_amount numeric(16,2) generated always as (service_quantity * unit_price) stored,
    notes text,
    created_by uuid not null references public.profiles(id),
    created_at timestamptz not null default now()
);

create table if not exists public.inventory_items (
    id uuid primary key default gen_random_uuid(),
    item_code text not null unique,
    item_name text not null,
    item_type text not null check (item_type in ('consumable','kit','kit_component','material')),
    unit text not null,
    manufacturer_cat_number text,
    origin text check (origin in ('local','international','both') or origin is null),
    runs_per_unit numeric(14,4) check (runs_per_unit is null or runs_per_unit >= 0),
    reorder_level numeric(14,3) not null default 0 check (reorder_level >= 0),
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.inventory_batches (
    id uuid primary key default gen_random_uuid(),
    item_id uuid not null references public.inventory_items(id) on delete restrict,
    lot_number text not null,
    catalogue_number text,
    received_date date,
    expiry_date date,
    supplier_name text,
    notes text,
    created_at timestamptz not null default now(),
    unique (item_id, lot_number)
);

create table if not exists public.inventory_movements (
    id uuid primary key default gen_random_uuid(),
    movement_number text not null unique,
    movement_type text not null check (movement_type in ('receipt','transfer','usage','quarantine','release','expiry','disposal','adjustment')),
    movement_date timestamptz not null default now(),
    slip_number text,
    reason text,
    created_by uuid not null references public.profiles(id),
    created_at timestamptz not null default now()
);

create table if not exists public.inventory_movement_lines (
    id uuid primary key default gen_random_uuid(),
    movement_id uuid not null references public.inventory_movements(id) on delete restrict,
    item_id uuid not null references public.inventory_items(id) on delete restrict,
    batch_id uuid not null references public.inventory_batches(id) on delete restrict,
    from_location_id uuid references public.stock_locations(id) on delete restrict,
    to_location_id uuid references public.stock_locations(id) on delete restrict,
    from_stock_state text check (from_stock_state in ('available','quarantine')),
    to_stock_state text check (to_stock_state in ('available','quarantine')),
    quantity numeric(14,3) not null check (quantity > 0),
    patients_served integer not null default 0 check (patients_served >= 0),
    customer_usage_id uuid references public.customer_usage(id) on delete restrict,
    created_at timestamptz not null default now(),
    check (from_location_id is not null or to_location_id is not null)
);

create table if not exists public.inventory_balances (
    location_id uuid not null references public.stock_locations(id) on delete restrict,
    item_id uuid not null references public.inventory_items(id) on delete restrict,
    batch_id uuid not null references public.inventory_batches(id) on delete restrict,
    stock_state text not null check (stock_state in ('available','quarantine')),
    quantity numeric(14,3) not null default 0 check (quantity >= 0),
    updated_at timestamptz not null default now(),
    primary key (location_id, item_id, batch_id, stock_state)
);

create table if not exists public.downtime_events (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid not null references public.customers(id) on delete restrict,
    event_number text not null unique,
    downtime_category text not null,
    title text not null,
    cause_details text not null,
    impact_details text,
    kit_unique_id text,
    component_name text,
    started_at timestamptz not null,
    ended_at timestamptz,
    patients_affected integer not null default 0 check (patients_affected >= 0),
    runs_lost integer not null default 0 check (runs_lost >= 0),
    services_delayed integer not null default 0 check (services_delayed >= 0),
    status text not null default 'reported' check (status in ('reported','investigating','action_required','resolved','reopened','verified','closed')),
    resolution_details text,
    corrective_action text,
    preventive_action text,
    is_backdated boolean not null default false,
    backdate_reason text,
    admin_alerted boolean not null default false,
    reported_by uuid not null references public.profiles(id),
    resolved_by uuid references public.profiles(id),
    resolved_at timestamptz,
    verified_by uuid references public.profiles(id),
    verified_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (ended_at is null or ended_at >= started_at),
    check (not is_backdated or nullif(trim(backdate_reason), '') is not null)
);

create table if not exists public.backdate_requests (
    id uuid primary key default gen_random_uuid(),
    request_type text not null,
    related_record_id uuid,
    requested_event_date timestamptz not null,
    reason text not null,
    status text not null default 'pending' check (status in ('pending','approved','rejected')),
    requested_by uuid not null references public.profiles(id),
    requested_at timestamptz not null default now(),
    reviewed_by uuid references public.profiles(id),
    reviewed_at timestamptz,
    review_notes text
);

create table if not exists public.notifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles(id) on delete cascade,
    title text not null,
    message text not null,
    related_type text,
    related_id uuid,
    is_read boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists public.kit_definitions (
    id uuid primary key default gen_random_uuid(),
    kit_name text not null unique,
    runs_per_kit integer not null check (runs_per_kit > 0),
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create table if not exists public.kit_component_requirements (
    id uuid primary key default gen_random_uuid(),
    kit_definition_id uuid not null references public.kit_definitions(id) on delete cascade,
    component_item_id uuid not null references public.inventory_items(id) on delete restrict,
    quantity_required numeric(14,3),
    notes text,
    unique (kit_definition_id, component_item_id)
);

create table if not exists public.individual_kits (
    id uuid primary key default gen_random_uuid(),
    kit_identifier text not null unique,
    kit_definition_id uuid not null references public.kit_definitions(id) on delete restrict,
    inventory_batch_id uuid references public.inventory_batches(id) on delete restrict,
    received_date date,
    expiry_date date,
    status text not null default 'available' check (status in ('available','partially_used','fully_used','quarantined','expired','disposed')),
    created_at timestamptz not null default now()
);

create table if not exists public.component_issues (
    id uuid primary key default gen_random_uuid(),
    issue_number text not null unique,
    individual_kit_id uuid not null references public.individual_kits(id) on delete restrict,
    component_item_id uuid references public.inventory_items(id) on delete restrict,
    customer_id uuid not null references public.customers(id) on delete restrict,
    issue_type text not null,
    severity text not null check (severity in ('low','medium','high','critical')),
    runs_affected integer not null default 0 check (runs_affected >= 0),
    issue_details text not null,
    status text not null default 'reported' check (status in ('reported','investigating','action_required','resolved','reopened','verified','closed')),
    resolution_details text,
    reported_by uuid not null references public.profiles(id),
    reported_at timestamptz not null default now(),
    resolved_by uuid references public.profiles(id),
    resolved_at timestamptz,
    verified_by uuid references public.profiles(id),
    verified_at timestamptz,
    updated_at timestamptz not null default now()
);

create table if not exists public.component_issue_actions (
    id uuid primary key default gen_random_uuid(),
    component_issue_id uuid not null references public.component_issues(id) on delete cascade,
    action_type text not null,
    action_details text not null,
    quantity numeric(14,3),
    evidence_url text,
    performed_by uuid not null references public.profiles(id),
    performed_at timestamptz not null default now()
);

create table if not exists public.kit_usage (
    id uuid primary key default gen_random_uuid(),
    individual_kit_id uuid not null references public.individual_kits(id) on delete restrict,
    customer_usage_id uuid not null references public.customer_usage(id) on delete restrict,
    runs_used integer not null check (runs_used > 0),
    created_by uuid not null references public.profiles(id),
    created_at timestamptz not null default now()
);

create table if not exists public.invoices (
    id uuid primary key default gen_random_uuid(),
    invoice_number text not null unique,
    customer_id uuid not null references public.customers(id) on delete restrict,
    contract_id uuid not null references public.contracts(id) on delete restrict,
    billing_period_start date not null,
    billing_period_end date not null,
    issue_date date not null,
    due_date date not null,
    status text not null default 'draft' check (status in ('draft','issued','cancelled','paid')),
    notes text,
    created_by uuid not null references public.profiles(id),
    created_at timestamptz not null default now(),
    check (billing_period_end >= billing_period_start),
    check (due_date >= issue_date)
);

create table if not exists public.invoice_items (
    id uuid primary key default gen_random_uuid(),
    invoice_id uuid not null references public.invoices(id) on delete cascade,
    customer_usage_id uuid references public.customer_usage(id) on delete restrict,
    description text not null,
    quantity numeric(14,3) not null check (quantity > 0),
    unit_price numeric(16,2) not null check (unit_price >= 0),
    line_total numeric(16,2) generated always as (quantity * unit_price) stored,
    is_void boolean not null default false,
    created_at timestamptz not null default now(),
    unique (invoice_id, customer_usage_id)
);

create table if not exists public.payments (
    id uuid primary key default gen_random_uuid(),
    payment_number text not null unique,
    invoice_id uuid not null references public.invoices(id) on delete restrict,
    payment_date date not null,
    amount numeric(16,2) not null check (amount > 0),
    payment_method text not null,
    reference_number text,
    status text not null default 'recorded' check (status in ('recorded','reversed')),
    notes text,
    created_by uuid not null references public.profiles(id),
    created_at timestamptz not null default now()
);

create table if not exists public.audit_logs (
    id bigint generated always as identity primary key,
    actor_id uuid references public.profiles(id),
    table_name text not null,
    record_id uuid,
    action text not null,
    old_data jsonb,
    new_data jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_contracts_customer on public.contracts(customer_id);
create index if not exists idx_usage_customer_date on public.customer_usage(customer_id, usage_date);
create index if not exists idx_batches_expiry on public.inventory_batches(expiry_date);
create index if not exists idx_movement_lines_batch on public.inventory_movement_lines(batch_id);
create index if not exists idx_downtime_customer_start on public.downtime_events(customer_id, started_at);
create index if not exists idx_component_issues_customer on public.component_issues(customer_id, status);
create index if not exists idx_notifications_user on public.notifications(user_id, is_read);

-- Security helpers
create or replace function public.current_app_role() returns text
language sql stable security definer set search_path = public
as $$ select role from public.profiles where id = auth.uid() and is_active $$;

create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public
as $$ select coalesce(public.current_app_role() = 'admin', false) $$;

create or replace function public.can_view_all() returns boolean
language sql stable security definer set search_path = public
as $$ select coalesce(public.current_app_role() in ('admin','management_viewer'), false) $$;

create or replace function public.has_location(p_location uuid) returns boolean
language sql stable security definer set search_path = public
as $$ select public.can_view_all() or exists (
    select 1 from public.user_location_access a where a.user_id = auth.uid() and a.location_id = p_location
) $$;

create or replace function public.has_customer(p_customer uuid) returns boolean
language sql stable security definer set search_path = public
as $$ select public.can_view_all() or exists (
    select 1 from public.user_location_access a
    join public.stock_locations l on l.id = a.location_id
    where a.user_id = auth.uid() and l.customer_id = p_customer
) $$;

-- Inventory ledger: validate a line and adjust calculated balances.
create or replace function public.apply_inventory_movement_line() returns trigger
language plpgsql security definer set search_path = public as $$
declare source_qty numeric; batch_item uuid; actor_role text;
begin
    select item_id into batch_item from public.inventory_batches where id = new.batch_id;
    if batch_item is distinct from new.item_id then raise exception 'Batch does not belong to item'; end if;
    actor_role := public.current_app_role();
    if actor_role not in ('admin','hospital_staff','warehouse_staff') then raise exception 'Role cannot post inventory'; end if;
    if actor_role <> 'admin' then
        if new.from_location_id is not null and not public.has_location(new.from_location_id) then
            raise exception 'No access to source location';
        end if;
        if new.from_location_id is null and (new.to_location_id is null or not public.has_location(new.to_location_id)) then
            raise exception 'No access to receiving location';
        end if;
    end if;
    if new.from_location_id is not null then
        select quantity into source_qty from public.inventory_balances
        where location_id = new.from_location_id and item_id = new.item_id
          and batch_id = new.batch_id and stock_state = new.from_stock_state for update;
        if coalesce(source_qty, 0) < new.quantity then raise exception 'Insufficient stock'; end if;
        update public.inventory_balances set quantity = quantity - new.quantity, updated_at = now()
        where location_id = new.from_location_id and item_id = new.item_id
          and batch_id = new.batch_id and stock_state = new.from_stock_state;
    end if;
    if new.to_location_id is not null then
        insert into public.inventory_balances(location_id,item_id,batch_id,stock_state,quantity)
        values(new.to_location_id,new.item_id,new.batch_id,new.to_stock_state,new.quantity)
        on conflict(location_id,item_id,batch_id,stock_state)
        do update set quantity = public.inventory_balances.quantity + excluded.quantity, updated_at = now();
    end if;
    return new;
end $$;

drop trigger if exists movement_line_apply_balance on public.inventory_movement_lines;
create trigger movement_line_apply_balance before insert on public.inventory_movement_lines
for each row execute function public.apply_inventory_movement_line();

create or replace function public.post_inventory_movement(
    p_movement_number text, p_movement_type text, p_movement_date timestamptz,
    p_slip_number text, p_reason text, p_item_id uuid, p_batch_id uuid,
    p_from_location_id uuid, p_to_location_id uuid, p_from_state text,
    p_to_state text, p_quantity numeric, p_patients_served integer default 0,
    p_customer_usage_id uuid default null
) returns uuid language plpgsql security invoker set search_path = public as $$
declare new_movement_id uuid;
begin
    insert into public.inventory_movements(movement_number,movement_type,movement_date,slip_number,reason,created_by)
    values(p_movement_number,p_movement_type,p_movement_date,nullif(p_slip_number,''),p_reason,auth.uid())
    returning id into new_movement_id;
    insert into public.inventory_movement_lines(
        movement_id,item_id,batch_id,from_location_id,to_location_id,from_stock_state,
        to_stock_state,quantity,patients_served,customer_usage_id
    ) values (
        new_movement_id,p_item_id,p_batch_id,p_from_location_id,p_to_location_id,p_from_state,
        p_to_state,p_quantity,coalesce(p_patients_served,0),p_customer_usage_id
    );
    return new_movement_id;
end $$;

create or replace function public.validate_customer_usage() returns trigger
language plpgsql set search_path = public as $$
begin
    if not exists (select 1 from public.contracts c where c.id=new.contract_id and c.customer_id=new.customer_id and new.usage_date between c.start_date and c.end_date) then
        raise exception 'Usage date is outside this customer contract';
    end if;
    if not exists (select 1 from public.contract_services s where s.id=new.contract_service_id and s.contract_id=new.contract_id and s.is_active) then
        raise exception 'Service does not belong to contract';
    end if;
    return new;
end $$;
drop trigger if exists customer_usage_validate on public.customer_usage;
create trigger customer_usage_validate before insert or update on public.customer_usage
for each row execute function public.validate_customer_usage();

create or replace function public.validate_kit_usage() returns trigger
language plpgsql set search_path = public as $$
declare allowed_runs integer; already_used integer;
begin
    select d.runs_per_kit into allowed_runs from public.individual_kits k
    join public.kit_definitions d on d.id=k.kit_definition_id where k.id=new.individual_kit_id;
    select coalesce(sum(runs_used),0) into already_used from public.kit_usage
    where individual_kit_id=new.individual_kit_id and id<>coalesce(new.id,gen_random_uuid());
    if already_used + new.runs_used > allowed_runs then raise exception 'Runs exceed remaining kit capacity'; end if;
    return new;
end $$;
drop trigger if exists kit_usage_validate on public.kit_usage;
create trigger kit_usage_validate before insert or update on public.kit_usage
for each row execute function public.validate_kit_usage();

create or replace function public.refresh_individual_kit_status() returns trigger
language plpgsql security definer set search_path = public as $$
declare maximum_runs integer; used_runs integer; target_kit_id uuid;
begin
    target_kit_id := coalesce(new.individual_kit_id, old.individual_kit_id);
    select d.runs_per_kit into maximum_runs from public.individual_kits k
    join public.kit_definitions d on d.id=k.kit_definition_id where k.id=target_kit_id;
    select coalesce(sum(runs_used),0) into used_runs from public.kit_usage where individual_kit_id=target_kit_id;
    update public.individual_kits set status=case when used_runs>=maximum_runs then 'fully_used'
        when used_runs>0 then 'partially_used' else 'available' end
    where id=target_kit_id and status not in ('quarantined','expired','disposed');
    return coalesce(new,old);
end $$;
drop trigger if exists kit_usage_refresh_status on public.kit_usage;
create trigger kit_usage_refresh_status after insert or update or delete on public.kit_usage
for each row execute function public.refresh_individual_kit_status();

create or replace function public.alert_admins_on_backdate() returns trigger
language plpgsql security definer set search_path = public as $$
begin
    if new.is_backdated then
        insert into public.backdate_requests(request_type,related_record_id,requested_event_date,reason,requested_by)
        values('downtime',new.id,new.started_at,new.backdate_reason,new.reported_by);
        insert into public.notifications(user_id,title,message,related_type,related_id)
        select id,'Backdated downtime submitted',new.event_number || ': ' || new.title,'downtime',new.id
        from public.profiles where role='admin' and is_active;
        update public.downtime_events set admin_alerted=true where id=new.id;
    end if;
    return new;
end $$;
drop trigger if exists downtime_backdate_alert on public.downtime_events;
create trigger downtime_backdate_alert after insert on public.downtime_events
for each row execute function public.alert_admins_on_backdate();

-- Reporting views
create or replace view public.current_contracts with (security_invoker=true) as
select c.*, case when c.status in ('terminated','renewed') then c.status
    when current_date<c.start_date then 'upcoming' when current_date>c.end_date then 'expired'
    else c.status end as current_status,
    c.end_date-current_date as days_remaining
from public.contracts c;

create or replace view public.app_available_inventory with (security_invoker=true) as
select b.location_id,l.location_name,l.customer_id,b.item_id,i.item_code,i.item_name,
    i.manufacturer_cat_number,i.unit,i.reorder_level,b.batch_id,bt.lot_number,
    bt.catalogue_number,bt.expiry_date,b.quantity,i.runs_per_unit,
    case when i.runs_per_unit is not null then b.quantity*i.runs_per_unit end estimated_runs
from public.inventory_balances b join public.inventory_items i on i.id=b.item_id
join public.inventory_batches bt on bt.id=b.batch_id join public.stock_locations l on l.id=b.location_id
where b.stock_state='available' and b.quantity>0 and (bt.expiry_date is null or bt.expiry_date>=current_date);

create or replace view public.expiry_alerts with (security_invoker=true) as
select a.*, (a.expiry_date-current_date) days_until_expiry from public.app_available_inventory a
where a.expiry_date is not null and a.expiry_date < current_date+60;

create or replace view public.low_stock_alerts with (security_invoker=true) as
select a.location_id,a.location_name,a.customer_id,a.item_id,a.item_code,a.item_name,a.unit,
    max(a.reorder_level) reorder_level,sum(a.quantity) available_quantity
from public.app_available_inventory a group by a.location_id,a.location_name,a.customer_id,
    a.item_id,a.item_code,a.item_name,a.unit
having max(a.reorder_level)>0 and sum(a.quantity)<=max(a.reorder_level);

create or replace view public.inventory_working_days with (security_invoker=true) as
with available as (
    select location_id,item_id,sum(quantity) available_quantity from public.app_available_inventory group by 1,2
), used as (
    select ml.from_location_id location_id,ml.item_id,sum(ml.quantity) quantity_used_last_30_days
    from public.inventory_movement_lines ml join public.inventory_movements m on m.id=ml.movement_id
    where m.movement_type='usage' and m.movement_date>=now()-interval '30 days' group by 1,2
)
select a.location_id,l.location_name,a.item_id,i.item_name,a.available_quantity,
    coalesce(u.quantity_used_last_30_days,0) quantity_used_last_30_days,
    round(coalesce(u.quantity_used_last_30_days,0)/30.0,3) average_daily_usage,
    case when coalesce(u.quantity_used_last_30_days,0)>0 then round(a.available_quantity/(u.quantity_used_last_30_days/30.0),1) end estimated_working_days
from available a join public.stock_locations l on l.id=a.location_id join public.inventory_items i on i.id=a.item_id
left join used u on u.location_id=a.location_id and u.item_id=a.item_id;

create or replace view public.downtime_event_details with (security_invoker=true) as
select d.*, c.hospital_name,c.branch_name,
    round(extract(epoch from (coalesce(d.ended_at,now())-d.started_at))/3600.0,2) duration_hours
from public.downtime_events d join public.customers c on c.id=d.customer_id;

create or replace view public.customer_monthly_downtime with (security_invoker=true) as
select d.customer_id,d.hospital_name,d.branch_name,date_trunc('month',d.started_at)::date month_start,
    count(*) downtime_events,round(sum(d.duration_hours),2) downtime_hours,
    sum(d.runs_lost) runs_lost,sum(d.patients_affected) patients_affected
from public.downtime_event_details d group by 1,2,3,4;

create or replace view public.customer_delivery_history with (security_invoker=true) as
select dest.customer_id,m.movement_number,m.movement_date,m.slip_number,
    src.location_name warehouse_name,dest.location_name destination_name,i.item_name,
    bt.lot_number,bt.expiry_date,ml.quantity,i.unit
from public.inventory_movement_lines ml join public.inventory_movements m on m.id=ml.movement_id
join public.stock_locations dest on dest.id=ml.to_location_id
left join public.stock_locations src on src.id=ml.from_location_id
join public.inventory_items i on i.id=ml.item_id join public.inventory_batches bt on bt.id=ml.batch_id
where m.movement_type='transfer' and dest.customer_id is not null;

create or replace view public.inventory_movement_details with (security_invoker=true) as
select m.id movement_id,m.movement_number,m.movement_type,m.movement_date,m.slip_number,m.reason,
    i.item_name,i.item_code,bt.lot_number,ml.quantity,i.unit,
    src.location_name from_location,dest.location_name to_location,
    ml.from_stock_state,ml.to_stock_state,ml.patients_served,ml.customer_usage_id
from public.inventory_movements m join public.inventory_movement_lines ml on ml.movement_id=m.id
join public.inventory_items i on i.id=ml.item_id join public.inventory_batches bt on bt.id=ml.batch_id
left join public.stock_locations src on src.id=ml.from_location_id
left join public.stock_locations dest on dest.id=ml.to_location_id;

create or replace view public.customer_quarterly_statistics with (security_invoker=true) as
with u as (
    select customer_id,date_trunc('quarter',usage_date)::date quarter_start,
        sum(service_quantity) services_provided,sum(patients_served) patients_served,sum(total_amount) sales_value
    from public.customer_usage group by 1,2
), d as (
    select customer_id,date_trunc('quarter',started_at)::date quarter_start,
        sum(duration_hours) downtime_hours,sum(runs_lost) runs_lost
    from public.downtime_event_details group by 1,2
), keys as (select customer_id,quarter_start from u union select customer_id,quarter_start from d)
select c.id customer_id,c.hospital_name,c.branch_name,k.quarter_start,
    coalesce(u.services_provided,0) services_provided,coalesce(u.patients_served,0) patients_served,
    coalesce(u.sales_value,0) sales_value,round(coalesce(d.downtime_hours,0),2) downtime_hours,
    coalesce(d.runs_lost,0) runs_lost
from keys k join public.customers c on c.id=k.customer_id
left join u on u.customer_id=k.customer_id and u.quarter_start=k.quarter_start
left join d on d.customer_id=k.customer_id and d.quarter_start=k.quarter_start;

create or replace view public.invoice_balances with (security_invoker=true) as
select i.id invoice_id,i.invoice_number,i.customer_id,i.contract_id,i.issue_date,i.due_date,i.status,
    coalesce(lines.invoice_total,0) invoice_total,coalesce(paid.amount_paid,0) amount_paid,
    greatest(coalesce(lines.invoice_total,0)-coalesce(paid.amount_paid,0),0) outstanding_amount,
    case when i.status='cancelled' then 'cancelled'
         when coalesce(lines.invoice_total,0)<=coalesce(paid.amount_paid,0) and coalesce(lines.invoice_total,0)>0 then 'paid'
         when current_date>i.due_date and coalesce(lines.invoice_total,0)>coalesce(paid.amount_paid,0) then 'overdue'
         when coalesce(paid.amount_paid,0)>0 then 'partially_paid' else i.status end calculated_status
from public.invoices i
left join (select invoice_id,sum(line_total) invoice_total from public.invoice_items where not is_void group by 1) lines on lines.invoice_id=i.id
left join (select invoice_id,sum(amount) amount_paid from public.payments where status='recorded' group by 1) paid on paid.invoice_id=i.id;

create or replace view public.kit_run_balances with (security_invoker=true) as
select k.id individual_kit_id,k.kit_identifier,d.kit_name,d.runs_per_kit,
    coalesce(sum(u.runs_used),0)::integer runs_used,
    greatest(d.runs_per_kit-coalesce(sum(u.runs_used),0),0)::integer runs_remaining,k.status
from public.individual_kits k join public.kit_definitions d on d.id=k.kit_definition_id
left join public.kit_usage u on u.individual_kit_id=k.id group by 1,2,3,4,7;

create or replace view public.customer_management_overview with (security_invoker=true) as
with q as (
    select * from public.customer_quarterly_statistics where quarter_start=date_trunc('quarter',current_date)::date
), inv as (
    select customer_id,count(distinct batch_id) available_batches from public.app_available_inventory where customer_id is not null group by 1
), issues as (
    select customer_id,count(*) open_component_issues from public.component_issues where status not in ('verified','closed') group by 1
)
select c.id customer_id,c.customer_code,c.hospital_name,c.branch_name,
    coalesce(q.sales_value,0) quarter_sales,coalesce(q.patients_served,0) quarter_patients,
    coalesce(q.downtime_hours,0) quarter_downtime_hours,coalesce(q.runs_lost,0) quarter_runs_lost,
    coalesce(inv.available_batches,0) available_batches,coalesce(issues.open_component_issues,0) open_component_issues
from public.customers c left join q on q.customer_id=c.id left join inv on inv.customer_id=c.id
left join issues on issues.customer_id=c.id where c.is_active;

-- Row-level security
do $$ declare t text; begin
    foreach t in array array['profiles','customers','stock_locations','user_location_access','contracts','contract_services',
        'customer_usage','inventory_items','inventory_batches','inventory_movements','inventory_movement_lines',
        'inventory_balances','downtime_events','backdate_requests','notifications','kit_definitions',
        'kit_component_requirements','individual_kits','component_issues','component_issue_actions','kit_usage',
        'invoices','invoice_items','payments','audit_logs'] loop
        execute format('alter table public.%I enable row level security',t);
    end loop;
end $$;

-- Recreate named policies so reruns stay predictable.
do $$ declare r record; begin
    for r in select schemaname,tablename,policyname from pg_policies where schemaname='public' loop
        execute format('drop policy if exists %I on %I.%I',r.policyname,r.schemaname,r.tablename);
    end loop;
end $$;

create policy profiles_self_read on public.profiles for select using (id=auth.uid() or public.is_admin());
create policy profiles_admin_write on public.profiles for all using (public.is_admin()) with check (public.is_admin());
create policy customers_read on public.customers for select using (public.has_customer(id) or public.current_app_role()='warehouse_staff');
create policy customers_admin_write on public.customers for all using (public.is_admin()) with check (public.is_admin());
create policy locations_read on public.stock_locations for select using (public.current_app_role() is not null);
create policy locations_admin_write on public.stock_locations for all using (public.is_admin()) with check (public.is_admin());
create policy access_self_read on public.user_location_access for select using (user_id=auth.uid() or public.is_admin());
create policy access_admin_write on public.user_location_access for all using (public.is_admin()) with check (public.is_admin());
create policy contracts_read on public.contracts for select using (public.has_customer(customer_id));
create policy contracts_admin_write on public.contracts for all using (public.is_admin()) with check (public.is_admin());
create policy services_read on public.contract_services for select using (exists(select 1 from public.contracts c where c.id=contract_id and public.has_customer(c.customer_id)));
create policy services_admin_write on public.contract_services for all using (public.is_admin()) with check (public.is_admin());
create policy usage_read on public.customer_usage for select using (public.has_customer(customer_id));
create policy usage_insert on public.customer_usage for insert with check (public.current_app_role() in ('admin','hospital_staff') and public.has_customer(customer_id) and created_by=auth.uid());
create policy catalogue_read on public.inventory_items for select using (public.current_app_role() is not null);
create policy catalogue_admin_write on public.inventory_items for all using (public.is_admin()) with check (public.is_admin());
create policy batches_read on public.inventory_batches for select using (public.current_app_role() is not null);
create policy batches_operational_insert on public.inventory_batches for insert with check (public.current_app_role() in ('admin','warehouse_staff'));
create policy batches_operational_update on public.inventory_batches for update using (public.current_app_role() in ('admin','warehouse_staff'));
create policy movements_read on public.inventory_movements for select using (public.current_app_role() is not null);
create policy movements_insert on public.inventory_movements for insert with check (public.current_app_role() in ('admin','hospital_staff','warehouse_staff') and created_by=auth.uid());
create policy movement_lines_read on public.inventory_movement_lines for select using (public.current_app_role() is not null);
create policy movement_lines_insert on public.inventory_movement_lines for insert with check (public.current_app_role() in ('admin','hospital_staff','warehouse_staff'));
create policy balances_read on public.inventory_balances for select using (public.has_location(location_id));
create policy downtime_read on public.downtime_events for select using (public.has_customer(customer_id) or public.current_app_role()='warehouse_staff');
create policy downtime_insert on public.downtime_events for insert with check (public.current_app_role() in ('admin','hospital_staff','warehouse_staff') and (public.has_customer(customer_id) or public.current_app_role()='warehouse_staff') and reported_by=auth.uid());
create policy downtime_update on public.downtime_events for update using (public.is_admin() or (public.has_customer(customer_id) and public.current_app_role()='hospital_staff') or public.current_app_role()='warehouse_staff');
create policy backdates_read on public.backdate_requests for select using (public.is_admin() or requested_by=auth.uid());
create policy backdates_admin_update on public.backdate_requests for update using (public.is_admin());
create policy notifications_own on public.notifications for select using (user_id=auth.uid());
create policy kit_defs_read on public.kit_definitions for select using (public.current_app_role() is not null);
create policy kit_defs_admin on public.kit_definitions for all using (public.is_admin()) with check (public.is_admin());
create policy kit_requirements_read on public.kit_component_requirements for select using (public.current_app_role() is not null);
create policy kit_requirements_admin on public.kit_component_requirements for all using (public.is_admin()) with check (public.is_admin());
create policy individual_kits_read on public.individual_kits for select using (public.current_app_role() is not null);
create policy individual_kits_admin on public.individual_kits for all using (public.is_admin()) with check (public.is_admin());
create policy issues_read on public.component_issues for select using (public.has_customer(customer_id));
create policy issues_insert on public.component_issues for insert with check (public.current_app_role() in ('admin','hospital_staff','warehouse_staff') and public.has_customer(customer_id) and reported_by=auth.uid());
create policy issues_update on public.component_issues for update using (public.is_admin() or (public.has_customer(customer_id) and public.current_app_role() in ('hospital_staff','warehouse_staff')));
create policy actions_read on public.component_issue_actions for select using (exists(select 1 from public.component_issues i where i.id=component_issue_id and public.has_customer(i.customer_id)));
create policy actions_insert on public.component_issue_actions for insert with check (public.current_app_role() in ('admin','hospital_staff','warehouse_staff') and performed_by=auth.uid());
create policy kit_usage_read on public.kit_usage for select using (public.current_app_role() is not null);
create policy kit_usage_insert on public.kit_usage for insert with check (public.current_app_role() in ('admin','hospital_staff') and created_by=auth.uid());
create policy invoices_read on public.invoices for select using (public.has_customer(customer_id));
create policy invoices_insert on public.invoices for insert with check (public.current_app_role() in ('admin','hospital_staff') and public.has_customer(customer_id) and created_by=auth.uid());
create policy invoices_admin_update on public.invoices for update using (public.is_admin()) with check (public.is_admin());
create policy invoice_items_read on public.invoice_items for select using (exists(select 1 from public.invoices i where i.id=invoice_id and public.has_customer(i.customer_id)));
create policy invoice_items_insert on public.invoice_items for insert with check (exists(select 1 from public.invoices i where i.id=invoice_id and public.has_customer(i.customer_id)));
create policy payments_read on public.payments for select using (exists(select 1 from public.invoices i where i.id=invoice_id and public.has_customer(i.customer_id)));
create policy payments_insert on public.payments for insert with check (public.current_app_role() in ('admin','hospital_staff') and created_by=auth.uid());
create policy audit_admin_read on public.audit_logs for select using (public.is_admin());

grant usage on schema public to authenticated;
grant select,insert,update on all tables in schema public to authenticated;
grant usage,select on all sequences in schema public to authenticated;
grant execute on function public.post_inventory_movement(text,text,timestamptz,text,text,uuid,uuid,uuid,uuid,text,text,numeric,integer,uuid) to authenticated;

-- Starter master data. Manufacturer catalogue numbers supplied by the project owner are preserved.
insert into public.customers(customer_code,hospital_name,branch_name,city,address)
values ('AKH-KHI','Aga Khan University Hospital','Karachi','Karachi','Karachi'),
       ('DUHS-KHI','Dow University of Health Sciences','Karachi','Karachi','Karachi'),
       ('JPMC-KHI','Jinnah Postgraduate Medical Centre','Karachi','Karachi','Karachi')
on conflict(customer_code) do update set hospital_name=excluded.hospital_name;

insert into public.stock_locations(location_code,location_name,location_type,address)
values ('NSW-KHI','National Stadium Warehouse','warehouse','National Stadium, Karachi')
on conflict(location_code) do update set location_name=excluded.location_name;

insert into public.stock_locations(location_code,location_name,location_type,customer_id,address)
select c.customer_code||'-STORE',c.hospital_name||coalesce(' — '||nullif(c.branch_name,''),''),'hospital',c.id,c.address
from public.customers c where c.customer_code in ('AKH-KHI','DUHS-KHI','JPMC-KHI')
on conflict(location_code) do update set customer_id=excluded.customer_id,location_name=excluded.location_name;

insert into public.inventory_items(item_code,item_name,item_type,unit,manufacturer_cat_number,origin,runs_per_unit)
values
('CMP-12759-DUAL','Cassette of Dual','kit_component','piece','12759','international',null),
('CMP-15115','Reagent Kit of Dual','kit_component','piece','15115','international',null),
('CMP-12759-QUAD','Cassette of Quad','kit_component','piece','12759','international',null),
('CMP-14225','Reagent Kit of Quad','kit_component','piece','14225','international',null),
('CMP-MANNOSE','Mannose','kit_component','unit',null,'international',null),
('CMP-WFI','Water for Injection (WFI)','kit_component','ml',null,'both',null),
('CMP-12144','Venting Filter with Needles','kit_component','piece','12144','international',null),
('CMP-1785','0.22 Micrometre Sterilizing Filter','kit_component','piece','1785','international',null),
('CMP-11665','25 ml Sterile Non-evacuated Vial with Crimped Cap','kit_component','piece','11665','international',null),
('CMP-2132','Spike: Metal Sampling B. Braun','kit_component','piece','2132','international',null),
('MAT-O18','O18 Water','material','ml',null,'international',0.4),
('KIT-FDG-DUAL','FDG-DUAL','kit','kit',null,'international',2),
('KIT-FDG-QUAD','FDG-QUAD','kit','kit',null,'international',4),
('KIT-F-PSMA','F-PSMA','kit','kit',null,null,null),
('KIT-F-NOTA','F-NOTA','kit','kit',null,null,null),
('KIT-LU177-PSMA','LU177-PSMA','kit','kit',null,null,null),
('KIT-LU177-DOTATATE','LU177-DOTATATE','kit','kit',null,null,null)
on conflict(item_code) do update set item_name=excluded.item_name,
manufacturer_cat_number=coalesce(public.inventory_items.manufacturer_cat_number,excluded.manufacturer_cat_number);

insert into public.kit_definitions(kit_name,runs_per_kit)
values ('FDG-DUAL',2),('FDG-QUAD',4)
on conflict(kit_name) do update set runs_per_kit=excluded.runs_per_kit;

insert into public.kit_component_requirements(kit_definition_id,component_item_id,quantity_required,notes)
select kd.id,i.id,v.qty,v.note from (values
('FDG-DUAL','CMP-12759-DUAL',1::numeric,null::text),('FDG-DUAL','CMP-15115',1,null),
('FDG-DUAL','CMP-MANNOSE',null,'Quantity to be confirmed'),('FDG-DUAL','CMP-WFI',500,'ml'),
('FDG-DUAL','CMP-12144',1,null),('FDG-DUAL','CMP-1785',1,null),('FDG-DUAL','CMP-11665',1,null),('FDG-DUAL','CMP-2132',1,null),
('FDG-QUAD','CMP-12759-QUAD',1,null),('FDG-QUAD','CMP-14225',1,null),
('FDG-QUAD','CMP-MANNOSE',null,'Quantity to be confirmed'),('FDG-QUAD','CMP-WFI',1000,'ml'),
('FDG-QUAD','CMP-12144',1,null),('FDG-QUAD','CMP-1785',1,null),('FDG-QUAD','CMP-11665',1,null),('FDG-QUAD','CMP-2132',1,null)
) v(kit,item,qty,note)
join public.kit_definitions kd on kd.kit_name=v.kit join public.inventory_items i on i.item_code=v.item
on conflict(kit_definition_id,component_item_id) do update set quantity_required=excluded.quantity_required,notes=excluded.notes;

-- Create the first Auth user in Supabase Authentication, then run (replace both values):
-- insert into public.profiles(id,full_name,role) values ('AUTH-USER-UUID','Administrator','admin');
-- Assign local staff after creating their profile:
-- insert into public.user_location_access(user_id,location_id) values ('AUTH-USER-UUID','LOCATION-UUID');
