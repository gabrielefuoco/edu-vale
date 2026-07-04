import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from zoneinfo import ZoneInfo

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

def get_spreadsheet():
    creds_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE")
    if not creds_file or not os.path.exists(creds_file):
        return None
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, SCOPE)
    client = gspread.authorize(creds)
    return client.open_by_url(os.getenv("GOOGLE_SHEET_URL"))

import asyncio

def _sync_append_session_to_sheet(data: dict):
    spreadsheet = get_spreadsheet()
    if not spreadsheet:
        return False, "Impossibile accedere al foglio Google. Controlla le credenziali o l'URL."
    
    date_str = data.get("Giorno", "")
    sheet_name = None
    
    try:
        if date_str and "-" in date_str:
            parts = date_str.split("-")
            if len(parts) >= 2:
                year, month = int(parts[0]), int(parts[1])
                if 1 <= month <= 12:
                    sheet_name = f"{MESI[month-1]} {year}"
    except Exception:
        pass
        
    if not sheet_name:
        now = datetime.now(ZoneInfo("Europe/Rome"))
        sheet_name = f"{MESI[now.month-1]} {now.year}"

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
        first_row = worksheet.row_values(1)
        if not first_row:
            worksheet.insert_row(["Giorno", "Ore", "Utente", "Luogo", "Attività svolte"], 1)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="10")
        worksheet.append_row(["Giorno", "Ore", "Utente", "Luogo", "Attività svolte"])
    
    worksheet.append_row([
        data.get("Giorno", ""), 
        data.get("Ore", ""), 
        data.get("Utente", ""), 
        data.get("Luogo", ""), 
        data.get("Attività svolte", "")
    ])
    return True, "Sessione registrata nel DB e nel Foglio Google."

async def append_session_to_sheet(data: dict):
    try:
        success, message = await asyncio.to_thread(_sync_append_session_to_sheet, data)
        return success, message
    except Exception as e:
        return False, f"Errore salvataggio Google Sheets: {str(e)}"
