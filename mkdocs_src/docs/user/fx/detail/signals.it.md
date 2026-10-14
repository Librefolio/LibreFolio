# 📈 Segnali

Il pannello **Segnali** disegna indicatori tecnici, serie di confronto e curve di benchmark sul grafico FX. LibreFolio calcola gli indicatori dai tassi memorizzati della coppia.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Pannello Segnali FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Aggiungere un segnale

1. Fai clic sulla barra **Segnali** sopra il grafico per aprire il pannello.
2. Scegli un segnale da uno dei tre menu a tendina: **Indicatori tecnici**, **Confronto dati** o
   **Benchmark sintetici**.
3. Regola i suoi parametri sulla sua scheda: il grafico si aggiorna.
4. Trascina le schede per riordinarle; 🗑️ ne rimuove una.

I segnali che aggiungi vengono mantenuti con le [impostazioni grafico](../chart-settings.md) di questa coppia.

---

## 🧮 Indicatori tecnici — 9 per FX

Nove indicatori funzionano sui tassi FX. Segui i link qui sotto, o fai clic su 📖 in una scheda, per la matematica alla base di ciascuno.

| Famiglia | Indicatori |
|---|---|
| 📈 **Trend** (3) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) |
| ⚡ **Momentum** (5) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [RSI Stocastico](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) |
| 🌊 **Volatilità** (1) | [Bande di Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) |

??? info "🤔 Perché solo 9? — gli altri indicatori richiedono più di un tasso giornaliero"

    I tassi FX hanno un solo valore al giorno, senza massimo, minimo o volume. Gli altri indicatori richiedono quei
    campi, o misurano il rischio in stile portafoglio, quindi sono disponibili solo sui
    [grafici degli asset](../../assets/detail/signals.md). L'elenco completo è in
    [Indicatori tecnici — Teoria finanziaria](../../../financial-theory/technical-analysis/indicators/index.md).

### 🔍 Trovare un indicatore

Il menu a tendina **Indicatori tecnici** è un albero raggruppato per famiglia (trend, momentum, volatilità), con
una casella di ricerca in alto: digita per filtrare tutte le famiglie contemporaneamente. Funzionano anche i tasti freccia e `Enter`.

*Screenshot in arrivo: l'albero raggruppato degli indicatori aperto sul pannello Segnali FX.*

---

## 💱 Confronto dati

- 💱 **Coppia FX** — un'altra delle tue coppie, ad es. GBP/USD accanto a EUR/USD. Nell'elenco, 👑 contrassegna la
  coppia di questa pagina e 📌 una coppia già usata da un altro segnale.
- ↔️ **Confronto asset** — il prezzo di un asset accanto al tasso.

Una scheda di confronto ha pulsanti per sincronizzare la coppia o l'asset confrontato e per aprire la sua pagina. Nella vista in %
entrambe le curve partono da 0 %, quindi i loro movimenti sono direttamente confrontabili.

## 📐 Benchmark sintetici

Curve di riferimento costruite solo da parametri, senza dati di mercato:
[Crescita Lineare](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md),
[Crescita Composta](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) e
[Onda Sinusoidale](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🎛️ Leggere una scheda segnale

- 📖 apre la pagina teorica dell'indicatore; passa il mouse su un parametro per visualizzare l'aiuto.
- Un badge conta i punti dati caricati per il segnale.
- Uno spinner gira mentre il segnale viene calcolato. Poi un'icona può segnalare un problema — passa il mouse sopra per
  i dettagli:
    - grigio ℹ️ — una piccola avvertenza;
    - ambra ⚠️ — calcolato con avvertenze, come gap, un breve warm-up o dati che iniziano dopo il
      periodo;
    - rosso ⚠️ — non calcolato, ad esempio perché la cronologia è troppo breve.

Se una scheda segnala dati mancanti, sincronizzare la coppia di solito colma la lacuna.

---

## 📚 Approfondimento: teoria finanziaria

La formula di ogni indicatore, la sua prospettiva di elaborazione dei segnali (EMA come filtro IIR, SMA come filtro FIR)
e come leggere i suoi incroci:

:material-book-open-variant: **[Indicatori tecnici — Teoria finanziaria](../../../financial-theory/technical-analysis/indicators/index.md)**
