import csv
import os
from database.connection import get_collection

async def export_sessions_to_csv(filename="export_diario.csv") -> str:
    col = await get_collection("diario_sessioni")
    sessions = await col.find().to_list(length=1000)
    
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Giorno", "Ore", "Utente", "Luogo", "Attività svolte", "Trascrizione Originale"])
        
        for s in sessions:
            parsed = s.get("parsed", {})
            writer.writerow([
                parsed.get("Giorno", ""),
                parsed.get("Ore", ""),
                parsed.get("Utente", ""),
                parsed.get("Luogo", ""),
                parsed.get("Attività svolte", ""),
                s.get("testo", "")
            ])
    
    return filename
