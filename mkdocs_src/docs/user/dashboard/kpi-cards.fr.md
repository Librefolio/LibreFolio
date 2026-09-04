# 💰 Cartes KPI

Les trois cartes KPI en haut du tableau de bord vous offrent un diagnostic rapide de votre portefeuille. Toutes les valeurs respectent la **période et le périmètre de courtier** sélectionnés en haut de la page.

!!! note "Le partage affecte ces chiffres"

    Tous les montants sont agrégés sur les courtiers auxquels vous avez accès, et chaque courtier en copropriété contribue proportionnellement à votre **part de propriété** (ex. un Owner à 50 % voit la moitié de la valeur et du P&L de ce courtier). Les Editors et Viewers, dont la part est toujours de 0 % par règle, voient les montants complets du courtier. Voir [Partage de courtier](../brokers/sharing.md).

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Aperçu des cartes KPI">
</div>

---

## 📉 Carte 1 — P&L de la période {: #card-1-period-pl }

<div class="kpi-card-crop-container card-period-pnl">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte P&L de la période">
</div>

La carte **P&L de la période** indique combien d'argent votre portefeuille a réellement *gagné* dans la fenêtre sélectionnée — après avoir neutralisé l'effet de vos propres dépôts et retraits.

Le chiffre principal est calculé à l'aide de la formule suivante :

\[\text{P&L de la période} = \text{VNI}_{\text{fin}} - \text{VNI}_{\text{début}} - \text{Flux nets}_{\text{période}}\]

Un nombre positif signifie que vous avez gagné de l'argent grâce à l'activité d'investissement. Un nombre négatif signifie que vous avez perdu de l'argent, net des mouvements de capitaux.

### Le nombre sous le chiffre principal

Juste en dessous de la valeur du P&L de la période, une ligne plus petite affiche quelque chose comme `+45,20 (+3,10%)`.

