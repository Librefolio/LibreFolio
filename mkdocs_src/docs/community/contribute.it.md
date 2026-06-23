# :heart: Supporta LibreFolio

LibreFolio è un progetto **open-source**, licenziato sotto AGPL-3.0. Il codice sorgente è liberamente disponibile e chiunque abbia le competenze e l'infrastruttura necessaria può installarlo ed eseguirlo indipendentemente — questa è la bellezza dell'open source.

Se utilizzi LibreFolio e lo trovi prezioso, apprezzeremmo molto il tuo supporto — sia esso tramite **codice**, **idee** o una **piccola donazione**. Ogni contributo alimenta la crescita del progetto.

---

## :coffee: Offrimi un caffè

Se LibreFolio ti aiuta a gestire meglio i tuoi investimenti, considera di supportare lo sviluppo con un caffè:

<a href="https://www.buymeacoffee.com/librefolio" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" alt="Buy Me a Coffee" style="height: 60px !important;width: 217px !important;" ></a>

Ogni donazione — non importa quanto piccola — aiuta a coprire gli strumenti di sviluppo, l'infrastruttura di test e motiva il miglioramento continuo.

---

## :rocket: Contributi ad alto impatto

Per noi, **una grande idea o un contributo al codice ha lo stesso valore di una donazione**. Ecco le aree in cui il tuo aiuto può fare la differenza maggiore:

### :electric_plug: Nuovi Plugin

LibreFolio utilizza un [Registry & Plugin System](../developer/architecture/patterns/registry_pattern.md) con auto-discovery. Aggiungere un nuovo plugin è uno dei contributi più impattanti che puoi offrire:

| Tipo | Guida | Cosa fa |
|------|-------|-------------|
| 📥 **BRIM** | [Guida Plugin BRIM](../developer/architecture/patterns/brim_plugin_guide.md) | Importa transazioni da un nuovo broker (CSV/Excel) |
| 📈 **Asset** | [Guida Plugin Asset](../developer/architecture/patterns/asset_plugin_guide.md) | Recupera i prezzi da una nuova fonte di dati |
| 💱 **FX** | [Guida Plugin FX](../developer/architecture/patterns/fx_plugin_guide.md) | Aggiunge un nuovo provider di tassi di cambio |
| 📊 **Chart Signals** | *Guida in arrivo* | Nuovi indicatori tecnici e overlay per i grafici (EMA, MACD, RSI, Bollinger…) |

* **Se non sei uno sviluppatore**: puoi richiederne l'implementazione compilando il nostro [Modulo di Richiesta Plugin](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml). Oltre ai dettagli della richiesta, è necessario fornire degli esempi reali e anonimizzati (es. file CSV o Excel) del report del tuo broker.
* **Se sei uno sviluppatore**: puoi procedere direttamente per conto tuo alla loro implementazione. Consulta la [Guida al Registry & Plugin System](../developer/architecture/patterns/registry_pattern.md) e le guide specifiche collegate nella tabella sopra per scoprire come creare i plugin.

### :art: Idee UI/UX

Miglioramenti estetici, suggerimenti per il layout, potenziamenti dell'accessibilità — se vedi qualcosa che potrebbe apparire o funzionare meglio, diccelo inviando una segnalazione tramite il nostro [Modulo di Suggerimenti UX/Idee](https://github.com/Librefolio/LibreFolio/issues/new?template=idea.yml) su GitHub.

### :bug: Segnalazione Bug

Trovare e segnalare chiaramente i problemi è incredibilmente utile. Apri una nuova segnalazione utilizzando il nostro [Modulo di Report Bug](https://github.com/Librefolio/LibreFolio/issues/new?template=bug_report.yml) su GitHub.

Il modulo ti guiderà nell'inserimento delle informazioni sul browser, del metodo di deploy e dei log di errore.

---

## :rocket: Richieste di Funzionalità

Proponi funzionalità specifiche con casi d'uso chiari compilando il nostro [Modulo di Richiesta Feature](https://github.com/Librefolio/LibreFolio/issues/new?template=feature_request.yml) su GitHub.

Ogni richiesta sarà valutata e presa in considerazione non appena ci sarà la capacità di svilupparla. Le richieste ben descritte con esempi concreti vengono prioritizzate più velocemente.

---

## :computer: Contribuire con il Codice

Se sei uno sviluppatore e vuoi contribuire direttamente:

1. Fai il **Fork** del [repository](https://github.com/Librefolio/LibreFolio)
2. **Crea un branch** per la tua funzionalità o correzione
3. **Sviluppa e testa** nel tuo repo
4. **Invia una Pull Request** con una descrizione chiara e il prefisso della parola chiave nel titolo:

| Parola chiave | Quando usarla |
|---------|------------|
| **`[FIX]`** | Correzioni di bug |
| **`[FEAT]`** | Nuove funzionalità o potenziamenti |
| **`[PLUGIN]`** | Nuovo plugin (BRIM, Asset, FX, segnale) |
| **`[DOCS]`** | Miglioramenti della documentazione |

!!! warning "Merge policy"

    Una PR sarà accettata **solo se tutti i test esistenti continuano a passare**. Se le tue modifiche richiedono aggiornamenti dei test, includili nella PR — è assolutamente normale e previsto.

Consulta il [Manuale dello Sviluppatore](../developer/index.md) per i dettagli sull'architettura, le convenzioni di codifica e le linee guida per i test.

---

## :star: Metti una Stella al Progetto

Un modo semplice ma potente per aiutare: **metti una stella al repository** su GitHub! Aumenta la visibilità e aiuta altri utenti a scoprire LibreFolio.

[:octicons-star-fill-24: Stella su GitHub](https://github.com/Librefolio/LibreFolio){ .md-button .md-button--primary }

---

## :globe_with_meridians: Prossimi Passi — LibreFolio Cloud

Per coloro che vogliono utilizzare LibreFolio ma non hanno il tempo, le competenze o l'infrastruttura per l'auto-hosting, stiamo pianificando una **piattaforma hosted** — **LibreFolio Cloud**. Offrirà tutte le stesse potenti funzionalità senza alcuna configurazione tecnica, oltre a future **analisi potenziate dall'IA** per aiutarti a prendere decisioni di investimento più intelligenti.

Per sostenere l'infrastruttura, la manutenzione e lo sviluppo continuo, la piattaforma cloud sarà offerta come **servizio in abbonamento** — i prezzi saranno determinati in seguito.

---

!!! tip "Grazie!"

    Ogni forma di supporto — codice, idee, segnalazioni di bug o donazioni — è profondamente apprezzata. Insieme possiamo costruire il miglior tracker di portafoglio self-hosted! :rocket:
