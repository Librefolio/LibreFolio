# Report Phase 0 — AI Export Final Hardening and Documentation V1

**Data**: 1 agosto 2026
**Run finale mirato**: `real_prompt_probe/20260801T085820.657238Z`
**Comparatore approvato**: `real_prompt_probe/20260801T072616.671347Z`
**Stato Task Adequacy**: **96 OPTIMAL / 0 SUFFICIENT / 0 INSUFFICIENT**
**Scope**: hardening renderer, semantica Broker, probe workflow, skill/instructions, Developer Guide e User Guide EN

---

## 1. Executive summary

La fase finale è pronta per review:

- bucket finanziari temporali completamente vuoti omessi dal prompt pubblico;
- zero, flussi, P&L, extrema, riconciliazioni e date osservate preservati;
- tre universi Broker resi espliciti;
- Entity Directory corretta per scope all-accessible con Broker senza posizioni;
- PAC invariato come OPTIMAL;
- Cost Efficiency invariato come OPTIMAL;
- 4/4 probe mirati, 0 failure/skip/regression;
- skill riutilizzabile e instruction generale AI create;
- Developer Guide aggiornata allo stato runtime corrente;
- soltanto la User Guide inglese aggiornata;
- nessun commit, cleanup, release, wiki lint o MkDocs build/lint/link-check globale.

---

## 2. Bucket finanziari vuoti

### Correzione

La policy è nel renderer pubblico generico:

`frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts`

Una riga temporale viene omessa soltanto quando:

- contiene confini/index nominali;
- `has_data` non dichiara dati presenti;
- non contiene osservazioni, valori economici, flow, variazioni, P&L, extrema,
  riconciliazioni, date osservate o altri stati significativi.

Sono mantenuti:

- valore osservato zero;
- flow zero o non-zero;
- P&L zero o non-zero;
- un singolo valore economico;
- una data economica;
- stato esplicito diverso dalla semplice assenza.

Il backend conserva bucket, confini, calcoli, frequenza e sampling invariati.
Requested/effective/available period, coverage e insufficient-history restano
fuori dalle righe omesse.

### Diagnostica

Nuove metriche:

- `empty_temporal_rows_detected`;
- `empty_temporal_rows_omitted`;
- `temporal_rows_rendered`;
- alias per-prompt `empty_temporal_rows_before`,
  `empty_temporal_rows_omitted`, `remaining_temporal_rows`.

---

## 3. Semantica Broker

Il calcolo Portfolio usa realmente l'intero scope selezionato dopo access
validation. Un Broker senza posizioni correnti resta nello scope.

| Campo | Semantica | Period-sensitive |
|---|---|:---:|
| `scoped_broker_count` | Broker inclusi nel calcolo | No |
| `broker_scope` | stesso scope come B# | No |
| `position_broker_count` | Broker con posizioni aperte a snapshot date | No |
| `period_contributor_broker_count` | Broker nei contributor performance del periodo | Sì |

Campione PAC:

```text
broker_scope = B1, B2
scoped_broker_count = 2
position_broker_count = 1
period_contributor_broker_count = 1
entity_directory_broker_count = 2
```

Il precedente `portfolio.summary.broker_count` è stato rinominato
`position_broker_count`.

Il manifest diagnostico distingue inoltre:

- `accessible_broker_count`;
- `scoped_broker_count`;
- `position_broker_count`;
- `period_contributor_broker_count`.

I vecchi density probe usano ora `scoped_broker_count`, eliminando la collisione
terminologica.

### Entity Directory

`runtime_service._entity_directory()` riceve il `prepared.broker_scope`, non
soltanto il filtro inviato nel request body. Una richiesta all-accessible include
quindi anche Broker scoped senza righe posizione/componenti e non produce
`broker_unmapped:<id>`.

---

## 4. Probe mirati finali

Generati soltanto:

- PAC 3M Compact;
- PAC 1Y Standard;
- PAC 1Y Full;
- Directa Cost Efficiency 1Y Compact.

### Risultati

| Prompt | Chars before | Chars after | Empty before | Omitted | Remaining | Rating | Regression |
|---|---:|---:|---:|---:|---:|---|---|
| PAC 3M Compact | 27.268 | 25.716 | 12 | 12 | 8 | OPTIMAL 94 | No |
| PAC 1Y Standard | 30.764 | 25.676 | 38 | 38 | 8 | OPTIMAL 93 | No |
| PAC 1Y Full | 34.704 | 25.672 | 67 | 67 | 8 | OPTIMAL 92 | No |
| Cost Efficiency 1Y Compact | 23.850 | 23.850 | 0 | 0 | 29 | OPTIMAL 96 | No |

La riduzione PAC deriva esclusivamente dalle righe finanziarie completamente
vuote. Dataset e componenti inclusi sono invariati.

### PAC non regressione

In tutte le varianti:

- checklist: 4 categorie, 13 required, 10 optional;
- Portfolio Drawdown presente;
- Asset Drawdown presente;
- nessuna Drawdown history;
- scope B1+B2 coerente;
- UI/probe byte-equivalent;
- rating OPTIMAL invariato.

### Cost Efficiency non regressione

Directa mantiene:

- fee e tasse;
- costi totali;
- turnover e denominatori;
- cinque ratio recorded;
- formule, numeratori, denominatori, unità e coverage;
- distinzione recorded/unavailable/not applicable;
- stesso prompt hash dimensionale: 23.850 caratteri.

### Integrità

- 4/4 prompt;
- failures 0;
- skipped 0;
- false removed comparison 0;
- secret scan passed;
- source snapshot unchanged;
- production DB unchanged;
- production writer rilevato ma senza drift;
- UI/probe exact match 4/4.

---

