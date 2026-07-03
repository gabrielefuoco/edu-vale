# Guida per il Recupero delle Chiavi API e Variabili d'Ambiente

Per far funzionare Edu-Agent, devi compilare il file `.env` con alcune chiavi segrete. Ecco dove trovare ciascuna di esse:

### 1. `TELEGRAM_BOT_TOKEN`
- **Cosa fa:** Permette al codice di controllare il tuo bot su Telegram.
- **Dove trovarlo:**
  1. Apri Telegram e cerca l'utente `@BotFather`.
  2. Invia il comando `/newbot` e segui le istruzioni per creare il bot.
  3. Alla fine, BotFather ti darà un token (una lunga stringa di lettere e numeri). Copialo e incollalo qui.

### 2. `AUTHORIZED_USER_ID`
- **Cosa fa:** È il tuo ID personale di Telegram. Impedisce ad altri di usare il tuo bot.
- **Dove trovarlo:**
  1. Su Telegram, cerca il bot `@userinfobot` (o simili, come `@myidbot`).
  2. Avvialo e ti risponderà con il tuo `Id`. È una stringa numerica (es. `123456789`).

### 3. `GROQ_API_KEY`
- **Cosa fa:** Permette di usare i server di Groq per trascrivere velocemente e gratis i tuoi audio (modello Whisper).
- **Dove trovarlo:**
  1. Vai su [console.groq.com](https://console.groq.com/) e fai il login.
  2. Vai nella sezione "API Keys" e clicca su "Create API Key".

### 4. `MISTRAL_API_KEY`
- **Cosa fa:** È il "cervello" per capire i tuoi intenti e strutturare il json (modelli Mistral Small/Large).
- **Dove trovarlo:**
  1. Vai su [console.mistral.ai](https://console.mistral.ai/) e crea un account.
  2. Vai su "API Keys" e generane una nuova. (Nota: potresti dover inserire un metodo di pagamento per accedere all'API, anche se i costi sono minuscoli, in alternativa puoi usare di nuovo Groq se preferisci modelli open come LLaMA 3 per tutto).

### 5. `MONGODB_URI`
- **Cosa fa:** È la stringa di connessione al tuo database cloud su MongoDB Atlas.
- **Nota bene:** Se hai già un cluster gratuito (M0) su Atlas per un altro progetto, **puoi usare tranquillamente quello**. Il bot creerà automaticamente un nuovo database separato chiamato `edu_agent` al suo interno, senza toccare i dati dell'altro progetto!
- **Dove trovarlo:**
  1. Vai su [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas) e fai il login.
  2. Seleziona il tuo cluster esistente e clicca su "Connect" (oppure vai in "Database Access" per assicurarti di ricordare le credenziali dell'utente e in "Network Access" per accertarti che l'IP `0.0.0.0/0` sia abilitato).
  3. Scegli "Drivers" (Python) e copia la stringa URI. Assicurati di sostituire `<password>` con la tua password.

### 6. `GOOGLE_SHEETS_CREDENTIALS_FILE` & `GOOGLE_SHEET_URL`
- **Cosa fa:** Permette al bot di scrivere sul tuo foglio di calcolo.
- **Dove trovarlo (Credentials File):**
  1. Vai sulla [Google Cloud Console](https://console.cloud.google.com/).
  2. Crea un nuovo progetto e abilita l'API "Google Sheets API" e "Google Drive API".
  3. Vai su "APIs & Services" -> "Credentials" -> "Create Credentials" -> "Service Account".
  4. Una volta creato, clicca sul Service Account, vai su "Keys" -> "Add Key" -> "Create new key" -> JSON. Scaricherai un file `.json`. Spostalo nella cartella del progetto e metti il nome del file in questa variabile (es. `credenziali.json`).
- **Passaggio extra fondamentale:** Apri il tuo file JSON, copia l'indirizzo email `client_email`. Vai sul tuo Foglio Google, clicca "Condividi" in alto a destra e condividilo con questa email (dandogli i permessi di "Editor").
- **Google Sheet URL:** Copia e incolla semplicemente l'URL completo del tuo foglio Google.

---
Una volta recuperati questi dati, duplica il file `.env.example`, rinominalo in `.env` e riempilo!
