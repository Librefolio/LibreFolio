# 🔌 Provider

LibreFolio supporta molteplici provider di prezzi per recuperare automaticamente i prezzi correnti e i dati storici dei tuoi asset.

## 📊 Confronto tra Provider

| Provider | Prezzo Corrente | Storico | Ricerca | Identificatore | Note |
|----------|:---:|:---:|:---:|---|---|
| **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (es. `AAPL`, `VWCE.DE`) | Ideale per azioni, ETF, fondi comuni |
| **justETF** | ✅ (EUR) | ✅ | ✅ | ISIN (es. `IE00BK5BQT80`) | ETF europei, multi-valuta (EUR/USD/CHF/GBP) |
| **CSS Scraper** | ✅ | ❌ | ❌ | URL | Estrae dati sui prezzi da qualsiasi pagina web |
| **Investimento programmato** | ✅ | ✅ | ❌ | Generato automaticamente | Strumenti a reddito fisso con piani di interessi |

## 🎯 Scegliere un Provider

- **Azioni & ETF**: Usa **Yahoo Finance** — copertura più ampia, supporta la ricerca
- **ETF Europei**: Usa **justETF** per dati più dettagliati sugli ETF europei
- **Obbligazioni su Borsa Italiana**: Usa **CSS Scraper** per fare lo scraping dei prezzi direttamente
- **Conti deposito / Depositi vincolati**: Usa **investimento programmato** con i calendari dei tassi di interesse

## 📚 Dettagli dei Provider

- [📈 Yahoo Finance](yahoo-finance.md)
- [📊 justETF](justetf.md)
- [🔍 CSS Scraper](css-scraper.md) — guida dettagliata per il web scraping
- [🧮 Investimento programmato](scheduled-investment.md)
