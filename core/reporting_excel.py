# core/reporting_excel.py
# Version i qëndrueshëm me formatim tekstual për raportet e analizës së telefonatave
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from pathlib import Path

def write_excel_report_textual(rows, out_path):
    """
    Krijon një raport Excel me dy nivele:
    1. Faqja 'Përmbledhje' që liston çdo agjent dhe përshkrimin e tij të përgjithshëm.
    2. Një faqe për secilin agjent me seksionet 'preggi' dhe 'da migliorare'.
    rows: list[dict] me fushat ['agent','summary','preggi','da_migliorare']
    """
    wb = Workbook()
    ws_summary = wb.active
    ws_summary.title = "Përmbledhje"

    # Stil bazë
    bold = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")

    # Kolonat për faqen kryesore
    ws_summary.append(["Agjenti", "Përmbledhje"])
    ws_summary.column_dimensions["A"].width = 25
    ws_summary.column_dimensions["B"].width = 120

    # Grupi sipas agjentit
    by_agent = {}
    for r in rows:
        ag = (r.get("agent") or "UNKNOWN").strip()
        if ag not in by_agent:
            by_agent[ag] = {
                "summary": r.get("summary", ""),
                "preggi": r.get("preggi", ""),
                "da_migliorare": r.get("da_migliorare", "")
            }
        # shto në faqen Përmbledhje vetëm një herë për agjent
        if not any(ws_summary.cell(row=i, column=1).value == ag for i in range(2, ws_summary.max_row+1)):
            ws_summary.append([ag, r.get("summary", "")])

    # Fletët individuale për agjentët
    for agent in sorted(by_agent.keys()):
        data = by_agent[agent]
        ws = wb.create_sheet(title=agent[:30])  # max 31 karaktere në titullin e faqes
        ws.column_dimensions["A"].width = 140

        # pregji
        ws["A1"] = "preggi"
        ws["A1"].font = bold
        ws["A2"] = data["preggi"]
        ws["A2"].alignment = wrap

        # da migliorare
        ws["A4"] = "da migliorare"
        ws["A4"].font = bold
        ws["A5"] = data["da_migliorare"]
        ws["A5"].alignment = wrap

    # Ruaj rezultatin
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
