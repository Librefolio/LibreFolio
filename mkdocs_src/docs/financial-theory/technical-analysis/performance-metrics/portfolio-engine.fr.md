# ⚙️ Moteur de Portefeuille — Modèle Mathématique

*[⬅️ Retour à l'aperçu des métriques de performance](index.md)*

## 💡 Aperçu

Cette page définit formellement le modèle mathématique sous-jacent au moteur de calcul de portefeuille de LibreFolio. Toutes les autres pages de métriques ([NAV](nav.md), [Valeur Comptable](book-value.md), [P&L de Période](period-pnl.md), [PMP](weighted-average-cost.md), [Capital Déposé](deposited-capital.md)) se réfèrent à cette page pour leurs règles de calcul précises.

---

## 📐 1. Notation et Ensembles

| Symbole | Signification |
|--------|---------|
| $V(u)$ | Tous les courtiers visibles pour l'utilisateur $u$ |
| $S \subseteq V(u)$ | Périmètre des courtiers sélectionnés (filtrés) |
| $A$ | Ensemble des actifs avec des positions |
| $C^*$ | Devise cible |
| $[t_0, t_1]$ | Cadre d'évaluation demandé |
| $q(a,b,t)$ | Quantité de l'actif $a$ chez le courtier $b$ à la date $t$ |
| $p(a,t)$ | Prix d'évaluation de l'actif $a$ à la date $t$ |
| $\mathrm{fx}(c_1, c_2, t)$ | Taux de change de la devise $c_1$ vers $c_2$ à la date $t$ |

---

## 📐 2. Prix d'Évaluation {: #2-valuation-price }

$$
p(a, t) = \begin{cases}
p_{\text{mkt}}(a, t) & \text{si PriceHistory} \leq t \text{ existe} \\
p_{\text{buy}}(a, t) & \text{si le dernier BUY de } V(u) \text{ existe} \\
\varnothing & \text{sinon (exclu de la NAV)}
\end{cases}
$$

- $p_{\text{mkt}}$ = comblement vers l'arrière (backward-fill) depuis PriceHistory (dernière clôture avec date $\leq t$)
- $p_{\text{buy}}$ = prix unitaire du BUY le plus récent de $a$ parmi tous les courtiers de $V(u)$, avec date $\leq t$
- Le PMP n'est **jamais** utilisé comme prix d'évaluation

---

## 📐 3. État de la Position {: #3-position-state }

Pour chaque position $(a, b)$ avec $q(a,b,t) > 0$ :

$$
\mathrm{MV}(a,b,t) = q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}\bigl(\mathrm{ccy}_p, C^*, t\bigr)
$$

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \cdot w(a,b,t) \cdot \mathrm{fx}\bigl(\mathrm{ccy}_w, C^*, t\bigr)
$$

$$
\mathrm{UGL}(a,b,t) = \mathrm{MV}(a,b,t) - \mathrm{CB}(a,b,t)
$$

Où $w(a,b,t)$ est le [prix moyen pondéré (PMP)](weighted-average-cost.md) pour la position $(a,b)$ à la date $t$.

---

## 📐 4. Mise à jour itérative du PMP

Maintenu par position $(a,b)$ avec un état de pool $(\hat{q}, \hat{c})$ :

**Acquisition** (qty $> 0$, coût unitaire $u$) :

$$
\hat{q}_{\text{new}} = \hat{q} + q_{\text{tx}}, \quad
\hat{c}_{\text{new}} = \hat{c} + u \cdot q_{\text{tx}}, \quad
w = \frac{\hat{c}_{\text{new}}}{\hat{q}_{\text{new}}}
$$

**Réduction** (qty $< 0$) :

$$
w_{\text{pre}} = \frac{\hat{c}}{\hat{q}}, \quad
\hat{q}_{\text{new}} = \hat{q} - |q_{\text{tx}}|, \quad
\hat{c}_{\text{new}} = \hat{q}_{\text{new}} \cdot w_{\text{pre}}
$$

!!! info "Ordre de traitement"

    Pour une même date : les additions sont traitées avant les réductions. Cela garantit que la VENTE lit le PMP correct incluant les ACHATS du même jour.

---

## 📐 5. Agrégation du Portefeuille {: #5-portfolio-aggregation }

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

