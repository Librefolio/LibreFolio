# 10 — Grafici & segnali frontend — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/10_frontend_charts.md)
> Metodo: analisi statica read-only; nessun test eseguito (run full in corso).
> Strumenti: `grep`/`find`/`git log --no-pager` + `npx knip --no-progress` (analisi
> statica, nessun server). Working tree incluse le modifiche beta NON committate del 02/09.

---

## Sintesi esecutiva

Il sottosistema grafici/segnali **conferma il primato di pulizia** e ha pure migliorato:
l'unico reperto del 2026-08 (`signalLabelToText`, J1) è stato risolto **per adozione** —
la variante HTML dell'etichetta è oggi usata da 3 componenti e 2 route. knip 2026-09-02
non segnala **alcun** export o tipo inutilizzato in `src/lib/charts/` (erano 1+1). Zero
`$:` legacy, struttura registry/bridge intatta, e la "nota di vigilanza" J4 ha ricevuto
la risposta giusta: `signalProblem.ts` è finito sotto test il 31/08.

Unica macchia, fuori dal perimetro grafici: il conteggio complessivo degli `$:` legacy
del frontend è **regredito da 101 a 109** (+4 `brokers/`, +3 `settings/`, +1 `routes/`) —
l'opposto della direzione raccomandata dal vecchio report.

| Metrica | Audit 2026-08-07 | Oggi 2026-09-02 | Comando |
|---|---:|---:|---|
| File `src/lib/charts/` | 28 | 36 (20 prod + 16 test) | `find src/lib/charts -name '*.ts'` |
| Righe | 4 288 | 6 258 (2 724 senza test) | `find … -exec cat {} + \| wc -l` |
| Export inutilizzati in `charts/` | 1 | **0** | `npx knip --no-progress` (nessuna voce `charts/`) |
| Tipi inutilizzati in `charts/` | 1 | **0** | idem |
| `$:` legacy in `charts/` + `components/charts/` | 0 | **0** | `grep -rn --include="*.svelte" -E "^\s*\\\$:" src/lib/charts/ src/lib/components/charts/ \| wc -l` |
| `$:` legacy totale frontend | 101 | **109** ⚠️ | `grep -rn --include="*.svelte" -E "^\s*\\\$:" src/ \| wc -l` |

