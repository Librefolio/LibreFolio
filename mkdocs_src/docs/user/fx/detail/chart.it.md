# 📉 Grafico interattivo

Il cuore della pagina di dettaglio della coppia: lo storico del tasso della coppia nel periodo selezionato.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Grafico di dettaglio FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Vista Abs o %

Cambia con **Abs** / **%** nell'angolo in alto a sinistra del grafico; la pagina si apre in vista %.

- 📊 **%** — la variazione dal primo giorno del periodo. Anche le sovrapposizioni partono da 0 %, così i loro
  movimenti si confrontano a colpo d'occhio.
- 📈 **Abs** — il tasso stesso, ad es. 1 EUR = 1,0845 USD.

---

## 🔍 Zoom, pan e periodo

| Azione | Desktop | Mobile |
|--------|---------|--------|
| **Zoom** | Rotella del mouse | Pinch |
| **Pan** | Clicca e trascina | Trascina con due dita (un dito scorre la pagina) |

- **Periodo**: le preimpostazioni da **1W** a **2Y**, **YTD** e **Tutto**, oppure **Personalizzato** (un numero di giorni,
  settimane, mesi o anni indietro da oggi); clicca sulle date per sceglierle su un calendario. Altre preimpostazioni
  compaiono quando la barra degli strumenti ha spazio. Le pagine della stessa scheda del browser condividono il periodo.
- Su un periodo lungo il grafico raggruppa i tassi per settimana o mese e mostra un badge **Settimanale** o
  **Mensile**: ingrandisci per i tassi giornalieri.
- Su uno schermo stretto l'asse mostra meno date, più corte; la prima e l'ultima restano sempre.

??? info "📅 Storico più corto del periodo — quando il grafico inizia più tardi"

    Un banner mostra la data da cui i dati sono disponibili. **Sync** può recuperare tassi più vecchi, se il
    provider li pubblica; altrimenti inseriscili nell'[editor dati](data-editor.md).

---

## 💬 Tooltip

Passa il mouse sul grafico, o toccalo su mobile, per vedere:

- 📅 la **data** (o la settimana o il mese, quando il grafico raggruppa i tassi);
- 💱 il **tasso** e il valore di ogni sovrapposizione;
- 📊 la **variazione dall'inizio del periodo**: Δ e % in vista Abs, % in vista %;
- ⚠️ **Obsoleto: N giorno/i di anzianità** nei giorni senza un nuovo tasso, come weekend e festivi.

---

## 🧰 Pulsanti del grafico

- 📏 **Misura** — vedi [Misure](measures.md).
- ✏️ **Modifica tassi** — vedi [editor dati](data-editor.md).
- ⚙️ **Estetica** — colori, riempimento, griglia e intervalli degli assi, come in [Impostazioni grafico](../chart-settings.md).
- 📊 Il pannello **Segnali** sopra il grafico — vedi [Segnali](signals.md).

---

## 🔗 Correlati

- ⚙️ **[Impostazioni grafico](../chart-settings.md)** — Aspetto del grafico e segnali di sovrapposizione
- 📈 **[Segnali](signals.md)** — Indicatori tecnici sul grafico
