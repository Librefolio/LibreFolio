# 📐 Misure

Il pannello Misure fornisce uno **strumento di misurazione da clic a clic** per analizzare i movimenti dei tassi tra qualsiasi coppia di punti sul grafico.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="Pannello Misure FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ Come utilizzare

1. Fai clic sul pulsante **Misure** (📏) nella barra degli strumenti del grafico
2. Il pannello Misure si apre sotto il grafico
3. **Fai clic** su un punto iniziale sul grafico — questo imposta la data e il tasso 'da'
4. **Fai clic** su un punto finale — questo imposta la data e il tasso 'a'
5. Il pannello mostra immediatamente le metriche calcolate tra i due punti

---

## 📊 Metriche calcolate

Per ogni misurazione, il pannello mostra:

| Metrica | Descrizione | Esempio |
|---------|-------------|---------|
| **Intervallo di date** | Da → A date | 15 gen 2024 → 20 mar 2024 |
| **Giorni** | Giorni di calendario tra i due punti | 65 giorni |
| **Delta (Δ)** | Variazione assoluta del tasso | +0,0342 |
| **Percentuale (%)** | Variazione relativa in percentuale | +3,12% |
| **Rendimento annualizzato** | Rendimento annuo proiettato basato sul periodo misurato | +17,8% p.a. |

!!! info "📚 Rendimento annualizzato"

    Il rendimento annualizzato utilizza la formula del **Compound Annual Growth Rate (CAGR, tasso di crescita annuo composto)**. Per una spiegazione completa che includa i rendimenti logaritmici, il compounding e quando utilizzare ciascun metodo, vedere:

    :material-book-open-variant: **[Rendimenti e tassi di crescita — Teoria finanziaria](../../../financial-theory/returns.md)**

---

## 🔁 Misure multiple

Puoi eseguire più misurazioni in sequenza — ogni nuova coppia di clic sostituisce la misurazione precedente. Questo ti permette di confrontare rapidamente i movimenti in diverse finestre temporali.

---

## 💡 Suggerimenti

- 🔍 **Effettua lo zoom** prima di misurare per una maggiore precisione sui punti di clic
- 📰 Utilizza le misurazioni per confrontare i movimenti dei tassi **prima e dopo l'evento** (ad esempio, prima e dopo un annuncio della banca centrale)
- ⚠️ Il rendimento annualizzato è più significativo per periodi di **30+ giorni** — periodi molto brevi possono produrre cifre annualizzate fuorvianti
