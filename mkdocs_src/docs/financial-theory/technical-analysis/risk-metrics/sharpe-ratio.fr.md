# 📐 Ratio de Sharpe

Le ratio de Sharpe est la mesure de **rendement ajusté au risque** la plus largement utilisée. Il mesure combien de rendement excédentaire vous recevez par unité de volatilité totale.

---

## 🔢 Formule {: #formula }

$$
S = \frac{R_p - R_f}{\sigma_p}
$$

où :

- $R_p$ = rendement du portefeuille (annualisé)
- $R_f$ = taux sans risque (par exemple, taux des bons du Trésor)
- $\sigma_p$ = écart-type du portefeuille (annualisé)

!!! info "Comment le taux entre dans le calcul"

    Le taux sans risque est fourni sous forme de taux **annuel effectif** et converti en taux **effectif par période** avant utilisation :

    $$
    r_{period} = (1 + r_{annual})^{1/f} - 1
    $$

    où $f$ est le même facteur d'annualisation qui met à l'échelle la volatilité, mesuré à partir des données observées — voir [Annualisation](#annualization). Ce taux par période est soustrait de chaque rendement par période, et les rendements excédentaires résultants sont ce sur quoi le ratio est construit. Utiliser le même $f$ que pour la volatilité maintient le numérateur et le dénominateur sur la même période : appliquer un taux en jours calendaires à des rendements en jours de bourse sous-estimerait la charge et, lorsque le taux est positif, gonflerait le ratio. La conversion tient compte de la capitalisation : un simple $r_{annual}/f$ traiterait le taux comme s'il ne se capitalisait pas sur l'année.

---

## 💡 Interprétation {: #interpretation }

| Ratio de Sharpe | Ce que la valeur signifie |
|---|---|
| $< 0$ | Le portefeuille a rapporté moins que le taux sans risque sur la fenêtre : le rendement excédentaire au numérateur est négatif, donc aucun niveau de volatilité ne peut rendre le ratio positif |
| $0 - 0.5$ | Moins d'une demi-unité de rendement excédentaire par unité de volatilité : le portefeuille a beaucoup évolué par rapport à ce que ce mouvement a rapporté |
| $0.5 - 1.0$ | Entre une demi-unité et une unité de rendement excédentaire par unité de volatilité |
| $1.0 - 2.0$ | D'une à deux unités de rendement excédentaire par unité de volatilité : le rendement excédentaire était supérieur à la volatilité qui l'a produit |
| $> 2.0$ | Plus de deux unités de rendement excédentaire par unité de volatilité — rare sur de longues périodes, beaucoup moins sur des périodes courtes et favorables |

!!! warning "Le même nombre n'est pas la même affirmation"

    Un ratio ne signifie rien s'il est détaché de la fenêtre et de la classe d'actifs sur lesquelles il a été mesuré. Une courte période favorable produit des valeurs qu'un cycle de marché complet ne soutiendrait pas, et les classes d'actifs ayant des rythmes de rendement différents occupent différentes parties de l'échelle par construction. Deux ratios ne sont comparables que lorsqu'ils couvrent la même période et ont été annualisés sur le même facteur observé — voir [Annualisation observée](observed-annualization.md). Le tableau dit ce que le nombre *est*, pas si le résultat était bon : ce jugement nécessite l'objectif pour lequel le portefeuille a été construit.

!!! example "Exemple numérique"

    Rendement du portefeuille : 12 %, Taux sans risque : 3 %, Volatilité : 15 %

    $$S = \frac{0.12 - 0.03}{0.15} = 0.60$$

    Pour chaque 1 % de volatilité, le portefeuille a gagné 0,60 % de rendement excédentaire.

---

## ⚙️ Annualisation {: #annualization }

Un ratio de Sharpe calculé sur des rendements par période est mis à l'échelle en une valeur annuelle par la racine carrée du nombre de périodes que contient une année :

$$
S_{annual} = S_{period} \times \sqrt{f}
$$

Le facteur $f$ est **mesuré à partir des données observées** — le nombre de rendements réellement utilisés, remis à l'échelle sur une année civile complète au prorata de la période qu'ils couvrent :

$$
f = \frac{N \times 365}{D}
$$

où $N$ est le nombre de rendements par période et $D$ le nombre de jours calendaires qu'ils couvrent. La racine carrée vient de la variance qui s'additionne sur des périodes indépendantes, donc la mise à l'échelle suppose que les rendements sont IID (indépendants et identiquement distribués) — une approximation qui ne tient plus pour des rendements autocorrélés.

!!! info "√252 est un résultat, pas une constante"

    Une action cotée quotidiennement fournit environ 252 rendements sur une année civile complète, donc $f \approx 252$ et le fameux $\sqrt{252}$ est retrouvé comme résultat de la mesure plutôt qu'inscrit dans celle-ci. Un instrument coté chaque jour calendaire donne plutôt $f \approx 365$, et un fonds coté hebdomadairement $f \approx 52$.

    → Voir **[Annualisation observée](observed-annualization.md)** pour la dérivation et des exemples détaillés.

---

## ⚠️ Limites {: #limitations }

### 📊 Pénalité symétrique {: #symmetric-penalty }

Le ratio de Sharpe pénalise la **volatilité à la hausse** autant que la volatilité à la baisse. Un actif qui monte fréquemment en flèche (hautement souhaitable !) aura un ratio de Sharpe inférieur à un autre avec le même rendement et moins de mouvement à la hausse.

→ Pour des distributions de rendement asymétriques, préférez le **[Ratio de Sortino](sortino-ratio.md)**.

### 📈 Sensibilité aux valeurs aberrantes {: #sensitivity-to-outliers }

Quelques rendements extrêmes peuvent considérablement fausser l'écart-type, rendant le ratio de Sharpe instable sur de courtes périodes.

### 🔄 Dépendance à la période d'observation {: #time-period-dependency }

Le ratio de Sharpe peut varier considérablement selon la fenêtre d'observation. Une stratégie avec un excellent ratio de Sharpe sur 5 ans peut avoir un mauvais ratio de Sharpe sur 1 an (ou inversement).

---

## 🔗 Voir aussi {: #related }

- 📊 **[Ratio de Sortino](sortino-ratio.md)** — Variante ne considérant que la baisse
- 📊 **[Volatilité](volatility.md)** — Le dénominateur du ratio de Sharpe
- 📈 **[Rendements](../../fundamentals/returns.md)** — Le numérateur du ratio de Sharpe
