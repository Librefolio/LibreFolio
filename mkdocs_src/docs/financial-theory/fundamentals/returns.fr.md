# 📈 Rendements & Taux de croissance

Cette page couvre les fondements mathématiques des **rendements d'investissement** — comment mesurer, comparer et annualiser les taux de croissance. Ces concepts sont utilisés dans l'ensemble des outils de mesure et des analyses de portefeuille de LibreFolio.

---

## 📊 Rendement Simple (Discret)

Le **rendement simple** sur une période est la variation en pourcentage :

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! example

    Si l'EUR/USD passe de 1,10 à 1,14 :

    $$R = \frac{1.14 - 1.10}{1.10} = 0.0364 = 3.64\%$$

### 📊 Propriétés

- **Intuitif** : représente directement le montant gagné ou perdu
- **Non additif** : on ne peut pas simplement sommer les rendements simples sur plusieurs périodes pour obtenir le rendement total
- **Composition** : les rendements multi-périodes doivent être **multipliés**, et non additionnés

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rendement Logarithmique (Continu)

Le **rendement logarithmique** est le logarithme naturel du ratio des prix :

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Propriétés

- **Additif dans le temps** : rendement logarithmique total = somme des rendements logarithmiques des sous-périodes

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Symétrique** : une hausse de +5 % suivie d'une baisse de −5 % revient exactement au point de départ
- **Approximativement égal** au rendement simple pour les petites valeurs : $r_{log} \approx R_{simple}$ lorsque $R_{simple}$ est faible

### 🔄 Conversion

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rendement Annualisé

Pour comparer des rendements sur différentes périodes, nous les **annualisons** — en projetant le taux de croissance observé sur une année complète.

### 📈 Taux de Croissance Annuel Composé (CAGR)

La méthode d'annualisation la plus courante. Étant donné un rendement total sur $d$ jours calendaires :

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

C'est ce que l'outil [Measures](../../user/fx/detail/measures.md) de LibreFolio affiche.

!!! example

    L'EUR/USD passe de 1,10 à 1,14 sur 90 jours :

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendement Logarithmique Annualisé

Pour les rendements logarithmiques, l'annualisation est simplement une mise à l'échelle :

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Cette linéarité est l'un des avantages clés des rendements logarithmiques en finance quantitative.

---

## 🔄 Relation Entre Rendements Simples et Logarithmiques

| Propriété | Rendement Simple $R$ | Rendement Logarithmique $r$ |
|----------|:---:|:---:|
| **Composition** | Multiplicative : $(1+R_1)(1+R_2)$ | Additive : $r_1 + r_2$ |
| **Symétrie** | Asymétrique : +10% puis −10% ≠ 0 | Symétrique : +10% puis −10% = 0 |
| **Annualisation** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendements de portefeuille** | La somme pondérée fonctionne ✅ | La somme pondérée ne fonctionne pas ❌ |
| **Séries temporelles** | Non additif ❌ | Additif ✅ |
| **Interprétation** | « J'ai gagné 5 % » | « Le taux de croissance log était de 0,0488 » |

!!! tip "Lequel utiliser ?"

    - **Rendements simples** pour le reporting aux utilisateurs et le calcul des rendements au niveau du portefeuille
    - **Rendements logarithmiques** pour l'analyse statistique, l'estimation de la volatilité et les modèles de séries temporelles

---

## 📏 Conventions de Comptage des Jours

Le nombre de jours $d$ peut être calculé différemment selon la convention :

- **Actual/365** : Jours calendaires (ce que LibreFolio utilise)
- **Actual/360** : Jours calendaires sur une année de 360 jours (courant sur les marchés monétaires)
- **30/360** : Suppose des mois de 30 jours et une année de 360 jours

Pour plus de détails, voir [Conventions de comptage des jours](day-count.md).

---

## ⚠️ Pièges

1. **Périodes très courtes** : Annualiser un rendement sur 3 jours peut produire des chiffres trompeurs (ex: une variation de 0,1 % sur 3 jours → 12,5 % annualisé)
2. **Prix négatifs** : Les rendements logarithmiques ne sont pas définis pour les valeurs négatives — ce n'est pas un problème pour les taux de change
3. **Fréquence de composition** : Le CAGR suppose une composition continue ; les instruments réels peuvent composer quotidiennement, mensuellement ou trimestriellement
