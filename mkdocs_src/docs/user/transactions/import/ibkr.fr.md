# <img src="https://www.interactivebrokers.com/favicon.ico" alt=""> Interactive Brokers (IBKR)

!!! info "Bêta"

    Ce plugin est en **Bêta** — testé avec des fichiers d'exemple, mais des cas limites peuvent exister.

## 📥 Comment exporter

LibreFolio lit les transactions d'une **Requête Flex d'activité** exportée au format CSV. Le
**Relevé d'activité** standard n'est pas pris en charge.

1. Connectez-vous au [Portail client Interactive Brokers](https://www.interactivebrokers.com) et ouvrez
   **Requêtes Flex**, dans le menu des rapports.
2. Créez une **Requête Flex d'activité** avec uniquement la section **Transactions**, et sélectionnez les champs qui
   donnent ces colonnes : `Buy/Sell`, `TradeDate`, `ISIN`, `Quantity`, `TradeMoney`,
   `CurrencyPrimary`, `IBCommission`, `IBCommissionCurrency`.
3. Choisissez **CSV** comme format et `yyyyMMdd` comme format de date (par exemple `20240315`), puis
   enregistrez la requête.
4. Exécutez-la pour la période souhaitée et téléchargez le fichier.

## ⚠️ Pièges courants

- **La première ligne doit être constituée des noms de colonnes.** LibreFolio reconnaît le fichier grâce aux
  en-têtes `Buy/Sell`, `TradeDate`, `ISIN` et `IBCommission` entre guillemets sur sa première ligne : laissez l'option
  d'en-têtes de colonnes activée, et désactivez les enregistrements d'en-tête et de pied de page ainsi que les codes de section.
- **CSV uniquement** : les exports PDF et XML ne sont pas lus.

## 📝 Ce qui est importé

- **Achats et ventes** d'instruments avec un ISIN, dans la devise de la transaction (`CurrencyPrimary` ;
  USD lorsque la colonne est vide).
- **Commissions**, chacune comme des **Frais** distincts sur le même actif et à la même date, dans
  `IBCommissionCurrency` (ou la devise de la transaction lorsque cette colonne est vide).
- **Non importés** : dividendes, intérêts, impôts, dépôts et retraits, conversions de devise
  (les lignes sans ISIN sont ignorées avec un avertissement) et opérations sociétaires. Ajoutez-les manuellement, ou
  avec un fichier [CSV générique](generic-csv.md).
