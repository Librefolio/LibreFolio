# S3 — L3 · «Sto venendo pagato per questo rischio?»

> **Fase 2 · superficie.** L'unica **full-stack**. Vincoli comuni: `implementation_2/_comune.md`
> **Corsia**: `--test-port 6155` · `--data-dir /tmp/librefolio-r2-s3`
> **Leggi prima di scrivere**: `implementation_2/PRIMITIVE.md` (360 righe, per intero)
> **Consulente**: il mandato **A** (`e-alfy-risk-oracle-math-migration`) per la matematica

---

## 1. Perché sei l'unico mandato full-stack della fase 2

`05-grammatica-visiva` §7.5 chiede lo **scatter rischio-rendimento**: X = volatilità,
Y = rendimento, **per ogni asset**, portafoglio a bolla ∝ peso, benchmark ◇, più la CML.

Il design stesso lo segnala: *«Unica proposta con un costo backend non marginale.»*
**Volatilità e rendimento per singolo asset oggi non esistono nel contratto.**

✅ **Il frontend però è già pronto**: F2 ha costruito `ScatterChart.svelte` +
`scatterChartHelpers.ts` (23 test), **con il contratto delle props preso da §7.5**, non inventato.
Lo trovi in `PRIMITIVE.md` §3. **Non costruire un grafico nuovo.**

⚠️ **`LineChart` non può farlo** e non provarci: il suo asse X è `type: 'category'` sulle date,
senza prop per cambiarlo, e `seriesType` non è nemmeno una sua prop — vive su `RenderedSignal`,
il sistema delle sovrapposizioni su serie storiche. F2 l'ha misurato prima di costruire.

---

## 2. 🔴🔴 La cosa che devi decidere, e che nessuno ha ancora deciso

**Il beta oggi legge circa zero, e non è un difetto dei dati.**

`L3Benchmark.svelte:70` manda `mode: 'historical'`. Misurato dal coordinatore sul ramo fuso,
stesso portafoglio e stesso benchmark:

| modo | beta | tracking error |
|---|---:|---:|
| `historical` | **−0,0079** | 0,1843 |
| `current_composition` | **+0,2327** | 0,1386 |

**Controprova a mano** sui prezzi grezzi con i pesi veri: **beta +0,189**, correlazione **+0,685**
— coerente col secondo, non col primo.

**Perché**: in `historical` la serie è il valore **reale nel tempo**, dominato da flussi,
ricomposizioni e dal **49 % di contante**. Un beta ~0 è **aritmeticamente corretto e privo di
significato come lettura di benchmark**.

> 🔑 **È la stessa forma che F1 ha chiuso un livello più sotto.** F1 aveva trovato un benchmark che
> dava beta `0,023` con zero avvisi — *«un benchmark solo di nome»* — e ha ricostruito gli indici
> perché co-muovessero (ora correlano **0,53–0,60** con i tre `STOCK` e **~0** con cripto e
> prestiti, che è giusto). **Il difetto è riapparso nella scelta del modo invece che nei dati.**

**La tua decisione**: quale modo risponde alla domanda *«sto venendo pagato per questo rischio?»*
— **e dichiaralo nella card**. Un beta senza il suo modo è un numero senza perimetro.

---

## 3. La tua superficie

**Possiedi**:
```
components/risk/levels/L3RiskAdjusted.svelte
components/risk/levels/L3Benchmark.svelte
backend/  — per volatilità e rendimento per-asset (concorda con il coordinatore PRIMA)
```

**Non toccare**: `L1*` → S1 · `L2*` → S2 · `levels/l4/*` → S4 · `AssetSetRiskPanel` → S5 ·
`RiskLevelsPanel.svelte` e `levelHelpers.ts` → **S1** · `i18n/*.json` fuori da `risk.levels.l3.*`.

---

## 4. Gli altri due difetti del tuo livello

**① Il selettore del confronto tronca** invece di riposizionarsi. Il developer:
*«dovrebbe scendere finché la pagina ha spazio, e nel caso mostrarsi verso l'alto»*.

> 🔴 **Correzione (18 Set, trovata da S3).** Avevo scritto: *«`Tooltip.svelte` ha già quella
> logica — flip a `:267`, clamp a `:314`. Non scrivere un popover nuovo.»* **`Tooltip` non
> c'entra.** Il selettore non è un popover scritto a mano: è `AssetSelect` → **`SearchSelect`**,
> che ha già `position: fixed` calcolata a mano (`:169-177`, quindi esce da qualunque
> `overflow: hidden`) e `dropdownPosition: 'top' | 'bottom' | 'auto'` (`:153-166`).
> `AssetSelect` inoltra già la prop (`:62`) e **`L3Benchmark.svelte:84` non la passa** → default
> `'bottom'` → la lista **si tronca invece di ribaltarsi**. **La riparazione è una prop.**
> ⚠️ E ci sono **due** troncature diverse — la lista che non si ribalta, e i nomi tagliati da
> `max-w-xs` sul trigger: **quale intendesse il developer va visto nel browser**, non dedotto.
> 📌 Ho indicato la primitiva sbagliata avendo verificato che `Tooltip` esiste e fa quel lavoro
> **da un'altra parte**: R2-19, stessa forma delle altre quattro.

**② Mancano i grafici concordati**: lo scatter §7.5 è il tuo, e con `ScatterChart` già pronto il
costo è quasi tutto backend.

---

## 5. Primo deliverable: analisi, non codice

1. **Il modo del beta**: quale, e perché? È la decisione che blocca il resto.
2. Volatilità e rendimento per-asset: quale analitica li produce, o ne serve una nuova?
   **Chiedi ad A** prima di derivare la matematica da solo.
3. `ScatterChart`: il contratto delle props di `PRIMITIVE.md` copre il tuo caso?
   ⚠️ **§7.5 è ambiguo su un punto** e F2 l'ha dichiarato invece di deciderlo: la bolla ∝ peso è
   **il portafoglio** o **i singoli asset**? F2 ha implementato la lettura flessibile. **Decidi tu.**
4. Il selettore: `Tooltip` basta, o serve altro?
5. I passi, con la verifica di ciascuno.

⚠️ **Nessuna riga di codice prima che l'analisi sia rivista.**
