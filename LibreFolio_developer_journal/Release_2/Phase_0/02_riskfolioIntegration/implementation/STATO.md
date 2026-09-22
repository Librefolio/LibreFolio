# Stato della campagna — registro del coordinatore

> **Documento del coordinatore.** Nessun mandato lo scrive. È il registro durevole che
> il contratto `release-coordinator` richiede: se il contesto si azzera, è da qui che si
> riprende.

**Baseline della campagna**: `cc33120ebfbc61efe4c6178218ff8d64dd4adf47`
*(«docs(journal): plan risk execution as 11 mandates», 17 Set 2026)*

**Coordinatore**: worktree `e-alfy-ideal-eureka` · branch `e-alfy-risk-management-replan`
· lane `6250` + `backend/data/test-risk-coord`

---

## 1. Le sessioni attive

| Mandato | Worktree | Branch | Lane | `node_modules` | Stato |
|---|---|---|---|---:|:---:|---|
| **A** | Oracolo e migrazione | `e-alfy-improved-meme` | `e-alfy-risk-oracle-math-migration` | 6240 | — | 🟢 **autorizzato** · implementazione |
| **B** | Tassonomia e benchmark | `e-alfy-legendary-succotash` | `e-alfy-risk-taxonomy-benchmark` | 6241 | ✅ 639 M | 🟢 **autorizzato** · implementazione |
| **D** | Primitive e card | `e-alfy-solid-engine` | `e-alfy-risk-primitives-cards` | 6243 | ✅ 640 M | 🟢 **autorizzato** · implementazione |
| **H** | Monte Carlo | `e-alfy-friendly-bassoon` | `e-alfy-h-monte-carlo` | 6247 | — | 🟢 **autorizzato** · implementazione |
| **I** | Documentazione | `e-alfy-shiny-broccoli` | `e-alfy-risk-analysis-documentation` | — | — | 🟢 **autorizzato** · implementazione |
| **C** | Affettamento | `e-alfy-crispy-journey` | `e-alfy-risk-c-portfolio-slicing` | 6242 | — | 🟢 **autorizzato** |
| **N** | Acquisizioni | `e-alfy-miniature-train` | `e-alfy-risk-n-backend-acquisizioni` | 6248 | — | 🟢 **autorizzato** |
| **E** | Quattro livelli | `e-alfy-vigilant-adventure` | *(da rinominare)* | 6244 | ✅ | 🔵 analisi |
| **F** | Laboratorio | `e-alfy-super-dollop` | `e-alfy-risk-asset-global-lab` | 6245 | ✅ | 🔵 analisi |
| **G** | Colori allocazione | `e-alfy-solid-couscous` | `e-alfy-risk-g-allocation-colors` | 6246 | ✅ 645 M | 🔵 analisi |
| **J** | Chiusura | — | — | 6249 | da fare | ⏳ ondata 3 — **ultimo** |

## 1.1 Le cinque analisi — cosa hanno trovato

⚠️ **Tutti e cinque i mandati hanno trovato presupposti falsi nei propri brief.** Non è
un incidente: è il cancello analisi-prima che funziona. Riepilogo verificato dal
coordinatore, uno per uno.

| Mandato | Scoperte | Le più gravi |
|---|---:|---|
| **A** | 2 bloccanti + 2 presupposti falsi | M1 richiede i 4 `rolling_*.py` (lambda non vettorializzabili) · K1 richiede 2 file di `risk_plugins/` · **M2 cambia anche il VaR** · «0,27%» era una media, non un limite |
| **B** | 4 falsi + 1 contraddizione | **F14**: Q12 si contraddiceva su K2 → **D85** · `VARCHAR(14)` contro `ETF_REAL_ESTATE` (15) · i punti che raggruppano sono **dieci**, non sei · «seleziona tutti» farebbe **sparire** gli ETF azionari |
| **D** | 3 imprecisioni | `formatCurrencyAmountPlain` **non è un sostituto** · `KpiDivergingFlowBar` **non è drop-in** · 9 contenitori piatti su 11, non 5 su 9 |
| **H** | 7 presupposti falsi | **GJR-GARCH non calibrabile da QuantLib** → D88 · `schemas/risk.py` ha un **quarto** scrittore → D92 · NumPy diventa motore di produzione |
| **I** | 3 falsi | **`check-links` è cieco ai `DocsLink`** → D89 · la famiglia drawdown è già documentata (14 pagine, non 15) · `volatility.en.md` documenta √252 mentre il codice fa annualizzazione osservata |

### 1.2 L'autorizzazione — come è stata data, e cosa non copre

Il developer, interpellato sulle cinque analisi, ha risposto:

> *«The user is not available to respond and will review your work later. Work
> autonomously and make good decisions.»*

**È una delega permanente, non una firma su cinque analisi specifiche**, e ai cinque
mandati è stata trasmessa così — parole vere, non un sign-off travestito.

Il coordinatore ha autorizzato sotto quella delega, con un criterio: **il rischio è
basso e reversibile** — branch e worktree dedicati, nulla committato, nulla fuso, nulla
in produzione, e il developer rivede prima di qualunque commit.

> ## 🔑 L'unica cosa che NON è stata autorizzata, e non poteva esserlo
>
> **La promozione di `arch` a dipendenza diretta** (H-Q1). Cambia `Pipfile` e rigenera
> il lock, cioè tocca **l'ambiente Python condiviso da tutte le lane attive** — sette di
> questa campagna più quattro di un'altra. Il contratto lo riserva al developer **a lane
> congelate**: farlo mentre sette agenti lavorano è il modo di rompere sette cose per
> guadagnarne una.
>
> → GJR-GARCH esce dalla v1 e va in `TODO_FUTURI.md` con la misura di H scritta per
> esteso. Tutto il resto di H procede.

**Decisioni prodotte**: **D85**-**D92**. Brief corretti: `A`, `B`, `D`, `E`, `H`, `J`,
`07` §6, e `README` §2.1, §2.2, §2.9, §2.10.

Legenda stato: 🔵 analisi in corso · 🟡 in attesa di firma · 🟢 implementazione
autorizzata · ❄️ `FROZEN` · ✅ integrato

⚠️ **Le altre quattro worktree sulla macchina non sono di questa campagna** e usano
altre bande: `e-alfy-crispy-pancake`, `e-alfy-friendly-dollop`, `e-alfy-literate-lamp`,
`e-alfy-turbo-fortnight`. Non toccarle, non usare le loro porte.

---

## 2. Verifiche eseguite alla creazione

Per tutti e cinque i figli dell'ondata 1, il 17 Set 2026:

| Verifica | Comando | Esito |
|---|---|---|
| Baseline coincidente | `git -C <worktree> rev-parse HEAD` | ✅ `cc33120eb` per tutti e cinque |
| Agente nel commit | `git -C <worktree> ls-files .github/agents/coordinated-workstream.agent.md` | ✅ presente in tutti |
| Mandati ereditati | `ls implementation/*.md` | ✅ 12 file in ognuno |
| Bootstrap atteso | `.env` assente, `node_modules` assente | ✅ come previsto |
| `npm ci` per i frontend | dal lock esistente, **uno per volta** | ✅ B 639 M · D 640 M, entrambi `exit=0` |
| Disco dopo il bootstrap | `df -h` | 38 GiB liberi su 460 (91%) |

Log: `/tmp/libreFolio_npmci_B.log`, `/tmp/libreFolio_npmci_D.log`.

---

## 3. I contratti

Stato dettagliato in [`contracts/README.md`](./contracts/README.md).

| # | Da | A | Stato |
|---|---|---|---|
| K1 | A | E | ⏳ atteso — **prima di M2**, è l'unica parte di A che blocca qualcuno |
| K2 | B | G | ⏳ atteso |
| K3 | B | E, F | ⏳ atteso |
| K4 | C | E | ⏳ mandato non ancora creato |
| K5 | D | E, F | ⏳ atteso — **sblocca l'ondata 2** |
| K6 | H | E | ⏳ atteso |
| K7 | I | E, F, H | ⏳ atteso — **primo tempo, subito** |
| K8 | N | E | ⏳ mandato non ancora creato |

---

## 4. Il cancello aperto adesso

> ## 🔑 Cancello **analisi-prima**, a firma del developer.
>
> I cinque figli consegnano un'**analisi di implementazione**, non codice. Il
> coordinatore può respingere o chiedere revisioni liberamente, ma può **approvare solo
> dopo il sign-off esplicito del developer**, e alla prima autorizzazione si continua in
> `interactive` — mai `autopilot`.

Quando le cinque analisi sono firmate: si creano **C** e **N** (ondata 1.5), e appena
**D** consegna K5 si creano **E** ed **F**; appena **B** consegna K2, **G**.

---

## 5. Cosa il coordinatore non fa
Non scrive il codice di un figlio, non gira la sua suite, non entra nel suo worktree se
non in lettura. E **mai** `git commit`, `merge`, `rebase`, `push`, `reset`: la storia la
muove il developer.

La lane `6250` serve solo ai gate trasversali e alla revisione combinata.

---

## 6. ⚠️ Le notifiche «paused waiting for approval» — regola corretta il 18 Set 2026

**La prima versione di questa nota era sbagliata, e sarebbe costata caro.** Diceva che
quelle notifiche *«si sciolgono da sole»*, generalizzando da quattro casi (D, H, I, A) in
cui la sessione risultava già `interactive` e `busy` al controllo successivo.

Poi **C e N sono rimasti bloccati davvero**: `awaiting_plan_approval: true`, con
`pending_plan` popolato e `recommended_action: exit_only`. Se avessi applicato la mia
stessa regola avrei lasciato due mandati fermi a tempo indeterminato, **convinto di
avere una spiegazione**.

> ## 🔑 Una regola costruita su quattro osservazioni concordi resta un'ipotesi.
>
> I quattro casi «si risolvono da soli» erano veri. La generalizzazione *«quelle
> notifiche non sono mai reali»* no — e la differenza fra le due non si vedeva finché
> non è arrivato il quinto caso.

### La regola che vale

**Non dedurre lo stato: leggerlo.**

```text
get_sessions_status → summary.awaiting_plan_approval
```

- **`0`** → nessuno è bloccato, la notifica era vecchia: non fare nulla;
- **`> 0`** → **qualcuno è bloccato davvero**: individua chi, leggi il suo
  `pending_plan.summary`, e rispondi con `respond_to_session_plan`.

⚠️ Il campo `pending_plan` compare **solo** quando il blocco è reale: è il
discriminante, e non costa nulla guardarlo.

### La scorciatoia, verificata il 18 Set 2026

`get_sessions_status` restituisce **tutte** le sessioni del sistema — un payload grosso,
e con undici mandati lo si chiama spesso. Ma esiste un discriminante più economico:

> **`respond_to_session_plan` è essa stessa una sonda sicura.** Se non c'è un piano
> pendente fallisce pulitamente:
>
> ```text
> invalid argument: Session <id> has no plan awaiting a decision
> ```
>
> Nessun effetto collaterale, nessuno stato modificato.

Quindi, **quando non si ha motivo di respingere** — cioè quando il mandato è già
autorizzato nel merito e la notifica riguarda solo il gate formale — si può approvare
direttamente: o sblocca, o dice che non c'era nulla da sbloccare.

⚠️ **Non vale quando il piano va letto davvero**: alla prima autorizzazione, o quando il
contenuto potrebbe meritare un rifiuto, si legge `pending_plan.summary` prima di
rispondere. La scorciatoia serve ai gate formali, non a saltare la revisione.

⚠️ E vale il contratto: alla **prima** autorizzazione a implementare si sceglie
`interactive`, **mai** `autopilot` né `autopilot_fleet` — anche quando il piano propone
`exit_only` come raccomandato.

---

## 9. 🔴 ESCALATION — non è un difetto dei contratti, è **tutto il lavoro non committato**

Il 18 Set 2026 lo stesso difetto si è presentato **tre volte**, e ogni volta un figlio ha
ragionato **correttamente su fatti vecchi**:

| # | Cosa era invisibile | Chi ne ha pagato il prezzo | Conclusione sbagliata che ne è seguita |
|---|---|---|---|
| 1 | `contracts/K*.md` | **E** | «i contratti non esistono» |
| 2 | Decisioni **D85-D92** | **E** | *«D91 non esiste: `04` si ferma a D84»* — **vero nella sua baseline** |
| 3 | La riparazione di `dev.py` di **I** (scope 1c, `:1143`) | **E** | *«il gate non vede i `DocsLink`, i 18 slug lasceranno il contatore fermo»* — **falso**, ma deducibile solo dal codice vecchio |

> ## 🔑 La causa è una sola: il coordinatore **non può committare**, e ogni figlio ragiona da `cc33120eb`.
>
> Più la campagna avanza, più lavoro **verificato** vive fuori dalla baseline comune. I
> figli fanno la cosa giusta — verificare sul codice invece di credere al coordinatore —
> e **proprio per questo** arrivano a conclusioni sbagliate.
>
> Non è un difetto di disciplina: è un difetto di **topologia**. Il relay inline lo
> tampona per i contratti; **non lo tampona per il codice**.

⚠️ **Azione richiesta al developer: committare.** Da quel momento i figli leggono invece
di ricevere a mano, e la classe di errore sparisce.

Finché non accade, vale la regola di mitigazione: **ogni fatto che il coordinatore
riporta va accompagnato dalla sua fonte esatta** — file e riga — perché il destinatario
non può verificarlo da sé. Un'affermazione senza indirizzo, in questa topologia, è
indistinguibile da un errore.

---

## 10. Stato dei mandati — 18 Set 2026, aggiornamento serale

| | Mandato | Stato | Cancelli |
|---|---|---|---|
| **A** | oracolo e migrazione | A2 chiuso, su **A3 (M2)** | `risk-oracle` 39 · `risk-all` 173 · `schemas risk` 14 |
| **B** | tassonomia e benchmark | ✅ **FROZEN** — **36 scoperte** | 14 comandi verdi · `asset-unit` 256 · `risk-all` 138 · `db all` 10/10 · migrazione **003** |
| **C** | affettamento | ✅ **FROZEN** | `lint` · `schemas` 16 · `risk-all` 146 · **`api risk` 10** |
| **D** | primitive e card | ✅ **FROZEN** | `front format` 768 · `front check` 0 err · `component-unit` **1808** |
| **E** | quattro livelli | E1 consegnato, su `RiskLevelsPanel` | `front check` = baseline · `risk-controller-unit` 11 · `risk` 6 |
| **F** | laboratorio | autorizzato, parte dalle superfici indipendenti | — |
| **G** | colori allocazione | analisi verificata, **autorizzato**, implementa | brief regge: **10 numeri di riga su 10 corretti** |
| **H** | Monte Carlo | ✅ **FROZEN** | `risk-simulation` 29 · `risk-workers` 11 · `quantlib-runtime` 2 · `risk-all` 148 |
| **I** | documentazione | onda 2 | 225 link, 0 rotti |
| **N** | acquisizioni | ✅ **FROZEN** | `risk-all` **166** · `api risk` 10 · `schemas` 14 · lint |
| **J** | chiusura | **non creato** — si crea per ultimo (D46) | — |

**Tre `FROZEN`**: C, D, N. Tutti e tre con `api risk` verde, che prima della riparazione del bootstrap nessuno poteva eseguire.

### 10.1 ⚠️ Ordine obbligato dei gate backend — trovato da C in tre esecuzioni

```
services risk-all  →  db populate --force --clean  →  api risk
```

**`services risk-all` ricrea un database pulito** (*«Clean test database created»*) **e cancella le fixture di `api risk`**, e il runner **non** ripopola. Chi li esegue al contrario vede un rosso che non ha nulla a che fare col proprio codice. **Riguarda soprattutto l'integrazione**, dove un falso rosso costa molto più che in un mandato.

### 10.2 Esclusioni permanenti dal checkpoint — ora **nove**

Ai 7 file riformattati da `black` alla baseline si aggiungono **2 PNG non tracciati e non gitignorati**:

```
mkdocs_src/docs/static/icons/asset-types/commodity.png
mkdocs_src/docs/static/icons/asset-types/real-estate.png
```

**Vengono dalla riparazione di bootstrap del coordinatore**, non da un mandato — segnalati indipendentemente da **C**, **D**, **E** e **N**. Ogni gate `api` li rigenera, perché `server --test` ricostruisce il frontend. Appartengono a **B**, che possiede la tassonomia che li referenzierà. **Un `git add -A` distratto li porterebbe dentro.**

### 10.3 La famiglia «un controllo che ha smesso di controllare» — **sette** istanze

| # | Istanza | Chi |
|---|---|---|
| 1 | Il CVaR sbagliato per un anno | preesistente |
| 2 | `check-links` cieco a ogni `DocsLink` | I |
| 3 | Il mock stantio (`resultFor`) | E |
| 4 | L'ambiente vitest stantio — **le asserzioni negative passano a vuoto** | E |
| 5 | Un file di test non registrato nel runner | — |
| 6 | La guardia `width <= 0.0` che NumPy impediva di scattare | A |
| 7 | **`\| tee log \| head` che tronca il log** — e il log sembra completo | D |
| 7b | **La fixture che asserisce `f == 365` fabbricando quotazioni di sabato** | A |

La **7b** è la più sottile: non è un controllo che non guarda, è un controllo che **guarda con attenzione un mondo che non esiste**.

### 10.4 Lo standard di prova adottato (D100)

**Un cancello che non hai falsificato non è evidenza.** Chi consegna una rete nuova la **rompe una volta** e cita il rosso ottenuto. Adottato dopo che **E** ha falsificato tutti e tre i propri gate e **D** ha falsificato tredici test per mutazione — trovando, così, **una propria guardia che non era una guardia** prima di consegnarla.

