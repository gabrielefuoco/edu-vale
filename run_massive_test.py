import asyncio
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

# Handlers and Services
from bot.handlers.commands import cmd_oggi, cmd_esporta
from bot.handlers.fsm_wizards import cmd_nuovo_utente, process_nome, process_ore
from bot.handlers.chat import chat_handler, confirm_tool_call, cancel_tool_call
from database.connection import get_collection

class FakeUser:
    def __init__(self):
        self.id = int(os.getenv("AUTHORIZED_USER_ID", "12345"))
        self.first_name = "EducatriceTest"

class FakeBot:
    def __init__(self, log_file):
        self.log_file = log_file

    async def send_chat_action(self, chat_id, action):
        pass
    
    def log(self, text):
        print(text, flush=True)
        self.log_file.write(text + "\n")
        self.log_file.flush()

class FakeChat:
    def __init__(self):
        self.id = 12345

class FakeMessage:
    def __init__(self, text, bot):
        self.text = text
        self.from_user = FakeUser()
        self.bot = bot
        self.chat = FakeChat()
        self.voice = None
        # For document export
        self.document_sent = None

    async def answer(self, text, **kwargs):
        self.bot.log(f"🤖 [BOT]: {text}")
        if "reply_markup" in kwargs and kwargs["reply_markup"]:
            self.bot.log("   [BOTTONI INLINE GENERATI]")
            
    async def edit_text(self, text, **kwargs):
        self.bot.log(f"🤖 [BOT EDITATO]: {text}")
            
    async def reply(self, text, **kwargs):
        self.bot.log(f"🤖 [BOT REPLY]: {text}")

    async def answer_document(self, document, **kwargs):
        self.document_sent = document
        self.bot.log(f"🤖 [BOT DOCUMENT]: Inviato file '{document.filename}'")

class FakeCallbackQuery:
    def __init__(self, data, bot, message_text=""):
        self.data = data
        self.from_user = FakeUser()
        self.message = FakeMessage(message_text, bot)
        
    async def answer(self, text=None):
        pass

