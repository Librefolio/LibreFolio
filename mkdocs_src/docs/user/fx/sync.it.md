# 🔄 Sincronizzazione FX

Le coppie con un provider ottengono i loro tassi da fonti ufficiali di banche centrali. LibreFolio li
scarica quando aggiungi una coppia, ogni volta che lo richiedi e — se il tuo amministratore l'ha
attivato — secondo una pianificazione.

---

## 🔄 Sincronizza tutte le coppie

1. Nella [pagina FX](index.md), scegli il periodo nel selettore di date. Seleziona **Tutto** per l'intera
   cronologia.
2. Clicca su **Sincronizza tutto**. La finestra **Sincronizza tassi FX** elenca ogni coppia con un
   provider: le coppie con soli tassi manuali non hanno nulla da scaricare.
3. Clicca su **Avvia sincronizzazione**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Avanzamento sincronizzazione" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Lettura dei risultati

- Ogni riga mostra una coppia, il provider che ha risposto, **↓** i tassi scaricati e **Δ** i tassi
  nuovi o modificati.
- Una riga ambra indica che il provider non ha inviato tassi per il periodo; una riga rossa indica che
  la sincronizzazione non è riuscita. Passa il mouse sul messaggio per leggerlo per intero e clicca sul
  pulsante ↻ della riga per riprovare con quella coppia.
- Il riepilogo in basso mostra quante coppie sono state sincronizzate e i totali. **Riprova N non riuscite**
  esegue di nuovo ogni coppia non riuscita.
- Una cronologia lunga può richiedere più tempo: se la finestra segnala *Request timed out*,
  aumenta il suo **Timeout**, quindi clicca su **Riprova N non riuscite**.

---

## 🎯 Sincronizza una coppia

- Nella pagina FX, il pulsante **Sincronizza** della scheda di una coppia, o di una riga della tabella,
  scarica i tassi di quella coppia per il periodo selezionato. Un messaggio riporta il risultato.
- Nella [pagina di dettaglio](detail/index.md) della coppia, **Sincronizza** apre la finestra di
  sincronizzazione per la coppia e per qualsiasi coppia o asset con cui la confronti sul grafico.

**Sincronizza** è disattivato per le coppie con soli tassi manuali.

---

## ⚠️ Cosa cambia una sincronizzazione

- Le date del periodo già memorizzate assumono il valore del provider; le date mancanti vengono aggiunte.
- Le date al di fuori del periodo vengono lasciate invariate.
- Se il primo percorso di una coppia non riesce, LibreFolio prova il successivo: vedi
  [Configurazione provider](detail/provider.md).

!!! warning "Il provider ha l'ultima parola"

    Una sincronizzazione sovrascrive i tassi che hai modificato manualmente all'interno del suo periodo. Per mantenere i tuoi tassi, usa una coppia senza provider (solo tassi manuali).

??? tip "🕰️ Cronologia più vecchia mancante — quando il grafico di una coppia inizia più tardi del previsto"

    Una coppia che aggiungi con un provider scarica da sola l'intera cronologia. Se il grafico di una coppia più vecchia inizia più tardi della cronologia del provider, imposta il periodo nella pagina FX su **Tutto** e clicca una volta su **Sincronizza tutto**: LibreFolio scarica tutto ciò che i provider pubblicano, fino a oggi.

---

## 🕐 Sincronizzazione automatica

Quando il tuo amministratore attiva lo scheduler in background, LibreFolio aggiorna da solo i tassi recenti di
ogni coppia con un provider, agli orari che sceglie: vedi
[Scheduler dati di mercato](../../admin/settings.md#market-data-scheduler).

---

## 🔗 Correlati

- ➕ **[Aggiungere una coppia](add-pair.md)** — Percorsi diretti e a catena
- 🔌 **[Provider FX](providers/index.md)** — Le banche centrali da cui LibreFolio legge i tassi
- ⚙️ **[Configurazione provider](detail/provider.md)** — Percorsi, priorità e fallback di una coppia
- 🧑‍💻 Per sviluppatori: **[Configurazione e routing FX](../../developer/backend/fx/configuration.md)**
