# P4 — Motore contabile e segnali

> **Priorità**: 🟠 Media
> **Ambito**: `backend/app/services/signal_plugins/drawdown.py`, `backend/app/services/asset_source.py`,
> `backend/app/services/portfolio_engine.py` *(solo documentazione e test)*
> **Rilievi coperti**: E1, E2
> **Riferimenti**: [`02_riconciliazione_credit_agricole.md`](02_riconciliazione_credit_agricole.md)

---

## 🟠 E1 — Il drawdown è relativo alla finestra visibile

### Il rilievo

> *"Il segnale del drawdown implementato non sembra ritornare il drawdown rispetto l'ultimo
> massimo, ma rispetto al massimo nel periodo mostrato."*

### La matematica è corretta

```python
# backend/app/services/risk/metrics.py:193-204
def underwater_drawdown(values):
    peak = values[0]
    for value in values[1:]:
        peak = max(peak, value)          # massimo espandente — corretto
        result.append(value / peak - 1.0)
```

`peak = max(peak, value)` **è** un massimo espandente (`cummax`). Il difetto non è qui.

### Il difetto è nell'input

```python
# backend/app/services/signal_plugins/drawdown.py:85-95
def warmup_requirement(...):
    return ...(minimum_points=2, total_points=2)     # costante, ignora params e contesto
```

Questo valore determina quanta storia viene caricata **prima** del calcolo:

```python
# backend/app/services/asset_source.py:2099-2110
warmup_days = max(plan.max_history_points_before_visible,
                  plan.max_prepared_history_points_before_visible * _RISK_WARMUP_DAY_MULTIPLIER)
load_range = (req.date_range.start - timedelta(days=warmup_days), end)
```

Con `total_points=2` e `_RISK_WARMUP_DAY_MULTIPLIER = 2`, la finestra caricata parte **~4 giorni**
prima del range visibile. Quindi `values[0]` cade praticamente all'inizio della finestra
visibile, e il "massimo espandente" **diventa di fatto il massimo della finestra**.

Lo slicing per la visualizzazione avviene *dopo* il calcolo (`signal_series_preparation.py:431-448`)
— quello è corretto: il problema è a monte, nel caricamento.

> 🔍 **Lezione**: il drawdown è un indicatore **con memoria illimitata**. A differenza di una media
> mobile a 20 periodi, non esiste un warm-up finito che lo renda corretto: il picco rilevante può
> trovarsi a qualunque distanza nel passato. Dichiarare `total_points=2` significa dichiarare
> "non ho bisogno di storia", che per questo indicatore è **falso per costruzione**.

### Fix

Il drawdown deve essere calcolato sull'**intera storia disponibile**, poi affettato per la
visualizzazione. Due strade:

| Opzione | Descrizione | Nota |
|---|---|---|
| **A** | `warmup_requirement()` restituisce un valore "storia completa" | Serve verificare che il percorso di fetch onori la semantica |
| **B** | Il plugin dichiara di richiedere il picco corrente e lo riceve come stato iniziale | Più invasivo, ma non carica serie enormi |

→ **Proposta: A**, con verifica del costo su asset di lunga storia. Se il caricamento completo
risulta oneroso, ripiegare su B (che è comunque il modello concettualmente corretto: al calcolo
serve *il picco*, non *tutti i prezzi*).

> ✅ **Decisione 02/09/2026 (utente)**: la segnalazione originale nasceva da un fraintendimento
> (il drawdown È rispetto al massimo storico), ma il warmup a 2 punti resta sbagliato.
> Si va con la **A**, in forma di **parametro utente**:
>
> 1. `DrawdownParams` guadagna `full_history: bool = True` — visibile in UI come toggle
>    (i parametri booleani sono già supportati: `SignalParamControl.svelte:86-87` renderizza
>    una checkbox per `type === 'boolean'`).
> 2. `SignalWarmupRequirement` guadagna un flag `full_history: bool = False`;
>    `warmup_requirement()` lo imposta quando il parametro è attivo; `prepare_plan` lo propaga;
>    `get_prices_bulk` (`asset_source.py:2169-2180`) usa il cap `date.min` come inizio finestra.
>    `compute()` resta invariato; lo slicing a finestra visibile esiste già a valle
>    (`signal_series_preparation.py`).
> 3. **AI export forza sempre `full_history=true`** — i dataset con drawdown
>    (`portfolio.drawdown_context`, `asset_drawdown_snapshot` nel catalogo) devono dare
>    all'IA dati reali, mai la variante accorciata.
>
> **Perché non B (seed del max pre-periodo via query)**: il drawdown gira sulla serie
> **convertita in valuta target**; un `MAX(close)` SQL sul prezzo grezzo è corretto solo a
> parità di valuta (con FX variabile `max(convertita) ≠ convertita(max)`). Il vantaggio di B
> evapora proprio nel caso multi-valuta. Costo di A a scala self-hosted: trascurabile
> (~7.8k righe per 30 anni giornalieri, query unica già condivisa tra asset).

### Il test che manca

`test_risk_signal_plugins.py:149,161-297` verifica la matematica su array costruiti a mano, e
`test_signal_service_computes_five_risk_plugins_from_prepared_series` usa un `requested_range` che
parte a metà array — ma **in quel fixture il picco vero cade dentro il range visibile**, quindi il
test non distingue il comportamento corretto da quello difettoso.

> Stessa famiglia già censita in `05_cleanAudit/17_stabilizzazione_suite_completa.md`:
> **un controllo che non può fallire non è un controllo.**

**Test da aggiungere**: serie con il **massimo assoluto prima** del range visibile → il drawdown
nel range deve essere misurato su quel picco, non sul massimo locale. È l'unico test che
distingue le due implementazioni.

