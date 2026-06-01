# Plan: RSI Signal — Zone Band Style

**Data**: 1 Giugno 2026
**Status**: ✅ DONE (2026-06-01)
**Priority**: P2 (UX significativo — i parametri overbought/oversold erano inutilizzati)
**Tipo**: Independent mini-plan (segnale chart, no transazioni)

## 🤖 Modello Suggerito & Effort

| Parametro | Valore |
|-----------|--------|
| **Modello** | `claude-sonnet-4.6` |
| **Effort stimato** | ~2-3h |
| **Difficoltà** | Bassa-Media |
| **Rationale** | Override `renderMulti` in `RsiSignal.ts` + piccole modifiche a `SignalStyleEditor` e `ChartSignalsSection` per nascondere il selettore lineType. Il colore è già gestito dal selettore stile esistente. Pattern di riferimento chiaro (MacdSignal). Unica complessità: logica segmentazione con junction points. |

---

## 🎯 Obiettivo

Attualmente `RsiSignal` ha i parametri `overbought` (default 70) e `oversold` (default 30)
ma non li usa nella visualizzazione: la linea RSI è sempre uniforme.

Il risultato desiderato è che la linea RSI cambi **stile** (lineType e lineWidth) in base alla
zona, usando **il colore già configurato dall'utente** nel selettore stile del segnale (`style.color`).
Il meccanismo è analogo alla main price line che viene spezzata in segmenti per zona.

| Zona | Condizione | Stile desiderato |
|------|-----------|-----------------|
| Oversold | `rsi < oversold` (es. < 30) | Linea **continua**, **+1px** spessa |
| Neutral | `oversold ≤ rsi ≤ overbought` | Linea **tratteggiata**, larghezza normale |
| Overbought | `rsi > overbought` (es. > 70) | Linea **continua**, **+1px** spessa |

Il **colore** è sempre `style.color` — uguale in tutte le zone, scelto dall'utente nel pannello
segnali tramite il selettore colore già esistente. Nessun nuovo parametro aggiunto.

Poiché il `lineType` è ora determinato automaticamente dalla zona, il relativo selettore
**non deve apparire** nell'editor stile del segnale RSI (solo colore, lineWidth e markers).

---

## Stato Attuale (code-verified 2026-06-01)

| Componente | Stato |
|---|---|
| `RsiSignal.ts` — `computePoints()` | ✅ Corretto, produce `LineDataPoint[]` |
| `RsiSignal.ts` — `static signalType = 'rsi'` | ✅ Chiave identificativa disponibile |
| `RsiSignal.ts` — `renderMulti()` | ❌ Non override — usa base class (1 linea uniforme) |
| `ChartSignal.ts` — `RenderedSignal` | ✅ Ha `lineType`, `lineWidth`, `color`, `yAxisIndex` |
| `ChartSignal.ts` — `SignalParamDescriptor` | ✅ Invariato — nessuna modifica necessaria |
| `SignalStyleEditor.svelte` — prop | ✅ Ha `simplified?: boolean` — pattern da estendere con `hideLineType` |
| `ChartSignalsSection.svelte` | ✅ Già branchia `signalType === 'macd'` per stile speciale — stessa logica per RSI |
| `MacdSignal.ts` — `renderMulti()` override | ✅ Pattern di riferimento per multi-series |

---

## Step 1 — Override `renderMulti` in `RsiSignal`

**File**: `frontend/src/lib/charts/signals/RsiSignal.ts`

### Algoritmo di segmentazione

```
Per ogni punto RSI:
  - se value < oversold → zona 'oversold'
  - se value > overbought → zona 'overbought'
  - altrimenti → zona 'neutral'

Costruire segmenti contigui per zona.
Ogni segmento ha [start_index, end_index] e una zona.
Ai confini di transizione: il punto di giunzione è incluso in ENTRAMBI i segmenti
adiacenti (per evitare gap visivi di 1px).
```

### Stile per zona

```typescript
// Stesso colore in tutte le zone (dal selettore stile segnale).
// Solo lineType e lineWidth variano.
function zoneStyle(zone: 'oversold' | 'neutral' | 'overbought', baseWidth: number) {
    if (zone === 'neutral') {
        return { lineType: 'dashed' as const, lineWidth: baseWidth };
    }
    // overbought e oversold: continua + spessa
    return { lineType: 'solid' as const, lineWidth: baseWidth + 1 };
}
```

### Implementazione `renderMulti`

```typescript
override renderMulti(baseData: LineDataPoint[], viewMode: 'absolute' | 'percentage'): RenderedSignal[] {
    const allPoints = this.computePoints(baseData);
    if (allPoints.length === 0) return [];

    const overbought = Number(this.params.overbought ?? 70);
    const oversold = Number(this.params.oversold ?? 30);

    type Zone = 'oversold' | 'neutral' | 'overbought';
    const getZone = (v: number): Zone => {
        if (v < oversold) return 'oversold';
        if (v > overbought) return 'overbought';
        return 'neutral';
    };

    // Build contiguous segments
    interface Segment { zone: Zone; startIdx: number; endIdx: number }
    const segments: Segment[] = [];
    let currentZone = getZone(allPoints[0].value);
    let segStart = 0;

    for (let i = 1; i <= allPoints.length; i++) {
        const z = i < allPoints.length ? getZone(allPoints[i].value) : null;
        if (z !== currentZone || i === allPoints.length) {
            segments.push({ zone: currentZone, startIdx: segStart, endIdx: i - 1 });
            currentZone = z!;
            segStart = i - 1; // overlap: include junction point in next segment
        }
    }

    // Build one RenderedSignal per segment
    const baseWidth = this.style.lineWidth;
    const color = this.style.color;

    return segments
        .map((seg) => {
            const segData = allPoints.slice(seg.startIdx, seg.endIdx + 1);
            if (segData.length === 0) return null;
            const s = zoneStyle(seg.zone, baseWidth);
            return {
                id: `${this.id}-${seg.zone}-${seg.startIdx}`,
                label: seg.startIdx === 0 ? this.getLabel() : '',  // label solo sul primo
                data: segData,
                color,
                lineWidth: s.lineWidth,
                lineType: s.lineType,
                markerStart: seg.startIdx === 0 ? this.style.markerStart : null,
                markerEnd: seg.endIdx === allPoints.length - 1 ? this.style.markerEnd : null,
                yAxisIndex: (this.constructor as typeof ChartSignal).yAxisIndex,
            } satisfies RenderedSignal;
        })
        .filter((s): s is RenderedSignal => s !== null);
}
```

