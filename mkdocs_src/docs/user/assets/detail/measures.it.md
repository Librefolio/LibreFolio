# 📐 Misure

Lo strumento Misure risponde alla domanda: *quanto è cambiato tra questi due giorni?* Scegli due punti sul grafico e leggi la variazione dell'asset e delle linee disegnate con esso tra i due punti.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-measures" alt="Pannello delle misure dell'asset" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Effettua una misura

1. Clicca **📏 Aggiungi misura** in alto a destra del grafico: il pannello **Misure** si apre sotto di esso.
2. Clicca il punto **iniziale** sul grafico, poi il punto **finale**.
3. La nuova misura si apre con la sua tabella, e il grafico la disegna con il suo colore.

Il pulsante **+ Aggiungi misura** nell'intestazione del pannello, invece, misura l'intero grafico, dal primo all'ultimo punto: comodo sul telefono. L'intestazione di ogni misura contiene il suo colore e 🗑️ per rimuoverla; espandi la misura per modificarne le date.

Le misure non vengono salvate: ricaricare la pagina svuota il pannello. **Prezzi** e **Rendimento rolling** mantengono misure separate.

---

## 💵 In modalità Prezzi

La tabella ha una riga per l'asset (una seconda riga nella sua valuta quando il grafico è convertito) e una per ogni linea tracciata sull'asse dei prezzi, come un asset di confronto o una media mobile. Accanto ai valori **Inizio** e **Fine**:

- **Δ Ass.** — la differenza $V_{end} - V_{start}$, nell'unità della linea.
- **Δ %** — la variazione $\frac{V_{end} - V_{start}}{V_{start}}$ → [Rendimenti e tassi di crescita](../../../financial-theory/fundamentals/returns.md)
- **Δ%/anno** — la stessa variazione come tasso annuo sui $d$ giorni di calendario tra i punti, $(1 + \Delta\%)^{365/d} - 1$ → [Rendimenti e tassi di crescita](../../../financial-theory/fundamentals/returns.md)

La riga di riepilogo della misura aggiunge il numero di giorni.

---

## 📈 In modalità Rendimento rolling

I valori sono già rendimenti, quindi la tabella li confronta:

- **Inizio**, **Fine** — il rendimento rolling su ciascuna delle due date.
- **Δ pp** — Fine meno Inizio, in punti percentuali → [Rendimento rolling sui giorni di calendario](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar)
- **Giorni** — i giorni di calendario tra i due punti.

---

## 🔗 Correlati

- 📈 **[Grafico interattivo](chart.md)** — Controlli del grafico e filtro dell'intervallo di date
- 📊 **[Segnali](signals.md)** — Sovrapposizioni di indicatori tecnici
