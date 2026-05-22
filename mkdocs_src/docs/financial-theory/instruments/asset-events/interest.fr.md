# 📈 Intérêts

Un événement d'**intérêt** représente un paiement d'intérêts périodique provenant d'un instrument de dette, d'un titre à revenu fixe ou d'un accord de prêt.

---

## 📖 Définition

L'intérêt est le coût de l'emprunt d'argent, payé par l'émetteur (emprunteur) au détenteur (prêteur). Pour les investisseurs, les paiements d'intérêts représentent des revenus gagnés grâce à la détention d'obligations, de billets, de dépôts à terme ou de prêts entre particuliers (P2P).

Contrairement aux dividendes (qui dépendent des bénéfices de l'entreprise), les paiements d'intérêts sont **contractuellement obligatoires** — l'émetteur doit payer le taux convenu indépendamment de la performance financière.

**Calendriers d'intérêts courants :**

| Fréquence | Instruments typiques |
|-----------|-------------------|
| Mensuelle | Comptes d'épargne, prêts P2P |
| Trimestrielle | Obligations d'entreprise, certaines obligations d'État |
| Semestrielle | Bons du Trésor américain, nombreuses obligations d'État européennes |
| Annuelle | Certaines obligations d'entreprise, dépôts à terme |
| À l'échéance | Obligations à coupon zéro, certificats de dépôt |

---

## 🧮 Formules d'intérêts

??? example "📏 Intérêt Simple"

 Intérêt calculé uniquement sur le principal d'origine — sans capitalisation :

 $$
 I = P \times r \times t
 $$

 Où :

 - $P$ = principal (investissement initial)
 - $r$ = taux d'intérêt annuel (ex: 0,04 pour 4 %)
 - $t$ = temps en années

 Utilisé pour : les prêts à court terme, certains comptes d'épargne, les bons du Trésor.

??? example "📈 Intérêts Composés"

 Intérêt calculé sur le principal **plus** les intérêts précédemment accumulés :

 $$
 A = P \times \left(1 + \frac{r}{n}\right)^{n \times t}
 $$

 Où :

 - $A$ = montant final (principal + intérêts)
 - $P$ = principal
 - $r$ = taux d'intérêt annuel
 - $n$ = fréquence de capitalisation par an (12 = mensuelle, 4 = trimestrielle, 1 = annuelle)
 - $t$ = temps en années

 L'intérêt gagné est : $I = A - P$

 Utilisé pour : la plupart des obligations, les comptes d'épargne avec réinvestissement, les plateformes P2P.

---

## 📉 Impact sur le prix du marché

Pour les **obligations à coupon**, les paiements d'intérêts provoquent une réinitialisation périodique de la composante des **intérêts courus** :

1. Entre les dates de coupon, le « prix plein » de l'obligation (prix net + intérêts courus) augmente progressivement
2. À la date de paiement du coupon, les intérêts courus sont remis à zéro
3. Le prix net peut baisser légèrement autour de la date de détachement du coupon

??? example "Cycle de coupon obligataire"

 Une obligation d'une valeur nominale de 1 000 € verse un coupon annuel de 4 % semestriellement (20 € tous les 6 mois).

 - **Jour avant le coupon** : Prix net 980 €, Intérêts courus 20 € → Prix plein 1 000 €
 - **Date du coupon** : Les intérêts courus sont remis à 0 €, l'investisseur reçoit 20 € en espèces
 - **Jour après le coupon** : Prix net 980 €, Intérêts courus ≈ 0,11 € → Prix plein 980,11 €

Pour les actifs d'**investissement programmé** dans LibreFolio, les événements d'intérêts modifient directement le prix calculé :

$$
\text{price}(d) = V_0 + I_{accrued}(d) - \sum_{k} C_k
$$

Où :

- $V_0$ = valeur de l'investissement initial
- $I_{accrued}(d)$ = intérêts courus jusqu'à la date $d$
- $\sum_k C_k$ = somme de tous les paiements d'intérêts (coupons) déjà distribués

---

## 📊 Métriques de rendement

??? example "📐 Rendement Actuel"

 La mesure de rendement la plus simple — le revenu annuel par rapport au prix actuel :

 $$
 \text{Current Yield} = \frac{\text{Annual Coupon}}{\text{Current Market Price}} \times 100
 $$

 Où :

 - **Coupon annuel** = total des paiements de coupons par an (ex: 40 € pour une obligation de 4 % avec une valeur nominale de 1 000 €)
 - **Prix actuel du marché** = ce que vous paieriez pour acheter l'obligation aujourd'hui

 Limitation : ignore la plus-value ou moins-value si l'obligation est détenue jusqu'à l'échéance.

??? example "📐 Rendement à l'échéance (YTM)"

 Le rendement total anticipé si l'obligation est détenue jusqu'à l'échéance, en tenant compte de **tous** les flux de trésorerie : paiements de coupons, remboursement de la valeur nominale et la différence entre le prix d'achat et la valeur au pair.

 Le YTM est le taux $y$ qui satisfait :

 $$
 P = \sum_{t=1}^{T} \frac{C}{(1+y)^t} + \frac{F}{(1+y)^T}
 $$

 Où :

 - $P$ = prix actuel du marché
 - $C$ = paiement du coupon par période
 - $F$ = valeur nominale (remboursée à l'échéance)
 - $T$ = nombre de périodes jusqu'à l'échéance
 - $y$ = rendement à l'échéance (par période)

 Le YTM doit être résolu numériquement (il n'y a pas de solution explicite).

---

## 🧮 Comment LibreFolio gère les intérêts

Dans LibreFolio, un événement `INTEREST` est enregistré avec :

- **Date** : La date du paiement des intérêts
- **Montant** : Le montant en espèces reçu
- **Devise** : La devise du paiement

Pour les actifs de fournisseurs d'**investissement programmé**, les événements d'intérêts sont générés automatiquement à partir du calendrier d'intérêts configuré et affectent directement le calcul du prix. Pour les obligations dont le prix est basé sur le marché, ils servent de marqueurs informationnels.

---

## 🔗 Liens connexes

- 📅 **[Aperçu des événements d'actifs](index.md)** — Tous les types d'événements
- 📆 **[Conventions de comptage des jours](../../fundamentals/day-count.md)** — Comment sont calculées les périodes d'accumulation d'intérêts
- 🏁 **[Règlement à l'échéance](maturity-settlement.md)** — Retour final du principal à l'échéance de l'obligation
- 📈 **[Rendements et taux de croissance](../../fundamentals/returns.md)** — Mesurer le rendement total
