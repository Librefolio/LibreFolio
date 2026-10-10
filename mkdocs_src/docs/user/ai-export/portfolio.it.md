# 🧠 AI Export del portafoglio

Esporta l'intero portafoglio, così come lo mostra la dashboard, per chiedere a un'AI informazioni sulla sua struttura, sulla sua
performance, su un piano di investimento ricorrente o sulle tue minusvalenze fiscali. Le opzioni e come incollare sono nella
[Panoramica di AI Export](index.md).

---

## 📍 Dove trovarlo

Nella **Dashboard**, seleziona **AI Export** nella barra degli strumenti, accanto a **Aggiorna**. Si apre inizialmente su
**Piano di investimento ricorrente**.

L'esportazione segue la [Dashboard](../dashboard/index.md):

- i broker che **possiedi** con una quota superiore allo 0%, ristretti dal filtro broker quando è attivo;
  i broker condivisi con te come editor o visualizzatore sono esclusi;
- la valuta della dashboard, con l'ultimo giorno del suo intervallo di date come data di esportazione.

Il pulsante si attiva una volta che la dashboard ha caricato i tuoi broker, e resta disattivato se non ne possiedi nessuno
con una quota superiore allo 0%.

---

## 📤 Dati esportati

| Scelta | Cosa ottieni |
| :--- | :--- |
| **Panoramica e storico del portafoglio** | Posizioni, liquidità, allocazioni, performance, flussi, reddito, costi registrati, un riepilogo FIFO economico, un contesto di mercato compatto per asset e drawdown |
| **Storico degli asset del portafoglio** | Prezzi dettagliati, rendimenti, indicatori, stati ed eventi per ogni asset che possiedi, con copertura |

---

## 🎯 Analisi

| Analisi | Cosa fa l'AI |
| :--- | :--- |
| **Piano di investimento ricorrente** | Pianifica investimenti ricorrenti condizionali a partire dai tuoi dati, chiedendo solo ciò che manca |
| **Ribilanciamento del portafoglio** | Confronta la tua allocazione con gli obiettivi che fornisci e delinea percorsi di ribilanciamento condizionali |
| **Performance del portafoglio e driver di mercato** | Spiega il tuo risultato e ricerca driver di mercato con riferimenti temporali per ogni asset che possiedi: usa un'AI in grado di cercare sul web |
| **Strategie di compensazione delle minusvalenze** | Esplora come le minusvalenze fiscali disponibili o in scadenza potrebbero compensare le plusvalenze, usando i tuoi lotti FIFO |

??? note "📅 Piano di investimento ricorrente — cosa ti chiederà l'AI"

    L'AI parte dai tuoi dati e chiede solo ciò che cambia il piano: quanto puoi investire e
    con quale frequenza, il tuo obiettivo e orizzonte temporale, quanto calo puoi sopportare, e limiti pratici come
    liquidità, broker, ordini minimi o asset da evitare. Non indovina mai queste risposte, può
    abbozzare scenari condizionali nel frattempo, e confronta l'investire subito con l'investire
    per fasi.

??? note "🧾 Strategie di compensazione delle minusvalenze — tieni a portata di mano i tuoi dati fiscali"

    I lotti FIFO sono il calcolo economico di LibreFolio, non la tua posizione fiscale legale. Prima di confrontare
    i percorsi, l'AI chiede la tua residenza fiscale e il regime fiscale, il tipo di conto e il tuo inventario
    ufficiale delle minusvalenze fiscali (per esempio il *cassetto fiscale* italiano) con importi, categorie e
    date di scadenza. Non suggerisce mai un'operazione solo per motivi fiscali.

---

## 🔗 Correlati

- 🧠 **[Panoramica di AI Export](index.md)** — opzioni, come incollare e privacy
- 📊 **[Dashboard](../dashboard/index.md)** — l'ambito che questa esportazione segue
