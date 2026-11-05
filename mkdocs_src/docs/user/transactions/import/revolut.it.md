# <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" alt=""> Revolut

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esserci casi limite.

## 📥 Come esportare

Per esportare lo storico delle transazioni su azioni/criptovalute da Revolut:

1. Apri l'**app mobile Revolut** o accedi tramite il client web.
2. Vai alla scheda **Invest** (o Stocks/Crypto).
3. Tocca **... (More)** accanto al saldo del portafoglio, quindi seleziona **Statements**.
4. Seleziona l'account desiderato (ad es. l'account Stocks) e tocca **Transaction Statement**.
5. Imposta l'intervallo di tempo, scegli **CSV** come formato ed esporta. Trasferisci il file sul tuo computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Segnaposto screenshot: App Revolut - selezione degli estratti conto Invest ed esportazione CSV] -->
</div>

## ⚠️ Insidie comuni

!!! warning "Conto Trading vs conto principale"

    Assicurati di esportare l'estratto conto dal sottoconto **Invest/Trading**. L'estratto conto della carta di debito del conto principale di Revolut usa un formato di file completamente diverso e non può essere interpretato da questo plugin.

## 📝 Note

- Supporta operazioni su azioni, acquisti di criptovalute, dividendi pagati, commissioni di custodia e giroconti.
- Gestisce automaticamente importi in più valute nello stesso file.
- I trasferimenti tra i tuoi account vengono omessi silenziosamente, poiché non cambiano nulla.

## 🔀 Split azionari {: #stock-splits }

In un file **Invest**, una riga **STOCK SPLIT** con una **Quantity** positiva viene importata come **rettifica** in entrata delle azioni aggiunte (la **Quantity** della riga è il numero di nuove azioni, non il totale dopo lo split), a costo zero.

L'importatore non riesce a distinguere uno split da un regalo o da uno spin-off, quindi segnala la riga. Al termine della procedura guidata di importazione (il passo **Review**) viene indicato il numero di righe che sembrano split, e l'editor bulk mostra un banner, *N righe potrebbero essere split azionari*. Per ogni riga elenca il ticker, le azioni aggiunte e la data. Quando le righe precedenti nel file mostrano quante azioni detenevi prima dello split, mostra anche il **rapporto** risultante (ad esempio 3 per uno split 3-a-1) e le azioni detenute.

Due pulsanti ti permettono di risolvere la questione:

- **Crea l'evento SPLIT e collega** apre il piccolo modulo dell'evento con il tipo già impostato su **Split** e il rapporto compilato con quello suggerito. Puoi modificarlo: digita `3` per uno split 3-a-1, `0.25` per uno split inverso 1-a-4.
- **Collega a un evento esistente** ti permette di scegliere uno degli eventi dell'asset, se hai già creato lo split.

Una volta collegata la riga, la voce nel banner scompare. Se l'asset della riga non è ancora stato scelto, il banner ti chiede di sceglierlo prima. Per maggiori informazioni sugli eventi, vedi [Eventi dell'asset](../../assets/detail/events.md).

!!! note "🔢 Quando il broker arrotonda la quantità"

    A volte i broker arrotondano le azioni che registrano (ad esempio 0.1643 invece di 0.16431924). Se la quantità della riga differisce dal valore ottenuto moltiplicando la tua posizione per (il rapporto meno uno), il banner lo segnala e indica la differenza in azioni. La vista **Lots** segue il rapporto dell'evento, mentre la **dashboard** e il costo medio seguono la quantità della riga. La differenza è piccola, ma dopo aver venduto l'intera posizione potrebbe restare un minuscolo lotto non vendibile.

!!! warning "Collega lo split a un evento Split"

    Finché la riga non è collegata a un evento **Split**, le nuove azioni entrano senza costo e diluiscono il costo medio dell'asset. La vista **Lots** mostra un lotto con costo 0. Se vendi parte della posizione, LibreFolio vende prima i lotti vecchi e costosi al prezzo dopo lo split, quindi vedi una perdita e in seguito un guadagno quando il lotto a costo zero viene esaurito. Un asset senza quotazioni resta inoltre sopravvalutato: le nuove azioni contano a pieno valore, anche se il prezzo non è stato diviso. Collegare l'evento fa sì che il costo segua le vecchie azioni, il che è corretto per uno split. Il file non indica se le azioni provengono da uno split, da un regalo o da uno spin-off, quindi la scelta resta a te.

## 🚧 Limiti noti

- **Gli split inversi non vengono importati.** Una riga **STOCK SPLIT** con **Quantity** negativa, pari a zero o mancante (o senza ticker) viene elencata in un avviso ambra, con un link per aprire una issue su GitHub: aggiungila manualmente.
- **Solo file Invest.** Gli split azionari vengono letti negli estratti conto Invest, non in quelli Crypto.
- **Qualcosa non torna?** Apri una [issue](https://github.com/Librefolio/LibreFolio/issues) con un file di esempio anonimizzato.

## 🔗 Riferimenti per sviluppatori

→ [Revolut provider — Dettagli di implementazione](../../../developer/backend/brim/providers_list.md)
