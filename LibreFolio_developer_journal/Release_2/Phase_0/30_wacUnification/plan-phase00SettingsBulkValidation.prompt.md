# Piano — validazione delle impostazioni globali salvate in blocco

> Workstream P, lavoro per la 1.2. Coordinator: sessione `c8328a01-f208-4ade-a352-0486d1f14de2`. Approvato dal
> developer: «Mi pare una mancanza che andrebbe risolta, non mi sembra difficiel, facciamola in 1.2». Reperto di Q
> (onda 3). Base: treno 21, `9b2acdd5d`. Corsia `--test-port 6161 --data-dir /tmp/librefolio-r2-p`.

## 1. Stato verificato (09/10)

- **Endpoint**: `PATCH /api/v1/settings/global/bulk` (`backend/app/api/v1/settings.py:319-336`), riservato agli admin.
  Chiama `update_global_setting` (`backend/app/services/settings_service.py:195`), che scrive il valore così com'è e
  **fa commit a ogni item**. È anche l'unico chiamante. Non c'è validazione, e il blocco **non è atomico**: con una
  chiave sconosciuta a metà lista risponde 404, ma le chiavi precedenti sono già salvate.
- **Salvataggio singolo**: non esiste un endpoint a parte. La UI salva una sola impostazione mandando un bulk con un
  item (`GlobalSettingsTab.svelte:141`, `globalSettings.ts:106`).
- **v1.1.0**: endpoint e service identici, verificato sul tag. Il difetto è nella release, quindi la riga va sotto
  «Fixed».
- **Definizioni**: un solo dizionario, `GLOBAL_SETTINGS_DEFAULTS` (`backend/app/schemas/settings.py:275`; 13 chiavi
  con valore, tipo e descrizione). Da lì derivano `SETTINGS_REGISTRY.global_` e i default dei lettori. Gli intervalli
  esistono solo come testo nelle descrizioni («1-1440», «1-365»).
- **Lettura** (`global_settings_service._convert_value`): un int non numerico diventa 0; un bool fuori da
  `true/1/yes/on` diventa False. Lo scheduler (`services/scheduler/settings.py`) legge orari e giorni in modo
  tollerante, ma un orario malformato fa sollevare `_parse_times` a ogni tick.

### Vincoli reali e danno di un valore sbagliato oggi

| Chiave | Tipo | Vincolo proposto | Danno oggi |
|---|---|---|---|
| `session_ttl_hours` | int | 1-8760 (un'ora, un anno) **da confermare** | negativo: sessioni già scadute, tutti fuori, admin compreso; enorme: overflow al login (`auth.py:118-135`) |
| `max_file_upload_mb` | int | 1-1024 **da confermare** (il file è letto tutto in memoria) | negativo: ogni upload rifiutato (`brokers.py:591`, `uploads.py:180`) |
| `enable_registration`, `require_email_verification`, `scheduler_enabled` | bool | `true/false/1/0/yes/no/on/off`, senza distinzione di maiuscole; salvato come `true`/`false` | un refuso diventa False in silenzio: registrazione o scheduler spenti |
| `scheduler_current_price_frequency_minutes` | int | 1-1440 (descrizione e UI) | 0 → fallback; negativo → ciclo sbagliato |
| `scheduler_history_sync_times` | str | lista di `HH:MM` (00:00-23:59), almeno uno; elementi vuoti ignorati come fa il lettore | `25:00` o `6` → eccezione a ogni tick dello scheduler |
| `scheduler_history_sync_days` | str | lista di `mon…sun`, senza distinzione di maiuscole, almeno uno | ignorati in silenzio, si torna al default |
| `scheduler_history_sync_horizon_days` | int | 1-365 (descrizione e UI) | come la frequenza |
| `scheduler_timezone` | str | nome IANA risolvibile sul server (vedi sotto) | il lettore tratta in silenzio gli orari come UTC |
| `default_currency` | str | ISO 4217 (`CurrencyCode`, pycountry); salvata in maiuscolo | codice inesistente dato ai nuovi utenti |
| `default_language` | str | `en/it/fr/es` (come `OnboardingWelcomeSettings`) | lingua inesistente ai nuovi utenti |
| `default_theme` | str | `light/dark/auto` (come `UserSettingsUpdate`) | tema inesistente ai nuovi utenti |

Il tipo è controllato in modo generico per ogni riga, anche fuori dal dizionario: `int` deve essere un intero, `bool`
deve stare nel vocabolario sopra, `json` deve essere un JSON valido.

**Fuso orario.** `tzdata` non è tra le dipendenze, e l'immagine Docker (`python:3.13-slim`, solo `gosu` e
`sqlite3`) potrebbe non avere `/usr/share/zoneinfo`. La regola: se il database IANA del server esiste, il nome deve
starci; se non esiste, si accetta come oggi e vale il ripiego dello scheduler. Altrimenti la modale dello scheduler,
che manda sempre il fuso, diventerebbe insalvabile su quelle installazioni.

