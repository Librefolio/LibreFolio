````text
Leggi il progetto LibreFolio e prepara un piano implementativo di dettaglio, senza modificare codice.

Obiettivo:
progettare un sistema unificato di DataQualityIssue/DataQualityBanner riusabile in:
- dashboard portfolio
- asset detail
- forex detail

Il sistema deve rispettare lo stile e i pattern UX già presenti in asset detail e forex detail, ma diventare generico, riusabile e guidato da DTO standardizzati.

Output da salvare in:

LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_2/portfolio_engine/code_agent_unified_data_quality_banner_plan.md

---

## 1. Contesto

Nel nuovo PortfolioCalculationEngine vogliamo esporre problemi, warning e informazioni tramite un modello unificato:

- missing price
- transaction-implied valuation
- stale price
- missing FX
- NAV incompleto
- allocation parziale
- performance parziale
- linked transaction rotta
- share mismatch
- asset/manual valuation issues

Ma lo stesso sistema deve poter coprire anche gli scenari oggi già gestiti in:

- asset detail
- forex detail

L’obiettivo è evitare tre sistemi banner diversi.

---

## 2. Target architetturale

Progettare:

```text
DataQualityIssue DTO
        ↓
DataQualityReport.issues[]
        ↓
DataQualityBanner.svelte
        ↓
riuso in dashboard / asset detail / forex detail
````

Il componente deve supportare due modalità:

```text
grouped
```

per dashboard portfolio, dove molte issue devono essere aggregate;

```text
flat
```

per asset detail e forex detail, dove il contesto è già ristretto.

***

## 3. Stile UI richiesto

Il componente deve rispettare lo stile già usato in asset detail e forex detail:

* amber per warning/error
* sky per info
* layout compatto
* CTA inline
* dettagli espandibili se ci sono molte entità coinvolte
* i18n con parametri
* niente UI rumorosa
* no lista infinita di banner

Esempio concettuale dashboard grouped:

```text
┌──────────────────────────────────────────────────────────────┐
│ ⚠️ Qualità dati: 1 errore, 3 avvisi                           │
│                                                              │
│ 🔴 1 asset non valorizzabile                    [Correggi]   │
│ 🟡 2 asset valorizzati temporaneamente al costo [Dettagli]   │
│ 🟡 1 prezzo obsoleto                            [Aggiorna]   │
│ 🔵 MWRR non disponibile per il periodo selezionato            │
│                                                              │
│                                      [Mostra dettagli]       │
└──────────────────────────────────────────────────────────────┘
```

Esempio asset/forex flat:

```text
┌──────────────────────────────────────────────────────────────┐
│ ⚠️ Manca la coppia FX EUR/USD necessaria per questo grafico   │
│                                      [Aggiungi coppia FX]     │
└──────────────────────────────────────────────────────────────┘
```

***

## 4. DTO target da validare/progettare

Partire da questo modello e verificare se è coerente col progetto reale:

```text
DataQualityIssue:
- domain
- code
- severity
- message_i18n_key
- message_params
- count
- affected_asset_ids
- affected_asset_names
- affected_fx_pairs
- affected_broker_ids
- affected_broker_names
- affected_transaction_ids
- affected_dates
- cta_action
- cta_target
- details_i18n_key
- details_params
- dismissible
- group_key
```

Enum:

```text
IssueDomain:
- portfolio
- asset
- forex
- transaction
- broker
- system

