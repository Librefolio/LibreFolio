# 💸 Capital Déposé, PnL Total et Pools de Cash

*[⬅️ Retour à l'aperçu des mesures de performance](index.md)*

## 💡 Aperçu du Concept

**Capital Déposé** = capital externe net cumulé apporté depuis le début :

$$
\mathrm{DepCap}(t) = \sum_{\tau \leq t} D(\tau) - \sum_{\tau \leq t} W(\tau)
$$

**PnL Total** = toute la valeur générée au-delà des contributions externes :

$$
\boxed{\mathrm{TotalPnL}(t) = \mathrm{NAV}(t) - \mathrm{DepCap}(t)}
$$

---

## 🎯 Ce qui est comptabilisé

| Transaction | Effet sur DepCap |
|------------|-----------------|
| DÉPÔT / RETRAIT (non lié) | ✅ Oui |
| TRANSFERT DE LIQUIDITÉS connecté-externe | ✅ Oui |
| TRANSFERT DE LIQUIDITÉS connecté-interne | ❌ Non |
| ACHAT, VENTE, DIVIDENDE, INTÉRÊT, FRAIS, TAXE | ❌ Non |

---

## 📊 Modèle de Cash à Trois Pools

Le graphique de croissance décompose le cash actuel en deux agrégats visibles plus un indicateur global caché :

$$
\mathrm{Cash}(t) \approx \sum_b K_b(t) + \sum_b R_b(t)
$$

| Pool | Portée | Signification |
|------|-------|---------|
| $K_b$ | Par courtier | Capital externe toujours chez le courtier $b$ |
| $R_b$ | Par courtier | Rendements générés toujours chez le courtier $b$ |
| $W$ | Global | Rendements ayant quitté le système (restaurables lors d'un nouveau dépôt) |

!!! info "Propriétés clés"

    - $\mathrm{DepCap}$ = somme historique de tous les flux. $\sum K_b$ = quelle part du cash actuel est du capital externe. Ils divergent après un ACHAT/VENTE.
    - Un ACHAT sur le courtier $b_1$ ne consomme que $R_{b_1}$, jamais $R_{b_2}$.
    - Les transferts de cash entre courtiers déplacent $R$ et $K$ de la source vers la destination sans toucher à $W$.

🔗 Règles complètes de mise à jour par courtier : **[Portfolio Engine — §6 Modèle de Cash à Trois Pools](portfolio-engine.md#6-modele-de-cash-a-trois-pools-par-courtier-k_b-r_b-w)**

---

## 📝 Exemples Pratiques

### A — Dépôt → Achat → Vente avec Gain

| Étape | Tx | $K$ | $R$ | Cash |
|------|----|-----|-----|------|
| 1 | DÉPÔT 1 000 € | 1 000 | 0 | 1 000 |
| 2 | ACHAT 1 000 € | 0 | 0 | 0 |
| 3 | VENTE P=1 200 €, C=1 000 € | 1 000 | 200 | 1 200 |

TotalPnL = 1 200 − 1 000 = **+200 €** ✓

### B — Dividende puis Retrait

| Étape | Tx | $K$ | $R$ | $W$ | Cash |
|------|----|-----|-----|-----|------|
| 1 | DÉPÔT 1 000 € | 1 000 | 0 | 0 | 1 000 |
| 2 | DIVIDENDE 50 € | 1 000 | 50 | 0 | 1 050 |
| 3 | RETRAIT 100 € (K d'abord) | 900 | 50 | 0 | 950 |
| 4 | RETRAIT 950 € (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | RE-DÉPÔT 30 € (restauration min(30,W=50)=30) | 0 | 30 | 20 | 30 |

Après l'étape 5 : Cash=30, K=0, R=30 ✓ (rendements restaurés depuis W)

### C — Régression après vente totale

| Étape | Tx | $K$ | $R$ | Cash |
|------|----|-----|-----|------|
| 1 | DÉPÔT 1 000 €, ACHAT 1@1 000 € | 0 | 0 | 0 |
| 2 | VENTE 1 à 1 005 € (C=1 000, G=5) | 1 000 | 5 | 1 005 |

Le capital retourne correctement vers $K$ ; seul le gain de 5 € va vers $R$. **Pas** la totalité des 1 005 € vers $R$.

---

## ⚙️ Implémentation

Le modèle à 3 pools s'exécute dans une **boucle unique par transaction** (basé sur les événements, et non par delta quotidien) :

1. Lecture du PMP avant la mutation du pool
2. Mise à jour de K/R/W selon les règles par type de transaction
3. Décrémentation ensuite du pool PMP (pour les VENTES)

🔗 Voir **[Portfolio Engine — §6](portfolio-engine.md#6-modele-de-cash-a-trois-pools-par-courtier-k_b-r_b-w)** pour toutes les règles formelles.

---

## 🔗 Liens Connexes

- 💼 [NAV](nav.md) — l'autre terme du PnL Total
- 📊 [Period PnL](period-pnl.md) — version par fenêtre
- ⚙️ [Portfolio Engine](portfolio-engine.md) — modèle mathématique complet
