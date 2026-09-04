# ➕ Crea e modifica asset

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Modulo di creazione manuale" alt="Modale di creazione manuale">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Modulo di creazione automatica tramite procedura guidata" alt="Crea asset dalla procedura guidata">
</div>

## 🚀 Flussi di creazione degli asset {: #asset-creation-flows }

In LibreFolio puoi creare nuovi asset in due modi diversi:

=== "Creazione manuale (con ricerca intelligente)"

 ```mermaid
 flowchart LR
 A[Start: Click '+ New Asset'] --> B[Type Name, ISIN, or Ticker in Smart Search]
 B --> C{Match Found?}
 C -->|Yes| D[Auto-fill details from external providers]
 C -->|No| E[Manually enter name, category, & currency]
 D --> F[Adjust config / Assign pricing provider]
 E --> F
 F --> G[Click Save]
 G --> H[Asset added to library]
 ```

=== "Creazione automatica da importazione broker"

 ```mermaid
 flowchart LR
 A[Start: Upload CSV report in Import Wizard] --> B[Parse report rows]
 B --> C{Asset ID recognized?}
 C -->|Yes| D[Auto-match with existing asset]
 C -->|No| E[Flag warning ⚠️ and show 'Create' button]
 E --> F[Click 'Create' to open pre-filled modal]
 F --> G[Save asset to resolve mapping]
 G --> D
 D --> H[Commit all transactions]
 ```

## 🧪 Verifica della configurazione del provider

Dopo aver configurato un provider, fai clic su **Test Configuration** per verificare che i dati di prezzo possano essere recuperati. Il test controlla:

- **Current Price**: recupera l'ultimo prezzo
- **History**: recupera i dati storici dei prezzi (se supportato)

I risultati vengono visualizzati inline con i tempi di esecuzione. Un avviso ⚠️ indica che l'operazione non è supportata da questo provider (ad esempio, CSS Scraper non supporta lo storico).

## 🔎 Dettagli della ricerca intelligente

La ricerca intelligente interroga prima di tutto il motore di ricerca di ciascun provider. Se un provider supportato non trova nulla,
LibreFolio può tentare una ricerca web dei collegamenti con criterio best-effort e ricondurre le pagine dei provider a candidati
asset. Per Borsa Italiana, ciò significa che l'URL di un fondo/dettaglio può diventare un asset pronto da salvare, con
i `provider_params` necessari per prezzare il fondo tramite il suo codice interno.

Per i fondi di Borsa Italiana, l'ISIN visibile identifica il fondo quando disponibile, ma la determinazione del prezzo utilizza il
codice interno Borsa del fondo salvato nella configurazione del provider. Il NAV corrente viene usato solo se datato oggi;
lo storico contiene un punto di NAV alla sua data reale.

## 🔌 Assegnazione del provider

Ogni asset può avere assegnato un solo provider di prezzo. Consulta [Provider](providers/index.md) per i dettagli sui provider disponibili e la loro configurazione.

## 🛠️ Modifica di un asset {: #editing-an-asset }

Fai clic sul pulsante **Edit** (✏️) nella [pagina di dettaglio](detail/index.md) per aprire la modale dell'asset con tutti i campi precompilati. Tutti i campi sono modificabili, comprese la configurazione del provider e le distribuzioni.

Il campo **Other identifiers** è un elenco modificabile di identificatori alternativi. Le importazioni e
i provider possono aggiungervi etichette del broker, codici tecnici o identificatori di fallback; ogni valore resta una
voce separata dell'elenco.

## 🗺️ Distribuzioni manuali geografiche e di settore

I provider compilano le distribuzioni per **area geografica** e per **settore** quando possono — ma molti
asset (strumenti personalizzati, obbligazioni, investimenti programmati, o semplicemente asset il cui provider non fornisce
alcuna ripartizione) arrivano senza distribuzioni. Puoi sempre impostare o correggere entrambe le distribuzioni a mano dalla
modale dell'asset: alimentano i **grafici di allocazione** della dashboard (anelli geografici e di settore, sia attuali sia
nel tempo) e il contesto di concentrazione dell'AI Export.

Nella modale dell'asset ([creazione](#asset-creation-flows) o [modifica](#editing-an-asset)) apri
l'area **Classificazione**:

1. **Distribuzione geografica** — una riga per paese/area, con il suo peso in percentuale.
2. **Distribuzione settoriale** — una riga per settore, con il suo peso in percentuale.

Per ogni distribuzione puoi:

- **Add a row** e scegli l'area/il settore dal menu a tendina, quindi digita il peso.
- **Edit weights inline**; il **totale** progressivo si trova in fondo all'editor e diventa
 **verde quando raggiunge esattamente il 100%** — ambra quando manca qualcosa, rosso quando si supera.
- **Remove** una riga con il relativo pulsante di eliminazione.

!!! tip "La regola del 100%"

    La dashboard normalizza le distribuzioni parziali, ma un 100% pulito produce gli anelli di allocazione più
    significativi. Se lo strumento è al 100% in un unico paese o settore, una singola riga al 100% è
    sia una scelta valida sia la più chiara.

