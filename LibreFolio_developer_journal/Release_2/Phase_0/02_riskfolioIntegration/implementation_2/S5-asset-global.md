# S5 — Asset Global · il laboratorio ai livelli ridotti

> **Fase 2 · superficie.** Vincoli comuni: `implementation_2/_comune.md`
> **Sessione**: F `e-alfy-risk-asset-global-lab` (riuso)
> **Corsia**: `--test-port 6157` · `--data-dir /tmp/librefolio-r2-s5`
> **Leggi prima di scrivere**: `implementation_2/PRIMITIVE.md` (360 righe, per intero)

---

## 1. Hai consegnato la parte più importante della mappa, e ti manca il resto

`03-mappa-livelli-pagine` §2 prescriveva per Asset Global:

```
Asset Global = L2 + L1° + L3° + L4°      (%)    L2 primario, gli altri ridotti
```

✅ **L2 l'hai consegnato**, ed era *«la casa primaria della correlazione»*, la parte che il design
considerava più importante di quella pagina.

🔴 **Ma L1°, L3° e L4° arrivano ancora dal pannello legacy.** `AssetSetRiskPanel.svelte:285` monta
`RiskAnalysisPanel` — **1 068 righe** del muro di metriche che il ridisegno doveva sostituire — e
lo fa **dentro** la pagina che avevi costruito.

> 📌 **Una correzione a una mia affermazione precedente**: nella review avevo insinuato che il
> pannello vecchio sopravvivesse su due superfici per un fallimento. **Per Asset Detail è falso** —
> `03` dice testualmente *«Fuori scopo in questo giro: Asset Detail, parcheggiato in beta»*.
> **Per Asset Global invece il delta è reale, ed è il tuo.**

---

## 2. Cosa deve esserci alla fine

I tre livelli ridotti, **in percentuali**, al posto del legacy. `03` §2 dà i confini:

| | su Asset Global |
|---|---|
| **L1°** | per-asset, **in %**, come confronto — mai in euro |
| **L3°** | confronto **fra** asset, **mai un giudizio** |
| **L4°** | **solo replay storico**, in % — ❌ niente shock ipotetico |

🔑 **La regola che tieni tu e che nessun altro ha**: *«con i pesi → euro → "me"; senza pesi →
percentuali → "questi"»*. Un insieme di asset non ha pesi, quindi **non deve comparire un euro**.
È la prima delle sei cose che il tuo spec verifica, e vale anche per i tre livelli nuovi.

⚠️ **Il legacy espone `sobol_start_index` come controllo** (`RiskAnalysisPanel:1013-1021`, con
etichetta e `data-testid`) — e il design lo vieta: *«esce dalla UI in ogni caso»*. Il pannello
nuovo di H lo rispetta. **Togliendo il legacy da qui, togli anche quella violazione.**

---

## 3. La tua superficie

**Possiedi** `components/risk/AssetSetRiskPanel.svelte` e `components/risk/CorrelationHeatmap.svelte`.

**Non toccare**: `levels/L1*` → S1 · `L2*` → S2 · `L3*` → S3 · `levels/l4/*` → S4 ·
`RiskLevelsPanel.svelte` e `levelHelpers.ts` → **S1** · `RiskAnalysisPanel.svelte` **resta com'è**
(serve ad Asset Detail, che è fuori scopo) · `i18n/*.json` fuori dal tuo namespace.

⚠️ **Il vincolo che rende questo mandato delicato**: i componenti dei livelli sono di S1–S4, e tu
ne vuoi una **versione ridotta**. **Non copiarli.** Concorda con il coordinatore se la riduzione si
esprime con una prop (`variant`, `moneyless`) sui componenti degli altri, **o** con componenti
tuoi. È una decisione di architettura, non di implementazione, e va presa **prima** — altrimenti
nasce la quinta variante di ciò che esiste già in quattro.

---

## 4. Una copertura che hai perso senza saperlo

Risolvendo il conflitto `add/add` su `risk-lab.spec.ts` ha vinto la tua versione (6 test) su quella
di D (1 test). **Giusto**: il test di D cliccava `risk-asset-add-button`, che il tuo pannello non
ha più.

🔴 **Ma i tuoi sei test non toccano `risk-broker-filter`**, che D copriva. Il filtro esiste ancora
nel tuo pannello (`:195`). La copertura sopravvive dentro `risk-analysis.spec.ts`, **ma nel file
sbagliato**: va riportata nel laboratorio con la ricombinazione di **T3**. Non è tua da riparare —
**è tua da non dimenticare.**

---

## 5. Primo deliverable: analisi, non codice

1. **La riduzione**: prop sui componenti degli altri, o componenti tuoi? **Argomenta**, non
   scegliere e basta. È la decisione che blocca il resto.
2. Cosa fa oggi il legacy dentro la tua pagina che i tre livelli ridotti **non** coprirebbero?
   *(Cercare ciò che si perde, non solo ciò che si guadagna.)*
3. La regola «niente euro» regge sui tre livelli nuovi, o qualcuno di essi è in euro per
   costruzione?
4. I passi, con la verifica di ciascuno.

⚠️ **Nessuna riga di codice prima che l'analisi sia rivista.**
