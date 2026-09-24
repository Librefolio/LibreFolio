# F — Laboratorio Asset Global · piano vivo post-merge e chiusura di `risk-lab`

> **Chi**: workstream **F — laboratorio** di Release 2 — lo stesso che fu il mandato F del round 1 e S5 del round 2.
> ⚠️ **Non** le fasi `F1`/`F2` della campagna rischio (`F1-esecuzione.md`, `F2-esecuzione.md` in questa cartella): omonimia, non parentela.
> **Mandato**: messaggi del coordinatore Release 2 del 23/09 (`c8328a01…`) · fogli `09_feedbackJobs/08_review_visiva_20260922.md` e `09_reperti_analisi_statica_20260922.md`
> **Worktree**: `e-alfy-super-dollop` · **Branch**: `e-alfy-risk-asset-global-lab`
> **Baseline**: `f1047f766cce67db888be81432a1544909601187` (verificata 23/09 10:36:58, fast-forward da `e4a46e9e0`)
> **Lane**: suite `--test-port 6154 --data-dir /tmp/librefolio-r2-f` (solo `dev.py test …`) · copia prod `--port 6164 --data-dir /tmp/librefolio-r2-f-prodcopy`
> **Piano precedente**: [`S5-esecuzione.md`](S5-esecuzione.md) (round 2) — questo lo prosegue.
> **Approvazione**: piano (rev. 2) approvato nella chat di F il 23/09, senza testo; letto come approvazione del developer, con le raccomandazioni D1–D10 accolte salvo diversa indicazione. D9-(a) richiede in più l'assenso di A.
> ⚠️ **Omonimia**: nella campagna rischio «I» era la documentazione; qui **I = grafici performance**.

## Stato dei passi

| # | passo | stato | data |
|---|---|---|---|
| F-0 | piano nel journal + rimando in `S5-esecuzione.md` | ✅ | 2026-09-23 |
| F-1 | rosso di partenza di `risk-lab`, spec intatto | ✅ **11/11 verdi** — nessun rosso | 2026-09-23 |
| F-1b | pin privacy OFF nel test del denaro | ✅ inerte oggi, 11/11 | 2026-09-23 |
| F-2 | selezione per-utente (N1) | ✅ | 2026-09-23 |
| F-2b | sync prezzi + cambi nel guscio (R2-128) | ✅ E2E 16/16 | 2026-09-23 |
| F-2c | citazioni per riga → simboliche | ✅ 8 su 8 | 2026-09-23 |
| F-2d | polling dei prezzi live di `/assets` legato agli id (voce assegnata il 23/09) | ✅ codice + E2E 16/16 + **prova per uso** (1 al montaggio, +1 per «Ricarica Tutto») | 2026-09-23 |
| F-2e | `data-quality.en.md` contro il codice: late start, «intersection», baseline (voce del coordinatore, 24/09) | ✅ 13 punti su 16 righe · build rigoroso 0 WARNING · check-links 80 = 80 · 7 residui riportati | 2026-09-24 |
| F-3 | review del laboratorio sulla copia, col developer | 🟡 server rialzato su `6164` alle 09:30:42 del 24/09 su copia **rinfrescata**; review col developer in corso | 2026-09-24 |
| F-4 | colonna ρ̄ (dopo F-3) | ⏳ | — |
| F-5 | devWiki R2-101 | ✅ 3 pagine nuove + 3 aggiornate | 2026-09-23 |
| F-6 | chiusura `risk-lab` | 🔒 dopo le review di Risk e A **e** dopo J | — |
| F-7 | handoff e `FROZEN` | ⏳ | — |

---

## 1. Voci dei fogli 08/09 di competenza di F