- Le montant est la variation **jour après jour** (aujourd'hui vs. hier) de votre **P&L total** — votre gain/perte cumulé de tous les temps, pas seulement pour la période sélectionnée.
- Le pourcentage l'exprime en part du **P&L total d'hier** — il vous indique combien le mouvement d'aujourd'hui a « pesé » par rapport à votre résultat cumulé de tous les temps.

\[\text{Variation quotidienne} = \text{P&L total}_{\text{aujourd'hui}} - \text{P&L total}_{\text{hier}}\]

Cette ligne n'apparaît que lorsque l'historique comporte au moins deux points quotidiens.

### Les lignes de détail

| Ligne | Ce qu'elle mesure |
|-----|-----------------|
| **Variation latente** | De combien le [gain/perte latent](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md) de vos positions ouvertes a changé pendant la période |
| **Ventes** | Gain ou perte réalisé(e) sur les positions closes pendant la période (prix de vente − coût moyen) |
| **Dividendes & intérêts** | Revenus en espèces provenant des dividendes, des coupons d'obligations et des intérêts de P2P |
| **Frais & taxes** | Commissions et taxes enregistrées comme transactions |

!!! tip "Vérification d'identité"

    Les quatre lignes additionnées donnent le chiffre principal du P&L de la période (± légers écarts dus à l'arrondi des devises).

🔗 **Théorie** : [P&L de la période](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md) · [Valeur comptable / PMP](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)

---

## 📈 Carte 2 — Rendements {: #card-2-returns }

<div class="kpi-card-crop-container card-returns">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte Rendements">
</div>

La carte **Rendements** présente des mesures de *taux de rendement* — des pourcentages qui vous permettent de comparer la performance indépendamment de la taille du portefeuille.

### Effet de cadencement

L'**Effet de cadencement** en haut de la carte mesure si vos décisions de dépôt/retrait ont *ajouté* ou *retiré* de la valeur par rapport à une stratégie passive d'achat-conservation :

\[\text{Effet de cadencement} = \text{MRP}_{\text{cumulé}} - \text{TRP}_{\text{cumulé}}\]

- **Favorable (positif)** ✅ : vous avez eu tendance à déposer quand les prix étaient bas, augmentant ainsi votre rendement personnel au-dessus de ce que les actifs seuls ont gagné.
- **Défavorable (négatif)** ❌ : vous avez eu tendance à déposer aux sommets ou à manquer les creux, tirant votre rendement en dessous de la performance pure des actifs.

### Le nombre sous l'Effet de cadencement

En dessous de l'Effet de cadencement, vous verrez un petit pourcentage (par ex. `+0,35%`) — c'est la variation de votre **P&L total** d'**hier à aujourd'hui**, exprimée en part de la valeur nette d'hier :

\[\text{%Variation quotidienne} = \frac{\text{P&L total}_{\text{aujourd'hui}} - \text{P&L total}_{\text{hier}}}{\text{Valeur nette}_{\text{hier}}} \times 100\]

C'est une estimation approximative du rendement **d'aujourd'hui** — une vérification rapide du pouls. Ce n'est ni le ROI, ni le TRP, ni le MRP affichés dans les lignes ci-dessous, qui restent ancrés à la période sélectionnée complète.

### Les quatre mesures de rendement

| Mesure | Question à laquelle elle répond |
|--------|---------------------|
| **[ROI](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)** | Combien ai-je gagné par rapport à mon capital net investi ? |
| **[TRP](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** | Comment mes choix d'actifs ont-ils performé, indépendamment du moment de mes dépôts ? |
| **[MRP cumulé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | Quel est le rendement pondéré en fonction des capitaux cumulé pour mes flux de trésorerie réels ? |
| **[MRP annualisé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** | À quel taux de composition annuel mon capital a-t-il réellement augmenté ? |

!!! note "TRP vs. MRP"

    - Le **[TRP](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)** mesure la **stratégie d'actifs** — de la même manière qu'un gestionnaire de fonds est évalué.
    - Le **[MRP](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)** mesure **votre résultat personnel** — y compris le moment de vos dépôts.
    - L'écart entre eux est l'[Effet de cadencement](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md).

---

## 💰 Carte 3 — Valeur nette {: #card-3-net-worth }

<div class="kpi-card-crop-container card-net-worth">
 <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte Valeur nette">
</div>

La carte **Valeur nette** affiche la valeur absolue de votre portefeuille à la fin de la période sélectionnée.

!!! note "La Valeur nette inclut les liquidités"

    Le montant est **titres à valeur de marché + solde liquide** (+ toute valeur en transit entre brokers). Comme il inclut les liquidités, il **n'est pas comparable** à la « contre-valeur titres » d'un relevé bancaire, qui exclut les liquidités — celles-ci y sont reportées séparément.

### Le nombre sous la Valeur nette

En dessous de la valeur de la Valeur nette, vous trouverez votre **P&L total**, avec votre rendement absolu entre parenthèses — par ex. `+12 450,30 (+24,85 %)`.

- Le montant est votre **P&L total** — le gain ou la perte cumulé(e) depuis le début, sur l'ensemble de l'historique de ce périmètre (pas seulement la période actuelle).
- Le pourcentage entre parenthèses est le **ROI absolu (depuis l'origine)** : P&L total ÷ capital net investi depuis l'origine. Ce n'est *pas* une variation jour après jour — pour ce contrôle quotidien, voyez les petites lignes des [Carte 1](#card-1-period-pl) et [Carte 2](#card-2-returns).

\[\text{P&L total} = \text{Valeur nette} - \text{Capital net investi depuis l'origine}\]

Remarque : « Capital net investi depuis l'origine » est ici la somme de **tous** les dépôts moins **tous** les retraits depuis que vous avez commencé à utiliser ce périmètre — un chiffre différent et plus grand que la ligne « Capital déposé » ci-dessous, qui ne compte que les mouvements au sein de la période sélectionnée.

🔗 **Théorie** : [Capital déposé, P&L total et Pools de trésorerie](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

### Ce que signifient les lignes

| Ligne | Définition |
|-----|-----------|
| **[Valeur de marché](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)** | Prix actuel du marché × quantité pour tous les actifs détenus |
| **[Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)** | Ce que vous avez payé pour vos positions ouvertes (coût moyen × qté) |
| **Trésorerie** | Solde liquide détenu sur les comptes de courtage |
| **[Capital déposé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)** | Capital externe net contribué à ce périmètre |

### La barre de Capital déposé

La barre horizontale en dessous des lignes visualise :

- 🟢 **Total déposé** — tous les dépôts de la période
- 🔴 **Total retiré** — tous les retraits de la période

Le chiffre principal indique le solde net (déposé − retiré).

!!! info "Instant précis vs. période"

    La Valeur de marché, la Valeur comptable et la Trésorerie sont des **instantanés** à la date de fin — ils sont indépendants de la date de début.
    Le Capital déposé est **périodique** — il compte les dépôts et les retraits entre le début et la fin de la plage sélectionnée.

---

## 🔗 Liens connexes

- 💼 **[VNI / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- 📚 **[Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- 📊 **[P&L de la période](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- 💸 **[Capital déposé & P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- 📈 **[TRP](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)**
- 📈 **[MRP](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)**
- ⏱️ **[Effet de cadencement](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)**

---

*[⬅️ Retour à l'aperçu du tableau de bord](index.md)*
