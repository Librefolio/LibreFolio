# 💸 Transazioni

Le transazioni rappresentano ogni movimento del tuo portafoglio: acquisti, vendite, dividendi, commissioni, trasferimenti e entrate o uscite di cassa. LibreFolio calcola da esse le tue posizioni, i rendimenti e i costi, così un registro completo mantiene corretti tutti i valori.

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="list" alt="Elenco transazioni">
</div>

La pagina **Transazioni** elenca le transazioni di tutti i broker a cui puoi accedere, dalla più recente alla più vecchia. Ogni broker mostra anche le proprie nella sua [scheda Transazioni](../brokers/import.md).

---

## 🔎 Trova e apri una transazione

- **Ordina** — clicca sull'intestazione di una colonna.
- **Filtra** — apri il filtro di una colonna (data, tipo, asset, broker, tag, descrizione…). I tuoi filtri vengono mantenuti nell'indirizzo della pagina, quindi un segnalibro riapre la stessa vista.
- **Apri** — fai doppio clic su una riga per visualizzarla in sola lettura; la matita passa alla modifica.

Senza filtri o ordinamento, le due righe di una coppia collegata (un trasferimento o un cambio valuta) rimangono una accanto all'altra, e l'icona del collegamento salta alla riga partner.

---

## ➕ Aggiungi o importa transazioni

