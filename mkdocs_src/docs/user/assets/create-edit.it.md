# ➕ Crea e modifica asset

Aggiungi uno strumento che possiedi o che segui, collegalo a un provider di prezzi e mantieni corretti i suoi dettagli.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Modulo di creazione manuale" alt="Modale di creazione manuale">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Modulo di creazione automatica della procedura guidata di importazione" alt="Crea asset dalla procedura guidata">
</div>

## 🚀 Crea un asset {: #asset-creation-flows }

=== "Dalla pagina Asset"

    1. Nella pagina **Asset**, fai clic su **+ Aggiungi asset**.
    2. In **Cerca online**, digita un nome, un ticker o un ISIN e scegli un risultato: LibreFolio compila il
       modulo, collega quel provider e [verifica i suoi dati](#provider-data-comparison). Nessun risultato?
       Compila il modulo da solo e segnala la ricerca con [**Faccelo sapere**](#let-us-know).
    3. Controlla i campi seguenti, poi fai clic su **Crea asset**.

=== "Da un'importazione del broker"

    1. Nella sezione **Risolvi asset** della procedura guidata di importazione, scegli **Crea nuovo asset** nel
       selettore del titolo.
    2. Il modulo si apre con i codici e i nomi del report. Se il report non ha un nome, **Nome**
       inizia con l'ISIN (o il ticker).
    3. Fai clic su uno dei **Suggerimenti** sotto **Cerca online** per cercare il titolo, oppure compila
       il modulo da solo. Poi fai clic su **Crea asset**.

    Se il risultato che scegli ha lo stesso nome di uno dei tuoi asset, LibreFolio propone di usare quell'asset
    invece; **Usalo e aggiungi la chiave** salva su di esso anche i codici del report.

Controlla questi campi prima di salvare:

- **Nome**: obbligatorio e univoco; se un altro asset lo usa già, compare un avviso.
- **Tipo**: vedi [Scegli il tipo di asset](#choosing-the-asset-type).
- **Unità per singolo prezzo**: a quante unità si riferisce un prezzo, di solito 1, e 100 per la maggior
  parte delle obbligazioni. La selezione di un risultato di **Cerca online** lo imposta, come imposta il nome:
  al suggerimento del provider, se ne fornisce uno, con una nota sotto il campo che ne spiega il motivo
  ([Yahoo Finance](providers/yahoo-finance.md) suggerisce 100 per una linea di Londra quotata in pence, per
  esempio), altrimenti a 100 per **Obbligazione** e 1 per qualsiasi altro tipo. Lo fa anche in **Modifica asset**,
  sovrascrivendo il valore salvato, che cambia solo quando salvi. Digitare nel campo rimuove la nota. Scegliere
  tu stesso il **Tipo** lascia il campo com'è; per un'**Obbligazione**, un suggerimento ti ricorda che le
  obbligazioni sono di solito quotate per 100.
- **Valuta**: la valuta in cui sono quotati i prezzi. Per un fondo quotato in euro è EUR, anche quando il
  fondo è denominato in un'altra valuta.

Dopo il salvataggio dalla pagina **Asset**, la conferma rimanda al nuovo asset. Se l'asset ha un
provider, la cronologia dei prezzi inizia subito a essere scaricata.

## 🔎 Risultati di Cerca online {: #search-online-results }

**Cerca online** interroga tutti i provider contemporaneamente e ordina i risultati man mano che arrivano:
prima le fonti **premium** (quelle garantite dalla tua istanza, come i dati con licenza), poi quelle
**community**, ciascun gruppo per priorità. Nessuno dei provider forniti con LibreFolio è
premium e tutti hanno la stessa priorità: i risultati compaiono man mano che i provider rispondono, a meno che
il tuo amministratore non [cambi l'ordine](../../admin/configuration_accounts.md#provider-order).

Quando la ricerca ha incluso una fonte premium, l'elenco ha due parti:

- **Premium**: i risultati delle fonti premium, oppure *Nessun risultato dalle fonti premium.*
- **Fonti non premium (community) · N risultati**, chiusa. All'apertura mostra prima un avviso: queste
  sono fonti di terze parti, LibreFolio non garantisce i loro prezzi o dati e sceglierne una vale solo per
  questo asset. La sezione viene richiusa la prossima volta che apri il modulo.

### 📨 Non lo trovi? Faccelo sapere {: #let-us-know }

Una volta terminata una ricerca, qualunque cosa abbia trovato, anche dopo un errore o un timeout, l'elenco offre
*Non lo trovi?* **Faccelo sapere** (tra le due parti, quando ce ne sono due), purché l'app
sappia dove inviare la segnalazione. La segnalazione va a chi gestisce il supporto della tua istanza. Se l'elenco
si è chiuso, fai clic nella casella di ricerca per riaprirlo; svuotare la casella fa dimenticare la ricerca.

La destinazione del link dipende dall'indirizzo di supporto della tua istanza; il suo tooltip ti dice quale:

| Indirizzo di supporto | Cosa fa **Faccelo sapere** |
|---|---|
| Un indirizzo email | Si apre la tua app di posta con un messaggio già compilato con oggetto e dettagli |
| Una pagina web | La pagina si apre in una nuova scheda con oggetto e dettagli nel suo indirizzo, così un modulo di supporto può compilarsi da solo. Anche i dettagli vengono copiati, pronti da incollare lì; un messaggio conferma la copia oppure indica che non è riuscita |
| Nessuno (predefinito), su un'istanza self-hosted | Una nuova issue GitHub si apre in una nuova scheda, già compilata. È **pubblica**: controllala prima di inviarla |

Il link manca, anche in presenza di un indirizzo di supporto, quando l'app non è riuscita a leggere la
configurazione della tua istanza; ricaricando la pagina si riprova.

I dettagli sono in inglese: il testo che hai cercato; ogni provider interrogato e il suo esito (quanti
risultati, *nessuna risposta*, o un errore, con il relativo codice quando presente; mai il messaggio
dell'errore); gli identificatori già presenti nel modulo, e la sua valuta e il suo tipo, a meno che siano
ancora i valori predefiniti di un modulo nuovo e vuoto (la tua valuta di base e Azione); la tua versione di
LibreFolio, il profilo dell'istanza e la lingua dell'app. Quando modifichi un asset, i dettagli includono
quindi gli identificatori dell'asset stesso (ISIN, ticker…), la sua valuta e il suo tipo, come li mostra il
modulo. Non includono mai chi sei, un indirizzo email, l'indirizzo della tua istanza o dati di portafoglio.
Sei tu a inviare la segnalazione, dal tuo dispositivo: non passa mai attraverso il server di LibreFolio.

## 🗂️ Scegli il tipo di asset {: #choosing-the-asset-type }

Il campo **Tipo** apre un menu ricercabile di
[tipi di asset](../../financial-theory/instruments/asset-types/index.md). **ETF** e
**Crowdfunding** sono famiglie: aprine una per vedere prima la voce generica (**ETF**, **Crowdfund**),
poi quelle specifiche come **ETF azionario** o **Crowdfunding immobiliare**. Digita qualche lettera per
cercare su entrambi i livelli, per nome o codice (ad esempio `etf_bond`).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="type-picker-open" alt="Menu Tipo con la famiglia ETF espansa, ogni tipo specifico di ETF mostra la sua icona composta">
</div>

**Cerca online** di solito imposta un tipo generale come **ETF**. Se sai cosa detiene il fondo,
affinalo, ad esempio a **ETF azionario**: il suo badge e la sua icona mostrano allora cosa detiene. Un successivo
[controllo rispetto ai dati del provider](#provider-data-comparison) mantiene la tua scelta.

## 🔌 Collega un provider di prezzi

Selezionare un risultato di **Cerca online** collega automaticamente il suo provider. Per impostarne uno
manualmente, espandi **Assegnazione provider** (deseleziona prima **Nessun provider** se è selezionato):

1. Scegli il **Provider**, poi inserisci l'**Identificatore**, il suo **Tipo di identificatore** e le eventuali
   impostazioni richieste dal provider.
2. Fai clic su **Test configurazione**: LibreFolio recupera un **Prezzo corrente** e alcuni giorni di
   **Cronologia**. ⚠️ significa che il provider non offre quel dato o non ne ha nessuno al momento (ad esempio,
   CSS Scraper non ha cronologia); il test viene comunque superato. ❌ è un errore: controlla l'identificatore e
   le impostazioni. Quando **Cronologia** risponde, anche con ⚠️, una nota ricorda che il test legge solo
   gli ultimi giorni: un nuovo asset riceve l'intera cronologia dei prezzi quando viene creato.

⚠️ *In pausa per troppe richieste fino a …* significa che il provider ha rifiutato le richieste di LibreFolio
perché erano troppe: LibreFolio non lo interroga fino all'ora indicata, nel tuo orario locale,
con la data, se la pausa termina in un altro giorno. Le tue impostazioni potrebbero benissimo essere corrette,
quindi il test viene comunque superato. Quando la fine della pausa non è nota, vedi *Troppe richieste: riprova più tardi*.
Nel frattempo, l'elenco Asset e la pagina dell'asset continuano a mostrare l'ultimo prezzo salvato.

Un asset ha al massimo un provider; seleziona **Nessun provider** se inserirai tu stesso i suoi prezzi. Vedi
[Provider](providers/index.md) per ciò che offre ciascuno.

## ⚖️ Controlla i dati del provider {: #provider-data-comparison }

LibreFolio confronta i dettagli del provider con il tuo modulo dopo che selezioni un risultato di **Cerca online**
e quando fai clic su **Chiedi al provider**: nella parte superiore di **Dettagli asset** per tutto, accanto a
**Identificatori** o in un editor di distribuzione solo per quella parte. Richiede un provider e un identificatore.

- I campi vuoti vengono compilati e i codici aggiuntivi del provider si aggiungono a **Altri identificatori**.
- *Il provider non ha dati per: …* indica una distribuzione settoriale o geografica mancante; *Tutti i dati
  corrispondono al provider* significa che non c'è nulla da rivedere.
- Qualunque cosa sia diversa apre la finestra di dialogo **Confronto dati provider**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="create-provider-compare" alt="La finestra di dialogo Confronto dati provider sopra il modulo Aggiungi asset: la riga TICKER chiede quale codice sia quello principale, con il codice del provider scelto al posto di quello già salvato, che viene mantenuto come alternativo; la riga Tipo con i suoi valori attuali e del provider come badge con icona; la riga Distribuzione settoriale, il valore attuale rispetto a quello del provider; e Seleziona tutto, Deseleziona tutto, Annulla e Applica selezionati">
</div>

Ogni riga della finestra di dialogo mostra il tuo **Valore corrente** accanto al **Valore del provider** e inizia
selezionata:

1. Deseleziona le righe in cui vuoi mantenere il tuo valore (**Seleziona tutto** e **Deseleziona tutto** aiutano).
2. Su una riga di identificatore, scegli il codice principale; l'altro viene mantenuto in **Altri identificatori**
   (vedi [Modifica identificatori](#one-instrument-several-codes)). Viene proposto il codice del provider,
   dato che di norma è quello quotato.
3. Fai clic su **Applica selezionati**, che conteggia le righe che prendi (ad esempio *Applica selezionati (2/3)*),
   oppure su **Annulla** per non cambiare nulla.

I valori accettati compilano solo il modulo: vengono memorizzati quando salvi l'asset.

- **Il tuo tipo affinato viene mantenuto.** Borsa Italiana, ad esempio, classifica ogni strumento ETFplus come
  semplice **ETF**: se hai scelto **ETF azionario**, questo conta come accordo e non compare alcuna riga (lo stesso
  vale per **Crowdfunding**). Un tipo *più specifico* del tuo viene comunque proposto.
- **Ogni domanda viene posta una sola volta.** Quando un risultato di ricerca porta un ISIN (o un altro codice)
  diverso da quello nel modulo, LibreFolio chiede prima quale sia quello principale e il confronto non lo chiede
  di nuovo.
- **Il valore di Unità per singolo prezzo viene proposto, mai compilato.** Un controllo completo (dopo aver scelto un risultato
  di ricerca, o con **Chiedi al provider** nella parte superiore di **Dettagli asset**) lo confronta con il
  suggerimento del provider o, in mancanza, con 100 per un'obbligazione e 1 per qualsiasi altro tipo (il tipo
  proposto dal provider, se ne propone un altro). Una differenza è una riga selezionata sotto **Dettagli asset**,
  con una nota che ne indica il motivo: il suggerimento del provider, oppure che le obbligazioni sono di solito
  quotate per 100 (una riga che propone il consueto 1 non ne ha). Deselezionala per mantenere il tuo valore.
  Se un controllo torna senza il suggerimento del provider (ad esempio, perché ha impiegato troppo tempo), vale
  ancora quello fornito in precedenza per lo stesso provider e identificatore, nel risultato di ricerca o in un
  controllo precedente: LibreFolio non propone di annullarlo.

## 🛠️ Modifica un asset {: #editing-an-asset }

Nella [pagina di dettaglio](detail/index.md) dell'asset, fai clic su **Modifica** (✏️), cambia ciò che serve nel
modulo **Modifica asset** e fai clic su **Salva modifiche**.

### 💱 Cambiare la valuta {: #changing-the-currency }

Una nuova **Valuta** è sempre consentita, ma i prezzi e gli eventi sono memorizzati nella valuta in cui sono
espressi, quindi quelli vecchi non possono restare accanto a quelli nuovi. Cambiare la valuta elimina una parte
di ciò che è memorizzato per l'asset e conserva il resto:

| Memorizzato per l'asset | Dopo la modifica |
|----------------------|------------------|
| La sua **cronologia dei prezzi** | Eliminata |
| I suoi **dividendi, interessi e altri eventi**, quelli inseriti da te e quelli generati dal provider | Eliminati |
| Le tue **transazioni** | Sempre **conservate**. Quelle collegate a un evento eliminato restano, ma perdono quel collegamento |
| I suoi **split** | **Conservati**, e così le transazioni a essi collegate: le rettifiche di uno split mantengono il loro collegamento e il loro costo |

Gli split sono un rapporto, non un importo di denaro, quindi significano la stessa cosa in qualsiasi valuta.

Prima di salvare qualsiasi cosa, il modulo chiede al server cosa verrebbe rimosso. Se la risposta non può essere
letta, il modulo mostra l'errore e non salva nulla. Se non verrebbe rimosso nulla (l'asset non ha ancora prezzi,
eventi o transazioni collegate), la modifica viene semplicemente salvata. Se qualcosa verrebbe rimosso, una finestra
di dialogo **Cambia valuta dell'asset** lo elenca:

- i **punti prezzo** che saranno eliminati, con il periodo che coprono;
- gli **eventi manuali** e gli **eventi generati dal provider** che verranno eliminati;
- le transazioni che **perdono il collegamento a un evento eliminato** (le transazioni stesse vengono conservate);
- gli **eventi split** che restano, con le transazioni a essi collegate.

Nulla viene eliminato finché non fai clic su **Elimina e cambia valuta**; **Annulla** lascia l'asset com'era.
La finestra di dialogo ti permette anche di scaricare prima un **backup** dei prezzi e degli eventi (CSV o JSON), quando ce ne sono.

Dopo la modifica, se l'asset ha un provider e aveva dei prezzi, questi vengono scaricati di nuovo dal
provider, a partire dalla data più vecchia che avevi, nella nuova valuta. Senza un provider, importi tu stesso i prezzi
di nuovo. Le transazioni che hanno perso il collegamento a un evento possono essere ricollegate in un colpo solo: vedi
[Ricollega eventi](../transactions/index.md#relink-events).

Cambiare o rimuovere il provider ha le sue regole, di seguito.

### 🔄 Cambiare o rimuovere il provider {: #changing-or-removing-the-provider }

Alcuni cambi di provider eliminano dati che LibreFolio aveva memorizzato. Prima di salvare, il modulo chiede al
server cosa verrebbe rimosso e, se qualcosa verrebbe rimosso, mostra **una** conferma che riporta i numeri.
Nulla viene eliminato finché non confermi; **Annulla** lascia l'asset com'era.

| Cosa cambi | Cosa viene eliminato |
|-----------------|-----------------|
| Nuove impostazioni per un piano di [investimento programmato](providers/scheduled-investment.md) | Tutti i prezzi dell'asset e gli eventi generati dal piano: vengono generati di nuovo dalle nuove impostazioni |
| Un altro provider, quando l'asset era su un piano di investimento programmato | Lo stesso: tutti i prezzi e gli eventi generati dal piano; il nuovo provider fornisce poi la cronologia |
| **Nessun provider** | Gli eventi generati dal provider (i suoi dividendi, split o cedole). I prezzi che hai già sono **conservati** |
| Un altro provider online, o nuove impostazioni per uno online (Yahoo Finance, justETF…); un primo provider per un asset che non ne aveva | Nulla, e non viene posta alcuna domanda |

Ad esempio, passando da un piano a Yahoo Finance viene chiesto:

> La cronologia di questo asset è stata generata dal piano di investimento programmato. Passare a Yahoo Finance
> elimina 1.240 punti prezzo e 6 eventi generati dal provider. 3 transazioni perdono il
> collegamento a un evento eliminato (le transazioni stesse vengono conservate). […] Gli eventi manuali vengono conservati.
> Questa operazione non può essere annullata. Continuare?

Cosa significa la finestra di dialogo:

- I **punti prezzo e gli eventi** sono conteggiati come memorizzati in questo momento. I prezzi includono quelli che hai inserito
  tu stesso, quando cambiano le impostazioni di un piano o il provider; con **Nessun provider** restano.
- **Le transazioni non vengono mai eliminate.** Una transazione che hai registrato su un evento eliminato, come un
  dividendo o una cedola, resta nel tuo portafoglio ma perde il collegamento: il suo campo **Evento collegato**
  è vuoto. La finestra di dialogo conteggia tutte queste transazioni, comprese quelle su broker
  che non puoi vedere, e non le nomina.
- **Gli eventi che hai aggiunto tu restano**, con i loro collegamenti.
- Se non andrebbe perso nulla, o se non è stato possibile ottenere il conteggio, il modulo salva senza finestra di dialogo.

⚠️ **Un caso viene rifiutato.** Se uno split generato dal provider ha rettifiche collegate senza un
[valore di acquisto](../transactions/form.md), la modifica o la rimozione non vengono effettuate: con lo split eliminato,
quelle unità conterebbero come acquistate a un prezzo sconosciuto. Il modulo mostra il messaggio invece della
finestra di dialogo, indica lo split con la sua data e il resto della modifica viene salvato. Assegna un valore di acquisto a quelle rettifiche, poi cambia di nuovo il provider.

## 🏷️ Modifica identificatori {: #one-instrument-several-codes }

Un titolo può avere diversi codici. LibreFolio mantiene **un solo asset** con tutti, sotto
**Altre informazioni** nel modulo dell'asset:

- **Identificatori**: i codici principali, uno per tipo (ISIN, ticker…). **Aggiungi identificatore** aggiunge una riga e
  **Chiedi al provider** li recupera.
- **Altri identificatori**: qualsiasi codice aggiuntivo o etichetta del broker. Digitane uno e premi Invio, virgola, punto e virgola
  o Tab. Questi codici sono ricercabili e aiutano a riconoscere l'asset nelle importazioni successive.

!!! tip "Mantieni il codice quotato come ISIN principale"

    Un prezzo è il valore dell'ultimo scambio, quindi solo un codice negoziabile ha un prezzo. Metti quel codice in
    **ISIN** e tutto il resto in **Altri identificatori**, altrimenti nessun provider può fornire un prezzo per l'asset.

### 🏛️ Titoli di Stato italiani per il retail (BTP Valore, BTP Più, BTP Italia)

Questi titoli vengono sottoscritti con un ISIN e negoziati con un altro:

| Fase | Codice | Cosa fa |
|---|---|---|
| Sottoscrizione all'emissione | l'ISIN "CUM" | Dà diritto al **premio fedeltà** se detieni fino a scadenza. **Non negoziabile**, quindi nessun provider lo quota |
| Mercato secondario | un ISIN diverso | Liberamente negoziato e **quotato**: è quello che ha un prezzo |

Per vendere prima della scadenza, il titolo viene convertito nel codice di mercato. Mantieni entrambi i codici su un unico asset:

1. Metti l'**ISIN di mercato** in **ISIN**.
2. Metti l'**ISIN CUM** in **Altri identificatori**.
3. Registra il **premio fedeltà**, quando viene pagato, come transazione di **Interesse** su quell'asset.
   Funziona anche dopo la scadenza: un asset disattivato resta selezionabile.

Quando un'importazione porta il codice CUM per un asset che ha quello di mercato, LibreFolio chiede quale codice
debba essere quello principale e mantiene l'altro in **Altri identificatori**.

## 🗺️ Imposta le distribuzioni settoriali e per paese

I provider compilano le distribuzioni settoriali e geografiche quando possono; per gli altri asset, impostale
tu stesso. Alimentano i grafici di allocazione della dashboard e l'AI Export.

Nel modulo dell'asset, espandi **Altre informazioni**: sotto **Classificazione**, **Distribuzione settoriale** e
**Distribuzione geografica** mostrano una riga per settore o paese, con il relativo peso in percentuale.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-distribution-editors" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="distribution-editor-sector" data-title="🏭 Distribuzione settoriale" alt="Editor della distribuzione settoriale nel modale dell'asset">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="distribution-editor-geographic" data-title="🌍 Distribuzione geografica" alt="Editor della distribuzione geografica nel modale dell'asset">
</div>

- I pulsanti **Aggiungi settore** / **Aggiungi paese** aggiungono una riga: scegli la voce, poi digita il suo peso.
- Il **Totale** diventa verde al 100%, ambra quando manca qualcosa, rosso quando superi il 100%.
- **Bilancia al 100%**, un'azione di riga, sposta l'intero scarto in quella riga. **Bilancia le righe selezionate**
  lo ripartisce tra le righe selezionate, in proporzione ai loro pesi.
- **Rimuovi** elimina una riga, **Chiedi al provider** recupera la distribuzione del provider e **Importa CSV**
  ne carica una da un file.

### 📥 Importa una distribuzione da CSV {: #importing-a-distribution-csv }

**Importa CSV** si aspetta un'intestazione `name,weight`, poi una riga per paese o settore, con i pesi in
percentuale:

```csv
name,weight
USA,60
Italy,40
```

- I **nomi** devono corrispondere esattamente, ignorando maiuscole/minuscole e spazi iniziali e finali. Paesi: un codice ISO
  (`IT`, `ITA`) o il nome nella tua lingua. Settori: la chiave del settore (come `Government Bonds`)
  o il nome nella tua lingua.
- I **pesi** vanno da `0` a `100` e devono sommare a 100 (entro 0,005 punti); ogni nome compare
  una sola volta.
- L'importazione è **tutto o niente**: una riga errata la blocca. Quando riesce, **sostituisce** l'intera distribuzione.

!!! warning "Virgole decimali"

    Il separatore, `,` o `;`, viene letto dall'intestazione. Con `,`, la riga `Italy,12,5` viene
    letta silenziosamente come `12`. Usa `;` ovunque (`name;weight`, poi `Italy;12,5`), racchiudi il valore tra virgolette
    (`Italy,"12,5"`), oppure scrivi `Italy,12.5`.

## 🧲 Unisci asset duplicati

Se lo stesso strumento è finito in due asset, ciascuno contiene una parte della sua cronologia. Per unirne uno all'altro:

1. Nella pagina **Asset**, usa **Unisci con…** sull'asset che deve sparire: il pulsante sulla sua scheda, o il menu contestuale nella tabella.
2. Scegli l'asset da mantenere (anche quelli inattivi) e fai clic su **Continua**. In un giorno in cui entrambi hanno un prezzo,
   prevale il prezzo dell'asset mantenuto; lo stesso vale per il suo provider di prezzi, se ne ha uno.
3. Leggi **Cosa viene spostato**: i conteggi esatti di transazioni, prezzi ed eventi. Dove entrambi gli asset
   hanno un codice diverso dello stesso tipo, scegli quello che deve prevalere.
4. Fai clic su **Unisci ed elimina**. Il primo asset viene eliminato; l'operazione non può essere annullata.

Nessun identificatore va perso: ogni codice dell'asset eliminato riempie un campo vuoto di quello mantenuto o si aggiunge
ai suoi **Altri identificatori**. Gli eventi identici vengono uniti.

Durante un'importazione, quando due dei tuoi asset riportano l'ISIN di un titolo, la sua scheda **Risolvi asset**
dice *Due asset memorizzati corrispondono a questo titolo* e offre **Unisci**. La sola corrispondenza dei nomi non lo attiva mai.

## 🔗 Correlati

- 📊 **[Pagina di dettaglio dell'asset](detail/index.md)** — Visualizza e analizza i dati dell'asset
- 🔌 **[Provider](providers/index.md)** — Provider di prezzi disponibili
- 🧬 **[Identità dell'asset](../../developer/frontend/components/features/asset-identity.md)** — Per gli sviluppatori: come funzionano identificatori, confronti con i provider e fusioni
