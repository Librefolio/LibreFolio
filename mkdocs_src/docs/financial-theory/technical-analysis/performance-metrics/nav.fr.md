# 💼 Net Asset Value (NAV) / Valeur Nette (Net Worth)

*[⬅️ Retour à l'Aperçu des Métriques de Performance](index.md)*

## 💡 Qu'est-ce que le NAV / Net Worth ?

Dans le tableau de bord LibreFolio, la **Net Asset Value (NAV)** (également appelée **Net Worth** ou **Valeur Nette**) représente la valeur totale du marché de votre portefeuille à la fin de la fenêtre temporelle sélectionnée (`date_to`).

Elle répond à la question fondamentale : _"Combien vaut le portefeuille dans le périmètre sélectionné en ce moment précis ?"_

Contrairement aux métriques de performance basées sur une période (comme le ROI ou le P&L), la NAV est un **instantané (snapshot) à une date précise**. Bien que son évolution historique puisse être tracée dans le temps, la valeur finale de la NAV affichée sur le tableau de bord dépend uniquement de la date de fin (`date_to`) et est complètement indépendante de la date de début (`date_from`).

---

## 🧮 Formula

LibreFolio calcule la Net Asset Value en utilisant la formule suivante :

$$
\text{NAV} = \text{Valeur de Marché} + \text{Liquidité} + \text{Valeur en Transit}
$$

Où :

- **$\text{Valeur de Marché}$** : La valorisation boursière actuelle de tous les actifs détenus (ETF, actions, obligations, cryptomonnaies, etc.), calculée à l'aide du dernier prix disponible et convertie dans la devise de référence du portefeuille.
- **$\text{Liquidité}$** : Le solde de trésorerie réel détenu sur les comptes des courtiers inclus dans le périmètre sélectionné.
- **$\text{Valeur en Transit}$** : La valeur marchande des liquidités ou des actifs actuellement en cours de transfert interne entre les comptes compris dans le périmètre (ex. transferts initiés mais non encore complétés). Tout comme pour le [Valeur Comptable (Book Value)](book-value.md), ce concept permet de gérer les transactions (ex. virements bancaires ou transferts de titres) qui quittent un compte le jour 1 et n'arrivent à destination que le jour 5 en raison des délais d'exécution.

---

## 📝 Exemple Pratique

Considérons un portefeuille avec les soldes suivants à la fin de la période sélectionnée :

- **Valeur de Marché des Actifs** : 32 759 €
- **Liquidité** : 631 €
- **Actifs en Transit** : 0 €

La Net Asset Value est calculée comme suit :

$$
\text{NAV} = 32 759 + 631 + 0 = 33 390\text{ €}
$$


---

## ⚖️ Différences Clés

Pour éviter les confusions, il est important de distinguer la NAV des autres métriques du tableau de bord :

- **Par rapport au Book Value (Valeur Comptable)** : La NAV représente la **valeur actuelle du marché** de vos actifs. Le [Book Value](book-value.md) représente le **coût d'achat historique** (ce que vous avez réellement payé pour les acquérir). La différence entre les deux constitue votre plus-value ou moins-value latente (unrealized gain/loss).
- **Par rapport au Period P&L (P&L de la Période)** : La NAV indique la valeur absolue de votre patrimoine. Le [Period P&L](period-pnl.md) mesure la *variation* de ce patrimoine sur une période donnée, après correction des dépôts et retraits externes.

---

## ⚠️ Qualité des Données et Valorisation

Comme la NAV repose sur les prix du marché et les taux de change (FX) pour convertir tous les actifs dans votre devise cible :

- Si les données de prix ou les taux de change sont manquants pour un actif à la date de fin (`date_to`), la valorisation peut être incomplète.
- Dans ce cas, LibreFolio affiche le **Data Quality Banner** (Bandeau de Qualité des Données) en haut du tableau de bord pour vous alerter que certaines valorisations sont basées sur des prix obsolètes ou manquants.
