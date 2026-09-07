# 🧙 Come importare le transazioni

<style>
/* Corrections plugin table: plugin column keeps icon+name on one line */
.md-typeset details.warning table th:first-child,
.md-typeset details.warning table td:first-child { min-width: 9rem; white-space: nowrap; }
.md-typeset details.warning .md-typeset__table table td { vertical-align: middle; }
</style>

Scopri come usare il Broker Report Import Module (BRIM) per importare le tue transazioni passo dopo passo.

---

## 🚀 Guida passo-passo

1. Esporta un report delle transazioni dal tuo broker (di solito un file CSV — controlla il centro assistenza del tuo broker).
2. In LibreFolio, vai alla pagina **[Transazioni](../index.md)**.
3. Fai clic sul pulsante **Importa** (:material-file-upload:) nell'intestazione della pagina.
4. Si apre la **procedura guidata di importazione** — puoi trascinare il file del tuo estratto conto nel passaggio di caricamento.
5. Controlla l'anteprima — verifica che date, importi e nomi degli asset siano corretti.
6. Fai clic su **Importa N transazioni** — le righe selezionate finiscono nell'**editor in blocco** come nuove righe, dove puoi dare un'ultima occhiata (o continuare a modificarle) prima che **Salva tutto** le registri nel tuo portafoglio.

<div class="lf-screenshot-carousel" data-carousel="carousel-import-wizard" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="brokers" data-name="import-modal" data-title="📥 Quick Import Modal" alt="Quick Import Modal">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step1" data-title="🧙 Step 1: Upload Report File" alt="Wizard Step 1">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step2" data-title="⚙️ Step 2: Select Files &amp; Parser" alt="Wizard Step 2">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step3" data-title="🧠 Step 3: Analysis &amp; Parsing" alt="Wizard Step 3">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-step4-resolution" data-title="🗂️ Asset Resolution" alt="Asset Resolution">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-wizard-duplicate" data-title="⚠️ Duplicate Detection" alt="Duplicate Detection">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="brokers" data-name="import-bulk-staging" data-title="📦 Step 4: Review &amp; Import" alt="Review and Import">
</div>

!!! tip "Creazione al volo di broker e asset"

       Se il report importato contiene un conto broker o asset non ancora creati in LibreFolio, non devi uscire dal flusso di importazione! La procedura guidata ti accompagnerà nella creazione al volo dei **[Broker](../../brokers/index.md)** e degli **[Asset](../../assets/index.md)** mancanti, precompilando i dettagli dall'estratto conto.

!!! tip "Puoi anche usare la sezione File"

       La sezione **[File](../../files/index.md)** (scheda BRIM) ti consente di gestire centralmente i report dei broker caricati, reimportarli o eliminarli.

---

## 🧙 I passaggi della procedura guidata di importazione

La procedura guidata ha **quattro passaggi che vedi sempre** e **tre che compaiono solo quando i tuoi file
ne hanno davvero bisogno**. La barra di avanzamento mostra solo i passaggi pertinenti alla tua importazione, quindi un
report pulito con un singolo file rimane un flusso breve, mentre uno disordinato con più file riceve esattamente le domande
extra che merita — e nessun'altra.

| Passaggio | Sempre mostrato? | Compare quando |
| :--- | :--- | :--- |
| 1 · Carica il file del report | ✅ Sempre | — |
| 2 · Seleziona file e parser | ✅ Sempre | — |
| 3 · Analisi e parsing | ✅ Sempre | — |
| 🧬 Unifica asset | ⚪ Opzionale | Lo stesso titolo è stato trovato con più di un nome o codice |
| 🔧 Correzioni | ⚪ Opzionale | Il parser ha registrato righe che non è riuscito a comprendere appieno |
| 🧹 Duplicati | ⚪ Opzionale | Lo stesso movimento appare in due dei file che stai importando insieme |
| 4 · Revisione e importazione | ✅ Sempre | — |

!!! info "I passaggi opzionali vengono eseguiti in questo ordine per un motivo"

       Ciascuno si basa sulle risposte del precedente. I titoli vengono unificati **per primi**, così,
       quando in seguito associ uno strumento a una riga corretta, scegli da un elenco pulito
       invece che da tre copie della stessa obbligazione. Le correzioni arrivano **prima** del controllo
       dei duplicati, perché un acquisto che il parser ha potuto leggere solo come prelievo di contante verrebbe altrimenti
       confrontato con i prelievi di contante — perdendo un duplicato reale, o inventandone uno che non
       esiste.

