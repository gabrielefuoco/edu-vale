from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from database.connection import get_collection, get_all_group_configs

scheduler = AsyncIOScheduler()

async def send_morning_recap(bot: Bot):
    all_configs = await get_all_group_configs()
    
    for cfg in all_configs:
        owner_id = cfg.get("owner_id")
        group_id = cfg.get("group_id")
        segreteria_id = cfg.get("segreteria_id")
        
        if not owner_id or not group_id:
            continue
            
        oggi = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d")
        col = await get_collection("programmazione", uid=owner_id)
        sessioni = await col.find({"data": oggi}).to_list(length=20)
        
        if not sessioni:
            testo = "Buongiorno! Oggi non hai sessioni in programma. Riposati!"
        else:
            testo = f"Buongiorno! ☀️ Ecco la tua agenda per oggi ({oggi}):\n\n"
            for s in sessioni:
                utente = s.get("utente_id", "Sconosciuto")
                inizio = s.get("ora_inizio", "")
                fine = s.get("ora_fine", "")
                luogo = s.get("luogo", "")
                testo += f"- <b>{utente}</b> ({inizio} - {fine}) | 📍 {luogo}\n"
            testo += "\nRicorda di usare /oggi per avere i file .ics da aggiungere al calendario Apple!"
            
        kwargs = {"chat_id": group_id, "text": testo, "parse_mode": "HTML"}
        if segreteria_id:
            kwargs["message_thread_id"] = int(segreteria_id)
            
        try:
            await bot.send_message(**kwargs)
        except Exception as e:
            print(f"Errore nell'invio del recap per il gruppo {group_id}: {e}")

def setup_scheduler(bot: Bot):
    scheduler.add_job(send_morning_recap, 'cron', hour=7, minute=0, args=[bot], timezone=ZoneInfo("Europe/Rome"))
    scheduler.start()
