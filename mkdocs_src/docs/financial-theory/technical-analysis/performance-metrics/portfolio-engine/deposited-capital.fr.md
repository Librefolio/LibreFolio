# 💸 Capital versé, PnL total et réservoirs de trésorerie

## 💡 Vue d'ensemble du concept

**Référence de capital** = capital économique cumulé apporté depuis l'origine :

$$
\mathrm{CapitalBaseline}(t)=
\sum_{\tau \leq t}\mathrm{ExternalCashFlow}(\tau)
+ \sum_{\tau \leq t}\mathrm{InKindCapital}(\tau)
$$

**PnL total** = toute la valeur générée au-delà des apports externes :

$$
\boxed{\mathrm{TotalPnL}(t) = \mathrm{NAV}(t) - \mathrm{CapitalBaseline}(t)}
$$

`InKindCapital` couvre les titres qui entrent ou sortent du périmètre sans trésorerie :

- les lignes ADJUSTMENT valorisées portant `cost_basis_override` (non liées à une division), **au coût** : le coût qu'une ligne entrante ajoute à la position, ou le coût moyen qu'une ligne sortante retire ;
- les jambes de TRANSFER dont l'autre jambe n'est pas dans le périmètre — elle se trouve chez un courtier hors de la vue, est manquante, ou n'a jamais été liée — **à la valeur de marché** à leur propre date : $+$ pour les titres reçus, $-$ pour les titres envoyés, rien si le titre ne peut pas être valorisé ce jour-là.

Ces lignes déplacent de la valeur sans trésorerie : elles constituent du capital, ni profit ni perte.

---

## 🎯 Ce qui compte

