# <img src="https://www.trading212.com/favicon-32x32.png" alt=""> Trading212

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esistere casi limite.

## 📥 Come esportare

Per esportare l'estratto conto delle transazioni da Trading212:

1. Accedi al [Trading212 Client Portal](https://www.trading212.com) (oppure apri l'app sul tuo dispositivo mobile).
2. Vai alla sezione menu/profilo e clicca su **Cronologia**.
3. Clicca sul pulsante **Esporta** (solitamente rappresentato da un'icona di esportazione o di documento nella parte alta della scheda della cronologia).
4. Seleziona le colonne desiderate (assicurati che tutti i campi come ticker, data, quantità, prezzo e valuta siano selezionati).
5. Scegli **CSV** come formato e clicca su **Esporta**. Salva il file sul tuo computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Trading212 Portal - History and CSV Export modal] -->
</div>

## ⚠️ Insidie comuni

!!! warning "Transazioni Pie"

    Trading212 supporta i "Pie" (panieri di asset gestiti automaticamente). Se fai trading all'interno di un Pie, l'esportazione riporta queste operazioni come transazioni separate dei singoli asset sottostanti. Il parser BRIM elabora automaticamente queste singole operazioni, ma assicurati che i saldi dei tuoi Pie siano completamente sincronizzati nella griglia di staging prima di confermare.

## 📝 Note

- Supporta acquisti e vendite di azioni/ETF, dividendi, interessi sulla liquidità, depositi e prelievi.
- Sono supportati i conti multi-valuta.
- I trasferimenti tra i tuoi stessi conti vengono omessi silenziosamente, poiché non cambiano nulla.

## 🔀 Split azionari

Trading212 scrive uno split come due righe, **Stock split close** (le vecchie azioni escono) e **Stock split open** (le nuove azioni arrivano), per lo stesso ISIN nello stesso istante. Quando le azioni dopo lo split sono **più** di prima, LibreFolio importa la coppia come un'unica **Rettifica** in entrata pari alla differenza, a costo zero.

L'importatore non è in grado di distinguere uno split da una donazione o da uno spin-off, quindi segnala la riga. Al termine della procedura guidata di importazione (il passo **Review**) ti indica quante righe sembrano split, e l'editor bulk mostra un banner, *N righe potrebbero essere split azionari*. Per ogni riga elenca il ticker, le azioni aggiunte e la data. Poiché la riga **Stock split close** contiene le azioni che avevi prima, mostra anche il **rapporto** risultante (ad esempio 3 per uno split 3 a 1) e le azioni possedute.

Due pulsanti ti permettono di risolvere la questione:

- **Crea l'evento SPLIT e collega** apre il piccolo modulo dell'evento con il tipo già impostato su **Split** e il rapporto compilato con quello suggerito. Puoi modificarlo: digita `3` per uno split 3 a 1, `0.25` per un raggruppamento (reverse split) 1 a 4.
- **Collega a un evento esistente** ti permette di scegliere uno degli eventi dell'asset, se hai già creato lo split.

Una volta collegata la riga, la voce scompare dal banner. Se l'asset della riga non è ancora stato scelto, il banner ti chiede di sceglierlo prima. Per maggiori informazioni sugli eventi, vedi [Eventi degli asset](../../assets/detail/events.md).

!!! note "🔢 Quando il broker arrotonda la quantità"

    A volte i broker arrotondano le azioni che scrivono (ad esempio 0.1643 invece di 0.16431924). Se la quantità della riga differisce dal prodotto tra la tua posizione e il rapporto, meno uno, il banner lo segnala e indica la differenza in azioni. La vista **Lots** segue il rapporto dell'evento, mentre la **Dashboard** e il costo medio seguono la quantità della riga. La differenza è piccola, ma dopo aver venduto l'intera posizione può rimanere un minuscolo lotto che non è possibile vendere.

!!! warning "Collega lo split a un evento Split"

    Finché la riga non è collegata a un evento **Split**, le nuove azioni entrano senza costo e diluiscono il costo medio dell'asset. La vista **Lots** mostra un lotto con costo 0. Se vendi parte della posizione, LibreFolio vende prima i vecchi lotti costosi al prezzo successivo allo split, così vedi una perdita, e in seguito un guadagno quando il lotto a costo zero viene esaurito. Un asset privo di quotazioni resta inoltre sopravvalutato: le nuove azioni contano a pieno valore, anche se il prezzo non è stato diviso. Collegare l'evento fa sì che il costo segua le vecchie azioni, il che è corretto per uno split. Il file non indica se le azioni provengono da uno split, da una donazione o da uno spin-off, quindi la scelta spetta a te.

## 🚧 Limiti noti

- **Split non importati.** Un reverse split (con meno azioni dopo rispetto a prima), uno split con lo stesso numero di azioni e una riga di split senza la sua riga abbinata vengono elencati in un avviso di colore ambra, con un link per aprire una issue su GitHub: aggiungili a mano.
- **Distribuzioni di azioni e conversioni di valuta non vengono importate.** Le righe **Stock distribution** e **Currency conversion** sono elencate nello stesso avviso: aggiungile a mano.
- **Qualcosa non torna?** Per favore [apri una issue](https://github.com/Librefolio/LibreFolio/issues) con un file di esempio anonimizzato.

## 🔗 Riferimenti per gli sviluppatori

→ [Trading212 Provider — Dettagli di implementazione](../../../developer/backend/brim/providers_list.md)
