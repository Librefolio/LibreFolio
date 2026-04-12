# <img src="../../../static/icons/transactions/dividend.png" width="32" style="vertical-align: middle;" /> Dividendo (Transazione)

Una **transazione di dividendo** registra il pagamento in contanti ricevuto a fronte del possesso di un asset che distribuisce dividendi (azione o ETF a distribuzione). Rappresenta l'impatto a livello di portafoglio di un [evento di dividendo](../asset-events/dividend.md).

---

## 🔑 Proprietà Principali

| Proprietà | Dettaglio |
|----------|--------|
| **Codice** | `DIVIDEND` |
| **Effetto cassa** | ⬆️ Aumenta il saldo |
| **Effetto asset** | — (quantità invariata) |
| **Evento fiscale** | Sì (reddito imponibile nella maggior parte delle giurisdizioni) |

---

## 📊 Evento vs Transazione

| Concetto | Evento di Dividendo | Transazione di Dividendo |
|---------|---------------|---------------------|
| **Ambito** | Globale — influisce sul prezzo dell'asset | Personale — influisce sul tuo portafoglio |
| **Esempio** | "Apple ha dichiarato $0,25/azione" | "Ho ricevuto $12,50 dalle mie 50 azioni" |
| **Registrato da** | Provider o manuale (Data Editor) | Report del broker (importazione BRIM) |
| **Impatto grafico** | Marcatore a diamante (◆) sul grafico dei prezzi | Non visibile sul grafico |

---

## 📐 Importo del Dividendo

L'importo ricevuto dipende dal numero di azioni detenute alla **data di registrazione** (record date):

$$
\text{Dividendo Ricevuto} = \text{Azioni Detenute} \times \text{Dividendo per Azione}
$$

### 💰 Ritenuta Fiscale

Molte giurisdizioni applicano una ritenuta fiscale sui dividendi, specialmente per le azioni estere:

$$
\text{Dividendo Netto} = \text{Dividendo Lordo} \times (1 - \tau_{withholding})
$$

La tassa trattenuta viene registrata come una transazione `TAX` separata.

---

## 🔗 Correlati

- 💰 **[Eventi di Dividendo](../asset-events/dividend.md)** — Come i dividendi influiscono sui prezzi degli asset
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Trattamento fiscale dei dividendi
- 📈 **[Azioni](../asset-types/stocks.md)** — La principale classe di asset che distribuisce dividendi
