import os
from dotenv import load_dotenv
load_dotenv()

from services.ai_service import transcribe_audio
import asyncio

async def main():
    print('Testing Groq client initialization...')
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=os.getenv('GROQ_API_KEY'))
        print('Groq client initialized successfully!')
        
        # Test if GROQ_API_KEY is actually valid by calling models
        models = await client.models.list()
        print('Groq models retrieved successfully! API key is valid.')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    asyncio.run(main())
