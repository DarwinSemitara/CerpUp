"""
Faculty Service Record (FSR) Generator
Generates FSR Excel reports matching the exact SAMPLE FSR.xlsx format
"""

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
import os


class FSRGenerator:
    """Generates Faculty Service Record Excel files"""

    def __init__(self):
        self.template_path = 'static/reference/SAMPLE FSR.xlsx'

    # ── Public entry points ───────────────────────────────────────────────

    def generate_fsr(self, faculty_data, research_data, extensions_data,
                     output_path, schedule_data=None):
        """
        Generate an FSR Excel file.

        Args:
            faculty_data:    dict with name, rank, department, etc.
            research_data:   list of research project dicts
            extensions_data: list of extension activity dicts
            output_path:     path to save the generated .xlsx
            schedule_data:   list of schedule entry dicts (optional)
        """
        wb = openpyxl.load_workbook(self.template_path)
        ws = wb.active

        ws.title = f"({faculty_data.get('rank_number', '1')}) {faculty_data.get('last_name', 'Faculty')}"

        self._fill_header(ws, faculty_data)

        if schedule_data:
            self._fill_teaching_load(ws, schedule_data)

        # Always run footnote/concurrent section cleanup
        self._fill_teaching_footnotes(ws)

        self._fill_research(ws, research_data, start_row=52)
        self._fill_extensions(ws, extensions_data, start_row=137)

        wb.save(output_path)
        return output_path

    def generate_fsr_for_member(self, member_id,
                                semester='2nd Semester',
                                academic_year='2025-2026'):
        """
        Generate FSR for a member by fetching all data from the database.
        Teaching load is matched by faculty last name in the schedules table.
        """
        from services.supabase_service import db, supabase

        member_doc = db.collection('members').document(member_id).get()
        if not member_doc.exists:
            raise ValueError(f"Member {member_id} not found")
        member_data = member_doc.to_dict()

        research_data = [d.to_dict() for d in
                         db.collection('research').where('uid', '==', member_id).stream()]

        extensions_data = [d.to_dict() for d in
                           db.collection('extensions').where('uid', '==', member_id).stream()]

        # Match schedules by last name
        last_name = (member_data.get('last') or '').strip().lower()
        schedule_data = []
        try:
            rows = supabase.table('schedules').select('*').execute().data or []
            for s in rows:
                prof = (s.get('prof') or '').lower()
                if last_name and last_name in prof:
                    schedule_data.append({
                        'subjCode': s.get('subj_code') or s.get('subjCode', ''),
                        'subjName': s.get('subj_name') or s.get('subjName', ''),
                        'room':     s.get('room', ''),
                        'day':      s.get('day', ''),
                        'start':    s.get('start', ''),
                        'end':      s.get('end', ''),
                        'section':  s.get('section', ''),
                        'units':    s.get('units', ''),
                    })
        except Exception as e:
            print(f"Warning: could not fetch schedule data: {e}")

        faculty_data = {
            'last_name':       member_data.get('last', ''),
            'first_name':      member_data.get('first', ''),
            'middle_initial':  member_data.get('middle', ''),
            'rank':            member_data.get('rank', 'Associate Professor'),
            'rank_number':     member_data.get('rank_number', '1'),
            'department':      member_data.get('department', 'DCERP'),
            'college':         member_data.get('college', 'CHE'),
            'employment_type': member_data.get('employment_type', 'full_time'),
            'semester':        semester,
            'academic_year':   academic_year,
        }

        output_dir = 'generated_fsr'
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(output_dir,
                                   f"FSR_{member_data.get('last', 'Faculty')}_{ts}.xlsx")

        return self.generate_fsr(faculty_data, research_data, extensions_data,
                                 output_path, schedule_data=schedule_data)

    # ── Private helpers ───────────────────────────────────────────────────

    def _fill_header(self, ws, faculty_data):
        """Fill the top header block (rows 2-9)."""
        semester = faculty_data.get('semester', '2nd Semester')
        acad_year = faculty_data.get('academic_year', '2025-2026')
        ws['D2'] = f"{semester} {acad_year}"

        ws['C4'] = faculty_data.get('last_name', '').upper()
        ws['E4'] = faculty_data.get('first_name', '').upper()
        ws['G4'] = faculty_data.get('middle_initial', '').upper()
        ws['I4'] = faculty_data.get('rank', 'Associate Professor 2')

        if faculty_data.get('employment_type', 'full_time') == 'full_time':
            ws['I5'] = '[ x ]    Full Time'
            ws['I6'] = '[  ]    Part Time'
        else:
            ws['I5'] = '[  ]    Full Time'
            ws['I6'] = '[ x ]    Part Time'

        ws['C7'] = faculty_data.get('department', 'DCERP')
        ws['J7'] = faculty_data.get('college', 'CHE')

        teaching_college = faculty_data.get('teaching_college', '')
        if teaching_college and teaching_college != faculty_data.get('college'):
            ws['E9'] = teaching_college

    def _fill_teaching_load(self, ws, schedule_data):
        """
        Fill Section I Teaching Load (rows 12-21).
        Populates: Subject (col A), Room (col C), Days (col D), Time (col E).
        Section code and calculated columns left blank per requirements.
        """
        DATA_START_ROW = 12
        MAX_ROWS = 10

        thin = Side(style='thin', color='000000')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        c_aln = Alignment(horizontal='center',
                          vertical='center', wrap_text=True)
        l_aln = Alignment(horizontal='left',
                          vertical='center', wrap_text=True)

        DAY_ABBR = {
            'Monday': 'M', 'Tuesday': 'T', 'Wednesday': 'W',
            'Thursday': 'TH', 'Friday': 'F', 'Saturday': 'S',
        }

        def fmt_range(start, end):
            if not start or not end:
                return ''
            try:
                hs, ms = int(start.split(':')[0]), int(start.split(':')[1])
                he, me = int(end.split(':')[0]),   int(end.split(':')[1])
                ps = 'PM' if hs >= 12 else 'AM'
                pe = 'PM' if he >= 12 else 'AM'
                hs12 = hs - 12 if hs > 12 else (12 if hs == 0 else hs)
                he12 = he - 12 if he > 12 else (12 if he == 0 else he)
                if ps == pe:
                    return f"{hs12}:{ms:02d}-{he12}:{me:02d} {pe}"
                return f"{hs12}:{ms:02d} {ps}-{he12}:{me:02d} {pe}"
            except Exception:
                return f"{start}-{end}"

        # Consolidate: same subject+room+time → merge days
        consolidated = {}
        for s in sorted(schedule_data, key=lambda x: (x.get('subjCode', ''), x.get('day', ''))):
            key = (s.get('subjCode', ''), s.get('room', ''),
                   s.get('start', ''), s.get('end', ''))
            if key not in consolidated:
                consolidated[key] = {'entry': s, 'days': []}
            abbr = DAY_ABBR.get(
                s.get('day', ''), (s.get('day', '') or '')[:2].upper())
            if abbr and abbr not in consolidated[key]['days']:
                consolidated[key]['days'].append(abbr)

        rows_to_write = list(consolidated.values())[:MAX_ROWS]

        # Clear existing template data in target columns
        for r in range(DATA_START_ROW, DATA_START_ROW + MAX_ROWS):
            for col in [1, 3, 4, 5]:
                ws.cell(row=r, column=col).value = None

        for i, item in enumerate(rows_to_write):
            row = DATA_START_ROW + i
            entry = item['entry']
            days = '/'.join(item['days'])
            time = fmt_range(entry.get('start'), entry.get('end'))

            c = ws.cell(row=row, column=1)
            c.value = entry.get('subjCode', '')
            c.font = Font(size=10)
            c.alignment = l_aln
            c.border = border

            c = ws.cell(row=row, column=3)
            c.value = entry.get('room', '')
            c.font = Font(size=10)
            c.alignment = c_aln
            c.border = border

            c = ws.cell(row=row, column=4)
            c.value = days
            c.font = Font(size=10)
            c.alignment = c_aln
            c.border = border

            c = ws.cell(row=row, column=5)
            c.value = time
            c.font = Font(size=10)
            c.alignment = c_aln
            c.border = border

    def _fill_teaching_footnotes(self, ws):
        """
        Clean up rows 23-41 (between Section I and Section II).

        Rows 23-25: Clear sample footnote text (team/relay teaching notes
                    are specific to the sample faculty — must not carry over).
        Rows 30,33: Ensure (NONE) defaults exist for concurrent load table.
        Everything else in this range (instruction text, NOTE, Registrar
        block) is preserved exactly as in the template.
        """
        font_n = Font(size=10)
        c_aln = Alignment(horizontal='center', vertical='center')

        # Clear sample footnote annotations
        for r in [23, 24, 25]:
            ws.cell(row=r, column=1).value = None

        # Ensure concurrent load defaults
        for r in [30, 33]:
            for col in [1, 5, 8]:   # A = institution, E = no. of subjects, H = no. of units
                cell = ws.cell(row=r, column=col)
                if not cell.value or str(cell.value).strip() == '':
                    cell.value = '(NONE)'
                    cell.font = font_n
                    cell.alignment = c_aln

    def _fill_research(self, ws, research_data, start_row=52):
        """Fill Section II.A2 — Research Implementation (rows start_row+)."""
        current_row = start_row

        for idx, research in enumerate(research_data, 1):
            ws.row_dimensions[current_row].height = 18.75

            project_id = research.get('project_id', '')
            title = research.get('title', '')

            cell = ws.cell(row=current_row, column=1)
            cell.value = (f"({idx}) OVCRE Project ID: {project_id}\n{title}"
                          if project_id else f"({idx}) {title}")
            cell.font = Font(size=10)
            cell.alignment = Alignment(
                horizontal='left', vertical='top', wrap_text=True)
            cell.fill = PatternFill(start_color='FFFFFFFF', end_color='FFFFFFFF',
                                    fill_type='solid')
            cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=5)
            cell.value = research.get('role', 'Study Leader')
            cell.alignment = Alignment(horizontal='left', vertical='top')
            cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=6)
            cell.value = research.get('co_authors', 'None')
            cell.alignment = Alignment(
                horizontal='left', vertical='top', wrap_text=True)
            cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=8)
            sd = research.get('start_date')
            cell.value = sd if isinstance(sd, str) else (
                sd.strftime('%Y-%m-%d') if sd else None)
            cell.alignment = Alignment(horizontal='left', vertical='top')
            cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=9)
            ed = research.get('end_date')
            cell.value = ed if isinstance(ed, str) else (
                ed.strftime('%Y-%m-%d') if ed else None)
            cell.alignment = Alignment(horizontal='left', vertical='top')
            cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=10)
            cell.value = research.get('funding_agency', 'Core Funded')
            cell.alignment = Alignment(horizontal='left', vertical='top')
            cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=11)
            cell.value = research.get('credit_units', 3)
            cell.alignment = Alignment(horizontal='center', vertical='top')
            cell.border = self._create_border()

            current_row += 1

        if research_data:
            ws.cell(row=current_row, column=11).value = \
                f"=SUM(K{start_row}:K{current_row - 1})"

        return current_row

    def _fill_extensions(self, ws, extensions_data, start_row=137):
        """Fill Section IV — Extension and Community Service."""
        current_row = start_row

        for extension in extensions_data:
            ws.row_dimensions[current_row].height = 18.75

            project_id = extension.get('project_id', '')
            title = extension.get('title', '')

            cell = ws.cell(row=current_row, column=1)
            cell.value = (
                f"Project ID: {project_id}\n{title}" if project_id else title)
            cell.font = Font(size=10, bold=True)
            cell.alignment = Alignment(
                horizontal='left', vertical='top', wrap_text=True)
            cell.fill = PatternFill(start_color='FFFFFFFF', end_color='FFFFFFFF',
                                    fill_type='solid')
            cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=5)
            cell.value = extension.get('role', 'Project Leader')
            cell.border = self._create_border()

            if extension.get('co_workers'):
                cell = ws.cell(row=current_row, column=6)
                cell.value = extension['co_workers']
                cell.alignment = Alignment(wrap_text=True)
                cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=8)
            sd = extension.get('start_date')
            cell.value = sd if isinstance(sd, str) else (
                sd.strftime('%m/%d/%Y') if sd else None)
            cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=9)
            ed = extension.get('end_date')
            cell.value = ed if isinstance(ed, str) else (
                ed.strftime('%Y-%m-%d') if ed else None)
            cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=10)
            cell.value = extension.get('funding_agency', '')
            cell.border = self._create_border()

            cell = ws.cell(row=current_row, column=11)
            cell.value = extension.get('credit_units', 2)
            cell.border = self._create_border()

            current_row += 1

        if extensions_data:
            ws.cell(row=current_row + 2, column=11).value = \
                f"=SUM(K{start_row}:K{current_row - 1})"

        return current_row

    def _create_border(self, style='thin'):
        """Return a uniform thin border."""
        side = Side(style=style, color='000000')
        return Border(left=side, right=side, top=side, bottom=side)


# ── Convenience function ──────────────────────────────────────────────────────

def generate_member_fsr(member_id, semester='2nd Semester', academic_year='2025-2026'):
    """Generate FSR for a member — thin wrapper around FSRGenerator."""
    return FSRGenerator().generate_fsr_for_member(member_id, semester, academic_year)
