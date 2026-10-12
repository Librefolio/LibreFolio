# Backlog dopo la 1.2 — indice unico

> **Aperto il 2026-10-11** dal coordinatore della Release 2, su proposta del developer (testuale): «materializzare in
> LibreFolio_developer_journal/Release_2/Phase_0 un file mardown con il baklog post 1.2 e farlo popolare oltre che a te
> anche ai vari sotto agenti [...] così che con i vari treni e riallineamenti di baseline anche gli altri agenti possono
> aggiungerci roba e ne viene fuori un indice completo, utile per quando si riparte con gli sviluppi della 1.3 o 1.2.1
> da una chat pulita».
>
> È il **punto d'ingresso** di tutto il lavoro lasciato dopo la 1.2. Non sostituisce i vademecum delle cartelle né il
> backlog 38: li indicizza, con una riga per voce e il rimando ai dettagli.

## Come si usa

- **Una riga per voce**: `- **ID · titolo** — peso; origine (chi, data). Dettagli: [dove](percorso), sezione «…».`
  I dettagli (file e righe, prove, decisioni) restano dove sono già: il backlog 38, il README o il piano della cartella.
- **Ognuno scrive solo nella propria sezione.** Così i merge dei treni non si scontrano. Una voce che riguarda un'altra
  area si segnala al coordinatore, che la sposta.
- **Quando**: nello stesso checkpoint in cui la voce nasce, insieme al proprio piano. Chi chiude una voce la marca
  ✅ con data e commit: una voce non si cancella.
- **Il coordinatore riconcilia a ogni treno**: doppioni, voci chiuse, spostamenti fra sezioni, conteggi dell'indice.
- **Non va qui** il futuro deliberato, che resta in [`TODO_FUTURI.md`](../../../TODO_FUTURI.md). Non va qui nemmeno
  il lavoro già pianificato per la 1.2 e ancora in corso: quello sta nei piani delle cartelle.
- Pesi: minimo, basso, medio-basso, medio, alto. «Da verificare» vuol dire che serve prima un test rosso.

## 🧭 Ripartire da qui

1. Questo file, per sapere cosa resta e dove sono i dettagli.
2. Le regole del progetto: [`.github/copilot-instructions.md`](../../../.github/copilot-instructions.md). La
   decisione 10 dice che la matematica finanziaria ha una casa sola, `backend/app/services/financial_math/`.
3. Lo stato del rilascio e delle cartelle: [`phases/00-index.md`](../phases/00-index.md).
4. Per una famiglia di lavoro, la sua guida per una chat nuova:
    - Rischio: [README della 02](02_riskfolioIntegration/README.md), sezione «🧭 Ripartire da qui»;
    - PAC: [README della 13](13_pacAllocator/implementation/README.md), blocco «🧭 Ripartire da qui» in testa.
5. Le cartelle restano in `Phase_0` anche da chiuse (developer, 10/10): si archiviano solo le chat.

## Indice per fonte

