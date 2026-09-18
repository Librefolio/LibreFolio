# S3 — L3 «Sto venendo pagato per questo rischio?» · piano vivo

| | |
|---|---|
| Mandato | **S3 — livello 3** (round 2, fase 2) — l'unico full-stack |
| Worktree | `e-alfy-jubilant-winner` · ramo `e-alfy-s3-livello-3` |
| Baseline | `7d75a9c6c283af4bccf11f6bf380ffaa701d53eb` ✅ verificata — **identica a `e-alfy-risk-management-replan`** |
| Corsia | porta **6155** · data dir **`/tmp/librefolio-r2-s3`** |
| Coordinatore | sessione `0000738d-b7e0-4561-9454-cf5ab2c439ca` |

> Aggiornato **dopo ogni passo**, non alla fine.

---

## Passo 0 — Analisi, e il muro della modalità piano ✅ 2026-09-18

Analisi consegnata al coordinatore prima di qualunque riga di codice: cinque risposte,
quattro divergenze, sei richieste.

> **⚠️ Fuori pista — non ho potuto misurare in fase di analisi.** La modalità piano
> blocca ogni scrittura fuori dalla cartella di sessione, e `db populate` crea
> `/tmp/librefolio-r2-s3`. Quindi la prima consegna è arrivata al coordinatore
> **argomentata sul codice e non provata sui numeri**, e l'ho dichiarato in testa al
> messaggio invece di lasciarlo dedurre. La misura è il passo 1, non un dettaglio
> rimandato.

**Le cinque risposte, in breve** (per esteso nel messaggio al coordinatore):

1. **Il modo del beta** — la domanda giusta non è «quale modo per il beta» ma **quale
   perimetro per L3**: Sortino/Sharpe/volatilità vengono da `historical_kpi`, che
   supporta *solo* `historical` (`historical_kpi.py:85`), quindi spostare il solo beta
   crea **due perimetri taciuti nella stessa card**. Raccomandata la **Decisione B**
   (solo beta, entrambi i perimetri dichiarati, costo zero in file condivisi e in T3)
   con la **Decisione A** come proposta — A costa un file di T3, perché
   `risk-mocks.ts:45` dichiara `historical_kpi` per il solo `historical`.
2. **Per-asset** — σᵢ e rendimento **non** sono derivabili dai payload (da
   `marginal/component/percentage` σᵢ è un sistema non lineare). Ma
   `risk_contribution.py:66-71` **già costruisce la covarianza per-asset** e ne scarta
   la diagonale. Manca il solo rendimento annualizzato.
3. **`ScatterChart`** — copre il caso per intero, **zero consumatori oggi**, spec già
   registrato in `_frontend_utility.py:68`. Ambiguità decise: bolla ∝ peso **degli
   asset** (il portafoglio ha peso 1 per definizione), pesi **veri sul patrimonio
   netto**, **nessun punto per il contante**.
4. **Il selettore** — 🔴 la primitiva indicata dal briefing è sbagliata.
5. **I passi** — il passo 1 è misurare, e blocca il resto.

---

## Passo 1 — Misurare in corsia 6155 ✅ 2026-09-18