| voce | verdetto misurato | azione |
|---|---|---|
| **09 §1.2** (di F) | ❌ smentito, errore di F: misurato *chi legge adesso*, non *quando vive lo stato* (09 §9.1) | nessun codice · ogni affermazione su stato o barra del tab si verifica **usando** la copia |
| 09 §9.1 «nota d'uso» | falso a metà: `mkdocs_src/docs/user/assets/index.en.md:30` lega già Abs/% alla griglia; manca «è globale, sopravvive al cambio di tab» | non di F → D7 |
| **09 §1.6 / §9.2** | 🔴 la §9.2 è vera per `currencyFormat.ts:41`, **non** per il cammino del laboratorio: `L4Replay:13`, `L4Shock:11`, `L1HowMuchItHurts:8` importano il formattatore di `riskAnalysisHelpers`, che sotto privacy restituisce `•••` **al posto dell'intera stringa** (`:160`). **Eseguito**: `npx vitest run src/lib/components/risk/riskAnalysisHelpers.test.ts -t "with global privacy on"` → `Test Files 1 passed (1)`, 7 test, `.toBe(PRIVACY_PLACEHOLDER)`. Classificato **difetto** dal coordinatore (viola «la privacy nasconde il numero, non la valuta»): **lo ripara J** | D4 decisa → F. Pin OFF subito (F-1b); variante ON **dopo J** (§3.1) |
| **09 §2.1** | ❌ **falso**: 6/6 e 11/11 sul ramo di A, corsia `6170`, 21/09 (`A-esecuzione.md:488,622`, `S2-esecuzione.md:318`). La rev. 1 di questo piano lo dava «confermato»: accettazione del brief, non misura | il coordinatore corregge il foglio; F-1 misura la **deriva da un verde noto** |
| 09 §2.3.2 | `risk.assetSet.panelTitle`: introdotta da F (`f2ad97dd4`), orfanata da A (`daa03c0f2`) | D6 decisa → F a fine round, non prima |
| 09 §2.4 | il guardiano riusabile è in `risk-lab.spec.ts` (test del catalogo + `MOCK_ALGORITHM_VERSION`) | preservarlo in F-6 |
| 09 §2.6 | `L4Replay:47` / `L4Shock:46` → **Risk** | non toccati |
| 09 §3.11 / **§3.12** | la variante ON asserisce sull'**output reso**, niente in comune con `SAFE_CALL` di J | vincolo di TL-C1b |
| 08 R1 `lastedDays` | → **A** (introdotta in `032b86959`); `risk-lab` non la asserisce | — |
| 08 §8.4 | replay: valutazione congiunta Risk (`L4Replay`) + F (montaggio, frase d'audit per scope) | F-3 |

## 2. Reperti nuovi dell'analisi del 23/09

- 🔴 **N1 — la selezione del laboratorio non è per-utente.** `assetSetSelection.ts` usa la chiave nuda `'assetGlobal.riskSelection.v1'` su `localStorage` grezzo; sulla stessa pagina il benchmark di Risk è per-utente (`riskBenchmarkStore.svelte.ts`, `lf_${getClientSessionUserId() ?? 'anon'}_…`). Il criterio lo dà J (`privacyStore.svelte.ts`, intestazione): la privacy è nuda perché *«descrive lo schermo che viene guardato, non chi è loggato»*, come tema e lingua. La selezione descrive **il lavoro dell'utente** → per-utente. Senza migrazione: migrare la chiave nuda consegnerebbe la selezione di un utente a chi entra per primo, cioè la fuga stessa.
- **N2** — il laboratorio non ha una pagina utente (`correlation` compare solo in `user/ai-export/portfolio.en.md`).
- **N3** — `frontend/tsconfig.e2e.json` al primo uso: 4 errori in 3 file non di F, uno di configurazione (manca l'alias `$lib`) → non adottabile come cancello così com'è.
- **N4** — la tabella «Stato dei passi» di `S5-esecuzione.md` è ferma al 18/09 → rimando in testa, non riscrittura (09 §2.7).
- ✅ **N5** — smentita la previsione di interferenza dell'onboarding: il popolatore rende terminali gli utenti E2E (`backend/test_scripts/test_db/populate_mock_data.py`, `_grandfather_onboarding_for_test_users`).
- 🧭 **Errori di F in quest'analisi, in chiaro**: il «confermato» sul §2.1 · la procedura della copia che leggeva il main checkout, non segnalata · **il 22/09 `onsynced` dichiarato «chiuso»** rispondendo a *«il cablaggio è orfano?»* invece che a *«la capacità è raggiungibile?»* — la forma esatta di R2-132, un giorno dopo la sua registrazione · tre sonde sbagliate verso il rosso (deriva dei testid, registrazione dei test, forma `export const`), denunciatesi da sole.

## 3. `risk-lab` — ricognizione su `f1047f766`

**Composizione**: 2057 righe · 1 `describe` · 11 test. Per `git blame` sulla riga del titolo: **6 di F** (`f2ad97dd4`) · **5 di A** (`032b86959`). Il test del denaro è **al 73% di A** (41 righe di F su 152).

**Verde noto**: 11/11 sul ramo di A il 21/09. Delta sulle sue dipendenze da allora (`git log 032b86959..f1047f766`): privacy di J (`b66e93003`, `9a6dd2015`, `0a1d98eaf`), banner beta (`c57fc7ef2`), grafici (`2d22130bd`), merge `7fd660846` / `d59051977`.

**Distanza statica — zero su tre assi**:

| asse | misura | esito |
|---|---|---|
| nomi | 50 testid contro `frontend/src`, con tre controlli (assente, letterale, dinamico) | 0 irraggiungibili: 32 letterali · 2 template · 4 prefisso · ~~12~~ **11 composti** (10 da `RiskLevelSection`, 1 da `TornadoChart`) **+ 1 template lato spec** con celle letterali in `src` — corretto il 23/09 dal `project-historian`: avevo letto male il mio stesso log (la prima sonda li dava assenti: errore della sonda, preso al secondo passaggio) |
| tipi | `npx tsc -p tsconfig.e2e.json --noEmit`; entrambi i file nel programma (`--listFilesOnly`: 2 su 2) | 0 errori in `risk-lab.spec.ts` e `risk-mocks.ts` |
| rotte | 3 simulate (`catalog`, `scenario-catalog`, `query`) + 1 reale (guardiano) | 4/4 nell'OpenAPI |

**Non misurabile senza eseguire**: la forma dei payload simulati (tipizzati a mano; solo il guardiano fa `parse`). È l'unica distanza possibile → F-1.
⚠️ ~~12~~ **11** testid su 50 dipendono dalla composizione di `RiskLevelSection` (10, Risk) e `TornadoChart` (1): una rinomina lì rompe `risk-lab` senza toccarlo. (Il «12, tutti da `RiskLevelSection`» è stato mandato al coordinatore e girato a Risk: **corretto al coordinatore**.)

### 3.1 Input del pin — la tabella delle tre asserzioni, con la colonna che mancava

| asserzione | privacy OFF | ON oggi (formattatore di rischio) | ON dopo J |
|---|---|---|---|
| `MONEY_PATTERN` (valore) | ✅ | ❌ | ❌ |
| `'€'` (canale) | ✅ | ❌ — l'intera stringa è `•••` | ✅ se J conserva la valuta |
| `.currency-symbol` | ⚠️ sorveglia un **altro** formattatore (`formatCurrencyAmountHtml`), mai quello di rischio | ❌ | ❌ |
| nuova `not.toContain('•••')` | — | ✅ | ✅ |

## 4. R2-128 — l'accesso al sync prezzi + cambi, da ri-alloggiare nel guscio

- Il legacy portava l'unico `PageSyncModal` di Asset Global, con prezzi **e** cambi (`RiskAnalysisPanel`: derivazioni `syncAssets`/`syncFxPairs`, `risk-sync-button`, il modale). La pagina ha solo `AssetSyncModal` (prezzi). FX sulla pagina: 0 occorrenze (misura di A, R2-132).
- ⚠️ La docstring di `AssetSetRiskPanel` (*«why removing it took nothing away»*) è falsa per R2-128 → va corretta nello stesso passo.
- **Il canale di propagazione esiste già e nessuno lo alimenta**: il controller ricarica forzato quando cambia `refreshVersion` (`riskPanelController.svelte.ts`), e le tre sezioni gli passano la costante `0` (`AssetSetCorrelationSection`, `AssetSetReplaySection`, `AssetSetComparisonLevels` — **di A**). `handleSynced` = `invalidateRisk()` (cache globale di `riskStore`) + `loadBase(true)`.
- **Disegno**: pulsante `risk-sync-button` + `PageSyncModal` nella sezione controlli del guscio, con `assets` = la selezione e `fxPairs` = valuta di ciascun asset ≠ valuta obiettivo (slug ordinato, deduplicato, stessa regola di `RiskPanelHeader`) → a sync **accettato**: `invalidateRisk()` una volta, poi `refreshVersion` nuovo alle tre sezioni (D9); un'omissione vale annullamento (09 §2.5) → `onsynced` **invocato** verso la pagina alla riga di montaggio, per invalidare i prezzi della griglia → derivazione come helper puro (D10).

## 5. Citazioni per riga nei file di F

Censimento: **38 citazioni** — 8 nei tre componenti che F spedisce, 28 in `risk-lab.spec.ts` (quasi tutte di A, verso il backend), 2 falsi positivi nel test di `L4Replay`. Controllo positivo: il censimento trova entrambe le citazioni segnalate da A.

| citazione | oggi | verdetto |
|---|---|---|
| `AssetSetRiskPanel` → `:124-130` | i sette `supports*` di `RiskAnalysisPanel` | ✅ |
| `AssetSetRiskPanel` → `:874` | il blocco è a `:879` | ❌ deriva · e il testo `{#if scope.kind === 'asset'}` compare **due volte** (`:742`, `:879`) → citare **per contenimento** |
| `AssetSetRiskPanel` → `AssetRiskScenariosView:89` | `<RiskAnalysisPanel` | ✅ |
| `AssetSetCorrelationSection` → `correlation.py:128` | `method="pearson_post_fx"` | ✅ |
| `AssetSetReplaySection` → `riskStore:134` | `queryCache.get(key)` | ✅ |
| `AssetSetReplaySection` → `service.py:840` | il campo è a `:873` | ❌ deriva |
| `AssetSetReplaySection` → `L4Replay:207` | `{#if output.portfolio_return != null}` | ✅ |
| `AssetSetReplaySection` → `L4Replay:238` | `:238` è il `<p>`; la scelta è a `:237`/`:239` | ❌ **nata sbagliata, di F**: in nessuno stato committato era a `:238` |

Rimedio: rendere simboliche **tutte e 8**. Le 28 di `risk-lab.spec.ts` in F-6.

## 6. Sviluppi concordati — stato reale

| voce | stato | proposta |
|---|---|---|
| Colonna ρ̄ — D54 (`implementation/F-frontend-laboratorio.md` §6), `S5-esecuzione.md` passo 3 | ⏳ mai costruita | dopo F-3 (D3) |
| Cancello-euro «a T3» — `S5-esecuzione.md` passo 6 | la ricombinazione non è mai diventata un mandato | assorbito in F-6 |
| Filtro broker — `S5-asset-global.md` §4, `08-review-post-integrazione.md` P3.3 | D5 decisa: F lo aggiunge, Risk lo toglie, ordina il coordinatore | F-6 |
| devWiki R2-101 | 📋 aperto | F-5 |
| R2-128 | assegnato a F | F-2b |

## 7. Passi e definizione di finito

| # | passo | finito quando |
|---|---|---|
| F-0 | piano nel journal + rimando in `S5-esecuzione.md` | due file, link reciproci, `git status` mostra solo quelli |
| F-1 | rosso di partenza di `risk-lab`, spec intatto | tabella degli 11 (esito, prima asserzione, classe); confronto col verde noto; `6154` provata libera |
| F-1b | pin OFF nel test del denaro, via `privacy-toggle` (`Header.svelte`, `aria-pressed`) | stessa corsa prima e dopo il pin: esiti identici → il pin è inerte oggi |
| F-2 | chiave per-utente + TL-A | vitest N-in⇒N-out, rosso provato mutando, `front check` con hash del client, `format --check`, provato usando con due utenti sulla copia, copia rinfrescata |
| F-2b | R2-128 + TL-D | sync accessibile dal guscio; le tre sezioni ricaricano; docstring corretta; zero euro per ricerca |
| F-2c | citazioni simboliche | le 8 dei componenti senza numeri di riga; il censimento le ritrova tutte e non ne trova di nuove |
| F-3 | review del laboratorio sulla copia, col developer | §9 alla lettera; scheda chiusa; server spento; `6164` provata libera |
| F-4 | colonna ρ̄ + TL-B | helper puro nella sezione di F; i18n via `dev.py i18n` × 4, ICU `{x}` |
| F-5 | devWiki R2-101 | pagine nel devWiki del worktree; `check_source_paths.py` verde; graphify assente nel worktree → dichiarato |
| F-6 | chiusura `risk-lab`, dopo le review di Risk e A e dopo J | rieseguito prima; poi TL-C; filtro broker nell'ordine del coordinatore; `panelTitle` rimossa; cancelli verdi |
| F-7 | handoff | voci CHANGELOG proposte · commit proposti · condivisi elencati · `FROZEN` con `lsof` su entrambe le porte |

Dopo ogni passo: questo piano aggiornato con data, `Note implementazione`, `Fuori pista`.

## 8. Test list (approvata con il piano)

**TL-A · selezione per-utente** — vitest, `assetSetSelection.test.ts` (`front-utility core-unit`)
1. scrive sotto `lf_<id>_assetGlobal.riskSelection.v1`, mai sotto la chiave nuda · 2. l'utente B non legge la selezione di A → `mine` · 3. una chiave nuda preesistente non è adottata e viene rimossa · 4. senza utente di sessione: nessuna persistenza · 5. la scala esistente invariata

**TL-B · colonna ρ̄** (se D3) — vitest, `correlationHelpers.test.ts`
1. 3×3 nota → media fuori diagonale calcolata a mano · 2. insieme di 2 → l'unico ρ; di 1 → assente, mai `0` · 3. celle nulle escluse e contate · 4. segno secondo D3

**TL-C · chiusura `risk-lab`** — E2E

| # | test | azione |
|---|---|---|
| C1a | nessun denaro — privacy OFF | pin (F-1b) |
| C1b | nessun denaro — privacy ON | dopo J: `not.toContain('•••')` + `'€'` se J conserva la valuta; barriere di presenza prima; via `privacy-toggle`; niente `SAFE_CALL` |
| C2 | apertura D19 | + `data-selection-source` per ramo · + caso incrociato `e2e_test_user` → esce → `e2e_test_admin`: sorgente ≠ `persisted` |
| C3-C6 | massive · filtro · coppie · ordinamento | riallineare al rosso; C4 dipende dai tipi (K) |
| C7 | guardiano del catalogo | intatto |
| C8-C11 | i quattro di A | riallineare dopo la review di A |
| C12 | preset broker (D5) | carica esattamente gli `asset_id` delle holding; nessun importo attraversa; svuotarlo non resetta la selezione |
| C13 | ρ̄ (se D3) | coincide con la matrice; nessun euro |
| C14 | sync dal guscio (R2-128) | pulsante nella sezione controlli; il modale riceve le coppie FX della selezione |
| C15 | ricarica dopo sync | a sync accettato ciascuna delle tre sezioni ri-chiede (contato dal proprio `page.route`); annullato → nessuna ricarica |

**TL-D · derivazione del sync** (D10) — vitest: asset deduplicati e noti · coppie FX solo per valuta ≠ obiettivo, slug ordinato, deduplicate · tutte in valuta obiettivo → nessuna coppia · id sconosciuti saltati

Isolamento: ogni test possiede i propri `page.route`; niente posizioni fisse, conteggi globali, attese a orologio, testo tradotto. Scrittura con `test-author`.

## 9. Copia di prod

Procedura del coordinatore (dalla snapshot `/tmp/librefolio-r2-prod-snapshot`, con `chmod -R u+w` sulla copia; deve stampare `004_release_1_2_0_schema`; snapshot assente → chiederla, mai ricostruirla dal main checkout).
**Credenziali**: fornite dal coordinatore il 23/09, **non trascritte** (questo file è versionato). Prima di ogni `reset`: `LIBREFOLIO_TEST_DATA_DIR=/tmp/librefolio-r2-f-prodcopy PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py user --test-db list` — controllo positivo: devono comparire gli utenti della copia, non gli `e2e_*` del checkout.
**Server**: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py server --test --port 6164 --data-dir /tmp/librefolio-r2-f-prodcopy`
**Coordinate**: `http://localhost:6164/assets?tab=correlation` · HEAD · `porcelain` scomposto · `cwd` del processo · `db_path` dal log · freschezza del bundle (nessun sorgente più nuovo di `frontend/build/index.html`) + chunk costruito == servito · hash degli artefatti di `api sync` · `data-selection-source`.
**Difetto** = euro o `•••` nel pannello · seconda heatmap · sorgente inattesa · chip ≠ `data-selected`. **Non difetto** = Abs/% che qui non agisce.

## 10. Decisioni

| | domanda | stato |
|---|---|---|
| D1 | rosso di partenza adesso (F-1) | ✅ accolta la raccomandazione: sì |
| D2 | chiave per-utente (N1) | ✅ sì, senza migrazione |
| D3 | colonna ρ̄ | dopo F-3; con segno; nella sezione di F |
| D4 | §1.6 → F | ✅ decisa dal coordinatore |
| D5 | filtro broker → `risk-lab`, stesso lotto | ✅ decisa, ordine del coordinatore |
| D6 | `panelTitle` → F a fine round | ✅ decisa |
| D7 | doc: frase Abs/% + pagina del laboratorio | ✅ **decisa dal coordinatore**: pagina di Asset Global e voce di nav le scrive **A** (suo D1); la frase di §9.1 F la **manda al coordinatore**, che la gira ad A — F non la scrive |
| D8 | R2-128 adesso | ✅ sì (F-2b) |
| D9 | ricarica della sezione di A dopo il sync | ✅ **decisa (a), la riga la scrive F**: in `AssetSetComparisonLevels.svelte` `refreshVersion` diventa prop **opzionale con default `0`** (comportamento identico finché il guscio non la alimenta); A non tocca il file finché R2-128 è aperto. Se D8 venisse rinviata, D9 decade |
| D10 | derivazione prezzi/cambi | helper puro di F + proposta a Risk di adottarlo in `RiskPanelHeader` |

## 11. Previsione dei conflitti

| ws | superficie | rischio | contromisura |
|---|---|---|---|
| A | non tocca più `risk-lab.spec.ts` né il guscio (unico scrittore: F) · resta la sua sezione (D9) | 🟠 | una riga con assenso, oppure `{#key}` |
| Risk | `CorrelationHeatmap` (di F, montata da `L2Diversification`) · `L4Replay` · `RiskLevelSection` (12 testid) · rimozione del filtro broker da `risk-analysis.spec.ts` · adozione facoltativa dell'helper di D10 | 🟠 | un solo scrittore per la heatmap; ordine D5 dal coordinatore |
| J | ripara `riskAnalysisHelpers:160` (blocca C1b) · `privacy-toggle` è il punto d'ingresso | 🟡 **pronto nel checkpoint C1 di J** (24/09); non ancora nel target, il commit è del developer | C1b solo quando C1 è nel target (F-6) |
| K | `utils/assetTypes.ts` · i chip di F leggono `assets.types.${type}` | 🟡 | i tipi nuovi arrivano da soli se K aggiunge le etichette |
| I | `assets/+page.svelte` condiviso | 🟢 | nessuna riga comune salvo quella di montaggio |
| D | — | 🟢 | — |
| condivisi | cataloghi i18n · runner · devWiki `index.md`/`log.md` · journal · riga di montaggio in `assets/+page.svelte` | 🟡 | solo aggiunte, elencati nell'handoff |

## 12. Comandi

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6154 --data-dir /tmp/librefolio-r2-f front-portfolio risk-lab
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6154 --data-dir /tmp/librefolio-r2-f front-utility core-unit
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test check-orphans
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check   # con shasum di generated.ts accanto
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front format --check
cd frontend && npx vitest run <N path>                                             # Test Files deve dire N
lsof -nP -iTCP:6154 -sTCP:LISTEN; lsof -nP -iTCP:6164 -sTCP:LISTEN                 # a ogni FROZEN
```

## 13. Rischi

- F-6 dipende da tre calendari (Risk, A, J): fino ad allora `risk-lab` resta rosso **dichiarato**, non ignorato.
- Il rosso di F-1 può contenere cause d'ambiente: hash del client prima della corsa.
- Una rinomina in `RiskLevelSection` rompe 12 selettori senza toccare `risk-lab.spec.ts`.
- Snapshot in `/tmp`: un reboot la cancella.
- Evidenze irriproducibili: mai in `/tmp` né nella data-dir.

---

# Esecuzione

## F-0 — piano nel journal ✅ 2026-09-23

> **Note implementazione**: creato questo file e aggiunto un rimando di 4 righe in testa a
> `S5-esecuzione.md` (`git diff --numstat` → `4 0`: additivo per misura, la tabella ferma al 18/09
> resta com'era). `git status --porcelain -uall` → esattamente questi due percorsi. I percorsi citati
> nel piano esistono tutti; nessuna credenziale trascritta.
>
> **⚠️ Fuori pista**: nella cartella esistono `F1-esecuzione.md` e `F2-esecuzione.md` — le **fasi** 1 e 2
> della campagna rischio. Il nome approvato è rimasto, ma l'intestazione dichiara l'omonimia: chi cerca
> «F» in questa cartella trova tre cose diverse, e solo una è questo workstream.

## F-1 — rosso di partenza di `risk-lab` ✅ 2026-09-23 · **non c'è rosso**

```
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6154 --data-dir /tmp/librefolio-r2-f front-portfolio risk-lab
15:57:20 → 15:59:35 · exit 0 · Running 11 tests using 1 worker · 11 passed (17.1s)
```

> **Note implementazione**: prima della corsa `HEAD f1047f766`, spec `sha256 480b5e4381af5f7e`
> (intatto), `generated.ts a085da1c8dac55f9`, `6154` libera. Nel log: `6154` ×3, `6041` ×0; data-dir
> `/tmp/librefolio-r2-f`. Dopo: `6154` e `6164` libere, nessun processo residuo della lane, `git status`
> invariato (solo i due file del journal). Lo snapshot del DB di test finisce in `.testLog/00_archive/`,
> ignorato.
>
> 🔑 **La lettura che cambia F-6.** Il verde noto del 21/09 (11/11 sul ramo di A) **regge sulla
> revisione integrata**: i merge successivi (privacy di J, banner beta, grafici, onboarding) non hanno
> rotto nulla. Con la ricognizione statica a zero su nomi, tipi e rotte, il quadro è netto:
> **`risk-lab` non è indietro perché fallisce, è indietro perché non copre ciò che il sistema fa oggi**
> — preset broker, privacy ON, selezione per-utente, sync, ρ̄. F-6 è quindi un lavoro di
> **copertura** più che di riparazione.
>
> **⚠️ Fuori pista**: il runner ha scritto *«Shared backend ignored SIGTERM for 5s — killing its process
> group»*. Il backend condiviso non ha risposto al SIGTERM ed è stato ucciso; verificato dopo: nessun
> processo residuo e porta libera. È un comportamento del runner, non del codice di F: segnalato al
> coordinatore, non indagato qui.
>
> **Decisioni arrivate durante il passo** (coordinatore, 23/09): approvazione del piano **del developer**;
> D9 → (a), riga scritta da F; D7 → la doc utente di Asset Global è di A.

## F-2c — citazioni per riga → simboliche ✅ 2026-09-23

> **Note implementazione**: le 8 citazioni dei tre componenti sono diventate riferimenti a simboli:
> `supports*`/`hasRiskCapability` · il blocco che contiene `risk-replay-controls` · `AssetRiskScenariosView`
> · l'unica assegnazione di `method` in `risk_plugins/correlation.py` · `queryRisk` in `riskStore` · il
> builder `_metadata` del servizio · la guardia `{#if output.portfolio_return != null}` · il predicato
> `omitted` di `L4Replay`. **Prova per somma e per assenza**: censimento prima 38, dopo 30 (−6 nominate,
> −2 nude); 0 nei tre componenti. Ogni ancora nuova esiste **una sola volta** (`grep -c` = 1 ciascuna).
> Diff: solo righe di commento (`git diff -U0` filtrato → vuoto); `prettier --check` sui tre file → pulito.
>
> **⚠️ Fuori pista**: la mia proposta del piano («citare per contenimento: la guardia dentro
> `{#if supportsStress}`») **non disambiguava**: misurato, entrambe le `{#if scope.kind === 'asset'}` di
> `RiskAnalysisPanel` stanno dentro `supportsStress`. Una contiene i controlli dello shock
> (`risk-stress-buckets`), l'altra `risk-replay-controls`. L'ancora giusta era il **contenuto**, non il
> contenitore — e la regola generale ne esce più precisa: *citare il simbolo* presuppone un simbolo unico;
> quando non lo è, si cita **ciò che il blocco contiene**, verificandone l'unicità.
> La correzione della frase falsa sul legacy (*«took nothing away»*, R2-128) resta a F-2b, dove esiste
> la cosa vera da scrivere al suo posto.

## In corso — 2026-09-23, stato intermedio (non passi chiusi)

**F-1b** — pin scritto da `test-author` (+34/−0: helper `pinPrivacyOff` via `privacy-toggle`/`aria-pressed`,
chiamato nel solo test del denaro), `tsc` e Prettier puliti. Manca la corsa «dopo».
⚠️ **Tre premesse del mio brief corrette da `test-author`**: (1) sul laboratorio è montato **solo**
`L4Replay`, non L4Shock né L1HowMuchItHurts (importano lo stesso formattatore, ma non sono sulla pagina);
(2) `.currency-symbol` ha **due** sorgenti — anche `formatCurrencyCodeHtml` (un codice valuta senza importo,
che il test stesso dichiara lecito) → incoerenza latente dell'asserzione 3, da risolvere in F-6;
(3) 🔴 **conseguenza del mio F-2**: lo spec ripulisce ancora la chiave nuda (`SELECTION_STORAGE_KEY`), quindi
«opens on a small selection» non garantisce più da sé la prima visita (passa solo perché il contesto è nuovo).

**F-2** — codice fatto (`assetSetSelection.ts`: chiave `lf_<id>_…`, niente identità ⇒ niente memoria, chiave
nuda rimossa e mai adottata). Misura sui test esistenti: **8 rossi rumorosi + 3 verdi a vuoto** («reading
throws», «refuses the write», «stores an empty selection» non toccano più lo storage). TL-A in scrittura.
**La corsa d'identità al boot non mi colpisce, per lettura del codice**: `initialState.user = null`,
`isAuthenticated = user !== null`, e l'utente entra solo in `login`/`checkAuth` **dopo**
`transitionClientSession(user.id)`; il layout `(app)` rende i figli solo `{:else if $isAuthenticated}`.
⚠️ Il commento di A in `risk-lab.spec.ts` (test del benchmark, «BOTH SPELLINGS OF THE KEY») descrive una
corsa che questa lettura rende irraggiungibile: **lettura, non esecuzione** — da verificare prima di toccarlo in F-6.

**F-2b** — codice fatto: helper puro `syncTargets.ts` (stessa regola di `RiskPanelHeader`, **incluse le sole
coppie configurate** — dettaglio che il piano non aveva); pulsante `risk-sync-button` + `PageSyncModal` nel guscio;
`invalidateRisk()` una volta, poi `syncGeneration` → `refreshVersion` alle tre sezioni (in `AssetSetComparisonLevels`
prop opzionale con default `0`, D9-a); il replay **scarta** anche la propria risposta (`resetAnalysis('replay')`).
🔑 **Perché serve lo scarto, misurato nel controller**: un cambio di input scarta le risposte on-demand, `handleSynced`
le scarta, ma `refreshVersion` fa **solo** `loadBase(true)` e le conserva — il replay sarebbe rimasto calcolato sui
prezzi vecchi. `onsynced` ripristinato alla riga di montaggio di `assets/+page.svelte`, **invocato**. Docstring del
guscio corretta (*«the one thing its removal did take away»*). Cancelli statici: in attesa della fine di TL-A.

**D5 — ordine del coordinatore**: F aggiunge il test del preset broker in `risk-lab.spec.ts`, lo fa girare verde
sulla `6154`, manda il **nome esatto**; solo dopo Risk rimuove `risk-analysis.spec.ts:1335`; `desc=` del runner:
F solo per aggiunta. ⚠️ **Il test di Risk copre di più del preset** — rimuovi/riaggiungi un chip, banner beta
assente, heatmap presente — quindi C12 dev'essere un **sovrainsieme**, o lo spostamento perde copertura in silenzio.

**F-5** — affidato a `project-historian`: 3 pagine nuove (R2-101) + 3 aggiornamenti di pagine **superate**:
`decisions/asset-global-page-shows-no-money` (diceva «nessuna guardia frontend»), `problems/asset-set-scope-has-no-primary-series`
(le KPI per-asset le ha poi costruite A), `problems/testid-grep-false-negative`.
🔴 **Errore mio**: quella pagina descrive esattamente la mia prima sonda sbagliata di stamattina. **Non ho eseguito
`wiki-search` all'inizio del turno**, come la regola chiede, e ho riscoperto un problema già archiviato.

## F-1b — pin privacy OFF ✅ 2026-09-23

```
spec 480b5e4381af5f7e → 44a9ce9be9939bb9 (+34/−0, helper pinPrivacyOff + una chiamata)
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6154 --data-dir /tmp/librefolio-r2-f front-portfolio risk-lab
16:22:32 → 16:24:21 · exit 0 · 11 passed — stessi 11 nomi di F-1, righe spostate di +29/+34
```

> **Note implementazione**: scritto da `test-author` (tsc e Prettier puliti); corsa mia. Il pin passa dal
> controllo pubblico (`privacy-toggle`, `aria-pressed`), mai dalla chiave di J; l'asserzione finale è
> incondizionata, ed è il controllo positivo che il pin ha avuto effetto. `6154` e `6164` libere dopo.
>
> **⚠️ Fuori pista**: il «prima e dopo» **non è isolato**. Fra F-1 e questa corsa sono cambiati sia lo spec
> (il pin) sia l'app (F-2, F-2b). Esiti identici provano che **nessuno dei due** ha rotto gli 11 test; l'inerzia
> del pin è mostrata congiuntamente, non da sola — sostenibile perché le modifiche app non toccano la privacy,
> ma è una misura su una coppia, non su un termine (09 §3.13).

## F-2 — cancelli statici della revisione con F-2 e F-2b dentro

```
generated.ts a085da1c8dac55f9 · front check 16:20:34→16:21:02: 3 errori + 41 avvisi in 4 file, 0 in risk/ e in assets/+page
  errori: TransactionFormModal.test.ts ×2, ToolExecutionMetrics.svelte ×1 (il pavimento noto)
  avvisi: BrokerSharingPanel 27 + GlobalSettingsTab 14 — nessuno nei file toccati (composizione, non totale)
front format --check: ROSSO su syncTargets.ts (file nuovo mio) → prettier --write su quel solo file
  (diff: la firma su una riga) → ricontrollo: verde
vitest, 7 path ⇒ Test Files 7 passed (7) · 260 test
```

> **TL-A** (da `test-author`): 69 verdi (62 + 7). Mutazione `storageKey → chiave nuda`: **5 rossi**, tutti
> sull'asserzione voluta; SHA di `assetSetSelection.ts` ripristinato (`9efb66cc…`). I tre verdi a vuoto ora
> provano di raggiungere lo storage (contatori sui tentativi, controllo di lettura prima dell'assenza).
> **Due mie premesse corrette**: un `undefined` esplicito **non** è «nessuna identità» — il default lo sostituisce
> con l'utente di sessione; e TL-A3 com'era scritto non poteva andare rosso sotto quella mutazione (la rimozione
> della chiave nuda avveniva prima della lettura): diviso in «non adottata» e «rimossa», entrambi rossi sotto mutazione.

## F-2b — il sync nel guscio: un difetto mio trovato da C14, rosso **provato** prima della riparazione

> **Note implementazione**: `test-author` ha scritto C12 (preset broker, sovrainsieme del test di Risk), C14 (bersagli
> del sync), C15 (ricarica dopo il sync), TL-D (`syncTargets.test.ts`, 10 test, rosso per mutazione) e il test sul
> default di sessione di TL-A. Registrato `syncTargets.test.ts` in `front-utility core-unit`; `desc=` di `risk-lab`
> estesa **solo per aggiunta** (provato: togliendo la clausola la riga torna identica all'HEAD).
>
> 🔴 **Il difetto, mio**: `AssetSetRiskPanel` leggeva `getConfiguredPairSlugs()` senza mai chiamare
> `ensureFxRoutesLoaded()`. Su `/assets` niente carica lo store delle rotte: la pagina scarica **la stessa lista** in
> una variabile propria (`loadFxPairSlugs`), e l'unico `CurrencySearchSelect` della pagina non è `configuredOnly`.
> Quindi `fxPairs` era sempre `[]`: **il mio F-2b riportava sulla pagina un sync solo prezzi, cioè la perdita di R2-128**.
> Nessuna mia prova l'avrebbe visto: la derivazione era giusta, era il suo **ingresso** a essere sempre vuoto.
>
> ```
> ROSSA  16:55:21→16:57:25 · 13 passed, 1 failed: C14 «the modal must target assets [1, 2, 6, 7] and pairs [EUR-USD]»
>        sync-modal-count Expected "5" Received "4" (data-section-count="1": la sezione cambi manca)
> fix    Promise.all([ensureAssetsLoaded(), ensureFxRoutesLoaded()]) al montaggio — il precedente di RiskAnalysisPanel;
>        anche lo store asset: oggi lo scalda per caso il selettore di aggiunta, ed è lo stesso genere di dipendenza
> VERDE  16:59:36→17:02:08 · C14 ✅ — ma C12 e C15 ROSSI (verdi nella corsa rossa) → triage sotto
> front check (post-fix) 3 errori + 41 avvisi negli stessi 4 file, 0 nei miei · format --check ✅ · vitest 8 path ⇒ 8, 271
> ```

## Triage di C12 e C15 (skill `test-triage`) — verdetto: **difetto**, non instabilità

> **Evidenza** (§0, prima di ogni rilancio): C12 `risk-selected-count` = *«0 selected of 17»* per 15 s, nessun
> `risk-broker-filter-error`; C15 sezione replay aperta, *«Run replay»* inerte, nessuno spinner né errore, nessuna riga.
> **Due risposte arrivate, due schermi vuoti.**
>
> **Catena, verificata nel codice e nel log del backend della corsa**:
> 1. il polling dei prezzi live di `assets/+page.svelte` (attivo se la finestra finisce oggi) → `POST /api/v1/assets/prices/current`
>    su `axiosInstance`, **due volte per ogni caricamento** — in **tutte e quattro** le corse di oggi, anche F-1, prima di
>    ogni mia riga (conteggio per login: F-1 `[0,0,0,5,2,1,2,0,2,1,2,4]`); ogni chiamata **scrive** (*«Current-price
>    persist … commit OK (14 row(s) written/updated)»*), quindi classificarla mutazione è corretto;
> 2. intercettore → `notifyPortfolioMutation` → `portfolioStore.invalidate` e `riskStore.invalidateRisk`
>    (quest'ultima registrata **come callback** a `riskStore:194`: il mio primo `grep invalidateRisk\(` la dava per assente);
> 3. `fetchReport` / `queryRisk` in volo → **`null`** (scarto);
> 4. C12: il **mio** `applyBrokerPreset` leggeva `null` come «nessuna partecipazione» e **azzerava la selezione**;
>    C15: `riskPanelController.runGuarded` → `setResult('replay', null)` → **codice di Risk**.
>
> Timeline di C12 (UTC): login 22.400 · report 22.54–22.72 · **scrittura 23.072** · report 23.117 · **scrittura 23.429** ·
> report 23.72–23.89. Totale scritture rossa 28 = verde 28: **la mia modifica non ha aggiunto chiamate**; cambia solo dove
> cade la scrittura, al sotto-secondo.
>
> ⚠️ **Fuori pista — un controllo positivo che ha evitato un falso «assente»**: `librefolio.log` non contiene
> `prices/current`, ma nemmeno `auth/login` né alcun `/api/v1/` — il log non registra percorsi. Lo zero era cieco.
>
> **Riparazione mia (C12)**: su un `null` il preset richiede **una volta** — la politica di `loadBase` dopo R2-66 — e se lo
> scarto si ripete alza `brokerLoadFailed` e **lascia la selezione com'era**. Verificato che la nuova richiesta non si
> aggancia a quella scartata: `invalidate()` fa `reportInflight.clear()`.
> **Test**: `test-author` isola il laboratorio dal polling (attore in background non controllato, che scrive 14 righe nel DB
> condiviso a ogni pagina) e scrive C12b/C12c **deterministici**: è il test a liberare la scrittura mentre il report è in volo.
> **C15**: nessun ritocco al test; il difetto è di Risk e glielo passo con l'evidenza.

## F-5 — devWiki R2-101 ✅ 2026-09-23 (`project-historian`)

> **Creati**: `problems/discarded-risk-answer-read-as-empty` · `concepts/span-as-a-detector` · `problems/tab-writes-after-the-look`.
> **Aggiornati**: `decisions/asset-global-page-shows-no-money` (aveva «nessuna guardia frontend») ·
> `problems/asset-set-scope-has-no-primary-series` (→ risolto) · `problems/testid-grep-false-negative` (recidiva del 23/09).
> `check_source_paths.py` sulle 6 pagine: 0 mancanti su 66; il resto del wiki ha 60 mancanti in 56 pagine **non toccate**.
> Verificato da me: solo file sotto `LibreFolio_devWiki/`, nessuna credenziale. graphify assente nel worktree → aggiornamento del grafo rinviato.
>
> **Tre smentite del historian, verificate da me**: (1) `032b86959` non tocca il backend: `asset_set_kpi.py` nasce in
> `d3afb92b6` (P) — **errore del mio brief**; (2) **11 composti, non 12** — errore mio di lettura del mio log, e il 12 era
> già arrivato a Risk; (3) la corsa d'identità di R2-66 è **irraggiungibile** per lettura (il layout `(app)` rende solo
> dopo l'autenticazione): la causa raggiungibile dello stesso sintomo è il polling qui sopra. **R2-66 aveva la
> riparazione giusta e la diagnosi sbagliata**: la re-richiesta cura l'effetto, qualunque sia la causa.

## Correzione del coordinatore su F2 (23/09)

> Sul perimetro `asset_set` un asset senza prezzi è **escluso** (`missing_price`, avviso `assets_excluded`), non liquidità:
> misurato da A sulla copia (574 osservazioni con e senza il crowdfunding). F2 vale per il **portafoglio**. Per ρ̄ (F-4):
> l'esclusione va **mostrata**.

## Quattro reperti dello specialista doc di A nei miei file — verificati

| # | reperto | verifica | esito |
|---|---|---|---|
| 1 | «By name» ordina per id | ✅ `original` teneva `[...output.asset_ids]`, e la richiesta canonicalizza crescente; **il mio test 6 fissava lo scollamento** (*«the original ordering is the payload order, ascending by id»*) | **riparato**: helper puro `nameOrder` (collatore, pareggi per id); modo rinominato `original` → `name` (testid `risk-correlation-ordering-name`); chiave i18n `risk.assetSet.ordering.name` aggiunta via `dev.py i18n` ×4 (`2 1` per file). Vale anche su `L2Diversification` (Risk), stesso componente |
| 2 | colori invertiti heatmap/coppie | ✅ heatmap −1 rosso / +1 blu (`16ff0eb57`, citata come «già giusta» da 05 §8); la **mia** lista faceva il contrario **e la sua docstring giurava il contrario** | **riparato** allineando la lista alla heatmap (valore e badge). La polarità è una scelta estetica → **al developer in F-3**: invertirla è una riga nel `visualMap`, e sposta anche la Dashboard |
| 3 | il replay offre un sostituto che non esiste | ✅ *«Leave it out, or give it a stand-in»*, ma c'è solo `risk-replay-exclude`; `proxyAssets: []` fisso in `L4Replay:101` | **di Risk** (componente e chiave `risk.levels.l4.replayNeedsChoice`), visibile su ogni pagina che monta L4 → riportato |
| 4 | teoria della correlazione contro il codice | ✅ la pagina dice «minimo per coppia»; `pairwise_correlation_matrix` restituisce **un** conteggio per tutta la matrice e il plugin marca **tutte** le celle insieme — contraddice anche il riquadro della pagina stessa | **a `docs-writer`**, solo `.en.md`, senza `translate-stamp` (il debito di traduzione deve restare visibile) |

> **Da togliere a fine round** (decisione del developer: nessuna chiave morta prima): `risk.assetSet.panelTitle` e
> `risk.assetSet.ordering.original`. ⚠️ La seconda sta sotto un prefisso dinamico (`risk.assetSet.ordering.${mode}`):
> l'audit la considererà «potenzialmente usata» per sempre, quindi **va nominata**, o non verrà mai tolta.

## Reperto 4 — pagina di teoria, primo passaggio di `docs-writer` (23/09)

> **Note implementazione**: `correlation.en.md` +7/−5 — la soglia di osservazioni è **dell'intera matrice** (un solo
> calendario condiviso ⇒ un solo conteggio), `insufficient_pair_history` nonostante il nome riguarda tutta la matrice,
> una serie piatta svuota solo la propria riga e colonna; un asset **senza prezzi** su un insieme di asset è escluso
> (`missing_price`, `assets_excluded`, esito `partial`) senza accorciare la finestra — nulla sul portafoglio.
> **Verificato eseguendo** il vero `RiskService.execute` su dati sintetici (solo le due letture DB sostituite): 44
> osservazioni con e senza l'asset senza prezzi; `min_observations=50` ⇒ 9/9 celle `insufficient`.
> `mkdocs build` exit 0, zero WARNING · `check-links` exit 0, 80 validi · `translate-validate` 0 file (nessuna traduzione).
>
> **⚠️ Fuori pista — due premesse del mio brief smentite**: (1) la pagina **non ha mai avuto traduzioni** («le traduzioni
> portano lo stesso errore» era una mia supposizione); (2) **`min_coverage` non può scattare**: la copertura vale 1,0 per
> costruzione (la serie preparata impone a tutte lo stesso numero di punti) → l'avviso `low_pair_coverage` è morto e il
> parametro non controlla nulla → **difetto del backend, riportato**, non documentato (documentarlo = descrivere un
> comando che non fa niente).
>
> **Secondo passaggio chiesto**: le imprecisioni **verificate** rimaste nella mia pagina (date «riportate», storia «a buchi»
> che in realtà è riempita in avanti senza limite, «valuta del portafoglio», «diagonale sempre +1») e **una sola frase** di
> `data-quality.en.md` (la soglia «cell by cell»): la mia correzione aveva messo le due pagine in contraddizione. Il resto
> di `data-quality` (lo stato `partial` di §Alignment, falso anch'esso) **non** lo tocco: lo riporto.

## Chiusura del lotto F-1b…F-2c + reperti — 2026-09-23, 17:35

> **Riparazioni di prodotto aggiunte dopo la triage**:
> - `applyBrokerPreset`: su `null` richiede una volta, poi `brokerLoadFailed` e la selezione resta com'era.
>   Il commento corretto da `test-author`: `fetchReport` risponde **report o `null`** (il `null` copre scarto **e**
>   fallimento, perché trasforma ogni errore in `null`); il `catch` non è raggiungibile da un fallimento del report.
> - `handleSynced`: **prima la pagina, poi le sezioni** (`try { await onsynced } finally { invalidateRisk; syncGeneration++ }`).
>   Misurato: l'`onsynced` della pagina riassegna `assets` fino a 4 volte e il polling riparte a ogni riassegnazione
>   (4 scritture, 4 invalidazioni). Nell'ordine vecchio le sezioni ricaricavano **attraverso** quella raffica, e `loadBase`
>   richiede una volta sola. La mia docstring (*«cannot discard»*) era falsa, ed è stata riscritta.
> - Reperti 1 e 2 di A: `nameOrder` + rinomina `original` → `name`; lista delle coppie allineata alla polarità della heatmap.
>
> **Test** (`test-author`, compiti 4-5): polling **trattenuto** in `installRiskMocks` (mai risposto: una risposta
> simulata passerebbe comunque dall'intercettore e invaliderebbe; l'unico effetto è un avviso non critico dopo il
> timeout di 30 s di axios). C12b e C12c **deterministici** con un metodo diverso da quello chiesto: liberare il polling
> non si poteva rendere deterministico (due completamenti XHR indipendenti, ordine non garantito); la mutazione è una
> corsa di sync, e il report trattenuto viene liberato solo dopo che il sync ha mosso la generazione. Test 6 riallineato
> sull'ordine per nome, con una precondizione che l'ordine alfabetico ≠ ordine per id (Bitcoin ed Ethereum prima di
> Microsoft e Tesla). `nameOrder`: 7 test, mutazione → 5 rossi.
>
> **Cancelli sulla revisione finale**:
> ```
> front check 17:32 · 3 errori + 41 avvisi negli stessi 4 file, 0 nei miei · generated.ts a085da1c8dac55f9
> front format --check ✅ · vitest 8 path ⇒ Test Files 8 passed (8) · 278 test
> front-portfolio risk-lab 17:33:54→17:35:45 · exit 0 · 16 passed (16 dichiarati) · 6154/6164 libere dopo
> check-orphans exit 1 — 5 orfani, TUTTI di J (privacyStore, privacyStoreSsr, currencyFormat, maskable,
>   moneyRenderSites; b66e93003 / 9a6dd2015), 0 menzioni all'HEAD con controllo positivo → rosso GIÀ sul target
> ```
>
> **Reperto 4 chiuso** (secondo passaggio di `docs-writer`): `correlation.en.md` +10/−8 cumulativo, `data-quality.en.md`
> +1/−1 (solo la frase «cell by cell»). Build rigoroso e check-links puliti; verificato con un secondo giro sul vero servizio
> (buco di 20 giorni: 90 osservazioni e 20 punti riempiti in avanti; ritardatario: 44 e nessuna data elencata).
> **⚠️ Fuori pista**: le «due soglie» del mio brief non esistono — la soglia dichiarata del plugin (2) non si applica mai
> alla correlazione (il servizio salta il cancello di rifiuto); agisce solo il parametro (20).
>
> **D5**: nome esatto di C12 mandato al coordinatore dopo la corsa verde. ⚠️ **Fuori pista**: il mio `grep "test('broker preset"`
> dava due risultati su tre — il titolo di C12 usa le **virgolette doppie** per l'apostrofo di *broker's*. Nome ricopiato
> dalla riga dello spec **e** dal referto della corsa, che coincidono.
>
> **Riportati, non miei**: il cancello privacy di J non è eseguito dal runner · il polling che riparte a ogni riassegnazione
> di `assets` · `runGuarded` (Risk) · il sostituto inesistente del replay (Risk) · `min_coverage` morto · riempimento in
> avanti senza limite · `data-quality` §Alignment · `en.json:3228`.

## F-2d — il polling dei prezzi live di `/assets` riparte solo se cambiano gli asset ✅ 2026-09-23 (voce nuova)

> **Assegnata dal coordinatore** (23/09): F è l'unico che scrive in `routes/(app)/assets/+page.svelte` in questo
> round, quindi il difetto della pagina è di F. **Ordine rispetto a F-3, deciso da F**: prima la riparazione, perché il
> server della review fa proprio questo polling (finestra che finisce oggi) e il developer vedrebbe gli effetti della corsa
> — per esempio un replay che finisce senza risposta, il difetto di Risk — invece del laboratorio.
>
> **Difetto misurato**: l'effetto leggeva `assets` direttamente e attraverso la testa sincrona di `fetchLivePrices`
> (che legge `assets.map(a => a.id)` prima del primo `await`), quindi ripartiva a **ogni riassegnazione** della lista;
> `fetchAllPriceData` la riassegna fino a 4 volte → fino a 4 `POST /assets/prices/current` per refresh, ognuno una
> scrittura di 14 righe e un'invalidazione globale di report e rischio.
>
> **Note implementazione**: chiave derivata `liveAssetIdsKey` = id ordinati uniti in stringa (una stringa si confronta
> per valore: non cambia finché non cambiano gli id); l'effetto legge solo `isHeadToday` e la chiave; `fetchLivePrices`
> chiamata sotto `untrack`. **Preservato esplicitamente** il comportamento che prima c'era per incidente: «Refresh All» e
> l'`onsynced` di `AssetSyncModal` chiedono **un** polling subito (`refreshLivePricesNow`, solo se la finestra comprende
> oggi). Non aggiunto all'`onsynced` del laboratorio: quel tab non mostra prezzi live e correrebbe contro le sezioni.
> La docstring di `handleSynced` (scritta mezz'ora prima) diceva che il polling riparte a ogni riassegnazione:
> **corretta** subito — l'ordine «prima la pagina» resta, ora motivato come difesa se il difetto tornasse.
>
> ```
> front check 17:41 · 3 errori + 41 avvisi negli stessi 4 file, 0 nei miei · format --check ✅
> front-portfolio risk-lab 17:42:26→17:44:14 · exit 0 · 16 passed · 6154/6164 libere
> ```
>
> **Test list per il developer (TL-P)** — non scritti, come da regola sui frontend:
> 1. caricamento di `/assets` (griglia) con finestra che finisce oggi: **esattamente 1** `POST /assets/prices/current`
>    (contato con un `page.route` che risponde vuoto) — prima 2-4;
> 2. un refresh che riassegna `assets` senza cambiare l'insieme (per esempio il cambio del periodo del delta o un
>    `fetchAllPriceData` interno): **0** polling in più fino al tick successivo;
> 3. «Refresh All» e sync della griglia: **+1** polling ciascuno, non +4;
> 4. l'insieme degli asset cambia (aggiunta, cancellazione, fusione): **+1** polling;
> 5. finestra storica (non comprende oggi): **0** polling, e nessun polling nemmeno da «Refresh All»;
> 6. il tick dei 30 s continua a funzionare (`page.clock` avanzato di 30 s → +1), senza attese a orologio reale.
> Collocazione naturale: lo spec della pagina asset (di K/B) o uno spec nuovo della pagina — decisione del coordinatore.

### F-2d — prova per uso ✅ 2026-09-23, 17:45–18:00

> Server di misura sulla copia rinfrescata alle 17:37:18 CEST (`--port 6164 --data-dir /tmp/librefolio-r2-f-prodcopy`), log dello stdout
> del server nella cartella di sessione (`files/F3_server_measure.log`). ⚠️ **Corretto il 24/09**: la copia **non era intatta**
> alla partenza di questo server. Il primo server sulla stessa copia (avviato alle 15:37:32Z, fermato prima di questo)
> ci aveva già fatto scrivere il suo scheduler: vedi le 575 osservazioni in F-3. Il conteggio dei polling qui sotto non ne dipende. ⚠️ **Qui le righe d'accesso di uvicorn ci
> sono**, a differenza di `librefolio.log`: il conteggio si fa per percorso. Tutte le navigazioni sono **in-app**.
> Orari in UTC, dagli eventi JSON `Current-price persist: commit OK`.
>
> | misura | atteso | osservato |
> |---|---|---|
> | un montaggio di `/assets` (click su `nav-assets` dalla Dashboard) | 1 subito, poi 1 ogni 30 s | 15:49:07.64 al montaggio · poi 15:49:37.64 · 15:50:07.64 · 15:50:37.87: **uno ogni 30,00 s**, nessuna raffica |
> | «Ricarica Tutto», un click | +1 | **+1** fuori fase (15:50:52.02). Il tick dopo cade a 15:51:07.64, **in fase col montaggio** → l'effetto **non** è ripartito: se fosse ripartito, `clearInterval` e un intervallo nuovo in fase col click |
> | tab Correlazione aperto, fermo per 65 s | solo i tick | 3 `prices/current`, **0** `risk/query` → l'invalidazione a ogni tick non fa ri-chiedere le sezioni: niente sfarfallio |
> | sync del guscio → «Annulla» | nessuna ricarica | **0** richieste in 14 s, in una finestra senza tick |
>
> **Controllo positivo del conteggio**: in ogni fetta del log, le righe d'accesso `POST /api/v1/assets/prices/current` e
> gli eventi JSON di commit danno **lo stesso numero**. Lo stesso `grep` trova `POST /api/v1/risk/query` nella fetta del
> replay, quindi lo zero della fetta «Annulla» non dipende dal pattern.
> Il conteggio di **prima** della riparazione (fino a 4 per refresh) resta **per lettura** del codice, non misurato per uso.
>
> **⚠️ Fuori pista**
> - Primo login → `422`: al click i campi risultavano vuoti, perché il testo digitato non era ancora arrivato al
>   binding. Ripetuto dopo aver verificato la lunghezza dei campi → `200`.
> - Nel browser del canvas una **navigazione completa** (URL digitato) perde la sessione (`/auth/me` → 401; il cookie è
>   httpOnly `lax`). La navigazione in-app invece la conserva. **Non indagato**: è fuori perimetro e il developer usa il
>   suo browser.
> - La misura ha **scritto** sulla copia: prezzi di oggi a ogni polling, più lo scheduler. Copia rinfrescata per la
>   review alle 18:00:34; la vecchia è in `.prev-20260923-180034`.
> - Leggendo le pagine ho visto i valori del developer (dashboard, prezzi, rendimenti). **Non li trascrivo** qui: questo
>   file è versionato. Nelle righe sotto uso solo id, conteggi e percentuali di copertura.

## F-3 — preparazione della review, 2026-09-23 18:00

> **Coordinate del server di review** (`files/review_coordinates.sh 6164 files/F3_server_review.log`):
> `http://localhost:6164/assets?tab=correlation` · HEAD `f1047f766` · albero **non committato**: 26 modificati + 6 nuovi,
> quelli del lotto, nessun altro · listener con `cwd` = questo worktree · `db_path` = la copia · versione
> `v1.1.0-228-gf1047f766-dirty` · bundle: nessun sorgente più nuovo di `index.html`, costruito = servito
> (`f7952064bf75a441`), 6 chunk contengono `risk-sync-button` · `generated.ts a085da1c8dac55f9` (= baseline).
> `openapi.json 0157533aebfa4a69` ≠ il `445629cf…` del mattino **perché** incorpora `info.version`, che ora porta
> `-dirty`. Verificato leggendo il campo: i tipi (`generated.ts`) non sono cambiati.
>
> **Verificato per uso sul server di misura** (stessa build; ~~stessa copia prima dei polling~~: **falso**, corretto il 24/09.
> La copia aveva già le scritture dello scheduler del primo server, delle 15:37Z; vedi le 575 osservazioni qui sotto):
> - `data-selection-source` = `mine` al primo accesso: tutti i 15 asset dell'utente, di cui **4 senza prezzi** (crowdfunding),
>   esclusi con avviso. Il pannello scrive subito la selezione sotto `lf_1_…`; al ritorno, e con `[1,3,8]` scritto
>   nella chiave, il valore è `persisted` e i chip sono esattamente 1, 3, 8 ✅. Chiave di prova rimossa dal browser del canvas.
> - **Nessun `€` e nessun `•••`** nel pannello (`asset-global-risk-panel`). «EUR» compare solo come etichetta del filtro
>   valuta (`risk-filter-currency-EUR`) e dentro i nomi di alcuni asset.
> - **Privacy ON**: l'`innerText` del pannello è **identico byte per byte** (3174 caratteri, FNV `3565dd0a` prima e dopo).
>   Nessun `•••` in tutta la pagina del tab. Replay aperto ed eseguito con privacy ON: solo percentuali, nessun
>   `•••` né `€`.
> - I tre fatti del coordinatore (justETF scrive nel weekend, la griglia è l'unione), **riprodotti nel laboratorio**:
>   - con `[1,3,8]` sul 3M: *Correlazione: Parziale* con il solo motivo *carried-forward*. *Dettagli calcolo*:
>     Osservazioni 93, Copertura 100.0%, fattore 365.00. Il fattore 365 dice che i weekend sono dentro;
>   - con `[1,3,8]` dal 2024-01-01: Osservazioni **575**, Copertura **57.7%**, nessun avviso di copertura. Le celle,
>     nel tooltip, riportano la loro copertura, che il coordinatore misura a 1,0.
>     Sulla snapshot il coordinatore misura 574/995. ~~**Non verificato**: la mia ipotesi è che l'osservazione in più
>     sia la riga di oggi, scritta dal polling durante la mia misura.~~
>     ✅ **Fatto (24/09)**: 575 = 574 + la riga del **2026-09-23** degli asset 1, 3 e 8, e 575/996 = 0,577. La riga non
>     esiste nella snapshot, dove la data massima è il 09-22. L'ha verificato il coordinatore sulla copia
>     `.prev-20260923-180034`; io l'ho riverificato con una lettura `immutable=1` (nessun file laterale creato) e coi
>     log dei due server.
>     🔴 **Ma la riga non l'ha scritta il polling: l'ha creata lo scheduler.**
>     - Primo server, current-price refresh alle 15:37:41Z: *«processing 11 fresh provider quote(s) for 2026-09-23
>       (existing rows today: 0)»*, poi `[F.2 bootstrap] asset=1/3/8 date=2026-09-23`. Lo `history sync` delle
>       15:37:42Z ha anche riscritto le righe del 09-22.
>     - Server di misura, avviato alle 15:44:59Z: al primo refresh del suo scheduler (15:48:08Z) la riga c'era già,
>       *«existing rows today: 11»*, prima di qualunque richiesta del browser.
>     - Le `POST /prices/current` del browser, dalle 15:49:07Z, l'hanno solo **ritoccata** (`[Intra-day price extend]`,
>       `patch_fields=['close']`).
>     - Il `fetched_at` della riga, 15:59:58Z, indica il browser: è una `POST /prices/current`, e la riga d'accesso segue
>       il commit. Ma la colonna registra l'**ultima** scrittura, non la prima: `F.2 bootstrap` e `F.3 intra-day extend`
>       la timbrano entrambi (`asset_sources/price_query.py`). Risponde a un'altra domanda, *«è cambiato qualcosa?»*:
>       serve all'impronta `COUNT + MAX(fetched_at)` della cache (`_compute_price_fingerprint`, `portfolio_engine.py`).
>       Chi ha creato la riga non lo dice.
>
>     La mia ipotesi aveva **la riga giusta e l'autore sbagliato**. La verifica ha confermato la riga e non l'autore, e
>     ripetendolo lo ha reso più credibile. È la forma di 09 §3.8: *«una correzione aumenta la credibilità di ciò che
>     non corregge»*.
>     📌 **Sul server di review è già successo.** Alle 07:30:47Z del 24/09, 5 s dopo l'avvio, lo scheduler ha creato la
>     riga del **2026-09-24** (`existing rows today: 0`, poi `F.2 bootstrap` per 1, 3 e 8), con **0** richieste
>     `prices/current` e **0** login. Le cifre che vedrà il developer quindi **non** saranno 575 / 57,7%. Non le ho rimisurate.
>   - La contraddizione fra le due coperture compare **solo dietro un'interazione**: il `<details>` *Dettagli calcolo*,
>     chiuso di default, e il tooltip della cella, al passaggio del mouse.
> - Visibile ma **non mio**:
>   - `durata {{days}} g` in ogni riga della sezione perdite. È R1, di A (`AssetSetLossComparisonSection.svelte` e
>     `lastedDays` in `it/en.json:3094`), ancora presente a questo HEAD.
>   - I motivi di `partial` restano in **inglese** nella UI italiana. È una scelta dichiarata di Risk (`levelHelpers.ts`,
>     `resultReasons`: *«Verbatim, or nothing»*).
>   - La frase d'audit del replay dice *«della fetta»* in un ambito senza pesi. La chiave è di Risk
>     (`risk.levels.l4.replayAudit`); la valutazione è congiunta con F (08 §8.4).
> - **Proposta, non attuata** (D11): il polling live continua sul tab Correlazione. Lì non mostra alcun prezzo live, ma
>   produce una scrittura e un'invalidazione globale ogni 30 s, cioè il meccanismo che scarta le risposte in volo
>   (triage C12/C15). Limitarlo al tab che mostra i prezzi è una riga nell'effetto di F-2d. La decisione spetta al developer.

## ⚠️ Fuori pista — l'«interruzione di corrente» della notte 23→24/09: la macchina **non** si è riavviata

> **Il presupposto e la misura.** Alla ripresa (24/09 09:26) il developer ha scritto *«era andata via la corrente e
> internet»*. La lettura naturale era un riavvio, con `/tmp` svuotato, server morto e snapshot persa. **Misurato**:
> `uptime` 1 giorno e 2:13, `kern.boottime` = 23/09 07:15, cioè il riavvio di ieri mattina. È caduta solo la connessione.
> `/tmp` era intatto, snapshot compresa, e **il server di review era ancora acceso**.
>
> **Cosa ha fatto il server in 15,5 ore** (18:00 → 09:29, log `files/F3_server_review.log`):
> - 0 login → il developer non l'ha usato; 0 errori, 0 traceback;
> - lo scheduler ha scritto nella copia come in prod: 23 refresh dei prezzi correnti e 3 sync dello storico;
> - **una sola** richiesta da browser: l'ultimo polling della scheda del canvas (16:00:57Z), con il token del server di
>   misura → **`401`** (*«JWT token invalid»*) → nessuna scrittura. Poi la scheda è rimasta sul login: 1 `/auth/me` in
>   15 ore, nessun polling. Controllo positivo del conteggio: le 3 `GET /` attese (prontezza, coordinate) ci sono tutte.
>
> **L'albero è quello verificato, per identità degli ingressi**: gli hash di pannello (`cc34324c…`), pagina (`0f19cffc…`),
> spec (`728afdea…`), heatmap (`c3dd866e…`) e client (`a085da1c…`) coincidono con quelli annotati prima delle corse delle
> 17:33 e 17:42. Dopo le 17:44 sono cambiati solo questo piano e `vendor/.cache_manifest.json`: toccato alle 18:00:45,
> **due secondi dopo** l'avvio del server (build d'avvio), e ignorato da `.gitignore:78`. I diff della documentazione sono
> quelli dichiarati (`+10/−8`, `+1/−1`). **I cancelli non si rigirano ora**: gli ingressi sono identici. Si rigirano tutti a F-7.
>
> **Rinfresco prima della review, per regola**: il server è stato spento, e questa volta lo `stop_bash` ha terminato anche
> il figlio `uvicorn` (ieri no). Copia rinfrescata dalla snapshot (23/09 10:52; `004`, marcatore assente) alle 09:30;
> quella della notte è in `.prev-20260924-093025`. **Server rialzato alle 09:30:42**, coordinate ricontrollate:
> `index.html` servito = costruito = `f7952064bf75a441`, **identico** a quello del server su cui F-2d è stato misurato per
> uso → i chunk hanno nomi derivati dal contenuto, quindi il developer guarda la build di cui ho misurato il comportamento.
> `openapi.json` è passato da `445629cf…` a `0157533a…` perché incorpora `info.version`, che ora porta `-dirty`
> (verificato leggendo il campo): i tipi non sono cambiati.
>
> **⚠️ Fuori pista minore**: il mio primo `kill $pid` in un ciclo è stato rifiutato dall'harness, che vuole un PID
> letterale. Nessun processo era sopravvissuto: verificato PID per PID.

## Le 575 osservazioni: riga confermata, autore corretto — 2026-09-24, 09:32–09:40

> Il coordinatore ha confermato la mia ipotesi sulla copia `.prev-20260923-180034`: c'è una riga del 2026-09-23 per
> gli asset 1, 3 e 8. **La riga è quella giusta, l'autore no**: non l'ha scritta il polling, l'ha creata lo scheduler.
> Il dettaglio e l'evidenza (log dei due server, `fetched_at` = ultima scrittura) sono in **F-3**, dove stava
> l'ipotesi. Corretta in F-2d anche la frase «stessa copia prima dei polling»: era falsa.
>
> **⚠️ Fuori pista**: nella prima stesura di questa correzione avevo citato due identificativi, `R2-115` e `R2-127`,
> come fonti di due affermazioni. **Non esistono**: un `grep` su `09_feedbackJobs/` li trova solo nelle righe che avevo
> appena scritto. Li ho tolti e sostituiti con i riferimenti al codice. Due affermazioni ho dovuto riscriverle:
> un «fermato dopo tre minuti» che il log non prova, e una previsione sul server di review, che ora è una misura.
> È la stessa forma della correzione che stavo scrivendo: **un rimando dà autorità a una frase anche quando non porta da
> nessuna parte**. Nessun altro file toccato: fra prima e dopo l'albero resta 26 modificati + 6 nuovi.

## F-2e — `data-quality.en.md` contro il codice (voce del coordinatore, 2026-09-24 10:07)

> **Origine**: il coordinatore mi assegna la pagina per questo round. Lo specialista doc di A ha segnalato due righe,
> e il coordinatore aggiunge un fatto nuovo:
> - **`:60`**: dice *«the intersection discarded»*, ma il calendario è l'unione delle quotazioni fresche, e una data resta
>   solo dove ogni asset può essere valutato;
> - **`:52`**: è il mio reperto del 23/09, che allora avevo riportato senza toccarlo. Un inizio tardivo dà `ok` con
>   `short_history`, non `partial`;
> - **fatto nuovo**: `partial` può scattare per la sola baseline, perché `series_preparation.py:311-313` la conta fra i
>   punti riportati. Il comportamento è di Risk (tempo ②), ma la pagina non deve promettere il contrario.
>
> **Verificato nel codice, prima di scrivere** (tutto in `backend/app/services/series_preparation.py`, salvo dove indicato):
>
> | affermazione | dove | esito |
> |---|---|---|
> | le date candidate sono l'unione delle quotazioni fresche nella finestra | `candidate_quote_dates`, `_price_is_fresh` | ✅ |
> | l'intersezione esiste, ma è quella delle date in cui ogni asset è **valutabile** (punti riportati compresi), non quella delle date quotate | `complete_dates`, con `intersection_update(item.target_points)` | ✅ |
> | un buco dentro una storia non costa date: va avanti senza limite di età | già misurato il 23/09 sul vero servizio (buco di 20 giorni ⇒ 90 osservazioni, 20 punti riempiti) e scritto nel riquadro di `correlation.en.md` | ✅ |
> | inizio tardivo ⇒ `baseline_inside_requested_range` + `short_history:<id>`, che finiscono **solo** in `warnings` | ramo `if not prior_baselines` | ✅ |
> | …e `data_quality_status` non legge i `warnings` | `DataQualityReport.data_quality_status` (`schemas/portfolio.py`) | ✅ ⇒ `ok` |
> | …e nessun `RiskWarning` degradante nasce da `short_history` | `grep short_history backend/app` ⇒ solo `series_preparation.py`; `_success` (`risk/service.py`) dà `partial` solo per avvisi degradanti, esclusioni o stato ≠ `ok` | ✅ ⇒ risultato `ok` |
> | le date prima di un inizio tardivo non sono elencate come incomplete | `return_candidates` richiede `> baseline_date` | ✅ |
> | i test lo fissano | `test_short_history_uses_effective_baseline_without_marking_partial` asserisce `DataQualityStatus.OK` | ✅ |
> | una data persa **dopo** la partenza è elencata e dà `partial` | `incomplete_valuation_dates`; `test_missing_fx_date_is_excluded_without_filling_returns` | ✅ |
> | la baseline è contata fra i riportati | ciclo `for index, point in enumerate(valuation_points)`: conta anche `index 0` | ✅ ⇒ `CARRIED_FORWARD` ⇒ `data_quality_degraded` ⇒ `PARTIAL` |
> | la quota di freschezza invece la esclude | `if index > 0 and not point.is_price_carried_forward`, divisa per asset × osservazioni | ✅ ⇒ 100% fresco **e** `partial` è possibile |
> | la baseline è il giorno prima dell'inizio | `_prepare_asset_series` carica da `start − 1 day` (`risk/service.py`) | ✅ **dedotto** dal codice: riportata ogni volta che quel giorno non è quotato per qualche asset, per esempio un weekend o un festivo prima dell'inizio |
>
> **Le promesse contrarie nella pagina sono sei, non tre**:
> - tabella degli stati, riga `partial`: *«dates on which not every holding could be valued»* include le date prima di un inizio tardivo;
> - §Alignment, punto 2 e paragrafo delle conseguenze (`:49`, `:52`);
> - §Coverage, prima misura (`:60`, *«intersection»*);
> - §Coverage, seconda misura: *«numeric counterpart of the `carried_forward` status»*;
> - §Interpretation, riga `partial` (*«on less than what was asked»*) e riquadro (*«over a shorter window, or over fewer holdings»*).
>
> Una `partial` dovuta alla sola baseline smentisce le ultime due, e un inizio tardivo smentisce le prime due.
>
> **Decisioni**:
> - **Baseline: formulazione neutra.** Non documento il conteggio: è un difetto di Risk in riparazione. Ma non prometto
>   il contrario. Ogni frase deve restare vera oggi **e** dopo la riparazione di Risk: stessa regola usata per
>   `min_coverage`. Esempio: *«100% fresco non esclude `carried_forward`»* resta vera anche dopo, per via dei cambi
>   riportati, che la quota non conta.
> - **Nessuna traduzione esiste**: `git ls-files` trova solo `.en.md`. Quindi niente `translate-stamp` e nessun debito
>   da `translate-validate`.
> - **Titoli e ancore invariati**: `#exclusions` è linkata da `correlation.en.md`.
> - **Sito servito**: `dev.py mkdocs build` riscrive `mkdocs_src/site/`, che il server di review su `6164` serve dal
>   disco (`main.py`, `SITE_DIR`). Il server gira **senza `--reload`** (riga di comando del PID 11035), quindi la modifica
>   del `.md` non lo riavvia. Alle 10:12: 0 login, 0 richieste `/mkdocs`. Il build si fa ora, e il developer troverà
>   la documentazione allineata all'albero. Il bundle del frontend non va toccato: `index.html` va ricontrollato dopo.
>
> **Finito quando**:
> - le sei frasi sono riscritte, solo in inglese, con titoli e ancore invariati e coerenti col riquadro di `correlation.en.md`;
> - `dev.py mkdocs build` esce 0 con zero WARNING, e `check-links` esce 0, col conteggio registrato prima e dopo;
> - il delta resta 26 M + 6 nuovi e `git diff --check` è pulito;
> - `index.html` servito è ancora `f7952064bf75a441`, il PID 11035 è su `6164` e `6154` è libera.

### F-2e — esecuzione ✅ 2026-09-24, 10:15–10:40

> **Note implementazione**: `data-quality.en.md` passa da +1/−1 a **+16/−16** cumulativo contro l'HEAD. Oggi 16 righe,
> fra cui la 107, già modificata il 23/09.
> Titoli e ancore sono identici all'HEAD, numeri di riga compresi (`diff` dei `^#` e dei `{: #`). Le righe vuote
> dopo i `!!!` sono intatte. Ogni affermazione sulla baseline è neutra.
> - **Primo passaggio di `docs-writer`: le sei promesse contrarie.**
>   - Tabella degli stati, riga `partial`: *«dates inside the analysed window»*.
>   - §Alignment 1–3: l'unione dei calendari; *valued* comprende il riportato senza limite di età; l'elenco degli
>     incompleti comincia solo dopo la baseline; la partenza tardiva è sulla prima data valutabile da tutti.
>   - Conseguenze: la finestra la accorcia **chi parte tardi**, non un buco. Un inizio tardivo da solo non dà
>     `partial`: i nomi finiscono nelle voci `short_history`, e la perdita si vede nel conteggio e nella copertura.
>     Solo una data persa dopo la partenza è elencata e dà `partial`.
>   - §Coverage: al posto di *«intersection»*, «un inizio tardivo o una conversione irrisolta, non i buchi»; al posto di
>     *«numeric counterpart»*, «100% non esclude `carried_forward`».
>   - §Interpretation, riga `partial` e riquadro: comprendono il riportato, «same window, same holdings».
> - **Secondo passaggio**: cinque contraddizioni trovate dallo specialista, **verificate da me nel codice prima di
>   commissionarle**.
>   - Il riquadro della copertura diceva che una copertura bassa è *«the shape of a market that is closed»*. È falso: un
>     giorno senza quotazioni non è candidato, e un asset chiuso viene riportato. Nel test del calendario congiunto il
>     2026-01-06 non è una data di rendimento.
>   - *«period return of exactly zero»*: vale solo nella valuta dello strumento. Stesso test: prezzo riportato con un
>     cambio che si muove ⇒ `91/90 − 1 ≠ 0`.
>   - Riga `ok`: *«complete source data»*, ma anche i dati `carried_forward` sono «complete».
>   - *«Nothing … declares … an observation count»*: smentito da `service.py:231` (`INSUFFICIENT_HISTORY`) e dal
>     paragrafo stesso della pagina.
>   - *«always ask which holding»*: `incomplete_valuation_dates` è un elenco di sole date.
> - **Due modifiche mie, dirette, perché legate a quelle appena scritte** (una parola ciascuna):
>   - *«Correlation is **the** exception»* → *«an exception»*: anche lo `stress` ipotetico salta il cancello
>     (`_available_observations` restituisce `None`). ⚠️ La frase era del **mio** passaggio del 23/09, che aveva
>     conservato l'articolo della versione precedente.
>   - Il titolo del riquadro *«No threshold is defined»* contraddiceva il suo corpo nuovo, che esenta le soglie di
>     osservazioni → *«No quality threshold discards a figure»*. Resta vero anche con `min_coverage`, che avverte senza scartare.
>
> **Evidenza** (i miei comandi finali, uno per volta, sull'albero finale):
> ```
> dev.py mkdocs build        10:39:56 · exit 0 · 0 WARNING · 0 ERROR       files/F2e_mkdocs_build3.log (cartella di sessione)
> dev.py mkdocs check-links  10:40:04 · exit 0 · 80 valid · 3 known-broken     (prima: 80 · 3, files/F2e_checklinks_before.log)   files/F2e_checklinks3.log
> /mkdocs/…/data-quality/ servita da 6164: HTTP 200 · 3 frasi nuove presenti (1/1/1) · 3 vecchie assenti (0/0/0)
> index.html servito = costruito = f7952064bf75a441 (invariato) · PID 11035 su 6164 · 0 login · 6154 libera
> albero: 26 M + 6 nuovi, gli stessi percorsi elencati uno per uno · git diff --check pulito
> ```
>
> **⚠️ Fuori pista**
> - Il coordinatore chiedeva **tre** correzioni. Nella pagina ne sono servite **tredici**, e ne restano sette riportate.
>   La pagina era stata «riportata, non toccata» il 23/09. Il debito si è accumulato proprio perché non aveva un
>   proprietario.
> - `write_agent` rifiuta gli agenti lanciati in modalità sincrona. Per il secondo passaggio ho aperto un compito nuovo
>   col contesto intero.
> - Il sito `/mkdocs` servito dal server di review è stato **ricostruito tre volte** (10:24:58, 10:36:54, 10:39:56; la
>   pagina servita ha mtime 10:39:33). Il server era inattivo (0 login); il bundle del laboratorio non è stato toccato.
>
> **Residui, riportati e non corretti** (non verificati, o fuori dal punto):
> 1. Riga *«Incomplete dates»* del rapporto: per le valutazioni esclude le date prima di una partenza tardiva. Per NAV,
>    valore di carico e allocazione non l'ho verificato.
> 2. *«An excluded asset … forces the result out of the clean state»*: `_success` scarta esclusioni e `assets_excluded`
>    sui piani ipotetici. Non ho verificato se su quel percorso esistano esclusioni.
> 3. *«A coverage of 80% … a fifth of the prices are missing»* è impreciso: i prezzi sono riportati, non mancano, oppure
>    sono date candidate perse.
> 4. *«`ok` says the series was complete»*: vero, ma più debole della definizione.
> 5. *«Each entry names the object it concerns»*: gli avvisi liberi, come `baseline_inside_requested_range`, non nominano nulla.
> 6. `min_coverage`, correlazione, 0,6: avviso degradante che in pratica non può scattare. È **già riportato** il 23/09 come difetto del backend.
> 7. Caso limite: se un inizio tardivo lascia **zero** osservazioni, tutti gli asset sono esclusi e l'esito non è `ok`.
>    È coerente con il «da solo» della pagina.
>
> **Per Risk (tempo ②), un dettaglio che conta per la priorità**: la baseline è sempre `start − 1 day`
> (`_prepare_asset_series`). Quindi una `partial` dovuta alla sola baseline è il caso **comune**, non un caso limite.
> Basta un asset non quotato il giorno prima dell'inizio: gli inizi di domenica e di lunedì per un titolo quotato solo
> nei feriali, più i festivi.
>
> **Voce CHANGELOG proposta per F-7** (`### 🐛 Fixed`): *«Data Quality theory page realigned with the engine: a late
> start shortens the window without marking the result partial, gaps are carried forward instead of costing dates,
> and a fully fresh sample does not rule out a carried-forward status.»*

## Node 26 e lo storage di default: i test della chiave per-utente provano qualcosa? — 2026-09-24, 10:45–11:00

> **Origine**: una misura di I, girata dal coordinatore. Sotto Node 26, senza `--localstorage-file`,
> `globalThis.localStorage` è `undefined`. Chi lo intercetta restituisce il default, e un test di persistenza può
> essere verde senza provare niente. Il precedente da seguire è lo stub con `vi.stubGlobal` di `ExposureTable.test.ts`.
>
> **Misurato qui**:
> - `node v26.8.2`: `typeof localStorage` = `undefined`, ma `'localStorage' in globalThis` = `true`, con
>   *«ExperimentalWarning: localStorage is not available because --localstorage-file was not provided»*. Col flag
>   diventa un oggetto vero.
> - Il meccanismo del messaggio (`getUserStorage`) **non** è quello del mio modulo, ma il rischio lo raggiunge per
>   un'altra strada. `readPersistedSelection` e `writePersistedSelection` ricevono storage e utente come parametri.
>   Il default dello storage è `safeStorage()`, che dà `null` se `typeof localStorage === 'undefined'`. Il default
>   dell'utente è quello di sessione.
> - `assetSetSelection.test.ts` gira in `@vitest-environment node`: vede il `globalThis` di Node.
>
> **Verdetto**:
> - **TL-A (7 casi) e «the session default» provano davvero.** Iniettano uno storage `Map` (`fakeStorage()`) e
>   asseriscono sul suo contenuto (`entries`, `keyUsed()`), con un controllo positivo prima di ogni assenza. Con uno
>   storage inerte non potrebbero essere verdi. La mutazione del 23/09, sullo stesso Node, ha dato 5 rossi
>   (`storageKey` → chiave nuda). Il sorgente ha ancora lo SHA `9efb66cc…`.
> - **Tre righe raggiungono il default dell'ambiente e sono verdi per ambiente**:
>   - `:172` `readPersistedSelection(undefined, USER_A)` → `null`, e `:225` `writePersistedSelection([1, 2], undefined,
>     USER_A)` → nessuna eccezione. Doppiano i fratelli `null` di `:171` e `:224`, che provano il ramo per costruzione.
>     Restano verdi anche con uno storage vero, quindi non possono andare rosse.
>   - `:490` *«…even when it reads storage itself»*: senza utente di sessione `storageKey(null)` è `null`, e nessuna
>     selezione viene mai letta, in nessun ambiente. Il titolo promette una lettura che non avviene. L'intersezione col
>     catalogo è provata altrove, a `:382`, con un elenco iniettato.
> - 🔴 **Perdita misurata**: con uno storage vero, il file resta verde (70/70) e ci lascia
>   `lf_7_assetGlobal.riskSelection.v1 = [1,2]`: è `:225`. La promessa dell'intestazione, *«never touch a global
>   `localStorage`, so no case can leave state behind»*, è vera **solo per ambiente**.
> - **Il seam vero non ha test unitari sotto Node 26**: nessuno esercita `safeStorage()` quando restituisce il
>   `localStorage` della pagina. Lo copre l'E2E in Chromium: in `risk-lab`, la prima visita dà
>   `data-selection-source=mine` (`:1796`), e la seconda riparte da `localStorage` (`:2420`–`:2432`).
>
> **Comandi**:
> ```
> cd frontend && npx vitest run src/lib/components/risk/assetSetSelection.test.ts
>   → Test Files 1 passed (1) · 70 test · ExperimentalWarning presente: il default è stato raggiunto e trovato vuoto
> cd frontend && NODE_OPTIONS=--localstorage-file=/tmp/libreFolio_lsprobe_vitest.db npx vitest run <stesso path>
>   → Test Files 1 passed (1) · 70 test · nello storage 1 chiave: lf_7_assetGlobal.riskSelection.v1 = [1,2]
> file di prova rimossi (db, -shm, -wal) · log in files/F2_node26_vitest_{plain,realstorage}.log
> ```
>
> **Test list TL-S proposta al developer.** La scrive `test-author` solo dopo l'approvazione, dentro F-6. Non è
> urgente: il prodotto non è toccato, e il seam è coperto dall'E2E.
> - **TL-S1 — pagina senza storage ⇒ nessuna memoria, nessuna eccezione.** `vi.stubGlobal('localStorage', undefined)`
>   al posto dell'`undefined` d'ambiente di `:172` e `:225`. Nello stesso caso, un controllo positivo: con uno storage
>   stubbato la stessa chiamata persiste.
> - **TL-S2 — il default è il `localStorage` della pagina.** Una `Map` stubbata come globale, più un utente di
>   sessione: la scrittura senza argomento storage atterra nello stub sotto la chiave di sessione, e la lettura senza
>   argomenti la rilegge. È la prima copertura unitaria di `safeStorage()`.
> - **TL-S3 — `:490` legge davvero una memoria.** Lo stub contiene, per l'utente di sessione, un id del catalogo e
>   uno fuori: torna solo il primo, con `source: 'persisted'`.
> - **Per tutti**: `vi.unstubAllGlobals()` e `transitionClientSession(null)` in `afterEach`, come nel precedente;
>   poi l'intestazione del file va corretta.
>
> **⚠️ Fuori pista**: nessuno. Nessun file del repository è stato toccato; albero 26 M + 6 nuovi, invariato.

## J ③a pronto nel checkpoint C1 di J — cosa chiude per C1b (2026-09-24, 10:45)

> Con la privacy attiva, `formatCurrencyAmount` restituisce `$•••` (per `'1234.5'`, USD), `-$•••` (per `-1234.5`,
> USD) ed `€•••` (per EUR). Un valore assente resta `—`. Il commit è del developer, e C1 **non è ancora nel target**.
> - **La condizione di C1b è sciolta.** La test list diceva *«+ `'€'` se J conserva la valuta»*: J la conserva. Un
>   importo trapelato si vedrebbe quindi come simbolo + `•••`. C1b asserisce `not.toContain('•••')`, che prende un
>   importo mascherato in qualunque valuta, e `not.toContain('€')`, sull'**output reso** e non su `SAFE_CALL`
>   (09 §3.12), con le barriere di presenza prima.
> - **L'assenza resta `—` anche con la privacy attiva**, quindi un «niente denaro» è identico ON e OFF. È coerente con
>   la misura di F-3: con la privacy ON l'`innerText` del pannello è identico byte per byte.
> - **Resta bloccato**: C1b parte in F-6, quando C1 è nel target.

## D12 — divisione del lavoro di test, decisa dal developer (2026-09-24, 10:57)

> *«mi rifai la test list in italiano? e non mettere test tecnici come quello di sostituire la memoria locale, a meno
> che non sia strettamente necessario, io voglio fare i test estetici e funzionali per rendermi conto se il sistema
> risponde bene, poi i casi limite e le rifiniture tecniche le lascio a te»*
>
> - **Al developer**: la lista di F-3, in italiano. Contiene solo controlli estetici e funzionali, da fare a mano sul
>   server di review (`6164`), più le tre decisioni che spettano a lui: polarità dei colori, D11, frase d'audit del replay.
> - **A F**: TL-S (seam dello storage), TL-P (polling di F-2d), i casi limite e le rifiniture tecniche. Le test list
>   tecniche restano scritte nel piano, per trasparenza, ma **non** vanno più al developer per approvazione; le scrive
>   `test-author` dentro F-6, come già pianificato.
> - **Verificato prima di scrivere la lista**, per non promettere al developer ciò che la pagina non fa:
>   - le etichette italiane reali, da `it.json`;
>   - il pulsante di sync è `common.sync` («Sincronizza»);
>   - l'errore del preset broker è `risk.states.loadFailed`;
>   - la frase d'audit del replay dipende dal trattamento: `replayAuditOmitted` se un asset è omesso, altrimenti
>     `replayAudit`, che parla di «fetta»;
>   - nel laboratorio non c'è nessun `DocsLink`;
>   - il tooltip dell'occhio è `'Show amounts'` / `'Hide amounts'`, in inglese nel codice di `PrivacyToggle.svelte`: di J.

## F-3 — esito della review del developer (2026-09-24, 11:15) → F-3b, riprogettazione a quattro mani

> **Verdetto**: il blocco di selezione **funziona**: aggiungendo e togliendo asset la matrice si ricalcola.
> **L'estetica no**: *«componenti con altezze e dimensioni fatti male, poche icone e poca chiarezza»*.
> **Decisione del developer**: finita la review a lista, ogni componente si ripensa insieme, **a quattro mani**:
> F fa e chiede. Niente test automatici, salvo quelli matematici o di basso livello, e un controllo funzionale
> minimo. F-6 (`risk-lab`) resta la chiusura, quando il comportamento è fissato.
>
> | # | osservazione del developer | verificato nel codice | di chi |
> |---|---|---|---|
> | V1 | il «Sincronizza» del guscio ha poco senso sotto «Sinc. Tutto» della barra; sul tab dovrebbe valere per la selezione | la barra (`PageToolbar` in `assets/+page.svelte`) è la stessa per i due tab. Su Correlazione sincronizza **tutti** gli asset della pagina, solo i prezzi (`AssetSyncModal`). Il pulsante del guscio sincronizza la **selezione**, prezzi e cambi (`PageSyncModal`, R2-128) | F (pagina e guscio) |
> | V2 | le azioni rapide vanno bene, ma disposte meglio | — | F |
> | V3 | precarica per broker, tipo e valuta: ripensare e avvicinare. Alla fine un **«+»** che apre una lista di asset **con filtri**, non una select fissa | «Aggiungi asset alla matrice» è `AssetSelect`: una select singola con ricerca. Non esiste un selettore multiplo di asset con filtri (`AssetPickerModal` è per le immagini), quindi serve un componente nuovo. Il filtro per tipo andrà sulla select di K | F (+ K per i tipi) |
> | V4 | «Correlazione: Parziale» e la frase che segue non sono chiari | li disegna `RiskLevelSection`, di Risk: lo stato del risultato e il messaggio del backend **alla lettera** (`data_quality_degraded`; *«Verbatim, or nothing»* in `levelHelpers.resultReasons`). La causa, sui dati del developer, sono i punti riportati: weekend, festivi e la baseline (F-2e). Quindi comparirà **quasi sempre** | Risk |
> | V5 | nomi troncati, fuori posto, coperti dalla matrice; la matrice non segue la finestra; meglio un pan che uscire dallo schermo | (a) l'unica etichetta **senza emoji** (`Btp Piu' Sc Fb33…`: il 🇮🇹 finale lo taglia il troncamento a 18 caratteri) è al posto giusto su **entrambi** gli assi. Tutte quelle che iniziano con un'emoji finiscono dentro il disegno: ECharts misura male la larghezza delle emoji nel canvas, e i nomi sono dati dell'utente. (b) Il canvas è largo 861 px in una card di 729 px (dall'HTML ispezionato). La causa esatta è ancora da misurare | F (unico scrittore); la montano anche `L2Diversification` (Risk, Dashboard) e il legacy |
> | V6 | l'ordine «Per nome» deve ignorare le emoji | confermato: oggi raggruppa per emoji iniziale, e «Btp» finisce ultimo | F · ✅ sotto |
> | V7 | nel titolo, a destra, l'icona del manuale: tooltip che spiega la card, descrizione più ampia, click verso una pagina di documentazione. Uguale in Dashboard e ovunque ci sia correlazione | `DocsLink` esiste (icona libro, tooltip `label`). Il titolo lo disegna `RiskLevelSection` (Risk), che non ha un posto per l'icona. La pagina di teoria `financial-theory/technical-analysis/risk-metrics/correlation/` esiste (solo EN, registro rigoroso); **nessuna pagina utente** (quella di Asset Global la scrive A, D7). La Dashboard (`L2Diversification`) non ha l'icona. La descrizione è `risk.analytics.correlation.description`, chiave del catalogo del backend (`description_i18n_key`): cambiarla la cambia ovunque | Risk (titolo, Dashboard) · A (pagina utente) · F (testo) |
> | V8 | «I più simili» / «Quelli che si compensano»: *«assolutamente incomprensibile, dammi dei suggerimenti»* | le liste promettono più di quanto le soglie garantiscano (`topPairs`). «Simili» = qualunque ρ > 0: top 5, dentro anche 0,55, che è «moderato». «Si compensano» = qualunque ρ < 0: dentro anche −0,01, che è indipendenza e non compensazione. Il blu scatta solo sopra 0,7. I nomi stanno su una riga troncata con «↔». Non c'è scala, né legame con la matrice | F |
>
> **Non è un difetto** (verificato): il contatore diceva «15 selezionati su 15» mentre la matrice aveva 7 asset. Gli
> elementi ispezionati vengono da momenti diversi: con asset esclusi, fra i motivi comparirebbe il messaggio di
> `assets_excluded` (`resultReasons` li mostra tutti), e non c'era.
>
> **Metodo F-3b**, per ogni componente:
> 1. diagnosi, 2–3 strade e una raccomandazione;
> 2. il developer sceglie;
> 3. F implementa e ricostruisce il bundle, e il developer guarda su `6164`;
> 4. si itera, e il piano registra.
>
> I test sono solo sugli helper puri, in un lotto per `test-author` (TL-R, D12); niente E2E fino a F-6.
> **Ordine proposto**:
> 1. matrice (con V6 ✅);
> 2. zona delle coppie (insieme a F-4, ρ̄);
> 3. intestazione della sezione (V4, V7: serve Risk);
> 4. guscio di selezione (V2, V3);
> 5. sync unico (V1, D11);
> 6. le sezioni non ancora viste: i confronti di A, il replay.
>
> **Conflitti nuovi**:
> - **Risk**:
>   - la heatmap cambia anche in Dashboard;
>   - 🔴 `risk-analysis.spec.ts:1347` asserisce un **canvas** nella heatmap (`expectChartCanvas`): una matrice in
>     HTML richiede una riga nello spec di Risk;
>   - `RiskLevelSection` (icona nel titolo; stato e motivi);
>   - `L2Diversification` (icona).
> - **A**: la pagina utente, destinazione dell'icona.
> - **K**: la select dei tipi.

### F-3b · V6 — ordine per nome senza emoji ✅ 2026-09-24

> **Note implementazione**: `nameOrder` confronta `sortableName(nome)`, cioè il nome senza emoji né i caratteri
> invisibili che le compongono (bandiere, toni della pelle, keycap, sequenze ZWJ). Un nome fatto di sole emoji resta
> intero; la parità si risolve ancora per id.
> **Prova sui nomi reali** (sonda node, stessi 7 nomi della review): prima raggruppati per emoji iniziale, con «Btp»
> ultimo; dopo in ordine alfabetico (Amundi, Amundi, Btp, iShares, Xtrackers ×3). Casi limite: `🇮🇹` → resta
> `🇮🇹`; `1️⃣ Uno` → `1 Uno`; `👍🏽 Bravo` → `Bravo`.
> ```
> cd frontend && npx vitest run src/lib/components/risk/correlationHelpers.test.ts → Test Files 1 passed (1) · 64 test
> npx prettier --check src/lib/components/risk/correlationHelpers.ts → pulito
> ```
> **Test nel lotto TL-R** (basso livello, per `test-author`):
> - R1: emoji iniziali e finali ignorate;
> - R2: un nome di sole emoji resta intero e non va in testa per stringa vuota;
> - R3: la parità si risolve ancora per id.

### Avviso del coordinatore su `tee log | head` (24/09): verificato, nessuna conclusione mia su un log troncato

> - Server di review: `… dev.py server … 2>&1 | tee files/F3_server_review2.log`, senza `head` (riga di comando del
>   PID 10908). I conteggi («0 login», richieste) vengono da `grep -c` sul file completo.
> - I due log vitest di oggi passavano da `tee | grep | head -6`, ma con ≤ 3 righe filtrate, quindi `head` non ha chiuso
>   la pipe. Completezza provata: entrambi contengono la riga finale di vitest (`Duration`).
> - I log dei server precedenti finiscono dove il server è stato fermato. Lo stop è brusco, quindi nessuna riga di shutdown.
> - Evidenze di F-2e: `> log 2>&1`, senza pipe.
> - D'ora in poi: `cmd > log 2>&1; head -n N log`.

### F-3b · decisioni del 24/09, fra le 11:30 e le 11:45

> - **V5, matrice**: il developer sceglie **A**, sistemare il grafico attuale (ECharts). Dentro il disegno i nomi
>   perdono le emoji, che restano nel tooltip e altrove. I margini si calcolano sul testo vero; le celle hanno una misura
>   minima fissa, con pan orizzontale nella card. La strada B (HTML) è scartata.
> - **Coordinatore, dopo l'assenso di Risk**: la prop dell'icona del manuale in `RiskLevelSection` la scrive **F**, nel
>   suo ramo. Condizioni:
>   - facoltativa e **senza default**;
>   - **solo** la zona del titolo;
>   - il blocco di stato e motivi resta di Risk, che lo cambia dopo aver unito questo ramo;
>   - i punti di chiamata di Dashboard e Broker (`RiskLevelsPanel.svelte`) li collega Risk dopo l'integrazione.
>
>   Fino ad allora F è l'unico scrittore del file. Stato e motivo (V4): li decide Risk col developer, nel tempo ②.
> - `risk-analysis.spec.ts:1347` (il canvas della heatmap) è nel ramo di base, ma Risk l'ha tolto al passo ⑥
>   (`551edffdc`). Le asserzioni sul canvas rimaste sono tutte in `risk-lab.spec.ts` e passano a F-6. All'integrazione
>   entrano F e Risk uno dopo l'altro; i cancelli si girano dopo entrambi.
> - **Pagina utente** della correlazione: esiste nel ramo di A, `mkdocs_src/docs/user/assets/correlation.en.md`
>   (`e2327e9a3`, `b67b8ba79`). A entra prima di F, quindi l'icona può puntare lì.
> - **K**: l'API della select dei tipi (`ui/select/TreeSelect.svelte`) la chiede il coordinatore. Nel ramo di F si
>   progetta sulla select di oggi; il passaggio a quella di K si fa all'integrazione.
> - `risk.analytics.correlation.description`: la riscrive F con `dev.py i18n` × 4. Il namespace è di Risk, che il
>   coordinatore avvisa.

## Checkpoint prima della riprogettazione — 2026-09-24, 11:35–11:50 (chiesto dal coordinatore)

> **Note implementazione**: cancelli rigirati sulla revisione esatta del checkpoint (F-0…F-2e + V6), uno per volta:
> ```
> vitest: 14 path (tutti i file di test che importano un modulo toccato, +syncTargets.test.ts nuovo) ⇒ Test Files 14 passed (14) · 452 test
> front check 11:36:22→11:36:50 · 3 errori + 41 avvisi negli stessi 4 file del pavimento, 0 in risk/ e assets/ · generated.ts a085da1c8dac55f9
> front format --check → pulito
> front-portfolio risk-lab (6154, /tmp/librefolio-r2-f) 11:37:33→11:39:39 · exit 0 · 16 passed (16 dichiarati)
> check-orphans → exit 1 · 5 orfani, lista identica al 23/09, tutti di J · già rossi sul target
> mkdocs build (10:39:56, 0 WARNING) + check-links (80 = 80): nessun sorgente mkdocs cambiato dopo il build
> ```
> **Target**: `dev_release2` = `2a23b7ad3`, quattro commit di journal e istruzioni avanti all'HEAD `f1047f766`, su 4
> percorsi, **nessuno** dei 32 di questo ramo.
>
> **⚠️ Fuori pista**: la lista degli 8 path vitest del 23/09 non era stata scritta. L'ho ricostruita dal codice, e ora
> sono 14. `git ls-files` non vede i file nuovi, quindi `syncTargets.test.ts` va aggiunto a mano: la stessa trappola
> è già costata una volta.
> **Stato**: `FROZEN` fino al commit. Server di review spento, `6164` e `6154` libere. Dopo il commit: copia di prod
> rinfrescata, server rialzato, e si riparte da V5-A.

### Checkpoint committato — 2026-09-24, 11:49 (dal developer, con lo script con guardie del coordinatore)

> `025b30222` → `7f06df51d` → `6e6061c33` → `553a20991` → `7227898d2` → `46ee7258c` → `c10e75f14` → `dc29a3089`
> su `f1047f766` · `git diff --shortstat f1047f766..HEAD` = **32 file, +3236/−159**, come atteso · albero pulito.
>
> **⚠️ Fuori pista, tutti presi prima del commit**:
> - **Di F, preso dal coordinatore**: i miei comandi `git add` non avevano `-C`. Lanciati dal checkout principale, dove
>   il developer ha il terminale, avrebbero committato **sul target**. Lo script del coordinatore usa
>   `git -C <worktree>` e si ferma se HEAD, stage o percorsi non tornano.
> - **Di F, preso dal coordinatore**: nei corpi dei messaggi c'erano righe da 73 a 75 colonne; avevo misurato solo i
>   soggetti (≤ 50). Il coordinatore li ha riavvolti a 72, e io ho verificato che le parole siano le stesse.
> - **Del coordinatore, preso da F**: la guardia sui 32 percorsi confrontava una lista in ordine C con un `sort` che
>   segue la lingua del terminale (`2.3-Apple`). Con `it_IT.UTF-8` ed `en_US.UTF-8` si sarebbe fermata su percorsi
>   giusti; con `C` e `C.UTF-8`, cioè le shell degli agenti, passava. Corretto con `export LC_ALL=C`, provato su tre lingue.
>
> Tre sviste in due direzioni, e nessuna vista da chi l'aveva scritta. Una lista di comandi da far eseguire a un altro
> va provata **nel suo ambiente**: cartella, lingua e larghezza di riga.

### Ripresa dopo il checkpoint — 2026-09-24, 11:51

> - Copia di prod rinfrescata dalla snapshot (23/09 10:52): `004_release_1_2_0_schema`, marcatore assente, nessun file
>   laterale prima né dopo la lettura `immutable=1`. La precedente è in `.prev-20260924-115121`.
> - Server su `6164`: PID 37059, `cwd` = questo worktree, `db_path` = la copia, versione `v1.1.0-236-gdc29a3089`, **pulita**,
>   senza `-dirty`. Bundle: costruito = servito = `cddd783650b0d142`, nessun sorgente più nuovo.
>   `generated.ts a085da1c8dac55f9`. Log: `files/F3b_server.log`, scritto con `| tee file` senza `head`.
> - **API della select dei tipi di K** (dal coordinatore, alle 11:47; per ora solo nel ramo di K). Nel ramo di F si
>   progetta sulla select di oggi.
>   - `TreeSelect` è **a scelta singola**, e la multipla non è prevista. Per il filtro «Tipo» del laboratorio: una lista
>     di caselle propria, alimentata da `buildAssetTypeTree()`, oppure un filtro per famiglia con `assetTypeFamily()`.
>   - `buildAssetTypeOptions()` non esiste più nel ramo di K: nessun consumatore nuovo.
>   - Dettaglio completo: `files/K_treeselect_api_20260924.md`.

### F-3b · V5-A — la matrice, sistemata dentro ECharts · 2026-09-24, 11:55–12:15 (in attesa dell'occhio del developer)

> **Note implementazione** (`CorrelationHeatmap.svelte`, `correlationHelpers.ts`):
> - **Nomi**: sugli assi i nomi sono senza emoji (`plainName`, lo stesso filtro dell'ordine per nome, ora esportato);
>   il tooltip e le liste le conservano. Le righe vanno a capo su due linee oltre i 200 px (`overflow: 'break'`); le
>   colonne, oblique a 45°, si tagliano con i puntini oltre i 150 px. `interval: 0` impedisce a ECharts di nascondere
>   etichette di sua iniziativa.
> - **Misure**: i margini vengono dalle etichette **misurate** (canvas 2D, stesso font esplicito dell'asse, `12px
>   sans-serif`), non più dal numero di caratteri. In ECharts 6 `grid.outerBoundsMode: 'none'`: altrimenti il
>   default `auto` restringe il disegno da solo quando un'etichetta sfora.
> - **Geometria** (`heatmapLayout`, puro): celle fra 44×34 e 88×52 px. Se la card è stretta il grafico diventa più
>   largo della card e la card **scorre in orizzontale**, con una sfumatura sul bordo destro. Se è larga, le celle si
>   fermano al massimo. L'altezza segue le righe; la prop `height` è ignorata, ma resta perché `L2Diversification` la
>   passa e deve compilare.
> - **Triangolo**: via la prima riga e l'ultima colonna, che erano vuote. Asse y invertito, così la riga piena
>   poggia sui nomi delle colonne. Via le bande grigie di sfondo; le celle hanno un bordo del colore della card.
> - **Legenda** in HTML sotto il grafico (−1 · 0 · +1, con le parole delle bande), così resta visibile quando la card
>   scorre. Valori nelle celle sempre visibili, bianchi sulle celle sature.
> - **Larghezza**: la colonna della griglia sotto `lg` è `grid-cols-1` (`minmax(0, 1fr)`). La larghezza disponibile è
>   quella del box che scorre, osservato con `ResizeObserver`, non più del grafico.
>
> **Prova sui numeri** (sonda del solo helper puro):
> - 7 asset, triangolo 6×6: in una card da 729 px → grafico 728×448, celle 84×52, **entra**; in 1100 px → celle al
>   massimo, 752 px; in 420 px → celle al minimo, **scorre**;
> - 15 asset, calcolato a mano: 14 colonne da 44 px → 840 px, **scorre**.
>
> ```
> front check: 3 errori + 41 avvisi negli stessi 4 file del pavimento, 0 nei miei · prettier pulito
> vitest correlationHelpers.test.ts → Test Files 1 passed (1) · 64 test
> front build → servito = costruito = 4728d8aaaf3b0759 · 1 chunk con il codice nuovo · nessun sorgente più nuovo
> ```
> **⚠️ Fuori pista**:
> - Per la sonda ho lanciato `npx tsx`, credendolo presente. npx l'ha **scaricato da solo** (`tsx@4.23.15`) nella sua
>   cache utente (`~/.npm/_npx/fd45a72a545557e9/`). Nel progetto non è cambiato niente: manifest intatti, nessun
>   `tsx` in `node_modules`. È un'installazione non autorizzata, anche se involontaria, ed è segnalata al coordinatore.
>   D'ora in poi le sonde TypeScript passano da vitest, che c'è già.
> - L'ultima riga della stessa sonda l'ha tagliata un mio `| head -6`, contato prima degli avvisi. Il caso da 15 asset
>   l'ho quindi ricalcolato a mano invece di rilanciare.
>
> **Per V8**, visto qui: il tooltip dice *«si muovono in direzioni opposte»* anche a ρ = −0,08, perché
> `correlationBand` dà `inverse` a qualunque negativo. È lo stesso difetto delle liste; si ripara con le soglie di V8.
>
> **Test per il lotto TL-R**:
> - R4 `heatmapLayout`: minimo e massimo delle celle, scorrimento solo sotto il minimo, `bottom` = (w + h)·sin 45°;
> - R5 `plainName`: stessi casi di R1–R2.

### F-3b · V5-B e V8 — i ritocchi del developer sulla matrice, e la graduatoria · 2026-09-24, 12:20–12:45

> **Il developer, sulla V5-A** (*«hai fatto un lavoro fighissimo!»*), con due schermate:
> 1. la barra dei colori va **allineata alla matrice**: oggi è fuori asse, e quando la card è stretta resta **fuori**
>    dallo scorrimento. Etichette su due righe: sopra numero e parola breve (*«concorde/indipendente/inversa, o
>    sinonimi migliori»*), sotto la spiegazione;
> 2. «I più simili»: *«il problema sono i nomi… così diversi… mandano in vacca il sistema»*. Proposta: una
>    **graduatoria 1°, 2°…** con tag e valore, e al click l'evidenza del riquadro nella matrice o il suo tooltip;
> 3. un terzo ordine **per tipo**; un quarto e un quinto per **settore** e **area**, ma sono distribuzioni:
>    *«hai qualche idea? se no dillo chiaramente e scartiamo l'idea»*.
>
> **Note implementazione**:
> - **Legenda**: ora è **dentro** il box che scorre, con margine sinistro = `grid.left` e larghezza = quella delle
>   celle (minimo 280 px), quindi parte dove parte la prima colonna e scorre con la matrice. Due righe per estremo:
>   `−1 · Inversa` / `0 · Nulla` / `+1 · Concorde` in grassetto, sotto le spiegazioni già esistenti (`band.*`).
>   *«Nulla»* e non *«indipendente»*: una correlazione zero non è indipendenza, e la pagina di teoria lo dice.
> - **Bande simmetriche** (`correlationBand`): `inverse` solo per ρ ≤ −0,3, e fra −0,3 e +0,3 `low` qualunque sia il
>   segno. Il tooltip non dice più *«direzioni opposte»* a −0,08.
> - **Graduatoria** (`CorrelationPairsList`):
>   - su una riga il rango (cerchietto numerato), il valore e un'etichetta: *quasi identici* da 0,9, *molto simili*
>     sopra 0,7, *si compensano* da −0,3, *opposti* da −0,7;
>   - sulla riga sotto i due nomi, in piccolo, ciascuno troncato per conto suo, completi nel `title`;
>   - entrano **solo** le coppie oltre le soglie (`topPairs`: `high` e `inverse`), e i suggerimenti lo dicono
>     (*«Coppie con ρ > 0.70…»*, *«…ρ ≤ −0.30…»*).
> - **Collegamento nei due sensi**: il click su una voce evidenzia la cella (`highlight`), ne apre il tooltip
>   (`showTip`) e la porta in vista, anche scorrendo di lato. Un secondo click chiude. Il click su una cella seleziona
>   la sua voce, se è in graduatoria. Dopo ogni ridisegno la selezione si ripunta, o cade se la coppia non c'è più.
> - **Ordine «Per tipo»** (`typeOrder`, puro): segue `ASSET_TYPE_MENU_ORDER`, i tipi sconosciuti vanno in fondo, e
>   dentro il tipo si ordina per nome senza emoji. Il pulsante compare solo se chi monta la heatmap passa i tipi: il
>   laboratorio sì (`selectionTypes`, dalle stesse fonti delle etichette), la Dashboard no, finché Risk non lo decide.
> - **i18n** (`dev.py i18n`): 7 chiavi nuove e 2 aggiornate, +13/−4 per catalogo; 3411 chiavi in ognuna delle 4
>   lingue, stesso insieme.
>
> ```
> front check: pavimento invariato, 0 nei miei file · prettier: 1 file riformattato (una riga riunita), poi pulito
> vitest correlationHelpers.test.ts: 5 rossi attesi (fissavano «ogni negativo compensa») → riallineo a test-author
> front build → servito = costruito = 63e24115192c1491 · 1 chunk con il codice nuovo
> ```
> **Settore e area: la mia valutazione, da decidere col developer.**
> - **I dati ci sono**: distribuzioni con pesi che sommano a 1 (`classification_params.sector_area` e
>   `.geographic_area`), lette in una sola richiesta (`GET /api/v1/assets?asset_ids=…`). Sui suoi 15 asset ce le hanno
>   10 per il settore e 9 per l'area.
> - **Regola proposta, «prevalente»**:
>   - gruppo = il peso più grande se ≥ 50% (es. *Tecnologia 95%*), altrimenti **Diversificato**;
>   - non classificati in fondo;
>   - nel gruppo, per peso decrescente e poi per nome;
>   - il gruppo compare nel tooltip.
> - **Scartata**: la «somiglianza di esposizione» (coseno fra le distribuzioni), opaca e confondibile con
>   «Per somiglianza», che è sui rendimenti.
>
> **⚠️ Fuori pista**: l'avviso del coordinatore su `npx`: nemmeno `--no-install` impedisce il download. Da qui in
> poi solo binari locali (`frontend/node_modules/.bin/vitest`, `…/prettier`) o `npm run`. I miei `npx vitest` e
> `npx prettier` di stamattina hanno trovato lo strumento in locale, ma senza garanzia.

### F-3b · V5-C — ordini «Per settore» e «Per area», regola «prevalente» (scelta del developer, 24/09 ~12:50)

> **Note implementazione**:
> - **Dati**: `AssetSetCorrelationSection` legge le distribuzioni della selezione con **una** richiesta
>   (`read_assets_bulk_api_v1_assets_get`, `GET /api/v1/assets?asset_ids=…`). La lettura riusa `safeScalar` e
>   `normalizeDistribution` del modulo `assets`, invece di copiarli.
>   - **Verificato nel codice**: una GET non passa da `notifyPortfolioMutation` (`isPortfolioAffectingMutation`
>     considera solo POST, PUT, PATCH e DELETE), quindi non può scartare la risposta di correlazione in volo.
>   - La chiave dell'effetto sono gli id ordinati, confrontati per valore (la lezione di F-2d).
>   - I nomi dei paesi arrivano da `countryStore`, caricato **prima** di pubblicare i gruppi, così non compaiono
>     mai come codici ISO.
> - **Regola** (`dominantExposure`, `exposureOrder`, puri):
>   - gruppo = la voce di peso massimo se ≥ 50%, altrimenti *Diversificato*; senza distribuzione *Non classificato*;
>   - a parità di peso massimo vince la chiave che viene prima nell'ordinamento;
>   - i gruppi con nome sono ordinati per etichetta; dentro il gruppo chi è più concentrato va prima, poi il nome;
>   - poi i diversificati e infine i non classificati, entrambi per nome.
> - **Etichette**: settori con `sectors.<sectorI18nKey>`, ripiego sulla chiave grezza, mai `sectors.…` a schermo;
>   paesi con `getCountryInfo(iso3).name`; `Other` → `common.other`. Icona del settore o bandiera del paese solo in HTML.
> - **Lettura**: una fila di etichette sopra la matrice con i gruppi nell'ordine della matrice e il loro numero
>   (`risk-correlation-groups`); nel tooltip, sotto ogni nome, il gruppo con la quota (*Tecnologia 95%*). I due
>   pulsanti compaiono solo se almeno un asset ha la distribuzione. La barra degli ordini ora scorre invece di
>   uscire dalla card.
> - **i18n** (`dev.py i18n`): altre 4 chiavi (`ordering.sector/region`, `group.diversified/unclassified`). Cumulativo
>   F-3b: +19/−4 per catalogo, 3415 chiavi, stesso insieme nelle 4 lingue.
>
> ```
> front check: pavimento invariato, 0 nei miei file · prettier: 1 riga riunita, poi pulito
> front build → servito = costruito = d767b2866e6fdad3 · 1 chunk con la fila dei gruppi
> ```
> **Test**: `dominantExposure` ed `exposureOrder` sono in coda a `test-author` (TL-R), insieme al riallineamento delle
> soglie. Come prima: solo test sui calcoli, niente E2E.

### Nuovo perimetro da Risk, tempo ② (dal coordinatore, 24/09 ~12:40) — **registrato, non iniziato**

> Tre funzioni approvate dal developer nel tempo ② di Risk; la divisione del lavoro è confermata dal coordinatore.
> 1. **Idoneità degli asset nel periodo**:
>    - **non selezionabile**, con il motivo: nessun prezzo, cambio assente, meno di 20 quotazioni;
>    - **selezionabile con un avviso**: l'asset parte dopo l'inizio del periodo, oppure l'ultimo prezzo ha più di 7 giorni.
> 2. **«I miei asset» = quantità > 0**, non più `tx_count_own > 0`. Chi li ha avuti in passato scende fra «di altri
>    utenti» se qualcuno li detiene adesso, altrimenti fra «in analisi».
> 3. **Il replay esclude da solo** gli asset che non coprono la finestra; il blocco «escludi e riprova» sparisce.
>
> **Di F**:
> - il selettore di Asset Global consuma `POST /api/v1/risk/eligibility`; `SearchSelect` supporta già `disabled`, e il
>   motivo va in un tooltip;
> - «I miei asset» per quantità nel preset;
> - il declassamento nei tre pannelli della pagina (`assetScope`).
>
> **Di Risk**: il servizio di idoneità, i campi nuovi della lista asset («posseduti ora da me / da altri»), il picker
> del benchmark, e il replay con esclusione automatica; il wrapper di F passa l'esito così com'è.
> **Dipendenza**: il backend esiste solo nel ramo di Risk. Checkpoint di Risk, poi un merge fra i rami o l'attesa
> dell'integrazione, da decidere col developer. Fino ad allora F progetta sul contratto: per ogni asset uno stato
> *ammesso / avviso / motivo*.
> **Collocazione nel piano**: dentro V3, il selettore «+» con i filtri, che si progetta direttamente con questi stati
> (voci disabilitate con il motivo), e V2 per il preset «I miei asset».

### F-3b · V5-D e V7 — tooltip, nomi che scorrono, icona del manuale · 2026-09-24, 12:40–13:15

> **Il developer** (12:38): le due informazioni per settore e area *«mi piacciono entrambe, ma le metterei
> sempre, non solo in base al selettore, e nel tooltip non solo il dominante ma tutte le opzioni»*; la graduatoria
> *«ora è mooolto meglio»*, e se i nomi non ci stanno devono *«scorrere come già facciamo altrove»*; *«a volte la
> cella cliccata viene nascosta sotto l'infobox»*; *«leverei il tooltip se il mouse resta fisso»*; e ancora manca
> l'icona del manuale con `Tooltip.svelte`.
>
> **Note implementazione**:
> - **Tooltip della matrice**:
>   - prima la lettura (ρ e banda) e le osservazioni, poi i due asset, ciascuno con **tutto** il settore e **tutta**
>     l'area, sempre, qualunque ordine sia scelto;
>   - le voci sotto l'1% non sono elencate ma contate (*«+N altri»*), perché un fondo mondiale ha decine di paesi
>     sotto l'1%;
>   - la posizione è `tooltipBesideCell`: sopra la cella, o sotto se sopra non c'è spazio, e mai sopra la cella. La
>     cella si ricava dal layout, non da ECharts, così il tooltip aperto dalla graduatoria (senza mouse) va nello
>     stesso posto;
>   - `appendTo: 'body'`: il tooltip esce dal box che scorre invece di esserne tagliato o spinto sopra la cella.
> - **Graduatoria**: i nomi scorrono con `use:scrollOnOverflow` e `overflowScrollTextClass`, gli stessi delle tabelle
>   di asset e broker. Via il `title` nativo: era il riquadro che compariva col mouse fermo e copriva le voci sotto.
> - **Icona del manuale (V7)** in `RiskLevelSection`, concordata con Risk tramite il coordinatore:
>   - due prop facoltative senza default, `docsPath` e `docsLabel`, e un `DocsLink` (icona libro, `Tooltip.svelte`)
>     subito dopo il titolo, nella sola zona del titolo;
>   - niente icona nei livelli richiudibili, perché un link dentro il `<button>` di apertura non è HTML valido. Lì
>     decide Risk;
>   - `docsPath` si chiama così perché `check-links` lo trova come letterale: **81** link validati (erano 80);
>   - destinazione: la pagina di teoria della correlazione, che esiste in questo ramo; all'integrazione si passa a
>     quella utente di A, `user/assets/correlation/`;
>   - testo del tooltip: `risk.analytics.correlation.help`, nuova chiave nel namespace di Risk, così la Dashboard può
>     riusarla.
> - **Correzioni di mio codice trovate da `test-author`**:
>   - `plainName` toglieva anche `®`, `©` e `™`, perché `Extended_Pictographic` li comprende: «SPDR® S&P 500®»
>     perdeva le ® sull'asse. Ora toglie solo le emoji *come emoji* (presentazione emoji, pittogrammi con VS16,
>     bandiere, toni, ZWJ, keycap, tag). Provato su 11 nomi: le ® restano, 👑 🇪🇺 ❤️ spariscono;
>   - `exposureOrder` confrontava i gruppi per verità delle chiavi: una chiave `''` stava fra i gruppi con nome ma
>     saltava il confronto, e l'ordine dipendeva dall'ingresso. Ora si confronta per livello, e `dominantExposure`
>     ignora le chiavi vuote.
>
> ```
> test-author: correlationHelpers.test.ts 5 rossi riallineati + 43 test nuovi → 107/107 (poi 107/107 anche sulle due correzioni)
> front check: pavimento invariato, 0 nei miei file · prettier pulito (2 file con righe riunite)
> check-links: exit 0 · 81 valid (+1: …/risk-metrics/correlation) · 3 known-broken
> i18n: +26/−5 per catalogo, cumulativo F-3b · 3419 chiavi, stesso insieme nelle 4 lingue
> front build → servito = costruito = e94da319475c3a49
> ```
> **⚠️ Fuori pista**: la prova positiva del marquee nel chunk della graduatoria dava 0. Non era un difetto: la classe
> e l'azione stanno in un chunk condiviso (`C0z5aG4O.js`) che quel chunk importa. Verificato seguendo l'import,
> invece di ripetere la ricerca nel posto sbagliato.
> **Riportati, non corretti** (da `test-author`): lo spareggio di `topPairs` dipende dall'ordine del payload
> (preesistente, innocuo finché gli id arrivano crescenti); `heatmapLayout` con 0 colonne; il ripiego di `plainName`
> su un nome di sole emoji non è ripulito dagli spazi.

### F-3b · V5-E — «Altro» mai criterio, tooltip su una riga, badge sempre, «Per nome» in fondo · 2026-09-24, 13:15–13:40

> **Il developer**:
> - *«mi piace tutto»*, ma nel tooltip una lista lunga diventa grande: **una sola riga**, il resto nascosto in
>   «Altro», e l'«Altro» dei dati **in fondo** anche quando è la quota maggiore;
> - nell'ordinamento *«altro non deve essere un parametro di ordinamento, se non come fallback finale»*;
> - l'icona del manuale *«solo lei, allineata a destra»*, e dovrà esserci *«in tutti i pannelli di tutte le pagine,
>   con annessa pagina di documentazione»* (girato al coordinatore);
> - rimettere la visualizzazione a badge, cioè le file dei gruppi che comparivano solo con «Per settore» e «Per area»;
> - *«metti l'ordinamento per nome alla fine»*.
>
> **Note implementazione**:
> - **Regola** (`dominantExposure`): `Other` (`OTHER_EXPOSURE`, la stessa chiave nei settori e nei paesi) è escluso
>   sia dai candidati sia dal totale. La soglia del 50% vale sulla sola parte classificata: *Altro 65 · Finanza 25 ·
>   Servizi 10* va in *Finanza*, al 71% del classificato. Un asset con il solo `Other` diventa il gruppo di ripiego.
>   Quattro livelli (`exposureOrder`): gruppi con nome, diversificati, solo-«Altro», non classificati.
> - **Tooltip**: una riga per dimensione, con le tre voci con nome più grandi e poi un solo «Altro» con tutto il resto,
>   compreso l'`Other` dei dati, sempre ultimo. La riga non va a capo e finisce con i puntini se proprio non ci sta.
>   La chiave `risk.assetSet.exposure.others`, ora inutile, è rimossa con `dev.py i18n remove`: nessuna chiave morta.
> - **Badge sempre**: due file, «Settore» e «Area», qualunque ordine sia scelto. Ogni gruppo compare una volta con il
>   numero dei suoi asset, nell'ordine di `exposureOrder`, quindi coincide con la matrice raggruppata. È sottolineata la
>   dimensione per cui la matrice è ordinata.
> - **Ordini**: somiglianza · tipo · settore · area · **nome** (ultimo).
> - **Icona**: `justify-between` nell'intestazione, così sta sola sul bordo destro.
>
> ```
> front check: pavimento invariato, 0 nei miei file · prettier pulito
> vitest correlationHelpers.test.ts: 4 rossi attesi (fissavano «Altro» come gruppo e la quota assoluta) → riallineo a test-author
> i18n: 3418 chiavi, stesso insieme nelle 4 lingue (una rimossa)
> front build → servito = costruito = fea7d5c451e3c1da
> ```

### Correzioni in avanti e decisione del developer sul seguito (dal coordinatore, 24/09 ~13:45)

> **⚠️ N5 (§2) era vera solo a metà**, e l'ha trovato J. `_grandfather_onboarding_for_test_users`
> (`populate_mock_data.py`) rende terminali gli utenti E2E per i **flow**, ma non semina le righe degli **step**,
> arrivate con il Round 5. Al primo `GET /settings/onboarding` il backend le crea `pending`, e le guide Import e Bulk
> seguono gli step: il coachmark parte per `TEST_USER` in ogni wizard di import, e l'esito dipende dall'ordine delle
> spec. J lo corregge alla radice nel suo C4, seminando gli step `completed`. **Fino all'ingresso di C4**, un
> coachmark Import o Bulk in un E2E di F con `TEST_USER` viene da qui, non dal lavoro di F. La mia N5 aveva letto la
> funzione, non l'insieme delle righe che l'onboarding crea davvero.
>
> **Decisione del developer sul seguito**:
> 1. F mette l'icona del manuale su **tutti i pannelli del laboratorio**, a fine riprogettazione.
> 2. Poi F prepara il **checkpoint finale**, e il developer fa il merge del ramo di F in quello di Risk.
> 3. Da lì prosegue **Risk**: review e rifinitura dei componenti successivi, l'icona su tutti i pannelli di tutte le
>    pagine, le pagine di documentazione.
>
> **Conseguenze**:
> - il vincolo «F prima di Risk» si soddisfa da sé, perché il ramo combinato lo porta Risk;
> - idoneità, «i miei asset» per quantità e declassamento restano di F **solo** se il backend di Risk arriva prima
>   del checkpoint finale; altrimenti passano a Risk col merge. Non si aspettano;
> - il link dell'icona verso `user/assets/correlation/` lo sposta chi integra, dopo l'ingresso di A.

### F-3b · V5-F — badge anche nel tooltip, file che non vanno a capo, spiegazione del pannello · 2026-09-24, 13:45–14:05

> **Il developer**: l'icona è nella posizione giusta. La spiegazione però deve descrivere il **pannello**
> (*«In questo pannello si vanno ad analizzare le correlazioni 2 a 2…»*). Il tooltip della matrice va bene, ma
> *«mi aspettavo i badge anche qui»*. I badge in cima non devono andare a capo: *«se capita farei foldare le label e
> lascerei icona e numero»*, con emoji anche per *Diversificato* e *Non classificato*.
>
> **Note implementazione**:
> - `risk.analytics.correlation.help` riscritta sul modello del developer (4 lingue): pannello, coppie, periodo, cambi,
>   lettura dei valori, guida.
> - **Tooltip**: le voci di settore e di area sono badge in HTML, stile inline perché il tooltip vive nel `body`. Tre
>   con nome, poi «Altro» in fondo, su una riga che non va a capo.
> - **File in cima**: `flex-nowrap`. Un'azione (`foldWhenNarrow`) confronta una copia invisibile della fila con tutti i
>   nomi (`w-max`) con la larghezza disponibile; se non ci sta, i badge si riducono a icona e numero, con il nome in un
>   `Tooltip.svelte` al passaggio. La decisione dipende solo dalla copia, non dalla fila visibile, quindi non oscilla.
> - **Emoji dei gruppi senza nome**: 🧩 *Diversificato*, ❔ *Non classificato*, 🌐 *Altro* per le aree; l'«Altro» dei
>   settori ha già 📦.
> - **Test**: `test-author` ha riallineato 4 test e ne ha aggiunti 3 per la regola «Altro»: **114/114**.
>
> ```
> front check: pavimento invariato, 0 nei miei file · prettier pulito · vitest correlationHelpers.test.ts 114/114
> front build → servito = costruito = 4eda94b83625944e · prove positive: copia di misura, 🧩, testo nuovo
> ```

### F-3b · V5-G — la cella scelta si riconosce · 2026-09-24, 14:05–14:10 — **matrice chiusa col developer**

> **Il developer**: *«tutto perfetto»*. Ultima richiesta: la cella scelta, dalla graduatoria o col mouse, deve avere
> un bordo acceso che risalti, altrimenti non si capisce a quale cella appartiene il tooltip. *«Tooltip, estetica,
> badge ed il resto mi piace un sacco!»*
>
> **Note implementazione**:
> - lo stato `emphasis` della serie è lo stesso per il passaggio del mouse e per l'`highlight` lanciato dalla
>   graduatoria; ora dà un bordo ambra da 3 px con alone. L'ambra non è nessuno dei due estremi della scala rosso–blu;
> - ECharts alza la cella evidenziata sopra le vicine (`Z2_EMPHASIS_LIFT = 10`, letto in `echarts/lib/util/states.js`),
>   quindi i bordi delle tessere accanto non coprono il suo.
>
> ```
> front check: pavimento invariato, 0 nei miei file · prettier pulito
> front build → servito = costruito = 1a0a0b623eb7056e · prova positiva: l'alone ambra è nel bundle
> ```
> **Stato di F-3b**: matrice (V5), graduatoria (V8), ordini (V6, tipo, settore, area), badge, tooltip e icona del
> manuale (V7) sono **approvati dal developer**. Restano:
> - V4, stato e motivi (Risk, tempo ②);
> - V1–V3, il guscio di selezione e il sync unico;
> - le sezioni ancora da guardare: i confronti di A e il replay;
> - l'icona del manuale su tutti i pannelli del laboratorio;
> - il checkpoint finale verso il ramo di Risk.

### F-3b · V5-H e apertura di V1–V3 · 2026-09-24, 14:10–14:25

> **V5-H**: l'ambra del bordo spariva sulle celle rosse (il developer). Ora è **verde** (`#22c55e`, alone
> `rgba(34,197,94,0.65)`), il complementare del rosso e lontano dal blu. Bundle servito `6b5fe6d053b5a890`; prova
> positiva: il verde c'è, l'ambra non c'è più.
>
> **Prossimo passo, scelto dal developer**: il blocco di selezione e il sync unico. Il developer chiede anche di
> domandare al coordinatore se nel frattempo sono arrivati altri compiti su questi due temi, per farli insieme.
> Domanda inviata alle 14:15.
>
> **Stato attuale, letto dal codice** (`AssetSetRiskPanel.svelte`):
> 1. riga 1: precarica per broker (`SimpleSelect`), «Aggiungi asset» (`AssetSelect` fissa, limitata agli asset della
>    pagina non ancora scelti) e, a destra, il «Sincronizza» del guscio;
> 2. riga 2: i quattro pulsanti rapidi (tutti, nessuno, inverti, i miei), con il conteggio a destra;
> 3. riga 3: le etichette dei filtri per tipo e per valuta, con «Azzera i filtri»;
> 4. riga 4: gli asset scelti, con la ×.
>
> I filtri restringono i **candidati** su cui agiscono i pulsanti rapidi; il broker **sostituisce** la selezione.
>
> **Pezzi riusabili, verificati**: `SearchSelect` è a scelta singola, con `disabled` per voce, sezioni, icone e
> ricerca; `AssetSelect` è costruito su di essa. Un «+» con **filtri** e **scelta multipla** richiede un componente
> nuovo, e lo stato *ammesso / avviso / motivo* dell'idoneità di Risk ci entra come voce disabilitata con il motivo.
> **Sync**: la barra della pagina (`PageToolbar`) è la stessa per i due tab. Sul tab Correlazione, «Sinc. Tutto»
> aggiorna i prezzi di tutti gli asset della pagina, mentre il guscio aggiorna la selezione con i cambi. Anche Abs/% e
> le impostazioni del grafico lì non agiscono.

### F-3b · V1–V3 — scheda di selezione e sync unico ✅ 2026-09-24, 14:30–15:20 (in attesa dell'occhio del developer)

**Decisioni del developer** (14:25–14:30): sul tab Correlazione la barra perde ricerca, valuta e tipo (attivi/inattivi
resta, «per ora non ci pensare»); via Abs/% e impostazioni; «Sinc.» della barra apre **il nostro** `PageSyncModal`
(prezzi + cambi della selezione) e il pulsante del guscio sparisce; il broker diventa un comando rapido accanto a
Tutti/Nessuno/Inverti, al posto di «I miei asset», con una prima voce «Tutti i miei»; la scheda tiene i filtri e
riceve un «+» con ricerca e scelta multipla.

> **Note implementazione**
> - **Barra (`assets/+page.svelte`)**: ricerca e riga valuta/tipo sotto `{#if activeTab !== 'correlation'}`; lo
>   snippet `actions` ha un ramo per il tab Correlazione con due pulsanti soli: **Sinc. selezione**
>   (`risk-sync-button`, apre il modal del laboratorio via `labPanel.openSync()`, spento finché `labCanSync` è falso)
>   e **Ricarica tutto** (`risk-reload-button`, `labPanel.reload()`: `invalidateRisk` + `syncGeneration`, niente
>   serie della griglia). Entrambi con `Tooltip.svelte`. Il ramo del tab Asset è quello di prima, re-indentato:
>   `git diff -w` sulla pagina = **+51/−2**.
> - **Pannello**: `openSync()` e `reload()` esportati, `canSync` `$bindable` (effetto su `syncTargets`); la regola
>   `{accepted}` resta in `handleSynced`, invariata. Via `SimpleSelect`, `AssetSelect`, il pulsante sync, «I miei
>   asset» e `pageAssetIds` (il «+» legge i `candidates`, che vengono dalla lista della pagina: la restrizione vale
>   per costruzione).
> - **Comando «I miei asset ▾»** (`loadHoldings(brokerId | null)`): «Tutti i miei» = `fetchReport` **senza** broker,
>   poi un broker per voce. Legge le *holdings* del report = posizioni aperte con quantità sopra la soglia di polvere
>   al `dateEnd` (verificato: `portfolio_service.py`, `end_positions … ps.quantity > _QUANTITY_DUST_THRESHOLD`), cioè
>   già il «quantità > 0» che Risk definirà nel tempo ②. Riusa la doppia domanda sul `null`. **Nuovo**: se non c'è
>   niente di posseduto la selezione **non** si svuota e compare un avviso (`risk-broker-filter-empty`).
> - **Filtri**: due menu compatti (`LabCheckMenu`: Tipo con le icone dei tipi, Valuta con le bandiere), con il
>   conteggio degli asset per voce e il numero di voci attive sul pulsante. Stessi testid per voce di prima
>   (`risk-filter-type-*`, `risk-filter-currency-*`, `risk-filters-clear`).
> - **Asset scelti**: chip con l'icona dell'asset (o del tipo), alti come il «+»; la × senza `title` nativo.
> - **«+» (`LabAssetPicker`)**: ricerca per parole, senza accenti (`foldForSearch`, `pickerRows`), elenco in ordine
>   per nome senza emoji (`nameOrder`), caselle, «Seleziona/Deseleziona visibili» (`toggleVisibleRows`), «Aggiungi N»,
>   rispetto del tetto dei 100. Elenca gli stessi candidati su cui agisce «Seleziona tutti»; con un filtro attivo lo
>   dice, con «Azzera i filtri». Nessun importo: nome, tipo, valuta.
> - **Guscio comune `LabPopover`**: il pulsante sta nella stessa radice del pannello, così premerlo di nuovo chiude
>   invece di riaprire (il difetto di un ascoltatore esterno che conosce solo il pannello); chiude su pressione fuori
>   ed Esc; si sposta sul bordo destro se uscirebbe dallo schermo.
> - **i18n ×4 via `dev.py i18n`**: +12 (`sharedResource.syncSelection`, `risk.assetSet.{syncSelectionHint,reloadHint}`,
>   `risk.assetSet.preset.{allMine,byBroker,hint,noneHeld}`, `risk.assetSet.picker.{selectVisible,deselectVisible,
>   confirm,allSelected,filtersOn}`), −2 (`risk.assetSet.presetBroker`, `presetNone`, ora senza chiamanti). 3428
>   chiavi per catalogo, insiemi identici.
> - **`applyFilters` generica** (`<T extends SelectableAsset>`): il tipo dei candidati ora arriva intatto al «+».
>
> **Prove**: `dev.py front check` → `svelte-check found 3 errors and 41 warnings in 4 files`, gli stessi quattro del
> pavimento, **0** in `risk/` e nella pagina (log `/tmp/libreFolio_f3b/frontcheck_v1v3b.log`); prettier `--write` sui 5
> file toccati; `dev.py front build` exit 0; prove positive nel bundle: `risk-asset-add-button`,
> `risk-broker-option-mine`, `risk-reload-button`, «Sinc. selezione». vitest `assetSetSelection` + `correlationHelpers` +
> `syncTargets`: 3 percorsi ⇒ **3 file, 194 test verdi**.
>
> ⚠️ **Fuori pista**: `Tooltip.svelte` con `interactiveChild` fissa il suggerimento al click per **30 s**
> (`PINNED_LEAVE_GRACE_MS`): sul «Sinc. selezione» sarebbe rimasto sopra il modal appena aperto. I tre pulsanti
> avvolti (sync, ricarica, «+») fermano il click prima del wrapper (`stopPropagation`): il suggerimento resta al
> passaggio del mouse. Ricostruito: bundle servito = costruito = `0fab55b6cffa9c4a`.
>
> ⚠️ **Fuori pista (atteso, per F-6)**: la E2E `risk-lab` userà selettori spariti — `risk-sync-button` dentro la
> scheda, `risk-asset-add-select`, `risk-bulk-mine`, le chip dei filtri visibili senza aprire il menu. Non è stata
> rilanciata: la politica della riprogettazione è niente E2E nuovi; il riallineamento è F-6.
>
> **Aperti**: D11 (fermare il polling live sul tab Correlazione) da chiedere al developer; il segnaposto del pulsante
> «adatta al periodo comune» di Risk (tempo ②, collegato da Risk dopo il merge F → Risk) solo se il developer vuole
> vederne la posizione; test di basso livello per `foldForSearch`, `pickerRows`, `toggleVisibleRows`,
> `visibleRowsAllChecked` via test-author.

### F-3b · feedback delle 15:27 sulla scheda di selezione, poi checkpoint 2 · 2026-09-24, 15:27–15:43

**Le nove osservazioni del developer (15:27)**, con lo stato di ognuna al checkpoint:

1. **Barra in alto sul tab Correlazione: via anche attivi/inattivi.** ✅ Tutto il blocco `asset-page-filters`
   (ricerca, attivi/inattivi, valuta, tipo, azzera) è sotto `{#if activeTab !== 'correlation'}`, e i due `{#if}`
   interni di V1 sono tolti (`git diff -w`: solo la condizione esterna). Verificato che non resta un filtro nascosto:
   `loadAssets` chiama `/assets/query` con `queries: {}`, quindi attivi/inattivi agisce solo su `filteredAssets`, che il
   laboratorio non legge.
2. **Icona del broker nel comando per broker.** ⏳ Dopo il merge: `BrokerIcon` con `size="sm"`, come in
   `BrokerSearchSelect`.
3. **«Seleziona tutti» e «Deseleziona tutti» non funzionavano subito.** ⏳ Ipotesi da riverificare col developer: agiscono
   sui candidati filtrati da Tipo e Valuta, quindi con un filtro attivo sembrano non fare niente. Con i filtri dentro il
   «+» agiranno su tutto il catalogo analizzabile.
4. **«15 selezionati su 15» non dice su cosa.** ⏳ Diventa «N in analisi su M analizzabili», con un tooltip: M è il
   catalogo intero, non solo gli asset del developer.
5. **All'apertura, «Tutti i miei».** Decisione (`ask_user`): **si riparte dall'ultima selezione; se non c'è, da «Tutti
   i miei»** (le holdings al `dateEnd`, non più `tx_count_own`), poi il piccolo insieme di ripiego. ⏳ Dopo il merge.
6. **Filtri Tipo e Valuta dentro il «+».** ⏳ Dopo il merge; `LabCheckMenu` allora sparisce.
7. **I 4 asset proposti come selezionabili.** Il developer: «il punto non è il tipo crowdfunding, ma che quei asset
   hanno 0 prezzi registrati», e la cosa «si dovrebbe ricollegare all'engine di ammissibilità». Verificato in sola
   lettura sulla copia (`sqlite/app.db` con `immutable=1`, solo id, tipo e conteggi): gli asset 12–15 hanno **0 righe**
   in `price_history`, tutti gli altri arrivano al 2026-09-24. Nessuna regola nel frontend: domanda sul contratto inviata
   a Risk (sessione «Risk management analysis»), coordinatore in copia. **Decisione del developer, relayata dal
   coordinatore**: il backend di Risk si collega adesso nel ramo di F. Quindi checkpoint, merge Risk → F a `14c334d85`,
   e solo dopo il collegamento del «+» agli stati di idoneità.
8. **Colore della cella scelta: il verde si confonde col blu.** Decisione (`ask_user`): **contorno neutro**. ✅ Nero
   `#0f172a` con alone bianco sul tema chiaro, bianco con alone `rgba(2,6,23,0.95)` sul tema scuro
   (`CorrelationHeatmap.svelte`, `emphasis.itemStyle`).
9. **D11**: il polling live **resta** (c'è comunque lo scheduler del backend ogni 10 minuti). **«Adatta al periodo
   comune»**: nessun segnaposto, il developer lo vedrà quando esisterà.

> ⚠️ **Fuori pista**
> - Una modifica a metà del modulo di selezione (tipi di ammissibilità e rimozione di `ownedAssetIds`) è stata
>   **annullata** prima del checkpoint. Da sola rompeva la compilazione, e la forma dei tipi va presa dal contratto vero
>   di Risk, dopo il merge. Il modulo differisce da `dc29a3089` solo per le aggiunte di V1–V3.
> - Guida di onboarding: l'anchor `asset.page.filters` non esiste sul tab Correlazione. Se la guida della pagina asset
>   parte da lì, quel passo va in stallo (`OnboardingOverlayHost`, `stalledStepId`). Rischio residuo, da segnalare nel
>   passaggio di consegne.

**Checkpoint 2, cancelli sulla revisione esatta** (uno per volta):
```
front check        · svelte-check 3 errori + 41 avvisi negli stessi 4 file del pavimento · 0 in risk/ e assets/
prettier --check   · 16 file del frontend → pulito
vitest             · gli stessi 14 path del checkpoint 1 ⇒ Test Files 14 passed (14) · 502 test (erano 452, +50 correlationHelpers)
check-orphans      · exit 1 · 5 orfani, lista identica al checkpoint 1, tutti di J
mkdocs check-links · exit 0 · 81 validi · 3 known-broken
git diff --check   · pulito · i18n +26/−2 per catalogo, 3428 chiavi, insiemi identici
server             · 6164 fermato (stop_bash f3bserver) · lsof 6154 e 6164 → exit 1 · PID 37059 assente
```
**Non girati**: E2E `risk-lab` (selettori cambiati: il riallineamento è F-6; dopo il merge il coordinatore la chiede nella
6154) e `front build` (l'ultimo bundle, `0fab55b6cffa9c4a`, precede il blocco filtri intero e il contorno neutro).
Log in `/tmp/libreFolio_f3b/ckpt2_*.log`.
