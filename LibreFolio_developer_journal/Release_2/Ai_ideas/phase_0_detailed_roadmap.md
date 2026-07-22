# Roadmap Dettagliata: Fase 0 (Preparazione Backend & Motore Finanziario)

Questa roadmap definisce nel dettaglio gli step operativi della **Fase 0** (e 0.1), necessaria per preparare l'infrastruttura di LibreFolio ad accogliere l'intelligenza artificiale (Fase 1 e successive). Lo scopo è consolidare la logica di calcolo nel backend e introdurre nuove primitive di analisi.

---

## 1. Migrazione dei Segnali Tecnici al Backend

Lo spostamento del calcolo degli indicatori (EMA, RSI, MACD, Bollinger Bands) dal frontend (TypeScript) al backend (Python).

*   **Risoluzione Warm-up (Dati "Scarichi"):** Implementazione di una finestra di pre-fetching (es. estrarre 1 anno + 100 giorni storici aggiuntivi dal DB) per permettere alle medie mobili di stabilizzarsi prima della data di inizio visualizzazione. Il frontend riceverà l'array già "tagliato" (sliced) alla data corretta ma con i valori tecnici perfetti fin dal primo giorno.
*   **Potenziamento API:** Estensione dell'endpoint `POST /api/v1/assets/prices/query` per supportare un payload in cui il frontend richiede la lista di segnali desiderati (es. `["MACD", "EMA_50"]`).
*   **Architettura a Plugin:** Creazione di una classe Python `SignalPlugin` per permettere l'aggiunta modulare di nuovi indicatori matematici nel backend.

---

## 2. Integrazione Riskfolio-Lib (Motore di Rischio e Monte Carlo)

Integrazione della libreria `Riskfolio-Lib` per dotare il backend di funzionalità analitiche di livello istituzionale.

*   **Metriche Esposte:** Sviluppo di servizi API per restituire i calcoli di: Value at Risk (VaR), Max Drawdown, Sharpe/Sortino Ratios, Matrice di Correlazione e Simulazioni Monte Carlo (tramite Moto Browniano Geometrico).
*   **Posizionamento Logico nella UI (Frontend):**
    *   **Monte Carlo:** Limitato alla pagina `Asset Detail` (creando magari una nuova sub-tab "Proiezioni" o "Risk"), in quanto genera simulazioni specifiche per asset o per la composizione mirata.
    *   **Matrice di Correlazione:** Da inserire in `Global Asset`, `Dashboard` o `Broker Detail`, per mostrare all'utente come gli asset del portafoglio (o di un singolo broker) si muovono l'uno rispetto all'altro.
    *   **Metriche Base (Drawdown, Sharpe):** Nelle summary card dell'Asset Detail o in tabelle dedicate all'analisi delle performance.

---

## 3. Gestione Stati Asset (Watchlist)

Estensione del concetto di asset "Attivo" per permettere analisi ad ampio respiro (soprattutto per futuri algoritmi di ottimizzazione e suggerimenti IA).

*   **Database:** Modifica del modello `Asset`. 
    *   *Opzione A:* Convertire la colonna booleana `active` in un Enum (es. `AssetStatus: ACTIVE, INACTIVE, WATCHLIST`).
    *   *Opzione B:* Mantenere `active` (che guida lo scheduler per scaricare i prezzi giornalieri) e aggiungere una colonna enum `watch_type` / `portfolio_state`. L'opzione B è preferibile: un asset in Watchlist deve comunque avere `active=True` affinché lo scheduler ne aggiorni i prezzi, ma non deve essere considerato nel Net Worth totale dell'utente.
*   **Frontend UI:**
    *   Inclusione di un selettore/badge per marcare un asset come "In Watchlist" durante la creazione o modifica.
    *   Nuovi filtri nella tabella "Assets" (Tutti | In Portafoglio | Watchlist | Venduti).
    *   I grafici di portafoglio globale ignoreranno automaticamente gli asset in Watchlist.

---

## 4. Grafico di Rendimento Rolling a N Periodi (da TODO Futuri)

Aggiunta di un nuovo strumento visivo per analizzare la persistenza del rendimento di un asset nel tempo.

*   **Logica Matematica:** Mostrare il guadagno/perdita percentuale che si sarebbe ottenuto comprando esattamente N giorni (o anni) fa e vendendo nel giorno plottato sul grafico.
*   **Backend:** Aggiunta del calcolo del rendimento rolling (tramite `.pct_change(periods=N)` di Pandas) all'interno dei dati esportati.
*   **Frontend UI:**
    *   Creazione di un **2° Tab** (es. "Performance Rolling") nel blocco grafico della pagina `Asset Detail`.
    *   Aggiunta di un input/slider per permettere all'utente di variare il parametro N in modo reattivo.
    *   Supporto nativo per gli "asset di comparazione": il grafico mostrerà anche il rendimento rolling dell'asset di benchmark (es. S&P500) per capire chi batte chi con coerenza temporale.
    *   Supporto per il sistema di aggregazione nel grafico già sviluppato per gli altri grafici 2d

---

→ Piano migrazione segnali: [plan-phase00SignalsBackendMigration.prompt.md](../Phase_0/plan-phase00SignalsBackendMigration.prompt.md)
