# S2 — L2 · «Sono diversificato come credo?»

> **Fase 2 · superficie.** Vincoli comuni: `implementation_2/_comune.md`
> **Corsia**: `--test-port 6154` · `--data-dir /tmp/librefolio-r2-s2`
> **Leggi prima di scrivere**: `implementation_2/PRIMITIVE.md` (360 righe, per intero)

---

## 1. Il tuo livello è l'unico che oggi dice qualcosa di vero

Fino a stamattina L2 diceva *«Non disponibile per i dati selezionati»*. **F1 ha riparato i dati**
e adesso dice questo:

```
Cash and uncovered: 49,3 %
                       peso      contributo al rischio
Apple Inc.            14,7 %          80,0 %      +65,3pp
Bitcoin                1,9 %          12,8 %      +10,9pp
Tesla, Inc.            3,4 %           3,9 %       +0,4pp
```

> **Apple pesa il 14,7 % e produce l'80 % del rischio.** È esattamente la risposta che la domanda
> del livello chiede, ed è la prima volta che compare. **Il tuo lavoro non è farla apparire: è
> farla leggere.**

---

## 2. La tua superficie

**Possiedi** `components/risk/levels/L2Diversification.svelte`.

**Non toccare**: `L1*` → S1 · `L3*` → S3 · `levels/l4/*` → S4 · `AssetSetRiskPanel` → S5 ·
`RiskLevelsPanel.svelte` e `levelHelpers.ts` → **scrittore unico S1, chiedi a lui** ·
`i18n/*.json` fuori da `risk.levels.l2.*`.

---

## 3. Cosa deve esserci alla fine

### 3.1 🔴 La heatmap delle correlazioni, che il design assegnava a L2 e non c'è mai stata

`05-grammatica-visiva` §7.4 la prescriveva per L2. **Esiste** — `components/risk/CorrelationHeatmap.svelte`,
costruita da F nel round 1 — **ma è montata solo nel pannello legacy e nel laboratorio Asset Global.**

`03-mappa-livelli-pagine` §2 lo dice esplicitamente: per Dashboard e Broker Detail, L2 è
*«correlazione + contributo al rischio»*. **Oggi c'è solo la seconda metà.**

⚠️ **Verifica prima di montarla**: la heatmap è stata scritta per il laboratorio, dove non c'è
denaro e i pesi non esistono. Qui i pesi ci sono. **Controlla che le sue props reggano lo scope
`portfolio`**, e se non reggono, dillo invece di forzarle.

### 3.2 La tabella su card

`RiskCardGrid` + `RiskMetricCard` sono in `ui/display/` e **nessuno le usa ancora**: S1 e tu siete
i primi. `KpiDivergingFlowBar` esiste ed è fatta apposta per una barra a due versi attorno allo
zero — che è esattamente la forma di `+65,3pp`.

📌 **`PRIMITIVE.md` ha l'esempio montato da copiare.** Se non ti basta, **è un difetto del
documento e va riportato**, non aggirato.

### 3.3 I campi che hai e che oggi non mostri

| campo | backend | reso oggi |
|---|---|---|
| `effective_number_of_assets` | ✅ **14,97** | ✅ |
| `diversification_ratio` | ✅ **1,94** | ✅ |

> ⚠️ **`14,97` e `1,94` sono misure del 18 Set su corsia `aae526009`, finestra non dichiarata — e `1,94` ha da allora TRE referenti**: l'ANTE misurato da S2, il **post-A previsto da N (`1,9436`)**, e questa trascrizione. **Non usarli per un raffronto**: vale il vincolo Ⓕ di `_comune.md` — *nessun numero che integri sulla finestra*. Le cifre vive stanno in `progress/N2-esecuzione.md`, con corsia, finestra e `composition_as_of` accanto. Vedi **R2-42**, **R2-53**.
| `cash_weight` | ✅ **0,493** | ✅ |

**Questi tre ci sono già.** ⚠️ Ma `effective_number_of_assets` **non è un conteggio**, malgrado il
nome: è `1/Σw²`, un indice di concentrazione. Con `Σw = 0,507` contro `cash = 0,493` può leggere
**molto più alto del numero di posizioni**. `levelHelpers.ts:432-445` ha un commento che lo spiega
con il caso misurato — **leggilo prima di etichettarlo**, perché una card che dice
«numero effettivo di asset: 14,97» sopra sette posizioni dice al lettore che il software è rotto.

---

## 4. Primo deliverable: analisi, non codice

1. Hai letto `PRIMITIVE.md`? Cosa ti manca per montare card e griglia **senza chiedere a F2**?
2. `CorrelationHeatmap` regge lo scope `portfolio`? **Misura, non dedurre.**
3. `effective_number_of_assets`: quale etichetta, dato che non è un conteggio?
4. Il denominatore taciuto: L2 misura il **50,7 %** del NAV sotto un titolo che chiede
   «sono diversificato?». `cash_weight` è già reso — **basta, o va detto meglio?**
5. I passi, con la verifica di ciascuno.

⚠️ **Nessuna riga di codice prima che l'analisi sia rivista.**