**Comandi**

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6155 --data-dir /tmp/librefolio-r2-s3 db populate --force --clean
# → ✅ Total records: 6679 — identico al numero post-fix di F1
```

Poi una sonda **di sola lettura** (file fuori dal repo, nella cartella di sessione)
che chiama il `RiskService` vero e il suo costruttore di contesto. Log completo:
`/tmp/libreFolio_s3_probe.log`.

> **Nota di metodo**: sonda a livello di servizio, non di router. F1 ha già provato al
> passo 9 che il router risponde `200` su queste due analitiche; quello che qui serve
> misurare è **come il contesto costruisce la serie**, ed è esattamente lo strato che
> il router non cambia. Dichiarato perché una sonda risponde per sé, non per il
> prodotto, finché non si dice dove è stata piantata.

**Finestra dichiarata**: A = `2025-09-18 → 2026-09-18` (365 giorni), B =
`2025-09-11 → 2026-09-18` (tutto lo storico). **Le due danno risultati identici**: i
prezzi partono dall'11 settembre, quindi entrambe le richieste vengono ritagliate sulla
stessa serie preparata. Utente `2` (`e2e_test_user`), benchmark `11` (MSCI World),
valuta `EUR`, portafoglio intero.

### ① Il beta nei due modi — la tesi del coordinatore è confermata

| modo | beta | correlazione | TE | IR | oss. | `return_basis` |
|---|---:|---:|---:|---:|---:|---|
| `historical` | **−0,007785** | **−0,019120** | 0,184071 | −0,132262 | 353 | `twrr` |
| `current_composition` | **+0,230739** | **+0,669035** | 0,138772 | −0,450659 | 360 | `current_composition_backtest` |

🔑 **Il numero che decide non è il beta, è la correlazione.** `−0,019` non è una
relazione debole: è **l'assenza di una relazione**. Un beta calcolato lì non è
impreciso, è *senza oggetto* — non c'è niente da misurare. A `+0,669` la relazione
esiste, e il beta la descrive.

### ② 🔴 Lo scarto fra i due perimetri è enorme, non cosmetico

I tre rapporti di L3, ricalcolati sulla **stessa** serie di backtest che darebbe il
beta `+0,231`:

| | `historical` (oggi) | `current_composition` | scarto |
|---|---:|---:|---:|
| volatilità | 0,068958 | 0,059025 | −14% |
| **Sharpe** | 0,826017 | **1,448143** | **+75%** |
| **Sortino** | 1,258917 | **2,155005** | **+71%** |
| rendimento annualizzato | +0,056104 | +0,087336 | — |

> **È questo che chiude la Decisione A contro la B.** Finché lo scarto era ignoto si
> poteva dire che mescolare i perimetri fosse un'imprecisione formale. Misurato, un
> Sortino `1,26` accanto a un beta `+0,23` sono **due mondi diversi stampati sulla
> stessa riga**, e il lettore non ha modo di accorgersene. Non è un dettaglio di
> etichetta: è la card che afferma due cose incompatibili.

### ③ Lo scatter è vivo — e dice qualcosa di vero

| punto | peso | volatilità | rendimento ann. |
|---|---:|---:|---:|
| Apple | 0,1470 | 0,2909 | **+0,5245** |
| Microsoft | 0,0234 | 0,3073 | −0,1011 |
| Tesla | 0,0343 | 0,2909 | +0,2599 |
| RE Loan Milano | 0,1860 | **0,0463** | +0,0526 |
| RE Loan Roma | 0,0919 | 0,0458 | +0,0465 |
| Bitcoin | 0,0192 | 0,8764 | −0,3896 |
| Ethereum | 0,0051 | **0,8932** | **−0,5188** |
| **MSCI World** ◇ | — | 0,1711 | +0,1427 |
| **Portafoglio** ⬤ | 1 | 0,0590 | +0,0873 |

Dispersione σ **0,046 → 0,893** (20×), rendimenti **−0,52 → +0,52**. Nessun
addensamento, nessun punto degenere: il grafico ha qualcosa da mostrare.

**E la CML non è decorativa.** Con `rf = 0` la pendenza per il portafoglio è
`0,0873 / 0,0590 = 1,48` (che è il suo Sharpe). Proiettata alla volatilità del
benchmark, la retta legge `0,253` contro il `+0,143` che il benchmark rende davvero:
**il benchmark sta sotto la retta**. La lettura «sopra la retta = pagato bene» risponde
alla domanda del livello al primo sguardo, senza pronunciare il nome della teoria.

**Controprova di coerenza**: la media pesata dei rendimenti per asset vale `+0,0877`
contro il `+0,0873` della serie di portafoglio. I due conti si chiudono — quindi i
punti e il punto-portafoglio vengono davvero dalla stessa misura.

### ④ Le mie misure contro quelle in circolazione

| | coordinatore | F1 | **io (corsia 6155)** |
|---|---:|---:|---:|
| beta `historical` | −0,0079 | −0,0035 | **−0,007785** (353 oss.) |
| beta `current_composition` | +0,2327 | +0,2280 | **+0,230739** (360 oss.) |
| TE `historical` | 0,1843 | — | **0,184071** |
| TE `current_composition` | 0,1386 | — | **0,138772** |
| `cash_weight` | «49 %» | 0,5089 | **0,493095** |

> **Le quattro cifre del coordinatore si riproducono**, allo scarto dell'ultima
> posizione e con conteggi di osservazioni diversi (350 / 353 / 357 / 360): la causa è
> **la finestra**, non un errore, come previsto. **E sul contante il briefing aveva
> ragione e io avevo sollevato un dubbio a vuoto**: `0,4931` è 49%, non 50,9%. Il
> `0,5089` di F1 veniva da uno stato del DB precedente al loro stesso fix. **Ritiro la
> divergenza ③**: l'avevo aperta perché due fonti discordavano, e la misura ha detto
> quale delle due.

> **⚠️ Fuori pista — la controprova a mano del coordinatore non si riproduce.** Il
> `+0,189` non l'ho ritrovato: la mia, sugli stessi giorni allineati, dà **esattamente
> il beta dell'analitica** (`+0,230739`, correlazione `+0,669035`). La differenza sta
> quasi certamente nei pesi — `current_buy_and_hold_returns` li lascia **derivare**
> lungo la finestra (è un buy-and-hold), mentre una controprova a pesi fissi dà un
> numero più basso. **Non è un difetto di nessuno dei due conti**: sono due domande
> («i pesi di oggi rigiocati» contro «i pesi di oggi, fermi»). Lo segnalo perché
> nel briefing quel numero è citato come *conferma* del secondo modo, e in realtà
> conferma il **verso** e non il valore.

> **Nota laterale, non mia da riparare**: `risk_contribution` dichiara
> `return_basis=price_only` anche in `current_composition`, perché riporta la base
> delle serie **per asset** (`risk_contribution.py:113`), mentre `comparison` nella
> stessa onda dichiara `current_composition_backtest`. Entrambe sono vere sul proprio
> oggetto. `backtestDeclared()` regge perché scorre tutti i risultati e basta un sì —
> ma chi un giorno leggesse *il primo* risultato dell'onda per sapere «che serie è»
> otterrebbe la risposta sbagliata.

**Tutti i risultati sono `partial`**, in entrambi i modi: in scope c'è l'asset `17`
(Test KRW) che non ha prezzi, quindi l'onda porta un `assets_excluded`. È atteso e già
mostrato dal pannello.

---

## Passo 2 — Il selettore che si accorciava ✅ 2026-09-18

**Una prop**, in un file mio: `dropdownPosition="auto"` su `AssetSelect` in
`L3Benchmark.svelte`.

> **Note implementazione**: la diagnosi del briefing era sbagliata nella primitiva ma
> giusta nel sintomo. Non serve riusare `Tooltip`: `SearchSelect` disegna già la lista
> a `position: fixed` calcolata a mano (`:169-177`), quindi **nessun `overflow` di un
> antenato c'entra**. Il difetto è che il default `bottom` non *taglia* la lista, la
> **accorcia**: `dynamicMaxHeight = maxBelow * ITEM_HEIGHT` (`:153-156`), e vicino al
> fondo pagina resta il pavimento di due voci. `auto` (`:158-166`) sceglie il lato con
> più spazio — «scendere finché la pagina ha spazio, e nel caso mostrarsi verso
> l'alto», parola per parola la richiesta del developer. Idioma già in uso in 9+ punti
> del repo.

**Verifica possibile**: prop tipata `'top' | 'bottom' | 'auto'` su
`AssetSelect.svelte:62`, inoltrata a `SearchSelect` · riga 232 caratteri contro
`printWidth: 300`, quindi Prettier non la riformatta · `git diff --check` pulito.

> **⚠️ Fuori pista — i cancelli statici del frontend non possono girare qui.**
> `frontend/node_modules` **non esiste** in questo worktree (e nemmeno
> `frontend/src/lib/api/generated.ts`, che è ignorato). Quindi:
>
> | comando | stato |
> |---|---|
> | `dev.py front format` (prettier) | ❌ non eseguibile |
> | `dev.py front check` (svelte-check) | ❌ non eseguibile |
> | unit vitest | ❌ non eseguibili |
> | `dev.py api sync` | ❌ non eseguibile — `cmd_api_client` lancia `npm run generate-api` (`dev.py:635-641`) |
> | pytest backend | ✅ disponibile, il venv condiviso risponde (la sonda del passo 1 ci ha girato) |
>
> **Non installo niente**: il mandato vieta `npm install/update/audit fix`, e `npm ci`
> richiede approvazione esplicita del coordinatore. **Riportato, non aggirato.** La
> modifica resta quindi *verificata per contratto e per forma, non da un cancello*, e
> lo dichiaro invece di scrivere «verde».

---

## Passo 3 — L'annualizzazione: avevo scelto la convenzione sbagliata ✅ 2026-09-18

Il coordinatore ha corretto la mia sonda: **aritmetica** (`media_periodale × fattore`),
non geometrica. **Citazioni verificate una per una sul codice di oggi**, prima di
adottarle — perché una correzione non è più esente dal controllo di ciò che corregge:

| riga | cosa dice |
|---|---|
| `service.py:907` | `annualization_factor = len(returns) * 365 / calendar_days` ✅ |
| `riskfolio_worker.py:203` | `annual_volatility = sqrt(period_variance * f)` ✅ |
| `riskfolio_worker.py:205` | `expected_annual_return = expected_period_return * f` — **aritmetico** ✅ |
| `metrics.py:203` | `excess_mean / volatility * sqrt(f)` — **media aritmetica** ✅ |

### La ragione è più forte dell'argomento che l'ha proposta — ed è dimostrabile

Con l'aritmetica, e `rf = 0`:

```
pendenza = (media · f) / (dev_std · √f) = (media / dev_std) · √f = Sharpe
```

**La pendenza della CML non *somiglia* allo Sharpe: è lo Sharpe.** Misurato, non
dedotto:

| | pendenza aritmetica | Sharpe | identiche? | pendenza geometrica | errore |
|---|---:|---:|:--:|---:|---:|
| `current_composition` | **+1,448143** | +1,448143 | ✅ `True` | +1,479630 | **0,0315 (2,2%)** |
| `historical` | **+0,826017** | +0,826017 | ✅ `True` | +0,813588 | 0,0124 (1,5%) |

Con la geometrica la retta passa per il punto ma **non è la retta di Sharpe**: la
lettura «sopra la retta = pagato bene per il rischio» perde il suo fondamento, e lo
perde in silenzio, perché il grafico resta plausibile. È la stessa forma del difetto
di `LineChart` descritto in `PRIMITIVE.md`: *non rotto, plausibile e sbagliato*.

### I punti rimisurati — il verdetto regge, i numeri no

| punto | peso | σ | **aritmetico** | geometrico | scarto |
|---|---:|---:|---:|---:|---:|
| Apple | 0,1470 | 0,2909 | **+0,4641** | +0,5245 | −0,060 |
| Microsoft | 0,0234 | 0,3073 | −0,0595 | −0,1011 | +0,042 |
| Tesla | 0,0343 | 0,2909 | +0,2732 | +0,2599 | +0,013 |
| RE Loan Milano | 0,1860 | 0,0463 | +0,0524 | +0,0526 | ~0 |
| RE Loan Roma | 0,0919 | 0,0458 | +0,0465 | +0,0465 | 0 |
| **Bitcoin** | 0,0192 | 0,8764 | **−0,1100** | **−0,3896** | **+0,280** |
| **Ethereum** | 0,0051 | 0,8932 | **−0,3327** | −0,5188 | +0,186 |
| MSCI World ◇ | — | 0,1711 | +0,1480 | +0,1427 | +0,005 |
| **Portafoglio** ⬤ | 1 | 0,0590 | **+0,0855** | +0,0873 | −0,002 |

✅ **Il verdetto sopravvive**, come previsto dal coordinatore: la CML alla volatilità
del benchmark legge **+0,2478** contro il **+0,1480** che il benchmark rende — **il
benchmark resta sotto la retta**. Il fatto era robusto; la pendenza no.

> 🔴 **Un effetto collaterale che va dichiarato nell'asse, non nascosto.** Lo scarto
> cresce con la volatilità — è il *volatility drag* — e su Bitcoin vale **28 punti
> percentuali**: l'aritmetica dice −11%, la geometrica −39%. **Chi ha tenuto Bitcoin
> ha vissuto il −39%.** L'aritmetica è giusta *come rendimento atteso*, che è la
> grandezza della geometria media-varianza, e sbagliata come risposta a «quanto ho
> guadagnato». Quindi l'asse Y **deve nominarsi «rendimento annualizzato atteso»**: un
> numero senza perimetro, su un asse, è un perimetro sbagliato ripetuto per ogni punto.

### Controprova di coerenza, rifatta nella nuova convenzione

Media pesata dei rendimenti aritmetici per asset: **+0,086400** contro **+0,085477**
della serie di portafoglio → scarto **0,000923** (1,1%). In geometrica era 0,46%.

> **Non è un peggioramento del conto: è la stessa deriva dei pesi, vista due volte.**
> `current_buy_and_hold_returns` lascia derivare i pesi lungo la finestra, quindi la
> media del portafoglio non è mai *esattamente* la media a pesi fissi. È la stessa
> causa che spiega il `+0,189` della controprova del coordinatore. Due indizi
> indipendenti che puntano allo stesso meccanismo valgono più di un conto che torna
> al centesimo.

---

## Passo 4 — Bootstrap del frontend, autorizzato ✅ 2026-09-18

`npm ci` in `frontend/` — **433 pacchetti dal lock**, nessun `install`, nessun
`update`, **nessun `audit fix`** (20 vulnerabilità segnalate e lasciate stare: non
sono mie da toccare). Poi `api sync`, in quest'ordine.

> **⚠️ L'ordine non è cosmetico**, e S2 l'ha pagato prima di me: un `api sync` lanciato
> *prima* di `npm ci` muore su `Cannot find package 'typescript'` e lascia i codec dei
> tool assenti → il `front check` successivo riporta decine di errori in file mai
> toccati. Io ho eseguito `npm ci → api sync → front check` e non l'ho incontrato.

## Passo 5 — B2: il backend per-asset ✅ 2026-09-18

**Forma approvata dal coordinatore: analitica nuova, non estensione di `risk_contribution`.**

| file | cosa |
|---|---|
| `services/risk/metrics.py` | `annualized_expected_return` — **aritmetica**, con l'identità nel docstring |
| `services/risk_plugins/asset_risk_return.py` | **nuovo** — `asset_risk_return`, `RISK_RETURN`, portfolio + `PORTFOLIO`/`CURRENT_COMPOSITION` |
| `services/risk_plugins/comparison.py` | `comparison_volatility` + `comparison_expected_annual_return`, **sui soli giorni comuni** |
| `services/risk_plugins/historical_kpi.py` | `supported_modes` += `CURRENT_COMPOSITION`, `2.1.0 → 2.2.0`, `method` onesto per base |
| `schemas/risk.py` | `RISK_RETURN`, `RiskReturnItem`, `RiskReturnOutput`, union + `__all__` |

> **Note implementazione — il punto del benchmark.** Lo scatter di §7.5 vuole anche il
> rombo, e il benchmark non è nell'onda di base: è una scelta *a domanda*. Invece di
> aggiungere una quinta analitica a domanda nel controller (file condiviso, quattro
> switch), i due campi stanno su `comparison`, che quel benchmark **già possiede**.
> Ogni punto arriva dall'analitica che possiede già la sua domanda.

**Verifica live** (sonda di sola lettura, corsia 6155), tutti e 7 gli asset coincidenti
col conto a mano del passo 3 a `1e-6`:

```
weights sum 0,506905 + cash 0,493095 = 1,000000 esatto
CML slope (rf=0) == lo Sharpe misurato
modo historical → unavailable / incompatible_mode  ✅
```

## Passo 6 — Card A e scatter ✅ 2026-09-18

`L3RiskAdjusted.svelte` riscritta su `RiskMetricCard` + `RiskCardGrid` (le primitive di
`PRIMITIVE.md`, non una griglia mia), più `ScatterChart` montato così com'è — **nessun
grafico nuovo**. Logica in `l3Helpers.ts` + `l3Helpers.test.ts`, secondo la convenzione
della casa.

> **Note implementazione — il ripiego, e perché il mock doveva cambiare.**
> `selectKpiWave` preferisce l'onda `current_composition` e ripiega sulla storica.
> Il ripiego serve davvero (backend più vecchi, scope asset), ma con il catalogo finto
> muto sul modo nuovo **l'E2E avrebbe esercitato per sempre il ramo di ripiego**: verde,
> misurando la strada che gli utenti non percorrono. Da qui il token in
> `risk-mocks.ts:45` (R2-18), a sole aggiunte.
>
> Il perimetro si legge da `metadata.mode` **del risultato scelto**, mai dall'array in
> cui stava: se un giorno i due non concordassero, ha ragione il payload.

**Decisioni dichiarate**: bolla ∝ peso **solo per gli asset** (il portafoglio ha peso 1
per definizione) · pesi **veri sul patrimonio netto, non rinormalizzati** · **nessun
punto per il contante**, che è un'assunzione di modello e non una misura · asse Y
**«rendimento annualizzato atteso»** + didascalia sul *volatility drag*.

## Passo 7 — 🔴 `api sync` esce 0 su un client che non compila ✅ 2026-09-18

`front check` dopo `api sync` → **2 errori dentro `generated.ts`**.

**Causa**: `frontend/scripts/fix-openapi-discriminators.mjs` tiene **due elenchi
hard-coded**. Un `kind` nuovo non registrato lì viene emesso come
`const RiskReturnOutput: z.ZodType<…>`, che perde i metodi di `ZodObject` e **rompe
`z.discriminatedUnion`**.

> 🔑 **E il cancello che avrebbe dovuto dirlo, tace: `api sync` è uscito `0`.** È il
> quarto membro di una famiglia già nota in questo round — ma il più insidioso, perché
> gli altri tre **omettono** e questo **certifica**. Due righe additive, ratificate dal
> coordinatore, che mi ha registrato come scrittore di quel file.

Dopo la registrazione: **`front check` → 0 errori**, 41 warning tutti preesistenti
(`GlobalSettingsTab`, `BrokerSharingPanel`), **nessuno nei miei file**.

## Passo 8 — I `DocsLink`: avevo previsto un difetto che non esiste ✅ 2026-09-18

I tre link rotti (`user/analysis/risk.md#…`) sono stati sostituiti nella riscrittura con
`financial-theory/technical-analysis/risk-metrics/{sortino-ratio,sharpe-ratio,volatility,beta-active-return}/`.

