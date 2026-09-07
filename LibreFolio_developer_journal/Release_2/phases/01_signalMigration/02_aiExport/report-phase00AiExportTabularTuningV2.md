Le misure principali di questo report riguardano i prompt finali renderizzati e copiabili dalla UI, non il JSON canonico grezzo.

# Report Phase 0 - AI Export Tabular Tuning V2

**Data**: 31 luglio 2026  
**Run autorevole**: `real_prompt_probe/20260731T084208.527843Z`  
**Profilo probe**: `tuning-v2`  
**Stato**: completato, nessuna ulteriore compressione applicata dopo questa misura

## 1. Risultato

Il tuning ha sostituito il corpo dati YAML ripetitivo con tabelle compatte e
localizzate, mantenendo invariati:

- dati finanziari e relativi calcoli;
- Signal calcolati dal backend;
- bucket temporali;
- eventi selezionati dal backend;
- period summary e latest value;
- universo di Asset, Broker e posizioni;
- contratti dataset/analisi.

Risultato principale sul caso tecnico Asset 1Y Standard:

| Misura | Prima | Dopo | Riduzione |
|---|---:|---:|---:|
| Caratteri | 795.944 | 148.676 | 81,32% |
| Righe | 22.999 | 1.392 | 93,95% |
| Token equivalenti `chars/4` | 198.986 | 37.169 | 81,32% |

Il guadagno non deriva da rimozione di indicatori, eventi o dati. Deriva da:

- eliminazione delle chiavi YAML ripetute per ogni osservazione;
- una tabella per Signal/istanza invece di un unico listone;
- definizioni semantiche dichiarate una volta vicino ai dati;
- formattazione numerica compatta;
- directory iniziale delle entita;
- tabelle finanziarie generiche per componenti non tecnici.

## 2. Corpus reale misurato

Il run non genera tutte le combinazioni possibili tra utenti, Asset, Broker e coppie
FX. Usa un solo utente reale e uno scope rappresentativo per dominio:

| Scope | Selezione |
|---|---|
| Utente | `marco` |
| Portfolio | intero portfolio accessibile |
| Broker | broker deterministico con piu posizioni/storia |
| Asset | Asset deterministico con storia piu lunga, almeno 1 anno |
| FX | coppia deterministica con storia piu lunga, almeno 1 anno |

Inventario Portfolio del run:

- 2 Broker;
- 19 position legs;
- 17 Asset unici detenuti;
- 14 Asset considerati dalla fotografia tecnica;
- 4 Asset tecnicamente eleggibili;
- 3 Asset con copertura tecnica;
- 47 lotti FIFO diagnostici;
- 111 transazioni.

### 2.1 Matrice

Dataset:

- 14 dataset base;
- 3 periodi: 3M, 6M, 1Y;
- 3 detail: Compact, Standard, Full;
- 126 tentativi.

Analisi:

- 16 analisi presenti nel catalogo reale;
- 2 periodi: 3M, 1Y;
- 3 detail: Compact, Standard, Full;
- 96 tentativi.

Totale:

| Tipo | Tentativi | Prompt prodotti | Fallimenti |
|---|---:|---:|---:|
| Export Data | 126 | 114 | 12 |
| Request Analysis | 96 | 87 | 9 |
| **Totale** | **222** | **201** | **21** |

I 201 prompt sono separati in:

- `prompts/data/`: fotografie dati normali;
- `prompts/analysis/`: prompt completi, inclusi PAC, ribilanciamento,
  performance attribution, income review, FIFO review e analisi tecniche.

La precedente cartella con quattro prompt era uno smoke test intenzionalmente minimo,
non il corpus finale. Il corpus finale contiene 201 prompt: abbastanza per misurare
periodo, detail e tipo di selezione senza tornare all'esplosione cartesiana da 1.545
prompt e circa 1,4 GB.

### 2.2 Dataset esclusi

Esclusi dal tuning:

- `portfolio.all_data`;
- `broker.all_data`;
- `asset.all_data`;
- `fx.all_data`.

