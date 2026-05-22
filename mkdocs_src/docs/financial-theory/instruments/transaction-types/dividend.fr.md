# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividende (Transaction)

Une **transaction de dividende** enregistre le paiement en espèces reçu lors de la détention d'une position d'actif versant des dividendes (action ou ETF de distribution). Elle représente l'impact au niveau du portefeuille d'un [événement de dividende](../asset-events/dividend.md).

---

## 🔑 Propriétés Clés

| Propriété | Détail |
|----------|--------|
| **Code** | `DIVIDEND` |
| **Effet sur le cash** | ⬆️ Augmente le solde |
| **Effet sur l'actif** | — (quantité inchangée) |
| **Événement fiscal** | Oui (revenu imposable dans la plupart des juridictions) |

---

## 📊 Événement vs Transaction

| Concept | Événement de Dividende | Transaction de Dividende |
|---------|---------------|---------------------|
| **Portée** | Globale — affecte le prix de l'actif | Personnelle — affecte votre portefeuille |
| **Exemple** | "Apple a déclaré 0,25 $/action" | "J'ai reçu 12,50 $ pour mes 50 actions" |
| **Enregistré par** | Fournisseur ou manuel (éditeur de données) | Rapport du courtier (import BRIM) |
| **Impact graphique** | Marqueur diamant (◆) sur le graphique de prix | Non visible sur le graphique |

---

## 📐 Montant du Dividende

Le montant reçu dépend du nombre d'actions détenues à la **date d'enregistrement** (la date à laquelle la société vérifie qui détient les actions) :

$$
\text{Dividende Reçu} = \text{Actions Détenues} \times \text{Dividende par Action}
$$

Où :

- **Actions Détenues** = nombre d'actions que vous possédez à la date d'enregistrement (date ex-dividende − 1 jour ouvré)
- **Dividende par Action** = montant déclaré par la société (ex: 0,25 $/action)

### 💰 Retenue à la source

De nombreuses juridictions appliquent une **retenue à la source** sur les dividendes — particulièrement pour les actions étrangères. La taxe est déduite à la source (par le courtier ou le pays de l'émetteur) avant que vous ne receviez le paiement :

$$
\text{Dividende Net} = \text{Dividende Brut} \times (1 - \tau_{withholding})
$$

Où :

- **Dividende Brut** = montant total déclaré (avant taxe)
- $\tau_{withholding}$ = taux de retenue à la source (ex: 15 % pour les actions US détenues par des résidents de l'UE selon la plupart des traités fiscaux)
- **Dividende Net** = le montant effectivement versé sur votre compte de courtage

Le montant retenu est généralement enregistré comme une transaction `TAX` distincte dans LibreFolio, permettant de séparer le dividende brut de la déduction fiscale pour les besoins de la déclaration d'impôts.

---

## 🔗 Liens connexes

- 💰 **[Événements de Dividende](../asset-events/dividend.md)** — Comment les dividendes affectent les prix des actifs
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Traitement fiscal des dividendes
- 📈 **[Actions](../asset-types/stocks.md)** — La principale classe d'actifs versant des dividendes
