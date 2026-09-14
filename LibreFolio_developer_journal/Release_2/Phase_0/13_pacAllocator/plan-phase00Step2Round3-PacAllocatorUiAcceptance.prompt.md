# PAC allocator UI acceptance - Round 3

**Stato:** approvato dal developer; baseline rollback-safe A-F committata a
`8504f0528`; aggiornamento target coordinato chiuso a `1e0b9bc519c1`. Round 3
autorizzato sulle sole superfici PAC-owned. ToolHub, cataloghi i18n e CHANGELOG
restano ai writer condivisi e non entrano in D fino al loro checkpoint frozen.

← Piano precedente: [PAC allocator UI refinement - Round 2](plan-phase00Step2Round2-PacAllocatorUiRefinement.prompt.md)

## 1. Obiettivo

La review manuale Round 2 e stata respinta: il comportamento A-F e presente, ma
la UI non e ancora accettabile. Round 3 deve:

1. mostrare le card Broker subito, senza preselezione o selettore a quattro stati;
2. rendere i contributi progressivi, con vuoto esplicito `[]` e nessun banner;
3. compattare tipografia, input e azioni secondo il resto dell'app;
4. tradurre e colorare Posseduti/Altri utenti/Osservati;
5. eliminare gli zero finali inutili e mostrare bandiere valuta;
6. spiegare perche serve FX e offrire una copia esplicita del tasso salvato;
7. rendere visibili nella preview finale card Tool full-width e cataloghi J;
8. ottenere approvazione manuale desktop/mobile prima di integrare D nel target.

Il Tool resta analisi P1 dello stato iniziale. Nessun solver, raccomandazione,
ordine, routing Broker, conversione implicita, short, leva, FIFO/WAC/fisco o
Riskfolio entra in Round 3.

## 2. Baseline e gate di rollback

| Evidenza | Valore |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-friendly-dollop` |
| Branch | `e-alfy-allocatore-pac` |
| Rollback A-F | `8504f05280d9ff15485b6f8c07fb2b93ab45e1b5` |
| Target coordinatore | `e1f3fe177861d2b9b953b218f66ea7d4714ab405` |
| HEAD combinato | `1e0b9bc519c13339353b840596048d5e012e6e85` |
| Parent HEAD | `8504f0528` + `e1f3fe177` |
| Stato iniziale | clean; index e untracked vuoti |
| Lane | porta `6153`, data `/tmp/librefolio-r2-d` |
| Venv | `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |
| Coordinatore | `c8328a01-f208-4ade-a352-0486d1f14de2` |

La preview Round 2 PID `35419`/shell `221` e stata fermata senza `--force`;
porta `6153` verificata libera. Nessun server review torna attivo prima della
produzione Round 3 completa, dipendenze shared integrate e gate verdi.

## 3. Decisioni chiuse

### 3.1 Cassa esistente

- Default UI: `broker_copy`.
- Le card dei soli Broker OWNER appaiono appena arriva allocation-source.
- Nessun Broker e preselezionato.
- Nessun selettore `not supplied / none / broker / manual`.
- `Inserisci manualmente` sostituisce il pannello Broker; `Torna ai Broker`
  ripristina card e selezione conservata.
- Zero Broker selezionati invia cassa esplicitamente vuota `[]`.
- Il frontend invia soltanto `selected_cash_balances` aggregato dal backend:
  non somma, converte, scala o ricostruisce saldi.
- Missing/error/no OWNER Broker resta visibile con Retry e fallback manuale.
- Account/date/selection request guards e blocco stale restano obbligatori.

### 3.2 Nuovi contributi

- Stato vuoto → `contributions=[]`.
- Nessun `SimpleSelect`, nessun `not supplied`, nessun banner giallo.
- `Aggiungi contributo` crea la prima riga in valuta report con
  `monetary_step="0.01"`.
- Rimuovere l'ultima riga torna a `[]`.
- Cash esistente e contributi restano pool distinti.

### 3.3 FX di valorizzazione

- Se i fatti selezionati sono tutti nella valuta report, la sezione resta
  nascosta.
