import openpyxl

wb = openpyxl.load_workbook('static/reference/class_schedule_new.xlsx', data_only=True)
sheet = wb.active

profs = set()
for row in sheet.iter_rows(min_row=2, values_only=True):
    if row[0]:
        profs.add(row[0])

search_terms = ['MARY', 'MARS', 'MARK']
for prof in sorted(profs):
    if any(term in str(prof).upper() for term in search_terms):
        print(prof)