*(Screenshot dei due editor di distribuzione — `assets/detail-classification` esiste già e mostra l'area; primi piani dedicati degli editor sono previsti per il prossimo aggiornamento della galleria.)*

## 🏷️ Un solo strumento, più codici

Lo stesso titolo può essere identificato da più di un codice. Quando accade, LibreFolio mantiene **un
solo asset** e archivia i codici aggiuntivi in **Other identifiers**, dove sono ricercabili e vengono
usati per riconoscere lo strumento nelle importazioni successive.

Quale codice inserire nel campo principale **ISIN** non è una questione di gusti:

!!! tip "Mantieni il codice quotato come ISIN principale"

    Un prezzo è il valore dell'ultimo scambio, quindi solo un codice realmente negoziabile ha un
    prezzo. Inserisci il codice negoziabile in **ISIN** e tutto il resto in **Other identifiers** —
    altrimenti nessun provider può prezzare l'asset.

### Titoli di Stato italiani retail (BTP Valore, BTP Più, BTP Italia)

Questi titoli vengono emessi con un ISIN e negoziati con un altro:

| Fase | Codice | A cosa serve |
|---|---|---|
| Sottoscrizione all'emissione | l'ISIN "CUM" | Dà diritto al **premio di fedeltà** se lo detieni fino alla scadenza. **Non negoziabile**, quindi nessun provider lo quota |
| Mercato secondario | un ISIN diverso | Liberamente negoziato e **quotato** — è questo ad avere un prezzo |

Per vendere prima della scadenza, il titolo viene convertito nel codice di mercato. In LibreFolio i due sono lo
stesso strumento, quindi:

1. Inserisci l'**ISIN di mercato** nel campo **ISIN**.
2. Inserisci l'**ISIN CUM** in **Other identifiers**.
3. Registra il **premio di fedeltà**, quando viene pagato, come una transazione **Interesse** su quell'asset,
 datata il giorno in cui lo ricevi.

Il passo 3 funziona anche dopo che il titolo è giunto a scadenza e l'asset è stato disattivato: un
asset disattivato resta selezionabile proprio perché possano essere inseriti l'ultima cedola, il rimborso e il
premio.

!!! note "Durante un'importazione la decisione ti viene chiesta, non imposta"

    Se un file del broker riporta il codice CUM e l'asset possiede già quello di mercato, l'importazione
    chiede quale dei due deve prevalere. Quello che non scegli viene aggiunto a **Other identifiers** —
    nulla viene scartato e l'importazione successiva riconosce il titolo da entrambi i codici.

    Quando lo stesso titolo compare in due file con codici diversi, il passo **Unify assets** della
    procedura guidata di importazione li raggruppa in un unico strumento prima che venga deciso qualsiasi altra cosa.

## 🧲 Unione di asset duplicati

Se lo stesso strumento è finito due volte nella tua libreria — un esito comune quando si importa un'obbligazione
una volta con il codice di sottoscrizione e un'altra con quello di mercato — puoi fondere l'uno nell'altro tramite
l'azione **Merge**, disponibile nell'elenco degli asset e nella pagina di dettaglio dell'asset.

L'operazione è **distruttiva**, quindi avviene in due passaggi espliciti:

1. **Scegli l'asset da conservare.** Quello da cui sei partito è quello che scomparirà; tu
 scegli il suo sopravvissuto dall'intero catalogo, inclusi gli asset disattivati — un titolo giunto a scadenza è
 esattamente il tipo di elemento che viene unito.
2. **Osserva cosa viene spostato, poi definisci l'identità.** LibreFolio esegue prima una simulazione e mostra i
 conteggi reali: quante transazioni, prezzi ed eventi verranno riassegnati e cosa succede al
 provider di prezzo. Quando entrambi gli asset hanno un valore per lo stesso identificatore, chiede quale
 deve prevalere; l'altro viene mantenuto in **Other identifiers**.

| Cosa viene spostato | Cosa succede |
|---|---|
| Transazioni | Riassegnate all'asset sopravvissuto |
| Storico dei prezzi | Riassegnato; se entrambi gli asset hanno un prezzo nello stesso giorno, vince quello del sopravvissuto |
| Eventi societari (dividendi, cedole) | Riassegnati; gli eventi identici vengono accorpati e le transazioni che vi fanno riferimento seguono |
| Assegnazione del provider | Spostata solo se il sopravvissuto non ne ha uno — altrimenti il sopravvissuto mantiene il proprio |
| Identificatori | **Uniti**, mai eliminati: tutto ciò che l'asset eliminato conosceva sopravvive come identificatore alternativo |

!!! warning "L'asset di origine viene eliminato"

    L'unione non può essere annullata dall'interfaccia. Leggi l'anteprima prima di confermare — è un
    conteggio esatto, non una stima.

!!! tip "Potrebbe esserti proposta un'unione durante un'importazione"

    Quando un'importazione trova **due** asset che rispondono allo stesso codice — la classica firma di un
    duplicato creato da un'importazione precedente — la procedura guidata mostra un avviso discreto con un pulsante
    **Merge**, proprio nel punto in cui puoi vederli entrambi affiancati. Le sole somiglianze di nome non vengono mai
    proposte: è normale che due fondi dello stesso emittente si assomiglino.

## 🔗 Correlati

- 📊 **[Pagina di dettaglio dell'asset](detail/index.md)** — Visualizza e analizza i dati dell'asset
- 🔌 **[Provider](providers/index.md)** — Provider di prezzo disponibili
