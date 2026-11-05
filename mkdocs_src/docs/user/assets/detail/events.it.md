# 📅 Eventi dell'asset

Gli eventi dell'asset sono cose che accadono all'asset stesso, per tutti coloro che lo detengono: un dividendo, uno split, un pagamento di interessi. Non sono le tue [transazioni](../../../financial-theory/instruments/transaction-types/index.md), che registrano ciò che accade nel tuo portafoglio.

---

## 📊 Tipi di evento

Ogni tipo, con l'effetto sul prezzo e la relativa pagina teorica:

- 💰 **Dividendo** (`DIVIDEND`) — denaro pagato da un'azione o da un ETF; il prezzo scende di circa quell'importo alla data ex → [📖](../../../financial-theory/instruments/asset-events/dividend.md)
- 📈 **Interesse** (`INTEREST`) — interessi pagati da un'obbligazione, un prestito o un deposito; il valore scende dell'importo pagato → [📖](../../../financial-theory/instruments/asset-events/interest.md)
- ✂️ **Split** (`SPLIT`) — le unità vengono frazionate; cambia il loro numero, non il valore totale → [📖](../../../financial-theory/instruments/asset-events/split.md)
- 📊 **Rettifica prezzo** (`PRICE_ADJUSTMENT`) — una variazione di valore senza movimenti di cassa, in aumento o in diminuzione: una svalutazione, un haircut, un re-rating → [📖](../../../financial-theory/instruments/asset-events/price-adjustment.md)
- 🏁 **Regolamento a scadenza** (`MATURITY_SETTLEMENT`) — l'asset raggiunge la scadenza e rimborsa il suo capitale; il suo valore smette di cambiare → [📖](../../../financial-theory/instruments/asset-events/maturity-settlement.md)

I codici tra parentesi sono quelli previsti da un [import CSV](data-editor.md#import-from-csv).

---

## 📈 Eventi sul grafico

In modalità **Prezzi**, gli eventi compaiono come marcatori sul [grafico dei prezzi](chart.md), ciascun tipo con la propria forma: un triangolo per un dividendo, un rombo per l'interesse, un quadrato per una rettifica prezzo, un quadrato arrotondato per la scadenza, una freccia per uno split. Passa il mouse su un marcatore per vederne data, tipo, importo e note.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-events" alt="Grafico dell'asset con il puntatore su un marcatore di evento">
</div>

- **In un'altra valuta**, l'importo viene convertito, con l'importo originale sotto; un evento che non può essere convertito viene nascosto.
- Gli **asset confrontati** mostrano anch'essi i propri eventi, nel colore della loro linea.

---

## ⚙️ Da dove vengono gli eventi

- **Da un provider**, a ogni sincronizzazione: dividendi e split da [Yahoo Finance](../providers/yahoo-finance.md), dividendi da [justETF](../providers/justetf.md), e dall'[investimento programmato](../providers/scheduled-investment.md) i pagamenti di interessi e il regolamento finale a scadenza di **Genera cedola**, oltre agli eventi elencati nel suo piano interessi (**Aggiungi evento** nel modulo dell'asset).
- **Da te**: nella scheda **Eventi** dell'[editor dati](data-editor.md), uno alla volta o da un file CSV, oppure con **+ Nuovo evento** nel campo **Evento collegato** di una transazione ([sotto](#new-event)).

Una sincronizzazione aggiorna gli eventi del provider e non tocca mai i tuoi. L'evento di un provider è di sola lettura nell'editor, e la sua eliminazione dura solo finché il provider non lo invia di nuovo: per modificare gli eventi di un investimento programmato, modifica il suo piano interessi. Rimuovere il provider (**Nessun provider** nel [modulo dell'asset](../create-edit.md#editing-an-asset)) elimina i suoi eventi, e l'operazione viene rifiutata finché una transazione è collegata a uno di essi.

### ✨ Nuovo evento da una transazione {: #new-event }

**+ Nuovo evento**, nel campo **Evento collegato** di un dividendo, di un interesse o di una rettifica, crea un evento per l'asset della transazione e lo collega alla transazione. Non sovrascrive mai un evento: se l'asset ha già un evento di quel tipo in quella data, inserito a mano o da un provider di dati, non viene salvato nulla e la finestra mostra ciò che è presente sotto *Questo evento esiste già*. Per ogni evento: il suo tipo, la data, l'importo e le note, da dove proviene e quante transazioni sono collegate a esso. Poi scegli:

- **Usa questo** — collega quell'evento alla transazione e non cambia nient'altro.
- **Modifica questo** — solo per un evento inserito a mano: la finestra diventa *Modifica evento per …*, compilata con i valori di quell'evento. Modifica ciò che ti serve e fai clic su **Salva**: lo stesso evento viene aggiornato, anche per le transazioni già collegate a esso, e questa transazione viene collegata a esso.
- **Annulla** — torna al modulo con quanto hai digitato (il pulsante **Annulla** in basso chiude la finestra).

Un evento proveniente da un provider di dati offre solo **Usa questo**, con una nota: il provider aggiorna i propri eventi. Da qui non è possibile aggiungere un secondo evento dello stesso tipo nella stessa data. Nell'[editor dati](data-editor.md), invece, una nuova riga o una riga CSV con la data e il tipo di uno dei tuoi eventi aggiorna quell'evento.

Dopo **Modifica questo**, il campo **Evento collegato** mostra l'evento con i suoi nuovi valori.

---

## 🧮 Eventi in un investimento programmato

Per un [investimento programmato](../providers/scheduled-investment.md#how-value-is-calculated), gli eventi fanno parte del prezzo stesso:

$$
P(d) = V_0 + I(d) - \sum \text{Interessi} + \sum \text{Rettifiche prezzo}
$$

dove $V_0$ è il valore iniziale e $I(d)$ è l'interesse maturato fino a quel momento. Per un asset con prezzo di mercato, gli eventi spiegano solo i movimenti del prezzo, come il calo alla data ex-dividendo; non modificano i prezzi inviati dal provider.

---

## 🔗 Correlati

- 📈 **[Grafico interattivo](chart.md)** — Marcatori di evento sul grafico
- ✏️ **[Editor dati](data-editor.md)** — Gestione manuale degli eventi con import CSV
- 🧮 **[Investimento programmato](../providers/scheduled-investment.md)** — Provider che genera eventi dai piani interessi
- 📚 **[Eventi dell'asset (Teoria finanziaria)](../../../financial-theory/instruments/asset-events/index.md)** — Analisi dettagliata di ciascun tipo di evento
- 💸 **[Tipi di transazione (Teoria finanziaria)](../../../financial-theory/instruments/transaction-types/index.md)** — Transazioni vs eventi
- 🛠️ **[Eventi dell'asset (sviluppatore)](../../../developer/backend/assets/events.md)** — Per gli sviluppatori: come vengono memorizzati e aggiornati gli eventi
