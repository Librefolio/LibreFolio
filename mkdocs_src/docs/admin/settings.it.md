# ⚙️ Impostazioni Globali

LibreFolio dispone di una serie di **impostazioni a livello di sistema** che interessano tutti gli utenti. Queste sono gestite dagli amministratori e memorizzate nel database.

---

## 👁️ Visualizzazione e modifica delle impostazioni

### 🖥️ Dalla UI

1. Vai su **Impostazioni** (icona dell'ingranaggio nella barra laterale)
2. Fai clic sulla scheda **Impostazioni Globali** (visibile a tutti gli utenti; solo admin/superuser possono modificarla)
3. Fai clic sull'**icona del lucchetto** accanto a un'impostazione per sbloccarla e modificarla
4. Modifica il valore e la modifica viene salvata automaticamente

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Impostazioni Globali" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Solo Amministratori"

    Solo gli utenti con privilegi **superuser** possono modificare le impostazioni globali. Gli utenti normali vedono una vista di sola lettura.

### 💻 Dalla CLI

Per inizializzare le impostazioni predefinite (crea solo quelle mancanti):

```bash
./dev.py user init-settings
```

---

## 🕐 Sessione

| Chiave | Tipo | Predefinito | Descrizione |
|-----|------|---------|-------------|
| `session_ttl_hours` | int | `24` | Tempo di scadenza del token JWT in ore. Dopo questo periodo, gli utenti devono accedere nuovamente. |

## 🛡️ Sicurezza

| Chiave | Tipo | Predefinito | Descrizione |
|-----|------|---------|-------------|
| `enable_registration` | bool | `true` | Indica se la registrazione di nuovi utenti è consentita. Imposta su `false` per impedire nuove iscrizioni. |
| `require_email_verification` | bool | `false` | **Segnaposto — non ancora applicato.** Indica se i nuovi utenti devono verificare la propria email prima di accedere al sistema. L'invio di email (SMTP) è una funzionalità prevista, quindi nella UI questa impostazione è di sola lettura e riporta un'etichetta "coming soon". |

## 🔄 Job di aggiornamento

| Chiave | Tipo | Predefinito | Descrizione |
|-----|------|---------|-------------|
| `scheduler_enabled` | bool | `true` | Abilita o disabilita il daemon di sincronizzazione automatica in background per i tassi di cambio e i prezzi storici/in tempo reale. |

I restanti parametri dello scheduler non vengono mostrati come campi individuali: vengono modificati tutti insieme tramite il modale **Configura** della riga Scheduler — vedi [Scheduler dei dati di mercato](#market-data-scheduler) di seguito.

| Chiave | Tipo | Predefinito | Descrizione |
|-----|------|---------|-------------|
| `scheduler_current_price_frequency_minutes` | int | `10` | Frequenza (in minuti) con cui il daemon aggiorna i prezzi correnti in tempo reale (1-1440). |
| `scheduler_history_sync_times` | str | `06:00,23:00` | Orari HH:MM separati da virgola per la sincronizzazione storica giornaliera, espressi **nel `scheduler_timezone` configurato**. Gli orari vengono memorizzati così come inseriti (orario locale); il daemon converte ogni slot locale in un istante UTC solo quando deve decidere se un job è da eseguire. |
| `scheduler_history_sync_days` | str | `mon,tue,wed,thu,fri,sat` | Giorni specifici della settimana (separati da virgola) per eseguire la sincronizzazione storica. |
| `scheduler_history_sync_horizon_days` | int | `14` | Finestra mobile di analisi retrospettiva (in giorni) utilizzata per verificare la presenza di prezzi storici mancanti. |
| `scheduler_timezone` | str | `UTC` | Fuso orario IANA utilizzato per **memorizzare e valutare** i giorni e gli orari di sincronizzazione storica dello scheduler. Gli orari/giorni configurati sono espressi in ora locale di questa zona; i valori non validi vengono riportati a UTC. |

## 🧠 Memoria

| Chiave | Tipo | Predefinito | Descrizione |
|-----|------|---------|-------------|
| `max_file_upload_mb` | int | `10` | Dimensione massima di caricamento dei file in megabyte. Si applica a tutti i caricamenti (risorse statiche e report del broker). |

La categoria Memoria ospita anche il pannello **Cache del server** — vedi [Cache del server](#server-caches) di seguito.

## 🌍 Predefiniti

| Chiave | Tipo | Predefinito | Descrizione |
|-----|------|---------|-------------|
| `default_currency` | str | `EUR` | Valuta di visualizzazione predefinita per i nuovi utenti registrati. Gli utenti possono modificarla nelle proprie impostazioni personali. |
| `default_language` | str | `en` | Lingua predefinita per i nuovi utenti registrati. Supportate: 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr`, 🇪🇸 `es`. |
| `default_theme` | str | `auto` | Tema predefinito per i nuovi utenti registrati: ☀️ `light`, 🌙 `dark`, 🖥️ `auto`. |

---

## 🕐 Scheduler dei dati di mercato {: #market-data-scheduler }

Quando lo scheduler in background è abilitato, gli amministratori possono configurare i parametri di sincronizzazione e ispezionare i log di esecuzione in background direttamente dall'interfaccia utente.

### ⚙️ Configura Scheduler

Fai clic sul pulsante **Configura** nella riga Scheduler per personalizzare le frequenze e i parametri di esecuzione:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modale di Configurazione dello Scheduler" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

* **Frequenza del prezzo corrente**: La frequenza (in minuti) con cui il daemon recupera le quotazioni in tempo reale per mantenere aggiornata la cache della dashboard (predefinita: 10 min).
* **Orari di sincronizzazione storica**: Orari giornalieri specifici (separati da virgola, es. `06:00,23:00`) per eseguire gli aggiornamenti giornalieri delle chiusure storiche. Gli orari indicano l'ora locale **del fuso orario dello scheduler configurato**.
* **Giorni di sincronizzazione storica**: Giorni specifici della settimana in cui viene eseguita la sincronizzazione storica (di solito dal lunedì al sabato), valutati anch'essi nel fuso orario dello scheduler.
* **Orizzonte storico**: La finestra di analisi (in giorni) per verificare i punti di prezzo storici mancanti (predefinita: 14 giorni).
* **Fuso orario**: Il fuso orario IANA (`scheduler_timezone`) in cui vengono memorizzati e valutati gli orari e i giorni sopra indicati. Il modale mostra a fianco l'orologio UTC del server, così puoi valutare lo scostamento; il backend converte ogni slot locale in un istante UTC solo quando deve decidere se un job è da eseguire. I valori non validi vengono riportati a UTC.

### 📜 Log dello Scheduler

Fai clic su **Visualizza Log** per aprire il visualizzatore dei log. Questo modale mostra un elenco delle esecuzioni recenti dello scheduler:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modale dei Log dello Scheduler" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Il log riporta il timestamp di esecuzione, il nome del job, lo stato (Success/Error), la durata dell'esecuzione e i dettagli strutturati degli asset elaborati, dei feed di prezzi e di eventuali tracce di errore.

---

## 🗄️ Cache del server {: #server-caches }

LibreFolio mantiene diverse **cache in memoria** sul backend (recupero dei prezzi, risultati di ricerca, calcoli di portafoglio, risposte dei provider e altro) in modo che le richieste ripetute non debbano interrogare i provider di dati esterni ogni volta. La scheda **Impostazioni Globali** termina con un **pannello Cache** (categoria Memoria) che elenca ogni cache registrata per nome, con le colonne **dimensione corrente / dimensione massima** e **TTL** (time-to-live) — ogni intestazione di colonna è cliccabile per ordinare per nome, dimensione o TTL; un pulsante **Aggiorna** rilegge le statistiche in tempo reale.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Pannello delle cache del server nelle Impostazioni Globali (categoria Memoria)">
</div>

**Chi può fare cosa:**

- 👁️ **La lettura dello stato** è disponibile per **qualsiasi utente autenticato** (`GET /api/v1/settings/cache/status`).
- 🧹 **Lo svuotamento** è **solo per admin e richiede che la pagina sia sbloccata** (i pulsanti appaiono solo per i superuser in modalità di modifica): ogni riga ha il proprio pulsante **Svuota** (`POST /api/v1/settings/cache/clear/{name}`) e l'intestazione del pannello ha un pulsante **Svuota tutto** (`POST /api/v1/settings/cache/clear-all`).

!!! warning "Lo svuotamento di una cache rallenta il recupero successivo"

    Entrambe le azioni di svuotamento richiedono una conferma, per una buona ragione: dopo uno svuotamento, la richiesta successiva per quei dati **interroga nuovamente i provider esterni**, quindi prevedi un rallentamento paragonabile a un riavvio del server mentre le cache si ricostruiscono. Le cache si svuotano anche a ogni riavvio del server — lo svuotamento è utile solo per forzare il recupero di dati aggiornati senza riavviare.

---

## 🔧 Note tecniche

- 🗃️ Le impostazioni sono memorizzate come **coppie chiave-valore** nella tabella `global_settings`
- 🔀 I valori sono memorizzati come stringhe e convertiti nel tipo appropriato (`int`, `bool`, `str`) quando vengono letti
- 🔒 All'avvio multi-worker, le impostazioni vengono inizializzate con `INSERT ... ON CONFLICT DO NOTHING` per evitare condizioni di corsa
- ⚡ Le modifiche hanno effetto **immediatamente** — non è richiesto alcun riavvio del server
