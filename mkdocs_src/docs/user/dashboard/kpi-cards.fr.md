# 💰 Cartes KPI

*[⬅️ Retour à l'aperçu du tableau de bord](index.md)*

Les trois cartes KPI en haut du tableau de bord vous offrent un diagnostic rapide de votre portefeuille. Toutes les valeurs respectent la **plage temporelle et le périmètre du courtier** sélectionnés en haut de la page.

---

## 💰 Carte 1 — Valeur Nette {: #card-1-net-worth }

La carte **Valeur Nette** affiche la valeur absolue de votre portefeuille à la fin de la période sélectionnée.

### Signification des lignes

| Ligne | Définition |
|-----|-----------|
| **[Market Value](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Prix du marché actuel × quantité pour tous les actifs détenus |
| **[Book Value](../../financial-theory/technical-analysis/performance-metrics/book-value.md)** | Ce que vous avez payé pour vos positions ouvertes (coût moyen × qté) |
| **Cash** | Solde liquide détenu sur les comptes de courtage |
| **[Deposited Capital](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Capital externe net injecté dans ce périmètre |

### La barre du Capital Déposé

La barre horizontale sous les lignes visualise :

- 🟢 **Total déposé** — tous les dépôts sur la période
- 🔴 **Total retiré** — tous les retraits sur la période

Le chiffre principal affiche le solde net (déposé − retiré).

!!! info "Instantané vs période"

    La Market Value, la Book Value et le Cash sont des **instantanés** à la date de fin — ils sont indépendants de la date de début.
    Le Deposited Capital **est calculé sur la période** — il comptabilise les dépôts et les retraits entre le début et la fin de la plage sélectionnée.

---

## 📉 Carte 2 — P&L de la Période {: #card-2-period-pl }

La carte **Period P&L** montre combien d'argent votre portefeuille a réellement *gagné* dans la fenêtre sélectionnée — après avoir supprimé l'effet de vos propres dépôts et retraits.

Le chiffre principal utilise la formule suivante :

> **NAV fin** − **NAV début** − **Flux externes nets sur la période**

Un nombre positif signifie que vous avez gagné de l'argent grâce à l'activité d'investissement. Un nombre négatif signifie que vous avez perdu de l'argent, net des mouvements de capitaux.

### Le détail des lignes

| Ligne | Ce qu'elle mesure |
|-----|-----------------|
| **Unrealized change** | L'évolution du [gain/perte non réalisé](../../financial-theory/technical-analysis/performance-metrics/book-value.md) de vos positions ouvertes durant la période |
| **Ventes** | Gain ou perte réalisé sur les positions clôturées durant la période (prix de vente − coût moyen) |
| **Dividends & interest** | Revenus en espèces provenant des dividendes, des coupons d'obligations et des intérêts P2P |
| **Fees & taxes** | Commissions et taxes enregistrées comme transactions |

!!! tip "Vérification de cohérence"

    La somme des quatre lignes correspond au chiffre principal du Period P&L (± de faibles résidus dus aux arrondis FX).

🔗 **Théorie** : [Period P&L](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md) · [Valeur Comptable / PMP](../../financial-theory/technical-analysis/performance-metrics/book-value.md)

---

## 📈 Carte 3 — Rendements {: #card-3-returns }

La carte **Returns** affiche des indicateurs de *taux de rendement* — des pourcentages qui vous permettent de comparer la performance indépendamment de la taille du portefeuille.

### Effet de Timing (Timing Effect)

Le **Timing Effect** en haut de la carte mesure si vos décisions de dépôt/retrait ont *ajouté* ou *soustrait* de la valeur par rapport à une stratégie passive d'achat et de conservation (buy-and-hold).

> **Timing Effect** = MWRR cumulé − TWRR cumulé

- **Favorable (positif)** ✅ : vous avez eu tendance à déposer quand les prix étaient bas, propulsant votre rendement personnel au-dessus de la performance intrinsèque des actifs.
- **Défavorable (négatif)** ❌ : vous avez eu tendance à déposer lors des sommets ou avez manqué des creux, entraînant votre rendement en dessous de la performance pure des actifs.

### Les quatre indicateurs de rendement

| Indicateur | Question à laquelle il répond |
|--------|---------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | Combien ai-je gagné par rapport à mon capital net investi ? |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | Comment mes choix d'actifs ont-ils performé, indépendamment du moment de mes dépôts ? |
| **[MWRR cumulé](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | Quel est le rendement cumulé pondéré par les flux monétaires pour mes flux de trésorerie réels ? |
| **[MWRR annualisé](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | À quel taux composé annuel mon capital a-t-il réellement crû ? |

!!! note "TWRR vs. MWRR"

    - Le **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** mesure la **stratégie d'actifs** — c'est la même méthode utilisée pour évaluer un gestionnaire de fonds.
    - Le **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** mesure **votre résultat personnel** — incluant le timing de vos dépôts.
    - L'écart entre les deux est le [Timing Effect](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

---

## 🔗 Liens connexes

- 💼 **[NAV / Valeur Nette](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 📚 **[Book Value](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- 📊 **[Period P&L](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- 💸 **[Deposited Capital & Total P&L](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)**
- 📈 **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)**
- ⏱️ **[Timing Effect](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
