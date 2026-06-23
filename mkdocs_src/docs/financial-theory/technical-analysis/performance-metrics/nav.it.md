# 💼 Net Asset Value (NAV) / Net Worth (Valore Netto)

*[⬅️ Torna alla Panoramica delle Metriche di Performance](index.md)*

## 💡 Che cos'è il NAV / Net Worth?

Nella dashboard di LibreFolio, il **Net Asset Value (NAV)** (chiamato anche **Net Worth** o **Valore Netto**) rappresenta il valore di mercato totale del tuo portafoglio alla fine della finestra temporale selezionata (`date_to`).

Risponde alla domanda fondamentale: _"Quanto vale il portafoglio nello scope selezionato in questo preciso momento?"_

A differenza delle metriche di performance basate su un periodo (come il ROI o il P&L), il NAV è uno **snapshot (istantanea) a una data precisa**. Sebbene il suo andamento storico possa essere tracciato nel tempo, il valore finale del NAV mostrato sulla card della dashboard dipende esclusivamente dalla data finale (`date_to`) ed è completamente indipendente dalla data iniziale (`date_from`).

---

## 🧮 Formula

LibreFolio calcola il Net Asset Value utilizzando la seguente formula:

$$
\text{NAV} = \text{Valore di Mercato} + \text{Liquidità} + \text{Valore in Transito}
$$

Dove:

- **$\text{Valore di Mercato}$**: La valutazione di mercato attuale di tutti gli asset detenuti (ETF, azioni, obbligazioni, criptovalute, ecc.), calcolata utilizzando l'ultimo prezzo disponibile e convertito nella valuta di riferimento del portafoglio.
- **$\text{Liquidità}$**: Il saldo di liquidità reale depositato sui conti dei broker inclusi nello scope selezionato.
- **$\text{Valore in Transito}$**: Il valore di mercato della liquidità o degli asset attualmente in fase di trasferimento interno tra i conti compresi nello scope (es. trasferimenti avviati ma non ancora completati). Come per il [Valore Contabile (Book Value)](book-value.md), questo concetto gestisce le transazioni (es. bonifici o trasferimenti titoli) che lasciano un conto il giorno 1 e arrivano a destinazione il giorno 5 per via dei tempi tecnici di esecuzione del sistema.

---

## 📝 Esempio Pratico

Consideriamo un portafoglio con i seguenti saldi alla fine del periodo selezionato:

- **Valore di Mercato degli Asset**: €32.759
- **Liquidità**: €631
- **Asset in Transito**: €0

Il Net Asset Value è calcolato come:

$$
\text{NAV} = 32.759 + 631 + 0 = \text{€}33.390
$$


---

## ⚖️ Differenze Chiave

Per evitare confusioni, è importante distinguere il NAV dalle altre metriche della dashboard:

- **Rispetto al Book Value (Valore Contabile)**: Il NAV rappresenta il **valore di mercato attuale** dei tuoi asset. Il [Book Value](book-value.md) rappresenta il **costo di acquisto storico** (quanto hai effettivamente pagato per acquistarli). La differenza tra i due costituisce la plusvalenza o minusvalenza latente (unrealized gain/loss).
- **Rispetto al Period P&L (P&L del Periodo)**: Il NAV indica il valore assoluto del tuo patrimonio. Il [Period P&L](period-pnl.md) misura la *variazione* di questo patrimonio in un determinato periodo, depurata da depositi e prelievi esterni.

---

## ⚠️ Qualità dei Dati e Valutazione

Poiché il NAV si basa sui prezzi di mercato e sui tassi di cambio (FX) per convertire tutti gli asset nella valuta di riferimento:

- Se mancano i dati sui prezzi o sui tassi di cambio per un asset alla data finale (`date_to`), la valutazione potrebbe essere incompleta.
- In questi casi, LibreFolio mostra il **Data Quality Banner** (Banner di Qualità dei Dati) nella parte superiore della dashboard per avvisare che alcune valutazioni si basano su dati obsoleti o mancanti.
