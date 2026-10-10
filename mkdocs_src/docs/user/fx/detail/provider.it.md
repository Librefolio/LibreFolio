# 🔌 Configurazione dei provider

Ogni coppia di valute ottiene i suoi tassi da uno o più **percorsi di conversione**: una banca centrale che quota la coppia
direttamente, oppure una catena di conversioni. Qui vedi e modifichi i percorsi della coppia che stai
visualizzando.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Configurazione del provider" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 Come accedere

Nella pagina di dettaglio della coppia, clicca su **Provider** (🔧) nella barra degli strumenti, accanto a **Sincronizza**. Si apre la
finestra **Modifica provider della coppia**.

---

## 📋 Cosa vedi

Sotto **Percorsi di conversione**, ogni riga è un percorso, in ordine di priorità:

- le valute, con il provider di ogni passaggio tra esse — passa il mouse sull'icona di un provider per vederne
  nome e descrizione;
- il badge di priorità: **#1** viene usato per primo;
- ⚠️ quando un provider presenta un avviso sui dati, come i tassi mensili della SNB;
- 🗑️ per rimuovere il percorso.

---

## 🔧 Modificare i provider

1. Clicca su **Aggiungi percorso di conversione** e scegli un percorso sotto **Conversione diretta (1 passaggio)** oppure
   **Conversione a catena**. Digita nella casella di ricerca per filtrare per provider, valuta o paese.
2. Trascina le righe per impostarne la priorità (su un telefono, usa le frecce su e giù).
3. Clicca su **Salva configurazione**: la prossima sincronizzazione userà i nuovi percorsi.

??? note "🔗 Crea anche coppie intermedie — quando scegli un percorso a catena"

    Seleziona questa opzione per salvare ogni passaggio della catena come coppia a sé stante, con il suo provider, così da poterla
    sincronizzare e visualizzare da sola.

??? note "✍️ Nessun percorso rimasto — quando li rimuovi tutti"

    La coppia diventa manuale: **Sincronizza** è disabilitato e inserisci i tassi tu stesso nell'[editor dati](data-editor.md).

---

## 🔢 Priorità e fallback

Una sincronizzazione prova i percorsi dall'alto. Se uno fallisce — per esempio, la sua banca centrale non
risponde — si passa al successivo; la coppia fallisce solo quando falliscono tutti i percorsi. Con EUR/USD impostata su
**#1** ECB e **#2** FED, una sincronizzazione che non riesce a contattare l'ECB usa invece il tasso della FED.

---

## 📚 Voci correlate

- ➕ **[Aggiunta di una coppia](../add-pair.md)** — Scoperta completa dei percorsi (percorsi diretti + a catena)
- 🔄 **[Sincronizzazione](../sync.md)** — Come la sincronizzazione utilizza i provider configurati
- 🔌 **[Provider FX](../providers/index.md)** — Guida utente e dettagli su ciascun provider (ECB, FED, BOE, SNB)
- 🧮 **Per gli sviluppatori: [Algoritmo della catena FX](../../../developer/frontend/fx-chain-algorithm.md)** — Come vengono trovati e calcolati i percorsi a catena