Motivo: sono composizioni deduplicate dei dataset base gia misurati. Includerli nella
matrice avrebbe duplicato lo stesso contenuto senza aggiungere evidenza sulla qualita
del renderer.

## 3. Cosa significa `canonical`

`canonical` e la risposta JSON esatta prodotta dal backend prima della presentazione
frontend.

Serve per:

- verificare schema e versioni;
- calcolare hash;
- attribuire dimensioni a componenti e Signal;
- confrontare dati backend e prompt renderizzato;
- diagnosticare eventuali differenze.

Non e:

- il testo copiato dall'utente;
- una seconda variante del prompt;
- il formato da valutare qualitativamente;
- un file conservato di default.

Nel run finale la directory `canonical/` e vuota. Il JSON canonico e stato usato
durante la misura, poi non trattenuto. I risultati persistenti da valutare sono i file
Markdown sotto `prompts/`.

## 4. Garanzia: probe e UI usano lo stesso renderer

Fonte di verita frontend:

```text
frontend/src/lib/features/ai-export/templates/promptRenderer.ts
└── renderAiExportPrompt()
```

Flusso del probe:

```text
DB produzione copiata
  -> login HTTP
  -> GET catalog HTTP
  -> POST snapshot HTTP
  -> frontend/scripts/ai-export-render-prompt-probe.ts
  -> import diretto di renderAiExportPrompt()
  -> file Markdown + metriche
```

Python orchestra HTTP, file e metriche. Non reimplementa il renderer. Il bridge Node
importa direttamente la stessa funzione usata dalla UI.

`renderAiExportPromptDiagnostics()` usa lo stesso builder interno del prompt e aggiunge
solo i confini dei blocchi necessari alle metriche.

Verifica finale:

| Controllo | Risultato |
|---|---:|
| Prompt riusciti confrontati | 201 |
| Stringhe diverse UI/probe | 0 |
| Byte UTF-8 diversi UI/probe | 0 |
| Hash diversi UI/probe | 0 |

Quindi ogni file del corpus finale rappresenta esattamente il testo che la UI prepara
per la copia, byte per byte.

## 5. Nuovo formato

### 5.1 Metadata

Resta un piccolo blocco YAML iniziale per:

- selection;
- dataset manifest;
- periodo;
- detail;
- target;
- policy tecniche dichiarative.

Il corpo voluminoso `Snapshot Data` non e piu YAML. Il metadata vale circa l'1% dei
caratteri nei Data Export e meno dell'1% nei prompt Analysis; convertirlo ora avrebbe
un beneficio marginale.

### 5.2 Directory entita

Ogni prompt dichiara prima dei dati una `ENTITY DIRECTORY`.

Asset:

- riferimento pubblico `A#`;
- nome;
- ticker, se disponibile;
- ISIN, CUSIP, SEDOL, FIGI o altri identificativi disponibili;
- valuta;
- tipo;
- `quote_base_quantity`.

Broker:

- riferimento pubblico `B#`;
- nome.

FX:

- riferimento pubblico `FX#`;
- label della coppia.

Le colonne completamente vuote vengono omesse. Gli ID DB non sono necessari per
leggere o collegare le tabelle.

Le istruzioni condivise ordinano esplicitamente all'agente di non usare `A#`, `B#`,
ID numerici, component ID, dataset ID, signal instance ID o annotation key come nomi
nella risposta all'utente. Deve usare nomi reali o abbreviazioni chiare.

### 5.3 Dati finanziari

I componenti finanziari sono resi come:

```text
COMPONENT <component_id>
SUMMARY
|field|value|
...
TABLE <collection>
|row|...|
...
```

Oggetti annidati diventano path stabili, per esempio:

- `current_value.amount`;
- `current_value.code`;
- `gross_gains.amount`;
- `gross_gains.code`.

Questo evita ripetizione di chiavi strutturali senza perdere unita, valuta o
provenance.

### 5.4 Dati tecnici

Struttura:

```text
COMPONENT <technical_component>
SUMMARY
SIGNAL <n>
  definizione Signal
  istanze
  definizioni output
  INSTANCE <id>
    period summary
    history
  events
  selection summary
```

Ogni Signal ha:

- una riga di definizione generale;
- una tabella istanze;
- una tabella output definitions;
- una sezione history per istanza;
- eventi vicini al Signal che li produce.

`semantic_description` non viene piu ripetuta per ogni osservazione. Compare una volta
nella definizione del Signal/output.

History continua a conservare:

- bucket start/end;
- giorni;
- observation count;
- first/last/min/max;
- date osservate;
- output multipli allineati.

### 5.5 Numeri e percentuali

Regole display:

- zeri finali eliminati;
- valori interi senza `.0`;
- precisione frazionaria limitata a quattro cifre significative dopo gli zeri
  iniziali;
- valori molto piccoli non trasformati in zero;
- percentuali ratio convertite in punti percentuali e marcate `%`;
- campi gia scalati protetti dalla doppia conversione.

Esempi:

| Input concettuale | Display |
|---|---|
| `12.340000` | `12.34` |
| `5.000000` | `5` |
| `0.000000456789987` | `0.0000004568` |
| ratio `0.0218` in campo percentuale | `2.18%` |

Il rounding riguarda solo il testo. I calcoli backend restano a piena precisione.

### 5.6 Prezzo unitario

Il vecchio `current_price` ambiguo e stato sostituito da:

```text
unit_price = current_value / quantity
```

Il valore e calcolato dal backend. `quote_base_quantity` resta nella directory per
spiegare la convenzione della quotazione di mercato, per esempio titoli quotati per
100 ma normalizzati a prezzo per singola unita nelle posizioni.

Regola prezzo mancante dichiarata una sola volta:

> ultima osservazione disponibile alla data richiesta o prima; mai usare dati futuri.

## 6. Metriche finali

### 6.1 Intero corpus

I totali sotto sommano una matrice diagnostica che ripete gli stessi scope a periodi e
detail diversi. Non rappresentano una singola sessione utente.

| Tipo | Prompt | Caratteri | Righe | Token equivalenti `chars/4` |
|---|---:|---:|---:|---:|
| Export Data | 114 | 7.515.217 | 73.399 | 1.878.804 |
| Request Analysis | 87 | 12.967.355 | 126.738 | 3.241.839 |
| **Totale** | **201** | **20.482.572** | **200.137** | **5.120.643** |

`chars/4` e una stima ripetibile, non il conteggio di un tokenizer specifico.

### 6.2 Distribuzione per singolo prompt

| Corpus | Mediana | P90 | Massimo |
|---|---:|---:|---:|
| Tutti | 20.995 char / 5.249 tok-eq | 285.727 / 71.432 | 643.662 / 160.916 |
| Export Data | 11.309 / 2.827 | 251.385 / 62.846 | 613.160 / 153.290 |
| Request Analysis | 74.060 / 18.515 | 418.604 / 104.651 | 643.662 / 160.916 |

Caso mediano dell'intero corpus:

```text
portfolio.pac_planning - 1Y - Compact
20.995 caratteri - 353 righe - circa 5.249 token equivalenti
```

Caso massimo:

```text
portfolio.rebalancing - 1Y - Full
643.662 caratteri - 4.974 righe - circa 160.916 token equivalenti
```

### 6.3 Confronti prima/dopo

Tutti i confronti usano prompt equivalenti 1Y Standard del primo probe
rappresentativo e del run finale.

| Prompt | Prima char | Dopo char | Riduzione | Dopo tok-eq |
|---|---:|---:|---:|---:|
| Asset technical | 795.944 | 148.676 | 81,32% | 37.169 |
| Performance attribution | 83.389 | 24.102 | 71,10% | 6.026 |
| PAC planning | 83.504 | 24.261 | 70,95% | 6.065 |
| Rebalancing | 2.685.516 | 431.683 | 83,93% | 107.921 |

