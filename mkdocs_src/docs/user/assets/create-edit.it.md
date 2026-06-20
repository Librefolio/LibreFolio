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

## 🔌 Assegnazione del Provider

Ogni asset può avere un unico provider di pricing assegnato. Consulta la sezione [Provider](providers/index.md) per i dettagli sui provider disponibili e sulla loro configurazione.

## 🛠️ Modifica di un Asset

Clicca sul pulsante **Edit** (✏️) nella [pagina di dettaglio](detail/index.md) per aprire la finestra modale dell'asset con tutti i campi precompilati. Tutti i campi sono modificabili, inclusa la configurazione del provider e le distribuzioni.

## 🔗 Correlati

- 📊 **[Pagina di Dettaglio Asset](detail/index.md)** — Visualizza e analizza i dati dell'asset
- 🔌 **[Provider](providers/index.md)** — Provider di pricing disponibili
