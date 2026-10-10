# ⚙️ Impostazioni grafico

La finestra **Impostazioni grafico** modifica l'aspetto dei grafici e le sovrapposizioni che
disegnano. Serve sia la [lista FX](index.md) sia la [lista Asset](../assets/index.md), e ciascuna
lista mantiene le proprie impostazioni: modificare i grafici FX non tocca mai i grafici degli asset.

---

## 🔓 Aprire le impostazioni grafico

- 🌐 **Per tutti i grafici** — fai clic su **Impostazioni** (⚙️) nella barra degli strumenti della
  lista. La finestra si intitola **Impostazioni grafico**. Applicandola si sostituiscono le
  impostazioni personalizzate di ogni grafico della lista, comprese le pagine di dettaglio, e la
  finestra te lo segnala.
- 🎯 **Per un singolo grafico** — fai clic su ⚙️ su una scheda. La finestra si intitola
  **Impostazioni grafico (Locali)**, e le sue impostazioni si applicano solo a quel grafico.

!!! note "Le pagine di dettaglio usano pannelli inline"

    In una [pagina di dettaglio di una coppia](detail/index.md) (e in una pagina di dettaglio di un
    asset), ⚙️ sul grafico apre le stesse impostazioni di aspetto in un pannello, e il pannello
    **Segnali** sopra il grafico contiene le sovrapposizioni. Sono le stesse impostazioni di quelle
    locali della scheda.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Modale delle impostazioni grafico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Anteprima prima di applicare

La finestra mostra un grafico di anteprima con il proprio interruttore **Abs** / **%**. I tuoi
grafici cambiano solo quando fai clic su **Applica**; **Annulla** chiede conferma prima di scartare
le modifiche.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Modale delle impostazioni grafico con l'anteprima dal vivo">
</div>

- 🌐 **Per tutti i grafici**, l'anteprima disegna una curva dimostrativa. Il server calcola su di
  essa gli indicatori, così appaiono esattamente come appariranno sui tuoi grafici reali.
- 🎯 **Per un singolo grafico**, l'anteprima usa i dati reali di quel grafico. Gli indicatori
  mostrano le ultime impostazioni applicate finché non fai clic su **Applica**, e un banner te lo
  ricorda.

---

## 🎨 Aspetto

| Impostazione | Cosa fa |
|---------|--------------|
| **Colori della linea di base** | Verde sopra, rosso sotto l'inizio del periodo |
| **Riempimento dell'area** | Gradiente sotto la linea |
| **Linee della griglia** | Griglia orizzontale tratteggiata |
| **Gradiente obsoleto** | Atenua i giorni senza un nuovo valore, che ripetono uno precedente |

### 📏 Intervalli degli assi

**Scala dell'asse Y** ha una riga per ogni asse del grafico: l'asse principale (il tasso, o la
percentuale nella vista %) e una per ogni scala di indicatore, come l'**asse RSI**. Gli indicatori
che condividono una scala condividono una riga.

- **Auto** adatta i dati su quell'asse.
- **Includi 0** adatta i dati e mostra anche lo zero.
- **Personalizzato** usa i valori **Min** e **Max** che digiti.

Le viste **Abs** e **%** mantengono intervalli separati: passa l'anteprima a **%** per impostare
quello percentuale.

---

## 📈 Segnali di sovrapposizione

Aggiungi sovrapposizioni da tre menu a tendina, come nel [pannello Segnali](detail/signals.md) della
pagina di dettaglio:

- 🧮 **Indicatori tecnici** — 9 indicatori funzionano sui tassi FX (i grafici degli asset ne offrono
  di più), raggruppati per famiglia con una casella di ricerca. La matematica è in
  [Indicatori tecnici — Teoria finanziaria](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Confronto dati** — un'altra coppia FX o un asset sullo stesso grafico.
- 📐 **Benchmark sintetici** — curve di riferimento costruite solo da parametri, non da dati di
  mercato: [Lineare](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md),
  [Composto](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) e
  [Onda sinusoidale](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

Ogni segnale diventa una scheda con i suoi parametri, un link 📖 alla sua pagina teorica e, una
volta calcolato, un'icona di diagnostica.

---

## 💾 Dove vengono salvate le impostazioni

- Le impostazioni grafico sono salvate in **questo browser**, per il tuo utente, separatamente per
  le liste FX e asset. Le impostazioni proprie di un grafico si sovrappongono a quelle della sua
  lista.
- Non sono memorizzate sul server: un altro browser o dispositivo parte dai valori predefiniti, e
  cancellare i dati del browser di questo sito le ripristina.
- Il periodo selezionato non è un'impostazione del grafico: le pagine della stessa scheda del
  browser lo condividono.