### 🧙 Passaggio 1: Carica il file del report

Questo passaggio accetta report CSV o XLSX esportati dal tuo broker. Puoi selezionare i file manualmente oppure trascinarli direttamente nella procedura guidata. Assegna un broker a ciascun file, file per file oppure con il selettore globale — e se il broker non esiste ancora, puoi crearlo al volo da qui.

Il passaggio è **facoltativo**: i report caricati nelle sessioni precedenti sono già archiviati e puoi selezionarli nel passaggio successivo senza ricaricarli.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Wizard Step 1: Upload" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⚙️ Passaggio 2: Seleziona file e parser

Questo passaggio elenca i report archiviati per ciascun broker, raggruppati in pannelli comprimibili per broker, così puoi scegliere esattamente quali analizzare — inclusi i file caricati in una sessione precedente (i file che hai appena caricato sono preselezionati). Da questo passaggio i report possono essere visualizzati in anteprima o eliminati. Ogni file ha il suo parser: il sistema rileva automaticamente il formato del broker (ad es. Degiro, Directa, Interactive Brokers, Intesa Sanpaolo, Crédit Agricole) e puoi sovrascrivere la scelta per ogni file. Se carichi un foglio di calcolo generico, usa il parser **CSV generico** per mappare manualmente le tue colonne (data, tipo, quantità, asset, cassa netta) sui campi di LibreFolio.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Wizard Step 2: Parser Configuration" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧠 Passaggio 3: Analisi e parsing

Il sistema analizza i file, validando date, numeri e valute. Vedrai una barra di avanzamento che indica la velocità e lo stato dell'analisi. Al termine dell'analisi, eventuali avvisi o errori di parsing verranno riepilogati prima di continuare.

I riquadri di riepilogo in alto sono **consolidati**: al termine dell'analisi descrivono ciò che verrà effettivamente importato — le transazioni selezionate e i titoli distinti dopo l'unificazione — non le righe grezze dei singoli file; **Vedi tutto** apre il dettaglio aggregato. Se torni indietro e cambi la scelta del parser, usa **Rianalizza tutto** per ricalcolare i risultati.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Wizard Step 3: Analysis" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Al termine dell'analisi, la tabella mostra un riepilogo dell'elaborazione per ciascun file con le seguenti colonne statistiche contrassegnate da emoji:

| Emoji / Colonna | Nome della metrica | Significato e regole di compilazione |
| :--- | :--- | :--- |
| `📊` | **Transazioni** | Il numero totale di transazioni finanziarie lette e identificate all'interno del file. |
| `🏦` | **Asset identificati** | Il numero di strumenti finanziari (azioni, ETF, ecc.) trovati nelle transazioni analizzate. |
| `✗` | **Asset non risolti** | Il numero di strumenti nel file non trovati nel database di LibreFolio (contrassegnati in rosso se > 0, richiedono la mappatura nel passaggio 4). |
| `🔴` | **Problemi di validazione** | Errori formali rilevati nei dati (ad es., formati non validi, date errate, dati obbligatori mancanti). |
| `🔧` | **Azione richiesta (TODOs)** | Campi o attributi che richiedono attenzione (rossi se bloccanti, arancioni per azioni di livello avviso/informativo). Non sono necessariamente errori: indicano semplicemente dati mancanti che non possono essere estratti automaticamente dal solo estratto conto e che puoi compilare facilmente a mano nel modulo delle transazioni in blocco alla fine della procedura guidata. |
| `⚠️` | **Avvisi** | Notifiche generali o messaggi di avviso generati dal parser durante l'elaborazione. |

