# ⚙️ Impostazioni del Grafico

La finestra modale **Impostazioni del Grafico** personalizza l'aspetto del grafico e i segnali di sovrapposizione. La stessa finestra serve sia la pagina [Elenco FX](index.md) sia quella [Assets](../assets/index.md), con **impostazioni indipendenti per ambito** — la modifica delle impostazioni predefinite FX non tocca mai i grafici degli asset, e viceversa.

---

## 🔓 Accesso alle Impostazioni del Grafico

La finestra modale si apre dalle pagine di elenco, in due varianti:

- 🌐 **Globale** — il pulsante delle impostazioni (⚙️) nella barra degli strumenti della pagina di elenco. Queste impostazioni diventano le impostazioni predefinite per ogni grafico dell'ambito; applicarle sostituisce tutte le personalizzazioni per singola card (la finestra modale ti avvisa di questo).
- 🎯 **Locale** — il pulsante delle impostazioni (⚙️) su qualsiasi card di coppia o asset. Queste impostazioni prevalgono su quelle globali solo per quella card.

!!! note "Le pagine di dettaglio usano invece pannelli in linea"

    Nella [pagina di dettaglio della coppia](detail/index.md) (e nelle pagine di dettaglio degli asset) il pulsante ⚙️
    attiva/disattiva un **pannello estetico** in linea e il pulsante 📈 attiva/disattiva
    il **pannello dei segnali** in linea — stesse impostazioni, stessa archiviazione per singolo elemento, nessuna finestra modale.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Finestra modale Impostazioni del Grafico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Anteprima in Tempo Reale

La finestra modale mostra sempre un **grafico di anteprima** con un interruttore Abs/%, così vedi l'effetto di ogni modifica prima di applicarla:

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Finestra modale delle impostazioni del grafico con anteprima in tempo reale">
</div>

- 🌐 **Modalità globale** — l'anteprima disegna una curva demo sintetica. Gli indicatori backend non possono essere eseguiti nel browser, quindi la finestra modale chiede al server di calcolarli in tempo reale su quella curva: ciò che vedi corrisponde a ciò che i grafici reali visualizzeranno.
- 🎯 **Modalità locale** — l'anteprima usa i **dati di prezzo reali** della card. Gli indicatori backend mostrano l'ultima configurazione applicata; un banner ti ricorda di fare clic su Apply per aggiornarli.

---

## 🎛️ Impostazioni Disponibili

### 🎨 Aspetto

| Impostazione | Descrizione |
|---------|-------------|
| **Colori della Linea di Base** | Colora la linea di verde sopra / di rosso sotto la linea di base |
| **Riempimento Area** | Riempimento sfumato sotto la linea |
| **Linee della Griglia** | Griglia orizzontale tratteggiata |
| **Sfumatura dei Dati Obsoleti** | Sfuma i dati più vecchi verso lo sfondo |
| **Scala dell'Asse Y** | Automatica, Includi 0, o un intervallo min/max personalizzato |

### 📈 Segnali di Sovrapposizione

La finestra modale gestisce gli stessi segnali di sovrapposizione del [pannello Segnali](detail/signals.md) della pagina di dettaglio, aggiunti da tre menu a tendina di categoria:

- 🧮 **Indicatori Tecnici** — il catalogo dei plugin backend per l'ambito corrente: **9 indicatori compatibili con FX** qui, 22 nell'ambito Assets. Il menu a tendina è un albero con ricerca raggruppato per famiglia (trend, momentum, volatilità, …). La matematica alla base di ogni indicatore è descritta in [Indicatori Tecnici — Teoria Finanziaria](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Confronto Dati** — sovrapponi un'altra coppia FX configurata o un asset sullo stesso grafico.
- 📐 **Benchmark Sintetici** — curve di riferimento generate da parametri ([Lineare](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Composta](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md), [Onda Sinusoidale](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md)). Sono pura matematica — non panieri personalizzati e non dati di mercato.

Ogni segnale configurato diventa una card con parametri in linea, un link 📖 alla sua pagina di teoria e diagnostica per singolo segnale una volta calcolato.

---

## 💾 Persistenza

Le impostazioni del grafico vengono salvate localmente nel `localStorage` del tuo browser, separatamente per gli ambiti FX e Assets, con sovrascritture per singola card applicate sopra le impostazioni predefinite dell'ambito. Persistono tra le sessioni — anche dopo aver chiuso e riaperto il browser — e andranno perse solo se svuoti la cache/l'archiviazione del browser o se l'archiviazione scade (dipende dal browser, in genere da mesi ad anni).
