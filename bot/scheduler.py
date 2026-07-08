from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from database.connection import get_collection

scheduler = AsyncIOScheduler()

async def send_morning_recap(bot: Bot):
    allowed_ids_str = os.getenv("AUTHORIZED_USER_IDS", "")
    allowed_ids = [uid.strip() for uid in allowed_ids_str.split(",") if uid.strip()]
    if not allowed_ids:
        return
        
    for user_id in allowed_ids:        
        oggi = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d")
        col = await get_collection("programmazione")
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
                testo += f"- **{utente}** ({inizio} - {fine}) | 📍 {luogo}\n"
            testo += "\nRicorda di usare /oggi per avere i file .ics da aggiungere al calendario Apple!"
            
        await bot.send_message(chat_id=user_id, text=testo)


def setup_scheduler(bot: Bot):
    scheduler.add_job(send_morning_recap, 'cron', hour=7, minute=0, args=[bot], timezone=ZoneInfo("Europe/Rome"))
    scheduler.start()
