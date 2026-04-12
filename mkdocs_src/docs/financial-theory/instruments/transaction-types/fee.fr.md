# <img src="../../../static/icons/transactions/fee.png" width="32" style="vertical-align: middle;" /> Frais et Taxes

Les **frais** et les **taxes** représentent des coûts qui réduisent la valeur de votre portefeuille. Ce sont des types de transactions distincts pour différencier les coûts facturés par le courtier des obligations imposées par le gouvernement.

---

## 🔑 Propriétés Clés

| Propriété | Frais | Taxe |
|----------|-----|-----|
| **Code** | `FEE` | `TAX` |
| **Effet sur le cash** | ⬇️ Diminue le solde | ⬇️ Diminue le solde |
| **Effet sur l'actif** | — | — |
| **Exemples** | Commission, frais de garde, spread | Impôt sur les plus-values, retenue à la source, droit de timbre |

---

## 📊 Types de Frais

| Type de Frais | Description | Fréquence |
|----------|-------------|-----------|
| **Commission de trading** | Coût par transaction facturé par le courtier | Par transaction |
| **Frais de garde** | Frais de tenue de compte | Mensuel/Trimestriel |
| **Spread** | Différence entre le prix d'achat et le prix de vente | Implicite par transaction |
| **Frais de conversion FX** | Coût du change de devises | Par conversion |
| **Frais de gestion (TER)** | Dépenses annuelles de l'ETF/Fonds | Déduits de la VNI |

---

## 💰 Types de Taxes

| Type de Taxe | Description | Moment du prélèvement |
|----------|-------------|-------------|
| **Impôt sur les plus-values** | Taxe sur le profit réalisé lors de la vente | À la vente |
| **Retenue à la source** | Taxe déduite à la source (dividendes, intérêts) | Au paiement |
| **Droit de timbre** | Taxe sur les transactions (ex: droit de timbre au Royaume-Uni) | À l'achat |
| **Taxe sur les transactions financières** | Taxe sur les échanges (ex: taxe Tobin en Italie) | À la transaction |

---

## 📐 Impact sur les Rendements

Les frais et les taxes réduisent directement votre rendement net :

$$
R_{net} = R_{gross} - \frac{\text{Frais} + \text{Taxes}}{V_{start}}
$$

Sur de longues périodes, même de petits frais récurrents s'accumulent de manière significative :

$$
V_{final} = V_0 \times (1 + r - f)^n
$$

où $f$ est le taux de frais annuel. Un taux de frais annuel de 1 % sur un rendement de 7 % sur 30 ans réduit la valeur finale de **26 %**.

---

## 🔗 Liens connexes

- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Théorie fiscale complète
- 🛒 **[Achat et Vente](buy-sell.md)** — Frais facturés lors des transactions