### UI e messaggio d'errore

- La UI non manda valori che i nuovi vincoli rifiutano:
  - la modale dello scheduler salva solo con frequenza 1-1440, orizzonte 1-365, almeno un orario e un giorno
    (`SchedulerConfigModal.svelte:118`); gli orari vengono dal selettore, i fusi da `Intl.supportedValuesOf`;
  - lingua, tema e valuta sono menu a scelta; i booleani sono interruttori.
  - Unico caso: `SettingNumber` ha `min = 0` e nessun massimo, quindi 0 o un numero enorme per la sessione o
    l'upload ora vengono rifiutati. È proprio il rifiuto di un valore sbagliato.
- Come mostra gli errori:
  - `GlobalSettingsTab` mostra già il messaggio generico di axios per ogni errore diverso da 403;
  - la modale dello scheduler mostra `response.data.detail`, che deve quindi essere una **stringa**: una lista o un
    oggetto comparirebbe come «[object Object]».
- **Risposta proposta**: `422` con `detail` stringa, che nomina ogni chiave rifiutata e il motivo. Nessuna chiave
  i18n nuova e nessuna modifica al frontend. Un messaggio per campo e tradotto nella UI resta un passo successivo
  facoltativo: servirebbe una chiave da O.
- **Atomicità**: si controllano prima tutte le chiavi (sconosciuta → 404, come oggi) e tutti i valori (→ 422), poi si
  scrive tutto con **un solo commit**. Con un errore non si salva niente. È coerente con
  `decisions/settings-write-path-contract`: mai un blocco applicato a metà senza dirlo.

## 2. Progetto

- **Unica fonte di verità**: i vincoli entrano nelle voci di `GLOBAL_SETTINGS_DEFAULTS`, accanto a tipo, default e
  descrizione (`min`/`max`, `choices`, `format`: `hhmm_list`, `weekday_list`, `timezone`, `currency`). Una funzione
  pura in `schemas/settings.py` controlla un valore (tipo, poi vincolo della chiave) e lo restituisce normalizzato,
  oppure solleva `ValueError` col motivo. Per la valuta riusa il validatore di `CurrencyCode`.
- **Service**: `update_global_settings_bulk(items, user_id, session)` sostituisce `update_global_setting`, che non
  ha altri chiamanti. Fa le verifiche, poi le assegnazioni e un solo commit; solleva un errore «chiave sconosciuta» o
  «valori non validi» con l'elenco.
- **Endpoint**: chiave sconosciuta → 404 col dettaglio di oggi; valori non validi → 422 con `detail` stringa.

## 3. Test (rossi prima, test-author, `api settings` → `test_settings_api.py`, già registrato)

- 422 e valore invariato per ogni chiave, su valori sbagliati scelti tra quelli innocui per la corsia mentre il test
  è rosso (per esempio `abc` invece di un negativo).
- Atomicità: un valore valido più uno sbagliato → 422, e il valido non è salvato. Una chiave sconosciuta dopo un item
  valido → 404, e il valido non è salvato.
- Controlli verdi: valori validi accettati; normalizzazione di valuta (`usd` → `USD`) e booleani (`1` → `true`).
- Dettaglio 422: una stringa che nomina la chiave (non è testo tradotto).
- Write-safe: ogni test legge prima i valori originali e li ripristina in `finally`.

