# Mandato D — Primitive promosse e card del rischio

| | |
|---|---|
| **Flusso** | W4 di [`../07-piano-esecutivo.md`](../07-piano-esecutivo.md) §2 |
| **Dominio** | frontend, fondamenta |
| **Taglia** | M |
| **Lane** | porta `6243` · data dir `backend/data/test-risk-d` |
| **Dipende da** | nulla — parte subito |
| **Consegna** | contratto **K5** a **E** ed **F** |
| **Blocca** | **E** ed **F**: sono i due mandati più grandi del frontend |

> Regole comuni: [`README.md`](./README.md) §5. Finito comune: §6.

---

## 1. Perché questo mandato esiste, e perché è piccolo ma primo

Il developer ha descritto la prima bozza di UI come *«esteticamente ampiamente
insufficiente, non segue le regole estetiche del resto del progetto, non è ottimizzata
per gli schermi, non è chiara, non è modulare»*. La verifica sul codice ha confermato
ogni punto **e ha rivelato che la causa non è dove sembrava**.

Il sottosistema rischio **non** è un'isola stilistica: usa già `SimpleSelect`,
`TabBar`, `InfoBanner`, `LineChart`, `KpiCard`. Ha adottato le primitive
**strutturali**. Non ha adottato **nessuna** di quelle espressive:

| Primitiva | Ruolo | File nel progetto | File nel rischio |
|---|---|---:|---:|
| `Tooltip` | spiegabilità — bordo punteggiato = «cliccami» | **61** | **0** |
| `DocsLink` | link alla documentazione | 3 | **0** |
| `TweenedValue` | numeri animati | 3 | **0** |
| `KpiMetricBar` | barra etichetta + valore + tooltip | 2 | **0** |
| `KpiDivergingFlowBar` | barra divergente | 1 | **0** |
| `formatCurrencyAmountPlain` | formattatore valuta unico | condiviso | **0** (duplicato) |

> I numeri ci sono ma **non parlano, non si muovono e non rimandano a nulla**. È questa
> l'origine dell'impressione di povertà, non la disposizione degli elementi.
>
> Disegnare nuovi layout sopra queste primitive riprodurrebbe gli stessi difetti in una
> disposizione diversa. Per questo D viene **prima** di E e F
> ([`../05-…`](../05-grammatica-visiva-e-rappresentazioni.md) §3, gradino 3).

---

## 2. Cosa leggere prima

1. [`../05-grammatica-visiva-e-rappresentazioni.md`](../05-grammatica-visiva-e-rappresentazioni.md)
   **§2 per intero** — la diagnosi, con i due doppioni e l'incoerenza dei contenitori.
