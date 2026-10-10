# ➕ Creare e modificare asset

Aggiungi uno strumento che possiedi o segui, collegalo a un provider di prezzi e mantieni corretti i suoi dettagli.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Modulo di creazione manuale" alt="Finestra di creazione manuale">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Modulo di creazione automatica dalla procedura guidata di importazione" alt="Creazione dell'asset dalla procedura guidata">
</div>

## 🚀 Creare un asset {: #asset-creation-flows }

=== "Dalla pagina Asset"

    1. Nella pagina **Asset**, fai clic su **+ Aggiungi asset**.
    2. In **Cerca online**, digita un nome, un ticker o un ISIN e scegli un risultato: LibreFolio compila
       il modulo, collega quel provider e [verifica i suoi dati](#provider-data-comparison). Nessun risultato?
       Compila il modulo manualmente.
    3. Controlla i campi sottostanti, poi fai clic su **Crea asset**.

=== "Da un'importazione del broker"

    1. Nella sezione **Risolvi asset** della procedura guidata di importazione, scegli **Crea nuovo asset** nel
       selettore del titolo.
    2. Il modulo si apre con i codici e i nomi del report. Se il report non ha un nome, **Nome**
       inizia con l'ISIN (o il ticker).
    3. Fai clic su uno dei **Suggerimenti** sotto **Cerca online** per cercare il titolo, oppure compila
       il modulo manualmente. Poi fai clic su **Crea asset**.

    Se il risultato che scegli ha lo stesso nome di uno dei tuoi asset, LibreFolio ti propone di usare
    quell'asset; **Usalo e aggiungi la chiave** salva su di esso anche i codici del report.

Controlla questi campi prima di salvare:

- **Nome**: obbligatorio e univoco; appare un avviso se un altro asset lo usa già.
- **Tipo**: vedi [Scegliere il tipo di asset](#choosing-the-asset-type).
- **Unità per singolo prezzo**: a quante unità si riferisce un prezzo, di solito 1. Le obbligazioni sono quotate per
  100: LibreFolio lo propone quando scegli **Obbligazione**.
- **Valuta**: la valuta in cui sono quotati i prezzi. Per un fondo quotato in euro è EUR,
  anche quando il fondo è denominato in un'altra valuta.

Dopo il salvataggio dalla pagina **Asset**, la conferma contiene il link al nuovo asset. Se l'asset ha un
provider, la cronologia dei prezzi inizia a essere scaricata subito.

## 🗂️ Scegliere il tipo di asset {: #choosing-the-asset-type }

Il campo **Tipo** apre un menu con ricerca tra i
[tipi di asset](../../financial-theory/instruments/asset-types/index.md). **ETF** e
**Crowdfunding** sono famiglie: aprine una per vedere prima il membro generico (**ETF**, **Crowdfund**),
poi quelli specifici come **ETF azionario** o **Crowdfunding immobiliare**. Digita qualche lettera per
cercare in entrambi i livelli, per nome o per codice (ad esempio `etf_bond`).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="type-picker-open" alt="Il menu Tipo con la famiglia ETF espansa: ogni tipo di ETF specifico mostra la sua icona composita">
</div>

**Cerca online** di solito imposta un tipo generico come **ETF**. Se sai cosa detiene il fondo,
affinalo, ad esempio a **ETF azionario**: il suo badge e la sua icona mostrano allora cosa detiene. Una successiva
[verifica rispetto ai dati del provider](#provider-data-comparison) mantiene la tua scelta.

## 🔌 Collegare un provider di prezzi

Scegliere un risultato di **Cerca online** collega automaticamente il suo provider. Per impostarne uno
manualmente, espandi **Assegnazione provider** (deseleziona prima **Nessun provider** se è selezionato):

1. Scegli il **Provider**, poi inserisci l'**Identificatore**, il suo **Tipo di identificatore** e tutte le impostazioni
   richieste dal provider.
2. Fai clic su **Testa configurazione**: LibreFolio recupera un **Prezzo attuale** e qualche giorno di
   **Cronologia**. ⚠️ significa che il provider non offre questi dati o non ne ha al momento (ad esempio, CSS Scraper
   non ha cronologia); il test passa comunque. ❌ è un errore: controlla l'identificatore e
   le impostazioni.

Un asset ha al massimo un provider; seleziona **Nessun provider** se inserirai tu stesso i prezzi. Vedi
[Provider](providers/index.md) per ciò che offre ciascuno.

## ⚖️ Verificare i dati del provider {: #provider-data-comparison }

LibreFolio confronta i dettagli del provider con il tuo modulo dopo che scegli un risultato di **Cerca online**
e quando fai clic su **Chiedi al provider**: in cima a **Dettagli asset** per confrontare l'intero asset, accanto
agli **Identificatori**, oppure in un editor di distribuzione per confrontare solo quella parte. Richiede un provider e un
identificatore.

- I campi vuoti vengono compilati e i codici extra del provider si aggiungono agli **Altri identificatori**.
- *Il provider non ha dati per: …* indica una distribuzione settoriale o geografica mancante; *Tutti i dati corrispondono
  al provider* significa che non c'è nulla da rivedere.
- Qualsiasi cosa che differisce apre la finestra di dialogo **Confronto dati provider**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="create-provider-compare" alt="La finestra Confronto Dati Provider sopra il modulo Aggiungi Asset: la riga TICKER che chiede quale codice sia il principale, con il codice del provider scelto al posto di quello già salvato, che resta come alternativo; la riga Tipo con il valore attuale e quello del provider come badge con icona; la riga Distribuzione settoriale, attuale contro provider; e Seleziona tutto, Deseleziona tutto, Annulla e Applica Selezionati">
</div>

Ciascuna riga della finestra di dialogo mostra il tuo **Valore attuale** accanto al **Valore del provider** ed è
selezionata all'inizio:

1. Deseleziona le righe in cui vuoi mantenere il tuo valore (**Seleziona tutto** e **Deseleziona tutto** aiutano).
2. Su una riga identificatore, scegli il codice principale; l'altro viene mantenuto sotto **Altri identificatori** (vedi
   [Modificare gli identificatori](#one-instrument-several-codes)). Il codice del provider è proposto, poiché è
   normalmente quello quotato.
3. Fai clic su **Applica selezionati**, che conta le righe che accetti (ad esempio *Applica selezionati (2/3)*),
   o su **Annulla** per non cambiare nulla.

I valori accettati compilano solo il modulo: vengono memorizzati quando salvi l'asset.

- **Il tipo più specifico che hai scelto viene mantenuto.** Borsa Italiana, ad esempio, riporta ogni strumento ETFplus come
  semplice **ETF**: se hai scelto **ETF azionario**, questo conta come concordanza e non appare alcuna riga (lo stesso
  vale per **Crowdfunding**). Un tipo *più specifico* del tuo viene comunque proposto.
- **Ogni domanda viene posta una sola volta.** Quando un risultato di ricerca porta un ISIN (o altro codice)
  diverso da quello nel modulo, LibreFolio chiede prima quale è quello principale e il confronto
  non lo chiede di nuovo.

## 🛠️ Modificare un asset {: #editing-an-asset }

Nella [pagina di dettaglio](detail/index.md) dell'asset, fai clic su **Modifica** (✏️), cambia ciò che ti serve nel
modulo **Modifica asset** e fai clic su **Salva modifiche**.

Una nuova **Valuta** per un asset che ha già prezzi implica l'eliminazione dei prezzi e
degli eventi memorizzati: al salvataggio, una finestra di dialogo elenca ciò che viene rimosso (le transazioni restano) e
offre un backup. Dopo **Elimina e cambia valuta**, i prezzi vengono scaricati di nuovo dal provider, se ce n'è uno.

## 🏷️ Modificare gli identificatori {: #one-instrument-several-codes }

Un titolo può avere diversi codici. LibreFolio mantiene **un unico asset** con tutti i loro codici, sotto
**Più informazioni** nel modulo dell'asset:

- **Identificatori**: i codici principali, uno per tipo (ISIN, ticker…). **Aggiungi identificatore** aggiunge una riga e
  **Chiedi al provider** li recupera.
- **Altri identificatori**: qualsiasi codice extra o etichetta del broker. Digitane uno e premi Invio, virgola, punto e virgola
  o Tab. Questi codici sono ricercabili e aiutano a riconoscere l'asset nelle importazioni successive.

!!! tip "Mantieni il codice quotato come ISIN principale"

    Un prezzo è il valore dell'ultimo scambio, quindi solo un codice negoziabile ha un prezzo. Metti quel codice in
    **ISIN** e tutto il resto in **Altri identificatori**, altrimenti nessun provider può quotare l'asset.

### 🏛️ Titoli di Stato italiani retail (BTP Valore, BTP Più, BTP Italia)

Questi titoli sono sottoscritti con un ISIN e negoziati con un altro:

| Fase | Codice | Cosa fa |
|---|---|---|
| Sottoscrizione all'emissione | l'ISIN "CUM" | Ti dà diritto al **premio fedeltà** se detieni fino a scadenza. **Non negoziabile**, quindi nessun provider lo quota |
| Mercato secondario | un ISIN diverso | Liberamente negoziato e **quotato**: questo è quello con un prezzo |

Per vendere prima della scadenza, il titolo viene convertito al codice di mercato. Mantieni entrambi i codici su un unico asset:

1. Metti l'**ISIN di mercato** in **ISIN**.
2. Metti l'**ISIN CUM** in **Altri identificatori**.
3. Registra il **premio fedeltà**, quando viene pagato, come transazione di **Interesse** su quell'asset.
   Funziona anche dopo la scadenza: un asset disattivato resta selezionabile.

Quando un'importazione porta il codice CUM per un asset che detiene quello di mercato, LibreFolio chiede quale
codice deve guidare e mantiene l'altro sotto **Altri identificatori**.

## 🗺️ Impostare le distribuzioni settoriali e geografiche

I provider compilano le distribuzioni settoriali e geografiche quando possono; per gli altri asset, impostale tu stesso.
Alimentano i grafici di allocazione della dashboard e l'AI Export.

Nel modulo dell'asset, espandi **Più informazioni**: sotto **Classificazione**, **Distribuzione settoriale** e
**Distribuzione geografica** elencano una riga per settore o paese, con il relativo peso in percentuale.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-distribution-editors" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="distribution-editor-sector" data-title="🏭 Distribuzione settoriale" alt="Editor della distribuzione settoriale nella finestra dell'asset">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="distribution-editor-geographic" data-title="🌍 Distribuzione geografica" alt="Editor della distribuzione geografica nella finestra dell'asset">
</div>

- **Aggiungi settore** / **Aggiungi paese** aggiunge una riga: scegli la voce, poi digita il suo peso.
- Il **Totale** diventa verde al 100%, ambra quando manca qualcosa, rosso quando superi.
- **Bilancia al 100%**, un'azione di riga, trasferisce l'intero scarto in quella riga. **Bilancia le righe selezionate**
  lo distribuisce tra le righe selezionate, in proporzione ai loro pesi.
- **Rimuovi** elimina una riga, **Chiedi al provider** recupera la distribuzione del provider e **Importa CSV**
  ne carica una da un file.

### 📥 Importare una distribuzione da CSV {: #importing-a-distribution-csv }

**Importa CSV** si aspetta un'intestazione `name,weight`, poi una riga per paese o settore, con pesi in
percentuale:

```csv
name,weight
USA,60
Italy,40
```

- I **Nomi** devono corrispondere esattamente, ignorando maiuscole/minuscole e spazi circostanti. Paesi: un codice ISO
  (`IT`, `ITA`) o il nome nella tua lingua. Settori: la chiave del settore (come `Government Bonds`)
  o il nome nella tua lingua.
- I **Pesi** vanno da `0` a `100` e devono totalizzare 100 (entro 0,005 punti); ogni nome appare
  una sola volta.
- L'importazione è **tutto o niente**: una riga errata la blocca. Quando riesce, **sostituisce** l'intera
  distribuzione.

!!! warning "Virgole decimali"

    Il separatore, `,` o `;`, viene letto dall'intestazione. Con `,`, la riga `Italy,12,5` viene letta
    silenziosamente come `12`. Usa `;` ovunque (`name;weight`, poi `Italy;12,5`), racchiudi il valore tra virgolette
    (`Italy,"12,5"`), oppure scrivi `Italy,12.5`.

## 🧲 Unire asset duplicati

Se lo stesso strumento è finito in due asset, ciascuno detiene una parte della sua cronologia. Per unirne uno
nell'altro:

1. Nella pagina **Asset**, usa **Unisci con…** sull'asset che dovrebbe sparire: il pulsante sulla
   sua scheda o il menu di clic destro nella tabella.
2. Scegli l'asset da mantenere (anche quelli inattivi) e fai clic su **Continua**. In un giorno in cui entrambi hanno un prezzo,
   vince il prezzo dell'asset mantenuto; lo stesso vale per il suo provider di prezzi, se ne ha uno.
3. Leggi **Cosa viene spostato**: i conteggi esatti di transazioni, prezzi ed eventi. Dove entrambi gli asset
   hanno un codice diverso dello stesso tipo, scegli quello che guida.
4. Fai clic su **Unisci ed elimina**. Il primo asset viene eliminato; questo non può essere annullato.

Nessun identificatore va perso: ogni codice dell'asset eliminato riempie un campo vuoto di quello mantenuto o si aggiunge
ai suoi **Altri identificatori**. Gli eventi identici vengono uniti.

Durante un'importazione, quando due dei tuoi asset portano l'ISIN di un titolo, la sua scheda **Risolvi asset**
dice *Due asset memorizzati corrispondono a questo titolo* e offre **Unisci**. La sola corrispondenza dei nomi
non lo attiva mai.

## 🔗 Correlati

- 📊 **[Pagina di dettaglio asset](detail/index.md)** — Visualizza e analizza i dati dell'asset
- 🔌 **[Provider](providers/index.md)** — Provider di prezzi disponibili
- 🧬 **[Identità dell'asset](../../developer/frontend/components/features/asset-identity.md)** — Per gli sviluppatori: come funzionano identificatori, confronti tra provider e unioni