| Fonte | Cosa contiene | Stato all'apertura |
| --- | --- | --- |
| [Backlog 38](38_postReleaseBacklog/README.md) | I residui delle cartelle archiviate il 09/10 (gruppi N, O, L, K, P, I) e il backlog del coordinatore (C-1…C-48) | 138 voci |
| [README della 02](02_riskfolioIntegration/README.md) | Rischio: lavoro aperto, buchi, difetti, domande aperte | A1–A6, B1–B3, B6–B8 aperti |
| [README della 13](13_pacAllocator/implementation/README.md) | PAC: il backlog delle righe e la nota di ripartenza | riga 14, E2E del PAC, difetti 1, 2, 5, opzione (e) |
| [Piano della 16](16_toolPlatform/plan-phase00ToolPlatform.prompt.md) | Piattaforma dei Tool: la definizione di fatto residua (§5) | da riverificare |
| [Cartella 21](21_onboarding/plan-phase00Onboarding.prompt.md) | Onboarding: «Cosa resta aperto», voci 2–7 | 6 voci; la 1, la review manuale C7, chiusa l'11/10 |
| [Piani della 27](27_releaseImages/) | Immagini di rilascio, galleria, pipeline delle traduzioni | vedi la sezione M |
| [Piano della 32](32_docsEnglish12/plan-phase00DocsEnglish12.prompt.md) | Documentazione inglese della 1.2 | chiusa (S24); C-43 nel 38, 32-1…32-5 nella sezione Q |
| [Piano della 37](37_brimScalable/plan-phase00BrimScalable.prompt.md) e [recap dell'esportatore](37_brimScalable/recap-phase00ScalableExporter.md) | Scalable: «Ancora aperti, con chi li ha» (passo 13) e «Todo aperti» | chiusa; aperti con responsabile |
| [Piano della 41](41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md) | P&L per broker: §14 Backlog (B1–B12) | lotto in corso (F) |
| [Piano della 42](42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md) | Controlli delle coppie promosse | chiuso; C-46…C-48 nel treno 37, C-45 nel 38; le voci P nella sezione P |
| [Piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md) | Casa unica della matematica finanziaria e riordino del codice: U1–U10, B4, i lotti della parte 2 | B1, B2, B3a nel treno 37; per la 1.2 B3b, PL3, BU1, FE1, T-1 |
| [README della 09](09_feedbackJobs/README.md) | Backlog strutturale P4 e feedback, «Cosa resta aperto» in cima (09/10) | 7 voci: 6 nella sezione 09, SP14 nella D |
| [`TODO_FUTURI.md`](../../../TODO_FUTURI.md) | Il futuro deliberato, non backlog | 52 temi |

---

## C · Coordinatore

Dettagli: [backlog 38](38_postReleaseBacklog/README.md). Qui le voci più pesanti o trasversali:

- **C-41 · Gli scatti dell'AI Export** — medio; developer, 10/10. Dettagli: 38, C-41.
- **C-42 · I vincoli delle coppie anche per contante e cambio** — medio. Dettagli: 38, C-42.
- **C-43 · Gli 8 scatti dei portali dei broker** — basso; servono schermate vere. Dettagli: 38, C-43.
- **C-44 · Gli helper della galleria in un posto solo** — basso. Dettagli: 38, C-44.
- **C-45 · Il picker del 💡 vede solo le righe caricate** — basso, da verificare. Dettagli: 38, C-45.
- **I-07 · Il controllo dei tipi sugli E2E** — basso: 2 errori e nessun gate. Dettagli: 38, I-07.
- **C-49 · Il backend non si ferma al SIGTERM entro 5 s dopo alcuni E2E** — basso, da verificare; anche per
  `docker stop`. Dettagli: 38, C-49.
- **C-50 · L'AI Export di un Asset espone il nome interno `portfolio_weight_ratio`** — basso. Dettagli: 38, C-50.
- **C-51 · I dati sintetici scrivono la vecchia forma di `classification_params`** — basso. Dettagli: 38, C-51.
- **C-52 · La CLI della sonda dell'AI Export non sa scegliere l'Asset né l'utente sintetico** — minimo. Dettagli: 38, C-52.
- **Devwiki e grafo** — medio: il passo 3 dell'historian e la ricostruzione del grafo dopo la 1.2 (P-6).

## Risk · Rischio (02)

Dettagli: [README della 02](02_riskfolioIntegration/README.md), sezioni «cosa resta aperto» e «🧭 Ripartire da qui».

- **A1–A6** — la fase 3 degli asset nei segnali, la scheda Rischio dell'asset, la guardia della simulazione, i percorsi
  adattivi, il rendimento totale, l'ottimizzazione oltre 100 titoli (A6, riaperta l'11/10).
- **B1–B3, B6–B8** — l'icona della doc sui pannelli, le colonne di rischio di Asset Global, la fetta del portafoglio per
  asset, V1/V2, gli ordinamenti della heatmap di L2, la paginazione di L3.

## D · PAC e Tool (13, 16)

Dettagli: [README della 13](13_pacAllocator/implementation/README.md), «🧭 Ripartire da qui» e «Backlog».

