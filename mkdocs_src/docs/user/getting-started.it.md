# 🚀 Guida Iniziale

Benvenuto in LibreFolio! Questa guida ti accompagnerà nella registrazione di un account, nel login e nell'importazione del tuo primo estratto conto per popolare istantaneamente la tua dashboard.

---

## 📝 1. Registra il tuo Account

Vai all'URL di LibreFolio (ad es. `http://localhost:6040`) e vedrai la pagina di login. Clicca su **Register** per creare un nuovo account.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Registration Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Inserisci i tuoi dati:

- 👤 **Username**: Il tuo nome visualizzato (unico all'interno del sistema)
- 📧 **Email**: Un indirizzo email valido
- 🔑 **Password**: Una password sicura (l'indicatore di forza ti aiuterà)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Primo Utente = Admin"

    Il primo utente a registrarsi diventa automaticamente l'**amministratore di sistema** (superuser). Questo utente può gestire le impostazioni globali, promuovere altri utenti e accedere a tutte le funzioni di amministrazione.

---

## 🔐 2. Accedi

Dopo la registrazione, verrai reindirizzato alla pagina di login. Inserisci le tue credenziali per accedere alla tua dashboard.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Importa il tuo Primo Estratto Conto (Crea Broker e Asset al Volo)

Al tuo primo accesso, sarai accolto da una dashboard completamente vuota e senza dati.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Dashboard Vuota" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

In LibreFolio, il modo più rapido per iniziare è importare direttamente la cronologia delle tue transazioni. Non è necessario configurare broker o asset in precedenza: il sistema li creerà automaticamente durante il processo di importazione!

### 📋 Passaggi

1. **Carica l'Estratto Conto**: Vai alla pagina delle **[Transazioni](transactions/index.md)** dal menu laterale. Clicca sul pulsante **"Importa"** (:material-file-upload:) oppure trascina e rilascia (**drag & drop**) il file del report del tuo broker (CSV o PDF) direttamente sulla pagina.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Step 1: Caricamento" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

2. **Configurazione Parser**: Il wizard rileverà automaticamente il formato dell'estratto conto. Puoi verificare le impostazioni (come formato date e delimitatori) e configurare le opzioni di fallback se stai caricando un report CSV generico.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Wizard Step 2: Configurazione Parser" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
    
    !!! tip "Ri-processare gli estratti conto esistenti"
    
        Puoi anche ri-elaborare (re-process) qualsiasi estratto conto precedentemente caricato direttamente dalla pagina **[File e Caricamenti](files/index.md#broker-reports)**. Questo è particolarmente utile dopo l'aggiornamento di un plugin di importazione o se hai accidentalmente cancellato alcune transazioni e desideri ripristinarle.

3. **Analisi & Parsing**: Il sistema legge, convalida ed elabora le righe dell'estratto conto. Verrà mostrata una barra di avanzamento che indica lo stato e la velocità di parsing.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Step 3: Analisi" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Risoluzione Broker e Asset**: Se il report contiene un conto broker o degli asset (come ETF, azioni) non ancora configurati in LibreFolio, il sistema li segnalerà. Puoi cercarli tra quelli esistenti o crearli **al volo** (on-the-fly) direttamente nel wizard con i dati precompilati. Per maggiori dettagli, consulta la guida **[Importazione da Broker - Asset Mapping](transactions/import/index.md#asset-mapping)**.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Wizard Step 4: Risoluzione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Rilevamento Duplicati**: Il wizard confronta le transazioni dell'estratto conto con quelle già presenti nel database. Raggruppa le potenziali corrispondenze in due badge di stato dell'interfaccia utente basandosi su 4 livelli di confidenza:
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Wizard Step 5: Rilevamento Duplicati" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
    
    | Badge UI | Livello di Confidenza | Criterio / Regole di Abbinamento |
    | :--- | :--- | :--- |
    | <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Campi base e descrizione corrispondono, ed asset risolto automaticamente (duplicato altamente probabile). |
    | <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Campi base e descrizione corrispondono, ma l'asset non è risolto. |
    | <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Campi base corrispondono, ed asset risolto automaticamente (ma la descrizione differisce o è vuota). |
    | <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Campi base (tipo, data, quantità, importo) corrispondono, ma l'asset non è risolto. |
    | <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNICO</span> | — | La transazione non presenta alcuna corrispondenza nel database e viene considerata come nuova (duplicazione esclusa). |
    | <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ NON RISOLTO</span> | — | Il broker o lo strumento finanziario non sono stati abbinati a entità esistenti nel database (richiede risoluzione nello Step 4 prima di poter importare). |

    Per maggiori dettagli sulle regole e la configurazione dei duplicati, consulta la sezione **[Import from Broker - Duplicate Detection](transactions/import/index.md#duplicate-detection)**.

6. **Staging e Revisione Finale**: Controlla l'anteprima di tutte le transazioni elaborate. Dopo aver verificato che tutto sia corretto, clicca su **Importa** per salvare le transazioni nel tuo portafoglio.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Wizard Step 6: Revisione Massiva" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

    La tabella di revisione di staging mostra le seguenti colonne:

    - **Date**: La data di esecuzione della transazione.
    - **Type**: Il tipo di operazione finanziaria (ACQUISTO, VENDITA, DIVIDENDO, VERSAMENTO, ecc.).
    - **Asset**: L'asset abbinato dalla tua libreria.
    - **Quantity**: Il numero di quote o unità scambiate.
    - **Price**: Il prezzo unitario dell'asset.
    - **Net Amount**: L'impatto di cassa totale (positivo o negativo) sul conto.
    - **Fees/Taxes**: Commissioni del broker o tasse di transazione incluse.

    Per le impostazioni avanzate o errori di convalida nello staging, consulta la pagina **[Import from Broker](transactions/import/index.md)**.

---

## 📈 4. Ritorno in Dashboard

Dopo aver completato l'importazione con successo, torna alla **Dashboard**.

LibreFolio calcolerà in tempo reale tutte le metriche del portafoglio, l'allocazione degli asset (per tipo, settore, area geografica) e lo storico delle performance. Ora puoi finalmente vedere l'intera situazione attuale del tuo portafoglio visualizzata graficamente!

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 5. E adesso?

Ora che il tuo portafoglio è popolato, puoi:

- 🤝 **[Condividere il tuo broker](brokers/sharing.md)** — Concedi l'accesso a familiari o consulenti.
- 💱 **[Configurare i tassi di cambio](fx/index.md)** — Configura la conversione valutaria per portafogli multi-valuta.
- ⚙️ **[Personalizzare le impostazioni](../admin/settings.md)** — Regola lingua, tema e preferenze di sistema.