## 4. Passi

- **S1** — Analisi, piano e riassunto al coordinator.
- **S2** — Rossi del test-author.
- **S3** — Vincoli nel dizionario, funzione di validazione, service bulk atomico, endpoint.
- **S4** — Gate nella corsia: `api settings`, `schemas all`, `services settings`; `utils all` se qualcosa del
  runner tocca le impostazioni; `front-utility component-unit` non serve, perché il frontend non cambia.
- **S5** — Checkpoint con la riga per il CHANGELOG, poi FROZEN.

## 5. Riga proposta per il CHANGELOG (`### 🐛 Fixed`)

- **Global settings reject invalid values.** The instance settings page and the settings API accepted any value — a
  negative session duration, an unknown timezone, a scheduler time such as 25:00 — which could lock every user out
  or stop the scheduler. Each value is now checked against its type and allowed range, and a save containing an
  invalid value is refused as a whole, with nothing applied.

## 6. Avanzamento

- **S1** ✅ (09/10) — Analisi fatta, sopra. Il developer approva i tre punti aperti (testuale: «Sì, tutti e tre come
  propone P»): `session_ttl_hours` 1-8760, `max_file_upload_mb` 1-1024, fuso validato contro il database IANA del
  server se c'è, altrimenti accettato come oggi.
- **S2** ✅ (09/10) — Rossi del test-author: `TestGlobalSettingsBulkValidation` (GSET-VAL-001..010) in
  `test_settings_api.py`, 56 test, solo aggiunte.
  - 44 rossi, ognuno per il motivo atteso: 200 col valore sbagliato salvato; 404 col valore valido già scritto;
    valori non normalizzati.
  - 12 verdi.
  - Tutte e 13 le impostazioni ripristinate dopo la run, verificato sul DB.
  > **Note del test-author** (ne ho tenuto conto):
  > - `Currency.validate_code("EURO")` passa, perché pycountry abbina anche i nomi: per la valuta serve una ricerca
  >   esatta per codice;
  > - il `detail` del 422 deve essere una stringa, mentre il 422 standard di FastAPI è una lista.
- **S3** ✅ (09/10) — Correzione.
  - **`schemas/settings.py`**: `SettingConstraint` e `GLOBAL_SETTINGS_CONSTRAINTS`, l'unica fonte dei vincoli,
    accanto ai default. `validate_global_setting_value(key, value, value_type)` controlla prima il tipo
    (int/bool/json), poi il vincolo della chiave; i formati sono verificati da una tabella di funzioni piccole. Il
    valore viene normalizzato dove il significato non cambia: booleani `true`/`false`, interi senza segni o zeri
    superflui, valuta in maiuscolo con ricerca esatta `alpha_3`, spazi esterni tolti. Il fuso è controllato contro
    `zoneinfo.available_timezones()` se non è vuoto.
  - **`services/settings_service.py`**: `update_global_settings(items, user_id, session)` sostituisce
    `update_global_setting`, che non aveva altri chiamanti. Controlla prima le chiavi (`GlobalSettingNotFoundError`),
    poi tutti i valori (`GlobalSettingValueError` con l'elenco), poi fa un solo commit.
  - **`api/v1/settings.py`**: 404 col dettaglio di prima, 422 con `detail` stringa che nomina ogni chiave
    rifiutata.
  - Tutti i 13 default passano la validazione invariati. Ruff e black puliti; il primo C901 di `_check_format` è
    stato sciolto nella tabella.
- **S4** ✅ (09/10) — Gate nella corsia 6161:

  | Selettore | Esito |
  |---|---|
  | `api settings` | 95/95: i 44 rossi sono verdi, i 39 test esistenti invariati |
  | `schemas all` | 1705 |
  | `services settings` | 23 |
  | `services global-settings` | 19 |
  | `front-utility scheduler` | 17: la modale salva davvero attraverso il bulk |
  | `front-utility settings` | 45 |

  `api sync` OK, con modifiche solo nei file generati e ignorati. Il frontend non cambia.
- **S5** ✅ (09/10) — Checkpoint al coordinator con la riga per il CHANGELOG (§5, sotto 🐛 Fixed), poi FROZEN.
