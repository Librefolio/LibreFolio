# 💰 Fiscalité & Efficience Fiscale

Comprendre la fiscalité est essentiel pour maximiser les rendements des investissements à long terme. Cette page couvre les fondements théoriques — **pas les règles spécifiques à chaque juridiction** — de l'interaction entre les impôts et la croissance du portefeuille.

!!! warning "Ceci n'est pas un conseil financier"

    LibreFolio ne fournit pas de conseil fiscal. Chaque juridiction a ses propres règles concernant les taux d'imposition, les durées de détention, le report des pertes et les méthodes d'appariement. Consultez un professionnel fiscal qualifié pour votre situation personnelle.

---

## 📊 Plus-values et Moins-values

Lorsque vous vendez un actif, la différence entre le prix de vente et le prix d'achat détermine votre **plus-value** ou **moins-value** :

$$
\text{Plus-value} = P_{vente} - P_{achat} - \text{Frais}
$$

- **Plus-value** ($> 0$) : Vous avez vendu plus cher que vous n'avez payé → événement imposable dans la plupart des juridictions
- **Moins-value** ($< 0$) : Vous avez vendu moins cher que vous n'avez payé → peut compenser des gains futurs

### 🔄 Réalisées vs Non Réalisées

| Type | Définition | Impact Fiscal |
|------|-----------|--------------|
| **Non réalisées** (gain/perte latent) | Actif encore détenu ; gain/perte n'existe que sur le papier | Non imposé (dans la plupart des juridictions) |
| **Réalisées** | Actif vendu ; gain/perte est concrétisé | Déclenche généralement un événement imposable |

Cette distinction est le fondement du **report d'imposition** — en ne vendant pas, vous reportez indéfiniment l'événement imposable.

### 📋 Méthodes d'Appariement

Lorsque vous avez acheté le même actif plusieurs fois à des prix différents, quel achat correspond à une vente ?

| Méthode | Règle | Effet |
|---------|-------|-------|
| **FIFO** (Premier Entré, Premier Sorti) | Les parts les plus anciennes sont vendues en premier | Défaut le plus courant |
| **LIFO** (Dernier Entré, Premier Sorti) | Les parts les plus récentes sont vendues en premier | Peut minimiser/maximiser les gains |
| **Identification Spécifique** | Vous choisissez quel lot vendre | Optimisation fiscale maximale |

!!! info "LibreFolio utilise le FIFO"

    LibreFolio calcule les plus-values en utilisant l'appariement **FIFO** à l'exécution. L'appariement est calculé à la demande, non stocké dans la base de données.

---

## 🔄 Report des Pertes

La plupart des juridictions permettent de **reporter** les moins-values pour compenser les plus-values futures :

$$
\text{Gain Imposable}_t = \max(0, \text{Plus-values Réalisées}_t - \text{Pertes Reportées}_{t-1})
$$

Paramètres clés qui varient selon la juridiction :

- ⏳ **Durée** : Combien de temps les pertes peuvent être reportées (ex. 4 ans en Italie, illimité en Allemagne, 7 ans aux États-Unis pour certains types)
- 📊 **Portée** : Si les pertes d'une classe d'actifs peuvent compenser des gains d'une autre
- 🚫 **Règles sur les ventes fictives** : Restrictions sur le rachat d'un actif vendu dans un court délai pour réclamer la perte

---

## ⏳ Avantage du Report d'Imposition { #tax-deferral-advantage }

L'un des concepts les plus puissants dans l'investissement fiscalement efficient est de **reporter** l'événement imposable le plus longtemps possible. Les mathématiques favorisent fortement le report :

### 📐 La Formule

Comparez deux scénarios sur $n$ années avec un rendement annuel $r$ et un taux d'imposition $\tau$ :

**Scénario A — Imposition annuelle** (ex. fonds distribuant) :

$$
V_A = P \cdot (1 + r \cdot (1 - \tau))^n
$$

