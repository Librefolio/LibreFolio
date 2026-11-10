# 💸 Transazioni

Le transazioni sono tutti i movimenti del tuo portafoglio: acquisti, vendite, dividendi, commissioni, trasferimenti e liquidità in entrata o in uscita. LibreFolio calcola da esse le tue posizioni, la performance e i costi, quindi un registro completo mantiene corretti tutti i valori.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Elenco transazioni">
</div>

La pagina **Transazioni** elenca le transazioni di tutti i broker a cui hai accesso, dalla più recente alla più vecchia. Ogni broker mostra le proprie transazioni anche nella sua [scheda Transazioni](../brokers/import.md).

---

## 🔎 Trovare e aprire una transazione

- **Ordina** — clicca l'intestazione di una colonna.
- **Filtra** — apri il filtro di una colonna (data, tipo, asset, broker, tag, descrizione…). Nel filtro data, digita una data solo in **Da** per vedere le transazioni da quel giorno in poi, oppure solo in **A** per quelle fino a quel giorno; i due estremi di un intervallo devono essere giorni diversi. I tuoi filtri vengono mantenuti nell'indirizzo della pagina, così un segnalibro riapre la stessa vista.
- **Apri** — fai doppio clic su una riga per vederla in sola lettura; la matita passa alla modifica.
- **Prezzo unitario** — una colonna accanto all'importo mostra il prezzo per unità implicito in un'operazione (l'importo diviso per la quantità, secondo la base di quotazione dell'asset); è in sola lettura e vuota per una riga priva di quantità e importo, e per le gambe di una coppia collegata. Nascondila dal menu delle colonne se non ti serve. L'editor bulk ha la stessa colonna.

Senza filtri né ordinamento, le due righe di una coppia collegata (un trasferimento o un cambio valuta) restano una accanto all'altra, e l'icona del collegamento salta alla riga partner.

---

## ➕ Aggiungere o importare transazioni

