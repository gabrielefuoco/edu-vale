from datetime import datetime
from zoneinfo import ZoneInfo
from bson import ObjectId

from database.connection import get_collection


async def execute_single_tool(fn_name: str, fn_args: dict, messages: list) -> tuple[str, str, list]:
    icona = "✅"
    res_text = ""
    
    if fn_name == "registra_sessione":
        col = await get_collection("diario_sessioni")
        await col.insert_one({"parsed": fn_args, "timestamp": datetime.now(ZoneInfo("Europe/Rome"))})
        
        icona = "✅"
        res_text = f"Sessione registrata nel Database: {fn_args.get('Utente')} ({fn_args.get('Ore')}h)."
        messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Sessione registrata nel DB."})
        
    elif fn_name == "pianifica_sessione":
        col = await get_collection("programmazione")
        await col.insert_one(fn_args)
        res_text = f"Sessione pianificata: {fn_args.get('Utente')} il {fn_args.get('Data')}"
        messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Sessione pianificata con successo."})
        
    elif fn_name == "crea_utente":
        col = await get_collection("utenti")
        existing = await col.find_one({"nome": {"$regex": f"^{fn_args.get('nome')}$", "$options": "i"}})
        if not existing:
            await col.insert_one({
                "nome": fn_args.get("nome"),
                "ore_settimanali": fn_args.get("ore_settimanali", 0),
                "preferenze": fn_args.get("preferenze", ""),
                "note": []
            })
            res_text = f"Utente creato: {fn_args.get('nome')}"
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Utente creato con successo."})
        else:
            icona = "⚠️"
            res_text = f"Creazione ignorata: {fn_args.get('nome')} esiste già."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' ignorata: L'utente esisteva già."})
            
    elif fn_name == "elimina_utente":
        col = await get_collection("utenti")
        result = await col.delete_one({"nome": {"$regex": f"^{fn_args.get('nome_utente')}$", "$options": "i"}})
        if result.deleted_count > 0:
            res_text = f"Utente {fn_args.get('nome_utente')} eliminato."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Utente eliminato."})
        else:
            icona = "⚠️"
            res_text = "Impossibile eliminare: utente non trovato."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita: Utente non trovato."})
            
    elif fn_name == "elimina_sessione_pianificata":
        col = await get_collection("programmazione")
        result = await col.delete_one({"Data": fn_args.get("Data"), "Utente": {"$regex": fn_args.get("Utente", ""), "$options": "i"}})
        if result.deleted_count > 0:
            res_text = f"Sessione annullata: {fn_args.get('Utente')} il {fn_args.get('Data')}"
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Sessione annullata con successo."})
        else:
            icona = "⚠️"
            res_text = f"Impossibile annullare: nessuna sessione trovata per {fn_args.get('Utente')} il {fn_args.get('Data')}"
            messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita: Nessuna sessione trovata da annullare."})
            
    elif fn_name == "modifica_sessione_pianificata":
        col = await get_collection("programmazione")
        update_data = {}
        if fn_args.get("Nuova_Data"): update_data["Data"] = fn_args["Nuova_Data"]
        if fn_args.get("Nuova Ora Inizio"): update_data["Ora Inizio"] = fn_args["Nuova Ora Inizio"]
        if fn_args.get("Nuova Ora Fine"): update_data["Ora Fine"] = fn_args["Nuova Ora Fine"]
        if fn_args.get("Nuovo_Luogo"): update_data["Luogo"] = fn_args["Nuovo_Luogo"]
        
        if update_data:
            result = await col.update_one(
                {"Data": fn_args.get("Data_Attuale"), "Utente": {"$regex": fn_args.get("Utente", ""), "$options": "i"}},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                res_text = f"Agenda modificata per {fn_args.get('Utente')}"
                messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Agenda aggiornata."})
            else:
                icona = "⚠️"
                res_text = "Nessuna sessione trovata da modificare."
                messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita: Sessione non trovata."})
        else:
            icona = "⚠️"
            res_text = "Nessuna modifica specificata."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' ignorata."})
            
    elif fn_name == "modifica_sessione_passata":
        col = await get_collection("diario_sessioni")
        id_sess = fn_args.get("id_sessione")
        update_data = {}
        if fn_args.get("Nuova_Data"): update_data["parsed.Giorno"] = fn_args["Nuova_Data"]
        if fn_args.get("Nuove_Ore"): update_data["parsed.Ore"] = fn_args["Nuove_Ore"]
        if fn_args.get("Nuove Attività"): update_data["parsed.Attività svolte"] = fn_args["Nuove Attività"]
        
        if update_data:
            try:
                obj_id = ObjectId(id_sess)
                result = await col.update_one({"_id": obj_id}, {"$set": update_data})
                if result.modified_count > 0:
                    doc = await col.find_one({"_id": obj_id})
                    res_text = "Sessione passata modificata con successo nel DB."
                    messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: DB aggiornato."})
                else:
                    icona = "⚠️"
                    res_text = "Nessuna sessione trovata con quell'ID."
                    messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita: ID non trovato."})
            except Exception as e:
                icona = "⚠️"
                res_text = f"Errore ID: {e}"
                messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita."})
        else:
            icona = "⚠️"
            res_text = "Nessun campo modificato."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' ignorata."})
            
    elif fn_name == "elimina_sessione_passata":
        col = await get_collection("diario_sessioni")
        id_sess = fn_args.get("id_sessione")
        try:
            obj_id = ObjectId(id_sess)
            doc = await col.find_one({"_id": obj_id})
            if doc:
                await col.delete_one({"_id": obj_id})
                res_text = "Sessione passata eliminata."
                messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: eliminata da DB."})
            else:
                icona = "⚠️"
                res_text = "Sessione non trovata."
                messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita."})
        except Exception as e:
            icona = "⚠️"
            res_text = f"Errore ID: {e}"
            messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita."})
            
    elif fn_name == "modifica_utente":
        col = await get_collection("utenti")
        update_data = {}
        if "ore_settimanali" in fn_args:
            update_data["ore_settimanali"] = fn_args["ore_settimanali"]
        if "preferenze" in fn_args:
            update_data["preferenze"] = fn_args["preferenze"]
            
        if update_data:
            await col.update_one({"nome": {"$regex": fn_args.get("nome_utente", ""), "$options": "i"}}, {"$set": update_data})
            res_text = f"Utente {fn_args.get('nome_utente', '')} aggiornato."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Utente aggiornato con successo."})
        else:
            icona = "⚠️"
            res_text = f"Nessun campo da aggiornare per {fn_args.get('nome_utente', '')}."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' ignorata: Nessuna modifica specificata."})

    elif fn_name == "aggiungi_nota_utente":
        col = await get_collection("utenti")
        utente = fn_args.get("nome_utente", "")
        doc = await col.find_one({"nome": {"$regex": f"^{utente}$", "$options": "i"}})
        if doc:
            note_list = doc.get("note", [])
            new_id = 1
            if note_list:
                new_id = max([n.get("id", 0) for n in note_list]) + 1
            await col.update_one(
                {"_id": doc["_id"]},
                {"$push": {"note": {"id": new_id, "testo": fn_args.get("nota_testuale")}}}
            )
            res_text = f"Nota episodica salvata (ID: {new_id})."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata: Nota aggiunta."})
        else:
            icona = "⚠️"
            res_text = "Utente non trovato."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita: Utente non trovato."})
            
    elif fn_name == "modifica_nota_utente":
        col = await get_collection("utenti")
        utente = fn_args.get("nome_utente", "")
        id_nota = fn_args.get("id_nota")
        nuovo_testo = fn_args.get("nuovo_testo")
        
        result = await col.update_one(
            {"nome": {"$regex": f"^{utente}$", "$options": "i"}, "note.id": id_nota},
            {"$set": {"note.$.testo": nuovo_testo}}
        )
        if result.modified_count > 0:
            res_text = f"Nota {id_nota} modificata."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata."})
        else:
            icona = "⚠️"
            res_text = "Utente o ID nota non trovati."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita."})
            
    elif fn_name == "elimina_nota_utente":
        col = await get_collection("utenti")
        utente = fn_args.get("nome_utente", "")
        id_nota = fn_args.get("id_nota")
        
        result = await col.update_one(
            {"nome": {"$regex": f"^{utente}$", "$options": "i"}},
            {"$pull": {"note": {"id": id_nota}}}
        )
        if result.modified_count > 0:
            res_text = f"Nota {id_nota} eliminata."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' confermata."})
        else:
            icona = "⚠️"
            res_text = "Utente o ID nota non trovati."
            messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita."})
            
    else:
        icona = "❌"
        res_text = f"Errore: Tool sconosciuto ({fn_name})."
        messages.append({"role": "system", "content": f"Azione '{fn_name}' fallita: Tool sconosciuto."})
        
    return icona, res_text, messages
