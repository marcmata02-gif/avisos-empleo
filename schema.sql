-- =====================================================================
--  Base de datos de "Avisos de empleo BCN" (Supabase, plan gratuito)
--  Pega TODO este archivo en Supabase > SQL Editor > New query > Run.
--  Se puede volver a ejecutar sin perder datos.
-- =====================================================================

create table if not exists public.offers (
  id                   text primary key,
  -- datos de la oferta (tal como llegan de las fuentes)
  title                text,
  company              text,
  description          text,
  published_at         timestamptz,
  links                jsonb default '[]'::jsonb,   -- [{source, url}]
  sources              jsonb default '[]'::jsonb,
  raw_location         text,
  raw_salary           text,
  raw_contract         text,
  raw_workday          text,
  raw_modality         text,
  raw_experience       text,
  sector_hint          text,
  company_sectors      jsonb default '[]'::jsonb,
  default_location     text,
  location_prefiltered boolean default false,
  implicit_fulltime    boolean default false,
  requirements_text    text,
  -- resultado del filtro
  passes               boolean default false,
  discard_reason       text,
  area                 text,
  areas                jsonb default '[]'::jsonb,
  sector               text,
  is_graduate          boolean default false,
  flags                jsonb default '[]'::jsonb,
  flag_texts           jsonb default '[]'::jsonb,
  lang                 text,
  cv_id                int,
  cv_name              text,
  cv_note              text,
  jornada              text,
  modalidad            text,
  contrato             text,
  summary              text,
  requirements         jsonb default '[]'::jsonb,
  salario              text,
  ubicacion            text,
  priority             int default 0,
  config_hash          text,
  -- control
  first_seen           timestamptz default now(),
  last_seen            timestamptz default now(),
  aviso                text,          -- null = pendiente, enviado, solo_web, omitido_antiguo...
  aviso_at             timestamptz
);

create index if not exists offers_passes_idx on public.offers (passes, first_seen desc);
create index if not exists offers_last_seen_idx on public.offers (last_seen);
create index if not exists offers_aviso_idx on public.offers (aviso) where aviso is null;

-- Tus marcas desde la web
create table if not exists public.offer_status (
  offer_id   text primary key references public.offers(id) on delete cascade,
  status     text check (status in ('guardada', 'aplicada', 'descartada')),
  cv_used    text,
  note       text,
  updated_at timestamptz default now()
);

-- Estado de cada fuente (última revisión, errores)
create table if not exists public.source_state (
  source     text primary key,
  last_run   timestamptz,
  last_ok    timestamptz,
  last_error text,
  runs       int default 0,
  meta       jsonb default '{}'::jsonb
);

-- Personas que pueden entrar en la web (solo tú). Tu email se añade
-- a mano en el paso 4 de la guía; no se guarda en el código.
create table if not exists public.allowed_users (
  email text primary key
);

-- ---------------------------------------------------------------------
-- Seguridad: nadie puede leer nada sin iniciar sesión con un email de
-- allowed_users. El robot de GitHub usa la clave secreta (no le afecta).
-- ---------------------------------------------------------------------
alter table public.offers        enable row level security;
alter table public.offer_status  enable row level security;
alter table public.source_state  enable row level security;
alter table public.allowed_users enable row level security;

create or replace function public.is_allowed() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.allowed_users
    where lower(email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );
$$;

drop policy if exists "leer ofertas" on public.offers;
create policy "leer ofertas" on public.offers
  for select to authenticated using (public.is_allowed());

drop policy if exists "leer estados" on public.offer_status;
create policy "leer estados" on public.offer_status
  for select to authenticated using (public.is_allowed());
drop policy if exists "crear estados" on public.offer_status;
create policy "crear estados" on public.offer_status
  for insert to authenticated with check (public.is_allowed());
drop policy if exists "cambiar estados" on public.offer_status;
create policy "cambiar estados" on public.offer_status
  for update to authenticated using (public.is_allowed()) with check (public.is_allowed());
drop policy if exists "borrar estados" on public.offer_status;
create policy "borrar estados" on public.offer_status
  for delete to authenticated using (public.is_allowed());

drop policy if exists "leer fuentes" on public.source_state;
create policy "leer fuentes" on public.source_state
  for select to authenticated using (public.is_allowed());

-- allowed_users no tiene políticas: no se puede leer ni cambiar desde la web.

-- Permisos de las tablas para los roles de la API (las políticas de arriba
-- deciden qué filas se ven)
grant select on public.offers, public.source_state to authenticated;
grant select, insert, update, delete on public.offer_status to authenticated;
revoke all on public.offers, public.offer_status, public.source_state, public.allowed_users from anon;