??? abstract "🧬 Unifica asset — compare quando lo stesso titolo è stato trovato con più di un nome o codice"

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-assets-step" alt="Import wizard — Unify Assets step with a proposed group">
    </div>

    **Quando lo vedrai.** Ogni volta che due o più strumenti letti dai tuoi file sembrano
    essere lo stesso titolo — perché condividono un ISIN, un ticker o un nome — oppure quando i tuoi file
    descrivono un'obbligazione con due codici diversi. Un'importazione con un solo file in cui ogni titolo è
    distinto non mostra mai questo passaggio.

    **Perché esiste.** Ogni file viene letto indipendentemente, quindi lo stesso BTP presente in un report delle posizioni
    *e* in un report dei movimenti arriva come due strumenti non correlati. Se lasciato così, diventa
    due asset duplicati nella tua libreria — e due voci dall'aspetto identico in ogni
    elenco successivo, dove metà delle tue righe verrebbero silenziosamente associate a metà dello strumento.

    **Cosa fai qui.** La procedura guidata propone un raggruppamento e tu lo confermi, lo modifichi o lo rifiuti.
    Ogni card è un titolo e il suo bordo ti dice chi ha deciso:

    | Bordo | Significato |
    | :--- | :--- |
    | 🟩 verde pieno | **Unificato** — il motore è certo (stesso ISIN, ticker o nome), oppure lo hai deciso tu |
    | 🟨 ambra tratteggiato | **Da confermare** — una somiglianza su cui il motore non agirà da solo |
    | ⬜ grigio semplice | **A sé stante** — nessuna decisione |

    - **Unisci o separa** con il menu `⋮` su ogni card, oppure trascinando una card sull'altra.
    - **Eleggi il codice principale** facendo clic su uno dei badge colorati: riceve una ⭐ e diventa
    l'identificatore con cui l'asset sarà conosciuto. I codici non eletti vengono mantenuti come identificatori
    alternativi, quindi nulla di ciò che i tuoi file conoscevano viene scartato.
    - **Rinomina** un gruppo con la matita. Un gruppo che corrisponde già a qualcosa nella tua libreria
    porta un badge **in archivio** e il nome della tua libreria ha la precedenza.
    - **Ripristina il raggruppamento automatico**, in alto, annulla ogni unione, separazione ed elezione del codice in
    un clic, se vuoi ricominciare da capo.

    !!! tip "È qui che si risolvono le obbligazioni a doppio codice"

        Le obbligazioni retail italiane (BTP Valore, BTP Più, BTP Italia) vengono sottoscritte con un ISIN e
        scambiate con un altro. Eleggi il codice **negoziabile** come principale — è l'unico
        che un provider di prezzi può quotare — e lascia il codice di sottoscrizione ("CUM") come
        alternativo. Consulta [Crea e modifica gli asset](../../assets/create-edit.md) per l'approfondimento completo.

??? warning "🔧 Correzioni — compare quando il parser ha registrato righe che non è riuscito a comprendere appieno"

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-fix-step" alt="Import wizard — Corrections step with flagged rows">
    </div>

    **Quando lo vedrai.** Quando il tuo report contiene righe che il plugin ha registrato ma non è riuscito
    a leggere completamente: un'operazione di cui il file semplicemente non riporta lo strumento o la quantità, oppure una
    commissione o un'imposta che non è riuscito ad associare ad alcun titolo. I report che vengono analizzati senza problemi saltano questo passaggio.

    Questo passaggio esiste solo se il plugin del broker **segnala le righe per la revisione** — un plugin che
    non emette mai queste segnalazioni non lo aprirà mai. I plugin che attualmente lo fanno:

    | Plugin | Segnalazioni che può generare |
    |--------|--------------------|
    | <img src="https://www.credit-agricole.it/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 4px;"> [Crédit Agricole](credit_agricole.md) | Righe con operazione+commissioni abbinate (offerte per il **frazionamento**), righe di cassa non collegabili a uno strumento, blocchi rilevanti per il rilevamento dei duplicati |

    Man mano che altri plugin impareranno a segnalare le righe, verranno elencati qui.

    **Perché esiste.** Un acquisto che il plugin ha potuto registrare solo come prelievo di contante — perché il
    file non forniva né una quantità né uno strumento — verrebbe confrontato con i prelievi
    di contante nel controllo dei duplicati. Un duplicato reale andrebbe perso, oppure ne verrebbe inventato uno
    immaginario. Correggere queste righe *prima* del confronto è l'unico momento in cui funziona.

    **Cosa fai qui.** Le righe sono raggruppate in base alla natura della questione, così risolvi casi simili
    insieme. Per ciascuna puoi:

    - **Correggerla** — scegli il tipo di transazione corretto e, dove applicabile, lo strumento
    e la quantità. Vengono offerti solo i tipi che hanno senso per quella riga; una commissione o un'imposta non ha
    un campo quantità e può legittimamente non avere **alcuno strumento** ("addebito broker").
    - **Frazionala** — quando una singola riga raggruppa un'operazione insieme alle sue commissioni o imposte.
    - **Mantienila come letta** — sei d'accordo con ciò che ha fatto il plugin. La riga diventa grigia e rimane
    nell'elenco, così puoi sempre vedere e rivedere ciò che hai deciso.
    - **Reimposta** una singola riga, oppure tutte le righe di un gruppo, e ricomincia.

    Un pulsante **mostrami la fonte** evidenzia ogni riga originale associata a un avviso nell'anteprima
    del file, così puoi controllare l'estratto conto stesso prima di decidere.

    !!! danger "Righe bloccanti"

        Le righe contrassegnate in **rosso** sono bloccanti: l'importazione non può essere salvata finché non le risolvi.
        Le righe ambra hanno solo scopo informativo — puoi lasciarle esattamente come sono.