**Complessità**: Piccola (A) / Media (B) · Solo backend · Nessun cambio di schema

---

## ✅ E2 — Patrimonio netto: caso chiuso, nessuna fix necessaria

### L'ipotesi del tester

> *"il patrimonio netto da noi calcolato è di 544k€ ma stando al sito dovrebbero essere 530k€,
> e ci sono 14,6k€ di dividendi e interessi nel P&L … credo che stiamo sommando 2 volte i
> dividendi e interessi, uno nel P&L che li comprende e un altro nella liquidità."*

L'aritmetica sembrava confermarla: `544 − 14,6 ≈ 530`. **È una coincidenza.**

### Verifica: nessun doppio conteggio

```python
# portfolio_engine.py:1002-1004
broker_nav = market_value + cumulative_cash
nav        = broker_nav + in_transit_mv
```

```python
# portfolio_engine.py:1031-1032
capital_baseline = cumulative_ecf
total_pnl        = nav - capital_baseline        # derivato DA nav, mai risommato IN nav
```

- `net_worth` e `total_gain_loss` provengono da campi distinti (`portfolio_service.py:1501`, `:1503`).
- Il frontend li rende separatamente (`KpiSection.svelte:111-112`): il P&L è un'etichetta
  secondaria **sotto** il patrimonio, mai addizionata.
- Dividendi e interessi entrano in cassa **una volta sola**, dallo stesso ramo di un deposito
  (`portfolio_engine.py:571-579`), e **non** toccano `capital_baseline`
  (`_EXTERNAL_CASH_TYPES = {DEPOSIT, WITHDRAWAL}`, `:63`).
- Invariante già coperta: `test_portfolio_service.py:411-430` →
  `nav_value == cash_value + market_value`.

Che il P&L **cresca** all'arrivo di una cedola è corretto: è rendimento totale.

### La spiegazione vera

| Passo | € |
|---|---:|
| CTV titoli banca (05/08) | 530.179,12 |
| − BTP 01/03/35 mai importato (**P1/B1**) | −48.860,00 |
| = titoli in LibreFolio | 481.319,12 |
| + liquidità | ~58.800 – 63.700 |
| **= patrimonio netto atteso** | **540 – 545 k** ✅ |

Il "530k" del sito è il **controvalore titoli soltanto**: la liquidità della banca (63.681,75 €)
è un dato di intestazione separato. **Non era un confronto omogeneo.**

### Cosa fare comunque (basso costo, alto valore)

Nessuna fix di codice. Ma il fatto che l'ipotesi sia stata formulata segnala un **problema di
comunicazione**, non di calcolo:

1. **Documentazione** — rendere esplicito nella pagina KPI che *Patrimonio Netto* include la
   liquidità, e che **non** è confrontabile con il "controvalore titoli" di un estratto conto.
2. **Tooltip** — sul KPI, esplicitare la composizione `titoli + cassa (+ in transito)`.
   Si coordina con **T2** di P5 (ritardo dei tooltip).
3. **Test di non-regressione** — aggiungere un caso che mescola DIVIDEND e INTEREST e verifica
   che `nav` non cambi rispetto a un DEPOSIT di pari importo. L'invariante è verificata; questo
   test presidia specificamente **l'ipotesi del doppio conteggio**, così se un giorno qualcuno la
   introducesse, fallirebbe subito.

**Complessità**: Banale (doc + tooltip + 1 test) · Nessuna modifica al motore

---

## Verifica

```bash
./dev.py test backend --filter "test_risk_signal_plugins or test_risk_metrics or test_portfolio_service"
./dev.py lint
```

---

## Stato

> 🔄 **Riverificato il 02/09/2026** sul codice `dev_release2`.

| ID | Rilievo | Esito analisi | Stato |
|---|---|---|---|
| E1 | Drawdown relativo alla finestra | ✅ Confermato — warm-up insufficiente. **Nota 02/09**: la segnalazione originale era un fraintendimento del tester, ma il warmup restava sbagliato | ✅ **Fatto 02/09** — `DrawdownParams.full_history` (default true, toggle in UI via checkbox booleana già supportata, chiavi `chartSettings.params.fullHistory` + `signals.tooltips.riskFullHistory` ×4); flag `full_history` su `SignalWarmupRequirement` → `SignalExecutionPlan.requires_full_history` → `get_prices_bulk` carica da `date.min`. **AI export sempre full**: `_execute_drawdown` ignora il periodo del build (asset: `date.min`; portfolio/broker: prima transazione accessibile via `resolve_date_sentinels`) |
| E2 | Doppio conteggio dividendi/interessi | ❌ **Smentito** — formula corretta e testata | ✅ **Fatto 02/09** — nota "include liquidità / non confrontabile col controvalore titoli" in `kpi-cards.*.md` ×4; tooltip di composizione sulla card Net Worth (`dashboard.netWorthTooltip` ×4); test di presidio DIVIDEND+INTEREST vs DEPOSIT in carico a test-author |

> ⚠️ **Fuori pista (02/09, collaudo E1)**: il primo giro del segnale drawdown su dati reali mostrava il banner "segnali non aggiornati" con retry risolutivo. Causa radice trovata con probe su server di test: **non** E1 in sé, ma una dedup errori FX quadratico dentro il loop per punto in `get_prices_bulk` (`err not in result.errors` per ogni punto fallito × ogni errore). Sotto full-history, un asset con FX scoperto su storia lunga produce decine di migliaia di errori distinti → spin CPU 100% nel worker per minuti → axios 30s timeout → banner; il retry funzionava a cache calda. Fix: dedup O(1) una tantum per job + tetto 10 errori con riga riepilogo (il FE legge solo `errors[0]`). Riprodotto prima/dopo in-process: ∞ → 2.6s su asset con 46k prezzi.
