from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from database.connection import get_collection
from services.ai_service import summarize_progress

router = Router()

@router.message(Command("progressi"))
async def cmd_progressi(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Usa: /progressi [Nome Utente]")
    
    nome = args[1]
    col = await get_collection("diario_sessioni")
    sessioni = await col.find({"parsed.Utente": nome}).to_list(length=50)
    
    if not sessioni:
        return await message.answer(f"Nessuna sessione trovata per {nome}.")
    
    await message.answer("Elaborazione del riassunto in corso...")
    texts = [s.get("testo", "") for s in sessioni]
    riassunto = await summarize_progress(texts, nome)
    
    await message.answer(f"📈 **Progressi di {nome}**:\n\n{riassunto}")
