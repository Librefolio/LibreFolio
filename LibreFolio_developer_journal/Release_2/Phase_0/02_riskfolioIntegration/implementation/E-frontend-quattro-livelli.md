# Mandato E — I quattro livelli su Dashboard e Broker Detail

| | |
|---|---|
| **Flusso** | W5 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | frontend — **il flusso più grande del piano** |
| **Taglia** | **XL** |
| **Lane** | porta `6244` · data dir `backend/data/test-risk-e` |
| **Dipende da** | **D** (bloccante) · innesti da A, C, H, I, N |
| **Riceve** | **K1** da A · **K4** da C · **K5** da D · **K6** da H · **K7** da I · **K3** da B · **K8** da N |

> Regole comuni: [`README.md`](./README.md) §5. Finito comune: §6.

---

## 1. Perché questo mandato esiste

`RiskAnalysisPanel.svelte` conta **1 271 righe** — il **40% di tutto il frontend
rischio** — e impila in una colonna verticale: KPI, correlazione, contributo, VaR,
confronto, stress, replay e simulazione. Tutto allo stesso peso visivo.

Non è un problema di ordine degli elementi. È la conseguenza della domanda con cui fu
costruito ([`../01-…`](../01-tesi-e-quattro-domande.md) §1):

```text
«quali strumenti di rischio esistono?»
  → ogni metrica pesa uguale
    → le implementi tutte
      → la UI diventa una lista verticale
        → l'utente non sa dove guardare
          → banner beta
```

> ## La tesi che questo mandato deve incarnare
>
> Risk non risponde a *«quanto rischio ho?»* (un numero). Risponde a **«il mio
> portafoglio è quello che credo che sia?»** (una sorpresa).
>
> Un numero isolato non produce decisioni: l'utente lo legge, non sa se sia alto o
> basso, e chiude la pagina. Una **discrepanza** produce sempre una decisione — anche
> solo quella di non fare nulla, ma consapevolmente.
>
> **Criterio operativo**: ogni sezione deve poter finire con la frase *«non lo
> sapevo»*. Se non può, non serve.

---

## 2. Cosa leggere prima — tutto, e non in diagonale

1. [`../01-tesi-e-quattro-domande.md`](../01-tesi-e-quattro-domande.md) **per intero**.
   È la fonte di ogni decisione: se una scelta non discende da lì, è arbitraria.
2. [`../03-mappa-livelli-pagine.md`](../03-mappa-livelli-pagine.md) §2 e §3.
3. [`../05-grammatica-visiva-e-rappresentazioni.md`](../05-grammatica-visiva-e-rappresentazioni.md)
   **§4** (anatomia della card), **§7.1, §7.2, §7.3, §7.5, §7.6, §7.7** (le sei
   rappresentazioni), **§9.1** (il layout).
4. [`../02-verdetti-per-strumento.md`](../02-verdetti-per-strumento.md) — per ogni
   strumento che si tocca, la sua mini-lezione: senza, si disegna una metrica senza
   sapere a cosa risponde.
5. Decisioni: **D3**, **D4**, **D10**, **D14**, **D15**, **D16**, **D17**, **D22**.

---

## 3. La regola strutturale, e come si verifica

Le tre regole implicite nel layout di
[`../05-…`](../05-grammatica-visiva-e-rappresentazioni.md) §9.1:

### 3.1 Un blocco = un livello, non un analytic

L'output di `historical_kpi` va **spezzato**: `max_drawdown` sale a L1,
`sharpe`/`sortino`/`volatility` scendono a L3. Il backend non cambia: cambia chi
aggrega.

> L'analytic è un'unità di **offerta**, il livello un'unità di **domanda**. Oggi la UI
> è organizzata per offerta, ed è questa l'origine della piattezza.

**Verificabile**: se un pannello non appartiene a un livello, non deve esistere
([`../03-…`](../03-mappa-livelli-pagine.md) §3.2).

### 3.2 Peso visivo proporzionale al livello

L1 e L2 sempre aperti, L3 aperto, **L4 chiuso** dietro un'azione esplicita — ed è lì
che vive il banner beta superstite.

### 3.3 La frase precede il grafico

In L2 il titolo è **generato dai dati** — *«NVDA pesa l'8% ma produce il 23% del
rischio»* — e il grafico lo *dimostra*. Oggi c'è solo il grafico, e la domanda resta
implicita.

---

## 4. ⚠️ Dashboard e Broker Detail sono lo stesso componente

