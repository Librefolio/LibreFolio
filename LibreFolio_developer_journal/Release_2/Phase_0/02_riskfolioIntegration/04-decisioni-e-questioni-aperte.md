# 04 — Decisioni e questioni aperte

**Data apertura**: 16 Settembre 2026
**Natura**: documento **vivo**. Ogni decisione presa si registra qui con data e
motivazione; ogni questione aperta resta qui finché non è chiusa.

---

## 1. Decisioni prese

| # | Data | Decisione | Motivazione |
|---|---|---|---|
| D1 | 16 Set 2026 | **Tesi adottata**: Risk risponde a *«il mio portafoglio è quello che credo che sia?»*, non a *«quanto rischio ho?»* | Un numero isolato non produce decisioni; una discrepanza sì |
| D2 | 16 Set 2026 | **Quattro livelli di domanda** (L1 fatti · L2 struttura · L3 relatività · L4 proiezione) | L1/L2/L4 sono autoreferenziali; serviva la domanda comparativa, altrimenti Sharpe/beta/TE restano senza casa |
| D3 | 16 Set 2026 | **Regola dei pesi**: con pesi → euro → «io»; senza pesi → percentuali → «questi» | Rende impossibile per costruzione confondere Asset Global con Broker Detail |
| D4 | 16 Set 2026 | **VaR/CVaR restano**, riformulati in scala temporale con CVaR primario | Sono oggettivi e basati sui dati; il difetto era l'assenza di scala dichiarata |
| D5 | 16 Set 2026 | **TE e IR rimossi dalla UI** (backend intatto) | Misurano l'aderenza a un mandato che un investitore privato non ha |
| D6 | 16 Set 2026 | **Portfolio optimization rinviata** a tempo indeterminato | Output prescrittivo non giustificabile; LibreFolio è un tracker, non un consulente |
| D7 | 16 Set 2026 | **Monte Carlo rifondato fino al livello 3** (bootstrap, GJR-GARCH, preset prescritti); livelli 4-5 rinviati | Il bootstrap batte il GBM su onestà, realismo, spiegabilità e costo |
| D8 | 16 Set 2026 | **Asset Detail parcheggiato in beta**, fuori da questo giro | Priorità su Dashboard, Broker Detail e Asset Global |
| D9 | 16 Set 2026 | **Segnali rolling restano nella Overview di Asset Detail** | Stanno bene dove sono; una card con un solo valore puntuale perde la forma nel tempo |
| D10 | 16 Set 2026 | **Broker Detail = stessa grammatica di Dashboard**, stesso componente con scope diverso | Già vero nel codice; va reso esplicito e preservato |
| D11 | 16 Set 2026 | **Asset Global = laboratorio**, non «un'altra vista del portafoglio» | Il pannello `analysis` rende il concetto già di prima classe nel modello dati |
| D12 | 16 Set 2026 | **Catena G6 abbandonata**, non ripresa | 23 item a catena singola con gate bloccanti: un solo stop congela tutto |
| D13 | 16 Set 2026 | **L3 con benchmark persistente** scelto fra gli asset in DB, da subito | Senza benchmark persistente il beta è un numero senza contesto e L3 resta la domanda debole |
| D14 | 16 Set 2026 | **Serie di drawdown dal backend**, non derivata client-side | Una curva calcolata nel browser può contraddire lo scalare del motore: due numeri discordi sullo stesso schermo costano più fiducia di quanta ne dia il grafico. Costo minore del previsto: `RiskComparisonPoint.primary_drawdown` già la calcola |
| D15 | 16 Set 2026 | **Ricostruire i componenti risk** sulle primitive condivise, dopo aver promosso quelle generiche in `components/ui/` | Ridisegnare il layout sopra gli stessi mattoni storti non risolve nulla |
| D16 | 16 Set 2026 | **Istogramma della distribuzione dei rendimenti** in v1, con VaR e CVaR marcati sopra; nuovo campo backend per i bin | Rende visibile la *definizione* delle due metriche: il CVaR è la media della coda rossa. Nessun testo lo spiega meglio |
| D17 | 16 Set 2026 | **Sei rappresentazioni adottate**: underwater, istogramma, barre appaiate peso/contributo, heatmap rifatta, scatter rischio-rendimento, tornado degli scenari | Ogni numero ha una forma che lo spiega; la card numerica è il ripiego, non il default |
| D18 | 16 Set 2026 | **`SignalDomain.PORTFOLIO` non serve per la v1** | Le sei rappresentazioni scelte usano dati che il backend già produce. Per la volatilità l'istogramma dice più di una sparkline del suo rolling |
| D19 | 16 Set 2026 | **Selezione di Asset Global persistita in `localStorage`**, con fallback agli asset posseduti | Il seed a cento asset apre una matrice di diecimila celle e non offre alcun modo di disfarla |
| D20 | 16 Set 2026 | **Nessuna generalizzazione della piattaforma segnali** per l'underwater chart | `underwater_drawdown` vive già in `services/risk/metrics.py` ed è il *segnale* a importarla dal rischio, non il contrario. `drawdown_episodes()` calcola già la serie in una variabile locale e ne butta via tutto tranne gli scalari |
| D21 | 16 Set 2026 | **Bin dell'istogramma secondo Freedman-Diaconis**, con un bordo forzato sul quantile del VaR e binning sulla stessa serie a `horizon_days` | L'IQR è robusto agli outlier; deviazione standard e normalità userebbero la coda per decidere come disegnare la coda. Il bordo forzato rende l'area rossa esattamente il 5% |
| D22 | 16 Set 2026 | **Nessuna gaussiana sovrapposta all'istogramma** (chiude Q6) | Il VaR mostrato è un quantile empirico: la campana confronterebbe i dati con un modello che non usiamo, e suggerirebbe che lo scarto sia un'anomalia mentre le code grasse sono la norma |
| D23 | 16 Set 2026 | **Riskfolio-Lib resta installata** (chiude Q2) | Misurata: 2,5 MB, closure solver ~16 MB su 2 780 totali. Lo 0,6% dell'immagine. I pesi veri sono scipy, pandas e QuantLib |
| D24 | 16 Set 2026 | **Le funzioni scalari di `metrics.py` non si toccano** | Coincidono con Riskfolio fino all'ottavo decimale su VaR, max drawdown, Sharpe e risk contribution; costano microsecondi; `math.fsum` dà una sommatoria compensata che `np.sum` non garantisce |
| D25 | 16 Set 2026 | **Riskfolio diventa oracolo di test per `metrics.py`** | `test_risk_metrics.py` verifica solo proprietà interne: nessun controllo indipendente. Venti righe coprono il buco e avrebbero intercettato da sole la trappola `MDD_Abs`/`MDD_Rel` |
| D26 | 16 Set 2026 | **`correlation_matrix` e `covariance_matrix` vanno vettorializzate** | O(N²·T) in Python puro: 3,7 s su cento asset contro 0,2 ms di NumPy. Il Python puro trattiene la GIL, NumPy la rilascia nel BLAS |
| ~~D27~~ | ~~16 Set 2026~~ | ~~Convenzione CVaR nostra confermata~~ | **REVOCATA lo stesso giorno da D28.** Motivata dalla spiegabilità, senza aver misurato la distorsione |
| D28 | 16 Set 2026 | **CVaR migra allo stimatore coerente** (Acerbi-Tasche / Rockafellar-Uryasev), off-by-one incluso | Il nostro è più basso di Riskfolio **2000 volte su 2000**, in media −0,27%, a sette deviazioni standard dallo zero. Non è convenzione: è distorsione. L'argomento della spiegabilità non regge, perché Acerbi-Tasche *è* «la media delle giornate peggiori» e lo scarto è invisibile |
| D29 | 16 Set 2026 | **Segnali rolling migrano a `pandas.rolling`** — priorità massima | `signal_helpers.py:69-84` copia una fetta e richiama la funzione scalare a ogni passo: fino a **1 514× più lento a valori identici**, e gira a ogni caricamento di grafico |
| D30 | 16 Set 2026 | **Le funzioni scalari a chiamata singola restano in Python puro** | Tutte sotto il millisecondo. E sul max drawdown il nostro **batte Riskfolio di quattro volte**, perché `MDD_Rel` è anch'essa interpretata: migrare in blocco peggiorerebbe quella riga |
| D31 | 16 Set 2026 | **I 17 plugin di analisi tecnica non si toccano** | Audit: una sola chiamata `ta.*` ciascuno, zero aritmetica a mano dopo. Sono il modello, non il debito |

