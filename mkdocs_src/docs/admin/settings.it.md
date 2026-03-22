# ⚙️ Impostazioni Globali

LibreFolio ha un set di **impostazioni di sistema** che riguardano tutti gli utenti. Sono gestite dagli amministratori e archiviate nel database.

---

## 👁️ Visualizzare e Modificare le Impostazioni

### 🖥️ Tramite l'UI

1. Vai su **Impostazioni** (icona dell'ingranaggio nella barra laterale)
2. Clicca sulla scheda **Impostazioni Globali** (visibile solo per amministratore/superutente)
3. Clicca sull'**icona del lucchetto** accanto a un'impostazione per sbloccarla per la modifica
4. Modifica il valore e la modifica viene salvata automaticamente

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Impostazioni Globali" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "**Solo Superutenti**"
 Solo gli utenti con privilegi di **superutente** possono modificare le impostazioni globali. Gli utenti standard vedono una vista di sola lettura.

### 💻 Tramite CLI

Per inizializzare le impostazioni predefinite (crea solo quelle mancanti):

```bash
./dev.py user init-settings
```

---

## 📋 Impostazioni Disponibili

| Chiave | Tipo | Predefinito | Descrizione |
|-----|------|---------|-------------|
| `session_ttl_hours` | int | `24` | Tempo di scadenza del token JWT in ore. Dopo questo periodo, gli utenti devono accedere di nuovo. |
| `enable_registration` | bool | `true` | Indica se la registrazione di nuovi utenti è consentita. Imposta a `false` per bloccare nuove iscrizioni. |
| `require_email_verification` | bool | `false` | Indica se i nuovi utenti devono verificare la loro email prima di accedere al sistema. |
| `max_file_upload_mb` | int | `10` | Dimensione massima di caricamento dei file in megabyte. Si applica a tutti i caricamenti (risorse statiche e report broker). |
| `auto_sync_fx_rates` | bool | `true` | Abilita la sincronizzazione giornaliera automatica dei tassi di cambio FX dai provider configurati. |
| `auto_sync_prices` | bool | `true` | Abilita la sincronizzazione automatica dei prezzi degli asset dai provider (Yahoo Finance, ecc.). |
| `price_sync_interval_hours` | int | `6` | Frequenza di sincronizzazione dei prezzi degli asset, in ore. |
| `default_currency` | str | `EUR` | Valuta di visualizzazione predefinita per gli utenti appena registrati. Gli utenti possono sovrascriverla nelle loro impostazioni personali. |
| `default_language` | str | `en` | Lingua predefinita per gli utenti appena registrati. Supportate: `en`, `it`, `fr`, `es`. |

---

## 🗂️ Categorie

Le impostazioni sono raggruppate in categorie nell'interfaccia:

### 🕐 Sessione
- ⏱️ `session_ttl_hours` — Controlla la durata di una sessione di login

### 🛡️ Sicurezza
- 📝 `enable_registration` — Attiva/disattiva la registrazione
- ✉️ `require_email_verification` — Obbligo di verifica email

### 📤 Sincronizzazione e Caricamenti
- 💱 `auto_sync_fx_rates` — Sincronizzazione automatica tassi FX
- 📈 `auto_sync_prices` — Sincronizzazione automatica prezzi asset
- ⏰ `price_sync_interval_hours` — Frequenza sincronizzazione prezzi
- 📦 `max_file_upload_mb` — Limite dimensione file

### 🌍 Predefiniti
- 💰 `default_currency` — Valuta predefinita per nuovi utenti
- 🗣️ `default_language` — Lingua predefinita per nuovi utenti

---

## 🔧 Note Tecniche

- 🗃️ Le impostazioni sono archiviate come **coppie chiave-valore** nella tabella `global_settings`
- 🔀 I valori sono archiviati come stringhe e convertiti nel tipo appropriato (`int`, `bool`, `str`) in lettura
- 🔒 All'avvio di un sistema multi-worker, le impostazioni sono inizializzate con `INSERT ... ON CONFLICT DO NOTHING` per evitare race condition
- ⚡ Le modifiche hanno effetto **immediatamente** — non è necessario riavviare il server
