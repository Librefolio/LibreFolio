# 📈 Intérêts

Un événement d'**intérêts** représente un paiement d'intérêts périodique provenant d'un instrument de dette, d'un titre à revenu fixe ou d'un accord de prêt.

---

## 📖 Définition

L'intérêt est le coût de l'emprunt d'argent, payé par l'émetteur (emprunteur) au détenteur (prêteur). Pour les investisseurs, les paiements d'intérêts représentent les revenus gagnés grâce à la détention d'obligations, de billets, de dépôts à terme ou de prêts entre particuliers (P2P).

Contrairement aux dividendes (qui dépendent des bénéfices de l'entreprise), les paiements d'intérêts sont **contractuellement obligatoires** — l'émetteur doit payer le taux convenu indépendamment de sa performance financière.

**Calendriers d'intérêts courants :**

| Fréquence | Instruments typiques |
|-----------|-------------------|
| Mensuelle | Comptes d'épargne, prêts P2P |
| Trimestrielle | Obligations d'entreprise, certaines obligations d'État |
| Semestrielle | Bons du Trésor US, nombreuses obligations d'État européennes |
| Annuelle | Certaines obligations d'entreprise, dépôts à terme |
| À l'échéance | Obligations à coupon zéro, certificats de dépôt |

---

## 📉 Impact sur le prix du marché

Pour les **obligations à coupon**, les paiements d'intérêts provoquent une réinitialisation périodique de la composante des **intérêts courus** :

1. Entre les dates de coupon, le « prix plein » (dirty price) de l'obligation (prix pied + intérêts courus) augmente progressivement.
2. À la date de paiement du coupon, les intérêts courus sont réinitialisés à zéro.
3. Le prix pied (clean price) peut baisser légèrement autour de la date de détachement du coupon.

!!! example "Exemple"

    Une obligation d'une valeur nominale de 1 000 € paie un coupon annuel de 4 % semestriellement (20 € tous les 6 mois).

    - **Jour avant le coupon** : Prix pied 980 €, Intérêts courus 20 € → Prix plein 1 000 €
    - **Date du coupon** : Les intérêts courus sont réinitialisés à 0 €, l'investisseur reçoit 20 € en espèces
    - **Jour après le coupon** : Prix pied 980 €, Intérêts courus ≈ 0,11 € → Prix plein 980,11 €

Pour les actifs de type **Scheduled Investment** dans LibreFolio, les événements d'intérêts modifient directement le prix calculé :

$$
\text{price}(d) = \text{initial{\_}value} + \text{accrued{\_}interest}(d) - \sum \text{INTEREST events}
$$

---

## 📊 Mesures de rendement

### Rendement actuel (Current Yield)

$$
\text{Current Yield} = \frac{\text{Annual Coupon}}{\text{Current Market Price}} \times 100\%
$$

### Rendement à l'échéance (YTM)

Le rendement total anticipé si l'obligation est détenue jusqu'à l'échéance, tenant compte des paiements de coupons, du remboursement de la valeur nominale et du prix de marché actuel.

---

## 🧮 Comment LibreFolio gère les intérêts

Dans LibreFolio, un événement `INTEREST` est enregistré avec :

- **Date** : La date du paiement des intérêts
- **Montant** : Le montant en espèces reçu
- **Devise** : La devise du paiement

Pour les actifs de fournisseurs de type **Scheduled Investment**, les événements d'intérêts sont générés automatiquement à partir du calendrier d'intérêts configuré et affectent directement le calcul du prix. Pour les obligations dont le prix est fixé par le marché, ils servent de marqueurs informationnels.

---

## 🔗 Liens connexes

- 📅 **[Aperçu des événements d'actifs](index.md)** — Tous les types d'événements
- 📆 **[Conventions de comptage des jours](../../fundamentals/day-count.md)** — Comment sont calculées les périodes d'accumulation des intérêts
- 🏁 **[Règlement à l'échéance](maturity-settlement.md)** — Retour final du principal à l'échéance de l'obligation
