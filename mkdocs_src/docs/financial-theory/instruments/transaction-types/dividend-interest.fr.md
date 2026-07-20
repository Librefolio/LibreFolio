# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividende & Intérêt ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" }

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-dividend" alt="Formulaire de transaction — DIVIDENDE" title="Formulaire de transaction — DIVIDENDE">
</div>

Les **dividendes** et les **intérêts** représentent le rendement généré par les actifs de votre portefeuille. Ce sont des paiements en espèces reçus sans vendre l'actif sous-jacent.

---

## 🔑 Propriétés clés

| Propriété | Dividende | Intérêt |
|-----------|-----------|---------|
| **Code** | `DIVIDEND` | `INTEREST` |
| **Effet sur la trésorerie** | ⬆️ Augmente le solde | ⬆️ Augmente le solde |
| **Effet sur l'actif** | — (quantité inchangée) | — (principal inchangé) |
| **Événement fiscal** | Oui (revenu imposable) | Oui (revenu imposable) |

---

## 💡 Quand les utiliser

Utilisez ces transactions lorsque des liquidités arrivent sur votre compte de courtage sous forme de rendement d'un actif :

- **Dividende**&nbsp;: Revenu des actions (actions, ETF distributeurs).
- **Intérêt**&nbsp;: Revenu des instruments à revenu fixe (obligations, comptes d'épargne, prêts P2P, financement participatif).

*Ne pas utiliser pour un remboursement de capital (ex. règlement d'obligation à maturité).*

---

## 💰 Les dividendes en détail

### Événement vs Transaction

| Concept | Événement de dividende | Transaction de dividende |
|---------|------------------------|-------------------------|
| **Périmètre** | Global — affecte le prix de l'actif | Personnel — affecte votre portefeuille |
| **Exemple** | "Apple a déclaré 0,25 $/action" | "J'ai reçu 12,50 $ pour mes 50 actions" |
| **Enregistré par** | Fournisseur ou manuellement (Éditeur de données) | Relevé de courtage (import BRIM) |
| **Impact sur le graphique** | Marqueur losange (◆) sur le graphique des prix | Non visible sur le graphique |

### Montant du dividende

Le montant reçu dépend du nombre d'actions détenues à la **date d'enregistrement** :

$$
\text{Dividende reçu} = \text{Actions détenues} \times \text{Dividende par action}
$$

### Retenue à la source

De nombreuses juridictions appliquent une **retenue à la source** sur les dividendes — en particulier pour les actions étrangères. L'impôt est prélevé à la source :

$$
\text{Dividende net} = \text{Dividende brut} \times (1 - \tau_{retenue})
$$

Le montant retenu est généralement enregistré comme une transaction `TAX` distincte dans LibreFolio, ce qui permet de distinguer le dividende brut et la déduction fiscale à des fins de reporting.

---

## 📈 Sources d'intérêts

| Source | Description | Fréquence |
|--------|-------------|-----------|
| **Coupons obligataires** | Paiements à taux fixe ou variable | Semestrielle / Annuelle |
| **Intérêts d'épargne** | Intérêts sur les dépôts en espèces | Mensuelle / Trimestrielle |
| **Remboursements de prêts P2P** | Part d'intérêts des remboursements de prêts | Mensuelle |
| **Rendements du financement participatif** | Rendements à taux fixe sur des projets | Variable |

!!! tip "Théorie et formules"

    Pour les mathématiques de la comptabilisation des intérêts (simple vs composé, conventions de décompte des jours, indicateurs de rendement), voir :

    - **[📈 Événements d'intérêts](../asset-events/interest.md)** — Mécanique de comptabilisation et impact sur le prix
    - **[📅 Conventions de décompte des jours](../../fundamentals/day-count.md)** — Comment les périodes d'intérêt sont calculées

---

## 🔗 Liens associés

- 💰 **[Événements de dividendes](../asset-events/dividend.md)** — Comment les dividendes affectent le prix des actifs
- 📈 **[Événements d'intérêts](../asset-events/interest.md)** — Mécanique de comptabilisation et des coupons
- 🔬 **[Analyse des lots FIFO](../../technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#income-allocation-across-lots)** — Comment le revenu est réparti au prorata entre les lots ouverts
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Traitement fiscal du rendement
- 🏛️ **[Obligations](../asset-types/bonds.md)** — Le principal actif générateur d'intérêts
- 📈 **[Actions](../asset-types/stocks.md)** — La principale classe d'actifs versant des dividendes
