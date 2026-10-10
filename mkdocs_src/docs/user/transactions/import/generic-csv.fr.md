# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> CSV générique

L'importateur **CSV générique** lit un fichier CSV que vous préparez vous-même. Nommez ses colonnes comme dans la
[référence des colonnes](#column-reference) — `date` et `type` au minimum — et LibreFolio les reconnaît
par leurs noms : il n'y a rien à mapper à la main.

## 🎯 Quand l'utiliser

- Votre courtier n'est pas dans la [liste des courtiers pris en charge](index.md).
- Votre courtier a modifié son export et son importateur ne le lit pas encore.
- Vous tenez votre propre tableur, ou un script génère le CSV pour vous.

## ⚙️ Comment l'importer

1. **Préparez le fichier.** Enregistrez-le au format `.csv` (depuis Excel, enregistrez une copie au format CSV). Sa première ligne nomme les
   colonnes, comme dans la [référence des colonnes](#column-reference) ; les autres colonnes sont ignorées.
2. **Téléchargez-le** dans l'**[Assistant d'importation](how-to.md)** et affectez-le à son courtier.
3. **Vérifiez le plugin** dans **Sélectionner les fichiers** : si **CSV générique** n'est pas déjà sélectionné, choisissez-le dans
   la colonne **Plugin** du fichier.
4. **Analyser et vérifier.** Chaque ligne devient une transaction.

!!! tip "Un fichier par courtier — pas un fichier par devise"

    Chaque ligne d'un fichier est importée dans le courtier auquel vous affectez ce fichier, donc ne mélangez jamais deux
    courtiers dans un même CSV. Des lignes dans différentes devises peuvent partager le même fichier, car chaque ligne porte
    sa propre `currency` ; vous pouvez aussi découper l'historique d'un courtier en plusieurs fichiers, un par année
    par exemple, et les importer ensemble.

### 🧯 Si quelque chose ne va pas

- **« required column 'date' not found »** (ou `type`) : la première ligne ne contient pas cette colonne, ou la nomme
  différemment. Ajoutez-la, ou renommez la colonne avec un nom accepté, et téléchargez à nouveau le fichier.
- **Une ligne manque** : les lignes que LibreFolio ne peut pas lire — un type inconnu, une date dans un format inconnu,
  une `currency` vide — sont ignorées et listées parmi les avertissements de l'étape **Analyser** ; les lignes avec
  un signe incorrect apparaissent comme des problèmes de validation. Corrigez-les dans le fichier et téléchargez-le à nouveau.
- **L'espace de travail groupé demande un coût sur une ligne `ADJUSTMENT`** : saisissez le coût d'**une** unité,
  et non la valeur totale de la position.

---

## 🔄 Convertir un rapport personnalisé

Si vos données proviennent d'un autre outil, un petit script peut les transformer en CSV générique. La
**[spécification technique du CSV générique](../../../developer/backend/brim/generic_csv.md)** décrit
le format en détail — signes, quel type utiliser selon le cas, exemples concrets. Vous pouvez la coller dans un assistant IA
(ChatGPT, Claude, Gemini…) avec quelques lignes d'exemple de votre fichier et demander le script.

---

## 📋 Référence des colonnes {: #column-reference }

Voici les colonnes que LibreFolio reconnaît dans un fichier CSV générique. Les noms de colonnes sont insensibles à la casse et les espaces qui les entourent sont ignorés.

| Colonne | Obligatoire ? | Alias acceptés | Description |
|--------|-----------|-----------------|-------------|
| **`date`** | ✅ Toujours | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Date de la transaction |
| **`type`** | ✅ Toujours | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Type de transaction — voir les valeurs ci-dessous |
| **`quantity`** | Obligatoire pour BUY/SELL/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Nombre d'unités. **Négatif pour SELL, positif pour BUY.** |
| **`amount`** | Obligatoire pour la plupart des types | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Impact sur la trésorerie. **Négatif quand la trésorerie sort, positif quand la trésorerie entre.** Vide pour ADJUSTMENT. |
| **`currency`** | Optionnel (EUR par défaut) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | Code de devise ISO 4217. EUR ne s'applique que si le fichier n'a pas de colonne currency : s'il en a une, remplissez-la sur chaque ligne avec un `amount`, sinon cette ligne est ignorée. |
| **`asset`** | Obligatoire pour BUY/SELL/DIVIDEND/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN, ou une chaîne de nom cohérente pour les actifs non cotés |
| **`description`** | Optionnel | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Notes en texte libre |

### 🏷️ Valeurs valides de `type`

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `ADJUSTMENT`

!!! warning "Non pris en charge : TRANSFER, FX_CONVERSION, CASH_TRANSFER"

    Ceux-ci nécessitent deux lignes liées, ce qu'un CSV ne peut pas exprimer : ces lignes sont ignorées avec un avertissement.
    Saisissez-les à la main depuis la page Transactions, ou utilisez l'importateur propre à votre courtier.

---

## 🔗 Voir aussi

- 🧙 **[Comment importer](how-to.md)** — l'Assistant d'importation, étape par étape
- 🏦 **[Courtiers pris en charge](index.md)** — vérifiez d'abord si votre courtier dispose de son propre importateur
- 🛠️ **[Spécification technique du CSV générique](../../../developer/backend/brim/generic_csv.md)** — le format complet, pour les scripts et les développeurs