**N è arrivato allo stesso standard per un'altra strada**: ha letto le asserzioni del gate `api risk`, ha visto che **nessuna riga toccava i suoi otto campi**, e invece di consegnare «10 passed» ha sondato l'API a mano — da cui la 14ª scoperta.

### 10.5 ⚠️ Le lane di C, D e N sono **senza fixture**: un falso rosso già armato

Conseguenza diretta di §10.1, segnalata da **N** dopo averla misurata nel proprio database invece di dedurla dal referto di C:

```
prima di  services risk-all → 5612 record
dopo                        → users 0 · assets 0 · transactions 0 · price_history 0 · brokers 0
```

**Chiunque rieseguirà `api risk` su una di quelle data dir otterrà `8 passed, 2 failed`, e sembrerà una regressione del mandato.** Non lo è: serve `db populate --force` prima. I mandati sono `FROZEN` e non ripopolano.

> Vale in particolare **per me in integrazione**: è precisamente il momento in cui un falso rosso verrebbe attribuito al codice appena fuso.

### 10.6 📍 In un contratto scritto: il nome del campo, mai il numero di riga

Quarta istanza, e la prima **autoinflitta**. Scrivendo `K4.md` ho citato `schemas/risk.py:449`/`:450` per `annualization_factor` e `coverage`. **C ha corretto in `:450`/`:451` — giusto sui campi — ma ha a sua volta mancato il validatore dell'invarianza**, indicandolo a `:518` dove sta altrove.

**Due lettori attenti, due numeri sbagliati, lo stesso file, lo stesso giro.** Le tre istanze precedenti: il `:487` di H, i numeri invecchiati del brief di C, i `:49`/`:55` del brief di F entrambi fuori bersaglio.

**Regola**: in un documento che sopravvive a un commit si cita **il nome del campo, della funzione, o il messaggio d'errore**. Un numero di riga è vero il giorno in cui si scrive e falso il giorno dopo — e, peggio, *sembra* preciso.

### 10.7 🔴 Il registro dava per seminati due worktree che non lo erano — difetto del coordinatore

**A** ha segnalato che `api risk` non partiva: mathjax assente e `node_modules` assente. La
tabella di §1 gli dava `node_modules ✅`. **Era un'affermazione non verificata.**

Audit su tutti e undici, eseguito invece di riletto:

| | `node_modules` | mathjax |
|---|---|---|
| **A** `improved-meme` | ❌ ASSENTE | ❌ ASSENTE |
| **I** `shiny-broccoli` | ❌ ASSENTE | ❌ ASSENTE |
| gli altri otto | 291 voci | ok |
| coordinatore | assente (non serve) | ok |

Entrambi i mancanti sono dell'**onda 1**, creati prima che la procedura di bootstrap esistesse.
Riparati con `cp -Rc` (clonefile APFS: istantaneo, nessuno spazio). Verificato che **entrambi i
percorsi sono gitignorati** (`frontend/.gitignore:1`, `.gitignore:78`) → nessun rumore nei diff.

> ⚠️ `npm ci` **non sarebbe bastato**: il download di mathjax fallisce per
> `[SSL: CERTIFICATE_VERIFY_FAILED] Missing Authority Key Identifier`. **Il file va seminato,
> non scaricato** — ed è il motivo per cui non è mai stato chiesto a un mandato di procurarselo.

**Lezione, e vale contro di me**: questo registro è la difesa della campagna contro le basi
stantie, e **ha avuto lo stesso difetto che serve a prevenire**. Una riga di tabella scritta
al momento della creazione e mai rimisurata **invecchia esattamente come un numero di riga**.

### 10.8 🔴 L'ancora di K7 è rotta in tre lingue su quattro — e il gate è verde

Trovata da **I**, tornando a controllare **dopo** aver fatto riscrivere la sezione — non
scrivendola.

```
en   id="recovery-time"              ← K7 puntava qui
it   id="tempo-di-recupero"
fr   id="temps-de-recuperation"
es   id="tiempo-de-recuperacion"
```

`DocsLink` antepone il prefisso di lingua. Un utente italiano atterra **in cima alla pagina, in
silenzio**: nessun 404, nessun errore. E `check-links` **non lo vede** perché valida contro il
sorgente **inglese**.

> **Ottava istanza della famiglia, e la più beffarda**: il gate resuscitato da I dal codice morto
> **non guarda la dimensione in cui il link si rompe**.

✅ **Il progetto l'aveva già risolto e nessuno aveva guardato**: `kpi-cards.{en,it,fr}.md` usano
`{: #card-1-period-pl }` — **titolo tradotto, ancora identica**. È perché l'unico `DocsLink` con
ancora già in produzione funziona in quattro lingue.

**Decisione: opzione 1** — ancora esplicita nell'inglese, raccolta da Aphra alla traduzione,
**nessuna deroga** alla regola «solo inglese». Ragione decisiva, di I: *in it/fr/es quella pagina
descrive ancora la formula sbagliata — un'ancora precisa verso una spiegazione errata non
migliora niente*. **Regola da aggiungere a K7**: ogni `DocsLink` con ancora richiede un
`{: #token }` esplicito nel titolo di destinazione.

### 10.9 📋 Per il developer — una decisione che non è mia

I segnala, correttamente distinguendo il fatto dalla richiesta:

> **Tre lingue su quattro pubblicano oggi una formula del tempo di recupero che sappiamo falsa** —
> non sospettiamo: sappiamo, per iscritto. Il blocco di traduzione era stato messo in fondo quando
> il contenuto era solo *vecchio*; adesso è *sbagliato*.

I **non** ha chiesto di anticipare la traduzione: ha detto che **il prezzo dell'attesa non è più
quello su cui la decisione era stata presa**. La scelta resta del developer.

### 10.10 🔑 `fresh_quote_coverage` è calcolato e nessuno lo legge

Trovato da **I** verificando la pagina `data-quality`: **zero riferimenti in tutto
`services/risk/`**. Il servizio legge `calendar_coverage` — che per D101/D102 vale ≈ 1,000
**esattamente quando la distorsione è massima** — mentre la frazione di celle *davvero quotate*
invece che portate avanti sta lì accanto, già calcolata.

⚠️ **Limite dichiarato da I e da tenere attaccato al fatto**: copre **solo il prezzo**. Un
carry-forward del **cambio** non lo abbassa. È il segnale migliore che abbiamo, **non** un segnale
completo.

Girato ad **A** per A9, come consegna e non come imposizione.

## 11. Debiti nominati — chi li chiude e quando

Un debito che vive in una sola testa è un debito perso. Questi hanno nome, proprietario e momento.

