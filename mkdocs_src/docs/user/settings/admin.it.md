# 🛡️ Impostazioni Globali

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Impostazioni Globali (Admin)">
</div>

!!! warning "Admin access required"

    La scheda **Impostazioni Globali** è visibile solo agli utenti con il ruolo **ADMIN**.

Le impostazioni globali influenzano tutti gli utenti dell'istanza:

| Impostazione | Descrizione |
|---------|-------------|
| **Registrazione** | Abilita o disabilita l'auto-registrazione di nuovi utenti |
| **Lingua Predefinita** | Lingua di fallback per i nuovi utenti |
| **Valuta Predefinita** | Valuta base predefinita per i nuovi account |
| **Timeout Sessione** | Timeout per inattività in minuti |
| **Scheduler** | Abilita o disabilita il demone automatico di sincronizzazione dei dati di mercato in background |

---

## 🕐 Scheduler dei Dati di Mercato

Quando lo scheduler in background è abilitato, gli amministratori possono configurare i parametri di sincronizzazione e ispezionare i log di esecuzione in background direttamente dall'interfaccia utente.

### ⚙️ Configura Scheduler

Clicca sul pulsante **Configura** nella riga dello Scheduler per personalizzare le frequenze di esecuzione e i parametri:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modale Configurazione Scheduler">
</div>

* **Current Price Frequency**: La frequenza (in minuti) con cui il demone recupera le quotazioni in tempo reale per mantenere aggiornata la cache della dashboard (default: 10m).
* **History Sync Times**: Orari specifici della giornata (separati da virgola, es. `06:00,23:00`) per eseguire gli aggiornamenti storici di chiusura giornaliera.
* **History Sync Days**: Giorni specifici della settimana in cui viene eseguita la sincronizzazione storica (solitamente da lunedì a sabato).
* **History Horizon**: La finestra di analisi (in giorni) per verificare l'eventuale mancanza di punti prezzo storici (default: 14 giorni).

### 📜 Log dello Scheduler

Clicca su **Visualizza Log** per aprire l'ispettore dei log. Questa modale mostra un elenco delle recenti esecuzioni dello scheduler:

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modale Log Scheduler">
</div>

Il log riporta il timestamp di esecuzione, il nome del job, lo stato (Success/Error), la durata dell'esecuzione e i dettagli strutturati degli asset elaborati, i feed dei prezzi e eventuali tracce di errore.

---

## 🔗 Correlati

- ⚙️ **[Panoramica Impostazioni](index.md)** — Riepilogo generale delle impostazioni
- 👤 **[Preferenze Utente](preferences.md)** — Profilo e preferenze di visualizzazione
- ℹ️ **[Informazioni](about.md)** — Info versione e licenza
