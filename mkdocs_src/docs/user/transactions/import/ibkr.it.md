# <img src="https://www.interactivebrokers.com/favicon.ico" alt=""> Interactive Brokers (IBKR)

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esistere casi limite.

## 📥 Come esportare

LibreFolio legge le operazioni di una **Activity Flex Query** esportata come CSV. L'
**Activity Statement** standard non è supportato.

1. Accedi al [Portale Clienti Interactive Brokers](https://www.interactivebrokers.com) e apri
   **Flex Queries**, nel menu dei report.
2. Crea una **Activity Flex Query** con solo la sezione **Trades**, e seleziona i campi che
   forniscono queste colonne: `Buy/Sell`, `TradeDate`, `ISIN`, `Quantity`, `TradeMoney`,
   `CurrencyPrimary`, `IBCommission`, `IBCommissionCurrency`.
3. Scegli **CSV** come formato e `yyyyMMdd` come formato data (ad esempio `20240315`), poi
   salva la query.
4. Eseguila per il periodo desiderato e scarica il file.

## ⚠️ Insidie comuni

- **La prima riga deve contenere i nomi delle colonne.** LibreFolio riconosce il file dalle
  intestazioni tra virgolette `Buy/Sell`, `TradeDate`, `ISIN` e `IBCommission` sulla sua prima
  riga: mantieni attive le intestazioni delle colonne e lascia disattivati i record di intestazione e chiusura e i codici di sezione.
- **Solo CSV**: le esportazioni PDF e XML non vengono lette.

## 📝 Cosa viene importato

- **Acquisti e vendite** di strumenti con un ISIN, nella valuta dell'operazione (`CurrencyPrimary`;
  USD quando la colonna è vuota).
- **Commissioni**, ciascuna come **commissione** separata sullo stesso asset e alla stessa data, in
  `IBCommissionCurrency` (o nella valuta dell'operazione quando quella colonna è vuota).
- **Non importati**: dividendi, interessi, imposte, depositi e prelievi, conversioni di valuta
  (le righe senza un ISIN vengono saltate con un avviso) e operazioni societarie. Aggiungili
  manualmente, oppure con un file [CSV generico](generic-csv.md).
