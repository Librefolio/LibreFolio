# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividendo (Transazione)

Una **transazione di dividendo** registra il pagamento in contanti ricevuto a fronte del possesso di un asset che distribuisce dividendi (azioni o ETF a distribuzione). Rappresenta l'impatto a livello di portafoglio di un [evento di dividendo](../asset-events/dividend.md).

---

## 🔑 Proprietà Chiave

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
| **Registrato da** | Provider o manuale (editor dati) | Report del broker (importazione BRIM) |
| **Impatto grafico** | Marcatore a diamante (◆) sul grafico dei prezzi | Non visibile sul grafico |

---

## 📐 Importo del Dividendo

L'importo ricevuto dipende dal numero di azioni detenute alla **data di record** (la data in cui la società verifica chi possiede le azioni):

$$
\text{Dividendo Ricevuto} = \text{Azioni Detenute} \times \text{Dividendo per Azione}
$$

Dove:

- **Azioni Detenute** = numero di azioni di tua proprietà alla data di record (data ex-dividend − 1 giorno lavorativo)
- **Dividendo per Azione** = importo dichiarato dalla società (es. $0,25/azione)

### 💰 Ritenuta d'Acconto

Molte giurisdizioni applicano una **ritenuta d'acconto** sui dividendi — specialmente per le azioni estere. La tassa viene detratta alla fonte (dal broker o dal paese dell'emittente) prima di ricevere il pagamento:

$$
\text{Dividendo Netto} = \text{Dividendo Lordo} \times (1 - \tau_{withholding})
$$

Dove:

- **Dividendo Lordo** = importo totale dichiarato (prima delle tasse)
- $\tau_{withholding}$ = aliquota della ritenuta d'acconto (es. 15% per azioni USA detenute da residenti UE secondo la maggior parte dei trattati fiscali)
- **Dividendo Netto** = ciò che effettivamente arriva sul tuo conto broker

L'importo trattenuto viene tipicamente registrato come una transazione `TAX` separata in LibreFolio, mantenendo distinti il dividendo lordo e la trattenuta fiscale ai fini della dichiarazione dei redditi.

---

## 🔗 Correlati

- 💰 **[Eventi di dividendo](../asset-events/dividend.md)** — Come i dividendi influenzano i prezzi degli asset
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Trattamento fiscale dei dividendi
- 📈 **[Azioni](../asset-types/stocks.md)** — La principale classe di asset che distribuisce dividendi
