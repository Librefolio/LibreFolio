# 🎛️ Preferenze Utente

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="Preferenze Utente">
</div>

La scheda **Preferenze** controlla **come l'app appare e si comporta per te** — le modifiche si applicano solo al tuo account. La tua identità (nome utente, email, avatar, password) si trova invece nella scheda **[Profilo](profile.md)**.

| Impostazione | Categoria | Descrizione |
|---------|----------|-------------|
| **Lingua** | 🌍 Visualizzazione | Lingua dell'interfaccia — 🇬🇧 English, 🇮🇹 Italiano, 🇫🇷 Français, 🇪🇸 Español. Si applica non appena la salvi |
| **Valuta Predefinita** | 💰 Valuta | La tua valuta di base. La Dashboard, la pagina Broker e la pagina di ogni broker, e la scheda **Correlazione** della pagina Asset si aprono in questa valuta, e anche l'AI Export di una coppia FX la utilizza; una valuta che scegli nella Dashboard rimane per la sessione. Viene inoltre proposta quando crei qualcosa di nuovo — un asset, il primo saldo di cassa di un nuovo broker, un piano PAC. Questo menu elenca tutte le valute |
| **Tema** | 🎨 Aspetto | ☀️ Chiaro / 🌙 Scuro / 🖥️ Auto (segue il tuo sistema operativo) |

<style>
/* Keep the first two columns on one line (long setting names would wrap otherwise) */
article table:first-of-type th:nth-child(-n + 2),
article table:first-of-type td:nth-child(-n + 2) {
    white-space: nowrap;
    min-width: 11rem;
}
</style>

Scegli una categoria nella barra laterale — su un telefono, nel menu **Categoria** — per mostrare solo le sue impostazioni;
**Tutte le Impostazioni** mostra tutto.

!!! tip "Menu delle valute nella Dashboard e nelle pagine degli asset"

    I menu delle valute della **Dashboard** e di una pagina asset sono più brevi di quello di **Valuta Predefinita**: offrono solo le valute delle tue coppie FX, e **Crea forex…** in fondo alla lista aggiunge una coppia mancante. Vedi **[Dashboard](../dashboard/index.md)**.

## 💾 Salvataggio, Annulla, Ripristina

Ogni campo mantiene il proprio stato:

- Modifica un campo e questo mostra **Salva** e **Annulla**; l'intestazione offre **Salva Tutto** e **Annulla Tutto**
  per ogni campo modificato.
- Quando un valore salvato differisce dal **valore predefinito dell'istanza** (impostato dal tuo amministratore in
  [Impostazioni Globali](../../admin/settings.md)), appare un pulsante arancione **Ripristina Predefinito**: riporta
  il valore predefinito nel campo, pronto per essere salvato. **Ripristina Tutto ai Predefiniti** lo fa per ogni
  campo.

---

## 🧭 Primo utilizzo e guide {: #onboarding-and-guides }

La categoria **Primo utilizzo** elenca ogni guida, raggruppata per dove appare. Ognuna mostra il suo
stato — **In Attesa**, **Completata** o **Saltata** — e la versione che hai visto.
**Nuova versione da visualizzare** significa che un contenuto aggiornato è in attesa: la guida ricomincia la prossima volta che
la raggiungi.

| Gruppo | Guide |
|---|---|
| **Configurazione** | Configurazione iniziale |
| **Tour principale** | Tour rapido |
| **Transazioni** | Panoramica transazioni, Guida aggiungi transazione, Panoramica workspace bulk, Guida importazione |
| **Broker** | Panoramica broker, Guida broker, Guida dettagli broker |
| **FX** | Panoramica FX, Guida FX, Guida dettagli coppia FX |
| **Asset** | Panoramica asset, Guida asset, Guida dettagli asset |

### 🔁 Ripetere una guida

- **Configurazione iniziale** e **Tour rapido** — **Ripeti** le avvia subito.
- Qualsiasi altra guida — **Ripeti al prossimo avvio** la prepara: si avvia la prossima volta che apri la sua
  pagina, modulo, procedura guidata o workspace. **Annulla attivazione** la riporta indietro.