- **Riga 14 · L'analisi del Rebalancer**, poi gli E2E del PAC insieme a quelli del Rebalancer.
- **Difetti 1, 2, 5 e l'opzione (e)** del backlog della 13; **C-38**, l'intestazione Actions su mobile.

## I · P&L per broker (41)

Dettagli: [piano della 41](41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md), §14. La sezione la completa I a
fine lotto; F (B4) è nella 1.2.

- **B1–B3, B5–B12** — l'avviso sulle quote, le coppie invertite, K/R delle gambe, il waterfall dei trasferimenti, le
  coppie ADJUSTMENT, lo split in viaggio, il prezzo dei contributi (B8), l'AI Export per quote e reddito (B9), le date
  future in chiamata diretta (B12).

## P · Transazioni e Bulk (42)

Dettagli: [piano della 42](42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md) e 38, sezione «P · Costo medio e
impostazioni». C-46…C-48 sono nel treno 37. Righe mandate da P l'11/10 e trascritte dal coordinatore; P-5 è passata nella
sezione T, e P-7 (chiudere le issue #32 e #35) è un compito del rilascio, non di dopo.

- **P-2 · Anteprima WAC: etichetta sbagliata per le righe di split e ramo `add_at_wac` morto** — basso; P, archivio
  della 30 (09/10). Dettagli: [38](38_postReleaseBacklog/README.md), sezione «P · Costo medio e impostazioni», P-2.
- **P-3 · Contributo per posizione: dividendi e costi senza cambio esclusi senza segnale** — basso; P, archivio della
  30 (09/10). Dettagli: idem, P-3. Lo chiude F (B14 di I), se entra nella 1.2.
- **P-4 · Fuso orario: verificare il database IANA nell'immagine Docker** — basso; P, archivio della 30 (09/10).
  Dettagli: idem, P-4.
- **P-8 · `tx-clone.spec.ts`: commento di testa superato** — minimo; P, archivio della 30 (09/10). Dettagli: idem, P-8.
- **P-9 · Black: riformattare `test_portfolio_api.py` e `test_portfolio_wac.py`** — minimo; P, archivio della 30
  (09/10). Dettagli: idem, P-9.
- **P-10 · `MISSING_COST_BASIS` raggiungibile dall'app riclassificando uno SPLIT** — basso, serve una decisione; P,
  analisi della 39 (09/10). Dettagli: idem, P-10.
- **P-12 · Griglia del Bulk: le quantità oltre 15 cifre significative appaiono arrotondate** — basso; test-author di
  P, C-46 (11/10). Dettagli: [piano della 42](42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md), sezione
  «7. Seguito: C-46, C-47, C-48».
- **P-13 · Percentuali non localizzate nei componenti condivisi della Dashboard** — basso; P, mini-lotto dell'audit di
  M (11/10). `KpiSection`: 7 siti con `formatPercent` senza `locale`, visibili anche nella pagina del broker. Dettagli:
  [piano della 42](42_promotePairChecks/plan-phase00PromotePairChecks.prompt.md), sezione «8. Mini-lotto dai reperti
  dell'audit di M», 8.1.
- **P-14 · es: «broker» senza accento in altre 46 chiavi** — basso; P (11/10); i nomi propri come Interactive Brokers
  restano. Dettagli: idem, 8.2.
- **P-15 · Altre etichette inglesi scritte nel codice** — basso; test-author di P (11/10). `DataEditor`: «Date», i
  contatori «modified/deleted/new», un `aria-label`, «Reset layout»; `BrokerSharingPanel:832`: «max». Dettagli: idem,
  8.1 e 8.

## T · Matematica finanziaria e riordino (43)

Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md). Prima della 1.2: B1–B3 (B1, B2 e B3a nel treno 37, B3b nel checkpoint successivo), PL3, BU1, T-1
(dopo F) e FE1, perché l'onboarding è libero dall'11/10. Righe scritte da T dal riallineamento al treno 37; le voci B9 e
P-5 le ha trascritte il coordinatore. Dopo la 1.2:

**Difetti e motore**

- **T-B4 · La data del lotto più vecchio dopo uno split** — medio; T, 11/10. Va con U6. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione
  «7.1 Lotti, passi, peso, quando».
