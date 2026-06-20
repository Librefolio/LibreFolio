# ⏱️ TWRR (Time-Weighted Rate of Return)

*[⬅️ Retour à l'aperçu des indicateurs de performance](index.md)*

## 💡 Qu'est-ce que c'est ?
Le TWRR mesure la performance « pure » des actifs que vous avez choisis (le Marché), en ignorant complètement le moment et le montant de vos dépôts ou retraits.

## 🧮 Comment ça fonctionne
À chaque fois que vous déposez ou retirez de l'argent, le TWRR « fragmente » la chronologie en sous-périodes. Il calcule le rendement pour chaque sous-période spécifique, puis enchaîne (multiplie) toutes les sous-périodes. 

$$
R_{TWRR} = \prod_{i=1}^{n} (1 + r_i) - 1
$$

## 🎯 Quand l'utiliser
- Pour juger si les **actifs que vous avez choisis** sont réellement performants.
- Pour comparer votre portefeuille à un benchmark externe (comme le S&P 500).
- Les fonds communs de placement et les ETF publient toujours le TWRR, car le gestionnaire du fonds ne peut pas contrôler le moment où les clients déposent ou retirent de l'argent.
