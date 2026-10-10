# ⚙️ Moteur de portefeuille — Modèle mathématique

## 💡 Vue d'ensemble

Cette page définit formellement le modèle mathématique qui sous-tend le moteur de calcul de portefeuille de LibreFolio. Toutes les autres pages de métriques ([NAV](nav.md), [Valeur comptable](book-value.md), [P&L période](period-pnl.md), [Rendement sur coût](yield-on-cost.md), [PRU](../weighted-average-cost.md), [Capital versé](deposited-capital.md)) font référence à cette page pour leurs règles de calcul précises.

---

## 📐 1. Notation et ensembles

| Symbole | Signification |
|--------|---------|
| $V(u)$ | Tous les courtiers visibles par l'utilisateur $u$ |
| $S \subseteq V(u)$ | Périmètre de courtiers sélectionné (filtré) |
| $A$ | Ensemble des actifs avec positions |
| $C^*$ | Devise cible |
| $[t_0, t_1]$ | Cadre d'évaluation demandé |
| $q(a,b,t)$ | Quantité de l'actif $a$ chez le courtier $b$ à la date $t$ |
| $p(a,t)$ | Prix de valorisation de l'actif $a$ à la date $t$ |
| $\mathrm{fx}(c_1, c_2, t)$ | Taux de change de la devise $c_1$ vers $c_2$ à la date $t$ |

---

## 📐 2. Prix de valorisation {: #2-valuation-price }

$$
\operatorname{mark}(a,t)=
\begin{cases}
\text{MARKET}(a,t) & \text{cotation actif-système du jour}\\
\operatorname{avg}(\text{TRADE}(a,t)) & \text{observations ACHAT/VENTE/AJUSTEMENT valorisées du jour}\\
\text{dernière observation avant }t & \text{reportée (LOCF)}\\
\varnothing & \text{aucune observation à la date }t\text{ ou avant}
\end{cases}
$$

- Le résolveur unifié est l'unique cerveau de valorisation : `MARKET → TRADE_AVG → CARRIED → MISSING`.
- `CARRIED` correspond à la dernière observation reportée (LOCF). Il transporte les métadonnées d'obsolescence `days_back`.
- `estimated=True` indique une origine TRADE. Une cotation MARKET reportée obsolète est obsolète, pas estimée.
- Les valorisations restent en devise native ; chaque consommateur les convertit en $C^*$ à la date de valorisation $t$.
- Le taux de change du coût de base reste fixé à la date de transaction.
- Le PRU n'est **jamais** utilisé comme prix de valorisation.

Voir [Résolution des prix](price-resolution.md) pour le contrat du résolveur et la sémantique de qualité des données.

---

## 📐 3. État de position {: #3-position-state }

Pour chaque position $(a, b)$ avec $q(a,b,t) > 0$ :

$$
\mathrm{MV}(a,b,t) =
\frac{q(a,b,t)}{qbq(a)}\cdot
\operatorname{mark}(a,t)\cdot
\mathrm{fx}\bigl(\mathrm{ccy}_{mark}, C^*, t\bigr)
$$

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \cdot w(a,b,t)
$$

$$
\mathrm{UGL}(a,b,t) = \mathrm{MV}(a,b,t) - \mathrm{CB}(a,b,t)
$$

Où $w(a,b,t)$ est le [Prix de revient unitaire (PRU)](../weighted-average-cost.md) pour la position $(a,b)$ à la date $t$, conservé en $C^*$ aux taux historiques (§4) : le coût de base ne prend aucun taux de change à $t$, donc pour un actif étranger, l'effet de taux de change fait partie de $\mathrm{UGL}$.

---

## 📐 4. Mise à jour itérative du PRU

Maintenu par position $(a,b)$ avec l'état du pool $(\hat{q}, \hat{c})$, le coût $\hat{c}$ conservé en $C^*$ :

**Acquisition** (qté $> 0$, montant $P$ payé en devise $c$ à la date $d$) :

$$
\hat{q}_{\text{new}} = \hat{q} + q_{\text{tx}}, \quad
\hat{c}_{\text{new}} = \hat{c} + P \cdot \mathrm{fx}(c, C^*, d), \quad
w = \frac{\hat{c}_{\text{new}}}{\hat{q}_{\text{new}}}
$$

$P$ est le montant en espèces payé pour un ACHAT, ou le coût de base unitaire imposé multiplié par $q_{\text{tx}}$ pour un TRANSFERT ou AJUSTEMENT ; $\mathrm{fx}(C^*, C^*, d) = 1$. Lorsqu'aucun taux n'existe à la date $d$ ou avant, ou que l'acquisition n'a pas de coût de base, la quantité entre et le coût n'entre pas : le coût de la position est signalé comme incomplet au lieu d'être compté comme zéro.

**Réduction** (qté $< 0$) :

$$
w_{\text{pre}} = \frac{\hat{c}}{\hat{q}}, \quad
\hat{q}_{\text{new}} = \hat{q} - |q_{\text{tx}}|, \quad
\hat{c}_{\text{new}} = \hat{q}_{\text{new}} \cdot w_{\text{pre}}
$$