Non «simili»: **identici, con scope diverso**. Lo conferma già il codice — entrambe le
route montano `RiskAnalysisPanel`, cambiando solo lo scope (`portfolio` contro
`portfolio + broker_ids`).

> **Non si progettano due pagine, se ne progetta una** (**D10**).
>
> Se a metà lavoro diventano due, **il mandato ha fallito anche con tutti i test
> verdi**. È il rischio 1 di [`../07-…`](../07-piano-esecutivo.md) §10.

Corollario per L3: il benchmark deve essere **lo stesso** nelle due pagine. Se Dashboard
dicesse «vs MSCI World» e Broker Detail «vs S&P 500», le due pagine non sarebbero più
confrontabili — e si perderebbe esattamente la proprietà che stiamo costruendo.

---

## 5. I quattro livelli, uno per uno

### L1 — «Quanto può fare male?»

Il difetto attuale non era includere il VaR: era **accostare una perdita a un giorno a
un drawdown pluriennale senza dichiarare la scala**, così che l'utente le sommasse
mentalmente. La cura è una **scala esplicita e crescente**, in una sola sezione:

```text
Quanto può fare male
  Una giornata storta   (peggiori 5%)      −1,8%        −2.340 €
  Un mese storto        (peggiori 5%)      −7,2%        −9.360 €
  La peggior discesa    (vissuta davvero) −38,4%      −49.900 €
                        durata 19 mesi · recupero richiesto +62,3%
```

Regole non negoziabili (**D4**):

- il **CVaR è il numero principale**, il VaR secondario — il VaR dichiara una soglia e
  **tace su cosa c'è oltre**, il CVaR dice quanto è brutto oltre;
- ogni riga porta **gli euro accanto alla percentuale**;
- ogni riga porta **il proprio** link di documentazione, non uno generico per la
  sezione;
- **nulla in L1 è stimato**: sono tutti fatti osservati sul campione.

**Rappresentazioni**: underwater chart (§7.1) e istogramma della distribuzione (§7.2).
Entrambe aspettano i campi del contratto **K1** da A.

L'underwater merita una nota, perché insegna da solo: la distanza verticale fra la
linea e lo zero **è** il recupero richiesto. Il numero più istruttivo del sottosistema
diventa una lunghezza che si guarda invece di una cifra da interpretare — perdere il
10% richiede +11,1%, a −50% servono +100%.

⚠️ **Niente gaussiana sovrapposta all'istogramma** (**D22**). Il VaR mostrato è un
quantile empirico: la campana confronterebbe i dati con un modello che non usiamo, e
suggerirebbe che lo scarto sia un'anomalia — mentre per i rendimenti finanziari **le
code grasse sono la norma**.

### L2 — «Sono diversificato come credo?»

**La rappresentazione che vale di più costa zero**: peso contro contributo al rischio
(§7.3). `weight` e `percentage_contribution` sono **già entrambi nel payload**, e
`weight` oggi viene **scartato**.

Il contributo al rischio da solo non risponde alla domanda: la risposta è lo **scarto**
fra quanto un asset pesa e quanto rischio produce. Ordinamento per scarto decrescente:
in cima finisce sempre ciò che rischia più di quanto si creda.

⚠️ Il contributo **può essere negativo** — un asset che *riduce* il rischio — quindi la
rappresentazione corretta è **a barre divergenti**, mai un treemap o una torta.

### L3 — «Sto venendo pagato per questo rischio?»

L'unica delle quattro che guarda **fuori**. È la domanda che un investitore fai-da-te
ha davvero in testa e raramente formula: *«tutta questa complessità rende più di un
singolo ETF mondiale, o mi sto solo dando da fare?»*

Sharpe, Sortino e beta apparivano come card orfane non perché fossero metriche
sbagliate, ma perché erano **metriche senza casa**.

Regole: se se ne mostra **uno** fra Sharpe e Sortino, si mostra **Sortino** — più
onesto su rendimenti asimmetrici, perché lo Sharpe usa la volatilità totale e quindi
**penalizza anche le salite violente**. Mai come «voto».

**Rappresentazione**: scatter rischio-rendimento (§7.5) — è la Capital Market Line
senza pronunciarne il nome. ⚠️ È l'unica proposta con un **costo backend non
marginale**: richiede volatilità e rendimento per ogni asset dell'insieme. Da
concordare col coordinatore se entra in v1.

### L4 — «Cosa succede se…?» — chiuso di default

