from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import os
from datetime import datetime
from database.connection import get_collection

scheduler = AsyncIOScheduler()

async def send_morning_recap(bot: Bot):
    user_id = os.getenv("AUTHORIZED_USER_ID")
    if not user_id:
        return
        
    oggi = datetime.now().strftime("%Y-%m-%d")
    col = await get_collection("programmazione")
    sessioni = await col.find({"Data": oggi}).to_list(length=20)
    
    if not sessioni:
        testo = "Buongiorno! Oggi non hai sessioni in programma. Riposati!"
    else:
        testo = f"Buongiorno! ☀️ Ecco la tua agenda per oggi ({oggi}):\n\n"
        for s in sessioni:
            utente = s.get("Utente", "Sconosciuto")
            inizio = s.get("Ora Inizio", "")
            fine = s.get("Ora Fine", "")
            luogo = s.get("Luogo", "")
            testo += f"- **{utente}** ({inizio} - {fine}) | 📍 {luogo}\n"
        testo += "\nRicorda di usare /oggi per avere i file .ics da aggiungere al calendario Apple!"
        
    await bot.send_message(chat_id=user_id, text=testo)

def setup_scheduler(bot: Bot):
    scheduler.add_job(send_morning_recap, 'cron', hour=7, minute=0, args=[bot])
    scheduler.start()
