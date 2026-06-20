# 📈 Métriques de Performance

Lors de l'évaluation du succès d'un portefeuille d'investissement, se contenter du solde total ou du profit absolu ne suffit pas. Pour comprendre réellement la performance, vous avez besoin de métriques standardisées qui répondent à différentes questions : « Comment se sont comportés mes actifs ? », « Mon timing était-il bon ? » et « Quel est le rendement de cette transaction spécifique ? ».

---

## 🎭 Les Deux Acteurs de Votre Portefeuille

Pour comprendre pourquoi plusieurs métriques existent, imaginez qu'il y a deux « acteurs » différents qui gèrent votre patrimoine :

1. **Le Marché (Les Actifs) :** Fait varier à la hausse ou à la baisse le cours des actifs que vous détenez.
2. **Vous (L'Investisseur) :** Décidez *quand* déposer ou retirer des liquidités du portefeuille.

Ces deux acteurs peuvent avoir des performances très différentes. Vous pouvez choisir une excellente action (Le Marché performe bien), mais vous pouvez l'acheter au sommet juste avant un krach (vous obtenez de mauvais résultats). LibreFolio utilise différentes métriques pour isoler ces deux comportements.

---

## 📚 Sujets de ce Chapitre

| Métrique / Concept | Description |
|------------------|-------------|
| **[ROI Simple](roi.md)** | Rendement en pourcentage absolu généré par un investissement par rapport à son coût. Idéal pour évaluer des positions uniques. |
| **[TWRR](twrr.md)** | Taux de rendement pondéré dans le temps. Mesure la performance pure des actifs sous-jacents, sans tenir compte du timing des flux de trésorerie. |
| **[MWRR (XIRR)](mwrr.md)** | Taux de rendement pondéré par les capitaux. Mesure votre performance personnelle en tant qu'investisseur, en tenant compte du timing des flux de trésorerie. |
| **[Coût Moyen Pondéré](weighted-average-cost.md)** | Le coût unitaire moyen d'un actif dans un portefeuille, pondéré par les quantités acquises. |

---

## 💡 L'Exemple Pratique (TWRR vs MWRR)

Voyons un exemple extrême pour voir comment le [TWRR](twrr.md) et le [MWRR](mwrr.md) racontent deux histoires complètement différentes, mais mathématiquement correctes.

* **Mois 1 :** Vous avez une excellente intuition. Vous achetez pour **1 000 €** d'une action. Le mois suivant, l'action double (+100 %). Vous avez maintenant **2 000 €**.
* **Mois 2 :** Emporté par l'excitation, vous videz votre compte d'épargne et déposez **100 000 €** supplémentaires dans cette même action. Vous avez maintenant 102 000 € investis.
* **Mois 3 :** Malheureusement, l'action chute de **-10 %**. Votre capital total passe de 102 000 € à **91 800 €**.

Si vous regardez LibreFolio maintenant, que verrez-vous ?

### 📈 Votre TWRR sera : +80 %
*Pourquoi ?* Les actifs que vous avez choisis ont augmenté de +100 %, puis ont chuté de -10 %. Mathématiquement : 

$$
(2.0 \times 0.9) - 1 = +0.8
$$

Les actifs que vous avez choisis ont incroyablement bien performé. Si vous aviez investi tout votre argent dès le premier jour, vous seriez riche. Votre *sélection d'actifs* était excellente.

### 📉 Votre MWRR sera : FORTEMENT NÉGATIF (env. -9 %)
*Pourquoi ?* Vous avez déposé un total de 101 000 € de votre propre poche, mais vous détenez actuellement 91 800 €. Vous avez subi une perte réelle et absolue de 9 200 € ! 
Votre mauvais timing — déposer 100 000 € juste au sommet avant une chute — a détruit vos rendements. Votre *timing* était terrible.

---

## ⚖️ Pourquoi LibreFolio affiche les deux côte à côte

En plaçant le TWRR et le MWRR l'un à côté de l'autre sur votre tableau de bord, LibreFolio vous donne un diagnostic comportemental immédiat :

- **TWRR > MWRR :** *« Vous choisissez de bons investissements, mais votre timing est mauvais. Vous achetez probablement au plus haut (FOMO) et faites baisser vos rendements personnels. »*
- **MWRR > TWRR :** *« Vous avez un excellent timing ! Vous achetez des actifs avec une décote lorsque le marché chute, augmentant vos rendements personnels au-dessus de la moyenne du marché. »*