- **T-B5 · Il P&L di una chiusura FIFO mescola le valute** — peso da stimare, serve una decisione; T, 11/10. Se un lotto
  è aperto e chiuso in valute diverse, `_close_position_piece` (`fifo_lot_engine.py:905-940`) sottrae il prezzo del
  lotto da quello di vendita senza convertirli. Limite già documentato nella pagina dev del servizio dei lotti.
  Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3a — Lotti, niente ripiego sull'importo non convertito».
- **T-B6 · Lotti: la fonte del prezzo di riferimento dice «exact» anche quando il prezzo convertito manca** — minimo;
  T, 11/10, dalla sonda di B3b. Senza cambio `reference_unit_price` è `None`, ma `reference_price_source` resta
  `exact`, e l'AI Export lo copia. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3b», «Sonda».
- **T-B7 · AI Export: segnalare le colonne tolte perché nulle in ogni riga, in tutti i componenti** — medio-basso;
  coordinatore, 11/10. Il renderer compatto toglie una colonna nulla in ogni riga; solo i lotti ne hanno la traccia
  (`unavailable_amount_lot_count`, B3b). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3b», «Scoperte sul renderer dell'AI Export».

- **T-B8 · Sintesi FIFO dell'AI Export: valore aperto e P&L non realizzato sommano insiemi di lotti diversi** — basso;
  T, 11/10, dal docs-writer di B3b. Ognuna delle due somme prende i lotti aperti in cui quel campo è noto, mentre i
  conteggi della copertura contano i lotti in cui sono noti entrambi; con il costo di un lotto ignoto (B3b) le due
  somme non coprono più gli stessi lotti. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «B3b», «Passo 6».

**Unificazioni della matematica comune (parte 1)**

- **T-U1 · Un piano dei cambi unico: mancanti e provenienza** — medio; T, 11/10. Esclude i giri del portafoglio, che
  chiude F (O2, X5). Comprende il servizio dei lotti, che con FEE/TAX presenti converte ogni BUY/SELL come peso
  possibile e può segnalare il cambio di un trade che nessun pool legge (docs-writer di B3b). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.3» e «7.1».
- **T-U2 · Frazionamenti: caricamento, validazione, rapporto cumulato** — medio-basso; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezioni «2.7» e «7.1».
- **T-U3 · Le quote di proprietà in un solo modulo** — basso nel servizio, medio nell'AI Export; T, 11/10. Esclude i
  giri del portafoglio di F; comprende B9 di I, qui sotto. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.6» e «7.1».
- **B9 (di I) · L'AI Export dalla pagina di un broker, per Viewer ed Editor** — medio-basso, in U3; developer, 11/10.
  Nel patrimonio lo 0 di Viewer ed Editor è giusto (la Dashboard passa solo i broker propri con quota > 0); dalla
  pagina di un broker solo visto le cifre del report sono piene e il turnover è moltiplicato per la quota grezza 0
  (`broker_cost_efficiency.py:150-157`); in più l'`abs` sul reddito (`portfolio_income.py:379`). La cura: una regola
  sola per export, quella della pagina da cui parte. Dettagli: [piano della 41](41_brokerPnlFlows/plan-phase00BrokerPnlFlows.prompt.md),
  §14 B9 e §17.6.
