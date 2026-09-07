# 🧠 Esportazione AI

L'Esportazione AI trasforma il contesto attuale di LibreFolio in testo strutturato
che puoi incollare in un assistente AI o conservare come snapshot portabile.

!!! important "Solo esportazione negli appunti"

    LibreFolio **non** contatta un servizio AI. Costruisce lo snapshot finanziario e
    tecnico sul tuo server, lo visualizza nel tuo browser e lo copia negli appunti.
    Sei tu a scegliere se e dove incollarlo.

## 📋 Cosa Fa

L'Esportazione AI è disponibile da:

- la barra degli strumenti della Dashboard per le attività di Portafoglio;
- la barra degli strumenti del Broker per le attività di Broker;
- la barra degli strumenti della pagina nelle pagine di dettaglio Asset e FX.

Il backend fornisce valutazioni, performance, allocazioni, fatti economici FIFO,
esposizione FX e indicatori tecnici. Il catalogo pubblico espone intenzionalmente
solo **otto scelte autonome di Esporta Dati** e **undici Analisi orientate alle
attività**. I dataset backend più piccoli rimangono blocchi di composizione interni.

**Esporta Dati** copia uno snapshot fattuale selezionato senza istruzioni di
analisi. **Richiedi Analisi** aggiunge un obiettivo e un contratto di risposta a
uno snapshot autonomo, oltre a un suggerimento di esportazione pubblica
complementare quando utile. Le note opzionali e la lingua di risposta richiesta si
applicano solo alle analisi.

## 🚀 Come Usarlo

1. Apri la pagina Portafoglio, Broker, Asset o FX pertinente.
2. Seleziona **Esportazione AI** (:material-brain:).
3. Scegli **Esporta Dati** o **Richiedi Analisi**, quindi seleziona un dataset o
 un'Analisi.
4. Scegli il periodo AI e il livello di dettaglio.
5. Per un'analisi, aggiungi note opzionali quando l'Analisi le supporta.
6. Seleziona **Copia Esportazione AI**, quindi incolla il risultato nello strumento
 che preferisci.

## 🎛️ Opzioni di Esportazione

| Opzione | Significato |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tipo di esportazione** | **Esporta Dati** crea un prompt di dataset fattuale. **Richiedi Analisi** aggiunge l'obiettivo dell'Analisi, le istruzioni di verifica, il contratto di risposta e i dataset pertinenti. |
| **Dataset o analisi** | Le scelte disponibili provengono dal catalogo runtime corrente di LibreFolio per la pagina/dominio. |
| **Periodo AI** | **3M**, **6M**, **1Y** o Personalizzato quando offerto. Il periodo termina alla data dello snapshot. La cronologia parziale della fonte rimane esplicita. |
| **Livello di dettaglio** | **Compatto**, **Standard** e **Completo** mantengono lo stesso universo di entità. Gli snapshot generali utilizzano mini-cronologie uniformi progressivamente più dense; le esportazioni di mercato dettagliate utilizzano la politica completa di campionamento tecnico. Completo può essere di grandi dimensioni e non è sempre necessario. |
| **Note per l'AI** | Disponibili per le analisi supportate. Aggiungono contesto utente opzionale come blocco dati serializzato in modo sicuro. |

Le bozze del tipo di esportazione, della selezione, del dettaglio, del periodo AI
e delle note rimangono nella memoria del browser per 10 minuti per contesto di
pagina. La chiusura del pannello o la navigazione altrove li conserva entro quella
finestra. La scadenza, il logout o un nuovo accesso reimpostano ogni pannello
Esportazione AI ai suoi valori predefiniti; le bozze non vengono persistite in
`localStorage`.

## 📤 Dati di Esportazione Disponibili

| Pagina | Snapshot generale | Cronologia di mercato dettagliata |
| --------- | -------------------------------------- | ----------------------------------- |
| Dashboard | **Panoramica e Cronologia del Portafoglio** | **Cronologia Asset del Portafoglio** |
| Broker | **Panoramica e Cronologia del Broker** | **Cronologia Asset del Broker** |
| Asset | **Posizione e Cronologia di Mercato (completa)** | **Solo Cronologia di Mercato (senza posizioni)** |
| FX | **Mercato ed Esposizione FX** | **Cronologia di Mercato FX** |

Gli snapshot generali combinano i fatti economici correnti con un percorso storico
compatto e un contesto di mercato mirato. Le cronologie di mercato dettagliate
contengono serie più dense di prezzi o tassi osservati, indicatori, stati, eventi
e copertura.

## 🗂️ Analisi Disponibili

### 📊 Portafoglio

| Attività | Scopo |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Piano di Investimento Ricorrente | Rivedere la struttura del portafoglio, i flussi di cassa e i vincoli per gli investimenti ricorrenti. |
| Ribilanciamento del Portafoglio | Confrontare l'allocazione attuale con il contesto di diversificazione e allocazione target. |
| Performance del Portafoglio e Fattori di Mercato | Riconciliare la performance, quindi ricercare i fattori datati per orizzonti a breve e lungo termine per ogni Asset detenuto senza sovrastimare la causalità. |
| Strategie di Compensazione delle Perdite di Capitale | Esplorare come le perdite fiscali disponibili o in scadenza potrebbero compensare i guadagni ammissibili utilizzando prove economiche FIFO e un inventario fiscale ufficiale esplicito. |