- Se esiste una valuta estera, la UI espone la causa concreta, per esempio:
  `Apple ha prezzo USD; il report e EUR`.
- Spiega che il tasso serve solo al confronto P1 e non scambia/trasferisce cassa.
- `Copia tasso salvato` chiama esplicitamente il dominio FX esistente:
  `lookupFxRate(native, report, as_of_date)`.
- Nessun auto-prefill al solo apparire della sezione.
- Tasso e data copiati restano editabili.
- Backward-fill espone la data effettiva.
- Missing/error lascia il campo vuoto e offre Retry.
- Sequence/account/as-of/pair/field-revision impediscono overwrite da risposta
  vecchia o da edit manuale.
- Nessuna API/schema/generated-client change; niente `api sync`.

### 3.4 Densita e accessibilita

- Rimuovere dalle superfici PAC le pseudo-classi `btn*` e `input-field` senza
  definizione globale; usare utility Tailwind esplicite.
- Titoli sezione `text-sm`; descrizioni e label `text-xs`.
- Input desktop circa 36 px, testo `text-sm`, padding compatto.
- Mobile mantiene font 16 px per l'anti-zoom iOS; niente
  `zoom-guard-exempt` sui form generali.
- Refresh, Duplica e Rimuovi diventano icon-only con Tooltip e `aria-label`.
- CTA di flusso hanno target minimo 32 px desktop/40 px mobile.
- `Analizza stato` resta l'unica CTA primaria piena.
- Focus, contrasto, disabled, dark mode e stato selezionato devono restare
  distinguibili.

### 3.5 Scope e valori

- Enum stabili: `owned`, `other_users`, `observed`; label tradotte.
- Colori derivati dall'enum, non dalla traduzione, tramite
  `frontend/src/lib/utils/colors.ts`.
- Lo stesso scope usa lo stesso colore in filtro e badge.
- Selezione aggiunge check/ring senza appiattire tutti i chip sul verde.
- Prezzi, saldi, aggregati, quote e percentuali usano
  `formatDecimalForDisplay` solo per la resa.
- Valute mostrano `getCurrencyInfo(code).flag_emoji` con `.emoji-flag`.
- Wire Decimal, exact view e payload non cambiano.

## 4. ASCII approvata

### 4.1 Card Tool condivisa

```text
+------------------------------------------------------------------+
| [calculator] Allocatore PAC                      [book] Documenti |
| Analizza lo stato iniziale esatto dell'allocazione.               |
+------------------------------------------------------------------+
```

Descrizione sibling full-width; card e Docs mantengono azioni separate.
`ToolsHub.svelte` resta J/coordinatore-owned.

### 4.2 Desktop - fondi e catalogo

```text
1. Fondi disponibili
Usa la cassa nativa dei tuoi Broker oppure inserisci importi esatti.

Cassa esistente                                      [Inserisci manualmente]
+----------------------+  +----------------------+
| [Broker] Fineco  [ ]  |  | [Broker] IBKR    [x] |
| quota personale 100%  |  | quota personale 50%  |
| [flag] EUR 1 240,5    |  | [flag] USD 325       |
+----------------------+  +----------------------+

Riserve selezionate dal backend
[[flag] USD 162,5]                                      [refresh]

Nuovi contributi
Nessun nuovo contributo.               [+ Aggiungi contributo]

2. Asset e target                         [refresh] [+ Asset manuale]
[Posseduti 3] [Altri utenti 5] [Osservati 8]   [ Cerca per nome... ]
+------------------+ +------------------+ +------------------+
| [Asset] VWCE [x] | | [Asset] Apple [ ]| | [Asset] BTP  [ ] |
| [Posseduto]      | | [Altri utenti]   | | [Osservato]      |
| [flag] EUR 121,34| | [flag] USD 208,5 | | Prezzo mancante  |
+------------------+ +------------------+ +------------------+
```

### 4.3 Desktop - contributo, editor e FX