## 5. Workflow probe riutilizzabile

Il probe targeted è stato generalizzato:

- confronto targeted limitato alle stable key richieste;
- nessun falso `removed` per casi volutamente non eseguiti;
- directory artifact basate sul selection ID, non hard-coded PAC/Cost;
- scope `all`, `broker=<display name>` e `representative`;
- `representative` riutilizzabile anche per Asset e FX;
- metriche Broker e temporal-row persistite.

Run autorevole:

`real_prompt_probe/20260801T085820.657238Z`

Artefatti aggiunti:

- `final_hardening_reviews.json`;
- rating before/after in `metrics.json`;
- riepilogo hardening in `summary.md`.

---

## 6. Skill creata

Percorso:

`.github/skills/ai-export-probe-tuning/SKILL.md`

Contiene:

- quando usarla/non usarla;
- smoke, targeted, full, comparison, Task Adequacy e partial-history probe;
- renderer UI come source of truth;
- DB copy, integrity, writer concorrenti, autenticazione, secret scan e anonimizzazione;
- scope selection;
- metriche;
- review qualitativa;
- rubrica Task Adequacy;
- regola input user-only;
- workflow iterativo;
- errori da evitare;
- gestione divergenze MkDocs/code/test/catalog/probe.

La skill rimanda a MkDocs per percorsi, simboli, comandi e flag correnti.

---

## 7. GitHub Instructions create/aggiornate

Nuova instruction:

`.github/instructions/ai-development.instructions.md`

È una regola d'ingresso breve per lo sviluppo AI:

- obbligo di leggere MkDocs e verificare implementazione;
- confine Backend/Frontend;
- prompt facts/limits/coverage/refs;
- riferimento alla skill probe;
- gestione divergenze;
- sezione futura MCP/infrastruttura AI senza convenzioni speculative.

Aggiornata:

`.github/instructions/frontend-ai-export.instructions.md`

Correzioni:

- rimossa la Snapshot UI-only/synthetic;
- rimossi Camera icon e mapping verso vecchi task;
- documentati i due selection kind catalog-backed: dataset/analysis;
- terminologia Export Data/Request Analysis;
- procedura moderna per aggiungere dataset/Analysis.

---

## 8. Developer Guide MkDocs

Aggiornate:

- `ai_export_snapshot.md`;
- `ai_export_composition.md`;
- `ai_export_sampling.md`.

Creata:

- `ai_export_probe_workflow.md`.

Aggiornato `mkdocs.yml` con la nuova pagina.

Contenuti allineati:

- 65 componenti / 32 dataset / 16 Analysis;
- backend components → datasets → Analysis → catalog → snapshot;
- renderer ufficiale frontend;
- tutti i 16 binding Analysis;
- PAC checklist e Drawdown;
- Cost Efficiency completo;
- Broker universes;
- partial FX;
- detailed/context/latest/digest events;
- no-empty-row pubblico;
- chars/4 e dimensioni;
- targeted/full/comparison/Task Adequacy workflow;
- command profile `tuning-v2`;
- formato pubblico a tabelle compatte, non vecchio YAML monolitico.

---

## 9. User Guide inglese

Aggiornate soltanto:

- `user/ai-export/index.en.md`;
- `portfolio.en.md`;
- `broker.en.md`;
- `asset.en.md`;
- `fx.en.md`.

Correzioni:

- termini UI Export Data / Request Analysis;
- AI period e Detail correnti;
- dataset vs Analysis;
- Additional LibreFolio Data;
- PAC required/optional e scenari condizionali;
- Cost zero/unavailable/not applicable;
- FX partial history;
- A#/B#/F#/L#;
- rimosso il non esistente Drawdown Recovery Analysis;
- aggiunto FX Exposure Impact.

Nessuna traduzione IT/FR/ES modificata.

---

## 10. Verifica manuale documentazione

Eseguito senza MkDocs build/lint/link checker globale:

- link skill → quattro pagine Developer Guide: validi;
- link reciproci AI Export Developer Guide: validi;
- nav nuova pagina: valida;
- file sorgente citati: presenti;
- skill referenziata dalle instructions;
- fence Markdown bilanciate;
- H1-H3 con emoji nelle pagine MkDocs;
- terminologia obsoleta assente nei file interessati;
- soltanto i cinque file User Guide EN modificati.

---

## 11. Test

- Backend mirato: **90 passed**.
- Frontend AI Export/Signal: **200 passed**.
- Typecheck: **0 errori, 0 warning**.
- Probe finale: **4/4**.
- Ruff: passed.
- Prettier scoped: passed.
- `git diff --check`: richiesto nel gate finale.

Non eseguiti per vincolo esplicito:

- MkDocs build;
- MkDocs lint;
- global link checker;
- wiki lint/update;
- release.

---

## 12. Problemi documentali fuori scope

Non modificati:

1. `mkdocs_src/docs/developer/test-walkthrough/api.md` non elenca ancora i test
   AI Export.
2. Le pagine User Guide AI Export non hanno traduzioni IT/FR/ES; questa attività
   autorizzava soltanto EN.
3. `.github/copilot-instructions.md` non cita AI Export nella descrizione generale
   del prodotto.

Questi punti non bloccano il runtime o la review corrente.

---

## 13. Decisione richiesta

Approvare:

1. hardening empty temporal rows;
2. nomenclatura Broker esplicita;
3. run `20260801T085820.657238Z` come prova finale mirata;
4. skill `ai-export-probe-tuning`;
5. instruction `ai-development.instructions.md`;
6. Developer Guide e User Guide EN aggiornate;
7. mantenimento Task Adequacy a **96 OPTIMAL / 0 SUFFICIENT / 0 INSUFFICIENT**.