---

## 2. Rinvii registrati in `TODO_FUTURI.md`

| Voce | Priorità | Precondizione dichiarata |
|---|---|---|
| Tracking Error / Information Ratio con benchmark selezionabile | 🔽 bassa | Benchmark persistente **e** una ragione semantica, non solo tecnica |
| Portfolio optimization / frontiera efficiente (Riskfolio) | 🔽 molto bassa | Provider dati esteso, semantica non prescrittiva, esclusione del max-Sharpe |
| Monte Carlo avanzato: Markov calibrato e volatilità stocastica | 🔽 bassa | Storia lunga e verificata (liv. 4); fonte dati di opzioni (liv. 5) |
| Catalogo scenari dinamico, proxy persistenti, RQMC | — | Preesistenti alla ripianificazione, invariati |

---

## 3. Questioni aperte

### Q1 — Dove vive il benchmark persistente 🔵 aperta

Decisione D13 presa; l'implementazione no.

**Casa naturale individuata**: `UserSettings` (`backend/app/db/models.py:330`), tabella
per-utente con colonne tipizzate (`base_currency`, `language`, `theme`, `avatar_url`).
Un benchmark è esattamente della stessa natura di `base_currency`: **l'unità di misura
personale dell'utente**.

Ipotesi di lavoro:

```python
risk_benchmark_asset_id: Optional[int] = Field(
    default=None, foreign_key="assets.id", nullable=True
)
```

Richiede una **migrazione Alembic incrementale** (nessuna modifica a `001_initial.py`:
lo schema è già rilasciato).

Sotto-questioni da chiudere:

1. **Ambito**: uno solo per utente, oppure uno per scope (portafoglio / broker)?
   *Orientamento*: **uno solo**. Un benchmark diverso per pagina distruggerebbe la
   confrontabilità Dashboard ↔ Broker Detail stabilita in D10.
2. **Override temporaneo**: si può cambiare benchmark al volo senza salvarlo?
3. **Vincoli di ammissibilità**: storia sovrapposta minima, valuta, avviso quando il
   benchmark non copre il periodo selezionato.
4. **Default**: nessuno (L3 parziale finché non si sceglie) oppure proposta automatica?
5. **Visibilità**: che succede se l'asset scelto come benchmark viene cancellato o perde
   la condivisione?

### Q2 — Rimozione delle dipendenze di ottimizzazione 🟢 chiusa → D23

Con D6, Riskfolio-Lib, CVXPY, CLARABEL e SCS restano nell'immagine senza essere
raggiungibili dal prodotto. La domanda era se valesse la pena rimuoverle.

**Misurato** (vedi [`06`](./06-matematica-librerie-e-reimplementazioni.md) §5):
Riskfolio pesa **2,5 MB**, l'intera closure di solver circa **16 MB su 2 780** —
lo 0,6%. I pesi veri sono `scipy` 96,6 MB, `pandas` 66,8 MB, `QuantLib` 59,6 MB.

**Chiusa in negativo: Riskfolio resta.** Rimuoverla non risolverebbe il problema
dell'immagine, e D25 le assegna un ruolo nuovo — oracolo di test — che la rende
utile anche senza `portfolio_optimization` attiva.

La premessa della domanda era sbagliata, e solo la misura poteva dirlo.

### Q3 — Colonne di rischio nelle tabelle di Asset Global 🔵 aperta

Ipotesi ad alto rapporto valore/costo (vedi documento 03 §4): volatilità annua, max
drawdown e correlazione media come colonne delle tre tabelle esistenti, sfruttando la
sincronizzazione già presente. Da valutare nel blocco UI/UX.

### Q4 — Destino del banner beta 🔵 aperta

Orientamento coerente con la tesi: il banner si rimuove dai livelli fondati su fatti
osservati (L1, L2, L3) e **resta solo su L4**, dove è vero — e anche lì, solo sul
gradino «simulazione», non su replay e shock che sono deterministici.

Da confermare quando le viste saranno ridisegnate.

### Q5 — Documentazione utente 🔵 aperta

D4 prevede un link alla documentazione **per riga** della scala L1. Le pagine
`mkdocs_src/docs/financial-theory/technical-analysis/risk-metrics/` esistono già per
volatilità, Sharpe, Sortino e max drawdown, ma **non** per CVaR/VaR, correlazione,
contributo al rischio, replay e simulazione.

Da pianificare insieme alla UI: ogni metrica mostrata dovrebbe avere la sua pagina.

### Q6 — Curva normale sovrapposta all'istogramma 🟢 chiusa → D22

D16 adotta l'istogramma della distribuzione dei rendimenti con VaR e CVaR marcati.
Si era considerato di sovrapporre la **gaussiana** con la stessa media e deviazione
standard, per mostrare quanto le code reali siano più grasse di quelle del modello.

**Chiusa in negativo.** Il VaR mostrato è `historical_var`, cioè un quantile empirico:
nessuna assunzione di normalità entra nel calcolo, quindi la campana sarebbe il
confronto con un modello che non stiamo usando — risponde a «perché altri strumenti
sbagliano», domanda che su L1 nessuno ha posto.

Peggio, produrrebbe un danno attivo: una campana accanto ai dati suggerisce che la
campana sia il comportamento *atteso* e lo scarto un'anomalia. È rovesciato — per i
rendimenti finanziari le code grasse **sono** la norma.

La lezione resta valida e va nella pagina wiki sul VaR (Q5). L'unico punto dove si
guadagnerebbe il posto è **L4**: lì un modello lo stiamo davvero scegliendo, e mostrare
cosa assume il GBM contro cosa produce il bootstrap è decision-relevant.

---

## 4. Prossimo blocco

Il blocco UI/UX è stato svolto ed è confluito in
[`05-grammatica-visiva-e-rappresentazioni.md`](./05-grammatica-visiva-e-rappresentazioni.md),
che contiene la diagnosi estetica verificata sul codice, il contratto di primitive,
l'anatomia della card e le sei rappresentazioni con il loro costo.

**Prossimo**: il piano esecutivo, che ordina il lavoro in workstream e ne definisce
i gate. Si scrive dopo aver chiuso Q1 (dove vive il benchmark persistente), unica
questione che blocca L3.