Il confronto con il run immediatamente precedente, gia quasi finale, mostra solo
un'ulteriore riduzione dello 0,062%. Il formato e quindi stabile; il grande salto e
quello da YAML ripetitivo a tabelle.

### 6.4 Crescita tecnica per periodo e detail

Token equivalenti `chars/4`:

| Dataset | Periodo | Compact | Standard | Full | Eventi esportati Standard |
|---|---|---:|---:|---:|---:|
| `asset.market_technical` | 3M | 16.764 | 20.074 | 25.020 | 105 |
| `asset.market_technical` | 6M | 20.900 | 26.926 | 35.753 | 184 |
| `asset.market_technical` | 1Y | 26.274 | 37.169 | 54.343 | 239 |
| `broker.technical` | 3M | 39.416 | 48.828 | 62.846 | 319 |
| `broker.technical` | 6M | 51.350 | 68.500 | 93.612 | 557 |
| `broker.technical` | 1Y | 66.652 | 97.743 | 146.654 | 711 |
| `portfolio.technical` | 3M | 41.244 | 51.109 | 65.861 | 319 |
| `portfolio.technical` | 6M | 53.458 | 71.432 | 97.826 | 557 |
| `portfolio.technical` | 1Y | 69.326 | 101.897 | 153.290 | 711 |
| `fx.market_technical` | 3M | 13.595 | 15.938 | 19.423 | 127 |

Conclusione oggettiva: periodo, detail e numero di Asset tecnici restano i principali
moltiplicatori. La sola formattazione non puo annullare questa crescita senza cambiare
la politica del contenuto.

### 6.5 Composizione dei prompt

Export Data:

| Blocco | Quota caratteri |
|---|---:|
| Snapshot Data | 96,96% |
| Metadata/manifest | 1,02% |
| Headings e overhead | 2,02% |

Request Analysis:

| Blocco | Quota caratteri |
|---|---:|
| Snapshot Data | 76,22% |
| Analysis instructions | 4,16% |
| Response contract | 3,22% |
| Metadata/manifest | 0,69% |
| Verifica condivisa, additional data, note, lingua e headings | 15,71% |

Il peso residuo non e causato soprattutto dalle istruzioni. Rimane dominato dai dati.

### 6.6 Composizione tecnica

Attribuzione diagnostica dei caratteri tecnici:

| Sezione | Caratteri aggregati | Quota tecnica |
|---|---:|---:|
| Indicatori | 13.771.165 | 75,85% |
| Eventi | 3.887.778 | 21,41% |
| Prezzi/rate | 497.219 | 2,74% |

Dentro i blocchi Signal renderizzati:

| Parte | Quota |
|---|---:|
| Definizioni | 5,81% |
| Period summary/latest | 6,04% |
| History | 69,60% |
| Eventi | 18,54% |

Quindi il problema residuo non sono piu le descrizioni duplicate. History ed eventi
valgono circa l'88% del contenuto Signal.

Signal con maggior contributo aggregato:

| Signal | Quota dei blocchi Signal |
|---|---:|
| Stoch RSI | 13,01% |
| Bollinger | 11,90% |
| MACD | 10,58% |
| EMA | 10,02% |
| Donchian | 8,45% |

I primi cinque producono il 53,95% del peso Signal. Gli eventi sono ancora piu
concentrati: Stoch RSI, Bollinger, MACD ed EMA rappresentano circa l'80,77% delle
occorrenze evento renderizzate.

## 7. Controlli automatici sul contenuto pubblico

| Controllo | Campione | Violazioni |
|---|---:|---:|
| Colonne completamente vuote nella Entity Directory | 201 prompt | 0 |
| Riferimenti `asset_unmapped` / `broker_unmapped` | 201 prompt | 0 |
| ID DB necessari per join pubblici | 201 prompt | 0 |
| Righe prezzo/history completamente vuote | 201 prompt | 0 |
| Violazioni formattazione percentuale | 201 prompt | 0 |
| Riconciliazioni `unit_price = current_value / quantity` | 1.365 | 0 |
| Separatori Markdown decorativi inutili | 201 prompt | 0 |
| `schema_id`, `schema_version`, `component_version` nel corpo pubblico | 201 prompt | 0 |
| `indicator_policies` pubbliche duplicate | 201 prompt | 0 |
| Rumore `entity_count=1` | 201 prompt | 0 |
| Findings secret scan | corpus completo | 0 |

