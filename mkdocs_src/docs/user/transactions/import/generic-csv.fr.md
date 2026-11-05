# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> Generic CSV

L'importateur **Generic CSV** lit un fichier CSV que vous préparez vous-même. Nommez ses colonnes
comme indiqué dans la [référence des colonnes](#column-reference) — `date` et `type` au minimum — et
LibreFolio les reconnaît par leur nom : il n'y a rien à associer à la main.

## 🎯 Quand l'utiliser

- Votre courtier ne figure pas dans la [liste des courtiers pris en charge](index.md).
- Votre courtier a modifié son export et son importateur ne le lit pas encore.
- Vous tenez votre propre tableur, ou un script écrit le CSV pour vous.

## ⚙️ Comment l'importer

1. **Préparez le fichier.** Enregistrez-le au format `.csv` (depuis Excel, enregistrez une copie au
   format CSV). Sa première ligne nomme les colonnes, comme dans la
   [référence des colonnes](#column-reference) ; les autres colonnes sont ignorées.
2. **Téléversez-le** dans l'**[Assistant d'importation](how-to.md)** et affectez-le à son courtier.
3. **Vérifiez le plugin** dans **Sélectionner les fichiers** : si **Generic CSV** n'est pas déjà
   sélectionné, choisissez-le dans la colonne **Plugin** du fichier.
4. **Analysez et vérifiez.** Chaque ligne devient une transaction.

!!! tip "Un fichier par courtier — pas un fichier par devise"

    Chaque ligne d'un fichier est importée dans le courtier que vous affectez à ce fichier : ne
    mélangez donc jamais deux courtiers dans un même CSV. Des lignes en devises différentes peuvent
    cohabiter dans un même fichier, puisque chaque ligne porte sa propre `currency` ; vous pouvez
    aussi découper l'historique d'un courtier en plusieurs fichiers, un par an, par exemple, et
    les importer ensemble.

!!! tip "Plusieurs colonnes de date ? Utilisez la date de l'opération"

    LibreFolio ne lit qu'**une seule** colonne de date par fichier, jamais deux. Si l'en-tête
    contient plusieurs colonnes portant un nom de date accepté (par exemple `trade_date` et
    `settlement_date`, voir la [référence des colonnes](#column-reference)), il prend la
    **première, en lisant de gauche à droite**, et ignore les autres. Une colonne portant un autre
    nom, comme `order date`, n'est pas lue du tout.

    Mettez dans la colonne de date la **date de l'opération** : le jour où la transaction a été
    effectuée, et non le jour de règlement ou de comptabilisation, qui peut survenir plusieurs jours
    plus tard. Cela importe particulièrement lorsque vous écrivez le CSV à la main ou le faites
    écrire par une autre IA : demandez-lui d'utiliser la date de l'opération et de laisser les
    autres dates hors du fichier.

### 🧯 Si quelque chose ne va pas

- **« required column 'date' not found »** (ou `type`) : la première ligne ne contient pas cette
  colonne, ou la nomme différemment. Ajoutez-la, ou renommez la colonne avec un nom accepté, puis
  téléversez à nouveau le fichier.
- **Une ligne manque** : les lignes que LibreFolio ne peut pas lire — un type inconnu, une date dans
  un format inconnu, une `currency` vide — sont ignorées et listées parmi les avertissements de
  l'étape **Analyse** ; les lignes dont le signe est erroné apparaissent comme des problèmes de
  validation. Corrigez-les dans le fichier et téléversez-le à nouveau.
- **L'espace de travail groupé demande un coût sur une ligne `ADJUSTMENT`** : saisissez le coût
  d'**une** unité, et non la valeur totale de la position. Seule une ligne qui ajoute des unités le
  demande : une ligne qui retire des unités (quantité négative) n'a pas de valeur.

### 📅 Format de date {: #day-month-order }

Une date comme `03/04/2025` peut signifier le 3 avril ou le 4 mars, et une année peut s'écrire avec
deux chiffres (`03/04/26`). LibreFolio vous laisse choisir la façon dont l'importateur Generic CSV lit
les dates de vos fichiers. Ce choix n'appartient qu'à vous : les autres utilisateurs du même
LibreFolio conservent le leur.

Ouvrez **Paramètres › Plugins**, trouvez **Importations de courtiers** et réglez le **Format de date**.
Chaque option affiche la forme de la date et un exemple complet :

| Option | Exemple |
|--------|---------|
| `dd/mm/yyyy` (par défaut) | `03/04/2025` = **3 avril 2025** |
| `mm/dd/yyyy` | `03/04/2025` = **4 mars 2025**, comme on l'écrit aux États-Unis |
| `dd/mm/yy` | `03/04/26` = **3 avril 2026** |
| `mm/dd/yy` | `03/04/26` = **4 mars 2026** |
| `yy/mm/dd` | `26/04/03` = **3 avril 2026** |
| `yyyy-mm-dd` | `2026-04-03` = **3 avril 2026** |

`dd/mm/yyyy` correspond à la façon dont LibreFolio a toujours lu les dates : rien ne change donc si
vous n'ouvrez jamais ce réglage. Avec `dd/mm/yyyy` et `mm/dd/yyyy`, une date qu'un seul ordre permet de
lire est toujours lue correctement : `25/12/2025` est le 25 décembre, car il n'existe pas de mois 25.
Avec les options à année sur deux chiffres, l'ordre choisi est le seul utilisé, et `yy` suit la règle
habituelle : `00`–`68` correspondent à 2000–2068, `69`–`99` à 1969–1999. Les dates écrites comme
`2025-12-25`, `20251225` ou `25 Dec 2025` n'ont qu'une seule signification et ne sont jamais décalées.

Une ligne dont la date ne peut pas être lue dans le format choisi est écartée, et l'analyse le signale
pour chaque ligne (*Ligne 4 : 25/12/26 n'est pas une date valide au format mm/dd/yy…*), en indiquant
où corriger : corrigez la date dans le fichier, ou changez le **Format de date** dans
**Paramètres › Plugins** et appuyez sur **Tout ré-analyser**. Au-delà de la vingtième ligne de ce
type, une seule note récapitule les suivantes.

!!! tip "Ré-analysez le fichier après l'avoir modifié"

    Un fichier déjà analysé conserve les dates avec lesquelles il a été lu. Après avoir changé le
    réglage, le fichier affiche un avertissement indiquant qu'il doit être **analysé à nouveau** :
    relancez l'analyse, puis vérifiez les lignes.

---

## 🔄 Convertir un rapport personnalisé

Si vos données proviennent d'un autre outil, un court script peut les convertir en Generic CSV. La
**[spécification technique du Generic CSV](../../../developer/backend/brim/generic_csv.md)** décrit
le format dans son intégralité — les signes, le type à utiliser selon le cas, des exemples concrets.
Vous pouvez la coller dans un assistant IA (ChatGPT, Claude, Gemini…) avec quelques lignes d'exemple
de votre fichier, et demander le script.

---

## 📋 Référence des colonnes {: #column-reference }

Voici les colonnes que LibreFolio reconnaît dans un fichier Generic CSV. Les noms de colonnes sont insensibles à la casse et les espaces qui les entourent sont ignorés.

| Colonne | Obligatoire ? | Alias acceptés | Description |
|---------|---------------|----------------|-------------|
| **`date`** | ✅ Toujours | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Date de la transaction |
| **`type`** | ✅ Toujours | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Type de transaction — voir les valeurs ci-dessous |
| **`quantity`** | Obligatoire pour BUY/SELL/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Nombre d'unités. **Négatif pour SELL, positif pour BUY.** |
| **`amount`** | Obligatoire pour la plupart des types | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Impact sur la trésorerie. **Négatif quand la trésorerie sort, positif quand elle entre.** Vide pour ADJUSTMENT. |
| **`currency`** | Facultatif (EUR par défaut) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | Code de devise ISO 4217. L'EUR ne s'applique que si le fichier n'a pas de colonne de devise : s'il en a une, renseignez-la sur chaque ligne comportant un `amount`, sinon cette ligne est ignorée. |
| **`asset`** | Obligatoire pour BUY/SELL/DIVIDEND/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN, ou un nom cohérent pour les actifs non cotés |
| **`description`** | Facultatif | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Notes en texte libre |

### 🏷️ Valeurs valides de `type`

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `ADJUSTMENT`

!!! warning "Non pris en charge : TRANSFER, FX_CONVERSION, CASH_TRANSFER"

    Ces opérations nécessitent deux lignes liées, ce qu'un CSV ne peut pas exprimer : ces lignes sont
    ignorées avec un avertissement. Saisissez-les à la main depuis la page Transactions, ou utilisez
    l'importateur propre à votre courtier.

---

## 🔗 Voir aussi

- 🧙 **[Comment importer](how-to.md)** — l'Assistant d'importation, étape par étape
- 🏦 **[Courtiers pris en charge](index.md)** — vérifiez d'abord si votre courtier dispose de son propre importateur
- 🛠️ **[Spécification technique du Generic CSV](../../../developer/backend/brim/generic_csv.md)** — le format complet, pour les scripts et les développeurs
