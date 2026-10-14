# Contratto proposto — `ASSET_SET` per i livelli ridotti di Asset Global

> **Autore**: mandato **A — Asset Global**, round 3. **Destinatario**: il mandato backend dipendente.
> **Stato**: proposta di contratto, **non un'implementazione**. Ratificata nel disegno dal
> coordinatore il 21 Set 2026.
> **Piano vivo del proponente**: [`A-esecuzione.md`](./progress/A-esecuzione.md)

---

## 0. Perché questo documento esiste

`03-mappa-livelli-pagine` §2 prescrive per Asset Global `L2* + L1° + L3° + L4°`, in percentuali.
**L2\* e L4° sono consegnati.** `L1°` e `L3°` non lo sono, e il briefing che li assegnava diceva
che *«escono dal monolite»*.

**Misurato: è falso.** `RiskAnalysisPanel` cancella ogni sezione dietro una capability del catalogo
(`RiskAnalysisPanel.svelte:124-130`), e su `asset_set` il backend ne concede due.

```
🟢 correlation            (ASSET_SET, PORTFOLIO)
🟢 stress                 (ASSET, ASSET_SET, PORTFOLIO)
🟡 portfolio_optimization (ASSET_SET, PORTFOLIO)   ← esiste, ma è TODO_FUTURI: non esiste per la UI
🔴 historical_kpi · historical_var · drawdown_summary · comparison · simulation
🔴 asset_risk_return · risk_contribution           ← PORTFOLIO only
```

> **Per la UI sono 2 plugin su 9, ed è esattamente la coppia già consegnata.**
> `L1°` e `L3°` non sono un'estrazione: **sono una costruzione su un percorso dati che non esiste.**

---

## 1. 🔴 La clausola ⓪ — *la ragione per cui questo mandato esiste*

**Una preparazione sola per richiesta.**

Non è una clausola fra le altre: **è il motivo per cui la via alternativa è stata scartata.**

L'alternativa era il fan-out: N richieste a scope `asset`, una per asset selezionato. È stata
respinta prima per costo, poi — decisivamente — **per correttezza**. `l3Helpers.ts`
`buildRiskReturnPoints` porta un avviso di S3 che vieta esattamente quella composizione:

> *«That figure is prepared differently: asset scope, historical mode, its own joint calendar — a
> different number of observations over the same reported `analyzed_range`. Mixing it with a beta
> from this wave breaks the textbook identity `sigma_b = rho * sigma_p / beta` by roughly a fifth,
> and nothing on screen would show why … **The dot would land in a place no measurement puts it,
> on a chart that still looks right.**»*

È il vincolo **Ⓔ** di `_comune.md`. N richieste a scope `asset` = **N preparazioni separate, N
calendari congiunti diversi**, poi disegnate sullo stesso grafico come se fossero commensurabili.

> 🔑 **Il fan-out non era caro: era sbagliato.** Una richiesta `ASSET_SET` sola è una preparazione
> sola, quindi ogni punto nasce sulle stesse date — che è la sola proprietà che rende i punti
> confrontabili, ed è l'intero scopo di una pagina di confronto.
>
> **Una scelta presa per costo si riapre appena il costo cambia; una presa per correttezza no.**

---

## 2. Il precedente da seguire — esiste già, in produzione

`stress` su `ASSET_SET` **restituisce già una lista per-asset con il peso opzionale**:

```python
class RiskStressImpact(StrictModel):
    asset_id: PositiveInt
    weight: Optional[FiniteFloat] = None   # ← None quando lo scope non ha pesi
    shock_return: FiniteFloat
    ...
impacts: List[RiskStressImpact]
```

> **La forma che serve a `L1°`/`L3°` non va progettata: è già stata scelta da questo progetto,
> è in produzione, e il campo `weight` è opzionale proprio per lo scope senza pesi.**
> Questo contratto **non introduce un disegno nuovo**: allinea i plugin rimasti indietro a uno
> che c'è già.

---

## 3. I plugin

| plugin | serve a | modifica |
|---|---|---|
| `historical_kpi` | `L1°` (σ ann.) · `L3°` (Sortino, Sharpe, σ per asset) | `+ASSET_SET`; output **per-asset** in una lista sul modello `impacts` |
| `historical_var` | `L1°` (giornata storta 1g, mese storto 21g) | `+ASSET_SET`; idem |
| `drawdown_summary` | `L1°` (peggior discesa, durata, risalita necessaria) | `+ASSET_SET`; idem |
| `asset_risk_return` | `L3°` — **è lo scatter, cioè l'intero livello** | vedi §4 |
| `comparison` | `L3°` (colonna β contro un `is_benchmark`) | `+ASSET_SET`, **oppure** resta per-asset e `L3°` lo interroga per la sola colonna β |

📌 `risk_contribution` **non entra**: senza pesi non esiste il dato, e S2 lo ha già misurato —
su `asset_set` risponde `200` con `status=unavailable`, `error=incompatible_scope`, `output=None`.
*«Nessuna delle tre card perde significato: non esiste proprio il dato.»* **Resta `PORTFOLIO`-only.**

---

## 4. `asset_risk_return` — misurato riga per riga: **non ha bisogno dei pesi**

