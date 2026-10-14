# ![](../../../static/icons/asset-types/other.png){: width="32" style="vertical-align: middle;" } Autres

Le type d'actif **Autres** est une catégorie générique pour toute classe d'actifs non couverte par les types standards. Elle offre une flexibilité maximale pour le suivi d'investissements non traditionnels.

---

## 🔑 Caractéristiques clés

| Propriété | Détail |
|----------|--------|
| **Code dans LibreFolio** | `OTHER` |
| **Évaluation** | Saisie manuelle ou tout fournisseur compatible |
| **Devise** | Toute devise ISO 4217 |
| **Revenus** | Dépend de l'actif spécifique |
| **Fournisseurs typiques** | CSS Scraper, ou prix saisis manuellement dans l'[éditeur de données](../../../user/assets/detail/data-editor.md) |

---

## 📊 Exemples d'Utilisation

| Actif | Description |
|-------|-------------|
| **Art & Objets de collection** | Tableaux, vin, pièces rares — évalués via des expertises |
| **Capital-investissement** | Parts dans des sociétés non cotées |
| **Capital-risque** | Investissements dans des startups en phase de démarrage |
| **Montres & Bijoux** | Biens de luxe détenus comme investissements |
| **Noms de domaine** | Actifs numériques avec valeur de revente |
| **Crédits carbone** | Certificats de compensation environnementale |

---

## 🔧 Suivi dans LibreFolio

Pour les actifs sans flux de prix public :

1. Cochez **Pas de Fournisseur** pour l'actif et saisissez les prix vous-même dans l'[Éditeur de données](../../../user/assets/detail/data-editor.md)
2. Ou utilisez le fournisseur **CSS Scraper** pour extraire les prix d'un site web
3. Enregistrez les transactions d'achat/vente comme d'habitude via les importations de courtiers

---

## 🔗 Articles connexes

- 📊 **[Vue d'ensemble des types d'actifs](index.md)** — Toutes les classes d'actifs supportées
- ✏️ **[Éditeur de données](../../../user/assets/detail/data-editor.md)** — Saisie manuelle des prix
- 🌐 **[CSS Scraper](../../../user/assets/providers/css-scraper.md)** — Extraire les prix de n'importe quelle page web