??? note "🧹 Duplicati — compare quando lo stesso movimento è presente in due dei file che stai importando insieme"

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicates-step" alt="Import wizard — Duplicates step with a cross-file pair">
    </div>

    **Quando lo vedrai.** Solo quando due o più file in questa importazione si sovrappongono nel tempo e
    contengono lo stesso movimento. I duplicati rispetto a transazioni **già presenti nel tuo database** *non*
    aprono questo passaggio — arrivano semplicemente alla revisione finale già deselezionati.

    **Perché esiste.** Le esportazioni sovrapposte sono normali: scarichi un estratto conto annuale e poi uno
    trimestrale che ne ripete una parte. Deselezionare le voci gemelle una alla volta è noioso e facile da sbagliare,
    quindi la procedura guidata le raggruppa e ti permette di decidere una sola volta.

    **Cosa fai qui.**

    - **Ordina i tuoi file per priorità.** Trascinali nell'ordine che ritieni affidabile: la copia conservata per ogni
    gruppo proviene dal file con priorità più alta.
    - **Ricalcola** dopo il riordinamento: ogni scelta viene ricalcolata in base alla nuova priorità.
    - **Sovrascrivi singolarmente** nella tabella del gruppo: ogni riga ha una casella di controllo **Mantieni** e mostra
    da quale file proviene e se è la copia che viene conservata. **Reimposta i valori predefiniti** ripristina le
    scelte automatiche.
    - **Confronta fianco a fianco** quando due copie differiscono e vuoi vedere esattamente come prima di
    scegliere — la finestra di confronto evidenzia i campi che differiscono.

    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-nway-compare" alt="N-way compare modal with per-field differences highlighted">
    </div>

    Ogni gruppo è etichettato **Totale** (i file concordano su ogni dettaglio — una sovrapposizione pura) o
    **Parziale** (qualcosa differisce, quindi merita un'occhiata).

### 📦 Passaggio 4: Revisione e importazione

La revisione finale mostra ogni transazione da importare in una griglia simile a un foglio di calcolo, ed è qui
che ogni strumento viene finalmente associato alla tua libreria.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Review and Import grid" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La tabella mostra:

- **Data**: La data di esecuzione.
- **Tipo**: BUY, SELL, DIVIDEND, DEPOSIT, ecc.
- **Asset**: L'asset associato dalla tua libreria.
- **Quantità**: Il numero di unità/azioni.
- **Prezzo**: Il prezzo unitario.
- **Importo netto**: L'impatto complessivo sulla cassa.
- **Commissioni/Imposte**: Commissioni e imposte incluse.

#### 🗂️ Risoluzione degli asset

Un pannello comprimibile sopra la griglia elenca ogni strumento trovato nei tuoi file e ti permette di indicare
a cosa corrisponde nella tua libreria. Un unico campo di ricerca copre tutto, in due sezioni:

- **In questa importazione** — gli strumenti letti dai tuoi file, già unificati dal passaggio precedente.
 Uno già collegato alla tua libreria mostra un badge **in archivio** e appare solo qui,
 mai due volte.
- **In archivio** — tutto il resto nella tua libreria di asset.

I candidati con corrispondenza automatica sono fissati in cima al campo di ricerca con un badge di affidabilità
(**Exact** / **High** / **Medium** / **Low**), quindi la corrispondenza più probabile di solito è a un clic di distanza.

Se nessuna delle due sezioni ha ciò che ti serve, il pulsante **Crea «…»** in fondo all'elenco è
sempre visibile e contiene già ciò che hai digitato — non devi mai andarlo a cercare.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Asset resolution panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La matita ✏️ accanto a uno strumento associato apre l'editor completo dell'asset senza uscire dalla
procedura guidata, così puoi correggere un identificatore o un nome e tornare subito. Quando uno strumento corrisponde
a **due** asset già presenti nella tua libreria, la procedura guidata rileva l'ambiguità e offre un'azione di **unione**
per fondere l'uno nell'altro.

!!! question "«Qual è il codice principale?»"

       Quando il tuo report contiene un identificatore e l'asset — o il provider di prezzi — ne porta uno
       diverso dello stesso tipo, LibreFolio non sovrascrive nulla. Chiede quale deve avere la precedenza,
       mostrando da dove proviene ciascun valore: **dal provider**, **già salvato** o
       **dal report**. Quello che scegli diventa l'identificatore dell'asset; gli altri vengono mantenuti come
       identificatori alternativi, così la prossima importazione riconosce il titolo in entrambi i casi.

       Il valore del provider è preselezionato, perché è l'unico ad avere un feed di prezzi alle spalle.

#### ⛔ Data di apertura del broker

Se il broker di destinazione ha una data di apertura, la procedura guidata contrassegna con lo stato `Before opening` le righe la cui data è **strettamente precedente**
a tale data. Quelle righe vengono deselezionate e non possono essere importate; una riga nel
giorno di apertura rimane valida. Se la data è errata, un banner relativo al broker ti consente di **Modificare la data
del broker** manualmente o di **correggerla automaticamente** impostandola alla prima data di transazione trovata, quindi di ricontrollare/aggiornare affinché
la procedura guidata rivaluti ogni riga rispetto alla data aggiornata.

#### ⚠️ Avvisi sugli asset

Alcuni plugin associano avvisi informativi agli asset estratti. Ad esempio, Intesa Sanpaolo e
Crédit Agricole possono avvisare che un titolo potrebbe essere scaduto o rimborsato. Questi avvisi compaiono come
banner ambra quando crei o mappi l'asset; non bloccano l'importazione.

#### ⚠️ Duplicati rispetto al tuo database

Indipendentemente dal passaggio opzionale **Duplicati** — che confronta i file importati *tra loro* —
ogni riga viene anche confrontata con le transazioni già presenti nel tuo database, per tipo,
data, importo, quantità e descrizione. Queste non aprono un passaggio dedicato: vengono segnalate
proprio qui con un badge di stato.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Duplicate detection badges" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Badge UI | Livello di affidabilità | Criteri / Regole di corrispondenza |
| :--- | :--- | :--- |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Campi di base e descrizione corrispondenti, e asset risolto automaticamente (duplicato con elevata affidabilità). |
| <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Campi di base e descrizione corrispondenti, ma asset non risolto. |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Campi di base corrispondenti e asset risolto automaticamente (ma la descrizione differisce o è vuota). |
| <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Campi di base (tipo, data, quantità, importo) corrispondenti, ma asset non risolto. |
| <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ UNIQUE</span> | — | La transazione non ha record corrispondenti nel database e viene classificata come nuova (nessun duplicato rilevato). |
| <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ UNRESOLVED</span> | — | Il broker o lo strumento finanziario non è stato associato a un'entità esistente nel database (richiede la risoluzione nel passaggio 4 prima dell'importazione). |

Per impostazione predefinita, la procedura guidata deseleziona automaticamente i duplicati "Likely" per evitare doppie registrazioni, ma
puoi sovrascrivere questa scelta. Un banner sopra la griglia riepiloga il motivo per cui le righe sono deselezionate.

Altri due badge provengono da confronti *all'interno di questa importazione* piuttosto che rispetto al database:

| Badge UI | Significato |
| :--- | :--- |
| ⧉ **Duplicato nel batch** | Copia esatta di una riga ancora in attesa in questa importazione (o già accodata nell'editor in blocco) — deselezionata per impostazione predefinita. |
| ≈ **Possibile duplicato nel batch** | Come sopra, ma la descrizione differisce — rimane selezionata così puoi decidere. |

Fai clic su **Importa N transazioni** per passare le righe selezionate all'**editor in blocco** come nuove righe:
nulla viene ancora scritto nel registro. Dai un'ultima occhiata — o continua a modificarle — e poi
**Salva tutto** per registrarle nel tuo portafoglio.