| Transaction | Effet sur la référence de capital |
|------------|-----------------|
| DEPOSIT / WITHDRAWAL (non liée) | ✅ Oui |
| CASH\_TRANSFER / FX\_CONVERSION dont l'autre jambe est hors de la vue, manquante, ou jamais liée (orpheline) | ✅ Oui, à son montant, comme un dépôt ou un retrait |
| CASH\_TRANSFER / FX\_CONVERSION / TRANSFER avec les deux jambes dans la vue (paire interne) | ❌ Non. Par courtier, une paire entre deux courtiers déplace du capital de l'expéditeur vers le destinataire le jour de l'arrivée, pour une somme nulle ([Transferts internes](#internal-transfers-broker-lines)) |
| TRANSFER de titres dont l'autre jambe est hors de la vue, manquante, ou jamais liée (orpheline) | ✅ Oui, capital en nature à la valeur de marché à sa date |
| ADJUSTMENT avec `cost_basis_override`, non liée à une division | ✅ Oui, capital en nature au coût |
| ADJUSTMENT liée à une DIVISION | ❌ Non, simple remise à l'échelle de la quantité |
| BUY, SELL, DIVIDEND, INTEREST, FEE, TAX | ❌ Non |

---

## 🔀 Transferts internes dans les lignes par courtier {: #internal-transfers-broker-lines }

Avec deux courtiers ou plus dans le périmètre, le [graphique P&L](../../../../user/dashboard/charts.md#pnl-line) trace une ligne par courtier. Chaque courtier $b \in S$ possède sa propre NAV, son propre capital et son propre PnL :

$$
\mathrm{PnL}_b(t) = \mathrm{NAV}_b(t) - C_b(t)
$$

$$
\mathrm{NAV}_b(t) = \mathrm{MV}_b(t) + \mathrm{Cash}_b(t) + \mathrm{InTransit}_b(t)
$$

$$
C_b(t) = \sum_{\tau \leq t}\mathrm{ExternalCashFlow}_b(\tau) + \sum_{\tau \leq t}\mathrm{InKindCapital}_b(\tau) + \sum_{\tau \leq t}\mathrm{Internal}_b(\tau)
$$

$\mathrm{InTransit}_b$ est la valeur en transit qui a quitté $b$, et $\mathrm{Internal}_b$ est la part de $b$ dans les transferts internes décrits ci-dessous. Comme $\sum_b \mathrm{NAV}_b = \mathrm{NAV}$ et que les flux internes s'annulent chaque jour, les lignes s'additionnent pour donner les chiffres du périmètre :

$$
\sum_{b \in S}\mathrm{Internal}_b(t) = 0
\quad\Rightarrow\quad
\sum_{b \in S} C_b(t) = \mathrm{CapitalBaseline}(t),
\qquad
\sum_{b \in S}\mathrm{PnL}_b(t) = \mathrm{TotalPnL}(t)
$$

La ligne d'un courtier représente donc le PnL gagné pendant que la valeur se trouvait chez ce courtier, ou en transit depuis celui-ci. Ce n'est pas la plus-value latente des positions que le courtier détient.

### 📐 Le flux interne

Une **paire interne** est un CASH\_TRANSFER, une FX\_CONVERSION ou un TRANSFER lié dont les deux jambes sont dans $S$, sur deux courtiers différents : l'expéditeur $A$ (la jambe sortante) et le destinataire $B$ (la jambe entrante). Elle produit un flux, le **jour d'arrivée** $t_{arr}$, à la date de la jambe la plus tardive :

$$
\mathrm{Internal}_A(t_{arr}) = -X,
\qquad
\mathrm{Internal}_B(t_{arr}) = +X,
\qquad
X = s_A \cdot V(t_{arr})
$$

$s_A$ est la [part de propriété](../../../../user/brokers/sharing.md) de l'expéditeur et $V(t_{arr})$ la valeur totale que l'arrivée apporte à $B$ ce jour-là, valorisée exactement comme la NAV la valorise :

| Paire | $V(t_{arr})$ |
|------|--------------|
| CASH\_TRANSFER | Le montant reçu, converti à $\mathrm{fx}(c, C^*, t_{arr})$ |
| FX\_CONVERSION entre courtiers | La jambe reçue, convertie de la même manière : $-1\,000$ USD chez $A$ → $+900$ EUR chez $B$ donne $V = 900$ EUR, et le coût de conversion reste dans la ligne de $A$ |
| TRANSFER de titres | $\mathrm{MV}$ de la quantité reçue au [prix de valorisation](index.md#2-valuation-price) de $t_{arr}$, le dernier prix connu reporté s'il n'y en a pas ce jour-là |

À parts égales, $X$ correspond exactement à ce que l'arrivée ajoute à $\mathrm{NAV}_B$, donc aucune ligne ne saute. Le $\mathrm{CapitalBaseline}$ du périmètre reste inchangé, car un mouvement interne n'est pas du capital externe : la NAV, la CapitalBaseline, le TotalPnL et ses bougies, le ROI, le TWRR, le MWRR et la trésorerie sont identiques avec ou sans le flux. Seule la répartition de la référence entre les courtiers change.

### ✈️ Valeur en transit

Lorsque les jambes tombent à des jours différents, la valeur voyage du jour de départ $t_{dep}$ jusqu'au jour précédant $t_{arr}$. Pendant ce temps, elle fait partie de $\mathrm{InTransit}_A$, à la part de l'expéditeur $s_A$, valorisée chaque jour : la trésorerie au taux de change du jour, les titres au prix de valorisation du jour (au coût enregistré lors du transfert si le titre n'a aucun prix du tout). Aucun flux n'a lieu pendant que la valeur voyage, donc ses variations de prix et de taux de change restent dans la ligne de $A$, y compris la variation propre du jour d'arrivée ; la ligne de $B$ démarre à la valeur reçue.

Par exemple, $A$ reçoit un dépôt de 1 000 USD au jour 0 à 0,90 EUR par USD ($C_A = 900$) et envoie les dollars au jour 1 ; $B$ les reçoit au jour 4. Avec le taux à 0,90, 0,91, 0,92, 0,93 aux jours 1–4, la ligne de $A$ affiche 0, +10, +20, +30 et celle de $B$ reste à 0. Au jour 4, $X = 930$ et $C_A = 900 - 930 = -30$.

### 🧩 Cas particuliers

- **Parts de propriété différentes.** $X$ utilise $s_A$, comme la valeur en transit, tandis que l'arrivée ajoute $s_B \cdot V(t_{arr})$ à $\mathrm{NAV}_B$. La ligne de $B$ conserve un saut résiduel de $(s_B - s_A)\,V(t_{arr})$ le jour de l'arrivée, et le TotalPnL montre le même saut, avec ou sans le flux.
- **Valeur inconnue le jour de l'arrivée.** Si $V(t_{arr})$ ne peut pas être calculée — le titre n'a aucune observation à $t_{arr}$ ou avant ($\operatorname{mark} = \varnothing$), ou un taux de change est manquant — alors $X = 0$, ce qui correspond à ce que l'arrivée ajoute à $\mathrm{NAV}_B$. Rien n'est deviné : le saut subsiste, et la valeur d'un titre apparaît dans la ligne du courtier qui le détient à partir de son premier prix.
- **Frais.** Ils ne font pas partie de $X$. Une ligne FEE de 5 enregistrée chez l'expéditeur, ou les mêmes 5 comme écart entre les jambes ($-1\,000$ envoyés, $+995$ reçus, donc $X = 995$), reste dans la ligne de $A$ comme une perte de 5.
- **Paires sur un même courtier.** Deux jambes sur le même courtier, comme une conversion de devise au sein d'un même compte, ne nécessitent aucun flux : la valeur ne quitte jamais la ligne.
- **Paires d'ADJUSTMENT.** Ce ne sont pas des paires internes : chaque jambe reste du capital en nature au coût (voir le tableau ci-dessus). Le capital de l'expéditeur diminue du coût moyen retiré et celui du destinataire augmente du coût ajouté, de sorte que la ligne du destinataire reprend la plus-value accumulée chez l'expéditeur. Avec la configuration de l'exemple ci-dessous et les deux jambes au jour 2 à un coût de 10, les lignes affichent $A = 0$, $B = +20$ ; une paire de TRANSFER donne $A = +20$, $B = 0$.

### 🔍 Vues filtrées

Dans une vue ne comportant que certains courtiers, une jambe de TRANSFER dont l'autre jambe est hors de $S$ — ou manquante, ou jamais liée — ne peut pas former de paire interne. C'est du capital en nature à la valeur de marché à sa propre date : $+\mathrm{MV}$ pour les titres reçus, $-\mathrm{MV}$ pour les titres envoyés, à la part de ce courtier, et rien si le titre ne peut pas être valorisé ce jour-là. Contrairement à un flux interne, cela déplace la CapitalBaseline de la vue, donc le TotalPnL, le ROI, le TWRR et le MWRR de la vue le traitent comme du capital, à l'instar d'un ADJUSTMENT en nature. Une jambe de CASH\_TRANSFER ou de FX\_CONVERSION dans la même position est de la trésorerie externe à son montant, comme un dépôt ou un retrait.

Une jambe perd son lien lorsque le courtier détenant l'autre jambe est supprimé. Une telle orpheline suit les mêmes règles dans toutes les vues, y compris la vue complète.

Comparer la vue propre d'un courtier avec la vue combinée :

- **Le destinataire seul correspond à sa ligne combinée.** Dans la vue propre de $B$, les titres reçus sont du capital à leur valeur de marché à $t_{arr}$, ce qui correspond au $X$ de la vue combinée. Cela vaut avec des parts égales et un prix que les deux vues peuvent voir : un prix qui provient uniquement de transactions chez $A$ n'est pas visible dans la vue propre de $B$.
- **L'expéditeur seul perd les variations en transit.** Dans la vue propre de $A$, son capital chute le jour du départ de $s_A \cdot V(t_{dep})$, alors que dans la vue combinée la valeur reste chez $A$ jusqu'à son arrivée.

En notant $\mathrm{PnL}_A^{(S)}$ la ligne de $A$ dans la vue du périmètre $S$, à partir du jour de départ :

$$
\mathrm{PnL}_A^{(A)}(t) = \mathrm{PnL}_A^{(A,B)}(t) - s_A\bigl[V(\min(t, t_{arr})) - V(t_{dep})\bigr]
$$

### 📦 Exemple — Titres en transit

Tous les montants en EUR, parts 100 %. $A$ reçoit un dépôt de 100 et achète 10 unités à 10 au jour 0. Le prix est 10, 11, 12, 13, 14, 15 aux jours 0–5. $A$ envoie les 10 unités au jour 1, et $B$ les reçoit au jour 3.

**Vue combinée** (les deux courtiers dans $S$) :

| Jour | Prix | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | TotalPnL |
|-----|-------|------------------|-------|------------------|------------------|-------|------------------|----------|
| 0 | 10 | 100 | 100 | 0 | 0 | 0 | 0 | 0 |
| 1 | 11 | 110 (en transit) | 100 | +10 | 0 | 0 | 0 | +10 |
| 2 | 12 | 120 (en transit) | 100 | +20 | 0 | 0 | 0 | +20 |
| 3 | 13 | 0 | −30 | +30 | 130 | 130 | 0 | +30 |
| 4 | 14 | 0 | −30 | +30 | 140 | 130 | +10 | +40 |
| 5 | 15 | 0 | −30 | +30 | 150 | 130 | +20 | +50 |

Au jour 3, le flux $X = 10 \times 13 = 130$ déplace du capital de $A$ vers $B$. $A$ conserve les +30 gagnés pendant que les unités étaient chez $A$ ou en transit (10 → 13), et $B$ gagne à partir de 13. $C_A$ devient négatif parce que $A$ a transmis plus de valeur (130) que le capital qu'il a reçu (100) : la différence constitue son gain. Le TotalPnL est identique avec ou sans le flux ; sans celui-ci, au jour 3 la ligne de $A$ chuterait à $0 - 100 = -100$ et celle de $B$ sauterait à $130 - 0 = +130$.

**Vues d'un seul courtier** :

| Jour | $B$ seul : $C_B$ | $B$ seul : $\mathrm{PnL}_B$ | $A$ seul : $C_A$ | $A$ seul : $\mathrm{PnL}_A$ |
|-----|------------------|-----------------------------|------------------|-----------------------------|
| 0 | — | — | 100 | 0 |
| 1 | — | — | −10 | +10 |
| 2 | — | — | −10 | +10 |
| 3 | 130 | 0 | −10 | +10 |
| 4 | 130 | +10 | −10 | +10 |
| 5 | 130 | +20 | −10 | +10 |

La vue propre de $B$ commence à sa première transaction et correspond à $B$ dans la vue combinée. Dans la vue propre de $A$, les unités partent au jour 1 à $10 \times 11 = 110$, donc $C_A = 100 - 110 = -10$ et la ligne reste à +10 : la variation de 11 à 13 pendant le transit n'y figure pas, et $+30 - (130 - 110) = +10$. Compté comme un gain ou une perte plutôt que comme du capital, le même transfert placerait $A$ seul à −100 dès le jour 1 et $B$ seul à +130 au jour 3.

### 💶 Exemple — Trésorerie entre deux courtiers

$A$ reçoit un dépôt de 5 000. Plus tard, $A$ envoie 1 000 à $B$, les deux jambes le même jour.

| Cas | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | TotalPnL |
|------|------------------|-------|------------------|------------------|-------|------------------|----------|
| Après le dépôt | 5 000 | 5 000 | 0 | 0 | 0 | 0 | 0 |
| Après le transfert | 4 000 | 4 000 | 0 | 1 000 | 1 000 | 0 | 0 |
| $B$ reçoit 995 (frais 5) | 4 000 | 4 005 | −5 | 995 | 995 | 0 | −5 |
| $B$ détenu à 50 % | 4 000 | 4 000 | 0 | 500 | 1 000 | −500 | −500 |
| Sans le flux | 4 000 | 5 000 | −1 000 | 1 000 | 0 | +1 000 | 0 |

La dernière ligne correspond au même transfert lu sans le flux interne : le mouvement apparaît comme une perte pour $A$ et un gain pour $B$. Avec $B$ détenu à 50 %, le saut de −500 est le résidu $(s_B - s_A)\,V = (0{,}5 - 1) \times 1\,000$, et le TotalPnL le montre aussi.

---

## 📊 Modèle de trésorerie à trois réservoirs {: #three-pool-cash-model }

Le graphique de croissance décompose la trésorerie actuelle en deux agrégats visibles plus un suivi global caché :

$$
\mathrm{Cash}(t) \approx \sum_b K_b(t) + \sum_b R_b(t)
$$

| Réservoir | Portée | Signification |
|------|-------|---------|
| $K_b$ | Par courtier | Capital externe encore chez le courtier $b$ |
| $R_b$ | Par courtier | Rendements générés encore chez le courtier $b$ |
| $W$ | Global | Rendements qui ont quitté le système (restaurables lors d'un re-dépôt) |

!!! info "Propriétés clés"

    - $\mathrm{CapitalBaseline}$ = somme historique des flux de trésorerie et de capital en nature. $\sum K_b$ = quelle part de la trésorerie actuelle est du capital externe. Ils divergent après un BUY/SELL.
    - Un BUY chez le courtier $b_1$ ne consomme que $R_{b_1}$, jamais $R_{b_2}$.
    - Les transferts de trésorerie entre courtiers déplacent $R$ et $K$ de la source vers la destination sans toucher à $W$.

🔗 Règles complètes de mise à jour par courtier : **[Moteur de portefeuille — §6 Modèle de trésorerie à trois réservoirs](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)**

---

## 📝 Exemples détaillés

### 🧾 A — Dépôt → Achat → Vente avec gain

| Étape | Tx | $K$ | $R$ | Trésorerie |
|------|----|-----|-----|------|
| 1 | DEPOSIT 1 000 € | 1 000 | 0 | 1 000 |
| 2 | BUY 1 000 € | 0 | 0 | 0 |
| 3 | SELL P=1 200 €, C=1 000 € | 1 000 | 200 | 1 200 |

TotalPnL = 1 200 − 1 000 = **+200 €** ✓

### 💸 B — Dividende puis retrait

| Étape | Tx | $K$ | $R$ | $W$ | Trésorerie |
|------|----|-----|-----|-----|------|
| 1 | DEPOSIT 1 000 € | 1 000 | 0 | 0 | 1 000 |
| 2 | DIVIDEND 50 € | 1 000 | 50 | 0 | 1 050 |
| 3 | WITHDRAWAL 100 € (K d'abord) | 900 | 50 | 0 | 950 |
| 4 | WITHDRAWAL 950 € (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | RE-DEPOSIT 30 € (restaure min(30,W=50)=30) | 0 | 30 | 20 | 30 |

Après l'étape 5 : Trésorerie=30, K=0, R=30 ✓ (rendements restaurés depuis W)

### 🧪 C — Régression de vente totale

| Étape | Tx | $K$ | $R$ | Trésorerie |
|------|----|-----|-----|------|
| 1 | DEPOSIT 1 000 €, BUY 1@1 000 € | 0 | 0 | 0 |
| 2 | SELL 1@1 005 € (C=1000, G=5) | 1 000 | 5 | 1 005 |

Le capital retourne correctement en $K$ ; seuls 5 € de gain vont en $R$. **Non**, les 1 005 € ne vont pas tous en $R$.

---

## ⚙️ Implémentation

Le modèle à 3 réservoirs s'exécute dans une **boucle unique par transaction** (événementielle, non par delta quotidien) :

1. On prend la part de la transaction dans le pool de PRU de sa position, calculée avant le rejeu — pour un SELL, le coût qu'elle retire ($C$ = PRU avant vente × quantité vendue, aux taux historiques)
2. On met à jour K/R/W selon les règles du type de transaction, avec ce $C$ pour un SELL

La série d'entrée du ROI/TWRR/MWRR est dérivée des variations jour après jour de `cumulative_external_cash_flow`, la référence de capital. Elle n'est pas dérivée du champ `external_cash_flow` limité à la trésorerie.

🔗 Voir **[Moteur de portefeuille — §6](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)** pour toutes les règles formelles.

---

## 🔗 Liens connexes

- 💼 [NAV](nav.md) — l'autre terme du PnL total
- 📊 [P&L période](period-pnl.md) — version fenêtrée
- ⚙️ [Moteur de portefeuille](index.md) — modèle mathématique complet
- 📈 [Vue d'ensemble des métriques de performance](../index.md) — toutes les métriques de performance en un coup d'œil
