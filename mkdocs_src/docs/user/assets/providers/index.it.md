# 🔌 Provider

LibreFolio supporta diversi provider di prezzi per recuperare automaticamente i prezzi attuali e i dati storici dei tuoi asset.

## 📊 Confronto tra Provider

| Provider | Prezzo Attuale | Storico | Ricerca | Identificatore | Note |
|----------|:---:|:---:|:---:|---|---|
| **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (es. `AAPL`, `VWCE.DE`) | Ideale per azioni, ETF, fondi comuni |
| **justETF** | ✅ | ✅ | ❌ | ISIN (es. `IE00BK5BQT80`) | ETF europei con dati dettagliati |
| **CSS Scraper** | ✅ | ❌ | ❌ | URL | Estrae dati di prezzo da qualsiasi pagina web |
| **Scheduled Investment** | ✅ | ✅ | ❌ | Generato automaticamente | Strumenti a reddito fisso con calendari di interessi |

## 🎯 Scegliere un Provider

- **Azioni & ETF**: Usa **Yahoo Finance** — copertura più ampia, supporta la ricerca
- **ETF Europei**: Usa **justETF** per dati più dettagliati sugli ETF europei
- **Obbligazioni su Borsa Italiana**: Usa **CSS Scraper** per estrarre i prezzi direttamente
- **Conti deposito / Depositi vincolati**: Usa **Scheduled Investment** con calendari dei tassi di interesse

## 📚 Dettagli dei Provider

- [📈 Yahoo Finance](yahoo-finance.md)
- [📊 justETF](justetf.md)
- [🔍 CSS Scraper](css-scraper.md) — guida dettagliata per il web scraping
- [🧮 Scheduled Investment](scheduled-investment.md)