- **T-U4 · Rendimenti e annualizzazione** — medio; T, 11/10. Comprende R1 (il ribasamento scritto due volte) e la
  riprova R2, il rendimento netto, il 365 osservato, la parità fra rischio e segnali, e C1 di I (`_wac_qualifying_txs`,
  il costo unitario dell'anteprima). Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.1» e «7.1».
- **T-U5 · Prezzo del giorno e valorizzazione** — medio-alto; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.2» e «7.1».
- **T-U6 · Finestre di detenzione dal FIFO** — medio; T, 11/10. Comprende L1 e L2 di I e T-B4. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezioni «2.5» e «7.1».
- **T-U7 · Pesi e concentrazione** — medio; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.8» e «7.1».
- **T-U8 · Il frontend solo di presentazione: Δ, KPI, lotti** — medio-alto; T, 11/10. Comprende il valore d'apertura
  che il modale della custodia ricalcola come quantità × prezzo d'apertura (`LotCustodyModal.svelte`) invece di
  leggere `original_cost`, trovato in B3b. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «7.1».
- **T-U9 · L'AI Export dalle case comuni** — medio; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «7.1».
- **T-U10 · Interessi e convenzioni di calendario (`interest.py`)** — basso-medio; T, 11/10, decisione D-8. Dettagli:
  [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «2.10» e «7.1».
- **T-D9 · MeasureSignal: la soglia dei 30 giorni sull'annualizzato** — minimo; T, 11/10, decisione D-9. Dettagli:
  [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «2.1», riga R18.
- **P-5 (di P) · Migrare `roi_utils` e `valuation_utils` in `financial_math`** — basso, refactor; decisione D1 del
  developer, registrata da P (09/10). Coperta da T-1 e BU1 se entrano nella 1.2. Dettagli:
  [38](38_postReleaseBacklog/README.md), sezione «P · Costo medio e impostazioni», P-5.

**Code reordering (parte 2)**

- **T-PL1 · Il runtime dei segnali in `services/signals/`, fine del ciclo rischio↔segnali** — medio; T, 11/10.
  Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
- **T-PL2 · Un registro per famiglia di plugin** — medio; T, 11/10, decisione D-P1. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
- **T-PL4 · `fx.py` diventa `services/fx/`** — medio; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
- **T-PL5 · `brim_provider.py` diventa `services/brim/`** — medio-alto; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
- **T-PL6 · Asset: `base.py`, via lo shim `asset_source.py`** — medio-basso; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.1».
- **T-PL7 · Un router proprio per i segnali, con gli URL invariati** — medio-basso; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «P2.1».
- **T-P2.2 · I file grandi del backend, divisi per cuciture** — medio; T, 11/10. L'evaluator del PAC,
  `portfolio_service`, le transazioni, `broker_service`, `price_store`, i router, gli schemi. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «P2.2».
- **T-BU1+BU2 · `utils/` del backend: gli aiuti di dominio, `cache_utils` e `decimal_utils`** — medio-basso, in attesa
  della decisione D-P7; T, 11/10; coordinatore, opzione A (11/10). BU1 non va prima della 1.2: `sector_fin_utils`,
  `geo_utils` e `identifier_utils` sono importati da `schemas/assets.py:58-60` e da `db/models.py:36`, e nei servizi
  rovescerebbero lo strato; `currency_utils` aspetta `services/fx/` (PL4, dopo F). D-P7: gli aiuti puri di dominio in
  `backend/app/domain/`, senza I/O, oppure in `utils/` con la regola scritta che `utils` non importa servizi.
  Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezioni «P2.3» e «Treno 38 e decisioni dopo B3b».
- **T-FE2…FE11 · Il frontend a cartelle per funzionalità** — da basso ad alto; T, 11/10. FE8 dopo P; FE6 e FE7 dopo F.
  Comprende due cose trovate con FE1 e con le durate: la copia di `DELTA_PERIODS` nella pagina FX
  (`routes/(app)/fx/+page.svelte:159`) e l'albero di `developer/frontend/index.md`, che non ha `lib/features/`.
  Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md), sezione «P2.4».
- **T-TS1 · I test del backend specchiati sul codice** — alto, solo se lo si vuole (D-P5); T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «P2.5».
- **T-TP · `pyproject.toml`: `testpaths` punta a una cartella che non esiste** — minimo; T, 11/10. Dettagli: [piano della 43](43_financialMathHome/plan-phase00FinancialMathHome.prompt.md),
  sezione «P2.5».

La voce di `TODO_FUTURI.md` sul riordino del codice si cancella a mano a mano.

## M · Traduzioni, galleria e pipeline (27)

Dettagli: [piani della 27](27_releaseImages/); per M-2…M-7 il [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
sezioni «5.9d» e «After 1.2». Righe M-4…M-7 mandate da M l'11/10, trascritte dal coordinatore.

- **M-1 · Immagini solo amd64** — [piano ReleaseGallery](27_releaseImages/plan-phase00ReleaseGallery.prompt.md), riga 209.
- **M-2 · Un passo deterministico della pipeline per i percorsi `../` delle traduzioni** — basso: solo se il caso si
  ripete (decisione del coordinatore, 11/10). I prompt (`step3_user.txt:16`, `step4`/`step5:28`) chiedono di copiare
  `src`/`href` alla lettera: ritradurre le 4 pagine con immagini locali in HTML grezzo rimette la copia, che
  `html-asset-depth` segnala.
- **M-3 · L'audit degli stamp come opzione di `translate-validate`** — basso; insieme alla scansione delle coppie
  mascherate (i tre script stanno fuori dal repo).
- ✅ **M-4 · Lo spazio insecabile della tipografia francese** — nella 1.2, decisione del developer dell'11/10: un hook
  di build, `mkdocs_src/hooks/fr_typography.py`, nel lotto 15 di M (checkpoint B). Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «6.1».
- **M-5 · La virgola decimale nelle formule** — basso; M, 11/10. Per la 1.2 restano col punto (decisione del developer
  dell'11/10).
- **M-6 · Il `../` di `srcset` e `poster` in `html-attr-mismatch`** — minimo; docs-writer di M, 11/10.
- **M-7 · La guida dei plugin BRIM e le favicon locali** — minimo; docs-writer di M, 11/10. Pagina EN: la prende chi
  riscrive la guida dei plugin BRIM.
- **M-8 · Le etichette della UI nelle pagine di teoria** — basso; M, 11/10: il 5.4 ha lasciato fuori 248 righe nelle
  pagine di teoria (scansione finale), dove il grassetto segna concetti e non citazioni. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «6.3».
- **M-9 · Il confronto etichette–catalogo come controllo di `translate-validate`** — basso; M, 11/10: oggi è uno script
  fuori dal repo (`b15_ui_label_scan.py`) che appaia per posizione grassetti e corsivi con il catalogo EN. Non vede i
  link, il testo semplice, le didascalie e gli alt: «Rendimento rolling» / «Rentabilidad móvil» (43 occorrenze, lotto 16)
  sono emersi a mano. Un controllo vero dovrebbe cercare anche i nomi delle modalità e dei pulsanti nel testo. Dettagli:
  [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezioni «6.3» e «7.2».
- **M-10 · I nomi dei provider nelle traduzioni** — minimo; M, 11/10: «Scheduled Investment» è tradotto nel nav e nei
  titoli delle pagine («Investimento Programmato», «Investissement Programmé», «Inversión Programada») e resta in inglese
  nelle tabelle (12/11/11 occorrenze); l'app mostra il nome del backend, in inglese. Scegliere una forma sola. Dettagli:
  [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md), sezione «7.3».
- **M-11 · Il registro nei prompt della pipeline** — basso; M, 11/10: i prompt (`prompts/short_article/`) non dicono
  a chi si rivolge la guida (es «tú», it «tu», fr «vous»): il lotto 16 ha tolto 112 forme di «usted» dalle pagine
  spagnole, e una run nuova potrebbe rimetterle. Una regola nei prompt e un controllo che confronti «you/your»
  dell'inglese con le forme della traduzione. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «7.4».
- **M-12 · La riga «FX on cash» negli scatti della galleria** — basso; M, 12/10: la vista Performance della galleria
  riproduce `frontend/e2e/dashboard-report.json`, una cattura reale normalizzata senza liquidità in valuta estera, quindi la
  riga di F non compare. Serve una cattura nuova dai dati del developer (regola 12: `dev.py mkdocs
  normalize-dashboard-fixture`), con un broker che tenga liquidità in un'altra valuta. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «9.3».
- **M-13 · Le sonde della galleria che ignorano il timeout** — medio; M, 12/10: in Playwright 1.61
  `locator.isVisible({timeout})` non aspetta, e `gallery.spec.ts` ne ha 76, 33 davanti a uno scatto. Se l'elemento non c'è
  in quell'istante, lo scatto salta in silenzio e il test passa: nel lotto 18, 8 scatti su 2.824. La correzione è
  `appears()` di `e2e/fixtures/probe.ts`, oggi mai usata, via test-author. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «9.3».
- **M-14 · I numeri degli scatti nella lingua del browser** — basso; M, 12/10: gli importi seguono la locale del browser
  (`toLocaleString(undefined, …)`), e la galleria gira in en-US, quindi gli scatti it/fr/es mostrano «1,188.58 €».
  Basterebbe una `locale` di Playwright per lingua. Dettagli: [journal del giro 12](27_releaseImages/plan-phase00TranslationRound12.prompt.md),
  sezione «9.3».

## Q · Documentazione e onboarding (21, 32)

Dettagli: [cartella 21](21_onboarding/) e [piano della 32](32_docsEnglish12/plan-phase00DocsEnglish12.prompt.md).

- ✅ **La review manuale C7 dell'onboarding** — chiusa l'11/10 dal developer: «tutte queste ricordo di averle
  testate, è tutto verde». Il punto 7, la guida della modale Aggiungi Broker che riparte dal primo passo, è coperto
  dall'E2E «OB-9 contrast» (`frontend/e2e/onboarding-guides.spec.ts`), verde l'11/10 sul target su desktop e mobile.
  FE1 è libero.
- **21-2 · Il contratto fra il catalogo TS e il registry Python dei flussi** — medio; nessun test confronta i due
  lati. Dettagli: [cartella 21](21_onboarding/plan-phase00Onboarding.prompt.md), «Cosa resta aperto», punto 2.
- **21-3 · Il re-trigger al cambio di versione di un flusso** — medio; mai provato end-to-end. Dettagli: idem, punto 3.
- **21-4 · La fascia 641–1023 px** — basso; Playwright prova solo 1280 e 430. Dettagli: idem, punto 4.
- **21-5 · Il reset admin o CLI dell'onboarding di un utente** — basso; oggi serve SQL. Dettagli: idem, punto 5.
- **21-6 · La telemetria su completamento e salto** — basso, facoltativa. Dettagli: idem, punto 6.
- **21-7 · L'ancora `tools.hub` senza guida** — basso; candidata per una guida Tools. Dettagli: idem, punto 7.

Le voci 32-1…32-5 vengono dai reperti dei docs-writer di S22 e S23, mai girati prima: i dettagli stanno solo qui
(trascritte dal coordinatore dalla ricognizione finale di Q, 11/10, verificate a `251067435`). Q è archiviata: le
voci le prende chi riparte sulla documentazione.

- **32-1 · Tre dettagli della pagina del banner di qualità dei dati** — minimo; Q (S23, docs-writer), 09/10. Il
  titolo `:93` attribuisce tutti i codici di portafoglio a `build_data_quality_report`, ma `MWRR_SERIES_UNRELIABLE`
  lo aggiunge `PortfolioService.get_report()` (titolo tenuto per l'ancora); la mappa dei file `:22` non cita
  quell'aggiunta per `portfolio_service.py`; la tabella dei trigger della Dashboard non ha una riga
  `MISSING_FX_RATES`. Dettagli: [data-quality-banner.md](../../../mkdocs_src/docs/developer/frontend/data-quality-banner.md),
  sezioni «🏷️ Active IssueCodes» e «🧪 How to Trigger Issues».
- **32-2 · La frase d'apertura del banner nella Dashboard** — basso; Q (S23, docs-writer), 09/10. `:88` dice che il
  banner compare se alla data finale mancano prezzi o cambi, ma il banner segnala anche prezzi vecchi, costi
  d'acquisto mancanti, cambi delle transazioni passate e asset valutati al prezzo di transazione; il `<div>` dello
  screenshot (`:89-91`) sta dentro il paragrafo, senza righe vuote. La pagina è tradotta: correggerla rimette il
  paragrafo nel giro di traduzione. Dettagli: [Dashboard](../../../mkdocs_src/docs/user/dashboard/index.en.md),
  sezione «🌡️ Data Quality Banner».
- **32-3 · `docker exec` gira come root** — basso; Q (S23, docs-writer), 09/10. `./dev.py docker exec` lancia
  `docker compose exec librefolio python dev.py …` senza `--user` (`dev.py:1796`), e l'immagine non ha `USER`: i
  comandi girano come root, e i file che creano in `LibreFolio-data/` restano di root fino al prossimo avvio, quando
  l'entrypoint ridà la cartella a `LIBREFOLIO_UID`/`GID` (`entrypoint.sh:21-29`). La pagina admin non lo dice, e il
  commento del compose d'esempio (`:287`, e lo stesso in `docker-compose.yml:42`) dice «drops to 'librefolio' user»,
  mentre gosu riceve gli id numerici (`Dockerfile:129-137`). Da decidere: documentarlo o passare `--user`.
  Dettagli: [docker_advanced.en.md](../../../mkdocs_src/docs/admin/docker_advanced.en.md), sezione «📡 `docker exec`».
- **32-4 · Le righe «Status: Implemented (Feb 2026)» delle pagine di stato del frontend** — minimo; Q (S23,
  docs-writer), 09/10. `developer/frontend/state/{index,app-state,domain-state,reference-state}.md` hanno ancora
  quella data, che git non conferma; `core-infrastructure.md` e `registries.md` sono già corrette con le date di git.
  Dettagli: [state/index.md](../../../mkdocs_src/docs/developer/frontend/state/index.md).
- **32-5 · La docstring di `daily_risk_free_rate`** — minimo; Q (S22, docs-writer), 09/10.
  `backend/app/services/risk/metrics.py:211-215` dice che un tasso per giorni di calendario «flatters every ratio
  computed with a non-zero rate»: succede solo con un tasso positivo, con uno negativo il rapporto scende (le pagine
  Sharpe e Sortino lo dicono già). Da fare insieme a C-32 del 38. Dettagli:
  [metrics.py](../../../backend/app/services/risk/metrics.py), `daily_risk_free_rate`.

## S · BRIM Scalable (37)

Dettagli: [piano della 37](37_brimScalable/plan-phase00BrimScalable.prompt.md), «Ancora aperti, con chi li ha», e
[recap dell'esportatore](37_brimScalable/recap-phase00ScalableExporter.md), «Todo aperti». S è archiviata: le voci
le prende chi riparte sui BRIM.

## 09 · Feedback e backlog strutturale

Dettagli: [README della 09](09_feedbackJobs/README.md), «Cosa resta aperto» in cima (verifica Q del 09/10). Prevale
sulle tabelle del 21/09, «Il residuo vero» compreso. Correzione della ricognizione finale di Q, 11/10.

- **P4-7 · Il ciclo di vita delle cache dei prezzi nel frontend** — medio; il registry è una `Map` senza limite né
  eviction, e niente lo azzera a fine sessione. Dettagli: README della 09, «Cosa resta aperto», e
  [`00_backlog_strutturale_P4.md`](09_feedbackJobs/00_backlog_strutturale_P4.md).
- **P4-9 · La conversione dei test specchio** — basso; gli specchi di `chartCoreHelpers.test.ts` leggono ancora il
  sorgente invece di eseguire le funzioni. Dettagli: idem.
- **P4-10 · I sei siti di Risk fuori dal canale di mascheramento** — basso, da riverificare dopo il Round 2 della
  privacy. Dettagli: idem.
- **R2 · `VERSION` stantio** — medio; manca la decisione: leggerlo solo senza `.git/`, o cancellarlo dopo la build.
  Dettagli: idem, e [08](09_feedbackJobs/08_review_visiva_20260922.md) R2.
- **§2.4 · Il guardiano del catalogo finto** — basso; debito dichiarato, non verificato nel codice. Dettagli: idem, e
  [09](09_feedbackJobs/09_reperti_analisi_statica_20260922.md) §2.4.
- **SP15 · `SensitiveValue`** — peso da stimare; sospeso dal 21/09 perché non c'era nessun consumatore misurato, e non
  sta in nessun altro backlog. Dettagli:
  [Round 1 della 24](../phases/24_privacyGlobal/plan-phase00PrivacyGlobalRound1-MaskingCore.prompt.md), passo 5.
- SP14, il Rebalancer, sta nella sezione D (riga 14 della 13).
