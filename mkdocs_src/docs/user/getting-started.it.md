# 🚀 Per iniziare

Benvenuto in LibreFolio! Questa guida ti accompagna nella registrazione di un account, nell'accesso e nell'importazione del tuo primo estratto conto del broker per popolare immediatamente la tua dashboard.

---

## 📝 1. Registra il tuo account

Vai all'URL di LibreFolio (ad es., `http://localhost:6040`) e vedrai la pagina di accesso. Fai clic su **Registrati** per creare un nuovo account.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Registration Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Compila i tuoi dati:

- 👤 **Nome utente**: il tuo nome visualizzato (unico nell'intero sistema)
- 📧 **Email**: un indirizzo email valido
- 🔑 **Password**: una password robusta (l'indicatore di robustezza ti aiuta)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Primo utente = amministratore"

    Il primo utente che si registra diventa automaticamente **amministratore di sistema** (superutente). Questo utente può gestire le impostazioni globali, promuovere altri utenti e accedere a tutte le funzionalità di amministrazione.

---

## 🔐 2. Accedi

Dopo la registrazione, verrai reindirizzato alla pagina di accesso. Inserisci le tue credenziali per accedere alla tua dashboard.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Importa il tuo primo estratto conto (crea broker e asset al volo)

Al primo accesso, ti accoglierà una dashboard vuota, senza alcun dato.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Empty Dashboard" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

In LibreFolio, il modo più rapido per iniziare è importare direttamente la cronologia delle tue transazioni. Non è necessario configurare in anticipo broker o asset: il sistema li creerà automaticamente per te durante il processo di importazione!

### 📋 Passaggi

1. **Apri la procedura guidata di importazione**: vai alla pagina **[Transazioni](transactions/index.md)** dalla barra laterale e fai clic sul pulsante **"Importa"** (:material-file-upload:). Puoi anche partire dalla pagina di dettaglio di un broker — in tal caso il broker risulta già preselezionato.

2. **Carica il tuo estratto conto**: trascina il file del report del tuo broker (`.csv`, `.xlsx` o `.xls`) nel primo passaggio della procedura — qui funziona il drag & drop — e assegalo a un broker, creando il broker **al volo** se è nuovo. Questo passaggio è facoltativo: i report caricati nelle sessioni precedenti sono già memorizzati e il passaggio successivo li elenca.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Upload Step" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

3. **Seleziona i file e analizza**: scegli esattamente quali report memorizzati importare. Per ogni file il parser è preselezionato in base al plugin di importazione predefinito del broker (modificabile per file — usa **CSV generico** per un formato sconosciuto); LibreFolio quindi legge e valida ogni riga. Un riepilogo consolidato mostra ciò che verrà effettivamente importato: transazioni, titoli distinti, problemi di validazione, TODO, avvisi e probabili duplicati.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Parse Step" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

4. **Passaggi aggiuntivi, solo quando necessario**: a seconda di ciò che contengono i tuoi file, possono comparire fino a tre passaggi aggiuntivi — **Unifica asset** (lo stesso titolo trovato con nomi o codici diversi), **Correzioni** (righe che il parser non è riuscito a leggere completamente) e **Duplicati** (lo stesso movimento presente in due file importati insieme). Un report pulito composto da un solo file li salta tutti.

5. **Revisiona e importa**: abbina ogni strumento alla tua libreria di asset — oppure crealo **al volo** con i dettagli precompilati dall'estratto conto — e controlla le flag per ogni riga: i duplicati (rispetto al tuo registro esistente, o copie esatte in sospeso in questa importazione) arrivano deselezionati e le righe antecedenti alla data di apertura del broker vengono escluse automaticamente. Per maggiori informazioni, consulta la guida **[Importa da broker - Mappatura asset](transactions/import/index.md#asset-mapping)**.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Wizard Review Step: Asset Resolution" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

6. **Salva dall'editor in blocco**: facendo clic su **Importa N transazioni**, le righe selezionate vengono passate all'editor in blocco come nuove righe — non viene ancora scritto nulla. Dai loro un'ultima occhiata, poi fai clic su **Salva tutto** per inserirle nel tuo portafoglio.

!!! tip "Non serve ricaricare"

    I report caricati nelle sessioni precedenti sono già elencati nel passaggio **Seleziona file** della procedura — basta rispuntarli. Puoi anche visualizzare in anteprima o eliminare i report memorizzati dalla pagina **[File e upload](files/index.md#broker-reports)**.

Per la guida completa, vedi **[Come importare le transazioni](transactions/import/how-to.md)**; per i broker e i formati di file supportati, vedi **[Importa da broker](transactions/import/index.md)**.

---

## 📈 4. Torna alla dashboard

Dopo aver importato correttamente il tuo estratto conto, torna alla **dashboard**.

LibreFolio calcola le metriche del tuo portafoglio, l'allocazione degli asset (per tipo, settore, area geografica) e la cronologia delle performance in tempo reale. Ora puoi vedere l'intera tua situazione finanziaria splendidamente rappresentata in grafici!

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard Main View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 5. Cosa fare dopo?

Ora che il tuo portafoglio è popolato, puoi:

- 🤝 **[Condividi il tuo broker](brokers/sharing.md)** — concedi l'accesso a familiari o consulenti.
- 💱 **[Configura i tassi di cambio](fx/index.md)** — configura la conversione valutaria per portafogli multi-valuta.
- ⚙️ **[Personalizza le impostazioni](../admin/settings.md)** — regola lingua, tema e preferenze di sistema.