async def run_massive_simulation():
    log_path = "massive_test.log"
    with open(log_path, "w", encoding="utf-8") as log_file:
        bot = FakeBot(log_file)
        
        bot.log("="*60)
        print(f"Avvio simulazione di 100 messaggi. L'esito sarà scritto in '{log_path}'.")
        bot.log("INIZIO TEST END-TO-END MASSIVO (100 MESSAGGI)")
        bot.log("="*60 + "\n")
        
        # Setup State Storage
        storage = MemoryStorage()
        key = StorageKey(bot_id=1, chat_id=FakeUser().id, user_id=FakeUser().id)
        state = FSMContext(storage=storage, key=key)
        
        # 1. Reset DB
        bot.log("⚙️  [SIMULATION] Ripristino database per utente di test...")
        utenti_col = await get_collection("utenti")
        diario_col = await get_collection("diario_sessioni")
        prog_col = await get_collection("programmazione")
        
        await utenti_col.delete_many({"nome": "AliceMassiveTest"})
        await diario_col.delete_many({"parsed.Utente": "AliceMassiveTest"})
        await prog_col.delete_many({"Utente": "AliceMassiveTest"})
        
        # 2. Registrazione Nuovo Utente (FSM) -> 3 turni
        bot.log("\n--- FASE 1: Creazione Utente ---")
        
        bot.log("👤 [TU]: /nuovo_utente")
        await cmd_nuovo_utente(FakeMessage("/nuovo_utente", bot), state)
        
        bot.log("👤 [TU]: AliceMassiveTest")
        await process_nome(FakeMessage("AliceMassiveTest", bot), state)
        
        bot.log("👤 [TU]: 8")
        await process_ore(FakeMessage("8", bot), state)
        
        # 3. Chiacchierata e inserimenti multipli per forzare summarization (oltre i 15 messaggi)
        bot.log("\n--- FASE 2: Conversazione e Inserimenti Multipli ---")
        
        # Generiamo le battute
        dialogue = [
            "Registra: oggi 3 Luglio ho fatto 1 ora di lezione con AliceMassiveTest in biblioteca. Argomento: analisi logica. E INOLTRE pianifica: 6 Luglio dalle 10 alle 12 incontro con AliceMassiveTest a domicilio in Via Roma 1, Milano.",
            "Registra: ieri 2 Luglio ho fatto 2 ore con AliceMassiveTest online su Zoom. Argomento: verbi ausiliari.",
        ]
        
        # Per forzare il limite di 15 messaggi ed innescare la summarization automatica, 
        # manderemo molte battute di chiacchierata libera e feedback.
        huge_text = "Testo riempitivo per testare la soglia dei 30000 caratteri. " * 600 # Circa 37000 caratteri
        small_talk = [
            f"Oggi il tempo è bellissimo comunque. {huge_text}",
            "Sì, fa caldo ma si lavora bene.",
            "Mi piace molto questo assistente.",
            "Grazie per l'aiuto che mi dai ogni giorno.",
            "AliceMassiveTest sta migliorando davvero tanto, sono felice.",
            "Il suo rendimento scolastico è salito moltissimo nell'ultimo mese.",
            "I genitori di AliceMassiveTest mi hanno ringraziato ieri.",
            "Penso che faremo altre sessioni extra nelle prossime settimane.",
            "Però per ora rimaniamo con le solite ore programmate."
        ]
        
        # Eseguiamo il dialogo principale con conferme dei tool
        for user_msg in dialogue:
            bot.log(f"👤 [TU]: {user_msg}")
            await chat_handler(FakeMessage(user_msg, bot), state)
            
            # Controlla se ci sono tool in attesa (coda) e confermali tutti in sequenza
            while True:
                data = await state.get_data()
                if data.get("pending_tool"):
                    bot.log(f"👤 [TU]: *Clicca ✅ Conferma Azione*")
                    await confirm_tool_call(FakeCallbackQuery("confirm_tool", bot), state)
                else:
                    break
                
        # Eseguiamo la chiacchierata libera per ingolfare il contesto (e forzare summarization)
        bot.log("\n--- FASE 3: Chit-Chat prolungato per innescare summarization (>15 messaggi) ---")
        for st in small_talk:
            bot.log(f"👤 [TU]: {st}")
            await chat_handler(FakeMessage(st, bot), state)
            
            # Verifichiamo se c'è stato summarization controllando il conteggio messaggi
            data = await state.get_data()
            msgs = data.get("messages", [])
            bot.log(f"ℹ️  [Stato RAM Context]: {len(msgs)} messaggi correnti.")
            
        # 4. Pianificazione con Annullamento
        bot.log("\n--- FASE 4: Test Tool di Pianificazione con Annullamento ---")
        bot.log("👤 [TU]: Segna che il 10 Luglio dalle 16 alle 18 ho un appuntamento con AliceMassiveTest in biblioteca.")
        await chat_handler(FakeMessage("Segna che il 10 Luglio dalle 16 alle 18 ho un appuntamento con AliceMassiveTest in biblioteca.", bot), state)
        
        data = await state.get_data()
        if data.get("pending_tool"):
            bot.log("👤 [TU]: *Clicca ❌ Annulla*")
            await cancel_tool_call(FakeCallbackQuery("cancel_tool", bot), state)
            
        # 5. Esecuzione comandi finali
        bot.log("\n--- FASE 5: Controllo Agenda (/oggi) ---")
        bot.log("👤 [TU]: /oggi")
        await cmd_oggi(FakeMessage("/oggi", bot), state)
        
        bot.log("\n--- FASE 6: Esportazione Dati (/esporta) ---")
        bot.log("👤 [TU]: /esporta")
        await cmd_esporta(FakeMessage("/esporta", bot), state)
        
        bot.log("\n" + "="*60)
        bot.log("FINE TEST END-TO-END MASSIVO")
        bot.log("="*60)

if __name__ == "__main__":
    asyncio.run(run_massive_simulation())
