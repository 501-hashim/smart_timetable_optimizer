import io
from typing import List, Dict, Any
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_excel_timetable(
    class_name: str,
    academic_year: str,
    entries: List[Dict[str, Any]],
    days: List[str],
    periods: List[int],
    fixed_events: List[Any]
) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = f"{class_name} Timetable"

    title_font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
    sub_font = Font(name="Calibri", size=11, bold=True, color="475569")
    hdr_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    cell_font = Font(name="Calibri", size=9)
    bold_cell_font = Font(name="Calibri", size=9, bold=True)

    hdr_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    break_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    lab_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
    theory_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    fixed_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    ws.merge_cells("A1:J1")
    ws["A1"] = "VIDYA ACADEMY OF SCIENCE & TECHNOLOGY"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A2:J2")
    ws["A2"] = f"ACADEMIC TIMETABLE - {class_name.upper()} ({academic_year})"
    ws["A2"].font = sub_font
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    cols = [
        "Day / Period",
        "Period I (09:00-09:55)",
        "Period II (09:55-10:50)",
        "INTERVAL (10:50-11:05)",
        "Period III (11:05-12:00)",
        "Period IV (12:00-12:55)",
        "LUNCH BREAK (12:55-01:45)",
        "Period V (01:45-02:35)",
        "Period VI (02:35-03:25)",
        "Period VII (03:25-04:15)"
    ]

    row_idx = 4
    for c_idx, title in enumerate(cols, start=1):
        cell = ws.cell(row=row_idx, column=c_idx, value=title)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[row_idx].height = 28

    grid_map = {d: {} for d in days}
    for e in entries:
        d = e["day"]
        p = e["period"]
        if d in grid_map:
            grid_map[d][p] = e

    fixed_map = {d: {} for d in days}
    for fe in fixed_events:
        d = getattr(fe, "day", fe.get("day") if isinstance(fe, dict) else "")
        p = getattr(fe, "period", fe.get("period") if isinstance(fe, dict) else 0)
        name = getattr(fe, "name", fe.get("name") if isinstance(fe, dict) else "")
        if d in fixed_map:
            fixed_map[d][p] = name

    col_mapping = {
        1: 2,  # P1 -> Col B
        2: 3,  # P2 -> Col C
        3: 5,  # P3 -> Col E
        4: 6,  # P4 -> Col F
        5: 8,  # P5 -> Col H
        6: 9,  # P6 -> Col I
        7: 10  # P7 -> Col J
    }

    row_idx = 5
    for day in days:
        ws.row_dimensions[row_idx].height = 42
        day_cell = ws.cell(row=row_idx, column=1, value=day)
        day_cell.font = bold_cell_font
        day_cell.alignment = Alignment(horizontal="center", vertical="center")
        day_cell.border = thin_border
        day_cell.fill = theory_fill

        int_cell = ws.cell(row=row_idx, column=4, value="INTERVAL")
        int_cell.font = Font(name="Calibri", size=8, italic=True, color="64748B")
        int_cell.alignment = Alignment(horizontal="center", vertical="center", text_rotation=90)
        int_cell.fill = break_fill
        int_cell.border = thin_border

        lunch_cell = ws.cell(row=row_idx, column=7, value="LUNCH")
        lunch_cell.font = Font(name="Calibri", size=8, italic=True, color="64748B")
        lunch_cell.alignment = Alignment(horizontal="center", vertical="center", text_rotation=90)
        lunch_cell.fill = break_fill
        lunch_cell.border = thin_border

        skip_periods = 0
        for p in range(1, 8):
            if skip_periods > 0:
                skip_periods -= 1
                continue

            target_col = col_mapping[p]
            cell = ws.cell(row=row_idx, column=target_col)
            cell.border = thin_border

            if p in fixed_map.get(day, {}):
                fe_name = fixed_map[day][p]
                cell.value = f"[Fixed] {fe_name}"
                cell.font = bold_cell_font
                cell.fill = fixed_fill
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                continue

            if p in grid_map.get(day, {}):
                entry = grid_map[day][p]
                code = entry.get("subject_code", "")
                fac_str = ", ".join(entry.get("faculty_short_names", []))
                room = entry.get("room_name", "").split("(")[0].strip()
                dur = entry.get("duration", 1)

                cell.value = f"{code}\n[{fac_str}]\n{room}"
                cell.font = cell_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

                if dur > 1:
                    cell.fill = lab_fill
                    end_p = p + dur - 1
                    end_col = col_mapping[end_p]
                    ws.merge_cells(start_row=row_idx, start_column=target_col, end_row=row_idx, end_column=end_col)
                    skip_periods = dur - 1
                else:
                    cell.fill = theory_fill
            else:
                cell.value = "-"
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.fill = theory_fill

        row_idx += 1

    ws.column_dimensions["A"].width = 14
    for col_letter in ["B", "C", "E", "F", "H", "I", "J"]:
        ws.column_dimensions[col_letter].width = 20
    ws.column_dimensions["D"].width = 8
    ws.column_dimensions["G"].width = 8

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.read()