```text
Nuovi contributi
[[flag] EUR v] [Importo 500] [Passo monetario 0,01] [trash]
[+ Aggiungi contributo]

+------------------------------------------------------------------+
| [Asset][Broker] Apple · snapshot importato    [copy] [trash]      |
| fonte/data/read-only                                             |
+-------------------------------+----------------------------------+
| STATO INIZIALE                | TARGET                           |
| Custodia          1,5 quote   | Peso target            [40] %   |
| Prezzo      [flag] USD 208,5  | Griglia           [Intere|Fraz.] |
| Base quotazione        1      | Passo quantita          [0,001] |
+-------------------------------+----------------------------------+

3. Tassi di valorizzazione
Apple ha prezzo in USD; il report e EUR.
Serve solo per confrontare i valori. Nessuna cassa viene scambiata.
[Copia tasso salvato]  1 [flag] USD = [0,9234] [flag] EUR [data]
```

### 4.4 Mobile

```text
1. Fondi disponibili
[Inserisci manualmente]
[Broker card]
[Broker card]
Riserve selezionate: [[flag] USD 162,5]

Nuovi contributi
[+ Aggiungi contributo]

2. Asset e target
[scope] [scope] [scope]
[cerca........................]
[Asset card]

[Asset/Broker header] [copy] [trash]
[STATO INIZIALE]
[TARGET]

3. Tassi di valorizzazione
[motivo USD -> EUR]
[Copia] [rate]
```

### 4.5 Stati

```text
Broker loading:   placeholder; nessun aggregato inviabile
Broker error:     errore + Retry + Inserisci manualmente
Zero Broker:      spiegazione + Inserisci manualmente
Contributi vuoti: nessun banner; payload []
FX loading:       spinner; input non sovrascritto
FX missing:       nessun tasso salvato + Retry
FX stale reply:   risposta ignorata; draft preservato
Invalid input:    errore vicino al campo
Busy compute:     controlli disabilitati; Stop disponibile
```

## 5. Superfici e ownership

### D produzione

- `frontend/src/lib/features/tools/pac-allocator/PacAllocatorTool.svelte`
- `frontend/src/lib/features/tools/pac-allocator/PacMoneySection.svelte`
- `frontend/src/lib/features/tools/pac-allocator/OwnedAssetGallery.svelte`
- `frontend/src/lib/features/tools/pac-allocator/PacContextEditor.svelte`
- `frontend/src/lib/features/tools/pac-allocator/PacResultPanel.svelte`
- `frontend/src/lib/features/tools/pac-allocator/editorTypes.ts`
- eventuale helper PAC currency display, solo se usato da almeno due componenti.

`allocationSource.ts` resta invariato salvo necessita di typing reale. Backend,
API, generated client, runner, Asset global, Header/Sidebar/onboarding sono
esclusi.

### Test

Writer esclusivo: `test-author`.

- `frontend/src/lib/features/tools/pac-allocator/PacAllocatorTool.test.ts`
- `frontend/e2e/tools/pac-allocator.spec.ts`
- eventuale test helper PAC mirato.

Nessun selector basato su testo tradotto, posizione fissa o conteggio globale;
nessun clock sleep; fixture create/verify/cleanup.

### Shared

J/coordinatore:

- `frontend/src/lib/features/tools/ToolsHub.svelte`
- `frontend/src/lib/i18n/en.json`
- `frontend/src/lib/i18n/it.json`
- `frontend/src/lib/i18n/fr.json`
- `frontend/src/lib/i18n/es.json`
- `CHANGELOG.md`

D non modifica questi file. Ingresso in D:

1. checkpoint J frozen;
2. developer merge target/shared -> D, oppure patch additiva deterministica del
   coordinatore dopo freeze;
3. mai cherry-pick;
4. mai D -> target per ottenere una review.

### Docs

`docs-writer` aggiorna soltanto
`mkdocs_src/docs/user/tools/pac-allocator/index.en.md`. Nessuna traduzione, nav o
CHANGELOG.

## 6. Passi

