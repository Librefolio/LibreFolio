# ➕ Creazione e Modifica di Asset

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Modulo di Creazione Manuale" alt="Finestra di Creazione Manuale">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Modulo di Auto-Creazione Wizard di Importazione" alt="Crea Asset da Wizard">
</div>

## 🚀 Flussi di Creazione Asset

In LibreFolio, è possibile creare nuovi asset in due modi diversi:

=== "Creazione Manuale (con ricerca intelligente)"

    ```mermaid
    flowchart LR
        A[Inizio: Clicca '+ New Asset'] --> B[Digita Nome, ISIN o Ticker nella ricerca intelligente]
        B --> C{Corrispondenza Trovata?}
        C -->|Sì| D[Compilazione automatica dei dettagli da provider esterni]
        C -->|No| E[Inserimento manuale di nome, categoria e valuta]
        D --> F[Regola configurazione / Assegna provider di pricing]
        E --> F
        F --> G[Clicca 'Save']
        G --> H[Asset aggiunto alla libreria]
    ```

=== "Auto-Creazione tramite Importazione Broker"

    ```mermaid
    flowchart LR
        A[Inizio: Carica report CSV nel Wizard di Importazione] --> B[Analisi righe del report]
        B --> C{ID Asset riconosciuto?}
        C -->|Sì| D[Corrispondenza automatica con asset esistente]
        C -->|No| E[Segnala avviso ⚠️ e mostra il pulsante 'Create']
        E --> F[Clicca 'Create' per aprire la finestra modale precompilata]
        F --> G[Salva asset per risolvere il mapping]
        G --> D
        D --> H[Conferma tutte le transazioni]
    ```

## 🧪 Test della Configurazione del Provider

Dopo aver configurato un provider, clicca su **Test Configuration** per verificare che i dati di pricing possano essere recuperati. Il test controlla:

- **Prezzo Attuale**: recupera l'ultimo prezzo disponibile
- **Storico**: recupera lo storico dei prezzi (se supportato)

I risultati vengono visualizzati inline con i relativi tempi di esecuzione. Un avviso ⚠️ indica che l'operazione non è supportata da quel provider (ad esempio, lo scraper CSS non supporta lo storico).

## 🔎 Dettagli di Ricerca Intelligente

La ricerca intelligente interroga prima la ricerca di ciascun provider. Se un provider supportato non trova
nulla, LibreFolio può tentare una ricerca dei collegamenti web per la risoluzione delle pagine dei provider
in candidati asset. Per Borsa Italiana, ciò significa che un URL di dettaglio/fondo può diventare un asset
pronto per il salvataggio con i `provider_params` necessari per prezzare il fondo tramite il suo codice interno.

Per i fondi di Borsa Italiana, l'ISIN visibile identifica il fondo quando disponibile, ma il pricing utilizza il
codice fondo interno Borsa salvato nella configurazione del provider. Il NAV attuale viene utilizzato solo se datato
oggi; lo storico contiene un punto NAV alla sua data reale.

## 🔌 Assegnazione del Provider

Ogni asset può avere un unico provider di pricing assegnato. Consulta la sezione [Provider](providers/index.md) per i dettagli sui provider disponibili e sulla loro configurazione.

## 🛠️ Modifica di un Asset

Clicca sul pulsante **Edit** (✏️) nella [pagina di dettaglio](detail/index.md) per aprire la finestra modale dell'asset con tutti i campi precompilati. Tutti i campi sono modificabili, inclusa la configurazione del provider e le distribuzioni.

Il campo **Altri identificatori** è un elenco modificabile di identificatori alternativi. Le importazioni
e i provider possono aggiungere etichette del broker, codici tecnici o identificatori di fallback
lì; ogni valore rimane una voce distinta dell'elenco.

## 🏷️ Uno strumento, più codici

Lo stesso titolo può essere noto con più di un codice. In questi casi LibreFolio tiene **un solo
asset** e conserva i codici in più negli **Altri identificatori**, dove sono ricercabili e servono
a riconoscere lo strumento nelle importazioni successive.

Quale codice vada nel campo **ISIN** principale non è una questione di gusto:

!!! tip "Tieni come principale il codice quotato"

    Il prezzo è il valore dell'ultima compravendita, quindi solo un codice effettivamente
    negoziabile ha un prezzo. Metti il codice negoziabile in **ISIN** e tutto il resto negli
    **Altri identificatori** — altrimenti nessun provider potrà quotare l'asset.

### Titoli di Stato italiani a collocamento retail (BTP Valore, BTP Più, BTP Italia)

Questi titoli vengono emessi con un ISIN e negoziati con un altro:

| Fase | Codice | A cosa serve |
|---|---|---|
| Sottoscrizione all'emissione | l'ISIN "CUM" | Dà diritto al **premio fedeltà** se detieni fino a scadenza. **Non negoziabile**, quindi nessun provider lo quota |
| Mercato secondario | un ISIN diverso | Liberamente scambiabile e **quotato** — è quello che ha un prezzo |

Per vendere prima della scadenza il titolo viene convertito nel codice di mercato. In LibreFolio i
due sono lo stesso strumento, quindi:

1. Metti l'**ISIN di mercato** nel campo **ISIN**.
2. Metti l'**ISIN CUM** negli **Altri identificatori**.
3. Registra il **premio fedeltà**, quando viene pagato, come transazione di tipo **Interesse** su
   quell'asset, alla data in cui lo ricevi.

Il punto 3 funziona anche a titolo scaduto e asset disattivato: un asset disattivato resta
selezionabile proprio perché l'ultima cedola, il rimborso e il premio possano essere inseriti.

!!! note "Durante l'importazione ti viene chiesto, non imposto"

    Se un file del broker porta il codice CUM e l'asset ha già quello di mercato, l'importazione
    chiede quale dei due debba essere il principale. Quello che non scegli finisce negli **Altri
    identificatori** — non si perde nulla, e la prossima importazione riconosce il titolo da
    entrambi i codici.

    Se lo stesso titolo compare in due file con codici diversi, lo step **Unifica asset** della
    procedura di importazione li raggruppa in un unico strumento prima di ogni altra decisione.

## 🔗 Correlati

- 📊 **[Pagina di Dettaglio Asset](detail/index.md)** — Visualizza e analizza i dati dell'asset
- 🔌 **[Provider](providers/index.md)** — Provider di pricing disponibili