def generate_pdf_timetable(
    class_name: str,
    academic_year: str,
    entries: List[Dict[str, Any]],
    days: List[str],
    periods: List[int],
    fixed_events: List[Any]
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=20,
        rightMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="TitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1
    )
    sub_style = ParagraphStyle(
        name="SubStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )
    cell_style = ParagraphStyle(
        name="GridCellStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        alignment=1
    )
    header_style = ParagraphStyle(
        name="GridHeaderStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.white,
        alignment=1
    )

    elements = []
    elements.append(Paragraph("VIDYA ACADEMY OF SCIENCE & TECHNOLOGY", title_style))
    elements.append(Paragraph(f"DEPARTMENT OF AIML - {class_name.upper()} ({academic_year})", sub_style))
    elements.append(Spacer(1, 10))

    headers = [
        Paragraph("Day / Period", header_style),
        Paragraph("Period I<br/>09:00-09:55", header_style),
        Paragraph("Period II<br/>09:55-10:50", header_style),
        Paragraph("INT<br/>10:50", header_style),
        Paragraph("Period III<br/>11:05-12:00", header_style),
        Paragraph("Period IV<br/>12:00-12:55", header_style),
        Paragraph("LUNCH<br/>12:55", header_style),
        Paragraph("Period V<br/>01:45-02:35", header_style),
        Paragraph("Period VI<br/>02:35-03:25", header_style),
        Paragraph("Period VII<br/>03:25-04:15", header_style)
    ]
    table_data = [headers]

    grid_map = {d: {} for d in days}
    for e in entries:
        grid_map[e["day"]][e["period"]] = e

    fixed_map = {d: {} for d in days}
    for fe in fixed_events:
        d = getattr(fe, "day", fe.get("day") if isinstance(fe, dict) else "")
        p = getattr(fe, "period", fe.get("period") if isinstance(fe, dict) else 0)
        name = getattr(fe, "name", fe.get("name") if isinstance(fe, dict) else "")
        fixed_map[d][p] = name

    for day in days:
        row = [Paragraph(f"<b>{day}</b>", cell_style)]
        for p in [1, 2]:
            if p in fixed_map.get(day, {}):
                row.append(Paragraph(f"[Fixed] {fixed_map[day][p]}", cell_style))
            elif p in grid_map[day]:
                e = grid_map[day][p]
                fac = ", ".join(e.get("faculty_short_names", []))
                row.append(Paragraph(f"<b>{e.get('subject_code','')}</b><br/>{fac}", cell_style))
            else:
                row.append(Paragraph("-", cell_style))

        row.append(Paragraph("I<br/>N<br/>T", cell_style))

        for p in [3, 4]:
            if p in fixed_map.get(day, {}):
                row.append(Paragraph(f"[Fixed] {fixed_map[day][p]}", cell_style))
            elif p in grid_map[day]:
                e = grid_map[day][p]
                fac = ", ".join(e.get("faculty_short_names", []))
                row.append(Paragraph(f"<b>{e.get('subject_code','')}</b><br/>{fac}", cell_style))
            else:
                row.append(Paragraph("-", cell_style))

        row.append(Paragraph("L<br/>U<br/>N", cell_style))

        for p in [5, 6, 7]:
            if p in fixed_map.get(day, {}):
                row.append(Paragraph(f"[Fixed] {fixed_map[day][p]}", cell_style))
            elif p in grid_map[day]:
                e = grid_map[day][p]
                fac = ", ".join(e.get("faculty_short_names", []))
                row.append(Paragraph(f"<b>{e.get('subject_code','')}</b><br/>{fac}", cell_style))
            else:
                row.append(Paragraph("-", cell_style))

        table_data.append(row)

    col_widths = [65, 75, 75, 25, 75, 75, 25, 75, 75, 75]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (3, 1), (3, -1), colors.HexColor("#F1F5F9")),
        ("BACKGROUND", (6, 1), (6, -1), colors.HexColor("#F1F5F9")),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