1. [x] 2026-09-12 - Preservare baseline rollback-safe e materializzare il piano.
   > **Nota implementazione**: il developer ha committato A-F a `8504f0528`; il
   > coordinatore ha integrato il target `e1f3fe177` in D. Verificato HEAD
   > `1e0b9bc519c1`, parent esatti, target contained, status/index/untracked
   > puliti. Fermati shell `221` e PID `35419`; porta `6153` libera. Creato
   > questo piano e cross-linkato Round 2 prima di ogni edit produzione.
   > **Evidenza**: `git rev-parse HEAD`, `git log -1 --format`,
   > `git merge-base --is-ancestor e1f3fe177... HEAD`, `git status
   > --porcelain=v1 --untracked-files=all`, `lsof -nP -iTCP:6153
   > -sTCP:LISTEN`.
   > **Fuori pista**: la review Round 2 e stata respinta anche per due
   > dipendenze J assenti dalla preview D. Restano volutamente fuori da questo
   > piano writer finche J non congela il checkpoint.
2. [x] 2026-09-12 - Compattare la fondazione visiva PAC.
   > **Nota implementazione**: rimosse tutte le pseudo-classi PAC `btn*` e
   > `input-field` prive di definizione globale. Le superfici PAC usano ora
   > utility Tailwind esplicite, gerarchia `text-sm`/`text-xs`, field compatti,
   > azioni secondarie icon-only con Tooltip/aria-label, focus-visible, disabled
   > e dark mode. I field mobile conservano il font anti-zoom globale.
   > **Evidenza**: `rg` sulle pseudo-classi nei componenti PAC -> zero match;
   > Prettier mirato sui sei file produzione; `pipenv run python dev.py front
   > check` con venv condiviso -> 0 errori, 41 warning preesistenti in due file.
   > **Fuori pista**: la densita incoerente non dipendeva soltanto dai valori
   > Tailwind: `btn*`/`input-field` erano nomi copiati da componenti con CSS
   > locale e quindi non governavano questi componenti PAC.
3. [x] 2026-09-12 - Ridisegnare cassa/contributi funding-first.
   > **Nota implementazione**: il draft apre in `broker_copy`; le card OWNER
   > appaiono senza preselezione o mode selector. Una CTA compatta passa a
   > manuale e una torna ai Broker, preservando selezione e guardie backend.
   > Saldi/quota/aggregato sono formattati e mostrano bandiera valuta.
   > Contributi vuoti producono `[]`; Add crea valuta report + step `0.01`;
   > remove ultimo torna a `none`. Rimossi selector triplo e banner amber.
   > **Evidenza**: tipi interni ristretti a `broker_copy|manual` e
   > `none|custom`; build input conserva aggregato server-owned e separazione
   > cash/contributi; type-check 0 errori.
4. [x] 2026-09-12 - Rifinire catalogo Asset, scope, Decimal e bandiere.
   > **Nota implementazione**: filtri e badge usano colori stabili derivati
   > dall'enum tramite `getIndexColor`, mantenendo label i18n indipendenti dal
   > colore e check/ring di selezione. Toolbar/search/card sono compatti;
   > prezzo usa `formatDecimalForDisplay` e bandiera dal currency store.
   > Lifecycle, ordering, ricerca, privacy e persistenza selezione invariati.
   > **Evidenza**: nessun calcolo economico aggiunto; formatter solo display;
   > type-check 0 errori.
5. [x] 2026-09-12 - Compattare editor corrente/target e risultati.
   > **Nota implementazione**: Duplica/Rimuovi sono icon-only accessibili,
   > input manuali/target/quantum hanno densita uniforme, scope candidato
   > conserva lo stesso colore del catalogo, prezzi/report/cash pool espongono
   > bandiera e Decimal leggibile. Exact view e wire restano intatti; locking,
   > current/target, quote base e quantum non cambiano.
   > **Evidenza**: Prettier mirato verde; type-check 0 errori.
