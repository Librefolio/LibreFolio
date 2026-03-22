# 📈 Rendements et taux de croissance

Cette page couvre les fondements mathématiques des **rendements d'investissement** — comment mesurer, comparer et annualiser les taux de croissance. Ces concepts sont utilisés dans les outils de mesure des **taux de change** de LibreFolio et dans l'analyse de portefeuille.

---

## 📊 Rendement simple (discret)

Le **rendement simple** sur une période est le changement en pourcentage :

$$
R_{simple} = \frac{P_{end} - P_{start}}{P_{start}} = \frac{P_{end}}{P_{start}} - 1
$$

!!! exemple
    Si EUR/USD passe de 1,10 à 1,14 :

    $$R = \frac{1,14 - 1,10}{1,10} = 0,0364 = 3,64\%$$

### 📊 Propriétés

- **Intuitif** : représente directement "combien vous avez gagné/perdu"
- **Non additif** : on ne peut pas simplement additionner les rendements simples sur plusieurs périodes pour obtenir le rendement total
- **Composition** : les rendements sur plusieurs périodes doivent être multipliés, et non additionnés

$$
R_{total} = (1 + R_1)(1 + R_2) \cdots (1 + R_n) - 1
$$

---

## 📐 Rendement logarithmique (continu)

Le **rendement logarithmique** est le logarithme naturel du rapport des prix :

$$
r_{log} = \ln\left(\frac{P_{end}}{P_{start}}\right) = \ln(P_{end}) - \ln(P_{start})
$$

### 📊 Propriétés

- **Additif dans le temps** : le rendement logarithmique total est la somme des rendements logarithmiques des sous-périodes

$$
r_{total} = r_1 + r_2 + \cdots + r_n
$$

- **Symétrique** : un mouvement de +5% suivi d'un mouvement de −5% ramène exactement au point de départ
- **Approximativement égal** au rendement simple pour les petites valeurs : $r_{log} \approx R_{simple}$ lorsque $R_{simple}$ est faible

### 🔄 Conversion

$$
r_{log} = \ln(1 + R_{simple}) \qquad R_{simple} = e^{r_{log}} - 1
$$

---

## 📅 Rendement annualisé

Pour comparer les rendements sur différentes périodes, nous les **annualisons** — en projetant le taux de croissance observé sur une année complète.

### 📈 Taux de croissance annuel composé (TCAC)

La méthode d'annualisation la plus courante. Étant donné un rendement total sur $d$ jours calendaires :

$$
R_{annual} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

C'est ce que l'outil [Mesures](../user/fx/detail/measures.md) de LibreFolio affiche.

!!! exemple
    EUR/USD passe de 1,10 à 1,14 sur 90 jours :

    $$R_{annual} = \left(\frac{1,14}{1,10}\right)^{365/90} - 1 = (1,0364)^{4,056} - 1 \approx 15,5\%$$

### 📐 Rendement logarithmique annualisé

Pour les rendements logarithmiques, l'annualisation est simplement un ajustement d'échelle :

$$
r_{annual} = r_{log} \times \frac{365}{d}
$$

Cette linéarité est l'un des avantages clés des rendements logarithmiques en finance quantitative.

---

## 🔄 Relation entre les rendements simples et logarithmiques

| Propriété | Rendement simple $R$ | Rendement logarithmique $r$ |
|----------|:---:|:---:|
| **Composition** | Multiplicatif : $(1+R_1)(1+R_2)$ | Additif : $r_1 + r_2$ |
| **Symétrie** | Asymétrique : +10% puis −10% ≠ 0 | Symétrique : +10% puis −10% = 0 |
| **Annualisation** | $(1+R)^{365/d} - 1$ | $r \times 365/d$ |
| **Rendements de portefeuille** | La somme pondérée fonctionne ✅ | La somme pondérée ne fonctionne pas ❌ |
| **Série temporelle** | Non additif ❌ | Additif ✅ |
| **Interprétation** | "J'ai gagné 5%" | "Le taux de croissance logarithmique était de 0,0488" |

!!! astuce "Quand utiliser l'un ou l'autre ?"
    - **Rendements simples** pour les rapports aux utilisateurs et le calcul des rendements au niveau du portefeuille
    - **Rendements logarithmiques** pour l'analyse statistique, l'estimation de la volatilité et les modèles de séries temporelles

---

## 📏 Conventions de décompte des jours

Le nombre de jours $d$ peut être calculé différemment selon la convention :

- **Réel/365** : jours calendaires (ce qu'utilise LibreFolio)
- **Réel/360** : jours calendaires sur une année de 360 jours (courant sur les marchés monétaires)
- **30/360** : suppose des mois de 30 jours et une année de 360 jours

Pour plus de détails, voir [Conventions de décompte des jours](day-count.md).

---

## ⚠️ Pièges

1. **Périodes très courtes** : annualiser un rendement de 3 jours peut produire des chiffres trompeurs (par exemple, un mouvement de 0,1% sur 3 jours → 12,5% annualisé)
2. **Prix négatifs** : les rendements logarithmiques ne sont pas définis pour des valeurs négatives — pas un problème pour les taux de change
3. **Fréquence de composition** : le TCAC suppose une composition continue ; les instruments réels peuvent être composés quotidiennement, mensuellement ou trimestriellement

