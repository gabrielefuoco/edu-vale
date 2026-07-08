import asyncio
import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

load_dotenv()
api_id = int(os.getenv("TELEGRAM_API_ID"))
api_hash = os.getenv("TELEGRAM_API_HASH")

async def main():
    print("Premi INVIO e inserisci il tuo numero di telefono quando richiesto (es. +39334...).")
    print("Telegram ti manderà un codice. Inseriscilo.")
    
    # Usiamo StringSession() vuoto per crearne uno nuovo
    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        print("\n" + "="*50)
        print("✅ LOGIN EFFETTUATO CON SUCCESSO!")
        print("COPIA L'INTERA STRINGA QUI SOTTO E INCOLLALA ALL'AGENTE (ANTIGRAVITY):")
        print("="*50)
        print(client.session.save())
        print("="*50)

if __name__ == '__main__':
    asyncio.run(main())
