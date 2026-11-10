# ⚙️ Impostazioni grafico

La finestra **Impostazioni grafico** modifica l'aspetto dei grafici e quali overlay disegnano. Serve sia
l'[elenco FX](index.md) sia l'[elenco Asset](../assets/index.md), e ciascun elenco mantiene le proprie
impostazioni: modificare i grafici FX non tocca mai i grafici degli asset.

---

## 🔓 Aprire le impostazioni del grafico

- 🌐 **Per tutti i grafici** — fai clic su **Impostazioni** (⚙️) nella barra degli strumenti dell'elenco. La finestra si intitola
  **Impostazioni grafico**. Applicandole si sostituiscono le impostazioni personalizzate di ogni grafico dell'elenco, comprese le pagine
  di dettaglio, e la finestra ti avvisa di questo.
- 🎯 **Per un singolo grafico** — fai clic su ⚙️ in una scheda. La finestra si intitola **Impostazioni grafico (locale)** e
  le sue impostazioni si applicano solo a quel grafico.

!!! note "Le pagine di dettaglio usano pannelli in linea"

    In una [pagina di dettaglio della coppia](detail/index.md) (e in una pagina di dettaglio dell'asset), ⚙️ sul grafico apre
    le stesse impostazioni di aspetto in un pannello, e il pannello **Segnali** sopra il grafico contiene gli
    overlay. Sono le stesse impostazioni di quelle locali della scheda.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Finestra modale Impostazioni grafico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Anteprima prima di applicare

La finestra mostra un grafico di anteprima con un selettore di visualizzazione. È la vista salvata del grafico, e **Applica**
la salva: **Assoluto**, **%** o **Rendimento rolling**. È lo stesso grafico delle pagine di dettaglio della
[coppia](detail/index.md) e dell'[asset](../assets/detail/chart.md), solo più alto di quello di una
scheda: una linea (niente candele), senza la barra degli strumenti, i marcatori degli eventi o lo strumento di misura, e puoi
ingrandirlo con la rotella del mouse come nella pagina di dettaglio. Viene disegnato con l'aspetto e gli intervalli degli assi
che stai modificando, e un segnale di confronto mostra l'icona e il tipo del suo asset nel tooltip. I tuoi grafici
cambiano solo quando fai clic su **Applica**; **Annulla** chiede conferma prima di scartare le modifiche.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Finestra modale Impostazioni grafico con anteprima live">
</div>

- 🌐 **Per tutti i grafici**, l'anteprima disegna una curva dimostrativa. Il server calcola gli indicatori su di essa,
  così appaiono esattamente come saranno nei tuoi grafici reali.
- 🎯 **Per un singolo grafico**, l'anteprima usa i dati reali di quel grafico. Gli indicatori mostrano le ultime impostazioni
  applicate finché non fai clic su **Applica**, e un banner te lo ricorda.

Un segnale appare uguale nell'anteprima e sulla scheda, quindi ciò che vedi qui è ciò che la scheda disegna
dopo **Applica**.

### 🔁 Vista Rendimento rolling {: #rolling-return-view }

Su **Rendimento rolling** l'anteprima disegna il rendimento rolling del tasso o dell'asset, con i
rendimenti rolling dei suoi confronti. Per un singolo grafico usa i dati reali della scheda e, su un grafico FX,
le coppie FX confrontate su di esso; per tutti i grafici disegna una curva dimostrativa. Altri due controlli scelgono la finestra mobile: **1W**, **1M**, **3M**, **1Y** o un
intervallo personalizzato. Finché non ne scegli una, la finestra mobile è automatica: il preset più grande che si adatta al periodo
mostrato nell'elenco. L'elenco Segnali mostra solo i confronti disegnati da questa vista, con un'altra coppia FX su
un grafico FX e con un altro asset su un grafico di asset; gli indicatori tecnici e i benchmark restano salvati
ma sono nascosti finché non riporti l'anteprima su **Assoluto** o **%**.

---

## 🎨 Aspetto

| Impostazione | Cosa fa |
|---------|--------------|
| **Colori della linea di base** | Verde sopra, rosso sotto l'inizio del periodo, con una linea di base tratteggiata. Si applica alle schede negli elenchi, alle pagine di dettaglio e all'anteprima |
| **Riempimento area** | Gradiente sotto la linea |
| **Linee della griglia** | Griglia orizzontale tratteggiata |
| **Gradiente dati obsoleti** | Attenua i giorni senza un nuovo valore, che ripetono un valore precedente |

### 📏 Intervalli degli assi

**Scala asse Y** ha una riga per ogni asse sul grafico: l'asse principale (il tasso, o la percentuale
nella vista %) e una per ogni scala di indicatore, come l'**asse RSI**. Gli indicatori che condividono una
scala condividono una riga.

- **Auto** adatta i dati su quell'asse.
- **Includi 0** adatta i dati e mostra anche lo zero.
- **Personalizzato** usa **Min** e **Max** che digiti.

Le viste **Assoluto** e **%** mantengono intervalli separati: passa l'anteprima a **%** per impostare
quello percentuale.

---

## 📈 Segnali in overlay

Aggiungi overlay da tre menu a tendina, come nel [pannello Segnali](detail/signals.md) della pagina di dettaglio:

- 🧮 **Indicatori tecnici** — 10 indicatori funzionano sui tassi FX (i grafici degli asset ne offrono di più), raggruppati per
  famiglia con una casella di ricerca. La matematica è in
  [Indicatori tecnici — Teoria finanziaria](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Confronto dati** — un'altra coppia FX o un asset sullo stesso grafico. Su una scheda FX la linea di
  un asset è il suo prezzo nella valuta dell'asset, senza conversione di valuta, esattamente come la disegna la
  [pagina di dettaglio della coppia](detail/index.md): leggila nella vista **%**, dove parte dal proprio
  primo valore come il tasso. In **Assoluto** si trova sull'asse del tasso. L'elenco carica i prezzi giornalieri degli
  asset confrontati una sola volta per tutte le schede e non chiede nulla quando nessuna scheda confronta un asset. Nella
  finestra aperta per **tutti i grafici** un confronto con un asset non viene disegnato, perché la curva dimostrativa
  non ha un asset reale con cui confrontarsi (come nell'[elenco Asset](../assets/index.md)).
  Un asset viene scelto nello stesso pannello del confronto di rischio: una casella di ricerca, filtri **Tipo** e
  **Valuta**, con ogni riga che mostra l'icona, il nome, il tipo e la valuta dell'asset, e i benchmark
  elencati per primi; un clic sceglie e chiude. L'asset del grafico stesso è visualizzato in grigio, e uno già usato da
  un altro confronto porta un segno di avviso ma può comunque essere scelto.
- 📐 **Benchmark sintetici** — curve di riferimento costruite solo da parametri, non da dati di mercato:
  [Lineare](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md),
  [Composto](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) e
  [Onda sinusoidale](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

Ogni segnale diventa una scheda con i suoi parametri, un link 📖 alla sua pagina teorica e, una volta calcolato, un'icona
di diagnostica.

---

## 💾 Dove vengono salvate le impostazioni

- Le impostazioni grafico vengono salvate in **questo browser**, per il tuo utente, separatamente per gli elenchi FX e asset.
  Le impostazioni specifiche di un grafico hanno la precedenza su quelle del suo elenco.
- Non sono memorizzate sul server: un altro browser o dispositivo parte dai valori predefiniti, e
  la cancellazione dei dati del browser per questo sito le azzera.
- Il periodo selezionato non è un'impostazione del grafico: le pagine della stessa scheda del browser lo condividono.
