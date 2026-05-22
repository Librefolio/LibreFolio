# ![](../../../static/icons/transactions/deposit.png){: width="32" style="vertical-align: middle;" } Depositi e Prelievi

I **depositi** e i **prelievi** tracciano i flussi di cassa in entrata e in uscita da un conto broker. Non coinvolgono alcun asset — cambia solo il saldo in contanti.

---

## 🔑 Proprietà Chiave

| Proprietà | Deposito | Prelievo |
|----------|---------|------------|
| **Codice** | `DEPOSIT` | `WITHDRAWAL` |
| **Effetto cassa** | ⬆️ Aumenta il saldo | ⬇️ Diminuisce il saldo |
| **Effetto asset** | — | — |
| **Evento fiscale** | No | No |

---

## 💡 Perché Sono Importanti

I depositi e i prelievi non cambiano il valore di mercato del tuo portafoglio, ma sono fondamentali per la **misurazione della performance**:

- **Money-Weighted Return (MWR)**: tiene conto della tempistica e dell'entità dei flussi di cassa — influenzato direttamente dai depositi e dai prelievi
- **Time-Weighted Return (TWR)**: elimina l'effetto dei flussi di cassa per misurare la performance "pura" del portafoglio

Senza un tracciamento accurato dei depositi/prelievi, è impossibile distinguere tra i rendimenti *generati* dal portafoglio e i rendimenti *causati* dall'aggiunta/rimozione di contanti.

!!! tip "Scopri di più"

    Consulta **[📈 Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** per le formule e la metodologia.

---

## 🔗 Correlati

- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — calcolo TWR vs MWR
- 🛒 **[Acquisto e Vendita](buy-sell.md)** — transazioni che utilizzano la liquidità depositata