2. Lo stesso documento **§3** (i tre gradini) e **§4** (l'anatomia della card).
3. **D15** in [`../04-…`](../04-decisioni-e-questioni-aperte.md).

---

## 3. Gradino 1 — Promuovere il generico

`KpiMetricBar` (68 righe) e `KpiDivergingFlowBar` (55 righe) vivono in
`components/dashboard/` ma **di dashboard non hanno nulla**: sono barre.

> Questo è il *«non è modulare»* nella sua forma concreta: non è il rischio a essere
> poco modulare, è che le primitive riusabili sono parcheggiate in una cartella che ne
> scoraggia il riuso. Chi scrive un componente rischio non pensa di cercare una barra
> dentro `dashboard/`.

Vanno in `components/ui/`. È uno spostamento più gli import: costo basso, effetto
sproporzionato.

⚠️ Chi le usa oggi (la dashboard) **non deve accorgersi di nulla**.

---

## 4. Gradino 2 — La card metrica del rischio

Una sola card, usata ovunque, costruita sopra le primitive promosse. Il modello è
`KpiSection.svelte` (391 righe), **la card che già funziona**:

| Elemento | Implementazione | Perché conta |
|---|---|---|
| Tipografia fluida | `@container` + `text-[clamp(0.95rem,8cqw,1.5rem)]` | Il numero si ridimensiona col **contenitore**, non col viewport |
| Striscia d'accento | `absolute top-0 h-0.5`, colorata per segno | Stato leggibile **prima** di leggere la cifra |
| Link documentazione | `DocsLink` nell'intestazione | Già pronto, già stilato |
| Numero animato | `TweenedValue` + `tabular-nums` | Le cifre non ballano durante la transizione |
| Etichetta | `text-xs font-medium uppercase tracking-wide text-gray-400` | Canone del progetto |
| Skeleton | `class:invisible={loading}` sopra un placeholder assoluto | Il valore resta nel DOM: **nessuno spostamento di layout** |
| Sotto-metriche | righe `KpiMetricBar` | Gerarchia interna alla card |

**La tipografia fluida è la risposta vera al «non ottimizzata per gli schermi».** Il
difetto attuale è `grid-cols-1 sm:grid-cols-2 xl:grid-cols-5`: fra 640px e 1280px non
esiste alcun gradino, quindi su un portatile da 1366px si ottengono due colonne per
cinque card, tre righe, una card orfana. `@container` risolve il problema **alla
radice**, invece di aggiungere breakpoint a una griglia sbagliata.

### 4.1 Due aggiunte specifiche del rischio

- **Etichetta doppia** — frase in lingua naturale come titolo, nome tecnico in piccolo
  accanto: *«Giornata brutta (1 su 20)»* con `VaR 95%` sottotitolo. Chi non sa cos'è il
  VaR legge la frase; chi lo sa trova il termine; chi vuole capire clicca la ⓘ.
- **Slot sparkline** — opzionale, popolato **solo** dove una serie esiste davvero.
  ⚠️ Su Dashboard e Broker Detail il rolling di portafoglio **non esiste in tutto il
  codice**: `SignalDomain` ha due soli valori, `ASSET` e `FX`
  (`schemas/signals.py:84`), e crearlo toccherebbe l'intera piattaforma segnali
  (**D18**). Lo slot resta vuoto lì, e non è una mancanza.

---

## 5. I due doppioni da far sparire

Non sono dettagli: sono la prova che le primitive esistenti non venivano trovate.

| Doppione | Dove | Sostituto |
|---|---|---|
| Barre divergenti scritte a mano | `RiskAnalysisPanel:854-870` — `<div>` con `absolute left-1/2` e larghezze inline | `KpiDivergingFlowBar`, 55 righe testate e con tooltip |
| Formattatore valuta | `riskAnalysisHelpers.ts:130` | `formatCurrencyAmountPlain`, condiviso |

La rimozione avviene dentro il mandato **E**, che possiede `components/risk/`. Questo
mandato **fornisce il sostituto e lo comunica**; E lo adotta.

---

## 5.1 Gradino 3 — Dividere lo spec E2E che E ed F si contenderebbero

⚠️ **Non è lavoro di primitive, ed è qui per una ragione sola: è l'unico mandato che
gira prima di entrambi.** Lo stesso motivo per cui esistono i gradini 1 e 2.

`e2e/portfolio/risk-analysis.spec.ts` conta **817 righe** in **un solo
`test.describe`**, e i suoi sei test appartengono a tre padroni diversi:

```text
:140-579   ~580 righe di impalcatura condivisa
           installRiskMocks · resultFor · definition · metadata
           openDashboardRisk · openFirstBrokerRisk · brokerWithHoldings
:587       dashboard renders base analytics…              → E
:619       per-analytic unavailable state…                → E
:628       asset global maps broker holdings…             → F
:687       broker tab sends a single-broker subset…       → E
:698       asset detail preserves Overview…               → 🚫 parcheggiato (D8, D47)
:719       asset Risk runs typed scenarios…               → 🚫 parcheggiato
```

Senza la divisione, **E ed F riscrivono lo stesso file nello stesso momento** — e se ne
accorgono a lavoro fatto.

**La divisione**, da consegnare dentro **K5**:

| File | Contenuto | Poi è di |
|---|---|---|
| `portfolio/risk-mocks.ts` | l'impalcatura condivisa | **E** scrive, **F** consuma |
| `portfolio/risk-analysis.spec.ts` | i tre test di portafoglio | **E** |
| `portfolio/risk-lab.spec.ts` | il test di Asset Global | **F** |
| `portfolio/risk-asset-detail.spec.ts` | i due test parcheggiati | 🚫 **nessuno li riscrive** |

> ⚠️ **I due test di Asset Detail non sono un residuo da sistemare: sono una rete.**
> Asset Detail è fuori ambito (**D8**, **D47**) e deve restare identico. Quei due test
> sono ciò che lo **dimostra** quando E ed F avranno finito. Vanno isolati proprio
> perché nessuno sia tentato di adattarli.

**Vincolo**: la divisione è **solo spostamento**. Nessun test cambia comportamento,
nessuna asserzione cambia, il numero di test prima e dopo è lo stesso. Si registra poi
i selettori nuovi in `scripts/test_runner/_frontend_portfolio.py`, dove oggi
`portfolio risk` punta al file unico.

> ### ⚠️ La trappola dentro l'impalcatura, da comunicare a E
>
> `resultFor` (`:210-463`) **codifica la forma del payload del rischio**. Quando A
> consegna K1 (serie underwater, bin dell'istogramma) e N consegna K8 (i KPI acquisiti),
> quel mock va aggiornato — altrimenti i test **passano** servendo una forma di payload
> che il backend non produce più.
>
> Un mock stantio non fallisce: **rassicura**. È la stessa famiglia del CVaR sbagliato
> per un anno.

---

## 6. Il canone dei contenitori

Nei soli componenti rischio convivono due stili, e **cinque contenitori su nove sono
piatti** — senza ombra. Il canone del progetto è
`bg-white rounded-xl border border-gray-100 shadow-sm`, con 29 occorrenze concordi.

> È il motivo per cui il pannello sembra un wireframe accanto al resto
> dell'applicazione.

⚠️ **Nota da non trasformare in regola**: `--shadow-card` è definita in `app.css` e
usata **zero volte** in tutto il progetto. È un token morto — va rimosso o adottato,
non citato come se fosse il canone.

---

## 7. Confini
**Di questo mandato**:

- `frontend/src/lib/components/ui/**` — le primitive promosse e la card nuova
- gli import aggiornati nei file che usavano le due barre da `dashboard/`

**Fuori**:

- `components/risk/**` → mandato **E**
- `AllocationPieChart`, `AllocationHistoryChart` → mandato **G**
- qualunque layout: questo mandato fornisce **mattoni**, non stanze

---

## 8. Contratto K5 → mandati E ed F

Nomi, percorsi e props di tutto ciò che viene promosso o creato:

- dove sono finite `KpiMetricBar` e `KpiDivergingFlowBar`;
- la firma della card metrica del rischio: props, slot, comportamento in `loading`;
- come si passano etichetta doppia, `DocsLink` e slot sparkline;
- **la divisione dello spec E2E** (§5.1): i quattro file risultanti, chi possiede
  quale, e i selettori nuovi registrati nel catalogo;
- **l'avvertimento su `resultFor`**: il mock codifica la forma del payload, quindi K1 e
  K8 lo invalidano quando arrivano.

> Va consegnato **prima** che E ed F comincino. È l'intero motivo per cui questo
> mandato viene prima.

---

## 9. Test

| Cosa | Comando |
|---|---|
| Formattazione e tipi | lint + `svelte-check` sul frontend |
| Unitari delle primitive | Vitest sui componenti promossi |
| Non regressione della dashboard | gli spec E2E che coprono la dashboard |

```bash
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
  pipenv run python dev.py test --test-port 6243 --data-dir backend/data/test-risk-d \
  <categoria> <azione>
```

Per scrivere gli spec si invoca **`test-author`**.

---

## 10. Definizione di finito

- [ ] `KpiMetricBar` e `KpiDivergingFlowBar` in `components/ui/`, con tutti gli import
      aggiornati;
- [ ] **la dashboard è visivamente invariata** — è la prova che lo spostamento è
      innocuo;
- [ ] card metrica del rischio esistente, con tipografia fluida, striscia d'accento,
      `DocsLink`, `TweenedValue`, skeleton senza spostamento di layout;
- [ ] etichetta doppia e slot sparkline opzionale supportati;
- [ ] **`risk-analysis.spec.ts` diviso in quattro file** (§5.1), con lo **stesso numero
      di test prima e dopo** e nessuna asserzione cambiata;
- [ ] i selettori nuovi registrati in `_frontend_portfolio.py`;
- [ ] i due test di Asset Detail **isolati e verdi**;
- [ ] lint, `svelte-check` e spec dashboard verdi;
- [ ] **K5 consegnato e comunicato a E ed F**;
- [ ] nessun processo in ascolto su `6243`.
