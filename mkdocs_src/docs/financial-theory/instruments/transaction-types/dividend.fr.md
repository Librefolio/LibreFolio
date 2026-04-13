# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividende (Transaction)

Une **transaction de dividende** enregistre le paiement en espèces reçu pour la détention d'un actif versant des dividendes (action ou ETF de distribution). Elle représente l'impact au niveau du portefeuille d'un [événement de dividende](../asset-events/dividend.md).

---

## 🔑 Propriétés clés

| Propriété | Détail |
|----------|--------|
| **Code** | `DIVIDEND` |
| **Effet sur la trésorerie** | ⬆️ Augmente le solde |
| **Effet sur l'actif** | — (quantité inchangée) |
| **Événement fiscal** | Oui (revenu imposable dans la plupart des juridictions) |

---

## 📊 Événement vs Transaction

| Concept | Événement de dividende | Transaction de dividende |
|---------|---------------|---------------------|
| **Portée** | Globale — affecte le prix de l'actif | Personnelle — affecte votre portefeuille |
| **Exemple** | "Apple a déclaré 0,25 $/action" | "J'ai reçu 12,50 $ pour mes 50 actions" |
| **Enregistré par** | Fournisseur ou manuel (Éditeur de données) | Rapport du courtier (import BRIM) |
| **Impact graphique** | Marqueur en forme de diamant (◆) sur le graphique de prix | Non visible sur le graphique |

---

## 📐 Montant du dividende

Le montant reçu dépend du nombre d'actions détenues à la **date d'enregistrement** :

$$
\text{Dividende reçu} = \text{Actions détenues} \times \text{Dividende par action}
$$

### 💰 Retenue à la source

De nombreuses juridictions appliquent une retenue à la source sur les dividendes, en particulier pour les actions étrangères :

$$
\text{Dividende net} = \text{Dividende brut} \times (1 - \tau_{withholding})
$$

La taxe retenue est enregistrée comme une transaction `TAX` distincte.

---

## 🔗 Liens connexes

- 💰 **[Événements de dividende](../asset-events/dividend.md)** — Comment les dividendes affectent le prix des actifs
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Traitement fiscal des dividendes
- 📈 **[Actions](../asset-types/stocks.md)** — La principale classe d'actifs versant des dividendes
