# 📅 Eventi dell'Asset

Gli eventi dell'asset rappresentano eventi che interessano l'asset a livello **globale**, non a livello di portafoglio. Sono distinti dalle [transazioni](../../../financial-theory/instruments/transaction-types/index.md), che tracciano ciò che accade nel portafoglio di un utente.

Per un approfondimento su ogni tipo di evento — inclusi l'impatto sul mercato, le formule e gli esempi pratici — consulta la sezione **[Asset Events (Financial Theory)](../../../financial-theory/instruments/asset-events/index.md)**.

---

## 📊 Tipi di Evento

| Tipo | Icona | Effetto sul Prezzo | Descrizione | Scopri di più |
|------|------|----------------|-------------|-----------|
| **Dividendo** | 💰 | Il prezzo diminuisce del valore dell'evento (ex-date) | Distribuzione di contanti da azioni o ETF | [📖](../../../financial-theory/instruments/asset-events/dividend.md) |
| **Interesse** | 📈 | Il prezzo diminuisce del valore dell'evento | Pagamento di interessi da strumento di debito o prestito | [📖](../../../financial-theory/instruments/asset-events/interest.md) |
| **Split** | ✂️ | Cambia la quantità, non il valore totale | Split azionario o di unità | [📖](../../../financial-theory/instruments/asset-events/split.md) |
| **Adeguamento del prezzo** | 📊 | Variazione algebrica (+/-) | Variazione di valore non monetaria: svalutazione, haircut, re-rating | [📖](../../../financial-theory/instruments/asset-events/price-adjustment.md) |
| **Regolamento a Scadenza** | 🏁 | Restituzione finale del capitale | L'asset raggiunge la scadenza — nessun ulteriore calcolo del prezzo | [📖](../../../financial-theory/instruments/asset-events/maturity-settlement.md) |

## 📈 Marcatori di Evento sul Grafico

Gli eventi appaiono come **marcatori colorati** sul [grafico dei prezzi](chart.md). Ogni tipo di evento ha un colore e un'icona distinti. Passa il mouse su un marcatore per vedere i dettagli dell'evento (data, tipo, valore, valuta).

## ⚙️ Origine degli Eventi

Gli eventi possono essere generati in due modi:

### 1. Generati dal Provider (automatici)

Alcuni provider producono eventi durante la sincronizzazione:

- **[Scheduled Investment](../providers/scheduled-investment.md)**: genera eventi INTEREST e PRICE_ADJUSTMENT dalla configurazione del programma di interessi
- **[Yahoo Finance](../providers/yahoo-finance.md)**: può produrre eventi DIVIDEND dai dati storici

Gli eventi generati dal provider hanno un `provider_assignment_id` e vengono aggiornati automaticamente durante la sincronizzazione (deduplicazione DELETE + INSERT su `asset_id, date, type`).

### 2. Creati dall'Utente (manuali)

Gli eventi possono anche essere aggiunti manualmente tramite la modale di modifica dell'asset. Gli eventi manuali non hanno un `provider_assignment_id` e non vengono mai eliminati automaticamente durante la sincronizzazione.

---

## 🧮 Come gli Eventi Influenzano il Calcolo del Prezzo

Per il provider **Scheduled Investment**, gli eventi sono parte integrante del calcolo del prezzo:

```
price(d) = initial_value + accrued_interest − Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)
```

Per gli asset con prezzi di mercato (Yahoo Finance, justETF), gli eventi sono informativi — spiegano i cali improvvisi di prezzo (date ex-dividend) ma non modificano direttamente il prezzo recuperato.

---

## 🔗 Correlati

- 📈 **[Grafico Interattivo](chart.md)** — Marcatori di evento sul grafico
- ✏️ **[Data Editor](data-editor.md)** — Gestione manuale degli eventi con importazione CSV
- 🧮 **[Scheduled Investment](../providers/scheduled-investment.md)** — Provider che genera eventi dai programmi di interessi
- 📚 **[Asset Events (Financial Theory)](../../../financial-theory/instruments/asset-events/index.md)** — Analisi dettagliata di ogni tipo di evento
- 💸 **[Tipi di Transazione (Teoria Finanziaria)](../../../financial-theory/instruments/transaction-types/index.md)** — Transazioni vs eventi