> **⚠️ Fuori pista — una deduzione plausibile e sbagliata, chiusa dalla misura.**
> `DocsLink` antepone la lingua (`/mkdocs/{lang}/{path}`), e
> `beta-active-return` esiste **solo come `.en.md`**. Ne avevo dedotto un 404 in
> italiano e stavo per chiedere una prop nuova su `RiskMetricCard`.
>
> **`mkdocs build` dice di no**: `mkdocs_static_i18n` genera la pagina in **tutte** le
> lingue, ripiegando sul contenuto predefinito — e il titolo italiano è perfino
> tradotto. **16 link su 16 risolvono** (4 pagine × en/it/fr/es), verificati come file
> esistenti in `site/`, non come percorsi plausibili.
>
> Il debito di traduzione della sola `beta-active-return` resta, ma è debito di
> contenuto, non un link rotto — e non è mio.

`mkdocs serve` **non è stato usato**: usa la porta fissa `6042`, fuori dal modello a
corsie. La prova è il build, che è più forte di un'occhiata.

## Passo 9 — Tolti i numeri vivi dai commenti ✅ 2026-09-18

Su vincolo del coordinatore (N sta riseminando il fattore comune: `portfolio_volatility`
+5,55 %, `diversification_ratio` −5,26 %, quota ETH ×9,5).

