-- Allow two or more faculty to share the same custom course+section
-- in a term (they meet at different times).
--
-- Run once in the Supabase SQL editor.

alter table public.custom_term_blocks
    drop constraint if exists custom_term_blocks_course_id_section_school_year_semester_key;

do $$
declare
  rec record;
begin
  for rec in
    select c.conname, array_agg(a.attname order by u.ord) as cols
    from pg_constraint c
    join unnest(c.conkey) with ordinality as u(attnum, ord) on true
    join pg_attribute a on a.attrelid = c.conrelid and a.attnum = u.attnum
    where c.conrelid = 'public.custom_term_blocks'::regclass
      and c.contype = 'u'
    group by c.conname
  loop
    if not ('faculty_id' = any(rec.cols))
       and ('course_id' = any(rec.cols))
       and ('section' = any(rec.cols)) then
      execute format('alter table public.custom_term_blocks drop constraint %I', rec.conname);
    end if;
  end loop;
end $$;

create unique index if not exists custom_term_blocks_faculty_course_section_term_key
    on public.custom_term_blocks (faculty_id, course_id, section, school_year, semester);
