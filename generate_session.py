import asyncio
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = 6
api_hash = 'eb06d4abfb49dc3eeb1aeb98ae0f581e'

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