Avevo inciso le misure del passo 1 e 3 in sei punti fra docstring e commenti. **Sarebbero
diventate false restando persuasive.** Riscritti per portare *il fenomeno* e il suo
ordine di grandezza, con il rimando a questo file — che è datato, con corsia e finestra
dichiarate — al posto della cifra.

> 🔑 **L'identità `pendenza == Sharpe` invece resta scritta nel codice**, perché non è
> una misura: è algebra, e non la può smentire nessun dataset. **La distinzione fra le
> due è il criterio**: un commento può affermare ciò che è vero per costruzione, e deve
> rimandare per ciò che è vero per misurazione.

Spazzata di controllo su **tutti** i file modificati: nessuna cifra viva residua nei
miei commenti; quel che resta sono fixture iniettate dai test e dai mock, che è
esattamente la forma consentita.

---

## Passo 10 — I test, e due rossi che erano miei ✅ 2026-09-18

Backend delegati all'agente `test-author`, con corsia concessa e restrizioni esplicite.
**Nessun file nuovo** → nessuna registrazione backend richiesta. Frontend scritto da me:
`l3Helpers.test.ts`, 14 casi, **ogni cifra inventata nella fixture del caso**.

> **Note implementazione — i due rossi che l'agente ha lasciato aperti erano miei, e ha
> fatto bene a non toccarli.** Erano **cambi di contratto**, non rotture:
>
> | test | cosa asseriva | perché è cambiato |
> |---|---|---|
> | `test_risk_api::…lists_plugins` | `supported_modes == ['historical']` | ora `historical_kpi` serve anche la composizione attuale |
> | `test_risk_service::…leaves_twrr` | `method == "historical_close_returns"` | ora `current_composition_backtest` |
>
> Il secondo merita una riga in più. Una fetta di portafoglio chiesta in `historical`
> **non può** essere filtrata dal TWRR del report, quindi il backend la ricostruisce dai
> pesi di oggi — e `return_basis` lo diceva **già**. Era il solo `method` a chiamarla
> «close returns». **Due serie identiche non possono portare nomi di metodo diversi solo
> perché sono state raggiunte attraverso modi diversi**: l'ho allineato al basis invece
> di restringere la funzione al solo caso nuovo, che sarebbe stato il modo minimale di
> conservare l'incoerenza.

