# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividendi e Interessi ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" }

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-dividend" alt="Transaction Form — DIVIDEND">
</div>

I **dividendi** e gli **interessi** rappresentano il rendimento generato dagli asset del tuo portafoglio. Si tratta di pagamenti in contanti ricevuti senza vendere l'asset sottostante.

---

## 🔑 Proprietà Principali

| Proprietà | Dividendo | Interesse |
|----------|----------|----------|
| **Codice** | `DIVIDEND` | `INTEREST` |
| **Effetto cassa** | ⬆️ Aumenta il saldo | ⬆️ Aumenta il saldo |
| **Effetto asset** | — (quantità invariata) | — (capitale invariato) |
| **Evento fiscale** | Sì (reddito imponibile) | Sì (reddito imponibile) |

---

## 💡 Quando Utilizzarli

Utilizza queste transazioni quando ricevi liquidità sul tuo conto broker come rendimento di un asset:

- **Dividendo**: Reddito da equity (azioni, ETF a distribuzione).
- **Interesse**: Reddito da strumenti a reddito fisso (obbligazioni, conti deposito, prestiti P2P, crowdfunding).

*Non utilizzare queste transazioni per il rimborso del capitale (ad es., liquidazione alla scadenza di un'obbligazione).*

---

## 💰 Dividendi nel Dettaglio

### Evento vs Transazione

| Concetto | Evento Dividendo | Transazione Dividendo |
|---------|---------------|---------------------|
| **Ambito** | Globale — influisce sul prezzo dell'asset | Personale — influisce sul tuo portafoglio |
| **Esempio** | "Apple ha dichiarato $0,25/azione" | "Ho ricevuto $12,50 per le mie 50 azioni" |
| **Registrato da** | Provider o manuale (Editor Dati) | Report del broker (importazione BRIM) |
| **Impatto grafico** | Marcatore a diamante (◆) sul grafico dei prezzi | Non visibile sul grafico |

### Importo del Dividendo

L'importo ricevuto dipende dal numero di azioni possedute alla **data di registrazione (record date)**:

$$
\text{Dividendo Ricevuto} = \text{Azioni Possedute} \times \text{Dividendo per Azione}
$$

### Ritenuta d'Acconto

Molte giurisdizioni applicano una **ritenuta d'acconto** (withholding tax) sui dividendi, specialmente per le azioni estere. La tassa viene detratta alla fonte:

$$
\text{Dividendo Netto} = \text{Dividendo Lordo} \times (1 - \tau_{ritenuta})
$$

L'importo trattenuto viene tipicamente registrato come una transazione `TAX` separata in LibreFolio, mantenendo distinti il dividendo lordo e la detrazione fiscale ai fini della reportistica.

---

## 📈 Fonti di Interesse

| Fonte | Descrizione | Frequenza |
|--------|-------------|-----------|
| **Cedole obbligazionarie** | Pagamenti a tasso fisso o variabile | Semestrale / Annuale |
| **Interessi conto deposito** | Interessi su depositi in contanti | Mensile / Trimestrale |
| **Pagamenti prestiti P2P** | Quota interessi dei rimborsi del prestito | Mensile |
| **Rendimenti crowdfunding** | Rendimenti a tasso fisso su progetti | Variabile |

!!! tip "Theory & formulas"

    Per la matematica dell'accumulo degli interessi (semplice vs composto, convenzioni di conteggio dei giorni, metriche di rendimento), consulta:

    - **[📈 Eventi Interesse](../asset-events/interest.md)** — Meccanismi di accumulo e impatto sul prezzo
    - **[📅 Convenzioni di Conteggio dei Giorni](../../fundamentals/day-count.md)** — Come vengono calcolati i periodi di interesse

---

## 🔗 Correlati

- 💰 **[Eventi Dividendo](../asset-events/dividend.md)** — Come i dividendi influenzano i prezzi degli asset
- 📈 **[Eventi Interesse](../asset-events/interest.md)** — Meccanismi di accumulo e cedole
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Trattamento fiscale dei rendimenti
- 🏛️ **[Obbligazioni](../asset-types/bonds.md)** — Il principale asset che genera interessi
- 📈 **[Azioni](../asset-types/stocks.md)** — La principale classe di asset che paga dividendi
