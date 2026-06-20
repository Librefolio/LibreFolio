# ⚖️ Allocation d'actifs

L'allocation d'actifs est le processus consistant à décider **comment répartir votre portefeuille** entre différentes classes d'actifs. Les recherches montrent systématiquement que l'allocation d'actifs explique la majorité de la variabilité du rendement d'un portefeuille — plus que la sélection de titres individuels ou le timing du marché.

---

## 📊 Allocation Stratégique vs Tactique

### 🏗️ Allocation Stratégique d'Actifs (SAA)

Un **objectif à long terme** basé sur votre tolérance au risque, votre horizon temporel et vos objectifs :

| Profil | Actions | Obligations | Actifs alternatifs | Liquidités |
|---------|--------|-------|-------------|------|
| Agressif (horizon long) | 80-90% | 5-15% | 5-10% | 0-5% |
| Équilibré | 50-60% | 30-40% | 5-10% | 5% |
| Prudent (horizon court) | 20-30% | 50-60% | 5-10% | 10-20% |

La SAA est revue peu fréquemment (annuellement ou lors de changements de vie majeurs).

### 🎯 Allocation Tactique d'Actifs (TAA)

Des **écarts à court terme** par rapport à l'objectif stratégique pour exploiter des opportunités de marché perçues :

- Surpondérer une classe d'actifs censée surperformer
- Réduire l'exposition à une classe d'actifs montrant des signes de faiblesse
- Ajuster en fonction des conditions macroéconomiques

!!! warning "La TAA est difficile"

    Réussir le timing du marché est extrêmement difficile. La plupart des recherches académiques montrent que les ajustements tactiques nuisent plus qu'ils n'aident les investisseurs moyens.

---

## 📈 Glide Path & Stratégie à Date Cible

Un **glide path** (trajectoire de glissement) déplace progressivement l'allocation d'un profil agressif (plus d'actions) vers un profil prudent (plus d'obligations) à mesure que l'investisseur approche de sa date cible (généralement la retraite) :

$$
w_{stocks}(t) = w_{max} - (w_{max} - w_{min}) \cdot \frac{t}{T}
$$

où $t$ est le nombre d'années écoulées et $T$ est le temps restant jusqu'à la date cible.

### 📉 La Logique

- **Les jeunes investisseurs** ont un horizon temporel long → peuvent tolérer la volatilité à court terme → devraient détenir plus d'actions
- **Les investisseurs proches de la retraite** ont besoin de préservation du capital → devraient détenir plus d'obligations
- Le glide path automatise cette transition

---

## 🔄 Rééquilibrage

Au fil du temps, les mouvements de prix des actifs entraînent une **dérive** du portefeuille par rapport à son allocation cible. Le rééquilibrage rétablit les pondérations initiales.

### 📊 Méthodes de Rééquilibrage

| Méthode | Déclencheur | Avantages | Inconvénients |
|--------|---------|------|------|
| **Calendrier** | Calendrier fixe (mensuel, trimestriel) | Simple, prévisible | Peut déclencher des transactions inutiles |
| **Seuil** | Quand l'allocation dérive de X% | Transactions uniquement si nécessaire | Nécessite un suivi |
| **Hybride** | Vérification calendrier, transaction si dépassement de seuil | Le meilleur des deux | Légèrement plus complexe |

### 📐 Bonus de Rééquilibrage

Dans un portefeuille d'actifs volatils et non corrélés, le rééquilibrage systématique génère un **bonus de rééquilibrage** — un léger rendement excédentaire provenant de la discipline consistant à « acheter bas, vendre haut » automatiquement :

$$
R_{rebalanced} \approx R_{buy\&hold} + \frac{1}{2} \sum_i w_i \sigma_i^2 (1 - \rho_{avg})
$$

Le bonus est plus important lorsque les volatilités sont élevées et les corrélations faibles.

---

## 🌍 Diversification Géographique

Au-delà de l'allocation par classe d'actifs, la diversification géographique répartit le risque entre différentes économies :

| Région | Rôle | Risque Devise |
|--------|------|---------------|
| Domestique | Positions principales, pas de risque FX | Aucun |
| Développées (US, EU, JP) | Croissance + stabilité | Modéré |
| Émergentes (CN, IN, BR) | Potentiel de croissance plus élevé | Plus élevé |

!!! info "Couverture devise"

    Les investissements étrangers introduisent un [risque FX](../../user/fx/index.md). Certains ETF proposent des variantes couvertes qui neutralisent l'exposition aux devises, au coût de la prime de couverture.

---

## 🔗 Liens connexes

- 🔀 **[Diversification](diversification.md)** — Les mathématiques derrière les décisions d'allocation
- 📊 **[Métriques de Risque](../technical-analysis/risk-metrics/index.md)** — Mesurer le risque du portefeuille
- 📊 **[Types d'Actifs](../instruments/asset-types/index.md)** — Les classes d'actifs pour l'allocation
- 💰 **[Fiscalité](../fundamentals/taxation.md)** — Stratégies d'allocation optimisées fiscalement
