# <img src="../../../static/icons/asset-types/other.png" width="32" style="vertical-align: middle;" /> Altro

Il tipo di asset **Altro** è una categoria generica per qualsiasi classe di attività non coperta dai tipi standard. Offre la massima flessibilità per il monitoraggio di investimenti non tradizionali.

---

## 🔑 Caratteristiche Principali

| Proprietà | Dettaglio |
|----------|--------|
| **Codice in LibreFolio** | `OTHER` |
| **Prezzi** | Inserimento manuale o qualsiasi provider compatibile |
| **Valuta** | Qualsiasi valuta ISO 4217 |
| **Rendimento** | Dipende dall'asset specifico |
| **Provider tipici** | Manual, CSS Scraper |

---

## 📊 Esempi di Casi d'Uso

| Asset | Descrizione |
|-------|-------------|
| **Arte e Collezionabili** | Quadri, vini, monete rare — valutati tramite perizie |
| **Private Equity** | Quote di società non quotate |
| **Venture Capital** | Investimenti in startup in fase iniziale |
| **Orologi e Gioielli** | Beni di lusso detenuti come investimento |
| **Nomi di Dominio** | Asset digitali con valore di rivendita |
| **Crediti di Carbonio** | Certificati di compensazione ambientale |

---

## 🔧 Monitoraggio in LibreFolio

Per gli asset senza un feed di prezzi pubblico:

1. Utilizza il provider **Manual** e inserisci i prezzi tramite il [Data Editor](../../../user/assets/detail/data-editor.md)
2. Oppure utilizza il provider **CSS Scraper** per estrarre i prezzi da un sito web
3. Registra le transazioni di acquisto/vendita come di consueto tramite importazioni da broker

---

## 🔗 Correlati

- 📊 **[Panoramica dei tipi di asset](index.md)** — Tutte le classi di asset supportate
- ✏️ **[Data Editor](../../../user/assets/detail/data-editor.md)** — Inserimento manuale dei prezzi
- 🌐 **[CSS Scraper](../../../user/assets/providers/css-scraper.md)** — Estrazione prezzi da qualsiasi pagina web
