# ⚙️ Impostazioni Globali

LibreFolio dispone di un set di **impostazioni di sistema** che influenzano tutti gli utenti. Queste sono gestite dagli amministratori e memorizzate nel database.

---

## 👁️ Visualizzazione e Modifica delle Impostazioni

### 🖥️ Dalla UI

1. Vai a **Settings** (icona dell'ingranaggio nella barra laterale)
2. Clicca sulla scheda **Global Settings** (visibile solo ad admin/superuser)
3. Clicca l'**icona del lucchetto** accanto a un'impostazione per sbloccarla e modificarla
4. Modifica il valore; la modifica viene salvata automaticamente

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Admin Only"

    Solo gli utenti con privilegi di **superuser** possono modificare le impostazioni globali. Gli utenti regolari hanno accesso a una vista in sola lettura.

### 💻 Dalla CLI

Per inizializzare le impostazioni predefinite (crea solo quelle mancanti):

```bash
./dev.py user init-settings
```

---

## 📋 Impostazioni Disponibili

| Chiave | Tipo | Default | Descrizione |
|-----|------|---------|-------------|
| `session_ttl_hours` | int | `24` | Tempo di scadenza del token JWT in ore. Dopo questo periodo, gli utenti devono effettuare nuovamente il login. |
| `enable_registration` | bool | `true` | Indica se la registrazione di nuovi utenti è consentita. Impostare a `false` per impedire nuove iscrizioni. |
| `require_email_verification` | bool | `false` | Indica se i nuovi utenti devono verificare la propria email prima di accedere al sistema. |
| `max_file_upload_mb` | int | `10` | Dimensione massima del caricamento file in megabyte. Si applica a tutti i caricamenti (risorse statiche e report dei broker). |
| `scheduler_enabled` | bool | `true` | Abilita o disabilita il demone automatico di sincronizzazione in background per tassi di cambio e prezzi storici/real-time. |
| `scheduler_current_price_frequency_minutes` | int | `10` | Frequenza (in minuti) con cui il demone aggiorna le quotazioni correnti in tempo reale (1-1440). |
| `scheduler_history_sync_times` | str | `06:00,23:00` | Orari giornalieri specifici (ora locale del server, separati da virgola) in cui far partire la sincronizzazione storica di chiusura. |
| `scheduler_history_sync_days` | str | `mon,tue,wed,thu,fri,sat` | Giorni della settimana (separati da virgola) in cui eseguire la sincronizzazione storica. |
| `scheduler_history_sync_horizon_days` | int | `14` | Finestra temporale di analisi retrospettiva (in giorni) usata per verificare la mancanza di prezzi storici. |
| `default_currency` | str | `EUR` | Valuta di visualizzazione predefinita per i nuovi utenti registrati. Gli utenti possono sovrascrivere questo valore nelle loro impostazioni personali. |
| `default_language` | str | `en` | Lingua predefinita per i nuovi utenti registrati. Supportate: `en`, `it`, `fr`, `es`. |

---

## 🗂️ Categorie

Le impostazioni sono raggruppate in categorie nella UI:

### 🕐 Sessione
- ⏱️ `session_ttl_hours` — Controlla la durata di una sessione di login

### 🛡️ Sicurezza
- 📝 `enable_registration` — Apri/chiudi la registrazione
- ✉️ `require_email_verification` — Obbligo di verifica email

### 📤 Sync e Caricamenti
- 🕐 `scheduler_enabled` — Abilita o disabilita lo scheduler in background
- ⚡ `scheduler_current_price_frequency_minutes` — Frequenza del recupero prezzi real-time
- 📅 `scheduler_history_sync_times` — Orari della sincronizzazione storica giornaliera
- 📅 `scheduler_history_sync_days` — Giorni della settimana per la sincronizzazione storica
- 🔍 `scheduler_history_sync_horizon_days` — Orizzonte di analisi storica (in giorni)
- 📦 `max_file_upload_mb` — Limite dimensione file

### 🌍 Predefiniti
- 💰 `default_currency` — Valuta predefinita per i nuovi utenti
- 🗣️ `default_language` — Lingua predefinita per i nuovi utenti

---

## 🕐 Scheduler dei Dati di Mercato

Quando lo scheduler in background è abilitato, gli amministratori possono configurare i parametri di sincronizzazione e ispezionare i log di esecuzione in background direttamente dall'interfaccia utente.

### ⚙️ Configura Scheduler

Clicca sul pulsante **Configura** nella riga dello Scheduler per personalizzare le frequenze di esecuzione e i parametri:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modale Configurazione Scheduler" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

* **Current Price Frequency**: La frequenza (in minuti) con cui il demone recupera le quotazioni in tempo reale per mantenere aggiornata la cache della dashboard (default: 10m).
* **History Sync Times**: Orari specifici della giornata (separati da virgola, es. `06:00,23:00`) per eseguire gli aggiornamenti storici di chiusura giornaliera.
* **History Sync Days**: Giorni specifici della settimana in cui viene eseguita la sincronizzazione storica (solitamente da lunedì a sabato).
* **History Horizon**: La finestra di analisi (in giorni) per verificare l'eventuale mancanza di punti prezzo storici (default: 14 giorni).

### 📜 Log dello Scheduler

Clicca su **Visualizza Log** per aprire l'ispettore dei log. Questa modale mostra un elenco delle recenti esecuzioni dello scheduler:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modale Log Scheduler" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Il log riporta il timestamp di esecuzione, il nome del job, lo stato (Success/Error), la durata dell'esecuzione e i dettagli strutturati degli asset elaborati, i feed dei prezzi e eventuali tracce di errore.

---

## 🔧 Note Tecniche

- 🗃️ Le impostazioni sono memorizzate come **coppie chiave-valore** nella tabella `global_settings`
- 🔀 I valori sono memorizzati come stringhe e convertiti nel tipo appropriato (`int`, `bool`, `str`) durante la lettura
- 🔒 All'avvio con più worker, le impostazioni vengono inizializzate con `INSERT ... ON CONFLICT DO NOTHING` per evitare race condition
- ⚡ Le modifiche hanno effetto **immediatamente** — non è richiesto il riavvio del server
