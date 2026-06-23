# 📊 P&L de la Période (Profit and Loss)

*[⬅️ Retour à l'aperçu des mesures de performance](index.md)*

## 💡 Qu'est-ce que le P&L de la Période?

Le **P&L de la Période** (Profit and Loss / Pertes et Profits) représente les gains ou pertes monétaires absolus générés par votre portefeuille au cours de la fenêtre temporelle sélectionnée, ajustés des flux de trésorerie externes.

Il répond à la question directe : _"Combien d'argent ai-je réellement gagné ou perdu au cours de cette période ?"_

Contrairement aux mesures exprimées en pourcentage (comme le [ROI Simple](roi.md) ou le [TWRR](twrr.md)), le P&L de la Période est exprimé sous forme d'un montant fiduciaire absolu (ex. EUR, USD). Surtout, il est **ajusté des flux de trésorerie**, ce qui signifie qu'il isole la performance réelle des investissements de vos dépôts et retraits.

---

## 🧮 Formule

LibreFolio calcule le P&L de la Période à l'aide de l'équation suivante :

$$
\text{P}\&\text{L de la Période} = \text{NAV}_{\text{fin}} - \text{NAV}_{\text{début}} - \text{Flux Externes Nets}
$$

Dans laquelle :

- **$\text{NAV}_{\text{début}}$** : La [Net Asset Value (Net Worth)](nav.md) au début de la fenêtre temporelle sélectionnée.
- **$\text{NAV}_{\text{fin}}$** : La Net Asset Value à la fin de la fenêtre temporelle sélectionnée.
- **$\text{Flux Externes Nets}$** : Le capital net injecté ou retiré par l'investisseur au cours de la période, défini comme :

$$
\text{Flux Externes Nets} = \text{Dépôts} - \text{Retraits}
$$

Seuls les flux qui entrent ou sortent du périmètre du portefeuille sélectionné comptent comme externes. Les transferments internes entre courtiers ou comptes dans le périmètre n'affectent pas ce calcul.

---

## 📝 Exemple Pratique

Supposons que votre portefeuille présente les mesures suivantes pour une année donnée :

- **NAV au début** : 27 000 €
- **Dépôts Totaux** : 1 000 €
- **Retraits Totaux** : 0 €
- **NAV à la fin** : 33 000 €

Nous calculons d'abord les Flux Externes Nets :

$$
\text{Flux Externes Nets} = 1 000 - 0 = 1 000\text{ €}
$$

Puis, nous calculons le P&L de la Période :

$$
\text{P}\&\text{L de la Période} = 33 000 - 27 000 - 1 000 = 5 000\text{ €}
$$

### 🔍 Explication du Résultat

Bien que la valorisation totale de votre portefeuille ait augmenté de **6 000 €** (passant de 27 000 € à 33 000 €), **1 000 €** de cette augmentation proviennent de vos propres versements. Par conséquent, vos placements ont généré un gain net réel de **5 000 €**.

Si la formule n'ajustait pas les flux externes, elle afficherait à tort un profit de 6 000 €, vous laissant croire que vos actifs ont été plus performants qu'ils ne l'ont été en réalité.

---

## ⚖️ Différences Clés

- **vs. ROI / TWRR / MWRR** : Ce sont des mesures en pourcentage indiquant le taux de rendement. Le P&L de la Période indique le montant monétaire absolu du profit/perte.
- **vs. Plus-value/Moins-value Latente** : La plus-value/moins-value latente est un instantané des positions ouvertes actuelles par rapport à leur coût d'achat initial. Le P&L de la Période mesure la performance des positions ouvertes et fermées (gains réalisés, dividendes, intérêts) spécifiquement dans les limites de la fenêtre temporelle choisie.
