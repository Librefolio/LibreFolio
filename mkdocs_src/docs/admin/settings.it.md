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
| `auto_sync_fx_rates` | bool | `true` | Abilita la sincronizzazione giornaliera automatica dei tassi di cambio dai provider configurati. |
| `auto_sync_prices` | bool | `true` | Abilita la sincronizzazione automatica dei prezzi degli asset dai provider (Yahoo Finance, ecc.). |
| `price_sync_interval_hours` | int | `6` | Frequenza di sincronizzazione dei prezzi degli asset, in ore. |
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
- 💱 `auto_sync_fx_rates` — Sincronizzazione automatica dei tassi di cambio
- 📈 `auto_sync_prices` — Sincronizzazione automatica prezzi asset
- ⏰ `price_sync_interval_hours` — Frequenza sincronizzazione prezzi
- 📦 `max_file_upload_mb` — Limite dimensione file

### 🌍 Predefiniti
- 💰 `default_currency` — Valuta predefinita per i nuovi utenti
- 🗣️ `default_language` — Lingua predefinita per i nuovi utenti

---

## 🔧 Note Tecniche

- 🗃️ Le impostazioni sono memorizzate come **coppie chiave-valore** nella tabella `global_settings`
- 🔀 I valori sono memorizzati come stringhe e convertiti nel tipo appropriato (`int`, `bool`, `str`) durante la lettura
- 🔒 All'avvio con più worker, le impostazioni vengono inizializzate con `INSERT ... ON CONFLICT DO NOTHING` per evitare race condition
- ⚡ Le modifiche hanno effetto **immediatamente** — non è richiesto il riavvio del server
