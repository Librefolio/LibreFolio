# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividendes & Intérêts ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" }

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-dividend" alt="Formulaire de transaction — DIVIDENDE">
</div>

Les **dividendes** et les **intérêts** représentent le rendement généré par les actifs de votre portefeuille. Il s'agit de paiements en espèces reçus sans vente de l'actif sous-jacent.

---

## 🔑 Propriétés Clés

| Propriété | Dividende | Intérêt |
|----------|----------|----------|
| **Code** | `DIVIDEND` | `INTEREST` |
| **Effet trésorerie** | ⬆️ Augmente le solde | ⬆️ Augmente le solde |
| **Effet actif** | — (quantité inchangée) | — (principal inchangé) |
| **Événement fiscal** | Oui (revenu imposable) | Oui (revenu imposable) |

---

## 💡 Quand les utiliser

Utilisez ces transactions lorsque des liquidités arrivent sur votre compte courtier au titre du rendement d'un actif :

- **Dividende** : Revenus provenant de fonds propres (actions, ETF de distribution).
- **Intérêt** : Revenus provenant d'instruments à revenu fixe (obligations, comptes d'épargne, prêts P2P, crowdfunding).

*Ne pas utiliser ces transactions pour le remboursement du principal (ex: règlement à l'échéance d'une obligation).*

---

## 💰 Les Dividendes en détail

### Événement vs Transaction

| Concept | Événement de Dividende | Transaction de Dividende |
|---------|---------------|---------------------|
| **Portée** | Globale — affecte le prix de l'actif | Personnelle — affecte votre portefeuille |
| **Exemple** | "Apple a déclaré 0,25 $ / action" | "J'ai reçu 12,50 $ pour mes 50 actions" |
| **Enregistré par** | Fournisseur ou manuel (éditeur de données) | Rapport du courtier (import BRIM) |
| **Impact graphique** | Marqueur diamant (◆) sur le graphique de prix | Non visible sur le graphique |

### Montant du Dividende

Le montant reçu dépend du nombre d'actions détenues à la **date d'enregistrement** :

$$
\text{Dividende Reçu} = \text{Actions Détenues} \times \text{Dividende par Action}
$$

### Retenue à la source

De nombreuses juridictions appliquent une **retenue à la source** sur les dividendes — particulièrement pour les actions étrangères. La taxe est déduite à la source :

$$
\text{Dividende Net} = \text{Dividende Brut} \times (1 - \tau_{withholding})
$$

Le montant retenu est généralement enregistré comme une transaction `TAX` distincte dans LibreFolio, afin de maintenir une distinction entre le dividende brut et la déduction fiscale pour les besoins du reporting.

---

## 📈 Sources d'Intérêts

| Source | Description | Fréquence |
|--------|-------------|-----------|
| **Coupons obligataires** | Paiements à taux fixe ou variable | Semestriel / Annuel |
| **Intérêts d'épargne** | Intérêts sur dépôts en espèces | Mensuel / Trimestriel |
| **Paiements de prêts P2P** | Partie intérêts des remboursements de prêts | Mensuel |
| **Rendements de crowdfunding** | Rendements à taux fixe sur projets | Variable |

!!! tip "Theory & formulas"

    Pour les mathématiques de l'accumulation d'intérêts (simples vs composés, conventions de comptage des jours, mesures de rendement), voir :

    - **[📈 Événements d'Intérêts](../asset-events/interest.md)** — Mécanismes d'accumulation et impact sur le prix
    - **[📅 Conventions de Comptage des Jours](../../fundamentals/day-count.md)** — Comment les périodes d'intérêts sont calculées

---

## 🔗 Liens connexes

- 💰 **[Événements de Dividendes](../asset-events/dividend.md)** — Comment les dividendes affectent le prix des actifs
- 📈 **[Événements d'Intérêts](../asset-events/interest.md)** — Mécanismes d'accumulation et de coupons
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Traitement fiscal des rendements
- 🏛️ **[Obligations](../asset-types/bonds.md)** — L'actif principal générateur d'intérêts
- 📈 **[Actions](../asset-types/stocks.md)** — La principale classe d'actifs versant des dividendes