L4 non è omogenea: contiene cose a **distanza crescente dai dati**, e l'ordine interno
deve renderlo visibile.

```text
replay storico       → rendimenti reali di un periodo reale
shock ipotetico      → deterministico, ipotesi dichiarata dall'utente
simulazione          → modello probabilistico, assunzioni del modello
```

**Solo l'ultimo gradino è un modello.** È lì, e solo lì, che ha senso un avvertimento —
ed è l'unico posto dove il banner beta sopravvive.

**Rappresentazioni**: tornado degli scenari (§7.6, dati già nel payload) e cono della
simulazione (§7.7, `buildBandSeries` già esistente — riuso puro).

⚠️ **Lo shock ipotetico va invertito** (**D4** su `stress`): oggi si chiede all'utente
di riempire i bucket uno per uno, e **nessuno lo farà mai**. Servono **preset a un
clic**, con il dettaglio per bucket disponibile solo su richiesta.

⚠️ Il replay storico richiede un **proxy** se un asset di oggi non esisteva nel 2008, e
**il proxy è una scelta, non un fatto**. Il backend ha già l'audit (`bucket_audit`,
`metadata_fallback`): va **mostrato**, non nascosto.

---

## 6. Cosa sparisce, e perché

| Sparisce | Motivo |
|---|---|
| Tracking error e information ratio | Misurano l'aderenza a un **mandato** che un investitore privato non ha (**D5**). Backend intatto: è rimozione dalla UI, non dal dominio |
| `sobol_start_index` (`:1224`) | È un controllo da quant, non da utente |
| Le barre divergenti scritte a mano (`:854-870`) | Sostituite da `KpiDivergingFlowBar` del mandato D |
| Il formattatore valuta duplicato (`riskAnalysisHelpers.ts:130`) | Sostituito da `formatCurrencyAmountPlain` |

⚠️ **Attenzione a un errore facile**: il benchmark persistente del mandato B **non
riapre** TE/IR. La precondizione tecnica sarà soddisfatta, ma la ragione del taglio è
**semantica**, non tecnica.

---

## 7. Gli innesti — costruire lasciando il posto

Quattro cose arrivano da altri mandati. **Non si aspetta**: si costruisce lasciando il
posto, e si innesta quando arrivano.

| Innesto | Da | Cosa cambia quando arriva |
|---|---|---|
| **K1** — serie underwater e bin istogramma | A | Le due rappresentazioni di L1 diventano disegnabili |
| **K4** — filtro per asset e pesi rinormalizzati | C | Compare il selettore di fetta. ⚠️ La rinormalizzazione **va dichiarata a schermo** |
| **K6** — modalità di simulazione e payload del cono | H | Il gradino 3 di L4 prende la sua forma |
| **K7** — slug delle pagine di documentazione | I | I `DocsLink` puntano a pagine vere |
| **K3** — selettore benchmark a sezioni | B | L3 acquista il suo riferimento persistente |
| **K8** — KPI acquisiti di L1 e L2 | N | L1 riceve `WR` e la famiglia drawdown (`DaR`, `CDaR`, `UCI`); L2 riceve **NEA e diversification ratio** |

> ## ⚠️ K8 porta con sé un obbligo, non solo dei campi
>
> **NEA e diversification ratio si mostrano insieme, sempre.** NEA è **cieco alla
> correlazione**: tre portafogli di dieci asset equipesati con ρ = 0 / 0,5 / 0,95 danno
> NEA **10,00 in tutti e tre**, mentre il diversification ratio fa **3,15 → 1,35 →
> 1,02** (**D38**).
>
> Mostrare NEA da solo significa dire *«sei diversificato»* a un portafoglio che non lo
> è — cioè **il difetto esatto che L2 esiste per smascherare**.
>
> E attenzione alla **convenzione di segno**: riskfolio restituisce magnitudini
> **positive** mentre `max_drawdown` è negativo. Quale convenzione arriva è nel
> contratto: leggerla, non indovinarla.

---

## 8. Confini

**Di questo mandato**: `frontend/src/lib/components/risk/**` — compresa la sostituzione
di `RiskAnalysisPanel.svelte` — `frontend/src/lib/stores/risk/**`,
`frontend/src/lib/risk/**`, e i punti di montaggio in `dashboard/+page.svelte` e
`brokers/[id]/+page.svelte`.

**Eccezione concordata**: `CorrelationHeatmap.svelte` sta dentro `risk/` ma appartiene
al mandato **F**. Non toccarla.

