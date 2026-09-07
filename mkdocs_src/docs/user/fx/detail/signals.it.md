# 📈 Segnali

Il pannello Segnali consente di sovrapporre **indicatori tecnici**, **serie di confronto** e **curve di benchmark** sul grafico FX. Gli indicatori vengono calcolati lato server dalla **piattaforma di plugin per segnali** del backend di LibreFolio a partire dalla cronologia dei tassi memorizzata per la coppia — il browser si limita a renderizzare i risultati.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="FX Signals Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧮 Segnali disponibili

I segnali sono organizzati in **tre categorie**, ciascuna con il proprio menu a tendina nella parte superiore del pannello: **Indicatori Tecnici**, **Confronto Dati** e **Benchmark Sintetici**.

### 📉 Indicatori tecnici — 9 plugin compatibili con FX

Dei 22 plugin per indicatori del backend, **9 operano sui tassi di chiusura FX**. La matematica di ciascun indicatore è trattata nella sezione Teoria Finanziaria — segui i link qui sotto, oppure clicca l'icona 📖 su qualsiasi scheda segnale per passare direttamente alla relativa pagina di teoria.

| Famiglia | Indicatori |
|---|---|
| 📈 **Trend** (3) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) |
| ⚡ **Momentum** (5) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [RSI Stocastico](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) |
| 🌊 **Volatilità** (1) | [Bande di Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) |

!!! info "Perché solo 9?"

    I tassi FX hanno un solo valore al giorno — non esiste massimo, minimo o volume. I
    restanti 13 plugin richiedono questi campi aggiuntivi (oppure calcolano metriche di
    rischio in stile portafoglio) e sono invece disponibili sui [grafici degli asset](../../assets/detail/signals.md).
    L'inventario completo è disponibile in
    [Indicatori Tecnici — Teoria Finanziaria](../../../financial-theory/technical-analysis/indicators/index.md).

### 💱 Confronto dati

Sovrapposizioni calcolate dal browser che normalizzano un'altra serie sullo stesso grafico:

- 💱 **Coppia FX** — sovrapponi un'altra coppia configurata (ad es. confronta EUR/USD con GBP/USD); le coppie già selezionate da un altro segnale sono contrassegnate con 📌, mentre la coppia della pagina corrente porta una 👑
- ↔️ **Confronto asset** — sovrapponi la performance di un asset accanto al tasso di cambio

### 📐 Benchmark sintetici

**Curve di riferimento matematiche** calcolate dal browser, generate esclusivamente dai parametri — nessun dato di mercato necessario: [Crescita Lineare](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Crescita Composta](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) e [Onda Sinusoidale](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🔍 Trovare un indicatore

Il menu a tendina degli indicatori è un **albero comprimibile raggruppato per famiglia** (trend, momentum, volatilità), con una casella di ricerca in alto — digita per filtrare su tutte le famiglie contemporaneamente; le frecce, `→`/`←` e `Enter` consentono di navigare nell'albero.

*Screenshot in arrivo: l'albero degli indicatori raggruppati aperto sul pannello Segnali FX.*

---

## 🎛️ Schede segnale

Ogni segnale aggiunto diventa una scheda che mostra:

- 📖 Un'**icona della documentazione** che rimanda alla pagina di Teoria Finanziaria dell'indicatore
- 🎚️ **Parametri inline** (periodo, periodo del segnale, …) — alcuni suggerimenti contengono formule LaTeX renderizzate con KaTeX
- 🏷️ Un **badge dati** con il numero di punti del tasso (📈) caricati
- 🗑️ Pulsante di rimozione; trascina le schede per riordinare le sovrapposizioni

Un piccolo **spinner** appare su ogni scheda mentre la richiesta al backend è in corso. Dopo il caricamento, un'icona colorata riporta le **diagnostiche** per singolo segnale — passa il mouse sopra per i dettagli: ℹ️ avviso (grigio) e ⚠️ avvertimento (ambra) quando il segnale è stato calcolato con riserve (lacune nei dati, riscaldamento incompleto, dati che iniziano dopo l'intervallo del grafico), 🔴 errore (rosso) quando non è stato possibile calcolarlo affatto (cronologia insufficiente, campi mancanti). Se una scheda segnala dati mancanti, la sincronizzazione della coppia di solito colma la lacuna.

---

## 🛠️ Come usarlo

1. Fai clic sull'interruttore **Segnali** (📈) nella barra degli strumenti del grafico
2. Il pannello Segnali si apre sotto il grafico
3. Aggiungi segnali dai tre menu a tendina delle categorie (Indicatori Tecnici, Confronto Dati, Benchmark Sintetici)
4. Regola i parametri di ciascun segnale direttamente sulla sua scheda
5. I segnali vengono renderizzati come sovrapposizioni direttamente sul grafico

---

## 🧠 Esportazione AI

Il pulsante **Esportazione AI** (:material-brain:) nella barra degli strumenti della pagina offre due attività FX:

- **Analisi Coppia FX**
- **Impatto dell'Esposizione FX**

Lo snapshot del backend utilizza la coppia di valute canonica della pagina, l'intervallo selezionato, la valuta obiettivo, la cronologia dei tassi e i risultati condivisi dei segnali tecnici. Per l'Impatto dell'Esposizione FX, l'esposizione è limitata alle valute di cassa e alle valute di negoziazione o di valutazione delle posizioni direttamente collegabili alla coppia; **non** esamina fondi o emittenti per dedurre un'esposizione valutaria nascosta. Vedi [Esportazione AI FX](../../ai-export/fx.md) o la [panoramica sull'Esportazione AI](../../ai-export/index.md).

---

## 📚 Approfondimento: teoria finanziaria

Per un trattamento matematico completo di ciascun indicatore — incluse formule, equivalenti nell'elaborazione dei segnali e interpretazione pratica:

:material-book-open-variant: **[Indicatori Tecnici — Teoria Finanziaria](../../../financial-theory/technical-analysis/indicators/index.md)**

Questa pagina di riferimento copre:

- 🔢 Le **formule matematiche** alla base di ciascun indicatore
- 🎛️ Gli equivalenti nell'**elaborazione dei segnali** (EMA = filtro IIR, SMA = filtro FIR, ecc.)
- ⚡ L'intuizione **"veloce vs lento"** in termini di frequenze di taglio del filtro
- 📈 **Esempi pratici** di rilevamento degli incroci e identificazione dei trend