- **Aggiungi transazione** apre il [workspace bulk](#bulk-workspace) su un modulo **Nuova transazione**: compilalo ([Modulo transazione](form.md)), clicca **Applica**, poi **Salva tutto**.
- **Importa** apre il workspace bulk con la **Procedura guidata di importazione**, che legge i file esportati dal tuo broker — vedi [Importa dal broker](import/index.md).

---

## ✏️ Modificare, clonare o eliminare transazioni

- **Una riga** — fai clic con il tasto destro, oppure usa le azioni della riga: **Visualizza**, **Modifica**, **Clona**, **Dividi coppia** o **Elimina**. Vedi solo le azioni che il tuo ruolo su quel broker consente.
- **Più righe** — selezionale, poi scegli **Modifica**, **Clona** o **Elimina** nella barra di selezione. **Modifica** ed **Elimina** escludono le righe dei broker in cui sei solo un visualizzatore.

Ognuna di queste apre il workspace bulk, e nulla cambia prima di **Salva tutto**. Modificare o eliminare un lato di una coppia collegata porta con sé il suo partner.

**Clona** mantiene la data originale: è così che registri di nuovo una riga storica, per esempio con un altro tipo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Workspace bulk con una riga di transazione clonata">
</div>

---

## 🔗 Collegare o scollegare una coppia {: #link-pairs }

Alcune operazioni consistono in due transazioni collegate — vedi [Transazioni abbinate](form.md#composite-transactions).

- **Collega** — seleziona due righe singole che vanno insieme e clicca **🔗 Promuovi coppia**. Due **Rettifiche** diventano un **Trasferimento asset**; un **Prelievo** e un **Deposito** diventano un **Cambio valuta** (stesso broker, due valute) oppure un **Giroconto** (due broker, stessa valuta e stesso importo). Se le righe hanno una descrizione diversa o tag diversi, scegli cosa mantenere; ogni riga mantiene la propria data. Una descrizione può contenere al massimo 500 caratteri: la finestra li conta e tiene **Conferma promozione** disabilitato finché la descrizione non rientra.
- **Scollega** — **Dividi coppia** su una riga collegata la riporta a due righe singole. Un **Trasferimento asset** diventa due **Rettifiche**: quella in entrata mantiene il proprio costo, quella in uscita preleva le unità senza attribuire loro un valore: sul suo broker le unità escono solo per la quantità, e il loro costo conta come una perdita realizzata (vedi [Rettifiche in uscita](../../financial-theory/instruments/transaction-types/adjustment.md#outgoing-adjustments)).

Entrambe le operazioni chiedono conferma, poi salvano subito, senza passare dal workspace bulk.

---

## 🔁 Ricollegare gli eventi {: #relink-events }

Un dividendo, un pagamento di interessi o una rettifica possono essere collegati all'**evento** dell'asset (il dividendo annunciato dal provider, uno split…). Il collegamento si perde quando [cambiare la valuta di un asset](../assets/create-edit.md#changing-the-currency) elimina gli eventi a cui puntava, e un dividendo che hai registrato prima che il suo evento fosse scaricato non ne ha mai avuto uno. **Ricollega eventi**, nella barra degli strumenti sopra la tabella, trova quelle transazioni e propone l'evento da collegare.

La finestra elenca i tuoi **dividendi, interessi e rettifiche** che hanno un asset e nessun evento, sui broker in cui hai almeno il ruolo di editor, dal più recente al più vecchio. Ogni riga mostra l'asset, la data, il tipo e ciò che è stato trovato:

| Cosa vedi | Significato | Cosa puoi fare |
|--------------|---------|-----------------|
| **Un evento quel giorno** | Esattamente un evento dello stesso asset, lo stesso giorno, del tipo corrispondente | **Collega** la riga |
| **Nessun evento quel giorno** | L'asset non ha un evento di quel tipo in quel giorno | Nulla qui: aggiungi l'evento, oppure collegane un altro nella transazione |
| **N eventi quel giorno** | Più di un candidato | Nulla qui: LibreFolio non tira mai a indovinare. Scegli quello giusto nella transazione |

**Collega ogni riga con un evento** collega in una volta tutte le righe del primo tipo, con un unico salvataggio: se una viene rifiutata, nessuna viene collegata. Nulla viene collegato finché non clicchi.

!!! info "L'evento deve avere la stessa data"

    Un candidato viene proposto solo se cade **lo stesso giorno** della transazione. Deve essere anche lo stesso asset e del tipo corrispondente: un dividendo con un dividendo, un pagamento di interessi con un evento di interessi, una rettifica con una rettifica prezzo o uno split.

    Per esempio, hai registrato un dividendo il **12 marzo**. Un evento dello stesso asset datato **12 marzo** viene proposto. Un evento datato **10 marzo** **non** viene proposto, anche se è l'unico nelle vicinanze: la riga mostra *Nessun evento quel giorno*.

    È ciò che accade quando il tuo broker ha accreditato il dividendo qualche giorno dopo l'evento. Apri la transazione e scegli tu stesso l'evento in **Evento collegato** ([Modulo transazione](form.md)).

---

## 🧰 Il workspace bulk {: #bulk-workspace }

Il workspace bulk è una griglia di righe in bozza — contrassegnate come **nuova**, **modifica** o **eliminazione** — in cui prepari le modifiche prima di scriverle:

- **Aggiungi riga**, **Importa** e **Reimposta tutto** si trovano sopra la griglia. Selezionando le righe compaiono **Reimposta selezionate**, **Elimina selezionate** e, per una coppia corrispondente, **🔗 Promuovi coppia**.
- Le righe vengono controllate mentre lavori: i problemi compaiono in alto sotto *Sono stati trovati errori di validazione*, e un clic ti porta alla riga. Con molte righe, il controllo automatico si sospende — premi **⚡ Valida ora** prima di salvare.
- Quando due righe sembrano le due metà di un trasferimento o di un cambio, un banner verde propone di unirle con **Unisci** — due righe nuove, due righe già salvate, oppure una nuova e una già salvata. Quando propone più di una coppia, **Unisci tutto (N)** le unisce in un colpo solo. Se le due righe di una coppia hanno una descrizione diversa o tag diversi, una sola scelta vale per tutte le coppie: **Tutto a sinistra** mantiene la descrizione e i tag della prima riga, come mostrati nel banner; **Tutto a destra**, quelli della seconda riga; **Combina**, l'impostazione predefinita, mantiene entrambe le descrizioni e i tag di entrambe le righe. Una descrizione può contenere al massimo 500 caratteri, come in qualsiasi transazione: con **Combina**, una coppia le cui due descrizioni insieme supererebbero quel limite non viene unita, e un messaggio dice quante coppie sono state lasciate — uniscile una alla volta con **Unisci**, dove puoi accorciare la descrizione.
- Quando l'altra metà è già salvata ma non è nel workspace bulk — un trasferimento il cui primo lato hai importato il mese scorso, per esempio — il pulsante 💡, sopra la griglia e nel menu della riga, propone di aggiungerla: una volta dentro, il banner propone la coppia.
- **Salva tutto** scrive tutto in una volta. Se ci sono suggerimenti di unione che non hai esaminato — il 💡 non è mai stato aperto, il banner verde non è mai stato cliccato — chiede prima (*Suggerimenti che non hai ancora esaminato*): **Mostra i suggerimenti** apre l'elenco del 💡, oppure porta in vista il banner; **Salva comunque** prosegue. Dopo che hai esaminato, non chiede più finché non chiudi il workspace bulk. **Annulla** chiude il workspace bulk, chiedendo prima se hai modifiche non salvate.

??? warning "🚦 Banner dopo un'importazione — quando compaiono"

    Dopo un'importazione, i banner sopra la griglia elencano cosa controllare prima di **Salva tutto**:

    - **rosso** — righe che l'importatore non ha compreso del tutto: **Salva tutto** resta disabilitato finché non le completi;
    - **ambra** — campi derivati automaticamente da verificare: **Salva tutto** ti chiede prima di **Esaminarli** oppure di premere **Salva comunque**;
    - **ambra, date** — righe datate prima del 1° gennaio 1900, elencate una per una (clicca una voce per andare alla riga corrispondente): **Salva tutto** chiede una volta sola per tutte (*Sì, le date sono corrette*). Una data così antica di solito è un errore di battitura; una volta confermata viene salvata come qualsiasi altra.
    - **ambra** — righe che potrebbero essere split (importazioni Revolut e Trading212): collega a ciascuna un evento split, oppure crealo dal banner; vedi [Revolut](import/revolut.md#stock-splits).

    Clicca un banner per espanderne l'elenco, poi una voce: la griglia passa alla pagina di quella riga e la evidenzia. I problemi di bilanciamento elencano le righe che li causano (*Righe del workspace: …*), e un clic apre la prima nell'ordine corrente. Se i filtri delle tue colonne nascondono la riga, un messaggio te lo segnala.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="bulk-todo-banner" alt="Workspace bulk con il banner dei campi da verificare espanso e la riga della voce cliccata evidenziata nella griglia">
</div>

Dopo un salvataggio, oppure dopo un'operazione **Promuovi coppia** o **Dividi coppia**, la pagina Transazioni azzera la sua selezione, poiché quelle righe potrebbero essere cambiate; chiudere o annullare la mantiene. Se un'operazione **Promuovi coppia** o **Dividi coppia** viene rifiutata, nulla cambia: un messaggio di errore spiega perché, e la conferma resta aperta.

---

## 🧭 Guide contestuali

La pagina Transazioni, il modulo **Aggiungi transazione**, il workspace bulk e la [Procedura guidata di importazione](import/how-to.md#guided-first-import) hanno ciascuno una breve guida. Una guida parte solo quando la sua schermata è pronta e non modifica mai una bozza né preme un pulsante al posto tuo; nel workspace bulk mostra un avviso alla volta, chiuso con **Ho capito**.

Puoi ripetere qualsiasi guida da [Impostazioni → Preferenze → Primo utilizzo e guide](../settings/preferences.md#onboarding-and-guides).

---

## 🔗 Correlati

* 📝 **[Modulo transazione](form.md)** — campi e tipi di transazione
* 📥 **[Importa dal broker](import/index.md)** — il flusso di importazione BRIM
* 📖 **[Tipi di transazione](../../financial-theory/instruments/transaction-types/index.md)** — la teoria finanziaria dietro ogni tipo
