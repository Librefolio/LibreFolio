# ![](../../../static/icons/transactions/fee.png){: width="32" style="vertical-align: middle;" } Frais & Taxes

Les **frais** et les **taxes** représentent des coûts qui réduisent la valeur de votre portefeuille. Ce sont des types de transactions distincts afin de différencier les frais facturés par le courtier des obligations imposées par le gouvernement.

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

| Type de frais | Description | Fréquence |
|----------|-------------|-----------|
| **Commission de trading** | Coût par transaction facturé par le courtier | Par transaction |
| **Frais de garde** | Frais de maintenance du compte | Mensuel/Trimestriel |
| **Spread** | Différence entre le prix offert et le prix demandé | Implicite par trade |
| **Frais de conversion de devise FX** | Coût de la conversion de devise | Par conversion |
| **Frais de gestion (TER)** | Frais annuels d'un ETF/Fonds | Déduit de la NAV |

---

## 💰 Types de Taxes

| Type de taxe | Description | Moment de l'imposition |
|----------|-------------|-------------|
| **Impôt sur les plus-values** | Taxe sur le profit réalisé lors de la vente | À la vente |
| **Retenue à la source** | Taxe déduite à la source (dividendes, intérêts) | Au paiement |
| **Droit de timbre** | Taxe sur la transaction (ex: stamp duty au Royaume-Uni) | À l'achat |
| **Taxe sur les transactions financières** | Taxe sur les transactions (ex: taxe Tobin en Italie) | À la transaction |

---

## 📐 Impact sur les Rendements

Les frais et les taxes réduisent directement votre rendement net. La relation entre la performance brute et nette est la suivante :

$$
R_{net} = R_{gross} - \frac{\text{Fees} + \text{Taxes}}{V_{start}}
$$

Où :

- $R_{gross}$ = rendement avant coûts (ce que le marché vous a apporté)
- $R_{net}$ = rendement après coûts (ce que vous conservez réellement)
- $V_{start}$ = valeur du portefeuille au début de la période

### 📉 Effet Composé des Frais

Sur de longues périodes de détention, même de petits frais récurrents érodent considérablement les rendements en raison du **frein composé** :

$$
V_{final} = V_0 \times (1 + r - f)^n
$$

Où :

- $V_0$ = investissement initial
- $r$ = taux de rendement brut annuel (ex: 0,07 pour 7 %)
- $f$ = taux de frais annuel (ex: 0,01 pour 1 %)
- $n$ = nombre d'années

!!! example "Le frein de 1 % sur 30 ans"

    Avec 10 000 $ investis à un rendement brut de 7 % :

    - **Sans frais** : 10 000 $ × $(1,07)^{30}$ = **76 123 $**
    - **Avec 1 % de frais** : 10 000 $ × $(1,06)^{30}$ = **57 435 $**

    Les frais annuels de 1 % vous coûtent **18 688 $** — soit une réduction de 26 % de la valeur finale.

---

## 🔗 Liens Associés

- 📈 **[Rendements & Taux de Croissance](../../fundamentals/returns.md)** — Comment les rendements sont mesurés (brut vs net)
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Théorie complète de la fiscalité et efficience fiscale
- 🛒 **[Achat & Vente](buy-sell.md)** — Commissions de trading liées aux transactions
- 💱 **[Conversion FX](fx-conversion.md)** — Spreads FX cachés comme frais implicites