**Scénario B — Imposition à la fin** (ex. fonds capitalisant) :

$$
V_B = P \cdot (1 + r)^n - \tau \cdot [P \cdot (1 + r)^n - P] = P \cdot [(1 + r)^n \cdot (1 - \tau) + \tau]
$$

### 📊 Exemple Numérique

Avec $P = 10\,000$, $r = 7\%$, $\tau = 26\%$, $n = 20$ ans :

| Scénario | Valeur Finale | Rendement Effectif |
|----------|--------------|-------------------|
| Imposition annuelle | 28 398 € | 5,18 % p.a. |
| Imposition à la fin | 31 616 € | 5,93 % p.a. |
| **Avantage du report** | **+3 218 €** | **+0,75 % p.a.** |

L'avantage croît exponentiellement avec le temps — sur 30 ans, l'écart dépasse 8 000 € sur le même investissement de 10 000 €.

---

## 📦 Instruments Capitalisants vs Distribuants

Cet avantage du report se manifeste directement dans le choix entre véhicules d'investissement capitalisants et distribuants :

### 📈 Capitalisant (ex. ETF Acc)

- Les dividendes sont **réinvestis en interne** par le fonds
- **Aucun événement imposable** tant que vous ne vendez pas les parts du fonds
- Plein bénéfice de la [croissance composée](synthetic-benchmarks.md#compound-growth) sur le montant brut d'impôts
- Idéal pour les investisseurs à long terme recherchant une croissance maximale

### 💵 Distribuant (ex. ETF Dist)

- Les dividendes sont **versés** périodiquement
- Chaque distribution est un **événement imposable** (imposé immédiatement)
- Vous recevez des liquidités mais perdez le bénéfice de la capitalisation sur la partie imposée
- Utile si vous avez besoin de revenus de vos investissements

### 🔗 Lien avec les Modèles de Croissance

- **[Croissance Linéaire](synthetic-benchmarks.md#linear-growth)** approxime le comportement lorsque les dividendes sont reçus mais **non réinvestis** — la croissance est additive
- **[Croissance Composée](synthetic-benchmarks.md#compound-growth)** représente le cas idéal avec réinvestissement complet — la croissance est multiplicative et bénéficie le plus du report d'imposition

---

## ⚠️ Considérations Spécifiques par Juridiction

Chaque pays a son propre cadre fiscal. Paramètres clés qui varient :

| Paramètre | Exemples |
|-----------|---------|
| **Taux d'imposition des plus-values** | 26 % (Italie), 25 % (Allemagne), 0-20 % (États-Unis, selon la durée de détention) |
| **Avantages liés à la durée de détention** | Certains pays réduisent les taux pour les détentions longues |
| **Durée du report des pertes** | 4 ans (Italie), illimité (Allemagne), 7 ans (États-Unis pour certains types) |
| **Conventions contre la double imposition** | Affectent les dividendes d'actions étrangères |
| **Abattements fiscaux** | Seuils annuels en dessous desquels les gains ne sont pas imposés |
| **Règles spécifiques aux cryptos** | En évolution rapide ; souvent traitées différemment des actifs traditionnels |

!!! abstract "Le rôle de LibreFolio"

    LibreFolio suit vos transactions et calcule les plus-values/moins-values réalisées en utilisant l'appariement FIFO. Il fournit les **données de base** pour la déclaration fiscale, mais ne génère pas de déclarations ni n'applique de règles spécifiques à une juridiction. Exportez vos données de transactions et consultez un professionnel fiscal.

---

## 🔗 Connexes

- 📈 **[Rendements et Taux de Croissance](returns.md)** — Comment mesurer et annualiser les rendements
- 🎯 **[Références Synthétiques](synthetic-benchmarks.md)** — Visualisation croissance linéaire vs composée
- 📅 **[Conventions de Comptage des Jours](day-count.md)** — Comment les périodes temporelles affectent les calculs