> La metrica 28 file / 4 288 righe è **riprodotta esattamente**: 8 file di test sono stati
> aggiunti a `src/lib/charts/` il 2026-08-31 (commit `ce8db7af`), cioè 36 − 8 = 28 come
> all'audit. Verifica: `git log --since="2026-08-01" --diff-filter=A --name-only --
> frontend/src/lib/charts/` → 8 file `__tests__/*.test.ts`. L'audit contava quindi tutti
> i file, test inclusi.

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza | Azione |
|---|---|---|---|---|
| J1 — `signalLabelToText` orfana (DRY orfano) | 🟢 aperto | **SUPERATO (risolto per adozione)** | La funzione non esiste più (`grep -rn "signalLabelToText" src/` → 0). `charts/signalLabel.ts` ora esporta `SignalLabelInfo` (`:21`), `signalLabelToHtml` (`:55`) e `buildOverlaySignalInfoMap` (`:100`) — tutti **usati**: `MeasurePanel.svelte:20,308`, `CandlestickChart.svelte:28,424`, `PriceChartFull.svelte:25,900+`, `fx/[pair]/+page.svelte:65-66`, `assets/[id]/+page.svelte:76-77`. La resa testuale delle etichette è stata unificata sulla variante HTML | nessuna |
| J2 — 0 `$:` in charts, migrazione Runes completa | 🟢 constatazione | **ANCORA VALIDO** | 0 statement `$:` in `src/lib/charts/` e `src/lib/components/charts/` (comando in tabella metriche) | nessuna qui; regressione altrove (N1) |
| J3 — struttura modello/rendering autopulente | 🟢 constatazione | **ANCORA VALIDO** | `ls src/lib/charts/signals/` → i 7 modelli (`ChartSignal`, `CompoundSignal`, `LinearSignal`, `MeasureSignal`, `SineSignal`, `AssetComparisonSignal`, `FxPairSignal`), i 6 bridge (`backendRenderer`, `backendTypes`, `requestBuilder`, `resultMapper`, `schemaMapper`, `catalogMapper`), `registry.ts`, `previewPolicy.ts`, `signalProblem.ts`, `signalVisualStyle.ts`, `index.ts` (barrel vivo: 30 import da `$lib/charts/signals`) tutti presenti | nessuna |
| J4 — `previewPolicy.ts` / `signalProblem.ts` da tenere d'occhio | 🟢 nota | **ANCORA VALIDO, mitigato** | Entrambi presenti. Dal 31/08 `signalProblem` è sotto test: `signals/__tests__/signalProblemSeverity.test.ts` (+ `registry.test.ts`, `measureSignal.test.ts`, `catalogPartitions.test.ts`, `backendRendererSegments.test.ts`, `comparisonSignals.test.ts`, `syntheticSignals.test.ts`, `loadComparisonData.test.ts` — commit `ce8db7af`). La politica che il vecchio report temeva crescesse incontrollata è ora coperta | controllo complessità al prossimo ciclo, come da nota originale |

---

## Dettaglio reperti ancora aperti / regrediti

### N1 (regressione) — `$:` legacy frontend: 101 → 109

Riproduzione per area (stesso comando del vecchio audit, `grep -rn --include="*.svelte"
-E "^\s*\\\$:" <area> | wc -l`):

| Area | 2026-08 | Oggi | Δ |
|---|---:|---:|---:|
| `components/ui/` | 26 | 26 | = |
| `components/brokers/` | 26 | 30 | **+4** |
| `components/settings/` | 25 | 28 | **+3** |
| `routes/` | 21 | 22 | **+1** |
| `components/layout/` | 3 | 3 | = |
| `charts/` + `components/charts/` | 0 | 0 | = |
| `components/transactions/` | — | 0 | = (le modifiche beta alle modali **non** hanno introdotto `$:`) |
| **Totale** | **101** | **109** | **+8** |

Concentrazione attuale: `BrokerSharingPanel.svelte` 24, `brokers/[id]/+page.svelte` 12,
`ImageEditModal.svelte` 10, `PreferencesTab.svelte` 9, `GlobalSettingsTab.svelte` 9
(`grep -rn … | cut -d: -f1 | sort | uniq -c | sort -rn`). Vale la conclusione operativa
del vecchio report: migrazione file-per-file quando si tocca il file, non campagna
dedicata — ma la direzione deve essere **in discesa**, e l'ultimo mese è stato in salita.

---

## Task riesumati

| # | Task | Evidenza | Stima |
|---|---|---|---|
| G1 | ~~Adottare o rimuovere `signalLabelToText`~~ | risolto per adozione (J1) | — chiuso |
| G2 | ~~Verificare l'unico tipo esportato inutilizzato~~ | knip oggi: 0 tipi orfani in `charts/` | — chiuso |
| G3 | Invertire la regressione `$:`: migrare i `$:` di `BrokerSharingPanel.svelte` (24) e dei due tab settings (9+9) alla prossima occasione di modifica di quei file | tabella N1 | **M** (spalmabile) |
| G4 | Mantenere la vigilanza J4: controllo complessità di `previewPolicy.ts`/`signalProblem.ts` al prossimo ciclo | file presenti, ora sotto test | **S** |

---

## Nuovi rilievi

1. **Copertura test del sottosistema segnali nettamente aumentata** (8 file, 31/08): è la
   risposta strutturale alla nota J4 e al principio "contratto esplicito" di J3 — il
   registry ora ha un test (`registry.test.ts`) che ne verifica le partizioni.
2. **Nessun nuovo orfano** nato in `charts/` nonostante la ondata beta sul frontend
   (Tooltip con delay, CompactCashCell, ecc.): `charts/` resta l'unico sottosistema a
   contributo zero nei 60 export inutilizzati di knip.
3. Fuori perimetro ma rilevante per il quadro: i 60 export / 86 tipi orfani residui del
   frontend sono trattati in [08](08_frontend_state_api.md) (store/api) e
   [09](09_frontend_components.md) (componenti/barrel/i18n).

---

## Cross-reference

- Fonte: [10_frontend_charts.md archiviato](../../phases/05_cleanAudit/10_frontend_charts.md)
- Vecchio crosscutting (conteggio `$:` originale): [11_crosscutting.md](../../phases/05_cleanAudit/11_crosscutting.md)
- Report gemelli: [08 — Stato & API](08_frontend_state_api.md), [09 — Componenti](09_frontend_components.md)
