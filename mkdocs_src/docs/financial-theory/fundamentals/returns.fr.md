# 📈 Rendements et Taux de Croissance

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

- **Intuitif** : représente directement « combien vous avez gagné/perdu »
- **Non additif** : vous ne pouvez pas simplement additionner les rendements simples sur plusieurs périodes pour obtenir le rendement total
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

Pour comparer des rendements sur différentes périodes, nous les **annualisons** — en projetant le taux de croissance observé sur une année entière.

### 📈 Taux de Croissance Annuel Composé (CAGR)

La méthode d'annualisation la plus courante. Étant donné un rendement total sur $d$ jours calendaires :

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

C'est ce que l' [outil de mesure](../../user/fx/detail/measures.md) de LibreFolio affiche.

!!! example

    L'EUR/USD passe de 1,10 à 1,14 sur 90 jours :

    $$R_{annual} = \left(\frac{1.14}{1.10}\right)^{365/90} - 1 = (1.0364)^{4.056} - 1 \approx 15.5\%$$

### 📐 Rendement Log Annualisé

Pour les rendements logarithmiques, l'annualisation est simplement une mise à l'échelle :

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Cette linéarité est l'un des avantages clés des rendements logarithmiques en finance quantitative.

---

## 🔄 Relation Entre Rendements Simples et Log

| Propriété | Rendement Simple $R$ | Rendement Log $r$ |
|----------|:---:|:---:|
| **Composition** | Multiplicative : $(1+R_1)(1+R_2)$ | Additive : $r_1 + r_2$ |
| **Symétrie** | Asymétrique : +10 % puis −10 % ≠ 0 | Symétrique : +10 % puis −10 % = 0 |
| **Annualisation** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendements de portefeuille** | La somme pondérée fonctionne ✅ | La somme pondérée ne fonctionne pas ❌ |
| **Séries temporelles** | Non additif ❌ | Additif ✅ |
| **Interprétation** | « J'ai gagné 5 % » | « Le taux de croissance log était de 0,0488 » |

!!! tip "Lequel utiliser ?"

    - **Rendements simples** pour le reporting aux utilisateurs et le calcul des rendements au niveau du portefeuille
    - **Rendements log** pour l'analyse statistique, l'estimation de la volatilité et les modèles de séries temporelles

---

## 📏 Conventions de Comptage des Jours

Le nombre de jours $d$ peut être calculé différemment selon la convention :

- **Actual/365** : Jours calendaires (ce que LibreFolio utilise)
- **Actual/360** : Jours calendaires sur une année de 360 jours (courant sur les marchés monétaires)
- **30/360** : Suppose des mois de 30 jours et une année de 360 jours

Pour plus de détails, voir [Conventions de Comptage des Jours](day-count.md).

---

## 💰 Méthodes de Rendement de Portefeuille

Lorsqu'un portefeuille comporte des **flux de trésorerie** (dépôts, retraits), une seule formule de rendement ne suffit pas. Deux méthodes existent pour isoler la performance des effets des flux de trésorerie :

### ⏱️ Rendement Pondéré dans le Temps (TWR)

Élimine l'effet des flux de trésorerie en calculant les rendements des sous-périodes entre chaque événement de flux et en les enchaînant :

$$
R_{TWR} = \prod_{i=1}^{n} (1 + r_i) - 1
$$

- Mesure la **performance pure du portefeuille** indépendamment du moment des dépôts/retraits
- Utilisé par les gestionnaires de fonds pour le benchmarking (conforme aux normes GIPS)
- Non affecté par le comportement de l'investisseur (ajouter de l'argent aux sommets, retirer aux creux)

### 💵 Rendement Pondéré par l'Argent (MWR / IRR)

Prend en compte le **moment et la taille** des flux de trésorerie — le taux de rendement interne qui ramène la NPV de tous les flux à zéro :

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i}}
$$

où $CF_i$ est chaque flux de trésorerie (dépôts positifs, retraits négatifs, valeur finale du portefeuille positive).

- Mesure **l'expérience spécifique de l'investisseur** (votre rendement réel compte tenu du moment où vous avez ajouté/retiré des fonds)
- Pénalise un mauvais timing (déposer aux plus hauts, retirer aux plus bas)
- Utilisé pour la performance d'un portefeuille personnel

!!! info "Lequel utilise LibreFolio ?"

    LibreFolio calculera à la fois le TWR et le MWR dans le tableau de bord d'analyse du portefeuille. Le TWR pour la comparaison avec les benchmarks, le MWR pour l'évaluation de la performance personnelle.

---

## ⚠️ Pièges

1. **Périodes très courtes** : Annualiser un rendement sur 3 jours peut produire des chiffres trompeurs (ex: un mouvement de 0,1 % sur 3 jours → 12,5 % annualisé)
2. **Prix négatifs** : Les rendements log sont indéfinis pour les valeurs négatives — ce n'est pas un problème pour les taux FX
3. **Fréquence de composition** : Le CAGR suppose une composition continue ; les instruments du monde réel peuvent composer quotidiennement, mensuellement ou trimestriellement
