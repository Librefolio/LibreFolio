# ⏱️ Effet de timing

*[⬅️ Retour à l'Aperçu des Métriques de Performance](index.md)*

## 💡 Qu'est-ce que c'est ?

L'**Effet de timing** mesure à quel point le moment et le montant de vos dépôts et retraits (flux de trésorerie) ont influencé le rendement personnel de l'investisseur par rapport au rendement de la stratégie sous-jacente, neutralisant l'effet des flux de trésorerie externes.

Il est calculé comme la différence entre votre taux de rendement pondéré par l'argent (MWRR) cumulé et votre taux de rendement pondéré par le temps (TWRR) cumulé :

$$
\text{Effet de timing} = \text{MWRR}_{\text{cumulé}} - \text{TWRR}_{\text{cumulé}}
$$

Il s'exprime en **points de pourcentage (pp)**.

---

## 🧮 Comment interpréter l'Effet de timing

En comparant le [MWRR Cumulé](mwrr.md#cumulative-mwrr) (qui intègre le moment des flux de trésorerie) au [TWRR Cumulé](twrr.md) (qui neutralise cet effet), l'Effet de timing met en évidence la différence entre le rendement personnel de l'investisseur et le rendement de la stratégie, attribuable au timing et à la dimension des flux de trésorerie :

- **Effet de timing positif ($> 0$ pp) :** Vos flux de trésorerie sont intervenus à des moments favorables (par exemple, en achetant des actifs à prix réduit lors d'une baisse des marchés). Votre rendement personnel (MWRR) est supérieur à celui de la stratégie pure (TWRR).
- **Effet de timing négatif ($< 0$ pp) :** Vos flux de trésorerie sont intervenus à des moments défavorables (par exemple, en déposant des sommes importantes au sommet du marché juste avant une correction). Votre rendement personnel (MWRR) est inférieur à celui de la stratégie pure (TWRR).
- **Effet de timing proche de zéro ($\approx 0$ pp) :** Vos flux de trésorerie ont eu peu ou pas d'impact sur la performance (par exemple, si vous avez effectué de très petits dépôts ou si le marché est resté stable pendant vos transactions).

---

## 🔢 Exemples Numériques

### Exemple 1 : Effet de timing positif (Flux favorables)
* **TWRR Cumulé (Rendement de la Stratégie) :** $+20\%$
* **MWRR Cumulé (Rendement de l'Investisseur) :** $+28\%$

$$
\text{Effet de timing} = 28\% - 20\% = +8\text{ pp}
$$

* **Interprétation :** La stratégie des actifs sous-jacents a généré un rendement de $+20\%$. Cependant, comme vous avez ajouté un montant significatif de capitaux au portefeuille avant que le marché ne monte, votre rendement personnel pondéré par l'argent a augmenté pour atteindre $+28\%$. Le timing et le montant de vos dépôts ont contribué positivement, générant **$+8$ points de pourcentage** de rendement supplémentaire.

### Exemple 2 : Effet de timing négatif (Flux défavorables)
* **TWRR Cumulé (Rendement de la Stratégie) :** $+20\%$
* **MWRR Cumulé (Rendement de l'Investisseur) :** $+12\%$

$$
\text{Effet de timing} = 12\% - 20\% = -8\text{ pp}
$$

* **Interprétation :** La stratégie a généré un rendement de $+20\%$. Cependant, vous avez versé un capital important près du sommet du marché, juste avant une baisse. Cela a exposé une plus grande partie de votre argent à une période de mauvaise performance, entraînant votre rendement personnel pondéré par l'argent à $+12\%$. Votre timing a réduit votre rendement de **$-8$ points de pourcentage**.

---

## ⚖️ Ce qu'il Capture et Ce qu'il Ne Capture Pas

### Ce qu'il Capture
- **Impact du moment des dépôts/retraits :** Si vous avez ajouté des liquidités pendant les creux du marché (achat à bas prix) ou les sommets (achat au prix fort).
- **Impact de la taille des flux :** Les flux de trésorerie les plus importants ont un poids plus fort et un impact accru sur le MWRR, ce que reflète l'Effet de timing.
- **L'"écart de l'investisseur" (Investor Gap) :** la distance entre le rendement de la stratégie et le rendement effectivement obtenu par l'investisseur, due au timing et à la taille des flux de trésorerie.

### Ce qu'il Ne Capture Pas
- **Gain monétaire absolu :** Un Effet de timing positif de $+5$ pp peut exister même si le portefeuille est en perte nette (par exemple, si le TWRR est de $-20\%$ et le MWRR de $-15\%$). Utilisez le [P&L de la Période](period-pnl.md) pour évaluer les gains monétaires absolus.
- **Risque et volatilité :** Il n'indique pas le profil de risque ni la volatilité des actifs.
- **Impact distinct des taxes/frais :** l'Effet de timing ne décompose pas les taxes et les coûts ; les coûts et taxes éventuels peuvent être affichés séparément dans le P&L de la période.
- **Qualité intrinsèque des actifs :** Un Effet de timing élevé peut se produire sur un actif médiocre si vous l'achetez juste avant un rebond temporaire. Vérifiez toujours le [TWRR](twrr.md) pour juger de la qualité de vos actifs.

---

## 🖥️ Utilisation dans le Tableau de Bord
LibreFolio affiche l'Effet de timing dans la carte de **Rendements** du tableau de bord. Cette carte regroupe les indicateurs clés de votre performance d'investissement :

- **Effet de timing :** Différence entre le MWRR cumulé et le TWRR cumulé, montrant comment vos flux de trésorerie ont affecté vos rendements.
- **Simple ROI :** rendement en pourcentage intuitif pour la période. Il est utile pour lire rapidement le résultat, mais ne prend pas en compte le timing des flux avec la même précision que le MWRR.
- **TWRR Cumulé :** Rendement de la stratégie sous-jacente, neutralisant les impacts des flux de trésorerie.
- **MWRR Cumulé :** Rendement de votre capital réel, prenant en compte les flux de trésorerie.
- **MWRR Annualisé :** Le taux annuel composé de croissance de votre argent.

!!! note "Aide Contextuelle (Tooltip)"

    Différence entre le MWRR cumulé et le TWRR cumulé. Indique à quel point le moment et le montant de vos flux de trésorerie ont influencé votre rendement global.


---

## 🔗 Relation avec les Autres Métriques

- **[Simple ROI](roi.md) :** Mesure le gain ou la perte en pourcentage absolu par rapport au capital investi.
- **[TWRR](twrr.md) :** Mesure le rendement de la stratégie ou des actifs sous-jacents, en ignorant le moment des flux de trésorerie de l'investisseur.
- **[MWRR](mwrr.md) :** Mesure le rendement du capital de l'investisseur, en tenant compte à la fois de la performance des actifs et du moment des flux de trésorerie.
- **[P&L de la Période](period-pnl.md) :** Mesure le profit ou la perte monétaire absolue générée par le portefeuille au cours de la période sélectionnée.