**Registrazione dello spec**: ⚠️ **non in `_frontend_utility.py`**, come indicato nel
kickoff — misurato: gli spec di `levels/` vivono in
`scripts/test_runner/_frontend_portfolio.py`, azione `risk-levels-unit` (`:117` e la
stringa `tests=`). Aggiunto lì.

### Cancelli

| comando | esito |
|---|---|
| `front-portfolio risk-levels-unit` | ✅ **102 passed** (4 file; erano 88) |
| `api risk` | ✅ **PASSED** (era 9/1) |
| `services risk-all` | ✅ **413 passed** (era 412/1) |
| `schemas risk` | ✅ **25 PASSED** |
| `check-orphans` | ✅ 80 + 213 + 207 raggiungibili |
| `lint` · `format` | ✅ puliti |
| `front format` · `front check` | ✅ **0 errori**, 41 warning preesistenti altrove |
| `mkdocs build` | ✅ + 16/16 link risolti |

> **⚠️ Fuori pista — il controllo dimensionale ha un punto cieco, e l'ho incontrato.**
> `scripts/test_runner/_frontend_portfolio.py` segna **+0 righe** pur essendo
> modificato: le due modifiche sono **dentro righe esistenti** (l'elenco dei file e la
> stringa `tests=`). `git diff --stat` lo conferma: `2 insertions, 2 deletions`.
>
> Il controllo dimensionale smaschera una troncatura, **non una sostituzione a parità di
> righe**. Va letto insieme a `--stat`, non al posto suo — quinto membro della famiglia
> «un cancello che passa non prova che il passaggio sia sano».

