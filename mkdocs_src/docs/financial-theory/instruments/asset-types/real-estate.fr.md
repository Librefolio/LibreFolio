# ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" style="vertical-align: middle;" } P2P / Crowdfunding

Les plateformes de **P2P / Crowdfunding** permettent aux investisseurs de participer à des projets immobiliers ou à des prêts aux particuliers/entreprises avec des montants relativement faibles. Ces instruments offrent généralement des paiements d'intérêts fixes ou variables et ont une date d'échéance définie.

---

## 🔑 Caractéristiques Clés

| Propriété | Détail |
|----------|--------|
| **Code dans LibreFolio** | `CROWDFUND` |
| **Valorisation** | Non coté en bourse — la valeur est généralement le capital investi |
| **Devise** | Libellé dans la devise d'exploitation de la plateforme |
| **Revenus** | Paiements d'intérêts périodiques (mensuels, trimestriels ou à l'échéance) |
| **Liquidité** | Très faible — les fonds sont bloqués jusqu'à l'échéance ou au rachat |
| **Fournisseurs types** | Scheduled Investment, Manual |

---

## 📊 Fonctionnement

### 🏗️ Crowdfunding Immobilier

1. Une plateforme liste un projet immobilier nécessitant un financement
2. Plusieurs investisseurs contribuent avec de petits montants (typiquement 500 € – 10 000 €)
3. Le projet verse des intérêts sur le capital investi
4. À l'échéance, le capital est restitué (si le projet réussit)

### 💸 Prêt P2P (Peer-to-Peer)

1. Des emprunteurs demandent des prêts via une plateforme
2. Des investisseurs financent des portions de ces prêts
3. Les emprunteurs remboursent le capital + les intérêts sur la durée du prêt
4. La plateforme distribue les paiements aux investisseurs

---

## ⚠️ Facteurs de Risque

| Risque | Description |
|------|-------------|
| **Risque de défaut** | L'emprunteur ou le projet peut faire défaut de paiement |
| **Risque de liquidité** | Impossible de vendre avant l'échéance (contrairement aux actions) |
| **Risque de plateforme** | La plateforme elle-même peut faire faillite |
| **Risque de concentration** | Chaque investissement concerne un seul projet/emprunteur |

---

## 🔧 Modélisation dans LibreFolio

Le fournisseur **Scheduled Investment** est conçu pour ces instruments. Il génère :

- **[Événements d'intérêts](../asset-events/interest.md)** — Paiements de coupons périodiques basés sur le taux et le calendrier configurés
- **[Événements de règlement à l'échéance](../asset-events/maturity-settlement.md)** — Retour final du capital à l'échéance
- **[Événements d'ajustement de prix](../asset-events/price-adjustment.md)** — Dépréciations si le projet est sous-performant

---

## 🔗 Liens Connexes

- 📈 **[Événements d'intérêts](../asset-events/interest.md)** — Fonctionnement du calcul des intérêts
- 🏁 **[Règlement à l'échéance](../asset-events/maturity-settlement.md)** — Retour du capital en fin de vie
- 📅 **[Conventions de comptage des jours](../../fundamentals/day-count.md)** — Calcul des périodes d'intérêt