Il renderer mantiene un fallback YAML solo per componenti o versioni sconosciute.
Nessun componente noto del run finale ha usato quel fallback.

## 8. Valutazione qualitativa

### 8.1 Cosa ora funziona bene

1. **Localita semantica**  
   Definizione, istanze, summary, history ed eventi dello stesso Signal sono vicini.
   L'agente non deve ricostruire la relazione da migliaia di elementi YAML separati.

2. **Leggibilita finanziaria**  
   Tabelle positions, allocations, performance, FIFO, income, fees e taxes mostrano
   righe confrontabili. Valuta e unita restano esplicite.

3. **Identita prima dei codici**  
   `A1`/`B1` sono lookup locali, non nomi opachi come `asset:42`. La directory rende
   immediato il collegamento con nome e identificativi.

4. **Precisione utile**  
   Full precision visuale e zeri finali sono rimossi, ma i numeri piccoli restano
   distinguibili da zero.

5. **Prompt normali presenti**  
   PAC, ribilanciamento, performance attribution, income e FIFO sono presenti in
   `prompts/analysis/`; non vengono confusi con i Data Export tecnici.

6. **Separazione responsabilita corretta**  
   Backend continua a possedere dati/calcoli. Frontend possiede presentazione,
   istruzioni e testo copiato.

### 8.2 Cosa resta grande

1. **Portfolio/Broker technical 1Y Full**  
   Quattro Asset eleggibili, 54 istanze indicatore ed eventi portano ancora a
   146-153 mila token equivalenti.

2. **Analisi finanziarie con technical opzionale**  
   `portfolio.rebalancing`, `portfolio.description`, `broker.review` e
   `broker.concentration_context` ereditano gran parte del dataset tecnico quando
   disponibile. Per questo possono essere quasi grandi quanto un export tecnico puro.

3. **History domina**  
   Dopo aver rimosso il rumore strutturale, il peso residuo e informazione vera:
   bucket per istanza, per Asset e per periodo.

4. **Eventi ad alta frequenza**  
   Stoch RSI, Bollinger, MACD ed EMA generano la maggior parte degli eventi. Il
   renderer li rende compatti, ma non puo eliminarli senza una decisione semantica.

## 9. Fallimenti FX

Tutti i 21 fallimenti hanno codice:

```text
snapshot_source_failure
```

Distribuzione:

| Selezione | Fallimenti |
|---|---:|
| `fx.market_technical` | 6 |
| `fx.overview` | 6 |
| `fx.trend_review` | 3 |
| `fx.conversion_timing` | 3 |
| `fx.exposure_impact` | 3 |

Pattern:

- dataset FX: falliscono 6M e 1Y per tutti i detail;
- analisi FX: fallisce 1Y per tutti i detail;
- 3M riesce.

Il problema e coerente con il coupling/warm-up della sorgente FX gia noto. Non e un
errore del renderer tabellare e non e stato corretto in questo tuning.

## 10. Sicurezza e sola lettura

Il probe:

- copia il DB di produzione;
- normalizza credenziali solo sulla copia;
- avvia API locale sulla copia;
- effettua login/catalog/snapshot via HTTP;
- non scrive intenzionalmente nel DB sorgente.

La fotografia sorgente usata dal run e rimasta identica. Il file DB di produzione e
cambiato durante il run per un writer esterno concorrente, rilevato dal probe; questo
non indica una scrittura del probe.

Secret scan finale: `passed`, zero findings.

## 11. Decisioni future suggerite, non implementate

1. **Separare densita tecnica per Data Export e Analysis**  
   Un export tecnico puo giustificare history completa. Ribilanciamento o descrizione
   potrebbero ricevere summary/latest/eventi senza tutta la history. Decisione prodotto,
   non modifica di formato.

