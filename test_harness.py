import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

# Handlers and Services
from bot.handlers.commands import cmd_oggi, cmd_esporta
from bot.handlers.fsm_wizards import cmd_nuovo_utente, process_nome, process_ore
from bot.handlers.chat import chat_handler, confirm_tool_call
from database.connection import get_collection

class FakeUser:
    def __init__(self):
        self.id = int(os.getenv("AUTHORIZED_USER_ID", "12345"))
        self.first_name = "TestUser"

class FakeBot:
    async def send_chat_action(self, chat_id, action):
        pass

class FakeChat:
    def __init__(self):
        self.id = 12345

class FakeMessage:
    def __init__(self, text=""):
        self.text = text
        self.from_user = FakeUser()
        self.bot = FakeBot()
        self.chat = FakeChat()
    
    async def answer(self, text, **kwargs):
        print(f"🤖 [BOT MSG]: {text}", flush=True)
        if "reply_markup" in kwargs and kwargs["reply_markup"]:
            # Simula la presenza di bottoni
            print(f"   [BOTTONI INLINE ALLEGATI]", flush=True)
            
    async def edit_text(self, text, **kwargs):
        print(f"🤖 [BOT MSG EDITED]: {text}", flush=True)
            
    async def reply(self, text, **kwargs):
        print(f"🤖 [BOT REPLY]: {text}", flush=True)

    async def answer_document(self, document, **kwargs):
        print(f"🤖 [BOT DOCUMENT]: Inviato file {document.filename}", flush=True)

class FakeCallbackQuery:
    def __init__(self, data):
        self.data = data
        self.from_user = FakeUser()
        self.message = FakeMessage("Messaggio originale con bottoni")
        
    async def answer(self, text=None):
        pass

async def main():
    print("🚀 INIZIO TEST HARNESS E2E (Cold Start)\n", flush=True)
    
    # 1. Setup State Storage
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=FakeUser().id, user_id=FakeUser().id)
    state = FSMContext(storage=storage, key=key)
    
    # 2. Reset database (Pulizia test)
    print("🧹 [TEST] Pulizia utenti di test da MongoDB...", flush=True)
    utenti_col = await get_collection("utenti")
    await utenti_col.delete_many({"nome": "UtenteDiTest123"})
    
    # 3. Test: /nuovo_utente
    print("\n--- TEST: /nuovo_utente ---", flush=True)
    msg1 = FakeMessage("/nuovo_utente")
    await cmd_nuovo_utente(msg1, state)
    
    msg2 = FakeMessage("UtenteDiTest123")
    await process_nome(msg2, state)
    
    msg3 = FakeMessage("15")
    await process_ore(msg3, state)
    
    # 4. Test: Free Chat (Tool Calling)
    print("\n--- TEST: Chat Libera (Mistral Tool Calling) ---", flush=True)
    chat_msg = FakeMessage("Oggi ho fatto 2 ore con UtenteDiTest123 in biblioteca, ha letto 5 pagine in modo eccellente.")
    await chat_handler(chat_msg, state)
    
    # Qui l'agente dovrebbe aver messo lo stato in attesa di conferma con un dict.
    data = await state.get_data()
    pending_tool = data.get("pending_tool")
    if pending_tool:
        print(f"✅ [TEST PASS] Tool intercettato: {pending_tool}", flush=True)
        # 5. Test: Callback Query (Conferma Tool)
        print("\n--- TEST: Conferma Tool (Google Sheets & MongoDB) ---", flush=True)
        cbq = FakeCallbackQuery(data="confirm_tool")
        await confirm_tool_call(cbq, state)
    else:
        print("❌ [TEST FAIL] Nessun tool chiamato da Mistral.", flush=True)

    # 6. Test: /oggi
    print("\n--- TEST: /oggi ---", flush=True)
    msg_oggi = FakeMessage("/oggi")
    await cmd_oggi(msg_oggi, state)
    
    # 7. Test: /esporta
    print("\n--- TEST: /esporta ---", flush=True)
    msg_esporta = FakeMessage("/esporta")
    await cmd_esporta(msg_esporta, state)

    print("\n✅ TEST HARNESS COMPLETATO.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
