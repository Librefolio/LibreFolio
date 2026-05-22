# 💰 Fiscalité et efficacité fiscale

Comprendre la fiscalité est essentiel pour maximiser les rendements d'investissement à long terme. Cette page couvre les fondements théoriques — **et non les règles spécifiques à une juridiction** — de l'interaction entre les impôts et la croissance d'un portefeuille.

!!! warning "Ceci ne constitue pas un conseil financier"

    LibreFolio ne fournit pas de conseils fiscaux. Chaque juridiction possède des règles différentes concernant les taux d'imposition, les périodes de détention, le report des pertes et les méthodes d'appariement. Consultez un professionnel de la fiscalité qualifié pour votre situation spécifique.

---

## 📊 Plus-values et Moins-values

Lorsque vous vendez un actif, la différence entre le prix de vente et le prix d'achat détermine votre **plus-value** ou votre **moins-value** :

$$
\text{Plus-value} = P_{vente} - P_{achat} - \text{Frais}
$$

- **Plus-value** ($> 0$) : Vous avez vendu plus cher que vous n'avez acheté → événement imposable dans la plupart des juridictions.
- **Moins-value** ($< 0$) : Vous avez vendu moins cher que vous n'avez acheté → peut compenser des gains futurs.

### 🔄 Réalisé vs Non réalisé

| Type | Définition | Impact Fiscal |
|------|-----------|------------|
| **Non réalisé** (gain/perte latent) | Actif toujours détenu ; le gain/perte n'existe que sur le papier | Non imposé (dans la plupart des juridictions) |
| **Réalisé** | Actif vendu ; le gain ou la perte est réalisé(e) | Déclenche généralement un événement fiscal |

Cette distinction est le fondement du **report d'imposition** — en ne vendant pas, vous différez l'événement fiscal indéfiniment.

### 📋 Méthodes d'appariement

Lorsque vous avez acheté le même actif plusieurs fois à des prix différents, à quel achat une vente est-elle associée ?

| Méthode | Règle | Effet |
|--------|------|--------|
| **FIFO** (First In, First Out) | Les parts les plus anciennes sont vendues en premier | Méthode par défaut la plus courante |
| **LIFO** (Last In, First Out) | Les parts les plus récentes sont vendues en premier | Peut minimiser/maximiser les gains |
| **Identification spécifique** | Vous choisissez quel lot vendre | Optimisation fiscale maximale |

!!! info "LibreFolio utilise le FIFO"

    LibreFolio calcule les plus-values en utilisant l'appariement **FIFO** lors de l'exécution. L'appariement est calculé à la demande et n'est pas stocké dans la base de données.

---

## 🔄 Report des pertes (Loss Carry-Forward)

La plupart des juridictions vous permettent de **reporter** les moins-values pour compenser les plus-values futures :

$$
\text{Gain Imposable}_t = \max(0, \text{Gains Réalisés}_t - \text{Pertes Reportées}_{t-1})
$$

Paramètres clés qui varient selon la juridiction :

- ⏳ **Durée** : Pendant combien de temps les pertes peuvent être reportées (ex: 4 ans en Italie, illimité en Allemagne, 7 ans aux USA pour certains types).
- 📊 **Portée** : Si les pertes d'une classe d'actifs peuvent compenser les gains d'une autre.
- 🚫 **Règles de "Wash sale"** (ventes fictives) : Restrictions sur le rachat d'un actif vendu dans un court intervalle pour pouvoir déduire la perte.

---

## ⏳ Avantage du report d'imposition { #tax-deferral-advantage }

L'un des concepts les plus puissants de l'investissement fiscalement efficace est de **différer** l'événement fiscal le plus longtemps possible. Les mathématiques favorisent fortement le report :

### 📐 La Formule

Comparez deux scénarios sur $n$ années avec un rendement annuel $r$ et un taux d'imposition $\tau$ :

**Scénario A — Imposition annuelle** (ex: fonds de distribution) :

$$
V_A = P \cdot (1 + r \cdot (1 - \tau))^n
$$

