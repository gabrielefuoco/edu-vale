const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

const API_BASE = window.location.origin;
const initData = tg.initData;

const tableBody = document.getElementById('tableBody');
const errorBox = document.getElementById('errorBox');
const refreshBtn = document.getElementById('refreshBtn');

function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.remove('hidden');
}

async function loadData() {
    errorBox.classList.add('hidden');
    tableBody.innerHTML = '<tr><td colspan="4" class="py-4 text-center text-gray-500">Caricamento...</td></tr>';
    
    try {
        const response = await fetch(`${API_BASE}/api/sessions`, {
            headers: {
                'X-Telegram-Init-Data': initData
            }
        });
        
        if (!response.ok) throw new Error("Errore API: " + response.statusText);
        
        const data = await response.json();
        renderTable(data.sessions);
    } catch (e) {
        showError("Impossibile caricare i dati: " + e.message);
    }
}

function renderTable(sessions) {
    tableBody.innerHTML = '';
    if (!sessions || sessions.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="py-4 text-center text-gray-500">Nessuna sessione trovata.</td></tr>';
        return;
    }

    sessions.forEach(s => {
        const p = s.parsed || {};
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="whitespace-nowrap py-2 pl-4 pr-3 text-gray-900">
                <div class="edit-cell" contenteditable="true" data-id="${s._id}" data-field="Giorno">${p.Giorno || ''}</div>
            </td>
            <td class="whitespace-nowrap px-3 py-2 text-gray-900">
                <div class="edit-cell" contenteditable="true" data-id="${s._id}" data-field="Ore">${p.Ore || ''}</div>
            </td>
            <td class="whitespace-nowrap px-3 py-2 text-gray-900">
                <div class="edit-cell" contenteditable="true" data-id="${s._id}" data-field="Utente">${p.Utente || ''}</div>
            </td>
            <td class="px-3 py-2 text-gray-900">
                <div class="edit-cell" contenteditable="true" data-id="${s._id}" data-field="Attività svolte">${p['Attività svolte'] || ''}</div>
            </td>
        `;
        tableBody.appendChild(tr);
    });
    
    // Add event listeners for editing
    document.querySelectorAll('.edit-cell').forEach(cell => {
        let originalContent = cell.innerText;
        
        cell.addEventListener('focus', () => {
            originalContent = cell.innerText;
        });
        
        cell.addEventListener('blur', async () => {
            if (cell.innerText !== originalContent) {
                await updateRecord(cell.dataset.id, cell.dataset.field, cell.innerText, cell);
            }
        });
    });
}

async function updateRecord(id, field, value, cellElement) {
    const originalColor = cellElement.style.backgroundColor;
    cellElement.style.backgroundColor = '#fef08a'; // yellow loading
    
    try {
        const body = {};
        // Per semplicità passiamo solo il campo modificato, ma l'API accetta un aggiornamento unificato.
        body[field] = field === 'Ore' ? parseFloat(value.replace(',','.')) : value;
        
        const response = await fetch(`${API_BASE}/api/sessions/${id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Telegram-Init-Data': initData
            },
            body: JSON.stringify(body)
        });
        
        if (!response.ok) throw new Error("Salvataggio fallito");
        
        cellElement.style.backgroundColor = '#bbf7d0'; // green success
        setTimeout(() => cellElement.style.backgroundColor = originalColor, 1000);
        tg.HapticFeedback.notificationOccurred('success');
    } catch (e) {
        showError("Errore durante il salvataggio: " + e.message);
        cellElement.style.backgroundColor = '#fecaca'; // red error
        tg.HapticFeedback.notificationOccurred('error');
    }
}

refreshBtn.addEventListener('click', loadData);
window.addEventListener('DOMContentLoaded', loadData);
