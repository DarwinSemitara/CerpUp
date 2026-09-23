-- Allow two or more faculty to teach the same course+section
-- (they meet at different times). Unique per faculty, not globally.
--
-- Run once in the Supabase SQL editor. Needed if assign fails with:
--   duplicate key value violates unique constraint
--   "faculty_courses_course_id_section_key"

alter table public.faculty_courses
    drop constraint if exists faculty_courses_course_id_section_key;

drop index if exists public.faculty_courses_course_id_section_key;

do $$
declare
  rec record;
begin
  for rec in
    select c.conname, array_agg(a.attname order by u.ord) as cols
    from pg_constraint c
    join unnest(c.conkey) with ordinality as u(attnum, ord) on true
    join pg_attribute a on a.attrelid = c.conrelid and a.attnum = u.attnum
    where c.conrelid = 'public.faculty_courses'::regclass
      and c.contype = 'u'
    group by c.conname
  loop
    if not ('faculty_id' = any(rec.cols))
       and ('course_id' = any(rec.cols))
       and ('section' = any(rec.cols)) then
      execute format('alter table public.faculty_courses drop constraint %I', rec.conname);
    end if;
  end loop;

  for rec in
    select i.relname as index_name, array_agg(a.attname order by u.ord) as cols
    from pg_index x
    join pg_class t on t.oid = x.indrelid
    join pg_class i on i.oid = x.indexrelid
    join pg_namespace n on n.oid = t.relnamespace
    join unnest(x.indkey) with ordinality as u(attnum, ord) on true
    join pg_attribute a on a.attrelid = t.oid and a.attnum = u.attnum
    where n.nspname = 'public'
      and t.relname = 'faculty_courses'
      and x.indisunique
      and not x.indisprimary
    group by i.relname
  loop
    if rec.index_name = 'faculty_courses_faculty_course_section_key' then
      continue;
    end if;
    if not ('faculty_id' = any(rec.cols))
       and ('course_id' = any(rec.cols))
       and ('section' = any(rec.cols)) then
      execute format('drop index if exists public.%I', rec.index_name);
    end if;
  end loop;
end $$;

create unique index if not exists faculty_courses_faculty_course_section_key
    on public.faculty_courses (faculty_id, course_id, section);
