# ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" } Interessi (Transazione)

Una **transazione di interesse** registra il reddito da interessi ricevuto da obbligazioni, conti di risparmio, prestiti P2P o altri strumenti a reddito fisso. Rappresenta l'impatto a livello di portafoglio di un [evento legato agli interessi](../asset-events/interest.md).

---

## 🔑 Proprietà Principali

| Proprietà | Dettaglio |
|----------|--------|
| **Codice** | `INTEREST` |
| **Effetto cassa** | ⬆️ Aumenta il saldo |
| **Effetto asset** | — (il capitale rimane invariato) |
| **Evento fiscale** | Sì (reddito imponibile) |

---

## 📊 Fonti di Interessi

| Fonte | Descrizione | Frequenza |
|--------|-------------|-----------|
| **Cedole obbligazionarie** | Pagamenti a tasso fisso o variabile | Semestrale / Annuale |
| **Interessi sui risparmi** | Interessi su depositi di liquidità | Mensile / Trimestrale |
| **Pagamenti prestiti P2P** | Quota interessi dei rimborsi del prestito | Mensile |
| **Rendimenti Crowdfunding** | Rendimenti a tasso fisso su progetti | Variabile |

---

## 💡 Quando Usarlo

Utilizza una transazione `INTEREST` quando la liquidità perviene sul tuo conto broker come reddito da interessi. Questo è distinto da:

- **Dividendo** — reddito da equity (azioni, ETF a distribuzione)
- **Regolamento a scadenza** — restituzione del capitale alla scadenza dell'obbligazione

!!! tip "Theory & formulas"

    Per la matematica della maturazione degli interessi (semplice vs composto, convenzioni di conteggio dei giorni, metriche di rendimento), vedi:

    - **[📈 Eventi di Interesse](../asset-events/interest.md)** — Meccanismi di maturazione e impatto sul prezzo
    - **[📅 Convenzioni di Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di interesse

---

## 🔗 Correlati

- 📈 **[Eventi di Interesse](../asset-events/interest.md)** — Meccanismi di maturazione e cedole
- 🏛️ **[Obbligazioni](../asset-types/bonds.md)** — Il principale asset che genera interessi
- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Misurazione del rendimento da reddito
- 📅 **[Convenzioni di Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di interesse