6. [x] 2026-09-12 - Aggiungere FX contestuale con copia esplicita protetta.
   > **Nota implementazione**: rimossi collapse/checkbox ridondanti. La sezione
   > deriva motivi separati da Asset, cassa e contributi e resta nascosta se non
   > serve. `Copia tasso salvato` usa `lookupFxRate(native, report, as_of)`,
   > conserva data effettiva di backward-fill, lascia il draft editabile e non
   > parte automaticamente. Sequence/account/date/pair/field identity bloccano
   > overwrite vecchi; missing resta visibile con retry/manuale.
   > **Evidenza**: nessun backend/schema/generated change o API sync;
   > type-check 0 errori.
   > **Fuori pista**: il review semantico post-format ha trovato che i ritorni
   > stale/account/field-guard potevano lasciare `fxCopyingCurrency` valorizzato.
   > Il cleanup e ora in `finally` e rispetta la sequence corrente, quindi non
   > spegne una richiesta piu nuova. Secondo `front check` verde.
7. [x] 2026-09-12 - Aggiornare component/unit tramite `test-author`.
   > **Nota implementazione**: lo stesso writer test esclusivo
   > `d9be354c-40ea-4fb1-902c-aca459b6e392` ha aggiornato
   > `PacAllocatorTool.test.ts` per Broker-first, contributi `[]`/Add/remove,
   > colori scope, bandiere/Decimal e copy FX esplicito con
   > retry/backfill/guardie field-date-report-account.
   > **Evidenza**: rilancio principale lane 6153
   > `component-unit 'PacAllocatorTool'` -> 30 passed / 1805 skipped.
8. [x] 2026-09-12 - Eseguire gate statici mirati; nessun server/E2E prima del verde.
   > **Nota implementazione**: Prettier mirato produzione e test verde;
   > `front check` eseguito due volte dopo produzione e cleanup FX.
   > **Evidenza**: 0 errori e 41 warning preesistenti in due file esterni;
   > component-unit completo 1835/1835; successivo gate pre-shared
   > `front check && front build` exit 0, check 0 errori/41 warning e build
   > client/server completate in 17.65s/28.36s. Nessun server persistente
   > avviato prima dei gate.
9. [x] 2026-09-12 - Aggiornare E2E desktop/mobile tramite `test-author`.
   > **Nota implementazione**: il writer esclusivo ha sostituito helper/select
   > legacy con azioni Round-3 via `data-testid`, mantenendo payload Decimal e
   > privacy. Coperti 14 scenari su entrambi i viewport.
   > **Evidenza**: rilancio principale lane 6153
   > `pac-tool 'PAC allocator'` -> 28 passed; selector legacy, locator CSS e
   > sleep -> zero match.
   > **Fuori pista**: i red intermedi del writer erano aspettative test
   > obsolete (submit senza riga valida, source pending, guardia SearchSelect
   > 200 ms, ordine testo prima delle bandiere), non regressioni prodotto.
10. [x] 2026-09-12 - Aggiornare docs EN e produrre handoff i18n/shared.
    > **Nota implementazione**: `docs-writer` ha aggiornato soltanto
    > `mkdocs_src/docs/user/tools/pac-allocator/index.en.md` per Broker-first,
    > contributi progressivi, scope/privacy, imported/manual, quantum distinti,
    > FX contestuale/copia esplicita e boundary P1. Inviato al coordinatore
    > handoff esatto 10 ADD / 0 UPDATE / 10 REMOVE condizionali con valori
    > EN/IT/FR/ES e call site; nessun catalogo D modificato.
    > **Evidenza**: MkDocs strict build verde; link 12/12. `translate-validate`
    > exit 1 per debito globale noto (549 file, 105 errori, 110 warning), senza
    > diagnostiche sulla pagina PAC. Nessuna traduzione, nav o stamp.
    > **Fuori pista**: il primo estrattore chiavi ha usato il binario shell
    > `rg`, non disponibile nel PATH di quel processo; ripetuto con `grep`
    > read-only, ottenendo il delta deterministico sopra.
11. [ ] Integrare checkpoint shared frozen e validare revisione combinata.
12. [ ] Avviare preview test e chiudere review manuale developer.