## 📐 6. Modèle de Cash à Trois Pools — Par Courtier $(K_b, R_b, W)$ {: #6-three-pool-cash-model-per-broker-k_b-r_b-w }

Trois pools accumulateurs suivent la provenance du cash. $K$ et $R$ sont maintenus **par courtier** $b$ ; $W$ est global (sort entièrement du système).

| Pool | Périmètre | Signification |
|------|-------|---------|
| $K_b$ | Par courtier | Capital externe toujours présent chez le courtier $b$ sous forme de cash |
| $R_b$ | Par courtier | Rendements générés toujours présents chez le courtier $b$ sous forme de cash |
| $W$ | Global | Rendements ayant quitté le système (cachés, restaurables lors d'un nouveau dépôt) |

!!! info "Propriété clé"

    Un BUY sur le courtier $b_1$ ne peut consommer que $R_{b_1}$, jamais $R_{b_2}$. Le cash ne se déplace pas par magie entre les courtiers — seuls les transferts explicites déplacent les soldes des pools.

### Règles de mise à jour (par transaction sur le courtier $b$, chronologique)

| Icône & Type | Formules de Mise à Jour | Logique & Description |
|:---:|---|---|
| ![](../../../static/icons/transactions/deposit.png){: width="24" }<br>**DÉPÔT**<br>$D > 0$ | $r = \min(D,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= D - r$ | Restaure d'abord les rendements précédemment retirés du tracker global $W$, puis ajoute le reste au capital $K_b$. |
| ![](../../../static/icons/transactions/withdrawal.png){: width="24" }<br>**RETRAIT**<br>$X > 0$ | $k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$ <br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Consomme d'abord le capital $K_b$, puis déplace les rendements restants $\rho$ vers le tracker global $W$. |
| ![](../../../static/icons/transactions/dividend.png){: width="24" } ![](../../../static/icons/transactions/interest.png){: width="24" }<br>**DIVIDENDE / INTÉRÊT**<br>$I > 0$ | $R_b \mathrel{+}= I$ | Les rendements augmentent directement le pool de rendements $R_b$. |
| ![](../../../static/icons/transactions/fee.png){: width="24" } ![](../../../static/icons/transactions/tax.png){: width="24" }<br>**FRAIS / TAXE**<br>$F > 0$ | $R_b \mathrel{-}= F$<br>$\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0$ | Consomme d'abord les rendements $R_b$ ; si $R_b$ devient négatif, il est prélevé sur le capital $K_b$. |
| ![](../../../static/icons/transactions/buy.png){: width="24" }<br>**ACHAT**<br>$B > 0$ | $\rho = \min(B,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$K_b \mathrel{-}= (B - \rho)$ | Consomme d'abord les rendements $R_b$, puis prélève le reste sur le capital $K_b$. |
| ![](../../../static/icons/transactions/sell.png){: width="24" }<br>**VENTE** | $G = P - C$<br>$K_b \mathrel{+}= C$<br>$R_b \mathrel{+}= G$<br>$\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b, \quad R_b = 0$ | La base de coût $C = |q_s| \cdot w_{\text{pre}}$ retourne au capital $K_b$ ; le gain $G$ va aux rendements $R_b$ (si $G < 0$, il se comporte comme des frais).<br><br>!!! warning "Ordre critique"<br><br>    $C$ doit être calculé **avant** que le pool PMP ne soit réduit (une vente totale donnerait sinon $C = 0$). |
| ![](../../../static/icons/transactions/cash-transfer.png){: width="24" }<br>**TRANSFERT DE LIQUIDITÉS**<br>(Interne, $s \to d$, $X > 0$) | **Flux de départ ($s$) :**<br>$\rho = \min(X,\, R_s)$<br>$R_s \mathrel{-}= \rho$<br>$\kappa = X - \rho$<br>$K_s \mathrel{-}= \kappa$<br><br>**Flux d'arrivée ($d$) :**<br>$K_d \mathrel{+}= \kappa$<br>$R_d \mathrel{+}= \rho$ | Les transferts de liquidités internes déplacent les allocations de pools ($R_s \to R_d$, $K_s \to K_d$) proportionnellement au solde de départ.<br>Le tracker global $W$ n'est **jamais** touché (le capital reste dans le système). |

Si les dates de départ et d'arrivée diffèrent, le transfert est "en transit" : soustrait de $s$ au jour du départ, ajouté à $d$ au jour de l'arrivée. Entre ces dates, $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$ du montant en transit — géré par une réconciliation proportionnelle.

### Agrégation pour la sortie

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t)
$$

$$
\mathrm{CashFromReturns}(t) = \sum_{b \in S} R_b(t)
$$

### Invariant de réconciliation

$$
\mathrm{Cash}_{\text{like}}(t) \approx \sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)
$$

Une mise à l'échelle proportionnelle par courtier est appliquée si la dérive est $> 0.01$ (due aux arrondis FX ou au timing du transit).

---

## 📐 7. Contribution de Période {: #7-period-contribution }

Pour la période $[t_0, t_1]$, par position $(a,b)$ :

$$
\Delta\mathrm{UGL}(a,b) = \mathrm{UGL}(a,b,t_1) - \mathrm{UGL}(a,b,t_0)
$$

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{Fees}(a,b)
$$

Ensemble des positions de contribution :

$$
\mathcal{P} = \mathcal{P}(t_0) \cup \mathcal{P}(t_1) \cup \mathrm{keys}(\text{Realized}) \cup \mathrm{keys}(\text{Income}) \cup \mathrm{keys}(\text{Fees})
$$

Les éléments non alloués (frais/revenus sans `asset_id`) sont groupés par courtier.

---

## 📐 8. Gain/Perte Réalisé

Lors d'une VENTE (SELL) de $|q_s|$ unités de la position $(a,b)$ :

$$
C = |q_s| \cdot w_{\text{pre}}(a,b) \cdot \mathrm{fx}(\mathrm{ccy}_w, C^*, t)
$$

$$
\mathrm{Realized} = P_{\text{sell}} - C
$$

Où $w_{\text{pre}}$ est le PMP **avant** la réduction du pool (même valeur utilisée par la règle VENTE des 3-pools ci-dessus).

---

## 📐 9. Architecture Pre-Frame / Frame

| Phase | Plage de dates | Calcule |
|-------|-----------|----------|
| Pre-frame | $[t_{\mathrm{first}},\ t_0)$ | Cash, qty, PMP, pools — pas d'évaluation de marché |
| Frame | $[t_0,\ t_1]$ | Quotidien complet : prix, FX, états des positions, états du portefeuille |

Les transactions Pre-frame mettent à jour les accumulateurs (grand livre de cash, pools PMP, pools K/R/W) sans utiliser de données de prix ou de FX. Cela permet une mise en cache efficace basée sur des plages de dates.

---

## 📐 10. Métriques de Performance (Couche 2)

Calculées **après** les états quotidiens, lors d'une passe séparée :

| Métrique | Formule | Référence |
|--------|---------|-----------|
| PnL Total | $\mathrm{NAV}(t) - \text{DepositedCapital}(t)$ | [Capital Déposé](deposited-capital.md) |
| PnL de Période | $\mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \text{ECF}_{[t_0,t_1]}$ | [P&L de Période](period-pnl.md) |
| TWRR | $\prod_i (1 + r_i) - 1$ (chaîne de sous-périodes) | [TWRR](twrr.md) |
| MWRR | XIRR résolvant $\sum \frac{CF_i}{(1+r)^{d_i/365}} = 0$ | [MWRR](mwrr.md) |
| ROI Simple | $(\mathrm{NAV} - \text{NetInvested}) / \text{NetInvested}$ | [ROI](roi.md) |
| Effet de Timing | $\text{MWRR}_{\text{cum}} - \text{TWRR}_{\text{cum}}$ | [Effet de Timing](timing-effect.md) |

---

## 🔗 Liens connexes

- 💼 [NAV](nav.md) — évaluation instantanée
- 📖 [Valeur Comptable](book-value.md) — agrégat de la base de coût
- 📊 [P&L de Période](period-pnl.md) — gain/perte sur fenêtre avec contribution
- 💸 [Capital Déposé](deposited-capital.md) — détails des 3-pools et exemples concrets
- 📈 [PMP](weighted-average-cost.md) — méthode de coût itérative
