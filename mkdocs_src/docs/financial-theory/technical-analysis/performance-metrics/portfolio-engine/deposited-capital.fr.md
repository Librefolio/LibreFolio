# 💸 Capital versé, P&L total et poches de trésorerie

## 💡 Aperçu du concept

**Base de capital** = capital économique cumulé apporté depuis l'origine :

$$
\mathrm{CapitalBaseline}(t)=
\sum_{\tau \leq t}\mathrm{ExternalCashFlow}(\tau)
+ \sum_{\tau \leq t}\mathrm{InKindCapital}(\tau)
$$

**P&L total** = toute la valeur générée au-delà des apports externes :

$$
\boxed{\mathrm{TotalPnL}(t) = \mathrm{NAV}(t) - \mathrm{CapitalBaseline}(t)}
$$

`InKindCapital` couvre les titres qui entrent ou sortent du périmètre sans liquidités :

- les lignes ADJUSTMENT entrantes portant un coût de base (`cost_basis_override`, non liées à une division), **au coût** : le coût qu'elles ajoutent à la position ; une ligne sortante ne compte jamais : elle n'a pas de valeur ([Ajustements sortants](#outgoing-adjustments)) ;
- les jambes TRANSFER dont l'autre jambe n'est pas dans le périmètre — elle se trouve chez un courtier hors de la vue, est manquante ou n'a jamais été liée — **à la valeur de marché** à leur propre date : $+$ pour les titres reçus, $-$ pour les titres envoyés. Une jambe reçue avec un coût de base, pour un titre sans cotation et sans autre opération à sa date ou avant, donne au titre son prix : son propre coût, sous forme d'[estimation](price-resolution.md#transfer-cost-estimate), donc à sa date sa valeur de marché est ce coût et la jambe est neutre. Un titre sans aucun prix à cette date — aucune cotation, aucun BUY ou SELL et aucune telle estimation à cette date ou avant — compte **au coût** à la place : le coût que la jambe déplace dans sa position, le coût qu'une jambe reçue ajoute ou le PRU qu'une jambe envoyée retire. Un coût inconnu compte pour zéro, comme dans le coût propre de la position. Tant que le coût de la position est complet, la NAV valorise la position à ce même coût et la jambe est neutre ; avec une partie du coût inconnue, la position n'a pas de valeur dans la NAV, mais la jambe déplace tout de même son coût connu, donc rien ne reste dans le capital une fois les unités parties. Rien ne compte si le titre ne peut pas être valorisé ce jour-là : il a un prix, mais le taux de change manque.

Ces lignes déplacent de la valeur sans liquidités : elles constituent du capital, et non un profit ou une perte. Un ADJUSTMENT sortant n'est pas du capital : il réalise une perte égale au PRU abandonné par sa position.

---

## 🎯 Ce qui compte

| Transaction | Effet sur la base de capital |
|------------|-----------------|
| DEPOSIT / WITHDRAWAL (non lié) | ✅ Oui |
| CASH\_TRANSFER / FX\_CONVERSION dont l'autre jambe est hors de la vue, manquante ou jamais liée (orpheline) | ✅ Oui, à hauteur de son montant, comme un dépôt ou un retrait |
| CASH\_TRANSFER / FX\_CONVERSION / TRANSFER avec les deux jambes dans la vue (paire interne) | ❌ Non. Par courtier, une paire entre deux courtiers déplace le capital de l'expéditeur vers le destinataire le jour d'arrivée, pour un total nul ([Transferts internes](#internal-transfers-broker-lines)) |
| TRANSFER de titres dont l'autre jambe est hors de la vue, manquante ou jamais liée (orpheline) | ✅ Oui, en capital en nature à la valeur de marché à sa date, ou au coût pour un titre sans aucun prix |
| ADJUSTMENT entrant avec `cost_basis_override`, non lié à une division | ✅ Oui, en capital en nature au coût |
| ADJUSTMENT sortant | ❌ Non : il n'a pas de valeur et réalise une perte égale au coût de ses unités ([ci-dessous](#outgoing-adjustments)) |
| ADJUSTMENT lié à une division | ❌ Non, simple remise à l'échelle de la quantité |
| BUY, SELL, DIVIDEND, INTEREST, FEE, TAX | ❌ Non |
| Variation du taux de change sur des liquidités détenues dans une autre devise (aucune transaction) | ❌ Non : c'est un résultat, faisant partie du P&L total ; les flux de capital (dépôts, retraits, jambes de liquidités orphelines) sont entrés dans la base au taux de leurs propres dates |

---

## 📤 Ajustements sortants {: #outgoing-adjustments }

Un ADJUSTMENT qui retire $|q|$ unités de l'actif $a$ du courtier $b$ à la date $d$ — unités données, envoyées vers un compte que LibreFolio ne suit pas, ou supprimées par une correction — **n'a pas de valeur**, quel que soit le coût de base porté par la ligne : il ne fait que réduire la quantité. La position abandonne le coût historique de ces unités, à son [prix de revient unitaire (PRU)](../weighted-average-cost.md) avant l'ajustement, chaque achat étant valorisé au taux de sa propre date, et rien ne revient :

$$
C = s_b \cdot |q| \cdot w_{\text{pre}}(a,b)
$$

$$
\Delta\mathrm{CapitalBaseline}(d) = 0, \qquad \mathrm{Realized} = -C
$$

$s_b$ est la [quote-part de propriété](../../../../user/brokers/sharing.md) du courtier.

- **Capital.** Rien ne quitte la base de capital, ni le capital de la ligne du courtier $b$. Aucune liquidité ne bouge, donc les [poches de trésorerie](#three-pool-cash-model) ne changent pas.
- **Réalisé.** $-C$ compte dans la plus-value ou moins-value réalisée de la période et dans la contribution de la position ([P&L période](period-pnl.md)), et est exclu, comme pour une vente, lorsque le coût de la position est incomplet. Le PRU des unités restantes ne change pas.
- **Rendements.** TWRR et MWRR prennent leurs flux dans les variations de la base de capital, donc l'ajustement n'est pas un flux : la valeur des unités quitte la NAV, et le rendement du jour l'interprète comme une perte.

!!! example "Deux actions données"

    Devise de reporting EUR, quote-part 100 %. Un dépôt de €500 achète 10 actions à €50 ; le prix monte à €80. Un ADJUSTMENT de −2 actions en donne deux, le prix restant inchangé ce jour-là : $C = 2 \times 50 = 100$.

    | Moment | NAV | CapitalBaseline | TotalPnL | P&L réalisé |
    |--------|-----|-----------------|----------|----------|
    | Avant l'ajustement | 800 | 500 | +300 | 0 |
    | Après l'ajustement | 640 | 500 | +140 | −100 |

    Les 8 actions restantes conservent un PRU de 50 €, donc leur plus-value latente est $8 \times (80 - 50) = 240$, et $-100 + 240 = +140$. Le flux du jour est de 0, donc le TWRR donne $640 / 800 - 1 = -20\%$ ce jour-là.

---

## 🔀 Transferts internes dans les lignes par courtier {: #internal-transfers-broker-lines }

Avec deux courtiers ou plus dans le périmètre, le [graphique P&L](../../../../user/dashboard/charts.md#pnl-line) trace une ligne par courtier. Chaque courtier $b \in S$ a sa propre NAV, son propre capital et son propre P&L :

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

La ligne d'un courtier est donc le P&L gagné pendant que la valeur se trouvait chez ce courtier, ou qu'elle voyageait depuis celui-ci. Ce n'est pas la plus-value latente des positions détenues par le courtier.

### 📐 Le flux interne

Une **paire interne** est un CASH\_TRANSFER, FX\_CONVERSION ou TRANSFER lié dont les deux jambes se trouvent toutes deux dans $S$, sur deux courtiers différents : l'expéditeur $A$ (la jambe sortante) et le destinataire $B$ (la jambe entrante). Elle produit un flux, le **jour d'arrivée** $t_{arr}$, à la date de la jambe la plus tardive :

$$
\mathrm{Internal}_A(t_{arr}) = -X,
\qquad
\mathrm{Internal}_B(t_{arr}) = +X,
\qquad
X = s_A \cdot V(t_{arr})
$$

$s_A$ est la [quote-part de propriété](../../../../user/brokers/sharing.md) de l'expéditeur et $V(t_{arr})$ la valeur totale que l'arrivée apporte à $B$ ce jour-là, valorisée exactement comme la NAV la valorise :

| Paire | $V(t_{arr})$ |
|------|--------------|
| CASH\_TRANSFER | Le montant reçu, converti au taux $\mathrm{fx}(c, C^*, t_{arr})$ |
| FX\_CONVERSION entre courtiers | La jambe reçue, convertie de la même manière : $-1{,}000$ USD chez $A$ → $+900$ EUR chez $B$ donne $V = 900$ EUR, et le coût de conversion reste dans la ligne de $A$ |
| TRANSFER de titres | $\mathrm{MV}$ de la quantité reçue au [prix de valorisation](index.md#2-valuation-price) de $t_{arr}$, le dernier prix connu étant reporté s'il n'y en a aucun ce jour-là. En l'absence de tout prix à $t_{arr}$ ou avant, le coût de base que les unités ajoutent à la position de $B$ — le coût enregistré sur la jambe de $B$, converti à la date de cette jambe —, puisque la NAV valorise une position sans prix à son coût ([§3](index.md#3-position-state)) |

Avec des quote-parts égales, $X$ correspond exactement à ce que l'arrivée ajoute à $\mathrm{NAV}_B$, donc aucune des deux lignes ne saute. La $\mathrm{CapitalBaseline}$ du périmètre n'est pas touchée, car un mouvement interne n'est pas du capital externe : la NAV, la CapitalBaseline, le TotalPnL et ses bougies, le ROI, le TWRR, le MWRR et les liquidités sont identiques à ce qu'ils seraient sans le flux. Seule la répartition de la base entre les courtiers change.

### ✈️ Valeur en transit

Lorsque les jambes tombent à des dates différentes, la valeur voyage du jour de départ $t_{dep}$ au jour précédant $t_{arr}$. Pendant ce temps, elle fait partie de $\mathrm{InTransit}_A$, à la quote-part $s_A$ de l'expéditeur, valorisée chaque jour : les liquidités au taux de change du jour, les titres au prix de valorisation du jour (au coût enregistré sur le transfert si le titre n'a aucun prix). Aucun flux n'a lieu pendant que la valeur voyage, donc ses variations de prix et de taux de change restent dans la ligne de $A$, y compris la variation propre au jour d'arrivée ; la ligne de $B$ part de la valeur reçue.

Par exemple, $A$ reçoit un dépôt de 1,000 USD au jour 0 à 0.90 EUR par USD ($C_A = 900$) et envoie les dollars au jour 1 ; $B$ les reçoit au jour 4. Avec un taux de 0.90, 0.91, 0.92, 0.93 aux jours 1 à 4, la ligne de $A$ affiche 0, +10, +20, +30 et celle de $B$ reste à 0. Au jour 4, $X = 930$ et $C_A = 900 - 930 = -30$. Une fois arrivés, les dollars constituent les liquidités de $B$, réévaluées chaque jour, donc à partir du jour 5, la ligne de $B$ évolue avec le taux : à 0.94, elle affiche +10.

### 🧩 Cas particuliers

- **Quote-parts de propriété différentes.** $X$ utilise $s_A$, comme la valeur en transit, tandis que l'arrivée ajoute $s_B \cdot V(t_{arr})$ à $\mathrm{NAV}_B$. La ligne de $B$ conserve un écart résiduel de $(s_B - s_A)\,V(t_{arr})$ le jour d'arrivée, et le TotalPnL présente le même écart, avec ou sans le flux.
- **Valeur inconnue le jour d'arrivée.** Si $V(t_{arr})$ ne peut pas être calculée — un taux de change manque, ou le titre n'a aucune observation à $t_{arr}$ ou avant ($\operatorname{mark} = \varnothing$) et le coût sur la jambe de $B$ est inconnu (aucun coût de base, ou un coût de base sans taux de change), de sorte que l'arrivée n'ajoute rien au coût de la position de $B$ — alors $X = 0$. Rien n'est deviné : le saut subsiste, et la valeur du titre apparaît dans la ligne du courtier qui le détient à partir de son premier prix.
- **Aucun prix du tout.** Un titre sans observation à $t_{arr}$ ou avant se déplace au coût que son arrivée ajoute à la position de $B$ — le coût enregistré sur la jambe de $B$, le PRU de l'expéditeur lorsque le transfert est enregistré avec un coût de base automatique —, que le coût de $B$ soit complet ou non. Lorsque le coût de $B$ est complet, c'est la valeur à laquelle la $\mathrm{NAV}_B$ prend les unités, donc avec des quote-parts égales, la ligne de $B$ ne saute pas. Le coût n'a pas besoin d'être égal à la valeur que les unités avaient chez $A$ avant leur départ, ni au coût de base propre de $A$ — ou à rien lorsque ce coût était incomplet ; la différence finit dans la ligne de $A$, et le TotalPnL la présente aussi. Lorsque le coût de $B$ est incomplet — $B$ détenait déjà des unités de coût inconnu —, la position de $B$ n'a pas de valeur dans la NAV, qui est incomplète : la ligne de $B$ absorbe l'écart, son propre coût inconnu, et la ligne de $A$ est la même qu'avec un coût complet chez $B$.
- **Frais.** Ils ne font pas partie de $X$. Une ligne FEE de 5 enregistrée chez l'expéditeur, ou les mêmes 5 sous forme d'écart entre les jambes ($-1{,}000$ envoyés, $+995$ reçus, donc $X = 995$), reste dans la ligne de $A$ comme une perte de 5.
- **Paires sur un même courtier.** Deux jambes chez le même courtier, comme une conversion de devise au sein d'un même compte, n'ont besoin d'aucun flux : la valeur ne quitte jamais la ligne.
- **Paires d'ADJUSTMENT.** Ce ne sont pas des paires internes : chaque jambe suit sa propre règle (voir le tableau ci-dessus). Le capital du destinataire augmente du coût que sa jambe ajoute ; la jambe de l'expéditeur n'a pas de valeur, donc son capital ne bouge pas et elle réalise une perte égale à son PRU ([Ajustements sortants](#outgoing-adjustments)). Avec la configuration de l'exemple ci-dessous et les deux jambes au jour 2, la jambe reçue à un coût de 10 : la ligne de $A$ chute à $-100$ et celle de $B$ affiche $+20$, donc le TotalPnL passe de $+20$ à $-80$. Pour déplacer des unités entre deux courtiers sans cette perte, liez les deux ajustements en une paire TRANSFER.

### 🔍 Vues filtrées

Dans une vue ne contenant que certains courtiers, une jambe TRANSFER dont l'autre jambe est hors de $S$ — ou manquante, ou jamais liée — ne peut pas former de paire interne. Elle constitue du capital en nature à la valeur de marché à sa propre date : $+\mathrm{MV}$ pour les titres reçus, $-\mathrm{MV}$ pour les titres envoyés, à la quote-part de ce courtier — au coût pour un titre sans aucun prix, comme ci-dessus — et rien si le titre ne peut pas être valorisé ce jour-là. Contrairement à un flux interne, elle déplace la CapitalBaseline de la vue, donc le TotalPnL, le ROI, le TWRR et le MWRR de la vue la traitent comme du capital, à l'image d'un ADJUSTMENT en nature. Une jambe CASH\_TRANSFER ou FX\_CONVERSION dans la même position est de la trésorerie externe à hauteur de son montant, comme un dépôt ou un retrait, et elle déplace les [poches de trésorerie](#three-pool-cash-model) comme le ferait ce dépôt ou ce retrait : la répartition de la trésorerie de la vue entre capital apporté et rendements générés, ainsi que le financement de ses achats ultérieurs, la suivent.

Lorsque le courtier détenant l'autre jambe est supprimé, la jambe restante devient ce qui reste après la séparation de la paire, et les jambes laissées par les anciennes versions sont converties de la même manière au démarrage : les titres deviennent un ADJUSTMENT — une jambe reçue en capital en nature au coût lorsqu'elle porte un coût de base (tableau ci-dessus), et non plus à la valeur de marché ; une jambe envoyée devient un ADJUSTMENT sortant sans valeur, qui réalise une perte égale au coût de ses unités ([Ajustements sortants](#outgoing-adjustments)) — et les liquidités deviennent un DEPOSIT ou un WITHDRAWAL. Les lignes converties suivent les mêmes règles dans toutes les vues, y compris la vue complète.

Comparaison entre la vue propre d'un courtier et la vue combinée :

- **Le destinataire seul correspond à sa ligne combinée.** Dans la vue propre de $B$, les titres reçus constituent du capital à leur valeur de marché à $t_{arr}$, qui est le $X$ de la vue combinée. Cela vaut avec des quote-parts égales et un prix que les deux vues peuvent voir : un prix qui provient uniquement de transactions chez $A$ n'est pas visible dans la vue propre de $B$.
- **L'expéditeur seul perd les variations en transit.** Dans la vue propre de $A$, son capital baisse le jour du départ de $s_A \cdot V(t_{dep})$, tandis que dans la vue combinée, la valeur reste chez $A$ jusqu'à son arrivée.

En notant $\mathrm{PnL}_A^{(S)}$ la ligne de $A$ dans la vue de périmètre $S$, à partir du jour de départ :

$$
\mathrm{PnL}_A^{(A)}(t) = \mathrm{PnL}_A^{(A,B)}(t) - s_A\bigl[V(\min(t, t_{arr})) - V(t_{dep})\bigr]
$$

### 📦 Exemple — Titres en transit

Tous les montants sont en EUR, quote-parts 100 %. $A$ reçoit un dépôt de 100 et achète 10 unités à 10 au jour 0. Le prix est de 10, 11, 12, 13, 14, 15 aux jours 0 à 5. $A$ envoie les 10 unités au jour 1, et $B$ les reçoit au jour 3.

**Vue combinée** (les deux courtiers dans $S$) :

| Jour | Prix | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | TotalPnL |
|-----|-------|------------------|-------|------------------|------------------|-------|------------------|----------|
| 0 | 10 | 100 | 100 | 0 | 0 | 0 | 0 | 0 |
| 1 | 11 | 110 (en transit) | 100 | +10 | 0 | 0 | 0 | +10 |
| 2 | 12 | 120 (en transit) | 100 | +20 | 0 | 0 | 0 | +20 |
| 3 | 13 | 0 | −30 | +30 | 130 | 130 | 0 | +30 |
| 4 | 14 | 0 | −30 | +30 | 140 | 130 | +10 | +40 |
| 5 | 15 | 0 | −30 | +30 | 150 | 130 | +20 | +50 |

Au jour 3, le flux $X = 10 \times 13 = 130$ déplace le capital de $A$ vers $B$. $A$ conserve les +30 gagnés pendant que les unités étaient chez $A$ ou en transit (10 → 13), et $B$ gagne à partir de 13. $C_A$ devient négatif parce que $A$ a transmis plus de valeur (130) que le capital qu'il a reçu (100) : la différence constitue son gain. Le TotalPnL est identique avec ou sans le flux ; sans celui-ci, au jour 3, la ligne de $A$ chuterait à $0 - 100 = -100$ et celle de $B$ sauterait à $130 - 0 = +130$.

**Vues d'un seul courtier** :

| Jour | $B$ seul : $C_B$ | $B$ seul : $\mathrm{PnL}_B$ | $A$ seul : $C_A$ | $A$ seul : $\mathrm{PnL}_A$ |
|-----|------------------|-----------------------------|------------------|-----------------------------|
| 0 | — | — | 100 | 0 |
| 1 | — | — | −10 | +10 |
| 2 | — | — | −10 | +10 |
| 3 | 130 | 0 | −10 | +10 |
| 4 | 130 | +10 | −10 | +10 |
| 5 | 130 | +20 | −10 | +10 |

La vue propre de $B$ commence à sa première transaction et correspond à $B$ dans la vue combinée. Dans la vue propre de $A$, les unités partent au jour 1 à $10 \times 11 = 110$, donc $C_A = 100 - 110 = -10$ et la ligne reste à +10 : la variation de 11 à 13 pendant le transit n'y figure pas, et $+30 - (130 - 110) = +10$. Si on la comptait comme un gain ou une perte plutôt que comme du capital, le même transfert placerait $A$ seul à −100 dès le jour 1 et $B$ seul à +130 au jour 3.

### 💶 Exemple — Liquidités entre deux courtiers

$A$ reçoit un dépôt de 5,000. Plus tard, $A$ envoie 1,000 à $B$, les deux jambes le même jour.

| Cas | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | TotalPnL |
|------|------------------|-------|------------------|------------------|-------|------------------|----------|
| Après le dépôt | 5,000 | 5,000 | 0 | 0 | 0 | 0 | 0 |
| Après le transfert | 4,000 | 4,000 | 0 | 1,000 | 1,000 | 0 | 0 |
| $B$ reçoit 995 (frais 5) | 4,000 | 4,005 | −5 | 995 | 995 | 0 | −5 |
| $B$ détenu à 50 % | 4,000 | 4,000 | 0 | 500 | 1,000 | −500 | −500 |
| Sans le flux | 4,000 | 5,000 | −1,000 | 1,000 | 0 | +1,000 | 0 |

La dernière ligne correspond au même transfert lu sans le flux interne : le mouvement apparaît comme une perte pour $A$ et un gain pour $B$. Avec $B$ détenu à 50 %, l'écart de −500 est le résidu $(s_B - s_A)\,V = (0.5 - 1) \times 1{,}000$, et le TotalPnL le présente aussi.

---

## 📊 Modèle de trésorerie à trois poches {: #three-pool-cash-model }

Le graphique de croissance décompose la trésorerie actuelle en deux agrégats visibles plus un compteur global masqué :

$$
\mathrm{Cash}(t) \approx \sum_b K_b(t) + \sum_b R_b(t)
$$

| Poche | Périmètre | Signification |
|------|-------|---------|
| $K_b$ | Par courtier | Capital externe encore chez le courtier $b$ |
| $R_b$ | Par courtier | Rendements générés encore chez le courtier $b$ |
| $W$ | Global | Rendements sortis du système (restaurables lors d'un nouveau dépôt) |

!!! info "Propriétés clés"

    - $\mathrm{CapitalBaseline}$ = somme historique des flux de liquidités et de capital en nature. $\sum K_b$ = part de la trésorerie actuelle qui est du capital externe. Elles divergent après un BUY/SELL.
    - Un BUY chez le courtier $b_1$ ne consomme que $R_{b_1}$, jamais $R_{b_2}$.
    - Les virements entre courtiers et les conversions de devise dont les deux jambes sont dans le périmètre déplacent $R$ et $K$ de la source vers la destination sans toucher $W$ : le départ fait d'abord sortir les rendements, et l'arrivée rapporte ce qu'elle a prélevé sur le capital et les rendements ; tout écart entre les deux jambes — une autre devise, le taux d'un autre jour, une autre quote-part de propriété — constitue un résultat.
    - Une jambe de virement ou de conversion dont l'autre jambe est hors du périmètre, ou qui a perdu sa paire, déplace les poches comme un DEPOSIT ou un WITHDRAWAL de son montant : à l'arrivée, elle restaure d'abord les rendements retirés depuis $W$ dans $R_b$ et le reste va à $K_b$ ; au départ, elle prélève d'abord $K_b$, puis $R_b$, qui va vers $W$ ([exemple E](#e-cash-from-outside-the-view)).
    - Un résultat de change sur des liquidités qu'un courtier détient dans une autre devise va dans $R_b$ ; une perte supérieure à $R_b$ est imputée sur $K_b$, comme le fait une FEE. La $\mathrm{CapitalBaseline}$ ne bouge pas ([Moteur de portefeuille — §6](index.md#exchange-result-on-foreign-cash)).

🔗 Règles complètes de mise à jour par courtier : **[Moteur de portefeuille — §6 Modèle à trois poches](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)**

---

## 📝 Exemples détaillés

### 🧾 A — Dépôt → Achat → Vente avec gain

| Étape | Tx | $K$ | $R$ | Trésorerie |
|------|----|-----|-----|------|
| 1 | DEPOSIT €1,000 | 1,000 | 0 | 1,000 |
| 2 | BUY €1,000 | 0 | 0 | 0 |
| 3 | SELL P=€1,200, C=€1,000 | 1,000 | 200 | 1,200 |

TotalPnL = 1,200 − 1,000 = **+€200** ✓

### 💸 B — Dividende puis retrait

| Étape | Tx | $K$ | $R$ | $W$ | Trésorerie |
|------|----|-----|-----|-----|------|
| 1 | DEPOSIT €1,000 | 1,000 | 0 | 0 | 1,000 |
| 2 | DIVIDEND €50 | 1,000 | 50 | 0 | 1,050 |
| 3 | WITHDRAWAL €100 (K d'abord) | 900 | 50 | 0 | 950 |
| 4 | WITHDRAWAL €950 (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | RE-DEPOSIT €30 (restaure min(30,W=50)=30) | 0 | 30 | 20 | 30 |

Après l'étape 5 : Trésorerie=30, K=0, R=30 ✓ (rendements restaurés depuis W)

### 🧪 C — Régression de vente totale

| Étape | Tx | $K$ | $R$ | Trésorerie |
|------|----|-----|-----|------|
| 1 | DEPOSIT €1,000, BUY 1@€1,000 | 0 | 0 | 0 |
| 2 | SELL 1@€1,005 (C=1000, G=5) | 1,000 | 5 | 1,005 |

Le capital revient correctement à $K$ ; seul un gain de €5 va à $R$. **Pas** la totalité des €1,005 à $R$.

### 💱 D — Dollars détenus pendant que le taux varie

Un seul courtier, devise de reporting EUR, taux en EUR par USD ; $\varepsilon$ est le [résultat de change sur les liquidités](index.md#exchange-result-on-foreign-cash).

| Étape | Événement | $\varepsilon$ | $K$ | $R$ | Trésorerie | TotalPnL |
|------|-------|---------------|-----|-----|------|----------|
| 1 | DEPOSIT 1,000 USD à 0.90 | — | 900 | 0 | 900 | 0 |
| 2 | Le taux monte à 0.95 | +50 | 900 | 50 | 950 | +50 |
| 3 | Le taux chute à 0.85 ($R$ = 50 − 100, $K$ absorbe −50) | −100 | 850 | 0 | 850 | −50 |
| 4 | BUY de 1,000 USD à 0.85 (€850) | — | 0 | 0 | 0 | MV − 900 |

La CapitalBaseline reste à €900 tout au long : les résultats de change sont des profits et pertes, pas du capital. Après l'étape 4, le TotalPnL est la valeur de marché MV du titre moins les €900 déposés — −50 le jour de l'achat si MV est égale aux €850 payés.

### 🔀 E — Liquidités provenant de l'extérieur de la vue {: #e-cash-from-outside-the-view }

La vue du courtier $B$ seul ; le courtier $A$ en est exclu, donc chaque virement entre eux est un flux externe de la vue, comme dans les vues filtrées ci-dessus.

| Étape | Tx chez $B$ | $K$ | $R$ | $W$ | Trésorerie |
|------|-----------|-----|-----|-----|------|
| 1 | DEPOSIT €100, INTEREST €100 | 100 | 100 | 0 | 200 |
| 2 | CASH\_TRANSFER €150 vers $A$, comme un WITHDRAWAL (K=100→0, R=100→50, W+=50) | 0 | 50 | 50 | 50 |
| 3 | CASH\_TRANSFER €100 depuis $A$, comme un DEPOSIT (restaure min(100,W=50)=50, les 50 autres vont à K) | 50 | 100 | 0 | 150 |
| 4 | BUY €100 (R d'abord) | 50 | 0 | 0 | 50 |

L'achat de l'étape 4 est entièrement constitué de rendements réinvestis, sans aucun nouveau capital. Il en va de même pour une jambe de virement qui a perdu sa paire, dans toutes les vues. Dans la vue de $A$ et $B$ réunis, les deux virements sont au contraire des paires internes et déplacent les poches d'un courtier à l'autre, sans toucher $W$.

---

## ⚙️ Implémentation

Le modèle à 3 poches fonctionne dans une **boucle unique par transaction** (pilotée par les événements, et non par delta quotidien) :

1. Prendre la variation de la transaction dans le pool de PRU de sa position, calculée avant le rejeu — pour un SELL, le coût qu'elle retire ($C$ = PRU avant vente × quantité vendue, aux taux historiques)
2. Mettre à jour K/R/W selon les règles propres au type de transaction, avec ce $C$ pour un SELL

Chaque jour où le taux de change d'une devise étrangère détenue sous forme de liquidités varie, le résultat de change de chaque courtier sur ces liquidités est également comptabilisé dans ses poches, après les mouvements de trésorerie du jour et avant les transactions du jour ([§6](index.md#exchange-result-on-foreign-cash)).

La série d'entrée ROI/TWRR/MWRR est dérivée des variations d'un jour à l'autre de `cumulative_external_cash_flow`, la base de capital. Elle n'est pas dérivée du champ `external_cash_flow`, qui ne concerne que les liquidités.

🔗 Voir **[Moteur de portefeuille — §6](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)** pour toutes les règles formelles.

---

## 🔗 Voir aussi

- 💼 [NAV](nav.md) — l'autre terme du P&L total
- 📊 [P&L période](period-pnl.md) — version fenêtrée
- ⚙️ [Moteur de portefeuille](index.md) — modèle mathématique complet
- 📈 [Vue d'ensemble des métriques de performance](../index.md) — toutes les métriques de performance en un coup d'œil
