# 💰 Cartes KPI

Les trois cartes en haut du Tableau de bord répondent d’un coup d’œil à trois questions : **combien ai-je gagné sur cette période**, **à quel point mon argent a travaillé** et **combien vaut mon portefeuille**. Elles suivent la plage temporelle et le filtre de courtier en haut de la page, et la page d’un courtier affiche les mêmes cartes pour ce courtier uniquement. L’icône **?** dans le coin d’une carte ouvre sa section ci-dessous.

- 📉 **[Carte 1 — P&L période](#card-1-period-pl)** — l’argent que vos investissements ont rapporté sur la période
- 📈 **[Carte 2 — Rendements](#card-2-returns)** — vos rendements en pourcentage, et ce que votre timing y a changé
- 💰 **[Carte 3 — Valeur nette](#card-3-net-worth)** — ce que vous possédez, et votre gain depuis le début

!!! note "Les courtiers partagés comptent pour votre part"

    Le Tableau de bord additionne les courtiers que vous **possédez** avec une part supérieure à 0 %, chacun au prorata de cette part : un propriétaire à 50 % voit la moitié de la valeur et du P&L du courtier. Les courtiers où vous êtes éditeur ou lecteur ne sont pas comptés ici ; leur propre page les affiche, avec leurs montants complets. Voir [Partage de courtier](../brokers/sharing.md).

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Aperçu des cartes KPI">
</div>

---

## 📉 Carte 1 — P&L période {: #card-1-period-pl }

Combien d’argent vos investissements ont-ils rapporté sur la période sélectionnée ? La carte **P&L période** répond, en laissant de côté l’argent que vous avez fait entrer ou sortir vous-même.

<div class="kpi-card-crop-container card-period-pnl">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte P&L période">
</div>

**Indicateurs affichés**

- **P&L période** — le grand chiffre : $\text{NAV}_{\text{fin}} - \text{NAV}_{\text{début}} - \text{Flux nets}$, les flux nets étant le capital que vous avez fait entrer ou sortir → [P&L période](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **La ligne en dessous** — par exemple `-1 141 € (-1,95 %)` : de combien votre P&L total a évolué depuis hier, et cette variation en pourcentage par rapport à la valeur du portefeuille d’hier (panneau ci-dessous)
- **Variation non réalisée** — comment la plus ou moins-value latente de vos positions a évolué sur la période, effet des taux de change inclus → [P&L période](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)
- **Ventes** — la plus ou moins-value réalisée des ventes de la période, rapportée au prix de revient unitaire des unités vendues. Un ajustement qui retire des unités n’a pas de valeur : il compte ici comme une vente sans produit, une perte de ce que ces unités ont coûté (voir [Ajustements sortants](../../financial-theory/instruments/transaction-types/adjustment.md#outgoing-adjustments)) → [Prix de revient unitaire (PRU)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)
- **Dividendes et intérêts** — dividendes, coupons et intérêts P2P reçus → [Dividende et intérêt](../../financial-theory/instruments/transaction-types/dividend-interest.md)
- **Frais et impôts** — commissions et impôts enregistrés comme transactions ; survolez la ligne pour voir la répartition → [Frais et impôt](../../financial-theory/instruments/transaction-types/fee.md)

**Comment la lire**

- **Le vert est un gain, le rouge une perte** — et un dépôt ou un retrait n’est ni l’un ni l’autre.
- **Les quatre lignes expliquent le grand chiffre.** Ce qu’elles ne peuvent pas voir se retrouve dans la [vue Période](positions.md#performance) : l’effet des taux de change sur les liquidités que vous détenez dans une autre devise y apparaît sous la forme **Effet de change sur les liquidités**, avec une ligne pour chaque courtier dont les liquidités ont été affectées par les taux. Lorsque vous ne consultez qu’une partie de vos courtiers, les titres transférés vers ou depuis un courtier extérieur à votre sélection comptent à leur valeur de marché du jour : le gain qu’ils ont réalisé chez l’autre courtier apparaît en **Transferts à la valeur de marché**, avec une ligne pour chaque courtier concerné ([comment cela fonctionne](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#transfers-at-market-value)). Le reste — comme des actifs passant d’un de vos courtiers à un autre le premier ou le dernier jour — constitue le **Résidu autre / réconciliation**.
- **La barre la plus longue** correspond à la ligne qui a le plus influé sur votre résultat.

??? info "📏 La ligne sous le grand chiffre — comment elle est calculée"

    C’est la variation de votre P&L total — votre gain ou votre perte depuis le début — d’hier à aujourd’hui, *aujourd’hui* étant la date de fin de la période. Le pourcentage le compare à la valeur nette d’hier — la valeur du portefeuille entier —, prise sans son signe :

    $$
    \Delta = \text{P}\&\text{L total}_{\text{aujourd'hui}} - \text{P}\&\text{L total}_{\text{hier}} \qquad \text{pourcentage} = \frac{\Delta}{\left|\text{Valeur nette}_{\text{hier}}\right|} \times 100
    $$

    - **Le signe et la couleur suivent la variation**, même lorsque le P&L total est une perte : de `-558,10 €` à `-466,79 €` sur une valeur nette de 10 000 €, la ligne affiche `+91,31 € (+0,91 %)`. La base est le portefeuille, pas le P&L total : près de zéro, un P&L total transformerait la même variation en un pourcentage énorme qui ne dit rien.
    - **Elle est absente uniquement lorsque la période se termine le premier jour de votre portefeuille**, car il n’y a pas de jour précédent pour comparer ; le pourcentage est omis lorsque la valeur nette d’hier est exactement nulle, et une journée sans variation affiche `0,00 %`. Le lundi, la ligne couvre tout le week-end, car un jour sans marché conserve les cours du dernier jour de bourse.

### 💱 Variation non réalisée par devise {: #unrealized-change-by-currency }

Survolez **Variation non réalisée** pour la ventiler par devise de valorisation de vos actifs — ici avec l’euro comme devise d’affichage :

| Ligne | Ce qu’elle montre |
|-----|---------------|
| 📈 **Actifs en USD** | Ce qu’ont fait vos actifs en dollars *en dollars* — leur propre variation de prix — comptabilisé au taux de change du jour |
| 💱 **Taux USD → EUR** | Ce que le taux de change a fait à ce que vous avez payé pour eux |
| ❔ **USD, non ventilé** | Uniquement lorsque, le premier ou le dernier jour, certains de ces actifs n’avaient pas de taux ou avaient un coût d’achat incomplet : leur variation, en un seul bloc |

Il y a une ligne 📈 pour chaque devise, euro compris, et une ligne 💱 pour chaque devise autre que votre devise d’affichage ; ensemble, les lignes totalisent **exactement** la variation non réalisée. Un jour où un actif est valorisé à ce qu’il vous a coûté, faute de prix, il ne présente ni plus-value ni moins-value latente et n’ajoute rien à aucune ligne.

??? example "Un ETF américain sur un tableau de bord en euros"

    Pendant la période, vous avez acheté 10 unités pour 400 €, alors qu’elles valaient 500 USD. À la fin de la période, elles valent 550 USD, et 1 USD = 0,75 €. L’infobulle affiche :

    - 📈 **Actifs en USD** : (550 − 500) × 0,75 = **+37,50 €** — votre ETF a gagné 10 % en dollars ;
    - 💱 **Taux USD → EUR** : 500 × 0,75 − 400 = **−25,00 €** — le dollar a perdu de la valeur face à l’euro ;
    - ensemble, la **variation non réalisée** : 550 × 0,75 − 400 = **+12,50 €**.

🔗 **Théorie** : [Variation non réalisée par devise](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md#unrealized-change-by-currency) — les formules derrière chaque ligne

---

## 📈 Carte 2 — Rendements {: #card-2-returns }

À quel point votre argent a-t-il travaillé, quelle que soit la taille de votre portefeuille ? La carte **Rendements** répond en pourcentages, et son grand chiffre vous dit si votre timing vous a aidé.

<div class="kpi-card-crop-container card-returns">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte Rendements">
</div>

**Indicateurs affichés**

- **Effet timing** — le grand chiffre, en points de pourcentage (pp) : $\text{MWRR}_{\text{cumulé}} - \text{TWRR}$ → [Effet timing](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/timing-effect.md)
- **ROI** — le gain de la période rapporté au capital investi : ce que valait le portefeuille au début de la période, plus les dépôts et moins les retraits effectués depuis. Lorsque la plage commence avant votre première transaction, votre premier dépôt compte aussi comme capital, si bien que le ROI est le même que sur tout votre historique → [ROI simple](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/roi.md#dashboard-period-roi)
- **TWRR** — la performance de vos choix d’actifs, quel que soit le timing de vos dépôts → [TWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md)
- **MWRR cumulé** et **MWRR annualisé** — votre rendement personnel, timing des dépôts inclus, sur la période et en taux annuel → [MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)

**Comment la lire**

- **Timing favorable** (vert) : vous avez eu tendance à déposer avant que les prix montent. **Timing défavorable** (rouge) : vous avez eu tendance à déposer aux sommets. Proche de zéro, l’affichage indique **Timing neutre**, ni vert ni rouge.
- **Le TWRR juge la stratégie, le MWRR votre résultat personnel** — comme pour un gérant de fonds et un investisseur.
- **Les quatre lignes couvrent toute la période**.
- **`—` signifie aucune valeur** : un rendement que LibreFolio ne peut pas calculer pour la période affiche `—` au lieu d’un nombre. Le TWRR et le MWRR affichent `—` lorsque votre portefeuille vaut zéro ou moins à la fin de la période, par exemple après que vous avez tout vendu et retiré les liquidités ([Quand aucun TWRR n’est affiché](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/twrr.md#when-no-twrr), [MWRR](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/mwrr.md)). L’effet timing a besoin du TWRR et du MWRR : quand l’un manque, il affiche un `—` gris, sans libellé de timing. Le ROI n’est jamais `—` : sans capital investi sur la période, il affiche `0,00 %`.

---

## 💰 Carte 3 — Valeur nette {: #card-3-net-worth }

Combien vaut votre portefeuille à la fin de la période, et qu’a-t-il gagné depuis le début ? La carte **Valeur nette** répond, liquidités comprises.

<div class="kpi-card-crop-container card-net-worth">
    <img class="gallery-img" data-category="dashboard" data-name="kpi-top" alt="Carte Valeur nette">
</div>

**Indicateurs affichés**

- **Valeur nette** — le grand chiffre : les titres à leur valeur de marché, plus les liquidités, plus tout ce qui est en transit entre vos courtiers → [NAV / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **La ligne en dessous** — par exemple `-1 141 € (-1,95 %)` : de combien votre P&L total a évolué depuis hier, et cette variation en pourcentage par rapport à la valeur du portefeuille d’hier (panneau ci-dessous)
- **Valeur de marché** — ce que valent les actifs que vous détenez aux prix du marché → [NAV / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)
- **Coût d’achat** — ce que vous ont coûté les positions que vous détenez encore, chaque achat au taux de change de sa propre date → [Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)
- **Liquidités** — les liquidités chez vos courtiers ; survolez-les pour séparer le capital que vous avez versé des rendements que vous avez réalisés → [Pools de liquidités](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md#three-pool-cash-model)
- **Capital versé (période)** — les dépôts moins les retraits sur la période, en vert à droite et en rouge à gauche ; survolez-le pour les totaux → [Capital versé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)

$$
\text{P}\&\text{L total} = \text{Valeur nette} - \text{Capital versé depuis le début}
$$

Ce capital correspond à tous les dépôts moins tous les retraits, plus le coût d’achat des titres que vous avez apportés sans liquidités, comme une position d’ouverture ; le ROI entre parenthèses divise le P&L total par ce capital.

**Comment la lire**

- **Date de fin ou période ?** Le grand chiffre et les trois premières lignes sont des valeurs à la date de fin ; le Capital versé (période) ne compte que les mouvements entre le début et la fin.
- **Le petit caret** sur une barre marque sa valeur au début de la période (survolez-le) ; la Valeur de marché passe au rouge lorsqu’elle finit en dessous de cette valeur.
- **La Valeur nette inclut les liquidités**, contrairement à la « valeur des titres » d’un relevé bancaire.
- **Le P&L total n’est pas une variation journalière** : pour le pouls du jour, voir la petite ligne de la Carte 1.

---

## 🔗 Voir aussi

- 🔍 **[Positions et analyse](positions.md)** — les mêmes résultats, position par position
- 📊 **[Graphiques](charts.md)** — la vue **P&L** du graphique de croissance suit votre P&L total dans le temps
- 📐 **[Vue d’ensemble des métriques de performance](../../financial-theory/technical-analysis/performance-metrics/index.md)** — chaque métrique de ces cartes, avec sa formule
- 🛠️ **[Détails techniques](../../developer/frontend/pages/index.md#dashboard)** — pour les développeurs : d’où viennent les chiffres des cartes

---

*[⬅️ Retour à la vue d’ensemble du Tableau de bord](index.md)*
