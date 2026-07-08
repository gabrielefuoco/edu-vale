from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database.connection import get_collection
from database.models import User
from services.ai_service import extract_session_data, transcribe_audio
import os
import json

router = Router()

class NewUser(StatesGroup):
    nome = State()
    ore = State()

class RegistraSessione(StatesGroup):
    audio_or_text = State()
    conferma = State()

@router.message(Command("nuovo_utente"))
async def cmd_nuovo_utente(message: Message, state: FSMContext):
    await message.answer("Nome del nuovo utente?")
    await state.set_state(NewUser.nome)

@router.message(NewUser.nome)
async def process_nome(message: Message, state: FSMContext):
    await state.update_data(nome=message.text)
    await message.answer("Quante ore settimanali previste?")
    await state.set_state(NewUser.ore)

@router.message(NewUser.ore)
async def process_ore(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        ore = int(message.text)
    except:
        return await message.answer("Inserisci un numero valido.")
    
    user = User(nome=data['nome'], ore_settimanali=ore)
    col = await get_collection("utenti")
    res = await col.insert_one(user.model_dump())
    
    await state.clear()
    await message.answer(f"Utente {user.nome} aggiunto! (ID: {res.inserted_id})")

@router.message(Command("registra"))
async def cmd_registra(message: Message, state: FSMContext):
    await message.answer("Inviami l'audio o il testo della sessione.")
    await state.set_state(RegistraSessione.audio_or_text)

@router.message(RegistraSessione.audio_or_text, F.voice)
async def process_audio(message: Message, state: FSMContext, bot):
    await message.answer("Trascrizione in corso...")
    file = await bot.get_file(message.voice.file_id)
    file_path = f"tmp_{message.voice.file_id}.ogg"
    await bot.download_file(file.file_path, file_path)
    
    text = await transcribe_audio(file_path)
    os.remove(file_path)
    await process_session_text(text, message, state)

@router.message(RegistraSessione.audio_or_text, F.text)
async def process_text_input(message: Message, state: FSMContext):
    await process_session_text(message.text, message, state)

async def process_session_text(text: str, message: Message, state: FSMContext):
    await message.answer(f"Trascrizione:\n{text}\n\nEstrazione dati in corso...")
    data = await extract_session_data(text)
    
    await state.update_data(session_data=data, text=text)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Salva nel Database", callback_data="salva_sessione")],
        [InlineKeyboardButton(text="❌ Annulla", callback_data="annulla_sessione")]
    ])
    
    await message.answer(f"Dati estratti:\n{json.dumps(data, indent=2)}\n\nConfermi?", reply_markup=markup)
    await state.set_state(RegistraSessione.conferma)

@router.callback_query(RegistraSessione.conferma, F.data == "salva_sessione")
async def salva_sessione(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    session_data = data['session_data']
    
    # Save to DB
    col = await get_collection("diario_sessioni")
    await col.insert_one({"testo": data['text'], "parsed": session_data})
    
    await callback.message.edit_text("✅ Salvato con successo!")
    await state.clear()

@router.callback_query(RegistraSessione.conferma, F.data == "annulla_sessione")
async def annulla_sessione(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Operazione annullata.")
    await state.clear()

# --- NUOVA FSM: Pianifica Sessione ---
from services.ai_service import extract_schedule_data
from database.models import Schedule

class PianificaSessione(StatesGroup):
    testo = State()
    conferma = State()

@router.message(Command("pianifica"))
async def cmd_pianifica(message: Message, state: FSMContext):
    await message.answer("Scrivi i dettagli della sessione (es. 'Venerdì dalle 15 alle 17 con Marco').")
    await state.set_state(PianificaSessione.testo)

@router.message(PianificaSessione.testo, F.text)
async def process_pianifica_text(message: Message, state: FSMContext):
    await message.answer("Elaborazione dati in corso...")
    data = await extract_schedule_data(message.text)
    await state.update_data(schedule_data=data)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Salva in Agenda", callback_data="salva_pianifica")],
        [InlineKeyboardButton(text="❌ Annulla", callback_data="annulla_pianifica")]
    ])
    
    await message.answer(f"Dati estratti:\n{json.dumps(data, indent=2)}\n\nConfermi?", reply_markup=markup)
    await state.set_state(PianificaSessione.conferma)

@router.callback_query(PianificaSessione.conferma, F.data == "salva_pianifica")
async def salva_pianifica(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    schedule_data = data['schedule_data']
    
    col = await get_collection("programmazione")
    # Save the raw parsed data to DB
    await col.insert_one(schedule_data)
    
    await callback.message.edit_text("✅ Pianificazione salvata con successo!")
    await state.clear()

@router.callback_query(PianificaSessione.conferma, F.data == "annulla_pianifica")
async def annulla_pianifica(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Operazione annullata.")
    await state.clear()

