-- Run this once after the database steps completed in the project conversation.

alter table public.inventory_items
add column if not exists manufacturer_cat_number text;

alter table public.inventory_items
add column if not exists reorder_level numeric(14,3) not null default 0
check (reorder_level >= 0);

create or replace view public.app_available_inventory
with (security_invoker = true)
as
select
    b.location_id, l.location_name, l.customer_id,
    b.item_id, i.item_code, i.item_name, i.manufacturer_cat_number,
    i.unit, i.reorder_level, b.batch_id, bt.lot_number,
    bt.catalogue_number, bt.expiry_date, b.quantity, i.runs_per_unit,
    case when i.runs_per_unit is not null
         then b.quantity * i.runs_per_unit end as estimated_runs
from public.inventory_balances b
join public.inventory_items i on i.id = b.item_id
join public.inventory_batches bt on bt.id = b.batch_id
join public.stock_locations l on l.id = b.location_id
where b.stock_state = 'available'
  and b.quantity > 0
  and (bt.expiry_date is null or bt.expiry_date >= current_date);

create or replace view public.low_stock_alerts
with (security_invoker = true)
as
select
    a.location_id,
    a.location_name,
    a.customer_id,
    a.item_id,
    a.item_code,
    a.item_name,
    a.unit,
    max(a.reorder_level) as reorder_level,
    sum(a.quantity) as available_quantity
from public.app_available_inventory a
group by a.location_id, a.location_name, a.customer_id,
         a.item_id, a.item_code, a.item_name, a.unit
having max(a.reorder_level) > 0
   and sum(a.quantity) <= max(a.reorder_level);

create or replace view public.inventory_movement_details
with (security_invoker = true)
as
select
    m.id as movement_id, m.movement_number, m.movement_type,
    m.movement_date, m.slip_number, m.reason,
    i.item_name, i.item_code, bt.lot_number, ml.quantity, i.unit,
    src.location_name as from_location,
    dest.location_name as to_location,
    ml.from_stock_state, ml.to_stock_state,
    ml.patients_served, ml.customer_usage_id
from public.inventory_movements m
join public.inventory_movement_lines ml on ml.movement_id = m.id
join public.inventory_items i on i.id = ml.item_id
join public.inventory_batches bt on bt.id = ml.batch_id
left join public.stock_locations src on src.id = ml.from_location_id
left join public.stock_locations dest on dest.id = ml.to_location_id;

create or replace function public.post_inventory_movement(
    p_movement_number text,
    p_movement_type text,
    p_movement_date timestamptz,
    p_slip_number text,
    p_reason text,
    p_item_id uuid,
    p_batch_id uuid,
    p_from_location_id uuid,
    p_to_location_id uuid,
    p_from_state text,
    p_to_state text,
    p_quantity numeric,
    p_patients_served integer default 0,
    p_customer_usage_id uuid default null
)
returns uuid
language plpgsql
security invoker
set search_path = public
as $$
declare
    new_movement_id uuid;
begin
    insert into public.inventory_movements (
        movement_number, movement_type, movement_date,
        slip_number, reason, created_by
    ) values (
        p_movement_number, p_movement_type, p_movement_date,
        nullif(p_slip_number, ''), p_reason, auth.uid()
    ) returning id into new_movement_id;

    insert into public.inventory_movement_lines (
        movement_id, item_id, batch_id,
        from_location_id, to_location_id,
        from_stock_state, to_stock_state,
        quantity, patients_served, customer_usage_id
    ) values (
        new_movement_id, p_item_id, p_batch_id,
        p_from_location_id, p_to_location_id,
        p_from_state, p_to_state,
        p_quantity, coalesce(p_patients_served, 0), p_customer_usage_id
    );

    return new_movement_id;
end;
$$;

create or replace function public.refresh_individual_kit_status()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    maximum_runs integer;
    used_runs integer;
    target_kit_id uuid;
begin
    target_kit_id := coalesce(new.individual_kit_id, old.individual_kit_id);

    select kd.runs_per_kit into maximum_runs
    from public.individual_kits k
    join public.kit_definitions kd on kd.id = k.kit_definition_id
    where k.id = target_kit_id;

    select coalesce(sum(runs_used), 0) into used_runs
    from public.kit_usage
    where individual_kit_id = target_kit_id;

    update public.individual_kits
    set status = case
        when used_runs >= maximum_runs then 'fully_used'
        when used_runs > 0 then 'partially_used'
        else 'available'
    end
    where id = target_kit_id
      and status not in ('quarantined', 'expired', 'disposed');

    return coalesce(new, old);
end;
$$;

drop trigger if exists kit_usage_refresh_status on public.kit_usage;
create trigger kit_usage_refresh_status
after insert or update or delete on public.kit_usage
for each row execute function public.refresh_individual_kit_status();

create or replace function public.alert_admins_on_backdate()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    if new.is_backdated then
        insert into public.backdate_requests (
            request_type, related_record_id, requested_event_date,
            reason, requested_by
        ) values (
            'downtime', new.id, new.started_at,
            new.backdate_reason, new.reported_by
        );

        insert into public.notifications (
            user_id, title, message, related_type, related_id
        )
        select id, 'Backdated downtime submitted',
               new.event_number || ': ' || new.title,
               'downtime', new.id
        from public.profiles
        where role = 'admin' and is_active;

        update public.downtime_events
        set admin_alerted = true
        where id = new.id;
    end if;
    return new;
end;
$$;

drop trigger if exists downtime_backdate_alert on public.downtime_events;
create trigger downtime_backdate_alert
after insert on public.downtime_events
for each row execute function public.alert_admins_on_backdate();

grant select on public.app_available_inventory to authenticated;
grant select on public.low_stock_alerts to authenticated;
grant select on public.inventory_movement_details to authenticated;
grant execute on function public.post_inventory_movement(
    text,text,timestamptz,text,text,uuid,uuid,uuid,uuid,text,text,numeric,integer,uuid
) to authenticated;
