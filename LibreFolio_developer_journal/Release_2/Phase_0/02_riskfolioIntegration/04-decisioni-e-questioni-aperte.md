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

### Q2 — Rimozione delle dipendenze di ottimizzazione 🔵 aperta

Con D6, Riskfolio-Lib, CVXPY, CLARABEL e SCS restano nell'immagine senza essere
raggiungibili. Prima di decidere se rimuoverle **va misurato quanto pesano davvero**
sui 2.781.625.742 byte totali — il numero non è mai stato scomposto.

Se si rimuovono, cade anche il pool `optimization`; il pool `simulation` (QuantLib)
resta comunque necessario.

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

---

## 4. Prossimo blocco

**UI/UX per zona e scelta delle rappresentazioni grafiche.**

Input già disponibili: i quattro livelli, la mappa livelli × pagine, la regola dei pesi,
i verdetti per strumento, e nell'archivio i nove concept UI con ASCII art
(`_archive-backendFirst-G0G6/brainstorm-phase01RiskUiConcepts.md`) — da rileggere
criticamente alla luce della tesi, non da applicare così com'è.

Il piano esecutivo si scrive **dopo** quel blocco.
