# 📊 Croissance Composée

Un benchmark de croissance composée représente les **intérêts composés** — la valeur croît de manière exponentielle, ce qui signifie que les rendements sont réinvestis.

---

## 💡 Signification Financière

Il s'agit du modèle de croissance naturel pour la plupart des actifs financiers et de l'hypothèse standard dans l'analyse des flux de trésorerie actualisés (DCF). La croissance composée produit une courbe exponentielle qui s'accélère avec le temps — le fondement de la constitution d'un patrimoine à long terme.

---

## 🔢 Formule Mathématique

$$
y(t) = y_0 \cdot (1 + r)^t
$$

où :

- $y_0$ est la valeur initiale,
- $r$ est le taux de croissance annuel (décimal),
- $t$ est le temps en années depuis le début.

Ceci est équivalent à la formule des **intérêts composés** $A = P(1 + r)^t$ avec une capitalisation annuelle. La formule généralisée avec $n$ périodes de capitalisation par an est :

$$
A = P \cdot \left(1 + \frac{r}{n}\right)^{n \cdot t}
$$

Le backend de LibreFolio prend en charge les fréquences de capitalisation suivantes : **Annuelle** ($n=1$), **Semestrielle** ($n=2$), **Trimestrielle** ($n=4$), **Mensuelle** ($n=12$), **Quotidienne** ($n=365$), et **Continue** ($n \to \infty$).

Lorsque $n \to \infty$ (capitalisation continue) :

$$
A = P \cdot e^{r \cdot t}
$$

---

## 🔄 Calcul Itératif (Pas Quotidien)

Dans LibreFolio, la courbe composée est calculée de manière **itérative** plutôt qu'en appelant `pow()` pour chaque point de données. C'est à la fois plus efficace et instructif :

$$
\text{dailyFactor} = (1 + r)^{1/365}
$$

Ensuite, pour chaque jour successif :

$$
y_{i+1} = y_i \cdot \text{dailyFactor}
$$

Ceci est mathématiquement équivalent à la forme analytique $y_0(1+r)^t$ mais remplace $N$ opérations de puissance coûteuses par $N$ multiplications simples — le même principe utilisé par les banques pour capitaliser les intérêts composés quotidiennement.

!!! tip "Règle de 72"

    Un raccourci mental rapide : un investissement croissant à $r$% par an doublera
    approximativement en $72 / r$ ans. À 7% → ~10,3 ans.

---

## ⚙️ Paramètres

| Paramètre | Clé | Par défaut | Description |
|---|---|---|---|
| Taux Annuel | `annualRate` | 7 | Taux de croissance composée en pourcentage par an. |
| Décalage | `offset` | 0 | Décalage vertical en % de la valeur de base. |

---

## 🔍 Interprétation

La courbe est droite sur une échelle **logarithmique** — c'est le signe distinctif d'une croissance exponentielle. Superposer un benchmark composé sur un graphique à échelle logarithmique est le moyen le plus clair de juger si un actif croît plus rapidement ou plus lentement qu'un taux cible.

:material-link: [Intérêts Composés sur Wikipédia](https://en.wikipedia.org/wiki/Compound_interest){ target="_blank" }
