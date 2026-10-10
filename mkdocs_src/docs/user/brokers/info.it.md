# ⚙️ Configurazione e informazioni del broker

La scheda **Info** di un broker mostra i dettagli dell'account a sinistra e chi può accedervi a destra.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Vista delle informazioni e della condivisione del broker">
</div>

---

## 📋 Dettagli dell'account

La scheda **Dettagli** elenca:

- **Account attivo** — **✓ Attivo**, oppure **✗ Chiuso** per un account che non usi più. Un broker chiuso conserva la sua cronologia nei tuoi grafici.
- **Account aperto** — quando hai aperto l'account, se lo hai impostato.
- **Consenti acquisto con leva** e **Consenti vendita allo scoperto** — le due opzioni di trading, spiegate di seguito.
- **Creato nel sistema** — quando il broker è stato aggiunto a LibreFolio.

Per modificarli, fai clic su **Modifica** nella barra degli strumenti del broker (proprietari ed editor).

---

## 🛡️ Opzioni di trading {: #trading-options }

Entrambe le opzioni sono disattivate per un nuovo broker e LibreFolio ti protegge da saldi impossibili:

- con **Consenti acquisto con leva** disattivato, un salvataggio viene rifiutato se lascerebbe la liquidità di una valuta sotto zero;
- con **Consenti vendita allo scoperto** disattivato, un salvataggio viene rifiutato se lascerebbe la quantità di un asset sotto zero.

Attiva un'opzione per un conto a margine, oppure per registrare vendite allo scoperto.

??? note "📅 Come vengono controllati i saldi — quando un salvataggio viene rifiutato"

    Per ogni valuta $c$ e ogni asset $i$ del broker, LibreFolio controlla il saldo alla **fine di ogni giorno** $d$, dopo tutte le transazioni di quel giorno:

    $$
    C_c(d) = \sum_{\text{date}_t \le d} a_t \ge 0 \qquad\qquad Q_i(d) = \sum_{\text{date}_t \le d} q_t \ge 0
    $$

    Qui $a_t$ è l'importo di cassa di ogni transazione $t$ nella valuta $c$, e $q_t$ la quantità di ogni transazione dell'asset $i$. La liquidità in entrata e in uscita nello stesso giorno si compensa, ma un deposito effettuato successivamente non corregge un giorno che si è già chiuso sotto zero.

    Un salvataggio rifiutato viene mostrato nel workspace sotto *Questa configurazione causa incoerenze nei dati*, con la valuta o l'asset, la data e i link alle righe del workspace coinvolte.

---

## 🤝 Condividi il broker

La colonna di destra contiene il pannello **Condividi broker**; anche **Condividi broker** nella barra degli strumenti ti porta qui. Solo un proprietario può modificarlo: tutti gli altri lo vedono in sola lettura.

Per concedere l'accesso a qualcuno:

1. Fai clic su **+** (**Aggiungi utente**) sotto il grafico di proprietà e trova la persona **tramite nome utente**.
2. Scegli il **Ruolo** — **visualizzatore** per impostazione predefinita, **editor** o **proprietario** — e, per un proprietario, la **Quota di proprietà %**. Poi fai clic su **Aggiungi utente**.
3. Fai clic su **Salva configurazione**: nulla cambia prima che tu lo faccia.

Salva prima di cambiare scheda: nella scheda Info, le modifiche non salvate vengono perse senza chiedere.

Sotto **Il tuo accesso** puoi anche **Abbandona broker**, oppure **Passa a visualizzatore** se sei un editor. I ruoli e le quote di proprietà sono spiegati in [Condivisione del broker](sharing.md).

---

## 🔗 Correlati

- 🧠 **[AI Export del broker](../ai-export/broker.md)** — **AI Export** si trova nella barra degli strumenti del broker e funziona da ogni scheda.
- 🏦 **[Broker](index.md)** — creazione di un broker e dei suoi campi opzionali.
