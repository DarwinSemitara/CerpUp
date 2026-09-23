-- Custom sections and rooms for the courses page.
--
-- Run once in the Supabase SQL editor (Dashboard -> SQL Editor -> New query).
-- Until this runs, the courses page shows a setup notice and the scheduler
-- keeps using the built-in room list and the A-Z sections.

create table if not exists public.sections (
    id         uuid primary key default gen_random_uuid(),
    name       text not null,
    created_at timestamptz not null default now()
);

create unique index if not exists sections_name_key
    on public.sections (lower(name));

create table if not exists public.rooms (
    id         uuid primary key default gen_random_uuid(),
    name       text not null,
    created_at timestamptz not null default now()
);

create unique index if not exists rooms_name_key
    on public.rooms (lower(name));

-- The app reaches Supabase with the service role key, which bypasses RLS, so
-- no policies are needed. RLS stays on to keep the tables closed to the
-- anon/public key.
alter table public.sections enable row level security;
alter table public.rooms enable row level security;
