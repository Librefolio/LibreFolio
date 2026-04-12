# 📈 Croissance Linéaire

Un benchmark de croissance linéaire représente l'**intérêt simple** — la valeur augmente d'un montant absolu fixe à chaque période.

---

## 💡 Signification Financière

Ceci modélise le scénario où vous **ne réinvestissez pas** les gains (dividendes, intérêts, coupons) : les paiements en espèces sont reçus mais mis de côté, de sorte que seul le capital initial génère des rendements.

Si, au contraire, vous **réinvestissez** ces gains — soit manuellement, soit automatiquement via des instruments de capitalisation (par exemple, des ETF de capitalisation, qui réinvestissent les dividendes en interne et bénéficient d'un [report d'imposition](../../fundamentals/taxation.md#tax-deferral-advantage)) — vous devez vous attendre à une **[croissance composée](compound.md)**, où les rendements génèrent d'autres rendements.

En pratique, la différence entre la croissance linéaire et la croissance composée s'accentue considérablement sur le long terme. C'est pourquoi le benchmark Linéaire apparaît comme une ligne droite tandis que le benchmark Composé s'incurve vers le haut de manière exponentielle.

!!! abstract "Plus-values et moins-values"

    Lors de la vente d'un actif au-dessus de son prix d'achat, la différence est une **plus-value** ;
    en dessous, une **moins-value**. Chaque juridiction possède ses propres règles concernant les taux d'imposition,
    les seuils de période de détention, la durée du report des pertes et les méthodes de calcul
    (FIFO, LIFO, identification spécifique). Pour un aperçu théorique, voir
    [Fiscalité et efficacité fiscale](../../fundamentals/taxation.md).

---

## 🔢 Formule Mathématique

$$
y(t) = y_0 \cdot (1 + r \cdot t)
$$

où :

- $y_0$ est la valeur de départ (premier point de données du graphique),
- $r$ est le taux de croissance annuel (exprimé sous forme décimale, par exemple 0,07 pour 7 %),
- $t$ est le temps en années depuis le début.

Ceci est équivalent à la formule de l'**intérêt simple** $A = P(1 + rt)$, où $t$ est exprimé en années en utilisant la [Convention de comptage des jours](../../fundamentals/day-count.md) applicable.

---

## ⚙️ Paramètres

| Paramètre | Clé | Par défaut | Description |
|---|---|---|---|
| Taux Annuel | `annualRate` | 5 | Taux de croissance en pourcentage par an. |
| Décalage | `offset` | 0 | Décalage vertical en % de la valeur de base. |

---

## 🔍 Interprétation

La ligne est parfaitement droite sur une échelle linéaire. Tout point où le prix réel est *au-dessus* de la ligne signifie que l'actif a surperformé la cible ; tout point *en dessous* signifie une sous-performance. Comme la croissance est additive, la ligne s'incurve vers le bas sur une échelle logarithmique — ce qui permet de la distinguer visuellement et aisément d'une croissance composée.

:material-link: [Intérêt Simple sur Wikipedia](https://en.wikipedia.org/wiki/Interest#Simple_interest){ target="_blank" }