---

## Passo 11 — I punti dello scatter stanno sulla stessa base? ✅ 2026-09-18

Domanda del coordinatore, nata da una misura di N: `historical_kpi` in **scope asset /
modo `historical`** riporta **258** osservazioni dove `comparison` in **scope portfolio
/ `current_composition`** ne riporta **360** — e le due dichiarano la **stessa**
`analyzed_range`. Chi applica l'identità di manuale a due numeri così conclude che uno
dei due è sbagliato; **nessuno dei due lo è.**

Il rilievo mi toccava perché uso la σ del benchmark **due volte**: come ascissa del
rombo nello scatter, e accanto al beta nella card.

**Sonda di sola lettura, corsia `6155`, finestra richiesta `2025-09-18 → 2026-09-18`**
(risolta in `2025-09-24 → 2026-09-18`), utente 2, portafoglio intero, EUR:

| | benchmark **10** (S&P 500) | benchmark **11** (MSCI World) |
|---|---:|---:|
| `asset_risk_return` · osservazioni | 360 | 360 |
| `comparison` · osservazioni | 360 | 360 |
| `comparison.observations` (giorni comuni) | 360 | 360 |
| σ_b **pubblicata** da `comparison` | 0,171487851 | 0,171145870 |
| σ_b **implicita** in `ρ·σₚ/β` | 0,171487851 | 0,171145870 |
| differenza | 2,8 · 10⁻¹⁷ | **0,0** |

