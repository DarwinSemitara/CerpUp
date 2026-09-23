-- Custom course+section+faculty blocks for one school year + semester.
--
-- Regular Course / Section / Faculty Assignment on the courses page is global.
-- Only rows in this table are term-specific. The GA does not schedule them;
-- they stay in the staging area so the admin can drag them onto the timetable.
--
-- Run once in the Supabase SQL editor.

create table if not exists public.custom_term_blocks (
    id          uuid primary key default gen_random_uuid(),
    faculty_id  uuid not null,
    course_id   uuid not null,
    section     text not null,
    units       numeric not null default 3,
    room        text,
    school_year text not null,
    semester    text not null,
    created_at  timestamptz not null default now(),
    unique (faculty_id, course_id, section, school_year, semester)
);

create index if not exists custom_term_blocks_term_idx
    on public.custom_term_blocks (school_year, semester);
create index if not exists custom_term_blocks_faculty_idx
    on public.custom_term_blocks (faculty_id);

alter table public.custom_term_blocks enable row level security;