> **✅ Note implementazione (2026-06-01)**: Implementato. Rispetto allo pseudocodice del piano, la versione finale usa `if (z !== null)` guard esplicito invece di `z!` non-null assertion (più sicuro con strict mode). Il loop è stato semplificato: il boundary check usa `z !== currentZone` (quando `z === null` cioè fine array, si chiude l'ultimo segmento). Import `RenderedSignal` aggiunto.

---

## Step 2 — Nascondere il selettore `lineType` nella UI del segnale RSI

Il `lineType` per RSI è ora determinato dalla zona, non dall'utente.
Bisogna nasconderlo dal popover di `SignalStyleEditor`, lasciando visibili solo colore, lineWidth e markers.

### Architettura attuale (code-verified)

- `SignalStyleEditor.svelte` — editor stile usato da tutti i segnali non-MACD
  - Mostra: color picker + pulsante preview → popover con **lineType**, lineWidth, markers
  - Ha già prop `simplified?: boolean` come precedente per nascondere markers
- `ChartSignalsSection.svelte` — linea 657: `{#if signal.signalType !== 'macd'}` → usa `SignalStyleEditor`

### Modifiche

**`SignalStyleEditor.svelte`** — aggiungere prop `hideLineType?: boolean`:

```svelte
interface Props {
    style: SignalStyle;
    onstylechange: (key: keyof SignalStyle, value: any) => void;
    simplified?: boolean;
    /** Hide the lineType selector — for signals where lineType is zone-driven (e.g. RSI) */
    hideLineType?: boolean;
}
let {style, onstylechange, simplified = false, hideLineType = false}: Props = $props();
```

Nel popover, avvolgere il blocco lineType:
```svelte
{#if !hideLineType}
    <span class="text-[9px] text-gray-400 dark:text-gray-500 uppercase block mb-1.5">
        {$t('chartSettings.style.lineType')}
    </span>
    <!-- ...buttons esistenti solid/dashed/dotted... -->
{/if}
```

> **✅ Note implementazione (2026-06-01)**: Implementato esattamente come da piano.

**`ChartSignalsSection.svelte`** — passare `hideLineType` per RSI:

```svelte
<SignalStyleEditor
    style={signal.style}
    onstylechange={(key, value) => updateSignalStyle(signal.id, key, value)}
    hideLineType={signal.signalType === 'rsi'}
/>
```

> **✅ Note implementazione (2026-06-01)**: Implementato. Linea 659 aggiornata.

---

## Step 3 — Verifica

1. Aprire un asset con RSI attivo: la linea deve essere tratteggiata nella zona neutral, continua e +1px nelle zone esterne
2. Modificare `overbought`/`oversold`: le soglie si aggiornano in tempo reale
3. Cambiare il colore del segnale dal selettore: il colore cambia uniformemente in tutte le zone
4. Aprire il popover stile RSI: il selettore lineType **non deve essere presente**, colore + lineWidth + markers sì
5. RSI con dati tutti in zona neutral: solo linea tratteggiata uniforme
6. RSI con dati tutti in zona oversold: solo linea continua spessa
7. `svelte-check` 0 errori

> **✅ Note implementazione (2026-06-01)**: `svelte-check` completato. 0 errori nei file modificati. Gli errori pre-esistenti (6 errori in `fxStoreRegistry.test.ts`, `FileGrid.svelte`, `PromoteMergeModal.svelte`) non sono correlati a questa feature.

---

## File Coinvolti

| File | Modifica |
|------|----------|
| `frontend/src/lib/charts/signals/RsiSignal.ts` | Override `renderMulti` con segmentazione per zona |
| `frontend/src/lib/components/charts/SignalStyleEditor.svelte` | Aggiungere prop `hideLineType?: boolean` |
| `frontend/src/lib/components/charts/ChartSignalsSection.svelte` | Passare `hideLineType={signal.signalType === 'rsi'}` |

`ChartSignal.ts`, i18n e altri file sono **invariati**.

---

## Note Architetturali

- **Colore unico per zona**: il colore è sempre `style.color` — l'utente lo imposta una volta per tutte nel selettore, e si propaga uniformemente a tutti i segmenti zona
- **Multi-series da singolo segnale**: pattern già usato da `MacdSignal` (3 series)
- **Label deduplicazione tooltip**: `label: ''` per segmenti non-first evita voci duplicate nel tooltip ECharts
- **`hideLineType` prop pattern**: già presente il precedente `simplified` in `SignalStyleEditor` — stessa convenzione
- **Retrocompatibilità piena**: nessun nuovo param, nessun breaking change

---

## Rischi

- **Basso**: la logica computazionale RSI non cambia, solo la visualizzazione
- **Unico rischio**: junction points. Se l'overlap di 1 punto crea artefatti visivi, si può rimuovere l'overlap e accettare 1px di gap (irrilevante in pratica)
