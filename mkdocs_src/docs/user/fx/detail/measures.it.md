# 📐 Misure

Il pannello Misure fornisce uno **strumento di misurazione click-to-click** per analizzare i movimenti dei tassi tra due punti qualsiasi sul grafico.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="Pannello Misure FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ Come Usarlo

1. Clicca sull'**interruttore** Misure (📏) nella barra degli strumenti del grafico
2. Il pannello misure si apre sotto il grafico
3. **Clicca** su un punto di partenza sul grafico — questo imposta la data e il tasso di partenza
4. **Clicca** su un punto di arrivo — questo imposta la data e il tasso di arrivo
5. Il pannello mostra immediatamente le metriche calcolate tra i due punti

---

## 📊 Metriche Calcolate

Per ogni misurazione, il pannello visualizza:

| Metrica | Descrizione | Esempio |
|--------|-------------|---------|
| **Intervallo Date** | Date Da → A | 15 gen 2024 → 20 mar 2024 |
| **Giorni** | Giorni di calendario tra i due punti | 65 giorni |
| **Delta (Δ)** | Variazione assoluta del tasso | +0,0342 |
| **Percentuale (%)** | Variazione relativa in percentuale | +3,12% |
| **Rendimento Annualizzato** | Rendimento annuale proiettato in base al periodo misurato | +17,8% p.a. |

!!! info "📚 Rendimento Annualizzato"

    Il rendimento annualizzato utilizza la formula del **Compound Annual Growth Rate (CAGR)**. Per una spiegazione completa che includa i rendimenti logaritmici, la capitalizzazione e quando utilizzare ogni metodo, consulta:

    :material-book-open-variant: **[Rendimenti e Tassi di Crescita — Teoria Finanziaria](../../../financial-theory/fundamentals/returns.md)**

---

## 🔁 Misurazioni Multiple

È possibile effettuare più misurazioni in sequenza — ogni nuova coppia di click sostituisce la misurazione precedente. Ciò consente di confrontare rapidamente i movimenti su diverse finestre temporali.

---

## 💡 Suggerimenti

- 🔍 **Effettua lo zoom** prima di misurare per una migliore precisione sui punti di click
- 📰 Usa le misurazioni per confrontare i movimenti dei tassi **pre/post evento** (ad esempio, prima e dopo l'annuncio di una banca centrale)
- ⚠️ Il rendimento annualizzato è più significativo per periodi di **30+ giorni** — periodi molto brevi possono produrre cifre annualizzate fuorvianti