### 🏦 Broker

| Attività | Scopo |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Revisione del Broker | Riassumere posizioni, liquidità, attività, performance e copertura dati per un broker. |
| Performance del Broker e Fattori di Mercato | Riconciliare la performance del Broker selezionato e ricercare i fattori datati per ogni Asset detenuto. |
| Strategie di Compensazione delle Perdite di Capitale | Esplorare i percorsi di compensazione delle perdite fiscali utilizzando le prove economiche FIFO del Broker selezionato e l'inventario fiscale ufficiale dell'utente. |

### 📈 Asset

| Attività | Scopo |
| ------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Revisione della Posizione | Rivedere dimensione, costo base, performance, reddito e contesto di concentrazione. |
| Analisi di Mercato dell'Asset | Rivedere la cronologia delle chiusure osservate, rendimenti, trend, momentum, volatilità, Drawdown, stati, eventi e copertura. |

### 💱 FX

| Attività | Scopo |
| ---------------------- | ------------------------------------------------------------------------------------------------ |
| Analisi della Coppia FX | Rivedere direzione della coppia, rendimenti, volatilità, prove tecniche, copertura e contesto macro datato. |
| Impatto dell'Esposizione FX | Rivedere i collegamenti diretti di liquidità, valuta di negoziazione e valuta di valutazione alla coppia. |

Le analisi che confrontano percorsi futuri utilizzano una **Tesi di Scenario**:
prove fornite, ipotesi, orizzonte temporale, compromessi, condizioni di attivazione,
condizioni di invalidazione e decisioni mancanti dell'utente. È obbligatoria per
gli scenari PAC, di ribilanciamento e di compensazione delle perdite di capitale.

## 🧩 Cronologia Parziale e Dati Aggiuntivi

LibreFolio può esportare la cronologia effettivamente disponibile quando è più
corta del periodo AI richiesto. Il prompt mostra le date richieste/disponibili,
la copertura, gli avvisi e qualsiasi Segnale parziale o omesso. Non utilizza mai
prezzi o tassi futuri.

Un'Analisi può raccomandare **Dati Aggiuntivi di LibreFolio** quando un'altra
esportazione migliorerebbe sostanzialmente la risposta. Il prompt fornisce il nome
pubblico dell'esportazione, il percorso UI, il periodo/dettaglio consigliato, il
motivo e se è richiesto o opzionale.

!!! info "Il Drawdown è sempre sull'intera cronologia"

    Ovunque appaia una sezione Drawdown in un'esportazione, è calcolata sull'**intera
    cronologia disponibile** — dal primo prezzo memorizzato per un Asset, o dalla
    prima transazione per un Portafoglio o Broker — mai relativamente al periodo AI
    selezionato. Una finestra di esportazione breve porta comunque il vero
    picco-minimo storico.

## 🔗 Riferimenti Locali

Il prompt utilizza riferimenti locali per unire tabelle compatte:

- A# per gli Asset;
- B# per i Broker;
- F# per le coppie FX;
- L# per i lotti FIFO.

La Directory delle Entità risolve i riferimenti A#, B# e F#. I lotti L# sono
diversi: sono **righe incorporate** dentro le tabelle FIFO dell'esportazione
stessa, non voci della directory — il modello li legge sul posto. Il modello
ricevente dovrebbe utilizzare nomi leggibili nella sua risposta; gli ID del
database non sono necessari.

## 🔒 Ambito e Privacy

- Le esportazioni del Portafoglio seguono il filtro broker attivo, l'intervallo di
 date e la valuta obiettivo.
- Le esportazioni del Broker contengono solo il broker selezionato e richiedono
 l'accesso ad esso.
- Le esportazioni Asset e FX utilizzano l'entità corrente, l'intervallo selezionato,
 la valuta obiettivo e l'ambito dei broker accessibili all'utente dove il contesto
 del portafoglio è necessario.
- Il testo negli appunti può contenere dati finanziari sensibili. Rivedilo prima di
 condividerlo o incollarlo in un servizio di terze parti.

## ⚠️ Disponibilità e Sicurezza

L'Esportazione AI fallisce in modalità sicura se i cataloghi del browser e del
server o i contratti di risposta non corrispondono. Un'opzione può anche essere
non disponibile quando i suoi fatti non si applicano, ad esempio la Revisione della
Posizione senza una posizione aperta o l'Impatto dell'Esposizione FX senza
esposizione diretta collegata.

L'esportazione fornisce un contesto fattuale, non consigli di investimento o
istruzioni di trading automatizzato.

## 🔗 Pagine Correlate

- [Esportazione AI del Portafoglio](portfolio.md)
- [Esportazione AI del Broker](broker.md)
- [Esportazione AI dell'Asset](asset.md)
- [Esportazione AI FX](fx.md)
