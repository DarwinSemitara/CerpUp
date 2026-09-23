-- Term-specific course allocation
--
-- Run once in the Supabase SQL editor (Dashboard -> SQL Editor -> New query).
-- Until this runs, the courses page still assigns globally (not per semester).
--
-- What this adds:
--   1. faculty_eligible_courses  — faculty is assigned to a COURSE (no section).
--                                  This persists across school years.
--   2. course_term_offerings     — which sections a course is offered for in a
--                                  given school year + semester (includes custom
--                                  sections such as BSCE-1A).
--   3. school_year / semester on faculty_courses — who teaches which SECTION of
--                                  an eligible course in that term.

create table if not exists public.faculty_eligible_courses (
    id         uuid primary key default gen_random_uuid(),
    faculty_id uuid not null,
    course_id  uuid not null,
    created_at timestamptz not null default now(),
    unique (faculty_id, course_id)
);

create index if not exists faculty_eligible_courses_faculty_idx
    on public.faculty_eligible_courses (faculty_id);
create index if not exists faculty_eligible_courses_course_idx
    on public.faculty_eligible_courses (course_id);

create table if not exists public.course_term_offerings (
    id                  uuid primary key default gen_random_uuid(),
    course_id           uuid not null,
    school_year         text not null,
    semester            text not null,
    available_sections  jsonb not null default '[]'::jsonb,
    updated_at          timestamptz not null default now(),
    unique (course_id, school_year, semester)
);

alter table public.faculty_courses
    add column if not exists school_year text,
    add column if not exists semester text;

-- Put existing assignments on the current school year so nothing is orphaned.
update public.faculty_courses
set school_year = coalesce(nullif(school_year, ''),
                           to_char(extract(year from now()), 'FM9999')
                           || '-' ||
                           to_char(extract(year from now()) + 1, 'FM9999')),
    semester    = coalesce(nullif(semester, ''), '1')
where school_year is null or semester is null or school_year = '';

-- Eligibility is "who can teach this course". Seed it from current assignments
-- so every faculty who already has a section stays eligible.
insert into public.faculty_eligible_courses (faculty_id, course_id)
select distinct faculty_id, course_id
from public.faculty_courses
on conflict (faculty_id, course_id) do nothing;

-- Copy today's section lists onto the current term so the first open of the
-- courses page is not empty.
insert into public.course_term_offerings
    (course_id, school_year, semester, available_sections)
select
    c.id,
    to_char(extract(year from now()), 'FM9999')
        || '-' ||
        to_char(extract(year from now()) + 1, 'FM9999'),
    '1',
    coalesce(to_jsonb(c.available_sections), '[]'::jsonb)
from public.courses c
where c.available_sections is not null
on conflict (course_id, school_year, semester) do nothing;

-- Optional FKs so the REST API can embed course rows. The app also joins in
-- Python, so this is not required if the tables already exist.
do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'faculty_eligible_courses_course_id_fkey'
    ) then
        alter table public.faculty_eligible_courses
            add constraint faculty_eligible_courses_course_id_fkey
            foreign key (course_id) references public.courses(id) on delete cascade;
    end if;
    if not exists (
        select 1 from pg_constraint
        where conname = 'course_term_offerings_course_id_fkey'
    ) then
        alter table public.course_term_offerings
            add constraint course_term_offerings_course_id_fkey
            foreign key (course_id) references public.courses(id) on delete cascade;
    end if;
end $$;

alter table public.faculty_eligible_courses enable row level security;
alter table public.course_term_offerings enable row level security;
