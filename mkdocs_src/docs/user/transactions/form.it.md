# 📝 Modulo transazione

Il modulo transazione aggiunge o modifica una transazione — o una coppia collegata — nel [workspace bulk](index.md#bulk-workspace). Mostra inoltre una transazione in sola lettura quando fai doppio clic su di essa in un elenco. Compaiono solo i campi necessari al tipo scelto.

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ACQUISTO' alt="Acquisto">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENDITA' alt="Vendita">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDENDO' alt="Dividendo">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DEPOSITO' alt="Deposito">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> RETTIFICA' alt="Rettifica">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRASFERIMENTO' alt="Trasferimento asset">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CONVERSIONE FX' alt="Conversione FX">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> GIROCONTO' alt="Giroconto">
</div>

---

## ✍️ Compila il modulo

1. Scegli il **Tipo**, poi il **Broker** se non è già impostato.
2. Compila la sezione **Obbligatori**: la **Data**, l'**Asset** e la sua quantità quando il tipo ne prevede una, e l'importo in denaro.
3. Apri **Opzionali** per i **Tag**, una **Descrizione** o, per dividendi, interessi e rettifiche, un **Evento collegato**.
4. Fai clic su **Applica** per inserire la riga nel workspace; **Salva tutto** nel workspace la salva.

Alcune regole rendono l'inserimento rapido:

- **Gli importi sono totali** — l'importo che salvi è il totale pagato o ricevuto, mai il prezzo per azione (*Importo totale (non per azione)*). In un acquisto o in una vendita puoi scrivere l'uno o l'altro: il totale, oppure il prezzo unitario (i pulsanti accanto al campo indicano quale), e il modulo calcola l'altro — vedi [Totale o prezzo unitario](#unit-price).
- **Digita numeri positivi** — il modulo aggiunge il segno meno dove escono denaro o unità: il pagamento di un acquisto, le unità di una vendita, un prelievo, una commissione, un'imposta. Solo la quantità di una **Rettifica** accetta un segno: positiva aggiunge unità, negativa le rimuove.
- **Controlli durante la compilazione** — una volta compilati i campi obbligatori, il modulo verifica l'inserimento rispetto al tuo registro e alle altre righe del workspace ed elenca eventuali problemi in alto. Il modulo individua anche da solo alcuni errori: una data che non riesce a leggere, o una data futura, resta sullo schermo in rosso e la data precedente non viene usata al suo posto; una quantità o un importo con segno o formato errato, come una quantità negativa in un acquisto, vengono segnalati in rosso; e un avviso in alto segnala un trasferimento con lo stesso broker su entrambi i lati, o un cambio con la stessa valuta. Finché non li correggi, non viene controllato nulla, *valido* non compare e **Applica** resta disabilitato. **⚡ Valida ora** li trova tutti in una volta — vedi [Valida ora](#validate-now). Le date delle transazioni possono risalire fino all'anno 1 e arrivare fino a domani, ma il modulo stesso si ferma a oggi. Una data precedente al 1900 è quasi sempre un errore di battitura, quindi il modulo ti avvisa con un banner ambra e **Applica** resta disabilitato finché non premi **Sì, la data è corretta**; se cambi la data, lo chiede di nuovo, e una volta confermata la data viene salvata come qualsiasi altra. Una data successiva a domani viene rifiutata con un messaggio come *Data: Non successiva al 2026-10-18*, quando oggi è il 17 ottobre 2026.
- **Broker o asset mancanti?** — **Crea nuovo** nell'elenco dei broker, o **Nuovo asset** nell'elenco degli asset, crea l'elemento senza uscire dal modulo.
- **Evento mancante?** — **+ Nuovo evento** nel campo **Evento collegato** crea l'evento dell'asset e lo collega. Se l'asset ha già un evento di quel tipo in quella data, non viene salvato nulla: la finestra mostra quell'evento, per usarlo, o per modificarlo se lo hai inserito manualmente, e non lo sovrascrive mai ([Nuovo evento da una transazione](../assets/detail/events.md#new-event)).

<div id="cost-basis"></div>

??? info "💰 Costo di carico delle unità in entrata — per Rettifiche e Trasferimenti asset"

    Quando una **Rettifica** aggiunge unità, o sul lato ricevente di un **Trasferimento asset**, il modulo chiede quanto costano quelle unità:

    - **Auto** — LibreFolio lo calcola come [prezzo medio di carico (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md); premi **⚡ Valida ora** per vederlo.
    - **Manuale** — lo digiti tu.

    Una **Rettifica** che rimuove unità non chiede alcun costo: non ha valore. Le unità vengono solo rimosse dalla quantità, e il loro costo viene conteggiato come minusvalenza realizzata. Per registrare una vendita, usa una **Vendita**.

    In **Auto**, la media viene calcolata presso il broker mittente di un trasferimento, o presso il broker della rettifica stessa. Se quel broker non detiene alcuna unità dell'asset nel giorno in cui le unità lo lasciano o vi arrivano, o detiene solo unità il cui costo è sconosciuto, non c'è nulla da mediare: **Auto** viene rifiutato e non viene salvato nulla — scegli **Manuale** e digita quanto ti sono costate quelle unità (0 per una donazione). In **Manuale**, il campo non può restare vuoto: LibreFolio segnala la riga e non salva nulla finché non lo compili o passi a **Auto**; un costo negativo viene rifiutato allo stesso modo — digita 0 o più. Modificare una transazione salvata non fa eccezione: se svuoti il suo costo in **Manuale**, il salvataggio viene rifiutato, perché la transazione necessita di un costo di carico — scegli **Auto** o digita un valore. Digita 0 per le nuove azioni di uno split azionario. Per una donazione, invece di 0, puoi digitare quanto il donatore ha pagato per quelle unità: questo mantiene più vicini ai valori reali il prezzo medio di carico (PMC) e la plusvalenza su cui potresti essere tassato. Le unità inserite con costo 0 contano come gratuite, non come sconosciute: una successiva media **Auto** presso il loro broker le conta a 0. Se manca un tasso di cambio, il link **Sincronizza tassi FX** lo recupera.

---

## 🧮 Totale o prezzo unitario {: #unit-price }

Su un **Acquisto** o una **Vendita** (e su qualsiasi altro tipo singolo che abbia sia una quantità sia un importo in denaro), l'etichetta del campo dell'importo in denaro ha due piccoli pulsanti, **Totale** e **Prezzo unitario**. Il modulo resta un unico importo e la sua valuta: i pulsanti indicano solo **come leggere il numero che hai digitato** in quel campo.

- **Totale** (predefinito) — il numero è l'importo pagato o ricevuto. Sotto il campo il modulo mostra il prezzo unitario che calcola: *= 83,40 per unità*.
- **Prezzo unitario** — il numero è il prezzo di un'unità. Sotto il campo il modulo mostra il totale che calcola: *= 1.000,80 in totale*.

Passando da un pulsante all'altro, il numero che hai scritto resta e viene letto nell'altro modo. Ciò che viene salvato è sempre il **totale**: con **Prezzo unitario** attivo, il totale mostrato sotto il campo è quello che entra nella transazione. Quando apri una transazione salvata, il campo mostra il totale, con i pulsanti su **Totale**.

Il calcolo viene fatto dal modulo stesso, immediatamente, sulle cifre esatte che hai digitato (senza errori di arrotondamento dovuti ai numeri in virgola mobile). Usa la stessa convenzione di prezzo del resto dell'app: la quantità viene divisa per il *prezzo per N unità* dell'asset e moltiplicata per il prezzo, così un'obbligazione quotata per 100 funziona nel modo in cui si legge la sua quotazione (*= 98,55 per 100 unità*). Il risultato viene arrotondato a ciò che viene memorizzato: gli importi mantengono 6 decimali e i prezzi unitari 12. In caso di parità, si arrotonda alla cifra pari (*half-even*). Un valore troppo lungo viene segnalato in rosso, come al solito. Il prezzo unitario è nella stessa valuta dell'importo. L'asset e la quantità devono essere inseriti; senza di essi non viene calcolato nulla e il campo mostra il suo consueto suggerimento (cosa inserire).

!!! example "Esempio"

    Hai acquistato 12 azioni a 83,40. Premi **Prezzo unitario**, digita *83,40* nel campo dell'importo in denaro e sotto leggi *= 1.000,80 in totale*. Il tuo broker ha effettivamente addebitato 1.000,90: premi **Totale**, digita *1.000,90* e sotto leggi *= 83,408333333333 per unità*. L'importo salvato è *1.000,90*.

Quando apri una transazione salvata solo per visualizzarla, vedi il totale e, sotto, il prezzo unitario calcolato dal totale e dalla quantità. I pulsanti compaiono solo mentre puoi modificare.

I tipi senza una quantità o senza un importo, i trasferimenti e i cambi non hanno pulsanti. La griglia dell'[editor bulk](index.md#bulk-workspace) non li ha ancora.

---

## ⚡ Valida ora {: #validate-now }

**⚡ Valida ora** è sempre cliccabile, anche su un modulo appena aperto. Premilo ogni volta che vuoi sapere cosa manca ancora o cosa è sbagliato. Funziona allo stesso modo per una transazione singola, una coppia di trasferimento e un cambio valuta.

Quando lo premi, esamina il modulo in due passaggi, prima che qualsiasi cosa lasci il tuo computer:

1. **Campi obbligatori** — la data, il broker, l'asset e la sua quantità quando il tipo ne prevede una, e l'importo in denaro. Per una coppia controlla anche l'altro lato: il broker ricevente e la seconda data, e per un cambio valuta entrambi gli importi ed entrambe le valute.
2. **Ciò che hai digitato** — una data che non può essere letta, una quantità o un importo che non è un numero valido o ha troppe cifre, un segno errato, oppure la stessa valuta o lo stesso broker su entrambi i lati.

Ogni cella errata diventa rossa immediatamente:

- un valore obbligatorio **mancante** riceve un contorno rosso;
- un valore **scritto male** è rosso sul campo stesso.

Il focus salta alla prima cella errata, contando dall'alto, e un piccolo contatore accanto al pulsante indica quanti campi devono essere corretti. Finché c'è qualcosa di errato, non viene inviato nulla al server. Ogni segnalazione scompare non appena correggi il suo campo.

Quando ogni campo è corretto, il pulsante interroga il server, come ha sempre fatto, e mostra *valido* oppure i problemi che il server trova nel tuo registro e nelle altre righe del workspace.

!!! example "Esempio"

    Lasci vuota la quantità e digiti *abc* come data. Premi **⚡ Valida ora**: entrambe le celle diventano rosse, il focus si posa sulla data, il contatore mostra *2 campi da correggere* e non viene inviato nulla. Correggi la data e la sua segnalazione scompare; compila la quantità e il contatore si azzera, e alla pressione successiva viene interrogato il server.

---

## 🏷️ Tipi di transazione

La [guida alla teoria finanziaria](../../financial-theory/instruments/transaction-types/index.md) spiega in profondità ogni tipo.

### 🧾 Transazioni singole

| Tipo | Cosa registra | Teoria |
|------|-----------------|--------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **Acquisto** | Unità di un asset acquistate e totale pagato | [📖 Leggi](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } **Vendita** | Unità di un asset vendute e totale ricevuto | [📖 Leggi](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **Dividendo** | Liquidità pagata da un asset che possiedi | [📖 Leggi](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } **Interesse** | Interessi ricevuti, con o senza un asset | [📖 Leggi](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **Deposito** | Liquidità che versi sul broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } **Prelievo** | Liquidità che prelevi dal broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **Commissione** | Una commissione o un altro costo, eventualmente associati a un asset | [📖 Leggi](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } **Imposta** | Un'imposta pagata, facoltativamente collegata a un asset | [📖 Leggi](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **Rettifica** | Unità aggiunte o rimosse senza movimenti di liquidità: uno split, una donazione, una posizione aperta altrove | [📖 Leggi](../../financial-theory/instruments/transaction-types/adjustment.md) |

### 🔗 Transazioni abbinate {: #composite-transactions }

Un'operazione abbinata viene registrata come due transazioni collegate, che il modulo mostra come una sola, con un lato **Da** e un lato **A**. Ogni lato ha la propria data, e la freccia **Inverti lati** inverte la direzione. In un cambio valuta le due date di solito coincidono: differiscono quando il broker accredita la nuova valuta in un altro giorno.

| Tipo | Cosa registra | Teoria |
|------|-----------------|--------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **Trasferimento asset** | Unità di un asset spostate tra due tuoi broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **Giroconto** | Liquidità spostata tra due tuoi broker, in un'unica valuta | [📖 Leggi](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **Cambio valuta** | Una valuta convertita in un'altra, all'interno di un unico broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

Un trasferimento richiede due broker diversi, un cambio richiede due valute diverse. Due righe singole possono anche essere collegate in una coppia in un secondo momento, e una coppia può essere separata di nuovo — vedi [Collega o scollega una coppia](index.md#link-pairs).

---

## 🔗 Voci correlate

- 📋 **[Transazioni](index.md)** — l'elenco, i filtri e il workspace bulk
- 📥 **[Importa dal broker](import/index.md)** — salta l'inserimento manuale con un'importazione BRIM
