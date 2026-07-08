import pytest
from langchain_core.runnables import RunnableConfig
from tools.write_tools import registra_sessione, crea_utente
from tools.read_tools import cerca_utenti

@pytest.mark.asyncio
async def test_registra_sessione_tool(mock_db):
    config = RunnableConfig(configurable={"user_id": "12345"})
    
    res = await registra_sessione.ainvoke({
        "Giorno": "2026-07-04",
        "Ore": 2.0,
        "Utente": "Luigi",
        "Attivita_svolte": "Fatto compiti",
        "Luogo": "Scuola"
    }, config=config)
    
    assert "registrata" in res
    
    col = mock_db["edu_agent_default"]["diario_sessioni"]
    docs = await col.find().to_list(10)
    assert len(docs) == 1
    assert docs[0]["utente_id"] == "Luigi"

@pytest.mark.asyncio
async def test_crea_utente_duplicate(mock_db):
    config = RunnableConfig(configurable={"user_id": "12345"})
    
    # 1. Creiamo il primo utente
    await crea_utente.ainvoke({"nome": "Mario Rossi", "ore_settimanali": 10}, config=config)
    
    # 2. Tentiamo di crearne uno identico
    res = await crea_utente.ainvoke({"nome": "Mario Rossi", "ore_settimanali": 5}, config=config)
    assert "esiste già" in res
    
    col = mock_db["edu_agent_default"]["utenti"]
    count = await col.count_documents({})
    assert count == 1 # Non deve averlo duplicato

@pytest.mark.asyncio
async def test_cerca_utenti_tool(mock_db):
    config = RunnableConfig(configurable={"user_id": "12345"})
    await crea_utente.ainvoke({"nome": "Luigi Bianchi", "ore_settimanali": 5}, config=config)
    
    res = await cerca_utenti.ainvoke({"query": "luigi"}, config=config)
    assert "Luigi Bianchi" in res
    
    res_empty = await cerca_utenti.ainvoke({"query": "giovanna"}, config=config)
    assert "Nessun utente trovato" in res_empty
