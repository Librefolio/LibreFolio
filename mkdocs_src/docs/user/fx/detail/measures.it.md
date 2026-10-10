# 📐 Misure

Il pannello Misure ti dice come si è mosso il tasso di cambio tra due punti del grafico: la variazione, la
variazione in % e il tasso annuo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="Pannello delle misure FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ Effettua una misura

### 📏 Passaggio 1: Attiva la modalità di misura

Fai clic su 📏 (**Aggiungi misura**) in alto a destra del grafico. Il pannello **Misure** sotto il grafico
si apre e mostra **Attivo — fai clic sul grafico**.

### 📍 Passaggio 2: Fai clic sul punto iniziale

Un suggerimento mostra la data e il tasso di cambio scelti; una linea tratteggiata segue il puntatore.

### 🏁 Passaggio 3: Fai clic sul punto finale

La misura viene aggiunta e la modalità di misura si disattiva. Le due date vengono ordinate automaticamente.

??? tip "➕ L'intero periodo in un clic — comodo su un telefono"

    Il pulsante **+** sulla barra **Misure** misura il periodo selezionato dal primo all'ultimo valore del cambio,
    senza fare clic sul grafico.

---

## 📊 Leggi una misura

Ogni misura è una scheda che mostra le sue date, la variazione in % e il numero di giorni di calendario;
puoi anche impostare il colore e lo stile della sua linea. Espandila per cambiare le date e vedere
**Inizio**, **Fine**, **Δ Assoluto**, **Δ %** e **Δ%/anno** per la coppia FX e per ogni serie sovrapposta sullo stesso asse.

**Δ%/anno** è il tasso annuo (CAGR), con $d$ i giorni di calendario tra le due date:

$$
\Delta\%_{yr} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Vedi [Rendimenti e tassi di crescita — Teoria finanziaria](../../../financial-theory/fundamentals/returns.md)
per i rendimenti logaritmici e la capitalizzazione composta.

---

## 🔁 Più misure

Ogni nuova misura viene aggiunta accanto alle altre, con il proprio colore; 🗑️ ne rimuove una. Rimangono
finché non lasci la pagina.

---

## 💡 Suggerimenti

- 🔍 **Ingrandisci** prima di fare clic, per individuare i punti esatti.
- 📰 Confronta il movimento **prima e dopo un evento**, come un annuncio di una banca centrale.
- ⚠️ Leggi **Δ%/anno** con attenzione sui periodi brevi: un movimento dell'1% in 7 giorni equivale a circa il 68% su base annua.
  È più significativo su periodi di almeno 30 giorni.