**Division** (liée à un événement de division) : $\hat{q}$ change, $\hat{c}$ ne change pas.

!!! info "Ordre"

    Au sein de la même date : les ajouts sont traités avant les réductions. Cela garantit que la VENTE lit le PRU correct, y compris les ACHATS du même jour.

---

## 📐 5. Agrégation du portefeuille {: #5-portfolio-aggregation }

$$
\mathrm{MV}(t) = \sum_{(a,b) \in S} \mathrm{MV}(a,b,t)
$$

$$
\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)
$$

$$
\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)
$$

$$
\mathrm{UGL}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

---

## 📐 6. Modèle de trésorerie à trois pools — Par courtier $(K_b, R_b, W)$ {: #6-three-pool-cash-model-per-broker-k_b-r_b-w }

Trois pools d'accumulation suivent la provenance des liquidités. $K$ et $R$ sont maintenus **par courtier** $b$ ; $W$ est global (il sort complètement du système).

| Pool | Portée | Signification |
|------|-------|---------|
| $K_b$ | Par courtier | Capital externe encore chez le courtier $b$ sous forme de liquidités |
| $R_b$ | Par courtier | Rendements générés encore chez le courtier $b$ sous forme de liquidités |
| $W$ | Global | Rendements sortis du système (masqués, restaurables lors d'un nouveau dépôt) |

!!! info "Propriété clé"

    Un ACHAT chez le courtier $b_1$ ne peut consommer que $R_{b_1}$, jamais $R_{b_2}$. Les liquidités ne se téléportent pas entre courtiers — seuls les transferts explicites déplacent les soldes des pools.

### 🔁 Règles de mise à jour (par transaction sur le courtier $b$, ordre chronologique)

| Icône et type | Formules de mise à jour | Logique et description |
|:---:|---|---|
| ![](../../../../static/icons/transactions/deposit.png){: width="24" }<br>**DÉPÔT**<br>$D > 0$ | $r = \min(D,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= D - r$ | Restaure d'abord les rendements précédemment retirés depuis le suivi global $W$, puis ajoute le reste au capital $K_b$. |
| ![](../../../../static/icons/transactions/withdrawal.png){: width="24" }<br>**RETRAIT**<br>$X > 0$ | $k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$<br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Consomme d'abord le capital $K_b$, puis déplace les rendements restants $\rho$ vers le suivi global $W$. |
| ![](../../../../static/icons/transactions/dividend.png){: width="24" } ![](../../../../static/icons/transactions/interest.png){: width="24" }<br>**DIVIDENDE / INTÉRÊT**<br>$I > 0$ | $R_b \mathrel{+}= I$ | Les rendements augmentent directement le pool de rendements $R_b$. |
| ![](../../../../static/icons/transactions/fee.png){: width="24" } ![](../../../../static/icons/transactions/tax.png){: width="24" }<br>**FRAIS / IMPÔT**<br>$F > 0$ | $R_b \mathrel{-}= F$<br>$\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0$ | Consomme d'abord les rendements $R_b$ ; si $R_b$ devient négatif, il ponctionne le capital $K_b$. |
| ![](../../../../static/icons/transactions/buy.png){: width="24" }<br>**ACHAT**<br>$B > 0$ | $\rho = \min(B,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$K_b \mathrel{-}= (B - \rho)$ | Consomme d'abord les rendements $R_b$, puis ponctionne le reste sur le capital $K_b$. |
| ![](../../../../static/icons/transactions/sell.png){: width="24" }<br>**VENTE** | $G = P - C$<br>$K_b \mathrel{+}= C$<br>$R_b \mathrel{+}= G$<br>$\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b, \quad R_b = 0$ | Le coût de base $C = |q_s| \cdot w_{\text{pre}}$ retourne au capital $K_b$ ; le gain $G$ va aux rendements $R_b$ (si $G < 0$, il se comporte comme des frais).<br><br>!!! warning "Ordre critique"<br><br> $C$ doit être calculé **avant** que le pool PRU ne soit réduit (une vente totale donnerait sinon $C = 0$). |
| ![](../../../../static/icons/transactions/cash-transfer.png){: width="24" }<br>**VIREMENT**<br>(Interne, $s \to d$, $X > 0$) | **Jambe de départ ($s$) :**<br>$\rho = \min(X,\, R_s)$<br>$R_s \mathrel{-}= \rho$<br>$\kappa = X - \rho$<br>$K_s \mathrel{-}= \kappa$<br><br>**Jambe d'arrivée ($d$) :**<br>$K_d \mathrel{+}= \kappa$<br>$R_d \mathrel{+}= \rho$ | Les virements internes déplacent les allocations de pool ($R_s \to R_d$, $K_s \to K_d$) proportionnellement au solde de départ.<br>Le suivi global $W$ n'est **jamais** touché (le capital reste à l'intérieur du système). |

Si les dates de départ et d'arrivée diffèrent, le virement est en transit : soustrait de $s$ au jour de départ, ajouté à $d$ au jour d'arrivée. Entre ces dates, $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$ du montant en transit — géré par réconciliation proportionnelle.

### 🧮 Agrégation pour la sortie

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t)
$$

$$
\mathrm{CashFromReturns}(t) = \sum_{b \in S} R_b(t)
$$

### ⚖️ Invariant de réconciliation

$$
\mathrm{Cash}_{\text{like}}(t) \approx \sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)
$$

Mise à l'échelle proportionnelle par courtier appliquée si la dérive $> 0.01$ (due à l'arrondi FX ou au timing en transit).

---

## 📐 7. Contribution de période {: #7-period-contribution }

Pour la période $[t_0, t_1]$, par position $(a,b)$ :

$$
\Delta\mathrm{UGL}(a,b) = \mathrm{UGL}(a,b,t_1) - \mathrm{UGL}(a,b,t_0)
$$

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

Ensemble des positions contributrices :

$$
\mathcal{P} = \text{positions avec activité ACHAT/VENTE/AJUSTEMENT/TRANSFERT ou quantité limite}
$$

Le P&L période au niveau du portefeuille expose aussi un résidu :

$$
\mathrm{Other} =
\mathrm{PnL}_{period} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Les frais/revenus non alloués sans `asset_id` sont regroupés par courtier comme autres effets de période.

---

## 📐 8. Plus-value/moins-value réalisée

Lors d'une VENTE de $|q_s|$ unités depuis la position $(a,b)$ à la date $t$ :

$$
C = |q_s| \cdot w_{\text{pre}}(a,b)
$$

$$
\mathrm{Realized} = P_{\text{sell}} \cdot \mathrm{fx}(\mathrm{ccy}_{\text{sell}}, C^*, t) - C
$$

Où $w_{\text{pre}}$ est le PRU en $C^*$ **avant** la réduction du pool (même valeur utilisée par la règle de vente à 3 pools ci-dessus) : les unités vendues sortent à leur coût historique, sans conversion à la date de vente. Une vente dont le produit ne peut pas être converti, ou prélevée sur une position dont le coût est incomplet, est exclue du P&L réalisé.

---

## 📐 9. Architecture Pré-frame / Frame

| Phase | Plage de dates | Calcule |
|-------|-----------|----------|
| Pré-frame | $[t_{\mathrm{first}},\ t_0)$ | Liquidités, qté, PRU, pools — aucune évaluation de marché |
| Frame | $[t_0,\ t_1]$ | Quotidien complet : prix, FX, états de position, états de portefeuille |

Les transactions pré-frame mettent à jour les accumulateurs (registre de liquidités, pools PRU, K/R/W à 3 pools) sans consommer de données de prix ou FX. Cela permet un cache efficace basé sur les plages.

---

## 📐 10. Métriques de performance (couche 2)

Calculées **après** les états quotidiens, en une passe séparée :

| Métrique | Formule | Référence |
|--------|---------|-----------|
| P&L total | $\mathrm{NAV}(t) - \text{CapitalBaseline}(t)$ | [Capital versé](deposited-capital.md) |
| P&L période | $\mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \text{ECF}_{[t_0,t_1]}$ | [P&L période](period-pnl.md) |
| TWRR | $\prod_i (1 + r_i) - 1$ (chaîne de sous-périodes) | [TWRR](twrr.md) |
| MWRR | XIRR résolvant $\sum \frac{CF_i}{(1+r)^{d_i/365}} = 0$ | [MWRR](mwrr.md) |
| ROI simple | $(\mathrm{NAV} - \text{NetInvested}) / \text{NetInvested}$ | [ROI](roi.md) |
| Rendement annualisé net | $(1+r_{\mathrm{net}})^{365/d}-1$, supprimé en dessous de 30 jours | [Rendement annualisé net](net-annualized-return.md) |
| Rendement sur coût | Revenu brut de transaction sur 365 jours glissants par unité historique éligible, divisé par le PRU unitaire résiduel à $t_1$ | [Rendement sur coût](yield-on-cost.md) |
| Effet timing | $\text{MWRR}_{\text{cum}} - \text{TWRR}_{\text{cum}}$ | [Effet timing](timing-effect.md) |

---

## 🔗 Voir aussi

- 💼 [NAV](nav.md) — valorisation instantanée
- 🧭 [Résolution des prix](price-resolution.md) — résolveur de valorisation unifié
- 📈 [Rendement annualisé net](net-annualized-return.md) — définitions CAGR des positions, de la période et FIFO
- 💸 [Rendement sur coût](yield-on-cost.md) — revenu brut enregistré sur 365 jours glissants par rapport au PRU unitaire résiduel
- 📖 [Valeur comptable](book-value.md) — agrégat du coût de base
- 📊 [P&L période](period-pnl.md) — gain/perte sur fenêtre avec contribution
- 💸 [Capital versé](deposited-capital.md) — détails des 3 pools et exemples détaillés
- 📈 [PRU](../weighted-average-cost.md) — méthode de coût itérative
- 📈 [Vue d'ensemble des métriques de performance](../index.md) — toutes les métriques de performance en un coup d'œil