✅ **L'identità chiude alla precisione macchina su entrambi.** Il rombo, il punto
portafoglio e il beta stanno sugli stessi 360 giorni.

🔑 **E non è fortuna del dataset.** Il servizio **unisce l'asset di confronto alla
preparazione congiunta** (`comparison_dependency_asset_ids` entra in
`_prepare_asset_series`), quindi la serie primaria e quella del benchmark nascono sulle
**stesse date congiunte**: `comparison.observations == prepared.n_observations` **per
costruzione**. Due benchmark diversi lo confermano.

**Il difetto di N resta intero**: nasce dal confronto fra **due preparazioni**, non fra
due misure della stessa cosa. Il mio è il caso in cui la preparazione coincide — che
**delimita** il difetto invece di negarlo. Il commento in `l3Helpers.ts` dice ora perché
quel punto **non** va preso da `historical_kpi`.

> **⚠️ Fuori pista — la corsia era vuota, e la misura non era riproducibile senza
> ripopolare.** Le suite backend **ricreano il DB come proprio prerequisito**: dopo
> `services risk-all`, `api risk` e `schemas risk` la corsia aveva **0 utenti, 0 asset,
> 0 prezzi**, e la prima esecuzione della sonda ha riportato `n_observations=0` con
> output assenti. Ripopolata (`6679` record, identico), la σ del benchmark 11 è tornata
> **`0,171145870`**, cifra per cifra quella del passo 5.
>
> **Il valore identico è la prova che il ripopolamento è una ripetizione e non un altro
> mondo** — cioè che il seme è deterministico. Una misura presa prima di una suite non
> è riproducibile dopo **senza ripopolare**, e questo va detto a chiunque rimisuri.

> **Nota sul commento scritto in `l3Helpers.ts`**: il `19,49 %` misurato da N **non**
> compare come cifra. È una misura su questa fixture, e la regola adottata oggi dice
> che un commento *rimanda* per ciò che è vero per misurazione. Il commento nomina la
> conseguenza come **«circa un quinto»** e rimanda a questo file, che porta corsia,
> finestra e data. La forma resta quella richiesta — dire **perché non** è l'altra
> analitica — senza incidere una cifra destinata a muoversi con la risemina di N.