- **Aggiungi transazione** apre il [workspace bulk](#bulk-workspace) su un modulo **Nuova transazione**: compilalo ([Modulo transazione](form.md)), clicca **Applica**, poi **Salva tutto**.
- **Importa** apre il workspace con la **Procedura guidata di importazione**, che legge i file esportati dal tuo broker — vedi [Importa da Broker](import/index.md).

---

## ✏️ Modifica, clona o elimina transazioni

- **Una riga** — fai clic con il pulsante destro del mouse, oppure usa le azioni della riga: **Visualizza**, **Modifica**, **Clona**, **Scollega coppia** o **Elimina**. Vedi solo le azioni che il tuo ruolo su quel broker consente.
- **Più righe** — spuntale, poi scegli **Modifica**, **Clona** o **Elimina** nella barra di selezione. **Modifica** ed **Elimina** escludono le righe dei broker dove sei solo un Visualizzatore.

Ciascuna di queste apre il workspace bulk, e nulla cambia prima di **Salva tutto**. Modificare o eliminare un lato di una coppia collegata porta con sé il suo partner.

**Clona** mantiene la data originale: è così che registri di nuovo una riga storica, ad esempio sotto un altro tipo.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="clone-flow" alt="Workspace bulk con una riga di transazione clonata">
</div>

---

## 🔗 Collega o scollega una coppia {: #link-pairs }

Alcune operazioni sono due transazioni collegate — vedi [Transazioni accoppiate](form.md#composite-transactions).

- **Collega** — spunta due righe singole che vanno insieme e clicca **🔗 Promuovi coppia**. Due **Rettifiche** diventano un **Trasferimento asset**; un **Prelievo** e un **Deposito** diventano un **Cambio valuta** (stesso broker, due valute) o un **Giroconto** (due broker, stessa valuta e importo). Se le righe non concordano su data, descrizione, tag o costo di carico, scegli cosa mantenere.
- **Scollega** — **Scollega coppia** su una riga collegata la riporta a due righe singole.

Entrambe richiedono conferma, poi salvano subito, senza il workspace.

---

## 🧰 Il workspace bulk {: #bulk-workspace }

Il workspace è una griglia di righe in bozza — contrassegnate **nuova**, **modifica** o **elimina** — dove prepari le modifiche prima di scriverle:

- **Aggiungi riga**, **Importa** e **Reimposta tutto** si trovano sopra la griglia. Spuntando le righe si aggiungono **Reimposta selezionati**, **Elimina selezionate** e, per una coppia corrispondente, **🔗 Promuovi coppia**.
- Le righe vengono controllate mentre lavori: i problemi appaiono in alto sotto *Sono stati identificati degli errori nei campi*, e un clic ti porta alla riga. Con molte righe, il controllo automatico si sospende — premi **⚡ Convalida ora** prima di salvare.
- Quando due righe sembrano le due metà di un unico trasferimento o cambio, un banner verde propone **Unisci** — due righe nuove, due già salvate, o una nuova e una già salvata. Quando propone più di una coppia, **Unisci tutti (N)** le unisce in un colpo solo. Dove le due righe di una coppia hanno una descrizione diversa o tag diversi, una scelta si applica a ogni coppia: **Tutti sinistra** mantiene la descrizione e i tag della prima riga, come elencato dal banner; **Tutti destra**, quelli della seconda riga; **Combina**, l'impostazione predefinita, mantiene entrambe le descrizioni e i tag di entrambe le righe. Una descrizione tiene al massimo 500 caratteri, come in ogni transazione: due descrizioni lunghe combinate possono superarli, e allora il salvataggio è rifiutato.
- Quando l'altra metà è già salvata ma non è nel workspace — un trasferimento di cui hai importato il primo lato il mese scorso, ad esempio — il pulsante 💡, sopra la griglia e nel menu della riga, offre di aggiungerla: una volta inserita, il banner propone la coppia.
- **Salva tutto** scrive tutto in una volta. Se ci sono suggerimenti di unione che non hai guardato — il 💡 mai aperto, il banner verde mai cliccato — chiede prima (*Suggerimenti non ancora visti*): **Mostra i suggerimenti** apre l'elenco 💡, o porta il banner in vista; **Salva comunque** procede. Una volta che hai guardato, non chiede più finché non chiudi il workspace. **Annulla** chiude il workspace, chiedendo prima se ci sono modifiche non salvate.

??? warning "🚦 Banner dopo un'importazione — quando appaiono"

    Dopo un'importazione, i banner sopra la griglia elencano cosa controllare prima di **Salva tutto**:

    - **rosso** — righe che l'importatore non ha compreso appieno: **Salva tutto** rimane disabilitato finché non le completi;
    - **ambra** — campi derivati automaticamente da verificare: **Salva tutto** chiede prima di **Rivedi** o **Salva comunque**.

    Clicca su un banner per aprirne l'elenco, poi su una voce: la griglia passa alla pagina di quella riga e la evidenzia. I problemi di bilanciamento elencano le righe che li causano (*Righe del workspace: …*), e un clic apre la prima nell'ordine di ordinamento corrente. Se i filtri delle colonne nascondono la riga, un messaggio te lo indica.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="transactions" data-name="bulk-todo-banner" alt="Workspace bulk con il banner dei campi da verificare aperto e la riga della voce cliccata evidenziata nella griglia">
</div>

Dopo un salvataggio, un **Promuovi coppia** o uno **Scollega coppia**, la pagina Transazioni cancella la sua selezione, poiché quelle righe potrebbero essere cambiate; chiudere o annullare la mantiene. Se un **Promuovi coppia** o uno **Scollega coppia** viene rifiutato, non cambia nulla: un messaggio d'errore dice perché, e la conferma resta aperta.

---

## 🧭 Guide contestuali

La pagina Transazioni, il modulo **Aggiungi transazione**, il workspace bulk e la [Procedura guidata di importazione](import/how-to.md#guided-first-import) hanno ciascuno una breve guida. Una guida inizia solo quando la sua schermata è pronta e non modifica mai una bozza né preme un pulsante per te; nel workspace mostra un avviso alla volta, chiuso con **Capito**.

Ripeti qualsiasi guida da [Impostazioni → Preferenze → Primo utilizzo e guide](../settings/preferences.md#onboarding-and-guides).

---

## 🔗 Correlati

* 📝 **[Modulo transazione](form.md)** — campi e tipi di transazione
* 📥 **[Importa da Broker](import/index.md)** — il flusso di importazione BRIM
* 📖 **[Tipi di transazione](../../financial-theory/instruments/transaction-types/index.md)** — la teoria finanziaria dietro ogni tipo