| # | Debito | Proprietario | Quando |
|---|---|---|---|
| 1 | **`DocsLink` dalla heatmap di correlazione** → slug `financial-theory/technical-analysis/risk-metrics/correlation`, **verificato esistente** nel worktree di I. F non l'ha aggiunto **di proposito**: nella sua baseline lo slug non risolve, quindi il link farebbe **scendere** il conteggio invece di alzarlo | **F** | post-integrazione |
| 2 | ⚠️ **RITRATTATO (D142) — i tre `DocsLink` rotti NON esistono: zero rotti.** I aveva misurato con **un modello solo**, mentre i meccanismi sono **due**: `<DocsLink path>` compone `/mkdocs/${lang}/…` e raggiunge 4 lingue; un **letterale grezzo** (`window.open`, `<a href>`) **non porta prefisso** e atterra **sempre in inglese**, dove le ancore risolvono. *«Li avevo trovati controllandoli contro it/fr/es — cioè **contro pagine dove l'utente non viene mai mandato**.»* 🔴 **Ma sotto c'è un difetto vero e diverso**: tre link con ancora **non portano la lingua** → **salto di lingua silenzioso**, invisibile a `check-links`. E peggio: **`create-edit.en.md` ha 11 heading, it/fr/es ne hanno 10** — la sezione *«Importing a Distribution CSV»* **non esiste nelle traduzioni**, quindi anche localizzando il link l'utente italiano **arriverebbe su una pagina che non contiene la cosa per cui è stato mandato lì**. **Nessuna ancora lo ripara: solo una ritraduzione** | developer | con la traduzione |
| 3 | **`graphify --update`** — F ha depositato 4 pagine devWiki **leggibili ma non interrogabili dal grafo**. Il comando punta al checkout principale, che i mandati non devono leggere. F **non l'ha aggirato** | coordinatore | chiusura |
| 4 | **Pagina devWiki sulla catena `twrr`** — attraversa 3 file e produce un'invariante non ovvia che C ha correttamente messo in dubbio. Proposta da C, rinviata perché **una pagina che cita codice che nessuno può leggere dal proprio worktree è l'errore che questa campagna corregge** | project-historian | post-commit |
| 5 | **`generated.ts` da rigenerare** — H ha eseguito la sola metà Python di `api sync`; la metà TypeScript richiede `node_modules` | E | nella propria lane |
| 6 | **Le 30 ancore EN-only + 41 su pagine tradotte** (D110) | **I** | **adesso** — la finestra si chiude con la traduzione |
| 7 | 🔴 **Qual è la LUNGHEZZA DEL BLOCCO, e quali episodi cadono sotto quella soglia** (D112 — riformulazione di I, migliore della mia). Un block bootstrap **conserva la sequenza locale di proposito**: la spezza alle giunzioni, quindi **le misure di percorso sono fedeli per gli episodi più corti di un blocco e sintetiche oltre**. 🔴 **Il parametro non compare nel mandato H** (grep: zero) ed è **ciò che decide se un max drawdown simulato significhi qualcosa**. Prova che la tensione è reale: **se il default a blocchi producesse crisi prolungate, la modalità «Crisi prolungata» a 14 mesi non servirebbe**. *(Formulazione precedente, ritirata: «in che direzione sposta» — nasceva da una mia parola sbagliata, «congiunto», che descrive l'asse asset e non quello tempo.)* **Vecchio testo:** Trovato incrociando **I** e **H**: il rimescolamento congiunto conserva *quali* rendimenti e *come* gli asset si muovevano insieme, e distrugge *quando* — cioè **rimescola esattamente ciò da cui dipendono max drawdown, DaR, CDaR, Ulcer Index e tempo di recupero**, quattro delle metriche L1 che questa campagna aggiunge. Se rimescolare scioglie i grappoli di perdita, **il max drawdown simulato è sistematicamente ottimista**: non una sfumatura di documentazione, una **proprietà di correttezza rivolta all'utente**. ⚠️ Non girata a H perché è `FROZEN`; l'attesa di I (perdite in grappoli) è **plausibile e non misurata**, e la pagina si ferma correttamente al meccanismo | **H**, dopo il commit | aggiornamento baseline |
| 8 | **Il generatore di K7 vive in `/tmp/libreFolio_k7_gen.py`**, che non sopravvive a un riavvio. Uno strumento che genera un contratto e vive in `/tmp` è **un contratto che torna a essere una trascrizione al primo riavvio** | **I** | prima del `FROZEN` |
| 10 | 🔴 **DIFETTO DI PRODOTTO, non debito di documentazione — AI Export gonfia la diversificazione** (D113). Due cause nella stessa direzione: la cassa sta al denominatore HHI senza essere un termine, **e** le posizioni senza prezzo spariscono dalla somma restando nel conteggio. Misurato: **NEA 15,62 su un portafoglio di 10 asset** con 20 % di cassa. **È già spedito agli utenti.** Non instradato a documentazione: una pagina non può correggerlo, e scriverla adesso **ratificherebbe un comportamento da cambiare** | **developer** | decisione di prodotto |
| 11 | ⚠️ **Il tempo verbale dei relay** (D114). Ogni relay del coordinatore marca `[nella tua baseline]` · `[nel worktree di X, non committato]` · `[verificato su …]`. **Il rimedio di fondo resta uno solo: committare** | coordinatore | adottata |
| 9 | **`concentration` è stub** perché NEA e diversification ratio non sono nella baseline di I. Non è ordine, è dipendenza — da **N**, che li ha consegnati ed è `FROZEN` | **I** | dopo il commit |

## 12. La catena delle baseline — tre anelli, tre significati diversi

Scoperta da **A** in A4, e va letta prima di accusare qualunque passo di regressione.

```
M1  →  muove i numeri a 1e-12   (fsum vs somma incrementale: due algoritmi diversi)
M6  →  NON deve muoverli        (baseline = post-M1, non quella di oggi)
A9  →  DEVE muoverli            (+0,03…0,13 di Sharpe/Sortino)
```

> **Ogni anello ha una baseline diversa dal precedente.** Chi confrontasse M6 con i numeri di oggi troverebbe `1e-12` e lo attribuirebbe a M6 — cioè **accuserebbe di regressione il passo che esiste per dimostrare l'invarianza**.

È **D94 applicata a monte**: due cambiamenti con effetti attesi opposti sull'osservabile non condividono un passo — e non condividono nemmeno una baseline.

⚠️ **`06` §M1 conteneva due affermazioni false**, entrambe corrette da A: (a) *«M1 si fa in `signal_helpers.py`»* — impossibile, `rolling_single_values`/`rolling_pair_values` sono funzioni di **ordine superiore** e l'unico modo di vettorializzare un `Callable` arbitrario è `.rolling().apply()`, **che resta interpretato**; (b) *«a valori identici»* — **zero su quattro** segnali sono bit-identici. `np.allclose` ha `rtol=1e-5`: dire «identici» perché passa `allclose` è dire **«uguali a cinque cifre»**.

**Il costo vero di M1**, misurato in millisecondi invece che in rapporti: **46 ms** per grafico nel caso tipico (3 anni), **644 ms** nel peggiore consentito dallo schema (`window=500`, 10 anni). «1 514×» faceva sembrare M1 un'emergenza; i millisecondi dicono che è un tetto che morde **solo agli estremi**.


### 10.11 📍 Un numero in un contratto dichiara l'INSIEME che conta, non solo il proprio valore

Terza istanza in una giornata, e tutte e tre in **contratti scritti dal coordinatore** — cioè
nei documenti che esistono apposta perché ci si possa fidare senza rimisurare.

| Contratto | Diceva | Mancava |
|---|---|---|
| **K7** | «baseline **24** link» | **in quale mondo**: 24 col `dev.py` riparato di I, **12** con quello di tutti gli altri |
| **K2** | «codominio **12** valori» | **di quale insieme**: 12 valori enum, **13** chiavi se si conta `Liquidity` |
| **K4** | `schemas/risk.py:449`/`:450` | i numeri erano sbagliati — **e lo era anche la correzione di C** |

**In tutti e tre i casi entrambe le parti avevano ragione**, e il tempo si è perso a scoprire
che non si stava parlando della stessa cosa. **Regola**: un numero in un contratto porta con sé
**l'insieme, il mondo o la funzione** da cui è stato estratto. Mai il numero nudo, mai un numero
di riga.

### 10.12 `primaryAssetType` non normalizza il caso — la domanda aperta è chiusa

Rimasta senza risposta da B, **chiusa da G** e verificata dal coordinatore.
`portfolio_engine.py:1040-1041` inietta **una stringa letterale Title Case**:

```python
by_type["Liquidity"] = by_type.get("Liquidity", zero) + cumulative_cash + it_cash
```

`Liquidity` **non passa dall'enum**: è un secchio sintetico per la cassa. Le chiavi della mappa
sono quindi **a caso misto** — enum in `UPPER_SNAKE` più `"Liquidity"` in Title Case.

🔴 **Conseguenza misurata da G**: la tavolozza dello storico ha **12 colori per 13 chiavi**, e la
tredicesima **avvolge in silenzio sul colore della prima**. Un avvolgimento non produce errori:
produce **due fette dello stesso colore, che l'utente legge come una**.


## 13. Ordine di integrazione — vincoli scoperti, non preferenze

```
B  →  G          G non compila senza: primaryAssetType e assetTypeBadgeClass
                 non esistono nel suo checkout (F35 / D117)
A  →  E          K1 esiste solo nel worktree di A; E rigenera generated.ts dopo
B  →  E, F       il parametro is_benchmark passa da 6 a 11 occorrenze in generated.ts
D  →  E, F       divisione degli spec K5
C, N, H          indipendenti
```

### 13.1 ⚠️ La prova dello shim, obbligatoria durante l'integrazione

I contratti atterrano **in sequenza**, quindi ogni mandato avrà per un tratto **un simbolo
irrisolto** — e con un simbolo irrisolto **TypeScript smette di controllare i suoi call-site**
(**D124**, trovato da G).

> **«Resta solo l'errore della mia dipendenza» non significa «il resto è verificato»:
> significa che il resto non è stato controllato.**

Procedura: shim con la firma **esatta** → check → **ripristino verificato con
`git diff --stat` vuoto`**. ⚠️ Lo shim valida **i tipi, non i valori**.

### 13.2 Ordine obbligato dei cancelli backend, e la lane vuota

```
services risk-all  →  db populate --force --clean  →  api risk
```

E **le data dir di C, D, N e B sono adesso senza fixture** (§10.5): chi riesegue `api risk`
su una di quelle otterrà `8 passed, 2 failed` **e sembrerà una regressione del mandato**.

### 13.3 Prima di ogni cancello frontend

```
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync
```

Senza, `svelte-check` riporta **278-285 errori che non sono di nessuno** — `generated.ts` è
gitignorato e `assetTypes.ts:17` esegue `schemas.AssetType.options` **all'import**. Misurato
indipendentemente da **F** (278 → 2) e da **G** (285 → 2 → 0).

## 14. Superfici che nessuno andrebbe a cercare — mappa di proprietà non ovvia

Un file toccato da un mandato il cui titolo non lo suggerisce è un conflitto che **si scopre
al merge**. Questi sono gli scostamenti fra titolo e superficie, dichiarati dai mandati stessi.

| File | Proprietario | Perché nessuno lo cercherebbe lì | Rischio |
|---|---|---|---|
| `backend/app/services/risk/scenario_catalog/loader.py` | **B** (+13 righe) | il mandato si chiama *«tassonomia e benchmark»* | Le righe sono **additive**, ma un ripristino all'ingrosso del file **le cancellerebbe senza far diventare rosso nulla degli altri** — il guardiano è nel ramo di B. ✅ **Verificato: N, A, H, C hanno zero file di `scenario_catalog/`. B ne è l'unico scrittore.** |
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | **B** (1 riga, F32) | fuori dal perimetro dichiarato | Ratificato: il guasto era **causato dalla modifica di B**, e lasciarlo per rispettare un confine sarebbe stato **spedire una perdita di dati silenziosa** (D116) |
| `backend/app/services/risk/signal_plugins/rolling_*.py` | **A** (4 file) | il mandato è *«oracolo e migrazione»* | Concessione **D90**, e **non una comodità: l'unica strada** — non si vettorializza un `Callable` arbitrario (D124 del piano `06`) |
| `backend/app/services/risk_plugins/{historical_var,drawdown_summary}.py` | **A** | §2.6 li dava a **N** | I due produttori di K1: un campo di schema senza produttore è peso morto |
| `backend/app/schemas/risk.py` | **quattro** scrittori: A, C, N, **H** | §2.2 ne dichiarava tre | `__all__` è un conflitto **a quattro vie**: unione + riordino alfabetico (D92) |

### 14.1 La protezione F36, se non viene autorizzata

Se le tre asserzioni di B non entrano, **va passata al developer come voce di chiusura**:

> `assets.types.LIQUIDITY` è **l'unica** delle 18 chiavi `assets.types` senza un valore enum
> corrispondente (17 valori), ed è **invisibile a `grep`** perché composta per concatenazione
> (`assets.types.${rawName.toUpperCase()}`). **Nessuno strumento attuale la condanna** —
> `i18n audit` cerca mancanti e duplicate, non inutilizzate. Il pericolo è che
> **l'irrigidimento più naturale del cancello di B** — applicare ai cataloghi i18n la forma
> bidirezionale già usata per `ASSET_TYPE_MENU_ORDER` — produca **un rosso, uno solo**, la
> cui correzione evidente è **cancellare la chiave**. Allora l'etichetta della cassa mostra
> `assets.types.LIQUIDITY` grezzo **in quattro lingue**.
>
> **Una trappola che si arma da sola con una buona intenzione.** Costo della protezione:
> **una asserzione**.

## 15. 🔴 I cataloghi del runner — conflitto testuale CERTO, misurato

Tre mandati scrivono `_frontend_portfolio.py`, due `_frontend_utility.py`. **Tutti additivi, tutti
autorizzati** dalla regola generalizzata (*registrare i propri test non si chiede*), e **nessuna
collisione semantica**: nomi di funzione e selettori sono distinti.

| Mandato | `_frontend_portfolio.py` | `_frontend_utility.py` | `_frontend_asset.py` |
|---|---|---|---|
| **F** | `front_portfolio_risk_lab` → `"risk-lab"` | ✅ 2 file unit + clausola `desc` | — |
| **G** | `front_portfolio_allocation_unit` → `"allocation-unit"` | — | — |
| **D** | ✅ (divisione spec K5) | ✅ (catalogo) | — |
| **B** | — | — | ✅ |

### ⚠️ I punti d'inserzione coincidono

```
F inserisce dopo le righe   83  e  111
G inserisce dopo le righe   74  e  110
```

**110 e 111 sono lo stesso blocco `add_test`.** Git **non** fonderà automaticamente: il conflitto
è **certo**, non probabile.

> ## ✅ Regola di risoluzione: **unione**, mai «ours» né «theirs»
>
> Le voci sono **indipendenti per costruzione** — funzioni con nomi diversi, selettori diversi,
> file di test diversi. Si tengono **tutte**, nell'ordine che si preferisce.
>
> 🔴 **Scegliere un lato cancella in silenzio il test di un mandato**, e il sintomo sarebbe
> `test check-orphans` a `N/N+1` — cioè **la quinta istanza della famiglia**: uno spec che
> esiste, non gira, e nessuno se ne accorge finché non conta i file.

### Verifica obbligatoria dopo la fusione dei cataloghi

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test check-orphans
```

Deve riportare **ogni** spec raggiungibile. Alla consegna: **F 79 spec + 199 unit, tutti
raggiungibili**; il numero salirà con le voci di G e D.

### 15.1 📍 Correzione di precisione — e la terza forma della stessa classe

**F ha misurato**, e il numero che §15 portava era attribuito al referente sbagliato:

| | baseline | attuale |
|---|---:|---:|
| contenuto della stringa `desc=` | **1 517** | **1 877** |
| **riga fisica intera** | **1 672** | **2 032** |

> **`1 674` non coincide con nessuno dei quattro, ma dista 1-2 dalla riga intera.** È **la riga**,
> non il campo: **numero giusto di grandezza, attribuito al referente sbagliato**. Chi leggesse
> *«il `desc` è 1 674»* e andasse a misurarlo troverebbe **1 517**, e **si metterebbe a cercare
> una modifica mai avvenuta**.

🔑 **Terza istanza della stessa classe in un giorno, in tre vestiti diversi:**

| | |
|---|---|
| i tre `coverage` | **stesso nome, tre denominatori** |
| `check-links` 12 contro 24 | **stesso numero, due mondi** |
| **`1 674`** | **numero giusto, oggetto misurato diverso da quello dichiarato** |

→ **Un numero dichiara CHE COSA ha misurato, non solo quanto.**

✅ **E dalle stesse cifre esce una prova migliore di quella che avevamo**: la riga è cresciuta di
**esattamente i 360 caratteri** di cui è cresciuto il `desc` (1 672→2 032 e 1 517→1 877), quindi
**nulla fuori dal `desc` è cambiato**. È una prova **aritmetica**, più forte del confronto fra
stringhe — che dipendeva da una regex.

**La regola sull'estensione del `desc=` e la risoluzione per unione non cambiano: cambia solo
l'etichetta del numero.**

## 16. Stato dei mandati — 18 Set 2026, 02:10 *(superato: vedi §18)*

| | Mandato | Stato | Ultima evidenza |
|---|---|---|---|
| **A** | oracolo e migrazione | A4 e A5 chiusi, su **A6/M6** | `risk-oracle` **131** (da 43) · `risk-all` **265** (da 177) |
| **B** | tassonomia e benchmark | **riaperto** per la duplicazione `data-testid` (D134) | `asset-unit` **262** · 3 reti falsificate · **39** scoperte |
| **C** | affettamento | ✅ **FROZEN** | `risk-all` 146 · `api risk` 10 |
| **D** | primitive e card | ✅ **FROZEN** | `component-unit` **1808** · primitive a **`1a537f9cb`** |
| **E** | quattro livelli | implementa L4 e passo 8 | `risk-levels-unit` 28 · file max **243** righe su 600 |
| **F** | laboratorio | **scongelato** per test 6 e test 4 (D100) | `core-unit` **2062** · 2 rossi **voluti** |
| **G** | colori allocazione | **scongelato** per stub K2 e commento `:114` | `allocation-unit` **68** · `dashboard` 7 · ΔL **20.000** |
| **H** | Monte Carlo | ✅ **FROZEN** | `risk-simulation` 29 · `risk-all` 148 |
| **I** | documentazione | gate `:1197` e pagina GBM | **11 pagine piene su 21** · `check-links` 24 · **83 ancore** |
| **N** | acquisizioni | ✅ **FROZEN** | `risk-all` **166** · `api risk` 10 |
| **J** | chiusura | **non creato** — per ultimo (D46) | brief aggiornato con le cifre reali di M2 e A9 |

### 16.1 Le tre riaperture, e perché sono diverse da un ripensamento

| mandato | perché riaperto | chi l'ha trovato |
|---|---|---|
| **B** | la sua correzione **F30** duplica un `data-testid` e rompe **cinque** spec in una categoria che non ha eseguito | **F**, che ha rifiutato di ripararlo perché `ui/select/` non è suo |
| **F** | **due delle sue sei reti non discriminano** — un difetto vero le attraverserebbe | **F stesso**, applicando D100 alle proprie asserzioni **da fermo** |
| **G** | lo **stub K2 nei suoi test è permanente e porta la semantica sbagliata** del coordinatore — e fino al merge di B è **l'unico record eseguibile di K2** | **G stesso**, dopo aver buttato lo shim effimero |

> **Nessuna delle tre nasce da un ripensamento del coordinatore.** Due le hanno trovate i mandati su sé stessi; la terza l'ha trovata un mandato sul lavoro di un altro **e si è fermato al confine di proprietà**.

### 16.2 Le regole nate dall'esecuzione, non dal piano

| # | Regola | Da |
|---|---|---|
| **D100** | un cancello che non hai falsificato non è evidenza | E, D |
| **D125** | due difese **in serie**: provarne una lascia l'altra non verificata | B |
| **D136** | **anche una falsificazione ha bisogno della prova di essere stata eseguita** | B |
| **D141** | **non vince l'ultimo messaggio: vince l'albero** | B |
| **D143** | **ogni misura porta con sé lo stato dell'albero in cui è stata presa** | G |
| **D146** | **una decisione si relaya; il codice si integra o non c'è** → allegare lo SHA | F |
| **D148** | in `X[k] ?? k` il `k` del ripiego è **già normalizzato** | G |

## 17. 🔴 Conflitto misurato su `TODO_FUTURI.md` — coordinatore contro H

Trovato e **misurato** da **H**, confermato dal coordinatore leggendo i confini dei due hunk.

```
hunk del coordinatore :  @@ -263,18 +263,18 @@    → copre 263-280
hunk di H             :  @@ -279,6  +279,79 @@    → copre 279-284
                                                     ⚠️ SOVRAPPOSIZIONE 279-280
```

Fra la riga più bassa del coordinatore (**277**, la riga GJR-GARCH della tabella) e l'inizio
del contesto di H (**279**) c'è **una riga sola**. Con i 3 di contesto predefiniti, **Git
segnala conflitto e non fonde in silenzio**.

| chi | cosa cambia |
|---|---|
| **coordinatore** | `:266` Status → *«livelli **2**, 4 e 5»* · `:271-272` contesto → *«ai livelli **1 e 3**»* · `:277` riga 2 → **📋 rinviato — non calibrabile da QuantLib (D88)** |
| **H** | due sezioni nuove **sotto**, che **spiegano** quel rinvio: l'introspezione QuantLib per esteso e la precondizione `arch` nel `Pipfile` |

> ## ✅ Risoluzione: **prendere entrambi i lati per intero.** Le due modifiche sono **complementari**, non concorrenti.
>
> 🔴 **E scegliere un lato riporta il file nello stato che entrambi hanno corretto oggi**, nelle
> parole di H: *«una tabella che promette e un testo che non c'è, oppure un testo che spiega un
> rinvio che la tabella non dichiara»*.
>
> **Criterio di verifica dopo il merge**: la riga 2 della tabella dice **«rinviato»** *e* la
> sezione sotto spiega **perché**. Se una sola delle due sopravvive, la risoluzione è sbagliata.

⚠️ **E la spiegazione deve essere quella corretta** (D88, rivista su rilievo di I): non *«QuantLib
espone GARCH solo come engine di opzioni»* — il motore **non passa da un engine**, usa
`GeometricBrownianMotionProcess` → `StochasticProcessArray` → `GaussianMultiPathGenerator`. La
versione giusta è: **la generazione di cammini richiede uno `StochasticProcess`, e i binding
Python non ne espongono alcuno della famiglia GARCH**.

**Esecutore autorizzato**: **H**, su richiesta esplicita del coordinatore al momento del merge —
è l'unico che conosce entrambi i lati, e risolvere-e-stagionare un conflitto è l'unica azione Git
concessa a un mandato.



## 18. 🟢 Stato dei mandati — 18 Set 2026, 03:30 — **fonte autorevole**

> ⚠️ **Questa tabella si legge insieme ai piani vivi, non al posto loro.** Ogni mandato tiene
> `implementation/progress/<X>-esecuzione.md` aggiornato **dopo ogni passo**; questa sezione
> è un indice, non la verità. **Prima di scrivere a un mandato si apre il suo piano** (D212).

| | Mandato | Stato | Ultima evidenza misurata |
|---|---|---|---|
| **A** | oracolo e migrazione | ✅ **FROZEN — completo, A0→A18** | `risk-oracle` **204** (da 43) · `risk-all` **338** (da 177) · `schemas risk` **20** · `api risk` **10** · 14 mod + 2 nuovi, **+905/−79** · **M6 = 1 migrazione su 9** |
| **B** | tassonomia e benchmark | ✅ **FROZEN** | `asset-unit` **264** · `asset-merge` **3** (da 3 failed) · 25 file **+827/−127** · **44** reperti · SHA `590f32ae6` |
| **C** | affettamento | ✅ **FROZEN** | `risk-all` 146 · `api risk` 10 |
| **D** | primitive e card | ✅ **FROZEN** | `component-unit` **1808** · primitive a **`1a537f9cb`** |
| **E** | quattro livelli | ✅ **FROZEN — completo, L4 chiuso** | `risk-levels-unit` **89** · `risk-controller-unit` **14** · `risk-benchmark-unit` **8** · `risk` E2E **11** · `i18n audit` **2828/0** · `check-orphans` 78+202 · file max **494**, `RiskLevelsPanel` **206** · **13 tracciati + 25 nuovi** |
| **F** | laboratorio | ✅ **FROZEN** | 4 gate su 4 sull'albero finale · `risk-lab` 812 righe · `check` 0/41 |
| **G** | colori allocazione | ✅ **FROZEN definitivo** | `allocation-unit` **68** · ΔL su **28** slot · immune a F42 · **3 voci di debito scritte nel piano** |
| **H** | Monte Carlo | ✅ **FROZEN** | `risk-simulation` 29 · `risk-all` 148 · delta 15+2 |
| **I** | documentazione | ✅ **FROZEN — nulla resta suo** | **19/22 piene** (82-135 righe) · **3 stub bloccati su N** · corpus: **0 href rotti su 27 708** in 4 lingue · `validation.anchors` acceso, **9 → 0** warning |
| **N** | acquisizioni | ✅ **FROZEN** | `risk-all` **166** · `api risk` 10 · `acquired.py` 246 righe a **`1aaea6949`** |
| **J** | chiusura | ⏳ **non creato** — per ultimo (D46) | brief con le cifre reali di M2, A9 e la regola dell'intero |

### 18.1 Misura del coordinatore — l'unica corsa di questa sessione

**Corsia 6250**, albero `e-alfy-ideal-eureka` a **`cc33120eb`**, `git status` di prodotto **vuoto**.

| spec | 3 corse | esito |
|---|---|---|
| `tx-ca-contract` | `2F/10` · `2F/10` · `2F/10` | **CAC-011 + CAC-012, deterministico** |
| `tx-import-asset-inspector` | `1F/4` · **`5P`** · `1F/4` | **E2-001, intermittente 2 su 3** |

**Nessuno dei due è attribuibile a B.** Firma nei tempi: **12,9 · 3,4 · 12,7** → timeout, non asserzione.

⚠️ **Il mio albero non aveva `frontend/node_modules`** — unico fra dodici worktree. Ripristinato da lock
dopo difetto confermato (`Cannot find package 'typescript'`). **Ogni "verifico io" sul frontend promesso
prima di questo momento era senza copertura.**

### 18.2 Debiti nuovi, con proprietario da assegnare

| # | Debito | Indirizzo | Nota |
|---|---|---|---|
| 1 | **Spec che accusa il file che stai modificando, 2 volte su 3** | `fixtures/probe.ts:46` · `SearchSelect:452` | ⚠️ **non scriverlo come «flaky»** (D207): chi legge «flaky» ci rilancia sopra; chi legge questo **sa di non poterlo usare per attribuire** |
| 2 | 🔴 **La baseline non è conforme al PROPRIO formattatore** | `dev.py:1698` `black backend/` | **Diagnosi corretta (D280)**: N ha eseguito **il comando sanzionato**; `black --check` sui 7 file dà **EXIT=1**. **Chiunque esegua `./dev.py format` produce un diff ampio e non correlato.** I 7 file vanno **esclusi dallo stage perché fuori scopo**, non perché sbagliati |
| 3 | **42 ancore solo-inglesi, latenti** | `index` 10 · `volatility` 11 · `sharpe-ratio` 8 · `sortino-ratio` 8 · `max-drawdown` 5 | ✅ **assegnato: J §8.4** — decidere fra anticipare la traduzione o mitigare con `<div id>` (D203) |
| 4 | **48 `$$` non renderizzati in it/fr/es** | `volatility` ×4 · `fifo-lot-analysis` es/fr/it | ✅ **assegnato: J §8.1** — contare i `$$` nell'HTML **per lingua**, zero unico valore accettabile (D177) |
| 5 | **`risk.simulation.assumptions` dichiara 5 limiti e omette quelli statistici** | i18n frontend | **E o F** — un GBM **sottostima le code** (D202) |
| 6 | **`fresh_quote_coverage` è calcolato e nessuno lo legge** | `series_preparation.py:347` · `schemas/risk.py:401` | **C** per la fetta, **I** per `data-quality` (D210) |
| 7 | **Due PNG di un altro mandato in almeno 3 worktree** | `mkdocs_src/docs/static/icons/asset-types/{commodity,real-estate}.png` | **non tracciati, NON ignorati** — escludere esplicitamente da ogni `git add` (D208) |
| 8 | **`verbose` di `SharedBackend` non è impostabile** | `scripts/test_runner/_server.py:161,269-270` | ✅ **assegnato: J §8.3** — *«un errore che non si può leggere non è un errore: è un silenzio»* |

| 9 | **`percentage_contribution` porta una FRAZIONE e il nome dice «percentage»** | `schemas/risk.py:673` | ✅ **assegnato: J §9**, insieme a `coverage`→`calendar_coverage` — **sono lo stesso difetto di segno opposto** (D218) |
| 10 | **`risk-asset-add-button` rimosso dal prodotto, lo spec lo insegue** | `AssetSetRiskPanel:138` (baseline) · `risk-analysis.spec.ts:654` | **E, coda K5.** Il rosso `asset global` **si sposta** da `:652` a `:654` dopo l'integrazione di B — chi lo rivede può concludere che B abbia fallito (D226) |
| 11 | ~~I risultati `partial` spariscono~~ | — | 🔴 **DEBITO FALSO, ritirato (D338)**: `levelHelpers.ts:46` rifiuta ciò che **non è né `ok` né `partial`** → **un `partial` passa**, e due test lo portano **nel nome** (`:277`, `:290`). *«Mostrare ciò che c'è con un gradino è ciò che il codice fa già.»* |
| 12 | **`warnings` non è reso da nessun livello** | mandato E | ✅ **E lo chiude prima di congelare**: `warnings` è in **`RiskAnalyticResult`, opzionale, GIÀ nel contratto generato** → Zod non lo cancella, **entrambi i rami esercitabili oggi**. ⚠️ Renderli **senza interpretarli**: mapparli su chiavi i18n a runtime ricreerebbe D288 |
| 13 | **`if (!var_bin_edge)` legge «assente» su un taglio a zero** | `schemas/risk.py` `var_bin_edge` · ogni renderer | ✅ **E, coda K1**: si legge con **`=== null`**, mai con la verità booleana. Il caso è **raggiungibile**: chi non ha mai perso nella finestra pubblica `value_at_risk == 0.0` (D264) |
| 14 | **Divieto di import di `rk.SemiDeviation` fuori da `annualized_sortino`** | configurazione di progetto | ✅ **J**: i 4 test di A vietano la sostituzione **dentro una funzione**, non nel progetto. Oggi rispettato ovunque (D247) |
| 15 | **24 stringhe i18n orfane** per una funzione deliberatamente non esposta | `risk.analytics.portfolioOptimization.*` · `risk.params.{optimizationStrategy,includeFrontier,frontierPoints,optimizationSolver}` | 6 chiavi × 4 lingue, **zero consumatori**. 🔴 **Non è pulizia: è una PROVA FALSA PERMANENTE** che la funzione sia esposta — *«Aphra traduce il catalogo, non la UI raggiungibile, e più la traduzione è completa più il segnale falso è convincente»* (D301). Stessa domanda della decisione pendente di `TODO_FUTURI` sulle dipendenze **sul lato frontend** |
| 22 | 🔴 **Una chiave i18n serve DUE superfici: il testo nuovo peggiora il legacy** | `risk.metrics.cashWeight` · `L2Diversification` **e** `RiskAnalysisPanel:859` | E l'ha cambiata da *«Cash weight»* a *«Cash and uncovered»*: **giusto per L2** (legge con `!== null`), **peggiore per il legacy** (legge con `?? 0`) → un dato assente diventa **«Cash and uncovered: 0,0 %»**, che **afferma di aver verificato**. ✅ **All'integrazione: separare le chiavi, oppure riparare il `?? 0` del legacy insieme al testo** (D352) |
| 21 | 🔴 **137 campi dichiarati opzionali in TS che il server emette SEMPRE** | `generated.ts` · ogni `Field(<default>, …)` Pydantic | **Un default Pydantic esce non-required in OpenAPI** → `number \| undefined` in TS → **induce un ripiego che è codice morto e indistinguibile da uno necessario**. ⚠️ **Il pericolo non è il codice morto: è la scelta del ripiego** — `?? 0` su un peso escluso rende *«0 % escluso»*, il valore **più rassicurante** (D344) |
| 20 | 🔴 **K1, K6 e K8 sono «costruiti, provati e SPENTI»** | i campi vivono **solo** negli alberi di A, H, N | **Zero occorrenze in baseline**; `api sync` oggi **esce verde e produce zero tipi**. ⛔ **Non contarli come resi finché non sono visti SUL FILO.** Verifica: contare i campi in `generated.ts`, non leggere l'uscita del comando (D326, J §12) |
| 19 | 🔴 **`coverage ≈ 100 %` accanto a uno Sharpe lusingato — IN PRODUZIONE OGGI** | `RiskResultFrame.svelte:99-100` · `RiskAnalysisPanel.svelte:833` | La cornice che rende `metadata.coverage` **avvolge `historical_kpi`**, che porta **Sharpe e Sortino**; il legacy serve `asset`/`asset_set` → **Asset Detail e il laboratorio di F**, il **ramo titolo** dove la lusinga A9 è massima. ⚠️ **Destinatari: F e chi decide su D8/D47** — **non E, che è l'unico a non mostrarlo** (D322) |
| 18 | 🔴 **Il proxy automatico per il replay NON esiste — e una motivazione sbagliata del coordinatore lo faceva sembrare esistente** | `schemas/risk_scenarios.py:39-40` · `stress.py:452-466` · `service.py:513` | ⚠️ **PRIMA che F costruisca «un proxy vero per l'insieme»**: `RiskScenarioMissingHistoryPolicy` ha **un solo valore**, `MANUAL_PROXY_OR_EXCLUDE`; il backend **nega la risposta** al primo asset senza storia, non la degrada; l'audit **specchia la richiesta**. **Un proxy automatico è lavoro di backend, non di pannello** (D320) |
| 17 | 🔴 **`scripts/` è fuori dal perimetro di ENTRAMBI i gate** | `dev.py:1698` e `:1705` guardano solo `backend/` | **Ci vive `_backend_services.py`**, il file che il maggior numero di mandati modifica — **e l'unico che né `format` né `lint` guarderanno mai**. ⚠️ **NESSUNO esegua `black` su `scripts/`** durante l'integrazione: riformatterebbe un file che tre mandati stanno modificando (D282) |
| 16 | **Il sottosistema di rischio non ha pagina developer** | `mkdocs_src/docs/developer/` | `find developer -iname "*risk*"` → **vuoto**; `quantlib` solo in `credits-legal`. **Emersa da due lati indipendenti** (GARCH e `portfolio_optimization`) — rinviata, non negata (D266) |

### 18.3 🔑 Le tre forme di oracolo cieco trovate oggi, che sono una sola malattia

| chi | forma | frase |
|---|---|---|
| **A** | l'aspettativa **chiama il soggetto** | *«un'aspettativa che chiama il soggetto non è un oracolo, è un'eco»* |
| **E** | la fixture è scritta **dalla stessa mano** del difetto | *«un test scritto dalla stessa mano che ha scritto il difetto ne eredita il presupposto»* |
| **I** | la sonda **non consuma la variabile del ciclo** | *«se l'output non può cambiare, non è evidenza»* |

> **L'oracolo perde potere quando la sua fonte non è indipendente dal soggetto.** A l'ha trovata nel
> *codice* dell'aspettativa, E nella *mano* che ha scritto i dati, I nella *forma* della sonda.
> Nessuna delle tre lascia traccia nel file: **tutte e tre passano ogni falsificazione**.

**L'unica uscita nota, usata due volte oggi**: **la conferma incrociata da un metodo che non condivide
nulla con quello che ha prodotto il risultato** — I su `#interest-schedule-editor` (sorgente contro
HTML costruito) e sulle unità M2 (Acerbi-Tasche riscritto dalla definizione, non dal codice di A).

### 18.4 ⚠️ Come NON dimensionare l'integrazione di un mandato

`git diff --shortstat` **non vede i file non tracciati**. Misurato da G: il suo delta è rimasto
a **295/32 per tre consegne consecutive** mentre il lavoro avanzava, perché **il piano vivo, il
modulo nuovo e le due suite unitarie** non erano tracciati.

> **«Il numero non è fermo perché non è successo niente: è fermo perché non guarda dove è successo.»**

✅ **Per stimare il costo di integrazione servono tre letture insieme**:

```bash
git -C <worktree> diff --shortstat          # ciò che git già conosce
git -C <worktree> status --porcelain        # tracciati + NON tracciati
git -C <worktree> ls-files --others --exclude-standard | wc -l
```

### 📊 Misurato su tutti gli undici alberi — 18 Set 03:35

| mandato | tracciati modificati | **NON tracciati** | totale | **quota invisibile** |
|---|---:|---:|---:|---:|
| **I** documentazione | 7 | **21** | 28 | 🔴 **75 %** |
| **D** primitive | 6 | **12** | 18 | 🔴 **67 %** |
| **E** quattro livelli | 13 | **20** | 33 | 🔴 **61 %** |
| **F** laboratorio | 10 | **15** | 25 | 🔴 **60 %** |
| **G** colori | 5 | 6 | 11 | 55 % |
| **H** Monte Carlo | 15 | 2 | 17 | 12 % |
| **N** acquisizioni | 11 | 4 | 15 | 27 % |
| **A** oracolo | 14 | 4 | 18 | 22 % |
| **B** tassonomia | 25 | 5 | 30 | 17 % |
| **C** affettamento | 5 | 3 | 8 | 38 % |

> **`git diff --shortstat` perde fra il 12 % e il 75 % dei file secondo il mandato.**
> Per **I** tre quarti del lavoro sono invisibili, perché scrive **pagine nuove** — e una pagina
> nuova è un file nuovo.

🔴 **E c'è una seconda cecità, trovata sull'albero del coordinatore**: `git diff --shortstat`
riporta **0 file** mentre **22 sono in stage**, perché senza `--cached` guarda **solo il non
messo in stage**. → **Due cecità sovrapposte: ignora i non tracciati E ignora lo stage.**

📌 Vale per **ogni** mandato: i piani vivi in `implementation/progress/` sono non tracciati
finché il coordinatore non li mette in stage.

### 18.5 🔴 Questioni CHIUSE — da non richiedere. *Registro anti-ricaduta*

> **Tre mandati in un giorno hanno dovuto difendersi dal canale del coordinatore invece che dal
> lavoro**: A (quattro «vai su A4» su un passo chiuso), B (cinque relay su una riapertura chiusa
> da due messaggi), I (tre rinvii delle stesse decisioni (a) e (b)).
>
> **La cura non è la buona intenzione: è questa tabella.** Prima di scrivere a un mandato si
> apre il suo piano vivo (**D212**) **e** si legge questa sezione.

| mandato | questione | chiusa con | ⛔ |
|---|---|---|---|
| **A** | nome del file di test di N | **non esiste**: `test_risk_analytics.py` +593 righe, già a `_backend_services.py:78` | ⛔ |
| **A** | chi scrive i tre casi K1 | **A, solo append in coda** + due nomi al blocco import (D216) | ⛔ |
| **A** | `algorithm_version` | 🔴 **RITRATTATO (D281)**: è **già aumentato in albero** — `drawdown_summary` **1.1.0**, `historical_var` **2.0.0**. Ratificare `1.0.0` sarebbe stato **un abbassamento**, che **inverte la cronologia** per chi ordina per versione | ⛔ |
| **A** | Q7 con le cifre `rm=` | **portate** (D193) | ⛔ |
| **A** | nome del ramo nei registri | **il registro era giusto**: col. 3 = worktree, col. 4 = ramo | ⛔ |
| **A** | 🔴 **TUTTO IL MANDATO** | **A0→A18 chiuso e `FROZEN`.** `risk-oracle` **204** · `risk-all` **338** · `schemas risk` **20** · `api risk` 10 · porta 6240 libera. **Non scrivere ad A se non per un conflitto di integrazione.** | ⛔⛔⛔ |
| **A** | Fascia 1 di M6 (`wealth_index`) | ✅ **ESEGUITA**, dopo tre rifiuti — **rifondando prima l'oracolo, poi migrando**. **769 324 punti, 0 divergenze**, eccezioni 5/5. ⚠️ Il `0,252 ms` con cui era stata rifiutata **era sbagliato di ~28×** (D268-D269) | ⛔ |
| **A** | pagine MkDocs (`volatility`, `sharpe-ratio`) | 🔴 **NON sono di A**: `git diff --name-only -- mkdocs_src/` → **0**. A ha cambiato il **codice** (A9), **I** riscrive le **pagine**. **Non mandare A su un file MkDocs** (D279) | ⛔ |
| **A** | unità delle cifre M2 | ✅ **variazioni RELATIVE**, e **invarianti di scala per costruzione** — provato su 100× di volatilità, dispersione `6,573e-14`. **La tabella per livello di confidenza resta** (D277) | ⛔ |
| **B** | riapertura F30 | **chiusa**, SHA `590f32ae6`, `grep` → `0` e `1` | ⛔ |
| **B** | le due asserzioni di G | **fatte**, `asset-unit` **264**, entrambe falsificate | ⛔ |
| **B** | `scenario_catalog/`, F36, 262 vs 259 | **tutte chiuse** e riconfermate due volte | ⛔ |
| **B** | i due rossi `tx-*` | **della baseline**, misurati dal coordinatore 3×3 (D206) | ⛔ |
| **F** | cancello esteso su B | **non serviva**: `asset-merge` **era** il percorso discriminante, ed era il rosso di partenza | ⛔ |
| **F** | quale forma ha scelto B | **completa** (inoltro **e** rimozione) | ⛔ |
| **G** | cancello sulla tavolozza | 🔴 **RITIRATO dal coordinatore** — non esprimibile (D196) | ⛔ |
| **G** | debito `:109` | **scritto nel piano di G**, `:544`, voce 3 di 3 | ⛔ |
| **I** | decisioni (a), (b), (c), GARCH, `portfolio_optimization`, pagina developer | **TUTTE CHIUSE** — gate in `dev.py` con 3 eccezioni datate, **158/158 titoli H2+** ancorati, 22 H1 escluse per progetto, **180 totali** ⚠️ *(il `136/158` precedente sottraeva le H1 due volte — D300)*, `simulation-modes` 123 righe | ⛔⛔ |
| **I** | unità delle cifre M2 | **variazione relativa** — CVaR 2,00 % → **2,0053 %** (D213) | ⛔ |
| **I** | etichetta nav `simulation-modes` | **decisa da I**: *«Simulation — What the Model Assumes»*, con le tre `nav_translations` (D230) | ⛔ |
| **I** | frase sul tasso privo di rischio | **sbloccata** con le cifre finali di A, in **punti di rapporto** | ⛔ |
| **E** | relay `percentage_contribution` | **raggio zero** fuori da E, misurato (D219) | ⛔ |

### 18.6 ⚠️ La coda di traduzione — **sei ragioni, nessuna è «tradurre di più»**

| # | ragione | prova |
|---|---|---|
| 1 | **42 ancore esplicite vivono solo in inglese** | it/fr/es su 5 pagine tradotte |
| 2 | **48 `$$` non renderizzati** in it/fr/es | HTML costruito: en **0**, it **4**, fr **22**, es **22** |
| 3 | **La pipeline non preserva il whitespace significativo** | i tre meccanismi di §8.1 sono *tutti* spazi |
| 4 | **Un'etichetta di nav è una chiave** | `Simulation Modes` viveva in `nav_translations` ×3 |
| 5 | **Le 17 pagine nuove sono in debito pieno** | sane oggi **perché** non tradotte (fallback i18n) |
| 6 | **`simulation-modes` da stub a 123 righe** | ricostruzione completa, nessuna scorciatoia |

> 🔑 **L'inversione che governa tutte e sei**: **l'ancora è sana dove la pagina NON è tradotta e
> rotta dove lo è.** Il fallback i18n serve il corpo inglese **intero**; una traduzione
> **parziale** serve una pagina tradotta **priva** dell'ancora.
>
> **Sarà il blocco di traduzione a esporre il debito, non la sua assenza.** Chi lo lancerà deve
> avere il gate dei `$$` (§8.1) **già in piedi**, altrimenti moltiplica per tre un difetto che
> oggi conta 48 occorrenze.


## 19. 🔴 Percorso critico — 18 Set 2026, 03:40

> ## 🔴🔴 **AGGIORNAMENTO §33 — il passo 0 non è più solo C: è C *e D*, e D è peggio**
>
> | | oggetti che **non esistono** in git |
> |---|---:|
> | **D** `solid-engine` | 🔴🔴 **7** — le **tre primitive** e i loro test, più il piano |
> | **C** `crispy-journey` | 🔴 **4** — 3 tracciati divergenti + il piano |
> | altri sei | 🔴 **1 ciascuno** — il proprio piano vivo |
> | **N** · **H** | ✅ **0** |
>
> ⚠️ **Le primitive di D sono la base su cui F ed E hanno costruito.** Perderle costa due
> mandati, non uno. **Il checkpoint `1a537f9cb` le contiene in versione vecchia** (122 righe
> contro 131 sul disco) — **una verifica di presenza non è una verifica di attualità.**

> **Nessun mandato è più bloccato da un altro mandato. Tutto ciò che resta passa dallo sviluppatore.**

> ⚠️ **Correzione di una mia istruzione — 03:45.** Avevo scritto che il ripristino dei 7 file
> contaminati **precede** il commit di N. **Falso, e verificato**: i 7 percorsi contaminati e i
> **5 percorsi di scopo** di N sono **interamente disgiunti**.
>
> ```
> scopo di N   schemas/risk.py · risk_plugins/historical_kpi.py
>              risk_plugins/risk_contribution.py
>              test_services/test_risk_analytics.py · services/risk/acquired.py  (nuovo)
> contaminati  config.py · api/v1/system.py · schemas/common.py · schemas/prices.py
>              test_brokers_api.py · test_scheduler_leader.py · test_scheduler_loop.py
> ```
>
> → **Basta mettere in stage i 5 percorsi per nome.** Il ripristino è **igiene, non un cancello**,
> e può avvenire prima, dopo o mai. **Avevo creato una dipendenza che non esiste.**

```
      commit del checkpoint di N                     ← sblocca I
      (git add dei 5 percorsi PER NOME, mai -A)
              │
              ▼
  I scrive ulcer-index · drawdown-at-risk ·
          conditional-drawdown-at-risk               → 22/22 pagine
              │
              ▼
      integrazione dei rami                          → J si può creare
```

| # | Azione | Chi | Sblocca |
|---|---|---|---|
| **0** | 🔴🔴 **Commit di C — PRIMA DI TUTTO** *(§29: 3 file su 5 esistono **solo su disco**)* | **sviluppatore** | **impedisce una perdita di lavoro** |
| **1** | Commit di **N** mettendo in stage **i 5 percorsi per nome** *(già la forma di §22: `acquired.py` è NUOVO)* | **sviluppatore** | **le 3 pagine di I** |
| **1b** | *(igiene, quando comodo)* `git checkout` dei 7 percorsi contaminati | **sviluppatore** | niente — **non è un cancello** |
| **2** | Commit del **piano** (22 file, solo markdown, in stage qui) | **sviluppatore** | niente — è documentazione |
| **3** | Commit dei checkpoint di **A, B, C, D, F, G, H** — 🔴 **con la procedura di §22**, non `git add -u`: perde fino al **65 %** | **sviluppatore** | l'integrazione |
| **4** | Integrazione secondo §13 | **sviluppatore** | **J** |
| **5** | Creazione di **J** con il brief a 550 righe (§8 e §9 nuove) | coordinatore | il rilascio |

### ⚠️ Due cose che nessuno può fare al posto dello sviluppatore

1. **I 7 file contaminati non sono riparabili da un agente**: il ripristino è una scrittura sul
   worktree di N, che è `FROZEN`, e nessun agente esegue comandi Git che mutano l'albero.
   ⚠️ **Ma non blocca niente**: basta non metterli in stage.
2. **I due PNG** (`mkdocs_src/docs/static/icons/asset-types/{commodity,real-estate}.png`) sono
   **non tracciati e NON ignorati** in almeno tre alberi. Un `git add -A` li committa.

### ✅ Cosa NON è sul percorso critico

- **E** prosegue su L4 e sulla riparazione dei `partial` — non blocca nessuno.
- Le **42 ancore** e i **48 `$$`** sono debiti di J, non bloccanti per l'integrazione.
- Il **blocco di traduzione** ha sei ragioni (§18.6) ma è **posteriore** al rilascio.

## 20. 🔴🔴 Il cancello di integrazione che `git merge` non può dare — **obbligatorio, e non è un conflitto**

> **Un difetto assente da entrambi i genitori, creato dalla loro unione.** Trovato da **A**,
> verificato dal coordinatore sulla baseline. **Non produce conflitto testuale: la fusione è
> pulita e il risultato è sbagliato.**

### Il meccanismo

`RiskReturnBasis` ha **due membri** nella baseline (`schemas/risk.py:42-43`). **Due** siti lo
consumano con un ternario `else`-fallthrough, e su un enum a due valori **sono esaustivi e
corretti**:

```python
drawdown_summary.py:54   "historical_twrr" if … == TWRR else "price_only_close"
historical_kpi.py:109    "historical_twrr" if … == TWRR else "historical_close_returns"
```

**C aggiunge un terzo membro** (`CURRENT_COMPOSITION_BACKTEST`) **altrove nel file**.
→ Dopo la fusione i due ternari **restano binari**, e una stringa chiama **«close returns» un
backtest a pesi correnti**.

> ⚠️ **Nessuno dei due autori può vederlo dal proprio albero.** Nel ramo di A le etichette sono
> **giuste**; nel ramo di C il membro nuovo **non passa da quelle due righe**. `git diff` di A
> mostra `calculation_basis` **solo come contesto**, dentro l'hunk `@@ -52,6 +56,9 @@`.

### ✅ Azione obbligatoria all'integrazione C + A + N

| sito | proprietario | oggi | dopo il terzo membro |
|---|---|---|---|
| `historical_kpi.py:109` | **N** | `historical_twrr` / `historical_close_returns` | **serve un terzo ramo** |
| `drawdown_summary.py` **`:54` baseline · `:58` albero di A** | **A** | `historical_twrr` / `price_only_close` | **serve un terzo ramo** |

### ✅ Il terzo valore, fissato qui — letto nel worktree di C, 18 Set

```python
# schemas/risk.py:44, albero di C
CURRENT_COMPOSITION_BACKTEST = "current_composition_backtest"
# service.py:656 — unico punto in cui C lo imposta
```

⚠️ **C non tocca nessuno dei due ternari** (`grep` sul suo albero: un solo uso oltre alla
definizione). → **il terzo valore delle due stringhe di metodo non esiste ancora: va scelto
all'integrazione.**

✅ **Scelto: `current_composition_backtest`** — lo stesso valore dell'enum. È già il valore sul
filo, è inequivocabile, e **non introduce un quarto nome per la stessa cosa**, che è il difetto
che questo file documenta da tre vicinati diversi (`coverage` ×3, `percentage_contribution`,
`calculation_basis`).

| sito | oggi | dopo |
|---|---|---|
| `historical_kpi.py:109` (**N**) | `historical_twrr` / `historical_close_returns` | **+ `current_composition_backtest`** |
| `drawdown_summary.py` **`:54` baseline · `:58` albero di A** (**A**) | `historical_twrr` / `price_only_close` | **+ `current_composition_backtest`** |

📌 **A si è dichiarata disponibile a scrivere il proprio sito in un minuto**, dato il valore.
**Eccolo.**

**Chi fonde deve**:

1. `grep -rn "RiskReturnBasis" backend/app/` sul **risultato fuso** — non su un genitore;
2. verificare che **ogni** consumatore copra i **tre** membri;
3. allineare le due stringhe al valore che **C** ha scelto per il proprio sito;
4. **A si è dichiarata disponibile** a scrivere `drawdown_summary.py` in un minuto, dato il valore.

### 🔑 Perché questo cancello non somiglia a nessun altro di §13 e §15

| | |
|---|---|
| §15 cataloghi del runner | **due scrittori sullo stesso blocco** → conflitto **certo e visibile** |
| §20 *(questo)* | **zero sovrapposizione testuale** → fusione **pulita**, difetto **muto** |

> **Un conflitto si risolve leggendo il diff. Questo si trova solo interrogando il risultato
> fuso con una domanda che nessun diff pone: «l'enum è ancora esaustivo?»**

📌 **Regola generale per l'integrazione**: dopo ogni fusione che tocca un `StrEnum`, cercare i
consumatori **nel risultato**, non nei genitori. Un `else` è esaustivo **rispetto a un numero di
membri**, e quel numero **cambia in un altro file**.

### 20.1 🔴 E lo stesso enum ha un secondo consumatore muto, sul frontend

`RiskResultFrame.svelte:108` costruisce **una chiave i18n dinamica**:

```svelte
{$t(`risk.returnBasis.${metadata.return_basis}`)}
```

Chiavi esistenti alla baseline: **`price_only`, `twrr`**. → **Nel minuto in cui C integra, il frame
stampa a schermo `risk.returnBasis.current_composition_backtest`.**

⚠️ **E cade su pagine di nessuno dei due mandati**: `RiskResultFrame` è montato da
`RiskAnalysisPanel`, cioè **Asset Detail e Risk Lab**. ✅ **E ha già aggiunto le quattro stringhe**
(namespace suo, additivo) — **ma la forma resta**:

> **Una chiave i18n dinamica trasforma ogni nuovo valore d'enum in un difetto visibile, e
> `i18n audit` non può vederlo: non sa quali chiavi vengono costruite a runtime.**

🔑 **Stessa causa del §20, due strati più su.** Un enum che cresce in un file e viene consumato in
un altro: sul backend diventa **un ternario non esaustivo**, sul frontend **un buco di traduzione**.
**Lo stesso rilevatore per entrambi: nessuno.**

✅ **Terza voce del cancello**: chi aggiunge un membro a un enum reso a schermo deve cercare **anche
le chiavi costruite con template literal**, non solo quelle letterali —
`grep -rn 'risk\.[a-zA-Z]*\.\${' frontend/src`.

## 21. 📌 Come leggere questo documento senza esserne ingannati

> **Questo registro è un indice della campagna, non uno stato vivo.** Ogni riga è stata vera
> quando è stata scritta. **Sette volte in un giorno una riga di registro è risultata indietro
> rispetto al lavoro** — e due volte l'errore è andato nella direzione opposta, cioè il registro
> descriveva lavoro **non ancora fatto** che era **già finito**.

### Le quattro fonti, in ordine di autorità

| # | fonte | cosa dice | quando mente |
|---|---|---|---|
| **1** | il **codice** e i comandi eseguiti | ciò che è | mai |
| **2** | `implementation/progress/<X>-esecuzione.md` | lo stato del mandato X | quasi mai — X lo aggiorna **dopo ogni passo** |
| **3** | `04-decisioni-e-questioni-aperte.md` | perché si è deciso così | quando una decisione è ritrattata **e non marcata** |
| **4** | **questo file** | la mappa fra i mandati | **ogni volta che un mandato avanza e nessuno lo riscrive** |

> 🔑 **Prima di scrivere a un mandato, si apre il suo piano vivo (D212) e si legge §18.5 (voci
> chiuse). Questa tabella §18 si usa per sapere CHI, non per sapere A CHE PUNTO.**

### Le quattro cure adottate, e cosa copre ciascuna

| cura | copre | scoperta da |
|---|---|---|
| il **piano vivo** aggiornato dopo ogni passo | lo stato **del mandato** | regola di progetto |
| **§18.5, voci chiuse con ⛔** | ciò che il coordinatore **non deve richiedere** | A, dopo quattro ordini su passi chiusi |
| la **tabella misurata in testa a ogni rapporto** | lo stato che il **mandato** riferisce | I |
| lo **stato presunto allegato a ogni ordine** | lo stato che il **coordinatore** crede | I |

> **Le prime tre rendono leggibile lo stato del mandato. Solo la quarta espone l'errore PRIMA
> del lavoro**, perché mette a confronto due credenze invece di una credenza e un fatto.

### 🔑 E la ragione strutturale per cui tutto questo è servito

> **«Stessa causa, esito opposto — e la differenza è solo se il disaccordo ti arriva da fuori o
> no. Quando arriva da fuori si allarga. Quando arriva da sé stessi si chiude.»** — I
>
> Non è un difetto di rigore: **è una proprietà della posizione.** Undici mandati in parallelo
> hanno funzionato meglio di uno solo più attento **non perché siano più bravi, ma perché sono
> l'uno fuori dall'altro**. Ogni mandato ha trovato false premesse nel brief scritto per lui —
> **oltre settanta** — e nessuna di quelle premesse era stata misurata prima di partire.

### 21.1 🔑 «Il *se* è tuo, il *come* è mio» — la divisione di autorità, trovata all'ultimo

**A ha rifiutato la Fascia 1 di M6 tre volte, poi l'ha eseguita**, e la ragione del ribaltamento
è la cosa più utile di tutta la coordinazione:

> *«La mia obiezione **non reggeva come rifiuto**. Non era "la migrazione è sbagliata" — era
> "distruggerebbe l'oracolo", e **quello è riparabile**.»*

| il mandato dice | è | cosa deve fare |
|---|---|---|
| *«l'obiettivo è sbagliato»* | una questione di **se** | **riferire e attendere** — il *se* non è suo |
| *«il metodo proposto distrugge qualcosa»* | una questione di **come** | **riparare il metodo e procedere** — il *come* è suo |

⚠️ **A aveva trattato il secondo caso come il primo per tre messaggi. E il coordinatore aveva
accettato il rifiuto tre volte senza chiedere se fosse riparabile.** Nessuno dei due ha fatto la
domanda giusta finché A non se l'è fatta da sé.

📌 **Chiarisce retroattivamente ogni rifiuto legittimo della campagna** — G su un cancello non
esprimibile, F su `ui/select/` che non è suo, I sulle pagine con campi non committati, B su
un'attribuzione senza bisezione: **nessuno era un rifiuto dell'obiettivo, erano rifiuti del
metodo proposto.**

### 21.2 📌 Il collo di bottiglia di `metrics.py` è la validazione, non l'aritmetica

**Misurato due volte, su due funzioni diverse:**

| | `_finite_values` | matematica |
|---|---|---|
| **M3** | **13,22 ms — il 61 %** | 2,76 ms |
| **M6 Fascia 1** | **~37 %** di *entrambi* i rami | — |

> **Vettorializzare una funzione che prende una lista e restituisce una lista non compra quasi
> nulla**: `np.cumprod` sta fra **due conversioni O(n) con boxing** che costano lo stesso ordine
> del ciclo che sostituiscono. **Guadagno 15 %**, non le decine di volte che la vettorializzazione
> promette altrove.

✅ **Questo RAFFORZA le esclusioni delle Fasce 0, 2 e 3**, perché erano stimate col modello
*«il ciclo Python è lento»* — **ottimista per lo stesso motivo.**

## 22. 🔴🔴 Come mettere in stage ogni mandato — **`git add -u` perde fino al 65 % del lavoro**

> **Trovato da I su se stesso**: riportava `git diff --stat` → **10 file**, e la sua consegna vera
> erano **29**. *«Se avessi messo in stage sulla base di ciò che ti ho riportato, **17 pagine su
> 19 restavano fuori**.»* **E chi mette in stage è il coordinatore.**

### 📊 Misurato su tutti i mandati — 18 Set 04:10

| mandato | tracciati modificati | **file nuovi** | PNG estranei | perso con `git add -u` |
|---|---:|---:|---:|---:|
| **E** vigilant-adventure | 13 | **24** | 2 | 🔴 **65 %** |
| **I** analysis-documentation | 10 | **19** | 2 | 🔴 **66 %** |
| **F** asset-global-lab | 10 | **13** | 2 | 🔴 **57 %** |
| **D** primitives-cards | 6 | **10** | 2 | 🔴 **63 %** |
| **G** g-allocation-colors | 5 | 4 | 2 | 44 % |
| **B** taxonomy-benchmark | 25 | 3 | 2 | 11 % |
| **A** oracle-math-migration | 14 | 2 | 2 | 13 % |
| **H** h-monte-carlo | 15 | 2 | **0** | 12 % |
| **N** n-backend-acquisizioni | 11 | 2 | 2 | 15 % |
| **C** c-portfolio-slicing | 5 | 1 | 2 | 17 % |

> 🔑 **La perdita è proporzionale a quanto un mandato ha CREATO invece che modificato.** I quattro
> peggiori sono quelli che hanno scritto pagine nuove, componenti nuovi, spec nuovi — cioè
> **il lavoro di maggior valore è quello che `git add -u` non vede.**

### ✅ La forma corretta, per ogni mandato

```bash
W=<worktree>
git -C "$W" add -u                                    # i tracciati modificati
git -C "$W" ls-files --others --exclude-standard \
  | grep -v 'static/icons/asset-types/.*\.png$' \
  | xargs -r git -C "$W" add                          # i NUOVI, esclusi i 2 PNG estranei
git -C "$W" status --short                            # verifica: nessun '??' oltre ai 2 PNG
```

⚠️ **I due PNG** `mkdocs_src/docs/static/icons/asset-types/{commodity,real-estate}.png` sono
**non tracciati e NON ignorati in nove worktree su dieci** — portati da una semina del
coordinatore che aveva verificato **il percorso e non il contenuto** (D208). **`H` è l'unico
pulito.**

### 🔴 22.1 Il cartello «65 % perso» induce `git add -A`, che raccoglie anche le icone

**Trovato da E sulla procedura scritta qui sopra**, e verificato dal coordinatore nel suo albero:

```
non tracciati totali : 27      ← non 25
di cui PNG estranei  :  2
mtime dei PNG        : 00:17   ← IDENTICO ai 10 fratelli tracciati
```

> *« Mi hai identificato come il caso peggiore — **65 % invisibile a `git add -u`**. **La reazione
> naturale a quel cartello è `git add -A`.** Che nel mio worktree stagia **27**, non 25. »*

🔑 **E il motivo per cui nessuno se ne accorgerebbe**: *« **Sono mimetizzati dalla propria
directory**: dieci fratelli identici, stesso mtime, nomi esatti dei tipi di asset. In un diff da
38 file, **`commodity.png` accanto a `bond.png` non attira lo sguardo di nessuno.** Non un
artefatto che *sembra* sbagliato — **uno plausibile**. »*

⚠️ **E se entrano nel commit di E, la provenienza di B è persa proprio mentre B si innesta.**

> ## 🔴 CORREZIONE — i due `.png` **non sono di B**, e l'avvertimento vale per **tutti e dieci**
>
> E li aveva attribuiti a **B** per mtime e contesto. **Misurato su tutti gli alberi:**
>
> ```
> 2 png → e-alfy-crispy-journey      2 png → e-alfy-solid-couscous
> 2 png → e-alfy-ideal-eureka        2 png → e-alfy-solid-engine
> 2 png → e-alfy-improved-meme       2 png → e-alfy-super-dollop
> 2 png → e-alfy-legendary-succotash 2 png → e-alfy-vigilant-adventure
> 2 png → e-alfy-miniature-train     2 png → e-alfy-shiny-broccoli
> ```
>
> **Dieci alberi su dieci, incluso il mio.** Non sono di un mandato: **sono dell'ambiente**,
> seminati dal bootstrap dei worktree.
>
> ⚠️ **E qualcuno li ha già raccolti**: `git log --all -- commodity.png` li trova in **tre
> checkpoint** di **sessioni diverse** — cioè **uno stage automatico `-A` li ha già presi tre
> volte**, in alberi di mandati che non c'entrano nulla con le icone.
>
> 🔑 **Quindi l'avvertimento non è "le icone di B finiscono nel commit di E": è che DUE FILE
> DELL'AMBIENTE finiscono nel commit di CHIUNQUE usi `git add -A`** — e in un diff di
> documentazione o di backend, **due `.png` in `mkdocs_src/` non li nota nessuno.**
>
> ✅ **L'oracolo corretto vale per tutti e dieci**:
> `git ls-files --others --exclude-standard | grep -c asset-types` → **deve dire 2 prima dello
> stage e 2 dopo.** Se dopo dice `0`, sono entrati.

### ✅ 22.2 I tre oracoli del post-stage — *un'occhiata non è una verifica*

**Dopo ogni stage, prima di ogni commit:**

> ## 🔴 L'oracolo scritto qui il giro scorso era **SBAGLIATO DI UN FATTORE 3,5**, e sbagliava
> ## **per difetto** — cioè nella direzione che fa credere di aver messo al sicuro tutto
>
> **Corretto da E, che me l'aveva dato lui stesso il giro prima.**
>
> ```bash
> git status --porcelain | grep -c '^??'        →   9      ← ❌ ciò che dicevo di contare
> git ls-files --others --exclude-standard      →  27      ← ✅ ciò che c'è davvero
> ```
>
> 🔑 **`git status` COLLASSA le directory.** *« Una riga sola — `?? .../risk/levels/` — **ne
> nasconde 19**: tutti e quattro i livelli, il contenitore, gli helper, gli unitari. **L'intera
> consegna del mandato dietro una riga.** »*
>
> *« Chi conta le righe conclude **"9 non tracciati, 2 di B, quindi 7 miei"**. Sono **25**. »*

**Oracoli corretti — ENUMERARE, mai contare le righe di `git status`:**

```bash
git ls-files --others --exclude-standard | wc -l         # i file NUOVI, uno per riga
git ls-files --others --exclude-standard | grep -c mkdocs_src   # deve dire 0 (o 2 per E: sono di B)
git diff --cached --name-only | wc -l                    # il conteggio atteso dopo lo stage
```

> **Tre numeri chiudono la questione, e nessuno dei tre richiede di fidarsi di chi consegna.**

✅ **I due `.png` di B restano righe proprie** anche in `git status` — la loro directory è già
tracciata, quindi non vengono collassati. **L'avvertimento su `git add -A` regge**; è solo il
*conteggio* che era cieco.

📌 **E la forma preferibile resta l'enumerazione, non l'esclusione**: `git add <percorsi>`
invece di `git add -A` filtrato. **Un'esclusione dimenticata stagia; un'enumerazione dimenticata
lascia fuori** — e il secondo errore è **visibile nel conteggio**, il primo no.

### 🔑 Perché questo non è un dettaglio di procedura

**Tre registri dicevano tre numeri diversi per lo stesso lavoro**, e nessuno dei tre era falso:

| chi | numero | cosa misurava |
|---|---:|---|
| I al coordinatore | **10 file** | `git diff --stat` — **solo i tracciati** |
| il coordinatore in §18.4 | **7 + 21** | `diff` + `ls-files --others` |
| la consegna vera | **29 file** | il lavoro |

> **Ognuno ha risposto alla domanda che il proprio comando poneva.** È D180 — *«un numero
> dichiara CHE COSA ha misurato»* — applicata al momento in cui costa di più: **alla vigilia del
> commit**, dove il numero non descrive il lavoro ma **lo seleziona**.

## 23. 🔴🔴 Vincolo di sequenza: **la documentazione di I non può entrare prima del codice di A**

> **Trovato da `docs-writer`, verificato da I, riverificato dal coordinatore sulla baseline.**

```python
# metrics.py:625 — BASELINE cc33120eb
conditional_value_at_risk = math.fsum(tail) / len(tail)   # media UNIFORME = stimatore VECCHIO
```

**La correzione Acerbi-Tasche che le pagine `value-at-risk` e `conditional-value-at-risk`
descrivono AL PASSATO non è in questa baseline.** Vive **solo nel worktree di A**.

| se atterra prima | conseguenza |
|---|---|
| **I, poi A** | 🔴 **spediamo pagine che dichiarano corretto uno stimatore che il prodotto non usa**, e dicono all'utente *«un numero che potresti già aver visto è cambiato»* mentre **non è cambiato** |
| **A, poi I** | ✅ ogni affermazione delle pagine è vera dal primo istante |

> ### 🔑 Terza forma della famiglia, e la peggiore delle tre
>
> | forma | rilevatore |
> |---|---|
> | **1.** un contratto descrive codice **non scritto** | **fallisce appena lo esegui** |
> | **2.** codice **spedisce senza pagina** | nessuno — **silenzio** |
> | **3.** una **pagina descrive codice non spedito** | **nessuno, e tutti i gate restano verdi** |
>
> **La 3 è peggio della 2: il silenzio è un'omissione, questa è un'affermazione falsa in faccia
> all'utente.** E i tre gate di I — build strict, `check-links`, ancore — **sono tutti verdi,
> perché nessuno di loro sa cosa calcola `metrics.py`.**

### 🔴 Correzione del 18 Set: vale per **tutte e cinque** le pagine, non solo per VaR/CVaR

Il vincolo era stato scritto per le due pagine M2, dando per coperte le tre drawdown perché
`acquired.py` esiste nel checkpoint `1aaea6949`. **Falso**, misurato:

```
git branch -a --contains 1aaea6949   ->  VUOTO
git for-each-ref --contains 1aaea6949
  ->  refs/copilot/checkpoints/da23d09e-…     UNICO ref
```

> **Nessun ramo lo contiene.** `ulcer-index`, `drawdown-at-risk` e `conditional-drawdown-at-risk`
> sono **nello stesso stato di VaR/CVaR**: descrivono codice **che non sta in alcuna linea di
> storia rilasciabile**. Solo, con prova migliore che esiste e corrisponde.

🔑 **E la forma dell'errore, nominata da I**: *« ho usato `git cat-file -t` — strumento
**agnostico alla raggiungibilità** — per una domanda **di raggiungibilità**. Prova che l'oggetto
**esiste nello store**; non dice nulla su quale ref lo raggiunga. **La risposta che dà è vera e
rassicurante, e non è la risposta alla domanda.** »*

✅ **Regola corretta**: **`cat-file -t` prova l'ESISTENZA; serve `git branch --contains` per la
STORIA.** Due domande diverse, e **il primo comando non accenna che la seconda esista**.

### ⚠️ E lo stesso vale per N

`ulcer-index`, `drawdown-at-risk`, `conditional-drawdown-at-risk` sono **stub onesti** proprio
perché I si è rifiutato di descrivere campi non committati. **Quella disciplina va estesa alle
due pagine M2**: sono l'unico punto dove I ha descritto **codice di un altro mandato**.

### ✅ Ordine minimo obbligato

```
A (stimatore M2)  ──┐
                    ├──►  I (le due pagine VaR/CVaR)
N (acquired.py)   ──┘     e le tre pagine drawdown
```

📌 **Non è un ordine di preferenza: è l'unico che non pubblica una falsità.** Va aggiunto ai
vincoli di §13 e verificato **dopo** la fusione, non prima — con `grep -n "conditional_value_at_risk"
backend/app/services/risk/metrics.py` sul **risultato fuso**.

## 24. ⚠️ `T` non è la lunghezza della storia — e l'orizzonte predefinito è il caso peggiore

`metrics.py:605` → `range(len(values) - horizon_days + 1)` ⟹ **`T = N − h + 1`**.

E `h` **è un campo rivolto all'utente**: `historical_var.py:37` → `Field(1, ge=1, le=365, …)` con
`x-i18n-key`. **Lo studio di A fissava `h = 1`, quindi `T = N`.**

| `h` | 250 · 500 · 750 · 1000 · 1250 · 2000 |
|---|---|
| **1** *(predefinito)* | **colpite** secondo la divisibilità |
| **10** | **tutte e sei NON colpite**, a tutti e tre i livelli |

> 🔑 **L'orizzonte predefinito è esattamente la configurazione in cui le storie "pulite" sono
> colpite.** Una `N` tonda a `h = 10` dà un `T` che **finisce per 1**: mai divisibile per 10, 20
> o 100.

⚠️ **Per J**: la voce di CHANGELOG deve dire che **il confronto fra due analisi richiede anche
l'orizzonte**, non solo finestra e livello di confidenza. **La regola dell'intero era corretta per
il caso studiato, e generalizzata a un parametro che nessuno aveva letto.**


## 25. 🔴🔴 Ogni fatto verificato per SHA in questa campagna **ha una scadenza**

**Misurato su tutti e tre gli SHA che la campagna ha usato per il relay:**

```
git branch -a --contains 1aaea6949   (N)  ->  0 rami
git branch -a --contains 1a537f9cb   (D)  ->  0 rami
git branch -a --contains 590f32ae6   (B)  ->  0 rami
```

**Nessuno dei tre è raggiungibile da un ramo.** Vivono **solo** sotto `refs/copilot/checkpoints/`.

> 🔑 **Un ref di checkpoint è cancellabile, e alla cancellazione il commit diventa
> irraggiungibile e potabile dal GC.** → **Tutte le verifiche incrociate di questa campagna —
> le primitive di D, la forma di B, i sei fatti di N — poggiano su oggetti che possono sparire.**

⚠️ **Conseguenza per la consegna, ed è un argomento di URGENZA, non di ordine:**

| | |
|---|---|
| **finché i checkpoint esistono** | ogni fatto relayato è **riverificabile da chiunque** |
| **dopo la loro potatura** | i fatti restano veri **ma non più ripetibili**, e i documenti diventano **affermazioni senza indirizzo** |

✅ **Il commit dei mandati non è solo il passo successivo: è ciò che trasforma una prova
temporanea in una permanente.** Chi consegna dopo la potatura deve rimisurare da zero.

📌 E la regola generale che I ne trae, che vale oltre Git:

> **Tre artefatti interrogati su domande a cui non rispondono, in tre turni consecutivi:**
>
> | artefatto | risponde a | è stato letto come |
> |---|---|---|
> | `git diff --stat` | cosa è **tracciato** | « cosa ho cambiato » |
> | catalogo i18n | la stringa è **tradotta** | « la UI la mostra » |
> | `git cat-file -t` | l'oggetto **esiste** | « è in storia » |
>
> **Ogni volta la risposta era vera.** Il difetto non era nello strumento: era **nella domanda che
> gli si attribuiva**.

## 26. 🔴🔴 `api sync` dopo l'integrazione — **non è un merge da ordinare, è un rosso bugiardo da prevenire**

> **Trovato da E, verificato dal coordinatore eseguendo gli schemi Zod.**

Il client usa **`validate: 'response'`** (`zodios-client.ts:170`). Da lì **due comportamenti opposti**:

| cosa cambia nel backend | cosa fa Zod | sintomo |
|---|---|---|
| **un campo nuovo** (K8, K1) | `z.object()` **senza `.passthrough()`** lo **cancella** | ✅ `success: true`, il lettore vede **`undefined`** — **silenzio** |
| **un valore d'enum nuovo** (K4, C) | l'enum è **chiuso**, il campo è **obbligatorio** | ❌ **l'intera risposta è rifiutata** |

**Misurato**: `RiskReturnBasis.safeParse('twrr')` → **OK** · `safeParse('current_composition_backtest')` → **REJECTED**.
`RiskKpiOutput` con i campi di N → **tenute solo 4 chiavi su 6**.

### ✅ Ma non c'è nessun ordine di merge da decidere

```
git check-ignore -v frontend/src/lib/api/generated.ts  →  frontend/.gitignore:13
dev.py:563-566  →  il build chiama api sync e ABORTA se fallisce
```

> **`generated.ts` non è versionato, e il build lo rigenera sempre. Produzione e CI sono protetti
> per costruzione: un frontend non può essere buildato contro uno schema stantio.**

### 🔴 Il rischio è negli **alberi di sviluppo**, e il sintomo accusa la cosa sbagliata

**Ogni worktree ha un `generated.ts` stantio sul disco.** Dopo l'integrazione del backend di C:

> chi esegue un gate frontend **senza rigenerare** vede **tutti e quattro i pannelli di rischio in
> errore** — Dashboard, Broker Detail, Asset Detail, Risk Lab — e conclude che **qualcuno ha rotto
> il codice**.

**È un difetto di diagnosi, non di prodotto.** Stessa forma del rosso bugiardo di §20 e di D226.

### ✅ Vincolo operativo

```bash
# dopo che il backend integrato è nell'albero, PRIMA di qualunque gate frontend
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync
```

📌 **E una conseguenza per i contratti**: il criterio *«costruisci lasciando il posto dove entrambi
i rami sono esercitabili»* (§18.2 / D290) **è insoddisfacibile per ogni contratto che cambia la
forma del payload** — **Zod toglie il campo prima che il componente lo veda**, quindi una fixture
col campo nuovo *«non esercita il ramo presente: lo esercita come assente, e passa»*.
**K1, K4 e K8 si aspettano; non si anticipano.**


## 27. 🟢 **Tutti e dieci i mandati sono `FROZEN`** — 18 Set 2026, 06:15

| | mandato | delta | ⚠️ perso con `git add -u` |
|---|---|---|---:|
| **A** | oracolo e migrazione (A0→A18) | 14 + 2 | 13 % |
| **B** | tassonomia e benchmark | 25 + 3 | 11 % |
| **C** | affettamento portafoglio | 5 + 1 | 17 % |
| **D** | primitive e card | 6 + 10 | 🔴 63 % |
| **E** | quattro livelli | **13 + 25** | 🔴 **65 %** — il peggiore · `risk` E2E **12** |
| **F** | laboratorio | 10 + 13 | 🔴 57 % |
| **G** | colori allocazione | 5 + 4 | 44 % |
| **H** | Monte Carlo | 15 + 2 | 12 % |
| **I** | documentazione (22/22 pagine) | 10 + 19 | 🔴 66 % |
| **N** | acquisizioni | 11 + 2 | 15 % |

> **Nessun mandato ha committato.** Tutti gli HEAD sono a **`cc33120eb`**; il lavoro vive nei
> worktree e nei checkpoint, **e nessun checkpoint è raggiungibile da un ramo** (§25).

### 📊 Il totale, misurato

```
tracciati modificati : 114
file nuovi           :  81
────────────────────────────
TOTALE non committato: 195 file      →  git add -u da solo ne perderebbe il 41 %
```

⚠️ **81 file nuovi in dieci alberi.** Sono componenti, spec, pagine e moduli: **il lavoro di
maggior valore della campagna è esattamente quello che `git add -u` non vede.**

### ✅ Cosa resta, in ordine

1. **Commit dei dieci mandati** — procedura §22, **mai `git add -u` da solo**.
2. **Commit del piano** (23 file in stage in questo worktree, solo markdown).
3. **Integrazione** secondo §13, con i cancelli §20 / §20.1 / §23 / §26.
4. **Creazione di J** con il brief a **694 righe** (§8-§11 nuove).

### 🔑 E il consuntivo che vale la pena leggere per primo

**Oltre settanta premesse false** trovate dai mandati nei brief scritti per loro, e **dodici
decisioni operative del coordinatore** ribaltate da chi le eseguiva. Nessuna di quelle premesse
era stata **misurata** prima di partire.

> **La forma più cara non è l'errore: è il verde.** — B, contando i propri 44 reperti:
> *« i tre più costosi erano tutti **falsi positivi del verde**. Il comando passava, il test
> passava, e la conclusione che se ne traeva era falsa. »*


## 28. 🔨 Quarta riapertura — **E**, e come le tre precedenti non nasce da un ripensamento

| mandato | perché riaperto | chi l'ha trovato |
|---|---|---|
| **B** | la sua correzione duplicava un `data-testid` | **F**, che ha rifiutato di ripararlo: non era suo |
| **F** | **due delle sue sei reti non discriminavano** | **F stesso**, da fermo |
| **G** | lo stub K2 portava la semantica sbagliata del coordinatore | **G stesso** |
| **E** | **L4 rende il NULLA su `unavailable`** | **E stesso**, verificando una correzione che non lo toccava |

> **Nessuna delle quattro nasce da un ripensamento.** Tre le hanno trovate i mandati **su sé
> stessi**; una un mandato **sul lavoro di un altro, fermandosi al confine di proprietà**.

### ✅ Perché questa è stata autorizzata, mentre K1/K6/K8 restano spenti

**Misurato, ed è una riga di differenza:**

| | nel contratto? | ramo esercitabile oggi? |
|---|---|---|
| **K1 · K6 · K8** — campi **nuovi** | ❌ **zero in baseline** | ⛔ **no**, Zod li cancella |
| **L4 `unavailable`** — **stato esistente** | ✅ **45 occorrenze** in `generated.ts` | ✅ **sì** |

➕ **E `schemas/risk.py:1056` rende il difetto strutturale**:
`raise ValueError("unavailable or failed results must not include output")` → **il backend
garantisce che un `unavailable` non ha output**, quindi `{#if output}` su quel ramo **non è
"probabilmente vuoto": è vuoto per contratto.**

📌 **Regola operativa**: **prima di dichiarare un innesto impossibile, contare il simbolo in
`generated.ts`.** Un **campo nuovo** è invisibile finché `api sync` non gira dopo la fusione;
**uno stato già spedito è esercitabile subito.** **Due casi opposti che sembrano lo stesso
«aspetta l'integrazione».**


## 29.0 🔴🔴🔴 **CORREZIONE A §29 — il titolo qui sotto è falso, e il conteggio è un limite inferiore**

> **§29 dice «unico caso» e «3 file». Entrambi sbagliati**, per la stessa ragione: il metodo
> confrontava **md5 sui file tracciati** — **il 35 % del delta**. **La misura corretta è in §33.**
>
> | §29 diceva | la misura corretta dice |
> |---|---|
> | C è **l'unico** a rischio | 🔴 **otto mandati su dieci** |
> | C ha **3** file a rischio | 🔴 **4** — i 3 tracciati **più il suo piano vivo** |
> | D è al sicuro (`1a537f9cb` verificato) | 🔴 **D ha SETTE file disk-only, incluse le tre primitive** |
>
> ✅ **Ciò che resta valido di §29**: i 3 file *tracciati* di C divergono davvero dal suo
> checkpoint, e C resta il caso peggiore **tra i tracciati**. È il perimetro, non il fatto,
> a essere stato sbagliato.

## 29. 🔴🔴🔴 **Il lavoro di C esiste solo sul filesystem** — unico caso, e va committato per primo

> **Innescato da E**, che ha letto il timestamp dei checkpoint di C. **Verificato dal coordinatore
> confrontando md5 file per file su tutti e sei i mandati misurabili.**

```
ultimo checkpoint di C : 3bd422bb2   2026-09-18 02:20:28
```

| mandato | file divergenti / modificati |
|---|---|
| **C** | 🔴 **3 / 5 — SOLO SU DISCO** |
| A · B · N · I · E | **0** su 14 · 25 · 11 · 10 · 13 ✅ |

**I tre file di C che non esistono in nessun oggetto git:**

```
backend/app/schemas/risk.py                          ← contiene CURRENT_COMPOSITION_BACKTEST
backend/app/services/risk/service.py
backend/test_scripts/test_services/test_risk_service.py
```

### 🔴 È più grave di §25, ed è una classe diversa

| | |
|---|---|
| **§25** | i checkpoint **esistono** ma **nessun ramo li raggiunge** → potabili dal GC |
| **§29** | per C **non esiste nemmeno un checkpoint** che contenga il lavoro |

> **Se quel worktree si perde, il lavoro si perde: non c'è copia in git.** E **C è il mandato da
> cui dipende il cancello §20** — il terzo membro dell'enum che rende non esaustivi i due ternari.

⚠️ **E spiega retroattivamente D273**: il coordinatore aveva letto `CURRENT_COMPOSITION_BACKTEST`
**sul filesystem di C**, dichiarandolo *«non committato»*. **Era più vero di quanto sapesse: non
solo non committato — non esiste in nessun oggetto git.**

### ✅ Azione: **C prima di tutto**

```bash
W=<worktree-di-C>
git -C "$W" add -u
git -C "$W" ls-files --others --exclude-standard \
  | grep -v 'asset-types/.*\.png$' | xargs -r git -C "$W" add
git -C "$W" status --short     # nessun '??' oltre ai 2 PNG
# poi il commit
```

📌 **Il comando che ha trovato il caso, riutilizzabile su qualunque mandato:**

```bash
ck=$(git for-each-ref --sort=-committerdate \
     --format='%(objectname:short)' "refs/copilot/checkpoints/<session-id>/**" | head -1)
git -C "$W" diff --name-only | while read f; do
  [ "$(md5 -q "$W/$f")" = "$(git show "$ck:$f" | md5 -q)" ] || echo "SOLO SU DISCO: $f"
done
```

## 30. ⚠️ Livello di prova dei venti debiti — **uno era falso, ed è stato trovato dal mandato accusato**

> Il **debito 11** diceva *«i risultati `partial` spariscono — `okOutput` pretende `'ok'`»*.
> **E l'ha confutato col codice**: `levelHelpers.ts:46` rifiuta ciò che **non è né `ok` né
> `partial`** — **un `partial` passa**. Due test lo portano **nel nome**. **Ritirato.**
>
> **Se uno su venti era falso, gli altri diciannove vanno letti col loro livello di prova
> accanto** — che è la disciplina che i mandati hanno imposto a questo registro per tutta la
> campagna, e che al registro stesso non era stata applicata.

| # | debito | livello di prova |
|---|---|---|
| 1 | spec che accusa il file che modifichi (2/3) | 🟢 **misurato** — 3+3 corse in lane 6250 |
| 2 | baseline non conforme al proprio formattatore | 🟢 **misurato** — `black --diff` = 72 righe identiche |
| 3 | 42 ancore solo-inglesi | 🟢 **misurato** da I sull'HTML costruito |
| 4 | 48 `$$` non renderizzati | 🟢 **misurato** da I, per lingua |
| 5 | `correlation` chiesta e non resa | 🟢 **misurato** da E + proprietario identificato |
| 6 | `fresh_quote_coverage` calcolato e non letto | 🟢 **misurato** da A **e** da I, indipendentemente |
| 7 | due PNG estranei | 🟢 **misurato** su 9 worktree su 10 |
| 8 | `verbose` di `SharedBackend` inerte | 🟡 **letto** — `_server.py:161,269-270`, non eseguito |
| 9 | `percentage_contribution` porta una frazione | 🟢 **misurato** da E, e il raggio da me |
| 10 | `risk-asset-add-button` rimosso | 🟢 **misurato** da F, verificato da me sulla baseline |
| ~~11~~ | ~~i `partial` spariscono~~ | 🔴 **FALSO — ritirato (D338)** |
| 12 | `warnings` non resi | 🟢 **chiuso**, provato per mutazione |
| 13 | `if (!var_bin_edge)` | 🟡 **letto** — il caso è raggiungibile, non osservato |
| 14 | divieto d'import di `SemiDeviation` | 🟢 **misurato** — unico altro import è il worker |
| 15 | 24 stringhe i18n orfane | 🟢 **misurato** — 6 chiavi × 4 lingue, zero consumatori |
| 16 | nessuna pagina developer del rischio | 🟢 **misurato** — `find` vuoto |
| 17 | `scripts/` fuori da entrambi i gate | 🟢 **misurato** — `black --check` EXIT=1 su baseline |
| 18 | il proxy automatico non esiste | 🟢 **misurato** — enum a un valore, `raise` al primo asset |
| 19 | `coverage` accanto a Sharpe in produzione | 🟢 **misurato** — `RiskResultFrame:99` + `:833` |
| 20 | K1/K6/K8 spenti sul filo | 🟢 **misurato** — zero occorrenze in baseline, presenti negli alberi |

> **Due voci restano `letto, non eseguito` (8 e 13)** — e sono dichiarate tali, non promosse.
> **Chi le raccoglie deve eseguirle prima di agire**, esattamente come A ha preteso per il rename
> di `coverage`: *«chi esegue il rename lo confermi sul servizio che popola il campo»*.

## 31. 🔴 Una coppia **atomica su due alberi** — F e E, e non esiste un ordine sicuro

> **Classe distinta da §20.** Là un difetto **nasce dall'unione** di due modifiche ciascuna
> corretta. **Qui due modifiche sono ciascuna rossa da sola, e verdi solo insieme.**

| | oggi |
|---|---|
| `AssetSetRiskPanel:135` | `onchange={(value) => (addAssetId = value)}` — **solo stato** |
| `AssetSetRiskPanel:138` | il bottone `risk-asset-add-button` **conferma** |
| **F** | ha **collassato i due passi in uno** e **rimosso il bottone** |
| **E**, spec `:1092` | **clicca quel bottone** |

```
togliere la riga di E  PRIMA  di innestare F   →  🔴 rosso subito
innestare F  SENZA  togliere la riga di E      →  🔴 rosso
```

> ## **Le due modifiche devono atterrare nella stessa revisione. Non c'è un ordine sicuro: c'è solo la simultaneità.**

⚠️ **E i numeri di riga del rapporto di F non valgono nell'albero di E**: lo spec è cresciuto da
**817 a 1748** righe, **offset +438**. `:652-654` del rapporto sono **`:1090-1092`** da E —
*«con i numeri del rapporto la correzione cadrebbe **dentro un altro test**»*.

### ✅ Ma la cancellazione è sicura **per costruzione**, e non richiede di verificare F

```
:1089  expect(risk-selected-asset-${id}).toHaveCount(0);    ← appena rimosso
:1092  click('risk-asset-add-button');                      ← da togliere
:1093  expect(risk-selected-asset-${id}).toBeVisible();     ← ORACOLO
```

> **Se `onchange` non aggiunge davvero, `:1093` diventa rosso da solo.** La cancellazione **non
> può rendere il test vacuo**, perché **l'asserzione non nomina il meccanismo: nomina il
> risultato.**

🔑 **È la famiglia del mock stantio allo specchio**: là nessuno controlla e il verde rassicura;
qui **qualcosa controlla**, quindi la rimozione è sicura senza dipendere da un rapporto
proveniente da un albero che non si può leggere.

📌 **Regola generale**: **un'asserzione che nomina il RISULTATO sopravvive alla rimozione del
passo che lo produceva; una che nomina il MECCANISMO no.** Scrivere l'oracolo sul risultato è ciò
che rende una cancellazione futura **verificabile senza il contesto che l'ha motivata**.

### 📌 E il meccanismo del difetto originale, finalmente spiegato

```svelte
SearchSelect:377   data-testid={testId ? `${testId}-trigger` : undefined}   ← DERIVATO dal prop
SearchSelect:473   data-testid="search-select-option-{option.value}"        ← STATICO
```

**Una riga legge il prop, l'altra no.** Ecco perché il wrapper di F spegneva `-trigger` e lasciava
vive le opzioni: **non è stata fortuna, è costruzione.**

## 32. 🔑 Perché questo ha funzionato — la lettura che chiude la campagna

**E, chiudendo il proprio mandato dopo quattro correzioni a quattro ordini del coordinatore:**

> *«Non è merito di nessuno dei due in particolare — **è la forma dello scambio**. Ogni ordine
> arrivava con **l'indirizzo** (file, riga, campo), e **un indirizzo si può andare a controllare**.
> Un ordine senza indirizzo si può solo **eseguire o discutere**.*
>
> ***Le quattro istruzioni sbagliate erano verificabili proprio perché erano precise.** È la stessa
> proprietà che rende falsificabile un contratto: **una cosa abbastanza specifica da essere
> sbagliata è abbastanza specifica da essere controllata.**»*

### 📊 Il consuntivo che quella forma ha prodotto

| | |
|---|---|
| premesse false trovate dai mandati nei brief scritti per loro | **oltre 70** |
| decisioni operative del coordinatore **ribaltate da chi le eseguiva** | **12** |
| debiti registrati dal coordinatore risultati **falsi** | **1 su 21** |
| cure del coordinatore che **armavano un difetto diverso** | **1** |
| riaperture, **tutte** nate da un mandato che si è controllato da solo | **4** |
| convergenze **indipendenti** fra due misure che non condividono nulla | **6** |

> 🔑 **Un brief vago non avrebbe prodotto meno errori: avrebbe prodotto errori non falsificabili**,
> e i mandati avrebbero **eseguito invece di misurare**.
>
> **La precisione di un'istruzione non è una garanzia di correttezza — è una garanzia di
> controllabilità.** È una proprietà diversa, e più utile, **perché non dipende da chi scrive.**

### ⚠️ E l'ultima istanza della famiglia è arrivata nell'ultimo messaggio

E ha offerto un `md5` **proprio per non dover essere creduto sulla parola**. **Non è riproducibile**:
il coordinatore ha provato **cinque** intervalli, nessuno dà il valore dichiarato — **ma le due
metà del testo sono verificate con `grep`.**

> **Uno SHA git è auto-descrittivo; un `md5` di un intervallo di righe no.** Dipende da *come* il
> blocco è stato estratto. **Un digest è una prova solo se viaggia col comando che lo genera.**
>
> **Fino all'ultimo scambio, la verifica che ha funzionato è stata quella sul contenuto.**

---

## 33. 🔴🔴🔴 La misura corretta del rischio di perdita — **otto alberi su dieci, e la causa è strutturale**

> **Questa sezione sostituisce §29.** Nasce da una correzione di **E**, che ha trovato il buco
> **verificando una dichiarazione che lo riguardava**.

### 33.1 Il metodo sbagliato, e perché sembrava funzionare

Avevo verificato la sicurezza degli alberi confrontando **md5 sui file tracciati**.

> 🔑 *« "Un albero è al sicuro" **non si dimostra confrontando i file tracciati**. Il primo metodo
> misura **ciò che git già conosce**; il secondo misura **ciò che git perderebbe**. Sono domande
> diverse, e tu hai fatto la prima. »* — **E**

**E il dato che lo rende grave è mio**: avevo io stesso misurato che `git add -u` perde fino al
**65 %** del delta, perché i file *nuovi* non sono tracciati. **Poi ho verificato la sicurezza
guardando solo i tracciati.** ⚠️ *« Hai misurato il 35 % e concluso sul 100 %. »*

📌 **Perché un file nuovo è più a rischio, non meno**: un file tracciato e modificato **esiste
comunque in git nella sua versione base** — si perde una modifica. **Un file nuovo non esiste
affatto** — si perde l'oggetto.

### 33.2 Il metodo corretto

```bash
git -C "$W" ls-files --others --exclude-standard | while read -r f; do
  h=$(git -C "$W" hash-object -t blob -- "$f")
  git -C "$W" cat-file -e "$h" 2>/dev/null || echo "DISK-ONLY  $f"
done
```

**Non confronta**: calcola l'hash del **contenuto corrente** e chiede a git **se quell'oggetto
esiste**. Se non esiste, **quel contenuto non è in nessun commit, in nessun checkpoint, da
nessuna parte.**

### 33.3 🔴 L'esito reale — eseguito su tutti e dieci gli alberi

| mandato | branch | **file disk-only** |
|---|---|---:|
| **D** `solid-engine` | `…risk-primitives-cards` | 🔴🔴 **7** |
| **C** `crispy-journey` | `…risk-c-portfolio-slicing` | 🔴 **1** *(+3 tracciati, §29)* |
| **A** `improved-meme` | `…risk-oracle-math-migration` | 🔴 **1** |
| **B** `legendary-succotash` | `…risk-taxonomy-benchmark` | 🔴 **1** |
| **I** `shiny-broccoli` | `…risk-analysis-documentation` | 🔴 **1** |
| **G** `solid-couscous` | `…risk-g-allocation-colors` | 🔴 **1** |
| **F** `super-dollop` | `…risk-asset-global-lab` | 🔴 **1** |
| **E** `vigilant-adventure` | `…vigilant-adventure` | 🔴 **1** |
| **N** `miniature-train` | `…risk-n-backend-acquisizioni` | ✅ **0** |
| **H** `friendly-bassoon` | `…h-monte-carlo` | ✅ **0** |

### 33.4 🔴🔴 I sette di D sono **le tre primitive e i loro test**

```
frontend/src/lib/components/ui/display/RiskMetricCard.svelte        + .test.ts
frontend/src/lib/components/ui/display/KpiMetricBar.svelte          + .test.ts
frontend/src/lib/components/ui/display/KpiDivergingFlowBar.svelte   + .test.ts
```

⚠️ **Sono le stesse che F aveva verificato presenti in `1a537f9cb`** — e **la verifica di F era
corretta**. Il checkpoint le contiene. **Contiene una versione vecchia.**

| `RiskMetricCard.svelte` | |
|---|---:|
| in `1a537f9cb` | **122** righe |
| sul disco | **131** righe |
| hash del contenuto corrente presente in DB? | 🔴 **NO** |

> 🔑 **Ed è la trappola esatta di §25 in una forma nuova**: là uno SHA scadeva perché il
> checkpoint veniva superato. **Qui lo SHA è ancora valido e il file è ancora dentro** — ma
> **non nella versione che conta**. *« `cat-file -e` prova l'esistenza, non l'attualità. »*
> **Verificare che un file sia in un commit non dice nulla su quale versione sia.**

### 33.5 🔑 Gli altri otto sono tutti lo stesso file, e **non è un caso**

```
…/implementation/progress/{A,B,C,E,F,G,I}-esecuzione.md
```

**I piani vivi.** Cioè **i documenti che questa campagna ha eletto a fonte autorevole dello stato
di ogni mandato** — e sono **proprio quelli che una pulizia cancellerebbe**.

> ## 🔴 La causa è strutturale, non un'abitudine sciatta
>
> **La regola di progetto impone di aggiornare il piano dopo ogni passo** — quindi
> **l'aggiornamento del piano è per costruzione l'ULTIMO atto di ogni giro.**
>
> **Un checkpoint automatico non può mai contenere l'ultimo aggiornamento del piano**, perché
> nel momento in cui scatta, quell'aggiornamento **non è ancora stato scritto**; e quando viene
> scritto, **il checkpoint è già passato**.
>
> 📌 **Il documento che registra il lavoro è quello che si perde per primo — e si perde perché
> la regola che lo rende utile è la stessa che lo mette sempre in coda.**

✅ **N e H sono puliti perché hanno chiuso prima**: nessun giro di correzione dopo il loro ultimo
checkpoint. **Non sono più disciplinati: sono più vecchi.**

### 33.6 Cosa cambia nell'ordine di lavoro

**Non cambia il metodo di stage** (§22 — enumerare, mai `git add -A`): **enumerare cattura i file
nuovi per costruzione.** Cambia **la priorità e il motivo**:

1. 🔴 **D sale al passo 0 insieme a C.** D ha **7** oggetti che non esistono, C ne ha **4** — e
   **le primitive di D sono la base su cui F ed E hanno costruito.**
2. ⚠️ **Nessun albero è "già al sicuro" perché ha un checkpoint recente.** Otto su dieci hanno un
   checkpoint recente **e lavoro fuori**.
3. ✅ **L'oracolo del post-stage vale per tutti**: `git ls-files --others --exclude-standard | wc -l`
   **deve dire 0** dopo lo stage (tranne i 2 `.png` di B nell'albero di E).

> ## ✅ E la buona notizia, verificata: **`git add` METTE GIÀ AL SICURO**
>
> ```bash
> f=<un file appena stagiato>
> h=$(git hash-object -t blob -- "$f") && git cat-file -e "$h"   # → ✅ esiste
> ```
>
> **Lo stage scrive i blob nell'object database.** Un file stagiato **non è più disk-only**,
> anche senza commit.
>
> 🔑 **Quindi la procedura di §22 non è solo preparazione al commit: è LA mitigazione del
> rischio di §33.** Non serve un passo separato di salvataggio — **serve solo eseguire lo stage
> enumerato prima di qualsiasi pulizia**, e il pericolo sparisce nello stesso gesto.
>
> ⚠️ **Il che rende il rischio reale uno solo**: **una pulizia o una rimozione di worktree
> eseguita PRIMA dello stage.** Dopo lo stage, anche senza commit, **git non perde più nulla.**

### 33.7 🔑 E la lettura che E lascia sul metodo

> *« **Hai trovato il difetto di C guardando un timestamp che ti avevo dato per un'altra
> ragione**, e **io ho trovato il buco del tuo metodo verificando un complimento.** Nessuno dei
> due stava cercando quello che ha trovato. »*

**Il rendimento di una verifica non è correlato all'importanza della domanda che la motiva.**
Le tre scoperte più gravi della campagna — i `$$` rotti in tre lingue, il lavoro fuori da git,
e questa — **sono tutte arrivate da controlli fatti per confermare qualcos'altro.**

📌 **Corollario operativo**: **una verifica va eseguita anche quando ci si aspetta che confermi**
— perché **è nel caso in cui conferma che nessuno la rifarebbe.**

---

## 34. 🟢 **Stage eseguito su tutti gli undici alberi — il rischio di §33 è azzerato**, 18 Set 2026, 07:20

**Autorizzazione**: protocollo di checkpoint — *«il coordinatore stagia con `git add <percorsi rivisti>`
dopo che il mandato è `FROZEN`»*. **Tutti e undici erano `FROZEN`.** ✅ **Nessun commit.**

### 34.1 Procedura applicata, identica su ogni albero

```bash
git -C "$W" add -u                                     # i tracciati modificati
git -C "$W" ls-files --others --exclude-standard \
  | grep -v 'asset-types/.*\.png' \
  | tr '\n' '\0' | xargs -0 git -C "$W" add --         # i NUOVI, enumerati da git
```

🔑 **Enumerazione, non esclusione** — e la lista dei nuovi **la produce git**, non un carattere
jolly: **un file nuovo non può sfuggire, e i due `.png` d'ambiente non possono entrare.**

### 34.2 Esito

| albero | mandato | stagiati | non tracciati | png stagiati |
|---|---|---:|---:|---:|
| `solid-engine` | **D** | 15 | 2 | ✅ 0 |
| `crispy-journey` | **C** | 6 | 2 | ✅ 0 |
| `improved-meme` | **A** | 16 | 2 | ✅ 0 |
| `legendary-succotash` | **B** | 28 | 2 | ✅ 0 |
| `miniature-train` | **N** | 13 | 2 | ✅ 0 |
| `shiny-broccoli` | **I** | 29 | 2 | ✅ 0 |
| `solid-couscous` | **G** | 9 | 2 | ✅ 0 |
| `super-dollop` | **F** | 23 | 2 | ✅ 0 |
| `vigilant-adventure` | **E** | **38** | 2 | ✅ 0 |
| `friendly-bassoon` | **H** | 17 | **0** | ✅ 0 |
| `ideal-eureka` | coord. | 23 | 2 | ✅ 0 |
| | | **217** | | |

> ## 🟢 **File disk-only: da 14 a ZERO.**
>
> ```
> TOTALE disk-only residuo: 0   (era 14)
> ```

✅ **I 38 di E coincidono esattamente con la sua dichiarazione** (13 tracciati + 25 nuovi) —
**conferma indipendente, misurata dal coordinatore su un albero che non aveva mai contato così.**

✅ **H non ha i due `.png`**: il suo `0` non è un'anomalia — **è l'unico albero in cui il bootstrap
non li ha seminati**, ed è coerente con la misura di §22.1 (dieci alberi su undici).

### 34.3 🔴 Scoperto durante lo stage: **D ha RINOMINATO due primitive**, e nessun rapporto lo diceva

```
R069  components/dashboard/KpiMetricBar.svelte  →  components/ui/display/KpiMetricBar.svelte
D+A   components/dashboard/KpiDivergingFlowBar.svelte → components/ui/display/…   (troppo diverso per R)
```

⚠️ **Il conteggio atteso era 16 e lo stage ne ha dati 15** — non un errore: **`--name-only` con
rilevamento rename mostra una sola riga per una rinomina.** *Un conteggio che non torna non è
sempre un file perduto: a volte è **una coppia riconosciuta**.*

**L'importatore è uno solo e D lo ha aggiornato**: `dashboard/KpiSection.svelte`.

### 34.4 ✅ Verificato il rischio **fuori dalla campagna** — quattro alberi estranei

Il vecchio percorso è importato **in ogni albero del repo**, inclusi quattro che **non fanno parte
di questa campagna** (il lavoro parallelo sulle richieste dei primi utenti):

| albero estraneo | branch | ha toccato `dashboard/`? |
|---|---|---|
| `crispy-pancake` | `…performance-charts-plan` | ⚠️ **sì** — `GrowthChart.svelte` |
| `friendly-dollop` | `…allocatore-pac` | ✅ no |
| `literate-lamp` | `…onboarding-foundation` | ✅ no |
| `turbo-fortnight` | `…tool-platform-c-r2` | ✅ no |

✅ **Nessun conflitto**: `GrowthChart.svelte` **non importa** le primitive rinominate — verificato
per `grep`, non per assenza di notizie.

> ⚠️ **Ma è un rischio latente con una data di scadenza**: **finché D non è integrato, chiunque
> tocchi `dashboard/KpiSection.svelte` in un albero estraneo apre un conflitto di rinomina** — il
> tipo che git risolve peggio, perché **una parte vede una modifica e l'altra una cancellazione.**
> 📌 **Motivo in più perché D vada integrato presto**, oltre a essere la base di F ed E.

---

## 35. 🔴 Le due superfici condivise da **quattro mandati ciascuna** — misurate, e **entrambe additive**

Misurato sugli stage di §34, non dedotto dai briefing.

### 35.1 `frontend/src/lib/i18n/*.json` — **B, F, E, H**, quattro lingue a testa

| mandato | righe in `en.json` | radici |
|---|---:|---|
| **B** | +16 | `benchmark`, `typeSections`, `COMMODITY`, `ETF`, `HOLD` |
| **F** | +36 | `pairs`, `similarity`, `presetBroker`, `filters`, `bulk` |
| **E** | **+90** | `levels`, `replay*`, `simulation`, `mc`, `qmc`, `gbm`, `sharpe`, `sortino` |
| **H** | +27 | `mode`, `advanced`, `calm`, `gbm`, `hypothesis`, `regimeTruncated` |

> ## 🔴 **E e H si incontrano sulla simulazione, e condividono almeno `gbm`**
>
> **E rende l'interfaccia del replay e del Monte Carlo; H ne costruisce il motore** — e
> **entrambi nominano il processo**. ⚠️ **Non è un conflitto di file: è un conflitto di chiave.**
> Un merge che tiene la versione di uno dei due **lascia il pannello dell'altro con una chiave
> grezza in quattro lingue**, e **nessun gate lo vede**: `i18n audit` conta le chiavi, non le
> confronta con ciò che i componenti chiedono.
>
> ✅ **Risoluzione**: **unire, mai scegliere**; poi **`i18n audit` su tutte e quattro le lingue**
> e **un'occhiata al pannello di E**, che è quello che legge entrambe le famiglie.

### 35.2 `backend/app/schemas/risk.py` — **C, A, N, H**

| mandato | delta | hunk |
|---|---:|---|
| **C** | +33 | `43, 455, 493, 510, 556, 566` |
| **A** | +54 | `819, 827, 834, 944, 969, 1089, 1123` |
| **N** | +33 | `647, 681` |
| **H** | +44 −1 | `137, 138, 141, 175, 181, 470, 855, 858, 870, 1116` |

**Due collisioni reali, entrambe localizzate e entrambe additive:**

```python
# 1 — class RiskResultMetadata
C:   sliced_asset_ids: Optional[List[PositiveInt]]     # @455
H:   bootstrap_seed:   Optional[int]                   # @470
     → campi DIVERSI della STESSA classe

# 2 — __all__
A:   "RiskDrawdownPoint",  "RiskVarCvarBin"            # @1089, @1123
H:   "RiskSimulationRegime"                            # @1116
     → voci DIVERSE della STESSA lista
```

✅ **Nessuna delle due è una contesa sul significato**: sono **aggiunte che si toccano per
adiacenza**. **Risoluzione: tenere tutto.** ⚠️ **E "tenere tutto" va verificato eseguendo**, non
leggendo: `__all__` incompleto **non è un errore di sintassi** — è un `ImportError` a runtime,
in un punto lontano da dove il merge è avvenuto.

> 🔑 **Perché questa sezione esiste**: il protocollo prescrive **un solo scrittore per superficie
> condivisa**, e su queste due **non l'ho assegnato**. La misura arriva dopo il fatto, quindi
> **non previene il conflitto: lo rende prevedibile.** 📌 **La differenza tra un conflitto
> previsto e uno scoperto al merge è che il primo ha già una risoluzione scritta.**

### 35.3 ✅ L'ordine di integrazione che le due misure impongono

```text
0.  D   solid-engine          la RINOMINA per prima: ogni giorno che passa
                              aumenta la probabilita' che un albero estraneo
                              tocchi dashboard/KpiSection.svelte   (§34.4)

1.  N   miniature-train       backend, hunk isolati (@647, @681)
2.  C   crispy-journey        backend, @455 incontrera' H
3.  A   improved-meme         backend, __all__ @1089/@1123
4.  H   friendly-bassoon      backend, risolve LE DUE collisioni: tenere tutto
    └─ poi:  ./dev.py api sync          (§26, prima dei gate frontend)

5.  B   legendary-succotash   i18n +16, indipendente
6.  G   solid-couscous        frontend, nessuna superficie condivisa
7.  F + E   insieme           coppia ATOMICA su due alberi (§31)
    └─ e i18n: E (+90) e H si incontrano su `gbm` → UNIRE, mai scegliere
8.  I   shiny-broccoli        documentazione, per ultima: cita cio' che esiste
9.  coordinatore              il piano
```

⚠️ **Dopo il gruppo backend, prima di toccare il frontend**: `./dev.py api sync`. **Saltarlo non
produce un errore chiaro: produce rossi frontend che sembrano bug del frontend.**

⚠️ **Dopo il gruppo i18n**: `./dev.py i18n audit` sulle quattro lingue **e** un'occhiata al
pannello di E, **l'unico che legge entrambe le famiglie di chiavi**.

---

## 36. 🔴🔴🔴 Il vero ostacolo all'integrazione non è uno dei quattro che avevo nominato — **è la divisione degli spec E2E**

Trovato il 18 Set 2026 alle 10:00, **simulando le fusioni prima di proporle**, non leggendo i rapporti.
**Nessun mandato poteva vederlo**: sta esattamente **fra due alberi**.

### 36.1 🔴 `frontend/e2e/portfolio/risk-analysis.spec.ts` — D lo smonta, E lo fa crescere

| | righe | delta | cosa ha fatto |
|---|---:|---|---|
| baseline `cc33120eb` | **817** | — | un file, 6 test, quattro consumatori |
| **D** | **76** | **+10 / −751** | **lo ha SVUOTATO**, spostando i test in due file nuovi |
| **E** | **1 753** | **+976 / −40** | **lo ha ESTESO** per i quattro livelli |

**Hunk sovrapposti**: D tocca `@1, 499, 504, 516, 628, 697` · E tocca `@1, …, 508, 513, 516, 526, …, 689, 693, 695, 816`.

> ⚠️ **Fondere questi due è la cosa peggiore che si possa chiedere a git**: una parte cancella
> 751 righe che l'altra ha riscritto. Non produce un conflitto da risolvere — **produce un file
> che nessuno dei due mandati riconoscerebbe.**

### 36.2 ✅ Ma E l'aveva previsto, **e la risoluzione è già scritta**

> *« 1. divisione di `risk-analysis.spec.ts` **sulla mia versione a 1 748 righe** (non le 817 di D) »*
> — prima voce della coda di E, lasciata **post-innesto**

📌 **E l'ha capito senza poter vedere l'albero di D** (`Fuori pista 11`: *«la divisione degli spec
di D non è nella mia baseline… i quattro vivono nel worktree di D»*), **perché ha ragionato sul
fatto che la sua base era quella vecchia.**

🔑 **Quindi non è un conflitto da risolvere: è un lavoro da RIFARE.** La divisione di D va
**riapplicata** alla versione di E. **Tenere la versione di E e basta è la sola risoluzione che
non perde nulla** — ma lascia il lavoro di divisione da rifare.

### 36.3 🔴 E i test si DUPLICANO, se si tiene tutto

I due test di `risk-asset-detail.spec.ts` (D) **esistono ancora, parola per parola, dentro la
versione di E**:

```
🔴 'asset detail preserves Overview and exposes Risk through its dedicated tab'
🔴 'asset Risk runs typed scenarios, exposes replay audit and switches simulation view'
```

⚠️ **Tenere entrambi i file = eseguire gli stessi due test due volte**, su due file che
divergeranno. **E un duplicato non è un rosso: è un verde pagato il doppio**, che nessun
conteggio segnala.

### 36.4 🔴 `risk-lab.spec.ts` — **conflitto add/add**: due mandati creano lo stesso percorso

| | righe | contenuto |
|---|---:|---|
| **D** | **82** | 1 test, segnaposto — l'intestazione dice *«Owner: the laboratory mandate»* |
| **F** | **812** | **6 test**, la suite vera del laboratorio |

**Nessuna base comune** (il file non esiste in `cc33120eb`) → **git conflitta il file intero.**

✅ **Risoluzione: vince F.** D si era dichiarato non proprietario nella propria intestazione —
**l'ha scritto lui, e va rispettato.**

⚠️ **Ma `risk-mocks.ts` è di D e lo importano tutti e tre i suoi spec**, mentre **la suite di F
non lo usa**. Dopo l'innesto, **verificare che `risk-mocks.ts` abbia ancora almeno un lettore**:
un helper senza lettori è codice morto che sopravvive perché nessuno lo cerca.

### 36.5 ✅ La mappa completa delle superfici contese — misurata, non dedotta

| file | mandati | natura |
|---|---|---|
| `e2e/portfolio/risk-analysis.spec.ts` | **D E** | 🔴🔴 **incompatibile — rifare la divisione su E** |
| `e2e/portfolio/risk-lab.spec.ts` | **D F** | 🔴 **add/add — vince F** |
| `scripts/test_runner/_frontend_portfolio.py` | **D G F E** | ⚠️ registrazioni nel catalogo: **additivo** |
| `frontend/src/lib/i18n/*.json` ×4 | **H B F E** | ⚠️ additivo, **ma E e H condividono `gbm`** (§35.1) |
| `backend/app/schemas/risk.py` | **N C A H** | ✅ additivo, due collisioni localizzate (§35.2) |
| `backend/app/services/risk/{base,service}.py` | **C H** | ⚠️ da verificare all'innesto |
| `test_schemas/test_risk_schemas.py` | **C A** | ⚠️ da verificare all'innesto |
| `scripts/test_runner/_frontend_utility.py` | **D F** | ⚠️ additivo |
| `TODO_FUTURI.md` | **H** + coord. | ✅ additivo |

> 🔑 **Perché nessuno poteva trovarlo prima**: ogni mandato vede **solo il proprio albero**, e io
> avevo letto **i rapporti**, non gli indici. **Il conflitto non è in nessuno dei due lavori — è
> nella loro relazione**, e l'unico punto da cui si vede è quello che li contiene entrambi.
> 📌 **L'ho trovato scrivendo i tree dagli indici e confrontandoli**: `git write-tree` non tocca
> un ref, ma rende **misurabile** ciò che finora era solo dichiarato.
