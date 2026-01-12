Perfetto Emanuele! Ecco un **riassunto completo** del progetto **LibreFolio**, suddiviso in:

1. 🎯 **Obiettivi del progetto**
2. 🧰 **Tecnologie e strumenti**
3. 🧠 **Logiche principali**
4. 📊 **Tipi di transazioni**
    - Tabella `transactions` (asset)
    - Tabella `cash_movements` (cassa)
    - Quando usarle e perché

---

## 🎯 1. Obiettivi del progetto

**LibreFolio** è un'applicazione **self-hosted**, **open source**, pensata per:

- Tenere traccia dei propri **investimenti finanziari** in modo **privato e personale**
- Supportare sia asset tradizionali (ETF, azioni, crypto) che **prestiti a rendimento programmato** (es. Recrowd)
- Calcolare performance, ROI, rendimenti, andamento storico
- Gestire **movimenti di cassa** associati alle transazioni
- Offrire una **interfaccia web** moderna e multilingua
- Essere **contenuta in un singolo container Docker**, facilmente distribuibile

---

## 🧰 2. Tecnologie e strumenti

### Backend

- **Python** con **FastAPI**
- **SQLModel** (SQLAlchemy 2.x) per ORM
- **SQLite** come DB locale
- **Alembic** per gestire le migrazioni dello schema
- **Pipenv** per la gestione degli ambienti
- **APScheduler** per job schedulati (fetch dati, backfill)
- **httpx** + **BeautifulSoup4** per scraping
- **yfinance** per dati di mercato
- **forex-python** o fetch da ECB per FX
- **Structlog** per logging strutturato

### Frontend

- **React + TypeScript + Vite**
- **Material UI (MUI)** per la UI
- **React Query** per il fetch dei dati
- **i18next** per la localizzazione (en, it, fr, es)

### Packaging

- **Docker** (multi-stage build) → immagine unica che serve FE e BE

---

## 🧠 3. Logiche principali

### Dati giornalieri

- **Un solo record al giorno** per ogni asset (`price_history`) e per ogni coppia FX (`fx_rates`)
- I job aggiornano il **dato del giorno corrente** (via upsert)
- Il job notturno fa **backfill dello storico** (idempotente)

### Plugin per asset

- Ogni asset può avere:
    - Un **plugin per il valore corrente**
    - Un **plugin per lo storico**
- Se un plugin è configurato per una funzione, **l’utente non può modificare manualmente** i dati relativi (via API/UI)

### Asset a rendimento programmato (loan)

- Valutati con `valuation_model = "SCHEDULED_YIELD"`
- Usano:
    - `face_value` (valore nominale per unità)
    - `interest_schedule` (fasce di rendimento nel tempo)
    - `late_interest` (mora dopo la scadenza)
- Il valore di mercato è calcolato come:
  ```
  unit_value = face_value + accrued_interest
  market_value = unit_value × quantità detenuta
  ```
- Gli interessi reali si registrano con transazioni `INTEREST`

### Analisi

- Calcolo **FIFO runtime** per le vendite
- Serie temporali:
    - **Invested**: somma dei cash out (BUY)
    - **Market**: valore di mercato giornaliero (prezzo × quantità)
- KPI: **Simple ROI**, **Duration-Weighted ROI (DW-ROI)**

---

## 📊 4. Tipi di transazioni

### 🔹 Tabella `transactions` (asset)

| Tipo             | Descrizione                                 | Effetto su asset | Effetto su cash          |
|------------------|---------------------------------------------|------------------|--------------------------|
| `BUY`            | Acquisto asset                              | ↑ quantità       | ↓ cash (BUY_SPEND)       
| `SELL`           | Vendita asset                               | ↓ quantità       | ↑ cash (SALE_PROCEEDS)   
| `DIVIDEND`       | Dividendo ricevuto                          | —                | ↑ cash (DIVIDEND_INCOME) 
| `INTEREST`       | Interesse ricevuto (prestiti)               | —                | ↑ cash (INTEREST_INCOME) 
| `TRANSFER_IN`    | Ricezione asset da altro broker             | ↑ quantità       | —                        
| `TRANSFER_OUT`   | Spostamento asset verso altro broker        | ↓ quantità       | —                        
| `ADD_HOLDING`    | Aggiunta asset senza acquisto (es. regalo)  | ↑ quantità       | —                        
| `REMOVE_HOLDING` | Rimozione asset senza vendita (es. perdita) | ↓ quantità       | —                        
| `FEE`            | Commissione standalone                      | —                | ↓ cash (FEE)             
| `TAX`            | Tassa standalone                            | —                | ↓ cash (TAX)             

> ⚠️ Le transazioni che **modificano la quantità** (BUY, SELL, ADD, REMOVE, TRANSFER) sono soggette a **oversell guard**: non puoi vendere più di quanto possiedi.

---

### 🔹 Tabella `cash_movements` (cassa)

| Tipo              | Descrizione                          | Effetto su cash |
|-------------------|--------------------------------------|-----------------|
| `DEPOSIT`         | Deposito fondi nel broker            | ↑ cash          
| `WITHDRAWAL`      | Prelievo fondi dal broker            | ↓ cash          
| `BUY_SPEND`       | Spesa per acquisto asset             | ↓ cash          
| `SALE_PROCEEDS`   | Incasso da vendita asset             | ↑ cash          
| `DIVIDEND_INCOME` | Incasso dividendi                    | ↑ cash          
| `INTEREST_INCOME` | Incasso interessi                    | ↑ cash          
| `FEE`             | Commissione standalone               | ↓ cash          
| `TAX`             | Tassa standalone                     | ↓ cash          
| `TRANSFER_IN`     | Ricezione fondi da altro broker      | ↑ cash          
| `TRANSFER_OUT`    | Spostamento fondi verso altro broker | ↓ cash          

> Ogni transazione asset che impatta il cash genera **automaticamente** un movimento cassa corrispondente.

---

## 🧩 Mapping eventi → transazioni

| Evento reale                 | Transazione asset              | Movimento cassa                |
|------------------------------|--------------------------------|--------------------------------|
| Acquisto ETF                 | `BUY`                          | `BUY_SPEND`                    
| Vendita ETF                  | `SELL`                         | `SALE_PROCEEDS`                
| Ricezione dividendo          | `DIVIDEND`                     | `DIVIDEND_INCOME`              
| Ricezione interesse prestito | `INTEREST`                     | `INTEREST_INCOME`              
| Rimborso prestito            | `SELL`                         | `SALE_PROCEEDS`                
| Spostamento asset tra broker | `TRANSFER_OUT` + `TRANSFER_IN` | —                              
| Spostamento fondi tra broker | —                              | `TRANSFER_OUT` + `TRANSFER_IN` 
| Airdrop / regalo             | `ADD_HOLDING`                  | —                              
| Perdita tecnica / delisting  | `REMOVE_HOLDING`               | —                              
| Canone mensile broker        | —                              | `FEE`                          
| Imposta di bollo             | —                              | `TAX`                          
| Deposito iniziale            | —                              | `DEPOSIT`                      
| Prelievo fondi               | —                              | `WITHDRAWAL`                   
