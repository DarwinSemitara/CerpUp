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
        
    def generate_fsr(self, faculty_data, research_data, extensions_data, output_path):
        """
        Generate an FSR Excel file
        
        Args:
            faculty_data: dict with faculty info (name, rank, department, etc.)
            research_data: list of research projects
            extensions_data: list of extension activities
            output_path: where to save the generated FSR
        """
        # Load template
        wb = openpyxl.load_workbook(self.template_path)
        ws = wb.active
        
        # Update sheet name with faculty name
        ws.title = f"({faculty_data.get('rank_number', '1')}) {faculty_data.get('last_name', 'Faculty')}"
        
        # Fill in header information
        self._fill_header(ws, faculty_data)
        
        # Fill in teaching load (Section I)
        # Note: Teaching load typically comes from schedule system
        # For now, we'll keep the template structure
        
        # Fill in research (Section II)
        research_start_row = 52  # Where research implementation data starts
        research_row = self._fill_research(ws, research_data, research_start_row)
        
        # Fill in extensions (Section IV)
        extension_start_row = 137  # Where extension data starts
        self._fill_extensions(ws, extensions_data, extension_start_row)
        
        # Save the workbook
        wb.save(output_path)
        return output_path
    
    def _fill_header(self, ws, faculty_data):
        """Fill in the header section with faculty information"""
        # Semester/Year (Row 2, Column D)
        semester = faculty_data.get('semester', '2nd Semester')
        academic_year = faculty_data.get('academic_year', '2025-2026')
        ws['D2'] = f"{semester} {academic_year}"
        
        # Name (Row 4)
        ws['C4'] = faculty_data.get('last_name', '').upper()
        ws['E4'] = faculty_data.get('first_name', '').upper()
        ws['G4'] = faculty_data.get('middle_initial', '').upper()
        
        # Rank (Row 4)
        ws['I4'] = faculty_data.get('rank', 'Associate Professor 2')
        
        # Employment type (Row 5, Row 6)
        employment_type = faculty_data.get('employment_type', 'full_time')
        if employment_type == 'full_time':
            ws['I5'] = '[ x ]    Full Time'
            ws['I6'] = '[  ]    Part Time'
        else:
            ws['I5'] = '[  ]    Full Time'
            ws['I6'] = '[ x ]    Part Time'
        
        # Department and College (Row 7)
        ws['C7'] = faculty_data.get('department', 'DCERP')
        ws['J7'] = faculty_data.get('college', 'CHE')
        
        # Teaching college if different (Row 9)
        teaching_college = faculty_data.get('teaching_college', '')
        if teaching_college and teaching_college != faculty_data.get('college'):
            ws['E9'] = teaching_college
    
    def _fill_research(self, ws, research_data, start_row):
        """Fill in research implementation section"""
        current_row = start_row
        
        for idx, research in enumerate(research_data, 1):
            # Set row height
            ws.row_dimensions[current_row].height = 18.75
            
            # Title with project ID (Column A)
            project_id = research.get('project_id', '')
            title = research.get('title', '')
            cell_a = ws.cell(row=current_row, column=1)
            if project_id:
                cell_a.value = f"({idx}) OVCRE Project ID: {project_id}\n{title}"
            else:
                cell_a.value = f"({idx}) {title}"
            
            # Styling for title cell
            cell_a.font = Font(size=10)
            cell_a.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            cell_a.fill = PatternFill(start_color='FFFFFFFF', end_color='FFFFFFFF', fill_type='solid')
            cell_a.border = self._create_border()
            
            # Role (Column E)
            cell_e = ws.cell(row=current_row, column=5)
            cell_e.value = research.get('role', 'Study Leader')
            cell_e.alignment = Alignment(horizontal='left', vertical='top')
            cell_e.border = self._create_border()
            
            # Co-workers (Column F)
            cell_f = ws.cell(row=current_row, column=6)
            cell_f.value = research.get('co_authors', 'None')
            cell_f.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            cell_f.border = self._create_border()
            
            # Start Date (Column H)
            cell_h = ws.cell(row=current_row, column=8)
            start_date = research.get('start_date')
            if start_date:
                if isinstance(start_date, str):
                    cell_h.value = start_date
                else:
                    cell_h.value = start_date.strftime('%Y-%m-%d %H:%M:%S')
            cell_h.alignment = Alignment(horizontal='left', vertical='top')
            cell_h.border = self._create_border()
            
            # End Date (Column I)
            cell_i = ws.cell(row=current_row, column=9)
            end_date = research.get('end_date')
            if end_date:
                if isinstance(end_date, str):
                    cell_i.value = end_date
                else:
                    cell_i.value = end_date.strftime('%Y-%m-%d %H:%M:%S')
            cell_i.alignment = Alignment(horizontal='left', vertical='top')
            cell_i.border = self._create_border()
            
            # Funding Agency (Column J)
            cell_j = ws.cell(row=current_row, column=10)
            cell_j.value = research.get('funding_agency', 'Core Funded')
            cell_j.alignment = Alignment(horizontal='left', vertical='top')
            cell_j.border = self._create_border()
            
            # Credit Units (Column K)
            cell_k = ws.cell(row=current_row, column=11)
            cell_k.value = research.get('credit_units', 3)
            cell_k.alignment = Alignment(horizontal='center', vertical='top')
            cell_k.border = self._create_border()
            
            current_row += 1
        
        # Update total formula
        if research_data:
            total_cell = ws.cell(row=current_row, column=11)
            total_cell.value = f"=SUM(K{start_row}:K{current_row - 1})"
        
        return current_row
    
    def _fill_extensions(self, ws, extensions_data, start_row):
        """Fill in extension/community service section"""
        current_row = start_row
        
        for idx, extension in enumerate(extensions_data, 1):
            # Set row height
            ws.row_dimensions[current_row].height = 18.75
            
            # Title with project ID (Column A)
            project_id = extension.get('project_id', '')
            title = extension.get('title', '')
            cell_a = ws.cell(row=current_row, column=1)
            if project_id:
                cell_a.value = f"Project ID: {project_id}\n{title}"
            else:
                cell_a.value = title
            
            # Styling
            cell_a.font = Font(size=10, bold=True)
            cell_a.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            cell_a.fill = PatternFill(start_color='FFFFFFFF', end_color='FFFFFFFF', fill_type='solid')
            cell_a.border = self._create_border()
            
            # Role (Column E)
            cell_e = ws.cell(row=current_row, column=5)
            cell_e.value = extension.get('role', 'Project Leader')
            cell_e.border = self._create_border()
            
            # Co-workers (Column F)
            if extension.get('co_workers'):
                cell_f = ws.cell(row=current_row, column=6)
                cell_f.value = extension.get('co_workers')
                cell_f.alignment = Alignment(wrap_text=True)
                cell_f.border = self._create_border()
            
            # Start Date (Column H)
            cell_h = ws.cell(row=current_row, column=8)
            start_date = extension.get('start_date')
            if start_date:
                cell_h.value = start_date if isinstance(start_date, str) else start_date.strftime('%m/%d/%Y')
            cell_h.border = self._create_border()
            
            # End Date (Column I)
            cell_i = ws.cell(row=current_row, column=9)
            end_date = extension.get('end_date')
            if end_date:
                cell_i.value = end_date if isinstance(end_date, str) else end_date.strftime('%Y-%m-%d %H:%M:%S')
            cell_i.border = self._create_border()
            
            # Funding Agency (Column J)
            cell_j = ws.cell(row=current_row, column=10)
            cell_j.value = extension.get('funding_agency', '')
            cell_j.border = self._create_border()
            
            # Credit Units (Column K)
            cell_k = ws.cell(row=current_row, column=11)
            credit_units = extension.get('credit_units', 2)
            cell_k.value = credit_units
            cell_k.border = self._create_border()
            
            current_row += 1
        
        # Update total formula
        if extensions_data:
            total_row = current_row + 2
            total_cell = ws.cell(row=total_row, column=11)
            total_cell.value = f"=SUM(K{start_row}:K{current_row - 1})"
        
        return current_row
    
    def _create_border(self, style='thin'):
        """Create a border style"""
        side = Side(style=style, color='000000')
        return Border(left=side, right=side, top=side, bottom=side)
    
    def generate_fsr_for_member(self, member_id, semester='2nd Semester', academic_year='2025-2026'):
        """
        Generate FSR for a specific member by fetching their data from database
        
        Args:
            member_id: The member's ID
            semester: Academic semester
            academic_year: Academic year
        
        Returns:
            Path to generated FSR file
        """
        from services.firebase_service import db
        
        # Fetch member data
        member_doc = db.collection('members').document(member_id).get()
        if not member_doc.exists:
            raise ValueError(f"Member {member_id} not found")
        
        member_data = member_doc.to_dict()
        
        # Fetch research data
        research_docs = db.collection('research').where('member_id', '==', member_id).stream()
        research_data = [doc.to_dict() for doc in research_docs]
        
        # Fetch extension data
        extension_docs = db.collection('extensions').where('member_id', '==', member_id).stream()
        extensions_data = [doc.to_dict() for doc in extension_docs]
        
        # Prepare faculty data
        faculty_data = {
            'last_name': member_data.get('last', ''),
            'first_name': member_data.get('first', ''),
            'middle_initial': member_data.get('middle', ''),
            'rank': member_data.get('rank', 'Associate Professor'),
            'rank_number': member_data.get('rank_number', '1'),
            'department': member_data.get('department', 'DCERP'),
            'college': member_data.get('college', 'CHE'),
            'employment_type': member_data.get('employment_type', 'full_time'),
            'semester': semester,
            'academic_year': academic_year
        }
        
        # Generate output filename
        output_dir = 'generated_fsr'
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"FSR_{member_data.get('last', 'Faculty')}_{timestamp}.xlsx"
        output_path = os.path.join(output_dir, filename)
        
        # Generate FSR
        return self.generate_fsr(faculty_data, research_data, extensions_data, output_path)


# Convenience function
def generate_member_fsr(member_id, semester='2nd Semester', academic_year='2025-2026'):
    """Generate FSR for a member"""
    generator = FSRGenerator()
    return generator.generate_fsr_for_member(member_id, semester, academic_year)