2. **Definire un budget contenuto per technical opzionale**  
   Non un token cap silenzioso: un contratto esplicito per analisi finanziarie che
   dichiari quali evidenze tecniche servono.

3. **Valutare eventi ad alta frequenza per Signal**  
   Stoch RSI/Bollinger/MACD/EMA meritano una review semantica: eventi distinti,
   severita, transizioni ridondanti, finestra recente. Nessun filtro aggiunto ora.

4. **Correggere il coupling FX 6M/1Y**  
   Necessario prima di usare la matrice FX completa per decisioni quantitative.

5. **Lasciare il metadata YAML finche non serve altro**  
   Vale circa l'1% del testo. Convertirlo a tabella ora complicherebbe il renderer con
   guadagno trascurabile.

6. **Usare tokenizer reali solo quando si sceglie un modello target**  
   `chars/4` resta migliore per confronti stabili tra run; un tokenizer specifico serve
   solo per limiti di contesto concreti.

## 12. Artefatti

Run:

```text
LibreFolio_developer_journal/Release_2/Phase_0/01_signalMigration/02_aiExport/
└── real_prompt_probe/20260731T084208.527843Z/
    ├── run_manifest.json
    ├── metrics.json
    ├── failures.json
    ├── summary.md
    ├── canonical/          # vuota nel run finale
    └── prompts/
        ├── data/
        └── analysis/
```

Esempi da leggere:

```text
prompts/data/
  marco__data__asset__asset.market_technical__asset_anon_01__1y__standard.md

prompts/analysis/
  marco__analysis__portfolio__portfolio.pac_planning__all__1y__standard.md
  marco__analysis__portfolio__portfolio.rebalancing__all__1y__standard.md
  marco__analysis__portfolio__portfolio.performance_attribution__all__1y__standard.md
```

File principali del tuning:

- `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts`
  - renderer tabellare;
  - Entity Directory;
  - numeri/percentuali;
  - gruppi Signal;
  - fallback versionato.
- `frontend/src/lib/features/ai-export/templates/promptRenderer.ts`
  - renderer ufficiale UI;
  - composizione prompt;
  - diagnostica derivata dallo stesso builder.
- `frontend/src/lib/features/ai-export/templates/sharedInstructions.ts`
  - divieto di usare codici interni come nomi utente.
- `frontend/scripts/ai-export-render-prompt-probe.ts`
  - bridge che importa il renderer UI.
- `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py`
  - orchestratore `tuning-v2`;
  - copia DB, HTTP, corpus, metriche e safety checks.
- `backend/test_scripts/diagnostics/ai_export_probe_app.py`
  - API locale contro DB copiato.
- `backend/app/schemas/ai_export_runtime.py`
  - directory entita pubblica.
- `backend/app/services/ai_export/runtime_service.py`
  - risoluzione centralizzata identita referenziate.
- `backend/app/services/ai_export/components/asset_payloads.py`
  - prezzo posizione normalizzato.
- `backend/app/services/ai_export/components/payloads/portfolio_broker.py`
  - prezzo posizione normalizzato Portfolio/Broker.

## 13. Conclusione

Il problema iniziale era reale: YAML annidato, descrizioni ripetute e precisione
visuale eccessiva trasformavano un dataset tecnico utile in 23 mila righe.

Il nuovo formato risolve il rumore strutturale:

- 70-84% meno caratteri nei casi confrontati;
- 94% meno righe nel caso Asset tecnico;
- zero perdita introdotta dal renderer;
- prompt UI e probe identici;
- entita leggibili;
- dati finanziari e tecnici localizzati in tabelle.

Il limite residuo non e piu principalmente il formato. E la quantita di history ed
eventi richiesta, soprattutto quando technical completo entra come dataset opzionale
in analisi finanziarie. La prossima decisione deve quindi riguardare il contratto del
contenuto, non un'altra ottimizzazione sintattica cieca.
