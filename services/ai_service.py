import os
import json
from datetime import datetime
from groq import AsyncGroq
from mistralai.async_client import MistralAsyncClient
from mistralai.models.chat_completion import ChatMessage

groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
mistral_client = MistralAsyncClient(api_key=os.getenv("MISTRAL_API_KEY"))

async def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as file:
        transcription = await groq_client.audio.transcriptions.create(
            file=(file_path, file.read()), model="whisper-large-v3", prompt="Trascrizione fedele e oggettiva di appunti tecnici. Nessun abbellimento testuale, preserva con massima precisione nomi, date e orari."
        )
    return transcription.text

async def extract_session_data(text: str) -> dict:
    prompt = (
        "Analizza il testo seguente ed estrai in modo asettico i dati operativi. "
        "Restituisci RIGOROSAMENTE E SOLO un oggetto JSON valido con queste chiavi: "
        "\"Giorno\" (es. YYYY-MM-DD), \"Ore\" (numero float), \"Utente\" (nome), "
        "\"Luogo\" (stringa), \"Attività svolte\" (stringa oggettiva, rimuovi giudizi). "
        "Nessun commento prima o dopo il JSON.\n"
        f"Testo: {text}"
    )
    response = await mistral_client.chat(
        model="mistral-small-latest",
        messages=[ChatMessage(role="user", content=prompt)],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

async def extract_schedule_data(text: str) -> dict:
    prompt = (
        f"Analizza il testo seguente per estrarre i dati di pianificazione. Usa la data odierna come base: {datetime.now().strftime('%Y-%m-%d')}. "
        "Restituisci RIGOROSAMENTE E SOLO un oggetto JSON valido con: "
        "\"Data\" (YYYY-MM-DD), \"Ora Inizio\" (HH:MM), \"Ora Fine\" (HH:MM), "
        "\"Utente\" (nome), \"Luogo\" (stringa o null se assente). "
        "Nessun commento testuale di accompagnamento.\n"
        f"Testo: {text}"
    )
    response = await mistral_client.chat(
        model="mistral-small-latest",
        messages=[ChatMessage(role="user", content=prompt)],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

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
    response = await mistral_client.chat(model="mistral-large-latest", messages=[ChatMessage(role="user", content=prompt)])
    return response.choices[0].message.content