**L'aritmetica per-punto non li tocca.** `volatility` e `expected_annual_return` escono da
`prepared_asset_returns(context, asset_id)`, una serie per-asset. **Nessun peso entra in nessuno
dei due numeri.**

I pesi compaiono in **tre punti, tutti accessori** — e **il frontend è già tollerante su tutti e
tre**:

| dove (backend) | cosa fa | consumatore (frontend) |
|---|---|---|
| `if any(asset_id not in context.weights)` → `DATA_UNAVAILABLE` | **è il solo blocco vero** | — |
| `RiskReturnItem.weight: FiniteFloat` | dimensione della bolla | `weight === null ? undefined : weight` ✅ già opzionale |
| `portfolio_volatility` / `portfolio_expected_annual_return` | il punto «il tutto» | dietro `if (… !== null && … !== null)` ✅ già opzionale |
| `cash_weight: Field(0, ge=0)` | nota sulla liquidità | dietro `cash !== null && cash > 0` ✅ già a default |

> 🔑 **Quindi: tre campi resi opzionali + una guardia rimossa + l'enum, e ZERO modifiche al
> frontend.**

📌 L'obiezione della docstring del plugin — *«Offering this in `historical` would have to invent
weights»* — **parla di modalità, non di scope.** Non vieta `ASSET_SET`.

---

## 5. Le sei clausole

| | clausola | perché |
|---|---|---|
| **⓪** | 🔴 **Una preparazione sola per richiesta** | §1 — *la ragione per cui il mandato esiste* |
| **①** | 🔴 Su `ASSET_SET`, `portfolio_volatility` e `portfolio_expected_annual_return` sono **`None`, mai un aggregato fabbricato** | §6 — **è ciò che tiene fuori il giudizio** |
| **②** | `weight` **opzionale ovunque** | precedente `RiskStressImpact` |
| **③** | Storia insufficiente → voce **dichiarata**, **mai zero-fill** | Ⓑ; ed è l'onestà che `asset_risk_return` già pratica col suo `continue` |
| **④** | **`n_observations` per asset deve viaggiare** | Ⓔ — è **l'unico campo che distingue due preparazioni**, e **nessuna card lo mostra**: debito di UI da assegnare, non un dettaglio |
| **⑤** | `supported_modes` su `ASSET_SET`: **domanda aperta da risolvere, non da ereditare** | §7 |

---

## 6. 🔴 La clausola ① è una decisione di prodotto difesa nel backend

Il design vieta il giudizio su questa pagina: `03` §2 dice `L3°` = *«confronto **fra** asset,
**mai un giudizio**»*.

Sullo scatter il giudizio è la **Capital Market Line**: «sopra la linea = pagato bene».
Misurato, la retta non è cancellata dal tasso privo di rischio ma **dall'esistenza di un punto
`role === 'portfolio'`** (`scatterChartHelpers.ts:111-116`), che a sua volta esiste solo se il
payload porta `portfolio_volatility` **e** `portfolio_expected_annual_return` non nulli
(`l3Helpers.ts:117`).

> **Su un insieme di asset non c'è un portafoglio → non c'è il punto → la retta non può nascere.
> Il giudizio non va soppresso: è impossibile.**
>
> 🔴 **Ma solo finché il backend non ne fabbrica uno.** Se `ASSET_SET` restituisse un aggregato
> equipesato «per comodità», il punto tornerebbe, la retta tornerebbe, **e il giudizio rientrerebbe
> dalla porta dei dati — invisibile a qualunque test del frontend, perché il frontend starebbe
> facendo esattamente il suo lavoro.**

**Una decisione di prodotto difesa da un'impossibilità strutturale non si può disfare per
distrazione. Una difesa da un interruttore sì.** Per questo la clausola sta qui e non in una prop.

---

## 7. La domanda aperta ⑤

`asset_risk_return` dichiara oggi `supported_modes = (CURRENT_COMPOSITION,)`, e la sua docstring
argomenta che un punto per-asset è *«a statement about the mix held now»*.

**Su un insieme di asset non esiste «la composizione detenuta oggi»**: non c'è una composizione,
c'è una selezione. Quindi su `ASSET_SET` la modalità va **decisa**, non ereditata:

- `HISTORICAL` — coerente con `correlation`, che su `asset_set` vive lì, **e con ⓪**: sarebbe la
  stessa onda, quindi la stessa preparazione di L2\*;
- `CURRENT_COMPOSITION` — conserverebbe la simmetria col caso portfolio, ma su uno scope dove il
  nome non descrive niente.

**Raccomandazione del proponente: `HISTORICAL`**, perché mette `L1°`, `L2*` e `L3°` sulla stessa
onda e quindi — per ⓪ — **sulla stessa preparazione**, che è la proprietà che rende la pagina
confrontabile con sé stessa. **Ma è una decisione del mandato backend, e va scritta, non assunta.**

---

## 8. Come lo verificherà il proponente

Il coordinatore ha assegnato ad **A** la prova end-to-end dopo il merge della piattaforma:
`L1°` e `L3°` montati su Asset Global, **una sola richiesta per livello**, ogni punto sulla stessa
preparazione, e il cancello *«nessun euro su questa pagina»* ancora dietro un click.

⚠️ **E la clausola ① va provata con un test che fallirebbe se il backend fabbricasse il
portafoglio** — altrimenti è una clausola scritta, non una difesa.
