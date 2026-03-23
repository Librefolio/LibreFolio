# Audit della Documentazione del Backend

Data: 2024-07-29

Questo documento analizza lo stato della documentazione del backend presente in `mkdocs_src` confrontandola con l'attuale implementazione nel codice sorgente.

## ✅ Ben Documentato

Questa sezione elenca le parti della documentazione che sono accurate, complete e allineate con il codice.

### Corretto e Aggiornato

1. **Architettura a Plugin (Registry Pattern)**
    - **File**: `developer/architecture/registry_pattern.md`
    - **Analisi**: La spiegazione del `ProviderRegistry`, del decoratore `@register_provider` e del flusso di auto-discovery è eccellente e rispecchia fedelmente l'implementazione
      in `backend/app/services/provider_registry.py` e nei vari provider.

2. **Liste dei Provider (BRIM, Asset, FX)**
    - **File**: `developer/backend/{brim|assets|fx}/providers_list.md`
    - **Analisi**: Le liste dei provider disponibili sono complete e corrispondono ai file presenti nelle rispettive cartelle dei servizi (`brim_providers`,
      `asset_source_providers`, `fx_providers`).

3. **Panoramiche Architetturali (BRIM, Asset, FX)**
    - **File**: `developer/backend/{brim|assets|fx}/architecture.md`
    - **Analisi**: Le spiegazioni concettuali di alto livello (es. il workflow di BRIM, la logica di backward-fill per gli asset, la normalizzazione delle valute per FX) sono
      corrette e forniscono un'ottima introduzione al funzionamento dei rispettivi servizi.

4. **Processo di Generazione dell'API**
    - **File**: `developer/api/overview.md`
    - **Analisi**: La descrizione del flusso `FastAPI -> openapi.json -> TypeScript Client` è accurata e rappresenta correttamente il workflow di sviluppo.

## ⚠️ Parzialmente Documentato o Obsoleto

Questa sezione elenca le parti della documentazione che sono parzialmente corrette ma incomplete o che contengono informazioni obsolete.

### 1. Schema del Database

- **File**: `developer/architecture/database.md`
- **Obsoleto**: Il diagramma ER (Mermaid) è significativamente obsoleto.
    - **Mancano tabelle chiave**: `BrokerUserAccess` (fondamentale per l'accesso multi-utente) e `FxConversionRoute` (per la configurazione dei provider FX e le catene di conversione).
    - **Mancano campi importanti**: La tabella `Asset` nel diagramma non include i nuovi campi `identifier_*` (es. `identifier_isin`, `identifier_ticker`), che sono invece presenti
      nel modello `models.py`.
- **Incompleto**: La descrizione della tabella `Transaction` è troppo semplicistica. Non menziona il campo `related_transaction_id`, che è cruciale per collegare transazioni di
  tipo `TRANSFER` e `FX_CONVERSION`.
- **Dettaglio Mancante**: La documentazione della tabella `FxRate` non menziona il `CHECK constraint` (`base < quote`), che è un dettaglio implementativo fondamentale per garantire
  l'univocità dei tassi.

### 2. Documentazione API

- **File**: `developer/api/curl-testing.md` vs `developer/architecture/users_and_brokers.md`
- **Inconsistente**: Esiste una grave contraddizione sul meccanismo di autenticazione.
    - `curl-testing.md` descrive correttamente l'autenticazione basata su **session cookie**, che è quella implementata.
    - `users_and_brokers.md` descrive erroneamente un'autenticazione basata su **JWT Bearer Token**, che non è utilizzata.
- **Incompleto**: La documentazione manuale non copre l'intera superficie dell'API. Mancano riferimenti a endpoint importanti come quelli per la gestione degli accessi ai broker (
  `/brokers/{id}/access`) e la configurazione dei provider FX (`/fx/providers/routes`). Sebbene sia corretto rimandare alla documentazione interattiva (Swagger) per la
  reference completa, i concetti chiave dovrebbero essere presenti.

## ❌ Scarsamente Documentato o Mancante

Questa sezione evidenzia le aree dove la documentazione è gravemente carente, errata o completamente assente.

### 1. Autenticazione e Autorizzazione

- **File**: `developer/architecture/users_and_brokers.md`
- **Errato**: Come già menzionato, la descrizione del meccanismo di autenticazione (JWT) è **fondamentalmente sbagliata**. L'implementazione usa sessioni gestite tramite cookie.
- **Mancante**: L'intero sistema di **Controllo Accessi Multi-Utente** è assente. Non c'è alcuna menzione della tabella `BrokerUserAccess`, dell'enum `UserRole` o dei ruoli
  `OWNER`, `EDITOR`, `VIEWER`. Questa è una delle funzionalità più importanti del sistema ed è completamente non documentata.

### 2. Sistema di Impostazioni (Settings)

- **File**: `developer/architecture/settings.md`
- **Incompleto/Generico**: La documentazione descrive un sistema a due livelli (`GlobalSetting` e `UserSetting`), che è corretto a livello concettuale. Tuttavia, non riflette
  l'implementazione specifica:
    - `UserSettings` in `models.py` è una tabella con colonne specifiche (`base_currency`, `language`, `theme`), non un generico key-value store per utente.
    - `GlobalSetting` è un key-value store generico.
      La documentazione è troppo astratta e non guida lo sviluppatore sulla struttura reale dei dati.

### 3. Configurazione dei Provider FX

- **File**: `developer/backend/fx/configuration.md`
- **✅ Aggiornato**: La documentazione è stata aggiornata per riflettere il nuovo modello `FxConversionRoute` e gli endpoint `/fx/providers/routes`, incluse le catene di conversione multi-step.

## Riepilogo e Azioni Consigliate

- **Priorità Alta**:
    1. Correggere la documentazione sull'autenticazione (`users_and_brokers.md`) per descrivere il sistema a session cookie.
    2. Creare una nuova pagina per documentare il sistema di controllo accessi multi-utente (ruoli `OWNER`, `EDITOR`, `VIEWER` e la tabella `BrokerUserAccess`).
    3. Aggiornare la documentazione dello schema del database (`database.md`), in particolare il diagramma ER e la descrizione delle tabelle `Asset` e `Transaction`.

- **Priorità Media**:
    1. ~~Creare una nuova pagina per documentare la configurazione dei provider FX~~ → ✅ Completato (`developer/backend/fx/configuration.md` aggiornato con `FxConversionRoute` e chain routes).
    2. Rivedere la documentazione del sistema di impostazioni (`settings.md`) per allinearla all'implementazione effettiva.

- **Priorità Bassa**:
    1. Mantenere aggiornate le liste di provider man mano che ne vengono aggiunti di nuovi.
