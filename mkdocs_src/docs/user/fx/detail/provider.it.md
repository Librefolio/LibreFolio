# 🔌 Configurazione del provider

Ogni coppia di valute in LibreFolio è supportata da uno o più **provider di dati** — banche centrali che forniscono i dati dei tassi di cambio. La configurazione del provider ti permette di visualizzare e modificare quali provider vengono utilizzati per una specifica coppia.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Configurazione provider" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 Come accedere

Fai clic sul pulsante **Provider** (⚙️) nella barra degli strumenti del grafico nella pagina **Dettaglio coppia**. Questo apre la modale di configurazione del provider che mostra la configurazione corrente del percorso.

---

## 📋 Cosa vedi

La modale mostra:

- 🛤️ **Percorso(i) corrente(i)** — Le fonti di dati attive per questa coppia, in ordine di priorità
- 🔀 **Tipo di percorso** — Se si tratta di un percorso **Diretto** (un singolo provider) o di un percorso **Catena** (multi‑salto attraverso una valuta intermedia)
- 🏛️ **Dettagli del provider** — Nome, icona e valuta di base di ogni provider nel percorso

---

## 🔧 Cambiare i provider

Puoi configurare **uno o più** provider di dati per ogni coppia. Più provider fungono da **catena di fallback** — se la fonte primaria fallisce, il sistema prova automaticamente la successiva.

Per modificare o aggiungere provider:

1. Apri la modale di configurazione del provider
2. **Rimuovi** il percorso corrente se necessario
3. **Aggiungi un nuovo percorso** — il sistema scoprirà i percorsi disponibili utilizzando lo stesso processo di [aggiunta di una nuova coppia](../add-pair.md)
4. **Riordina** i percorsi per impostare le priorità (trascinamento o pulsanti freccia)
5. Clicca **Salva** — la prossima sincronizzazione preleverà i dati dal provider disponibile con la priorità più alta

---

## 🔢 Priorità & Fallback

Quando sono configurati più percorsi per una coppia:

- I percorsi vengono provati **in ordine di priorità** (il primo = massima priorità)
- Se il provider principale fallisce (timeout, errore API), il sistema **esegue il fallback** automaticamente al percorso successivo
- Puoi **riordinare** i percorsi per cambiare le priorità

!!! example "Esempio di fallback"
    EUR/USD configurato con:

    1. **BCE** (primario) — Banca Centrale Europea
    2. **FED** (fallback) — Federal Reserve

    Se l'API della BCE è irraggiungibile durante la sincronizzazione, il sistema utilizza automaticamente la FED.

---

## 📚 Correlati

- ➕ **[Aggiunta di una coppia](../add-pair.md)** — Scoperta completa del percorso (diretto + percorsi a catena)
- 🔄 **[Sincronizzazione](../sync.md)** — Come la sincronizzazione utilizza i provider configurati
- 📋 **[Elenco dei provider FX](../../../developer/backend/fx/providers_list.md)** — Dettagli tecnici su ogni provider (BCE, FED, BOE, SNB)

!!! tip "🔗 Come vengono calcolati i percorsi a catena"
    Per l'algoritmo matematico dietro le catene di conversione multi‑salto, vedi [Algoritmo della catena FX](../../../developer/frontend/fx-chain-algorithm.md).
