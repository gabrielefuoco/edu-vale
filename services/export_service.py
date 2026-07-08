import os
from openpyxl import Workbook
from openpyxl.styles import Font
from database.connection import get_collection

async def export_sessions_to_excel(user_id: str, filename: str = None) -> str:
    """
    Esporta le sessioni dell'utente corrente (basato su contextvars) in un file Excel (.xlsx).
    Ritorna il path assoluto del file generato.
    """
    if filename is None:
        filename = f"export_diario_{user_id}.xlsx"
        
    filepath = os.path.abspath(os.path.join(os.getcwd(), filename))
    
    col = await get_collection("diario_sessioni")
    sessions = await col.find().sort("parsed.Giorno", 1).to_list(length=2000)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Sessioni"
    
    # Intestazioni
    headers = ["Giorno", "Ore", "Utente", "Luogo", "Attività svolte"]
    ws.append(headers)
    
    # Stile intestazioni
    for cell in ws[1]:
        cell.font = Font(bold=True)
        
    # Dati
    for s in sessions:
        parsed = s.get("parsed", {})
        ws.append([
            parsed.get("Giorno", ""),
            parsed.get("Ore", ""),
            parsed.get("Utente", ""),
            parsed.get("Luogo", ""),
            parsed.get("Attività svolte", "")
        ])
        
    # Auto-resize colonne base
    for col_cells in ws.columns:
        length = max(len(str(cell.value) if cell.value else "") for cell in col_cells)
        ws.column_dimensions[col_cells[0].column_letter].width = length + 2
        
    wb.save(filepath)
    return filepath