- **Ripeti tutto** prepara ogni guida e apre prima la pagina di Benvenuto.

Una ripetizione non cambia mai lo stato salvato, e le guide non cliccano né salvano per te. Un'eccezione: in
una ripetizione del Benvenuto, **Continua** salva la lingua, la valuta e l'immagine che hai scelto (**Esci dal tour**
esce senza salvare).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="onboarding-replay" alt="La categoria Primo utilizzo delle Preferenze: Primo utilizzo e guide con Ripeti tutto; Configurazione e Tour principale aperti, ogni guida con il suo badge Completata, Visualizzato v1 · corrente v1 e Ripeti; le altre aree richiuse con i loro conteggi">
</div>

??? info "🧩 Guida importazione e Panoramica workspace bulk — guide con passaggi"

    Espandi la riga di una delle due guide per vedere ogni passaggio con il suo stato. Un passaggio di importazione opzionale
    (**Unifica asset**, **Correzioni**, **Duplicati**, **Allinea con la banca**) rimane **In Attesa**
    finché un'importazione non lo richiede per la prima volta.

    In queste due guide, **✕** salta solo il passaggio corrente: il successivo inizia quando la procedura guidata o
    il workspace lo raggiunge. In una ripetizione, **✕** rimuove il passaggio dalla ripetizione senza cambiare
    il suo stato salvato.

??? note "💾 Dove viene conservata una ripetizione — solo in questo browser"

    Una ripetizione viene conservata in questo browser, per il tuo account: una ripetizione a metà sopravvive a un ricaricamento,
    alla chiusura del browser, o al logout e nuovo login. Non è condivisa con altri account,
    browser o dispositivi. Termina quando la finisci o la abbandoni, la annulli qui, o un aggiornamento porta una
    versione più recente della guida — e quindi si chiude anche nelle tue altre schede aperte.

Se la lista delle guide non può essere caricata, questa sezione mostra il suo pulsante **Riprova**.

---

## 🙈 Modalità privacy {: #privacy-mode }

La modalità privacy nasconde quanto possiedi mentre qualcun altro può vedere il tuo schermo — un collega che passa
davanti, uno schermo condiviso, un proiettore. Non è un campo di questa scheda: è il **pulsante a forma di occhio** nell'intestazione della pagina, in alto a destra accanto ai pulsanti del tema e della lingua.

- :material-eye-outline: **Nascondi importi** — gli importi sono visibili; clicca per nasconderli.
- :material-eye-off-outline: **Mostra importi** — la modalità privacy è attiva; clicca per mostrare di nuovo gli importi.

La modifica si applica subito alla pagina su cui ti trovi, senza ricaricamento, e la modalità privacy rimane attiva mentre
navighi tra le pagine e dopo un ricaricamento, finché non la disattivi. Da non confondere con l'icona a forma di occhio
di una **barra degli strumenti di una tabella**, che mostra o nasconde le colonne della tabella.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="privacy-masked" alt="La Dashboard con la modalità privacy attiva: il pulsante a forma di occhio barrato nell'intestazione, gli importi delle schede KPI e dei Saldi di Cassa mostrati come ••• con il loro segno e valuta, le percentuali ancora leggibili, e l'asse della Crescita del Portafoglio mascherato">
</div>

### 🔒 Cosa viene nascosto

La modalità privacy sostituisce il **numero** di un importo con `•••`. La valuta rimane sempre, e così
il segno, quindi un guadagno si legge ancora come un guadagno e una perdita come una perdita:

| Normalmente | Con la modalità privacy |
|---|---|
| `1,234.56 € 🇪🇺 EUR` | `••• € 🇪🇺 EUR` |
| `-1,234.56 € 🇪🇺 EUR` | `-••• € 🇪🇺 EUR` |
| `€1,234.56` o `1.234,56 €` | `€•••` o `••• €` |
| `—` (nessun valore) | `—` |

`•••` sono sempre gli stessi tre punti — anche il **K** o il **M** di una cifra abbreviata spariscono — quindi
non rivelano mai l'ordine di grandezza. Copre:

- **Dashboard**, **Broker** e i **pannelli di rischio** — i loro importi: le schede KPI, i Saldi di Cassa,
  i tooltip dell'Allocazione, le schede dei broker e la pagina di dettaglio del broker.
- **[Posizioni](../dashboard/positions.md)** e
  **[Analisi Lotti FIFO](../dashboard/positions.md#fifo-lots-analysis)** — ogni importo tranne i
  prezzi per unità, nelle tabelle, nel modale Dettaglio Lotto e nei grafici, e le quantità che possiedi
  (la colonna **Qty** delle Posizioni, le quantità dei lotti). Un lotto parzialmente chiuso mostra la sua quota aperta, per
  esempio `••• (60%)`.
- **Transazioni** — l'importo in denaro di ogni transazione.
- **[Allocatore PAC](../tools/pac-allocator/index.md#reading-the-result)** — ogni importo e
  quantità del risultato, e i limiti di acquisto di una route.

### 👀 Cosa rimane visibile

I numeri che non indicano **quanto possiedi** rimangono leggibili, così puoi continuare a lavorare:

- la **valuta** di ogni importo nascosto, le **percentuali** (rendimenti, pesi, quote di allocazione,
  rendimento sul costo) e i **tassi FX**;
- i **prezzi per unità** — prezzi di mercato, le colonne **Prezzo** e **Costo Medio** delle Posizioni, i
  prezzi dei lotti e le linee di prezzo del grafico PMC / Prezzo di Mercato;
- **conteggi, date e nomi**, e **eventi dell'asset** come un dividendo o uno split, che descrivono
  l'asset piuttosto che il tuo portafoglio;
- le **quantità nella lista Transazioni** — una scelta deliberata, anche se una quantità moltiplicata
  per il prezzo pubblico suggerisce la dimensione di un'operazione;
- i numeri all'interno dei **campi di modifica**, per esempio mentre aggiungi o modifichi una transazione: un campo che
  non puoi leggere è un campo che non puoi modificare.

### 🌐 Dove viene conservata l'impostazione

La modalità privacy appartiene a **questo browser**, non al tuo account: riguarda lo schermo che qualcuno potrebbe
stare guardando.

- È disattivata finché non la attivi. Il logout o il cambio di account la lascia così com'è, e non
  ti segue su un altro browser o dispositivo.
- Le altre schede di LibreFolio già aperte in questo browser recepiscono la modifica quando le ricarichi.
- Se il browser blocca l'archiviazione del sito, la modalità privacy funziona comunque in questa scheda, ma potrebbe essere di nuovo disattivata
  dopo un ricaricamento.

!!! warning "Cosa non copre la modalità privacy"

    - L'**[AI Export](../ai-export/index.md)** copia le cifre reali negli appunti anche mentre
      la modalità privacy è attiva. Rivedi il testo prima di condividerlo.
    - I **download e i file esportati** contengono le cifre reali.
    - Nasconde ciò che è **disegnato sullo schermo**. Le cifre raggiungono comunque il tuo browser, quindi non è
      una protezione contro qualcuno che può usare il tuo dispositivo o i suoi strumenti per sviluppatori.
    - Alcune cifre possono comunque essere **ricavate**: il segno distingue un guadagno da una perdita, e quando possiedi
      una singola unità di un asset, il suo prezzo visibile è il suo valore.

---

## 🔗 Correlati

- 👤 **[Profilo](profile.md)** — Nome utente, email, avatar, password, elimina account
- ⚙️ **[Panoramica Impostazioni](index.md)** — Riepilogo delle impostazioni generali
- ℹ️ **[Informazioni](about.md)** — Info versione, plugin e changelog
- 🛡️ **[Impostazioni Globali](../../admin/settings.md)** — Opzioni amministratore e scheduler
- 🛠️ **[Componenti delle impostazioni](../../developer/frontend/components/features/settings.md)** — Come sono costruite questa scheda e la sua lista Primo utilizzo (per sviluppatori)