Dopo ogni step: data, `Nota implementazione`, evidenza esatta e ogni
`Fuori pista` prima di passare allo step successivo.

## 7. Prove

Component/unit:

- default `broker_copy`, zero selezioni, card visibili;
- nessun selettore cash legacy;
- ID Broker ordinati e aggregato backend copiato esatto;
- old response/data/account/report change non sovrascrive;
- manuale/ritorno Broker preservano stato;
- default contributi `none`, payload `[]`, add/remove/step;
- nessun select/banner not-supplied;
- scope color key stabile e label indipendente dal colore;
- display Decimal/flag senza cambiare payload;
- FX nascosto se non necessario;
- reason Asset/cash/contribution;
- zero chiamate FX prima del click;
- direzione `1 native = rate report`;
- backward-fill, missing/error/retry e late-response guard;
- locking, manual duplicate, quote base e quantum invariati.

E2E desktop/mobile:

- Broker immediati, selezione singola/multipla, aggregato progressivo;
- fallback manuale;
- contributi vuoti/add/remove;
- scope tradotti/colorati, prezzo formattato, flag;
- controlli compatti e azioni accessibili;
- motivo FX, no auto-fetch, copia/edit/missing/stale;
- regressione dei 14 scenari desktop + 14 mobile esistenti.

Comandi sequenziali:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
pipenv run python dev.py test \
--test-port 6153 \
--data-dir /tmp/librefolio-r2-d \
<categoria> <azione>
```

Gate:

- PAC component mirati;
- `ExactDecimalInput CurrencySearchSelect SingleDatePicker`;
- component-unit completo;
- PAC E2E desktop/mobile;
- Prettier mirato;
- `front check`;
- `front build`;
- i18n parity/audit dopo shared;
- MkDocs strict/check-links secondo docs-writer;
- `git diff --check`;
- port teardown.

Nessun `api sync`: API/schema non cambiano. Se l'endpoint FX corrente non basta,
fermarsi e chiedere una decisione; non estendere il backend implicitamente.

## 8. Runbook review

- URL: `http://127.0.0.1:6153/tools/pac_allocator`
- Utente: `e2e_test_user`
- Lingua: IT, poi smoke EN
- Viewport: desktop e mobile
- Fixture: esclusivamente test data `/tmp/librefolio-r2-d`

Scenari:

1. Tool card description full-width e Docs separato.
2. Primo open con Broker card immediate e zero preselezioni.
3. Riserve native progressive, formattate e con bandiere.
4. Manuale e ritorno Broker.
5. Contributi vuoti, add, edit, remove ultimo.
6. Scope tradotti, distinti e coerenti.
7. Prezzi/quote senza zeri inutili e flag.
8. Imported/manual + current/target compatti.
9. Asset USD/report EUR: motivo, copia FX, edit.
10. Solo USD/report USD: nessun FX.
11. FX missing e risposta vecchia.
12. Invalid/busy/stale/error senza perdita draft.

## 9. DoD

1. Tutti i feedback visuali sono coperti da produzione, test o dipendenza shared
   verificata.
2. Preview IT senza fallback EN nei call site PAC/ToolsHub.
3. Tool card description full-width.
4. Broker card immediate e aggregato backend progressivo.
5. Contributi vuoti `[]` senza selector/banner.
6. Scope tradotti/colorati, Decimal leggibili e valute con bandiera.
7. Densita coerente desktop/mobile senza perdere accessibilita/anti-zoom.
8. FX contestuale, esplicito, editabile e protetto.
9. Contratto `1.0.0` e invarianti Round 2 intatti.
10. Unit/static/E2E/i18n/docs/diff-check verdi sulla revisione combinata.
11. Developer approva esplicitamente la review desktop/mobile.
12. Solo dopo il punto 11 il coordinatore puo proporre D -> target.
13. Nessun generated/runtime/private artifact staged; nessuna operazione Git
    mutante dall'agente.

→ Follow-up: [Round 4 — PAC + Ribilanciamento P1 multi-servizio](plan-phase00Step2Round4-PacAndRebalancerUiAcceptance.prompt.md)
