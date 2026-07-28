import os
from groq import AsyncGroq
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
mistral_llm = ChatMistralAI(model="mistral-large-latest", temperature=0)

async def transcribe_audio(file_path: str, known_names: list[str] = None) -> str:
    """Trascrive audio con Groq Whisper, iniettando nomi noti come contesto."""
    names_hint = ""
    if known_names:
        names_hint = f" Nomi noti: {', '.join(known_names)}."
    
    prompt = (
        "Trascrizione in lingua italiana di un messaggio vocale di un operatore educativo. "
        "Preserva con massima precisione nomi propri di persona, date, orari e luoghi. "
        "Non abbreviare, non abbellire, non tradurre in altre lingue."
        f"{names_hint}"
    )
    
    with open(file_path, "rb") as file:
        transcription = await groq_client.audio.transcriptions.create(
            file=(file_path, file.read()),
            model="whisper-large-v3",
            language="it",
            prompt=prompt,
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

