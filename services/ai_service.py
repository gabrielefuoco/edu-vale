import os
from groq import AsyncGroq
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
mistral_llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

async def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as file:
        transcription = await groq_client.audio.transcriptions.create(
            file=(file_path, file.read()), model="whisper-large-v3", prompt="Trascrizione fedele e oggettiva di appunti tecnici. Nessun abbellimento testuale, preserva con massima precisione nomi, date e orari."
        )
    return transcription.text

async def summarize_progress(history_texts: list[str], user_name: str) -> str:
    combined_text = "\n".join(history_texts)
    prompt = (
        f"Genera un report analitico e formale sui progressi dell'utente '{user_name}' basato sui seguenti diari di sessione. "
        "REGOLE:\n"
        "- Mantieni un tono distaccato e professionale.\n"
        "- Struttura il documento in bullet points chiari evidenziando le competenze trattate e le aree di lavoro.\n"
        "- EVITA assolutamente toni celebrativi, esclamazioni o pedagogicamente paternalistici.\n"
        f"Diari:\n{combined_text}"
    )
    
    response = await mistral_llm.ainvoke([HumanMessage(content=prompt)])
    return response.content

