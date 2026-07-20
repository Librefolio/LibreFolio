# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividendi e Interessi ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" }

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-dividend" alt="Modulo Transazione — DIVIDENDO">
</div>

**Dividendi** e **interessi** rappresentano il rendimento generato dagli asset del tuo portafoglio. Sono pagamenti in contanti ricevuti senza vendere l'asset sottostante.

---

## 🔑 Proprietà Chiave

| Proprietà | Dividendo | Interesse |
|-----------|-----------|-----------|
| **Codice** | `DIVIDEND` | `INTEREST` |
| **Effetto sulla liquidità** | ⬆️ Aumenta il saldo | ⬆️ Aumenta il saldo |
| **Effetto sull'asset** | — (quantità invariata) | — (capitale invariato) |
| **Evento fiscale** | Sì (reddito imponibile) | Sì (reddito imponibile) |

---

## 💡 Quando Usarli

Utilizza queste transazioni quando il denaro arriva sul tuo conto broker come rendimento da un asset:

- **Dividendo**: Reddito da azioni (titoli azionari, ETF a distribuzione).
- **Interesse**: Reddito da strumenti a reddito fisso (obbligazioni, conti di risparmio, prestiti P2P, crowdfunding).

*Non utilizzare queste transazioni per la restituzione del capitale (es. rimborso a scadenza di un'obbligazione).*

---

## 💰 Dividendi in Dettaglio

### Evento vs Transazione

| Concetto | Evento Dividendo | Transazione Dividendo |
|----------|-----------------|----------------------|
| **Ambito** | Globale — influenza il prezzo dell'asset | Personale — influenza il tuo portafoglio |
| **Esempio** | "Apple ha dichiarato $0,25/azione" | "Ho ricevuto $12,50 per le mie 50 azioni" |
| **Registrato da** | Provider o manualmente (Editor Dati) | Report del broker (importazione BRIM) |
| **Impatto sul grafico** | Indicatore a diamante (◆) sul grafico dei prezzi | Non visibile sul grafico |

### Importo del Dividendo

L'importo ricevuto dipende dal numero di azioni possedute alla **data di registrazione**:

$$
\text{Dividendo Ricevuto} = \text{Azioni Possedute} \times \text{Dividendo per Azione}
$$

### Ritenuta d'Acconto

Molte giurisdizioni applicano una **ritenuta d'acconto** sui dividendi — specialmente per le azioni estere. L'imposta viene detratta alla fonte:

$$
\text{Dividendo Netto} = \text{Dividendo Lordo} \times (1 - \tau_{ritenuta})
$$

L'importo trattenuto viene tipicamente registrato come una transazione `TAX` separata in LibreFolio, mantenendo distinti il dividendo lordo e la detrazione dell'imposta per finalità di rendicontazione.

---

## 📈 Fonti di Interesse

| Fonte | Descrizione | Frequenza |
|-------|-------------|-----------|
| **Cedole obbligazionarie** | Pagamenti a tasso fisso o variabile | Semestrale / Annuale |
| **Interessi di risparmio** | Interessi su depositi in contante | Mensile / Trimestrale |
| **Pagamenti prestiti P2P** | Parte interessi dei rimborsi del prestito | Mensile |
| **Rendimenti crowdfunding** | Rendimenti a tasso fisso su progetti | Variabile |

!!! tip "Teoria e formule"

    Per la matematica della maturazione degli interessi (semplice vs composto, convenzioni sul conteggio dei giorni, metriche di rendimento), vedi:

    - **[📈 Eventi di Interesse](../asset-events/interest.md)** — Meccanismi di maturazione e impatto sul prezzo
    - **[📅 Convenzioni sul Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di interesse

---

## 🔗 Correlati

- 💰 **[Eventi di Dividendo](../asset-events/dividend.md)** — Come i dividendi influenzano i prezzi degli asset
- 📈 **[Eventi di Interesse](../asset-events/interest.md)** — Meccanismi di maturazione e cedola
- 🔬 **[Analisi dei Lotti FIFO](../../technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#income-allocation-across-lots)** — Come il reddito viene allocato proporzionalmente tra i lotti aperti
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Trattamento fiscale del rendimento
- 🏛️ **[Obbligazioni](../asset-types/bonds.md)** — Il principale asset portatore di interessi
- 📈 **[Azioni](../asset-types/stocks.md)** — La principale classe di asset che paga dividendi
