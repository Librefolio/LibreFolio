# Brainstorming: LibreFolio AI Agent & Risk Analysis Integration (Revised)

Questo documento aggiornato definisce le scelte tecnologiche e l'architettura concordata per l'integrazione AI in LibreFolio (Release 2.0.0).

---

## 1. Vision & Flusso dei Calcoli

L'assistente AI agirà in sinergia con i moduli core di LibreFolio:
* **Calcoli Complessi e Stabili (es. Monte Carlo, Markowitz):** Devono essere codificati all'interno di LibreFolio come funzionalità stabili (Python backend) ed essere esposti all'agente come **Tool MCP** specifici. L'interfaccia utente (UI) fornirà un cruscotto interattivo dedicato per permettere all'utente di giocherellare visivamente con i parametri.
* **Calcoli Spiccioli / Ad-hoc:** L'agente potrà scrivere codice Python autonomamente solo per piccoli calcoli estemporanei o logiche personalizzate non ancora implementate nativamente nel server.

---

## 2. Accesso ai Dati: Sicurezza & Integrità

Per proteggere l'integrità dei portafogli, stabiliamo la seguente politica di accesso ai dati per l'agente:
* **Scrittura (Inserimento/Modifica/Cancellazione):** L'agente **NON** può effettuare query SQL dirette o inserimenti grezzi. Deve obbligatoriamente passare per i service layer e gli endpoint FastAPI esistenti. Questo garantisce che tutte le validazioni di business logic, i calcoli sui lotti e i controlli di integrità siano sempre eseguiti.
* **Lettura:** L'agente può leggere i dati tramite i moduli di servizio interni del backend, garantendo performance ottimali e la flessibilità di estrarre report complessi.

---

## 3. Posizionamento dell'Harness AI: Backend (Consigliato)

Abbiamo analizzato dove far risiedere il runtime dell'agente (l'Harness che gestisce memoria, pianificazione cron, prompt e ciclo agentico). La scelta è di **implementare l'Harness sul Backend Python**.

### Confronto di Presenza dell'Harness

| Feature | Harness sul Backend (FastAPI / Python) | Harness sul Client (SvelteKit / Browser) |
| :--- | :--- | :--- |
| **Condivisione Sessioni** | **Sì.** Le chat e le memorie persistono nel DB e sono accessibili da qualsiasi dispositivo (Web, Mobile). | **No.** La cronologia rimane nel LocalStorage del browser del singolo dispositivo. |
| **Sicurezza delle API Key** | **Alta.** Le chiavi (OpenRouter, OpenAI) sono conservate in variabili d'ambiente protette sul server. | **Bassa.** Le chiavi devono essere inserite nel browser dell'utente, aumentando il rischio di esposizione. |
| **Esecuzione di Tool e File** | **Diretta e veloce.** L'agente chiama codice locale per leggere il db o avviare processi. | **Lenta.** Ogni tool require una richiesta di rete API round-trip dal browser al backend. |
| **Background / Cron Tasks** | **Sì.** Hermes Agent può eseguire compiti pianificati in background anche se il browser è chiuso. | **No.** L'applicazione web deve rimanere aperta per eseguire compiti pianificati. |
| **Latenza LLM** | Identica (la latenza di rete del server verso l'LLM domina ampiamente rispetto alla rete locale). | Leggermente inferiore solo per la fase di rendering (marginale). |

**Architettura Scelta:** L'agente (Harness basato su un'evoluzione di Hermes Agent) risiede nel backend Python. Il frontend SvelteKit funge da interfaccia di chat in streaming (via Server-Sent Events o WebSocket) e renderizza i grafici interattivi.

---

## 4. Scelte Tecnologiche Dettagliate

### A. Server MCP: FastMCP vs mcp-python-sdk
* **Scelta:** **FastMCP** (il framework ad alto livello di Anthropic).
* **Rapporto con FastAPI:** FastMCP offre un'API basata su decoratori (`@mcp.tool()`) identica a FastAPI. È asincrono, facilissimo da manutenere, riduce a zero il boilerplate JSON-RPC e può essere montato direttamente come endpoint SSE all'interno della nostra applicazione FastAPI esistente, evitando di creare processi sidecar separati.

### B. Ricerca Web: Playwright (Self-Hosted)
* **Scelta:** **Playwright** (Python).
* **Motivazione:** Rispetto a Firecrawl (che richiede un'infrastruttura Docker complessa con Redis ed API key), Playwright gira interamente in locale come dipendenza del backend. Offre:
  1. Controllo totale sul browser (evasione bot più flessibile).
  2. Possibilità di catturare **screenshot di pagine web**, permettendo a modelli multimodali (es. Claude 3.5 Sonnet, GPT-4o) di analizzare grafici ed andamenti visivi online.

### C. Gestione Chiavi e Modelli (LLM Engine)
L'Harness leggerà le chiavi API e l'endpoint tramite variabili d'ambiente (`.env`) impostate dall'utente.
* **Flessibilità totale:** Il backend fungerà da proxy verso l'endpoint configurato dall'utente (che si tratti di *OpenRouter*, *Doubleword*, *Ollama* locale o *OpenAI/Anthropic* ufficiali).
* **GitHub Copilot CLI:** L'integrazione con Copilot (es. tramite il provider `copilot-acp`) sarà delegata alla configurazione client dell'utente (BYOK/BYOEndpoint), senza necessità di codificare connettori ad-hoc complessi all'interno di LibreFolio.

---

## 5. Prossimi Passi (Roadmap di Sviluppo)

### Fase 1: Sviluppo Server MCP (FastMCP)
* Integrare `fastmcp` nel backend LibreFolio.
* Creare i tool di sola lettura: `get_portfolio_summary`, `list_assets`, `list_transactions`.
* Creare i tool di scrittura guidati da business logic: `add_transaction` (con validazione del payload).

### Fase 2: Configurazione AI nel Backend & UI Chat
* Implementare il proxy/connettore LLM nel backend Python per inoltrare i messaggi all'endpoint configurato.
* Creare l'interfaccia chat interattiva in SvelteKit.
* Aggiungere il tool per l'esecuzione di piccoli script Python (Code Interpreter).

### Fase 3: Tool Complessi & Visualizzazioni
* Integrare la simulazione Monte Carlo nel backend come endpoint stabile.
* Esporla all'agente come tool MCP.
* Sviluppare grafici dinamici in SvelteKit per permettere all'utente di variare interattivamente le proiezioni.