IssueSeverity:
- error
- warning
- info
```

Valuta se usare un unico `IssueCode` globale o codici per dominio. Preferenza attuale: enum unico.

***

## 5. Requisito importante: rendering entità

Quando il banner mostra entità coinvolte, deve rispettare le convenzioni visuali del progetto.

### Forex / currencies

Se una issue riguarda valute o coppie FX:

* usare l’helper/componente già presente nel progetto che stampa le valute nello stile standard;
* non stampare semplicemente `"EUR/USD"` se esiste già una funzione/componente per mostrare bandiere, simboli o formato coerente;
* identificare file/helper esatti da riusare.

Esempi:

```text
🇪🇺 EUR / 🇺🇸 USD
```

secondo lo stile effettivo del progetto.

### Asset

Se una issue riguarda asset:

* mostrare l’icona prima del nome asset;
* usare le attuali regole di fallback del progetto:
  * icona asset se disponibile
  * fallback coerente già usato nelle liste asset/detail
  * eventuale ticker/simbolo se nome non disponibile
* identificare componenti/helper esatti da riusare.

Esempio concettuale:

```text
[asset icon] BTP Più SC FB33 EUR
```

### Broker

Se una issue riguarda broker:

* mostrare l’icona prima del nome broker;
* usare le regole attuali di fallback con i dati disponibili;
* identificare componenti/helper esatti da riusare.

Esempio concettuale:

```text
[broker icon] Directa
```

### Intento generale

Non duplicare rendering custom nel banner.

Il banner deve delegare il rendering di:

* valute
* coppie FX
* asset
* broker

agli helper/componenti già usati dal progetto, o proporre piccoli adapter se non esistono.

***

## 6. Requisito importante: navigazione e CTA

Le CTA devono rispettare l’intento UX già deciso.

### Correzione di dati esistenti

Se l’utente deve correggere o verificare un dato esistente:

* andare verso asset detail o forex detail;
* usare la struttura di link/navigazione impilata già presente nel progetto, non `goto` diretto;
* il comportamento desiderato è:
  * clic su CTA dal banner
  * apertura asset detail / forex detail
  * tasto indietro torna alla pagina dove il banner era mostrato
* identificare la struttura/link helper esatta da usare.

Esempi:

```text
Correggi asset → asset detail
Correggi FX → forex detail
Verifica transazioni → pagina transazioni filtrata, se esiste pattern
```

### Aggiunta di dati mancanti

Se l’utente deve aggiungere qualcosa:

* non navigare via pagina se il progetto usa già modali;
* aprire direttamente la modale di aggiunta nella pagina che usa il componente;
* il componente deve emettere un evento/callback, non conoscere direttamente tutta la logica della pagina.

Esempi:

```text
Aggiungi coppia FX → apri FxPairAddModal nella pagina corrente
Aggiungi prezzo manuale → apri price/manual add modal se esiste
Aggiungi altro dato → callback verso parent
```

### Regola generale

Il componente DataQualityBanner deve essere generico.

Quindi:

```text
DataQualityBanner emette intenti:
- navigate_asset
- navigate_fx
- navigate_broker
- navigate_transactions
- add_fx_pair
- add_price
- sync_asset
- sync_fx
- view_details
```

La pagina che usa il componente decide come eseguire l’azione, soprattutto per modali e sync.

***

## 7. Scenari da coprire

Mappare questi scenari a DataQualityIssue e CTA.

### Portfolio

* MISSING\_PRICE
* TRANSACTION\_IMPLIED
* STALE\_PRICE
* MISSING\_FX\_MARKET
* MISSING\_FX\_COST\_BASIS
* IN\_TRANSIT\_NO\_PRICE
* IN\_TRANSIT\_CB\_FALLBACK
* LINKED\_TX\_BROKEN
* SHARE\_MISMATCH
* NAV\_INCOMPLETE
* ALLOCATION\_PARTIAL
* PERFORMANCE\_PARTIAL
* MWRR\_NOT\_CALCULABLE
* ASSET\_AT\_COST
* ASSET\_UNVALUED

### Asset detail

* ASSET\_ARCHIVED
* RANGE\_BEFORE\_FIRST\_DATA
* FX\_PAIR\_MISSING
* FX\_PAIR\_NO\_DATA
* FX\_PAIR\_PARTIAL\_GAP
* PRICE\_HISTORY\_EMPTY
* PROVIDER\_SYNC\_ERROR

### Forex detail

* FOREX\_NO\_DATA
* FOREX\_STALE
* CONVERSION\_ROUTE\_MISSING
* RANGE\_BEFORE\_FIRST\_DATA
* PROVIDER\_SYNC\_ERROR

Per ogni scenario indicare:

* severity
* banner mode: principale / dettaglio
* CTA
* target
* rendering entità
* se richiede dati backend o può essere costruito frontend-side

***

## 8. Integrazione con Portfolio Report

Tenere conto che la dashboard portfolio userà un endpoint unico:

```text
POST /portfolio/report
```

Il response deve includere:

```text
data_quality.issues[]
```

La dashboard non deve più costruire banner da campi sparsi tipo:

```text
missing_price_assets
missing_fx_pairs
```

ma da:

```text
report.data_quality.issues
```

I campi legacy possono restare solo se servono internamente o come dettaglio dati, ma non devono guidare la UI banner.

***

## 9. Relazione con asset detail e forex detail

Per asset detail e forex detail ci sono due opzioni:

```text
A. backend restituisce già DataQualityIssue
B. frontend costruisce DataQualityIssue localmente dai dati attuali
```

Valutare quale conviene ora.

Preferenza:

* dashboard portfolio: issue prodotte dal backend;
* asset detail / forex detail: migrazione graduale, anche costruendo issue lato frontend all’inizio;
* componente unico subito;
* sorgente dati unificata progressivamente.

***

## 10. Frontend store / cache

Per ora NON progettare cache intelligente avanzata.

Decisione attuale:

```text
POST /portfolio/report deve evitare 3 engine run.
Niente subset intelligente per metriche period-based.
Eventuale cache frontend solo esatta sulla stessa query.
```

Nel piano indicare solo:

* come il banner riceve `issues`;
* come la dashboard riceve il report unico;
* non progettare ottimizzazioni complesse di cache.

***

## 11. Output richiesto

Produrre un piano implementativo di dettaglio con:

1. File backend da modificare.
2. File frontend da modificare.
3. DTO/enum finali consigliati.
4. Design props/eventi di `DataQualityBanner.svelte`.
5. Come raggruppare issue in grouped mode.
6. Come renderizzare asset/broker/currency usando helper esistenti.
7. Come gestire CTA e navigazione impilata.
8. Come aprire modali di aggiunta tramite callback parent.
9. Mappatura issue code → severità → CTA.
10. Strategia di migrazione:
    * prima dashboard portfolio
    * poi asset detail
    * poi forex detail
11. Test minimi backend/frontend.
12. Rischi e domande aperte.

Formato:

* Markdown
* tecnico, sintetico, concreto
* cita file/funzioni/componenti reali quando possibile
* nessuna modifica codice

```
```
