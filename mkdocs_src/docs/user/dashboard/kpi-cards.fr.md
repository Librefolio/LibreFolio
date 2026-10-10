# 💰 Cartes KPI

Les trois cartes en haut du Tableau de bord répondent en un coup d'œil à trois questions : **combien ai-je gagné sur cette période**, **à quel point mon argent a-t-il travaillé**, et **combien vaut mon portefeuille**. Elles suivent la plage temporelle et le filtre de courtier en haut de la page, et la page d'un courtier affiche les mêmes cartes pour ce courtier uniquement. L'icône **?** dans le coin d'une carte ouvre sa section ci-dessous.

- 📉 **[Carte 1 — P&L période](#card-1-period-pl)** — l'argent que vos investissements ont généré sur la période
- 📈 **[Carte 2 — Rendements](#card-2-returns)** — vos rendements en pourcentage, et ce que votre timing leur a fait
- 💰 **[Carte 3 — Valeur nette](#card-3-net-worth)** — ce que vous possédez, et votre gain depuis le début

!!! note "Les courtiers partagés comptent pour votre part"

    Le Tableau de bord additionne les courtiers que vous **possédez** avec une part supérieure à 0 %, chacun au prorata de cette part : un propriétaire à 50 % voit la moitié de la valeur et du P&L du courtier. Les courtiers où vous êtes éditeur ou lecteur ne sont pas comptés ici ; leur propre page les affiche, avec leurs montants complets. Voir [Partage de courtier](../brokers/sharing.md).

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Vue d'ensemble des cartes KPI">
</div>

---

## 📉 Carte 1 — P&L période {: #card-1-period-pl }

Combien d'argent vos investissements ont-ils généré sur la période sélectionnée ? La carte **P&L période** répond, en excluant l'argent que vous avez déplacé vers l'intérieur ou vers l'extérieur vous-même.

<div class="kpi-card-crop-container card-period-pnl">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte P&L période">
</div>

**Indicateurs affichés**

- **P&L période** — le grand nombre : $\text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \text{Net flows}$, les flux nets étant le capital que vous avez déplacé vers l'intérieur ou vers l'extérieur → [P&L période](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **La ligne en dessous** — par exemple `+91.31 € (+16.36%)` : de combien votre P&L total a évolué depuis hier (panneau ci-dessous)
- **Variation non réalisée** — comment la plus-value ou moins-value latente de vos positions a évolué sur la période, effet de change inclus → [Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Ventes** — la plus-value ou moins-value réalisée des ventes de la période, par rapport au prix de revient unitaire des unités vendues → [Prix de revient unitaire (PRU)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Dividendes et intérêts** — dividendes, coupons et intérêts P2P reçus → [Dividendes et intérêts](../../financial-theory/instruments/transaction-types/dividend-interest.md)
- **Frais et impôts** — commissions et impôts enregistrés comme transactions ; survolez la ligne pour voir la répartition → [Frais et impôts](../../financial-theory/instruments/transaction-types/fee.md)

**Comment la lire**

- **Le vert est un gain, le rouge une perte** — et un dépôt ou un retrait n'est ni l'un ni l'autre.
- **Les quatre lignes expliquent le grand nombre.** Ce qu'elles ne peuvent pas voir, comme des actifs passant d'un de vos courtiers à un autre le premier ou le dernier jour, va dans le **Autre / résidu de réconciliation** de la [vue Performance](positions.md#performance).
- **La barre la plus longue** est la ligne qui a le plus fait bouger votre résultat.

??? info "📏 La ligne sous le grand nombre — comment elle est calculée"

    C'est la variation de votre P&L total — votre gain ou votre perte depuis le début — d'hier à aujourd'hui, *aujourd'hui* étant la date de fin de la période. Le pourcentage le compare au P&L total d'hier, pris sans son signe :

    $$
    \Delta = \text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}} \qquad \text{percentage} = \frac{\Delta}{\left|\text{Total P}\&\text{L}_{\text{yesterday}}\right|} \times 100
    $$

    - **Le signe et la couleur suivent la variation**, même lorsque le P&L total est une perte : de `-558.10 €` à `-466.79 €`, la ligne affiche `+91.31 € (+16.36%)` — votre perte a diminué de 16.36 %.
    - **Il faut deux jours d'historique** ; le pourcentage est omis lorsque le P&L total d'hier est exactement nul, et un jour sans variation affiche `0.00%`.

### 💱 Variation non réalisée par devise {: #unrealized-change-by-currency }

Survolez **Variation non réalisée** pour la ventiler par la devise dans laquelle vos actifs sont valorisés — ici avec l'euro comme devise d'affichage :

| Ligne | Ce qu'elle montre |
|-----|---------------|
| 📈 **Actifs en USD** | Ce que vos actifs en dollars ont fait *en dollars* — leur propre variation de prix — comptés au taux de change du jour |
| 💱 **Taux USD → EUR** | Ce que le taux de change a fait à ce que vous avez payé pour eux |
| ❔ **USD, non ventilé** | Uniquement lorsque, le premier ou le dernier jour, certains de ces actifs n'avaient pas de prix, pas de taux ou un coût d'achat incomplet : leur variation, en un seul bloc |

Il y a une ligne 📈 pour chaque devise, euro inclus, et une ligne 💱 pour chaque devise autre que votre devise d'affichage ; ensemble, les lignes totalisent **exactement** la Variation non réalisée.

??? example "Un ETF américain sur un tableau de bord en euros"

    Pendant la période, vous avez acheté 10 unités pour 400 €, alors qu'elles valaient 500 USD. À la fin de la période, elles valent 550 USD, et 1 USD = 0,75 €. L'infobulle affiche :

    - 📈 **Actifs en USD** : (550 − 500) × 0,75 = **+37,50 €** — votre ETF a gagné 10 % en dollars ;
    - 💱 **Taux USD → EUR** : 500 × 0,75 − 400 = **−25,00 €** — le dollar a perdu de la valeur face à l'euro ;
    - ensemble, la **Variation non réalisée** : 550 × 0,75 − 400 = **+12,50 €**.

🔗 **Théorie** : [Variation non réalisée par devise](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#unrealized-change-by-currency) — les formules derrière chaque ligne

---

## 📈 Carte 2 — Rendements {: #card-2-returns }

À quel point votre argent a-t-il travaillé, quelle que soit la taille de votre portefeuille ? La carte **Rendements** répond en pourcentages, et son grand nombre vous dit si votre timing a aidé.

<div class="kpi-card-crop-container card-returns">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte Rendements">
</div>

**Indicateurs affichés**

- **Effet timing** — le grand nombre, en points de pourcentage (pp) : $\text{MWRR}_{\text{cumulative}} - \text{TWRR}$ → [Effet timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)
- **Le pourcentage en dessous** — par exemple `+0.35%` : la variation d'aujourd'hui de votre P&L total, rapportée à la valeur nette d'hier (panneau ci-dessous)
- **ROI** — le gain de la période rapporté au capital investi → [ROI simple](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md)
- **TWRR** — la performance de vos choix d'actifs, quel que soit le timing de vos dépôts → [TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)
- **MWRR cumulé** et **MWRR annualisé** — votre rendement personnel, timing des dépôts inclus, sur la période et en taux annuel → [MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)

**Comment la lire**

- **Timing favorable** (vert) : vous aviez tendance à déposer avant que les prix montent. **Timing défavorable** (rouge) : vous aviez tendance à déposer au sommet. Proche de zéro, il indique **Timing neutre**, et plus la couleur est forte, plus l'effet est important.
- **Le TWRR juge la stratégie, le MWRR votre résultat personnel** — comme pour un gestionnaire de fonds et un investisseur.
- **Les quatre lignes couvrent toute la période** ; le petit pourcentage ne couvre qu'aujourd'hui.
- **`—` signifie aucune valeur** : un rendement que LibreFolio ne peut pas calculer pour la période affiche `—` au lieu d'un nombre. L'effet timing nécessite à la fois le TWRR et le MWRR : quand l'un manque, il affiche un `—` gris, sans libellé de timing.

??? info "📏 Le pourcentage sous l'effet timing — comment il est calculé"

    La même variation de votre P&L total que sur la [Carte 1](#card-1-period-pl), divisée par la valeur nette d'hier prise sans son signe :

    $$
    \text{percentage} = \frac{\text{Total P}\&\text{L}_{\text{today}} - \text{Total P}\&\text{L}_{\text{yesterday}}}{\left|\text{Net Worth}_{\text{yesterday}}\right|} \times 100
    $$

    Son signe et sa couleur suivent la variation, comme sur la Carte 1. Il nécessite deux jours d'historique et est masqué lorsque la valeur nette d'hier était exactement nulle.

---

## 💰 Carte 3 — Valeur nette {: #card-3-net-worth }

Que vaut votre portefeuille à la fin de la période, et qu'a-t-il gagné depuis que vous avez commencé ? La carte **Valeur nette** répond, liquidités incluses.

<div class="kpi-card-crop-container card-net-worth">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte Valeur nette">
</div>

**Indicateurs affichés**

- **Valeur nette** — le grand nombre : les titres à leur valeur de marché, plus les liquidités, plus tout ce qui est en transit entre vos courtiers → [NAV / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **La ligne en dessous** — par exemple `+12,450.30 (+24.85%)` : votre **P&L total** depuis le début et, entre parenthèses, votre **ROI depuis le début** → [Capital versé et P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)
- **Valeur de marché** — ce que valent les actifs que vous détenez aux prix du marché → [NAV / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **Coût d'achat** — ce que vous ont coûté les positions que vous détenez encore, chaque achat au taux de change de sa propre date → [Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Liquidités** — les liquidités chez vos courtiers ; survolez-les pour séparer le capital que vous avez déposé des rendements que vous avez générés → [Poches de liquidités](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)
- **Capital versé (période)** — les dépôts moins les retraits sur la période, vert à droite et rouge à gauche ; survolez-le pour les totaux → [Capital versé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

$$
\text{Total P}\&\text{L} = \text{Net Worth} - \text{Capital put in since the start}
$$

Ce capital correspond à chaque dépôt moins chaque retrait, plus le coût d'achat des titres que vous avez apportés sans liquidités, comme une position d'ouverture ; le ROI entre parenthèses divise le P&L total par celui-ci.

**Comment la lire**

- **Date de fin ou période ?** Le grand nombre et les trois premières lignes sont des valeurs à la date de fin ; le Capital versé (période) ne compte que les mouvements entre le début et la fin.
- **Le petit caret** sur une barre marque sa valeur au début de la période (survolez-le) ; la Valeur de marché devient rouge lorsqu'elle termine en dessous.
- **La Valeur nette inclut les liquidités**, contrairement à la « valeur des titres » d'un relevé bancaire.
- **Le P&L total n'est pas une variation quotidienne** : pour le pouls du jour, voir les petites lignes sur la Carte 1 et la Carte 2.

---

## 🔗 Voir aussi

- 🔍 **[Positions et analyse](positions.md)** — les mêmes résultats, position par position
- 📊 **[Graphiques](charts.md)** — la vue **P&L** du graphique de croissance suit votre P&L total dans le temps
- 📐 **[Vue d'ensemble des métriques de performance](../../financial-theory/technical-analysis/performance-metrics/index.md)** — chaque indicateur de ces cartes, avec sa formule
- 🛠️ **[Détails techniques](../../developer/frontend/pages/index.md#dashboard)** — pour les développeurs : d'où viennent les chiffres des cartes

---

*[⬅️ Retour à la vue d'ensemble du Tableau de bord](index.md)*
