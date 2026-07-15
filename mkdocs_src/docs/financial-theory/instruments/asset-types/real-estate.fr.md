# ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" style="vertical-align: middle;" } P2P / Crowdfunding

Les plateformes **P2P / Crowdfunding** permettent aux investisseurs de participer à des projets immobiliers ou à des prêts à la consommation/aux entreprises avec des montants relativement faibles. Ces instruments offrent généralement des paiements d'intérêts fixes ou variables et ont une date d'échéance définie.

---

## 🔑 Caractéristiques clés

| Propriété | Détail |
|-----------|--------|
| **Code dans LibreFolio** | `CROWDFUND` |
| **Évaluation** | Non coté en bourse — la valeur correspond généralement au capital investi |
| **Devise** | Libellé dans la devise de fonctionnement de la plateforme |
| **Revenus** | Paiements d'intérêts périodiques (mensuels, trimestriels ou à l'échéance) |
| **Liquidité** | Très faible — les fonds sont bloqués jusqu'à l'échéance ou le rachat |
| **Fournisseurs typiques** | Scheduled Investment, Manual |

---

## 📊 Comment ça fonctionne

### 🏗️ Crowdfunding immobilier

1. Une plateforme liste un projet immobilier nécessitant un financement
2. Plusieurs investisseurs contribuent avec des montants modestes (500 € – 10 000 € en général)
3. Le projet verse des intérêts sur le capital investi
4. À l'échéance, le capital est remboursé (si le projet réussit)

### 💸 Prêt P2P

1. Les emprunteurs demandent des prêts via une plateforme
2. Les investisseurs financent des portions de prêts
3. Les emprunteurs remboursent le capital + les intérêts sur la durée du prêt
4. La plateforme distribue les paiements aux investisseurs

---

## ⚠️ Facteurs de risque

| Risque | Description |
|--------|-------------|
| **Risque de défaut** | L'emprunteur/le projet peut ne pas rembourser |
| **Risque de liquidité** | Impossible de vendre avant l'échéance (contrairement aux actions) |
| **Risque de plateforme** | La plateforme elle-même peut faire faillite |
| **Risque de concentration** | Chaque investissement est un seul projet/emprunteur |

---

## 🔧 Modélisation dans LibreFolio

Le fournisseur **Scheduled Investment** est conçu pour ces instruments. Il génère :

- **[Événements d'intérêts](../asset-events/interest.md)** — Paiements de coupons périodiques basés sur le taux et le calendrier configurés
- **[Événements de règlement à échéance](../asset-events/maturity-settlement.md)** — Remboursement final du capital à la fin du terme
- **[Événements d'ajustement de prix](../asset-events/price-adjustment.md)** — Dépréciations en cas de sous-performance du projet

---

## 🔗 Liens connexes

- 📈 **[Événements d'intérêts](../asset-events/interest.md)** — Comment fonctionne l'accumulation des intérêts
- 🏁 **[Règlement à échéance](../asset-events/maturity-settlement.md)** — Remboursement du capital en fin de vie
- 📅 **[Conventions de calcul des jours](../../fundamentals/day-count.md)** — Comment les périodes d'intérêts sont calculées