**Scénario B — Imposition à la fin** (ex: fonds de capitalisation) :

$$
V_B = P \cdot (1 + r)^n - \tau \cdot [P \cdot (1 + r)^n - P] = P \cdot [(1 + r)^n \cdot (1 - \tau) + \tau]
$$

### 📊 Exemple Numérique

Avec $P = 10{,}000$, $r = 7\%$, $\tau = 26\%$, $n = 20$ ans :

| Scénario | Valeur Finale | Rendement Effectif |
|----------|------------|-----------------|
| Imposition annuelle | 28 398 € | 5,18% par an |
| Imposition à la fin | 31 616 € | 5,93% par an |
| **Avantage du report** | **+3 218 €** | **+0,75% par an** |

L'avantage croît de manière exponentielle avec le temps — sur 30 ans, l'écart s'élargit à plus de 8 000 € pour le même investissement de 10 000 €.

---

## 📦 Instruments de Capitalisation vs Distribution

Cet avantage du report se manifeste directement dans le choix entre les véhicules d'investissement de capitalisation et de distribution :

### 📈 Capitalisation (ex: ETF Acc)

- Les dividendes sont **réinvestis au sein du fonds**.
- **Aucun événement imposable** tant que vous ne vendez pas les parts du fonds.
- Plein bénéfice de la [croissance composée](../technical-analysis/synthetic-benchmarks/compound.md) sur le montant avant fiscalité.
- Idéal pour les investisseurs à long terme recherchant une croissance maximale.

### 💵 Distribution (ex: ETF Dist)

- Les dividendes vous sont **versés** périodiquement.
- Chaque distribution est un **événement imposable** (imposé immédiatement).
- Vous recevez des liquidités mais perdez le bénéfice des intérêts composés sur la portion imposée.
- Utile si vous avez besoin de revenus provenant de vos investissements.

### 🔗 Lien avec les modèles de croissance

- **[Croissance Linéaire](../technical-analysis/synthetic-benchmarks/linear.md)** approxime le comportement lorsque les dividendes sont reçus mais **non réinvestis** — la croissance est additive.
- **[Croissance Composée](../technical-analysis/synthetic-benchmarks/compound.md)** représente le cas idéal avec réinvestissement total — la croissance est multiplicative et bénéficie le plus du report d'imposition.

---

## ⚠️ Considérations spécifiques aux juridictions

Chaque pays possède son propre cadre fiscal. Paramètres clés qui varient :

| Paramètre | Exemples |
|-----------|---------|
| **Taux d'imposition des plus-values** | 26% (Italie), 25% (Allemagne), 0-20% (USA, selon la période de détention) |
| **Avantages selon la durée de détention** | Certains pays réduisent les taux pour les détentions à long terme |
| **Durée du report des pertes** | 4 ans (Italie), illimité (Allemagne), 7 ans (USA pour certains types) |
| **Traités de double imposition** | Affectent les dividendes des actions étrangères |
| **Abattements fiscaux** | Seuils annuels en dessous desquels les gains ne sont pas imposés |
| **Règles spécifiques aux cryptos** | Évoluent rapidement ; souvent traitées différemment des actifs traditionnels |

!!! abstract "Le rôle de LibreFolio"

    LibreFolio suit vos transactions et calcule les gains/pertes réalisés en utilisant l'appariement FIFO. Il fournit le **socle de données** pour le reporting fiscal, mais ne génère pas de déclarations d'impôts et n'applique pas de règles spécifiques à une juridiction. Exportez vos données de transaction et consultez un professionnel de la fiscalité.

---

## 🔗 Liens connexes

- 📈 **[Rendements & Taux de Croissance](returns.md)** — Comment mesurer et annualiser les rendements
- 🎯 **[Benchmarks Synthétiques](../technical-analysis/synthetic-benchmarks/index.md)** — Visualisation croissance linéaire vs composée
- 📅 **[Conventions de calcul des jours](day-count.md)** — Comment les périodes temporelles affectent les calculs
