# 📥 Import depuis un courtier (BRIM)

**BRIM** (Broker Report Import Module) vous permet d'importer des transactions directement depuis les fichiers d'exportation de votre courtier — aucune saisie manuelle n'est nécessaire. Téléchargez un rapport CSV et LibreFolio analyse, associe et importe toutes les transactions en un seul flux.

---

## 🚀 Comment importer

1. Exportez un rapport de transactions depuis votre courtier (généralement un fichier CSV — consultez le centre d'aide de votre courtier).
2. Dans LibreFolio, accédez à votre page **Courtier**.
3. Cliquez sur le bouton **Importer** (:material-file-upload:) dans l'en-tête du courtier.
4. La **fenêtre modale d'importation** s'ouvre.
5. **Glissez-déposez** ou cliquez pour sélectionner votre fichier.
6. LibreFolio **détecte automatiquement** le format du courtier et affiche un **aperçu** des transactions analysées.
7. Vérifiez l'aperçu — assurez-vous que les dates, les montants et les noms des actifs sont corrects.
8. Cliquez sur **Importer** pour valider toutes les transactions.

!!! tip "Vous pouvez également utiliser la section Fichiers"

    La section **[Fichiers](../../files/index.md)** (onglet BRIM) vous permet de gérer les rapports de courtier téléchargés de manière centralisée, de les ré-importer ou de les supprimer.

---

## 🏦 Courtiers supportés

| Courtier | Page |
|--------|------|
| Interactive Brokers (IBKR) | [→](ibkr.md) |
| Degiro | [→](degiro.md) |
| eToro | [→](etoro.md) |
| Directa SIM | [→](directa.md) |
| Charles Schwab | [→](schwab.md) |
| Revolut | [→](revolut.md) |
| Coinbase | [→](coinbase.md) |
| Freetrade | [→](freetrade.md) |
| Finpension | [→](finpension.md) |
| Trading212 | [→](trading212.md) |
| Generic CSV | [→](generic-csv.md) |

!!! note "Tous les fournisseurs sont en Beta"

    Les plugins d'importation sont maintenus par la communauté et s'améliorent avec le temps. Si un format de rapport spécifique présente des anomalies, le fournisseur **[Generic CSV](generic-csv.md)** permet un mappage manuel des colonnes en guise de fallback.

---

## 🗂️ Mappage des actifs

Lors de l'étape d'aperçu, LibreFolio tente de **faire correspondre automatiquement** chaque nom d'actif de votre rapport à un actif déjà présent dans votre bibliothèque.

- ✅ **Correspondance trouvée** — sera importé vers l'actif existant.
- ⚠️ **Aucune correspondance** — sélectionnez ou créez l'actif cible avant l'importation.
- ❌ **Erreur** — la ligne n'a pas pu être analysée.

---

## ♻️ Détection des doublons

BRIM vérifie la présence de **transactions en double** en se basant sur la date, le type, l'actif, la quantité et le montant. Les lignes en double sont signalées dans l'aperçu — vous pouvez choisir de les ignorer ou de forcer leur importation.

---

## 🔗 Liens connexes

- 📋 **[Tableau des transactions](../index.md)** — Visualiser et gérer les transactions importées
- 🗂️ **[Fichiers](../../files/index.md)** — Gérer les fichiers de rapports de courtier téléchargés
- 🏦 **[Courtiers](../../brokers/index.md)** — Configurer d'abord vos comptes de courtage