**i18n**: namespace `risk` (righe ~2 889-3 125) e `dashboard` (~1 316-1 458). Vanno
aperti i sotto-blocchi `risk.simulation.*` per **H** e `risk.lab.*` per **F**, che
scrivono solo lì dentro. **Non riordinare e non riformattare** i file.

**Fuori**: `(app)/assets/+page.svelte` (mandato F), i grafici di allocazione (G),
`components/ui/**` (D), qualunque cosa nel backend.

⚠️ **Asset Detail è fuori** (**D8**, **D47**): si riapre dopo il rilascio, così eredita
una grammatica già decisa. E i **segnali rolling restano dove sono** (**D9**), nella
Overview di Asset Detail: non vengono spostati né duplicati qui.

---

## 9. Il rischio numero uno di questo mandato

> **Che W5 diventi un secondo monolite.**
>
> Sintomo misurabile: un file oltre le 600 righe.
>
> La regola è verificabile, quindi va verificata: **un pannello, un livello**. La
> scomposizione non è «dividere 1 271 righe in pezzi più piccoli» — sarebbe un refactor
> senza tesi. È **un pannello per livello**, composto diversamente da ogni pagina.

---

## 10. Test

Per scrivere gli spec si invoca **`test-author`**, passandogli lane e file consentiti.

| Cosa | Come |
|---|---|
| Unitari | Vitest sugli helper e sulla composizione dei livelli |
| E2E | `portfolio/risk-analysis.spec.ts` (tuo) e `portfolio/dashboard.spec.ts` (**condiviso con G**) |
| Statici | lint + `svelte-check` |

> ## ⚠️ Lo spec E2E arriva già diviso — e uno dei quattro file non si tocca
>
> Il mandato **D** divide le 817 righe di `risk-analysis.spec.ts` (K5, §5.1 del suo
> file). Dopo la divisione:
>
> | File | Chi |
> |---|---|
> | `portfolio/risk-mocks.ts` | **tuo**, ma **F lo consuma** — cambiarlo rompe anche lui |
> | `portfolio/risk-analysis.spec.ts` | **tuo** |
> | `portfolio/risk-lab.spec.ts` | di **F** — non toccare |
> | `portfolio/risk-asset-detail.spec.ts` | 🚫 **di nessuno** |
>
> L'ultimo è la **rete che dimostra che non hai toccato Asset Detail** (**D8**,
> **D47**). Se lo adatti per farlo passare, hai cancellato l'unica prova che cercavi.

> ## ⚠️ `resultFor` in `risk-mocks.ts` codifica la forma del payload
>
> Quando arrivano **K1** (serie underwater, bin dell'istogramma) e **K8** (i KPI
> acquisiti), quel mock va aggiornato. Altrimenti i test **passano** servendo una forma
> che il backend non produce più.
>
> Un mock stantio non fallisce: **rassicura**. È la stessa famiglia del CVaR rimasto
> sbagliato per un anno.

⚠️ **Selettori `data-testid` sempre**, mai classi CSS e **mai testo tradotto**: questa
UI esiste in quattro lingue. E ogni test condivide DB e backend con i vicini — niente
posizioni fisse, niente conteggi globali, niente attese sull'orologio.

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6244 --data-dir backend/data/test-risk-e \
  <categoria> <azione>
```

---

## 11. Definizione di finito

- [ ] `RiskAnalysisPanel.svelte` **non esiste più** nella sua forma monolitica;
- [ ] **nessun file del mandato supera le 600 righe**;
- [ ] ogni pannello appartiene a un livello e a uno solo;
- [ ] Dashboard e Broker Detail montano **lo stesso componente** con scope diverso;
- [ ] L1 ha la scala temporale, il CVaR primario, gli euro accanto alle percentuali e
      un `DocsLink` **per riga**;
- [ ] L2 mostra lo scarto peso/contributo con barre divergenti, titolo generato dai dati;
- [ ] L3 mostra Sortino, non Sharpe, e il benchmark persistente;
- [ ] L4 è **chiuso di default**, con i tre gradini in ordine di distanza dai dati;
- [ ] TE, IR e `sobol_start_index` **spariti dalla UI**;
- [ ] zero barre divergenti a mano, zero formattatori valuta duplicati;
- [ ] i cinque innesti ricevuti e collegati, o dichiarati mancanti;
- [ ] lint, `svelte-check`, Vitest ed E2E verdi;
- [ ] nessun processo in ascolto su `6244`.
