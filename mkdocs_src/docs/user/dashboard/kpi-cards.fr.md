# 💰 Cartes KPI

*[⬅️ Retour à l'aperçu du tableau de bord](index.md)*

Les trois cartes KPI en haut du tableau de bord offrent un diagnostic rapide de votre portefeuille. Toutes les valeurs respectent la **période et la sélection de courtier** choisies en haut de la page.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Aperçu des cartes KPI">
</div>

---

## 📉 Carte 1 — P&L de la période {: #card-1-period-pl }

<div class="kpi-card-crop-container card-period-pnl">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte P&L de la période">
</div>

La carte **P&L de la période** indique combien d'argent votre portefeuille a *gagné* dans la fenêtre sélectionnée — après avoir retiré l'effet de vos propres dépôts et retraits.

Le nombre principal est calculé à l'aide de la formule suivante :

\[\text{P&L de la période} = \text{VNI}_{\text{fin}} - \text{VNI}_{\text{début}} - \text{Flux nets}_{\text{période}}\]

Un nombre positif signifie que vous avez gagné de l'argent grâce à l'activité d'investissement. Un nombre négatif signifie que vous avez perdu de l'argent net des mouvements de capitaux.

### Les lignes de détail

| Ligne | Ce qu'elle mesure |
|-------|-------------------|
| **Variation non réalisée** | Variation des [gains/pertes non réalisés](../../financial-theory/technical-analysis/performance-metrics/book-value.md) de vos positions ouvertes pendant la période |
| **Ventes** | Gain ou perte réalisé(e) sur les positions clôturées pendant la période (prix de vente − coût moyen) |
| **Dividendes & intérêts** | Revenus en espèces provenant des dividendes, coupons obligataires et intérêts P2P |
| **Frais & taxes** | Commissions et taxes enregistrées comme transactions |

!!! tip "Vérification d'identité"

    Les quatre lignes additionnées donnent le nombre principal P&L de la période (± faibles écarts dus à l'arrondi des devises).

🔗 **Théorie** : [P&L de la période](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md) · [Valeur comptable / PMP](../../financial-theory/technical-analysis/performance-metrics/book-value.md)

---

## 📈 Carte 2 — Rendements {: #card-2-returns }

<div class="kpi-card-crop-container card-returns">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte Rendements">
</div>

La carte **Rendements** présente des indicateurs de *taux de rendement* — des pourcentages qui permettent de comparer la performance indépendamment de la taille du portefeuille.

### Effet de date

L'**Effet de date** en haut de la carte mesure si vos décisions de dépôt/retrait ont *ajouté* ou *soustrait* de la valeur par rapport à une stratégie passive d'achat et de conservation :

\[\text{Effet de date} = \text{MWRR}_{\text{cumulé}} - \text{TWRR}_{\text{cumulé}}\]

- **Favorable (positif)** ✅ : vous avez eu tendance à déposer quand les prix étaient bas, augmentant votre rendement personnel au-dessus de ce que les actifs seuls ont rapporté.
- **Défavorable (négatif)** ❌ : vous avez eu tendance à déposer aux sommets ou avez manqué les creux, réduisant votre rendement en dessous de la performance pure des actifs.

### Les quatre indicateurs de rendement

| Indicateur | Question à laquelle il répond |
|------------|-------------------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/roi.md)** | Combien ai-je gagné par rapport à mon capital net investi ? |
| **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** | Comment mes choix d'actifs ont-ils performé, indépendamment du moment de mes dépôts ? |
| **[MWRR cumulé](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | Quel est le rendement pondéré par l'argent cumulé pour mes flux de trésorerie réels ? |
| **[MWRR annualisé](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** | À quel taux composé annuel mon capital a-t-il réellement augmenté ? |

!!! note "TWRR vs. MWRR"

    - Le **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)** mesure la **stratégie d'actifs** — de la même manière qu'un gestionnaire de fonds est évalué.
    - Le **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)** mesure **votre résultat personnel** — y compris le moment de vos dépôts.
    - L'écart entre eux est l'[Effet de date](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md).

---

## 💰 Carte 3 — Valeur nette {: #card-3-net-worth }

<div class="kpi-card-crop-container card-net-worth">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte Valeur nette">
</div>

La carte **Valeur nette** affiche la valeur absolue de votre portefeuille à la fin de la période sélectionnée.

### Ce que signifient les lignes

| Ligne | Définition |
|-------|------------|
| **[Valeur de marché](../../financial-theory/technical-analysis/performance-metrics/nav.md)** | Prix de marché actuel × quantité pour tous les actifs détenus |
| **[Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/book-value.md)** | Ce que vous avez payé pour vos positions ouvertes (coût moyen × qty) |
| **Trésorerie** | Solde liquide détenu sur les comptes courtier |
| **[Capital déposé](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)** | Capital externe net contribué à ce périmètre |

### La barre de capital déposé

La barre horizontale sous les lignes visualise :

- 🟢 **Total déposé** — tous les dépôts de la période
- 🔴 **Total retiré** — tous les retraits de la période

Le nombre principal montre le solde net (déposé − retiré).

!!! info "Instantané vs. période"

    La Valeur de marché, la Valeur comptable et la Trésorerie sont des **instantanés** à la date de fin — ils sont indépendants de la date de début.
    Le Capital déposé est **limité à la période** — il compte les dépôts et retraits entre le début et la fin de la plage sélectionnée.

---

## 🔗 Liens connexes

- 💼 **[VNI / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/nav.md)**
- 📚 **[Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/book-value.md)**
- 📊 **[P&L de la période](../../financial-theory/technical-analysis/performance-metrics/period-pnl.md)**
- 💸 **[Capital déposé et P&L total](../../financial-theory/technical-analysis/performance-metrics/deposited-capital.md)**
- 📈 **[TWRR](../../financial-theory/technical-analysis/performance-metrics/twrr.md)**
- 📈 **[MWRR](../../financial-theory/technical-analysis/performance-metrics/mwrr.md)**
- ⏱️ **[Effet de date](../../financial-theory/technical-analysis/performance-metrics/timing-effect.md)**
