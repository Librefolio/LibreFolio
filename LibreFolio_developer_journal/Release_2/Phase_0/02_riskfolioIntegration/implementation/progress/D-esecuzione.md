# D — piano di esecuzione

| | |
|---|---|
| Mandato | [`../D-frontend-primitive-e-card.md`](../D-frontend-primitive-e-card.md) — sola lettura |
| Branch | `e-alfy-risk-primitives-cards` |
| Baseline | `cc33120ebfbc61efe4c6178218ff8d64dd4adf47` ✅ verificata |
| Lane | porta `6243` · data dir `backend/data/test-risk-d` |
| Coordinatore | sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca` |
| Autorizzazione | relayata dal coordinatore sotto delega permanente del developer |

> Ordine scelto: **prima la divisione dello spec**, che è meccanica e sblocca metà di
> **K5**, così il coordinatore può creare **E** ed **F** mentre costruisco la card.

---

## Decisioni ereditate dall'analisi (chiuse dal coordinatore)

| # | Verdetto |
|---|---|
| **Q-D1** | Estendere `KpiDivergingFlowBar` — `testId`, colori, altezza, modalità valore-con-segno. **Additivo**, dashboard invariata |
| **Q-D2** | Destinazione `components/ui/display/` |
| **Q-D3** | Divisione **letterale** in 4 file. `openFirstAssetDetail` **dentro** `risk-asset-detail.spec.ts`; `risk-mocks.ts` **additivo** per E |
| **Q-D4** | `formatCurrencyAmount` **resta** — istruzione falsa ritirata dai brief D ed E |
| **Q-D5** | Nome della card: `RiskMetricCard` |

---

## Passi

- [x] 1. Creare questo piano vivo — *2026-09-18*
- [x] 2. Dividere `risk-analysis.spec.ts` in quattro file — *2026-09-18*
- [x] 3. Registrare i selettori nuovi in `_frontend_portfolio.py` — *2026-09-18*
- [x] 4. Provare che è «solo spostamento» — **provato staticamente, byte per byte**; la
      controprova a runtime è bloccata da un guasto d'ambiente (vedi *Fuori pista 3*) — *2026-09-18*
- [x] 5. Consegnare **K5 parte 1** (la divisione) al coordinatore — *2026-09-18*
- [x] 6. Spostare le due barre in `ui/display/` + i 2 import di `KpiSection` — *2026-09-18*
- [x] 7. Estendere `KpiDivergingFlowBar` in modo additivo — *2026-09-18*
- [ ] 8. Creare `RiskMetricCard` + il suo Vitest (via `test-author`) — componente fatto, test in corso
- [ ] 9. Gate statici e suite sulla lane `6243`
- [ ] 10. Consegnare **K5 parte 2** e dichiarare `FROZEN`

> **Note implementazione (passo 5+)**: sbloccato il seed `mathjax` dal coordinatore, la rete
> Asset Detail è stata rieseguita **a runtime**: `2 passed (6.8s)`. La divisione non è più solo
> byte-identica, è verde proprio dove conta — sui due test che dovranno dimostrare che E ed F
> non hanno toccato la pagina che hanno promesso di non toccare.

> **Note implementazione (passo 6)**: `mv` semplice, non `git mv`, per non mettere nulla in
> staging. Gli importatori erano esattamente i due previsti (`KpiSection.svelte:15-16`);
> ri-verificato con una `grep` esaustiva su `src` ed `e2e` prima di muovere. Le intestazioni
> dei due file ora dicono *perché* sono generici: erano parcheggiati in `dashboard/` e per
> questo nessuno li cercava.

> **Note implementazione (passo 7)**: estensione **additiva**. `depositPct`/`withdrawPct` da
> obbligatori diventano opzionali (allentamento, non rottura) e si aggiungono `signedPct`,
> `positiveColor`, `negativeColor`, `barHeight`, `layout`, `inlineColumns`, `valueClass`,
> `testId`. I default riproducono il rendering attuale. Il corpo della barra è stato estratto
> in due `{#snippet}` (`labelNode`, `track`) per non duplicare il markup fra i due layout.
>
> Una scelta di sicurezza degna di nota: **una coppia esplicita vince sempre su `signedPct`**.
> Se un chiamante passa solo `depositPct` e anche `signedPct`, il componente usa la coppia e
> ignora il valore firmato, invece di leggere silenziosamente l'altro campo. Una barra
> mezza-specificata deve rendere ciò che è stato scritto, non indovinare.

> **⚠️ Fuori pista 4 — una mia `edit` ha lasciato un `</div>` orfano.** Sostituendo il corpo di
> `KpiDivergingFlowBar` ho chiuso il blocco con `{/if}` mentre l'originale finiva con `</div>`:
> il file è rimasto con un tag di troppo e senza chiusura del condizionale. **Preso da Prettier**
> alla riscrittura — di nuovo un gate statico, di nuovo non un test. Seconda volta in un giorno
> che `front format` intercetta un errore strutturale prima che costi un ciclo di test: vale la
> pena eseguirlo *subito dopo* ogni modifica strutturale, non a fine passo.

> **Note implementazione (passo 2)**: la divisione è stata eseguita con `sed` su intervalli di
> riga misurati, non riscrivendo a mano: ogni corpo di test è uscito dal file originale e vi è
> rientrato identico. `risk-mocks.ts` ha ricevuto 10 `export` — l'unica modifica testuale al
> codice spostato. `openFirstAssetDetail` è finito dentro `risk-asset-detail.spec.ts` (vincolo
> Q-D3.1): `risk-mocks.ts` non nomina né `openFirstAssetDetail` né `goToAssetsPage`.

> **Note implementazione (passo 3)**: `front_portfolio_risk` è stato ristretto a Dashboard +
> Broker Detail e affiancato da `front_portfolio_risk_lab` e
> `front_portfolio_risk_asset_detail`. La `desc` del terzo selettore dice a chi legge `--list`
> che quel rosso è una scoperta, non una manutenzione.

> **⚠️ Fuori pista 1 — l'off-by-one nella mia stessa tabella.** Avevo misurato la fine di
> `openFirstBrokerRisk` a `:527`: è `:528`. L'estrazione `8,527p` ha quindi lasciato fuori una
> graffa di chiusura e `risk-mocks.ts` è nato sintatticamente rotto. **L'ha intercettato
> Prettier**, non un test: `SyntaxError: '}' expected. (575:1)`. È la ragione per cui il gate
> statico gira prima di quello a runtime — e la ragione per cui i confini di riga vanno
> ri-verificati sul codice, non ricopiati da una tabella. La tabella qui sotto è corretta.

> **⚠️ Fuori pista 2 — `front check` non guarda `e2e/`.** `frontend/tsconfig.json` ha
> `"exclude": ["e2e/**/*", "playwright.config.ts"]`. Un «zero errori in e2e» letto dall'output
> di `svelte-check` è quindi **vuoto**: non ha controllato nulla. Esiste
> `frontend/tsconfig.e2e.json`, che include `e2e/**/*.ts` — e `grep` su tutto il repo dice che
> **non lo usa nessuno**: né `dev.py`, né gli script, né la CI. Il controllo di tipo sugli spec
> E2E, in questo progetto, oggi non viene eseguito da nessun gate. L'ho eseguito a mano.
> *Non è materia di D*: lo segnalo e basta.

> **⚠️ Fuori pista 3 — il build frontend non parte, e non per causa mia.**
> `dev.py server --test` muore prima di Vite perché la cache delle risorse statiche è
> incompleta: `mathjax` non è scaricabile
> (`SSL: CERTIFICATE_VERIFY_FAILED ... Missing Authority Key Identifier`) e in un worktree
> fresco non esiste copia, perché `mkdocs_src/docs/javascripts/vendor/` è ignorato
> (`.gitignore:78`). Senza build non c'è E2E, quindi non c'è controprova a runtime — **per D,
> per E e per F allo stesso modo**. Rimando al coordinatore senza aggirarlo: non disattivo la
> verifica TLS, non copio il file da un altro checkout, non tocco `.gitignore` né
> `update_js_cache.py`.
>
> Da notare: `mathjax` è un asset **della documentazione** (`vendor_dir_key: "mkdocs"`,
> destinazione `mkdocs_src/…`), eppure la sua assenza fa fallire il build **dell'applicazione**.

---

## Evidenza

| Comando | Esito |
|---|---|
| `git rev-parse HEAD` | `cc33120e…` — coincide con la baseline |
| `npx playwright test --list` sui 4 file nuovi | `Total: 12 tests in 3 files` — `risk-mocks.ts` **non** raccolto |
| `npx playwright test --list` sul file originale (`git show HEAD:…`, ricollocato a pari profondità) | `Total: 12 tests in 1 file` |
| `diff` dei titoli normalizzati (file:riga rimossi) | **vuoto** — 12 prima, 12 dopo, zero differenze |
| `/tmp/libreFolio_d_prove_movement.sh` | 6 corpi di test `IDENTICAL` (31+8+58+10+20+98 = 225 righe), `openFirstAssetDetail` `IDENTICAL` (12), impalcatura mock `IDENTICAL` (554, a meno dei 10 `export`) |
| `dev.py front format` | i 4 file `(unchanged)` dopo la correzione di *Fuori pista 1* |
| `npx tsc --noEmit -p tsconfig.e2e.json` | 59 errori, **0 nei file di D**; tutti e 59 discendono da `generated.ts` assente, in file che D non ha toccato |
| `dev.py front check` (`svelte-check`) | 283 errori / 41 warning — **stessa causa**, e comunque cieco su `e2e/` (*Fuori pista 2*) |
| `dev.py test --test-port 6243 --data-dir backend/data/test-risk-d front-portfolio all` | ❌ `Shared backend exited during startup (code 1)` in 5 s — causa in *Fuori pista 3*, nessun test raccolto |
| `lsof -nP -iTCP:6243 -sTCP:LISTEN` | vuoto — la lane non ha mai aperto la porta |
| **dopo lo sblocco `mathjax`** — `dev.py test --test-port 6243 --data-dir backend/data/test-risk-d front-portfolio risk-asset-detail` | ✅ **`2 passed (6.8s)`** — la rete Asset Detail è verde a runtime |
| `dev.py front format` (dopo passi 6-8) | `KpiMetricBar` · `KpiDivergingFlowBar` · `RiskMetricCard` · `KpiSection` tutti `(unchanged)` |
| `dev.py front check` (`svelte-check`) | **`0 errors and 41 warnings in 2 files`** — i 283 errori precedenti erano *tutti* `generated.ts` assente, rigenerato dal build E2E. I 41 warning sono `on:click` deprecati in `BrokerSharingPanel.svelte` e `GlobalSettingsTab.svelte`, **non toccati da D** |
| `dev.py test … front-utility component-unit` | ✅ **`66 passed (66)` file, `1775 passed (1775)` test** — include `KpiSection.test.ts`: **la dashboard non si accorge dello spostamento** |

**Cosa NON è stato provato**: che i sei test *passino* dopo la divisione. Il gate a runtime non
è mai partito. Quello che è provato è più ristretto e più forte di un «verde»: che i byte
eseguiti siano gli stessi di prima, e che Playwright raccolga esattamente gli stessi dodici
titoli. Se i sei erano verdi prima, nessuna riga che li riguardava è cambiata.

---

## Baseline dei sei titoli — catturata a file intatto

Metà *prima* della prova di non-regressione, letta staticamente (zero runtime, porta
mai toccata):

```text
:587  dashboard renders base analytics, quality, warnings, sync and capability gate
:619  per-analytic unavailable state remains isolated
:628  asset global maps broker holdings and supports remove/add
:687  broker tab sends a single-broker portfolio subset and labels it
:698  asset detail preserves Overview and exposes Risk through its dedicated tab
:719  asset Risk runs typed scenarios, exposes replay audit and switches simulation view
```

> Si confrontano i **titoli**, non il conteggio: «6 = 6» passerebbe anche avendo
> riscritto un test al posto di un altro.

---

## Confini di riga misurati sul file originale

Servono a rendere la divisione verificabile invece che raccontata.

| Blocco | Righe | Va in |
|---|---:|---|
| import | 1-6 | tutti e quattro (sottoinsieme per file) |
| tipi → `openFirstBrokerRisk` | 8-**528** | `risk-mocks.ts` |
| **`openFirstAssetDetail`** | **530-541** | **`risk-asset-detail.spec.ts`** (vincolo Q-D3.1) |
| `brokerWithHoldings` → `selectedAssetIds` | 543-575 | `risk-mocks.ts` |
| commento «Earned parallel» + `configure` | 577-580 | i tre file spec |
| `beforeEach` | 583-585 | i tre file spec |
| test 1 — dashboard | 587-617 | `risk-analysis.spec.ts` (**E**) |
| test 2 — unavailable | 619-626 | `risk-analysis.spec.ts` (**E**) |
| test 3 — asset global | 628-685 | `risk-lab.spec.ts` (**F**) |
| test 4 — broker tab | 687-696 | `risk-analysis.spec.ts` (**E**) |
| test 5 — asset detail Overview | 698-717 | `risk-asset-detail.spec.ts` (🚫) |
| test 6 — asset Risk scenari | 719-816 | `risk-asset-detail.spec.ts` (🚫) |

---

## Contratti

| # | Verso | Stato |
|---|---|---|
| **K5** parte 1 — divisione dello spec | E, F | ✅ **consegnata e accettata** |
| **K5** parte 2 — primitive e card | E, F | ✅ **consegnabile** (vedi in fondo) |

### K5 parte 1 — la divisione dello spec E2E del rischio

`frontend/e2e/portfolio/risk-analysis.spec.ts` era **817 righe in un solo `test.describe`**,
con test di tre padroni diversi. Ora sono quattro file:

| File | Test | Proprietario | Selettore |
|---|---:|---|---|
| `risk-mocks.ts` | — | **D**, poi **additivo per E** | non raccolto (`testMatch` prende solo `*.spec.ts`) |
| `risk-analysis.spec.ts` | 3 — dashboard, unavailable, broker tab | **E** | `front-portfolio risk` |
| `risk-lab.spec.ts` | 1 — asset global | **F** | `front-portfolio risk-lab` |
| `risk-asset-detail.spec.ts` | 2 — Overview, scenari | **nessuno** 🚫 | `front-portfolio risk-asset-detail` |

**Tre clausole che valgono quanto la divisione stessa:**

1. **`risk-mocks.ts` è additivo.** E può aggiungere; non può togliere né rinominare ciò che
   la rete importa (`installRiskMocks`, `waitForRiskCatalog`, `RiskRequest`). F lo *consuma*
   e non lo possiede: se gli serve una modifica, la chiede.
2. **`risk-asset-detail.spec.ts` non si adatta.** Asset Detail è parcheggiata (D8, D47) e deve
   uscire dal ridisegno identica. Quei due test sono l'unica cosa che lo dimostrerà (D82). Se
   diventano rossi, si indaga la pagina, non l'asserzione. Adattarli cancella la prova.
   `openFirstAssetDetail` vive lì dentro, non in `risk-mocks.ts`, per tenere minima la
   superficie condivisa col ridisegno.
3. **`resultFor` è un mock che invecchia in silenzio** (`risk-mocks.ts`, ex `:210-462`).
   Congela la forma del payload. Quando **A** consegna K1 e **N** consegna K8, quella forma
   cambia e il mock resta indietro: **non fallisce, rassicura.** Va riallineato da chi
   modifica il contratto, non scoperto da chi eredita il rosso.

---

## Passo 6-8 — primitive promosse, card, e i tre spec — ✅ 2026-09-02

> **Note implementazione**: le due barre sono uscite da `components/dashboard/` e sono
> entrate in `components/ui/display/`. `KpiDivergingFlowBar` ha guadagnato in modo
> **additivo** `signedPct`, `positiveColor`, `negativeColor`, `barHeight`, `layout`,
> `inlineColumns`, `valueClass`, `testId`, più gli snippet interni `labelNode`/`track`.
> `RiskMetricCard` è nuova. I due import di `KpiSection.svelte` (`:15`, `:16`) sono le
> uniche righe toccate nel chiamante esistente.

### La prova che la dashboard non è cambiata

Ogni literal sostituito nel markup è diventato una prop il cui **default è il valore
identico**: `h-1.5` → `barHeight`, `bg-green-500 dark:bg-green-400` → `positiveColor`,
`bg-red-400 dark:bg-red-500` → `negativeColor`, e il layout impilato è il ramo `{:else}`.
Il `diff` contro `HEAD:frontend/src/lib/components/dashboard/*.svelte` non mostra nessun
altro cambiamento di comportamento. A runtime lo conferma `KpiSection.test.ts`, che passa
dentro la suite completa senza una riga modificata.

### I tre spec, e perché non mi sono fidato del verde

| File | Test |
|---|---:|
| `ui/display/KpiMetricBar.test.ts` | 9 |
| `ui/display/KpiDivergingFlowBar.test.ts` | 11 |
| `ui/display/RiskMetricCard.test.ts` | 13 |

Tutti e tre sono passati **al primo colpo**, che è esattamente il momento in cui un test
non va creduto. Ho quindi **mutato il componente** e preteso il rosso:

| Mutazione | Esito preteso | Esito osservato |
|---|---|---|
| `clampPct` senza `Number.isFinite` (FlowBar) | rosso sui 2 test NaN | `AssertionError: expected '' to be '0%'` ×2 |
| `clampPct` senza `Number.isFinite` (MetricBar) | rosso sul test NaN | `AssertionError: expected '' to be '0%'` |
| `{#key loading}` attorno al wrapper della card | rosso **solo** sull'identità di nodo | `expected <p …(2)></p> to be <p …(2)></p>` — 1 fallito, 12 passati |

La terza è la più stringente: `{#key}` lascia markup, classi e testo **identici** e cambia
*solo* l'identità del nodo. Un test che passasse anche così non starebbe dimostrando nulla.
Ne è fallito esattamente uno, e gli altri dodici hanno continuato a passare — cioè misurano
altro, senza sovrapposizioni.

Dopo ogni mutazione il file è stato ripristinato da copia e verificato con `diff` (`component
identical to pre-mutation backup`).

> **⚠️ Fuori pista 5 — il selettore sbagliato, scoperto dalla mutazione.**
> Il primo helper cercava i riempimenti con `div[style*="width"]`. Sotto mutazione il rosso
> è arrivato, ma con il messaggio sbagliato: `Expected exactly 2 fill elements, found 1`.
> Il motivo è istruttivo: Svelte imposta la larghezza via `style.setProperty`, e cssstyle
> **rifiuta `NaN%`**, quindi l'attributo `style` resta vuoto e l'elemento **esce dalla query
> stessa**. Un test che seleziona per la proprietà che sta verificando perde l'elemento
> proprio nel caso che deve descrivere. Helper riscritto su classi strutturali
> (`div.absolute.rounded-l-full`): ora il rosso dice `expected '' to be '0%'`, che è il
> sintomo reale — *la dichiarazione non è mai atterrata*.

> **⚠️ Fuori pista 6 — una guardia che non era una guardia.**
> Avevo messo `Number.isFinite` anche su `clampedMarker` di `KpiMetricBar` e stavo per
> consegnarla come «guardia + test». La mutazione ha detto altro: **il test resta verde**
> anche togliendola. Il motivo è che il template ha già `clampedMarker > 0`, e **ogni
> confronto con `NaN` è falso**, quindi il caret non veniva comunque disegnato. La guardia
> è quindi una **chiarificazione, non una correzione**. Il commento nel componente la
> descriveva come se proteggesse da un difetto reale: corretto, perché è la stessa classe
> del docstring bugiardo di D51. Il test è rimasto, dichiarato per quello che è — un pin di
> comportamento, non un acchiappa-regressioni.

> **⚠️ Fuori pista 7 — `head` che uccide il produttore.**
> `dev.py front format 2>&1 | tee log | grep | head -40` è morto a metà: `head` chiude la
> pipe, `tee` e `prettier` prendono SIGPIPE e la corsa si interrompe. Il log sembrava
> completo (505 righe, tutte `(unchanged)`) ma **non conteneva un solo file `e2e/`**. Il
> `tee` prescritto dalle istruzioni serve a non ri-eseguire, non a sopravvivere a `head`:
> su un produttore lungo si redirige su file e si legge *dopo*. Rilanciato pulito: 768 file,
> 98 `e2e/`, exit 0.

> **⚠️ Fuori pista 8 — l'agente delegato non ha prodotto nulla.**
> Il `test-author` delegato è rimasto `running` per ~39 minuti con **41 tool call e 0 turni**,
> senza scrivere un file. I tre spec li ho scritti io. Gli ho poi mandato uno *stand down*
> esplicito: se si fosse svegliato avrebbe sovrascritto lavoro già verificato per mutazione.

### Cancelli eseguiti

| Comando | Esito |
|---|---|
| `dev.py front format` | exit 0 — 768 file, tutti `(unchanged)` |
| `dev.py front check` | exit 0 — **0 errori**, 41 warning in 2 file (invariato dalla baseline, nessuno mio) |
| `dev.py test --test-port 6243 --data-dir backend/data/test-risk-d front-utility component-unit` | exit 0 — **69 file / 1808 test** |

La baseline era **66 file / 1775 test**. Il delta è **+3 file / +33 test**, che è esattamente
`9 + 11 + 13`: ho aggiunto i miei e non ho rotto nessuno degli altri.

`lsof -nP -iTCP:6243 -sTCP:LISTEN` → nessun listener.

---

## K5 parte 2 — le primitive promosse e la card metrica

### Dove sono finite

| Prima | Adesso |
|---|---|
| `components/dashboard/KpiMetricBar.svelte` | `components/ui/display/KpiMetricBar.svelte` |
| `components/dashboard/KpiDivergingFlowBar.svelte` | `components/ui/display/KpiDivergingFlowBar.svelte` |
| — | `components/ui/display/RiskMetricCard.svelte` *(nuova)* |

`KpiSection.svelte` è l'unico chiamante preesistente e ha cambiato **solo i due import**.
Le barre sono retrocompatibili: tutte le prop nuove sono opzionali e i default riproducono
il rendering della dashboard alla lettera.

### `KpiDivergingFlowBar` — due modi di alimentarla

- `depositPct` / `withdrawPct` — due magnitudini indipendenti (la dashboard).
- `signedPct` — **una** magnitudine con segno, −100..100. Positivo riempie a destra,
  negativo a sinistra. È la forma giusta per un contributo al rischio o un peso attivo.

La coppia esplicita **vince sempre**: chi passa un flusso *e* `signedPct` ottiene il flusso
che ha scritto e uno zero dall'altra parte. La barra rende ciò che è stato chiesto, non ciò
che si potrebbe dedurre.

Presentazione, tutta opzionale: `positiveColor`, `negativeColor`, `barHeight`, `valueClass`,
`testId`, e `layout: 'stacked' | 'inline'` con `inlineColumns` per il layout a tre celle
(etichetta │ barra │ valore) delle tabelle dense.

### `RiskMetricCard` — la firma

```
label, technicalName?, value?, numericValue?, formatValue?, caption?,
sentiment? ('positive' | 'negative' | 'neutral' = 'neutral'),
docsPath?, loading? = false, testId?, submetrics?: Snippet, sparkline?: Snippet
```

Testid derivati da `testId`: `-label`, `-technical`, `-value`, `-caption`, `-accent`,
`-skeleton`, `-docs`, `-sparkline`.

- `sentiment` neutro è il **default**, e non disegna la striscia d'accento: una metrica di
  rischio spesso non è né buona né cattiva, e colorarla comunque è un'opinione inventata.
- `sparkline` va riempita **solo dove una serie esiste davvero**. Su Dashboard e Broker
  Detail una serie rolling di portafoglio non esiste in nessun punto del codice —
  `SignalDomain` ha due soli valori, ASSET e FX — quindi lì lo slot resta vuoto, ed è
  corretto, non mancante (D18).

### ⚠️ La garanzia di non-salto è **parziale**, e l'altra metà è vostra

La card tiene l'elemento del valore **montato** durante il caricamento e lo nasconde con
`class:invisible`, sopra uno scheletro in posizione assoluta. Non è una sfumatura stilistica:
le card 2 e 3 di `KpiSection` usano `{#if loading}{:else}` e **spostano il layout**. Qui il
nodo è lo stesso oggetto DOM prima e dopo, e il test lo dimostra per **identità di nodo**,
non per somiglianza di classi.

**Ma la garanzia copre la sola riga del valore.** `caption`, `sparkline` e `submetrics`
stanno dietro `{#if}` **dentro** il wrapper invisibile. Quindi:

> **Regola operativa per E e F:** chi fornisce `caption`, `sparkline` o `submetrics` deve
> fornirli **anche durante `loading`** — vuoti o come segnaposto — non solo dopo. La card
> non può riservare spazio per un contenuto che non le è mai stato dato, e il salto
> comparirebbe **esattamente sui pannelli più pieni**, cioè L1 e L2.

### Nessun `aria-busy`

Deliberatamente non introdotto: è un segnale di prodotto che nessuno ha chiesto, e un
mandato di primitive non è il posto dove allargare l'ambito senza che nessuno decida.
**L'E2E si ancora all'assenza di `-skeleton`.**

### La guardia sul non-finito

Entrambe le barre mandano a `0` qualunque percentuale non finita. Il motivo è che
`width: NaN%` **non è CSS valido**: la dichiarazione viene rifiutata e il riempimento resta
alla larghezza precedente — cioè mostra un dato vecchio come se fosse nuovo. La dashboard
non ci arrivava perché divide per `|| 1`; **i pannelli di rischio non hanno quella guardia
e non hanno motivo di sapere che serve.** È la promozione stessa a rendere raggiungibile un
difetto che prima non lo era.
