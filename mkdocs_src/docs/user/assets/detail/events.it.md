# 📅 Eventi dell'asset

Gli eventi dell'asset sono cose che accadono all'asset stesso, per tutti coloro che lo detengono: un dividendo, uno split, un pagamento di interessi. Non sono le tue [transazioni](../../../financial-theory/instruments/transaction-types/index.md), che registrano ciò che accade nel tuo portafoglio.

---

## 📊 Tipi di evento

Ogni tipo, con il suo effetto sul prezzo e la relativa pagina teorica:

- 💰 **Dividendo** (`DIVIDEND`) — denaro pagato da un'azione o da un ETF; il prezzo scende di circa quell'importo alla data ex-dividendo → [📖](../../../financial-theory/instruments/asset-events/dividend.md)
- 📈 **Interesse** (`INTEREST`) — interesse pagato da un'obbligazione, un prestito o un deposito; il valore scende dell'importo pagato → [📖](../../../financial-theory/instruments/asset-events/interest.md)
- ✂️ **Split** (`SPLIT`) — le quote vengono frazionate; cambia il loro numero, non il valore totale → [📖](../../../financial-theory/instruments/asset-events/split.md)
- 📊 **Rettifica prezzo** (`PRICE_ADJUSTMENT`) — una variazione di valore senza movimenti di cassa, in aumento o in diminuzione: una svalutazione, un haircut, un re-rating → [📖](../../../financial-theory/instruments/asset-events/price-adjustment.md)
- 🏁 **Regolamento a scadenza** (`MATURITY_SETTLEMENT`) — l'asset raggiunge la scadenza e rimborsa il suo capitale; il suo valore smette di cambiare → [📖](../../../financial-theory/instruments/asset-events/maturity-settlement.md)

I codici tra parentesi sono quelli che si aspetta un [import CSV](data-editor.md#import-from-csv).

---

## 📈 Gli eventi sul grafico

In modalità **Prices**, gli eventi compaiono come marcatori sul [grafico dei prezzi](chart.md), ognuno con la propria forma: un triangolo per un dividendo, un rombo per l'interesse, un quadrato per una rettifica prezzo, un quadrato arrotondato per la scadenza, una freccia per uno split. Passa il mouse su un marcatore per vederne data, tipo, importo e note.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-events" alt="Grafico dell'asset con un marcatore di evento evidenziato al passaggio del mouse">
</div>

- **In un'altra valuta**, l'importo viene convertito, con l'importo originale indicato sotto; un evento che non può essere convertito viene nascosto.
- **Gli asset confrontati** mostrano anch'essi i loro eventi, nel colore della loro linea.

---

## ⚙️ Da dove provengono gli eventi

- **Da un provider**, a ogni sincronizzazione: dividendi e split da [Yahoo Finance](../providers/yahoo-finance.md), dividendi da [justETF](../providers/justetf.md), e da [Investimento programmato](../providers/scheduled-investment.md) i pagamenti degli interessi e il regolamento finale a scadenza di **Generate Coupon**, più gli eventi elencati nel suo piano (**Aggiungi evento** nel modulo dell'asset).
- **Da te**: nella scheda **Eventi** dell'[Editor dati](data-editor.md), uno alla volta o da un file CSV, oppure con **Nuovo evento** nel campo **Evento collegato** di una transazione.

Una sincronizzazione aggiorna gli eventi del provider e non tocca mai i tuoi. Un evento di un provider è di sola lettura nell'editor, e la sua cancellazione dura solo finché il provider non lo invia di nuovo: per modificare gli eventi di un investimento programmato, modifica il suo piano.

---

## 🧮 Gli eventi in un investimento programmato

Per un [Investimento programmato](../providers/scheduled-investment.md#how-value-is-calculated), gli eventi fanno parte del prezzo stesso:

$$
P(d) = V_0 + I(d) - \sum \text{Interessi} + \sum \text{Rettifiche prezzo}
$$

dove $V_0$ è il valore iniziale e $I(d)$ l'interesse maturato fino a quel momento. Per un asset prezzato dal mercato, gli eventi spiegano solo i movimenti del prezzo, come il calo alla data ex-dividendo; non modificano i prezzi inviati dal provider.

---

## 🔗 Correlati

- 📈 **[Grafico interattivo](chart.md)** — Marcatori di eventi sul grafico
- ✏️ **[Editor dati](data-editor.md)** — Gestione manuale degli eventi con import CSV
- 🧮 **[Investimento programmato](../providers/scheduled-investment.md)** — Provider che genera eventi dai piani interessi
- 📚 **[Eventi dell'asset (Teoria Finanziaria)](../../../financial-theory/instruments/asset-events/index.md)** — Analisi dettagliata di ogni tipo di evento
- 💸 **[Tipi di transazione (Teoria Finanziaria)](../../../financial-theory/instruments/transaction-types/index.md)** — Transazioni ed eventi a confronto
- 🛠️ **[Eventi dell'asset (sviluppatore)](../../../developer/backend/assets/events.md)** — Per gli sviluppatori: come vengono memorizzati e aggiornati gli eventi
